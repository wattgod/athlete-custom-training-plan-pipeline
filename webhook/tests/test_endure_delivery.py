#!/usr/bin/env python3
"""
Tests for Endure Labs plan delivery (Phase 4b/4c pipeline side).

Covers the pinned contract mapping (build_profile output → delivery body),
fallback-on-failure (delivery must never fail the order), idempotent
re-post handling (already_delivered), the coach/customer email variants,
the durable streak counter, and the env-off pin (feature unset = zero
behavior change).

Run with: pytest webhook/tests/test_endure_delivery.py -v
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import requests as real_requests

# Add webhook directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set test environment before importing app (mirrors test_webhook.py)
os.environ.setdefault('FLASK_ENV', 'test')
os.environ.setdefault('WOOCOMMERCE_SECRET', '')
os.environ.setdefault('STRIPE_WEBHOOK_SECRET', '')
os.environ.setdefault('STRIPE_SECRET_KEY', '')
os.environ.setdefault('SYNC_PIPELINE', '1')

# app.py bakes ATHLETES_DIR/SCRIPTS_DIR at import; seed a session-lifetime
# mock athletes dir so a combined suite keeps its baseline behavior
# (identical shape to test_engine_block.py's bootstrap).
_SESSION_TMP = tempfile.TemporaryDirectory()  # module ref → survives session
_SESSION_ATHLETES = Path(_SESSION_TMP.name) / 'athletes'
(_SESSION_ATHLETES / 'scripts').mkdir(parents=True)
(_SESSION_ATHLETES / 'scripts' / 'generate_full_package.py').write_text(
    '#!/usr/bin/env python3\nimport sys; sys.exit(0)')
os.environ.setdefault('ATHLETES_DIR', str(_SESSION_ATHLETES))
os.environ.setdefault('SCRIPTS_DIR', str(_SESSION_ATHLETES / 'scripts'))

import endure_delivery


# =============================================================================
# FIXTURES
# =============================================================================

ENDURE_URL = 'https://endure-delivery.test'
ENDURE_SECRET = 'test-delivery-secret'


@pytest.fixture
def endure_env(monkeypatch):
    """Enable the Endure delivery feature."""
    monkeypatch.setenv('ENDURE_DELIVERY_URL', ENDURE_URL)
    monkeypatch.setenv('ENDURE_DELIVERY_SECRET', ENDURE_SECRET)
    monkeypatch.delenv('DELIVERY_TARGET_DEFAULT', raising=False)


@pytest.fixture
def endure_env_off(monkeypatch):
    """Explicitly disable the feature (both env vars unset)."""
    monkeypatch.delenv('ENDURE_DELIVERY_URL', raising=False)
    monkeypatch.delenv('ENDURE_DELIVERY_SECRET', raising=False)
    monkeypatch.delenv('DELIVERY_TARGET_DEFAULT', raising=False)


def make_profile(**overrides):
    """A build_profile()-shaped profile.yaml dict (field names verbatim
    from athletes/scripts/intake_to_plan.py::build_profile)."""
    profile = {
        'name': 'Jane Doe',
        'email': 'jane@example.com',
        'athlete_id': 'jane-doe',
        'sex': 'female',
        'discipline_default': '',
        'target_race': {
            'name': 'Unbound Gravel 200',
            'race_id': 'unbound_gravel_200',
            'date': '2026-05-30',
            'distance_miles': 200,
            'elevation_ft': 11000,
            'goal_type': 'finish',
            'discipline': 'gravel',
        },
        'a_events': [{
            'name': 'Unbound Gravel 200',
            'date': '2026-05-30',
            'distance_miles': 200,
            'goal': 'finish',
            'priority': 'A',
        }],
        'b_events': [{
            'name': 'Local Spring Gravel',
            'date': '2026-04-12',
            'distance_miles': 60,
            'goal': 'compete',
            'priority': 'B',
        }],
        'racing': {
            'obstacles': 'Fading in the final hour of long races',
        },
        'training_history': {
            'years_cycling': 6,
            'years_structured': 2,
        },
        'fitness_markers': {
            'ftp_watts': 210,
            'ftp_estimated': False,
            'weight_kg': 62.0,
            'max_hr': 186,
            'lthr': 168,
        },
        'weekly_availability': {
            'total_hours_available': 10,
            'cycling_hours_target': 8,
            'volume_warning': None,
        },
        'schedule_constraints': {
            'preferred_off_days': ['monday'],
            'preferred_long_day': 'saturday',
        },
        'injury_history': {
            'current_injuries': [],
            'past_injuries': [],
        },
        'health_factors': {
            'age': 34,
            'medical_conditions': '',
        },
        'travel_dates': [],
        'plan_start': {
            'preferred_start': '2026-07-13',
        },
    }
    profile.update(overrides)
    return profile


def _resp(status_code=200, body=None):
    """Mock requests.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    if body is None:
        resp.json.side_effect = ValueError('no body')
    else:
        resp.json.return_value = body
    return resp


DELIVERED_BODY = {
    'order_id': 'cs_test_1',
    'athlete_id': 'ath_endure_1',
    'plan_id': 'plan_endure_1',
    'block_id': 'block_endure_1',
    'invitation_id': 'inv_endure_1',
    'status': 'delivered',
}


# =============================================================================
# TARGET RESOLUTION + ENV-OFF PIN
# =============================================================================

class TestResolveDeliveryTarget:

    def test_env_off_is_always_trainingpeaks(self, endure_env_off):
        """PIN: feature unset → trainingpeaks, even with per-order override."""
        assert endure_delivery.is_enabled() is False
        assert endure_delivery.resolve_delivery_target({}) == 'trainingpeaks'
        assert endure_delivery.resolve_delivery_target(
            {'delivery_target': 'endure'}) == 'trainingpeaks'

    def test_env_off_when_only_url_set(self, endure_env_off, monkeypatch):
        monkeypatch.setenv('ENDURE_DELIVERY_URL', ENDURE_URL)
        assert endure_delivery.is_enabled() is False
        assert endure_delivery.resolve_delivery_target(
            {'delivery_target': 'endure'}) == 'trainingpeaks'

    def test_enabled_default_is_trainingpeaks(self, endure_env):
        """TP stays DEFAULT (Decision 2) even with the feature on."""
        assert endure_delivery.resolve_delivery_target({}) == 'trainingpeaks'
        assert endure_delivery.resolve_delivery_target(None) == 'trainingpeaks'

    def test_per_order_override_opts_in(self, endure_env):
        assert endure_delivery.resolve_delivery_target(
            {'delivery_target': 'endure'}) == 'endure'
        assert endure_delivery.resolve_delivery_target(
            {'delivery_target': 'ENDURE '}) == 'endure'

    def test_env_default_endure(self, endure_env, monkeypatch):
        monkeypatch.setenv('DELIVERY_TARGET_DEFAULT', 'endure')
        assert endure_delivery.resolve_delivery_target({}) == 'endure'

    def test_override_beats_env_default(self, endure_env, monkeypatch):
        """Operator can force TP on one order even after the default flips."""
        monkeypatch.setenv('DELIVERY_TARGET_DEFAULT', 'endure')
        assert endure_delivery.resolve_delivery_target(
            {'delivery_target': 'trainingpeaks'}) == 'trainingpeaks'

    def test_garbage_override_ignored(self, endure_env):
        assert endure_delivery.resolve_delivery_target(
            {'delivery_target': 'carrier-pigeon'}) == 'trainingpeaks'

    def test_garbage_env_default_ignored(self, endure_env, monkeypatch):
        monkeypatch.setenv('DELIVERY_TARGET_DEFAULT', 'yes')
        assert endure_delivery.resolve_delivery_target({}) == 'trainingpeaks'


class TestEnvOffZeroBehaviorChange:
    """PIN: with the env unset, order processing is byte-identical."""

    def test_extract_stripe_data_defaults_to_trainingpeaks(self, endure_env_off):
        from app import extract_stripe_data
        data = {'data': {'object': {
            'id': 'cs_test_off',
            'metadata': {'delivery_target': 'endure'},  # ignored while off
            'customer_details': {'name': 'Jane Doe', 'email': 'j@x.com'},
        }}}
        order = extract_stripe_data(data)
        assert order['delivery_target'] == 'trainingpeaks'

    def test_no_delivery_call_when_off(self, endure_env_off):
        with patch.object(endure_delivery.requests, 'post') as mock_post:
            record = endure_delivery.deliver_purchased_plan({'order_id': 'x'})
        mock_post.assert_not_called()
        assert record['status'] == 'failed'
        assert 'not configured' in record['error']

    def test_health_has_no_endure_key_when_off(self, endure_env_off):
        from app import app as flask_app
        flask_app.config['TESTING'] = True
        with flask_app.test_client() as client:
            data = client.get('/health').get_json()
        assert 'endure_delivery' not in data

    def test_health_reports_streak_when_on(self, endure_env, monkeypatch,
                                           tmp_path):
        import app as app_module
        monkeypatch.setattr(app_module, 'DATA_DIR', str(tmp_path))
        endure_delivery.record_delivery_result(True, 'cs_1', str(tmp_path))
        app_module.app.config['TESTING'] = True
        with app_module.app.test_client() as client:
            data = client.get('/health').get_json()
        assert data['endure_delivery']['enabled'] is True
        assert data['endure_delivery']['default_target'] == 'trainingpeaks'
        assert data['endure_delivery']['consecutive_successes'] == 1


# =============================================================================
# PROFILE → CONTRACT MAPPING
# =============================================================================

class TestBuildDeliveryPayload:

    def test_contract_top_level_shape(self):
        payload = endure_delivery.build_delivery_payload(
            make_profile(), 'cs_test_1', intake={'q': 'a'})
        assert set(payload.keys()) == {'order_id', 'athlete', 'races',
                                       'plan', 'intake'}
        assert payload['order_id'] == 'cs_test_1'
        assert payload['intake'] == {'q': 'a'}

    def test_athlete_mapping_and_units(self):
        athlete = endure_delivery.build_delivery_payload(
            make_profile(), 'cs_1')['athlete']
        assert athlete['email'] == 'jane@example.com'
        assert athlete['name'] == 'Jane Doe'
        assert athlete['ftp'] == 210                # fitness_markers.ftp_watts
        assert athlete['weight_kg'] == 62.0         # already kg in profile.yaml
        assert athlete['age'] == 34                 # health_factors.age
        assert athlete['hours_per_week'] == 8       # cycling_hours_target
        assert athlete['experience_years'] == 6     # training_history.years_cycling
        assert athlete['off_days'] == ['monday']    # preferred_off_days
        assert athlete['long_ride_day'] == 'saturday'
        assert athlete['limiters'] == 'Fading in the final hour of long races'
        # empty constraints omitted, not sent as ''/null
        assert 'constraints' not in athlete

    def test_races_a_plus_b_events(self):
        races = endure_delivery.build_delivery_payload(
            make_profile(), 'cs_1')['races']
        assert len(races) == 2
        a, b = races[0], races[1]
        assert a == {'name': 'Unbound Gravel 200', 'date': '2026-05-30',
                     'priority': 'A', 'distance_mi': 200.0,
                     'elevation_ft': 11000, 'discipline': 'gravel'}
        # B event has no elevation/discipline source — keys omitted
        assert b == {'name': 'Local Spring Gravel', 'date': '2026-04-12',
                     'priority': 'B', 'distance_mi': 60.0}

    def test_plan_name_and_start_date(self):
        plan = endure_delivery.build_delivery_payload(
            make_profile(), 'cs_1')['plan']
        assert plan['start_date'] == '2026-07-13'   # plan_start.preferred_start
        assert 'Unbound Gravel 200' in plan['name']

    def test_optional_fields_omitted_when_absent(self):
        profile = make_profile()
        profile['fitness_markers'] = {'ftp_watts': None, 'weight_kg': 0}
        profile['health_factors'] = {'age': 0}
        profile['training_history'] = {}
        profile['schedule_constraints'] = {}
        profile['racing'] = {}
        athlete = endure_delivery.build_delivery_payload(
            profile, 'cs_1')['athlete']
        for key in ('ftp', 'weight_kg', 'age', 'experience_years',
                    'off_days', 'long_ride_day', 'limiters', 'constraints'):
            assert key not in athlete, f'{key} should be omitted'
        # required fields still present
        assert athlete['email'] and athlete['hours_per_week']

    def test_constraints_from_injuries_and_warnings(self):
        profile = make_profile()
        profile['injury_history']['current_injuries'] = [{
            'area': 'general', 'description': 'IT band pain', 'status': 'active'}]
        profile['health_factors']['medical_conditions'] = 'asthma'
        profile['weekly_availability']['volume_warning'] = (
            'Target volume (12h/wk) exceeds schedule capacity (9h/wk).')
        athlete = endure_delivery.build_delivery_payload(
            profile, 'cs_1')['athlete']
        assert 'IT band pain' in athlete['constraints']
        assert 'asthma' in athlete['constraints']
        assert 'exceeds schedule capacity' in athlete['constraints']

    def test_missing_email_raises_mapping_error(self):
        profile = make_profile(email='')
        with pytest.raises(endure_delivery.EndureMappingError):
            endure_delivery.build_delivery_payload(profile, 'cs_1')

    def test_missing_hours_raises_mapping_error(self):
        profile = make_profile()
        profile['weekly_availability'] = {'cycling_hours_target': 0}
        with pytest.raises(endure_delivery.EndureMappingError):
            endure_delivery.build_delivery_payload(profile, 'cs_1')

    def test_empty_profile_raises_mapping_error(self):
        with pytest.raises(endure_delivery.EndureMappingError):
            endure_delivery.build_delivery_payload({}, 'cs_1')

    def test_generic_race_uses_derived_discipline(self):
        """Unmatched races carry generic_discipline instead of DB discipline."""
        profile = make_profile()
        profile['target_race'] = {
            'name': 'Backyard Gravel Bash', 'date': '2026-09-01',
            'distance_miles': 80, 'elevation_ft': 0,
            'generic_profile': True, 'generic_discipline': 'gravel',
        }
        profile['a_events'] = [{'name': 'Backyard Gravel Bash',
                                'date': '2026-09-01', 'distance_miles': 80,
                                'goal': 'finish', 'priority': 'A'}]
        profile['b_events'] = []
        races = endure_delivery.build_delivery_payload(profile, 'cs_1')['races']
        assert races[0]['discipline'] == 'gravel'
        assert 'elevation_ft' not in races[0]  # 0 → omitted


# =============================================================================
# DELIVERY CALL — timeout, ONE retry, idempotent re-post
# =============================================================================

class TestDeliverPurchasedPlan:

    def test_success_first_attempt(self, endure_env):
        with patch.object(endure_delivery.requests, 'post',
                          return_value=_resp(200, DELIVERED_BODY)) as mock_post:
            record = endure_delivery.deliver_purchased_plan({'order_id': 'cs_1'})
        assert record['ok'] is True
        assert record['status'] == 'delivered'
        assert record['attempts'] == 1
        assert record['plan_id'] == 'plan_endure_1'
        assert record['block_id'] == 'block_endure_1'
        assert record['invitation_id'] == 'inv_endure_1'
        assert record['athlete_id'] == 'ath_endure_1'
        assert record['review_url'] == (
            'https://endurelabs.app/coach/athletes/ath_endure_1/plan')
        # secret header + pinned path
        _, kwargs = mock_post.call_args
        assert mock_post.call_args[0][0] == (
            ENDURE_URL + '/api/delivery/purchased-plan')
        assert kwargs['headers']['X-Delivery-Secret'] == ENDURE_SECRET
        assert kwargs['timeout'] == 20.0

    def test_already_delivered_is_success(self, endure_env):
        """Idempotent re-post: Endure returns already_delivered → success."""
        body = dict(DELIVERED_BODY, status='already_delivered')
        with patch.object(endure_delivery.requests, 'post',
                          return_value=_resp(200, body)):
            record = endure_delivery.deliver_purchased_plan({'order_id': 'cs_1'})
        assert record['ok'] is True
        assert record['status'] == 'already_delivered'
        assert record['plan_id'] == 'plan_endure_1'

    def test_retries_once_on_5xx(self, endure_env):
        with patch.object(endure_delivery.requests, 'post',
                          side_effect=[_resp(500),
                                       _resp(200, DELIVERED_BODY)]) as mock_post:
            record = endure_delivery.deliver_purchased_plan({'order_id': 'cs_1'})
        assert record['ok'] is True
        assert record['attempts'] == 2
        assert mock_post.call_count == 2

    def test_retries_once_on_timeout(self, endure_env):
        with patch.object(endure_delivery.requests, 'post',
                          side_effect=[real_requests.Timeout('slow'),
                                       _resp(200, DELIVERED_BODY)]) as mock_post:
            record = endure_delivery.deliver_purchased_plan({'order_id': 'cs_1'})
        assert record['ok'] is True
        assert record['attempts'] == 2
        assert mock_post.call_count == 2

    def test_fails_after_two_attempts(self, endure_env):
        with patch.object(endure_delivery.requests, 'post',
                          side_effect=[_resp(500), _resp(502)]) as mock_post:
            record = endure_delivery.deliver_purchased_plan({'order_id': 'cs_1'})
        assert record['ok'] is False
        assert record['status'] == 'failed'
        assert record['attempts'] == 2
        assert mock_post.call_count == 2  # exactly ONE retry, not more

    def test_401_is_not_retried(self, endure_env):
        with patch.object(endure_delivery.requests, 'post',
                          return_value=_resp(401)) as mock_post:
            record = endure_delivery.deliver_purchased_plan({'order_id': 'cs_1'})
        assert record['ok'] is False
        assert record['attempts'] == 1
        assert mock_post.call_count == 1
        assert 'HTTP 401' in record['error']

    def test_400_carries_error_detail_no_retry(self, endure_env):
        body = {'error': 'invalid payload', 'details': {'athlete': 'bad'}}
        with patch.object(endure_delivery.requests, 'post',
                          return_value=_resp(400, body)) as mock_post:
            record = endure_delivery.deliver_purchased_plan({'order_id': 'cs_1'})
        assert record['ok'] is False
        assert mock_post.call_count == 1
        assert 'HTTP 400' in record['error']
        assert 'invalid payload' in record['error']

    def test_never_raises_on_connection_error(self, endure_env):
        with patch.object(endure_delivery.requests, 'post',
                          side_effect=real_requests.ConnectionError('down')):
            record = endure_delivery.deliver_purchased_plan({'order_id': 'cs_1'})
        assert record['ok'] is False
        assert record['status'] == 'failed'


# =============================================================================
# STREAK COUNTER (Decision 2)
# =============================================================================

class TestStreakCounter:

    def test_consecutive_successes_increment(self, tmp_path):
        d = str(tmp_path)
        endure_delivery.record_delivery_result(True, 'cs_1', d)
        endure_delivery.record_delivery_result(True, 'cs_2', d)
        streak = endure_delivery.record_delivery_result(True, 'cs_3', d)
        assert streak['consecutive_successes'] == 3
        assert streak['total_successes'] == 3
        assert streak['total_failures'] == 0

    def test_failure_resets_consecutive(self, tmp_path):
        d = str(tmp_path)
        endure_delivery.record_delivery_result(True, 'cs_1', d)
        endure_delivery.record_delivery_result(True, 'cs_2', d)
        streak = endure_delivery.record_delivery_result(False, 'cs_3', d)
        assert streak['consecutive_successes'] == 0
        assert streak['total_successes'] == 2
        assert streak['total_failures'] == 1
        assert streak['last_status'] == 'failure'

    def test_idempotent_repost_not_double_counted(self, tmp_path):
        """A retried order (already_delivered) must not inflate the streak."""
        d = str(tmp_path)
        endure_delivery.record_delivery_result(True, 'cs_1', d)
        streak = endure_delivery.record_delivery_result(True, 'cs_1', d)
        assert streak['consecutive_successes'] == 1
        assert streak['total_successes'] == 1

    def test_success_after_failure_of_same_order_counts(self, tmp_path):
        """Failure then successful retry of the SAME order → streak 1."""
        d = str(tmp_path)
        endure_delivery.record_delivery_result(False, 'cs_1', d)
        streak = endure_delivery.record_delivery_result(True, 'cs_1', d)
        assert streak['consecutive_successes'] == 1

    def test_streak_is_durable_json(self, tmp_path):
        d = str(tmp_path)
        endure_delivery.record_delivery_result(True, 'cs_1', d)
        path = tmp_path / endure_delivery.STREAK_FILENAME
        assert path.exists()
        on_disk = json.loads(path.read_text())
        assert on_disk['consecutive_successes'] == 1
        # fresh read (no in-memory state)
        assert endure_delivery.read_streak(d)['consecutive_successes'] == 1

    def test_unreadable_file_returns_default(self, tmp_path):
        (tmp_path / endure_delivery.STREAK_FILENAME).write_text('{corrupt')
        streak = endure_delivery.read_streak(str(tmp_path))
        assert streak['consecutive_successes'] == 0


# =============================================================================
# ORDER FLOW — delivery must never fail the order
# =============================================================================

@pytest.fixture
def isolated_app(monkeypatch, tmp_path):
    """app module with DATA_DIR/JOBS_DIR/DELIVERIES_DIR pointed at tmp."""
    import app as app_module
    monkeypatch.setattr(app_module, 'DATA_DIR', str(tmp_path))
    monkeypatch.setattr(app_module, 'JOBS_DIR', str(tmp_path / 'jobs'))
    monkeypatch.setattr(app_module, 'DELIVERIES_DIR', str(tmp_path / 'deliveries'))
    return app_module


def _make_job(app_module, athlete_id='jane_doe', target='endure'):
    order_data = {
        'athlete_id': athlete_id,
        'order_id': 'cs_test_flow',
        'tier': 'custom',
        'delivery_target': target,
        'profile': {'name': 'Jane Doe', 'email': 'jane@example.com',
                    'fitness_markers': {}, 'target_race': {},
                    'weekly_schedule': {}},
    }
    return {
        'athlete_id': athlete_id,
        'order_id': 'cs_test_flow',
        'intake_id': '',
        'delivery_target': target,
        'status': 'queued',
        'attempts': 1,
        'order_data': order_data,
    }


class TestExecuteJobEndureFlow:

    def test_endure_success_recorded_on_job(self, isolated_app, endure_env):
        app_module = isolated_app
        job = _make_job(app_module)
        notifications = []
        with patch.object(app_module, 'run_pipeline',
                          return_value={'success': True, 'stdout': '', 'stderr': ''}), \
             patch.object(app_module, 'persist_deliverables', return_value={}), \
             patch.object(app_module, '_load_profile_yaml',
                          return_value=make_profile()), \
             patch.object(endure_delivery.requests, 'post',
                          return_value=_resp(200, DELIVERED_BODY)), \
             patch.object(app_module, '_notify_new_order',
                          side_effect=lambda t, d: notifications.append((t, d))):
            result = app_module._execute_plan_job(job)

        assert result['success'] is True
        record = app_module._read_job('jane_doe')
        assert record['status'] == 'succeeded'
        assert record['endure_delivery']['status'] == 'delivered'
        assert record['endure_delivery']['plan_id'] == 'plan_endure_1'
        assert record['endure_delivery']['streak'] == 1
        # Coach email got the endure details
        assert notifications[0][0] == 'training_plan'
        assert notifications[0][1]['delivery_target'] == 'endure'
        assert notifications[0][1]['endure_delivery']['status'] == 'delivered'

    def test_endure_failure_never_kills_the_order(self, isolated_app,
                                                  endure_env):
        """Order-killer-prevention: delivery down → order still succeeds,
        endure status failed, coach email still sent (TP fallback)."""
        app_module = isolated_app
        job = _make_job(app_module)
        notifications = []
        with patch.object(app_module, 'run_pipeline',
                          return_value={'success': True, 'stdout': '', 'stderr': ''}), \
             patch.object(app_module, 'persist_deliverables', return_value={}), \
             patch.object(app_module, '_load_profile_yaml',
                          return_value=make_profile()), \
             patch.object(endure_delivery.requests, 'post',
                          side_effect=real_requests.ConnectionError('down')), \
             patch.object(app_module, '_notify_new_order',
                          side_effect=lambda t, d: notifications.append((t, d))):
            result = app_module._execute_plan_job(job)

        assert result['success'] is True                     # order NOT killed
        record = app_module._read_job('jane_doe')
        assert record['status'] == 'succeeded'               # job succeeded
        assert record['endure_delivery']['status'] == 'failed'
        assert notifications[0][0] == 'training_plan'        # not _FAILED
        # streak reset recorded
        streak = endure_delivery.read_streak(app_module.DATA_DIR)
        assert streak['consecutive_successes'] == 0
        assert streak['total_failures'] == 1

    def test_mapping_error_falls_back(self, isolated_app, endure_env):
        """profile.yaml missing → failed delivery record, order fine."""
        app_module = isolated_app
        job = _make_job(app_module)
        with patch.object(app_module, 'run_pipeline',
                          return_value={'success': True, 'stdout': '', 'stderr': ''}), \
             patch.object(app_module, 'persist_deliverables', return_value={}), \
             patch.object(app_module, '_load_profile_yaml', return_value={}), \
             patch.object(endure_delivery.requests, 'post') as mock_post, \
             patch.object(app_module, '_notify_new_order'):
            result = app_module._execute_plan_job(job)
        assert result['success'] is True
        mock_post.assert_not_called()
        record = app_module._read_job('jane_doe')
        assert record['endure_delivery']['status'] == 'failed'
        assert 'profile.yaml' in record['endure_delivery']['error']

    def test_tp_order_makes_no_endure_call(self, isolated_app, endure_env):
        """PIN: target=trainingpeaks → no HTTP call, no endure fields."""
        app_module = isolated_app
        job = _make_job(app_module, target='trainingpeaks')
        notifications = []
        with patch.object(app_module, 'run_pipeline',
                          return_value={'success': True, 'stdout': '', 'stderr': ''}), \
             patch.object(app_module, 'persist_deliverables', return_value={}), \
             patch.object(endure_delivery.requests, 'post') as mock_post, \
             patch.object(app_module, '_notify_new_order',
                          side_effect=lambda t, d: notifications.append((t, d))):
            app_module._execute_plan_job(job)
        mock_post.assert_not_called()
        assert notifications[0][1]['delivery_target'] == 'trainingpeaks'
        assert 'endure_delivery' not in notifications[0][1]
        assert 'endure_delivery' not in app_module._read_job('jane_doe')


# =============================================================================
# COACH EMAIL VARIANT
# =============================================================================

def _email_details(**overrides):
    details = {
        'name': 'Jane Doe',
        'email': 'jane@example.com',
        'tier': 'custom',
        'order_id': 'cs_test_1',
        'athlete_id': 'jane_doe',
        'race_name': 'Unbound Gravel 200',
        'race_date': '2026-05-30',
        'ftp': 210,
        'weight_kg': 62.0,
        'hours_per_week': 8,
        'plan_weeks': '16',
        'workout_count': '112',
        'methodology': 'Polarized (80/20)',
        'error': '',
        'needs_review': False,
        'pipeline_success': True,
        'download_token': 'tok123',
    }
    details.update(overrides)
    return details


class TestCoachEmailVariant:

    def test_tp_checklist_unchanged(self):
        from app import _build_training_plan_email
        subject, text, html = _build_training_plan_email(_email_details())
        assert 'Create athlete in TrainingPeaks' in html
        assert 'Import ZWO files' in html
        assert 'live on TrainingPeaks' in html
        assert 'Endure' not in html
        assert 'Create Jane Doe in TrainingPeaks' in text
        assert 'Import ZWO files into their TP calendar' in text
        assert 'Endure' not in text

    def test_endure_checklist_replaces_tp_import_steps(self):
        from app import _build_training_plan_email
        details = _email_details(
            delivery_target='endure',
            endure_delivery={
                'status': 'delivered', 'athlete_id': 'ath_endure_1',
                'plan_id': 'plan_endure_1', 'block_id': 'block_endure_1',
                'invitation_id': 'inv_endure_1',
                'review_url': 'https://endurelabs.app/coach/athletes/ath_endure_1/plan',
            })
        subject, text, html = _build_training_plan_email(details)
        # Endure review link + approve step present
        assert 'https://endurelabs.app/coach/athletes/ath_endure_1/plan' in html
        assert 'Approve the block in Endure' in html
        assert 'live on Endure' in html
        # TP import steps GONE
        assert 'Create athlete in TrainingPeaks' not in html
        assert 'Import ZWO files' not in html
        # Endure ids visible to the coach (invitation carried here — the
        # customer-facing invite email is sent by Endure itself)
        assert 'inv_endure_1' in html
        # download link (fallback artifact) stays
        assert '/api/download/jane_doe?type=full' in html
        # text variant too
        assert 'Review block 1 in Endure' in text
        assert 'Import ZWO files' not in text

    def test_endure_failure_flags_loudly_keeps_tp_checklist(self):
        from app import _build_training_plan_email
        details = _email_details(
            delivery_target='endure',
            endure_delivery={'status': 'failed', 'error': 'HTTP 503'})
        subject, text, html = _build_training_plan_email(details)
        assert 'ENDURE DELIVERY FAILED' in html
        assert 'HTTP 503' in html
        # fallback: full TP checklist intact
        assert 'Create athlete in TrainingPeaks' in html
        assert 'Import ZWO files' in html
        # failure makes the subject a review subject
        assert 'REVIEW' in subject

    def test_already_delivered_treated_as_delivered(self):
        from app import _build_training_plan_email
        details = _email_details(
            delivery_target='endure',
            endure_delivery={'status': 'already_delivered',
                             'athlete_id': 'ath_endure_1',
                             'review_url': 'https://endurelabs.app/coach/athletes/ath_endure_1/plan'})
        _, text, html = _build_training_plan_email(details)
        assert 'Approve the block in Endure' in html
        assert 'Import ZWO files' not in html


# =============================================================================
# /api/confirm CUSTOMER EMAIL VARIANT
# =============================================================================

class TestConfirmEndureVariant:

    CRON = 'test-cron-secret'

    @pytest.fixture
    def confirm_env(self, isolated_app, monkeypatch):
        monkeypatch.setenv('CRON_SECRET', self.CRON)
        app_module = isolated_app
        # order log so confirm can find the customer
        log_dir = Path(app_module.DATA_DIR) / '.logs'
        log_dir.mkdir(parents=True, exist_ok=True)
        (log_dir / '2026-07.jsonl').write_text(json.dumps({
            'athlete_id': 'jane_doe', 'success': True,
            'email': 'jane@example.com', 'name': 'Jane Doe',
        }) + '\n')
        app_module.app.config['TESTING'] = True
        return app_module

    def _confirm(self, app_module, sent):
        with patch.object(app_module, '_send_email',
                          side_effect=lambda *a, **k: sent.append((a, k)) or True):
            with app_module.app.test_client() as client:
                return client.post('/api/confirm/jane_doe',
                                   headers={'X-Cron-Secret': self.CRON})

    def test_endure_order_gets_endure_email(self, confirm_env):
        app_module = confirm_env
        app_module._update_job(
            'jane_doe', delivery_target='endure', status='succeeded',
            endure_delivery={'status': 'delivered',
                             'invitation_id': 'inv_endure_1'})
        sent = []
        resp = self._confirm(app_module, sent)
        assert resp.status_code == 200
        assert resp.get_json()['delivery_target'] == 'endure'
        (args, kwargs) = sent[0]
        subject, body = args[1], args[2]
        assert 'live on Endure' in subject
        assert 'Accept your Endure invitation' in body
        assert 'TrainingPeaks' not in body
        assert 'David' in body

    def test_tp_order_email_unchanged(self, confirm_env):
        app_module = confirm_env
        app_module._update_job('jane_doe', delivery_target='trainingpeaks',
                               status='succeeded')
        sent = []
        resp = self._confirm(app_module, sent)
        assert resp.status_code == 200
        assert 'delivery_target' not in (resp.get_json() or {})
        (args, kwargs) = sent[0]
        subject, body = args[1], args[2]
        assert 'live on TrainingPeaks' in subject
        assert 'Endure' not in body

    def test_endure_target_but_failed_delivery_gets_tp_email(self, confirm_env):
        """Fallback orders were delivered via TP — email must say TP."""
        app_module = confirm_env
        app_module._update_job(
            'jane_doe', delivery_target='endure', status='succeeded',
            endure_delivery={'status': 'failed', 'error': 'HTTP 503'})
        sent = []
        resp = self._confirm(app_module, sent)
        assert resp.status_code == 200
        (args, kwargs) = sent[0]
        assert 'live on TrainingPeaks' in args[1]


# =============================================================================
# JOB RECORD FLAG
# =============================================================================

class TestJobRecordFlag:

    def test_spawn_records_delivery_target(self, isolated_app, monkeypatch):
        app_module = isolated_app
        monkeypatch.setenv('SYNC_PIPELINE', '')  # background path; patch thread
        order_data = {'athlete_id': 'flag_test', 'order_id': 'cs_flag',
                      'delivery_target': 'endure', 'profile': {}}
        with patch.object(app_module, '_start_job_thread'):
            job, _ = app_module._spawn_plan_job(order_data)
        assert job['delivery_target'] == 'endure'
        assert app_module._read_job('flag_test')['delivery_target'] == 'endure'

    def test_spawn_defaults_to_trainingpeaks(self, isolated_app, monkeypatch):
        app_module = isolated_app
        monkeypatch.setenv('SYNC_PIPELINE', '')
        order_data = {'athlete_id': 'flag_test2', 'order_id': 'cs_flag2',
                      'profile': {}}
        with patch.object(app_module, '_start_job_thread'):
            job, _ = app_module._spawn_plan_job(order_data)
        assert job['delivery_target'] == 'trainingpeaks'
