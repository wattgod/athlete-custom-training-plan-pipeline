# Coaching onboarding pipeline

## Purpose

One onboarding contract serves Gravel God, Roadie Labs, and XC Ski Labs without
mixing brand identity, coaching tier names, TrainingPeaks benefits, or Stripe
state. Public application is not acceptance.

## Flow

1. A brand form posts to the `coaching-intake` Cloudflare Worker.
2. The Worker derives the brand from the page origin, validates name/email/tier
   and honeypot, generates a UUID submission receipt, and forwards the payload
   to `POST /api/coaching-intakes` with `X-Coaching-Intake-Secret`.
3. Railway creates `coaching_onboarding_case/v1` in `FIT_REVIEW`. Duplicate
   submission IDs return the existing case and do not resend email. Every case
   includes `coaching_intake_audit/v1`, which keeps three review queues
   separate:
   - required form answers that are missing (`missing_required`);
   - useful, optional answers that are asked but blank (`missing_followup`);
   - facts deliberately not collected on the public form (`unasked`);
   - athlete-reported or platform/payment facts that remain unverified.
4. The athlete receives a receipt. The coach receives the case ID and approval
   command. The full case is available only through the authenticated
   `GET /api/coaching-intakes/{case_id}` operator endpoint. No checkout exists
   yet.
5. `POST /api/coaching-intakes/{case_id}/approve`, authenticated with
   `X-Cron-Secret`, records only coach fit approval. It does not create a
   checkout and does not treat the application as acceptance.
6. `POST /api/coaching-intakes/{case_id}/verify` records one allowlisted,
   operator-authenticated evidence receipt. Identity, health-clearance
   disposition, signed coaching agreement, and signed data consent must all be
   present. Agreement and consent receipts require both a document version and
   a receipt ID; a clinician-cleared health gate requires its receipt ID.
   Athlete answers never self-verify these gates. Re-verification updates the
   current gate but appends an immutable history entry for audit.
   For athletes age 13–17, a separate `guardian_consent` receipt is also
   required. Guardian contact fields on the intake are routing information,
   not consent. This intake rejects athletes under 13.
7. `POST /api/coaching-intakes/{case_id}/payment-handoff` creates one
   60-minute Stripe Checkout only when every pre-payment gate passes and a live
   Stripe readback confirms the selected tier amount, four-week cadence, $99
   one-time setup fee, and the private fixed-$99 waiver coupon. It sends
   one brand-specific handoff containing:
   - conditional TrainingPeaks attachment instructions;
   - the live Stripe checkout URL;
   - a statement that the $99 setup fee is included by default, or that a
     coach-approved case-specific waiver is already reflected in checkout;
   - the correct Min/Mid/Max coaching tier name;
   - a separate statement that TrainingPeaks Premium is included.
8. Stripe `checkout.session.completed` advances the same case to
   `PLATFORM_SETUP`, stores the payment/subscription receipt, sends the normal
   payment confirmation, and notifies the coach.
   If the session expires first, Stripe's recovery URL is used only when the
   athlete opted into promotional email. Recovery is case-bound, limited to
   one email per onboarding case, and suppressed after payment or whenever the
   case is no longer `PAYMENT_PENDING`. A recovered Checkout Session must point
   back to the exact session created by the approved handoff.
   Later `invoice.paid`, `invoice.payment_failed`,
   `invoice.payment_action_required`, `customer.subscription.updated`,
   `customer.subscription.deleted`, `customer.subscription.paused`, and
   `customer.subscription.resumed` events update the case-bound billing record
   idempotently. Delinquent, paused, or ended billing blocks plan release
   instead of leaving stale `ACTIVE` status. These events alert the operator
   but never email the athlete.
9. After `athlete_context = sealed` records the canonical `athlete_id`, the
   authenticated `POST /api/coaching-intakes/{case_id}/onboarding-materials`
   operation creates `coaching_welcome.html` and the privacy-minimized
   `coaching_onboarding.yaml`. It requires confirmed payment, all pre-payment
   evidence gates, any minor guardian receipt, and a verified HTTPS
   `COACHING_BOOKING_URL`. If the custom training guide already exists, the
   same chapter is injected idempotently; otherwise the canonical guide builder
   adds it when the first approved guide is generated. The operation sends the
   same privacy-minimized operating guide by email; for a minor, both athlete
   and guardian delivery must succeed.
   `onboarding_materials = ready` is derived from successful delivery, not file
   generation alone, and is a release prerequisite, so an
   approved plan cannot be marked athlete-release-ready without this package.
10. The daily `POST /api/cron/coaching-onboarding-reminders` operation creates
    deduplicated day 0/2/7/14/28 suggestions in the coach review queue. It never
    sends a communication; every suggestion requires coach approval.
11. Existing athletes enter through the private
    `POST /api/coaching-intakes/legacy-repaper` operator route. The import is
    idempotent by canonical `athlete_key`, creates a real UUID case, and records
    the review-workbook source. It never sends email or a SignWell packet,
    creates checkout, changes payment, or treats roster membership as verified
    identity, age, jurisdiction, guardian authority, or health disposition.
    `PATCH /api/coaching-intakes/{case_id}/legacy-source` can correct only the
    bound review-workbook pointer; it cannot change athlete identity.

## Operator and billing controls

- `GET /api/coaching-intakes` is the authenticated cross-brand work queue. It
  returns the canonical athlete key, identity, source type, current state, next
  action, e-sign document/status, billing standing, and reminder count, but not
  questionnaire answers.
- `GET /api/coaching-intakes/{case_id}/esign-readiness` exposes only missing
  configuration and adapter status. It never issues documents. The
  provider-neutral payload contract is
  `schemas/coaching_esign_packet_v1.schema.json`.
- `POST /api/coaching-intakes/{case_id}/esign-packet` is the authenticated,
  operator-controlled SignWell send. It is idempotent by provider document ID,
  uses SignWell's email delivery and email passcode, disables signer
  reassignment, and keeps provider reminders off unless deliberately enabled.
  It sends a non-embedded packet only after fit, identity, and health gates are
  complete. It never returns a signing URL or places questionnaire/health data
  in SignWell metadata.
- `POST /webhook/signwell` verifies SignWell's event HMAC. A completion event
  does not prove completion by itself: the backend reads the document back from
  SignWell, checks the case, exact template IDs, test/live mode, all signer
  emails, and all signer statuses, then retrieves the completed PDF with audit
  page. Only that verified live result records agreement/consent receipts. Test
  documents are retained as test evidence but have no legal effect.
- `POST /api/coaching-intakes/{case_id}/billing-portal` creates a short-lived,
  case-bound Stripe portal session. `mode=manage` opens the configured portal;
  `mode=cancel` opens cancellation for the recorded subscription. The URL is
  returned only to the operator and is never stored or emailed. Authenticate
  the athlete before handing it over.
- Stripe Portal must allow cancellation and payment-method updates. Stripe
  webhook readback updates the case after any portal action.

## Brand gates

The authoritative settings live in `athletes/config/brands.yaml`.

- `gravelgod`, `roadielabs`, and `xcskilabs`: coaching enabled with the same
  Min/Mid/Max tier names, $199/$299/$1,200 four-week prices, TrainingPeaks
  attachment flow, included TrainingPeaks Premium, $99 setup fee, and private
  case-specific waiver path.
- `billing_period_days: 28` is the canonical cadence. Public copy must say
  “four weeks,” not “monthly.”
- All coaching checkouts use the shared Endurance Labs Stripe merchant account;
  the session metadata records the originating brand for reporting, receipts,
  email, success URL, and webhook handling.
- XC Ski Labs automated custom-plan generation is a separate capability gate
  and remains disabled until its ski-specific workout and zone adaptation is
  release-ready. This does not disable XC Ski Labs coaching or consulting.

Unknown and disabled brands fail closed. A browser-provided `brand` value is
never trusted; the Worker derives it from the Origin hostname.

The legacy public `POST /api/create-coaching-checkout` path is disabled by
default. `COACHING_DIRECT_CHECKOUT_ENABLED=true` is rollback-only because that
route bypasses fit, identity, health, agreement, and consent gates.

## Legal and e-sign activation

The owner reported qualified-counsel approval on 2026-08-26. The immutable
approval receipt is `coaching_legal_approval_receipt/v1`; any content change
requires a new artifact hash, version, and approval receipt. Three operative
SignWell templates are active: the coaching services agreement, privacy/data
consent, and minor/guardian addendum. Provider document IDs, versions, signer
receipts, completion timestamps, the signed-PDF hash, and its private storage
pointer belong on the case. The signed PDF itself must never enter Git or a
broad Google Sheet.

SignWell is the canonical e-sign adapter. The integration boundary fails
closed: no packet can be issued without the API key, webhook ID, UUID template
IDs, immutable document versions, and a real legal-approval receipt. Production
also requires the explicit live-send switch and forbids test mode. Completed
PDFs and their SHA-256 hashes are stored on the private persistent volume under
`coaching_esign/{case_id}/`; signed documents must never be committed to Git.
`manual_receipt` remains an operator-only recovery path for already-executed,
independently verified documents, not the normal onboarding flow.

The live brand privacy disclosures name the active Cloudflare/Railway intake
path and private handling of training and optional health data. Any processor,
purpose, or retention change requires a matching disclosure/version review.

## Required deployment configuration

Use the same randomly generated value in both places:

- Cloudflare Worker secret: `COACHING_INTAKE_SECRET`
- Railway environment variable: `COACHING_INTAKE_SECRET`

Existing Railway values still required: `CRON_SECRET`, `RESEND_API_KEY`,
`NOTIFICATION_EMAIL`, Stripe keys, and brand sender configuration.
`COACHING_BOOKING_URL` must be a verified HTTPS URL before athlete onboarding
materials can be generated. `COACHING_SETUP_FEE_WAIVER_COUPON_ID` defaults to
the provider-verified fixed-$99 coupon ID.

Legal/e-sign configuration (do not set placeholders):

- `COACHING_ESIGN_PROVIDER=signwell`
- `COACHING_LEGAL_APPROVAL_RECEIPT`
- `COACHING_AGREEMENT_TEMPLATE_ID` and
  `COACHING_AGREEMENT_TEMPLATE_VERSION`
- `COACHING_DATA_CONSENT_TEMPLATE_ID` and
  `COACHING_DATA_CONSENT_TEMPLATE_VERSION`
- for minors, `COACHING_GUARDIAN_CONSENT_TEMPLATE_ID` and
  `COACHING_GUARDIAN_CONSENT_TEMPLATE_VERSION`
- `SIGNWELL_API_KEY`
- `SIGNWELL_WEBHOOK_ID` for the webhook registered to
  `https://{railway-host}/webhook/signwell`
- staging: `SIGNWELL_TEST_MODE=true` and
  `SIGNWELL_LIVE_SEND_ENABLED=false`
- production, only after the activation audit:
  `SIGNWELL_TEST_MODE=false` and `SIGNWELL_LIVE_SEND_ENABLED=true`
- recommended defaults: `SIGNWELL_REMINDERS_ENABLED=false`; optional
  `SIGNWELL_REQUESTER_EMAIL`, `SIGNWELL_ATHLETE_PLACEHOLDER`, and
  `SIGNWELL_GUARDIAN_PLACEHOLDER` must match the approved SignWell templates

Daily monitoring additionally requires:

- Cloudflare Worker secret: `COACHING_CANARY_SECRET`
- GitHub Actions repository secret: `COACHING_CANARY_SECRET` (same value)
- all three brand-specific GA4 Measurement Protocol IDs/secrets on Railway;
  missing analytics for any brand intentionally fails the coaching canary.

The daily backend canary also checks complete SignWell configuration and makes
an authenticated, read-only `/me` request. It never creates a signature packet.

Deployment order matters:

1. Deploy Railway backend with the new endpoint and secret.
2. Deploy the `coaching-intake` Worker with the matching secret.
3. Smoke-test a synthetic intake from the brand origin, record synthetic gate
   receipts, and exercise payment handoff using Stripe test mode or a fully
   mocked local server.
4. Deploy the brand form last.

Until all three steps pass, keep the existing live form unchanged. Never deploy
the form first: it would point athletes at a Worker/backend contract that is not
ready.

### Activation audit — 2026-08-26

Production is active. Railway, Stripe lifecycle webhooks/portal, SignWell live
templates/webhook, brand analytics, booking URL, public forms, exact-origin
CORS, Cloudflare Worker, persistent volume, and daily cron are configured. The
GitHub and Worker canary secrets were rotated together on 2026-08-26; manual
workflow run `33002552283` passed every checkout, public-page, edge/provider,
storage, and configuration check. The legacy roster now has 21 unique,
UUID-bound cases in `IDENTITY_REVIEW`; zero signature packets were sent during
migration.

The remaining operational gates are athlete-specific, not activation gaps:
verify each legal identity, age/adult status, jurisdiction, health-clearance
disposition, and exact recipient. Ari additionally requires verified guardian
identity, authority, and email. SignWell automatic reminders remain disabled
until a deliberate cadence and exception/escalation policy is approved.

## Operational notes

- Checkout creation is idempotent per case; retrying payment handoff resends a failed
  handoff using the existing URL instead of creating another session.
- The 2026-08-25 provider audit found that the original live `NOSETUP` code was
  an unrestricted 100%-off-once coupon. It had zero redemptions and was
  deactivated. A later fixed-$99 `NOSETUP` promotion code was also deactivated
  with zero redemptions after the owner chose private case-by-case waivers.
  The fixed $99 USD, once-only coupon remains valid for backend-only automatic
  application; payment handoff fails closed if that contract or any live tier
  price drifts.
- `coaching_onboarding_materials.py` creates a privacy-minimized standalone
  welcome guide after fit, identity, health, agreement, consent, payment, and
  any guardian gate pass. The canonical training-guide builder embeds the same
  chapter when `coaching_onboarding.yaml` is present; it never changes the
  training prescription.
- The included `coaching-start` course is the preferred operational guide. It
  is invite-only, unlisted from the public course catalog, and has seven
  ordered lessons covering the coach/athlete loop, TrainingPeaks setup,
  reading the plan, useful comments, calls and urgent channels, health/recovery
  boundaries, and the first 30 days. Normal enrollment requires signed terms,
  data consent, and confirmed payment. The sole owner may exercise an explicit,
  audited owner-pilot exemption tied to the configured notification email; the
  exemption never appears in public checkout and cannot be used for an athlete.
- Course enrollment is bound in Cloudflare D1 to the canonical `case_id` and
  `athlete_key`. New lesson completions sync a privacy-minimized receipt—course,
  lesson, counts, percent, event ID—back to Railway. The sync carries no email,
  health data, questionnaire text, or performance data and is idempotent.
  Course completion is educational evidence only: it cannot satisfy identity,
  health, agreement, consent, payment, TrainingPeaks, plan-approval, or release
  gates.
- Personalized course copy may use first/preferred name, brand, tier,
  discipline, and a short goal label. Private health facts, training metrics,
  free-text intake answers, and plan details remain in the case/athlete record
  and must never be embedded in static course HTML.
- The full questionnaire is private health/performance data. Case files are
  written mode `0600` under the Railway persistent volume and must not be
  committed to Git or copied into broad operational surfaces.
- Platform connection remains a verification gate. The email says “if not
  already connected” because neither Stripe nor intake submission proves the
  TrainingPeaks relationship.
- The audit marks terms/signature, data consent, clinician clearance,
  TrainingPeaks connection, Premium activation, payment, and plan release as
  distinct gates. It does not pretend that an intake answer proves any of them.
- Terms/signature and clinician-clearance collection are not automated here.
  They remain required when applicable before athlete-facing plan release; use
  only approved agreement language and clinician clearance, never form-invented
  legal or medical claims.

## Analytics and abandoned-checkout operations

Two analytics layers serve different purposes:

- Consent-aware GA4 events measure page behavior:
  `coaching_page_view`, CTA/scroll/FAQ events, and
  `coaching_apply_started`, `coaching_apply_submitted`, and
  `coaching_apply_error`.
- Each private onboarding case contains idempotent
  `coaching_funnel_event/v1` lifecycle receipts. These contain brand, tier,
  canonical event name, timestamp, and hashed source receipt only—never athlete name,
  email, questionnaire answers, recovery URL, or free text. This durable case
  ledger is the conversion source of truth when cookies, consent, ad blockers,
  or browser retries make GA4 incomplete.

The authenticated `GET /api/coaching-funnel-report?days=30` endpoint returns
aggregate stage counts, conversion percentages, abandoned/recovered checkout
counts, billing-healthy/attention/ended counts, and median
application-to-payment/active times by brand and tier. It never returns case
IDs or athlete PII. Legacy re-papering is reported in a separate aggregate and
is excluded from acquisition/application conversion. The same aggregate is embedded in authenticated
`GET /api/intel-stats?hours=24` output for the Morning Intel consumer.

Stripe Checkout expires after 60 minutes with native recovery enabled. The
`checkout.session.expired` webhook records the expiration even when no email
can be sent. It sends a recovery email only with Stripe promotional consent,
records delivery success/failure on the case, and will not send a second case
recovery. `checkout.session.completed` records whether payment came through a
Stripe-recovered session.

## Daily canary and incident response

`.github/workflows/daily-checkout-health.yml` runs at 13:00 UTC and must fail
loudly when any onboarding rail drifts. It:

1. loads the public coaching, application, and welcome pages for all brands;
2. verifies the application pages still contain the stable submission-ID and
   shared Worker contracts;
3. calls the authenticated Worker `POST /__canary`, proving the public edge can
   reach Railway;
4. asks Railway to read back every live Min/Mid/Max price, four-week cadence,
   $99 setup fee, private waiver coupon, the full Checkout/recurring webhook
   subscription, and an active Stripe Customer Portal configuration with
   cancellation and payment-method update enabled;
5. verifies brand analytics, email, booking-link, and secret configuration;
6. performs a disposable write/read/delete on the persistent volume and keeps
   a privacy-safe canary receipt under `.canary/coaching/`; and
7. uploads the response as a 30-day GitHub Actions artifact.

The canary creates no athlete case, Checkout Session, charge, email, or
TrainingPeaks write. A failed scheduled run is the alert. Triage the named
failed check in the artifact, repair the provider/config/page drift, rerun with
`workflow_dispatch`, and require a green receipt before re-enabling an affected
handoff. Do not deploy the Worker/form or enable the controlled payment path
until the legal/privacy/e-sign gates above are complete.

### Owner production pilot — 2026-08-26

`bd724b71-1913-40db-936a-c0443745a4e1` is the production owner-pilot case for
legal name Matti Rowe, preferred name Klokka Skaddla, athlete key
`klokka-skaddla-owner-pilot`, Gravel God Mid. It is intentionally held in
`IDENTITY_REVIEW`: date of birth/adult status, jurisdiction, current health
attestation, TrainingPeaks state, and legal signatures were not inferred from
stale or conflicting local profiles. Course access was granted under the
owner-only exemption and the invite-delivery receipt was verified. The case is
also indexed in `Athlete Index`, `Legal Status 2025-26`, and
`Onboarding Queue 2025-26` in the master coaching workbook.
