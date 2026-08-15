# Spec — trustworthy custom-plan fulfilment

**Status: r9 — CONVERGED. Codex adversarial review returned
GO-WITH-CONDITIONS (`docs/reviews/SPEC_TRUSTWORTHY_FULFILMENT_CODEX_R9.md`).
Implementation may begin; production rollout is held by the twelve standing
conditions in that review (phase gates, fake-server/kill-point proofs,
controlled live-canary evidence).**

Review log:

- r1 → codex NO-GO, 22 blockers (`docs/reviews/SPEC_TRUSTWORTHY_FULFILMENT_CODEX_R1.md`).
- r2 → codex NO-GO, 15 new blockers; 10/22 r1 resolved, 10 partial, 2 not
  (`docs/reviews/SPEC_TRUSTWORTHY_FULFILMENT_CODEX_R2.md`).
- r3 → codex NO-GO, 9 spec-level blockers remaining; all other residual items
  classified implementation-gated
  (`docs/reviews/SPEC_TRUSTWORTHY_FULFILMENT_CODEX_R3.md`).
- r4 narrowly scoped to the nine r3 blockers.
- r4 → codex NO-GO, 3/9 resolved, 6 remaining spec-level (seal finalization
  graph, exchange predicates, serializable supersession, APPLIED semantics
  for manual delivery, fixture consistency, changed-content evidence)
  (`docs/reviews/SPEC_TRUSTWORTHY_FULFILMENT_CODEX_R4.md`).
- r5 narrowly scoped to those six.
- r5 → codex NO-GO, 4/6 resolved; two remaining: the cancellation
  quiescence barrier and self-verifying/compensable supersession
  dispositions (`docs/reviews/SPEC_TRUSTWORTHY_FULFILMENT_CODEX_R5.md`).
- r6 narrowly scoped to those two, plus the r5 editorial items.
- r6 → codex NO-GO, 1/2 resolved (D1 quiescence complete); one localized
  D0/D3 repair remaining: per-kind/per-disposition field matrix and an
  effective remote inventory distinct from the landed journal
  (`docs/reviews/SPEC_TRUSTWORTHY_FULFILMENT_CODEX_R6.md`).
- r7 narrowly scoped to that repair.
- r7 → codex NO-GO: repair shape correct, three residual cross-section
  contradictions (stale S2 digest sentence; predecessor sub-schema vs
  positional kinds + blanket absent→create rule; non-total inventory
  schema/transitions) (`docs/reviews/SPEC_TRUSTWORTHY_FULFILMENT_CODEX_R7.md`).
- r8 narrowly scoped to those three.
- r8 → codex NO-GO by one localized collision: two positional
  completeness/matrix phrases (singleton-keep before_image; entitlement-keep
  predecessor keyed to origin instead of inventory existence)
  (`docs/reviews/SPEC_TRUSTWORTHY_FULFILMENT_CODEX_R8.md`).
- r9 repairs exactly those two phrases, unifies the singleton predecessor
  rule on inventory existence, adds the first/subsequent-revision schema
  tests, and fixes the stale D3 "landed inventory" wording; no other
  sections changed in substance.
- r9 → codex **GO-WITH-CONDITIONS — converged**. Zero new blockers; twelve
  standing implementation/rollout conditions
  (`docs/reviews/SPEC_TRUSTWORTHY_FULFILMENT_CODEX_R9.md`).

Successor to `docs/HANDOFF_CUSTOM_PLAN_FULFILMENT.md`. All `file:line` anchors
refer to **`origin/main` @ `af284c2`**; verify with
`git show origin/main:<path>`, never the working tree.

**Settled inputs (not open questions):**

1. **No TrainingPeaks partner API — permanently.** The browser worker is the
   production mechanism, engineered as such. ToS exposure is an accepted,
   logged business risk.
2. The state machine in `webhook/fulfillment_state.py` is kept as the spine;
   schema v2 (§S) adds `APPLYING` (between APPROVED and APPLIED),
   `APPLIED_ATTESTED` (manual delivery) and `CANCELLED` without reordering
   approve-before-apply.
3. Approval precedes application.
4. The coach sends the athlete-facing email personally, forever.
5. **One apply contract** (§D0); `tp_apply_driver.js` retired after migration.
6. **The Gmail draft is the athlete-facing message**; `/api/confirm`'s
   customer send is removed (§E2).
7. **Blocked review means a non-executable review bundle** (§B1).
8. *(new in r3)* **Every fulfilment is an order, not an athlete.** Immutable
   `order_id` is the primary identity everywhere (§S1).
9. *(new in r3)* **Approval approves sealed content**, identified by digest,
   not a mutable directory (§S2).
10. *(new in r3)* **Endure is a delivery platform under the same gate** — its
    current pre-approval push is disabled in Phase 1 (§D4).

---

## 0. Invariants

- **I1 — No fabricated athlete data.** No estimated/defaulted value anchors an
  athlete-facing deliverable while presenting as measured — at any stage,
  including fueling. Every derived value is recorded with basis and surfaces
  for review.
- **I2 — One road to the athlete.** No executable deliverable, customer
  download, published guide, athlete-calendar write, **or platform push (any
  platform)** exists outside the state machine. Pre-approval review access is
  non-executable by construction (§B1).
- **I3 — Review precedes application**, and what was reviewed is what is
  applied: approval binds to a content seal (§S2).
- **I4 — Drafts, not sends.** Athlete-facing prose is machine-drafted,
  coach-sent. No automated email to the athlete exists after §E2 (including
  platform-initiated invitations, §D4).
- **I5 — Provenance.** From the state file alone: which credential approved,
  what it waived, what it confirmed **with the confirmed values**, what was
  applied (per operation), and what readback showed.
- **I6 — Failure is loud and closed.** No subsystem failure reports success.
  Fail closed toward "coach must look."

---

## S. State schema v2 (shared foundation)

`SCHEMA_VERSION` → 2, with migration for v1 files. The pinned v1 stores only
coach/time in `approval` (`fulfillment_state.py:185`), has no order identity
(`:135-140`), and drops transition metadata into history only (`:209-210`);
the Flask endpoint forwards none (`webhook/app.py:2393-2397`).

### S1. Order identity

- New immutable fields: `order_id` (Stripe session/order id or an opaque
  generated id for manual orders) and `delivery_platform`
  (`trainingpeaks | endure | manual`). State lives at an order-keyed path;
  the athlete-slug path (`webhook/app.py:2367-2368`) becomes a lookup, not
  the authority.
- **v1 migration is fail-closed** (r3 blocker 9: v1 files carry
  `athlete_id` + revision but no order reference,
  `fulfillment_state.py:135-140`, and a repeat athlete can map to multiple
  ledger orders — slug inference would recreate the cross-order flaw S1
  removes). Every legacy file receives a new opaque
  `legacy_order_id`; its prior approval/application grants **no authority
  for new actions** — the file enters status-preserving quarantine
  (`legacy: true`) with original evidence retained verbatim; resuming
  fulfilment on a quarantined order requires an authenticated manual
  binding (coach asserts which ledger order it is, recorded as a
  transition). All pre-migration tokens are revoked (key rotation). Path
  moves are write-new → verify → tombstone-old, recoverable at startup.
  Multiple ledger candidates are listed in the quarantine record, never
  auto-selected.
- `order_id` appears in: review routes (`/review/<order_id>`), all token and
  capability claims, artifact paths, apply-contract external-id construction,
  audit records, and every transition. Athlete slug is never the sole key.
- Tests: repeat customer (two orders, one athlete), two concurrent orders,
  slug collision (two people normalizing to one slug), cross-order token
  reuse rejected, regeneration of one order not disturbing another.

### S2. Content seal — two non-circular layers

(r3 blocker 1: hashing a contract that contains the hash is circular, and
Phase 1's PlanIR/`tp_manifest.json` are *reflections* of already-emitted
artifacts — ZWO is generated first, the guide reads it, PlanIR aggregates
afterward, `generate_athlete_package.py:3044-3052, 3124-3131` — not a source
from which those bytes can be rebuilt.)

**Canonical serialization** (used everywhere a digest is defined): UTF-8,
JSON with lexicographically sorted keys, no insignificant whitespace, arrays
in schema-defined order, sha256. **`expected_digest` is defined exactly once,
in D0, per disposition** (create/update hash their payload; keep carries the
desired digest of the kept resource; delete carries none) — S2 defers to
that definition entirely. No digest is ever computed "from the seal."

**The acyclic finalization sequence** (r4 blocker 1 — each step's input is
complete before the step runs; nothing is rewritten after being hashed):

1. Canonical workout model + review-item catalog inputs + guide sources are
   finalized → **`model_seal`** = hash of their canonical serialization,
   including the apply contract's *operations payload* (which needs no seal
   field) — the contract envelope is not part of this hash.
2. The apply-contract **file** is then emitted with `model_seal` filled in
   its envelope. It is never emitted before the seal exists, so it is never
   rewritten.
3. All artifact bytes are emitted (ZWOs, guide HTML/PDF, preview, customer
   ZIP, the apply-contract file from step 2).
4. **`release_manifest`** = `{model_seal, artifacts: [{path, kind, sha256,
   bytes}]}` over every artifact from step 3. It is **immutable** once
   written; `release_manifest_digest` = hash of its `artifacts` array.
5. Approval records `{model_seal, release_manifest_digest}`.
6. Projections legitimately built *after* approval (e.g. the Gmail draft
   MIME) go in a **separate component manifest** — `{model_seal, component,
   artifacts: [...]}`, one per release component (S5), immutable once
   written, bound to approval via `model_seal` — never appended to the
   approved release manifest.

**Phase 1 (transitional):** there is no upstream model and no apply
contract yet, so the transitional order is its own numbered sequence:
(1) emit all eager artifact bytes; (2) build the `artifacts` array (path +
per-file sha256 + size for *every* emitted artifact, including eagerly
built release artifacts that B1 merely hides); (3) `model_seal` = hash of
that array alone (the containing `model_seal` and manifest-digest fields
are excluded by construction); (4) write the release-manifest envelope and
seal to state. This binds bytes, not provenance — weaker than post-A1.1
sealing and labeled so — but makes same-revision mutation detectable, which
is the Phase 1 requirement.
(Pinned generation is ZWO → guide → advisory PlanIR,
`generate_athlete_package.py:3044-3052, 3124-3131`, so PlanIR cannot be the
authority for those bytes.)

Downloads, the publish tool, the Gmail drafter, and the worker verify the
artifact they touch against the release (or component) manifest and the
manifest against approval; any mismatch is fatal (I3, I6). Content-changing
corrections call `write_generation`. Finalization writes seal + manifest to
state under the lock before any notification.

### S3. Review-item catalog and approval snapshot

- State gains a server-generated, revisioned `review_items` catalog: every
  blocker, required confirmation, and soft confirmation, each with stable
  `item_id`, type, **typed canonical value** (plus display unit, source,
  basis), sensitivity label, and revision.
- `approval` gains `confirmations`: per item — `{item_id, value (typed, as
  cataloged), disposition: confirmed | unconfirmed | resolved:<choice>,
  revision}` plus the approving credential id (§C4). Values, not digests:
  I5 requires recovering what was confirmed from the state file alone. The
  state file is server-side only and already excluded from packages
  (`webhook/app.py` persist exclusion); §A3's sensitivity labels govern
  redaction in every *other* surface (logs, emails, audit exports, review
  page caching). Unknown or wrong-revision item ids are rejected.

### S4. Blocker policy — waivable vs non-waivable

The pinned waiver semantics approve *any* blocked plan once the waiver covers
every id (`fulfillment_state.py:187-196`) — codex r2 is right that "hard
blocker" was only a label. v2 adds server-owned policy by stable rule id:
`waivable: true | false`.

- **Non-waivable** (approval impossible; remediation = fix and regenerate):
  `FTP_ESTIMATED` (fabricated anchor), `COURSE_UNRESOLVED` (unless remediated
  by a facts-omitted regeneration: plan/guide rebuilt from athlete-supplied
  facts only, which clears the blocker), `STATE_UNAVAILABLE`, validator-crash
  blockers, and seal-mismatch findings.
- **Waivable with reason**: `RACE_STALE`, `WEEKS_MISMATCH` (business
  judgment), availability/brand items, structural rules.
- Platform-scoped: `ATHLETE_UNLINKED` / `ATHLETE_NO_ACCOUNT` block only
  orders whose `delivery_platform` requires automated apply; manual delivery
  orders don't raise them.
- Negative tests: a complete waiver containing a non-waivable id is rejected.

### S5. Release components and outbox — inside the state file

APPLIED remains strictly the *complete verified* calendar fact (§D3 defines
`APPLYING` for anything less). Post-apply release side effects get revisioned
components in state: `guide_release`, `draft`, each
`{status: pending|succeeded|failed, attempts, evidence, at}`.

(r3 blocker 2: a lock serializes callers; it does not make two adjacent
files crash-atomic — `_atomic_write` replaces exactly one JSON file,
`fulfillment_state.py:69-86`.) Therefore **the outbox is a field of the
state JSON itself**: `outbox: [{event_id, event, template_version, status:
pending|delivered|failed, attempts, created_at}]`. A transition and its
pending outbox entries commit in the *same* single atomic file replacement.
Consumers (the notifier, the guide publisher, the drafter) read pending
entries, perform the side effect, and mark the entry `delivered`/`failed`
via a subsequent locked write; startup recovery is "scan state files for
pending entries older than a threshold." Either crash window is
deterministic: entry-without-effect (retried) or effect-without-mark
(consumers are idempotent per `event_id`). Kill-point tests after every
durable write.

Phase 5's gate requires all required components succeeded; a component
failure is loud (coach notice via the same outbox) without falsifying
calendar state (I6).

New top-level statuses: `APPLYING` (§D3), `APPLIED_ATTESTED` (manual
delivery attestation, §D3 — release-equivalent to APPLIED, provenance-
distinct) and `CANCELLED` (legal from any state; §F4 defines compensations;
terminal facts — approval, application, confirmation, compensation history
— are preserved, never erased). Wherever this spec says a release action
requires APPLIED, `APPLIED_ATTESTED` also satisfies it; only APPLIED means
readback-verified.

### S6. Blocker merge

`set_generation_blockers` *replaces* the list (`fulfillment_state.py:162`) —
an append-style caller would erase earlier blockers (codex r2 blocker 13).
v2 adds `merge_generation_blockers(path, expected_revision, source,
issues)`: under the state lock, replaces only that source's namespace,
preserves others, rejects on revision mismatch. The intake gate
(`intake_to_plan.py:3307-3330`) and the post-render validator (§C2) use
distinct sources. Tests: intake blockers survive validator merge; a clean
validator rerun clears only its own namespace.

---

## Workstream A — truthful inputs

### A1. Power basis, not fabricated FTP

**Today:** intake invents FTP (`intake_to_plan.py:829-842`); `ftp_estimated`
is email-copy-only (`:2854, :2970`); fueling *re-fabricates* watts from mass
(`fueling_policy.py:102-104`) and serializes them (`:152-154`).

**A1.1 — Canonical workout model (prerequisite).** The pinned architecture
cannot express a no-power plan: PlanIR globs ZWOs and synthesizes rest days
(`plan_ir.py:483-503`), segments are power-only (`:56-63`), TP projection
hardcodes `percentOfFtp` (`:362`), tests pin both
(`test_tp_projection.py:171-176, 214-231`). A metric-neutral model upstream
of all rendering: typed segment targets (`power_pct_ftp`, `pct_lthr`,
`pct_hrmax`, `rpe`, `free`), one target type per segment, plan-level
`control_metric` from `power_basis` + HR markers (`intake_to_plan.py:852-856`).
ZWO/PlanIR/preview/apply-contract/guide/polyline become projections. ZWO
emitted only for `control_metric == power`; HR/RPE plans use TP-native
`percentOfThresholdHr`/`percentOfMaxHr`/RPE-in-description — **live TP
acceptance is unverified and is proven via worker canary before the first
automated apply of an HR/RPE plan (Phase 5 gate, not Phase 3 — the worker
does not exist in Phase 3).** Offline fixtures (HR-with-LTHR, HR-only-HRmax,
RPE-only) assert: zero watt figures in every artifact, metric-appropriate
week-1 field test, documented re-anchor point.

**A1.2 — Intake.** Estimation deleted; `power_basis: "measured"|"none"`;
`ftp_watts` may be `None`; the `float(None)` swallow in
`generate_plan_preview.py` fixed. `power_basis: none` is a confirmation item,
not a blocker.

**A1.3 — Fueling without watts.** Null-power mode derives prescriptions from
duration, intensity descriptor, and body-mass g/kg bounds; no watt-derived
inputs computed or serialized; unsafe cases defer to the field test rather
than inventing a work rate. Guide copy for no-power athletes rewritten.

**Transitional (Phase 1):** `FTP_ESTIMATED` as a **non-waivable** blocker.

### A2. Devices reflect the form — fix the source, not just the parser

Codex r2 located the actual fabrication: the paid-order adapter hardcodes the
answer — `webhook/app.py:1487` writes `Devices: power meter, HR strap` into
the intake markdown regardless of the form, and `tp-skus/generate_skus.py:82`
bakes the same string into SKU fixtures. Parser-only work would tokenize a
fabricated string more neatly. Therefore:

- The adapter emits only what the form supplied; absent → `Devices: unknown`.
- `parse_device_list` (`intake_to_plan.py:506-508`) splits on
  commas/newlines only, maps through a canonical vocabulary, preserves
  unknown tokens verbatim as confirmation items.
- SKU fixtures corrected; a test asserts no device token exists in a profile
  whose intake did not state it.

### A3. Derived-value registry — with enforcement

`_derived` entries: `{id, field, class ∈ {measured, athlete_reported,
defaulted, inferred, externally_observed}, basis, inputs, sensitivity, at}`,
versioned with the revision, feeding §S3's catalog. **Sensitivity is
enforced, not decorative**: values labeled sensitive are redacted from
notifications, logs, audit exports, and any surface outside the
authenticated review page and the server-side state file. A rendering
checklist test greps notification/log output for seeded sensitive fixtures.

---

## Workstream B — one gated path

### B1. Review bundle vs release artifacts

The full ZIP contains `workouts/` (`webhook/app.py:1682, 1719-1722`) — the
importable bypass. Split:

- **Review bundle** (any state, coach audience): plan preview, coaching
  brief, unpublished guide draft, human-readable rendered target summaries.
  Excludes ZWO, TP-native structures, apply payloads, `tp_apply_driver.js`
  inputs, customer artifacts.
- **Release artifacts** (APPROVED+, seal-verified per §S2): ZWO, apply
  contract, customer ZIP, published guide, Gmail draft.

`persist_deliverables` (`:1659`) refactored accordingly (exposure is the
invariant if eager build is cheaper). Residual hand-transcription bypass is
procedural, acknowledged, audit-covered.

### B2. Notifications become state-aware — with a real sending mechanism

The pinned flow sends exactly one notification, immediately post-generation
(`webhook/app.py:2011-2025`); transitions return JSON and notify nobody
(`:2393-2401`). Codex r2 blocker 10: specifying APPROVED/APPLIED emails
without a sender is unreachable behavior. r3 model:

- **Generation-time email** (the one that exists today) becomes state-aware:
  - `BLOCKED_REVIEW`: blocker list (id/severity/message, waivability),
    review link, review-bundle download. Never: import steps, confirm
    controls, release artifacts. (Today's unconditional import steps and
    confirm curl: `:482-483, 512, 576`.)
  - `GENERATED`: review checklist, review link, review-bundle download.
  - state unreadable: `STATE_UNAVAILABLE` banner, treated as blocked (B4).
- **Post-generation states have no bespoke emails**: the review page (§C1) is
  the control surface for APPROVED/APPLIED actions. State-change and
  failure *notices* (apply failed, guide release failed, draft ready) are
  produced by the §S5 outbox — durable, keyed by
  `{order_id, revision, event, template_version}`, retried, deduplicated;
  notification failure never rolls back a transition.

### B3. Endpoint and token semantics

- Typed tokens replacing the month-window HMAC (`:1764-1788`; caller-chosen
  `?type=full` escalation at `:2249-2253`; real lifetime 28–62 days): signed
  claims `{order_id, athlete_id, generation_revision, artifact, audience,
  iat, exp, jti, kid}`; per-audience keys (review link, coach download,
  customer download); `CRON_SECRET` for operator curl only. Unknown
  `artifact`/`type` rejected. **Revocation is per-link (`jti` denylist) and
  per-key (`kid`)** — codex r2 non-blocking 4: a kid blacklist alone nukes
  every link under a key. Negative tests: escalation, revision mismatch,
  expiry bounds, cross-athlete, cross-order, unknown kid, replayed jti after
  revocation, key rotation.
- `/api/download` (`:2226`): review bundle — any state, coach audience.
  Customer artifact — status ∈ {APPROVED, APPLYING, APPLIED,
  APPLIED_ATTESTED, CONFIRMED} + customer audience + seal match; else 409
  `{"error": "plan not released"}`. Missing state = not released.
- `/api/order-status` (`:2280`): `download_ready` requires the same release
  condition.
- Regeneration bumps revision (`fulfillment_state.py:124-148`), killing
  revision-bound tokens; stale review links render "superseded".
  Post-APPLY regeneration semantics: §F4.

### B4. State-write failure stops presenting as success

`intake_to_plan.py:3340-3345` downgrades failed state writes to warnings.
Target: pipeline result carries `fulfillment_state: "unavailable"`; webhook
treats as blocked with synthetic non-waivable `STATE_UNAVAILABLE`; job
flagged. Fail-closed extends from confirm to notify/download.

---

## Workstream C — the review surface

### C1. The page

`/review/<order_id>`, served by the webhook. Ranked: header → blockers (with
waive controls for waivable ids; non-waivable ids show remediation, not a
control) → required confirmations → soft confirmations → verified facts
(collapsed, display-only; Approve records every sealed fact — no per-fact
checkbox) → (post-approval) apply → (post-apply) verify + draft/confirm.
Non-goals: no multi-coach roles; no in-browser plan editing — **which is
exactly why D2 resolutions are state-changing commands, not edits (§D2)**.
Target: clean order < 3 minutes. The coach decides exceptions (blockers +
required confirmations), not an inventory of derived calendar abbreviations.

### C2. Blockers, confirmations, and the post-render validator

**Generation-time blockers** (via §S6 merge, source `intake`):
`RACE_UNMATCHED`, `RACE_STALE`, availability, brand, quality-criticals
(pinned assembly `intake_to_plan.py:3307-3330`), plus `FTP_ESTIMATED`
(non-waivable, transitional), `COURSE_UNRESOLVED` (non-waivable; remediation
= facts-omitted regeneration; interim for the `courses[]` ticket),
`WEEKS_MISMATCH` (F6; non-calendar count bugs only). Calendar-forced
shortfall is confirmation `WEEKS_CALENDAR_SHORT`.

**Post-render validator** (source `post_render`; Phase 1 it validates the
*named transitional artifacts* PlanIR + `tp_manifest.json`, both already
emitted at `generate_athlete_package.py:3142-3151`; after D0 it validates the
apply contract — the validator's input is explicitly versioned so Phase 1
does not depend on Phase 5):

- `NO_RACE_DAY_WORKOUT` — race date carries a race-day entry.
- `THIN_RACE_WEEK` — race week has < 3 **counted** entries. Counted kinds are
  exhaustively enumerated: bike sessions and the race-day entry count;
  `rest`/`day_off` (including PlanIR-synthesized rest, `plan_ir.py:455-464,
  500-503`), notes, and strength do **not**. Fixture: a week of seven
  synthesized rest days + one race entry must fire.
- `DUPLICATE_FIELD_TEST` — >1 field test of the same metric in one week.
- `SESSION_PREDATES_GENERATION` — any session whose local calendar date
  (athlete timezone, from intake; default event-local) is before the
  pipeline's generation date. This catches Monika's Aug-4/Aug-5 workouts
  delivered Aug 6 ("in the past at delivery time" — findings §5), which a
  pure order-date rule legalizes (codex r2 blocker 14).
- `SESSION_PREDATES_ORDER` — session date before `order_created_at`'s local
  date (data-corruption signal; kept separate).
- Guide semantics (F1, F2): altitude section fires when the frozen snapshot
  qualifies; fueling labels match plan weeks; no cross-artifact carb
  contradiction.

Validator crash → non-waivable blocker via the merge op if state is
writable, `STATE_UNAVAILABLE` path if not (I6).

**Schedule conflicts.** v1 day-lists are availability, not prohibition
(`intake_to_plan.py:1033-1077`; findings adjudication). The required
confirmation `SCHEDULE_MISMATCH_CONFIRM` fires when the *generated* plan
places a high-intensity session on a day the athlete listed only as
long-ride-available, or a long ride on a day listed only for intervals —
i.e. generated placement vs stated availability role, not overlap between
the two stated lists (which may legitimately be disjoint).
`SCHEDULE_CONTRADICTION` blocks only on explicit constraints (a stated
off-day scheduled; expressible prohibitions post-intake-v2), **with one
normative exemption: the race-day entry itself never violates a stated
off-day** — races land where the organizer put them, and scheduling the
athlete's goal race is the plan's purpose, not a contradiction of their
weekly availability.

**Required vs soft confirmations.** Required when the unconfirmed value would
anchor an athlete-facing target (D2 account findings for the control metric,
v1 schedule overlaps). Approval rejected while required items are unresolved
(enforced by S3 snapshot validation, not page JS).

### C4. Auth — credential model

Signed links: single-order, single-revision, action-scoped, short-TTL
(default 7 days), `kid` + `jti`; server session on first open; transitions
POST server-side with CSRF token — `CRON_SECRET` never reaches a browser
(pinned endpoint trusts a typed name behind the global secret,
`webhook/app.py:2383-2395`). Provenance records
`credential: review-link:<kid>:<jti-issued-to>`; operator curl records
`operator-secret`. GET renders only; `Referrer-Policy: no-referrer`;
`Cache-Control: no-store`; tokens redacted from logs; first-open consumes
nothing (scanner-safe) — actions, not opens, are the audited events.

---

## Workstream D — delivery platforms

### D0. One apply contract — normative schema

Two incompatible contracts exist (`tp_manifest.json`:
`tp_apply_order.py:50, 237-248` for the JS driver; `fulfillment_manifest.json`:
`fulfillment_manifest.py:21-39, 67-80` for the adapter) and the full
operation inventory is larger than r2 admitted: workouts, calendar dates,
native notes, **attachments, mental_training_tasks, course_entitlement**
(`fulfillment_manifest.py:67-76`; adapter consumption `adapter.py:79-94`).

**This section is the normative schema** (r3 blocker 4: "shipped with
implementation" was a deferral; r3 blocker 5: revision-scoped remote
identity defeats supersession). The JSON Schema file checked in with the
implementation must be generated from, and tested equivalent to, this
definition.

**Envelope:**

```
{ "contract_version": "apply_contract/v1",
  "order_id": str, "tp_athlete_id": str, "generation_revision": int,
  "model_seal": str,          // S2 Layer 1; "" when computing the seal
  "operations": [Operation],  // execution order = array order (rules below)
  "compat": { "min_reader": "apply_contract/v1" } }
```

**Three identities, exactly** (r3 blocker 5):

- `logical_id` — stable **across revisions** of one order:
  `{order_id}:{kind}:{logical_key}` where `logical_key` is defined **per
  kind**: calendar date + daily ordinal for dated objects (`2026-08-14#1`);
  the note slug for notes; `{parent_logical_key}:{filename}` for
  attachments; the singleton name for thresholds/zones (`lthr`,
  `hr_zones`); the product id for entitlements. This is the reconciliation
  and supersession key.
- `op_id` — revision-scoped attempt id:
  `{logical_id}@r{generation_revision}`.
- `remote_marker` — **optional**, present only for kinds with a remote
  field that round-trips (`workout_upsert`, `calendar_note_upsert`,
  `attachment_upsert`, `mental_task_upsert`); it embeds `logical_id`
  (never the revision). Singletons and entitlements have **no**
  remote marker; their identity is positional (the account's one threshold
  set; the product id).

**Operation union** — common fields (r4 blocker 3: the shape must
serialize everything D3/F4 consume):

```
{ "op_id": str, "logical_id": str, "kind": str,
  "disposition": "create" | "update" | "keep" | "delete",
  "payload": {...} | null,
  "expected_digest": str | null,
  "prior_payload": {...} | null,  // snapshot of the predecessor's payload,
                                  // carried in THIS document (no
                                  // dereferencing another contract needed)
  "before_image": {...} | null,   // top-level; singleton compensation source
  "remote_marker": str | null,    // logical_id-embedding marker; only for
                                  // kinds that round-trip one (see table)
  "predecessor": { "op_id": str, "remote_id": str | null } | null,
                                  // remote_id: REQUIRED (string) for dated
                                  // kinds — their reconciliation needs a
                                  // remote object id; null for positional
                                  // kinds (singletons, entitlements), whose
                                  // identity is positional, not remote
  "rollback": { "strategy": "delete_by_remote_id"
                          | "restore_prior_payload"       // update, dated kinds
                          | "recreate_from_prior_payload" // delete, dated kinds
                          | "restore_before_image"        // singletons
                          | "none" } }                    // irreversible; manual
```

Which of these fields are required, null, or forbidden depends on
`kind × disposition`: the matrix below is the single normative authority.

**`expected_digest` is the desired remote field-set digest** (r6 blocker 1
— one formula per disposition, defined here once; S2 defers here): for
`create`/`update` it is sha256 of the operation's own canonically
serialized non-null `payload` (S2 rules); for `keep` the payload is `null`
and the digest is the desired digest of the resource being kept — copied
from the effective remote inventory entry (below) when one exists, and
otherwise (positional resources we never wrote: a pre-existing entitlement,
an account singleton value adopted as-is) the canonical digest of the
inspected desired field set from the D2 inspection snapshot (for
entitlements, the field set is `{product_id}`), with that snapshot recorded
as the digest's provenance; `delete` alone carries no expected digest.
Readback verifies the remote object against `expected_digest` for
create/update/keep; absence for delete.

**Per-kind / per-disposition field matrix** (REQ = required, ∅ = must be
null/absent; the generated JSON Schema enforces these branches):

| kind × disposition | payload | expected_digest | prior_payload | before_image | predecessor |
|---|---|---|---|---|---|
| dated `create` | REQ | REQ | ∅ | ∅ | ∅ |
| dated `update` | REQ | REQ | REQ | ∅ | REQ |
| dated `keep` | ∅ | REQ (copied) | ∅ | ∅ | REQ |
| dated `delete` | ∅ | ∅ | REQ | ∅ | REQ |
| singleton `update` (incl. **first revision**: positional identity, no prior operation exists) | REQ | REQ | ∅ | REQ | ∅ when no effective-inventory record exists; REQ otherwise |
| singleton `keep` | ∅ | REQ (copied from inventory, or from D2 inspection when the account value was never ours) | ∅ | ∅ | ∅ when no effective-inventory record exists; REQ otherwise |
| entitlement `create` | REQ | REQ | ∅ | ∅ | ∅ |
| entitlement `keep` | ∅ | REQ | ∅ | ∅ | ∅ when no effective-inventory record exists (first inspected-present keep); REQ once a prior grant **or verified keep** installed a record — inventory existence, not historical origin, decides |

`predecessor` is required **exactly when an effective-inventory record for
this logical id exists** — never demanded of first-revision positional
operations (r6: D2 legitimately emits a first-revision `threshold_update`;
there is no predecessor op to name; `before_image` supplies compensation).

Compensation strategies: dated `update` → `restore_prior_payload`; dated
`delete` → `recreate_from_prior_payload` (new remote id recorded on
recreation); dated `create` → `delete_by_remote_id`; singletons →
`restore_before_image` (CAS); entitlements → `none` (irreversible-by-us: a
recorded coach manual-cleanup item, flagged non-reconcilable). A singleton
no longer wanted is `keep`; "removing" one means an `update` back to its
before-image, an explicit coach choice.

**Two data structures, not one** (r6 blocker 2 — an append-only journal is
not the current remote state):

- `landed[]` (D3) stays the **attempt/compensation journal**: append-only,
  one entry per completed operation or compensation, consumed by F4 to
  compensate what just landed.
- **`effective_remote_inventory`** — a materialized state field with one
  exact schema: `{logical_id → {remote_id: str | null, desired_digest: str,
  payload_snapshot_ref: str | null, kind: str, last_op_id: str}}`, where
  `payload_snapshot_ref` names the immutable stored canonical payload that
  a later contract copies into `prior_payload` (null only for keeps of
  never-written positional resources, whose digest provenance is the D2
  inspection snapshot). It is updated by a **closed transition table** —
  every successful operation and every compensation has exactly one row
  (r7 blocker 3):

| journal event | inventory transition |
|---|---|
| dated `create` success; `delete`-compensation recreation | **install** `{remote_id: returned id, desired_digest, payload_snapshot_ref, last_op_id}` |
| dated `update` success; `update`-compensation restore | **replace** `desired_digest` + `payload_snapshot_ref` + `last_op_id`; `remote_id` unchanged |
| dated `delete` success; `create`-compensation (`delete_by_remote_id`) | **remove** the entry |
| singleton `update` success (**installs when absent** — the legal first-revision case); singleton compensation (`restore_before_image`) | **install-or-replace** `{remote_id: null, desired_digest, payload_snapshot_ref, last_op_id}` (compensation writes the before-image values) |
| verified `keep` on an **absent** entry (never-written singleton adopted as-is; pre-existing entitlement) | **install** `{remote_id: null, desired_digest: inspection digest, payload_snapshot_ref: null, last_op_id}` — so subsequent revisions have a predecessor |
| verified `keep` on an existing entry | **update `last_op_id` only** |
| entitlement `create` success | **install** `{remote_id: null, …}` |

  The supersession snapshot of this inventory is taken **after D1's
  quiescence barrier**.

**Completeness is measured against the effective remote inventory
snapshot, not the journal and not the prior contract** — and the
absent-from-snapshot rule is **kind-aware** (r7 blocker 2):

- Every logical id **present** in the snapshot gets exactly one operation;
  its `predecessor` = the snapshot's `{last_op_id, remote_id}` (remote_id
  null for positional kinds, per the branch-specific predecessor schema).
- **Dated** logical ids absent from the snapshot: if still desired →
  `create` (no predecessor); if not desired → they do not appear and must
  remain absent.
- **Singletons** are never `create`. A desired singleton absent from the
  snapshot is either the first-revision positional `update`
  (`predecessor: null`, `before_image` **required** — it mutates) or a
  verified first-revision `keep` (`predecessor: null`, `before_image`
  **absent** — it performs no mutation; its digest source is the D2
  inspection snapshot per the matrix).
- **Entitlements** absent from the snapshot: not on the account per D2
  inspection → `create`; already on the account → `keep` with the
  inspection digest, `predecessor: null`.

A contract missing a disposition for any snapshot entry, or naming a
predecessor absent from the snapshot, is rejected before any write. Per
kind:

| kind | payload (required fields) | readback expectation | rollback (for `create`; other dispositions use the strategies above) |
|---|---|---|---|
| `workout_upsert` | `{date, title, description, tp_workout_type, total_seconds, tss_planned, structure}` — `structure` is the TP-native structure object projected from the canonical model (or `null` for race/day-off kinds per pinned projection semantics) | remote object exists on `date` with `remote_marker`, field-set digest equals `expected_digest`, persisted `remote_id` | `delete_by_remote_id` |
| `calendar_note_upsert` | `{date, title, body}` | same pattern | `delete_by_remote_id` |
| `attachment_upsert` | `{parent_logical_id, filename, sha256, bytes_ref}` | attachment listed on parent, size+digest match | `delete_by_remote_id` |
| `mental_task_upsert` | `{date, title, body}` | same pattern | `delete_by_remote_id` |
| `course_entitlement_grant` | `{product_id}` | entitlement present | `none` (revocation is a recorded coach action) |
| `threshold_update` | `{metric, after_value, unit}`; top-level `before_image` REQUIRED (captured at D2 inspection) | current value == `after_value` | `restore_before_image` (CAS: only if current still == `after_value`) |
| `zone_update` | `{zone_set, after_table}`; top-level `before_image` REQUIRED | current table == `after_table` | `restore_before_image` (CAS) |

**Ordering rules:** singletons first (zones correct before workouts land),
then deletes/updates from supersession, then creates by date, notes and
tasks after their dates' workouts, attachments after parents, entitlements
last. **Update-vs-stop policy is per kind and fixed here:** dated objects
with one remote match and a different digest → update in place via
`remote_id`; multiple matches → stop (coach repair); singletons → CAS or
stop. No "operation policy" indirection.

**Supersession semantics:** the diff is *serialized in the contract itself*
via the `disposition`/`predecessor`/`prior_payload` fields above — D3
executes and F4 compensates from the same serialized records; nothing is
computed by dereferencing an earlier contract at apply time. Singletons
always re-CAS from a fresh before-image (`update` with new `before_image`).
Dangling landed logical ids fail contract validation, not the apply.
`calendar_dates` in the pinned manifest (`fulfillment_manifest.py:71`) is a
verification inventory, not a remote operation class — dates remain derived
from dated operations; no feature is lost.

**Compatibility:** readers reject a `contract_version` they don't know;
additive optional fields are minor-safe; any field removal or semantic
change bumps the version. Every operation class in the pinned manifests
(workouts, calendar dates, native notes, attachments, mental_training_tasks,
course_entitlement — `fulfillment_manifest.py:67-76`, `adapter.py:79-94`)
is retained above; intentional drops require a spec change. **Migration
parity tests**: old `fulfillment_manifest` path vs new contract produce
equivalent remote effects per operation class against the fake server. The
generated JSON Schema and completeness tests MUST cover first **and**
subsequent revisions of an adopted singleton keep and an adopted
pre-existing entitlement keep (the two branches where predecessor presence
flips between revisions). The JS driver is retired only after parity; until
then it is review-bundle-excluded (B1).

### D1. Session service — broker with a defined trust mechanism

Operations only — `probe_athlete(identity)`, `inspect_account(tp_id)`,
`apply(contract)`, `verify(contract)`, `rollback(contract, op_ids)`; the
adapter runs inside the worker; no bearer/cookie/TOTP crosses the API.

**Authorization truth — capability union with a live exchange** (r3
blocker 3). Two capability shapes:

- **Probe capability** (read-only, pre-binding): signed
  `{order_id, subject: {kind: "identity_query", email | tp_athlete_id |
  candidate_list_ref}, action: probe|inspect, audience, iat, exp, jti}` —
  no `tp_athlete_id` required, because probing is how one is found. Can
  never authorize a write.
- **Mutation capability** (apply / verify / rollback — rollback is a
  separate capability requiring explicit operator action): signed
  `{order_id, tp_athlete_id, generation_revision, model_seal, action,
  audience, iat, exp, jti}`.

**Cancellation/regeneration cannot be outrun** (a signed token stays
cryptographically valid after the webhook cancels the order): after
acquiring the lease and before mutating, the worker performs an **online
exchange**: it presents the capability jti to the webhook, which
re-validates its authoritative state and returns a **short-TTL execution
grant** bound to the worker's fencing token. No live grant → no mutation.
The exchange predicate is **action-specific** (r4 blocker 2 —
APPROVED-only would deadlock resume/verify/rollback):

| action | predicate | grant effect |
|---|---|---|
| apply (initial) | status APPROVED, revision current, seal matches | grant issuance **atomically** transitions APPROVED → APPLYING and binds the attempt record to this grant + fencing token |
| apply (resume) | status APPLYING, same attempt (jti + request digest) | new grant, **new fencing token**, bound to the same attempt — this is the re-grant rule for `accepted`/`running` crash recovery |
| verify | status APPLYING, APPLIED, or APPLIED_ATTESTED | read-only grant |
| rollback | status APPLYING, APPLIED, or CANCELLED-with-compensation-pending; operator capability required | grant bound to a compensation record |

**Quiescence barrier** (r5 blocker 1: grant expiry alone does not prove a
started batch has stopped). Grants are short-TTL and carry the order's
**execution epoch**; the authoritative state holds
`{cancel_requested, execution_epoch}`. Normative rules:

1. The worker revalidates `{grant unexpired, epoch current}` against the
   webhook **immediately before every remote mutation** — not per batch.
   (Each mutation is a seconds-scale browser operation; one lightweight
   authenticated check per mutation is acceptable and required.) Epoch
   mismatch or expiry → stop, flush the journal, release the lease,
   acknowledge.
2. Cancellation/regeneration sets `cancel_requested` and increments
   `execution_epoch`; no new grant is issued afterward.
3. **CANCELLED may finalize (and F4 compensation may begin) only after the
   worker has acknowledged stop/completion and released the lease.** If the
   worker is unreachable, expiry may substitute for acknowledgement only
   after the last grant's expiry **plus `M`** — a fixed spec constant, the
   maximum duration of one remote mutation (rule 1 guarantees no mutation
   *starts* after expiry, so expiry + M bounds the last possible write).
4. Both post-barrier reads — the `landed[]` journal slice F4 compensates
   from, and the `effective_remote_inventory` snapshot a supersession diff
   is built against (D0) — are taken **after** this barrier, never before.

Compensation never races a live writer; both sides serialize on the same
per-`tp_athlete_id` lease. This gives the webhook a revocation point
without giving the worker fulfilment authority (the worker's lease/journal
are operational state, not authority).

**Crash-safe retry — a durable operation record, not "consumed"** (jti
burn-then-crash would strand the order as replay-rejected): the worker
persists, per jti, `{status: accepted|running|succeeded|failed,
request_digest, fencing_token, results}`. Ordering is: acquire lease →
persist `accepted` → online exchange → `running` → mutate with per-
operation intent/result records → `succeeded|failed`. A retry bearing the
same jti and `request_digest` against an `accepted`/`running` record
**resumes reconciliation** (D3 lookups decide what already landed); it is
rejected as replay only when the record is `succeeded`/`failed` (the
recorded result is returned) or the digest differs. Lease-acquisition
failure before `accepted` leaves nothing consumed.

**Mutual exclusion:** a durable per-`tp_athlete_id` lease (fencing token,
TTL + renewal) serializes mutating operations. Lookup-before-write is not
mutual exclusion; the lease is.

Credentials + TOTP seed in a secrets store; rotation and revocation runbook
(incl. "TP password changed"); distinct rotating caller secrets (not
`CRON_SECRET`); TLS; egress allowlisted to TP hosts; payload limits;
immutable redacted audit log; rate limits. Token expiry is the worker's
problem: one retry then loud failure. **Canary before write** (fixture
athlete probe; proves SPA shape, external-id round-trip, HR/RPE structure
acceptance) gates every apply batch.

### D2. Identity resolution and account inspection

Inputs: order email; optional "TrainingPeaks account email, if different"
intake field (single question, not gated on the v2 rewrite); coach-entered
identity on the review page. Outcomes: `bound` / `multiple-candidates`
(coach selects) / `not-coached` (`ATHLETE_UNLINKED`) / `not-found`
(`ATHLETE_NO_ACCOUNT`) / `unresolved`. Binding → `platform_identity` in
state (S1 order-scoped); **required before APPROVED only when `d2_active`
is true** (the identity probe has actually run). When D2 is inactive,
automated apply is not live: approval is the plan decision, and the
review page / coaching brief / pre-delivery checklist carry the
TrainingPeaks loading steps. Manual orders still record delivery evidence
at APPLIED. Probes revalidate immediately before write.

**Resolutions are state-changing commands (codex r2 blocker 4).** The plan is
generated from intake before review (`generate_athlete_package.py:2989-3052`),
so a resolution that changes an anchor *must* re-enter generation:

- `use-tp-value` → writes the inspected value into canonical inputs → new
  revision, regeneration, re-review. (The seal makes skipping this fatal.)
- `update-from-intake` → emits a `threshold_update`/`zone_update` operation
  (with before-image) into the apply contract; plan unchanged.
- `manually-corrected` → requires worker readback confirming the corrected
  value before approval proceeds.
- `cannot-resolve` → blocks.

Approval is legal only when, for the plan's control metric, the sealed plan
value and the inspected account value are consistent under the chosen
resolution. Dormancy/cosmetic mismatches stay soft.

### D3. Apply — reconciliation per operation type

The pinned adapter checkpoints after POST (`adapter.py:57-60`), sends an
unproven `Idempotency-Key` (`:44-45`), has no
threshold/zone/delete/rollback/intent primitives (verified absent), and its
fake server self-dedupes (`test_trainingpeaks_adapter.py:31-39`). r3
protocol:

- **Persisted intent** before each POST; **remote object id persisted** after
  every lookup/create (the embedded external-id marker is a search key, not
  the authority — user edits can strip it).
- **Calendar objects** (workouts, notes, attachments, tasks): pre-write
  window listing; absent → create; one match, same digest → record, skip;
  one match, different digest → the fixed per-kind policy in D0 (dated
  kinds: update in place via `remote_id`);
  **multiple matches → stop, coach repair page** (fail closed). Ambiguous
  timeout → lookup-then-decide; zero-after-ambiguous-write → stop.
- **Account singletons** (threshold/zone): before-image captured at
  inspection; compare-and-swap semantics (verify current == before-image
  before write, verify after-image after); restore-on-rollback only if
  current still equals this operation's after-image; else stop and report.
- **Entitlements**: grant-if-absent; rollback strategy `none` (revocation is
  a coach action; recorded as non-reconcilable).
- Apply preflight: capability valid + exchanged (D1), lease held, canary
  green, identity revalidated, seal match.
- **`APPLYING` is a real state** (r3 blocker 6: representing partial remote
  mutation as APPROVED lets F4 classify its refund as "pre-APPLIED" and
  skip rollback, leaving landed objects on the athlete's account). The
  transition sequence is APPROVED → APPLYING (attempt record created:
  jti, contract digest, started_at) → APPLIED. Each landed operation is
  appended durably to the attempt's `landed[]` (op_id, remote_id, result)
  as it completes, and the `effective_remote_inventory` (D0) is updated by
  the same deterministic transition in the same write. **APPLIED means the
  complete required operation set verified by readback** — never
  "something landed."
- Partial failure: state stays `APPLYING` with the exact landed journal
  and effective inventory;
  coach notified (outbox); retry resumes reconciliation under the same
  jti/lease; explicit coach choices from `APPLYING`: resume, rollback
  landed set (compensation), or manual completion (typed inventory).
  Rollback proven against fake server *and* canary athlete before any
  customer use.
- **Cancellation inspects landed operations, never the top-level status**
  (F4): any state whose attempt records show landed operations gets D3
  compensation regardless of whether APPLIED was reached.
- **Manual fallback (permanent) — honestly named** (r4 blocker 4: a typed
  inventory without readback is a coach assertion, not a verified calendar
  fact, and must not share a status whose definition is "complete set
  verified by readback"). "I imported manually" records
  **`APPLIED_ATTESTED`** — a distinct status between APPROVED and CONFIRMED
  carrying a typed inventory (what was placed, where) + the attesting
  credential. If worker readback subsequently verifies the complete set, it
  upgrades to APPLIED. `APPLIED_ATTESTED` grants the same downstream
  release rights as APPLIED (the coach is the delivery authority for manual
  orders — S5 components, E1, E2 all accept either status) but: it is
  flagged `non_reconcilable` unless the inventory carries remote ids,
  **automated rollback promises (F4) exclude non-reconcilable
  attestations** (compensation is a recorded coach checklist), and
  provenance always distinguishes attested from verified (I5).
- Prior ticket adopted in full
  (`docs/followups/AUTOMATED_TRAININGPEAKS_FULFILLMENT_TICKET.md:18-29`).

### D4. Endure — same gate or off

Codex r2 blocker 11: at the pinned commit an `endure`-target order is pushed
**immediately after generation, before any approval**
(`webhook/app.py:2000-2009`), by a helper that "NEVER raises, never fails
the order" (`:1918-1920`), silently falling back to TP and owning its own
invitation email (violating I2, I3, I6, and I4). r3:

- **Phase 1: the pre-approval Endure push is disabled.** `delivery_target`
  is preserved into `delivery_platform` (S1) and the order proceeds through
  the normal gate.
- Endure re-enable is Phase 5 work under identical rules: sealed content,
  APPROVED precondition, apply evidence + readback, rollback contract,
  release components, no platform-initiated athlete email while I4 stands
  (Endure's invitation becomes part of §E2's coach-sent flow or is
  explicitly deferred).
- Fixtures: athlete-m variants for `trainingpeaks` and `endure`, including
  endure-failure-without-silent-TP-fallback (fallback requires coach
  authorization).

---

## Workstream E — release

### E1. Guide publish — gated, revocable, deterministic

Publishing is a **release component** (S5): enqueued on APPLIED, never
before APPROVED; unpublished draft is review-bundle content. Supersession/
revocation defined for regeneration and cancellation; published revision
recorded in component evidence. **Privacy is a Phase 5 prerequisite** with a
safe default: until decided, no public URL — guide ships in the customer ZIP
and as the draft attachment only. Mechanics: deterministic PDF (pinned
render container + fonts), unconditional `noindex` for any athlete guide
that is published, publish + verify scripted.

### E2. The drafted email — typed evidence

After APPLIED, the `draft` release component creates a Gmail draft
(`gmail.compose`, OAuth refresh token in the secrets store, documented
consent flow, brand-keyed sender per F5): athlete-addressed, brand voice,
~268-word shape, guide attached, plan summary. Never auto-sent.

`/api/confirm`'s customer send is removed. CONFIRMED requires **typed
evidence** (codex r2 blocker 9), validated server-side:

- `provider_verified`: `{provider: gmail, message_id, draft_id, from, to,
  sent_at, revision, body_digest, attachment_digests}` — the server fetches
  the message via the Gmail API and verifies recipient (order email),
  sender (brand alias), sent state, revision, and attachment digest against
  the sealed guide. Arbitrary/foreign/unsent/stale-revision ids rejected.
- `manual_attestation` (r3 blocker 8: optional digests let CONFIRMED record
  only that *something* was sent): the system supplies the expected values —
  at draft creation the sealed `{body_digest, attachments: [{filename,
  sha256}]}` is recorded in the `draft` release component — and the coach
  attests against them: `{channel, recipient, sent_at, revision,
  expected_body_digest, expected_attachment_digests, used_exactly:
  true|false, deviation?, reason_not_verified}`. All digest fields are
  **required** (copied from the release component, not typed by hand).
  `used_exactly: false` additionally requires the **actual** sent content
  (r4 blocker 6: expected digests plus free text cannot identify what was
  delivered): the coach supplies the sent body and attachment set through
  the review surface, which computes and stores
  `{actual_body_digest, actual_attachments: [{filename, sha256}],
  content_snapshot_ref}` and the expected-vs-actual comparison result; the
  reviewed override (a second confirm action) binds to that actual
  evidence and the revision — never a silent CONFIRMED. Non-email channels
  are legal but recorded as such with the same content binding. Honest
  labeling stands: attestation, not verification.

`confirm_after_send`'s locked exactly-once shape (`fulfillment_state.py:
215-231`) is retained as **exactly-once state recording** with its callback
semantics explicitly changed: in v2 the callable **validates typed evidence
under the lock and never invokes an athlete send** (the pinned Boolean
`send()` performed the send; that behavior is removed with the customer
send). The send is human; the primitive records it once.

---

## Workstream F — defect closures and flow prerequisites

- **F1 — Guide semantic validation**: qualifying frozen race snapshot
  (start/avg elevation over threshold — trigger shape
  `training_guide_builder.py:225-241`) must yield the altitude section in
  the rendered guide; post-render blocker on failure.
- **F2 — Fueling truth, full inventory**: `GUT_TRAINING_PHASES` hardcoded
  bands (`calculate_fueling.py:94-116`) replaced by plan-derived labels —
  **and** the guide's independent fixed carb figures
  (`training_guide_builder.py:1367, 1668-1776, 2939-2941` et al.) are
  inventoried and classified: *personalized prescription* (must come from
  the single canonical fueling prescription), *generic education* (must be
  labeled "general guidance, not your target" — the pattern `:2941` already
  uses), or removed. Replay asserts label/plan-week agreement and no
  personalized figure that disagrees with the canonical prescription.
- **F3 — Polyline**: unrounded cumulative time (bug `tp_polyline.py:62`,
  documented overshoot `:31-34`), clamp to `[0,1]`, monotonic; goldens
  replaced (`test_tp_polyline.py:26`); property tests. **This repo's copy is
  Phase 1; the vendored copy in `gravel-god-training-plans` is tracked as a
  named cross-repo follow-up with owner (coach/pipeline) — it does not gate
  this repo's Phase 1.**
- **F4 — Cancellation, refund, regeneration-after-apply** (Phase 5
  prerequisite), concretely: `CANCELLED` status legal from any state,
  preserving terminal facts (approval/application/confirmation/compensation
  history). The refund branch is decided by **landed operations, not
  top-level status** (see D3): no landed operations → CANCELLED, tokens
  revoked (jti), artifacts unexposed; any landed operations (including an
  order still in `APPLYING`) → compensation workflow first: rollback of
  reconcilable operations (D3), guide unpublish (E1), draft deletion if
  unsent; `non_reconcilable` applications instead produce a recorded coach
  cleanup checklist. Regeneration after APPLIED requires an explicit coach
  choice: *supersede* (new revision, re-review, re-apply as the D0
  supersession diff — logical-id matched, predecessor-linked) or *abandon*
  (CANCELLED + compensation). A revision bump alone is never claimed to
  clean a calendar.
- **F5 — Multi-brand**: sender identity, guide host, templates, secrets
  brand-keyed; unknown brand fails closed (blocker), replacing
  default-to-gravelgod.
- **F6 — Weeks sold vs delivered**: deliver the purchased week count when
  the calendar allows (Week 1 never starts before generation;
  `clamp_past_start=True`). 1+ week paid plans are valid; the hard
  generator cap is 52 weeks; there is no 4/6/8 minimum. If the race is
  too soon to fit purchased weeks without past sessions, deliver the
  maximum weeks that fit and emit confirmation `WEEKS_CALENDAR_SHORT`
  (not a critical blocker). `WEEKS_MISMATCH` remains a waivable blocker
  when generated ≠ purchased for a **non-calendar** reason (SKU/mapping/
  generator bug). Example: purchased 7, calendar allows 10+, generated 6.
- **F7 — intel-stats**: the fixed 24 h window (`webhook/app.py:4022-4042`)
  becomes `?hours=` (validated int, default 24, max 720; malformed/negative
  → 400) — `limit` is rejected as a design (one knob); ordering is
  deterministic (timestamp then id); reads span the monthly ledger files
  the window requires, not just current+previous; same auth as today;
  tests for bounds, malformed input, multi-month windows.

---

## The athlete-m fixture — exact contract

(r3 blocker 7: "exactly … ∪ whatever" is not a golden set; the device JSON
key did not exist; the schedule expectation contradicted its own disjoint
day lists; the week arithmetic was ambiguous.)

**Inputs**, checked in at `tests/fixtures/athlete_m/`:

- `intake.json` — the production questionnaire JSON shape (the one read at
  `webhook/app.py:1248-1275`) **plus the new `devices` field A2 adds to that
  schema** (string, verbatim form answer; the pinned schema has no device
  key — the markdown adapter hardcodes the line at `:1487`, which A2
  removes). Values: `ftp: ""`, `powerOrHr: "hr"`, `age: 45`,
  `hr_threshold: ""` (both fields exist in the pinned schema,
  `webhook/app.py:1251-1259`), `devices: "power meter, hr strap"`,
  long-ride days `["monday","tuesday","sunday"]`, interval days
  `["wednesday","thursday"]`, off-day `saturday`, 7–10 h budget, 7 weeks
  purchased, race `three-course-race` distance `"75 miles"`. A traversal
  test asserts the devices string survives JSON → markdown → parser and
  produces exactly `["power_meter", "hr_strap"]` post-A2 (multi-word tokens
  preserved by comma-only split). The race-day entry on Saturday 2026-09-19
  is legal despite the Saturday off-day (C2's normative race-day
  exemption).
- `race_snapshot.json` — frozen record: slug `three-course-race`, race date
  `2026-09-19`, three courses (55 mi / 75 mi / 89 mi), headline course
  89 mi / 7,500 ft, `verified_at: null` (stale provenance).
- `worker_probes.json` — canned D2 responses (consumed by the **Phase 4**
  golden, not Phase 1): account found, coached, age 19, FTP 197 W dated
  2019-05-01, LTHR 148 bpm dated 2019-05-01, expire 2019-11-18, zero
  workouts since 2019.
- `clock.json` — `order_created_at: 2026-08-04T17:00:00Z`, generation clock
  `2026-08-06T15:00:00Z`, athlete timezone `America/Denver`.
- **Determinism:** generation under the fixture is required to be
  deterministic (fixed clock injected; any RNG seeded with a fixture seed);
  the generated plan-dates output is itself a checked-in golden
  (`expected/plan_dates.json`) — plan W00 lead-in (2026-08-05 →
  2026-08-09, first workout dated **2026-08-05**) + paid weeks W1–W6,
  race-day entry on 2026-09-19, one HR field test in W1, ≥3 counted
  entries in race week.

**Phase 1 golden (`expected/phase1.json`) — literal, closed sets:**

- Status `BLOCKED_REVIEW`. Blockers **exactly** (ordered by rule id):
  `COURSE_UNRESOLVED` (non-waivable), `FTP_ESTIMATED` (non-waivable),
  `RACE_STALE`, `SESSION_PREDATES_GENERATION` (the 2026-08-05 W00 workout
  precedes the 2026-08-06 generation date in `America/Denver`).
  Calendar-forced shortfall is confirmation `WEEKS_CALENDAR_SHORT` (6 paid
  weeks generated of 7 purchased; Week 1 Monday 2026-08-10 through
  race-week Monday 2026-09-14 is 6; W00 excluded per F6).
  `WEEKS_MISMATCH` remains for non-calendar count bugs only.
- Blockers that must **not** fire: `NO_RACE_DAY_WORKOUT` (race-day entry
  exists), `THIN_RACE_WEEK` (counted entries ≥ 3), `DUPLICATE_FIELD_TEST`
  (one test), `SESSION_PREDATES_ORDER` (2026-08-05 is after the
  2026-08-04 order date — this discriminates the two date rules),
  `SCHEDULE_CONTRADICTION` (the only entry on the stated Saturday off-day
  is the race-day entry, which C2's normative race-day exemption permits),
  `WEEKS_MISMATCH` (the 7→6 shortfall is calendar-forced).
- Required confirmations **exactly**: `SCHEDULE_MISMATCH_CONFIRM` (the
  golden plan places a VO2 session on Sunday, a long-ride-only day),
  `WEEKS_CALENDAR_SHORT` (purchased 7, delivered 6, calendar max 6). D2
  confirmations do not appear here — worker probes are Phase 4 (r4 blocker
  5: a phase's closed set may contain only outputs that exist in that
  phase).
- Surface assertions: coach email lists the four blockers with waivability,
  contains no import steps and no confirm control; review bundle contains
  zero `.zwo` entries; customer download → 409; order-status "processing";
  `/api/confirm` → 409; profile devices == `["power_meter", "hr_strap"]`
  (from the form string only); fueling phase labels reference only
  W00/W1–W6; an approval attempt whose waiver covers all four ids is
  rejected (two are non-waivable).

**Phase 3 golden (`expected/phase3.json`):** `FTP_ESTIMATED` absent from
blockers; `power_basis: none` present as a confirmation; zero watt figures
in every artifact (fueling.yaml, guide, preview, plan payloads, ZIP
listing); HR field test in W1; all Phase 1 negative assertions still hold.

**Phase 4 golden (`expected/phase4.json`):** with `worker_probes.json`
active, required confirmations **exactly**: `D2_DEMOGRAPHIC_AGE_MISMATCH`,
`D2_THRESHOLD_LTHR_STALE_MISMATCH`, `SCHEDULE_MISMATCH_CONFIRM` (carried),
`WEEKS_CALENDAR_SHORT` (calendar-forced 7→6). D2 threshold staleness
(`lthr`: account 148 bpm dated 2019 for control metric `hr`); D2
demographic mismatch (account age 19 vs intake age 45). Identity
resolution outcome `bound`; approval remains rejected until the D2 items
carry a resolution.

No real person's name, email, ids, or free text anywhere in the fixture.

---

## Rollout — dependency-ordered

Dependency graph (prerequisite → dependent): S1/S2/S6 → everything;
transitional validator inputs (PlanIR + tp_manifest) → Phase 1 validator;
canonical model (A1.1) → D0 contract → D3/worker apply; D1 worker → D2
probes → D3; S5 outbox → E1/E2; F4+F5+privacy decision → Phase 5.

- **Phase 0 — hygiene.** Delete `plan-truth-fixes` and `plan-ir-v0` (local
  and remote; housekeeping, not a gate). Clean `main` checkout.
- **Phase 1 — blocked means blocked.** S1, S2 (seal over transitional
  artifacts), S4, S6; B1–B4 (incl. disabling the pre-approval Endure push,
  D4); typed tokens; post-render validator on PlanIR+tp_manifest; new
  blockers; A2 (incl. source hardcode); F2, F3 (this repo), F6, F7.
  *Gate:* athlete-m Phase 1 golden set passes.
- **Phase 2 — review surface.** S3, C1, C2 surface, C4; approval snapshot
  with values; policy enforcement. *Gate:* one real order approved entirely
  on the page with a complete, seal-bound approval snapshot.
- **Phase 3 — truthful power.** A1 (canonical model + projections, intake,
  fueling), A3, D0 contract *as an offline projection with schema +
  migration parity tests against the fake server*. *Gate:* athlete-m Phase 3
  + HR/LTHR/RPE fixtures pass offline. (Live TP acceptance explicitly NOT
  gated here.)
- **Phase 4 — worker, read-only.** D1 (probe/inspect + capability
  validation), D2 feeding C. *Gate:* live identity binding + inspection
  confirmations for a real order; zero writes; scheduled canary probe green.
- **Phase 5 — apply + release.** D3, D0 cutover (JS driver retired after
  parity), D4 Endure decision (re-enable under the gate, or defer), S5
  components, E1, E2. *Prerequisites:* F4, F5, guide-privacy decision;
  rollback + HR/RPE acceptance + external-id round-trip proven on the
  canary athlete. *Gate:* one real order end-to-end: generated → reviewed →
  approved → applied → verified → guide released → draft in Gmail → coach
  sends → CONFIRMED with provider-verified evidence.

---

## Out of scope (tracked)

- Questionnaire v2 (`docs/QUESTIONNAIRE_V2_SPEC.md`, NO-GO, rewrite against
  the real intake path). D2's single TP-email field and A1's null-FTP safety
  do not wait for it.
- `courses[]` schema — `docs/followups/RACE_COURSES_SCHEMA_TICKET.md`;
  interim: non-waivable `COURSE_UNRESOLVED` + facts-omitted remediation.
- Archetype selection quality (handoff §5.7).
- `gravel-god-training-plans` polyline copy (named cross-repo follow-up, F3).

## Open decisions for the coach

1. Guide privacy (Phase 5 prerequisite; safe default: no public URL).
2. `WEEKS_MISMATCH`: fix pricing or generation (blocker forces the
   conversation per order until decided).
3. Gravel Grit: four notes vs plan 417473.
4. Endure: re-enable under the gate in Phase 5, or defer.

---

## Appendix 1 — disposition maps

**r8 blocker → r9 (final round; codex verdict GO-WITH-CONDITIONS):**

| r8 | Disposition |
|---|---|
| 1 positional completeness/matrix collision | Absent-singleton branch split (first-revision `update` requires `before_image`; verified first-revision `keep` forbids it, D2 inspection digest); entitlement-keep and both singleton predecessor rules keyed to effective-inventory existence, not historical origin; first/subsequent-revision schema tests required for both adopted-keep branches; stale D3 "landed inventory" phrase corrected |

**r7 blockers → r8 (this revision changed nothing else in substance):**

| r7 | Disposition |
|---|---|
| 1 stale S2 digest formula; entitlement-keep digest source | S2 defers to D0's per-disposition definition; keep-digest formula names the inventory entry when present, else the D2 inspection snapshot (entitlements: `{product_id}`) with recorded provenance |
| 2 predecessor type vs positional kinds; blanket absent→create | Common shape: `predecessor.remote_id` is `str | null` — required string for dated kinds, null for positional kinds; completeness rule rewritten kind-aware (dated create; singletons positional update/keep, never create; entitlements create-or-keep per inspection) |
| 3 inventory schema/transitions not total | Inventory schema gains `payload_snapshot_ref`; closed transition table covering every successful operation and compensation, including install-on-absent for first-revision singleton updates and verified keeps |

**r6 blockers → r7:**

| r6 | Disposition |
|---|---|
| 1 field collisions (keep digest formula; first-revision singletons) | D0: per-kind × per-disposition field matrix is the single normative authority; `expected_digest` defined per disposition (keep copies the desired digest despite null payload); `predecessor` required exactly when an effective-inventory record exists — first-revision positional singletons and pre-existing entitlement keeps carry `predecessor: null` with `before_image`/inspection digest |
| 2 journal ≠ inventory | D0/D3: `landed[]` stays the compensation journal (F4's input); a materialized `effective_remote_inventory` with deterministic per-operation/per-compensation transitions is the supersession authority; snapshot taken after D1's barrier; absent entries get no disposition (create if desired, remain absent if not) |

**r5 blockers → r6:**

| r5 | Disposition |
|---|---|
| 1 grant expiry ≠ quiescence | D1 quiescence barrier: per-mutation epoch/grant revalidation, no-new-batch after cancel, CANCELLED finalizes only after worker ack (or expiry + max-mutation-duration `M` when unreachable), landed snapshot taken after the barrier |
| 2 keep unverifiable / update-delete uncompensable | D0: `keep` carries `expected_digest`; `update`/`delete` carry `prior_payload` with `restore_prior_payload`/`recreate_from_prior_payload`; allowed dispositions per kind (singletons update/keep; entitlements create/keep, non-reconcilable); completeness measured against the landed inventory; never-landed prior ids are `create` |

Also folded from r5 non-blocking: transitional Phase 1 seal steps renumbered
(S2); `APPLIED_ATTESTED`/`APPLYING` added to B3's literal status list; D3's
"operation policy" wording now cross-references D0's fixed policy; the
fixture's `SCHEDULE_CONTRADICTION` negative assertion cites the race-day
exemption as the operative reason.

**r4 blockers → r5:**

| r4 | Disposition |
|---|---|
| 1 seal finalization graph | S2: single acyclic sequence (model_seal from sources incl. contract *payload* → contract file emitted with seal → artifact bytes → immutable release manifest → approval); `expected_digest` defined once (D0); post-approval projections in separate immutable component manifests; Phase 1 hash input = artifacts array only |
| 2 exchange predicates | D1: action-specific predicate table; initial-apply grant atomically creates the APPLYING attempt; resume re-grant with new fencing token; verify/rollback predicates; short-TTL batch renewal; CANCELLED finalizes only after all grants expired/revoked-and-acked, serialized on the same lease |
| 3 supersession not serializable | D0: `disposition` (create/update/keep/delete) + `remote_marker` + `predecessor` in the common shape; per-kind logical keys incl. attachments; top-level before_image; complete-supersession-document validation rule; calendar_dates clarified as verification inventory |
| 4 manual APPLIED | D3/S5: `APPLIED_ATTESTED` status — release-equivalent, provenance-distinct, upgradeable to APPLIED on verified readback; APPLIED strictly means readback-verified |
| 5 fixture contradictions | C2 race-day off-day exemption (normative); intake pins `age: 45` + empty `hr_threshold`; probes pin LTHR 148; D2 confirmations moved to a new Phase 4 golden |
| 6 changed-content evidence | E2: `used_exactly: false` requires actual body/attachment digests + snapshot + stored comparison; confirm primitive explicitly validates evidence under lock and never sends |

**r3 blockers → r4:**

| r3 | Disposition |
|---|---|
| 1 self-referential seal / Phase 1 authority | S2: two layers (`model_seal` with seal-fields-zeroed normalization + `release_manifest` of per-artifact digests); Phase 1 seals bytes of all eagerly built artifacts explicitly |
| 2 outbox not crash-atomic | S5: outbox is a field of the state JSON, committed in the one atomic replace; idempotent consumers; kill-point tests |
| 3 capability lifecycle | D1: capability union (probe subject without tp_id); one-time online exchange before mutation (revocation point); durable per-jti operation record with accepted/running resume semantics |
| 4 contract not normative | D0: full per-kind payload/readback/rollback table, canonical digest rule, fixed update-vs-stop policy, version compatibility — in the spec |
| 5 revision-scoped identity | D0: `logical_id` (cross-revision) vs `op_id` (attempt) vs optional `remote_marker`; supersession diff with predecessor links and full disposition requirement |
| 6 partial apply = APPROVED | D3: `APPLYING` state with durable landed[] inventory; APPLIED = complete verified set; F4 branches on landed operations, not status |
| 7 fixture not exact | athlete-m: closed literal blocker/confirmation sets, negative set, checked-in plan-dates golden, deterministic generation, named `devices` JSON field with traversal test, week arithmetic fixed (W00 + 6 vs 7 purchased) |
| 8 manual evidence unbound | E2: required system-supplied digests, `used_exactly` + deviation + reviewed override |
| 9 v1 migration | S1: fail-closed quarantine with `legacy_order_id`, no slug inference, manual binding, token revocation |

**r2 disposition maps (from r3):**

**r2 new blockers → r3:**

| r2 | Disposition |
|---|---|
| 1 dependency inversions | Rollout rebuilt with explicit graph; validator gets versioned transitional input; identity binding platform-scoped; canary gates Phase 5, not 3 |
| 2 approval/content TOCTOU | S2 content seal; seal-bound approval, downloads, worker |
| 3 digests not values | S3 stores typed values; sensitivity handled via A3 enforcement + server-only state file |
| 4 resolutions don't change the plan | D2 resolutions are state-changing commands; anchor changes force regeneration |
| 5 apply contract not a schema | D0 normative shape, full operation inventory, ordering, before-images, parity tests |
| 6 broker trust/replay/lease | D1 webhook-issued single-action capabilities, jti consumption, per-athlete lease with fencing |
| 7 singleton rollback | D3 per-type reconciliation; CAS + before-images; manual applies flagged non-reconcilable and excluded from F4 promises |
| 8 APPLIED vs release side effects | S5 release components + outbox; APPLIED = calendar fact only |
| 9 arbitrary confirm evidence | E2 typed evidence union; server verification; attestation labeled as such |
| 10 unreachable emails | B2: review page is the control surface; outbox produces notices; no bespoke APPROVED/APPLIED emails |
| 11 Endure bypass | D4: pre-approval push disabled Phase 1; re-enable only under the full gate |
| 12 no order identity | S1 order_id everywhere + tests |
| 13 blocker replace vs append | S6 namespaced merge op under lock |
| 14 rule definitions fail | C2: counted-kinds enumeration; SESSION_PREDATES_GENERATION with timezone semantics |
| 15 waivable "hard" blockers | S4 waivability policy; non-waivable set; facts-omitted remediation; negative tests |

**r2 partials/not-resolved → r3:** r1-1 (lease, persisted remote ids,
ambiguity rules — D1/D3); r1-2 (schema + parity — D0); r1-3 (canary timing —
A1.1/Phase 5); r1-6 (validator input versioning — C2); r1-8 (values — S3);
r1-10 (order identity — S1); r1-12 (write-back — D2); r1-13 (trust mechanism
— D1); r1-16 (exact fixture contract — athlete-m section); r1-19 (F7 API
chosen); r1-21 (S4 non-waivable + remediation); r1-22 (F4 concrete states +
non-reconcilable exclusion). Non-blocking r2 items folded: F2 inventory
(nb-2), A2 source hardcode (nb-3), jti revocation (nb-4), F3 cross-repo
pinning (nb-5), fixture contract (nb-6), F7 API (nb-7), A3 enforcement
(nb-8).

## Appendix 2 — code anchors (origin/main @ af284c2)

| Fact | Anchor |
|---|---|
| FTP fabrication (intake) | `athletes/scripts/intake_to_plan.py:829-842` |
| `ftp_estimated` email-only | `intake_to_plan.py:2854, 2970` |
| FTP re-fabrication (fueling) | `athletes/scripts/fueling_policy.py:102-104, 152-154` |
| Device split | `intake_to_plan.py:506-508` |
| Device hardcode (source) | `webhook/app.py:1487`; `tp-skus/generate_skus.py:82` |
| Day-lists are availability | `intake_to_plan.py:1033-1077` |
| Gate assembly | `intake_to_plan.py:3307-3330` |
| State-write downgrade | `intake_to_plan.py:3340-3345` |
| Generation order (profile→ZWO→guide→IR) | `generate_athlete_package.py:2989-3052, 3124-3131` |
| Both manifests emitted | `generate_athlete_package.py:3142-3151` |
| Compliance gate pre-render | `generate_athlete_package.py:753-767`; `block_compliance.py:78-90, 351-356` |
| PlanIR ZWO-glob / power-only / percentOfFtp / synthesized rest | `plan_ir.py:483-503, 56-63, 362, 455-464, 500-503`; `test_tp_projection.py:171-176, 214-231` |
| Notify ignores state; single send | `webhook/app.py:2011-2025` |
| Import steps + confirm curl | `webhook/app.py:482-483, 512, 576` |
| Full zip contains workouts/ | `webhook/app.py:1682, 1719-1722` |
| Download type escalation; month token | `webhook/app.py:2226-2266, 1764-1788` |
| Order-status | `webhook/app.py:2280` |
| Transition endpoint (secret + typed name; no metadata) | `webhook/app.py:2380-2397` |
| Status endpoint | `webhook/app.py:2404` |
| Confirm sends + fails closed | `webhook/app.py:2437-2459` |
| Endure pre-approval push | `webhook/app.py:1918-1926, 2000-2009` |
| intel-stats 24 h | `webhook/app.py:4022-4042` |
| State machine v1 (waiver/apply/confirm/write/set/replace) | `webhook/fulfillment_state.py:187-196, 199-211, 215-231, 124-148, 153-165` |
| Adapter checkpoint-after-POST; no rollback primitives | `delivery/trainingpeaks/adapter.py:44-45, 57-60, 67-94` |
| Fake server self-dedupes | `athletes/scripts/test_trainingpeaks_adapter.py:31-39` |
| Two manifests | `tools/tp_apply_order.py:4-17, 50, 237-248`; `fulfillment_manifest.py:21-39, 67-80` |
| Fueling table + guide carb figures | `calculate_fueling.py:94-116`; `training_guide_builder.py:1367, 1668-1776, 2939-2941` |
| Polyline | `tp_polyline.py:31-34, 62`; `test_tp_polyline.py:26` |
| Altitude trigger | `training_guide_builder.py:225-241` |
| Prior ticket | `docs/followups/AUTOMATED_TRAININGPEAKS_FULFILLMENT_TICKET.md:18-29` |
