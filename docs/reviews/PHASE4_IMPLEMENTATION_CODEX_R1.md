# Phase 4 implementation adversarial review — Codex R1

Date: 2026-08-09

Binding contract: `docs/SPEC_TRUSTWORTHY_FULFILMENT.md` r9, especially D1,
D2, A3, C, S1-S3, D0, the athlete-m Phase 4 fixture, and the Phase 4 rollout
boundary.

Diff reviewed: `c005bc4`, `627fc1a`, `d3ebdb2`, `82b4fb2` relative to
`d291eb4`.

## Verdict

**NO-GO.** Four code-level blockers remain in the offline Phase 4 scope. The
read-only mutation boundary itself held: I found no Phase 4 path that can issue
an execution grant or reach a remote apply/verify/rollback. The blockers are in
approval identity enforcement, D2 resolution consistency, manual-readback
completion, and probe-jti freshness.

## Blockers

### 1. Automated orders can be approved without any platform identity

**Claim.** The D2 approval gate is conditional on `d2_active`. An automated
order for which probing never ran (or was simply omitted) bypasses the binding
requirement and reaches `APPROVED` with `platform_identity: null`.

**Evidence.** `transition()` does invoke D2 validation before approval
(`webhook/fulfillment_state.py:1236-1238`), but `validate_d2_approval()` returns
immediately when `d2_active` is false (`webhook/d2_identity.py:646-649`). The
automated-platform binding check is therefore reachable only after D2 has
already been activated (`webhook/d2_identity.py:650-653`). This is not a
hypothetical malformed-file case: the settled bypass test helper creates and
approves ordinary `trainingpeaks` state without D2 (`athletes/scripts/
test_phase1_bypass_gates.py:25-41,44-63`), and those tests remain green.

Independent probe: I created a sealed `delivery_platform: trainingpeaks`
order, never called a D2 function, and submitted a complete current review
snapshot. The result was `automated_without_binding_approved=APPROVED`.

**Why it blocks.** D2 requires order-scoped `platform_identity` before
`APPROVED` for automated delivery. Making the invariant opt-in lets the absence
of the safety subsystem disable the safety check—the exact fail-open direction
R9 prohibits.

**Minimal fix.** Enforce a valid order-scoped binding for every automated
delivery platform regardless of `d2_active`; keep manual orders exempt at
approval and retain their nonempty, platform-matching evidence requirement at
APPLIED. Add the full matrix: TP/Endure without binding rejected, wrong-order
binding rejected, both automated platforms with a valid binding accepted, and
manual approval accepted without binding followed by evidence-required APPLIED.

### 2. Switching a D2 resolution leaves contradictory effects, and approval accepts them

**Claim.** Resolution choices are not mutually exclusive state commands.
Changing a threshold item from `use-tp-value` to `update-from-intake` retains
the adopted canonical override while adding a write back to the old intake
value. The resulting sealed plan and apply contract disagree, yet approval is
legal.

**Evidence.** `use-tp-value` installs a persistent canonical override
(`webhook/d2_identity.py:514-525`); `update-from-intake` adds an apply operation
but does not clear that override or any prior command effect
(`webhook/d2_identity.py:527-545`). Regeneration deliberately carries both
`canonical_input_overrides` and `d2_apply_operations`
(`webhook/fulfillment_state.py:730-739`). Approval checks only that an `lthr`
operation exists for `update-from-intake`; it does not compare its kind,
metric, unit, or `after_value` with the sealed control value
(`webhook/d2_identity.py:669-681`). Existing tests exercise isolated choices,
not legal choice switching (`webhook/tests/test_d2_identity.py:135-190,
201-232`).

Independent command-sequence probe, using only public state commands:

```text
use-tp-value -> regenerate -> update-from-intake -> regenerate
sealed plan value / retained override: 148 bpm
threshold_update after_value:          160 bpm
recorded choice:                       update-from-intake
approval result:                       APPROVED
```

The reverse direction is also unsafe: moving away from
`update-from-intake` does not remove the old singleton operation.

**Why it blocks.** D2 makes approval legal only when the sealed plan value and
inspected account value are consistent under the chosen resolution. This path
approves one target while serializing a remote mutation to another target. It
would apply reviewed-inconsistent content in Phase 5.

**Minimal fix.** Make each resolution replace the complete effect state for
that item: clear incompatible canonical overrides, singleton operations,
pending readback, prior readback evidence, and cannot-resolve state before
installing the new effect. At approval, validate the exact sealed operation
kind/metric/unit/after-value/before-image against the selected resolution,
sealed control anchor, intake source, and current inspection. Add all pairwise
choice-switch tests and approve only the consistent terminal state.

### 3. `manually-corrected` cannot complete from a sealed review, and its alleged worker evidence is forgeable

**Claim.** On the real sealed-review path, an exact readback can never make the
order approvable. There is also no review/worker endpoint that obtains the
readback: the unit test fabricates a dictionary and caller-supplied jti and
calls the persistence function directly.

**Evidence.** Every resolution first calls `_begin_regeneration()`
(`webhook/d2_identity.py:492-512`). For a sealed revision this increments the
revision, removes the seal, and installs `regeneration_request`
(`webhook/d2_identity.py:168-197`). The manual branch then records a pending
requirement (`webhook/d2_identity.py:546-562`), while the review route
explicitly declines to queue regeneration for that choice
(`webhook/app.py:2880-2885`). `record_manual_readback()` clears the pending
requirement but, because the seal is already gone, `_begin_regeneration()`
returns early and leaves the existing `regeneration_request` untouched
(`webhook/d2_identity.py:168-171,588-622`). Approval rejects any such request
(`webhook/d2_identity.py:654-657`).

Independent sealed-state probe produced:

```text
exact readback accepted and pending requirement cleared
regeneration_request remains present
approval -> FulfillmentStateError: D2 regeneration is pending
```

No production caller or review route invokes `record_manual_readback`; the
only caller is its test (`webhook/tests/test_d2_identity.py:235-254`). That test
starts from an unsealed state and stops before sealing/approval. The function
accepts a bare mapping plus arbitrary `capability_jti` and checks only value
equality (`webhook/d2_identity.py:588-605`), so it does not itself prove the
evidence came from a verified, order-bound worker capability.

**Why it blocks.** R9 requires manual correction to block until worker
readback and then permit approval when the evidence is consistent. The shipped
path is both unusable for honest evidence and insufficiently bound against
fabricated evidence.

**Minimal fix.** Add an authenticated, CSRF-safe review/worker completion path
that performs `inspect_account` with a verified order/subject-bound capability
and persists verified jti/result provenance atomically. Define whether manual
readback changes sealed inputs; either avoid creating a regeneration request
when it does not, or queue and complete the required regeneration. Add a
sealed end-to-end negative-before-readback / negative-wrong-readback /
positive-exact-readback approval test. Do not accept caller-asserted worker
evidence.

### 4. Fresh probe capabilities reuse a completed jti and silently return stale account data

**Claim.** The pipeline deterministically derives probe jtis from only the
order and operation. Every later inspection issuance for the same order reuses
the old durable record, so a newly signed capability returns the first result
without consulting the transport.

**Evidence.** Probe jti is `sha256(order_id:probe)` and inspect jti is
`sha256(order_id:inspect:tp_id)` (`athletes/scripts/intake_to_plan.py:
3872-3879,3888-3895`); neither includes an attempt, revision, or nonce.
`ProbeExecutionStore` returns a completed result solely on matching
order/jti/request digest (`delivery/trainingpeaks/worker_service.py:275-293`).
The existing replay test correctly proves same-token retry idempotency, but
does not distinguish a later newly issued operation
(`delivery/trainingpeaks/test_worker_service.py:63-82`).

Independent probe: a changing injected transport returned `athlete-1` on its
first call. A second, newly signed and currently valid token with later
`iat/exp` but the same pipeline-style jti returned `athlete-1` again and the
transport call count remained one.

**Why it blocks.** D1's durable record makes one jti resumable; it does not make
a jti a permanent cache key for all future probes on an order. Reusing a
terminal jti can bind stale identity and account facts and defeats a new D2
inspection even though capability signature, audience, and expiry all pass.

**Minimal fix.** Issue a unique jti per logical probe/inspection attempt (or
persist and deliberately reuse one only for recovery of that same attempt).
Keep the same-jti/same-digest retry behavior, but add a test proving a newly
issued jti after terminal completion calls the transport and records fresh
results. Bind/persist the attempt identity so crash recovery remains explicit.

## Normative MUST inventory

| Requirement | Enforcement | Test/evidence | Result |
|---|---|---|---|
| D1 exposes only probe, inspect, apply, verify, rollback; credentials do not cross the boundary | `ReadOnlyWorkerTransport` has only read methods (`worker_service.py:49-52`); worker module has no HTTP/browser/credential client | Source/import audit; focused suite | Pass for the shipped canned transport; live credential boundary is standing |
| Probe capability is the exact signed pre-binding union and needs no bound TP id | Exact top-level and one-locator subject schemas (`worker_service.py:91-126,176-214`) | `test_worker_service.py:85-117` | Pass |
| Signature/header/kid/audience/time/action validation fails closed | HMAC verification and closed header (`worker_service.py:147-214`); max 15-minute lifetime and typed `iat/exp` (`:33,91-111`) | Tamper/unknown-kid/audience/expiry/future-iat tests (`test_worker_service.py:102-128`) | Pass; overlong-TTL and malformed-jti negatives are missing |
| A probe request is bound exactly to its signed subject | Exact request comparisons (`worker_service.py:391-413`) | Probe/inspect mismatch tests (`test_worker_service.py:85-99,131-137`) | Pass |
| A probe capability can never authorize mutation | Probe action/type split (`worker_service.py:114-145,208-214`); mutation predicate rejects probe type (`:217-224`) | `test_worker_service.py:185-199` plus crafted-token inspection | Pass |
| Read-only jti records are durable, order-scoped, atomic, resumable, and reject digest confusion | Safe paths, file lock, accepted/running/terminal states, fsync+replace (`worker_service.py:261-340`) | Replay and request mismatch tests (`test_worker_service.py:63-82,131-137`) | **Blocker 4:** terminal jti is wrongly reused by later issuances |
| Mutation capability has the distinct exact D1 shape and action predicates | Shape (`worker_service.py:129-145`); pure predicate (`:217-258`) | Predicate table test (`test_worker_service.py:140-182`) | Pass as an offline predicate only; grant effects remain Phase 5 |
| No live execution grant means no mutation in Phase 4 | Worker apply/verify/rollback and exchange all raise before transport (`worker_service.py:415-435`) | `test_worker_service.py:192-200` | Pass |
| Legacy/direct paths cannot mutate or issue an apply grant | Adapter apply raises (`delivery/trainingpeaks/adapter.py:125-130`); old issuer raises (`webhook/app.py:3241-3244`); status omits token and gate always 409 (`webhook/app.py:3363-3389,3392-3401`); legacy CLI job/runbook refuse (`tools/tp_apply_order.py:225-229,313-322`) | `test_phase1_bypass_gates.py:211-295`; adapter/tool suites in full run | Pass |
| D1 lease, online exchange transition effects, fencing, per-mutation epoch revalidation, quiescence, secrets/TLS/egress/rate/audit, and canary-before-write | No mutation worker exists in Phase 4 | Not executable offline | Standing Phase 5/live conditions, not Phase 4 blockers |
| D2 accepts order email, optional TP email, and coach-entered identity; produces the five closed outcomes | Pipeline signs order-email probe (`intake_to_plan.py:3855-3884`); outcome set and review candidate command (`d2_identity.py:24-29,204-303`) | `test_d2_identity.py:268-306`; review surface test | Pass for fixture/order email and candidate selection; no separate TP-email/coach-entered freeform control is tested |
| Binding is stored as order-scoped `platform_identity` | State validator requires binding order id (`d2_identity.py:90-96`); writers stamp current order (`:233-239,290-294`) | `test_d2_identity.py:92-96,268-306` | Pass for bindings that exist |
| Binding is required before APPROVED only for automated delivery; manual records evidence at APPLIED | `_automated` covers TP/Endure (`d2_identity.py:36-38`); APPLIED requires platform/evidence (`fulfillment_state.py:1357-1393`) | Manual no-account and APPLIED tests (`test_d2_identity.py:309-317`; `test_fulfillment_state.py:447-455`) | **Blocker 1:** automated absence bypasses the gate |
| `not-coached`, `not-found`, multiple/unresolved block automated delivery with non-waivable policy | D2 issue mapping (`d2_identity.py:241-257`); policy (`fulfillment_state.py:49-82`) | `test_d2_identity.py:268-306` | Pass once D2 is active; Blocker 1 covers omitted D2 |
| `use-tp-value` writes canonical input, creates a new revision, regenerates, and re-reviews | Command and durable pre-queue invalidation (`d2_identity.py:168-201,492-526`); queue applies overrides (`webhook/app.py:2892-2953`) | Unit and queue tests (`test_d2_identity.py:135-158`; `test_review_surface.py:153-239`) | Pass in isolation; **Blocker 2** on choice switching |
| `update-from-intake` emits threshold/zone update with inspected before-image and leaves plan anchor unchanged | Command desire (`d2_identity.py:527-545`); inspection-to-contract bridge (`:625-643`) and D0 builder | Contract test (`test_d2_identity.py:161-190`) | Pass in isolation; **Blocker 2** allows retained override/inconsistent approval. No zone-path test exists |
| `manually-corrected` blocks approval until worker readback confirms the value | Pending/equality checks (`d2_identity.py:546-562,588-622`); approval checks pending/evidence (`:654-686`) | Direct unsealed unit test (`test_d2_identity.py:235-254`) | **Blocker 3** |
| `cannot-resolve` blocks | Non-waivable D2 blocker (`d2_identity.py:563-577`; `fulfillment_state.py:61,81`) | `test_d2_identity.py:257-265` | Pass |
| Approval requires every D2 item resolved and sealed-plan/account consistency under the selected control-metric resolution | Server-side gate (`d2_identity.py:646-686`) called by transition | Unresolved and one valid update test (`test_d2_identity.py:123-132,201-232`) | **Blocker 2**: inconsistent update operation is accepted |
| Control-metric findings are required; dormancy/cosmetic mismatch is soft | LTHR required, age required, dormancy soft (`d2_identity.py:404-465`) | Fixture findings test (`test_d2_identity.py:92-120`) | Pass for HR fixture |
| D2 values carry A3 provenance and sensitivity | Externally observed derived records (`d2_identity.py:306-320,386-402`); common validation/catalog (`fulfillment_state.py:263-283,365-429`) | `test_d2_identity.py:92-120`; independent seeded surface probe | Pass for age/FTP/LTHR/expiry/workout count; account weight is ignored/not modeled |
| Sensitive D2 values stay off non-review status, notifications, logs, and exposed packages | Status uses recursive projection (`webhook/app.py:3364-3389`); generation notification projects selected details (`:411-467`); logs do not serialize state (`:2190-2220`); apply contract remains private (`:1812-1828`) | Existing A3 suite plus independent unique-value status/review/notification probes | Pass on current reachable surfaces; hardening/test gap noted below |
| D2 choices are authenticated state-changing C commands, not client-side edits | CSRF/revision-bound POST routes (`webhook/app.py:2830-2889`); server validates allowed current item (`d2_identity.py:476-507`) | Review surface command test (`test_review_surface.py:153-206`) | Pass for identity/use-TP command; **Blocker 3** for absent readback completion route |
| Phase 4 golden has bound identity, exact three required confirmations, and rejects approval until D2 resolutions exist | Fixture and literal expected set (`tests/fixtures/athlete_m/worker_probes.json`; `expected/phase4.json`) | `test_athlete_m_phase1.py:236-371` | Pass |
| Phase 1/3 athlete-m assertions remain true under Phase 4 | Phase 4 golden checks devices, null FTP, HR control, no ZWO/watts, one field test, race day, blockers and closed confirmation set (`test_athlete_m_phase1.py:293-329`) | Golden plus full suite | Pass |

## Non-blocking findings

1. **D2-sensitive projection coverage is too indirect.** Unique seeded age,
   FTP, LTHR, and workout-count values were absent from the real status response
   and visible on the authenticated review page, as required. Current
   generation notifications select only projected blocker/confirmation data,
   and order logs do not serialize D2 state. However, applying
   `external_notification_projection()` to an entire raw D2 state still leaks
   values from `account_inspection` and `d2_context`, because those containers
   are not sensitivity-labeled (`webhook/fulfillment_state.py:125-194`;
   `webhook/d2_identity.py:350-385`). No current external caller passes those
   fields, so this is not a present exposure, but a D2-specific regression
   should pin the actual status, success/failure notification, log, and bundle
   surfaces before a future caller broadens a response.

2. **Account weight is silently ignored.** `record_account_inspection()`
   normalizes age, FTP, LTHR, expiry, and workout count but has no account-weight
   field or D2 registry entry (`webhook/d2_identity.py:323-402`). Weight is not
   in the athlete-m R9 probe literal, so this does not block this phase, but a
   future transport response containing weight currently receives neither A3
   provenance nor a review policy.

3. **Capability negatives are not exhaustive.** Code inspection found closed
   checks for overlong TTL, bad jti syntax, malformed headers, boolean time
   claims, mutation-shape extras, and wrong expected action, but the worker test
   file does not independently pin each one. Add the matrix when repairing
   Blocker 4.

4. **The implementation note's 253-ZWO/hash claim is not reproducible from a
   fresh archive today.** Fresh `d291eb4` and `HEAD` archives both generated
   284 ZWOs: 89 Gravel, 77 Masters, 72 Road Fondo, 46 Road Climb. Their sorted
   per-file manifests were identical and both hashed to
   `7044d8924e08cfeefa423d342059ff725d2232393efdc7f20607daa1a85a0298`.
   The Road Fondo acceptance fixture selected the date-dependent Lake Taupo
   race on 2026-11-28, explaining the extra weeks. This disproves the notes'
   current exact count/hash but proves no Phase 4 ZWO regression; both sides
   behave identically. The acceptance race selection should be clock-pinned if
   the count is intended to be a durable golden.

5. `resolve_d2_item()` can be called against an unsealed generated state, in
   which case `_begin_regeneration()` returns without creating a revision or
   regeneration request (`webhook/d2_identity.py:168-171`). The authenticated
   production review path is sealed, so I did not count this separately, but
   the state command would be safer if it rejected an unsealed review rather
   than weakening `use-tp-value` semantics for direct callers.

## Standing conditions (not blockers in this review)

- Complete the R9 Phase 4 live gate: real order identity binding and inspection
  confirmations, zero writes, and scheduled read-only canary green.
- Retain the prior human review-page gate and the reported outside-sandbox
  evidence; neither was independently re-performed against production.
- Phase 5 owns execution-grant issuance, lease/fencing/epoch enforcement,
  mutation intent/journals, reconciliation, quiescence, canary-before-write,
  apply/readback/rollback, release components, and D0 cutover.
- Live TP transport, credential/TOTP storage, TLS, egress restrictions,
  immutable worker audit, rate limits, and live HR/RPE/marker acceptance remain
  human/live rollout evidence, not offline Phase 4 code blockers.
- The sandbox loopback and PDF gaps remain environmental. The supplied outside
  results (2,523 passed / 86 skipped; acceptance 42 passed / 2 skipped) were not
  independently reproduced here.

## Verification performed

- Read `CLAUDE.md`, `.claude/skills/order-safety/SKILL.md`, and
  `.claude/skills/generator-conventions/SKILL.md` before review.
- Read the R9 D1/D2 clauses and their A3/C/S/D0/fixture dependencies; inspected
  all four commits and the implementation notes rather than accepting the
  notes as evidence.
- Phase 4 broad focused set (worker, D2, review, fulfilment state, athlete-m,
  bypass gates): **98 passed**.
- Settled state/review/download-token files: **68 passed**. This is the prior
  66-test suite plus two Phase 4 review tests; no settled test regressed.
- Full suite: **2,522 passed, 87 skipped, 21 warnings** in 45.87 s.
- Focused apply-contract suite: **42 passed**.
- TrainingPeaks adapter subset: **2 passed, 1 skipped**; the skip is the
  sandbox-forbidden loopback fake-TP test.
- Opt-in acceptance with isolated writable HOME: **36 passed, 4 skipped,
  4 failed**. The failures were only mandatory PDF existence/structure for
  Gravel Full Gym and Masters; the four skips were the two Roadie HTML-fallback
  PDF cases and two Roadie-only package cases.
- Fresh-archive Phase 3 versus Phase 4 acceptance manifests: byte-identical,
  **284/284** with the count discrepancy explained above.
- `python3 -m compileall -q athletes/scripts delivery tools webhook` passed.
- `git diff --check d291eb4..HEAD` and all four commit whitespace checks passed.
- Independent adversarial probes covered: no-D2 automated approval; sealed
  manual readback completion; resolution switching and inconsistent approval;
  fresh-token/same-jti stale replay; seeded D2 status/review/notification
  projections; route/grant/adapter refusal inspection.
- No live TrainingPeaks, browser, external-network, email, Stripe, apply,
  verify, rollback, or grant action was attempted.

## What I could not verify

- Real TrainingPeaks identity/session transport, live binding, scheduled
  canary, or any live write/readback behavior—correctly outside this offline
  review.
- The loopback fake-server test, because this sandbox forbids loopback sockets.
- Mandatory PDF generation/structure for Gravel Full Gym and Masters, because
  this sandbox has no usable PDF engine.
- The supplied outside-sandbox green totals or prior production human gates;
  I recorded them as supplied evidence only.
- The claimed 253-ZWO historical manifest under its original environmental
  inputs; fresh current archives select a different date-dependent Road Fondo
  while remaining identical across the Phase 3/4 boundary.

**Verdict: NO-GO — 4 blockers.**
