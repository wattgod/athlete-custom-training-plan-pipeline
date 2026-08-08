import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from review_auth import (ReviewAuthError, create_review_session,
                         issue_review_token, load_review_session,
                         review_credential_id, verify_review_token)


@pytest.fixture(autouse=True)
def review_key(monkeypatch):
    for name in (
        'REVIEW_TOKEN_KEYS', 'REVIEW_TOKEN_SECRET', 'REVIEW_TOKEN_KID',
        'DOWNLOAD_TOKEN_KEYS', 'DOWNLOAD_TOKEN_KID',
        'DOWNLOAD_TOKEN_COACH_KID',
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv('DOWNLOAD_TOKEN_SECRET', 'phase2-review-test-secret')


def _issue(now=1000, **overrides):
    values = {
        'order_id': 'test_order', 'athlete_id': 'athlete-m',
        'generation_revision': 2, 'issued_to': 'coach@example.invalid',
        'now': now,
    }
    values.update(overrides)
    return issue_review_token(**values)


def _verify(token, tmp_path, now=1001, **overrides):
    values = {
        'order_id': 'test_order', 'athlete_id': 'athlete-m',
        'generation_revision': 2,
        'revocation_path': tmp_path / 'revocations.json', 'now': now,
    }
    values.update(overrides)
    return verify_review_token(token, **values)


def test_review_token_is_action_revision_and_audience_scoped(tmp_path):
    claims = _verify(_issue(), tmp_path)
    assert claims['action'] == 'review'
    assert claims['audience'] == 'coach'
    assert claims['generation_revision'] == 2
    assert review_credential_id(claims).startswith('review-link:phase1-v1:')


@pytest.mark.parametrize('override, message', [
    ({'order_id': 'other'}, 'order_id mismatch'),
    ({'athlete_id': 'other'}, 'athlete_id mismatch'),
    ({'generation_revision': 3}, 'revision mismatch'),
])
def test_review_token_rejects_scope_mismatch(tmp_path, override, message):
    with pytest.raises(ReviewAuthError, match=message):
        _verify(_issue(), tmp_path, **override)


def test_review_token_expiry_and_revocation_fail_closed(tmp_path):
    token = _issue(now=1000, ttl_seconds=10, jti='review-jti')
    with pytest.raises(ReviewAuthError, match='expired'):
        _verify(token, tmp_path, now=1010)

    (tmp_path / 'revocations.json').write_text(json.dumps({
        'jti': ['review-jti'], 'kid': [],
    }))
    with pytest.raises(ReviewAuthError, match='revoked'):
        _verify(token, tmp_path, now=1001)


def test_review_tokens_fail_closed_without_keys(monkeypatch):
    monkeypatch.delenv('DOWNLOAD_TOKEN_SECRET')
    with pytest.raises(ReviewAuthError, match='not configured'):
        _issue()


def test_server_session_is_opaque_scoped_and_revocation_aware(tmp_path):
    claims = _verify(_issue(jti='session-jti'), tmp_path)
    session_id, session = create_review_session(
        tmp_path / 'sessions', claims, now=1001)
    assert 'session-jti' not in session_id
    loaded = load_review_session(
        tmp_path / 'sessions', session_id, order_id='test_order',
        revocation_path=tmp_path / 'revocations.json', now=1002)
    assert loaded['csrf_token']
    assert loaded['credential'] == review_credential_id(claims)

    with pytest.raises(ReviewAuthError, match='mismatched'):
        load_review_session(
            tmp_path / 'sessions', session_id, order_id='other', now=1002)

    (tmp_path / 'revocations.json').write_text(json.dumps({
        'jti': ['session-jti'], 'kid': [],
    }))
    with pytest.raises(ReviewAuthError, match='revoked'):
        load_review_session(
            tmp_path / 'sessions', session_id, order_id='test_order',
            revocation_path=tmp_path / 'revocations.json', now=1002)
