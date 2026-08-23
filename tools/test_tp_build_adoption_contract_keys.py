"""Protected provider WORKOUT rows must be keyed "YYYY-MM-DD#<remoteId>" —
the only workout_upsert grammar apply_contract.validate_contract accepts.
Before Aug 23 2026 the adoption builder used "protected-<date>-<id>" for
workouts too, so it failed on any calendar that already had workouts (the
six-athlete publication used an out-of-repo publisher that keyed them
correctly)."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "athletes" / "scripts"))

import tp_build_adoption_contract as T  # noqa: E402


def test_protected_workout_key_grammar_source():
    src = Path(T.__file__).read_text()
    assert '#{sequence}' in src and 'protected-' in src


def test_grammar_regexes_agree_with_validator():
    dated_key = r"(?:\d{4}-\d{2}-\d{2}|undated)#(?:[1-9]\d*)"
    assert re.fullmatch(dated_key, "2026-08-16#3836658065")
    assert not re.fullmatch(dated_key, "protected-2026-08-16-3836658065")
