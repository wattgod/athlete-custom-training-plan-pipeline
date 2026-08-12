# Phase 4 implementation adversarial review — Codex R2

Date: 2026-08-09

Binding contract: `docs/SPEC_TRUSTWORTHY_FULFILMENT.md` R9, especially D1,
D2, C, S1-S3, A3, D0, the athlete-m Phase 4 fixture, and the Phase 4 rollout
boundary.

Claimed fix boundary: `ad7f5f7` and notes commit `1e29200`, reviewed relative
to R1 and the Phase 3 boundary `d291eb4`.

## Verdict

**NO-GO.** Three of the four R1 blockers are closed. R1 blocker 3 is only
functionally closed on the honest HTTP path: its new evidence type is publicly
constructible and remains forgeable at the persistence boundary. One new
approval-provenance blocker also allows a CSRF-authenticated client to submit a
resolution disposition different from the resolution command actually stored
and executed.

The retraction, approval-effect consistency, fresh-JTI, platform-identity,
CSRF/authentication, zero-write, Phase 1/2/3 regression, Phase 4 closed-golden,
and ZWO-byte probes otherwise held.

## R1 blocker closure

| R1 blocker | R2 result | Evidence |
|---|---|---|
| 1. Automated approval without identity | **Closed.** `trainingpeaks` and `endure` without an order-scoped binding reject; valid bindings approve. A manual order approves without identity, but APPLIED rejects empty evidence and requires the requested platform to match the immutable platform. The supported regeneration API rejects a `delivery_platform` change, and a raw platform-only edit makes the review catalog inconsistent and the state unloadable. | Automated gate: `webhook/d2_identity.py:815-823`; it is reached for both active and inactive D2 state at `webhook/fulfillment_state.py:1236-1239,1338-1343`. Platform immutability: `webhook/fulfillment_state.py:655-663`. Manual APPLIED evidence/platform checks: `webhook/fulfillment_state.py:1364-1400`. Matrix tests: `webhook/tests/test_d2_identity.py:406-477`. |
| 2. Resolution switching leaves stale effects and approval accepts tampered effects | **Closed.** All 12 directed transitions among `use-tp-value`, `update-from-intake`, `manually-corrected`, and `cannot-resolve` ended with only the terminal override, operation, pending requirement, derived readback, resolved marker, and blocker. A tampered terminal operation rejected approval. Injecting an exception after in-memory retraction left the state byte-identical; concurrent plan-changing switches serialized, with one success and one stale-revision rejection. | Retraction: `webhook/d2_identity.py:557-590`; revision/CAS check and single locked command write: `webhook/d2_identity.py:600-605,640-715`; exact approval reconstruction: `webhook/d2_identity.py:828-908`; regression matrix and tamper negative: `webhook/tests/test_d2_identity.py:480-580`; atomic replace: `webhook/fulfillment_state.py:559-597`. |
| 3. Sealed manual correction cannot complete and caller can forge readback | **Not closed.** The sealed HTTP flow now works, wrong CSRF/value and a bare dict reject, exact worker output records JTI/kid/digest/time plus a sensitive registry record, and approval then succeeds. But `VerifiedInspectionEvidence` is a public ordinary dataclass. `record_manual_readback()` treats `isinstance(..., VerifiedInspectionEvidence)` as proof of worker origin and never verifies a capability, signature, or succeeded replay record. An independently constructed instance with `capability_kid="forged-kid"`, a zero digest, invented timestamp/JTI, and a matching result cleared the pending requirement and reached `APPROVED`. This is still caller-asserted evidence in a different container. | Public constructor: `delivery/trainingpeaks/worker_service.py:66-76`; honest construction after capability verification: `delivery/trainingpeaks/worker_service.py:421-454`; nominal-type-only gate and persistence: `webhook/d2_identity.py:719-790`; load-time checks prove only shape/self-consistency, not origin: `webhook/d2_identity.py:124-179`; honest authenticated route: `webhook/app.py:2891-2969`; existing test covers bare dict and honest evidence only: `webhook/tests/test_d2_identity.py:281-340`. |
| 4. Fresh capabilities reuse a terminal JTI and return stale probe data | **Closed.** Pipeline probe and inspection attempts and review readbacks now use UUID4 JTIs. A fresh JTI invoked the changing transport and returned the second value; the same JTI/digest invoked transport once and returned its recorded terminal result. | Issuance: `athletes/scripts/intake_to_plan.py:3875-3890`, `webhook/app.py:2922-2930`; replay semantics: `delivery/trainingpeaks/worker_service.py:289-335`; same-JTI and fresh-JTI tests: `delivery/trainingpeaks/test_worker_service.py:64-84,103-135`. |

## Blockers

### 1. R1 blocker 3 remains open: the typed readback evidence is forgeable

The new type carries the right fields, and the honest worker fills them from a
verified capability and canonical request digest. That is useful typing, but it
is not an authenticity boundary. Any caller can import and instantiate the
dataclass. The persistence function checks the Python class, order id, TP id,
and expected value, then copies the caller's JTI, kid, digest, and timestamp
into authoritative state. The derived registry cross-check proves the two
stored records agree with each other; it does not prove either record came from
the worker.

Independent sealed-state probe:

```text
bare dict                                  -> REJECTED
public VerifiedInspectionEvidence instance -> ACCEPTED
capability_kid                             -> forged-kid
request_digest                             -> 0000...0000
approval                                   -> APPROVED
```

This violates D2's worker-readback requirement and I5's evidence provenance.
The persistence boundary needs evidence whose origin it can verify—for example,
a signed worker evidence envelope or an exact cross-check against the durable
succeeded replay record—not a caller-constructible nominal type.

### 2. New: approval trusts the submitted resolution disposition instead of the executed state command

For active D2 state, `validate_d2_approval()` validates the authoritative
resolution and effects before the transition processes the submitted review
decisions (`webhook/fulfillment_state.py:1236-1239`). The decision loop then
accepts any `resolved:<choice>` that appears in the catalog's allowed choices
(`webhook/fulfillment_state.py:1283-1337`). It never requires that submitted
choice to equal the catalog's `resolved_resolution` or the matching
`d2_resolutions[item_id].choice`. The HTTP route builds these decisions directly
from client-controlled `resolved_item` form values (`webhook/app.py:2795-2802`).

Independent sealed-state probe:

```text
executed authoritative choice -> update-from-intake
sealed apply operation         -> threshold_update to 160 bpm
submitted approval disposition -> resolved:use-tp-value
approval result                -> APPROVED
stored approval snapshot       -> resolved:use-tp-value
```

The apply effect remains consistent with the authoritative command, so this is
not an effect-tampering bypass. It is nevertheless a blocking I5/C/D2 failure:
the state file falsely says which resolution the approving credential approved,
and the supposedly server-owned command can be rewritten in approval evidence
by the browser. The transition must derive the disposition from authoritative
state or reject a submitted mismatch.

## Non-blocking findings

1. The new readback endpoint's auth and CSRF direction is sound in the inspected
   offline path: session loading is order/revision-bound
   (`webhook/app.py:2669-2685`), the endpoint is POST-only and checks the session
   CSRF token with `compare_digest` (`webhook/app.py:2939-2957`), and the CSRF
   token itself comes from `secrets.token_urlsafe(32)`
   (`webhook/review_auth.py:275-295`). Wrong CSRF returned 403; wrong worker value
   returned 409 and retained the pending requirement.

2. Worker/fixture I/O and `WorkerTransportError` are not included in the
   endpoint's handled exception set (`webhook/app.py:2963-2969`). Such a failure
   remains closed because the pending requirement is retained, but it becomes a
   generic 500 instead of a durable, coach-readable readback failure.

3. `D2_CANNOT_RESOLVE` is represented as one global blocker id. Installing a
   second cannot-resolve choice removes the first item's blocker before adding
   the second (`webhook/d2_identity.py:699-707`). Approval still fails closed
   because every authoritative D2 resolution is rechecked, but multi-item coach
   triage can under-report which findings are unresolvable.

4. The R1 sensitivity-projection hardening gap remains: current reachable
   status/notification/log/package surfaces did not expose seeded D2-sensitive
   values, but applying the generic external projection to a raw whole D2 state
   would not inherently redact unlabeled `account_inspection`/`d2_context`
   containers. No current caller was found doing that.

5. Account weight remains unmodeled by D2. It is not present in the R9 athlete-m
   worker literal and does not block Phase 4, but a future transport weight value
   would receive neither A3 provenance nor review policy.

6. The acceptance race selection remains date-dependent. Fresh Phase 3 and
   Phase 4 archives both selected 72 Road Fondo workouts on this review date;
   clock-pinning remains advisable if a stable historical count/hash is intended.

## Standing conditions

- Complete the R9 Phase 4 live gate: real-order identity binding and account
  inspection, zero writes, and the scheduled read-only canary green.
- Retain the Phase 2 real-order human review gate; it was not independently
  repeated in this offline review.
- Phase 5 still owns live execution-grant exchange effects, leases/fencing and
  epochs, cancellation quiescence, mutation intents/journals, reconciliation,
  apply/readback/rollback, D0 cutover, release components, and Endure's final
  gated disposition.
- Live credential/TOTP storage, TLS, egress restrictions, immutable worker
  audit, production rate limits, and live HR/RPE/marker acceptance remain
  rollout evidence, not offline Phase 4 blockers.
- The supplied outside-sandbox green results—full **2,551 passed / 86 skipped**
  and acceptance **42 passed / 2 skipped**—remain external evidence. The local
  loopback/PDF restrictions below explain the independently reproduced gap.

## Verification performed

- Read `CLAUDE.md`, all three task-relevant handover skills, the full R9 spec,
  the R1 review, both claimed commits, and the implementation notes.
- R1 closure-only regression selection: **20 passed**, including the two
  automated platforms, manual approval/APPLIED direction, all 12 directed
  threshold-resolution switches, tampered effects, sealed manual readback,
  authenticated review flow, fresh JTI, and same-JTI replay.
- Broad first focused Phase 4/state/review/golden set: **135 passed**.
- Phase 1/2/3 plus Phase 4 focused invariants, D0 projection, download, bypass,
  worker and adapter set: **195 passed, 1 skipped**. The skip was the
  sandbox-forbidden loopback fake-TP parity test.
- Full suite: **2,550 passed, 87 skipped, 21 warnings** in 45.50 s.
- Opt-in acceptance with `GG_RUN_ACCEPTANCE=1`, a writable isolated HOME, and
  the existing user-site dependency path: **36 passed, 4 skipped, 4 failed**.
  The four failures were only mandatory PDF existence/structure for Gravel Full
  Gym and Masters. The four skips were the two permitted Roadie PDF fallbacks
  and two Roadie-only package cases.
- Repeated acceptance from fresh `git archive d291eb4` and fresh `git archive
  HEAD`; each independently produced the same **36 passed, 4 skipped, 4 failed**
  sandbox result.
- Compared sorted per-file SHA-256 manifests for the four clean-archive athlete
  trees. Phase 3 and Phase 4 were byte-identical **284/284**: Gravel 89, Masters
  77, Road Fondo 72, Road Climb 46. No per-file diff existed. Under this review's
  explicit manifest serialization (sorted `shasum -a 256` lines including
  relative paths), both combined manifests hash to
  `fd4d9ca1a63ad7880d7e633fd8afac0b096aa26485c9148255d8217253537289`.
- Independent adversarial probes covered forged typed evidence, mismatched
  approval disposition, injected failure after in-memory retraction, concurrent
  plan-changing switches, supported and raw platform-only mutation, fresh vs
  same-JTI transport behavior, and the exact R1 command sequences.
- `python3 -m compileall -q athletes/scripts delivery tools webhook`,
  `git diff --check` for each claimed commit, and `git diff --check d291eb4..HEAD`
  passed.
- No implementation code was changed; no push or external mutation was made.

## What I could not verify

- Real TrainingPeaks session/identity/inspection transport, live capability
  exchange, the scheduled canary, or any live platform write/readback behavior.
- The fake-TP loopback parity case, because the workspace sandbox forbids
  loopback sockets.
- Mandatory PDF generation/structure for Gravel Full Gym and Masters, because
  the sandbox does not permit a usable PDF engine.
- The supplied outside-sandbox suite totals, production canary evidence, or
  prior real-order human gates; those are recorded as supplied evidence only.

**Verdict: NO-GO — 2 blockers.**
