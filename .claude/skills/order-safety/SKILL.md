---
name: order-safety
description: Load when touching intake validation, checkout, delivery, or any customer-facing failure path — a paid order that dies is a refund and a reputation hit, not just a bug.
---

# Order Safety

This repo's NORTHSTAR line says it plainly: "reliability here IS the
business — a failed order is a refund and a reputation hit." This skill is
the scar tissue on that sentence. Read CLAUDE.md's Known Pitfalls first
(idempotency, Stripe timeout) — not repeated here. This covers the
*order-killer* class of bug: code that turns a recoverable gap into a dead
order.

## The order-killer principle

Never hard-fail an order on a field the pipeline can estimate, default, or
defer. Two war stories, both verified in this repo's history:

**(a) FTP hard-required, but the builder estimates it anyway.**
`validate_parsed_intake()` in `athletes/scripts/intake_to_plan.py` used to
require FTP in Current Fitness. On 2026-06-22 a real paying customer
(Taylor Foster, Big Sugar Gravel, `cs_live_…`) left FTP blank and the order
died at intake validation — step one — even though `build_profile()`
already estimates FTP from weight (2.5/2.2 W/kg × age factor) and schedules
a week-1 FTP test for exactly this case. Fixed in commit `dddbbfd`, then
generalized same-day in commit `d3aa314` ("Forgiving intake"): **race is
now the only hard-required intake field**; everything else (age, sex,
weight, FTP, hours) is optional with a flagged default in `build_profile()`.
The synthetic avatar fleet had the same blind spot — `synthesize_athlete.py`
always emitted the non-empty string `"unknown"` for unknown FTP, which
*passed* validation and never exercised a truly blank `""` field like a
real athlete would type; half of unknown-FTP avatars now submit `""`. New
synthetic-athlete generators must emit the blank/malformed form of a
field, not just the well-formed "I don't know" string — blank is what
actually broke production.

**(b) A silent timeout killed orders after validation passed.**
Jun 9 2026: Railway's container has no Chrome, so `pdf_generator.py` fell
back to WeasyPrint in-process with no timeout — 30+ min CPU-bound on a
shared vCPU, past the 300s pipeline timeout, worker killed, no FAILED-order
email, no retry (idempotency already marked the order processed before the
pipeline ran — see CLAUDE.md's idempotency pitfall). A real order (Jesse
Couch) needed manual recovery. Fixed same day (commit `2ab8a22`): Chromium
bundled into the image, WeasyPrint time-boxed to a 120s subprocess,
`PIPELINE_TIMEOUT` raised to 480s under gunicorn's 600s (`webhook/app.py:181`,
`athletes/scripts/pdf_generator.py:271`). Lesson: **any step between "order
accepted" and "delivered" that can hang without a timeout is an
order-killer** — correct idempotency (per CLAUDE.md) is exactly what makes
a silent hang unrecoverable, since the retry that would have saved it
never fires.

**(c) The compliance gate used to hard-fail instead of flagging.**
The block-builder's 11 CRITICAL compliance rules (CLAUDE.md) used to
hard-fail the whole order on any miss. Commit `ddd13a7` ("Safety net: never
deliver NOTHING") changed this: the gate now **delivers the built plan**,
writes `NEEDS_REVIEW.txt` into the athlete dir, banners the coaching brief,
prints `GG_NEEDS_REVIEW=1`, and the coach email subject becomes distinct
(`_build_order_email()` / `_notify_new_order()`, `webhook/app.py` ~line
339-400). The block-builder **exception** path (a crash, not a compliance
miss) still hard-fails — a crash has no plan to deliver. When a new gate
is ambiguous: if there's a built artifact, flag and deliver it; only raise
when there's nothing to hand the coach.

## Failures invisible to customer, loud to coach

Never auto-email an athlete that something broke internally. This was
tried and reverted the same day it shipped: commit `8dcc926` ("Revert
athlete failure-email — it advertised our breakage to the customer"). The
"we hit a snag, finishing by hand" email fired on every failure including
transient ones a retry would fix — so a customer could get a snag email
followed by a success email, contradictory noise — and it planted doubt
nobody had. The payment confirmation already promises "24 hours, reviewed
personally," so that buffer already covers ghosting risk. **A
customer-visible message belongs only on a genuine SLA-breach risk** (order
aging toward the promised window with nothing delivered), worded warmly,
never as an admission the automation broke.

The actual failure-notification mechanism is the coach email:
`_notify_new_order()` → `_build_order_email()` in `webhook/app.py`, sent
via `_send_email()` to `NOTIFICATION_EMAIL` (Resend API). Subject line
encodes the state: `[GG] New order` (clean), `[GG] FAILED` (no plan
produced — `product_type == 'training_plan_FAILED'`, `webhook/app.py:2398`),
or the needs-review variant (plan delivered but `GG_NEEDS_REVIEW=1` in
pipeline stdout). Route any new failure mode through this same
subject-line vocabulary rather than a new channel — the coach's triage
habit depends on exactly these three states.

## The recoverable-field checklist

Before marking any new intake field required, ask:

1. Can it be **estimated** from other answers (like FTP from weight)?
2. Can it be **defaulted with a flag** for the coach to fix later (age
   40, weight 75/62kg, hours 8 — see `build_profile()`)?
3. Can it be **collected later by reply** without blocking the build?

If any answer is yes, it is not hard-required — default/estimate it in
`build_profile()` and let `validate_profile_sanity()` bounds-check the
result instead of blocking at `validate_parsed_intake()`. Ask **"does this
field failing lose us the order, or just precision we can dial in during
week 1?"** — only race clears that bar today.

## When NOT to use this

- Pure algorithm/scoring changes inside the block-builder engine that don't
  touch what blocks an order or what a customer/coach sees on failure —
  use CLAUDE.md's block-builder pitfalls instead.
- Idempotency, Stripe timeout mechanics, Railway/Docker config, PII
  masking, rate limiting — covered in CLAUDE.md's Known Pitfalls; read
  there, don't restate here.
- Cosmetic or internal-only test failures with no path to a customer
  order (e.g., a coaching-brief formatting nit) — a real bug, not an
  order-killer.
