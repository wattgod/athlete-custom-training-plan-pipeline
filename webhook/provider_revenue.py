"""Read-only, privacy-bounded Stripe revenue reconciliation.

The production order service owns the live Stripe credential.  This module
uses only provider list/retrieve methods and returns deterministic HMAC record
keys instead of Stripe IDs, customer details, names, emails, or addresses.
"""

from __future__ import annotations

import hashlib
import hmac
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Callable, Iterable, Mapping


MAX_WINDOW_DAYS = 400
PAGE_LIMIT = 100
MAX_PAGES = 1000
_ALLOWED_BRANDS = {"gravelgod", "roadielabs", "xcskilabs"}
_ALLOWED_OFFERS = {
    "training_plan", "coaching", "consulting", "consult_addon", "unknown",
}


class ProviderRevenueError(RuntimeError):
    """Safe error raised for invalid requests or incomplete pagination."""


def parse_reconciliation_window(start_date: str, end_date: str) -> tuple[date, date]:
    """Parse an inclusive ISO-date window and enforce the bounded export."""
    try:
        start = date.fromisoformat(str(start_date))
        end = date.fromisoformat(str(end_date))
    except (TypeError, ValueError) as exc:
        raise ProviderRevenueError(
            "start_date and end_date must be ISO dates (YYYY-MM-DD)") from exc
    if end < start:
        raise ProviderRevenueError("end_date must be on or after start_date")
    if (end - start).days + 1 > MAX_WINDOW_DAYS:
        raise ProviderRevenueError(
            f"date window must be {MAX_WINDOW_DAYS} days or fewer")
    return start, end


def _unix_window(start: date, end: date) -> tuple[int, int]:
    start_at = datetime.combine(start, time.min, tzinfo=timezone.utc)
    end_exclusive = datetime.combine(
        end + timedelta(days=1), time.min, tzinfo=timezone.utc)
    return int(start_at.timestamp()), int(end_exclusive.timestamp())


def _plain(value: Any) -> dict:
    if value is None:
        return {}
    if hasattr(value, "_to_dict_recursive"):
        converted = value._to_dict_recursive()
        return dict(converted) if isinstance(converted, Mapping) else {}
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _object_id(value: Any) -> str:
    if isinstance(value, str):
        return value
    return str(_plain(value).get("id") or "")


def _page_items(result: Any) -> list:
    data = getattr(result, "data", None)
    if data is None and isinstance(result, Mapping):
        data = result.get("data")
    return list(data or [])


def _page_has_more(result: Any) -> bool:
    has_more = getattr(result, "has_more", None)
    if has_more is None and isinstance(result, Mapping):
        has_more = result.get("has_more")
    return bool(has_more)


def _iter_pages(list_method: Callable[..., Any], **params: Any) -> Iterable[dict]:
    starting_after = ""
    seen_last_ids = set()
    for _ in range(MAX_PAGES):
        request_params = {"limit": PAGE_LIMIT, **params}
        if starting_after:
            request_params["starting_after"] = starting_after
        result = list_method(**request_params)
        items = _page_items(result)
        for item in items:
            yield _plain(item)
        if not _page_has_more(result):
            return
        if not items:
            raise ProviderRevenueError("provider pagination returned an empty partial page")
        last_id = _object_id(items[-1])
        if not last_id or last_id in seen_last_ids:
            raise ProviderRevenueError("provider pagination cursor did not advance")
        seen_last_ids.add(last_id)
        starting_after = last_id
    raise ProviderRevenueError("provider pagination exceeded the safety limit")


def _record_key(secret: str, kind: str, provider_id: Any) -> str:
    raw_id = _object_id(provider_id)
    if not raw_id:
        return ""
    digest = hmac.new(
        secret.encode("utf-8"), f"stripe:{kind}:{raw_id}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"srk_{digest}"


def _created_at(value: Any) -> str:
    try:
        return datetime.fromtimestamp(int(value), tz=timezone.utc).isoformat()
    except (TypeError, ValueError, OSError):
        return ""


def _currency(value: Any) -> str:
    candidate = str(value or "").strip().lower()
    return candidate if len(candidate) == 3 and candidate.isalpha() else "unknown"


def _safe_dimension(value: Any, allowed: set[str], default: str) -> str:
    candidate = str(value or "").strip().lower()
    return candidate if candidate in allowed else default


def _offer(metadata: Any) -> str:
    data = _plain(metadata)
    return _safe_dimension(data.get("product_type"), _ALLOWED_OFFERS, "unknown")


def _brand(metadata: Any) -> str:
    data = _plain(metadata)
    return _safe_dimension(data.get("brand"), _ALLOWED_BRANDS, "unknown")


def _invoice_subscription_id(invoice: Mapping[str, Any]) -> str:
    direct = _object_id(invoice.get("subscription"))
    if direct:
        return direct
    parent = _plain(invoice.get("parent"))
    details = _plain(parent.get("subscription_details"))
    return _object_id(details.get("subscription"))


def _totals(rows: Iterable[dict], amount_field: str) -> dict[str, dict[str, int]]:
    by_currency: dict[str, dict[str, int]] = defaultdict(
        lambda: {"count": 0, "amount_cents": 0})
    for row in rows:
        currency = row["currency"]
        by_currency[currency]["count"] += 1
        by_currency[currency]["amount_cents"] += int(row.get(amount_field) or 0)
    return dict(sorted(by_currency.items()))


def _balance_totals(rows: Iterable[dict]) -> dict[str, dict[str, dict[str, int]]]:
    result: dict[str, dict[str, dict[str, int]]] = defaultdict(
        lambda: defaultdict(lambda: {
            "count": 0, "amount_cents": 0, "fee_cents": 0, "net_cents": 0,
        }))
    for row in rows:
        bucket = result[row["currency"]][row["reporting_category"]]
        bucket["count"] += 1
        bucket["amount_cents"] += int(row.get("amount_cents") or 0)
        bucket["fee_cents"] += int(row.get("fee_cents") or 0)
        bucket["net_cents"] += int(row.get("net_cents") or 0)
    return {
        currency: dict(sorted(categories.items()))
        for currency, categories in sorted(result.items())
    }


def _balance_snapshot(balance: Any) -> dict[str, dict[str, int]]:
    data = _plain(balance)
    result: dict[str, dict[str, int]] = defaultdict(
        lambda: {"available_cents": 0, "pending_cents": 0})
    for state, field in (("available", "available_cents"),
                         ("pending", "pending_cents")):
        for entry in data.get(state) or []:
            item = _plain(entry)
            result[_currency(item.get("currency"))][field] += int(
                item.get("amount") or 0)
    return dict(sorted(result.items()))


def build_stripe_revenue_receipt(
        stripe_provider: Any, start: date, end: date, record_key_secret: str) -> dict:
    """Read the live provider ledger and return a PII-free reconciliation receipt."""
    if not record_key_secret:
        raise ProviderRevenueError("record key secret is required")
    start_ts, end_exclusive_ts = _unix_window(start, end)
    created = {"gte": start_ts, "lt": end_exclusive_ts}

    sessions = list(_iter_pages(
        stripe_provider.checkout.Session.list, created=created))
    session_by_payment_intent: dict[str, dict] = {}
    session_by_subscription: dict[str, dict] = {}
    session_rows = []
    for session in sessions:
        metadata = _plain(session.get("metadata"))
        session_id = _object_id(session.get("id"))
        projection = {
            "record_key": _record_key(record_key_secret, "checkout_session", session_id),
            "payment_intent_record_key": _record_key(
                record_key_secret, "payment_intent", session.get("payment_intent")),
            "subscription_record_key": _record_key(
                record_key_secret, "subscription", session.get("subscription")),
            "customer_record_key": _record_key(
                record_key_secret, "customer", session.get("customer")),
            "created_at": _created_at(session.get("created")),
            "currency": _currency(session.get("currency")),
            "amount_total_cents": int(session.get("amount_total") or 0),
            "amount_discount_cents": int(
                _plain(session.get("total_details")).get("amount_discount") or 0),
            "amount_tax_cents": int(
                _plain(session.get("total_details")).get("amount_tax") or 0),
            "status": str(session.get("status") or "unknown")[:32],
            "payment_status": str(session.get("payment_status") or "unknown")[:32],
            "mode": str(session.get("mode") or "unknown")[:32],
            "offer_family": _offer(metadata),
            "brand": _brand(metadata),
            "livemode": bool(session.get("livemode")),
        }
        payment_intent_id = _object_id(session.get("payment_intent"))
        subscription_id = _object_id(session.get("subscription"))
        if payment_intent_id:
            session_by_payment_intent[payment_intent_id] = projection
        if subscription_id:
            session_by_subscription[subscription_id] = projection
        session_rows.append(projection)

    invoices = list(_iter_pages(stripe_provider.Invoice.list, created=created))
    invoice_by_id: dict[str, dict] = {}
    invoice_rows = []
    for invoice in invoices:
        invoice_id = _object_id(invoice.get("id"))
        subscription_id = _invoice_subscription_id(invoice)
        session = session_by_subscription.get(subscription_id, {})
        row = {
            "record_key": _record_key(record_key_secret, "invoice", invoice_id),
            "subscription_record_key": _record_key(
                record_key_secret, "subscription", subscription_id),
            "customer_record_key": _record_key(
                record_key_secret, "customer", invoice.get("customer")),
            "created_at": _created_at(invoice.get("created")),
            "currency": _currency(invoice.get("currency")),
            "status": str(invoice.get("status") or "unknown")[:32],
            "amount_due_cents": int(invoice.get("amount_due") or 0),
            "amount_paid_cents": int(invoice.get("amount_paid") or 0),
            "amount_remaining_cents": int(invoice.get("amount_remaining") or 0),
            "offer_family": session.get("offer_family", "unknown"),
            "brand": session.get("brand", "unknown"),
            "livemode": bool(invoice.get("livemode")),
        }
        invoice_by_id[invoice_id] = row
        invoice_rows.append(row)

    charge_rows = []
    for charge in _iter_pages(stripe_provider.Charge.list, created=created):
        payment_intent_id = _object_id(charge.get("payment_intent"))
        invoice_id = _object_id(charge.get("invoice"))
        session = session_by_payment_intent.get(payment_intent_id, {})
        invoice = invoice_by_id.get(invoice_id, {})
        charge_rows.append({
            "record_key": _record_key(
                record_key_secret, "charge", charge.get("id")),
            "payment_intent_record_key": _record_key(
                record_key_secret, "payment_intent", payment_intent_id),
            "invoice_record_key": _record_key(
                record_key_secret, "invoice", invoice_id),
            "customer_record_key": _record_key(
                record_key_secret, "customer", charge.get("customer")),
            "balance_transaction_record_key": _record_key(
                record_key_secret, "balance_transaction",
                charge.get("balance_transaction")),
            "created_at": _created_at(charge.get("created")),
            "currency": _currency(charge.get("currency")),
            "status": str(charge.get("status") or "unknown")[:32],
            "paid": bool(charge.get("paid")),
            "captured": bool(charge.get("captured")),
            "disputed": bool(charge.get("disputed")),
            "gross_cents": int(charge.get("amount") or 0),
            "refunded_cents": int(charge.get("amount_refunded") or 0),
            "gross_less_refunds_cents": (
                int(charge.get("amount") or 0) -
                int(charge.get("amount_refunded") or 0)),
            "offer_family": session.get(
                "offer_family", invoice.get("offer_family", "unknown")),
            "brand": session.get("brand", invoice.get("brand", "unknown")),
            "livemode": bool(charge.get("livemode")),
        })

    refund_rows = []
    for refund in _iter_pages(stripe_provider.Refund.list, created=created):
        refund_rows.append({
            "record_key": _record_key(
                record_key_secret, "refund", refund.get("id")),
            "charge_record_key": _record_key(
                record_key_secret, "charge", refund.get("charge")),
            "payment_intent_record_key": _record_key(
                record_key_secret, "payment_intent", refund.get("payment_intent")),
            "balance_transaction_record_key": _record_key(
                record_key_secret, "balance_transaction",
                refund.get("balance_transaction")),
            "created_at": _created_at(refund.get("created")),
            "currency": _currency(refund.get("currency")),
            "status": str(refund.get("status") or "unknown")[:32],
            "amount_cents": int(refund.get("amount") or 0),
        })

    balance_rows = []
    for transaction in _iter_pages(
            stripe_provider.BalanceTransaction.list, created=created):
        balance_rows.append({
            "record_key": _record_key(
                record_key_secret, "balance_transaction", transaction.get("id")),
            "source_record_key": _record_key(
                record_key_secret, "balance_source", transaction.get("source")),
            "created_at": _created_at(transaction.get("created")),
            "available_at": _created_at(transaction.get("available_on")),
            "currency": _currency(transaction.get("currency")),
            "type": str(transaction.get("type") or "unknown")[:64],
            "reporting_category": str(
                transaction.get("reporting_category") or "unknown")[:64],
            "status": str(transaction.get("status") or "unknown")[:32],
            "amount_cents": int(transaction.get("amount") or 0),
            "fee_cents": int(transaction.get("fee") or 0),
            "net_cents": int(transaction.get("net") or 0),
        })

    payout_rows = []
    for payout in _iter_pages(stripe_provider.Payout.list, created=created):
        payout_rows.append({
            "record_key": _record_key(
                record_key_secret, "payout", payout.get("id")),
            "balance_transaction_record_key": _record_key(
                record_key_secret, "balance_transaction",
                payout.get("balance_transaction")),
            "created_at": _created_at(payout.get("created")),
            "arrival_at": _created_at(payout.get("arrival_date")),
            "currency": _currency(payout.get("currency")),
            "status": str(payout.get("status") or "unknown")[:32],
            "amount_cents": int(payout.get("amount") or 0),
            "automatic": bool(payout.get("automatic")),
        })

    successful_charges = [
        row for row in charge_rows
        if row["paid"] and row["captured"] and row["status"] == "succeeded"
    ]
    succeeded_refunds = [row for row in refund_rows if row["status"] == "succeeded"]
    paid_payouts = [row for row in payout_rows if row["status"] == "paid"]
    paid_invoices = [row for row in invoice_rows if row["status"] == "paid"]

    account = _plain(stripe_provider.Account.retrieve())
    account_key = _record_key(record_key_secret, "account", account.get("id"))
    current_balance = _balance_snapshot(stripe_provider.Balance.retrieve())

    return {
        "schema": "stripe_revenue_reconciliation/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "period": {
            "start_date": start.isoformat(),
            "end_date_inclusive": end.isoformat(),
            "timezone": "UTC",
        },
        "provider": {
            "name": "stripe",
            "account_record_key": account_key,
            "charges_enabled": bool(account.get("charges_enabled")),
            "payouts_enabled": bool(account.get("payouts_enabled")),
        },
        "privacy": {
            "projection": "financial_and_offer_fields_only",
            "record_keys": "hmac_sha256_using_server_secret",
            "excluded": [
                "provider_ids", "names", "emails", "phones", "addresses",
                "payment_methods", "bank_destinations", "descriptions",
            ],
        },
        "controls": {
            "successful_charges": _totals(successful_charges, "gross_cents"),
            "succeeded_refunds": _totals(succeeded_refunds, "amount_cents"),
            "paid_payouts": _totals(paid_payouts, "amount_cents"),
            "paid_invoices": _totals(paid_invoices, "amount_paid_cents"),
            "balance_activity_by_category": _balance_totals(balance_rows),
            "current_balance": current_balance,
        },
        "rows": {
            "checkout_sessions": session_rows,
            "invoices": invoice_rows,
            "charges": charge_rows,
            "refunds": refund_rows,
            "balance_transactions": balance_rows,
            "payouts": payout_rows,
        },
        "boundaries": [
            "Provider rows are selected by each object's created timestamp.",
            "Payout arrival dates can fall outside the selected creation window.",
            "Offer attribution is unknown when provider objects lack a checkout-session link.",
            "Current balance is an observation-time control, not a period flow.",
            "Bank-statement matching is outside this receipt.",
        ],
        "side_effects": (
            "read_only_provider_list_and_retrieve_calls; no checkout, charge, "
            "refund, customer, invoice, subscription, payout, or metadata mutation"
        ),
    }
