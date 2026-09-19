"""profile library_exclusions.title_regex -> items removed at selection."""
from library_selector import profile_excluded_item_ids


_INDEX = {"items": [
    {"item_id": 1, "name_base": "Better Late Than Cadence", "structure": {"structure": [1]}},
    {"item_id": 2, "name_base": "Low Z2 + HC", "structure": {"structure": [1]}},
    {"item_id": 3, "name_base": "VO2max 30-30 (Billat)", "structure": {"structure": [1]}},
]}


def test_title_regex_matches_case_insensitively():
    assert profile_excluded_item_ids(_INDEX, [r"better late than", r"^Low Z2"]) == frozenset({1, 2})


def test_empty_patterns_exclude_nothing():
    assert profile_excluded_item_ids(_INDEX, []) == frozenset()
    assert profile_excluded_item_ids(_INDEX, None) == frozenset()
