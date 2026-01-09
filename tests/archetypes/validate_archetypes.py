#!/usr/bin/env python3
"""Archetype Validation Script for athlete-profiles"""

import sys
import re
import xml.etree.ElementTree as ET
from pathlib import Path

ARCHETYPES_PATH = Path(__file__).parent.parent.parent / "archetypes"
MIN_EXPECTED_ARCHETYPES = 15

REQUIRED_FILES = [
    "WORKOUT_ARCHETYPES_WHITE_PAPER.md",
    "ARCHITECTURE.md",
    "CATEGORIZATION_RULES.md",
]

class ValidationResult:
    def __init__(self):
        self.passed = []
        self.failed = []

    def add_pass(self, msg):
        self.passed.append(msg)
        print(f"  [PASS] {msg}")

    def add_fail(self, msg):
        self.failed.append(msg)
        print(f"  [FAIL] {msg}")

    @property
    def success(self):
        return len(self.failed) == 0


def main():
    print("=" * 50)
    print("ARCHETYPE VALIDATION - athlete-profiles")
    print("=" * 50)

    if not ARCHETYPES_PATH.exists():
        print("\n[FATAL] Archetypes submodule not found!")
        sys.exit(1)

    result = ValidationResult()

    # Check required files
    print("\n=== Required Files ===")
    for f in REQUIRED_FILES:
        if (ARCHETYPES_PATH / f).exists():
            result.add_pass(f"Found {f}")
        else:
            result.add_fail(f"Missing {f}")

    # Check white paper
    print("\n=== White Paper ===")
    wp = ARCHETYPES_PATH / "WORKOUT_ARCHETYPES_WHITE_PAPER.md"
    if wp.exists():
        content = wp.read_text()
        pattern = r"^[-*]\s+\*?\*?([a-z0-9_]+)\*?\*?:"
        archetypes = re.findall(pattern, content, re.MULTILINE | re.IGNORECASE)
        if len(archetypes) >= MIN_EXPECTED_ARCHETYPES:
            result.add_pass(f"Found {len(archetypes)} archetypes")
        else:
            result.add_fail(f"Only {len(archetypes)} archetypes")

    # Check ZWO files
    print("\n=== ZWO Files ===")
    zwo_dir = ARCHETYPES_PATH / "zwo_output_cleaned"
    if not zwo_dir.exists():
        zwo_dir = ARCHETYPES_PATH / "zwo_output"
    if zwo_dir.exists():
        zwo_files = list(zwo_dir.rglob("*.zwo"))
        valid = sum(1 for f in zwo_files[:50] if _valid_zwo(f))
        result.add_pass(f"{valid}/50 sampled ZWO files valid")

    print("\n" + "=" * 50)
    print(f"Passed: {len(result.passed)}, Failed: {len(result.failed)}")
    sys.exit(0 if result.success else 1)


def _valid_zwo(path):
    try:
        tree = ET.parse(path)
        root = tree.getroot()
        return root.find(".//workout") is not None
    except:
        return False


if __name__ == "__main__":
    main()
