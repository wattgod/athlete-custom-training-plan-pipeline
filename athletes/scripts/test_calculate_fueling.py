import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from calculate_fueling import generate_fueling_context


def _profile(weight, ftp, goal="podium"):
    return {
        "fitness_markers": {"weight_kg": weight, "ftp_watts": ftp, "sex": "female"},
        "target_race": {"distance_miles": 90, "goal_type": goal},
    }


def test_heather_scale_podium_is_not_flat_90g_per_hour():
    fueling = generate_fueling_context(_profile(61, 230))
    prescription = fueling["prescription"]
    assert 60 <= prescription["race_target_g_per_hour"] <= 75
    assert prescription["race_target_g_per_hour"] != 90
    assert prescription["race_target_g_per_hour"] in range(
        prescription["race_range_g_per_hour"][0], prescription["race_range_g_per_hour"][1] + 1)
    assert abs(prescription["total_g"] - prescription["race_target_g_per_hour"] * 5.6) <= 1
    assert any("tolerance was not captured" in item for item in prescription["assumptions"])


def test_heavier_higher_absolute_work_resolves_higher_and_goal_cannot_jump_to_90():
    heather = generate_fueling_context(_profile(61, 230, "finish"))["prescription"]
    heavy = generate_fueling_context(_profile(80, 310, "podium"))["prescription"]
    podium_only = generate_fueling_context(_profile(61, 230, "podium"))["prescription"]
    assert heavy["race_target_g_per_hour"] > heather["race_target_g_per_hour"]
    assert podium_only["race_target_g_per_hour"] < 90
    assert podium_only["race_target_g_per_hour"] - heather["race_target_g_per_hour"] <= 6
