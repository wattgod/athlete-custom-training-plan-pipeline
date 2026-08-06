from pathlib import Path
import sys


SCRIPTS = Path(__file__).resolve().parents[1] / "athletes" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import heat_classifier  # noqa: E402
import training_guide_builder as guides  # noqa: E402


def test_flatten_race_data_accepts_current_climate_description_schema():
    flattened = guides._flatten_race_data({
        "race": {
            "vitals": {"distance_mi": 61.5, "elevation_ft": 889},
            "terrain": {"primary": "Fast forest gravel"},
            "climate": {
                "primary": "Early-autumn southern Poland",
                "description": "The organizer publishes no temperature range; mild or wet conditions are possible.",
            },
        }
    })

    assert flattened["race_characteristics"]["climate"].startswith(
        "The organizer publishes no temperature range"
    )


def test_race_data_environment_overrides_are_searched_first(monkeypatch, tmp_path):
    gravel = tmp_path / "gravel"
    road = tmp_path / "road"
    monkeypatch.setenv("GUIDE_GRAVEL_RACE_DATA_DIR", str(gravel))
    monkeypatch.setenv("GUIDE_ROAD_RACE_DATA_DIR", str(road))

    assert heat_classifier._candidate_race_data_dirs("gravel")[0] == gravel
    assert heat_classifier._candidate_race_data_dirs("road")[0] == road


def test_nutrition_copy_does_not_invent_a_course_mile_marker():
    html = guides._section_nutrition({}, "save_my_race", 61.5)

    assert "GI distress deep into a 61.5-mile race" in html
    assert "GI distress at mile" not in html
