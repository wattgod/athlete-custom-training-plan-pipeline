# Phase 3 implementation adversarial review — Codex R5

Date: 2026-08-09
Branch reviewed: `build/trustworthy-phase3` at `88200ae`
Round-4 baseline: `4a379b1`
Binding contract: `docs/SPEC_TRUSTWORTHY_FULFILMENT.md` R9

## Verdict

**NO-GO. One blocker remains.**

Commit `88200ae` closes the literal Round-4 histories: both
`singleton update -> keep -> null snapshot` and
`entitlement create -> keep -> null snapshot` are rejected. The legal adopted
keep chain remains accepted, missing links and cycles fail closed, a
payload-installing compensation record is rejected, and an iterative 5,000-link
adopted chain succeeds without recursion failure.

The new walker does not, however, validate each loaded predecessor as an exact,
revision-bound D0 operation from an integrity-verified contract. It compares a
small field subset and trusts the lookup key. A coordinated forged operation id,
a future/reversed revision chain, or a schema-invalid keep record carrying
compensation fields passes. I used that boundary to hide a real entitlement
`create` behind a forged adoption root; the resulting null snapshot was accepted.
This remains a Phase-3 offline provenance-validation defect, not a later worker
or live-platform condition.

## Round-4 blocker closure

| R4 obligation | Independent result | Closure | Evidence |
|---|---|---|---|
| Written singleton: `update -> keep -> null snapshot` | **Rejected** | **Literal probe closed.** The walker reaches the originating `update` and rejects it because every null-snapshot ancestor must be a payload-null keep. | Walker: `athletes/scripts/apply_contract.py:318-356`; inventory gate: `:392-397`; regression: `athletes/scripts/test_apply_contract.py:212-263`. |
| Created entitlement: `create -> keep -> null snapshot` | **Rejected** | **Literal probe closed.** The same walk reaches and rejects the originating `create`. | Shared parameterized regression: `athletes/scripts/test_apply_contract.py:212-263`. |
| Three-revision adopted keep chain | **Accepted** | **Closed.** A predecessor-null adoption root followed by verified keeps remains legal. | `athletes/scripts/test_apply_contract.py:266-304`. |
| Missing predecessor link | **Rejected** | **Closed.** Reader failure is converted to `ApplyContractError`. | Walker: `athletes/scripts/apply_contract.py:329-333`; regression: `athletes/scripts/test_apply_contract.py:307-347`. |
| Predecessor cycle | **Rejected** | **Closed.** Repeated operation ids fail before another read. | Walker: `athletes/scripts/apply_contract.py:323-328`; regression: `athletes/scripts/test_apply_contract.py:307-347`. |

The R4 blocker is therefore closed for authentic, schema-valid predecessor
records. New Blocker 1 is the adjacent boundary exposed when those records are
forged or type-confused, as this round explicitly required probing.

## New blockers

### 1. Forged or schema-invalid predecessor operations can still manufacture a never-written ancestry

**Claim.** The chain walker validates selected values but not the normative
identity, complete operation branch, containing revision, or integrity of a
loaded predecessor. Equality between `provenance.op_id` and the reader lookup
key is not proof that the id is the required
`{logical_id}@r{generation_revision}` or that the record came from the sealed
contract for that revision.

**Evidence.** R9 makes D0 the normative schema and defines the operation id
exactly as `{logical_id}@r{generation_revision}`
(`docs/SPEC_TRUSTWORTHY_FULFILMENT.md:498-502,514-524`). The executable schema
forbids extra fields and fixes every keep field/rollback shape
(`athletes/scripts/apply_contract.py:107-150`). Current-contract operations are
checked for op-id/revision binding at `athletes/scripts/apply_contract.py:568-569`.
By contrast, predecessor records are converted to a dict and checked only for
lookup-key equality, logical id, kind, digest, disposition, payload, and the
next predecessor shape (`athletes/scripts/apply_contract.py:329-356`). They are
never schema-validated, bound to a containing contract revision, checked to be
older than their child/current contract, or verified against an immutable
contract digest.

Independent adversarial results:

```text
deep_5000_link_adopted_chain: ACCEPTED_LEGAL
middle_link_wrong_logical_id: REJECTED
middle_link_wrong_kind: REJECTED
middle_link_wrong_expected_digest: REJECTED
middle_link_wrong_op_id_uncoordinated: REJECTED
payload_installing_compensation_middle_link: REJECTED
middle_link_coordinated_forged_op_id: ACCEPTED
schema_invalid_keep_labeled_compensation_middle_link: ACCEPTED
non_monotonic_revision_chain_r5_to_r2: ACCEPTED
future_predecessor_r99_for_current_r3: ACCEPTED
coordinated_noncanonical_op_id_hiding_real_create: ACCEPTED
future_revision_r99_hiding_real_create: ACCEPTED
```

The final two probes began with a real entitlement `create` at r1 and a real
keep at r2. I dropped the snapshot, changed the r2 predecessor to either
`forged-adoption-root` or the future but syntactically plausible
`{logical_id}@r99`, supplied a payload-null keep under that key, and retained
the real r1 create in the reader. Revision 3 contract construction accepted the
inventory as never written.

**Why it blocks.** `effective_remote_inventory` is the supersession and later
compensation authority. R9 permits its snapshot reference to be null only for
never-written positional resources
(`docs/SPEC_TRUSTWORTHY_FULFILMENT.md:609-627`). Accepting a non-D0 or
impossible-revision adoption root reclassifies a created entitlement or written
singleton as external state, losing the immutable payload evidence needed by
later reconciliation and cleanup. This is the same offline D0 trust boundary
the R4 repair is intended to close.

**Minimal fix.** Make the operation reader return provenance bound to its
containing, integrity-verified contract (or an equivalent immutable record),
then validate every hop against the exact D0 kind/disposition branch. Enforce
the canonical op-id binding and a strictly older predecessor revision (revision
gaps may remain legal), reject journal/compensation records masquerading as
operations, and verify the root is a genuine sealed predecessor-null adoption
keep. Add direct regressions for a real write/create whose keep is rewired to a
coordinated noncanonical root, a future/reversed revision root, and a keep with
extra compensation fields.

## Non-blocking findings

1. **The intended transitive walk is otherwise sound.** It is iterative, a
   5,000-link legal chain completed, every ordinary wrong middle-link field was
   rejected, and cycle/missing-link handling failed closed.
2. **A recognizable payload-installing compensation cannot pass as-is.** A
   middle record with compensation disposition and a non-null payload was
   rejected. The blocking type-confusion case requires it to retain the checked
   `keep`/null fields while carrying fields forbidden by the D0 keep schema.
3. **R1-R4 closure spot-checks did not regress.** Truthful-power, metric-neutral
   packages, recursive derived coverage/redaction, inventory/attachment
   identity, legacy parity, and catalog projections passed their focused
   suites. The only focused skip was the sandbox-forbidden loopback transport.
4. **Phase 1/2 invariants remain intact.** All 66 state, review-surface, and
   download-token tests passed. Review bundles remain non-executable and
   customer release remains approval- and seal-gated.
5. **No TrainingPeaks execution path is enabled.** The legacy extractor is pure
   and the adapter raises before the historical request loop
   (`delivery/trainingpeaks/adapter.py:24-75,125-139`). Apply-job construction,
   runbook, and job mode raise (`tools/tp_apply_order.py:225-229,313-322`), the
   JavaScript driver throws at line 1 (`tools/tp_apply_driver.js:1-13`), and
   Endure APPLIED remains rejected
   (`webhook/fulfillment_state.py:1268-1280`). The 95-test disabled-path and
   Endure-gate subset passed.
6. **No generation or acceptance-content regression appeared.** The full
   sandbox suite gained the five claimed R4 tests and passed. Opt-in acceptance
   reproduced only the established PDF-engine limitations.

## Standing conditions

New Blocker 1 is the sole remaining offline Phase-3 blocker. The R9 rollout
conditions remain standing and are not reclassified as Phase-3 defects:

1. Keep phase gates ordered. The Phase 2 live human approval gate remains
   pending.
2. Preserve the exact D0 schema, first/subsequent positional branches, and
   migration parity until the historical driver is retired at the later
   cutover.
3. In Phase 4/5, prove persisted intent, reconciliation, ambiguity handling,
   effective-inventory transitions, compensations, kill-point recovery,
   cancellation, and quiescence against the fake server.
4. Prove worker capability exchange, replay recovery, lease fencing,
   per-mutation grant/epoch checks, credential isolation, rate/egress controls,
   and audit redaction before any production write.
5. Obtain controlled live TrainingPeaks canary evidence for identity, marker
   round-trip, HR/LTHR/HRmax/RPE structures, every operation kind,
   create/update/delete/readback/rollback, attachments, singletons,
   entitlements, timeout recovery, and actual idempotency behavior.
6. Preserve deterministic athlete-m, truthful metric-neutral artifacts,
   state/token/seal/outbox failure proofs, and non-executable review/customer
   release gates.
7. Before Phase 5, complete Gmail evidence, deterministic/revocable guide
   release and privacy, F4 compensation, F5 brand isolation, and the explicit
   Endure gate/no-silent-fallback decision.
8. Finish with the controlled real-order end-to-end proof; retain the
   course-resolution, cross-repo polyline, and accepted TrainingPeaks ToS
   conditions.

## Verification performed

### Literal and adversarial probes

- Exact R4 closure selection: **5 passed** — both transitive write/create
  negatives, the legal adopted chain, missing link, and cycle.
- Full focused apply-contract suite: **35 passed, 0 failed**.
- Independent chain probes: 5,000-link legal chain accepted; simple wrong
  logical id/kind/digest/op id rejected; payload-installing compensation
  rejected; coordinated forged id, schema-invalid compensation-labeled keep,
  reversed/future revisions, and both direct real-create bypasses accepted.

### Regression and test suites

- R1-R4 focused truthful-power, metric-neutral package, registry, adapter,
  manifest, and external-catalog subset: **44 passed, 1 skipped**. The skip was
  only loopback transport.
- Phase 1/2 state, review, and token invariant suite: **66 passed**.
- Disabled TP tooling, Phase 1 bypass, and Endure-gate subset: **95 passed**.
- Full suite (`python3 -m pytest -q --disable-warnings --maxfail=25`):
  **2,490 passed, 87 skipped, 21 warnings, 0 failed** in 23.20 s.
- `python3 -m compileall -q athletes/scripts delivery tools webhook` passed.
- `git diff --check 4a379b1..HEAD` passed.

### Opt-in acceptance

With `GG_RUN_ACCEPTANCE=1`, an isolated writable `HOME`, and the original
Python 3.14 user-site packages on `PYTHONPATH`: **36 passed, 4 skipped,
4 failed** in 12.22 s. The four failures are the unchanged mandatory-PDF
presence/structure checks for Gravel Full Gym and Masters. Two Roadie PDF
cases skip under their HTML-fallback contract; the other two skips are the
Roadie-only package cases.

## What I could not verify

1. **Loopback fake-TP transport.** This sandbox forbids binding `127.0.0.1`,
   so the parity transport test skipped. The user-provided outside-sandbox
   result is green, and the reported full result is **2,491 passed / 86
   skipped**; I did not independently execute that socket path.
2. **Mandatory PDFs and non-power PDF text.** No usable PDF engine exists in
   this sandbox. The user reports the PDF checks green outside the sandbox; I
   did not weaken or fabricate the four local failures.
3. **Live systems and later phases.** I made no TrainingPeaks, browser worker,
   Endure, Stripe, email, or external-network call. Identity binding, live
   structure/marker acceptance, apply/readback/rollback, authorization,
   quiescence, Gmail evidence, guide release, and canary health remain later
   gates.
4. **Phase 2 human gate.** One real order approved entirely on the live page
   with a complete seal-bound snapshot remains pending.

## Final disposition

**NO-GO — 1 blocker.**
