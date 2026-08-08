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

## Remaining human gates

- Run the socket suite outside the sandbox, including the existing fake TP
  server parity test.
- Complete the already-pending Phase 2 live human approval gate separately.
- Do not treat Phase 3 as live TP evidence. HR/LTHR/HRmax/RPE acceptance,
  marker round-trip, identity binding, reconciliation, apply, readback,
  rollback, worker authorization/quiescence, and canary health remain the
  explicit Phase 4/5 gates. The transitional driver remains hard-disabled.
