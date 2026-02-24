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

## Intake-to-Plan Pipeline

### Architecture Overview
```
Questionnaire (markdown)
  → intake_to_plan.py (parse + validate + build profile)
    → generate_full_package.py (9-step pipeline)
      → Step 1: validate_profile.py
      → Step 2: derive_classifications.py
      → Step 3: build_weekly_structure.py
      → Step 4: select_methodology.py (scores 13 methodologies objectively)
      → Step 5: calculate_fueling.py
      → Step 6: calculate_plan_dates.py (incl. B-race overlay)
      → Step 7: generate_athlete_package.py (ZWO files via nate_workout_generator.py)
      → Step 8: generate_html_guide.py
      → Step 9: generate_dashboard.py
    → 3 quality gates (distribution, integrity, pre-delivery)
    → coaching_brief.md
    → copy deliverables to ~/Downloads/
```

### Key Files Map
```
athletes/scripts/
├── intake_to_plan.py          ← Entry point. Parse questionnaire → run pipeline → deliver
├── generate_full_package.py   ← Pipeline orchestrator. Runs 9 steps in order
├── select_methodology.py      ← Scores 13 methodologies by objective data (hours/experience/stress)
├── generate_athlete_package.py ← ZWO workout generator. Maps methodology → Nate generator
├── nate_workout_generator.py  ← 14 training systems, workout archetypes, ZWO XML rendering
├── calculate_plan_dates.py    ← Phase assignment (base/build/peak/taper/race) + B-race overlay
├── build_weekly_structure.py  ← Day-by-day slot assignment from profile availability
├── generate_html_guide.py     ← Data-driven HTML guide (zero LLM content)
├── known_races.py             ← Single source of truth for race dates/distances
├── constants.py               ← Validation bounds, day mappings, phase definitions
├── config/methodologies.yaml  ← 13 methodology definitions with scoring parameters
└── tests/
    ├── test_intake_to_plan.py           ← 164 tests (parser, methodology, multi-athlete)
    ├── test_distribution_and_schedule.py ← 38 tests (day placement, zones, FTP)
    └── test_*.py                        ← 73 more tests (formats, validation, generation)
```

### Methodology System
- 13 methodologies defined in `config/methodologies.yaml`
- Each scored on 7 criteria: hours (±30), experience (±15), stress (±15), flexibility (±10), race demands (±15), goal type (±10), preferences (±10)
- `past_failure_with` = hard veto (-50 points)
- `METHODOLOGY_MAP` in `generate_athlete_package.py` translates YAML IDs → Nate generator IDs
- Every YAML ID must have a MAP entry (test enforced: `test_all_yaml_ids_in_methodology_map`)

### Output Deliverables
What the user gets in `~/Downloads/{athlete-id}-training-plan/`:
- `workouts/*.zwo` — all weeks, all days
- `training_guide.html` — data-driven, no LLM
- `training_guide.pdf` — requires Chrome
- `dashboard.html`
- `coaching_brief.md` — PRIVATE (coach eyes only)
- `fueling.yaml`
- `plan_summary.yaml`

### One-command usage
```bash
# From file:
python3 athletes/scripts/intake_to_plan.py --file intake.md

# From clipboard (macOS):
pbpaste | python3 athletes/scripts/intake_to_plan.py

# Dry run (parse + build profile, skip pipeline):
python3 athletes/scripts/intake_to_plan.py --file intake.md --dry-run
```

### Pipeline steps
1. Parse markdown questionnaire → flat dict
2. Validate parsed intake (required sections + fields)
3. Build profile.yaml (unit conversions, race matching, methodology derivation)
4. Validate profile sanity (FTP/weight/height/age bounds from constants.py)
5. Run 9-step pipeline (validate → derive → structure → methodology → fueling → dates → workouts → guide → dashboard)
6. Run 3 quality gates (distribution, integrity, pre-delivery)
7. Generate coaching brief (questionnaire→decision mapping table)
8. Copy deliverables to ~/Downloads/

### Known Pitfalls (Training Pipeline)

#### Intake fields must be coerced to correct types
`parse_years("4+")` used to return the string `"4+"`. `validate_profile.py` does `years_structured < 0` which throws `TypeError: '<' not supported between str and int`. ALL fields consumed by validators must be parsed to int/float at intake time. Tests: `TestBuildProfileTypes` (10 tests).

#### KNOWN_RACES must come from `known_races.py` (single source of truth)
Race data was duplicated in `intake_to_plan.py`, `test_athlete_integrity.py`, and race JSON files. When Unbound moved from June 6 to May 30, only one copy was updated. Now: `known_races.py` is the sole source. NEVER define race dates locally.

#### FTP_Test is an assessment, not a training session
FTP tests are periodic assessments that skew zone distribution counts. They're excluded from distribution validation via `EXCLUDED_PREFIXES` in `validate_workout_distribution.py` (alongside RACE_DAY and Strength). If you add a new non-training workout type, add it to `EXCLUDED_PREFIXES`.

#### FTP_Test must NEVER land on the long ride day
The long ride is the single most important workout in a polarized plan. `get_ftp_day_candidates()` explicitly excludes `long_day_abbrev` and then prefers key days sorted by max_duration descending. Without this exclusion, Sunday (600min, key) outranks Saturday (240min, key) and the FTP test eats the long ride — losing 2 of 12 long rides. Test: `TestFTPTestPlacement.test_ftp_never_on_long_day` + `test_every_base_build_peak_week_has_long_ride`.

#### Weight unit detection: the 100-threshold rule
No unit specified: value > 100 → assume lbs and convert; value 40-100 → assume kg; value < 40 → keep raw (sanity check will catch it with "Was the unit lbs?" message). Explicit "kg" or "lbs" in string always wins.

#### Quality day derivation must be dynamic
`quality_days` and `easy_days` were hardcoded as `['Mon','Wed','Thu','Fri']` and `['Tue','Sun']`. This assumed Sat=long day. Any athlete with Sun long day got Saturday as a stealth 5th quality day with VO2max every week. Now derived dynamically from profile availability.

#### Polarized cycle must use key_positions, not position 0
`cycle == 0` puts intensity on the first quality day (Monday), but Monday may not be `is_key_day_ok`. Intensity must land on `key_positions[0]` and `key_positions[1]`.

#### Taper phase is NOT all-intensity
Original code: all quality days in taper = VO2max openers. Taper should have exactly 1 opener at kp0, rest Easy. A taper that's 100% intensity is a build week in disguise.

#### Section heading normalization
The intake parser normalizes `"## Recovery & Baselines"` → `recovery` and similar variations. If you add a new questionnaire section, add the mapping to `_normalize_section_name()` in `intake_to_plan.py`. Tests: `TestParseIntakeMarkdown.test_handles_alternate_section_headings`.

#### Validation bounds are defined in constants.py
`FTP_MIN_WATTS=50`, `FTP_MAX_WATTS=500`, `WEIGHT_MIN_KG=40`, `WEIGHT_MAX_KG=150`, `AGE_MIN=16`, `AGE_MAX=100`. The intake validator imports these. If you change bounds in constants.py, the intake sanity checks update automatically.

#### Methodology is selected by objective data, NOT free text
`select_methodology.py` scores all 13 methodologies based on hours, experience, stress, race demands, goal type, and special conditions (masters, injury). `_derive_methodology()` in `intake_to_plan.py` does NOT set preference scores — all stay neutral at 3. It only extracts explicit exclusions: "sweet spot didn't work" → `past_failure_with` → hard veto (-50 points). Tests: `TestMethodologySelection` (15 tests).

#### METHODOLOGY_MAP keys must match YAML keys
`generate_athlete_package.py` has `METHODOLOGY_MAP` that translates `select_methodology.py` IDs to Nate generator names. The MAP keys must exactly match `config/methodologies.yaml` keys (e.g., `polarized_80_20`, not `polarized`). Wrong keys silently fall through to `'POLARIZED'` default. Tests: `TestMethodologySelection.test_all_yaml_ids_in_methodology_map`.

#### All 13 methodologies must be in both YAML and METHODOLOGY_MAP
Adding a methodology to `config/methodologies.yaml` without a METHODOLOGY_MAP entry means it can be selected but generates wrong workouts. Adding a MAP entry without a YAML entry means it can never be selected. Test: `test_all_yaml_methodologies_scored` + `test_all_yaml_ids_in_methodology_map`.

#### B-race periodization: overlay, not override
B-races (priority B events from `b_events` in profile) get a mini-taper overlay on the existing phase. Race day → RACE_DAY ZWO. Day before → Openers (40min cap). In build/peak phases, 2 days before → Easy (45min cap). The week's phase stays unchanged (base/build/peak). B-race logic fires before FTP test injection, so FTP tests on B-race day are naturally displaced.

#### Dashboard and PDF failures must be visible
`copy_to_downloads()` prints a DELIVERY SUMMARY at the end showing [OK] and [MISS] items. Dashboard missing = ERROR (not warning). PDF missing = ERROR with "install Google Chrome" message. Both tracked in `delivery_gaps` list.

## Testing (Training Pipeline)
```bash
# Full test suite (includes webhook + pipeline tests):
python3 -m pytest athletes/scripts/ -v

# Just intake parser tests:
python3 -m pytest athletes/scripts/test_intake_to_plan.py -v

# Just distribution/schedule tests:
python3 -m pytest athletes/scripts/test_distribution_and_schedule.py -v
```
275 tests: 164 intake parser + methodology + multi-athlete, 38 distribution/schedule, 7 generation pipeline, 1 custom guide, 13 plan dates, 4 pre-plan workouts, 13 validation, 15 workout generation, 6 workout library, 12 ZWO format, 1 all-files.
