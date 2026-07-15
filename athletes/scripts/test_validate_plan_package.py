"""G5 semantic package gate tests."""
import json
from pathlib import Path

import yaml

from plan_ir import PlanIR, Athlete, RaceSnapshot, Fulfillment, Session, Segment, Week
from validate_plan_package import validate_plan_package


def _package(tmp_path: Path):
    (tmp_path / 'workouts').mkdir()
    zwo = tmp_path / 'workouts' / 'W08_Tue_FTP_Test.zwo'
    zwo.write_text("""<?xml version='1.0' encoding='UTF-8'?><workout_file><name>W08 FTP Test</name><description>Week 8 FTP test\n\nMAIN SET:\n- 4x1min @ 120% FTP, 1min recovery @ 50% FTP</description><workout><IntervalsT Repeat="4" OnDuration="60" OnPower="1.2" OffDuration="60" OffPower="0.5" /></workout></workout_file>""")
    segment = Segment(name='Intervals 4x', kind='intervals', seconds=480, power_low=.5, power_high=1.2,
                      repeat=4, on_seconds=60, on_power=1.2, off_seconds=60, off_power=.5)
    ir = PlanIR(athlete=Athlete(id='heather'), race_snapshot=RaceSnapshot(name='Nannup', elevation_feet=10171),
                fueling={'policy_version': 'x', 'race': {'hourly_target': 70}},
                weeks=[Week(number=8, sessions=[Session(date='2026-01-01', title='W08 FTP Test', sport='cycling', type='ftp_test', origin='prescribed', duration_s=480, tss=1, segments=[segment], source_file=zwo.name)])],
                fulfillment=Fulfillment(status='GENERATED'))
    (tmp_path / 'plan_ir.json').write_text(json.dumps(ir.to_dict()))
    (tmp_path / 'fulfillment_status.json').write_text(json.dumps({'status': 'GENERATED'}))
    (tmp_path / 'fueling.yaml').write_text(yaml.safe_dump({'prescription': ir.to_dict()['fueling']}))
    return zwo


def test_mutated_zwo_interval_duration_is_named_blocking_failure(tmp_path):
    zwo = _package(tmp_path)
    zwo.write_text(zwo.read_text().replace('OnDuration="60"', 'OnDuration="75"'))
    issues = validate_plan_package(tmp_path)
    assert any(issue['id'].startswith('PACKAGE_ZWO_') and 'segments' in issue['message'] for issue in issues)


def test_mutated_ftp_week_label_is_named_blocking_failure(tmp_path):
    zwo = _package(tmp_path)
    zwo.write_text(zwo.read_text().replace('Week 8', 'Week 1'))
    assert any('plan_week' in issue['message'] for issue in validate_plan_package(tmp_path))


def test_mutated_guide_fuel_and_elevation_are_named_blocking_failures(tmp_path):
    _package(tmp_path)
    (tmp_path / 'training_guide.html').write_text('Race target: 69 g/hr; Race elevation: 8202 ft')
    messages = [issue['message'] for issue in validate_plan_package(tmp_path)]
    assert any('training_guide.html.fueling.race_target' in message for message in messages)
    assert any('training_guide.html.race.elevation_feet' in message for message in messages)


def _sub_minute_package(tmp_path: Path):
    """A clean package whose only interval is sub-minute (30/30) — the case that
    regressed the validator: PlanIR stores None-filled Segment dicts and integer
    minute division rounded 30s intervals to '0min'."""
    (tmp_path / 'workouts').mkdir()
    zwo = tmp_path / 'workouts' / 'W05_Tue_VO2_3030.zwo'
    zwo.write_text(
        "<?xml version='1.0' encoding='UTF-8'?><workout_file><name>W05 VO2 30/30</name>"
        "<description>Week 5 VO2\n\nMAIN SET:\n- 9x0.5min @ 110% FTP, 0.25min recovery @ 55% FTP"
        "</description><workout>"
        "<IntervalsT Repeat=\"9\" OnDuration=\"30\" OnPower=\"1.1\" OffDuration=\"15\" OffPower=\"0.55\" />"
        "</workout></workout_file>")
    segment = Segment(name='Intervals 9x', kind='intervals', seconds=405, power_low=.55, power_high=1.1,
                      repeat=9, on_seconds=30, on_power=1.1, off_seconds=15, off_power=.55)
    ir = PlanIR(athlete=Athlete(id='e2e'), race_snapshot=RaceSnapshot(name='Big Sugar', elevation_feet=9500),
                fueling={'policy_version': 'x', 'race': {'hourly_target': 70}},
                weeks=[Week(number=5, sessions=[Session(date='2026-01-01', title='W05 VO2 30/30', sport='cycling',
                        type='vo2max', origin='prescribed', duration_s=405, tss=1, segments=[segment],
                        source_file=zwo.name)])],
                fulfillment=Fulfillment(status='GENERATED'))
    (tmp_path / 'plan_ir.json').write_text(json.dumps(ir.to_dict()))
    (tmp_path / 'fulfillment_status.json').write_text(json.dumps({'status': 'GENERATED'}))
    (tmp_path / 'fueling.yaml').write_text(yaml.safe_dump({'prescription': ir.to_dict()['fueling']}))
    return zwo


def test_clean_package_with_sub_minute_intervals_has_zero_issues(tmp_path):
    """Guards two representation bugs: None-filled PlanIR segments vs compact ZWO
    parse, and integer-minute rounding of 30/30-style intervals to '0min'."""
    _sub_minute_package(tmp_path)
    issues = validate_plan_package(tmp_path)
    assert issues == [], [i['message'][:120] for i in issues]


def _interval_package(tmp_path: Path):
    """Clean package with a 90/90 interval whose recovery renders '1.5min'."""
    (tmp_path / 'workouts').mkdir()
    zwo = tmp_path / 'workouts' / 'W03_Tue_Threshold.zwo'
    zwo.write_text(
        "<?xml version='1.0' encoding='UTF-8'?><workout_file><name>W03 Threshold</name>"
        "<description>Week 3 threshold\n\nMAIN SET:\n- 4x1.5min @ 120% FTP, 1.5min recovery @ 50% FTP"
        "</description><workout>"
        "<IntervalsT Repeat=\"4\" OnDuration=\"90\" OnPower=\"1.2\" OffDuration=\"90\" OffPower=\"0.5\" />"
        "</workout></workout_file>")
    segment = Segment(name='Intervals 4x', kind='intervals', seconds=720, power_low=.5, power_high=1.2,
                      repeat=4, on_seconds=90, on_power=1.2, off_seconds=90, off_power=.5)
    ir = PlanIR(athlete=Athlete(id='e2e'), race_snapshot=RaceSnapshot(name='Big Sugar', elevation_feet=9500),
                fueling={'policy_version': 'x', 'race': {'hourly_target': 70}},
                weeks=[Week(number=3, sessions=[Session(date='2026-01-01', title='W03 Threshold', sport='cycling',
                        type='threshold', origin='prescribed', duration_s=720, tss=1, segments=[segment],
                        source_file=zwo.name)])],
                fulfillment=Fulfillment(status='GENERATED'))
    (tmp_path / 'plan_ir.json').write_text(json.dumps(ir.to_dict()))
    (tmp_path / 'fulfillment_status.json').write_text(json.dumps({'status': 'GENERATED'}))
    (tmp_path / 'fueling.yaml').write_text(yaml.safe_dump({'prescription': ir.to_dict()['fueling']}))
    return zwo


def test_superstring_recovery_duration_is_flagged(tmp_path):
    """A wrong '11.5min recovery' must NOT satisfy a required '1.5min recovery'.
    Substring-per-fragment matching passed this; whole-line matching flags it."""
    zwo = _interval_package(tmp_path)
    assert validate_plan_package(tmp_path) == []  # clean baseline
    zwo.write_text(zwo.read_text().replace('1.5min recovery', '11.5min recovery'))
    assert any('main_set' in i['message'] for i in validate_plan_package(tmp_path))
