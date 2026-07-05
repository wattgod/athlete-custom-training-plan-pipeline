#!/usr/bin/env python3
"""
Tests for POST /engine/block — deterministic block generation for Endure Labs
(Convergence Phase 1). Contract is FROZEN; these tests pin the exact enums
and shapes Endure Zod-validates against.

Run with: pytest webhook/tests/test_engine_block.py -v
"""

import os
import sys
import tempfile
from pathlib import Path

import pytest

# Add webhook directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set test environment before importing app (mirrors test_webhook.py)
os.environ.setdefault('FLASK_ENV', 'test')
os.environ.setdefault('WOOCOMMERCE_SECRET', '')
os.environ.setdefault('STRIPE_WEBHOOK_SECRET', '')
os.environ.setdefault('STRIPE_SECRET_KEY', '')
os.environ.setdefault('SYNC_PIPELINE', '1')

# app.py bakes ATHLETES_DIR/SCRIPTS_DIR at import, and test_webhook.py assumes
# ITS fixture performs the first `import app`. When this module runs first in
# a combined session, seed the same shape of environment (a session-lifetime
# mock athletes dir) so the webhook suite keeps its baseline behavior.
_SESSION_TMP = tempfile.TemporaryDirectory()  # module ref → survives the session
_SESSION_ATHLETES = Path(_SESSION_TMP.name) / 'athletes'
(_SESSION_ATHLETES / 'scripts').mkdir(parents=True)
(_SESSION_ATHLETES / 'scripts' / 'generate_full_package.py').write_text(
    '#!/usr/bin/env python3\nimport sys; sys.exit(0)')
os.environ.setdefault('ATHLETES_DIR', str(_SESSION_ATHLETES))
os.environ.setdefault('SCRIPTS_DIR', str(_SESSION_ATHLETES / 'scripts'))

ENGINE_SECRET = 'test-engine-secret'

VALID_WEEK_TYPES = {'load', 'recovery', 'medium', 'race', 'testing'}
VALID_DAYS = {'mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'}
VALID_FUEL_TAGS = {'high', 'moderate', 'practice', 'none'}
VALID_PHASES = ['base', 'build', 'stabilize', 'peak', 'taper', 'race',
                'recovery', 'transition']


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv('ENGINE_SHARED_SECRET', ENGINE_SECRET)
    from app import app as flask_app, limiter
    flask_app.config['TESTING'] = True
    # The endpoint is rate-limited (60/min); this module fires hundreds of
    # requests, so disable the limiter for these tests.
    monkeypatch.setattr(limiter, 'enabled', False)
    with flask_app.test_client() as c:
        yield c


def _payload(**overrides):
    """Baseline valid request; keyword overrides replace top-level keys."""
    body = {
        'athlete': {
            'ftp': 250,
            'hours_per_week': 8,
            'experience_years': 3,
            'age': 38,
            'discipline': 'gravel',
        },
        'block': {
            'phase': 'build',
            'weeks': 3,
            'start_date': '2026-07-06',
        },
    }
    body.update(overrides)
    return body


def _post(client, body, secret=ENGINE_SECRET):
    headers = {}
    if secret is not None:
        headers['X-Engine-Secret'] = secret
    return client.post('/engine/block', json=body, headers=headers)


# =============================================================================
# AUTH
# =============================================================================

class TestAuth:
    def test_missing_env_secret_returns_503(self, client, monkeypatch):
        monkeypatch.delenv('ENGINE_SHARED_SECRET', raising=False)
        resp = _post(client, _payload())
        assert resp.status_code == 503

    def test_wrong_secret_returns_401(self, client):
        resp = _post(client, _payload(), secret='wrong-secret')
        assert resp.status_code == 401

    def test_missing_header_returns_401(self, client):
        resp = client.post('/engine/block', json=_payload())
        assert resp.status_code == 401


# =============================================================================
# HAPPY PATH — 3-week build block (contract snapshot-ish assertions)
# =============================================================================

class TestHappyPath:
    def test_three_week_build_block_shape(self, client):
        resp = _post(client, _payload())
        assert resp.status_code == 200
        data = resp.get_json()

        # Top-level contract keys
        assert set(data.keys()) == {
            'weeks', 'seriesUsed', 'rationale', 'compliance', 'engine'}

        # 3-week block: load / load / recovery
        assert len(data['weeks']) == 3
        assert [w['type'] for w in data['weeks']] == [
            'load', 'load', 'recovery']

        for i, week in enumerate(data['weeks']):
            assert week['number'] == i + 1
            assert week['type'] in VALID_WEEK_TYPES
            assert isinstance(week['strengthProtocol'], str)
            assert week['strengthProtocol']
            assert isinstance(week['blockNote'], str) and week['blockNote']
            assert isinstance(week['targetTss'], int) and week['targetTss'] > 0
            assert isinstance(week['targetHours'], float)
            assert week['targetHours'] > 0
            assert week['workouts'], f"week {i+1} has no workouts"
            for wo in week['workouts']:
                assert wo['day'] in VALID_DAYS
                assert isinstance(wo['coachName'], str) and wo['coachName']
                assert isinstance(wo['durationMinutes'], int)
                assert wo['durationMinutes'] > 0
                assert isinstance(wo['estimatedTss'], int)
                assert wo['estimatedTss'] >= 0
                assert wo['fuelTag'] in VALID_FUEL_TAGS
                assert isinstance(wo['isIntensity'], bool)
                if 'notes' in wo:
                    assert isinstance(wo['notes'], str)

        # Load weeks carry intensity; recovery week only openers-level work
        assert any(wo['isIntensity'] for wo in data['weeks'][0]['workouts'])

        assert isinstance(data['seriesUsed'], list) and data['seriesUsed']
        assert all(isinstance(s, str) for s in data['seriesUsed'])

        assert data['compliance'] == {'passed': True, 'violations': []}

        assert isinstance(data['engine']['version'], str)
        assert isinstance(data['engine']['generated_ms'], int)
        assert data['engine']['generated_ms'] < 500

    def test_rationale_always_empty(self, client):
        for phase in VALID_PHASES:
            body = _payload()
            body['block']['phase'] = phase
            resp = _post(client, body)
            assert resp.status_code == 200, (phase, resp.get_json())
            assert resp.get_json()['rationale'] == ''

    def test_deterministic_output(self, client):
        r1 = _post(client, _payload()).get_json()
        r2 = _post(client, _payload()).get_json()
        r1.pop('engine')
        r2.pop('engine')
        assert r1 == r2

    def test_race_param_accepted_and_ignored(self, client):
        body = _payload(race={
            'name': 'Unbound Gravel 200', 'date': '2026-08-01',
            'distance_mi': 200, 'discipline': 'gravel',
            'unknown_extra': True,
        })
        resp = _post(client, body)
        assert resp.status_code == 200

    def test_race_discipline_used_when_athlete_omits_it(self, client):
        body = _payload(race={'name': 'Giro X', 'discipline': 'road'})
        del body['athlete']['discipline']
        resp = _post(client, body)
        assert resp.status_code == 200

    def test_methodology_variants_all_generate(self, client):
        # NOTE: an explicit methodology engages its selection profile
        # (methodology_profiles.yaml) so the four methods deliver different
        # zone/intensity mixes — distribution assertions live in
        # TestMethodologyDifferentiation. Here: all four must generate and
        # be individually deterministic.
        for m in ['polarized_80_20', 'time_crunched', 'g_spot',
                  'traditional_pyramidal']:
            r1 = _post(client, _payload(methodology=m))
            r2 = _post(client, _payload(methodology=m))
            assert r1.status_code == 200, m
            assert r1.get_json()['seriesUsed'] == r2.get_json()['seriesUsed']

    def test_default_off_day_monday_has_no_workout(self, client):
        resp = _post(client, _payload())
        data = resp.get_json()
        for week in data['weeks']:
            assert all(wo['day'] != 'mon' for wo in week['workouts'])


# =============================================================================
# WEEK STRUCTURES — 2 / 3 / 4 weeks, phase → type mapping
# =============================================================================

class TestWeekStructures:
    def _types(self, client, phase, weeks):
        body = _payload()
        body['block']['phase'] = phase
        body['block']['weeks'] = weeks
        resp = _post(client, body)
        assert resp.status_code == 200, (phase, weeks, resp.get_json())
        return [w['type'] for w in resp.get_json()['weeks']]

    def test_two_week_block_is_load_load(self, client):
        assert self._types(client, 'build', 2) == ['load', 'load']

    def test_three_week_block_ends_in_recovery(self, client):
        assert self._types(client, 'build', 3) == ['load', 'load', 'recovery']

    def test_four_week_block_is_three_load_one_recovery(self, client):
        assert self._types(client, 'build', 4) == [
            'load', 'load', 'load', 'recovery']

    def test_taper_phase_weeks_are_medium(self, client):
        assert self._types(client, 'taper', 2) == ['medium', 'medium']

    def test_race_phase_ends_in_race_week(self, client):
        assert self._types(client, 'race', 2) == ['medium', 'race']

    def test_recovery_phase_weeks_are_recovery(self, client):
        assert self._types(client, 'recovery', 2) == ['recovery', 'recovery']

    def test_transition_phase_weeks_are_recovery(self, client):
        assert self._types(client, 'transition', 3) == [
            'recovery', 'recovery', 'recovery']

    def test_all_phases_all_weeks_generate(self, client):
        for phase in VALID_PHASES:
            for weeks in (2, 3, 4):
                types = self._types(client, phase, weeks)
                assert len(types) == weeks
                assert all(t in VALID_WEEK_TYPES for t in types)


# =============================================================================
# AVAILABILITY
# =============================================================================

class TestAvailability:
    def test_unavailable_day_has_no_workout(self, client):
        body = _payload()
        body['athlete']['availability'] = {
            'wed': {'available': False},
            'fri': {'available': False},
        }
        resp = _post(client, body)
        assert resp.status_code == 200
        for week in resp.get_json()['weeks']:
            days = [wo['day'] for wo in week['workouts']]
            assert 'wed' not in days
            assert 'fri' not in days

    def test_day_duration_cap_respected(self, client):
        body = _payload()
        body['athlete']['availability'] = {
            'tue': {'available': True, 'max_duration_min': 60},
        }
        resp = _post(client, body)
        assert resp.status_code == 200
        for week in resp.get_json()['weeks']:
            for wo in week['workouts']:
                if wo['day'] == 'tue':
                    assert wo['durationMinutes'] <= 60

    def test_full_availability_object(self, client):
        body = _payload()
        body['athlete']['availability'] = {
            'mon': {'available': False},
            'tue': {'available': True, 'max_duration_min': 75},
            'wed': {'available': True, 'max_duration_min': 60},
            'thu': {'available': True, 'max_duration_min': 75},
            'fri': {'available': False},
            'sat': {'available': True, 'max_duration_min': 240},
            'sun': {'available': True, 'max_duration_min': 120},
        }
        resp = _post(client, body)
        assert resp.status_code == 200
        for week in resp.get_json()['weeks']:
            for wo in week['workouts']:
                assert wo['day'] not in ('mon', 'fri')
                caps = {'tue': 75, 'wed': 60, 'thu': 75, 'sat': 240,
                        'sun': 120}
                assert wo['durationMinutes'] <= caps[wo['day']]

    def test_long_ride_lands_on_biggest_available_day(self, client):
        body = _payload()
        body['athlete']['availability'] = {
            'sat': {'available': False},
            'sun': {'available': True, 'max_duration_min': 300},
            'tue': {'available': True, 'max_duration_min': 60},
        }
        resp = _post(client, body)
        assert resp.status_code == 200
        week1 = resp.get_json()['weeks'][0]
        long_rides = [wo for wo in week1['workouts']
                      if 'long ride' in wo.get('notes', '')]
        assert long_rides and long_rides[0]['day'] == 'sun'


# =============================================================================
# PROGRESSION SEED (previous)
# =============================================================================

class TestPreviousSeed:
    def test_previous_levels_raise_starting_level(self, client):
        cold = _post(client, _payload()).get_json()
        body = _payload(previous={
            'seriesUsed': ['VO2max Extended', 'Threshold Progressive'],
            'levels': {'VO2max Extended': 3},
        })
        seeded_resp = _post(client, body)
        assert seeded_resp.status_code == 200
        seeded = seeded_resp.get_json()

        def w1_intensity_levels(data):
            return sorted(
                wo['notes'] for wo in data['weeks'][0]['workouts']
                if wo['isIntensity'])

        assert w1_intensity_levels(seeded) != w1_intensity_levels(cold)
        # Seeded block starts at level 4 (previous max 3 + 1)
        assert any('Level 4' in wo.get('notes', '')
                   for wo in seeded['weeks'][0]['workouts']
                   if wo['isIntensity'])

    def test_previous_seed_is_deterministic(self, client):
        body = _payload(previous={'levels': {'A': 2}})
        r1 = _post(client, body).get_json()
        r2 = _post(client, body).get_json()
        r1.pop('engine')
        r2.pop('engine')
        assert r1 == r2


# =============================================================================
# INVALID REQUESTS — 400 with field errors
# =============================================================================

class TestInvalidRequests:
    def test_non_json_body(self, client):
        resp = client.post('/engine/block', data='not json',
                           content_type='text/plain',
                           headers={'X-Engine-Secret': ENGINE_SECRET})
        assert resp.status_code == 400
        assert resp.get_json()['error'] == 'invalid_request'

    def test_missing_athlete(self, client):
        body = _payload()
        del body['athlete']
        resp = _post(client, body)
        assert resp.status_code == 400
        data = resp.get_json()
        assert data['error'] == 'invalid_request'
        assert 'athlete' in data['fields']

    def test_missing_block(self, client):
        body = _payload()
        del body['block']
        resp = _post(client, body)
        assert resp.status_code == 400
        assert 'block' in resp.get_json()['fields']

    def test_hours_below_buildable_minimum(self, client):
        body = _payload()
        body['athlete']['hours_per_week'] = 2
        resp = _post(client, body)
        assert resp.status_code == 400
        assert 'athlete.hours_per_week' in resp.get_json()['fields']

    def test_hours_wrong_type(self, client):
        body = _payload()
        body['athlete']['hours_per_week'] = 'eight'
        resp = _post(client, body)
        assert resp.status_code == 400
        assert 'athlete.hours_per_week' in resp.get_json()['fields']

    def test_invalid_phase(self, client):
        body = _payload()
        body['block']['phase'] = 'threshold'
        resp = _post(client, body)
        assert resp.status_code == 400
        assert 'block.phase' in resp.get_json()['fields']

    def test_invalid_weeks(self, client):
        for weeks in (1, 5, 'three', None):
            body = _payload()
            body['block']['weeks'] = weeks
            resp = _post(client, body)
            assert resp.status_code == 400, weeks
            assert 'block.weeks' in resp.get_json()['fields']

    def test_invalid_start_date(self, client):
        for bad in ('July 6', '2026-13-40', 20260706, None):
            body = _payload()
            body['block']['start_date'] = bad
            resp = _post(client, body)
            assert resp.status_code == 400, bad
            assert 'block.start_date' in resp.get_json()['fields']

    def test_invalid_methodology(self, client):
        resp = _post(client, _payload(methodology='sweet_spot_only'))
        assert resp.status_code == 400
        assert 'methodology' in resp.get_json()['fields']

    def test_invalid_discipline(self, client):
        body = _payload()
        body['athlete']['discipline'] = 'triathlon'
        resp = _post(client, body)
        assert resp.status_code == 400
        assert 'athlete.discipline' in resp.get_json()['fields']

    def test_unknown_availability_day(self, client):
        body = _payload()
        body['athlete']['availability'] = {'monday': {'available': False}}
        resp = _post(client, body)
        assert resp.status_code == 400
        assert 'athlete.availability.monday' in resp.get_json()['fields']

    def test_too_few_available_days(self, client):
        body = _payload()
        body['athlete']['availability'] = {
            d: {'available': False}
            for d in ('mon', 'tue', 'wed', 'thu', 'fri')
        }
        resp = _post(client, body)
        assert resp.status_code == 400
        assert 'athlete.availability' in resp.get_json()['fields']

    def test_availability_budget_below_minimum(self, client):
        body = _payload()
        body['athlete']['availability'] = {
            'mon': {'available': False}, 'tue': {'available': False},
            'wed': {'available': False}, 'thu': {'available': False},
            'fri': {'available': True, 'max_duration_min': 30},
            'sat': {'available': True, 'max_duration_min': 60},
            'sun': {'available': True, 'max_duration_min': 30},
        }
        resp = _post(client, body)
        assert resp.status_code == 400
        assert 'athlete.availability' in resp.get_json()['fields']

    def test_invalid_previous(self, client):
        resp = _post(client, _payload(previous='block-3'))
        assert resp.status_code == 400
        assert 'previous' in resp.get_json()['fields']

    def test_invalid_previous_levels(self, client):
        resp = _post(client, _payload(previous={'levels': {'A': 'high'}}))
        assert resp.status_code == 400
        assert 'previous.levels' in resp.get_json()['fields']


# =============================================================================
# COMPLIANCE GATE — 422
# =============================================================================

class TestComplianceGate:
    def test_marginal_config_returns_422(self, client):
        """Known marginal config from the domain sweep: 4h/week beginner in a
        build block with partial day caps trips the R03 recovery-ratio
        boundary (86% vs 85% ceiling)."""
        body = _payload()
        body['athlete'].update({'hours_per_week': 4, 'experience_years': 0})
        body['athlete']['availability'] = {
            'mon': {'available': True, 'max_duration_min': 60},
            'sat': {'available': True, 'max_duration_min': 300},
        }
        resp = _post(client, body)
        assert resp.status_code == 422
        data = resp.get_json()
        assert data['error'] == 'compliance_failed'
        assert data['compliance']['passed'] is False
        assert data['compliance']['violations']
        assert any('R03' in v for v in data['compliance']['violations'])

    def test_422_branch_unit(self, client, monkeypatch):
        """Pin the 422 branch independent of core rule tuning."""
        import engine_adapter

        def failing_validate(plan, **kwargs):
            return {
                'critical_pass': False,
                'rules': {'R99': {'severity': 'CRITICAL', 'passed': False,
                                  'message': 'forced failure'}},
            }

        monkeypatch.setattr(engine_adapter, 'validate_plan', failing_validate)
        resp = _post(client, _payload())
        assert resp.status_code == 422
        data = resp.get_json()
        assert data['error'] == 'compliance_failed'
        assert data['compliance'] == {
            'passed': False, 'violations': ['R99: forced failure']}


# =============================================================================
# ADAPTER UNIT TESTS (no HTTP)
# =============================================================================

class TestAdapterUnits:
    def test_fuel_tag_mapping(self):
        from engine_adapter import _fuel_tag
        assert _fuel_tag('Race Simulation', 'intensity') == 'practice'
        assert _fuel_tag('VO2max 30/30', 'intensity') == 'high'
        assert _fuel_tag('Endurance', 'long_ride') == 'moderate'
        assert _fuel_tag('Endurance', 'filler') == 'moderate'
        assert _fuel_tag('Openers', 'intensity') == 'none'
        assert _fuel_tag('Rest Day', 'filler') == 'none'
        assert _fuel_tag('OFF', 'off') == 'none'

    def test_week_descriptors_shapes(self):
        from engine_adapter import build_week_descriptors
        d = build_week_descriptors('build', 4)
        assert [w['week_type'] for w in d] == [
            'load', 'load', 'load', 'recovery']
        assert [w['plan_week'] for w in d] == [1, 2, 3, 4]
        assert all(set(w.keys()) == {'plan_week', 'phase', 'week_type'}
                   for w in d)
        d = build_week_descriptors('race', 3)
        assert [w['week_type'] for w in d] == ['taper', 'taper', 'race']
        d = build_week_descriptors('stabilize', 2)
        assert all(w['phase'] == 'maintenance' for w in d)

    def test_hours_clamped_by_training_age(self):
        from engine_adapter import validate_request
        payload = {
            'athlete': {'hours_per_week': 20, 'experience_years': 0,
                        'age': 38},
            'block': {'phase': 'build', 'weeks': 3,
                      'start_date': '2026-07-06'},
        }
        params, errors = validate_request(payload)
        assert not errors
        assert params['hours_per_week'] == 14  # max_level 2 ceiling
        assert params['archetype'] == 'volume'  # derived from clamped hours

    def test_masters_intensity_cap(self):
        from engine_adapter import validate_request
        payload = {
            'athlete': {'hours_per_week': 10, 'experience_years': 5,
                        'age': 55},
            'block': {'phase': 'build', 'weeks': 3,
                      'start_date': '2026-07-06'},
        }
        params, errors = validate_request(payload)
        assert not errors
        assert params['max_intensity'] == 2

    def test_strength_protocol_deloads_on_recovery(self):
        from engine_adapter import _strength_protocol
        assert 'Deload' in _strength_protocol('build', 'recovery')
        assert 'Maintenance' in _strength_protocol('build', 'load')
        assert 'Anatomical Adaptation' in _strength_protocol('base', 'load')
        assert 'Racing' in _strength_protocol('race', 'race')

    def test_generated_ms_measured(self):
        from engine_adapter import validate_request, generate_block
        params, errors = validate_request(_payload())
        assert not errors
        result = generate_block(params)
        assert 0 <= result['engine']['generated_ms'] < 500


# =============================================================================
# STRUCTURED STRENGTH — additive `strength` field (July 2026)
# =============================================================================

class TestStructuredStrength:
    """Additive per-week `strength` object — structured twin of the
    `strengthProtocol` prose string (same strength_periodization.yaml
    source). Backward compat: nothing pre-existing may change."""

    OLD_WEEK_KEYS = {'number', 'type', 'workouts', 'strengthProtocol',
                     'blockNote', 'targetTss', 'targetHours'}

    def _weeks(self, client, **overrides):
        resp = _post(client, _payload(**overrides))
        assert resp.status_code == 200, resp.get_json()
        return resp.get_json()['weeks']

    def test_strength_present_on_every_week_with_protocol(self, client):
        for phase in VALID_PHASES:
            for weeks in (2, 3, 4):
                body = _payload()
                body['block'].update({'phase': phase, 'weeks': weeks})
                resp = _post(client, body)
                assert resp.status_code == 200, (phase, weeks)
                for week in resp.get_json()['weeks']:
                    assert week['strengthProtocol']  # every week has one
                    strength = week['strength']
                    assert isinstance(strength, dict), (phase, weeks)
                    assert strength['sessions'], (phase, weeks)
                    assert strength['avoidSameDayAs'] == [
                        'threshold', 'vo2max']

    def test_schema_shape(self, client):
        for week in self._weeks(client):
            strength = week['strength']
            assert set(strength.keys()) == {'sessions', 'avoidSameDayAs'}
            for sess in strength['sessions']:
                assert set(sess.keys()) == {
                    'day', 'name', 'focus', 'durationMinutes', 'exercises'}
                assert sess['day'] is None or sess['day'] in VALID_DAYS
                assert isinstance(sess['name'], str) and sess['name']
                assert isinstance(sess['focus'], str) and sess['focus']
                assert isinstance(sess['durationMinutes'], int)
                assert sess['durationMinutes'] > 0
                assert isinstance(sess['exercises'], list)
                assert sess['exercises']
                for ex in sess['exercises']:
                    assert set(ex.keys()) == {
                        'name', 'sets', 'reps', 'intensityPct'}
                    assert isinstance(ex['name'], str) and ex['name']
                    for k in ('sets', 'reps'):
                        assert ex[k] is None or (
                            isinstance(ex[k], int) and ex[k] > 0)
                    assert ex['intensityPct'] is None or (
                        isinstance(ex['intensityPct'], int)
                        and 1 <= ex['intensityPct'] <= 100)

    def test_days_avoid_intensity_and_off_days(self, client):
        """Placed sessions never share a day with an intensity workout, the
        long ride, or an athlete off-day (off days carry no workout, so a
        valid day must belong to a non-intensity, non-long-ride workout)."""
        for phase in VALID_PHASES:
            body = _payload()
            body['block']['phase'] = phase
            resp = _post(client, body)
            assert resp.status_code == 200, phase
            for week in resp.get_json()['weeks']:
                easy_days = {
                    w['day'] for w in week['workouts']
                    if not w['isIntensity']
                    and 'long ride' not in w.get('notes', '')
                }
                for sess in week['strength']['sessions']:
                    if sess['day'] is not None:
                        assert sess['day'] in easy_days, (
                            phase, week['number'], sess['day'])
                        assert sess['day'] != 'mon'  # default off day

    def test_days_respect_custom_off_days(self, client):
        body = _payload()
        body['athlete']['availability'] = {
            'wed': {'available': False},
            'fri': {'available': False},
        }
        resp = _post(client, body)
        assert resp.status_code == 200
        for week in resp.get_json()['weeks']:
            for sess in week['strength']['sessions']:
                assert sess['day'] not in ('wed', 'fri')

    def test_sessions_spaced_apart(self, client):
        """When 2+ sessions are placed they never land back-to-back-same-day
        and keep at least 1 day between them (2 preferred)."""
        day_idx = {d: i for i, d in enumerate(
            ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'])}
        for week in self._weeks(client):
            placed = sorted(day_idx[s['day']]
                            for s in week['strength']['sessions']
                            if s['day'] is not None)
            assert len(placed) == len(set(placed))  # no double-day
            for a, b in zip(placed, placed[1:]):
                assert b - a >= 1

    def test_matches_protocol_phase(self, client):
        """The structured focus must agree with the prose protocol — both
        derive from the same YAML phase key."""
        cases = {
            'base': 'anatomical_adaptation',
            'build': 'maintenance',
            'peak': 'race_prep',
            'race': 'racing',
            'recovery': 'deload',
        }
        for phase, expected_focus in cases.items():
            body = _payload()
            body['block']['phase'] = phase
            resp = _post(client, body)
            assert resp.status_code == 200, phase
            weeks = resp.get_json()['weeks']
            first = weeks[0]
            assert all(s['focus'] == expected_focus
                       for s in first['strength']['sessions']), phase
            label = expected_focus.replace('_', ' ').title()
            assert first['strengthProtocol'].startswith(label)
            # Recovery week inside a load-bearing block always deloads —
            # string and structure together.
            for week in weeks:
                if week['type'] == 'recovery':
                    assert all(s['focus'] == 'deload'
                               for s in week['strength']['sessions'])
                    assert week['strengthProtocol'].startswith('Deload')

    def test_deload_is_bodyweight(self, client):
        weeks = self._weeks(client, block={'phase': 'recovery', 'weeks': 3,
                                           'start_date': '2026-07-06'})
        for week in weeks:
            for sess in week['strength']['sessions']:
                for ex in sess['exercises']:
                    assert ex['sets'] is None
                    assert ex['reps'] is None
                    assert ex['intensityPct'] is None

    def test_maintenance_numbers_match_yaml(self, client):
        """build → maintenance: 3 × 5 @ 75% 1RM, 2x/week (exact YAML pin)."""
        weeks = self._weeks(client)
        load_week = weeks[0]
        sessions = load_week['strength']['sessions']
        assert len(sessions) == 2  # 2x/week
        for ex in sessions[0]['exercises']:
            assert ex['sets'] == 3
            assert ex['reps'] == 5
            assert ex['intensityPct'] == 75
        assert any(ex['name'] == 'Back Squat'
                   for ex in sessions[0]['exercises'])

    def test_backward_compat_old_fields_untouched(self, client):
        """`strength` is purely additive: every pre-existing week field is
        still present with its pre-existing shape, and the top level is
        unchanged apart from nothing (strength lives inside weeks)."""
        resp = _post(client, _payload())
        assert resp.status_code == 200
        data = resp.get_json()
        assert set(data.keys()) == {
            'weeks', 'seriesUsed', 'rationale', 'compliance', 'engine'}
        for week in data['weeks']:
            assert set(week.keys()) == self.OLD_WEEK_KEYS | {'strength'}
            assert isinstance(week['strengthProtocol'], str)
            assert week['strengthProtocol']
            assert isinstance(week['workouts'], list)
            assert isinstance(week['targetTss'], int)
            assert isinstance(week['targetHours'], float)

    def test_deterministic(self, client):
        r1 = _post(client, _payload()).get_json()
        r2 = _post(client, _payload()).get_json()
        assert [w['strength'] for w in r1['weeks']] == \
               [w['strength'] for w in r2['weeks']]


# =============================================================================
# RACE DEMAND VECTOR — event-specific selection bias (Phase 2)
# =============================================================================

class TestRaceDemandVector:
    """The race{} object is now WIRED: a conservative 8-dim demand vector
    derived from distance/elevation/discipline biases which archetypes fill
    the intensity + long-ride slots. No race → byte-identical to before."""

    def test_demand_heuristic_table(self):
        from engine_adapter import derive_race_demands
        # Ultra-distance → max durability; unknown dims sit neutral (5).
        d = derive_race_demands(200, 11000, 'gravel')
        assert d['durability'] == 10
        assert d['technical'] == 5   # gravel
        assert d['vo2_power'] == 5   # no wire signal → neutral
        assert d['heat_resilience'] == d['altitude'] == 5
        # Short crit → low durability, road technical floor.
        d = derive_race_demands(30, 500, 'road')
        assert d['durability'] == 1
        assert d['technical'] == 2
        # MTB is technical-heavy.
        assert derive_race_demands(40, 4000, 'mtb')['technical'] == 8
        # Distance bands (race_demand_analyzer parity).
        assert derive_race_demands(150, 0, 'gravel')['durability'] == 8
        assert derive_race_demands(100, 0, 'gravel')['durability'] == 6
        assert derive_race_demands(75, 0, 'gravel')['durability'] == 4
        assert derive_race_demands(50, 0, 'gravel')['durability'] == 2
        assert derive_race_demands(10, 0, 'gravel')['durability'] == 1

    def test_demand_climbing_ratio(self):
        from engine_adapter import derive_race_demands
        # High ft/mi → steep climbing demand; flat → low.
        steep = derive_race_demands(60, 12000, 'gravel')   # 200 ft/mi
        flat = derive_race_demands(100, 1000, 'gravel')    # 10 ft/mi
        assert steep['climbing'] > flat['climbing']
        assert steep['climbing'] >= 9
        assert flat['climbing'] <= 2

    def test_demand_all_dims_clamped_0_10(self):
        from engine_adapter import derive_race_demands
        from race_category_scorer import DEMAND_DIMENSIONS
        for dist, elev, disc in [(350, 90000, 'mtb'), (1, 0, 'road'),
                                 (None, None, 'gravel'), (131, 11000, 'gravel')]:
            d = derive_race_demands(dist, elev, disc)
            assert set(d.keys()) == set(DEMAND_DIMENSIONS)
            assert all(0 <= v <= 10 for v in d.values())

    def test_no_race_is_byte_identical(self, client):
        """The determinism-diff pin: adding NO race must not change a byte."""
        without = _post(client, _payload()).get_json()
        # Same request, race key absent (default payload has none).
        again = _post(client, _payload()).get_json()
        without.pop('engine'); again.pop('engine')
        assert without == again

    def test_long_distance_race_biases_selection(self, client):
        """A 131mi durability race changes the intensity/long-ride series vs
        the identical request with no race (observable selection bias)."""
        body = _payload()
        body['athlete'].update({'hours_per_week': 12, 'experience_years': 5})
        body['block'] = {'phase': 'base', 'weeks': 4,
                         'start_date': '2026-07-06'}
        no_race = _post(client, body).get_json()
        assert no_race['compliance']['passed']

        raced = dict(body)
        raced['race'] = {'name': 'Big Sugar', 'distance_mi': 131,
                         'elevation_ft': 11000, 'discipline': 'gravel'}
        with_race = _post(client, raced).get_json()
        assert with_race['compliance']['passed']
        assert with_race['seriesUsed'] != no_race['seriesUsed']

    def test_elevation_ft_field_accepted(self, client):
        resp = _post(client, _payload(race={
            'name': 'Steep', 'distance_mi': 80, 'elevation_ft': 14000,
            'discipline': 'gravel'}))
        assert resp.status_code == 200

    def test_race_bias_is_deterministic(self, client):
        body = _payload(race={'name': 'X', 'distance_mi': 200,
                              'elevation_ft': 11000, 'discipline': 'gravel'})
        r1 = _post(client, body).get_json()
        r2 = _post(client, body).get_json()
        r1.pop('engine'); r2.pop('engine')
        assert r1 == r2

    def test_garbage_race_fields_do_not_400(self, client):
        """distance_mi/elevation_ft were always free-form on the frozen
        contract — bad types are treated as UNKNOWN, never a validation error."""
        resp = _post(client, _payload(race={
            'name': 'X', 'distance_mi': 'lots', 'elevation_ft': None,
            'discipline': 'gravel'}))
        assert resp.status_code == 200

    def test_extreme_race_never_breaks_compliance(self, client):
        """Race bias must NEVER violate the R01-R11 gate — sweep extremes
        across every phase/weeks combination."""
        for phase in VALID_PHASES:
            for weeks in (2, 3, 4):
                for dist, elev in [(1, 0), (350, 90000), (131, 11000)]:
                    body = _payload()
                    body['athlete'].update({'hours_per_week': 12,
                                            'experience_years': 5})
                    body['block'] = {'phase': phase, 'weeks': weeks,
                                     'start_date': '2026-07-06'}
                    body['race'] = {'name': 'X', 'distance_mi': dist,
                                    'elevation_ft': elev, 'discipline': 'mtb'}
                    resp = _post(client, body)
                    assert resp.status_code == 200, (phase, weeks, dist, elev,
                                                     resp.get_json())


# =============================================================================
# SERIES ROTATION ACROSS BLOCKS (previous.seriesUsed)
# =============================================================================

class TestSeriesRotation:
    """previous.seriesUsed is now WIRED: consecutive blocks rotate to
    alternatives NOT in the previous block's series (intensity + long-ride
    slots). Exhausted pools reuse rather than crash."""

    def _big(self, **extra):
        body = _payload()
        body['athlete'].update({'hours_per_week': 12, 'experience_years': 5})
        body['block'] = {'phase': 'base', 'weeks': 4,
                         'start_date': '2026-07-06'}
        body.update(extra)
        return body

    def test_rotation_changes_series(self, client):
        first = _post(client, self._big()).get_json()
        assert first['compliance']['passed']
        second = _post(client, self._big(
            previous={'seriesUsed': first['seriesUsed']})).get_json()
        assert second['compliance']['passed']
        # At least one intensity/long-ride series rotates to an alternative.
        assert second['seriesUsed'] != first['seriesUsed']

    def test_rotation_is_deterministic(self, client):
        body = self._big(previous={'seriesUsed': [
            'Threshold Accumulation', 'Endurance with Surges']})
        r1 = _post(client, body).get_json()
        r2 = _post(client, body).get_json()
        r1.pop('engine'); r2.pop('engine')
        assert r1 == r2

    def test_small_pool_exhaustion_reuses_no_crash(self, client):
        """When previous.seriesUsed names EVERY option in a slot's pool, the
        slot reuses (small pools must not raise)."""
        # Feed a huge exhaustive avoid-list of every intensity/long name.
        exhaustive = [
            'VO2max 30/30', 'VO2max 40/20', 'VO2max Extended',
            'VO2max Steady Intervals', 'VO2 Bookend', 'Threshold Accumulation',
            'Threshold Progressive', 'Threshold Steady', 'Threshold Touch',
            'G-Spot', 'Tempo with Accelerations', 'Tempo with Sprints',
            'Cadence Work', 'Mixed Intervals', 'Mixed Climbing',
            'Mixed Climbing Variations', 'SFR', 'Microbursts', 'Stomps',
            'Race Simulation', 'Blended VO2max and G Spot', 'NP/IF Target',
            'Endurance', 'Endurance Blocks', 'Endurance with Surges',
        ]
        resp = _post(client, self._big(previous={'seriesUsed': exhaustive}))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['compliance']['passed']
        assert data['seriesUsed']  # still produced a full block

    def test_rotation_preserves_within_block_coherence(self, client):
        """Rotating in a new series must not break series coherence WITHIN the
        block (compliance R09 still passes)."""
        first = _post(client, self._big()).get_json()
        second = _post(client, self._big(
            previous={'seriesUsed': first['seriesUsed']})).get_json()
        assert second['compliance'] == {'passed': True, 'violations': []}

    def test_empty_series_used_is_byte_identical(self, client):
        """previous with empty seriesUsed == no rotation signal → identical."""
        base = _post(client, self._big()).get_json()
        empty = _post(client, self._big(
            previous={'seriesUsed': []})).get_json()
        base.pop('engine'); empty.pop('engine')
        assert base == empty


def test_null_methodology_uses_default(client):
    """Explicit null methodology means 'default', not a validation error
    (clients that JSON-serialize optional fields send null — Endure adapter)."""
    resp = _post(client, _payload(methodology=None))
    assert resp.status_code == 200, resp.get_json()


# =============================================================================
# METHODOLOGY DIFFERENTIATION (convergence Phase 2, decision B)
# =============================================================================

class TestMethodologyDifferentiation:
    """An EXPLICIT request methodology engages its selection profile
    (athletes/config/methodology_profiles.yaml): category-weight multipliers
    that combine (multiply) with race-demand weights at the _pick_option
    seam. Two methodologies must produce measurably different zone/intensity
    distributions for the same athlete request, every methodology must pass
    the compliance gate, and methodology absent/null must stay byte-identical
    to the historical default selection."""

    ALL_METHODOLOGIES = ['polarized_80_20', 'time_crunched', 'g_spot',
                         'traditional_pyramidal']
    # Name→family sets mirror workout_library categories via the scorer
    # taxonomy: sweet-spot family = category ∈ {G_Spot, Tempo, TT_Threshold};
    # VO2 family = category ∈ {VO2max, Anaerobic_Capacity} (the library's
    # anaerobic stimulus lives inside the VO2-classed names).
    SWEET_SPOT_FAMILY = {
        'G-Spot', 'Threshold Touch', 'Threshold Steady',
        'Threshold Accumulation', 'Threshold Progressive',
        'Tempo', 'Tempo with Accelerations', 'Tempo with Sprints',
    }
    VO2_FAMILY = {
        'VO2max 30/30', 'VO2max 40/20', 'VO2max Extended',
        'VO2max Steady Intervals',
    }

    def _block(self, client, methodology, phase='build', weeks=4, **extra):
        body = _payload(methodology=methodology)
        body['block'] = {'phase': phase, 'weeks': weeks,
                         'start_date': '2026-07-06'}
        body.update(extra)
        resp = _post(client, body)
        assert resp.status_code == 200, (methodology, phase, resp.get_json())
        return resp.get_json()

    def _family_counts(self, data):
        names = [wo['coachName'] for wk in data['weeks']
                 for wo in wk['workouts'] if wo['isIntensity']]
        sweet = sum(1 for n in names if n in self.SWEET_SPOT_FAMILY)
        vo2 = sum(1 for n in names if n in self.VO2_FAMILY)
        return sweet, vo2

    # ---- THE acceptance assertion ------------------------------------------

    def test_gspot_vs_polarized_measurably_different(self, client):
        """Same athlete request under g_spot vs polarized_80_20: g_spot has
        STRICTLY more sweet-spot-family selections, polarized STRICTLY more
        VO2-family, zero compliance violations in both."""
        for phase in ('base', 'build', 'peak'):
            pol = self._block(client, 'polarized_80_20', phase=phase)
            gsp = self._block(client, 'g_spot', phase=phase)
            assert pol['compliance'] == {'passed': True, 'violations': []}
            assert gsp['compliance'] == {'passed': True, 'violations': []}
            pol_sweet, pol_vo2 = self._family_counts(pol)
            gsp_sweet, gsp_vo2 = self._family_counts(gsp)
            assert gsp_sweet > pol_sweet, (
                f"{phase}: g_spot sweet {gsp_sweet} <= polarized {pol_sweet}")
            assert pol_vo2 > gsp_vo2, (
                f"{phase}: polarized vo2 {pol_vo2} <= g_spot {gsp_vo2}")

    def test_pyramidal_delivers_tempo(self, client):
        data = self._block(client, 'traditional_pyramidal')
        names = {wo['coachName'] for wk in data['weeks']
                 for wo in wk['workouts'] if wo['isIntensity']}
        assert any('Tempo' in n for n in names), names

    def test_time_crunched_intensity_stays_short(self, client):
        """Duration-capped picks: even seeded at a high progression level,
        time_crunched never selects the long-form intensity names the cap
        excludes (VO2 Bookend 109-197min, big blended rides 104-216min)."""
        long_forms = {'VO2 Bookend', 'Blended 30/30 and SFR',
                      'Blended Endurance, Threshold, and Sprints',
                      'Buffer Workout'}
        for prev in (None, {'levels': {'a': 3}}, {'levels': {'a': 5}}):
            extra = {'previous': prev} if prev else {}
            data = self._block(client, 'time_crunched', **extra)
            names = {wo['coachName'] for wk in data['weeks']
                     for wo in wk['workouts'] if wo['isIntensity']}
            assert not (names & long_forms), (prev, names)

    # ---- compliance gate holds for every methodology × phase × weeks -------

    def test_every_methodology_phase_weeks_combo_passes_gate(self, client):
        for m in self.ALL_METHODOLOGIES:
            for phase in VALID_PHASES:
                for weeks in (2, 3, 4):
                    data = self._block(client, m, phase=phase, weeks=weeks)
                    assert data['compliance'] == {
                        'passed': True, 'violations': []}, (m, phase, weeks)

    def test_profiles_and_race_demands_combine_compliantly(self, client):
        race = {'name': 'X', 'distance_mi': 131, 'elevation_ft': 11000,
                'discipline': 'gravel'}
        for m in self.ALL_METHODOLOGIES:
            data = self._block(client, m, race=race)
            assert data['compliance'] == {'passed': True, 'violations': []}, m

    # ---- pinning: absent/null methodology is the historical default --------

    def test_absent_and_null_methodology_byte_identical(self, client):
        body_absent = _payload()
        body_null = _payload(methodology=None)
        r1 = _post(client, body_absent).get_json()
        r2 = _post(client, body_null).get_json()
        r1.pop('engine'); r2.pop('engine')
        assert r1 == r2

    def test_absent_methodology_engages_no_profile(self, client):
        """Unit pin: no request methodology → methodology_profile None →
        the selection code path is the pre-profile fast path (byte-identical
        default behavior). Explicit methodology → profile engaged."""
        import engine_adapter
        params, errors = engine_adapter.validate_request(_payload())
        assert not errors
        assert params['methodology'] == 'polarized_80_20'
        assert params['methodology_profile'] is None
        params, errors = engine_adapter.validate_request(
            _payload(methodology=None))
        assert not errors
        assert params['methodology_profile'] is None
        params, errors = engine_adapter.validate_request(
            _payload(methodology='g_spot'))
        assert not errors
        assert params['methodology_profile'] is not None
        assert params['methodology_profile']['category_weights']['G_Spot'] == 3.0

    def test_explicit_methodology_changes_selection_vs_default(self, client):
        """Decision B in one assertion: naming a methodology changes the
        delivered names for the same request (it is not just copy)."""
        base = _post(client, _payload()).get_json()
        gsp = _post(client, _payload(methodology='g_spot')).get_json()
        assert base['seriesUsed'] != gsp['seriesUsed']

    def test_methodology_response_shape_unchanged(self, client):
        """Selection-level only: the contract response shape is identical
        with and without an explicit methodology."""
        base = _post(client, _payload()).get_json()
        gsp = _post(client, _payload(methodology='g_spot')).get_json()
        assert set(base.keys()) == set(gsp.keys())
        for wk_b, wk_g in zip(base['weeks'], gsp['weeks']):
            assert set(wk_b.keys()) == set(wk_g.keys())
            for wo in wk_g['workouts']:
                assert {'day', 'coachName', 'durationMinutes', 'estimatedTss',
                        'fuelTag', 'isIntensity'} <= set(wo.keys())

    def test_unhashable_methodology_is_field_error_not_500(self, client):
        resp = _post(client, _payload(methodology={'name': 'polarized'}))
        assert resp.status_code == 400
        assert 'methodology' in resp.get_json()['fields']

    def test_explicit_methodology_is_deterministic(self, client):
        for m in self.ALL_METHODOLOGIES:
            r1 = _post(client, _payload(methodology=m)).get_json()
            r2 = _post(client, _payload(methodology=m)).get_json()
            r1.pop('engine'); r2.pop('engine')
            assert r1 == r2, m
