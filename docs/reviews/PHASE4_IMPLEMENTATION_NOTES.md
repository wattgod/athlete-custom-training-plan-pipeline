# Phase 4 implementation notes — read-only worker and D2 review flow

Date: 2026-08-09

Binding contract: `docs/SPEC_TRUSTWORTHY_FULFILMENT.md`, converged R9,
especially D1, D2, C's review/approval surface, the athlete-m fixture
contract, and the rollout entry for Phase 4.

## Scope and safety boundary

Phase 4 implements the complete offline path through the read-only worker
transport boundary and the D2 coach-review flow. It performs no TrainingPeaks
network or browser operation. The only executable worker operations are
`probe_athlete(identity)` and `inspect_account(tp_id)` against an injected
read-only transport.

`apply`, `verify`, and `rollback` exist on the worker interface and refuse
unconditionally. Mutation execution-grant exchange also refuses
unconditionally. The older webhook browser apply-grant issuer now refuses,
the authenticated status response issues no apply token or URL, and the
legacy apply-gate route always returns HTTP 409. Consequently neither a
valid Phase 4 capability nor an older route can authorize a remote write.

The legacy adapter, JavaScript driver, and `tp_apply_order` remain disabled.
No live TrainingPeaks, browser, external-network, email, Stripe, or worker
mutation action was attempted during implementation or verification.

## D1 — read-only session-service boundary

`delivery/trainingpeaks/worker_service.py` defines:

- `ReadOnlyWorkerTransport`, the operation boundary for `probe_athlete` and
  `inspect_account`;
- `CannedProbeTransport`, which consumes the checked-in
  `worker_probes.json` shape and performs no I/O beyond reading that fixture;
- `ReadOnlyWorkerService`, which binds each request to a verified capability
  and a durable replay record before invoking the transport;
- `CapabilityCodec`, with rotating `kid`-selected HMAC-SHA256 keys and exact,
  closed claim schemas;
- `ProbeExecutionStore`, an atomic, order-scoped, file-locked jti store; and
- the offline mutation exchange predicate plus explicit Phase 4 refusal
  stubs.

Probe claims are exactly:

```text
{order_id, subject: {kind: identity_query, exactly one of email |
 tp_athlete_id | candidate_list_ref}, action: probe|inspect,
 audience, iat, exp, jti}
```

Verification covers token encoding, header algorithm/type, `kid`, signature,
audience, exact action and claim shape, exact subject locator, issuance and
expiry, a 15-minute maximum lifetime, safe order ids, and jti syntax. The
request must exactly match the signed subject. A probe capability is rejected
for every mutation action.

Probe replay records use the D1 lifecycle
`accepted -> running -> succeeded|failed`, with a canonical request digest.
Writing each state uses fsync plus atomic replace while holding the per-record
lock. A retry with the same order/jti/digest returns its recorded successful
result (or its recorded failure); a different request digest fails closed.
The records are segregated by order id.

Mutation capabilities use the exact D1 shape:

```text
{order_id, tp_athlete_id, generation_revision, model_seal,
 action: apply|verify|rollback, audience, iat, exp, jti}
```

Their type and validation are implemented for Phase 5 reuse. The pure offline
exchange predicate pins the R9 action table: initial apply at `APPROVED`,
same-attempt apply resume at `APPLYING`, verify at
`APPLYING|APPLIED|APPLIED_ATTESTED`, and operator-authorized rollback at the
eligible apply/cancellation states. It additionally binds the authoritative
order, platform identity, revision, seal, cancellation state, jti, and request
digest. This predicate never issues a grant in Phase 4.

## D2 — identity, inspection, and state commands

`webhook/d2_identity.py` owns the D2 state extension and validates it on every
fulfilment-state load/write. Supported identity outcomes are `bound`,
`multiple-candidates`, `not-coached`, `not-found`, and `unresolved`.
Candidate selection is an authenticated state-changing review command. A
binding is stored as order-scoped `platform_identity`; automated-platform
approval requires it, while manual delivery remains governed by APPLIED
delivery evidence.

The automated identity outcomes map to the R9 policy:

- `not-coached` -> non-waivable `ATHLETE_UNLINKED`;
- `not-found` -> non-waivable `ATHLETE_NO_ACCOUNT`; and
- multiple/unresolved without a binding -> non-waivable
  `ATHLETE_IDENTITY_UNRESOLVED`.

Inspection stores typed account facts and emits the fixture-backed review
items:

- `D2_THRESHOLD_LTHR_STALE_MISMATCH`, required, for the account LTHR of
  148 bpm dated 2019-05-01 against an HR-controlled plan;
- `D2_DEMOGRAPHIC_AGE_MISMATCH`, required, for account age 19 versus intake
  age 45; and
- `D2_ACCOUNT_DORMANCY`, soft, for zero workouts since 2019.

Age, FTP, LTHR, expiry, and workout-history observations remain in
authenticated server state. Their registry entries are typed
`externally_observed`, sensitive derived values with source, method/version,
observed time, dependency references, confidence, and review policy. External
status surfaces continue through the Phase 3 recursive projection, so these
values are not exposed by the operational API.

All four resolution choices execute server-side state commands:

1. `use-tp-value` copies the inspected value to canonical input overrides,
   invalidates the seal and approval, advances the authoritative revision,
   records a durable regeneration requirement, and re-enters the normal
   generation job. The regenerated review item carries the new sealed plan
   value.
2. `update-from-intake` preserves the plan anchor and emits a D0
   `threshold_update`/`zone_update` desire with the inspected before-image.
   The normal generation path builds it into the apply contract; no operation
   is executed in Phase 4.
3. `manually-corrected` records a pending readback requirement and leaves
   approval blocked. `record_manual_readback` accepts only exact worker
   evidence and records its probe jti before clearing the requirement.
4. `cannot-resolve` creates a non-waivable D2 blocker.

Any sealed command that changes generation inputs or the apply contract first
persists the new non-approvable state. Only then does the review route queue
the long generation job. Queue/source failures therefore leave a loud durable
`D2_REGENERATION_REQUIRED` condition rather than an old approval or seal.
Candidate binding uses this same path.

Approval validation is server-side. It requires an automated-platform
binding, no pending regeneration/readback, a resolution on every required D2
item, and consistency among the selected resolution, inspected account value,
and sealed control-metric value. A posted generic confirmation cannot bypass
these checks.

## Review surface

The authenticated Phase 2 review page now renders an identity panel with the
outcome, bound id, candidates, and candidate-binding control. Typed D2 items
render resolution selectors that post to dedicated authenticated, CSRF-bound
commands. Approval snapshots record the chosen resolution as
`resolved:<choice>` and remain bound to the current revision and review
catalog digest.

## athlete-m Phase 4 fixture contract

The checked-in `tests/fixtures/athlete_m/worker_probes.json` already matched
the converged R9 literal fixture and was therefore retained byte-for-byte. The
Phase 4 pipeline activates it only when `GG_WORKER_PROBES_FIXTURE` and a
distinct 32-byte-or-longer `GG_WORKER_CAPABILITY_SECRET` are explicitly
provided. It then exercises the real signed-capability, replay-store, and
canned-transport path.

`tests/fixtures/athlete_m/expected/phase4.json` pins:

- identity outcome `bound` with `fixture-athlete-m`;
- the unchanged Phase 3 blocker set;
- exactly `D2_DEMOGRAPHIC_AGE_MISMATCH`,
  `D2_THRESHOLD_LTHR_STALE_MISMATCH`, and
  `SCHEDULE_MISMATCH_CONFIRM` as required confirmations;
- account LTHR 148 bpm dated 2019-05-01 for control metric `hr`; and
- account age 19 versus intake age 45.

The golden also proves unresolved D2 selections reject approval, preserves
all Phase 1 negative assertions, retains the Phase 3 null-power/no-watts
contract, and checks the authenticated identity/resolution surface. The more
general Phase 3 `POWER_BASIS_NONE_CONFIRM` is removed once the inspected LTHR
provides the account-specific HR decision.

## Deviations and remaining live gate

There is no offline contract deviation. The real TrainingPeaks session/browser
transport, scheduled canary, and live identity/inspection proof are expressly
the Phase 4 rollout's human-scheduled LIVE gate and are not fabricated here.
The optional webhook exchange endpoint for probes was not needed because the
read-only worker verifies and consumes signed capabilities directly. Apply
grant issuance remains deliberately absent/refused until Phase 5.

## Verification evidence

- Focused worker, D2, review, fulfilment-state, and legacy-gate suite:
  **92 passed**.
- Complete sandbox suite: **2,522 passed, 87 skipped, 21 warnings, 0
  failed**.
- Opt-in production acceptance with a writable `HOME`: **36 passed, 4
  skipped, 4 failed**. The four failures are the unchanged mandatory PDF
  presence/structure checks for Gravel Full Gym and Masters in this sandbox,
  which has no PDF engine. The Roadie HTML fallbacks and package cases account
  for the four expected skips.
- The isolated Phase 3 baseline and Phase 4 fixed-clock acceptance builds each
  contain exactly **253 ZWOs** (89 Gravel, 77 Masters, 41 Road Fondo, 46 Road
  Climb). Their sorted per-file manifests are identical and hash to
  `e82ebcd550b7cbedc46b9c0d8ae4ff2a955bbc690a26231f110797344c885c7c`.
- `python3 -m compileall -q delivery/trainingpeaks webhook athletes/scripts`
  and `git diff --check` pass.

The sandbox-forbidden loopback/PDF checks and the scheduled live read-only
canary remain external verification items. No push is part of this phase.

## R1 blocker disposition — 2026-08-09

Review: `docs/reviews/PHASE4_IMPLEMENTATION_CODEX_R1.md`.

All four blockers were accepted as valid; there are no disputes.

| R1 blocker | Disposition | Closing implementation and regression evidence |
|---|---|---|
| 1. Automated approval without identity | **Closed** | `validate_d2_approval` now requires a nonempty, order-scoped binding for every `trainingpeaks` or `endure` approval even when D2 never activated. Manual approval remains identity-exempt, while APPLIED still requires nonempty evidence matching the immutable manual platform. The matrix covers TP/Endure missing binding, wrong-order binding, valid bindings, and the manual direction. |
| 2. Stale effects after resolution switching | **Closed** | Every D2 command now retracts the prior choice's canonical override, singleton operation, pending requirement, typed readback/derived record, resolved marker, and cannot-resolve blocker under the same state lock before installing the new effect. Plan/apply-contract changes revoke the seal and persist regeneration intent atomically. Approval reconstructs the exact expected override and singleton-operation maps from the current choices and validates metric, kind, unit, after-value, inspected before-image, intake source, and sealed control anchor. All 12 directed threshold-choice switches plus a tampered terminal operation are covered. |
| 3. Unusable/forgeable manually-corrected completion | **Closed** | Manual selection no longer invalidates a seal when it changes neither plan nor apply contract. The authenticated CSRF-bound review command issues a fresh order/TP-id-bound inspect capability and calls the read-only worker itself; the browser supplies no value or jti. Persistence accepts only `VerifiedInspectionEvidence`, records `d2_worker_readback/v1` with capability jti/kid, request digest, inspected field/value/unit and worker timestamp, and cross-checks a sensitive `externally_observed` derived-registry record on every load. Sealed end-to-end coverage rejects pre-readback, bare-dict, wrong-value, wrong-CSRF, and accepts exact worker readback followed by approval. |
| 4. Terminal probe record reused as an implicit cache | **Closed** | Pipeline and review issuance use a UUID jti for every new logical probe/inspection attempt. `ProbeExecutionStore` remains keyed by `{order_id, jti}` and bound to the canonical request digest, so the same jti/digest resumes or returns its terminal result while a fresh jti necessarily creates a new durable record and calls transport again. Tests prove changing transport data is freshly observed and pin overlong TTL, malformed jti/header, boolean time claims, mutation-shape extras, and wrong expected action. |

The zero-write boundary is unchanged: Phase 4 apply/verify/rollback and execution
grant exchange still refuse before transport. The production image now includes
the read-only `delivery/` package and `/app` import root required by the verified
review-readback path.

### R1 verification evidence

- Blocker-focused worker + D2 + review surface: **79 passed**.
- Broad Phase 4/settled state gate (worker, D2, review, fulfilment state,
  download tokens, athlete-m Phase 1/3/4 goldens, bypass gates): **139 passed**.
- Worker + D2 + D0 apply-contract projection: **91 passed**.
- Complete sandbox suite: **2,550 passed, 87 skipped, 21 warnings, 0 failed**.
- Opt-in production acceptance with writable `HOME` and the existing user-site
  dependency path: **36 passed, 4 skipped, 4 failed**. The four failures are
  the unchanged missing mandatory PDF checks for Gravel Full Gym and Masters;
  the four Roadie PDF/package cases remain expected skips. The same result was
  reproduced from a clean `d291eb4` archive.
- Fresh current and `d291eb4` acceptance builds produced byte-identical ZWOs:
  **284/284** (89 Gravel, 77 Masters, 72 Road Fondo, 46 Road Climb). Recursive
  directory comparison reported no difference; both sorted per-file manifests
  hash to `69e150efe14ea2cbda277bb3677835859c3a7280707d2d1f860745528ffa1e7e`.
  This supersedes the earlier unreproducible 253-ZWO note and confirms no Phase
  4 or R1 workout-byte change under the current date-dependent acceptance input.
- `python3 -m compileall -q athletes/scripts delivery tools webhook` and
  `git diff --check` pass.

Implementation commit boundary: `ad7f5f7` (`fix(phase4): close R1 identity and
readback blockers`). This notes update is a separate documentation boundary.
No push or remote write was performed.

## R2 blocker disposition — 2026-08-09

Review: `docs/reviews/PHASE4_IMPLEMENTATION_CODEX_R2.md`.

Both blockers were accepted as valid; there are no disputes.

| R2 blocker | Disposition | Closing implementation and regression evidence |
|---|---|---|
| 1. Caller-constructible readback evidence | **Closed** | A successful inspect operation now stores worker-owned evidence context (operation, bound TP athlete id, capability kid, and first observation time) beside the order/jti, canonical request digest, and exact results in the atomic replay record. `record_manual_readback` requires the authoritative `ProbeExecutionStore` to find that jti in `succeeded` state and exactly match every evidence field, including a recomputed inspect-request digest, before it changes fulfilment state. A publicly constructed `VerifiedInspectionEvidence` with no record, an evidence object pointed at a different jti's record, and a changed digest all reject while retaining the pending requirement; the exact worker-produced record succeeds and still approves through the authenticated route. |
| 2. Approval snapshot could contradict the executed D2 command | **Closed** | Approval now rejects a submitted `resolved:<choice>` unless it exactly equals the server catalog's `resolved_resolution`, which `validate_d2_approval` has already cross-checked against `d2_resolutions` and the installed effects. Rejection was chosen instead of silent override so a stale or tampered form cannot appear successful; the coach reloads and explicitly approves the authoritative command. The HTTP regression submits `use-tp-value` against an executed `update-from-intake` command and receives 409, then submits the exact command and proves the stored snapshot disposition equals `resolved:` plus the authoritative resolution while the sealed apply payload remains the executed 160 bpm update. |

The evidence check is performed before any pending requirement, derived value,
or resolution marker is changed. Replay records remain crash-safe and immutable
at terminal success: same order/jti/digest returns the originally recorded
result and first observation provenance; a different digest fails closed.

### R2 verification evidence

- Blocker-focused worker + D2 + authenticated review route: **83 passed**.
- Broad Phase 1/2/3/4 state, review, download, golden, bypass, worker, adapter,
  and D0 apply-contract set: **205 passed, 1 skipped**. The skip is the
  sandbox-forbidden loopback fake-TrainingPeaks parity test.
- Complete sandbox suite: **2,554 passed, 87 skipped, 21 warnings, 0 failed**.
- `python3 -m compileall -q athletes/scripts delivery tools webhook` and
  `git diff --check` pass.
- The opt-in acceptance suite was not rerun in this managed workspace: its
  harness deletes and recreates `$HOME/.gg-acctest-delivery`, outside the
  writable workspace roots, and no safe writable-home override was available.
  No acceptance expectations, closed golden fixture, workout generator, or ZWO
  file changed in this R2 boundary.

Implementation commit boundary: `a2cd1de` (`fix(phase4): verify readback and
approval provenance`). This notes update is a separate documentation boundary.
No push, external request, remote write, or TrainingPeaks operation was
performed.

## R3 blocker disposition — 2026-08-09

Review: `docs/reviews/PHASE4_IMPLEMENTATION_CODEX_R3.md`.

The remaining evidence-authenticity blocker was accepted as valid; there are
no disputes.

| R3 requirement | Disposition | Closing implementation and regression evidence |
|---|---|---|
| Server-selected trust root | **Closed** | `record_manual_readback` no longer accepts a `ProbeExecutionStore` from its caller. It opens the authoritative replay root selected by server configuration (`GG_WORKER_REPLAY_DIR`, otherwise the server `DATA_DIR` replay directory), and both the pipeline worker and review worker use the same resolver. A matching record and public evidence created under an attacker-selected root are ignored; readback stays pending and approval remains null. |
| Verified record-creation boundary | **Closed** | Public `ProbeExecutionStore.run`/`run_record` now accept the presented signed capability, not a claims mapping, and invoke their configured `CapabilityCodec.verify` themselves. The request determines the required `probe`/`inspect` action and must exactly match the signed subject; signature, audience, issuance/expiry, TTL, action, and exact claim-shape checks therefore run before any replay directory, record, or transport operation is created. Inspection provenance and the v2 record's capability context are derived only from the verified token. The unsigned-claims regression proves the operation is not called and no JSON record is written; direct wrong-action and expired-capability attempts also reject. |
| Evidence/state TOCTOU | **Closed** | Manual readback acquires the fulfilment-state lock, then the authoritative execution-record lock, validates the exact succeeded record, performs the in-memory transition, re-reads the still-locked record, and only then atomically replaces the state file. The injected delete-after-initial-verify regression rejects before `_atomic_write`, leaves the state byte-identical, retains the pending requirement, and keeps approval null. |
| Honest signed path | **Closed** | A server-issued inspect capability still executes the canned worker transport, creates a verified v2 execution record, yields matching evidence, clears the sealed manual-readback requirement, records the capability kid/jti/digest, and reaches `APPROVED` through the existing end-to-end regression and authenticated review route. |

The v2 replay-record shape deliberately rejects terminal records written by
the former unsigned-claims API because they lack verified capability
provenance. The Phase 4 zero-write boundary is unchanged: apply, verify,
rollback, and mutation execution-grant exchange still refuse before transport.

### R3 verification evidence

- Blocker-focused worker + D2 suite: **56 passed**.
- Worker, D2, authenticated review, fulfilment-state, and athlete-m Phase 4
  golden gate: **119 passed**.
- Complete sandbox suite: **2,558 passed, 87 skipped, 21 warnings, 0 failed**
  in 40.29 seconds. The four-test increase over the R3 review total is exactly
  the new unsigned-boundary, action/expiry, caller-root forgery, and TOCTOU
  coverage.
- Opt-in production acceptance in an isolated workspace-owned output root:
  **36 passed, 4 skipped, 4 failed**. As in the R3 review and clean Phase 3
  baseline, the four failures are only the mandatory PDF presence/structure
  checks for Gravel Full Gym and Masters in this environment without a usable
  PDF engine; all non-PDF acceptance assertions passed.
- `python3 -m compileall -q athletes/scripts delivery tools webhook`,
  `git diff --check`, and the focused compile checks pass.
- No golden fixture, expected Phase 4 JSON, workout generator, checked-in ZWO,
  or ZWO manifest changed.

Commit creation was attempted, but this managed worktree cannot create
`.git/worktrees/trustworthy-phase4/index.lock` (`Operation not permitted`), so
the seven scoped implementation, regression, and notes files remain unstaged.
No push, external request, remote write, or TrainingPeaks operation was
performed.
