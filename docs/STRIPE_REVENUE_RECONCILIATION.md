# Stripe revenue reconciliation

The production Railway service is the only component that owns the live
standalone Stripe credential. `POST /api/cron/stripe-reconciliation` uses that
credential for a bounded, read-only provider export without copying it into
GitHub or an operator laptop.

## Safety boundary

- Authentication uses the existing `X-Cron-Secret` contract.
- The requested inclusive UTC window is limited to 400 days.
- Provider calls are limited to list/retrieve operations for merchant products
  and prices, Checkout Sessions, invoices, charges, refunds, balance
  transactions, payouts, the account, and current balance.
- Stripe IDs and customer IDs become deterministic HMAC-SHA256 record keys.
- Customer names, emails, phones, addresses, descriptions, receipt URLs,
  payment methods, price nicknames, and bank destinations are never projected.
  Merchant-authored product names are retained to classify historical revenue.
- Known health-check/test checkout metadata becomes only a `synthetic` boolean;
  the identifying test label itself is not projected.
- The endpoint cannot create or change a checkout, charge, refund, customer,
  invoice, subscription, payout, or metadata record.

The receipt separates period flows from the observation-time current balance.
It also preserves balance activity by Stripe reporting category so charges,
refunds, disputes, adjustments, fees, and payouts are not silently collapsed
into an invented definition of revenue.

## Production run

Use the manual **Stripe Revenue Reconciliation** GitHub workflow. Its artifact
contains the complete PII-free receipt and is retained for 30 days.

```text
start_date: 2025-08-27
end_date:   2026-08-27
```

The endpoint intentionally does not prove a bank deposit. Match paid payout
record keys and amounts to the bank statement before classifying the result as
bank-settled cash.
