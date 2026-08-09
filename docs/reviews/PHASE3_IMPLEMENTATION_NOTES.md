# Phase 3 implementation notes — truthful power and offline apply contract

Date: 2026-08-08

Normative basis: `docs/SPEC_TRUSTWORTHY_FULFILMENT.md` r9 and the standing
conditions in `docs/reviews/SPEC_TRUSTWORTHY_FULFILMENT_CODEX_R9.md`, with the
closed Phase 1/2 review records treated as regression requirements. Phase 2's
human live-page gate remains pending. Phase 3 performs no live TrainingPeaks
inspection or mutation, adds no worker, and does not re-enable the transitional
JS/browser driver.

## Scope disposition

### A1 — canonical truthful training model: implemented

- `canonical_training_model/v1` is the persisted per-session authority. Every
  segment carries exactly one typed target: `power_pct_ftp`, `pct_lthr`,
  `pct_hrmax`, `rpe`, or `free`. PlanIR, TP manifest, preview, guide, and D0
  operations project from this artifact.
- Intake no longer estimates FTP from weight, sex, or age. Missing/unknown FTP
  persists as `ftp_watts: null`, `power_basis: none`, and a typed
  `POWER_BASIS_NONE_CONFIRM` catalog item. The transitional `FTP_ESTIMATED`
  rule remains server-owned and non-waivable, but truthful Phase 3 generation
  no longer emits it.
- Control selection prefers a requested measured-power basis, then LTHR, then
  HRmax, then RPE. An athlete requesting HR without either HR anchor keeps an
  HR plan identity with `rpe_pending_lthr`; sessions use RPE until the Week 1
  HR field test records an anchor. The re-anchor point is serialized in the
  profile, canonical model, guide, preview, and review value.
- ZWO is a power-only release projection. HR/RPE authored intermediates live
  only in a short-lived compiler directory and are destroyed immediately
  after canonicalization; they never enter the athlete artifact tree, review
  bundle, customer ZIP, release manifest, or apply contract. A canonicalization
  failure therefore cannot strand a non-power ZWO in the package directory.
- TP-native offline projections use `percentOfThresholdHr` for LTHR,
  `percentOfMaxHr` for HRmax, and RPE in the description with `structure: null`.
  Live acceptance/readback remains the explicit Phase 5 canary gate.

### A1 fueling/intake projections: implemented

- Null-power fueling uses duration, goal/intensity descriptor, and body-mass
  g/kg/hour bounds. Its serialized inputs contain no FTP, watts, work rate, or
  fabricated kJ. Unsafe/missing body mass is labeled and deferred to the field
  test rather than converted to a power estimate.
- The guide and preview are null-safe and omit numeric power/FTP rows and
  examples for HR/RPE athletes. Metric-neutral copy is applied to remaining
  general execution prose before publication.
- Existing forgiving-order behavior remains: estimable/defaultable intake
  fields do not kill a paid order. Defaults are labeled in provenance and the
  review catalog.

### A3 — derived-value registry and enforcement: implemented

- The shared registry validates `{id, field, class, basis, inputs,
  sensitivity, at, revision}` and rejects duplicate IDs, unknown classes,
  unknown sensitivity labels, non-canonical inputs, and invalid revisions.
- Intake, fueling, and canonical-session derivations record provenance. Their
  typed values are materialized only into the server-side fulfillment state
  and feed `review_catalog/v1` as `verified_fact` items. Regeneration rewrites
  each state record to the current generation revision.
- `sensitive` is enforced: notification construction, non-review status/API
  projections, and export/log-safe projections replace value, message, basis,
  and review value with an authenticated-review redaction. Intake/fueling CLI
  output no longer prints sensitive FTP, W/kg, weight, or carbohydrate values.
  The authenticated no-store review page and server-side state retain the
  typed value as required by S3.

### D0 — `apply_contract/v1` offline projection: implemented

- `schemas/apply_contract_v1.schema.json` is generated from the executable D0
  definition and checked for byte-equivalent JSON content before validation.
  Every emitted contract is Draft 2020-12 schema-validated and semantically
  validated; unknown versions fail closed.
- The schema contains the three identities, all seven operation kinds, the
  exact allowed dispositions, per-kind payload shapes, nullable/common fields,
  rollback strategies, positional/dated predecessor shapes, compatibility
  floor, and first/subsequent singleton and entitlement branches.
- Logical IDs are stable across revisions and use date plus daily ordinal,
  note/task slug, parent plus filename, singleton name, or product ID. Attempt
  IDs bind logical ID and generation revision. Remote markers exist only for
  round-tripping dated kinds and embed the logical ID.
- Contract construction diffs desired resources against the supplied
  `effective_remote_inventory`, serializes every inventory disposition,
  copies prior payloads for dated update/delete compensation, requires fresh
  singleton before-images for CAS updates, and rejects missing/incorrect
  predecessors. Positional resources are kept rather than implicitly deleted;
  entitlements remain irreversible-by-us with rollback `none`.
- Ordering is deterministic: singletons; dated deletes/updates with parent
  workouts before dependent notes/tasks/attachments; dated creates/keeps by
  date with the same dependency order; entitlements last.
- The current legacy manifest's workouts, derived calendar dates, native
  notes, attachments, mental tasks, and course entitlement all have parity in
  D0. Pure offline parity runs in the normal suite. A second gate uses the
  repository's existing in-process fake TP server and is skipped only where
  loopback sockets are sandbox-forbidden; no live host or credentials exist in
  that test.
- When no D2 binding exists, the offline envelope records
  `tp_athlete_id: offline-unbound:<athlete_id>` rather than claiming the local
  slug is a TrainingPeaks identity. Phase 4 binding/inspection must regenerate
  that projection before any later apply gate.

### S2 binding used by Phase 3: implemented

- The finalization graph is acyclic: finalized canonical model, pre-seal
  review catalog, guide-source digests, and ordered operation payloads produce
  the model seal; the contract is emitted once with that seal; artifact bytes
  then produce the immutable release manifest and artifacts-array digest.
- Persistence recomputes the canonical seal from copied release sources and
  rejects a mismatched contract before writing `release_manifest.json`.
  Verification rechecks both layers. `FACT_RELEASE_SEAL` is intentionally
  excluded from the upstream catalog input because that fact exists only after
  the model seal; it remains in the approval catalog.
- Revisions without a Phase 3 contract retain the tested Phase 1 transitional
  artifact-byte seal path. This preserves existing Phase 1/2 orders and tests.

## Fixture and regression disposition

- Athlete-m has a literal `expected/phase3.json` and fixed-clock production
  replay. Exact blockers are `COURSE_UNRESOLVED`, `RACE_STALE`,
  `SESSION_PREDATES_GENERATION`, and `WEEKS_MISMATCH`; exact confirmations are
  `POWER_BASIS_NONE_CONFIRM` and `SCHEDULE_MISMATCH_CONFIRM`.
  `FTP_ESTIMATED` is absent. All Phase 1 negative assertions remain active.
- Athlete-m additionally proves the Week 1 HR field test, no source/customer
  ZWOs, no numeric watt figures across textual artifacts, duration-based
  fueling, schema-valid D0 output, canonical seal equality through persistence,
  review-bundle non-executability, customer-release refusal, and non-waivable
  approval refusal.
- Deterministic HR-with-LTHR, HR-only-HRmax, and RPE-only fixtures prove target
  types, TP-native offline projection, Week 1 field-test naming/re-anchor, null
  FTP, and zero watt figures.
- D0 fixtures cover schema tampering, stable/revision identities, first and
  subsequent adopted singleton keeps, first and subsequent pre-existing
  entitlement keeps, serialized update/delete prior payloads, ordering,
  legacy-manifest parity, the fake server, and absence of a production apply or
  network surface.
- A3 regressions cover invalid registry classes/sensitivities, typed catalog
  materialization, revision advancement, seeded-sensitive notification/export
  redaction, and rejection of an unbound contract seal.

## Decisions, deviations, and rebuttals

- No normative deviation was taken. The mature workout authoring engine is
  retained as an internal compiler input to reduce unrelated scheduling churn,
  but the persisted canonical model is upstream of every published or platform
  projection and non-power ZWO bytes never enter an artifact tree.
- The six legacy tests that positively required fabricated FTP/W/kg were
  superseded under A1.2. They now assert null FTP, `power_basis: none`, no W/kg
  fabrication, and continued profile sanity/buildability. No Phase 1 negative
  or bypass assertion was removed.
- The `VO2max` schedule classifier was corrected to recognize the title as an
  intensity session. This preserves athlete-m's settled
  `SCHEDULE_MISMATCH_CONFIRM` rather than silently weakening the Phase 1
  review catalog after metric-neutral projection.
- There are no reviewer findings rebutted. R9 conditions 2, 3, and 7 are
  implemented for the Phase 3 offline boundary. R9 conditions 4–6 and 8–11
  remain later-phase/live gates and were not represented as complete.

## Verification

- Complete sandbox suite: `pytest -q --disable-warnings --maxfail=25` →
  **2,416 passed, 87 skipped, 21 warnings, 0 failed**.
- The additional skip is the fake-TP loopback parity gate; it runs outside the
  restricted sandbox together with the existing socket tests.
- Fixed-clock athlete-m Phase 3 production replay: **1 passed**.
- HR/LTHR, HRmax, RPE plus D0 offline fixtures: **11 passed**.
- `python3 -m compileall -q athletes/scripts delivery tools webhook` passed.
- `git diff --check` passed.
- No live TrainingPeaks, browser, worker, Stripe, email, or external-network
  action was attempted.

## Commits

1. `035acee` — implement Phase 3 truthful power, A3 enforcement, canonical
   sealing, and the offline schema-backed D0 contract.
2. `1bc8260` — add Phase 3 athlete-m, HR/RPE, positional, parity, redaction,
   and negative regression gates.
3. `ebe5ea5` — keep non-power authored intermediates outside release artifacts.
4. `b0bafae` — label unbound Phase 3 TP identities truthfully.
5. `42cb466` — assert null-power fueling never fabricates work rate or kJ.
6. This notes file is committed last. No push was attempted.

## Roadie order-acceptance regression disposition (2026-08-08)

### Zone distribution — measurement regression, no plan-content change

- Diagnosis was performed against the Phase 2 merge parent (`d8cb3e1^2`), not
  inferred from the failing percentages. The Phase 2 roadie acceptance subset
  passed (**20 passed, 4 environment skips**), and recursive comparison plus
  per-file SHA-256 comparison showed every Phase 2 and Phase 3 roadie ZWO was
  byte-identical for both `acc-roadiefondo` and `acc-roadieclimber`. No golden
  plan content or workout serializer changed.
- The regression was introduced when the Phase 3 preview projection replaced
  ZWO-derived aggregate intensity with the maximum target found anywhere in a
  canonical session. A 40/20 interval therefore classified its warm-up,
  recoveries, and cooldown as VO2 time. That produced the false 49% and 39%
  easy-time results even though the executable plans were unchanged.
- Disposition: preview zone accounting consumes the canonical segment
  durations and typed targets to calculate one normalized session intensity,
  using fourth-power duration weighting for work and recovery. The session is
  then classified once and its actual duration contributes to that zone. This
  restores the Phase 2 check's calibrated unit—duration-weighted hard/easy
  **session emphasis**—without returning to Phase 3's erroneous maximum-target
  shortcut. It follows
  `SPEC_TRUSTWORTHY_FULFILMENT.md` **A1.1**, which requires preview to be a
  projection of the metric-neutral canonical model and gives each segment one
  typed target. The target and PASS/WARN/FAIL thresholds were not changed or
  weakened.
- Repaired results under the final, single definition: fondo **84% easy
  session time (2269/2695 min), WARN**; hill climb **83% (2602/3123 min),
  WARN**. Both remain visible coach signals and no longer fail delivery on
  maximum-target classification.

### 40/20 PlanIR-to-ZWO mismatch — incomplete canonical projection

- Diagnosis: the canonical model correctly held interval `on`/`off` targets,
  repeat count, and work/recovery durations. Its PlanIR compatibility
  projection populated `on_power` and `off_power` but left `power_low` and
  `power_high` null. The persisted ZWO parser truthfully exposes both pairs:
  `on_power`/`off_power` plus their derived min/max bounds. Consequently the
  G5 validator compared an incomplete PlanIR projection with the executable
  ZWO and raised the named `PACKAGE_ZWO_*_SEGMENTS` findings. Null fields on
  non-interval segments were display noise and were not suppressed to fix the
  mismatch.
- Disposition: the power PlanIR projection now derives interval `power_low`
  and `power_high` from the canonical on/off targets while preserving the
  original fields. This makes PlanIR describe the on-disk workout exactly, as
  required by `SPEC_TRUSTWORTHY_FULFILMENT.md` **A1.1** (PlanIR and ZWO are
  projections of one canonical model) and `PLAN_TRUTH_SPEC.md` **G5** (session
  structure must compare exactly against the executable ZWO). The validator
  was not silenced or weakened. Both roadie packages now return zero findings.

### Regression verification

- Focused preview/canonical/package tests: **73 passed, 1 expected warning**.
- Phase 3 golden/replay group: **25 passed, 1 sandbox socket skip**.
- Full order-acceptance file after the gravel closure: **42 passed, 2 expected
  non-roadie skips, 0 failed**. A temporary sandbox-only Chromium launcher was
  used for mandatory PDF rendering and removed immediately after the run;
  production PDF configuration was restored unchanged.
- Complete sandbox suite: **2,419 passed, 87 skipped, 21 warnings, 0 failed**.
- `git diff --check` passed. No acceptance golden or expected plan-content file
  was changed, and no push or external mutation was attempted.
- Git commits could not be created in this managed worktree because Git could
  not create `.git/worktrees/trustworthy-phase3/index.lock` (`Operation not
  permitted`). Intended coherent boundaries are: (1) duration-weighted
  canonical session-intensity preview accounting plus its roadie/gravel
  regressions; (2) faithful PlanIR interval bounds plus the end-to-end
  package-validator regression; (3) these diagnosis and verification notes.
  No push was attempted.

## Gravel-fullgym order-acceptance closure (2026-08-08)

### Artifact identity and population diagnosis

- The comparison reused the preserved Phase 2 checkout at
  `/private/tmp/gg-phase2-acceptance.WnuTzO` and the Phase 3
  `acc-gravelrider` package. Both packages contain **89 ZWOs**. Sorted
  per-file SHA-256 manifests are identical: no filename, byte, workout
  structure, or plan-content change occurred. The only Phase 3-only package
  artifacts are the canonical model and apply contract; differences in common
  non-ZWO artifacts are Phase 3 provenance/seal fields, generated timestamps,
  and projections.
- Strength was explicitly tested as the first suspected population change and
  ruled out. Phase 2's ZWO-based preview included **300 strength minutes** in
  the evaluated calendar population and classified all 300 as easy from the
  strength ZWO's low normalized IF. Phase 3 included the same 300 minutes and
  classified them the same way. The total denominator remained exactly
  **5008.75 minutes**. Strength therefore did not cause the regression, and no
  per-order or strength-specific filter was added.
- The actual delta was entirely measurement semantics. Phase 2 assigned
  **4228.75 easy / 780 hard minutes** by each ZWO's normalized session IF
  (**84.43% easy, WARN**). Segment-literal accounting assigned **4411 easy /
  597.75 hard minutes** (**88.07%, FAIL**) because recovery, warm-up, and
  cooldown portions of hard sessions moved to the easy bucket. That 182.25
  minute reclassification explains the failure without any plan change.

### One zone-distribution definition

- The check now has one definition for every order and control metric:
  canonical typed segments → fourth-power duration-weighted session effort →
  one session zone → the session's actual duration in that zone. This is
  duration-weighted **session-zone time**, not literal physiological
  segment-level time-in-zone; the preview label now says “easy session time”
  to remove that ambiguity.
- This is the truthful comparison for this check's existing target. The
  methodology catalog describes a hard/easy split in terms of “hard days,”
  and the generator/distribution regressions classify whole workout types.
  Phase 2 calibrated the acceptance thresholds against normalized session IF.
  Comparing that session-emphasis target with segment-literal minutes mixed
  two different units. `SPEC_TRUSTWORTHY_FULFILMENT.md` **A1.1** is preserved:
  the preview derives the session effort from all canonical typed segments,
  rather than independently authoring or taking the maximum target. No target,
  threshold, golden order, or expected plan content changed.
- Final acceptance results are gravel-fullgym **84% (4229/5009, WARN)**,
  masters **78% (2979/3796, PASS)**, roadie fondo **84% (2269/2695, WARN)**,
  and roadie hill climb **83% (2602/3123, WARN)**.

## R1 adversarial-review disposition (2026-08-08)

All nine findings in `PHASE3_IMPLEMENTATION_CODEX_R1.md` were accepted as
valid. No finding is disputed or silently omitted.

1. **Canonical authority — closed.** The mature generator now emits every
   authoring document into a private in-memory inventory inside a temporary
   directory. `canonical_training_model/v1` is finalized and exact-union
   validated before publication; ZWO, PlanIR, preview, TP structure/polyline,
   apply-contract session payloads, and guide control/re-anchor evidence then
   project from it. Production canonicalization neither reads nor globs a
   published ZWO. Negative union tests reject missing, mixed, forbidden,
   cross-metric, non-finite, out-of-range-RPE, and illegal-free shapes.
   Round-trip tests delete/poison the legacy source and prove the canonical
   session alone controls every downstream session projection.
2. **Numeric FTP edges — closed.** `parse_watts` full-matches one signed token
   and accepts only finite values within the existing plausible FTP bounds.
   Zero, negative, malformed/partial, and implausible tokens produce null FTP,
   `power_basis: none`, null W/kg, and `POWER_BASIS_NONE_CONFIRM`; the paid
   order remains sanity-valid and buildable.
3. **Metric-aware zone accounting — closed.** Power retains its byte/content-
   pinned normalized IF behavior. LTHR and HRmax invert their own canonical
   mapping, RPE uses its own 1–10 effort mapping, and free rides remain
   unprescribed estimates. Ramp and interval duration weighting happens only
   after that type-specific normalization. Preview verification carries a
   metric-neutral effort internally and publishes IF only for power.
4. **Every-artifact non-power fixtures — closed.** LTHR, HRmax, and RPE cases
   now run the production webhook subprocess, package builder, sealing,
   release-manifest creation, and both ZIP builders. Each case inspects guide,
   preview, coaching brief, plan summary, release manifest, every textual ZIP
   member, and PDF text when a PDF engine is available. They assert zero
   numeric watts/%FTP, the exact Week 1 field test, serialized re-anchor type
   and action, and absence of customer ZWOs.
5. **Derived registry — closed.** Revision is mandatory at entry construction,
   every owning artifact stamps the prospective/current generation revision,
   and registry documents reject stale entries. Explicit coverage inventories
   now gate computed profile fields; fueling duration, calories, carb targets
   and ranges, gut phases/progression, timeline, prescription, basis,
   recommendations and hydration; and review-facing plan-summary dates,
   methodology/score, tier, ability, fueling summaries, control/field-test/
   re-anchor evidence, and workout count. A negative coverage test fails on an
   unregistered derived output.
6. **Sensitive external projection — closed.** One recursive
   `external_state_projection` owns the non-review API boundary. It redacts
   sensitive live and archived catalog objects plus approval credentials,
   waiver reasons, and application evidence at any nesting depth. The real
   post-approval status endpoint is exercised with a seeded sensitive value;
   neither live nor approval-snapshot output contains it.
7. **Normative inventory — closed.** The offline builder accepts exactly
   `{remote_id, desired_digest, payload_snapshot_ref, kind, last_op_id}`.
   Inline payload is rejected. Dated update/delete requires an explicit
   snapshot reader, validates the resolved canonical payload against the kind
   schema and stored digest, and copies that immutable value into
   `prior_payload`. Exact update and delete records are regression-tested.
8. **Attachment identity — closed.** Attachment logical keys are exactly
   `{parent_logical_key}:{filename}`; `parent_logical_key` is carried
   separately from the full parent logical ID and the pair must agree. Literal
   identity fixtures and per-kind grammar checks cover workouts, notes/tasks,
   attachments, singletons, and entitlements.
9. **Legacy-to-D0 parity — closed offline.** The legacy projection now exposes
   the complete normalized remote field set. A field-aware socket-free fake
   remote compares legacy reconciliation with D0 effects across create,
   update, delete, keep, every dated kind, positional singletons,
   attachments, and entitlements. The loopback test uses the identical full
   state comparison and remains enabled for CI environments that permit local
   sockets.

### R1 verification evidence

- Focused R1 regressions: **144 passed, 1 skipped**; the skip is only the
  loopback transport variant, while its field-aware socket-free equivalent
  passed.
- Phase 1/2 sealing, gated-review, and download-token invariants:
  **66 passed**.
- Complete sandbox suite: **2,452 passed, 87 skipped, 21 warnings, 0 failed**.
- Opt-in production order acceptance with a writable `HOME`: **36 passed,
  4 skipped**. Four remaining test failures are solely the two mandatory-PDF
  assertions for each Gravel God fixture: this sandbox has no Chromium/PDF
  engine. The two Roadie PDF cases correctly skipped under their HTML-fallback
  contract. No PDF result was fabricated.
- Golden power projection: the pre-change and final sorted manifests contain
  exactly **253 ZWOs** (89 Gravel, 77 Masters, 41 Road Fondo, 46 Road Climb).
  `diff -u` is empty and both manifest files have SHA-256
  `0b9bad73ac3b38a4b3c0f72b007a9f0c8e0c9330ca8d9741cd883df0aa4624b5`.
- `python3 -m compileall -q athletes/scripts webhook` and
  `git diff --check` passed. No live TP, network, email, Stripe, browser, or
  worker action was attempted.

### R1 commit boundaries

1. `494d3ce` — `fix(phase3): make canonical sessions authoritative and metric truthful` —
   `intake_to_plan.py`, `canonical_training_model.py`, `zwo_parser.py`,
   `generate_athlete_package.py`, `training_guide_builder.py`, `plan_ir.py`,
   `generate_plan_preview.py`, `validate_plan_package.py`,
   `calculate_fueling.py`, `derived_registry.py`, and their focused tests,
   including `test_metric_neutral_packages.py`.
2. `ab65607` — `fix(phase3): enforce normative reconciliation inventory and identities` —
   `apply_contract.py`, `fulfillment_manifest.py`, `fake_remote_parity.py`,
   `test_apply_contract.py`, `test_fulfillment_manifest.py`, and
   `test_trainingpeaks_adapter.py`.
3. `b413280` — `fix(phase3): recursively redact external fulfillment evidence` —
   `webhook/fulfillment_state.py`, `webhook/app.py`, and
   `webhook/tests/test_phase3_derived_catalog.py`.
4. `docs(phase3): record all R1 dispositions and verification evidence` —
   this notes file (committed last).

## R2 adversarial-review disposition (2026-08-08)

All five blockers in `PHASE3_IMPLEMENTATION_CODEX_R2.md` are closed offline.
The R1 probes and Phase 1/2 invariant suites remain regression tests.

1. **Authoritative A3 coverage — closed.** `derived_registry.py` now owns an
   authoritative field schema for each computed artifact: profile, fueling,
   summary, classifications, methodology, calendar, and weekly schedule. The
   coverage gate enumerates those schemas itself; callers can no longer supply
   a list that omits a new output. Entirely computed artifacts reject unknown
   top-level output fields. Classifications, methodology, calendar, and
   schedule owners now emit `_derived` records, and package generation
   materializes all four namespaces into fulfillment state/review catalog.
   The negative regression adds an output without changing a coverage list and
   proves that validation fails.
2. **External notification and CLI projection — closed.** Success and failure
   notification data is recursively passed through the same external
   projection before template rendering or log fallback. Sensitive legacy
   aliases and raw top-level failure text are removed. Seeded regressions cover
   failed-order email, missing-email-configuration logging, email-send-failure
   logging, and fueling CLI stdout; none exposes FTP, weight, carbohydrate
   ranges, or product quantities.
3. **Per-kind inventory values — closed.** Every dated record requires a
   non-empty `remote_id` and `payload_snapshot_ref`. Positional singletons
   require null `remote_id`; written singleton inventory carries a snapshot,
   while an adopted positional keep may retain null remote/snapshot identity.
   Tests cover first and subsequent keeps plus later compensable updates from
   both adopted and previously written singleton branches, and from dated
   records.
4. **Loaded attachment identity — closed.** Semantic validation splits the
   attachment logical key and binds its filename component to
   `payload.filename`, its parent-key component to
   `payload.parent_logical_id`, and that parent to an existing workout
   operation or inventory identity. The same rules apply to prior payloads.
   Digest-preserving tampered-contract tests cover filename, parent ID, and
   missing-parent attacks.
5. **Exact legacy/D0 parity boundary — closed.** The adapter exposes a pure,
   non-executing extraction of its historical request builders with the exact
   legacy fields (`external_id`, `title`, `date`, `duration`, `sportType`, and
   `segments` for workouts) and exact supported create operations. The adapter
   still raises before that code and no TrainingPeaks execution path is
   enabled. A field-complete fake applies legacy requests and D0 operations
   independently, then compares only shared normalized remote facts.

### Intentional D0 migration differences

The following are migration behavior, not legacy-parity claims:

- Mental-task installation is required by the R9 D0 contract; the historical
  adapter omitted it.
- Positional singleton writes are new D0 operations; the historical adapter
  did not own those remote facts.
- Update and delete are required for revision supersession and reconciliation;
  the historical adapter supported create/keep only.
- D0 workout payloads preserve richer typed target data than the historical
  request builder. Shared legacy fields must still normalize identically.

These differences remain behind the offline contract plus the Phase 4/5
coach-reviewed cutover, canary, readback, and rollback gates. The parity suite
classifies them explicitly and never silently treats them as equivalent legacy
effects.

### R2 verification evidence

- R2-focused apply/registry/adapter/catalog suite: **50 passed, 1 skipped**;
  the only skip is the loopback transport variant. Its socket-free,
  field-complete equivalent passed.
- Phase 1/2 state, review, and download-token invariants: **66 passed**.
- Complete sandbox suite: **2,465 passed, 87 skipped, 21 warnings, 0 failed**.
- Opt-in order acceptance with writable `HOME`: **36 passed, 4 skipped,
  4 failed**. The same result occurs in a fresh pre-change archive. All four
  failures are the mandatory PDF presence/structure assertions for Gravel and
  Masters in a sandbox without a PDF engine. Roadie HTML fallback accounts for
  two skips; the other two are expected Roadie-only package cases.
- Fresh pre-change and final acceptance builds each contain **253 ZWOs**:
  89 Gravel, 77 Masters, 41 Road Fondo, and 46 Road Climb. The sorted manifest
  diff is empty and both manifests have SHA-256
  `e82ebcd550b7cbedc46b9c0d8ae4ff2a955bbc690a26231f110797344c885c7c`.
- No live TrainingPeaks, network, email, Stripe, browser, or worker action was
  attempted. The remaining loopback and PDF checks require a less restricted
  environment.

No push is part of Phase 3 implementation.

## R3 adversarial-review disposition (2026-08-08)

All five blockers in `PHASE3_IMPLEMENTATION_CODEX_R3.md` are closed at the
offline Phase 3 boundary. The R1/R2 probes, Phase 1/2 release gates, pure
extraction boundary, and disabled adapter remain intact.

1. **Total artifact schemas — closed.** `derived_registry.py` now owns a
   recursive, closed output-shape classification for profile, fueling, summary,
   classifications, methodology, calendar, and weekly schedule. Every emitted
   root is derived or explicitly raw/non-derived; registered aggregates have
   closed descendant inventories, including fueling phases/progression,
   methodology configuration, calendar weeks/days, and schedule days. Unknown
   top-level or nested paths fail before provenance coverage is considered.
   Seven independent negatives add an output to each artifact class without
   editing the schema or a caller-supplied list and all are rejected.
2. **Sensitive fueling phase aggregate — closed.** `gut_training.phases`
   remains one sensitive typed value. The CLI no longer iterates or renders any
   descendant: phase names, week labels, descriptions, guidance, and targets
   are all suppressed behind one authenticated-review message. A seeded phase
   name and seeded week label are both absent from the CLI-safe rendering.
3. **Positional snapshot provenance — closed.** A null positional
   `payload_snapshot_ref` now requires an explicit durable last-operation
   reader. The resolved operation must match logical id, kind, op id, and
   digest and must be a payload-null verified `keep`; a preceding singleton
   write or entitlement create is rejected. Adopted singleton and pre-existing
   entitlement keeps retain their legal null-snapshot path with immutable
   provenance, while written singleton keep/update and created-entitlement
   keep paths retain non-null snapshots.
4. **Attachment rollback identity — closed.** Loaded attachment validation
   independently binds both non-null `payload` and `prior_payload` to the
   logical-key filename and stable parent workout identity. With effective
   inventory present, `prior_payload` must also hash to the predecessor
   inventory digest. Update regressions independently tamper the prior
   filename, parent, and content digest; all fail before apply.
5. **Six-field legacy parity — closed.** Workout normalization retains all six
   historical request facts: `external_id`, `title`, `date`, `duration`,
   `sportType`, and `segments`. Title/date/duration are exact shared facts.
   External-marker, sport/workout-type, and segments/TP-native-structure
   conversions have exact named dispositions with both legacy and D0 evidence
   retained. The comparator works field-by-field, has a closed disposition
   whitelist, and raises on any unclassified D0-only, legacy-only, kind,
   normalized-field-inventory, or shared-field delta. Independent tampering of
   every historical workout field either fails comparison or produces the
   exact tested conversion disposition; none remains silently equal.

### R3 reviewer-probe replay

The R3 transcript was replayed against the final implementation:

```text
fueling_undeclared_top_level: REJECTED
fueling_cli_sensitive_phase_label_leaked: False
written_singleton_null_snapshot: REJECTED
attachment_update_prior_payload_tamper: REJECTED
external_id tamper_still_parity= False disposition= legacy_external_id_to_d0_logical_remote_marker
sportType tamper_still_parity= False disposition= legacy_sport_type_to_d0_tp_workout_type
segments tamper_still_parity= False disposition= legacy_segments_to_d0_tp_native_structure
```

Created-entitlement/null-snapshot and all six individual workout fields are
also pinned as direct unit regressions.

### R3 verification evidence

- R3/R2 registry, apply-contract, adapter, and external-catalog boundary:
  **56 passed, 1 skipped**. The skip is the sandbox-forbidden loopback
  transport; the same field-complete socket-free comparator passed.
- Phase 1/2 sealing, authenticated review, and download-token invariants:
  **66 passed**.
- Complete sandbox suite: **2,485 passed, 87 skipped, 21 warnings, 0 failed**.
- Opt-in production order acceptance: **36 passed, 4 skipped, 4 failed**. The
  four failures are unchanged mandatory-PDF presence/structure assertions for
  Gravel Full Gym and Masters in this no-PDF-engine sandbox; an isolated
  pre-fix `f41d1dc` archive produced the identical result.
- Current and isolated pre-fix acceptance builds each contain exactly **253
  ZWOs**: 89 Gravel, 77 Masters, 41 Road Fondo, and 46 Road Climb. Their sorted
  per-file SHA-256 manifests have an empty `diff -u`; both complete manifests
  hash to `79452230ea1cdf33fcc684e971816bc1805e84eefbbdbc7e3579bb5d49c3985e`.
- `python3 -m compileall -q athletes/scripts delivery tools webhook`,
  `git diff --check`, and the reviewer transcript replay passed. No live TP,
  browser, worker, Stripe, email, or external-network action was attempted.

## Remaining human gates

- Run the socket suite outside the sandbox, including the existing fake TP
  server parity test.
- Complete the already-pending Phase 2 live human approval gate separately.
- Do not treat Phase 3 as live TP evidence. HR/LTHR/HRmax/RPE acceptance,
  marker round-trip, identity binding, reconciliation, apply, readback,
  rollback, worker authorization/quiescence, and canary health remain the
  explicit Phase 4/5 gates. The transitional driver remains hard-disabled.

## R4 adversarial-review disposition (2026-08-09)

The single blocker in `PHASE3_IMPLEMENTATION_CODEX_R4.md` is closed at the
offline Phase 3 contract boundary. Null-snapshot positional inventory now
walks the complete durable predecessor chain instead of trusting only
`last_op_id`. Every resolved operation must match the referenced op id,
logical id, positional kind, and inventory digest and must remain a
payload-null `keep`. Positional predecessor shapes are checked at every hop;
missing links and repeated op ids fail closed. The only accepted terminus is a
predecessor-null verified adoption keep, so a singleton update, entitlement
create, or payload-installing compensation cannot be hidden behind later
keeps.

Regression coverage now proves:

- singleton `update -> keep -> null snapshot` is rejected;
- entitlement `create -> keep -> null snapshot` is rejected;
- a three-revision adopted `keep -> keep -> keep` ancestry retains the legal
  null-snapshot path; and
- missing predecessor records and cyclic predecessor chains are rejected.

The R3 closures remain pinned in the focused file: direct singleton-write and
entitlement-create null snapshots fail, both legal adoption branches pass,
attachment current/prior identity stays bound, and all parity tamper tests
remain closed.

### R4 verification evidence

- Focused apply-contract suite: **35 passed, 0 failed**.
- Complete sandbox suite: **2,490 passed, 87 skipped, 21 warnings, 0 failed**.
- `python3 -m compileall -q athletes/scripts delivery tools webhook` and
  `git diff --check` passed.
- The golden ZWO manifest is unchanged. This repair changes only contract
  validation, its regressions, and these notes; no workout generator, ZWO,
  fixture, or golden file changed. The established sorted **253-ZWO** manifest
  remains byte-identical with SHA-256
  `79452230ea1cdf33fcc684e971816bc1805e84eefbbdbc7e3579bb5d49c3985e`.
- No live TrainingPeaks, browser, worker, Stripe, email, network, or push action
  was attempted.

## R5 adversarial-review disposition (2026-08-09)

The sole blocker in `PHASE3_IMPLEMENTATION_CODEX_R5.md` is closed at the
offline Phase 3 predecessor-reader boundary. An operation lookup no longer
returns a free-standing mapping. It returns immutable canonical bytes for the
containing contract together with that contract's trusted canonical SHA-256
and model seal. Every predecessor hop verifies the digest and seal, validates
the complete containing contract with the generated D0 schema, selects exactly
one operation by the lookup key, and verifies the canonical
`{logical_id}@r{generation_revision}` identity. The containing order and
athlete identities must match the current contract, and revisions must descend
strictly at every hop without exceeding the current contract revision.

The walk remains iterative. The legal 5,000-link adopted keep regression
completes without recursion, and revision gaps remain legal when every
predecessor is strictly older than its child. The R4 legal three-revision chain,
missing-link/cycle failures, authentic write/create ancestry failures, and
ordinary provenance-field rejection coverage remain green.

Direct R5 regressions now reject all six previously accepted forgeries:

- `middle_link_coordinated_forged_op_id` fails the containing-contract digest
  binding;
- `schema_invalid_keep_labeled_compensation_middle_link` fails the generated
  exact D0 operation branch;
- `non_monotonic_revision_chain_r5_to_r2` and
  `future_predecessor_r99_for_current_r3` fail strict revision descent; and
- `coordinated_noncanonical_op_id_hiding_real_create` and
  `future_revision_r99_hiding_real_create` can no longer hide the authentic
  entitlement create behind a manufactured adoption root.

### R5 verification evidence

- Focused apply-contract suite: **42 passed, 0 failed** (the prior 35 plus six
  forgery regressions and one 5,000-link legal-chain regression).
- Complete sandbox suite: **2,497 passed, 87 skipped, 21 warnings, 0 failed**.
- `python3 -m compileall -q athletes/scripts delivery tools webhook` and
  `git diff --check` passed.
- The state manifest and golden ZWOs are unchanged. This repair changes only
  the offline contract reader/validator, its regressions, and these notes; the
  established sorted **253-ZWO** manifest remains byte-identical with SHA-256
  `79452230ea1cdf33fcc684e971816bc1805e84eefbbdbc7e3579bb5d49c3985e`.
- No live TrainingPeaks, browser, worker, Stripe, email, network, or push action
  was attempted.
