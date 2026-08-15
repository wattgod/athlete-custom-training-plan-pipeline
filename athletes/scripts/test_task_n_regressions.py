"""Regression coverage for Task N: descriptions must reflect emitted work."""

import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from act_race_sim import RaceFacts, render_act_sim_zwo
from block_chain import build_plan_from_calendar
from generate_athlete_package import (_format_block_derived_description,
                                      _race_countdown, _replace_fuel_tag)
from workout_library import WorkoutLibrary
from workout_mapper import render_workout
from workout_spec import rewrite_zwo_description
from workout_templates import scale_zwo_to_target_duration


def test_ftp_protocol_description_uses_the_emitted_warmup_and_cooldown():
    blocks = '''<Warmup Duration="600" PowerLow="0.45" PowerHigh="0.70"/>
<SteadyState Duration="300" Power="0.80"/>
<SteadyState Duration="300" Power="0.50"/>
<SteadyState Duration="300" Power="1.05"/>
<SteadyState Duration="300" Power="0.50"/>
<SteadyState Duration="1200" Power="1.00"/>
<Cooldown Duration="600" PowerLow="0.55" PowerHigh="0.40"/>'''
    description = _format_block_derived_description('FTP_Test', blocks)

    assert '-10min building from Z1 to Z2' in description
    assert '-10min easy spin Z1-Z2' in description
    assert '15 min warmup' not in description
    assert '15 min cooldown' not in description
    assert '20min @ 100% FTP' in description


def test_recovery_openers_description_is_only_the_final_emitted_sequence():
    xml = render_workout('Openers', level=1)
    xml = scale_zwo_to_target_duration(xml, 35, 'Openers', snap_to=60)
    xml = rewrite_zwo_description(xml)
    root = ET.fromstring(xml)
    description = root.findtext('description') or ''
    duration = sum(int(node.get('Duration', 0)) for node in root.find('workout'))

    assert duration == 35 * 60
    assert 'WARM-UP:' not in description
    assert 'COOL-DOWN:' not in description
    assert '20min warmup' not in description.lower()
    assert 'MAIN SET:' in description


def test_only_calendar_flagged_act_uses_dress_rehearsal_copy():
    facts = RaceFacts(distance_miles=80, elevation_ft=5000)
    ordinary = ET.fromstring(render_workout('Race Simulation', level=2))
    rehearsal = ET.fromstring(render_act_sim_zwo(
        workout_name='act', display_name='Race Simulation — Act 2 of 2 — Dress Rehearsal',
        duration_min=120, index=2, total=2, facts=facts, author='Test',
        dress_rehearsal=True, race_rate_g_per_hour=70,
    ))
    assert 'dress rehearsal' not in (ordinary.findtext('description') or '').lower()
    assert 'DRESS REHEARSAL:' in (rehearsal.findtext('description') or '')


def test_anaerobic_360_uses_twenty_repeats_except_for_developing_athletes():
    standard = ET.fromstring(render_workout('Anaerobic Test', level=1))
    developing = ET.fromstring(render_workout(
        'Anaerobic Test', level=6, training_age='developing'))
    assert next(node for node in standard.find('workout')
                if node.tag == 'IntervalsT').get('Repeat') == '20'
    assert next(node for node in developing.find('workout')
                if node.tag == 'IntervalsT').get('Repeat') == '10'


def test_cadence_filler_progresses_between_load_weeks():
    plan = build_plan_from_calendar(
        week_descriptors=[
            {'plan_week': 1, 'phase': 'base', 'week_type': 'load'},
            {'plan_week': 2, 'phase': 'base', 'week_type': 'load'},
            {'plan_week': 3, 'phase': 'base', 'week_type': 'recovery'},
        ],
        archetype='specialist', off_days=['Mon'], long_ride_day='Sat',
        hours_per_week=10,
    )
    cadence_levels = [
        (week['plan_week'], day['level'])
        for week in plan['weeks']
        for day in week['days'] if day['name'] == 'Cadence Work'
    ]
    by_week = {}
    for week, level in cadence_levels:
        by_week.setdefault(week, set()).add(level)

    assert by_week[2] == {level + 1 for level in by_week[1]}


def test_power_sessions_are_explicitly_fast_concentric_and_masters_safe():
    session = WorkoutLibrary.get_strength_workout(
        1, 1, equipment_tier='full-gym', phase='peak', is_masters=True)
    prescriptions = ' '.join(reps for _, reps in session['exercises'])

    assert session['name'].startswith('Power A')
    assert '55-65% 1RM' in prescriptions
    assert 'fast' in prescriptions
    assert not re.search(r'jump|hop|plyo', prescriptions, re.I)


def test_fuel_reconciliation_leaves_one_race_fuel_banner_and_singular_countdown():
    xml = '''<workout_file><description>MAIN SET:
- emitted work

[FUEL: Target 50g carbs/hr. Practice this prescription.]

[RACE FUEL: Target 50g carbs/hr. Practice this prescription.]

main</description></workout_file>'''
    reconciled = _replace_fuel_tag(xml, 70)

    assert reconciled.count('[RACE FUEL:') == 1
    assert '[FUEL:' not in reconciled
    assert _race_countdown(1, 'Target Race') == '1 week to Target Race'
