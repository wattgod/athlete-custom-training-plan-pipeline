# CONSULT-ENGINE: automated consultation — checkout → intake → TP link → analysis → coach report

**Status**: draft v2 (2026-08-17; adversarial review folded in — sol unavailable until Aug 19, re-run before dispatch); base all work on `origin/main` (`fbbfb4d`+; re-verify line numbers). Owner: Matti. Brand first: Gravel God; parameterised so Roadie Labs / XC Ski follow.
**Decisions already made (Matti, 2026-08-17)**: consult stays **$150 / 60 min**; **+$100
custom-plan add-on** (one goal event, ≤12 weeks, built from consult intake+data only, delivered on
TP within 7 days of the call, one adjustment round inside 14 days, add-on purchasable ≤7 days after
the call). TP invite link `https://home.trainingpeaks.com/attachtocoach?sharedKey=2OTEPC6BXNVQU`
needs **no coach acceptance click**. Coach account 1248813 is Coach Edition Unlimited
(`maximumBasicAthletes` unbounded — verified live). Endure delivery is a later slice (C6).

## 0. What exists today (verified in `webhook/app.py` @ origin/main)
- `POST /api/create-consulting-checkout` (:4293) → Stripe Checkout, `CONSULTING_PRICE_ID`
  (`price_1T2ekVLoaHDbEqSq0GGfoBEX`, $150/hr, `quantity=hours`), metadata
  `{product_type:'consulting', athlete_name, hours}`, success_url hardcoded to
  gravelgodcycling.com/consulting/confirmed/?session_id=…
- `_handle_consulting_webhook` (:4728): mark processed → GA4 → `_log_product_event` →
  `_notify_new_order('consulting')` → `_build_consulting_email` (:753) tells Matti to email the
  athlete by hand. **No intake, no record, no TP step, no athlete email.**
- Durable job records: `_write_job/_read_job/_update_job` (:2407–2480), `JOBS_DIR/orders/<order>.json`,
  `sweep_stuck_jobs` (:2670), `POST /api/jobs/sweep` (CRON_SECRET), `GET /api/order-status/<ref>`
  (:3341). Intake storage: `store_intake/load_intake` (:1221/:1240) — UUID-keyed JSON on the volume.
- Emails via Resend (`_send_email` :285-ish); `NOTIFICATION_EMAIL`; follow-up cron
  (`process_followup_emails`, `/api/cron/followup-emails`) explicitly skips consulting.
- The plan-fulfilment email already sends the TP invite link (:3929/:3959) — reuse the copy pattern.

## 1. Data model — `consultations/<order_id>.json` on the volume (new dir beside `orders/`)
```json
{ "order_id": "cs_…", "brand": "gravelgod", "created_at": "...",
  "status": "open|analysis_running|report_ready|needs_attention|closed",   // pipeline state ONLY
  "welcome_sent_at": null,                                                  // null → cron re-sends
  "athlete": {"name": "...", "email": "...", "tp_athlete_id": null, "tp_matched_at": null},
  "products": {"consult": {"hours": 1, "amount": 15000},
               "plan_addon": {"purchased": false, "amount": 10000, "purchased_at": null, "offer_expires_at": null}},  // FLAG, not a status
  "intake": {"intake_id": null, "received_at": null},                       // TIMESTAMPS; intake and TP link arrive in either order
  "call_at": null,                                                          // set by the operator endpoint (Google Calendar has no hook); call-relative timers only run when non-null
  "analysis": {"claimed_by": null, "lease_expires_at": null, "attempts": 0, "started_at": null, "finished_at": null, "report_path": null, "error": null},
  "closed_reason": null,                                                    // e.g. "no_data_30d", "delivered"
  "timeline": [{"at": "...", "event": "paid|welcome_sent|intake_received|tp_linked|claimed|report|error|call_set|addon_paid|closed", "detail": "..."}] }
```
Path: `DATA_DIR/consultations/<safe_order_id>.json` (use `_safe_order_id`, `:1976`; outside
`jobs/orders/` so `sweep_stuck_jobs` never touches it). Written atomically (temp+replace as
`_write_job`). Readiness for analysis is DERIVED: `tp_matched_at` set (intake optional but
preferred). Every event appends to `timeline`. **Never** delete; `closed` is terminal.
Give-up: no TP link 30 d after `paid` → `closed` with `closed_reason: no_data_30d` + coach email.
Brand keys are the registry's (`athletes/config/brands.yaml`: `gravelgod`, `roadielabs`, …) —
add `consulting_path` / `consulting_success_path` there.

## 2. Checkout changes (`create_consulting_checkout`)
- Add optional `plan_addon: true` → second `line_item` `{price: CONSULT_PLAN_ADDON_PRICE_ID, quantity: 1}`.
  New Stripe product "Custom plan add-on (post-consult)", $100, created by Matti (the product
  script lives in `gravel-race-automation/scripts/create_stripe_products.py`). Price ids in this
  app are constants (`:200-228`); for the add-on use `CONSULT_PLAN_ADDON_PRICE_ID = os.environ.get(...)`
  and gate the line item AND the page copy on it being set (Stripe-before-display).
- Brand from `Origin` via `_brand_from_origin` (`:4126`), exactly as `/api/create-checkout`;
  `success_url`/`cancel_url` from the brands.yaml consulting paths (today hardcoded to GG; Roadie's
  `/consulting/` is 403 and its `/confirmed/` is a live orphan, so RL stays disabled until C5).
- metadata adds `plan_addon: "1|0"`, `brand` (the webhook already reads `metadata.get('brand')`, :4737).
- **Post-call add-on purchase** (missing in v1): `POST /api/create-consult-addon-checkout {ref}` →
  Checkout for the add-on price only, `metadata {product_type:'consult_addon', consult_order_id}`;
  webhook branch flips `products.plan_addon` on the EXISTING record (idempotent on `purchased_at`).
  The offer email and the success-page clause link here.
- Keep `hours` (1–10) but the page sells 1; multi-hour stays backend-only.

## 3. Webhook changes (`_handle_consulting_webhook`)
Order matters (today `mark_order_processed` runs FIRST at :4735 — a Resend timeout would then
lose the athlete email forever on Stripe's retry):
1. Write the consultation record (status `open`) — atomic.
2. Athlete welcome (new `_send_consult_welcome`, `_send_email` directly, brand-styled): (a) the
   booking link (new `CONSULT_BOOKING_URL` env in this app — the Google Calendar constant currently
   lives only in gravel-race-automation), (b) **the intake link with the token in the URL FRAGMENT**
   `https://gravelgodcycling.com/consulting/intake/#ref=<order_id>&t=<token>` — query-string
   credentials are forbidden here (`app.py:103-105`, `:3286`) and only `token=` is log-redacted;
   the page JS POSTs `{ref, t, answers}` in the body. Token = purpose-scoped (`consult_intake`),
   TTL 30 d, minted with `download_tokens.py`-style helper (`DOWNLOAD_TOKEN_KEYS`), NOT CRON_SECRET;
   valid ONLY for `/api/consult-intake`. (c) the TP invite link + three-step copy, (d) the no-TP
   fallback, (e) add-on terms if bought. Set `welcome_sent_at` on success; leave null on failure.
3. `mark_order_processed` LAST. Cron re-sends the welcome when `welcome_sent_at` is null.
4. Coach email via `_send_email` directly (NOT `_notify_new_order`, whose
   `external_notification_projection` nulls athlete numbers and replaces errors — `fulfillment_state.py:159-190`).
5. **Follow-ups**: new `process_consult_followups()` over `consultations/*.json` (state-conditional,
   not day-offset — `process_followup_emails` hard-filters `product_type == 'training_plan'` at :4988
   and is keyed `(order_id, day)`); called from `/api/cron/followup-emails` beside
   `process_touchpoint_emails` (:5421). Rules: welcome missing → resend; +24 h no intake → nudge;
   +48 h no TP link → nudge with fallback; each at most once (record `nudges_sent`). Call-relative:
   ONLY when `call_at` set — +1 d after call: plan-of-action reminder to Matti if not `closed`;
   +2 d: add-on offer if not purchased (`offer_expires_at = call_at + 7 d`). Copy lives in
   `email_templates.py` so voice tests apply.
6. Existing test `test_consulting_webhook_processes_payment` (`test_webhook.py:1429`) posts an event
   with no `amount_total`/`customer_email`/`brand` and asserts `status=='success'`, `hours=='2'`
   with RESEND unset — keep the response shape, tolerate missing fields, never 500 on email failure.

## 4. Intake — new page + endpoint
- Page: `wordpress/generate_consult_intake.py` in gravel-race-automation (same spine as
  `generate_coaching_apply.py`, ~14 fields, localStorage save/resume). Fields: goal event + date;
  weekly hours (typical / max); years training; FTP or "don't know"; LTHR or "don't know"; the one
  question you most want answered; what's gone wrong this year; injuries/limits (free text);
  TrainingPeaks email (the one you'll log in with) or "no TP"; devices (power meter y/n, HR y/n);
  coaching/plan history; anything else. Plus the privacy sentence (Matti's wording).
- Endpoint: `POST /api/consult-intake` (+ `OPTIONS` 204; token in BODY — CORS `Allow-Headers` is
  `Content-Type` only, :277) `{ref, t, answers}` → verify token (purpose+TTL) → `intake_id = uuid4()`
  → `store_intake` → update record `intake.{intake_id, received_at}` → 200. `@limiter.limit("10/minute")`.
  Idempotent: a second submission for the same ref replaces the intake and appends a timeline event.
  **Never** synthesize an unanswered field (retro rule): "don't know" stays "not available" in the
  report; the runner may quote TP settings (FTP/LTHR) but must label the source "TrainingPeaks
  setting", never present it as the athlete's answer.
- Optional pre-pay: the intake can also be filled from the sell page before checkout (store with a
  temp id, attach on webhook via metadata `intake_id`) — same as the plan flow. v1: post-pay only.

## 5. Runner job contract (Railway side)
All runner routes: `X-Runner-Secret` header (Railway env `CONSULT_RUNNER_SECRET`; 503 when unset,
401 when wrong — same pattern as :5412), `@limiter.limit("60/minute")`, `MAX_CONTENT_LENGTH`
set app-wide (none today) with the report upload capped at 25 MB. Every route idempotent (runner
retries with backoff are guaranteed): repeated `tp-linked`/`report`/`error` for the same state
return 200 and send NO second email.
- `GET /api/consult/jobs/pending` → open records lacking `tp_matched_at` (emails + intake TP-email
  hints) so the runner does ONE roster fetch per poll, not one per record.
- `GET /api/consult/jobs/ready` → TP-matched records ready for analysis: status `open`, or
  `analysis_running` with an EXPIRED lease (a safety net ahead of the hourly
  `sweep_stuck_consultations()` sweep), `analysis.attempts < 3`, never `closed`. Returns
  `{ready:[{order_id, tp_athlete_id, email, intake_answers, plan_addon:{purchased, purchased_at},
  call_at, attempts}]}`, oldest (`created_at`) first. `intake_answers` is the stored intake
  `answers` dict or `null` — never synthesized (§4's no-synthesis rule).
- `POST /api/consult/jobs/<order_id>/tp-linked` `{tp_athlete_id}` → sets `tp_matched_at`.
- `POST /api/consult/jobs/<order_id>/claim` → lease (`claimed_by`, `lease_expires_at = now+90 min`,
  `attempts+1`, status `analysis_running`); refuse if a live lease exists. Stuck sweep: expired lease
  → back to `open` (attempts <3) or `needs_attention` (copy `JOB_STUCK_AFTER_MINUTES` pattern).
- `POST /api/consult/jobs/<order_id>/report` multipart `{report_md, report_json, receipts.zip}` →
  `consultations/<order_id>/`, status `report_ready`, coach email (markdown→html) + attachments;
  athlete gets nothing automatically.
- `POST /api/consult/jobs/<order_id>/error` `{error}` → `needs_attention`, coach email (error text
  in the mail, since this is coach-only — no projection).
- `GET /api/consult/jobs/<order_id>` (X-Runner-Secret ONLY — the athlete intake token never reads
  the record).
- `POST /api/consult/runner/heartbeat` `{runner_id, ok, detail?}` → persisted to
  `DELIVERIES_DIR/consult_runner_heartbeat.json` (atomic temp+replace) as `{runner_id, ok, detail,
  at}`. `process_consult_followups()` checks it once per cron run: heartbeat missing or older than
  6 h, or the latest heartbeat has `ok: false`, sends the coach `[GG] Consult runner needs
  attention` — at most once per 24 h (`last_runner_alarm_at` recorded in the same file).
- **Operator endpoint** `POST /api/consult/<order_id>/op` (X-Cron-Secret)
  `{call_at? | close?:reason | retry? | deliver_endure?:{plan_of_action_md}}`
  — Matti's only lever until a review surface exists (curl one-liners in the coach email).
  `deliver_endure` writes an `endure` block onto the record —
  `{requested_at, plan_of_action_md, delivered_at:null, result:null}` — and appends timeline
  event `endure_requested`. This is how Matti hands the pipeline a plan-of-action write-up
  (drafted from the coach report) for delivery to Endure (C6, endurelabs
  `specs/consult-delivery/spec.md` §6).
- `GET /api/consult/jobs/deliver` (X-Runner-Secret) → records with `endure.requested_at` set and
  `endure.delivered_at` still `null`:
  `{order_id, tp_athlete_id, email, first_name, last_name, consult_date (call_at ?? created_at),
  goal_event (from the stored intake answers, or null), plan_addon (bool), plan_of_action_md,
  findings, prefill}`. `findings` is read from the runner's stored
  `consultations/<order_id>/report.json` (`~/gg-consult-runner/report/build_report.py` shape): the
  `one_thing` first (`kind: "physiological_limiter"` when `one_thing.label == "durability"`, else
  `"pattern"`), then up to 7 non-placeholder `data_bullets` (`"not available: …"` strings are
  dropped) each as `{title, body, kind: "pattern", confidence: 0.75}` — `title` is the bullet text
  itself (truncated to 60 chars), `body` is the full bullet. `prefill` is `{ftp, lthr, max_hr,
  weight}` read from `report.json.athlete_card`, keys omitted when absent (the current
  `build_athlete_card()` only ever populates `ftp`/`lthr`; `max_hr`/`weight` are forward-compatible).
  A record with no `report.json` yet on disk still appears, with `findings: []` and `prefill: {}`.
- `POST /api/consult/jobs/<order_id>/endure-delivered` `{result}` → sets `endure.delivered_at` (once)
  and `endure.result` (the full payload each call, even on repeats), appends timeline event
  `endure_delivered`, and sends the coach ONE confirmation email (`[GG] Consult delivered to
  Endure: …`) including `result.invitation.url` when present. Idempotent: `delivered_at` is set on
  the first call only; a repeat post (runner retry with backoff) sends no second email.

## 6. Runner (`~/gg-consult-runner`, runs on the Mac with a logged-in TP Chrome)
- Poll `/pending` every 10 min; ONE roster fetch (`coaches/v1/coaches/1248813/athletes`); match
  by checkout email (case-insensitive) or the intake's TP email; **never** by name; on match post
  `tp-linked` then `claim`. Back off on 429/401; after 3 consecutive auth failures post a heartbeat
  failure so Railway can email `needs_attention` (session expiry/MFA otherwise stalls silently).
  Keep request rate low (≤6 detaildata in flight, 200 ms spacing) — a coach-session pull is outside
  what TP's ToS licenses; low volume, coach account only, never athlete credentials.
- Pull 180 d: `fitness/v6/athletes/{id}/workouts/{start}/{end}`, `…/workouts/{wid}/details`
  (TIZ + mean-max), `…/detaildata` for rides ≥ 20 min in the last 120 d, `fitness/v1/athletes/{id}/settings`,
  PMC (`POST …/reporting/performancedata/{start}/{end}` with the constants body), events
  (`…/events/{start}/{end}`), notes. Chunk ≤6 detaildata calls in flight; write to
  `athletes/<order_id>/tp/`.
- Analysis: `npx tsx endurelabs/scripts/analyze-tp-streams.ts <dir>` (Endure's own chain) +
  the review script (weekly TIZ/accumulation table, PMC/ramp, durability, suppression check,
  PD validity gate, strength/fueling threads, race calendar cross-read) → `report.json`.
- Synthesis: `report.md` in the fixed shape below, generated by a template first (numbers), then
  a Claude pass **in this Mac session, not via API key** (memory rule: no Anthropic API key) —
  v1: the template only; the narrative pass is Fable's job when the report lands until a
  no-key path exists.
- Post `/report`. Secrets in the Mac keychain, launchd job, FileVault on; delete
  `athletes/<order_id>/tp/` 30 d after `closed`; never in the repo. Heartbeat: `POST /api/consult/runner/heartbeat`
  every poll; Railway emails Matti if silent > 6 h.

## 7. Report shape (`report.md`, one page for the coach)
1. **ONE thing** (single sentence). 2. Athlete card (age, FTP/LTHR & when last tested, CTL/ATL/TSB
today, 2025 peak, goal event + days). 3. What they said (intake, verbatim key answers) vs what the
data says (5 bullets, each with the number). 4. Composition: TIZ table + accumulation line (earned vs
scraps). 5. Load: ramp Sun→Sun, monotony, ACWR, longest rides. 6. Durability, suppression check,
PD validity + phenotype (labelled "Endure open-model fit"). 7. Race calendar + oddities. 8. Questions
to ask on the call (5). 9. If plan add-on bought: a proposed 12-week shape (phases + weekly hours) — labelled DRAFT, built
only from answered intake fields + data; unknown availability → "ask on the call", never guessed. 10. Receipts: files pulled, endpoints, timestamps.

## 8. Success page + sell page (gravel-race-automation)
- `/consulting/confirmed/`: three steps (Book your time · Fill in the intake · Connect
  TrainingPeaks) with the two links live; add-on clause if not bought ("Add a custom 12-week plan
  built from your consult — $100, available for 7 days after the call"); coaching clause stays.
- **Immediately (before C1 lands)**: fix the live FAQ line "You also get a confirmation email with
  a short intake form" (`generate_consulting.py:210`) — it promises something nothing sends.
- `/consulting/`: rewrite per Sultanic + Dossier spine; how-it-works strip (Book → Connect TP →
  Your read arrives → We talk → Plan-of-action in 48 h); add-on rung; remove the three unverified
  testimonials; Normie Test; `tests/test_consulting.py` updated with the copy. **Publish only
  after Matti reads it.**

## 9. Tests
- Webhook: record written BEFORE `mark_order_processed`; welcome content (fragment link, TP link,
  booking link); `welcome_sent_at` null on Resend failure + cron resend; add-on line item gated on
  env; brand from Origin; post-call add-on webhook branch idempotent; existing
  `test_consulting_webhook_processes_payment` still green; follow-up state machine (each nudge once,
  call-relative only with `call_at`); runner routes 503/401/200, lease + stuck sweep, idempotency
  (`report` twice = one email, `tp-linked` twice = one timestamp); intake token purpose/TTL/scope
  (rejected on `/api/consult/jobs/*`), body-token CORS, no-synthesis; `MAX_CONTENT_LENGTH`.
- Runner: roster matcher (case, alias, none), pull chunking, analysis wrapper on the Steve fixture
  (`~/Downloads/steve-wagner-tp` → expected numbers), report template renders with missing sections
  as explicit "not available" (never blank), retries with backoff.

## 10. Order of work
C1 Railway (record, checkout add-on, webhook, intake endpoint, emails, follow-ups, runner endpoints)
→ C2 runner → C3 report template + first real report read by Matti → C4 pages → C5 RL/XC → C6 Endure
delivery. Each slice: adversarial review before dispatch, tests green, Matti gate where marked.
