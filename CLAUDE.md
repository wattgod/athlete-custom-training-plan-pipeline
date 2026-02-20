# Athlete Custom Training Plan Pipeline

## Project Structure
```
webhook/
  app.py           <- Flask webhook server (Stripe + WooCommerce)
  Dockerfile       <- Docker build (expects repo root as context)
  requirements.txt
  tests/
    test_webhook.py <- 98 tests
athletes/
  scripts/         <- Pipeline scripts (generate_full_package.py)
railway.json       <- Railway deploy config (root, NOT webhook/)
```

## Railway Deployment
- **Project**: gravel-god-services
- **Service**: stripe-webhook
- **Domain**: `athlete-custom-training-plan-pipeline-production.up.railway.app`
- **Builder**: Dockerfile at `webhook/Dockerfile`
- **Root directory**: MUST be repo root (not `/webhook`) -- Dockerfile COPYs both `webhook/` and `athletes/`
- **Auto-deploy**: pushes to `main` trigger redeploy

## Required Environment Variables (Railway)
- `STRIPE_SECRET_KEY` -- Stripe live secret key
- `STRIPE_WEBHOOK_SECRET` -- Stripe webhook endpoint signing secret
- `FLASK_ENV=production` -- Set in Dockerfile, enables production guards
- `CRON_SECRET` -- Secret for `/api/cron/followup-emails` endpoint
- Optional: `NOTIFICATION_EMAIL`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS` -- for email notifications + follow-up sequence

## Stripe Products
- **Training plans**: 14 pre-built prices ($60-$249, keyed by weeks 4-17+)
- **Coaching**: 3 subscription prices (min=$199/4wk, mid=$299/4wk, max=$1,200/4wk)
- **Coaching setup fee**: $99 one-time, added as second line item to all coaching checkouts
- **Setup fee waiver**: Coupon "Waive Setup Fee" + promo code `NOSETUP` ($99 off, applies to setup fee product only)
- **Consulting**: 1 per-hour price ($150/hr, quantity=hours)
- **Price IDs**: Hardcoded in `app.py` lines 73-108, created by `scripts/create_stripe_products.py`
- **Webhook endpoint**: `we_1T2gDcLoaHDbEqSqb5sp6Tfj`, listens for `checkout.session.completed` + `checkout.session.expired`

## Checkout Features
- **Apple Pay / Google Pay**: Auto-enabled (no `payment_method_types` restriction)
- **Abandoned cart recovery**: 60-min expiry, Stripe-native recovery URL, consent collection, recovery email on `checkout.session.expired`
- **Session tracking**: Success URLs include `?session_id={CHECKOUT_SESSION_ID}` for GA4 attribution
- **GA4 funnel**: `begin_checkout` -> Stripe -> `purchase` (with dedup via sessionStorage)
- **Post-purchase emails**: Day 1 (getting started), Day 3 (check-in), Day 7 (coaching cross-sell). Triggered via `/api/cron/followup-emails` daily endpoint.

## Known Pitfalls

### Idempotency: mark BEFORE long operations
`mark_order_processed()` MUST run BEFORE `run_pipeline()`. The pipeline takes up to 5 minutes. Stripe retries webhooks after ~20s timeout. If marking happens after the pipeline, retries pass the idempotency check and start duplicate pipelines. The TOCTOU window is real.

### Railway railway.json: only ONE file at repo root
Railway uses the root `railway.json`. Delete any `webhook/railway.json` -- it's a stale duplicate with wrong paths that confuses contributors. The Dockerfile path must be `webhook/Dockerfile` (relative to repo root).

### Railway $PORT variable
Railway injects `$PORT` as an environment variable, but it doesn't interpolate in `startCommand` strings in railway.json. Hardcode the port in the Dockerfile CMD instead (`0.0.0.0:8080`). Railway maps its dynamic port to the container's exposed port.

### STRIPE_WEBHOOK_SECRET on first deploy
The webhook secret doesn't exist until after the webhook endpoint is registered in Stripe. The app must start without it (warn, don't crash). Add the secret as an env var after endpoint registration.

### PII in logs
Never log raw email addresses. Use `_mask_email()` for all log output. Railway logs persist and are accessible to anyone with project access.

### Stripe Checkout timeout
The pipeline runs synchronously and takes up to 5 minutes. Stripe expects 2xx within 20 seconds. The response will be late, and Stripe will mark it as "failed" and retry. Retries are caught by idempotency, so processing is correct. But the Stripe dashboard will show failed delivery attempts. Future improvement: run pipeline in a background thread or job queue.

### Price parity timezone edge case
JS `new Date()` uses browser timezone, Python `date.today()` uses server timezone (UTC on Railway). At midnight boundaries, week counts can differ by 1. The parity test runs both in the same timezone so it doesn't catch this. Real-world impact is low ($15 difference at week boundaries).

### Docker build context
The Dockerfile copies `webhook/` and `athletes/` from repo root. If Railway's root directory is set to `/webhook`, the build context is restricted and `COPY athletes/` fails. Always keep root directory empty/unset.

### Billing interval: every 4 weeks, NOT monthly
Coaching subscriptions bill every 4 weeks (13 cycles/year), NOT monthly (12 cycles/year). The Stripe prices use `interval=week, interval_count=4`. Never use "monthly", "/mo", or "per month" in customer-facing copy. Tests enforce this: `TestPIIMasking.test_no_month_in_recovery_emails` and coaching-side `TestAccessibility.test_no_month_in_billing_context`.

### CSS tokens must exist before use
Never guess a CSS token name (e.g., `--gg-font-size-3xs`). Always check `gravel-god-brand/tokens/tokens.css` first. Undefined `var()` references silently inherit from the parent element. The coaching test `TestCssTokenValidation.test_all_var_refs_defined` catches this by checking every `var(--gg-*)` in coaching CSS against the actual token definitions.

### Setup fee on ALL tiers
The $99 setup fee must be tested on every coaching tier, not just `min`. `TestSetupFeeAllTiers.test_setup_fee_on_every_tier` verifies all 3 tiers have exactly 2 line items.

### Follow-up email log path mismatch (KNOWN BUG)
`process_followup_emails()` reads from `orders.jsonl` but `log_order()` writes to `YYYY-MM.jsonl`. The follow-up email system is non-functional until this is fixed. The test suite uses synthetic data that masks this bug.

### Expired checkout handler: no idempotency
`_handle_checkout_expired` returns 500 on error, causing Stripe to retry. There's no idempotency guard on expired events, so recovery emails can be sent multiple times. Fix: add idempotency tracking or return 200 on error.

### Cross-repo dependency
The coaching PAGE lives in `gravel-race-automation` but the checkout BACKEND lives here. Stripe prices are created by `gravel-race-automation/scripts/create_stripe_products.py` but consumed by `webhook/app.py`. Changes to pricing must update BOTH repos. No automated parity test exists yet.

### `create_stripe_products.py` is documentation, not idempotent
The script in `gravel-race-automation` documents the Stripe product structure. Running it creates NEW products/prices (Stripe prices are immutable). It does NOT update existing prices. When changing billing intervals or amounts, create new prices via Dashboard, update the hardcoded IDs in `app.py`, and update the script to match.

## Testing
```bash
python3 -m pytest webhook/tests/test_webhook.py -v
```
103 tests: health, validation, WooCommerce, Stripe, coaching checkout (setup fee on ALL tiers + promo codes + success URL), consulting checkout, coaching webhook, consulting webhook, intake storage, price computation, Python/JS parity, past date rejection, email masking, PII compliance, notification, idempotency timing, checkout recovery, follow-up emails.

## Quality Gate Tests (prevent regressions)
- `TestSetupFeeAllTiers` — setup fee on every tier, correct price ID
- `TestPIIMasking` — no raw emails in logs, no "month" in recovery emails
- `TestCoachingSuccessUrl` — success URL includes session_id for GA4
- Coaching-side `TestCssTokenValidation` — every var(--gg-*) must be defined in tokens.css
- Coaching-side `TestAccessibility` — FAQ aria-expanded reset, no "/MO" in billing

## Pending Work
- [ ] **FIX: Follow-up email log path** — `process_followup_emails()` reads wrong file (orders.jsonl vs YYYY-MM.jsonl) and expects wrong schema
- [ ] Set up SMTP env vars in Railway (NOTIFICATION_EMAIL + SMTP_* + CRON_SECRET)
- [ ] Set up daily cron to call `/api/cron/followup-emails` (after log path fix)
- [ ] Create success/cancel pages in WordPress: `/coaching/welcome/`, `/consulting/confirmed/`, `/consulting/`
- [ ] Add rate limiting to checkout endpoints (Flask-Limiter)
- [ ] Enable `automatic_tax` on all checkout sessions (requires Stripe Tax setup)
- [ ] Add `customer_creation='always'` to training plan + consulting checkouts
- [ ] Add `phone_number_collection` to coaching checkout
- [ ] Add `subscription_data.metadata` to coaching checkout (tier, athlete name)
- [ ] Set up Stripe Customer Portal for subscription management
- [ ] Custom domain (replace long Railway subdomain)
- [ ] Add idempotency to expired checkout handler
- [ ] Consider async pipeline execution to avoid Stripe timeout retries
