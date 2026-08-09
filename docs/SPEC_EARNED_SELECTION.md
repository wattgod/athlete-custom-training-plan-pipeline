# SPEC: Earned Selection — workout quality and selection as verified claims

Status: DRAFT r1 — awaiting adversarial review
Author: assistant, from Matti's direction ("bake in workout quality, selection,
etc. — using our repos, knowledge base, previous work we think is world class")
Depends on: docs/SPEC_TRUSTWORTHY_FULFILMENT.md (converged R9; Phases 1–3
implemented on build/trustworthy-phase3)

---

## 0. Purpose and relationship to the fulfilment spec

SPEC_TRUSTWORTHY_FULFILMENT made *delivery* trustworthy: blocked means blocked,
approval binds to sealed content, the canonical model describes what athletes
actually ride, and nothing ships without passing through the gate and the coach
review surface.

This spec makes the *training content itself* earn the same trust. Today,
"workout quality" in the pipeline means: the workout's name came from a
constrained pool, the week passed structural rules (R01–R20 subset), and the
plan's zone mix roughly matches the methodology. Nothing verifies that a
workout named "VO2max 40/20" actually delivers a VO2max dose, that an
archetype's Level 5 is actually harder than its Level 4, or that a recovery
ride cannot quietly drain a rider's anaerobic reserves. The interval content of
~100 Nate archetypes (~600 archetype×level entries in
`athletes/scripts/new_archetypes.py` and its imported modules) is effectively
unaudited.

The business already built the machinery to close this gap — in other repos:

| Asset | Where it lives today | What it gives us |
|---|---|---|
| Physiological dose scorer (TSS, kJ, Skiba W′bal nadir, T@VO2max proxy) computed from the same segments a workout renders | `gravel-god-training-plans/engine/physiology.py` (port of this repo's `experimental-workout-library/progression_engine.py`) | Per-workout "does the dose match the name" math |
| Library gate logic with calibrated pass bands (T@VO2max 8–14 min for VO2-main-set work; W′bal nadir 0–6 kJ for W′-drain work; monotonic dose across L1→L6) | `experimental-workout-library/score_library.py` + `_ENRICHMENT_SCORECARD.md` (this repo, currently untracked) | Library-level certification harness |
| The selection rubric: 25 compliance rules (14 CRITICAL), scorer reference, and the block-builder skill (the "how Matti builds a block" algorithm) | `gravel-god-training-engine/docs/block-builder-compliance-rules.md`, `docs/block-builder-scorer-reference.py`, `docs/block-builder-skill.md` | The normative definition of a well-built week/block |
| Plan-quality doctrine (determinism, calendar as truth, explainability) | `endurelabs/docs/PLAN-GENERATOR-WHITEPAPER.md` | Principles the checks must respect |

This spec brings that machinery INTO the pipeline as enforced gates, wired to
the fulfilment architecture that Phases 1–3 built. It does not invent new
training science; it enforces the training science the business already wrote
down and calibrated.

### Naming

"Earned selection": a workout appears in a released plan only if (a) its
content is certified to deliver what its name claims, and (b) its placement in
this athlete's week survives the full selection rubric. Both are verified
claims, not conventions.

---

## 1. Definitions

- **Segment dose**: TSS, kJ, and duration computed from a workout's typed
  segments (the Phase 3 canonical model's segment vocabulary: warmup, cooldown,
  steady, intervals, free_ride, ramp), using the same fourth-power conventions
  the preview's canonical accounting uses.
- **W′bal nadir**: minimum of the Skiba differential W′ balance over the
  workout's power trace, seeded from a reference W′ (20 kJ) and CP ≈ FTP/0.96.
  Near-zero positive nadir = the last rep is the limiter (well-designed);
  negative = over-cooked; large positive (for W′-drain work) = doesn't deliver.
- **T@VO2max proxy**: accumulated seconds at ≥106% FTP. A proxy that
  over-counts short reps — usable to compare designs and to band-check
  VO2-main-set workouts, not as physiological truth. Any athlete-facing use of
  this number MUST carry its proxy basis (Phase 3 derived-value registry
  rules apply).
- **Purpose contract**: the machine-readable claim a workout makes by its
  archetype/system tag (e.g. `vo2max`, `threshold`, `anaerobic`, `endurance`,
  `recovery`, `openers`), against which its measured dose is checked.
- **Certification manifest**: a versioned artifact listing every
  archetype×level entry with its measured dose metrics and PASS/FAIL verdict
  against its purpose contract's gate.
- **Selection rubric**: rules R01–R25 from the block-builder reference, with
  the CRITICAL/WARNING severities as written there.

---

## 2. Invariants

These hold for every released plan once this spec's final phase lands. As in
the fulfilment spec, "released" means content sealed and offered for approval
on the review surface; nothing reaches an athlete without them.

- **Q1 — Dose matches the name.** Every cycling workout in a released plan
  passes its purpose contract gate: VO2-main-set workouts band-check on
  T@VO2max; W′-drain workouts band-check on W′bal nadir; recovery-class
  workouts must not breach W′ at all and must stay under a recovery dose
  ceiling; endurance/steady classes must satisfy dose sanity (duration,
  IF ceiling for their zone). A workout that fails its gate is a blocker, not
  a warning.
- **Q2 — The library is certified, not trusted.** Generation may only emit
  archetype×level entries present and PASSING in the current certification
  manifest. The manifest is regenerated whenever archetype sources change, and
  its digest is part of the release seal inputs, so approval binds to the
  exact library that produced the plan.
- **Q3 — Levels progress.** Within an archetype, dose (TSS/min at minimum)
  is monotonically non-decreasing L1→L6. Certification enforces this at the
  library level; a flat or inverted progression fails the whole archetype.
- **Q4 — One methodology source of truth.** Selection, rendering, and
  validation all read methodology definitions from the config surface
  (`athletes/scripts/config/methodologies.yaml` + profile/selection YAMLs).
  The legacy hardcoded `TRAINING_METHODOLOGIES` dict in
  `nate_workout_generator.py` and the legacy target IDs in
  `validate_workout_distribution.py` are removed or reduced to thin,
  config-derived views. No two sources may disagree.
- **Q5 — The full selection rubric runs.** All 25 rules run on every plan.
  CRITICAL failures are blockers (waivable only per the fulfilment spec's
  waiver rules, and each waiver names the rule and the coach's reason).
  WARNING failures surface on the review surface as findings the coach
  sees before approving.
- **Q6 — Quality findings ride the existing rails.** Every check in this spec
  reports through the fulfilment state machine's blocker/finding mechanism and
  the Phase 2 review surface. No new delivery path, no side channel, no
  quality report that an approval can skip past.
- **Q7 — Truthfulness holds (Phase 3 inheritance).** For HR/RPE-prescribed or
  null-FTP athletes: no fabricated watts, ever. Power-based gates (W′bal,
  T@VO2max) run only on power-prescribed content; non-power content is gated
  on duration/RPE-zone dose sanity per the canonical model. Every derived
  quality metric is registered in the derived-value registry with source,
  basis, and sensitivity.

---

## 3. Workstreams

### W1 — Physiology scorer in the pipeline (per-workout quality gate)

Port the scorer into this repo as a first-class module (working name
`athletes/scripts/workout_physiology.py`), sourced from:

- `gravel-god-training-plans/engine/physiology.py` (the polished port), and
- this repo's `experimental-workout-library/progression_engine.py` (the
  original; cites Buchheit & Laursen, Skiba, Coggan).

Requirements:

1. **Input is the canonical model, not re-parsed XML.** Phase 3 made typed
   segments the source of truth (`plan_ir.py`, `canonical_training_model.py`).
   The scorer consumes those segments. A thin ZWO adapter may exist for
   library certification (W2) where canonical segments don't exist yet, but
   for athlete plans the scored segments MUST be the sealed canonical ones —
   otherwise the score describes something other than what was approved.
2. **Purpose contracts.** Each archetype carries (or is assigned in a mapping
   table checked into config) a purpose class: `vo2max`, `wprime_drain`,
   `threshold`, `endurance`, `recovery`, `openers`, `race_sim`, `mixed`.
   Gate bands per class start from the calibrated values in
   `experimental-workout-library/score_library.py` (T@VO2max 8–14 min;
   W′bal nadir 0–6 kJ) and live in config, not code.
3. **Blocker codes.** New codes in the fulfilment taxonomy:
   - `WORKOUT_DOSE_MISMATCH` — measured dose fails the purpose gate.
   - `WORKOUT_OVERCOOKED` — W′bal nadir below the floor for its class
     (including any negative nadir on recovery/endurance-class work).
   - `LIBRARY_UNCERTIFIED` — plan references an archetype×level not passing
     in the certification manifest (see W2).
   All are coach-waivable per rule; waivers name the workout and metric.
4. **Reference-athlete scoring.** Dose math is %-FTP-based and mostly
   FTP-independent; W′bal uses reference constants (FTP 250 W, W′ 20 kJ,
   Skiba tau fit). Gates therefore certify the DESIGN, not the individual.
   Where the athlete's own FTP and (if ever available) W′ are known, the
   per-athlete trace MAY be computed additionally and surfaced as review
   findings — but per-athlete values never silently replace the design gate,
   and estimated inputs follow Phase 3 basis rules.

### W2 — Library certification

Extend `experimental-workout-library/score_library.py` from an ad-hoc audit
into the certification source:

1. Promote the scorecard runner into the tracked tree (working name
   `athletes/scripts/certify_workout_library.py`) and run it over ALL
   archetype sources the generator can emit (`new_archetypes.py` plus
   imported modules — the ~600 archetype×level entries), not only the
   experimental library.
2. Output a versioned certification manifest
   (`athletes/config/workout_certification.json`): per entry — id, level,
   purpose class, dose metrics, verdict, and the digest of the archetype
   source files it was computed from.
3. Wire generation: `nate_workout_generator` / `workout_mapper` refuse to
   emit an entry absent from or failing in the manifest (subject to the W5
   rollout mode). The manifest digest joins the release seal inputs so a
   stale manifest cannot certify a new library.
4. Initial certification WILL find failures (that is the point). Disposition
   protocol: each failing archetype×level is either (a) fixed (interval
   structure corrected, with the fix reviewed like any generator change),
   (b) re-classed (its purpose contract was wrong — e.g. mis-tagged as
   vo2max), or (c) retired (removed from selectable pools). Dispositions are
   recorded in the manifest history; no entry may be waived at the library
   level.

### W3 — Complete the selection rubric

The pipeline's `block_compliance.py` implements R01–R06, R08, R11, R14, R19,
R20 (with R08/R11 partially delegated). The reference defines R01–R25 with 14
CRITICALs. Close the gap:

1. Implement the missing rules — R07, R09, R10, R12, R13, R15–R18, R21–R25 —
   with the reference severities, using
   `gravel-god-training-engine/docs/block-builder-compliance-rules.md` and
   `docs/block-builder-scorer-reference.py` as the normative source. Where a
   rule references TP-library specifics that don't map to this pipeline
   (e.g. R21 "exists in TP library" becomes "exists in the certified
   library" = Q2), the mapping is documented per-rule in the implementation
   notes.
2. CRITICAL failures → blockers; WARNING failures → review-surface findings
   (Q5). The existing `GG_STRICT_COMPLIANCE` escape hatch is removed in the
   final phase: strictness is the only mode; softness is expressed through
   waivers, which are visible and attributable, not through env vars.
3. Rules run on the post-overlay plan — the same content that gets sealed.
   The known gap where compliance runs pre-overlay (documented in
   `docs/MONIKA_RENK_PIPELINE_FINDINGS.md` and the fulfilment spec) is closed
   as part of this workstream; running the rubric on content that later
   mutates would recreate exactly the seal-vs-reality split that Phase 1
   eliminated.

### W4 — One methodology source of truth

1. `nate_workout_generator.TRAINING_METHODOLOGIES` (14 legacy systems) stops
   being an authority: render-time behavior it still drives (via
   `METHODOLOGY_MAP`) is re-derived from the 4-method config or explicitly
   frozen as named render styles with a documented mapping from config
   methodologies. Dead entries are deleted.
2. `validate_workout_distribution.METHODOLOGY_TARGETS` legacy IDs are removed;
   targets come from `methodologies.yaml` `intensity_distribution` only.
3. `select_methodology.py`'s docstring/scoring is reconciled to the 4-method
   catalog (it still narrates 13).
4. A consistency test asserts that every methodology id referenced anywhere
   (selector, profiles, render map, distribution validator, guide copy)
   exists in `methodologies.yaml`, and that intensity-distribution numbers
   used by any check equal the config values.

### W5 — Rollout modes (mirrors the fulfilment rollout discipline)

- **Mode A (report-only):** scorer + certification + full rubric run on every
  order; results attach to the review surface as findings; nothing new
  blocks. Golden orders and the athlete-m replay establish the baseline
  ("how bad is the current library?") without destabilizing fulfilment.
- **Mode B (enforce):** Q1/Q2/Q3 gates become blockers; `GG_STRICT_COMPLIANCE`
  removed; manifest digest joins the seal.
- Mode transitions are explicit commits, not env toggles, and Mode B entry
  requires: zero unexplained golden-order regressions in Mode A, and the
  library disposition backlog (W2.4) at zero CRITICAL-class failures.

---

## 4. HR/RPE and null-FTP athletes (Q7 detail)

Phase 3 made HR/RPE prescriptions first-class and banned fabricated watts.
This spec must not regress that:

- Power-trace gates (W′bal, T@VO2max) run ONLY on segments whose canonical
  target type is power. For HR/RPE-target segments, the design gate is the
  purpose-class dose-sanity check on duration × canonical effort scale
  (RPE/10, HR ratio), consistent with the canonical intensity accounting the
  Phase 3 preview uses.
- Library certification (W2) runs on the power-rendered form of each
  archetype (archetypes are authored in %FTP), so the library gate is
  well-defined even though individual athletes may receive HR/RPE
  projections of the same structure. The certification claim is about the
  DESIGN; the athlete-facing projection remains governed by Phase 3's
  projection-equality validators.
- No quality metric derived for an HR/RPE athlete may mention watts, %FTP, or
  power-derived values in athlete-facing artifacts (guide, preview, review
  surface athlete panes). Coach-facing panes may show design-gate results
  labeled as reference-athlete design metrics.

---

## 5. Fixtures and acceptance

1. **Scorer goldens.** Unit fixtures with hand-computed TSS/kJ/W′bal/T@VO2max
   for each segment kind and a known 40/20, 30/30, threshold, endurance, and
   recovery workout. Values cross-checked against
   `gravel-god-training-plans/engine/physiology.py` outputs for identical
   segments (the two implementations must agree within rounding, or the
   divergence is documented and justified).
2. **Certification snapshot test.** The manifest for the current library is a
   committed fixture; archetype source changes that alter any entry's metrics
   fail CI until the manifest is regenerated and the diff reviewed.
3. **Golden orders.** The existing `GG_RUN_ACCEPTANCE=1` acceptance suite
   gains: (a) every emitted workout has a certification entry and gate result;
   (b) in Mode A, findings are present on the review bundle; (c) in Mode B,
   a deliberately mis-dosed fixture workout produces `WORKOUT_DOSE_MISMATCH`
   and blocks approval without a waiver. Golden-order plan content does not
   change as a side effect of this spec (measurement and gating only) — the
   same byte-identity discipline used for the Phase 3 regressions applies.
4. **athlete-m replay.** The fixed-clock production replay runs in Mode A and
   asserts the full rubric + scorer execute and report without altering the
   sealed outputs.
5. **Methodology consistency test** (W4.4) runs in the standard unit suite.

---

## 6. Explicit non-goals

- **No replanning.** This spec measures and gates; it does not change how
  plans are structured or which workouts are selected, except where a
  certification failure removes a defective archetype from pools (W2.4c) —
  and that is a reviewed library change, not a silent runtime substitution.
- **No new training science.** Gate bands come from the already-calibrated
  scorecard; changing a band is a config change with review, not a code
  side effect.
- **No merge of the 524-workout TrainingPeaks library** into this pipeline's
  generator. That convergence (one library across custom plans and TP
  catalog plans) is real and desirable but is its own program; tracked as a
  follow-up ticket, not smuggled in here.
- **No per-athlete W′ estimation.** We do not have per-athlete W′ data and
  will not estimate it silently (Phase 3 basis rules); design gates use the
  reference athlete.
- **No LLM-judged quality in the gate path.** `judge_plan.py` (narrative
  head-coach review) remains advisory; deterministic checks only in the
  blocker path (per the plan-generator whitepaper's determinism doctrine).

---

## 7. Open questions for review

1. Should the certification manifest live in-repo (versioned artifact,
   proposed) or be generated in CI only? In-repo is proposed for seal-digest
   stability and reviewable diffs.
2. R25 ("readiness decision points present") assumes HRV/monitoring context
   the intake may not collect; proposed disposition is WARNING-only with
   text-presence semantics until intake supports it.
3. Whether Mode A findings should appear in the coach email summary or only
   on the review surface (proposed: review surface only, to keep the email's
   state-aware contract from Phase 1 untouched).
4. The exact seal-input ordering for the manifest digest (fulfilment spec
   §seal defines the current inputs; this adds one).
