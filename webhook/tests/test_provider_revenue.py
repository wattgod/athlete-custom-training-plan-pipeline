import json
import os
import sys
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ.setdefault("FLASK_ENV", "test")
os.environ.setdefault("STRIPE_SECRET_KEY", "")

import app as webhook_app
from provider_revenue import (
    ProviderRevenueError,
    build_stripe_revenue_receipt,
    parse_reconciliation_window,
)


SECRET = "provider-revenue-test-secret"


class Page:
    def __init__(self, data, has_more=False):
        self.data = data
        self.has_more = has_more


class ListResource:
    def __init__(self, rows):
        self.rows = list(rows)
        self.calls = []

    def list(self, **params):
        self.calls.append(params)
        start = 0
        if params.get("starting_after"):
            ids = [row["id"] for row in self.rows]
            start = ids.index(params["starting_after"]) + 1
        page_size = min(params.get("limit", 100), 2)
        data = self.rows[start:start + page_size]
        return Page(data, start + page_size < len(self.rows))


def _provider():
    session = {
        "id": "cs_live_private", "created": 1777507200, "livemode": True,
        "payment_intent": "pi_private", "customer": "cus_private",
        "currency": "usd", "amount_total": 15000, "mode": "payment",
        "status": "complete", "payment_status": "paid",
        "metadata": {
            "product_type": "consulting", "brand": "gravelgod",
            "athlete_name": "Private Person", "email": "private@example.com",
        },
        "total_details": {"amount_discount": 0, "amount_tax": 0},
    }
    invoice = {
        "id": "in_private", "created": 1777507201, "livemode": True,
        "customer": "cus_private", "currency": "usd", "status": "paid",
        "amount_due": 15000, "amount_paid": 15000, "amount_remaining": 0,
        "lines": {"has_more": False, "data": [{
            "id": "il_private", "price": "price_consulting",
            "currency": "usd", "amount": 15000, "quantity": 1,
            "description": "private@example.com must not escape",
            "period": {"start": 1777507200, "end": 1777507200},
        }]},
    }
    charge = {
        "id": "ch_private", "created": 1777507202, "livemode": True,
        "payment_intent": "pi_private", "customer": "cus_private",
        "invoice": "in_private", "balance_transaction": "txn_charge_private",
        "currency": "usd", "status": "succeeded", "paid": True,
        "captured": True, "disputed": False, "amount": 15000,
        "amount_refunded": 1000,
        "billing_details": {"email": "private@example.com"},
        "receipt_url": "https://example.test/secret-receipt",
    }
    refund = {
        "id": "re_private", "charge": "ch_private",
        "payment_intent": "pi_private", "balance_transaction": "txn_ref_private",
        "created": 1777507203, "currency": "usd", "status": "succeeded",
        "amount": 1000,
    }
    balance_rows = [
        {
            "id": "txn_charge_private", "source": "ch_private",
            "created": 1777507202, "available_on": 1777593600,
            "currency": "usd", "type": "charge", "reporting_category": "charge",
            "status": "available", "amount": 15000, "fee": 465, "net": 14535,
        },
        {
            "id": "txn_ref_private", "source": "re_private",
            "created": 1777507203, "available_on": 1777593600,
            "currency": "usd", "type": "refund", "reporting_category": "refund",
            "status": "available", "amount": -1000, "fee": 0, "net": -1000,
        },
        {
            "id": "txn_adjust_private", "source": "adj_private",
            "created": 1777507204, "available_on": 1777593600,
            "currency": "usd", "type": "adjustment",
            "reporting_category": "adjustment", "status": "available",
            "amount": 25, "fee": 0, "net": 25,
        },
    ]
    payout = {
        "id": "po_private", "balance_transaction": "txn_payout_private",
        "created": 1777507205, "arrival_date": 1777680000, "currency": "usd",
        "status": "paid", "amount": 13560, "automatic": True,
        "destination": "ba_private",
    }
    provider = SimpleNamespace(
        Product=ListResource([{
            "id": "prod_consulting", "created": 1777507100,
            "name": "Gravel Race Consulting", "active": True,
            "livemode": True,
        }]),
        Price=ListResource([{
            "id": "price_consulting", "created": 1777507101,
            "product": "prod_consulting", "currency": "usd",
            "unit_amount": 15000, "active": True, "livemode": True,
        }]),
        checkout=SimpleNamespace(Session=ListResource([session])),
        Invoice=ListResource([invoice]),
        Charge=ListResource([charge]),
        Refund=ListResource([refund]),
        BalanceTransaction=ListResource(balance_rows),
        Payout=ListResource([payout]),
        Account=SimpleNamespace(retrieve=lambda: {
            "id": "acct_private", "charges_enabled": True, "payouts_enabled": True,
            "email": "owner@example.com",
        }),
        Balance=SimpleNamespace(retrieve=lambda: {
            "available": [{"currency": "usd", "amount": 2000}],
            "pending": [{"currency": "usd", "amount": 300}],
        }),
    )
    return provider


def test_window_is_inclusive_and_bounded():
    assert parse_reconciliation_window("2025-08-27", "2026-08-27") == (
        date(2025, 8, 27), date(2026, 8, 27))
    with pytest.raises(ProviderRevenueError):
        parse_reconciliation_window("2026-08-28", "2026-08-27")
    with pytest.raises(ProviderRevenueError):
        parse_reconciliation_window("2025-01-01", "2026-08-27")


def test_receipt_controls_and_privacy_projection():
    receipt = build_stripe_revenue_receipt(
        _provider(), date(2026, 4, 30), date(2026, 5, 1), SECRET)

    assert receipt["controls"]["successful_charges"]["usd"] == {
        "count": 1, "amount_cents": 15000}
    assert receipt["controls"]["succeeded_refunds"]["usd"] == {
        "count": 1, "amount_cents": 1000}
    assert receipt["controls"]["paid_payouts"]["usd"] == {
        "count": 1, "amount_cents": 13560}
    assert receipt["controls"]["balance_activity_by_category"]["usd"]["charge"] == {
        "count": 1, "amount_cents": 15000, "fee_cents": 465,
        "net_cents": 14535}
    charge = receipt["rows"]["charges"][0]
    assert charge["offer_family"] == "consulting"
    assert charge["gross_less_refunds_cents"] == 14000
    assert charge["record_key"].startswith("srk_")
    assert receipt["rows"]["invoices"][0]["line_items"] == [{
        "price_record_key": receipt["rows"]["prices"][0]["record_key"],
        "product_record_key": receipt["rows"]["products"][0]["record_key"],
        "merchant_product_name": "Gravel Race Consulting",
        "offer_family": "consulting", "currency": "usd",
        "amount_cents": 15000, "quantity": 1,
        "period_start_at": "2026-04-30T00:00:00+00:00",
        "period_end_at": "2026-04-30T00:00:00+00:00",
    }]
    assert receipt["rows"]["checkout_sessions"][0]["synthetic"] is False

    encoded = json.dumps(receipt, sort_keys=True)
    for forbidden in (
        "private@example.com", "owner@example.com", "Private Person",
        "cs_live_private", "pi_private", "cus_private", "ch_private",
        "re_private", "po_private", "acct_private", "ba_private",
        "secret-receipt",
        "private@example.com must not escape",
    ):
        assert forbidden not in encoded


def test_pagination_advances_without_mutation_methods():
    provider = _provider()
    receipt = build_stripe_revenue_receipt(
        provider, date(2026, 4, 30), date(2026, 5, 1), SECRET)
    assert len(receipt["rows"]["balance_transactions"]) == 3
    calls = provider.BalanceTransaction.calls
    assert len(calls) == 2
    assert "starting_after" not in calls[0]
    assert calls[1]["starting_after"] == "txn_ref_private"
    assert not hasattr(provider.Charge, "create")
    assert not hasattr(provider.Refund, "create")


def test_synthetic_monitor_is_classified_without_projecting_identity():
    provider = _provider()
    provider.checkout.Session.rows[0]["metadata"]["athlete_name"] = (
        "Daily Health Check [TEST]")
    receipt = build_stripe_revenue_receipt(
        provider, date(2026, 4, 30), date(2026, 5, 1), SECRET)
    session = receipt["rows"]["checkout_sessions"][0]
    assert session["synthetic"] is True
    assert "Daily Health Check" not in json.dumps(receipt)


def test_server_price_registry_overrides_catalog_name_inference():
    receipt = build_stripe_revenue_receipt(
        _provider(), date(2026, 4, 30), date(2026, 5, 1), SECRET,
        offer_price_ids={"consult_addon": ("price_consulting",)})
    assert receipt["rows"]["prices"][0]["offer_family"] == "consult_addon"
    assert receipt["rows"]["invoices"][0]["offer_family"] == "consult_addon"
    assert receipt["rows"]["charges"][0]["offer_family"] == "consulting"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(webhook_app, "CRON_SECRET", SECRET)
    webhook_app.app.config["TESTING"] = True
    webhook_app.limiter.reset()
    return webhook_app.app.test_client()


def test_endpoint_requires_auth_and_valid_window(client):
    body = {"start_date": "2025-08-27", "end_date": "2026-08-27"}
    assert client.post("/api/cron/stripe-reconciliation", json=body).status_code == 401
    assert client.post(
        "/api/cron/stripe-reconciliation", json=body,
        headers={"X-Cron-Secret": "wrong"}).status_code == 401
    webhook_app.limiter.reset()
    invalid = client.post(
        "/api/cron/stripe-reconciliation",
        json={"start_date": "bad", "end_date": "2026-08-27"},
        headers={"X-Cron-Secret": SECRET})
    assert invalid.status_code == 400


def test_endpoint_returns_sanitized_receipt(client, monkeypatch):
    expected = build_stripe_revenue_receipt(
        _provider(), date(2025, 8, 27), date(2026, 8, 27), SECRET)
    monkeypatch.setattr(
        webhook_app, "build_stripe_revenue_receipt",
        lambda *args, **kwargs: expected)
    response = client.post(
        "/api/cron/stripe-reconciliation",
        json={"start_date": "2025-08-27", "end_date": "2026-08-27"},
        headers={"X-Cron-Secret": SECRET})
    assert response.status_code == 200
    assert response.get_json()["schema"] == "stripe_revenue_reconciliation/v1"
