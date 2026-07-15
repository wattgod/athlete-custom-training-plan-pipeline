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
