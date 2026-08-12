# Phase 4 implementation adversarial review — Codex R5

Date: 2026-08-10

Binding contract: `docs/SPEC_TRUSTWORTHY_FULFILMENT.md` R9, especially I5,
D1, D2, the athlete-m Phase 4 fixture, and the Phase 4 rollout boundary.

Claimed closure boundary: `a6152ab` (`fix(phase4): bind readback records to
server signer`), reviewed on `build/trustworthy-phase4` relative to the R4
review and the Phase 3 boundary `d291eb4`.

## Verdict

**GO-WITH-CONDITIONS.** The R4 same-root authenticity blocker is closed. A
caller-selected codec can no longer construct a store over the configured
authoritative root, and—independently of that constructor guard—readback
re-verifies the retained v3 capability with the server-configured verifier.
The exact attacker-signed same-root record remains pending and cannot reach
approval. Tampered proof, server-signed proof for another order/JTI/action/
subject/audience, and a v2 downgrade all fail closed; the honest server-signed
path still reaches approval.

No new Phase 4 offline blocker was found. Live transport, the scheduled
canary, real-order identity binding, the human gates, and Phase 5 remain the
standing conditions required by R9 rather than offline blockers.

## R4 blocker closure

| R4 requirement | R5 result | Evidence |
|---|---|---|
| Durable server-verifiable authorization proof | **Closed.** The record type is v3. Every accepted, running, failed, and succeeded write retains the exact capability token. Terminal replay additionally requires exact retained-token and capability-context equality. | `delivery/trainingpeaks/worker_service.py:35,391-486`. |
| Trust only the authoritative signer at readback | **Closed.** `ProbeExecutionStore.authoritative()` accepts no codec and obtains its verifier from server configuration. Before any record field or result is trusted, readback verifies the retained token's signature, audience, time bounds, exact `inspect` action, closed claim shape, order, JTI, identity-query subject/TP id, kid, capability type, and claims digest. | Server verifier construction: `delivery/trainingpeaks/worker_service.py:84-102,342-348`; cryptographic and claim verification: `:187-254,545-594`; state entrypoint: `webhook/d2_identity.py:723-748`. |
| R4 same-root attacker codec | **Rejected.** Direct construction over the configured root now rejects. The stronger read-side probe copied a correctly shaped attacker-created v3 record into the configured authoritative order directory; server verification rejected `attacker-kid`, retained the pending requirement, and approval still rejected. | Constructor guard: `delivery/trainingpeaks/worker_service.py:331-348`; regression: `webhook/tests/test_d2_identity.py:430-493`. |
| Retained-token and record downgrade attacks | **Rejected.** A signature-tampered retained token rejects. A v2 record or any record without the retained proof rejects before self-consistency fields can matter. | Read boundary: `delivery/trainingpeaks/worker_service.py:545-560,584-594`; retained-token regression: `webhook/tests/test_d2_identity.py:496-519`; independent v2 downgrade probe described below. |
| Authoritative-root containment | **Closed for the prescribed paths.** Components are lexically constrained; the configured root is resolved once, and unsafe order/record/lock paths, including the R4 symlinked-order escape, reject before transport or persistence. | `delivery/trainingpeaks/worker_service.py:84-92,353-382`; regression: `delivery/trainingpeaks/test_worker_service.py:210-239`. |
| Evidence/state TOCTOU | **Still closed.** Fulfilment state is locked before record validation, the execution-record lock remains held throughout the in-memory transition, and the record is re-read immediately before the atomic state replace. | Record guard: `delivery/trainingpeaks/worker_service.py:597-625`; state lock, final recheck, and commit: `webhook/d2_identity.py:736-822`; regression: `webhook/tests/test_d2_identity.py:522-559`. |
| Honest issuance and readback | **Works.** Both generation-time D2 inspection and the authenticated manual-readback route use the server worker builder, fixed audience/kid, authoritative root, and same server configuration later used by readback. Exact evidence clears the requirement and reaches `APPROVED`. | Issuance wiring: `athletes/scripts/intake_to_plan.py:3838-3895`, `webhook/app.py:2891-2930`; honest state/HTTP regressions: `webhook/tests/test_d2_identity.py:289-350`, `webhook/tests/test_review_surface.py:319-415`. |

### Independent R5 probe matrix

| Probe | Result |
|---|---|
| R4 verbatim construction: `ProbeExecutionStore(authoritative_probe_execution_root(), attacker_codec)` | **Rejected at construction** with the server-internal-wiring guard. |
| Attacker-signed matching v3 record placed under the configured authoritative order root | **Rejected at readback** (`unknown capability signing key`); pending retained; approval rejected. |
| Retained token with a changed signature | **Rejected** (`invalid capability signature`). |
| Token signed by the server key but naming another order | **Rejected** by exact record/evidence/claim binding. |
| Token signed by the server key but naming another JTI | **Rejected** by exact record/evidence/claim binding. |
| Token signed by the server key but carrying `probe` rather than `inspect` | **Rejected** (`capability action mismatch`). |
| Token signed by the server key but naming another TP subject | **Rejected** by exact subject binding. |
| Token signed by the server key but naming another audience | **Rejected** (`capability audience mismatch`). |
| Record changed to `trainingpeaks_probe_execution/v2` and retained token removed | **Rejected** (`lacks retained capability proof`). |
| Old kid present in a verifier key ring | **Accepted**, as intended. |
| Same old kid removed from that verifier key ring | **Rejected** (`unknown capability signing key`), as intended. |
| Untampered v3 server-issued record | **Accepted**. |

The trust decision no longer derives authenticity from record/evidence
self-consistency. Equality remains necessary for result, request, context,
and state binding, but it is evaluated only after the retained token has
passed the server verifier (`worker_service.py:545-594`).

## New blockers

None.

## Caller-writable state-path review

The only path that writes `effect: worker-readback-confirmed`, installs
`readback_evidence`, and clears a pending worker readback is
`record_manual_readback()` (`webhook/d2_identity.py:723-822`). It requires a
sealed revision, an exact pending requirement, the order-scoped TP binding,
the expected inspected value, the authoritative server verifier, both locks,
and the final record recheck.

The other removal of `d2_pending_requirements` is
`_retract_resolution_effects()` (`webhook/d2_identity.py:561-594`). It runs
inside the locked resolution command, retracts the old resolution's complete
effect set, and installs the newly selected server-validated command before
commit (`:597-720`). It cannot mark manual readback confirmed. Approval still
requires no pending requirement and reconstructs every current D2 resolution
and effect (`:846-939`).

No second HTTP route or production writer for `worker-readback-confirmed` was
found. Direct arbitrary rewriting of the authoritative fulfilment state,
server environment, or trusted key store is the sealed-store/in-process
attacker excluded by the stated offline threat model.

## Prior closures and Phase 1–4 spot-checks

- **R1 blocker 1 — automated approval identity:** TrainingPeaks and Endure
  reject without an order-scoped binding; valid bindings pass; manual approval
  remains identity-exempt while application requires matching evidence
  (`webhook/tests/test_d2_identity.py:651-736`).
- **R1 blocker 2 — resolution switching:** all 12 directed pairs among
  `use-tp-value`, `update-from-intake`, `manually-corrected`, and
  `cannot-resolve` retract prior effects and validate the terminal state
  (`webhook/tests/test_d2_identity.py:738-818`).
- **R1 blocker 4 — terminal probe reuse:** a new logical attempt uses a fresh
  JTI and freshly observes changed transport data
  (`delivery/trainingpeaks/test_worker_service.py:108-140`).
- **R2 blocker 2 — approval snapshot provenance:** a client resolution that
  contradicts the executed command rejects; the exact authoritative command
  is stored in the sealed approval snapshot
  (`webhook/tests/test_review_surface.py:248-317`).
- **R3 regressions:** unsigned record creation, caller-selected roots,
  delete-after-verify, wrong action/expiry, and the honest signed path all
  pass (`delivery/trainingpeaks/test_worker_service.py:162-207`;
  `webhook/tests/test_d2_identity.py:289-427,522-559`).
- The athlete-m Phase 4 golden retains the exact identity, account values,
  blocker/confirmation sets, null-power/no-watts assertions, one HR field
  test, sealed projection, no review-bundle ZWOs, and unresolved-approval
  rejection (`athletes/scripts/test_athlete_m_phase1.py:270-371`;
  `tests/fixtures/athlete_m/expected/phase4.json:1-40`).
- Phase 4 mutation entrypoints and execution-grant issuance continue to
  refuse before transport. The broad gate also covered sealed downloads,
  review authority, fulfilment state, bypass gates, D0/apply-contract parity,
  PlanIR, metric-neutral packages, truthful power, and TP projection.
- No fixture golden, checked-in ZWO, or checked-in manifest changed in
  `a6152ab`.

## Non-blocking findings

1. **The readback algorithm handles rotating key rings, but production wiring
   exposes only one fixed kid.** `CapabilityCodec` correctly accepts multiple
   `kid`-selected keys and the independent rotation probe accepted an old key
   while retained and rejected it after removal
   (`delivery/trainingpeaks/worker_service.py:187-247`). However,
   `_server_configured_probe_codec()` maps the single
   `GG_WORKER_CAPABILITY_SECRET` to the constant `phase4-fixture`; there is no
   configured overlapping old/new ring (`:39-40,95-102`). This is fail-closed
   and the authenticated route can issue a fresh readback under the new
   secret, so it is not an authenticity blocker. Before the first planned key
   rotation, configuration should support distinct current/retained kids so
   provenance identifies the generation and in-flight v3 records can survive
   an overlap window.

2. `WorkerTransportError` and malformed fixture I/O remain outside the review
   route's handled exception set (`webhook/app.py:2957-2963`). State fails
   closed, but the coach can receive a generic 500 instead of the durable 409
   review error. This is carried from R4.

3. `D2_CANNOT_RESOLVE` remains a global blocker id. Selecting a second such
   item can replace the first displayed issue (`webhook/d2_identity.py:703-711`).
   Approval still validates every D2 item and fails closed. This is carried
   from R4.

4. Acceptance race selection is date-dependent. On 2026-08-10 both HEAD and a
   clean `d291eb4` archive selected the same current race and failed the same
   Gravel zone-distribution assertion (88% easy vs 70% target), in addition to
   the established four local PDF failures. This is not a Phase 4 regression;
   a fixed acceptance clock/race would make the gate stable. This is the
   concrete recurrence of R4's carried date-dependence finding.

## Standing conditions

- Complete the R9 Phase 4 live gate: bind and inspect a real order with zero
  writes, and demonstrate a green scheduled read-only canary.
- Retain the Phase 2 real-order human review gate; it was not repeated here.
- Phase 5 still owns live execution-grant exchange effects, leases/fencing and
  epochs, cancellation quiescence, mutation intents/journals,
  reconciliation, apply/readback/rollback, D0 cutover, release components,
  and Endure's final gated disposition.
- Live credential/TOTP storage, rotation/revocation operations, TLS, egress
  restrictions, immutable worker audit, production rate limits, and live
  HR/RPE/marker acceptance remain rollout evidence.

## Verification performed

- Read `CLAUDE.md`, all three applicable handover skills, R9, R4, the complete
  `a6152ab` diff, and the implementation notes.
- Exact closure regression set (same-root signer, retained token,
  authoritative constructor, symlink, unsigned record, caller root, TOCTOU,
  honest state path, honest HTTP path): **9 passed**.
- Worker, D2, authenticated review, fulfilment-state, and athlete-m focused
  suite: **123 passed**.
- Broad Phase 1–4 authority/projection/golden gate: **249 passed, 1 skipped,
  1 warning**. The skip is the sandbox-forbidden loopback fake-TP parity test;
  the warning is the deliberate simulated disk-full PlanIR test.
- Complete local suite: **2,562 passed, 87 skipped, 21 warnings** in 47.06 s.
- Opt-in acceptance with `GG_RUN_ACCEPTANCE=1`, an isolated writable `HOME`,
  and the existing user-site dependency path: **35 passed, 4 skipped, 5
  failed**. Four failures are the established missing mandatory PDFs for
  Gravel Full Gym and Masters. The fifth is the date-dependent Gravel zone
  distribution assertion described above.
- A clean `d291eb4` archive reproduced the exact acceptance result: **35
  passed, 4 skipped, 5 failed**.
- Fresh HEAD and clean `d291eb4` acceptance builds produced byte-identical
  ZWOs: **305/305** (101 Gravel, 88 Masters, 72 Road Fondo, 44 Road Climb).
  The sorted `<file-sha256>  <athlete-relative-path>` manifests had zero
  differences and both combined manifests hashed to
  `825e78e09bfff48b3b4d61bf7660bf817f24e073404abac3aa899deeb212a914`.
- Independently exercised server-signed substitutions for order, JTI, action,
  subject, and audience; v2 downgrade; old-key retained/removed; and honest
  v3, with the results listed above.
- `python3 -m compileall -q athletes/scripts delivery tools webhook`,
  `git diff --check d291eb4..HEAD`, and working-tree `git diff --check` passed.
- No implementation code was changed, no push was performed, and no external
  or live-platform mutation was attempted.

## What I could not verify

- Real TrainingPeaks session/identity/inspection transport, the scheduled
  canary, a live real-order identity binding, or any live platform operation.
- The loopback fake-TP parity test because this managed sandbox forbids its
  socket.
- Mandatory PDF generation/structure for Gravel Full Gym and Masters because
  this environment has no usable PDF engine.
- The supplied outside-workspace totals (**2,563 passed / 86 skipped** and
  acceptance **42 passed / 2 skipped**), production canary evidence, and prior
  real-order human gates. They remain supplied rather than independently
  reproduced evidence.
- Overlapping old/new keys through actual server environment configuration;
  the codec behavior was verified, but the current production loader exposes
  only the single fixed kid noted above.

**Verdict: GO-WITH-CONDITIONS — 0 blockers.**
