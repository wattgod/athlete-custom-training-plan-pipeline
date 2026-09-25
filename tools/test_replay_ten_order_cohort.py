"""Cohort contract checks; the real generation run is an opt-in CLI rehearsal."""
from pathlib import Path

import pytest

from tools import replay_ten_order_cohort as replay


def test_fixed_cohort_covers_requested_variation_without_reusing_order_identity():
    cases = replay.cohort()
    assert len(cases) == 10
    assert len({case["order_id"] for case in cases}) == 10
    assert {case["label"] for case in cases} == {
        "short_runway", "long_runway", "unknown_ftp_blank", "hr_rpe",
        "full_gym", "no_strength", "joint_a_races", "repeat_buyer_first",
        "repeat_buyer_second", "tight_schedule",
    }
    by_label = {case["label"]: case["intake"] for case in cases}
    assert by_label["unknown_ftp_blank"]["ftp"] == ""
    assert by_label["hr_rpe"]["ftp"] == ""
    assert by_label["no_strength"]["strength_want"] == "no"
    assert len(by_label["joint_a_races"]["races"]) == 2
    assert all(race["priority"] == "A" for race in by_label["joint_a_races"]["races"])
    assert by_label["repeat_buyer_first"]["email"] == by_label["repeat_buyer_second"]["email"]
    assert by_label["repeat_buyer_first"]["name"] == by_label["repeat_buyer_second"]["name"]
    assert by_label["short_runway"]["races"][0]["date"] < by_label["long_runway"]["races"][0]["date"]


def test_existing_output_root_refused(tmp_path: Path):
    (tmp_path / "prior-report.json").write_text("{}")
    with pytest.raises(ValueError, match="must be empty"):
        replay.run_all(tmp_path, limit=1)
