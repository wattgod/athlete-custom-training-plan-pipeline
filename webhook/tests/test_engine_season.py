#!/usr/bin/env python3
"""
Tests for POST /engine/season — deterministic season/periodization planning
for Endure Labs (Convergence Phase 2). Contract is FROZEN; these tests pin
the exact enums and shapes Endure Zod-validates against.

The season brain is calculate_plan_dates (the pipeline's SINGLE SOURCE OF
TRUTH for week typing) — these tests verify the endpoint wraps it faithfully:
phase ordering, the B-race mini-taper overlay, and the block-partition
invariant (every week in exactly one 2-4-week block feedable to /engine/block).

Run with: pytest webhook/tests/test_engine_season.py -v
"""

import os
import sys
import tempfile
from collections import Counter
from pathlib import Path

import pytest

# Add webhook directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set test environment before importing app (mirrors test_engine_block.py)
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

ENGINE_SECRET = 'test-engine-secret'

VALID_PHASES = {'base', 'build', 'peak', 'taper', 'race', 'recovery',
                'transition'}
VALID_WEEK_TYPES = {'load', 'recovery', 'taper', 'race', 'testing'}
VALID_PRIORITIES = {'A', 'B', 'C'}
# /engine/block accepts these week counts — season blocks must land here.
BLOCK_WEEKS = {2, 3, 4}
# Phase ordering rank for sanity checks (base earliest → race latest).
PHASE_RANK = {'base': 0, 'build': 1, 'peak': 2, 'taper': 3, 'race': 4,
              'recovery': 0, 'transition': 0}

# Fixed anchor dates chosen so start→anchor spans exactly N Mon-Sun weeks.
# start_date 2026-08-03 is a Monday.
START = '2026-08-03'
ANCHOR_12W = '2026-10-25'   # 12 calendar weeks inclusive
ANCHOR_16W = '2026-11-22'   # 16 calendar weeks inclusive
ANCHOR_24W = '2027-01-17'   # 24 calendar weeks inclusive


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv('ENGINE_SHARED_SECRET', ENGINE_SECRET)
    from app import app as flask_app, limiter
    flask_app.config['TESTING'] = True
    monkeypatch.setattr(limiter, 'enabled', False)
    with flask_app.test_client() as c:
        yield c


def _payload(**overrides):
    """Baseline valid 12-week single-A-race season; keyword overrides replace
    top-level keys."""
    body = {
        'athlete': {
            'hours_per_week': 8,
            'experience_years': 3,
            'age': 38,
            'discipline': 'gravel',
        },
        'races': [
            {'name': 'Goal Gravel 200', 'date': ANCHOR_12W, 'priority': 'A',
             'discipline': 'gravel', 'distance_mi': 200, 'elevation_ft': 11000},
        ],
        'start_date': START,
    }
    body.update(overrides)
    return body


def _post(client, body, secret=ENGINE_SECRET):
    headers = {}
    if secret is not None:
        headers['X-Engine-Secret'] = secret
    return client.post('/engine/season', json=body, headers=headers)


def _ok(client, body):
    resp = _post(client, body)
    assert resp.status_code == 200, resp.get_json()
    return resp.get_json()


# =============================================================================
# AUTH
# =============================================================================

class TestAuth:
    def test_missing_env_secret_returns_503(self, client, monkeypatch):
        monkeypatch.delenv('ENGINE_SHARED_SECRET', raising=False)
        assert _post(client, _payload()).status_code == 503

    def test_wrong_secret_returns_401(self, client):
        assert _post(client, _payload(), secret='wrong').status_code == 401

    def test_missing_header_returns_401(self, client):
        assert client.post('/engine/season',
                           json=_payload()).status_code == 401


# =============================================================================
# HAPPY PATH — contract shape pin
# =============================================================================

class TestContractShape:
    def test_top_level_keys(self, client):
        data = _ok(client, _payload())
        assert set(data.keys()) == {'weeks', 'phases', 'blocks', 'engine'}
        assert isinstance(data['engine']['version'], str)
        assert isinstance(data['engine']['generated_ms'], int)
        assert data['engine']['generated_ms'] < 500

    def test_week_shape(self, client):
        data = _ok(client, _payload())
        for i, week in enumerate(data['weeks']):
            assert week['number'] == i + 1
            assert set(week.keys()) >= {
                'number', 'start_date', 'end_date', 'phase', 'type',
                'block', 'races'}
            assert set(week.keys()) <= {
                'number', 'start_date', 'end_date', 'phase', 'type',
                'block', 'races', 'note'}
            assert week['phase'] in VALID_PHASES
            assert week['type'] in VALID_WEEK_TYPES
            blk = week['block']
            assert set(blk.keys()) == {'index', 'position', 'length'}
            assert isinstance(blk['index'], int)
            assert 1 <= blk['position'] <= blk['length']
            assert 2 <= blk['length'] <= 4
            assert isinstance(week['races'], list)
            for r in week['races']:
                assert set(r.keys()) == {'name', 'priority', 'date'}
                assert r['priority'] in VALID_PRIORITIES
            if 'note' in week:
                assert isinstance(week['note'], str) and week['note']

    def test_weeks_are_consecutive_monday_sunday(self, client):
        from datetime import datetime, timedelta
        weeks = _ok(client, _payload())['weeks']
        for w in weeks:
            mon = datetime.strptime(w['start_date'], '%Y-%m-%d')
            sun = datetime.strptime(w['end_date'], '%Y-%m-%d')
            assert mon.weekday() == 0  # Monday
            assert (sun - mon).days == 6
        for a, b in zip(weeks, weeks[1:]):
            prev_sun = datetime.strptime(a['end_date'], '%Y-%m-%d')
            nxt_mon = datetime.strptime(b['start_date'], '%Y-%m-%d')
            assert (nxt_mon - prev_sun).days == 1

    def test_phase_shape(self, client):
        data = _ok(client, _payload())
        total = sum(p['weeks'] for p in data['phases'])
        assert total == len(data['weeks'])
        for p in data['phases']:
            assert set(p.keys()) == {'phase', 'start_date', 'end_date',
                                     'weeks'}
            assert p['phase'] in VALID_PHASES
            assert p['weeks'] >= 1

    def test_block_shape_feeds_engine_block(self, client):
        data = _ok(client, _payload())
        for i, b in enumerate(data['blocks']):
            assert set(b.keys()) == {'index', 'phase', 'start_date', 'weeks'}
            assert b['index'] == i
            # Exactly the /engine/block request shape.
            assert b['phase'] in {'base', 'build', 'peak', 'taper', 'race',
                                  'recovery', 'transition'}
            assert b['weeks'] in BLOCK_WEEKS


# =============================================================================
# SEASON LENGTHS — 12 / 16 / 24 weeks
# =============================================================================

class TestSeasonLengths:
    @pytest.mark.parametrize('anchor,expected', [
        (ANCHOR_12W, 12), (ANCHOR_16W, 16), (ANCHOR_24W, 24)])
    def test_week_count(self, client, anchor, expected):
        body = _payload(races=[
            {'name': 'A', 'date': anchor, 'priority': 'A'}])
        data = _ok(client, body)
        assert len(data['weeks']) == expected
        # Last week is the race week.
        assert data['weeks'][-1]['type'] == 'race'
        assert data['weeks'][-1]['phase'] == 'race'

    @pytest.mark.parametrize('anchor', [ANCHOR_12W, ANCHOR_16W, ANCHOR_24W])
    def test_anchor_race_lands_in_race_week(self, client, anchor):
        body = _payload(races=[
            {'name': 'Anchor', 'date': anchor, 'priority': 'A'}])
        data = _ok(client, body)
        race_week = data['weeks'][-1]
        names = [r['name'] for r in race_week['races']]
        assert 'Anchor' in names

    def test_nearest_future_a_race_is_anchor(self, client):
        """Two A-races → the nearer one anchors the season (the season ends
        on it, the later A-race is just a C-priority-style week inside)."""
        body = _payload(races=[
            {'name': 'Later A', 'date': ANCHOR_24W, 'priority': 'A'},
            {'name': 'Nearer A', 'date': ANCHOR_12W, 'priority': 'A'},
        ])
        data = _ok(client, body)
        assert len(data['weeks']) == 12
        assert 'Nearer A' in [r['name']
                              for r in data['weeks'][-1]['races']]


# =============================================================================
# PHASE ORDERING SANITY
# =============================================================================

class TestPhaseOrdering:
    @pytest.mark.parametrize('anchor', [ANCHOR_12W, ANCHOR_16W, ANCHOR_24W])
    def test_base_before_build_before_peak_taper_race(self, client, anchor):
        body = _payload(races=[{'name': 'A', 'date': anchor, 'priority': 'A'}])
        data = _ok(client, body)
        # Rank of the (non-recovery) training phase must never decrease.
        ranks = [PHASE_RANK[w['phase']] for w in data['weeks']]
        assert ranks == sorted(ranks), ranks
        phases_seq = [p['phase'] for p in data['phases']]
        # base present and first; race present and last.
        assert phases_seq[0] == 'base'
        assert phases_seq[-1] == 'race'
        assert phases_seq.index('base') < phases_seq.index('race')
        if 'build' in phases_seq:
            assert phases_seq.index('base') < phases_seq.index('build')

    def test_recovery_weeks_keep_training_phase(self, client):
        """Recovery weeks are typed 'recovery' but retain their base/build/
        peak phase (calculate_plan_dates preserves phase on deloads)."""
        data = _ok(client, _payload())
        for w in data['weeks']:
            if w['type'] == 'recovery':
                assert w['phase'] in {'base', 'build', 'peak'}


# =============================================================================
# BLOCK PARTITION INVARIANT
# =============================================================================

class TestBlockPartition:
    @pytest.mark.parametrize('anchor', [ANCHOR_12W, ANCHOR_16W, ANCHOR_24W])
    def test_every_week_in_exactly_one_2_4_week_block(self, client, anchor):
        body = _payload(races=[{'name': 'A', 'date': anchor, 'priority': 'A'}])
        data = _ok(client, body)
        blocks = data['blocks']
        weeks = data['weeks']

        # Blocks are 0..N-1, each 2-4 weeks.
        assert [b['index'] for b in blocks] == list(range(len(blocks)))
        for b in blocks:
            assert 2 <= b['weeks'] <= 4

        # Every week points at a real block; membership count matches
        # block['weeks']; positions are 1..length in order.
        membership = Counter()
        per_block_positions = {}
        for w in weeks:
            idx = w['block']['index']
            assert 0 <= idx < len(blocks)
            assert w['block']['length'] == blocks[idx]['weeks']
            membership[idx] += 1
            per_block_positions.setdefault(idx, []).append(w['block']['position'])
        for b in blocks:
            assert membership[b['index']] == b['weeks']
            assert per_block_positions[b['index']] == list(
                range(1, b['weeks'] + 1))

        # Total coverage: sum of block weeks == season length.
        assert sum(b['weeks'] for b in blocks) == len(weeks)

    def test_block_start_date_matches_first_week(self, client):
        data = _ok(client, _payload())
        first_week_of_block = {}
        for w in data['weeks']:
            idx = w['block']['index']
            if w['block']['position'] == 1:
                first_week_of_block[idx] = w['start_date']
        for b in data['blocks']:
            assert b['start_date'] == first_week_of_block[b['index']]

    def test_blocks_are_contiguous_in_week_order(self, client):
        """Walking the weeks in order, the block index never decreases and
        only steps up by 1 (blocks partition the timeline left to right)."""
        data = _ok(client, _payload())
        seen = [w['block']['index'] for w in data['weeks']]
        cur = 0
        assert seen[0] == 0
        for idx in seen:
            assert idx in (cur, cur + 1)
            cur = idx


# =============================================================================
# B / C RACE OVERLAY
# =============================================================================

class TestBraceOverlay:
    def test_b_race_lands_and_is_noted(self, client):
        """A B-race inside the window gets the mini-taper overlay: its week
        is not typed recovery, carries the race in `races`, and gets a note."""
        b_date = '2026-09-19'  # a Saturday inside the 12-week window
        body = _payload(races=[
            {'name': 'Goal Gravel 200', 'date': ANCHOR_12W, 'priority': 'A'},
            {'name': 'Tune-Up Crit', 'date': b_date, 'priority': 'B'},
        ])
        data = _ok(client, body)
        hits = [w for w in data['weeks']
                if any(r['name'] == 'Tune-Up Crit' for r in w['races'])]
        assert len(hits) == 1
        week = hits[0]
        assert week['type'] != 'recovery'  # overlay clears the deload flag
        assert 'Tune-Up Crit' in week['note']
        assert week['races'][0]['priority'] == 'B'

    def test_c_race_appears_in_its_week(self, client):
        c_date = '2026-09-12'
        body = _payload(races=[
            {'name': 'Goal Gravel 200', 'date': ANCHOR_12W, 'priority': 'A'},
            {'name': 'Local C', 'date': c_date, 'priority': 'C'},
        ])
        data = _ok(client, body)
        assert any(
            any(r['name'] == 'Local C' for r in w['races'])
            for w in data['weeks'])

    def test_race_outside_window_is_ignored(self, client):
        """A B-race after the anchor never appears in any week."""
        body = _payload(races=[
            {'name': 'Goal Gravel 200', 'date': ANCHOR_12W, 'priority': 'A'},
            {'name': 'Future B', 'date': ANCHOR_24W, 'priority': 'B'},
        ])
        data = _ok(client, body)
        assert not any(
            any(r['name'] == 'Future B' for r in w['races'])
            for w in data['weeks'])


# =============================================================================
# DETERMINISM
# =============================================================================

class TestDeterminism:
    def test_identical_requests_identical_output(self, client):
        r1 = _ok(client, _payload())
        r2 = _ok(client, _payload())
        r1.pop('engine')
        r2.pop('engine')
        assert r1 == r2

    def test_determinism_with_b_races(self, client):
        body = _payload(races=[
            {'name': 'A', 'date': ANCHOR_16W, 'priority': 'A'},
            {'name': 'B1', 'date': '2026-09-19', 'priority': 'B'},
            {'name': 'C1', 'date': '2026-10-17', 'priority': 'C'},
        ])
        r1 = _ok(client, body)
        r2 = _ok(client, body)
        r1.pop('engine')
        r2.pop('engine')
        assert r1 == r2


# =============================================================================
# INVALID REQUESTS — 400 with field errors
# =============================================================================

class TestInvalidRequests:
    def test_non_json_body(self, client):
        resp = client.post('/engine/season', data='not json',
                           content_type='text/plain',
                           headers={'X-Engine-Secret': ENGINE_SECRET})
        assert resp.status_code == 400
        assert resp.get_json()['error'] == 'invalid_request'

    def test_missing_athlete(self, client):
        body = _payload()
        del body['athlete']
        resp = _post(client, body)
        assert resp.status_code == 400
        assert 'athlete' in resp.get_json()['fields']

    def test_missing_hours(self, client):
        body = _payload()
        del body['athlete']['hours_per_week']
        resp = _post(client, body)
        assert resp.status_code == 400
        assert 'athlete.hours_per_week' in resp.get_json()['fields']

    def test_hours_below_minimum(self, client):
        body = _payload()
        body['athlete']['hours_per_week'] = 2
        resp = _post(client, body)
        assert resp.status_code == 400
        assert 'athlete.hours_per_week' in resp.get_json()['fields']

    def test_missing_start_date(self, client):
        body = _payload()
        del body['start_date']
        resp = _post(client, body)
        assert resp.status_code == 400
        assert 'start_date' in resp.get_json()['fields']

    def test_start_date_too_far_in_past(self, client):
        body = _payload()
        body['start_date'] = '2020-01-06'
        resp = _post(client, body)
        assert resp.status_code == 400
        assert 'start_date' in resp.get_json()['fields']

    def test_no_races(self, client):
        body = _payload(races=[])
        resp = _post(client, body)
        assert resp.status_code == 400
        assert 'races' in resp.get_json()['fields']

    def test_no_a_race(self, client):
        body = _payload(races=[
            {'name': 'B only', 'date': ANCHOR_12W, 'priority': 'B'}])
        resp = _post(client, body)
        assert resp.status_code == 400
        assert 'races' in resp.get_json()['fields']

    def test_a_race_before_start_rejected(self, client):
        """An A-race dated before start_date does not anchor a season."""
        body = _payload(races=[
            {'name': 'Past A', 'date': '2026-07-04', 'priority': 'A'}])
        resp = _post(client, body)
        assert resp.status_code == 400
        assert 'races' in resp.get_json()['fields']

    def test_season_too_short(self, client):
        """< 4 weeks start→anchor is rejected."""
        body = _payload(races=[
            {'name': 'Soon', 'date': '2026-08-17', 'priority': 'A'}])
        resp = _post(client, body)
        assert resp.status_code == 400
        assert 'season' in resp.get_json()['fields']

    def test_season_too_long(self, client):
        """> 40 weeks start→anchor is rejected."""
        body = _payload(races=[
            {'name': 'Far', 'date': '2027-07-04', 'priority': 'A'}])
        resp = _post(client, body)
        assert resp.status_code == 400
        assert 'season' in resp.get_json()['fields']

    def test_invalid_priority(self, client):
        body = _payload()
        body['races'][0]['priority'] = 'X'
        resp = _post(client, body)
        assert resp.status_code == 400
        assert 'races[0].priority' in resp.get_json()['fields']

    def test_invalid_race_date(self, client):
        body = _payload()
        body['races'][0]['date'] = 'August 3rd'
        resp = _post(client, body)
        assert resp.status_code == 400
        assert 'races[0].date' in resp.get_json()['fields']

    def test_missing_race_name(self, client):
        body = _payload()
        del body['races'][0]['name']
        resp = _post(client, body)
        assert resp.status_code == 400
        assert 'races[0].name' in resp.get_json()['fields']

    def test_invalid_discipline(self, client):
        body = _payload()
        body['athlete']['discipline'] = 'triathlon'
        resp = _post(client, body)
        assert resp.status_code == 400
        assert 'athlete.discipline' in resp.get_json()['fields']

    def test_invalid_methodology(self, client):
        resp = _post(client, _payload(methodology='sweet_spot_only'))
        assert resp.status_code == 400
        assert 'methodology' in resp.get_json()['fields']

    def test_negative_distance(self, client):
        body = _payload()
        body['races'][0]['distance_mi'] = -5
        resp = _post(client, body)
        assert resp.status_code == 400
        assert 'races[0].distance_mi' in resp.get_json()['fields']


# =============================================================================
# OPTIONAL FIELDS
# =============================================================================

class TestOptionalFields:
    def test_null_methodology_uses_default(self, client):
        assert _post(client, _payload(methodology=None)).status_code == 200

    def test_minimal_athlete_hours_only(self, client):
        body = _payload(athlete={'hours_per_week': 6})
        assert _post(client, body).status_code == 200

    def test_methodology_variants_all_generate(self, client):
        for m in ['polarized_80_20', 'time_crunched', 'g_spot',
                  'traditional_pyramidal']:
            assert _post(client, _payload(methodology=m)).status_code == 200, m


# =============================================================================
# ADAPTER UNIT TESTS (no HTTP)
# =============================================================================

class TestAdapterUnits:
    def test_split_sizes_prefers_three_and_recovery_boundary(self):
        from engine_season import _split_sizes
        # 4-week L/L/L/R → one 4-week block (recovery ends it).
        assert _split_sizes(['load', 'load', 'load', 'recovery']) == [4]
        # 3-week L/L/R → one 3-week block.
        assert _split_sizes(['load', 'load', 'recovery']) == [3]
        # 6-week L/L/R/L/L/R → two clean 3-week blocks at recovery seams.
        assert _split_sizes(
            ['load', 'load', 'recovery', 'load', 'load', 'recovery']) == [3, 3]
        # 2-week → single 2-week block.
        assert _split_sizes(['taper', 'race']) == [2]

    def test_split_sizes_only_yields_2_to_4(self):
        from engine_season import _split_sizes
        for n in range(2, 25):
            sizes = _split_sizes(['load'] * n)
            assert sum(sizes) == n
            assert all(2 <= s <= 4 for s in sizes)

    def test_validate_request_anchor_selection(self):
        from engine_season import validate_request
        params, errors = validate_request(_payload())
        assert not errors
        assert params['anchor']['name'] == 'Goal Gravel 200'
        assert params['plan_weeks'] == 12

    def test_generate_season_measured_ms(self):
        from engine_season import validate_request, generate_season
        params, errors = validate_request(_payload())
        assert not errors
        result = generate_season(params)
        assert 0 <= result['engine']['generated_ms'] < 500
