"""Regression coverage for the demand-unit Act simulation composer
(docs/SPEC_DEMAND_UNIT_COMPOSER.md, D1-D7) and T17 race-day pacing.
"""

import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from act_race_sim import (RACE_SIM_SERIES, RaceFacts, act_sim_description,
                          act_sim_title, compose_act_simulation,
                          compose_midweek_sim, composed_if, demand_unit,
                          midweek_sim_description, render_act_sim_zwo,
                          render_midweek_sim_zwo, resolve_race_sim_series)
from generate_athlete_package import (_library_selection_in_scope,
                                      _race_day_pacing_strategy)
from plan_ir import Session, Week, _annotate_delivery_context
from zwo_parser import parse_zwo_text

HIGH = RaceFacts(distance_miles=100, elevation_ft=11000)      # ~110 ft/mi
MODERATE = RaceFacts(distance_miles=100, elevation_ft=8000)   # ~80 ft/mi
FLAT = RaceFacts(distance_miles=100, elevation_ft=6200)       # ~62 ft/mi (Big Sugar band)
UNKNOWN = RaceFacts()


def _duration(segments):
    return sum(
        item['seconds'] if item['kind'] == 'steady'
        else item['repeat'] * (item['on_seconds'] + item['off_seconds'])
        for item in segments
    )


def _unit_labels(segments):
    return [s['label'] for s in segments if s['label'].startswith('Unit ')]


def _z2_gap_durations(segments):
    """Durations of the fixed inter-unit Z2 spacing segments (excludes the
    filler/settle segments, which are labeled '... fill'/'... settle')."""
    return [
        s['seconds'] for s in segments
        if s['kind'] == 'steady' and re.match(r'^Z2 spine \d+$', s['label'])
    ]


# =============================================================================
# D1 — demand unit derivation
# =============================================================================

class TestDemandUnitTotality:
    def test_every_emphasis_resolves_a_unit(self):
        for facts in (HIGH, MODERATE, FLAT, UNKNOWN):
            unit = demand_unit(facts)
            assert unit is not None
            assert unit.pieces
            assert unit.unit_seconds > 0

    def test_high_and_moderate_are_climb_sets_flat_and_unknown_are_rhythm(self):
        assert demand_unit(HIGH).is_rhythm is False
        assert demand_unit(MODERATE).is_rhythm is False
        assert demand_unit(FLAT).is_rhythm is True
        assert demand_unit(UNKNOWN).is_rhythm is True

    def test_high_unit_matches_the_coach_table(self):
        unit = demand_unit(HIGH)
        assert [(p.seconds, p.power) for p in unit.pieces] == [
            (30, 1.23), (270, 1.10), (600, 0.85),
        ]

    def test_flat_unit_matches_the_coach_table(self):
        unit = demand_unit(FLAT)
        on, off = unit.pieces
        assert (on.seconds, on.power) == (170, 0.83)
        assert (off.seconds, off.power) == (10, 1.65)


# =============================================================================
# D2 — density schedule
# =============================================================================

class TestDensitySchedule:
    def test_unit_count_monotone_non_decreasing_across_acts(self):
        # A wide budget (330min) leaves plenty of room for the guard/duration
        # fit not to truncate the target count, so units(k) = 3+k is visible.
        counts = []
        for k in range(1, 7):
            segs = compose_act_simulation(330, k, 6, HIGH)
            counts.append(len(set(_unit_labels(segs))))
        assert counts == sorted(counts)
        assert counts[0] >= 3

    def test_unit_segments_identical_across_acts_only_count_and_spacing_change(self):
        first = compose_act_simulation(240, 1, 4, HIGH)
        second = compose_act_simulation(300, 4, 4, HIGH)
        first_unit1 = [(s['seconds'], s['power']) for s in first
                       if s['label'].startswith('Unit 1 —')]
        second_unit1 = [(s['seconds'], s['power']) for s in second
                        if s['label'].startswith('Unit 1 —')]
        assert first_unit1 == second_unit1

    def test_final_act_tightens_last_gap_to_fifteen_minutes(self):
        non_final = compose_act_simulation(300, 1, 4, HIGH)
        final = compose_act_simulation(300, 4, 4, HIGH)
        non_final_gaps = _z2_gap_durations(non_final)
        final_gaps = _z2_gap_durations(final)
        assert non_final_gaps and all(g == 40 * 60 for g in non_final_gaps)
        assert final_gaps
        assert final_gaps[-1] == 15 * 60
        assert all(g == 40 * 60 for g in final_gaps[:-1])

    def test_consecutive_act_sims_change_structure_and_duration(self):
        first = compose_act_simulation(180, 1, 3, HIGH)
        second = compose_act_simulation(240, 2, 3, HIGH)
        assert _duration(first) == 180 * 60
        assert _duration(second) == 240 * 60
        assert first != second


# =============================================================================
# D3 — the belief guard
# =============================================================================

class TestBeliefGuard:
    def test_duration_exact_to_the_second_across_budgets_and_emphases(self):
        for facts in (HIGH, MODERATE, FLAT, UNKNOWN):
            for total in (3, 4, 6):
                for duration in range(150, 331, 30):
                    for index in range(1, total + 1):
                        segs = compose_act_simulation(duration, index, total, facts)
                        assert _duration(segs) == duration * 60

    def test_composed_if_within_guard_band(self):
        for facts in (HIGH, MODERATE, FLAT, UNKNOWN):
            for total in (3, 4, 6):
                for duration in range(150, 331, 30):
                    for index in range(1, total + 1):
                        segs = compose_act_simulation(duration, index, total, facts)
                        value = composed_if(segs)
                        ceiling = 0.79 if index == total else 0.77
                        assert round(value, 3) <= ceiling, (facts, total, duration, index, value)
                        assert value >= 0.68 - 1e-9, (facts, total, duration, index, value)

    def test_final_act_may_exceed_non_final_ceiling(self):
        # A budget/total combo where the final act's guarded count legitimately
        # lands above 0.77 but still under 0.79 -- non-final acts at the same
        # duration must stay at or under 0.77.
        final_segs = compose_act_simulation(300, 6, 6, HIGH)
        non_final_segs = compose_act_simulation(300, 1, 6, HIGH)
        assert round(composed_if(non_final_segs), 3) <= 0.77
        assert round(composed_if(final_segs), 3) <= 0.79

    def test_tss_recomputed_from_composed_segments_matches_repo_np_formula(self):
        duration_min = 240
        segs = compose_act_simulation(duration_min, 1, 4, HIGH)
        expected_tss = round(composed_if(segs) ** 2 * (duration_min / 60) * 100)
        # A 4hr composed act must land well under the retired composer's
        # ~450 TSS hero-day failure mode.
        assert expected_tss < 300


# =============================================================================
# D4 — the audible
# =============================================================================

class TestAudible:
    def test_audible_present_on_every_act_card(self):
        for facts in (HIGH, FLAT):
            for index, total in ((1, 4), (4, 4)):
                description = act_sim_description(index, total, facts, 240)
                assert 'AUDIBLE:' in description

    def test_rehearsal_fueling_line_only_on_final_act(self):
        non_final = act_sim_description(1, 4, HIGH, 240, dress_rehearsal=False)
        final = act_sim_description(4, 4, HIGH, 300, dress_rehearsal=True,
                                    race_rate_g_per_hour=75)
        assert 'Fueling practice continues at race rate' not in non_final
        assert 'Fueling practice continues at race rate' in final
        assert 'DRESS REHEARSAL:' in final
        assert 'DRESS REHEARSAL:' not in non_final

    def test_audible_wording_differs_climb_set_vs_rhythm_unit(self):
        climb_desc = act_sim_description(1, 4, HIGH, 240)
        rhythm_desc = act_sim_description(1, 4, FLAT, 240)
        assert 'skip the remaining attacks and ride the climbs at tempo' in climb_desc
        assert 'skip the remaining surges and ride the tempo blocks steady' in rhythm_desc

    def test_midweek_card_also_carries_an_audible_line(self):
        assert 'AUDIBLE:' in midweek_sim_description(FLAT, 61)


# =============================================================================
# D5 — description rewrite
# =============================================================================

class TestDescription:
    def test_watts_render_alongside_pct_ftp_for_known_ftp(self):
        with_ftp = act_sim_description(1, 4, HIGH, 240, ftp=250)
        without_ftp = act_sim_description(1, 4, HIGH, 240, ftp=None)
        assert re.search(r'\d+-\d+w', with_ftp)
        assert not re.search(r'\d+-\d+w', without_ftp)

    def test_the_unit_and_the_shape_sections_present(self):
        description = act_sim_description(2, 4, HIGH, 240)
        assert 'THE UNIT:' in description
        assert 'THE SHAPE:' in description
        assert 'Act 2 of 4' in description

    def test_altitude_copy_is_gated_by_supplied_asl_not_climbing_gain(self):
        low_asl = RaceFacts(distance_miles=100, elevation_ft=6200)
        high_asl = RaceFacts(distance_miles=60, elevation_ft=7000, altitude_asl_ft=8100)
        assert 'ride to RPE' not in act_sim_description(1, 2, low_asl, 220)
        assert 'ride to RPE' in act_sim_description(1, 2, high_asl, 220)

        # Big Sugar's supplied gain ratio stays in the flat/rhythm band; total
        # climbing alone never makes it an altitude race, and the composer
        # never bumps power for altitude (D1: RPE-not-watts execution line
        # only, no power change).
        xml = render_act_sim_zwo(
            workout_name='flat', display_name='Flat Act', duration_min=220,
            index=1, total=2, facts=low_asl, author='Test')
        assert 'OffPower="1.65"' in xml  # the rhythm unit's surge, unmodified by altitude

    def test_no_invented_race_name(self):
        # RaceFacts carries no race name; the description must not fabricate one.
        description = act_sim_description(1, 4, HIGH, 240)
        assert 'the race' in description
        assert '{race' not in description

    def test_closing_line_present(self):
        description = act_sim_description(1, 4, HIGH, 240)
        assert 'Boredom is the skill.' in description


# =============================================================================
# ZWO rendering
# =============================================================================

class TestZwoRendering:
    def test_final_act_is_dress_rehearsal_at_race_rate_and_reaches_plan_ir_flag(self):
        title = act_sim_title(3, 3, dress_rehearsal=True)
        xml = render_act_sim_zwo(
            workout_name='W09_Sat_Race_Sim', display_name=title,
            duration_min=300, index=3, total=3, facts=HIGH, author='Test',
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

    def test_zwo_is_valid_and_race_shaped(self):
        xml = render_act_sim_zwo(
            workout_name='w', display_name='Race Simulation — Act 1 of 4',
            duration_min=240, index=1, total=4, facts=HIGH, author='Coach')
        root = ET.fromstring(xml)  # raises if malformed
        powers = {node.get('Power') for node in root.findall('.//SteadyState')}
        assert len(powers) > 3


# =============================================================================
# D6 — curated race-matched sims take precedence
# =============================================================================

class TestRaceSimSeries:
    def test_every_series_entry_resolves_to_exactly_one_index_item(self):
        from tp_library_snapshot import load_index
        idx = load_index()
        for race_id, names in RACE_SIM_SERIES.items():
            for name in names:
                matches = [item for item in idx['items'] if item.get('name_raw') == name]
                assert len(matches) == 1, (race_id, name, len(matches))

    def test_mapped_race_places_verbatim_structure_authored_tss_if(self):
        from tp_library_snapshot import load_index
        idx = load_index()
        names = RACE_SIM_SERIES['usa-cycling-gravel-nationals']
        resolution = resolve_race_sim_series(
            'usa-cycling-gravel-nationals', 2, 4, index_data=idx)
        assert resolution is not None
        source_item = next(
            item for item in idx['items'] if item.get('name_raw') == names[1])
        assert resolution['structure'] == source_item['structure']
        assert resolution['description'] == source_item['description']
        assert resolution['tss'] == source_item['tss']
        assert resolution['if_planned'] == source_item['if_planned']

    def test_last_act_always_resolves_to_last_entry(self):
        resolution = resolve_race_sim_series('unbound_gravel_200', 6, 6)
        assert resolution is not None
        assert resolution['name_base'] == 'Leather Bound'
        assert resolution['duration_min'] == 361  # Leather Bound - 4

    def test_oversize_item_falls_back_to_composer(self):
        # Leather Bound - 4 is 361min; a 200min day cap makes it >15% over.
        resolution = resolve_race_sim_series(
            'unbound_gravel_200', 6, 6, day_cap_min=200)
        assert resolution is None

    def test_unmapped_race_returns_none(self):
        assert resolve_race_sim_series('big_sugar', 1, 4) is None
        assert resolve_race_sim_series(None, 1, 4) is None

    def test_act_simulation_days_are_still_excluded_from_the_general_selector(self):
        # D6 does not re-scope the selector -- act_simulation days must stay
        # excluded even when they also carry a library_resolution attached
        # directly by resolve_race_sim_series.
        day = {
            'name': 'Act Race Simulation', 'role': 'long_ride',
            'act_simulation': {'index': 1, 'total': 4, 'dress_rehearsal': False},
            'library_resolution': {'item_id': 1},
        }
        assert _library_selection_in_scope(day) is False


# =============================================================================
# Compliance: R14 series coherence must not fire on Act days
# =============================================================================

class TestComplianceOnActDays:
    def test_r14_series_coherence_does_not_fire_on_act_days(self):
        from block_chain import build_plan_from_calendar
        from block_compliance import r14_series_coherence

        descriptors = [
            {'plan_week': 1, 'phase': 'build', 'week_type': 'load'},
            {'plan_week': 2, 'phase': 'build', 'week_type': 'load'},
            {'plan_week': 3, 'phase': 'build', 'week_type': 'recovery'},
            {'plan_week': 4, 'phase': 'peak', 'week_type': 'load'},
        ]
        plan = build_plan_from_calendar(
            week_descriptors=descriptors, archetype='specialist',
            off_days=['Mon'], long_ride_day='Sat', hours_per_week=10,
        )
        # Mark eligible long rides as Act sims, mirroring
        # generate_athlete_package.py's Act-day loop.
        from act_race_sim import is_act_sim_eligible
        descriptor_by_week = {d['plan_week']: d for d in descriptors}
        act_days = []
        for week in plan['weeks']:
            descriptor = descriptor_by_week.get(week.get('plan_week'), {})
            for day in week.get('days', []):
                if is_act_sim_eligible(descriptor.get('phase', ''),
                                       descriptor.get('week_type', ''),
                                       day.get('role', '')):
                    act_days.append(day)
        assert act_days  # sanity: the fixture actually exercises Act days
        for day in act_days:
            day['name'] = 'Act Race Simulation'
            day['act_simulation'] = {'index': 1, 'total': len(act_days),
                                     'dress_rehearsal': False}

        passed, _detail = r14_series_coherence(plan)
        assert passed


# =============================================================================
# D7 — midweek (compressed) race simulation
# =============================================================================

class TestMidweekRaceSimulation:
    def test_exact_duration_budget(self):
        for duration in (30, 45, 61, 75, 90):
            segments = compose_midweek_sim(duration, FLAT)
            assert _duration(segments) == duration * 60

    def test_two_units_same_shape_as_long_ride_above_tight_budget(self):
        segments = compose_midweek_sim(120, FLAT)
        long_ride_unit = demand_unit(FLAT)
        midweek_unit1 = [(s['on_seconds'], s['on_power'], s['off_seconds'], s['off_power'])
                         for s in segments if s['label'].startswith('Unit 1 —')]
        assert midweek_unit1 == [
            (long_ride_unit.pieces[0].seconds, long_ride_unit.pieces[0].power,
             long_ride_unit.pieces[1].seconds, long_ride_unit.pieces[1].power)
        ]
        assert len(set(_unit_labels(segments))) == 2

    def test_tight_budget_degrades_to_one_unit(self):
        segments = compose_midweek_sim(40, FLAT)  # under the 45min threshold
        assert len(set(_unit_labels(segments))) == 1

    def test_no_negative_durations_and_has_warmup_cooldown(self):
        for duration in (30, 45, 61, 75, 90):
            segments = compose_midweek_sim(duration, FLAT)
            assert all(
                (s.get('seconds', 0) if s['kind'] == 'steady'
                 else s['repeat'] * (s['on_seconds'] + s['off_seconds'])) >= 0
                for s in segments)
            labels = ' '.join(s['label'] for s in segments)
            assert 'Warm-up' in labels
            assert 'Cooldown' in labels

    def test_zwo_is_race_shaped_not_a_flat_over_under(self):
        zwo = render_midweek_sim_zwo(
            workout_name='test', display_name='Race Simulation — Midweek',
            duration_min=61, facts=FLAT, author='Coach')
        assert 'RACE SIMULATION' in zwo
        powers = set(re.findall(r'Power="([\d.]+)"', zwo))
        assert len(powers) > 3

    def test_midweek_description_names_it_compressed_from_the_long_ride(self):
        description = midweek_sim_description(FLAT, 61)
        assert 'same unit as your long-ride simulations, compressed for a midweek slot' in description.lower()


# =============================================================================
# T17 race-day pacing (unrelated to the composer; unchanged)
# =============================================================================

def test_finisher_nine_hour_pacing_has_no_aggressive_climb_or_pass_people_copy():
    pacing = _race_day_pacing_strategy('finish', 9)
    assert 'Ceiling rule' in pacing
    assert 'First third: deliberately conservative' in pacing
    assert 'hold form, keep eating' in pacing
    assert 'pass people' not in pacing.lower()
    assert '88-94% FTP' not in pacing

    assert '88-94% FTP' in _race_day_pacing_strategy('podium', 4)


def test_bwr_california_resolves_the_waffles_sim_series():
    """Coach ruling Aug 19: the 'Black Canyon (Waffles)' ladder is his BWR
    California series (the item names carry a course landmark, not the race
    name). Both the curated known_races id and the snapshot slug map to it,
    and every named item must exist in the committed index."""
    from act_race_sim import RACE_SIM_SERIES
    from tp_library_snapshot import load_index
    assert "black_canyon" not in RACE_SIM_SERIES
    by_name = {item["name_raw"]: item for item in load_index()["items"]}
    for race_id in ("belgian_waffle_ride", "bwr-california"):
        series = RACE_SIM_SERIES[race_id]
        assert len(series) == 4
        for name in series:
            assert name in by_name, f"{race_id}: {name} missing from index"


def test_torque_hc_authored_rpe_corrected_at_source():
    """Coach ruling Aug 19 ('wrong it seems'): item 14357243 carried RPE8-9
    on a 5x1min @80-85% high-cadence drill (IF 0.645). Corrected to RPE5-6
    in TrainingPeaks and its _MANUAL_REVIEW entry deleted, so it is
    selectable again."""
    from tp_library_snapshot import load_index, _MANUAL_REVIEW
    assert 14357243 not in _MANUAL_REVIEW
    item = next(i for i in load_index()["items"] if i["item_id"] == 14357243)
    assert item["rpe_text"] == "5-6"
    assert not item.get("lint_manual_review")
