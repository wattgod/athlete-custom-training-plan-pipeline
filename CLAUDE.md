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

### Rate limiting
Flask-Limiter is configured with per-IP limits (20/min checkout endpoints, 60/min webhook, 5/min cron). Uses `X-Forwarded-For` header on Railway proxy. Storage is in-memory (`memory://`) — resets on deploy. If you need persistent rate limiting, switch to Redis.

### Automatic tax
`ENABLE_AUTOMATIC_TAX` env var (default: off). Set to `true` in Railway after configuring Stripe Tax. Adds `automatic_tax={'enabled': True}` to all checkout sessions.

### Cross-repo dependency
The coaching PAGE lives in `gravel-race-automation` but the checkout BACKEND lives here. Stripe prices are created by `gravel-race-automation/scripts/create_stripe_products.py` but consumed by `webhook/app.py`. Changes to pricing must update BOTH repos. No automated parity test exists yet.

### `create_stripe_products.py` is documentation, not idempotent
The script in `gravel-race-automation` documents the Stripe product structure. Running it creates NEW products/prices (Stripe prices are immutable). It does NOT update existing prices. When changing billing intervals or amounts, create new prices via Dashboard, update the hardcoded IDs in `app.py`, and update the script to match.

## Testing
```bash
python3 -m pytest webhook/tests/test_webhook.py -v
```
114 tests: health, validation, WooCommerce, Stripe, coaching checkout (setup fee on ALL tiers + promo codes + success URL), consulting checkout, coaching webhook, consulting webhook, intake storage, price computation, Python/JS parity, past date rejection, email masking, PII compliance, notification, idempotency timing, checkout recovery, follow-up emails, rate limiting, customer creation, coaching enhancements, log order schema, expired checkout idempotency.

## Quality Gate Tests (prevent regressions)
- `TestSetupFeeAllTiers` — setup fee on every tier, correct price ID
- `TestPIIMasking` — no raw emails in logs, no "month" in recovery emails
- `TestCoachingSuccessUrl` — success URL includes session_id for GA4
- `TestExpiredCheckoutIdempotency` — duplicate expired events caught, returns 200 on error
- `TestCustomerCreation` — training plan + consulting include `customer_creation='always'`
- `TestCoachingCheckoutEnhancements` — phone_number_collection + subscription_data.metadata present
- `TestLogOrderSchema` — log entries include email, name, product_type fields
- `TestFollowupReadsCorrectLogFiles` — reads YYYY-MM.jsonl, skips failed orders
- `TestRateLimiting` — limiter exists on app, checkout endpoints have rate limit decorators
- Coaching-side `TestCssTokenValidation` — every var(--gg-*) must be defined in tokens.css
- Coaching-side `TestAccessibility` — FAQ aria-expanded reset, no "/MO" in billing

## Pending Work
- [x] Set up SMTP env vars in Railway — NOTIFICATION_EMAIL, SMTP_HOST, SMTP_PORT, SMTP_USER, CRON_SECRET all configured
- [ ] Add `SMTP_PASS` to Railway (Gmail App Password from https://myaccount.google.com/apppasswords)
- [ ] Set up daily cron to call `/api/cron/followup-emails` (needs external service — Railway cron restarts entire container)
- [ ] Enable `ENABLE_AUTOMATIC_TAX=true` in Railway (requires Stripe Tax account setup first)
- [ ] Set up Stripe Customer Portal for subscription management
- [ ] Custom domain (replace long Railway subdomain)
- [ ] Consider async pipeline execution to avoid Stripe timeout retries
- [ ] Rotate Stripe secret key (current key was exposed in Playwriter session)
