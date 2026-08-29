"""Regression tests for two generate_athlete_package defects (2026-08-29).

1. Race-day ZWO filenames were built as ``race_name.replace(' ', '_')`` with
   no path-separator handling. ``Gran Fondo Pekan / Pekan Classic`` is a real
   entry in the race database; generating for an athlete targeting it died
   with FileNotFoundError partway through, AFTER the compliance gate passed.

2. Strength frequency was read only from ``profile.strength.sessions_per_week``
   with a hardcoded default of 2, ignoring ``derived.yaml``'s
   ``strength_frequency``. An athlete whose classifier had already concluded
   ``strength_frequency: 0`` (no equipment, no available days) still got two
   strength sessions a week generated.
"""
import re
import sys
import pathlib

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent))

from generate_athlete_package import safe_filename_component  # noqa: E402


# ---------------------------------------------------------------------------
# 1. Filename sanitisation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", [
    "Unbound Gravel",
    "SBT GRVL",
    "Mad Gravel",
    "The Hibernator 100",
    "L'Étape Mexico City",
    "Rad am Ring Gravel",
    "Belgian Waffle Ride",
])
def test_ordinary_names_keep_the_legacy_underscore_form(name):
    """No reserved character -> byte-identical to the old behaviour.

    This is the compatibility guarantee: fixing the slash case must not
    rename a single existing athlete's workout files.
    """
    assert safe_filename_component(name) == name.replace(" ", "_")


def test_forward_slash_does_not_become_a_path_separator():
    out = safe_filename_component("Gran Fondo Pekan / Pekan Classic")
    assert "/" not in out
    assert out == "Gran_Fondo_Pekan_-_Pekan_Classic"


def test_the_exact_name_that_broke_generation():
    """'TBD — 10/24 event slot' produced a nested path and killed the run."""
    out = safe_filename_component("TBD — 10/24 event slot")
    assert "/" not in out
    assert (pathlib.Path("workouts") / f"W05_{out}.zwo").parent.name == "workouts"


@pytest.mark.parametrize("bad", ['\\', ':', '*', '?', '"', '<', '>', '|'])
def test_every_reserved_character_is_removed(bad):
    out = safe_filename_component(f"Race{bad}Name")
    assert bad not in out


def test_control_characters_are_removed():
    assert "\n" not in safe_filename_component("Race\nName")
    assert "\x00" not in safe_filename_component("Race\x00Name")


@pytest.mark.parametrize("value,expected", [
    (".", "Race"),
    ("..", "Race"),
    ("/", "Race"),
    ("", "Race"),
    ("   ", "Race"),
])
def test_never_produces_a_dot_or_empty_component(value, expected):
    """A filename of '.' or '..' would resolve to a directory, not a file."""
    assert safe_filename_component(value) == expected


def test_result_is_never_hidden_or_dot_prefixed():
    assert not safe_filename_component(".hidden race").startswith(".")


def test_runs_of_reserved_characters_collapse():
    assert safe_filename_component("A///B") == "A-B"


# ---------------------------------------------------------------------------
# 2. Strength frequency source-of-truth
# ---------------------------------------------------------------------------

def _resolve_strength_sessions(profile, derived):
    """Mirror of the resolution order in generate_zwo_files.

    Kept as a copy rather than an import because the real code is a local
    inside a 3,000-line function; this asserts the ORDER is what we fixed it
    to be. If the production order changes, the docstring reference in
    generate_athlete_package.py must change with it.
    """
    derived_strength = (derived or {}).get('strength_frequency')
    if derived_strength is not None:
        return int(derived_strength or 0)
    return int((profile.get('strength', {}) or {}).get('sessions_per_week', 2) or 0)


def test_derived_zero_beats_the_hardcoded_default_of_two():
    """The bug: classifier said 0, generator emitted 2 sessions/week."""
    assert _resolve_strength_sessions({}, {'strength_frequency': 0}) == 0


def test_derived_zero_beats_an_explicit_profile_value():
    profile = {'strength': {'sessions_per_week': 3}}
    assert _resolve_strength_sessions(profile, {'strength_frequency': 0}) == 0


def test_derived_nonzero_is_honoured():
    assert _resolve_strength_sessions({}, {'strength_frequency': 2}) == 2


def test_profile_is_the_fallback_when_derived_is_silent():
    """Athletes generated before the classifier existed keep working."""
    profile = {'strength': {'sessions_per_week': 3}}
    assert _resolve_strength_sessions(profile, {}) == 3


def test_default_of_two_survives_when_neither_source_speaks():
    assert _resolve_strength_sessions({}, {}) == 2


def test_production_code_consults_derived_first():
    """Guard against a refactor silently dropping the derived lookup."""
    src = (pathlib.Path(__file__).parent / 'generate_athlete_package.py').read_text()
    assert "_derived_strength = (derived or {}).get('strength_frequency')" in src
    idx_derived = src.index("_derived_strength = (derived or {}).get('strength_frequency')")
    idx_profile = src.index("(profile.get('strength', {}) or {}).get('sessions_per_week', 2)")
    assert idx_derived < idx_profile, "derived lookup must precede the profile fallback"
