# Phase 3 implementation adversarial review — Codex R3

Date: 2026-08-08
Branch reviewed: `build/trustworthy-phase3` at `f41d1dc`
Round-2 baseline: `92fb448`
Binding contract: `docs/SPEC_TRUSTWORTHY_FULFILMENT.md` R9

## Verdict

**NO-GO. Five blockers remain.**

All literal Round-2 regression probes now pass, and the three fix commits are
material improvements. The missing computed artifacts are registered and
materialized, the original FTP/weight/carb notification seeds are suppressed,
dated inventory rejects a null snapshot, attachment create payloads are bound to
their logical key, and the legacy side now calls a pure extraction shared with the
disabled adapter.

The fixes are not authoritative at the boundaries they claim to close. The
derived-field gate remains fail-open for three production artifacts; the fueling
CLI prints parts of a value labeled sensitive; the exact inventory validator cannot
distinguish a written positional resource from an adopted keep; attachment update
rollback payloads bypass identity binding; and parity stores all six historical
workout request fields but compares only title/date/duration. These are offline
Phase-3 contract defects, not Phase-4/5 live-evidence conditions.

## Round-2 blocker closure

| R2 blocker | Literal probe | Closure status | Evidence |
|---|---|---|---|
| 1. A3 coverage was caller-declared and omitted computed artifacts | **Passes.** Adding `new_computed_output` to the strict `derived` artifact now raises `undeclared computed output`; callers can no longer pass `required_fields`. | **Partially closed; still blocking.** The four previously omitted artifacts now emit registries and are materialized, but the authoritative gate is still fail-open for `profile`, `fueling`, and `summary`. | Authoritative tables and their `strict_top_level` flags: `athletes/scripts/derived_registry.py:27-98`; enforcement only when that flag is true: `:181-221`; exact regression: `athletes/scripts/test_derived_registry.py:47-67`; production materialization of all namespaces: `athletes/scripts/generate_athlete_package.py:3353-3374`. See Blocker 1. |
| 2. Failure notification/log and fueling CLI leaked sensitive values | **Passes for the R2 seeds.** FTP, weight, raw failure text, carb ranges, total calories, and product quantities are absent from failure HTML/text, both critical-log fallbacks, and CLI output. | **Partially closed; still blocking.** Failure notification projection is effective and retains ordinary details, but the CLI still prints phase names and week labels from `gut_training.phases`, whose registry entry labels the complete value sensitive. | Notification projection: `webhook/fulfillment_state.py:147-182`; failure render/log boundary: `webhook/app.py:468-485,654-712,835-856`; failure regressions: `webhook/tests/test_phase3_derived_catalog.py:119-160`; sensitive `GUT_PHASES` record: `athletes/scripts/calculate_fueling.py:563-594`; CLI rendering: `:789-800`. See Blocker 2. |
| 3. Dated keep accepted null `payload_snapshot_ref` | **Passes.** A dated inventory record now requires both a non-empty remote ID and snapshot reference. | **Partially closed; still blocking.** The dated branch is fixed, but the stated per-kind invariant is not: a positional record produced by a singleton update is still accepted with a null snapshot, indistinguishable from an adopted keep. | Dated checks and positional remote-ID check: `athletes/scripts/apply_contract.py:317-350`; exact dated regression: `athletes/scripts/test_apply_contract.py:215-232`; adopted/written happy-path tests: `:235-341`. See Blocker 3. |
| 4. Attachment key was not bound to filename/parent payload | **Passes for the current-payload probe.** Filename, parent mismatch, and missing parent are rejected after digest recomputation. | **Partially closed; still blocking.** An attachment `update` has both `payload` and `prior_payload`; validation selects only the first truthy object, so a tampered rollback payload is accepted. | Both payloads are required for dated update: `athletes/scripts/apply_contract.py:106-150`; semantic validation uses `payload or prior_payload`: `:499-513`; the regression tampers only the current payload: `athletes/scripts/test_apply_contract.py:98-115`. See Blocker 4. |
| 5. Legacy parity invented adapter behavior | **Passes for request extraction.** The unreachable adapter and parity test now share `legacy_apply_requests()`, and the extracted workout request contains exactly `external_id`, `title`, `date`, `duration`, `sportType`, and `segments`. Intentional D0-only operation classes and update/delete behavior are named. | **Partially closed; still blocking.** The fake retains the exact request, but the equality projection discards `external_id`, `sportType`, and `segments`. All three can change while parity stays green; the migration-difference assertion is also non-exhaustive. | Shared builder and disabled call site: `delivery/trainingpeaks/adapter.py:24-75,125-139`; declared differences: `athletes/scripts/fake_remote_parity.py:15-32`; workout normalizer compares only three fields: `:41-52`; permissive difference classifier: `:139-158`; parity assertions: `athletes/scripts/test_apply_contract.py:367-441`. See Blocker 5. |

## Blocking findings

### 1. The derived schema is not authoritative for three production artifacts

**Claim.** `ARTIFACT_DERIVED_SCHEMAS` prevents undeclared top-level output only
for artifacts marked `strict_top_level`. `profile`, `fueling`, and `summary` are
explicitly non-strict, so a newly computed output can be added without a schema
entry or provenance record.

**Evidence.** The schema marks those three artifacts `strict_top_level: False`
(`athletes/scripts/derived_registry.py:32-66`). `assert_registry_covers()` checks
unknown document roots only inside the true branch (`:201-208`). I generated a
real fueling document, removed its `_derived` list, added
`new_computed_output: 8675309`, and called the gate with the original records:

```text
fueling_undeclared_top_level: ACCEPTED
```

The checked-in negative test uses `derive_all()`, one of the strict artifacts
(`athletes/scripts/test_derived_registry.py:47-59`), so it cannot detect this
production omission mode. Nested additions under an already registered aggregate
such as `weeks`, `days`, or `configuration` are likewise unclassified by the
schema.

**Why it blocks.** R9 A3 requires every derived value to carry basis, inputs,
sensitivity, time, and revision. A future fueling/profile/summary output can still
shape an athlete-facing artifact while remaining absent from the review catalog.
The R2 defect therefore survives outside the one strict fixture used by the test.

**Minimal fix.** Make every artifact schema total: classify every output path as
derived or explicitly non-derived/raw, reject all unclassified additions, and pin
that inventory with an independent negative test for each artifact class. Do not
let the owner and the enforcement inventory silently omit the same field.

### 2. The fueling CLI exposes part of a value labeled sensitive

**Claim.** The CLI suppresses carb targets and quantities, but prints the keys and
week labels of `gut_training.phases`. That entire field is registered as sensitive.

**Evidence.** The registry helper defaults fueling records to `sensitive`, and
`GUT_PHASES` registers the whole `gut_training.phases` value under that label
(`athletes/scripts/calculate_fueling.py:563-594`). The CLI iterates that value and
prints `phase.upper()` and `info['weeks']` (`:794-797`). A seeded phase key produced:

```text
fueling_cli_sensitive_phase_label_leaked: True
```

The current test checks only `g/hr` values and total calories
(`athletes/scripts/test_derived_registry.py:70-105`), so it passes while another
part of the same sensitive typed value is emitted.

**Why it blocks.** A3 says a value labeled sensitive is absent from every surface
outside authenticated review and server state. The CLI is an operator/log surface;
partial display is still disclosure under the current field-level label.

**Minimal fix.** Either suppress every part of `gut_training.phases` from CLI
output, or split the field into separately registered public/internal labels and
sensitive targets, then render only the non-sensitive records through the common
projection. Add a seed in phase name/week metadata, not only numeric targets.

### 3. Positional inventory snapshot provenance remains unenforceable

**Claim.** `_validate_inventory()` enforces null `remote_id` for positional kinds
but accepts a null `payload_snapshot_ref` for every singleton/entitlement record.
It cannot establish the R9 exception: null is legal only for a never-written
positional keep.

**Evidence.** After the dated checks, the positional branch checks only
`remote_id` (`athletes/scripts/apply_contract.py:337-346`). I built a first-revision
`threshold_update`, materialized an inventory record whose `last_op_id` names that
write but whose snapshot is null, and built revision 2:

```text
written_singleton_null_snapshot: ACCEPTED
```

The happy-path test manually supplies a snapshot for the written branch
(`athletes/scripts/test_apply_contract.py:275-312`) but contains no negative test
that removes it. This contradicts both R9 D0's null-only-for-never-written rule and
the implementation note's claim that written singleton inventory is enforced to
carry a snapshot.

**Why it blocks.** The effective inventory is the supersession authority. Accepting
an impossible record loses the immutable evidence of what this system wrote and
allows corrupted state to pass as complete.

**Minimal fix.** Validate a null positional snapshot against durable last-operation
provenance: permit it only when the resource is demonstrably an adopted verified
keep; otherwise require the immutable payload snapshot. Add negative written
singleton and created-entitlement cases, plus subsequent keep/update coverage.

### 4. Attachment update rollback identity is not validated

**Claim.** Loaded attachment validation binds either `payload` or `prior_payload`,
not both. Dated updates require both, so the rollback source escapes the identity
check.

**Evidence.** The generated operation schema requires current and prior payloads
for dated updates (`athletes/scripts/apply_contract.py:106-150`). The semantic
validator chooses `op.get("payload") or op.get("prior_payload")`
(`:503`), validating only the current value. I built an attachment update by
changing the bytes at the same filename, then changed the prior filename and
parent to a nonexistent workout. With the current payload/digest untouched:

```text
disposition: update
attachment_update_prior_payload_tamper: ACCEPTED
```

The implementation note says the same rules apply to prior payloads, but the
three-way regression only tampers the current create payload or removes the parent
operation (`athletes/scripts/test_apply_contract.py:98-115`).

**Why it blocks.** `prior_payload` is the normative `restore_prior_payload`
compensation source. A valid-looking contract can therefore restore an attachment
under the wrong filename/parent after partial failure or cancellation.

**Minimal fix.** Validate every non-null attachment `payload` and `prior_payload`
independently against the logical-key filename and parent workout identity. When
inventory is supplied, also bind the prior payload digest to the predecessor
snapshot/digest. Add update-specific tamper regressions.

### 5. Parity ignores half of the historical workout request

**Claim.** The legacy builder is now exact, but parity normalizes its six-field
workout request down to `date`, `title`, and `duration`. It does not compare
`external_id`, `sportType`, or `segments` with a D0 equivalent or classify their
absence as an intentional migration difference.

**Evidence.** `legacy_apply_requests()` emits all six fields
(`delivery/trainingpeaks/adapter.py:32-46`), and the raw-shape test pins them
(`athletes/scripts/test_trainingpeaks_adapter.py:82-98`). The comparator discards
three of them (`athletes/scripts/fake_remote_parity.py:41-52`). Independently
changing each exact legacy request field left equality green:

```text
external_id tamper_still_parity= True
sportType tamper_still_parity= True
segments tamper_still_parity= True
```

The declared richer-workout difference mentions TP-native structure replacing the
legacy target representation, but does not classify external identity or sport
type (`fake_remote_parity.py:20-31`). The second-revision test asserts only that
some differences exist and that three expected labels occur; it does not reject
unclassified extra deltas (`athletes/scripts/test_apply_contract.py:434-441`).

**Why it blocks.** R9 requires equivalent normalized remote effects for each
legacy operation class, with intentional migration changes explicitly disposed.
This gate can stay green if an MTB workout becomes the wrong remote sport or if
the historical marker/segment effect changes. That is the exact false-parity class
Round 2 identified.

**Minimal fix.** Define a field-complete normalization for every shared legacy
remote fact, including external marker and sport type. Compare legacy segments with
the explicitly equivalent D0 structure, or classify that conversion with an exact
tested disposition. Assert an exhaustive whitelist of differences; any unknown
delta must fail.

## Non-blocking findings

1. **No over-redaction regression found on the authenticated page.** The authorized
   route passes raw server state to `render_review_page()`
   (`webhook/app.py:2667-2725`), and the renderer displays the typed value directly
   (`webhook/review_surface.py:16-26,68-78`). A seeded sensitive value was present
   on the authenticated page. The external status projection remained redacted.
2. **Ordinary notification details survive.** A direct failure-email probe retained
   athlete name/email, race/date, hours, weeks, workout count, and methodology while
   removing the FTP/weight seed and raw error. The failure path is loud to the coach
   and does not expose those seeded sensitive aliases.
3. **The computed-artifact wiring is real.** Classifications, methodology, calendar,
   and schedule now emit `_derived` entries and all four namespaces reach state
   (`athletes/scripts/generate_athlete_package.py:3357-3374`). The issue is the
   completeness boundary, not absence of this wiring.
4. **No validator thresholds or acceptance expectations were weakened.** The only
   relevant narrowing is the new parity normalization itself, which is Blocking
   Finding 5. `git diff --check 92fb448..HEAD` passes. The Phase-2-to-HEAD check still
   reports only the two already committed trailing-space lines in the R1 review.
5. **R1 spot checks remain closed.** Production finalizes canonical state before ZWO
   publication (`athletes/scripts/generate_athlete_package.py:3145-3177`), ZWO bytes
   render only from validated canonical sessions
   (`athletes/scripts/canonical_training_model.py:658-747`), FTP edge parsing remains
   whole-token and bounded (`athletes/scripts/intake_to_plan.py:466-487`), and
   preview normalization remains metric-aware
   (`athletes/scripts/generate_plan_preview.py:50-100`). The three every-artifact
   non-power fixtures still traverse the webhook, seal, and both bundles
   (`athletes/scripts/test_metric_neutral_packages.py:60-139`).
6. **Phase 1/2 invariants did not regress.** The 66-test sealing/review/token subset
   passed. Review bundles remain non-executable, customer release stays approval- and
   seal-gated, and state/catalog approval behavior is unchanged in the inspected
   paths.
7. **No TrainingPeaks execution path was enabled.** The adapter still raises before
   the shared historical request loop (`delivery/trainingpeaks/adapter.py:125-139`),
   Python job construction/runbook/job mode still raise
   (`tools/tp_apply_order.py:221-229,309-322`), and the JS driver throws at line 1
   (`tools/tp_apply_driver.js:1-13`). The new request extractor is pure and performs
   no I/O. Endure remains gated off for Phase 1.

## Verification performed

### Literal R2 probes and focused suites

- Exact R2 regression selection: **12 passed**.
- R2 changed-file suite (`test_derived_registry`, `test_apply_contract`,
  `test_trainingpeaks_adapter`, `test_phase3_derived_catalog`): **36 passed,
  1 skipped**. The skip is loopback transport.
- Broader Phase-3/R1 focused suite across athlete-m, canonical power, metric-neutral
  packages, preview, manifest, TP projection, derived catalog, apply contract, and
  adapter: **141 passed, 1 skipped**.
- R1 spot-check selection (canonical authority, four FTP edges, LTHR/HRmax/RPE zone
  cases, and every-artifact non-power cases): **16 passed**.

Independent adversarial variants produced:

```text
fueling_undeclared_top_level: ACCEPTED
fueling_cli_sensitive_phase_label_leaked: True
written_singleton_null_snapshot: ACCEPTED
attachment_update_prior_payload_tamper: ACCEPTED
external_id tamper_still_parity= True
sportType tamper_still_parity= True
segments tamper_still_parity= True
```

The authenticated review/non-sensitive notification probe produced:

```text
authenticated_review_retains_sensitive_value: True
notification_redacts_seed: True
all seeded non-sensitive detail checks: True
```

### Full and invariant suites

```text
python3 -m pytest -q --disable-warnings --maxfail=25
```

Result: **2,465 passed, 87 skipped, 21 warnings, 0 failed** in 22.56 s.

```text
python3 -m pytest -q \
  webhook/tests/test_fulfillment_state.py \
  webhook/tests/test_review_surface.py \
  webhook/tests/test_download_tokens.py
```

Result: **66 passed, 0 skipped, 0 failed**.

`python3 -m compileall -q athletes/scripts delivery tools webhook` passed.

### Opt-in acceptance

From `athletes/scripts`, with a writable temporary HOME and the original user-site
packages preserved:

```text
review_home=$(mktemp -d /private/tmp/gg-phase3-r3-home.XXXXXX)
HOME="$review_home" \
PYTHONPATH="/Users/mattirowe/Library/Python/3.14/lib/python/site-packages${PYTHONPATH:+:$PYTHONPATH}" \
GG_RUN_ACCEPTANCE=1 python3 -m pytest test_order_acceptance.py -q -rs
```

Result: **36 passed, 4 skipped, 4 failed** in 12.09 s. The four failures are the
mandatory PDF presence/structure assertions for Gravel Full Gym and Masters. Two
Roadie PDF cases skip under their HTML-fallback contract; the other two skips are
the expected Roadie-only package cases. This matches the documented sandbox result
and is not a new Phase-3 regression.

## What I could not verify in this sandbox

1. **Loopback fake-TP transport.** Binding `127.0.0.1` is forbidden, so the socket
   parity test skipped. It is reported green outside. Its shared normalization has
   the same field-coverage defect as the socket-free path, so transport success does
   not close Blocker 5.
2. **Mandatory PDFs and PDF text for non-power fixtures.** No usable PDF engine was
   available. The four acceptance assertions failed/skipped exactly as documented;
   PDFs are reported green outside. I did not fabricate output or weaken tests.
3. **Live platform evidence.** I made no TrainingPeaks, worker, browser-session,
   Endure, Stripe, email, or external-network call. HR/LTHR/HRmax/RPE live
   acceptance, identity binding, marker round-trip, reconciliation, apply,
   readback, rollback, quiescence, and canary health remain Phase 4/5 standing
   conditions, not Phase-3 code blockers.
4. **Phase-2 human review gate.** One real order approved entirely on the live page
   remains the separate standing condition recorded by R9.

## Final disposition

**NO-GO — 5 blockers.**
