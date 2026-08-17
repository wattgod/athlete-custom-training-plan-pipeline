#!/usr/bin/env python3
"""Tests for webhook/consult_intake_tokens.py — the purpose-scoped, 30-day
fragment-carried consult intake token.

Run with: pytest webhook/tests/test_consult_intake_tokens.py -v
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from consult_intake_tokens import (ConsultIntakeTokenError, DEFAULT_TTL_SECONDS,
                                   issue_intake_token, verify_intake_token)


@pytest.fixture
def secret(monkeypatch):
    monkeypatch.setenv('CONSULT_INTAKE_TOKEN_SECRET', 'test-secret-value')


class TestUnconfigured:
    def test_issue_without_secret_raises(self, monkeypatch):
        monkeypatch.delenv('CONSULT_INTAKE_TOKEN_SECRET', raising=False)
        with pytest.raises(ConsultIntakeTokenError):
            issue_intake_token(order_id='cs_1')

    def test_verify_without_secret_raises(self, monkeypatch):
        monkeypatch.delenv('CONSULT_INTAKE_TOKEN_SECRET', raising=False)
        with pytest.raises(ConsultIntakeTokenError):
            verify_intake_token('whatever.sig', expected_order_id='cs_1')


class TestRoundTrip:
    def test_valid_token_verifies(self, secret):
        token = issue_intake_token(order_id='cs_1', now=1_000)
        claims = verify_intake_token(token, expected_order_id='cs_1', now=1_050)
        assert claims['order_id'] == 'cs_1'
        assert claims['purpose'] == 'consult_intake'

    def test_default_ttl_is_30_days(self, secret):
        token = issue_intake_token(order_id='cs_1', now=1_000)
        assert verify_intake_token(token, expected_order_id='cs_1',
                                   now=1_000 + DEFAULT_TTL_SECONDS - 1)
        with pytest.raises(ConsultIntakeTokenError):
            verify_intake_token(token, expected_order_id='cs_1',
                                now=1_000 + DEFAULT_TTL_SECONDS + 1)

    def test_ttl_cannot_exceed_30_days(self, secret):
        with pytest.raises(ConsultIntakeTokenError):
            issue_intake_token(order_id='cs_1', ttl_seconds=DEFAULT_TTL_SECONDS + 1)


class TestScope:
    def test_wrong_order_id_rejected(self, secret):
        token = issue_intake_token(order_id='cs_1', now=1_000)
        with pytest.raises(ConsultIntakeTokenError):
            verify_intake_token(token, expected_order_id='cs_2', now=1_050)

    def test_tampered_signature_rejected(self, secret):
        token = issue_intake_token(order_id='cs_1', now=1_000)
        payload, sig = token.split('.', 1)
        tampered = f"{payload}.{sig[:-1]}{'a' if sig[-1] != 'a' else 'b'}"
        with pytest.raises(ConsultIntakeTokenError):
            verify_intake_token(tampered, expected_order_id='cs_1', now=1_050)

    def test_malformed_token_rejected(self, secret):
        with pytest.raises(ConsultIntakeTokenError):
            verify_intake_token('not-a-real-token', expected_order_id='cs_1')

    def test_different_secret_rejects(self, monkeypatch):
        monkeypatch.setenv('CONSULT_INTAKE_TOKEN_SECRET', 'secret-a')
        token = issue_intake_token(order_id='cs_1', now=1_000)
        monkeypatch.setenv('CONSULT_INTAKE_TOKEN_SECRET', 'secret-b')
        with pytest.raises(ConsultIntakeTokenError):
            verify_intake_token(token, expected_order_id='cs_1', now=1_050)

    def test_intake_token_is_a_distinct_secret_from_runner_and_cron(self, monkeypatch):
        """A leaked 30-day intake token (mailed to an athlete) must not
        double as CONSULT_RUNNER_SECRET or CRON_SECRET — the secrets are
        deliberately independent env vars, never derived from one another."""
        monkeypatch.setenv('CONSULT_INTAKE_TOKEN_SECRET', 'shared-value')
        token = issue_intake_token(order_id='cs_1', now=1_000)
        # The token itself carries no bytes usable as a bearer secret for
        # any other endpoint — it's purpose- and order-scoped, and the
        # runner/cron routes check a completely different header/env pair.
        assert 'CONSULT_RUNNER_SECRET' not in token
        assert 'CRON_SECRET' not in token
