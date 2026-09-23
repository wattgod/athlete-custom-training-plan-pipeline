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


def test_joint_a_guide_includes_both_source_traced_race_playbooks():
    profile = {'a_events': [
        {'name': 'Mid South', 'date': '2027-03-13', 'priority': 'A', 'race_id': 'mid_south'},
        {'name': 'Unbound Gravel 100', 'date': '2027-06-05', 'priority': 'A',
         'race_id': 'unbound_gravel_100'},
    ]}
    html = guides._section_race_day({}, 'finisher', 100, 'Unbound Gravel 100', '7',
                                    profile=profile)
    assert 'Mid South' in html and 'Unbound Gravel 100' in html
    assert 'sticky' in html and 'sharp flint' in html
    assert 'verify the 2027' in html


def test_race_card_choices_are_event_specific():
    from race_execution_cues import race_card_cues
    mid = race_card_cues('mid_south')
    unbound = race_card_cues('unbound_gravel_100')
    assert 'sticky' in mid and 'Council Grove' not in mid
    assert 'flint' in unbound and 'Council Grove' in unbound


def test_long_ride_dimensions_track_the_next_a_race_only():
    from race_execution_cues import long_ride_dimension_cue
    events = [
        {'name': 'Mid South', 'date': '2027-03-13', 'priority': 'A', 'race_id': 'mid_south'},
        {'name': 'Unbound Gravel 100', 'date': '2027-06-05', 'priority': 'A',
         'race_id': 'unbound_gravel_100'},
    ]
    mid = long_ride_dimension_cue(events, '2027-02-05', 'long_ride', 'load')
    unbound = long_ride_dimension_cue(events, '2027-04-30', 'long_ride', 'load')
    assert 'Mid South' in mid and 'wind' in mid
    assert 'Unbound Gravel 100' in unbound and 'line' in unbound
    assert not long_ride_dimension_cue(events, '2027-05-07', 'long_ride', 'recovery')


def test_strength_guide_states_actual_frequency_day_and_knee_limit():
    html = guides._section_strength_personalization({
        'strength': {'sessions_per_week': 1},
        'schedule_constraints': {'strength_only_days': ['saturday']},
        'movement_limitations': {'deep_squat': 'limited'},
    })
    assert '1 strength session each load week on Saturday' in html
    assert 'skip Saturday' in html
    assert 'deep-squat range is still limited' in html
