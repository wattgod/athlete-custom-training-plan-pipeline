# Phase 3 implementation adversarial review — Codex R4

Date: 2026-08-09
Branch reviewed: `build/trustworthy-phase3` at `a87812c`
Round-3 baseline: `3507435`
Binding contract: `docs/SPEC_TRUSTWORTHY_FULFILMENT.md` R9

## Verdict

**NO-GO. One blocker remains.**

All five literal Round-3 probes now close. The derived-output gate rejects both
the original fueling addition and nested additions under registered aggregates;
the fueling CLI suppresses seeded phase and week metadata; inventory rejects a
null snapshot when `last_op_id` directly names a singleton write or entitlement
create while still accepting the two legal adopted keeps; both attachment
payload directions are identity-bound; and all six historical workout fields
are compared or assigned an exact, value-retaining migration disposition.

The positional provenance repair is not transitive. Once a system-written
singleton or system-created entitlement is followed by a valid `keep`, a
corrupted inventory record can drop its snapshot and pass validation because
the validator inspects only that immediate payload-null keep. R9 permits a null
snapshot only for a resource that was *never written*. This is an offline D0
validation defect in Phase 3 scope, not a later worker or live-platform
condition.

## Round-3 blocker closure

| R3 blocker | Probe result | Closure | Evidence |
|---|---|---|---|
| 1. Derived schemas were fail-open for production and nested outputs | A real fueling document with `_derived` removed plus `new_computed_output` is rejected. Additions under `gut_training.phases.<phase>`, calendar `weeks[].days[]`, methodology `configuration`, and schedule `days.<day>` are also rejected as unclassified paths. | **Closed.** The owner now supplies recursive closed shapes, and enforcement walks maps/lists and rejects unknown descendants before checking provenance. No legitimate generation regression appeared in focused, full, or acceptance generation. | Closed schema intent and registered aggregates: `athletes/scripts/derived_registry.py:27-33,100-225`; enforcement: `:431-475,478-554`; independent per-artifact negatives: `athletes/scripts/test_derived_registry.py:47-83`. |
| 2. Fueling CLI leaked sensitive phase names/week labels | A seeded `phase-secret-8675309` and `week-secret-8675309` passed through `calculate_fueling.main()` are both absent; the authenticated-review notice remains. | **Closed.** The CLI no longer traverses any descendant of the sensitive `gut_training.phases` aggregate. | Sensitive aggregate record: `athletes/scripts/calculate_fueling.py:589-594`; safe projection and CLI use: `:738-740,789-805`; regression seed: `athletes/scripts/test_derived_registry.py:132-143`. |
| 3. Written positional inventory accepted a null snapshot | A written singleton whose `last_op_id` directly names `update` is rejected. A created entitlement whose `last_op_id` directly names `create` is rejected. First/subsequent adopted singleton and pre-existing-entitlement keeps remain accepted. | **Literal probe closed, but an adjacent transitive-origin defect remains blocking.** See New Blocker 1. | Immediate provenance check: `athletes/scripts/apply_contract.py:318-370`; direct negative and legal-adoption tests: `athletes/scripts/test_apply_contract.py:126-230`. |
| 4. Attachment update rollback identity was unchecked | On a real attachment `update`, changing `prior_payload.filename` or `prior_payload.parent_logical_id` to a nonexistent workout is rejected by `validate_contract`; changing prior content is rejected against the predecessor digest. | **Closed.** Current and prior payloads are independently bound to filename/parent, and prior content is inventory-digest-bound. | Both payload directions and parent existence: `athletes/scripts/apply_contract.py:523-539`; predecessor digest: `:546-556`; update regressions: `athletes/scripts/test_apply_contract.py:263-296`. |
| 5. Parity ignored half the six-field workout request | Tampering `title`, `date`, or `duration` fails. Tampering `external_id`, `sportType`, or `segments` yields respectively `legacy_external_id_to_d0_logical_remote_marker`, `legacy_sport_type_to_d0_tp_workout_type`, or `legacy_segments_to_d0_tp_native_structure`, with exact old/new values retained. An unknown shared-title delta fails. | **Closed.** The normalized workout inventory contains all six fields; allowed dispositions are closed; unknown kinds, field inventories, and shared deltas fail. | Six-field normalization: `athletes/scripts/fake_remote_parity.py:45-67`; closed whitelist and exhaustive classifier: `:20-36,158-219`; six independent tampers: `athletes/scripts/test_apply_contract.py:560-588`. |

## New blockers

### 1. A keep can erase the evidence that a positional resource was previously written

**Claim.** Null-snapshot validation proves only that the immediate
`last_op_id` names a payload-null keep. It does not prove the R9 condition that
the resource was never written. A keep on an existing inventory entry changes
`last_op_id` only, so the prior write/create remains reachable through the
keep's predecessor and must still make a null snapshot illegal.

**Evidence.** R9 defines `payload_snapshot_ref` as null only for keeps of
never-written positional resources and requires existing-entry keeps to update
only `last_op_id`, preserving the snapshot
(`docs/SPEC_TRUSTWORTHY_FULFILMENT.md:609-627`). The validator resolves one
operation and accepts it when it is a matching payload-null `keep`; it never
examines that keep's `predecessor` or origin
(`athletes/scripts/apply_contract.py:351-369`). The new tests cover a direct
write/create as `last_op_id` and a direct adopted keep, but not a write/create
followed by a keep (`athletes/scripts/test_apply_contract.py:126-230`).

I independently built both three-revision histories:

```text
written singleton update -> keep -> null snapshot: ACCEPTED
created entitlement       -> keep -> null snapshot: ACCEPTED
```

The corresponding direct probes are correctly rejected, and both genuinely
adopted branches are correctly accepted. This isolates the defect to lost
origin across a keep, rather than an over-strict rejection of legal adoption.

**Why it blocks.** The effective inventory is the D0 supersession authority.
For a singleton that this system wrote, losing its immutable snapshot destroys
the evidence needed to distinguish owned state and support later compensation.
For an entitlement that this system created, it falsely reclassifies a grant as
a never-written pre-existing keep. Both invalid records pass the Phase-3
contract boundary as complete.

**Minimal fix.** When a positional snapshot is null, follow the durable
predecessor chain (with missing-link and cycle rejection), validating logical
id, kind, digest, and op id at every link. Permit null only when the chain roots
in a predecessor-null, verified adoption `keep`; reject a chain rooted in any
`update`, `create`, or compensation that installed a payload. Add singleton and
entitlement regressions for `write/create -> keep -> lost snapshot`, plus a
three-revision adopted-keep chain that remains legal.

## Non-blocking findings

1. **No over-strict generation regression found.** The recursive schemas
   accepted production profile/fueling/methodology/calendar/schedule variants
   exercised by 2,485 passing tests and by all four acceptance orders through
   package generation. Independent nested additions under the specifically
   registered aggregates failed at the intended boundary.
2. **The CLI is deliberately less informative, but not over-redacted under the
   current label.** Phase names and week labels are suppressed together because
   `gut_training.phases` remains one sensitive typed value. If operator-visible
   phase metadata is desired later, split it into independently classified
   public/internal and sensitive records; printing descendants of the current
   record would violate A3.
3. **The parity whitelist did not admit an unclassified create-path delta.**
   Normalized field inventories must match, title/date/duration differences
   fail, D0-only shared kinds fail, and each representation conversion retains
   exact evidence. The generic `update` disposition applies only when the D0
   operation itself is an update—the intentional legacy-skip-versus-D0-
   supersession behavior—and the normalized field set remains closed.
4. **Commit `1b186e8` repairs the loopback assertions logically.** The post body
   nests the normalized payload beside the idempotency key, and `retained()`
   reconstructs every stored key/payload record for exact comparison against
   each source snapshot (`athletes/scripts/test_trainingpeaks_adapter.py:158-178`).
   It no longer compares bucket count to record count or lets the payload's own
   `external_id` replace the normalized key. The socket-free classifier runs
   before transport. I could inspect but not execute this socket path.
5. **R1/R2 closures and Phase 1/2 invariants remain intact.** The 264-test
   canonical/metric-neutral/seal/state/review/token/apply-contract subset
   passed. Authenticated review still retains typed values while external
   projections redact them, review bundles remain non-executable, and customer
   release remains approval- and seal-gated.
6. **No automated TrainingPeaks execution path is enabled.** The shared legacy
   extractor is pure (`delivery/trainingpeaks/adapter.py:24-46`) and the adapter
   raises before its historical loop (`:125-139`). Python job construction,
   runbook, and job mode raise (`tools/tp_apply_order.py:225-229,313-322`), and
   the JS driver throws at line 1 (`tools/tp_apply_driver.js:1-13`). Endure
   application remains rejected in state transition
   (`webhook/fulfillment_state.py:1268-1284`).

## Standing conditions

The blocker above is the only new offline code blocker. The R9 rollout
conditions remain standing and are not reclassified as Phase-3 defects:

1. Keep the phase gates ordered; the Phase 2 live human approval gate remains
   pending.
2. Keep the D0 schema and first/subsequent positional branches exact, then
   prove migration parity before retiring any historical driver.
3. In Phase 4/5, prove reconciliation, persisted intent, remote-id inventory,
   ambiguity handling, every transition/compensation, kill-point recovery, and
   cancellation/quiescence behavior against the fake server.
4. Prove worker capability exchange, replay recovery, lease fencing,
   per-mutation grant/epoch checks, credential isolation, rate/egress controls,
   and audit redaction before any production write.
5. Obtain controlled live TrainingPeaks canary evidence for identity, markers,
   HR/LTHR/HRmax/RPE structures, create/update/delete/readback/rollback,
   attachments, singletons, entitlements, timeout recovery, and actual
   idempotency limits.
6. Preserve state/token/seal/outbox failure proofs and deterministic athlete-m
   plus metric-neutral fixture gates.
7. Before Phase 5, complete typed Gmail evidence, deterministic/revocable guide
   release and privacy, F4 compensation, F5 brand isolation, and the Endure
   gate/no-silent-fallback decision.
8. Finish with the specified controlled real-order end-to-end proof; retain the
   course-resolution, cross-repo polyline, and accepted TP ToS conditions.

## Verification performed

### Literal and adversarial probes

Independent output:

```text
fueling_removed_registry_plus_new_root: REJECTED
fueling_nested_registered_phase: REJECTED
calendar_nested_weeks_days: REJECTED
methodology_nested_configuration: REJECTED
schedule_nested_days: REJECTED
fueling_cli_seed_phase_leaked: False
fueling_cli_seed_week_leaked: False
written_singleton_last_op_write_null_snapshot: REJECTED
created_entitlement_last_op_create_null_snapshot: REJECTED
adopted_singleton_null_snapshot: ACCEPTED_LEGAL
adopted_entitlement_null_snapshot: ACCEPTED_LEGAL
written_then_keep_lost_snapshot: ACCEPTED
created_entitlement_then_keep_lost_snapshot: ACCEPTED
attachment_prior_filename: REJECTED
attachment_prior_parent: REJECTED
parity title/date/duration tampers: FAILED
parity external_id/sportType/segments tampers: exact named dispositions
unknown shared parity delta: FAILED
```

### Test suites

- R3/R2 registry, apply-contract, adapter, and external-catalog boundary:
  **56 passed, 1 skipped**. The skip is loopback transport.
- Broader R1/R2/R3 and Phase 1/2 invariant subset, including athlete-m,
  truthful power, all-artifact non-power packages, preview, TP projection,
  manifests, state, review, tokens, and disabled TP tooling:
  **264 passed, 1 skipped**.
- Full suite (`python3 -m pytest -q --disable-warnings --maxfail=25`):
  **2,485 passed, 87 skipped, 21 warnings, 0 failed** in 21.51 s.
- `python3 -m compileall -q athletes/scripts delivery tools webhook` passed.
- `git diff --check 3507435..HEAD` passed.

### Opt-in acceptance

With `GG_RUN_ACCEPTANCE=1`, a writable temporary `HOME`, and the original
user-site packages on `PYTHONPATH`: **36 passed, 4 skipped, 4 failed** in
11.49 s. The four failures are the unchanged mandatory PDF
presence/structure assertions for Gravel Full Gym and Masters. Two Roadie PDF
cases skip under their HTML-fallback contract; the other two skips are the
Roadie-only package cases. All four orders completed generation far enough to
exercise the new closed artifact schemas.

## What I could not verify

1. **Loopback fake-TP transport.** Binding `127.0.0.1` is forbidden here, so
   the test skipped. I reviewed `1b186e8` line by line and ran the same
   field-complete socket-free model/comparator. The reported outside result
   (**2,486 passed / 86 skipped**) is consistent with exactly this one test
   moving from skip to pass, but I could not independently execute it.
2. **Mandatory PDFs and non-power PDF text.** This sandbox has no usable PDF
   engine. I did not weaken or fabricate the four acceptance results.
3. **Live systems and later phases.** I made no TrainingPeaks, browser worker,
   Endure, Stripe, email, or external-network call. Identity binding, live
   structure/marker acceptance, apply/readback/rollback, authorization,
   quiescence, Gmail evidence, guide release, and end-to-end canary health
   remain standing Phase 4/5 conditions.
4. **Phase 2 human gate.** One real order approved entirely on the live page
   with a complete seal-bound snapshot remains pending.

## Final disposition

**NO-GO — 1 blocker.**
