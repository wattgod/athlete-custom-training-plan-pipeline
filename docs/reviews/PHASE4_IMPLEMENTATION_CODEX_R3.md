# Phase 4 implementation adversarial review — Codex R3

Date: 2026-08-09

Binding contract: `docs/SPEC_TRUSTWORTHY_FULFILMENT.md` R9, especially I3,
I5, I6, S3, C, D1, D2, the athlete-m Phase 4 fixture, and the Phase 4
rollout boundary.

Claimed fix boundary: `a2cd1de` and notes commit `b108b14`, reviewed relative
to R2 and the Phase 3 boundary `d291eb4`.

## Verdict

**NO-GO.** The approval-provenance blocker is closed, and every specifically
required malformed/stale/cross-order evidence probe rejects. The readback
authenticity blocker is not closed, however: the new persistence boundary
accepts a caller-selected `ProbeExecutionStore`, while that store's public
`run_record()` method can create a matching `succeeded` record from unsigned,
unverified claims. A caller can therefore manufacture both halves of the new
equality check, clear a sealed order's pending readback, and reach `APPROVED`
with `capability_kid="forged-kid"` without ever presenting a signed worker
capability.

This is one concrete Phase 4 offline code blocker. Live transport, the
scheduled canary, human gates, and Phase 5 work remain standing conditions,
not additional blockers.

## R2 blocker closure

| R2 blocker | R3 result | Evidence |
|---|---|---|
| 1. Caller-constructible readback evidence | **Not closed (partial).** The exact R2 forgery and all prescribed record-confusion negatives now reject, but the new durable-record check is itself caller-forgeable. `ProbeExecutionStore` accepts an arbitrary root; `run_record()` accepts unsigned claims and writes a terminal success; `record_manual_readback()` accepts the caller's store instance as authoritative. An independently fabricated success record plus matching public evidence cleared the requirement and reached `APPROVED`. | Public evidence type: `delivery/trainingpeaks/worker_service.py:67-77`; arbitrary store root and unsigned record writer: `delivery/trainingpeaks/worker_service.py:279-280,298-358`; equality check: `delivery/trainingpeaks/worker_service.py:360-397`; caller-selected store and persistence: `webhook/d2_identity.py:723-804`. Existing regression covers only a missing record and field changes: `webhook/tests/test_d2_identity.py:346-411`. |
| 2. Approval trusts client-submitted resolution disposition | **Closed.** Approval now requires a submitted `resolved:<choice>` to equal the server catalog's `resolved_resolution`, then snapshots that authoritative catalog item. The HTTP mismatch returned 409 with no approval; the honest request returned 303 and stored `resolved:update-from-intake`, matching both `d2_resolutions` and the sealed 160 bpm operation. Unresolved items, all 12 directed resolution switches, and unknown catalog decisions also rejected or approved according to their terminal authoritative state. | Enforcement and snapshot: `webhook/fulfillment_state.py:1283-1347`; HTTP form construction: `webhook/app.py:2787-2819`; mismatch/accepted-path regression: `webhook/tests/test_review_surface.py:248-316`; unresolved gate: `webhook/tests/test_d2_identity.py:170-179`; switch matrix: `webhook/tests/test_d2_identity.py:566-631`; unknown HTTP item: `webhook/tests/test_review_surface.py:738-763`. |

## Blocker

### 1. The replay record is not an authenticity boundary

The fix proves only that two caller-influenced objects agree. It does not
prove that a signed capability was verified before the record was created:

1. `ProbeExecutionStore(root)` accepts any filesystem root supplied by its
   caller (`worker_service.py:279-280`).
2. Its public `run_record(claims, request, operation, ...)` performs no
   `CapabilityCodec.verify()` call. It accepts a dict containing only the
   desired order/JTI for the fields it consumes and writes
   `status: succeeded`, the result, digest, and evidence context
   (`worker_service.py:298-358`).
3. `record_manual_readback()` requires only that the caller also pass an
   instance of that class; it does not obtain the configured authoritative
   store itself or authenticate the record writer
   (`d2_identity.py:723-739`).

Independent sealed-order probe:

```text
public VerifiedInspectionEvidence, forged kid, zero digest, no record
  -> REJECTED; pending retained

ProbeExecutionStore.run_record(
  unsigned {order_id, jti}, canonical inspect request,
  caller result lthr_bpm=155,
  caller evidence context capability_kid=forged-kid)
matching public VerifiedInspectionEvidence
  -> ACCEPTED; pending cleared
approval after fabricated record
  -> APPROVED
stored capability_kid
  -> forged-kid
```

This reproduces the substance of R2 blocker 1 through the new record layer and
violates D2's requirement that manual correction be confirmed by worker
readback (`docs/SPEC_TRUSTWORTHY_FULFILMENT.md:797-811`) and I5's provenance
requirement.

The record check also happens before the fulfillment-state lock is acquired.
`verify_inspection_evidence()` releases the replay-record lock before
`record_manual_readback()` enters `locked_state()`
(`worker_service.py:360-397`, `d2_identity.py:735-740`). In an injected
delete-after-verify store, the record was removed in that interval and the
state still committed `worker-readback-confirmed`. This TOCTOU is another
facet of the same missing authoritative evidence boundary, not a separately
counted blocker.

Closure requires persistence to authenticate evidence whose creation a caller
cannot synthesize—for example, a server-selected trust root plus a record
creation boundary that requires the verified capability, or a signed worker
evidence envelope retained and re-verifiable in state. Merely adding more
equality fields to a caller-writable record is insufficient.

## Required probe results

### Readback evidence

- Public `VerifiedInspectionEvidence` with forged kid and zero digest against
  a sealed order: **rejected**, pending requirement retained.
- JTI pointing at another order's succeeded record: **rejected** by
  order-scoped lookup.
- Exact-shape `failed` record: **rejected**.
- Exact-shape `running` record: **rejected**.
- `succeeded` record with a different inspected value: **rejected**.
- Legitimate order-one evidence replayed against a second sealed order:
  **rejected** by the state/order binding after record verification.
- Honest worker-produced exact record: **accepted** on its original order.
- New unsigned caller-fabricated `succeeded` record plus matching evidence:
  **accepted and approved** — blocker 1.

### Approval provenance

- HTTP `resolved:use-tp-value` against authoritative
  `update-from-intake`: **409 rejected**, approval remained null.
- HTTP authoritative `resolved:update-from-intake`: **303 accepted**;
  snapshot and sealed operation both equal the executed command.
- Unresolved D2 required items: **rejected**.
- Every directed switch among `use-tp-value`, `update-from-intake`,
  `manually-corrected`, and `cannot-resolve`: terminal effects and approval
  behavior matched the terminal command (**12/12**).
- Decision for an item absent from the catalog: **409 rejected**, approval
  remained null.

## New-fix failure-path review

- **Durable-record lookup confusion: blocking.** The caller chooses the store
  and can populate it through an unauthenticated public API, as described in
  blocker 1.
- **Record-check/state-persist TOCTOU: confirmed.** Deleting the exact record
  immediately after verification did not prevent fulfillment-state
  persistence. Counted as part of blocker 1.
- **State-write failure after successful evidence verification: safe in the
  injected probe.** An exception from `_atomic_write` left the fulfillment
  state byte-identical with the pending requirement intact; retrying the same
  durable evidence succeeded. No partial authoritative state was observed.
- **Wrong value/status/order errors: safe.** Each rejected before any pending
  requirement, resolution marker, or derived value changed.

## Non-blocking findings

1. `WorkerTransportError` and worker fixture I/O remain outside the review
   endpoint's handled exception set (`webhook/app.py:2963-2969`). The state
   remains closed, but the coach receives a generic 500 rather than the
   durable 409 review error used for `FulfillmentStateError`.

2. `D2_CANNOT_RESOLVE` remains a global blocker id. Installing another such
   resolution replaces the previous issue before inserting the new one
   (`webhook/d2_identity.py:703-711`). Approval still fails closed because
   every authoritative D2 item is revalidated, but multi-item triage can
   under-report unresolved findings.

3. Acceptance race selection remains date-dependent. The current and Phase 3
   runs selected the same 284 workouts on this review date; a fixed clock/date
   remains preferable for a permanently stable manifest hash.

## Phase 1-4 invariant and golden spot-checks

- Athlete-m Phase 3 retains null FTP, `power_basis: none`, HR control, zero
  watt figures, one W1 HR field test, the exact closed blocker/confirmation
  lists, and a review bundle with no ZWO (`test_athlete_m_phase1.py:34-233`).
- Athlete-m Phase 4 retains those Phase 1/3 negatives while pinning the exact
  D2 identity, inspection values, blocker list, required-confirmation list,
  and unresolved-approval rejection (`test_athlete_m_phase1.py:236-371`).
- Phase 4 expected confirmations remain exactly
  `D2_DEMOGRAPHIC_AGE_MISMATCH`,
  `D2_THRESHOLD_LTHR_STALE_MISMATCH`, and
  `SCHEDULE_MISMATCH_CONFIRM`; the blocker and absent-blocker sets are closed
  (`tests/fixtures/athlete_m/expected/phase4.json:1-39`).
- Zero-write boundaries, non-executable pre-approval bundles, sealed downloads,
  order-scoped identity, D0 projection, null-power packages, and legacy apply
  refusal all passed the focused regression selection.
- Fresh current and clean `d291eb4` acceptance builds produced byte-identical
  ZWOs **284/284**: Gravel 89, Masters 77, Road Fondo 72, Road Climb 46.
  Sorted per-file SHA-256 manifests had no diff; each combined manifest hash
  was `7044d8924e08cfeefa423d342059ff725d2232393efdc7f20607daa1a85a0298`.

## Standing conditions

- Complete the R9 Phase 4 live gate: real-order identity binding and account
  inspection, zero writes, and a green scheduled read-only canary.
- Retain the Phase 2 real-order human review gate; it was not independently
  repeated here.
- Phase 5 still owns live execution-grant exchange effects, leases/fencing and
  epochs, cancellation quiescence, mutation intents/journals,
  reconciliation, apply/readback/rollback, D0 cutover, release components,
  and Endure's final gated disposition.
- Live credential/TOTP storage, TLS, egress restrictions, immutable worker
  audit, production rate limits, and live HR/RPE/marker acceptance remain
  rollout evidence.

## Verification performed

- Read `CLAUDE.md`, all three task-relevant handover skills, the full R9 spec,
  R2 review, both claimed commits, and the implementation notes.
- Re-ran every required R2 probe plus the unsigned-record and TOCTOU probes
  described above.
- Blocker/approval-focused selection: **18 passed**.
- Worker, D2, review, and fulfillment-state focused suites: **109 passed**.
- Broad Phase 1/2/3/4 state, review, download, golden, bypass, worker, D0,
  PlanIR, and metric-neutral set: **241 passed, 1 skipped, 1 warning**. The
  skip was the sandbox-forbidden loopback fake-TP parity test.
- Full local suite: **2,554 passed, 87 skipped, 21 warnings** in 47.56 s.
  The one-test delta from the supplied outside result is the same loopback
  fake-TP skip.
- Opt-in acceptance with `GG_RUN_ACCEPTANCE=1`, isolated writable `HOME`, and
  the existing user-site dependency path: **36 passed, 4 skipped, 4 failed**.
  The failures were only missing mandatory PDFs for Gravel Full Gym and
  Masters; Roadie PDF fallbacks/package cases supplied the four skips. A clean
  Phase 3 archive produced the identical result.
- Independently compared the current and clean Phase 3 ZWO manifests as
  described above.
- Injected state-write failure proved no partial state and successful retry.
- `python3 -m compileall -q athletes/scripts delivery tools webhook`,
  `git diff --check d291eb4..HEAD`, and the claimed commit diffs passed.
- No implementation code was changed and no push or external mutation was
  made.

## What I could not verify

- Real TrainingPeaks session/identity/inspection transport, live capability
  exchange, scheduled canary behavior, or any live platform operation.
- The loopback fake-TP parity test because the managed sandbox forbids the
  socket.
- Mandatory PDF generation/structure for Gravel Full Gym and Masters because
  this sandbox has no usable PDF engine.
- The supplied outside-workspace totals (**2,555 passed / 86 skipped** and
  acceptance **42 passed / 2 skipped**), production canary evidence, and prior
  real-order human gates; these remain supplied evidence rather than
  independently reproduced evidence.

**Verdict: NO-GO — 1 blocker.**
