"""Library rotation must be seeded on the athlete's stable identity, never on
the authoring directory. Under A1.1 metric authoring generate_zwo_files runs
inside a short-lived ".metric-authoring-<random>" tempdir; seeding on its
name made every build of the same intake draw a different plan (Aug 23 2026:
R06 passed or failed run to run for one unchanged Cheese Head intake).
"""
import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import generate_athlete_package as G


def test_generate_zwo_files_accepts_explicit_seed():
    assert "athlete_seed" in inspect.signature(G.generate_zwo_files).parameters


def test_authoring_call_site_passes_the_athlete_id_as_seed():
    src = inspect.getsource(G.generate_athlete_package)
    assert "athlete_seed=athlete_id" in src


def test_resolution_never_seeds_on_directory_name_alone():
    src = inspect.getsource(G.generate_zwo_files)
    assert "athlete_seed=athlete_dir.name" not in src
    assert "athlete_seed=_seed" in src


def test_ragged_long_block_descriptions_are_advisory_not_excluded():
    import library_selector as L
    assert L._has_ragged_long_block("MAIN SET:\n• 7x (8:08 @57%-67% FTP → 30s @140% FTP)")
    assert not L._has_ragged_long_block("• 4x (1:30 @120% FTP → 2:50 easy)")
    assert not L._has_ragged_long_block("• 2x (20:00 @88% FTP)")
    assert "lint_ragged_duration_text" in L.advisory_flags({"description": "• 8:08 @60% FTP"})
    assert "lint_ragged_duration_text" not in L._lint_flags({"description": "• 8:08 @60% FTP"})
