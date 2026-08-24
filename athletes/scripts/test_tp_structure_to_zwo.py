"""Contract tests for the C2 TP-structure -> ZWO converter (INTERNAL ONLY,
docs/SPEC_LIBRARY_SELECTION.md D4).

Two layers:
  1. Unit fixtures -- one per mapping case named in the spec, built by hand
     from the real shapes observed in gg_tp_library_full.json.
  2. A property sweep over every workoutTypeId==2 item with a structure in
     the REAL dump (~1,463 items) -- never synthetic fixtures alone. It
     asserts >=95% round-trip pass and writes failing item ids to
     athletes/config/tp_structure_roundtrip_failures.json for C1's
     exclusion hook.
"""
import json
import sys
from collections import Counter
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from tp_structure_to_zwo import (convert_structure, render_full_zwo,
                                 structure_has_hard_effort, verify_round_trip)
from workout_spec import normalize_zwo_blocks

REAL_DUMP_PATH = Path.home() / 'Downloads' / 'guillermo-romero-delivery' / 'gg_tp_library_full.json'
FAILURES_REPORT_PATH = (Path(__file__).parent.parent / 'config'
                         / 'tp_structure_roundtrip_failures.json')


def _wrap(blocks):
    return {'structure': blocks}


def _wrap_rpe(blocks):
    return {'structure': blocks, 'primaryIntensityMetric': 'rpe'}


# =============================================================================
# Unit fixtures -- one per mapping case
# =============================================================================

def test_single_step_renders_steady_state():
    # Real shape: a lone "type": "step" block, length.value=1, one leaf.
    structure = _wrap([
        {'type': 'step', 'length': {'value': 1, 'unit': 'repetition'}, 'steps': [
            {'name': 'Active', 'length': {'value': 600, 'unit': 'second'},
             'targets': [{'minValue': 76, 'maxValue': 85}], 'intensityClass': 'active'},
        ]},
    ])
    result = convert_structure(structure)
    assert result['blocks_xml'].strip() == '<SteadyState Duration="600" Power="0.81"/>'
    assert result['dropped_cadence'] == 0
    ok, detail = verify_round_trip(structure)
    assert ok, detail


def test_repetition_with_work_rest_renders_intervals_t():
    # Real shape from vo2_classic: 6x(3min Z5 / 3min Z1).
    structure = _wrap([
        {'type': 'repetition', 'length': {'value': 6, 'unit': 'repetition'}, 'steps': [
            {'type': 'step', 'name': 'Hard', 'length': {'value': 180, 'unit': 'second'},
             'targets': [{'minValue': 106, 'maxValue': 120}], 'intensityClass': 'active'},
            {'type': 'step', 'name': 'Easy', 'length': {'value': 180, 'unit': 'second'},
             'targets': [{'minValue': 55, 'maxValue': 65}], 'intensityClass': 'rest'},
        ]},
    ])
    result = convert_structure(structure)
    xml = result['blocks_xml']
    assert '<IntervalsT Repeat="6"' in xml
    assert 'OnDuration="180" OnPower="1.13"' in xml
    assert 'OffDuration="180" OffPower="0.60"' in xml
    ok, detail = verify_round_trip(structure)
    assert ok, detail


def test_min_only_target_renders_at_min_over_100():
    structure = _wrap([
        {'type': 'step', 'length': {'value': 1, 'unit': 'repetition'}, 'steps': [
            {'name': 'Recovery', 'length': {'value': 300, 'unit': 'second'},
             'targets': [{'minValue': 55}], 'intensityClass': 'rest', 'openDuration': True},
        ]},
    ])
    result = convert_structure(structure)
    assert result['blocks_xml'].strip() == '<SteadyState Duration="300" Power="0.55"/>'
    ok, detail = verify_round_trip(structure)
    assert ok, detail


def test_both_bounds_target_renders_at_midpoint():
    structure = _wrap([
        {'type': 'step', 'length': {'value': 1, 'unit': 'repetition'}, 'steps': [
            {'name': 'Active', 'length': {'value': 600, 'unit': 'second'},
             'targets': [{'minValue': 55, 'maxValue': 65}], 'intensityClass': 'active'},
        ]},
    ])
    result = convert_structure(structure)
    # midpoint of 55-65 == 60
    assert result['blocks_xml'].strip() == '<SteadyState Duration="600" Power="0.60"/>'
    ok, detail = verify_round_trip(structure)
    assert ok, detail


def test_warmup_intensity_class_renders_ramp_low_to_high():
    # Real shape from vo2_classic: 15min warm up, 55-65% FTP.
    structure = _wrap([
        {'type': 'step', 'length': {'value': 1, 'unit': 'repetition'}, 'steps': [
            {'name': 'Warm up', 'length': {'value': 900, 'unit': 'second'},
             'targets': [{'minValue': 55, 'maxValue': 65}],
             'intensityClass': 'warmUp', 'openDuration': True},
        ]},
    ])
    result = convert_structure(structure)
    xml = result['blocks_xml']
    assert '<Warmup Duration="900" PowerLow="0.55" PowerHigh="0.65"/>' in xml
    ok, detail = verify_round_trip(structure)
    assert ok, detail


def test_cooldown_intensity_class_renders_ramp_high_to_low():
    structure = _wrap([
        {'type': 'step', 'length': {'value': 1, 'unit': 'repetition'}, 'steps': [
            {'name': 'Cool down', 'length': {'value': 600, 'unit': 'second'},
             'targets': [{'minValue': 45, 'maxValue': 65}], 'intensityClass': 'coolDown'},
        ]},
    ])
    result = convert_structure(structure)
    xml = result['blocks_xml']
    # Ramps high -> low: eases off, doesn't build.
    assert '<Cooldown Duration="600" PowerLow="0.65" PowerHigh="0.45"/>' in xml
    ok, detail = verify_round_trip(structure)
    assert ok, detail


def test_open_duration_with_target_free_style_leaf_renders_free_ride():
    # Genuinely target-free leaf (never observed in the real dump, but part
    # of the spec contract): no targets at all -> FreeRide.
    structure = _wrap([
        {'type': 'step', 'length': {'value': 1, 'unit': 'repetition'}, 'steps': [
            {'name': 'Free', 'length': {'value': 120, 'unit': 'second'},
             'targets': [], 'intensityClass': 'active', 'openDuration': True},
        ]},
    ])
    result = convert_structure(structure)
    assert result['blocks_xml'].strip() == '<FreeRide Duration="120"/>'
    ok, detail = verify_round_trip(structure)
    assert ok, detail


def test_open_duration_with_real_target_keeps_steady_state():
    # Judgment call fixture: in the real dump 100% of openDuration leaves
    # (497/497) carry a genuine %FTP target -- honoring openDuration alone
    # as a FreeRide trigger would discard real TSS-bearing data, so the
    # target wins.
    structure = _wrap([
        {'type': 'step', 'length': {'value': 1, 'unit': 'repetition'}, 'steps': [
            {'name': 'Active', 'length': {'value': 3600, 'unit': 'second'},
             'targets': [{'minValue': 56, 'maxValue': 75}],
             'intensityClass': 'active', 'openDuration': True},
        ]},
    ])
    result = convert_structure(structure)
    xml = result['blocks_xml']
    assert '<SteadyState Duration="3600" Power="0.66"' in xml  # midpoint of 56-75 = 65.5 -> 0.65/0.66 (fp rounding)
    ok, detail = verify_round_trip(structure)
    assert ok, detail


def test_cadence_target_emits_cadence_low_high_on_steady_state():
    structure = _wrap([
        {'type': 'step', 'length': {'value': 1, 'unit': 'repetition'}, 'steps': [
            {'name': 'Steady State', 'length': {'value': 300, 'unit': 'second'},
             'targets': [{'minValue': 85}, {'minValue': 100, 'unit': 'roundOrStridePerMinute'}],
             'intensityClass': 'active'},
        ]},
    ])
    result = convert_structure(structure)
    xml = result['blocks_xml']
    assert 'CadenceLow="100" CadenceHigh="100"' in xml
    assert result['dropped_cadence'] == 0
    ok, detail = verify_round_trip(structure)
    assert ok, detail


def test_cadence_target_with_range_emits_low_high():
    structure = _wrap([
        {'type': 'step', 'length': {'value': 1, 'unit': 'repetition'}, 'steps': [
            {'name': 'Hardest', 'length': {'value': 60, 'unit': 'second'},
             'targets': [{'minValue': 106, 'maxValue': 120},
                         {'minValue': 100, 'maxValue': 120, 'unit': 'roundOrStridePerMinute'}],
             'intensityClass': 'active'},
        ]},
    ])
    result = convert_structure(structure)
    assert 'CadenceLow="100" CadenceHigh="120"' in result['blocks_xml']


def test_intervals_off_leg_cadence_is_dropped_and_counted():
    # IntervalsT can only carry one cadence spec (for the on-interval, per
    # nate_workout_generator.generate_intervals_block); an off-leg cadence
    # target has nowhere to go.
    structure = _wrap([
        {'type': 'repetition', 'length': {'value': 3, 'unit': 'repetition'}, 'steps': [
            {'type': 'step', 'name': 'Hard', 'length': {'value': 30, 'unit': 'second'},
             'targets': [{'minValue': 120, 'maxValue': 127},
                         {'minValue': 100, 'unit': 'roundOrStridePerMinute'}],
             'intensityClass': 'active'},
            {'type': 'step', 'name': 'Easy', 'length': {'value': 120, 'unit': 'second'},
             'targets': [{'minValue': 55, 'maxValue': 65},
                         {'minValue': 90, 'unit': 'roundOrStridePerMinute'}],
             'intensityClass': 'rest'},
        ]},
    ])
    result = convert_structure(structure)
    assert result['dropped_cadence'] == 1
    assert any('off-leg cadence' in note for note in result['notes'])
    xml = result['blocks_xml']
    assert 'CadenceLow="100" CadenceHigh="100"' in xml  # on-leg cadence kept
    ok, detail = verify_round_trip(structure)
    assert ok, detail  # cadence isn't part of the power/duration contract


def test_three_substep_repeat_unrolls_never_truncates():
    # Real shape from race_sim "Loaded Climbs": repeat=1 group of 3 distinct
    # sequential leaves (Hardest/Hard/Hardish) -- not a work/rest pair, so it
    # cannot become an IntervalsT and must not be silently truncated to 2.
    structure = _wrap([
        {'type': 'repetition', 'length': {'value': 1, 'unit': 'repetition'}, 'steps': [
            {'type': 'step', 'name': 'Hardest', 'length': {'value': 60, 'unit': 'second'},
             'targets': [{'minValue': 106, 'maxValue': 120}], 'intensityClass': 'active'},
            {'type': 'step', 'name': 'Hard', 'length': {'value': 60, 'unit': 'second'},
             'targets': [{'minValue': 91, 'maxValue': 105}], 'intensityClass': 'active'},
            {'type': 'step', 'name': 'Hardish', 'length': {'value': 2400, 'unit': 'second'},
             'targets': [{'minValue': 87, 'maxValue': 94}], 'intensityClass': 'rest'},
        ]},
    ])
    result = convert_structure(structure)
    segments = normalize_zwo_blocks(result['blocks_xml'])
    assert len(segments) == 3
    assert [s['seconds'] for s in segments] == [60, 60, 2400]
    ok, detail = verify_round_trip(structure)
    assert ok, detail


def test_repeated_three_substep_group_unrolls_all_repeats():
    # repeat=6, 3 leaves per repeat -> 18 sequential elements, not 3.
    structure = _wrap([
        {'type': 'repetition', 'length': {'value': 6, 'unit': 'repetition'}, 'steps': [
            {'type': 'step', 'name': 'A', 'length': {'value': 30, 'unit': 'second'},
             'targets': [{'minValue': 120, 'maxValue': 130}], 'intensityClass': 'active'},
            {'type': 'step', 'name': 'B', 'length': {'value': 30, 'unit': 'second'},
             'targets': [{'minValue': 90, 'maxValue': 100}], 'intensityClass': 'active'},
            {'type': 'step', 'name': 'C', 'length': {'value': 60, 'unit': 'second'},
             'targets': [{'minValue': 55, 'maxValue': 65}], 'intensityClass': 'rest'},
        ]},
    ])
    result = convert_structure(structure)
    segments = normalize_zwo_blocks(result['blocks_xml'])
    assert len(segments) == 18
    ok, detail = verify_round_trip(structure)
    assert ok, detail
    assert detail['source_total_seconds'] == 6 * (30 + 30 + 60)


def test_non_ftp_labeled_target_renders_free_ride_not_garbage_power():
    # Real shape (2 occurrences in the dump): "Power Zone" / RPE labeled
    # targets are not %FTP and must never be divided by 100.
    structure = _wrap([
        {'type': 'step', 'length': {'value': 1, 'unit': 'repetition'}, 'steps': [
            {'length': {'value': 300, 'unit': 'second'}, 'intensityClass': 'active',
             'targets': [{'label': 'Power Zone', 'minValue': 6, 'maxValue': 6}]},
        ]},
    ])
    result = convert_structure(structure)
    assert result['blocks_xml'].strip() == '<FreeRide Duration="300"/>'
    assert any('non-%FTP' in note for note in result['notes'])
    ok, detail = verify_round_trip(structure)
    assert ok, detail


def test_rpe_metric_target_decodes_through_table_not_divided_by_100():
    # DEFECT FIX (coach TP-review, plan 672143, 2026-08-24; AE 9c): a
    # top-level primaryIntensityMetric=="rpe" structure must decode its 1-10
    # RPE points through the coach's table -- never divide by 100 (that
    # shipped "Muscle Recruitment Progressions - Trainer" as 1-4% FTP).
    structure = _wrap_rpe([
        {'type': 'step', 'length': {'value': 1, 'unit': 'repetition'}, 'steps': [
            {'name': 'Low Z3', 'length': {'value': 600, 'unit': 'second'},
             'targets': [{'minValue': 5}], 'intensityClass': 'active'},
        ]},
    ])
    result = convert_structure(structure)
    # RPE5 -> 60-70% FTP bucket, midpoint 65% -> Power 0.65.  NOT 0.05.
    assert result['blocks_xml'].strip() == '<SteadyState Duration="600" Power="0.65"/>'
    ok, detail = verify_round_trip(structure)
    assert ok, detail


def test_rpe_metric_warmup_ramp_decodes_through_table():
    structure = _wrap_rpe([
        {'type': 'step', 'length': {'value': 1, 'unit': 'repetition'}, 'steps': [
            {'name': 'Warm Up', 'length': {'value': 600, 'unit': 'second'},
             'targets': [{'minValue': 1, 'maxValue': 2}], 'intensityClass': 'warmUp'},
        ]},
    ])
    result = convert_structure(structure)
    # RPE1 low (40%) -> RPE2 high (60%). NOT PowerLow=0.01/PowerHigh=0.02.
    assert 'PowerLow="0.40" PowerHigh="0.60"' in result['blocks_xml']
    ok, detail = verify_round_trip(structure)
    assert ok, detail


def test_rpe_metric_no_power_leg_speed_leaf_ships_whole_item_unstructured():
    # DEFECT FIX: the real "Muscle Recruitment Progressions - Trainer" shape
    # -- one leaf explicitly says "no power just leg speed focus". Per the
    # ruling, that leaf's presence means the WHOLE item ships unstructured
    # (FreeRide), even the otherwise-decodable RPE5 leaves.
    structure = _wrap_rpe([
        {'type': 'step', 'length': {'value': 1, 'unit': 'repetition'}, 'steps': [
            {'name': 'Warm Up', 'length': {'value': 600, 'unit': 'second'},
             'targets': [{'minValue': 1, 'maxValue': 2}], 'intensityClass': 'warmUp'},
        ]},
        {'type': 'step', 'length': {'value': 1, 'unit': 'repetition'}, 'steps': [
            {'name': 'Low Z3 60-70rpm', 'length': {'value': 60, 'unit': 'second'},
             'targets': [{'minValue': 5}], 'intensityClass': 'active'},
        ]},
        {'type': 'repetition', 'length': {'value': 6, 'unit': 'repetition'}, 'steps': [
            {'name': 'Leg speed', 'length': {'value': 30, 'unit': 'second'},
             'targets': [{'minValue': 3}], 'intensityClass': 'active',
             'notes': 'no power just leg speed focus'},
            {'name': 'Recovery', 'length': {'value': 60, 'unit': 'second'},
             'targets': [{'minValue': 1, 'maxValue': 2}], 'intensityClass': 'rest'},
        ]},
    ])
    result = convert_structure(structure)
    xml = result['blocks_xml']
    assert 'Power=' not in xml
    assert 'PowerLow=' not in xml
    assert xml.count('<FreeRide') == 1 + 1 + 6 * 2  # warmup, Z3 leaf, 6x(work+rest)
    assert any('ships unstructured' in note for note in result['notes'])
    ok, detail = verify_round_trip(structure)
    assert ok, detail


def test_render_full_zwo_wraps_blocks_with_author_name_description():
    structure = _wrap([
        {'type': 'step', 'length': {'value': 1, 'unit': 'repetition'}, 'steps': [
            {'name': 'Active', 'length': {'value': 600, 'unit': 'second'},
             'targets': [{'minValue': 76, 'maxValue': 85}], 'intensityClass': 'active'},
        ]},
    ])
    blocks_xml = convert_structure(structure)['blocks_xml']
    xml = render_full_zwo(blocks_xml, author='Gravel God Training', name='Test & Drills',
                           description='2 > 1')
    assert '<author>Gravel God Training</author>' in xml
    assert '<name>Test &amp; Drills</name>' in xml
    assert '<description>2 &gt; 1</description>' in xml
    assert '<sportType>bike</sportType>' in xml
    assert '<SteadyState Duration="600" Power="0.81"/>' in xml
    import xml.etree.ElementTree as ET
    ET.fromstring(xml.split("?>\n", 1)[1])  # must parse as valid XML


def test_verify_round_trip_flags_duration_mismatch(monkeypatch):
    import tp_structure_to_zwo as c2

    structure = _wrap([
        {'type': 'step', 'length': {'value': 1, 'unit': 'repetition'}, 'steps': [
            {'name': 'Active', 'length': {'value': 600, 'unit': 'second'},
             'targets': [{'minValue': 76, 'maxValue': 85}], 'intensityClass': 'active'},
        ]},
    ])
    ok, detail = verify_round_trip(structure)
    assert ok and not detail['duration_mismatch']

    # The converter is internally self-consistent by construction (source
    # and rendered totals are both derived from the same walk), so proving
    # this check is load-bearing means simulating a converter bug: make the
    # independent source-total computation disagree with what got emitted.
    real_source_total = c2._source_total_seconds
    monkeypatch.setattr(c2, '_source_total_seconds', lambda structure: real_source_total(structure) + 1)
    ok, detail = verify_round_trip(structure)
    assert not ok
    assert detail['duration_mismatch'] is True


def test_verify_round_trip_flags_power_mismatch(monkeypatch):
    import tp_structure_to_zwo as c2

    structure = _wrap([
        {'type': 'step', 'length': {'value': 1, 'unit': 'repetition'}, 'steps': [
            {'name': 'Active', 'length': {'value': 600, 'unit': 'second'},
             'targets': [{'minValue': 76, 'maxValue': 85}], 'intensityClass': 'active'},
        ]},
    ])
    ok, detail = verify_round_trip(structure)
    assert ok and not detail['power_mismatches']

    # Simulate a converter bug where the emitted XML's Power attribute
    # disagrees with what the leaf actually prescribed (the 'expected' value
    # recorded during the same walk is untouched, so this is a genuine
    # emitted-vs-source mismatch, not a self-consistent shift of both sides).
    real_steady_xml = c2._steady_xml
    monkeypatch.setattr(
        c2, '_steady_xml',
        lambda seconds, power, cadence=None: real_steady_xml(seconds, power + 0.10, cadence))
    ok, detail = verify_round_trip(structure)
    assert not ok
    assert detail['power_mismatches']


def test_empty_structure_round_trips_trivially():
    ok, detail = verify_round_trip(_wrap([]))
    assert ok
    assert detail['source_total_seconds'] == 0
    assert detail['rendered_total_seconds'] == 0


# =============================================================================
# Property sweep over the REAL dump
# =============================================================================

def _iter_real_bike_structure_items():
    if not REAL_DUMP_PATH.exists():
        return []
    with open(REAL_DUMP_PATH) as f:
        data = json.load(f)
    items = []
    for library_key, library in data.items():
        for item in library.get('items', []):
            if item.get('workoutTypeId') == 2 and item.get('structure'):
                items.append((library_key, item))
    return items


@pytest.mark.skipif(not REAL_DUMP_PATH.exists(), reason='real TP dump not present at ' + str(REAL_DUMP_PATH))
def test_round_trip_sweep_over_real_dump():
    items = _iter_real_bike_structure_items()
    assert len(items) > 0, 'expected workoutTypeId==2 items with structure in the real dump'

    passed = 0
    failures = []  # (item_id, item_name, library_key, detail)
    failure_shape_counter = Counter()

    for library_key, item in items:
        item_id = item.get('exerciseLibraryItemId')
        item_name = item.get('itemName')
        try:
            ok, detail = verify_round_trip(item['structure'])
        except Exception as exc:  # a converter crash is also a failure, not a test error
            ok = False
            detail = {'exception': str(exc)}
        if ok:
            passed += 1
        else:
            failures.append((item_id, item_name, library_key, detail))
            if detail.get('segment_count_mismatch'):
                shape = 'segment_count_mismatch'
            elif detail.get('duration_mismatch'):
                shape = 'duration_mismatch'
            elif detail.get('power_mismatches'):
                shape = f"power_mismatch:{detail['power_mismatches'][0].get('kind')}"
            elif 'exception' in detail:
                shape = f"exception:{detail['exception'][:60]}"
            elif 'parse_error' in detail:
                shape = 'parse_error'
            else:
                shape = 'unknown'
            failure_shape_counter[shape] += 1

    total = len(items)
    pass_rate = passed / total

    FAILURES_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(FAILURES_REPORT_PATH, 'w') as f:
        json.dump({
            'total_items': total,
            'passed': passed,
            'failed': len(failures),
            'pass_rate': round(pass_rate, 4),
            'failure_item_ids': [item_id for item_id, *_ in failures],
            'failure_shapes': dict(failure_shape_counter.most_common()),
        }, f, indent=2)

    print(f'\nC2 round-trip sweep: {passed}/{total} passed ({pass_rate:.2%})')
    print(f'Failure shapes: {dict(failure_shape_counter.most_common(10))}')
    for item_id, item_name, library_key, detail in failures[:10]:
        print(f'  FAIL {item_id} [{library_key}] "{item_name}": '
              f"{ {k: v for k, v in detail.items() if k not in ('notes',)} }")

    assert pass_rate >= 0.95, (
        f'round-trip pass rate {pass_rate:.2%} below 95% threshold '
        f'({len(failures)}/{total} failed); see '
        f'{FAILURES_REPORT_PATH} for failing item ids')


# =============================================================================
# R5 (SPEC_LIBRARY_SELECTION.md regrade): structure_has_hard_effort, the
# hard-day detector fed into generate_athlete_package's SEQUENCING/adjacency
# classification for library-resolved sessions.
# =============================================================================

def _leaf(name, seconds, min_value, intensity_class='active'):
    return {
        'name': name,
        'length': {'value': seconds, 'unit': 'second'},
        'targets': [{'minValue': min_value}],
        'intensityClass': intensity_class,
    }


def test_sustained_hard_target_is_hard():
    structure = _wrap([
        {'type': 'step', 'length': {'value': 1, 'unit': 'repetition'},
         'steps': [_leaf('Push', 300, 125)]},
    ])
    assert structure_has_hard_effort(structure)


def test_moderate_sustained_target_is_not_hard():
    structure = _wrap([
        {'type': 'step', 'length': {'value': 1, 'unit': 'repetition'},
         'steps': [_leaf('Steady', 600, 90)]},
    ])
    assert not structure_has_hard_effort(structure)


def test_short_sprint_target_is_not_hard():
    # R1's exact case: 30s @200% is a different stimulus than a sustained
    # push -- must not trip the classifier on duration alone.
    structure = _wrap([
        {'type': 'repetition', 'length': {'value': 6, 'unit': 'repetition'},
         'steps': [_leaf('On', 30, 200), _leaf('Off', 90, 60, 'rest')]},
    ])
    assert not structure_has_hard_effort(structure)


def test_cadence_target_never_counts_toward_hard_effort():
    structure = _wrap([
        {'type': 'step', 'length': {'value': 1, 'unit': 'repetition'},
         'steps': [{
             'name': 'Spin-up', 'length': {'value': 300, 'unit': 'second'},
             'targets': [{'minValue': 60},
                        {'minValue': 100, 'maxValue': 110, 'unit': 'roundOrStridePerMinute'}],
             'intensityClass': 'active',
         }]},
    ])
    assert not structure_has_hard_effort(structure)


def test_empty_structure_is_not_hard():
    assert not structure_has_hard_effort(_wrap([]))
