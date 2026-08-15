"""Regression coverage for T4 Act simulations and T17 race-day pacing."""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from act_race_sim import (RaceFacts, act_sim_description, act_sim_title,
                          compose_act_simulation, render_act_sim_zwo)
from generate_athlete_package import _race_day_pacing_strategy
from plan_ir import Session, Week, _annotate_delivery_context
from zwo_parser import parse_zwo_text


def _duration(segments):
    return sum(
        item['seconds'] if item['kind'] == 'steady'
        else item['repeat'] * (item['on_seconds'] + item['off_seconds'])
        for item in segments
    )


def test_consecutive_act_sims_change_structure_and_duration():
    facts = RaceFacts(distance_miles=100, elevation_ft=6200)
    first = compose_act_simulation(180, 1, 3, facts)
    second = compose_act_simulation(240, 2, 3, facts)

    assert _duration(first) == 180 * 60
    assert _duration(second) == 240 * 60
    assert first != second
    assert any(item['label'].startswith('Act 1') for item in first)
    assert any('low-cadence climb' in item['label'] and item['cadence'] == 55
               for item in second if item['kind'] == 'steady')


def test_final_act_is_dress_rehearsal_at_race_rate_and_reaches_plan_ir_flag():
    facts = RaceFacts(distance_miles=100, elevation_ft=9000)
    title = act_sim_title(3, 3, dress_rehearsal=True)
    xml = render_act_sim_zwo(
        workout_name='W09_Sat_Race_Sim', display_name=title,
        duration_min=300, index=3, total=3, facts=facts, author='Test',
        dress_rehearsal=True, race_rate_g_per_hour=75,
    )
    assert parse_zwo_text(xml, source_name='act')['duration_sec'] == 300 * 60
    assert 'Dress Rehearsal' in title
    assert "race food at the ladder's race rate (75g carbs/hr)" in ET.fromstring(
        xml).findtext('description')

    pre_taper = Week(number=1, week_type='load', sessions=[
        Session(date='2026-09-01', title='Race Simulation — Act 1 of 3',
                sport='cycling', type='workout', origin='generated', duration_s=180 * 60,
                tss=100, tp_kind='bike'),
        Session(date='2026-09-15', title=title, sport='cycling', type='workout',
                origin='generated', duration_s=300 * 60, tss=180, tp_kind='bike'),
    ])
    taper = Week(number=2, week_type='taper')
    _annotate_delivery_context([pre_taper, taper])
    assert pre_taper.sessions[-1].is_simulation
    assert pre_taper.sessions[-1].is_dress_rehearsal


def test_altitude_copy_is_gated_by_supplied_asl_not_climbing_gain():
    low_asl = RaceFacts(distance_miles=100, elevation_ft=6200)
    high_asl = RaceFacts(distance_miles=60, elevation_ft=7000, altitude_asl_ft=8100)
    assert 'ride to RPE' not in act_sim_description(1, 2, low_asl)
    assert 'ride to RPE' in act_sim_description(1, 2, high_asl)

    # Big Sugar's supplied gain ratio stays in the short-climb, punchy-start
    # band; total climbing alone never makes it an altitude race.
    root = ET.fromstring(render_act_sim_zwo(
        workout_name='flat', display_name='Flat Act', duration_min=220,
        index=1, total=2, facts=low_asl, author='Test'))
    low_cadence = [node for node in root.findall('.//SteadyState')
                   if node.get('Cadence') == '55']
    assert low_cadence
    assert all(int(node.get('Duration')) <= 10 * 60 for node in low_cadence)


def test_finisher_nine_hour_pacing_has_no_aggressive_climb_or_pass_people_copy():
    pacing = _race_day_pacing_strategy('finish', 9)
    assert 'Ceiling rule' in pacing
    assert 'First third: deliberately conservative' in pacing
    assert 'hold form, keep eating' in pacing
    assert 'pass people' not in pacing.lower()
    assert '88-94% FTP' not in pacing

    assert '88-94% FTP' in _race_day_pacing_strategy('podium', 4)
