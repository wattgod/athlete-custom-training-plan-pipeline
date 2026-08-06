"""F2 plan-derived fueling labels and guide classification contracts."""

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))

from calculate_fueling import align_fueling_to_plan
from training_guide_builder import _build_nutrition_section, _section_nutrition


def test_plan_labels_are_literal_calendar_weeks_including_w00(tmp_path):
    (tmp_path / 'fueling.yaml').write_text(yaml.safe_dump({
        'prescription': {
            'race_target_g_per_hour': 58,
            'race_range_g_per_hour': [52, 64],
            'total_g': 350,
        },
        'gut_training': {},
    }))
    (tmp_path / 'plan_dates.yaml').write_text(yaml.safe_dump({
        'plan_weeks': 6,
        'weeks': [
            {'week': 0, 'phase': 'lead_in'},
            {'week': 1, 'phase': 'base'},
            {'week': 2, 'phase': 'base'},
            {'week': 3, 'phase': 'build'},
            {'week': 4, 'phase': 'build'},
            {'week': 5, 'phase': 'taper'},
            {'week': 6, 'phase': 'race'},
        ],
    }))
    aligned = align_fueling_to_plan(tmp_path)
    labels = [
        week['week_label']
        for week in aligned['gut_training']['weekly_progression']
    ]
    assert labels == ['W00', 'W1', 'W2', 'W3', 'W4', 'W5', 'W6']
    serialized = yaml.safe_dump(aligned)
    assert '7-14' not in serialized and '15-18' not in serialized
    assert aligned['gut_training']['phases']['race']['target_range'] == [52, 64]


def test_guide_has_one_canonical_personalized_hourly_target():
    fueling = {
        'prescription': {
            'race_target_g_per_hour': 58,
            'race_range_g_per_hour': [52, 64],
            'total_g': 350,
            'hydration': {'target_ml_per_hour': 600, 'electrolytes': 'sodium'},
        },
    }
    personalized = _build_nutrition_section(fueling, {}, store_mode=False)
    education = _section_nutrition({}, 'FINISHER', 75, {
        'demographics': {'weight_lbs': 150}}, plan_duration=6)
    assert 'data-fueling-classification="personalized_prescription"' in personalized
    assert 'data-canonical-carb-target="58"' in personalized
    assert 'YOUR DAILY MACRO TARGETS' not in education
    assert 'data-fueling-classification="generic_education"' in education
    assert 'General guidance, not your target' in education
