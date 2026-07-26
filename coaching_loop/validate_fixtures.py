"""Validate a TP READ fixture file against tp_fixture.schema.json.

Use this script on both the synthetic fixtures in this repo and on real
captures dropped in later through the parent's authenticated TP browser
session (see coaching_loop/fixtures/README.md for the capture recipe).
The schema is the same for both. No network access. No TP calls. This
script only reads a JSON file from disk.

Usage:
    python3 -m coaching_loop.validate_fixtures <path> [<path> ...]
    python3 -m coaching_loop.validate_fixtures <directory>

Exit code 0 if every file passes. Exit code 1 if any file fails schema
validation or names an excluded athlete.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from coaching_loop.exclusions import ExcludedAthleteError, assert_not_excluded
from coaching_loop.validation import iter_errors


def _iter_target_files(paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for raw in paths:
        p = Path(raw)
        if p.is_dir():
            files.extend(sorted(p.glob("*.json")))
        else:
            files.append(p)
    return files


def validate_file(path: Path) -> list[str]:
    """Return a list of problem strings for `path`. Empty list = pass."""
    problems: list[str] = []
    try:
        with path.open("r", encoding="utf-8") as fh:
            instance = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        return [f"could not read/parse JSON: {exc}"]

    # Drop human-readable documentation keys before validating, same as
    # the fixture loader does -- real captures will not have these, but
    # synthetic fixtures in this repo do.
    if isinstance(instance, dict):
        instance = {k: v for k, v in instance.items() if k != "_note"}

    athlete_id = instance.get("athlete_id") if isinstance(instance, dict) else None
    if athlete_id is not None:
        try:
            assert_not_excluded(athlete_id, layer="validate_fixtures")
        except ExcludedAthleteError as exc:
            problems.append(str(exc))

    for error in iter_errors(instance, "tp_fixture"):
        location = "/".join(str(part) for part in error.absolute_path) or "<root>"
        problems.append(f"{location}: {error.message}")

    return problems


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 1

    files = _iter_target_files(argv)
    if not files:
        print("No files found to validate.")
        return 1

    exit_code = 0
    for path in files:
        problems = validate_file(path)
        if problems:
            exit_code = 1
            print(f"FAIL {path}")
            for problem in problems:
                print(f"  - {problem}")
        else:
            print(f"PASS {path}")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
