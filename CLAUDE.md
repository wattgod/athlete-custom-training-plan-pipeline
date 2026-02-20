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

## Testing
```bash
python3 -m pytest webhook/tests/test_webhook.py -v
```
98 tests: health, validation, WooCommerce, Stripe, coaching checkout (incl. setup fee + promo codes), consulting checkout, coaching webhook, consulting webhook, intake storage, price computation, Python/JS parity, past date rejection, email masking, notification, idempotency timing, checkout recovery, follow-up emails.

## Pending Work
- [ ] Rotate Stripe secret key (exposed in conversation)
- [ ] Create coaching setup fee product + price + coupon + promo code in LIVE mode (currently test mode only — update `COACHING_SETUP_FEE_PRICE_ID` in app.py)
- [ ] Update Stripe webhook endpoint to also listen for `checkout.session.expired` events
- [ ] Set up SMTP env vars in Railway (NOTIFICATION_EMAIL + SMTP_* + CRON_SECRET)
- [ ] Set up daily cron to call `/api/cron/followup-emails` (cron-job.org or Railway cron)
- [ ] Create success/cancel pages in WordPress: `/coaching/welcome/`, `/consulting/confirmed/`, `/consulting/`
- [ ] Custom domain (replace long Railway subdomain)
- [ ] Add rate limiting to checkout endpoints (Flask-Limiter)
- [ ] Consider async pipeline execution to avoid Stripe timeout retries
- [ ] Deploy updated training-plans HTML pages to WordPress (paste into Custom HTML blocks)
