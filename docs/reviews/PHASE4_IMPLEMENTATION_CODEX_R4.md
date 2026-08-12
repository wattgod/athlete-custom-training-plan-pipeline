# Phase 4 implementation adversarial review — Codex R4

Date: 2026-08-09

Binding contract: `docs/SPEC_TRUSTWORTHY_FULFILMENT.md` R9, especially I5,
D1, D2, the athlete-m Phase 4 fixture, and the Phase 4 rollout boundary.

Claimed closure boundary: `4930055` and notes commit `eb1010c`, reviewed on
`build/trustworthy-phase4` relative to R3 and the Phase 3 boundary `d291eb4`.

## Verdict

**NO-GO.** The prescribed R3 regressions pass: unsigned claims cannot create a
record, a record under a caller-selected root is ignored, delete-after-verify
fails before the state commit, and the honest signed path reaches approval.
The claimed authenticity boundary is nevertheless incomplete. A caller can
construct `ProbeExecutionStore` over the **server-selected root** with a
caller-controlled `CapabilityCodec`; the resulting v2 record is accepted by
readback because persistence checks only record shape and equality, not that
the record was authorized by the server's trusted signing key. The independent
probe cleared the pending requirement and reached `APPROVED` with
`capability_kid=attacker-kid`.

This is the inherited R3 authenticity blocker through a new, concrete
same-root path, not a separate second blocker. Live transport, the scheduled
canary, human gates, and Phase 5 remain standing conditions rather than
additional blockers.

## R3 blocker closure

| R3 requirement | R4 result | Evidence |
|---|---|---|
| Fabricated `succeeded` record through `run_record()` using unsigned claims plus matching public evidence | **Rejected as prescribed.** `run_record()` derives the expected action from the request and calls its configured codec before creating the order directory or invoking transport. The verbatim regression proved the operation was not called and no JSON was written. | Verification before paths/writes: `delivery/trainingpeaks/worker_service.py:351-358,443-472`; regression: `delivery/trainingpeaks/test_worker_service.py:160-183`. |
| Caller-supplied store root | **Rejected as prescribed, but insufficient.** `record_manual_readback()` no longer accepts a store argument and opens the configured root itself. Evidence written only under a different attacker-selected root was ignored and approval stayed null. | Server root resolver: `delivery/trainingpeaks/worker_service.py:82-90`; persistence selects it: `webhook/d2_identity.py:723-744`; regression: `webhook/tests/test_d2_identity.py:377-426`. |
| Delete-after-verify TOCTOU | **Closed for the prescribed race.** Fulfilment state is locked before evidence, the record lock remains held, and the record is re-read immediately before atomic state replacement. Injected deletion left state byte-identical and pending. | Guard and record lock: `delivery/trainingpeaks/worker_service.py:289-313,527-551`; lock ordering/final recheck: `webhook/d2_identity.py:731-744,811-814`; regression: `webhook/tests/test_d2_identity.py:429-465`. |
| Honest signed capability -> record -> evidence -> readback -> approval | **Works.** Exact signed worker output cleared the sealed requirement, stored JTI/kid/digest/time and derived provenance, and then approved. The authenticated CSRF route also passed. | Worker evidence construction: `delivery/trainingpeaks/worker_service.py:624-691`; state transition: `webhook/d2_identity.py:743-815`; unit path: `webhook/tests/test_d2_identity.py:288-349`; HTTP path: `webhook/tests/test_review_surface.py:319-417`. |
| Overall authenticity boundary | **Not closed.** The configured filesystem location is authoritative, but the signer that populated a record at that location is not authenticated during readback. | Blocker below. |

## New blockers / remaining blocker

There is no independent second blocker. The new same-root exploit below shows
that the one inherited R3 blocker remains open.

### 1. The authoritative root is not bound to the authoritative signer

`ProbeExecutionStore` still has a public constructor accepting any root and
any `CapabilityCodec` (`delivery/trainingpeaks/worker_service.py:316-324`).
Its verification is only as trustworthy as that caller-supplied codec
(`:443-472`). The server-selected root is itself available from the public
resolver (`:82-90`), so a caller can instantiate:

```text
ProbeExecutionStore(authoritative_probe_execution_root(), attacker_codec)
```

and present a capability signed by the attacker's own key. `run_record()`
correctly verifies that token against the attacker's codec, then stores only a
derived context containing the claimed kid, audience, action, and claims digest
(`:351-377`). It does not retain a server-verifiable signed envelope.

At the trust decision, `record_manual_readback()` opens the authoritative store
**without a capability codec** (`webhook/d2_identity.py:723-744`). The record
reader accepts any nonempty audience, a syntactically valid claims digest, and a
kid equal to the public evidence object's kid; it never verifies those fields
against a configured trusted key or signed capability
(`delivery/trainingpeaks/worker_service.py:474-524`). Exact self-consistency is
therefore mistaken for authenticity. Persistence then removes the pending
requirement and writes the resolution (`webhook/d2_identity.py:764-815`), after
which the normal approval consistency check accepts it
(`webhook/d2_identity.py:892-903`).

Independent sealed-order probe:

```text
attacker-controlled CapabilityCodec
  + ProbeExecutionStore(server-selected root, attacker codec)
  + correctly shaped attacker-signed inspect capability
  + matching canned result lthr_bpm=155
    -> v2 succeeded record written under authoritative root

record_manual_readback(public matching evidence)
    -> pending requirement cleared

transition(..., APPROVED, ...)
    -> APPROVED

stored capability_kid
    -> attacker-kid
```

This violates D2's requirement that `manually-corrected` be confirmed by worker
readback (`docs/SPEC_TRUSTWORTHY_FULFILMENT.md:797-811`) and I5's requirement to
distinguish verified external evidence from caller assertion.

The filesystem probe exposed the same missing boundary from another angle.
Lexical order-id escapes such as `../escape`, `a/b`, and `/absolute` reject, but
a symlinked per-order directory under the configured root is followed: both the
record and lock were written outside the root and the operation succeeded.
`_paths()` validates components but does not resolve and contain the resulting
path (`delivery/trainingpeaks/worker_service.py:336-342`), and subsequent mkdir,
open, and replace operations follow it (`:357-378,566-579`). This is counted as
part of the same authenticity/root-integrity blocker.

Closure requires the record consumed at readback to be cryptographically or
operationally bound to the server's trusted signer and protected root, rather
than merely having been verified by some codec selected by the writer. It must
also reject symlink escapes beneath that root.

## Additional adversarial probe results

- Wrong action at record creation: **rejected** before record creation.
- Wrong audience at record creation: **rejected** before record creation.
- Wrong subject/TP athlete id at record creation: **rejected** before record
  creation.
- Expired capability at record creation: **rejected** before record creation.
- All four capability negatives left **zero JSON records**.
- Concurrent readback of the same honest evidence: **serialized safely**; one
  attempt committed and the other rejected because no pending requirement
  remained.
- Direct lexical record-root path escape: **rejected**.
- Symlinked order directory beneath the record root: **accepted and escaped the
  root**, counted in blocker 1.
- Other `d2_pending_requirements` mutation sites were reviewed. The only other
  clearing path is resolution-effect retraction
  (`webhook/d2_identity.py:561-590`), which installs the replacement command
  under the state lock and remains covered by exact approval-effect
  reconstruction (`:842-907`). No separate HTTP/state bypass was found.

## Prior closure and Phase 1-4 spot-checks

- **R1 blocker 1 — automated approval identity:** TrainingPeaks and Endure
  reject without an order-scoped binding and approve with a valid binding;
  manual approval remains identity-exempt while APPLIED requires nonempty
  delivery evidence (`webhook/tests/test_d2_identity.py:560-642`).
- **R1 blocker 2 — stale effects after switching:** all 12 directed pairs among
  `use-tp-value`, `update-from-intake`, `manually-corrected`, and
  `cannot-resolve` still retract prior effects and validate the terminal state
  (`webhook/tests/test_d2_identity.py:645-726`).
- **R1 blocker 4 — stale terminal probe reuse:** fresh logical attempts use
  fresh JTIs and freshly observe changed transport data
  (`delivery/trainingpeaks/test_worker_service.py:108-140`).
- **R2 blocker 2 — approval snapshot provenance:** a client disposition that
  contradicts the executed D2 command returns 409; the exact authoritative
  command is snapshotted and its sealed operation preserved
  (`webhook/tests/test_review_surface.py:248-317`).
- The athlete-m Phase 3/4 goldens retain null FTP, `power_basis: none`, HR
  control, no watt claims, exactly one HR field test, no pre-approval ZWOs,
  sealed PlanIR/apply-contract artifacts, the closed blocker set, exact D2
  inspection values, exact three confirmations, and unresolved-approval
  rejection (`athletes/scripts/test_athlete_m_phase1.py:34-371`;
  `tests/fixtures/athlete_m/expected/phase4.json:1-40`).
- Phase 4 mutation entrypoints and execution-grant issuance continue to refuse
  before transport (`delivery/trainingpeaks/test_worker_service.py:320-335`).
- The broad Phase 1-4 gate covered sealed downloads, review authority,
  fulfilment state, bypass gates, D0/apply-contract projection, PlanIR,
  metric-neutral packages, truthful power, worker/D2, and athlete-m goldens.
- Fresh current and clean `d291eb4` acceptance builds produced byte-identical
  ZWOs: **284/284** (Gravel 89, Masters 77, Road Fondo 72, Road Climb 46).
  The sorted `<file-sha256>  <athlete-relative-path>` manifests had zero
  differences and each combined manifest hashed to
  `fd4d9ca1a63ad7880d7e633fd8afac0b096aa26485c9148255d8217253537289`.

## Non-blocking findings

1. `WorkerTransportError` and malformed worker-fixture I/O remain outside the
   review route's handled exception set (`webhook/app.py:2961-2968`). State
   fails closed, but the coach gets a generic 500 instead of the durable 409
   review error used for `FulfillmentStateError`.

2. `D2_CANNOT_RESOLVE` remains a global blocker id. Installing a second such
   resolution removes the first global issue before inserting the new one
   (`webhook/d2_identity.py:703-711`). Approval still fails closed because it
   revalidates every D2 item, but multi-item triage can under-report findings.

3. Acceptance race selection remains dependent on the review date. Current
   and clean Phase 3 selected the same races and 284 workouts on this run, but
   a fixed clock would make the manifest a permanently stable golden.

No new non-blocking defect separate from these carried findings was found.

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

- Read `CLAUDE.md`, all three task-relevant handover skills, R9, R3, the two
  claimed commits, their diffs, and the implementation notes.
- Re-ran the four prescribed R3 probe classes plus the honest HTTP path:
  **6 passed**.
- Worker, D2, authenticated review, fulfilment-state, and athlete-m focused
  suites: **119 passed**.
- Broad Phase 1-4 state/authority/projection/golden gate: **244 passed, 1
  skipped, 1 warning**. The skip is the sandbox-forbidden loopback fake-TP
  contract.
- Complete local suite: **2,558 passed, 87 skipped, 21 warnings** in 49.14 s.
- Opt-in acceptance with `GG_RUN_ACCEPTANCE=1`, isolated writable `HOME`, and
  the existing user-site dependency path: **36 passed, 4 skipped, 4 failed**.
  The four failures were only the mandatory PDF presence/structure checks for
  Gravel Full Gym and Masters; the four Roadie PDF/package cases supplied the
  expected skips.
- A clean `d291eb4` archive reproduced the same acceptance result: **36 passed,
  4 skipped, 4 failed**.
- Independently compared the current and clean Phase 3 ZWO manifests as
  described above.
- Executed the attacker-codec-at-authoritative-root, wrong
  action/audience/subject/expiry, lexical/symlink escape, and concurrent
  readback probes described above.
- `python3 -m compileall -q athletes/scripts delivery tools webhook` and
  `git diff --check d291eb4..HEAD` passed.
- No implementation code was changed and no push or external mutation was
  performed.

## What I could not verify

- Real TrainingPeaks session/identity/inspection transport, live capability
  exchange, scheduled canary behavior, or any live platform operation.
- The loopback fake-TP parity contract because the managed sandbox forbids the
  socket.
- Mandatory PDF generation/structure for Gravel Full Gym and Masters because
  this sandbox has no usable PDF engine.
- The supplied outside-workspace totals (**2,559 passed / 86 skipped** and
  acceptance **42 passed / 2 skipped**), production canary evidence, and prior
  real-order human gates; these remain supplied evidence rather than
  independently reproduced evidence.

**Verdict: NO-GO — 1 blocker.**
