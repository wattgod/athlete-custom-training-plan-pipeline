#!/usr/bin/env python3
"""Regression tests for archetypes in athlete-profiles"""

import re
import xml.etree.ElementTree as ET
from pathlib import Path
import pytest

ROOT_DIR = Path(__file__).parent.parent.parent
ARCHETYPES_PATH = ROOT_DIR / "archetypes"


class TestArchetypeSubmodule:
    def test_submodule_exists(self):
        assert ARCHETYPES_PATH.exists()

    def test_white_paper_exists(self):
        assert (ARCHETYPES_PATH / "WORKOUT_ARCHETYPES_WHITE_PAPER.md").exists()

    def test_architecture_exists(self):
        assert (ARCHETYPES_PATH / "ARCHITECTURE.md").exists()


class TestArchetypeContent:
    def test_critical_archetypes(self):
        content = (ARCHETYPES_PATH / "WORKOUT_ARCHETYPES_WHITE_PAPER.md").read_text().lower()
        for arch in ["vo2", "threshold", "tempo", "endurance"]:
            assert arch in content, f"Missing {arch}"

    def test_six_levels(self):
        content = (ARCHETYPES_PATH / "WORKOUT_ARCHETYPES_WHITE_PAPER.md").read_text().lower()
        assert "level 1" in content and "level 6" in content


class TestZWOFiles:
    @pytest.fixture
    def zwo_dir(self):
        d = ARCHETYPES_PATH / "zwo_output_cleaned"
        if not d.exists():
            d = ARCHETYPES_PATH / "zwo_output"
        return d

    def test_zwo_files_exist(self, zwo_dir):
        if not zwo_dir.exists():
            pytest.skip("No ZWO directory")
        assert len(list(zwo_dir.rglob("*.zwo"))) >= 100

    def test_zwo_valid_xml(self, zwo_dir):
        if not zwo_dir.exists():
            pytest.skip("No ZWO directory")
        for f in list(zwo_dir.rglob("*.zwo"))[:20]:
            ET.parse(f)  # Raises if invalid


class TestBaseline:
    def test_min_archetypes(self):
        content = (ARCHETYPES_PATH / "WORKOUT_ARCHETYPES_WHITE_PAPER.md").read_text()
        archetypes = re.findall(r"^[-*]\s+\*?\*?([a-z0-9_]+)\*?\*?:", content, re.MULTILINE | re.IGNORECASE)
        assert len(archetypes) >= 15


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
