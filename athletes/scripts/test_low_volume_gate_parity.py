"""Generator/gate parity for a low-volume, low-frequency athlete.

2026-09-22 order: a time-crunched rider (~5 h/wk, 2-3 rides, kettlebells 3x
a week, back from a crash and concussion, MidSouth B-race then Unbound 100)
got a 34-week plan the review gate blocked with 31 findings, most of them
the generator producing something its own gate rejects:

  HARD_MINUTES_BELOW_FLOOR x26  fixed: gate ignored AE-2.1's ">=6 h/wk" scope
  SHORT_SESSION_BELOW_FLOOR     fixed: B-race easy spin had no recovery role
  VO2_DOSE_OUT_OF_RANGE         fixed: floor growth stretched a 4-min VO2 rep
  UNRESOLVED_PAIN_MAX_...       partly fixed: no retests for genuinely
                                unresolved pain; the rest is a rule conflict
  R05                           PENDING Matti's R05 decision
  VOICE_CONTRACT                PENDING new phrase pools (copy work)
  RACE_STALE                    race-data gap, not code

The profile below is synthetic. The end-to-end test runs the real intake
path once (~15 s): fixed classes must not come back, pending ones are
asserted present so the tests flip when the rulings land.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

from block_compliance import r05_intensity_count, validate_plan  # noqa: E402

FIXED_CLASSES = (
    "HARD_MINUTES_BELOW_FLOOR",
    "SHORT_SESSION_BELOW_FLOOR",
    "VO2_DOSE_OUT_OF_RANGE",
)

# Webhook-shaped questionnaire (webhook/app.py::_questionnaire_to_markdown).
# Thu/Sat/Sun are the only riding days: one quality day fits, the long ride
# is Saturday, and Thursday is two days before the B-race.
LOW_VOLUME_INTAKE = """# Athlete Intake: Synthetic Lowvol
Email: lowvol.synthetic@example.com
Submitted: 2026-09-22

## Basic Info
- Sex: Male
- Age: 38
- Weight: 185 lbs
- Height: 5'11"

## Goals
- Primary Goal: specific_race
- Brand: gravelgod
- Race Slug:
- Course Facts Mode:
- Discipline: gravel
- Race Format:
- Race Demands:
- Road Category:
- Races:
  Unbound 100 (2027-05-29, 100 mi, priority A)
  Mid South (2027-03-13, 100 mi, priority B)
- Success: Finish Strong

## Current Fitness
- FTP: 240
- Training Metric: power
- HR Max:
- HR Threshold:
- W/kg:
- Years Cycling: 6
- Years Structured: 1
- Longest Recent Ride: 3-4 hrs

## Recovery & Baselines
- Resting HR:
- Typical Sleep: 6-7 hours
- Sleep Quality: fair

## Equipment
- Indoor Trainer: smart trainer
- Devices: power meter, head unit

## Schedule
- Weekly Hours Available: 5
- Current Volume: 5
- Long Ride Days: Saturday
- Interval Days: Thursday
- Off Days: Monday, Tuesday, Wednesday, Friday
- Programmed Midweek Max Minutes:
- Travel Dates: None

## Strength
- Current: kettlebell 3 days per week
- Include: yes
- Equipment: kettlebells

## Health
- Current Injuries: Mountain bike crash last year with a concussion; still easing back in

## Work & Life
- Life Stress: high

## Nutrition
- Training Fuel:

## Additional
- Notes: Time-crunched father of three. Ride 2-3 days a week, about 75 miles. I want a structured plan that will not leave me over trained and blasted all the time.

## Fulfillment
- Order ID: synthetic-lowvol-parity
- Delivery Platform: manual
- Order Created At: 2026-09-22T15:00:00
- Generation At: 2026-09-22T15:05:00
- Effective Date:
- Planning Horizon End:
- Publication Horizon Weeks:
- Weeks Purchased:
- Athlete Timezone: America/Chicago
"""


# ---------------------------------------------------------------------------
# R05 -- the rule
# ---------------------------------------------------------------------------

def _load_week(intensity_days):
    days = [{'day': d, 'role': 'intensity' if d in intensity_days else 'filler',
             'name': 'VO2max 30/30' if d in intensity_days else 'Endurance'}
            for d in ('Thu', 'Sat', 'Sun')]
    days[1]['role'] = 'long_ride'
    return {'plan_week': 1, 'week_type': 'load', 'phase': 'base', 'days': days}


def test_r05_pending_matti_still_wants_two_quality_days_on_three_riding_days():
    """PENDING MATTI'S R05 DECISION (docs/proposals/low-volume-intensity-
    floor-2026-09.md). Production R05 is frozen at min(2, max_intensity)
    (SPEC_EARNED_SELECTION A3.0); the registry's "<=3 available cycling days
    allows 1-3" clause is a DRAFT E3 target, and AE-2.1 says any R05
    revision needs owner review and a version bump. So a Thu/Sat/Sun rider
    with one quality day still fails. Update this test with the ruling."""
    result = validate_plan({'weeks': [_load_week({'Thu'})]}, target_hours=5,
                           max_intensity=2, off_days=['Mon', 'Tue', 'Wed', 'Fri'])
    assert not result['rules']['R05']['passed']
    assert '1 intensity (need 2-2)' in result['rules']['R05']['message']
    assert r05_intensity_count([_load_week({'Thu', 'Sun'})], max_per_week=2)[0]


# ---------------------------------------------------------------------------
# VO2 dose -- floor growth goes to Z2, never to a work step
# ---------------------------------------------------------------------------

_PYRAMID = """<workout_file><name>x</name><description>WARM-UP:
- 15 min
</description><workout>
    <Warmup Duration="900" PowerLow="0.50" PowerHigh="0.70"/>
    <SteadyState Duration="240" Power="1.10"/>
    <SteadyState Duration="180" Power="0.55"/>
    <SteadyState Duration="180" Power="1.12"/>
    <SteadyState Duration="180" Power="0.55"/>
    <SteadyState Duration="120" Power="1.17"/>
    <SteadyState Duration="180" Power="0.55"/>
    <SteadyState Duration="60" Power="1.22"/>
    <Cooldown Duration="600" PowerLow="0.70" PowerHigh="0.50"/>
    </workout></workout_file>"""


def _durations(zwo):
    import re
    return [int(v) for v in re.findall(r'Duration="(\d+)"', zwo)]


def test_growing_a_steady_state_vo2_set_keeps_every_rep_intact():
    """Descending VO2 Pyramid is written as SteadyState steps, no IntervalsT,
    so floor growth used to add the whole difference to its largest block --
    the first 110% rep -- turning 4 minutes into 45 (29 min >=106% FTP on
    the real order; AE-3.1 allows 18)."""
    from generate_athlete_package import _zwo_vo2_seconds
    from workout_templates import scale_zwo_to_target_duration
    grown = scale_zwo_to_target_duration(_PYRAMID, 85, 'VO2max Extended', snap_to=60)
    assert sum(_durations(grown)) == 85 * 60
    assert _durations(grown)[1:8] == _durations(_PYRAMID)[1:8]
    assert _zwo_vo2_seconds(grown) == _zwo_vo2_seconds(_PYRAMID) == 600


def test_growing_an_endurance_ride_still_extends_its_z2_block():
    from workout_templates import scale_zwo_to_target_duration
    endurance = ("<workout_file><workout>\n"
                 '    <SteadyState Duration="3000" Power="0.68"/>\n'
                 '    <SteadyState Duration="10" Power="1.20"/>\n'
                 '    <Cooldown Duration="300" PowerLow="0.65" PowerHigh="0.50"/>\n'
                 "    </workout></workout_file>")
    grown = scale_zwo_to_target_duration(endurance, 90, 'Endurance', snap_to=60)
    assert _durations(grown) == [5100, 10, 300]


# ---------------------------------------------------------------------------
# Field tests -- retests follow the gate's pain predicate, W1 follows reanchor
# ---------------------------------------------------------------------------

_ACTIVE = 'Mountain bike crash last year with a concussion; still easing back in'
_HEALED = 'Broke my wrist in 2023, fully healed and cleared'


def _injured(text):
    # Intake stamps every current-injury answer 'active' (the healed case too).
    return {'injury_history': {'current_injuries': [
        {'area': 'general', 'description': text, 'status': 'active'}]}}


def test_healed_language_keeps_the_injury_with_the_coach():
    from post_render_validator import genuinely_unresolved_pain, unresolved_pain_evidence
    for text in (_HEALED, 'Knee pain from 2024, resolved', 'Old back tweak, pain-free now',
                 'Not yet cleared by my doctor'):
        assert unresolved_pain_evidence(_injured(text)), text  # the gate still fires
        assert genuinely_unresolved_pain(_injured(text)) == [], text
    assert genuinely_unresolved_pain(_injured(_ACTIVE))
    assert genuinely_unresolved_pain({'movement_limitations': {'squat': 'painful'}})


def test_only_genuinely_unresolved_pain_withholds_retests():
    from generate_athlete_package import _field_retests_withheld_for_pain
    assert _field_retests_withheld_for_pain(_injured(_ACTIVE)) is True
    assert _field_retests_withheld_for_pain(_injured(_HEALED)) is False
    assert _field_retests_withheld_for_pain({}) is False


def test_pain_never_withdraws_the_promised_week_one_reanchor():
    """The W1 re-anchor is promised by the profile, canonical model, TP
    manifest and guide. Pain leaves it scheduled; the gate puts it in front
    of the coach."""
    from generate_athlete_package import _initial_field_test_required
    for text in (_ACTIVE, _HEALED):
        profile = {**_injured(text),
                   'fitness_markers': {'reanchor': {'required': True, 'week': 1}}}
        assert _initial_field_test_required(profile) is True


def test_b_race_easy_spin_is_published_as_recovery():
    from generate_athlete_package import _b_race_overlay_role
    assert _b_race_overlay_role(True) == {'role': 'recovery'}
    assert _b_race_overlay_role(False) == {}


# ---------------------------------------------------------------------------
# End to end: the synthetic order through the real intake path
# ---------------------------------------------------------------------------

def _run_intake(root, intake_text):
    intake = root / 'intake.md'
    intake.write_text(intake_text)
    env = {key: value for key, value in os.environ.items()
           if key not in ('GG_AUTO_EMAIL', 'GG_STRICT_COMPLIANCE', 'GG_STRICT_QUALITY')}
    env.update({
        'GG_FIXED_NOW': '2026-09-22T15:05:00',
        'GG_ATHLETES_BASE_DIR': str(root / 'athletes'),
        'GG_DELIVERY_DIR': str(root / 'review'),
        'PYTHONPATH': str(SCRIPTS_DIR.parent.parent),
    })
    result = subprocess.run(
        [sys.executable, 'intake_to_plan.py', '--file', str(intake)],
        cwd=str(SCRIPTS_DIR), capture_output=True, text=True, timeout=600, env=env)
    assert result.returncode == 0, result.stdout[-3000:] + result.stderr[-3000:]
    athlete_dir = next((root / 'athletes').iterdir())
    import yaml
    return {
        'state': json.loads((athlete_dir / 'fulfillment_status.json').read_text()),
        'plan_ir': json.loads((athlete_dir / 'plan_ir.json').read_text()),
        'profile': yaml.safe_load((athlete_dir / 'profile.yaml').read_text()),
        'canonical': json.loads((athlete_dir / 'canonical_training_model.json').read_text()),
        'manifest': json.loads((athlete_dir / 'tp_manifest.json').read_text()),
    }


@pytest.fixture(scope='module')
def low_volume_order(tmp_path_factory):
    return _run_intake(tmp_path_factory.mktemp('low-volume-order'), LOW_VOLUME_INTAKE)


def test_low_volume_plan_has_none_of_the_fixed_finding_classes(low_volume_order):
    ids = [item['id'] for item in low_volume_order['state']['blocking_issues']]
    assert not [i for i in ids if i.startswith(FIXED_CLASSES)], ids


def test_low_volume_plan_r05_is_pending_matti(low_volume_order):
    """PENDING MATTI'S R05 DECISION: the generator fits one quality day
    per load week on Thu/Sat/Sun and production R05 still wants two.
    When the ruling lands, move R05 into FIXED_CLASSES or change the
    generator, and delete this test."""
    r05 = [item for item in low_volume_order['state']['blocking_issues']
           if item['id'] == 'R05']
    assert r05 and '1 intensity (need 2-2)' in r05[0]['message']


def test_low_volume_plan_voice_contract_is_pending_phrase_pools(low_volume_order):
    """PENDING new note phrase pools (copy work for Matti): a 35-week plan
    repeats position/notice sentences. The gate now reports every repeat in
    one finding instead of only the last one."""
    voice = [item for item in low_volume_order['state']['blocking_issues']
             if item['id'] == 'VOICE_CONTRACT']
    assert voice and len(voice[0]['review_value']['findings']) > 1


def test_low_volume_plan_really_is_one_quality_day_per_load_week(low_volume_order):
    """Guards the fixture: if the generator ever finds room for two quality
    days here, the R05 test above stops describing the order."""
    counts = {sum(1 for s in week['sessions'] if s.get('role') == 'intensity')
              for week in low_volume_order['plan_ir']['weeks']
              if week.get('week_type') == 'load' and week.get('phase') == 'base'}
    assert counts == {1}


def test_low_volume_plan_schedules_no_field_test(low_volume_order):
    sessions = [s for week in low_volume_order['plan_ir']['weeks'] for s in week['sessions']]
    assert not [s['title'] for s in sessions if s.get('is_field_test')
                or 'test' in str(s.get('title') or '').lower()]
    for item in low_volume_order['state']['blocking_issues']:
        if item['id'] == 'UNRESOLVED_PAIN_MAX_PRESCRIPTION':
            assert not [s for s in item['review_value']['blocked_sessions']
                        if s['field_test']]


def test_b_race_easy_spin_carries_its_recovery_role(low_volume_order):
    easy = [s for week in low_volume_order['plan_ir']['weeks'] for s in week['sessions']
            if s.get('date') == '2027-03-11' and s.get('tp_kind') == 'bike']
    assert easy and all(s.get('role') == 'recovery' for s in easy)


# ---------------------------------------------------------------------------
# End to end: field tests and their promises agree, injured or not
# ---------------------------------------------------------------------------

def _test_control_intake(injury, ftp='240', testing=''):
    text = (LOW_VOLUME_INTAKE
            .replace('- Current Injuries: ' + _ACTIVE, '- Current Injuries: ' + injury)
            .replace('- FTP: 240', '- FTP: ' + ftp)
            # One A race, ~24 weeks: long enough for both retests.
            .replace('  Unbound 100 (2027-05-29, 100 mi, priority A)\n', '')
            .replace('priority B)', 'priority A)'))
    if testing:
        text = text.replace('## Work & Life', '## Testing\n- Include Field Tests: '
                            + testing + '\n\n## Work & Life')
    return text


TEST_CONTROL_CASES = {
    # healed + no FTP: everything as on main -- W1 re-anchor and retests stay,
    # the gate still flags them (intake calls the injury active), coach decides.
    'healed_no_ftp': dict(intake=_test_control_intake(_HEALED, ftp='unknown'),
                          week_one=True, retests=True, pain_finding=True),
    # genuinely unresolved + no FTP: the promised W1 re-anchor stays, retests go.
    'active_no_ftp': dict(intake=_test_control_intake(_ACTIVE, ftp='unknown'),
                          week_one=True, retests=False, pain_finding=True),
    # declined tests: no retests either (FIELD_TEST_SUPPRESSION_BREACH on main).
    'declined': dict(intake=_test_control_intake('None', testing='no'),
                     week_one=False, retests=False, pain_finding=False),
}


@pytest.fixture(scope='module', params=sorted(TEST_CONTROL_CASES))
def test_control_order(request, tmp_path_factory):
    case = TEST_CONTROL_CASES[request.param]
    built = _run_intake(tmp_path_factory.mktemp(request.param), case['intake'])
    return {**case, **built}


def test_field_tests_match_what_the_deliverable_promises(test_control_order):
    order = test_control_order
    reanchor = order['profile']['fitness_markers']['reanchor']
    assert order['canonical']['athlete']['reanchor'] == reanchor
    assert order['manifest']['control']['reanchor'] == reanchor
    tests = sorted((int(week['number']), s['date'])
                   for week in order['plan_ir']['weeks'] for s in week['sessions']
                   if s.get('is_field_test'))
    assert bool(reanchor['required']) is order['week_one']
    assert any(week == 1 for week, _ in tests) is order['week_one'], tests
    assert any(week > 1 for week, _ in tests) is order['retests'], tests
    ids = {item['id'] for item in order['state']['blocking_issues']}
    assert 'FIELD_TEST_SUPPRESSION_BREACH' not in ids
    assert ('UNRESOLVED_PAIN_MAX_PRESCRIPTION' in ids) is order['pain_finding']
