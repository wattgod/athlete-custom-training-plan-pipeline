import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from download_tokens import (DownloadTokenError, issue_download_token,
                             revoke_download_token, verify_download_token)


@pytest.fixture
def configured_keys(monkeypatch):
    monkeypatch.setenv('DOWNLOAD_TOKEN_KEYS', json.dumps({
        'coach': {'coach-v1': 'coach-secret'},
        'customer': {'customer-v1': 'customer-secret'},
    }))
    monkeypatch.setenv('DOWNLOAD_TOKEN_COACH_KID', 'coach-v1')
    monkeypatch.setenv('DOWNLOAD_TOKEN_CUSTOMER_KID', 'customer-v1')


def _token(**overrides):
    values = {
        'order_id': 'cs_order_1', 'athlete_id': 'athlete-m',
        'generation_revision': 2, 'artifact': 'review_bundle',
        'now': 1_000, 'ttl_seconds': 100, 'jti': 'link-1',
    }
    values.update(overrides)
    return issue_download_token(**values)


def _verify(token, **overrides):
    values = {
        'expected_order_id': 'cs_order_1',
        'expected_athlete_id': 'athlete-m', 'expected_revision': 2,
        'expected_artifact': 'review_bundle', 'expected_audience': 'coach',
        'now': 1_050,
    }
    values.update(overrides)
    return verify_download_token(token, **values)


def test_typed_claims_round_trip(configured_keys):
    claims = _verify(_token())
    assert claims['jti'] == 'link-1'
    assert claims['kid'] == 'coach-v1'


@pytest.mark.parametrize(('field', 'override'), [
    ('expected_order_id', 'cs_order_2'),
    ('expected_athlete_id', 'other-athlete'),
    ('expected_revision', 3),
    ('expected_artifact', 'customer_bundle'),
    ('expected_audience', 'customer'),
])
def test_cross_scope_reuse_is_rejected(field, override, configured_keys):
    with pytest.raises(DownloadTokenError, match='mismatch|audience'):
        _verify(_token(), **{field: override})


def test_expiry_and_max_lifetime_are_enforced(configured_keys):
    with pytest.raises(DownloadTokenError, match='expired'):
        _verify(_token(), now=1_100)
    with pytest.raises(DownloadTokenError, match='lifetime'):
        _token(ttl_seconds=8 * 24 * 60 * 60)


def test_unknown_artifact_and_unknown_kid_fail_closed(monkeypatch, configured_keys):
    with pytest.raises(DownloadTokenError, match='unknown artifact'):
        _token(artifact='full')
    token = _token()
    monkeypatch.setenv('DOWNLOAD_TOKEN_KEYS', json.dumps({
        'coach': {'coach-v2': 'new-secret'},
        'customer': {'customer-v1': 'customer-secret'},
    }))
    with pytest.raises(DownloadTokenError, match='unknown token key'):
        _verify(token)


def test_per_link_and_per_key_revocation(tmp_path, configured_keys):
    revocations = tmp_path / 'revoked.json'
    token = _token()
    revoke_download_token(revocations, jti='link-1')
    with pytest.raises(DownloadTokenError, match='revoked'):
        _verify(token, revocation_path=revocations)

    second = _token(jti='link-2')
    revoke_download_token(revocations, kid='coach-v1')
    with pytest.raises(DownloadTokenError, match='revoked'):
        _verify(second, revocation_path=revocations)


def test_customer_key_cannot_sign_coach_artifact(configured_keys):
    with pytest.raises(DownloadTokenError, match='audience'):
        _token(audience='customer')


def test_missing_secret_refuses_issue_and_verify(monkeypatch, configured_keys):
    token = _token()
    for name in (
        'DOWNLOAD_TOKEN_KEYS', 'DOWNLOAD_TOKEN_SECRET', 'DOWNLOAD_TOKEN_KID',
        'DOWNLOAD_TOKEN_COACH_KID', 'DOWNLOAD_TOKEN_CUSTOMER_KID',
    ):
        monkeypatch.delenv(name, raising=False)
    # CRON_SECRET is deliberately not a signing-key fallback.
    monkeypatch.setenv('CRON_SECRET', 'operator-secret-is-not-a-token-key')

    with pytest.raises(DownloadTokenError, match='not configured'):
        _token()
    with pytest.raises(DownloadTokenError, match='not configured'):
        _verify(token)


def test_legacy_month_window_token_is_rejected():
    legacy_token = '0123456789abcdef0123456789abcdef'
    with pytest.raises(DownloadTokenError, match='malformed'):
        _verify(legacy_token)


def test_authenticated_endpoint_revokes_real_issued_jti(
    monkeypatch, tmp_path, configured_keys,
):
    import app as webhook_app

    token = _token(jti='issued-operational-link')
    monkeypatch.setattr(webhook_app, 'DATA_DIR', str(tmp_path))
    monkeypatch.setenv('CRON_SECRET', 'ops-secret')
    response = webhook_app.app.test_client().post(
        '/api/download-tokens/revoke',
        headers={'X-Cron-Secret': 'ops-secret'},
        json={'jti': 'issued-operational-link'},
    )
    assert response.status_code == 200
    assert response.get_json()['status'] == 'revoked'
    with pytest.raises(DownloadTokenError, match='revoked'):
        _verify(token, revocation_path=tmp_path / 'token_revocations.json')
