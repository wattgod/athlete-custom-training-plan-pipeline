# Phase 3 implementation adversarial review — Codex R6

Date: 2026-08-09
Branch reviewed: `build/trustworthy-phase3` at `8ed00aa`
Round-5 baseline: `88200ae`
Binding contract: `docs/SPEC_TRUSTWORTHY_FULFILMENT.md` R9

## Verdict

**GO-WITH-CONDITIONS. Zero blockers remain.**

Commit `8ed00aa` closes the sole Round-5 blocker at the offline Phase-3
boundary. A predecessor lookup now returns immutable canonical bytes for a
containing contract plus a trusted contract digest and model seal. The walker
rehashes and canonicalizes those bytes, checks the seal binding, validates the
complete contract against the generated exact D0 schema, selects exactly one
operation by the lookup key, binds its canonical operation id to the containing
revision, binds order and athlete identity, and requires revisions to descend
strictly. It then applies the existing logical-id, kind, desired-digest,
payload-null keep, and predecessor-shape checks at every hop.

All six Round-5 forgeries are rejected. The legal 5,000-link adopted chain and
the three-revision adopted keep chain remain accepted; the Round-4 write/create
histories, ordinary uncoordinated tampers, missing links, and cycles remain
rejected. I found no new Phase-3 offline code defect.

The remaining trust-anchor obligation is real but not a blocker under the
specified threat model: a later production reader must obtain the trusted
contract digest and model seal from the integrity-verified immutable store. If
it instead recomputes both from attacker-supplied candidate bytes, it has
self-certified the forgery and defeated the assumed seal. That is a Phase-4/5
integration condition, or an out-of-model sealed-store rewrite, not a defect in
this offline walker.

## Round-5 blocker closure

| R5 requirement | Independent result | Evidence |
|---|---|---|
| Reader returns contract-bound immutable provenance | **Closed.** `OperationProvenance` contains canonical contract bytes, trusted digest, and model seal; the binding helper rejects malformed digests, digest mismatch, and seal mismatch. | `athletes/scripts/apply_contract.py:40-54,72-94`; direct binding negatives at `athletes/scripts/test_apply_contract.py:72-83`. |
| Containing-contract digest and canonical-byte binding | **Closed.** Every hop requires the typed provenance record, hashes the returned bytes, parses them, and requires byte-for-byte canonical serialization. | `athletes/scripts/apply_contract.py:374-402`. |
| Contract seal and exact D0 schema binding | **Closed.** The containing contract's seal must equal the trusted seal and be a lowercase SHA-256 value; the entire contract is then checked through the generated schema whose operation union forbids extra fields and fixes each `kind x disposition` branch. | Walker: `athletes/scripts/apply_contract.py:403-409`; exact branches/schema: `:150-236`; schema execution: `:243-256`. |
| Order, athlete, canonical op-id, unique membership | **Closed.** Containing identities must match the current contract, lookup selects exactly one member, and the id must equal `{logical_id}@r{containing revision}`. | `athletes/scripts/apply_contract.py:410-429`. |
| Revision monotonicity | **Closed.** Every containing revision must be older than both its child and the current revision; the child bound advances at each iterative hop. Revision gaps remain legal. | `athletes/scripts/apply_contract.py:410,415-418,451-452`. |
| Complete never-written ancestry | **Closed.** Every hop must match logical id, positional kind, and inventory digest and must be an exact payload-null keep; only a predecessor-null root returns success. | `athletes/scripts/apply_contract.py:431-452`; null-snapshot inventory gate and current identity context: `:455-497,623-628`. |

This implements R9's canonical operation identity and exact operation schema
(`docs/SPEC_TRUSTWORTHY_FULFILMENT.md:498-524`) and protects the rule that a
null positional snapshot is legal only for never-written adopted state
(`docs/SPEC_TRUSTWORTHY_FULFILMENT.md:609-627`).

### Required Round-5 forgery probes

Re-run independently by exact scenario name:

```text
middle_link_coordinated_forged_op_id: REJECTED
schema_invalid_keep_labeled_compensation_middle_link: REJECTED
non_monotonic_revision_chain_r5_to_r2: REJECTED
future_predecessor_r99_for_current_r3: REJECTED
coordinated_noncanonical_op_id_hiding_real_create: REJECTED
future_revision_r99_hiding_real_create: REJECTED
```

The six direct regressions are at
`athletes/scripts/test_apply_contract.py:364-541`. The exact six-test selection
passed **6/6**.

### Required legal and prior-negative probes

```text
deep_5000_link_adopted_chain: ACCEPTED_LEGAL
three_revision_adopted_keep_chain: ACCEPTED_LEGAL
written_singleton update -> keep -> null snapshot: REJECTED
created_entitlement create -> keep -> null snapshot: REJECTED
missing_predecessor_link: REJECTED
predecessor_cycle: REJECTED
middle_link_wrong_logical_id: REJECTED
middle_link_wrong_kind: REJECTED
middle_link_wrong_expected_digest: REJECTED
middle_link_wrong_op_id_uncoordinated: REJECTED
payload_installing_compensation_middle_link: REJECTED
```

The 5,000-hop regression is
`athletes/scripts/test_apply_contract.py:322-361`; the legal adopted chain and
Round-4 transitive negatives are at `:227-319`; missing-link and cycle
regressions are at `:544-582`. The Round-4/adoption/missing/cycle selection
passed **5/5**. I also reconstructed the five ordinary uncoordinated middle-hop
tampers outside the checked-in cases; all were rejected.

## New blockers

None.

## Non-blocking findings

1. **The binding fails closed at each independently probed boundary.**
   Noncanonical containing bytes, cross-order provenance, cross-athlete
   provenance, duplicate lookup membership, a mismatched trusted seal, a
   mismatched trusted contract digest, and the former unbound mapping reader
   were all rejected. A legal revision gap from r1 to current r7 was accepted.
2. **The walk remains iterative but exact validation is intentionally paid per
   hop.** The full 5,000-link case completed without recursion failure. This is
   sufficient for the required offline regression; production latency and
   storage lookup behavior remain later-worker concerns.
3. **R1-R5 closure probes did not regress.** The truthful-power,
   metric-neutral-package, recursive derived registry/redaction, manifest,
   projection, adapter/parity, and derived-catalog set passed **58**, with only
   the sandbox-forbidden loopback case skipped.
4. **Phase 1/2 invariants remain intact.** All **66** fulfillment-state,
   authenticated-review, and download-token tests passed. Review bundles
   remain non-executable and customer release remains approval- and seal-gated.
5. **No TrainingPeaks execution path was enabled.** The legacy request
   extractor is pure and `TrainingPeaksAdapter.apply` raises before the
   historical request loop (`delivery/trainingpeaks/adapter.py:24-75,125-139`).
   Apply-job construction, runbook, and job mode raise
   (`tools/tp_apply_order.py:225-229,313-322`), the JavaScript driver throws at
   line 1 (`tools/tp_apply_driver.js:1-13`), and Endure APPLIED remains rejected
   (`webhook/fulfillment_state.py:1268-1284`). The focused disabled-path set was
   **80 passed / 1 loopback skip**.
6. **Golden ZWO scope is unchanged.** `8ed00aa` modifies only
   `apply_contract.py`, `test_apply_contract.py`, and the implementation notes.
   The diff from `88200ae` contains no ZWO, golden, schema, workout generator,
   or state-manifest change. The Round-5 established clean-twin 253-ZWO
   manifest therefore remains byte-identical at SHA-256
   `79452230ea1cdf33fcc684e971816bc1805e84eefbbdbc7e3579bb5d49c3985e`.

## Standing conditions

1. **Sealed-store reader construction.** The later reader must resolve one
   authoritative immutable contract for an order/revision and source
   `contract_digest` and `model_seal` from seal-bound trusted state. It must not
   compute the alleged trust values from the candidate bytes it is validating.
   Rewriting that store or defeating its seal remains outside the Phase-3
   offline threat model.
2. **Phase ordering and human approval.** Complete the pending Phase-2 live
   human gate: one real order approved entirely on the authenticated page with
   a complete seal-bound snapshot.
3. **D0 and migration parity.** Preserve the exact operation schema,
   first/subsequent positional branches, effective-inventory rules, and
   field-complete legacy parity until the historical driver is retired at the
   later cutover.
4. **Phase 4/5 fake-server evidence.** Prove persisted intent,
   reconciliation, ambiguity handling, inventory transitions, compensations,
   kill-point recovery, cancellation, and quiescence against the fake server.
5. **Worker security.** Prove capability exchange and replay recovery, lease
   fencing, per-mutation grant/epoch checks, credential isolation,
   rate/egress controls, and audit redaction before any production write.
6. **Controlled live canary.** Obtain live TrainingPeaks evidence for identity,
   marker round-trip, HR/LTHR/HRmax/RPE structures, every operation kind,
   create/update/delete/readback/rollback, attachments, singletons,
   entitlements, timeout recovery, and real idempotency behavior.
7. **Phase-5 release prerequisites.** Complete Gmail evidence,
   deterministic/revocable guide release and privacy, F4 compensation, F5
   brand isolation, and the explicit Endure gate/no-silent-fallback decision.
8. **Final end-to-end gate.** Finish with the controlled real-order proof and
   retain the course-resolution, cross-repo polyline, and accepted
   TrainingPeaks ToS conditions.

## Verification performed

### Focused and adversarial verification

- Full focused apply-contract suite: **42 passed, 0 failed** in 19.54 s.
- Exact six Round-5 forgeries: **6 passed, 36 deselected**; all six rejected.
- Required Round-4/adopted/missing/cycle selection: **5 passed,
  37 deselected**.
- Independent uncoordinated middle-hop probes: **5/5 rejected**.
- Independent binding probes: noncanonical bytes, wrong order, wrong athlete,
  duplicate lookup membership, seal confusion, digest confusion, and the old
  unbound mapping return were rejected; legal r1-to-r7 revision gap accepted.

### Regression suites

- Phase 1/2 state, review, and token invariants: **66 passed**.
- R1-R5 truthful-power, metric-neutral package, derived registry/redaction,
  adapter, manifest, projection, and derived-catalog spot-check:
  **58 passed, 1 skipped**. The skip was only loopback transport.
- Disabled TP tooling, Phase-1 bypass, adapter, and state gate subset:
  **80 passed, 1 skipped**. The same loopback case was the skip.
- Full suite (`python3 -m pytest -q --disable-warnings --maxfail=25`):
  **2,497 passed, 87 skipped, 21 warnings, 0 failed** in 41.74 s.
- `python3 -m compileall -q athletes/scripts delivery tools webhook` passed.
- `git diff --check 88200ae..HEAD` and `git diff --check 4a379b1..HEAD`
  passed.

### Opt-in acceptance

With `GG_RUN_ACCEPTANCE=1`, an isolated writable `HOME`, the repository root
and original Python 3.14 user-site packages on `PYTHONPATH`: **36 passed,
4 skipped, 4 failed** in 13.07 s. The four failures are the unchanged mandatory
PDF presence/structure checks for Gravel Full Gym and Masters. Two Roadie PDF
cases skip under their HTML-fallback contract; the other two skips are the
Roadie-only package cases. All non-PDF acceptance behavior passed.

## What I could not verify

1. **Loopback fake-TP transport.** This workspace sandbox forbids loopback
   sockets, so `test_phase3_contract_has_fake_server_effect_parity_with_legacy_manifest`
   skipped. The provided outside-sandbox full result is **2,498 passed / 86
   skipped**, exactly one skip becoming a pass; I did not independently run
   that socket path.
2. **Mandatory PDFs and non-power PDF text.** No usable PDF engine is available
   in this sandbox. The four local failures are the established environmental
   cases. The review brief reports them green outside; I did not weaken the
   assertions or claim an independent outside run.
3. **A second clean-twin ZWO rebuild.** I verified the golden boundary by git
   tree scope and the unchanged generating code, not by recreating the Round-5
   clean pre-fix/current archives. The acceptance fixture reuses local athlete
   work directories, so those directories are not a trustworthy clean manifest
   source.
4. **Live and later-phase systems.** I made no TrainingPeaks, browser worker,
   Endure, Stripe, email, or external-network call. Store implementation,
   identity binding, live structure/marker acceptance, apply/readback/rollback,
   authorization, quiescence, Gmail evidence, guide release, and canary health
   remain the standing gates above.
5. **Phase-2 human gate.** The required real-order live approval remains
   pending and was not simulated as implementation evidence.

## Final disposition

**GO-WITH-CONDITIONS — 0 blockers.**
