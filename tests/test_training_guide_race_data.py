from pathlib import Path
import sys


SCRIPTS = Path(__file__).resolve().parents[1] / "athletes" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import training_guide_builder as guides  # noqa: E402


def test_current_climate_description_schema_is_preserved():
    climate = {
        "primary": "Early-autumn southern Poland",
        "description": "The organizer publishes no temperature range; mild or wet conditions are possible.",
    }

    assert guides._climate_text(climate).startswith(
        "The organizer publishes no temperature range"
    )


def test_gravel_race_data_environment_override_is_searched_first(monkeypatch, tmp_path):
    catalog = tmp_path / "race-data"
    monkeypatch.setenv("GUIDE_GRAVEL_RACE_DATA_DIR", str(catalog))

    assert guides._gravel_race_data_dirs(SCRIPTS)[0] == catalog


def test_nutrition_copy_does_not_invent_a_course_mile_marker():
    html = guides._section_nutrition({}, "save_my_race", 61.5)

    assert "GI distress deep into a 61.5-mile race" in html
    assert "GI distress at mile" not in html
