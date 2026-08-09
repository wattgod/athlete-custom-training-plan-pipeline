# SPEC: Earned Selection — workout quality and selection as verified claims

Status: DRAFT r2 — addresses all 19 blockers from
docs/reviews/SPEC_EARNED_SELECTION_CODEX_R1.md (disposition map in Appendix 1)
plus two owner corrections (workout-estate scale; invisible rigor).
Author: assistant, from Matti's direction.
Depends on: docs/SPEC_TRUSTWORTHY_FULFILMENT.md (converged R9). Phases 1–3 are
implemented on `build/trustworthy-phase3`, NOT on main. **This spec's
implementation branches from (or after the merge of) `build/trustworthy-phase3`;
every reference to canonical model, derived-value registry, seal, or review
surface refers to that code.**

---

## 0. Purpose

SPEC_TRUSTWORTHY_FULFILMENT made *delivery* trustworthy. This spec makes the
*training content itself* earn the same trust: every workout in a released
plan is verified — internally — to deliver what its name claims, and its
placement in the athlete's week is graded against the full selection rubric
the business already wrote.

### 0.1 Invisible rigor (owner directive — binding)

All validation in this spec is **internal**. It exists so we and the reviewing
coach know the content is right. None of it is athlete-facing:

- The athlete-facing surface (workout names, descriptions, TrainingPeaks
  formatting, guides, previews shown to athletes) is **byte-unchanged** by
  this spec. Workout descriptions keep the established, documented TP format.
- No dose metrics, gate results, certification language, methodology
  footnotes, or justification copy are ever added to athlete artifacts. A
  plan that explains itself invites second-guessing; the best plans convey
  confidence in what they say and in what they don't say.
- Gate results appear only in: the certification manifest, the coach review
  surface, and internal reports.

### 0.2 The workout estate (scale, stated honestly)

The business's workout corpus spans four bodies:

| Body | Scale | Existing validation |
|---|---|---|
| This pipeline's generator space: Nate archetypes | 100 archetypes × 6 levels = 600 entries, 24 categories (`athletes/scripts/archetype_registry.py` runtime validation; module prose saying 95/570 is stale) | Partial — see §0.3 coverage matrix |
| Curated TrainingPeaks workout library | 524 ZWOs (`gravel-god-training-plans/workout-library/`) | `gravel-god-training-plans/engine/physiology.py` scoring |
| Master-plan instances (rendered from the curated library) | 14,840 ZWOs (`gravel-god-training-plans/master_plans/`) | Inherit library validation; QC specs in that repo |
| Endure Labs stock workout library | Own repo | `endurelabs/scripts/validate-stock-workouts.ts` et al. |

**Scope of this spec: the first body only** — the content this pipeline
generates for paid custom orders. Bringing the other three bodies under the
same certification regime is real, desirable, and explicitly a follow-up
program (see §8 non-goals). Instances derive from designs, so certifying
designs is the leverage point everywhere.

### 0.3 What exists today (coverage matrix — replaces r1's false "nothing verifies")

Existing protections that MUST remain as regression tests:

| Protection | Where | Coverage | Gap this spec closes |
|---|---|---|---|
| L1-vs-L6 endpoint power comparison for imported archetypes | `athletes/scripts/test_workout_generation.py:1203-1216` | Endpoints only | Adjacent-level dose monotonicity (all 5 transitions) |
| Power/volume progression for advanced archetypes | `test_workout_generation.py:2263-2347` | Advanced subset | All 100 archetypes |
| Per-design monotonic checks (BPA, Late-Race VO2max, Glycolytic Power) | `test_workout_generation.py:2855-2910` | 3 designs | All designs |
| Registry completeness (100 archetypes × 6 levels present) | `athletes/scripts/archetype_registry.py:178-209` | Presence, not dose | Dose verdicts per entry |
| Structural week rules R01–R06, R14, R19, R20 (R08/R11 registered but unconditionally passing) | `athletes/scripts/block_compliance.py` | 9 real + 2 no-op of 26 reference rules | Full rubric with parity audit (W3) |
| Zone-mix vs methodology targets (advisory ±5%, catastrophic hard-fail) | `athletes/scripts/validate_workout_distribution.py` | Filename-classified | Canonical-segment accounting; config-only targets (W4) |

What genuinely does not exist today: purpose-dose verification (does a VO2max
workout deliver a VO2max dose), library-level certification bound to the
release, and rubric coverage beyond the 9 real rules.

---

## 1. Definitions

- **Normative dose equation (single authority — resolves the r1 math
  contradiction).** For every workout, dose is computed from the canonical
  typed segments via a 1 Hz power-fraction trace:
  - Trace construction: steady → constant; warmup/cooldown/ramp → linear
    interpolation low→high; intervals → repeat × (on, off); free_ride →
    excluded from the trace (see FreeRide contract, §4.3).
  - `IF = (mean(pf⁴))^(1/4)` over the trace (fourth-power mean, matching
    Phase 3's canonical accounting in `generate_plan_preview.py`).
  - `TSS = duration_hours × IF² × 100`; `kJ = Σ pf × FTP_ref × dt / 1000`.
  - Sampling dt = 1 s; no intermediate rounding; final display rounding only.
  - **Migration statement:** the experimental scorer's per-segment
    `duration × p²` convention (`experimental-workout-library/
    progression_engine.py`, mirrored in `gravel-god-training-plans/engine/
    physiology.py`) is superseded for this pipeline. The sibling repo is out
    of scope and unchanged. Acceptance fixtures carry ONE golden answer per
    fixture computed by the normative equation; r1's "two implementations
    must agree" clause is deleted. Manifest metric churn vs the old scorecard
    is expected and is quantified in the W2 baseline report.
- **W′bal reference diagnostic** (renamed from r1's design/safety claim):
  minimum of the Skiba differential W′ balance over the trace under a fixed,
  versioned reference model: FTP_ref 250 W, CP = FTP_ref/0.96, W′ 20 kJ,
  recovery constants per Skiba (fit to a 7-subject cohort — stated basis).
  It is a deterministic property of the DESIGN under the reference model. It
  is **prohibited** to describe it as an athlete-safety fact, an actual-rider
  reserve, or "cannot drain a rider" — anywhere, including coach copy.
- **T@VO2max proxy**: trace seconds ≥ 106% FTP_ref, computed over the
  **authored main set only** (§4.2). Known to over-count short reps and
  ignore post-rep VO2 tail; usable to compare designs of the SAME rep
  geometry, never across geometries with one band.
- **Purpose contract**: the machine-readable claim an archetype makes:
  purpose class + rep-geometry subtype (e.g. `vo2max/steady`, `vo2max/30_30`,
  `vo2max/40_20`, `wprime_drain`, `threshold`, `endurance`, `recovery`,
  `openers`, `race_sim`, `assessment`, `free`, `mixed`), assigned in a
  config mapping table, with gate parameters per subtype.
- **Certification manifest**: versioned artifact listing every archetype×level
  entry with metrics, verdict, purpose contract, source digests, scorer
  version. See §5.
- **Rule registry**: the single normative selection-rubric source (§4.5).

---

## 2. Invariants

"Released" as in the fulfilment spec: sealed and offered for approval. These
hold at Mode B (§7); Mode A runs everything report-only.

- **Q0 — Invisible rigor.** §0.1 in full. Athlete-facing artifacts are
  byte-unchanged by this spec's machinery. Acceptance asserts it (§6).
- **Q1 — Dose matches the name.** Every power-prescribed workout in a
  released plan passes its purpose-contract gate, evaluated on the **final
  sealed segments** (post-scaling, post-overlay — §4.4). Gate failure is a
  **non-waivable** blocker (§4.6); remediation is fix-and-regenerate.
- **Q2 — The library is certified, not trusted.** Generation emits only
  entries passing in the manifest snapshot pinned to that generation revision
  (§5). Non-waivable.
- **Q3 — Levels progress.** Defined precisely in §4.1. Certification-level;
  no per-order waiver exists because no per-order blocker exists — failing
  archetypes are dispositioned at the library level (§5.3).
- **Q4 — One methodology source of truth.** §4.7. Config is authoritative;
  the selector's inline fallback is deleted (fail closed); legacy dicts are
  either deleted or generated from config; a consistency test enforces it.
- **Q5 — The full rubric runs.** All rules in the rule registry run on every
  plan per the execution matrix (§4.5). CRITICAL failures are blockers
  (waivable per fulfilment rules — these are structural judgments, unlike
  Q1/Q2 integrity gates); WARNING failures are quality findings (§4.8).
- **Q6 — Quality results ride defined rails.** Every output maps to an
  exactly specified review-item type (§4.8). No new delivery path.
- **Q7 — Truthfulness holds.** §4.9. No fabricated watts; power gates only on
  power-prescribed content; HR/RPE content uses Phase 3's exact piecewise
  normalization tables; per-workout metrics live in a schema-owned artifact
  with defined sensitivity (§4.10).

---

## 3. Gate authority: calibration before blocking

r1 presented the experimental scorecard's bands (T@VO2max 8–14 min, W′bal
nadir 0–6 kJ) as "already calibrated." They are not: the scorecard is an
exploratory audit of a separate 39-archetype experimental model (234 rows, 79
failing, including systematic failures of every 5x3/30-30/40-20 VO2 format —
evidence of rep-geometry sensitivity, not miscalibrated workouts).

Therefore:

1. All gate bands enter this spec as **hypotheses**, recorded in
   `athletes/config/quality_gates.yaml` with: value, unit, purpose subtype,
   evidence basis, owner (Matti), status (`hypothesis` | `calibrated`),
   version, and date.
2. A band may block (Mode B) only after a **calibration pass**: run against
   the full 600-entry production library, every failure hand-dispositioned by
   the owner (fix / re-class / retire / band-adjust), sensitivity noted for
   W′bal over a stated grid (FTP_ref ∈ {200, 250, 300}, W′ ∈ {15, 20, 25} kJ
   — a design gate must not flip verdict across the grid without the
   disposition saying so), and the accepted false-positive/negative policy
   written down. The signed disposition log is
   `athletes/config/quality_gates_dispositions.md`.
3. Changing a band thereafter is a config change with review — never a code
   side effect.

This is the honest version of "no new training science": the science exists
(Buchheit & Laursen, Skiba, Coggan; the business's own scorecard work), but
the *authority* to block paid orders is earned through the calibration pass,
not asserted.

---

## 4. Workstreams

### W1 — Physiology scorer in the pipeline

New module `athletes/scripts/workout_physiology.py` implementing §1's
normative equations. Requirements:

1. **Input is canonical segments** (`plan_ir.py` /
   `canonical_training_model.py` vocabulary). A ZWO adapter exists ONLY for
   library certification of archetype renders; athlete-plan scoring always
   consumes the sealed canonical segments.
2. Scorer version string is part of every manifest row and every stored
   result; changing the scorer invalidates the manifest (§5.2).

#### 4.1 Q3 progression semantics (exact)

Per archetype, over levels L1→L6, using unrounded normative metrics:

- `TSS(L+1) ≥ TSS(L) + 1.0` (strictly increasing with epsilon 1.0 TSS), AND
- `TSS/min(L+1) ≥ TSS/min(L) − 0.05` (intensity density may plateau but not
  materially regress; duration-led progression is legitimate).
- One failing transition fails the **archetype** (all six levels), because a
  broken ladder invalidates series progression (+1 level/week) wherever it
  starts.
- Purpose-gated archetypes (VO2, W′-drain) take BOTH their purpose gate and
  this dose-progression gate.
- Fixtures: flat pair, rounded-flat pair, mixed-direction, single-transition
  failure, duration-led progression (must pass).

#### 4.2 Main-set boundary (T@VO2max)

The canonical model gains an authored `main_set: true` marker on segments
(source: archetype structure — the interval blocks between warmup and
cooldown; explicit list per archetype in the purpose-contract mapping where
ambiguous, e.g. primers, hard starts, finishers, which are enumerated there
as in/out). T@VO2max is computed over main-set segments only. Bands are per
rep-geometry subtype (§1 purpose contract) and start as hypotheses (§3).

#### 4.3 FreeRide contract

`free`-target segments (self-paced tests, race overlays, unstructured rides —
17 entries across 3 archetypes in the current registry, plus B-race and
testing overlays) are **excluded from all power-dose gates**. Their contract
is non-power: identity (what it is), duration, intent, and truthful no-target
semantics (Phase 3 already enforces `free` only on `free_ride` kinds). Race
day and assessments are never dose-gated. Where a workout NEEDS a dose
guarantee, the fix is a real prescription, not an assumed intensity. The
legacy 55%/65% accounting assumptions remain preview-only estimates and never
feed a gate.

#### 4.4 Gating the workout that actually ships

r1's fatal gap: production selects a Nate archetype but records only the
block-builder name, then **rescales segment durations post-render** to hit
block targets (`generate_athlete_package.py`, `workout_templates.py`), so a
manifest row keyed archetype×level cannot attest the shipped workout.
Requirements:

1. **Immutable archetype IDs.** Every archetype gets a stable public
   `archetype_id` (registry becomes ID-keyed; names remain display-only).
   IDs are never reused; retired IDs get tombstones (§5.3).
2. **Provenance propagation.** The selector/renderer return and the canonical
   session record: `archetype_id`, level, category, variation, renderer
   version, source digest, and all transformation parameters applied
   (duration scaling factors, overlay injections).
3. **Two-part gate.** (a) `LIBRARY_UNCERTIFIED`: the recorded
   archetype_id×level must be PASS in the pinned manifest. (b) **Final-dose
   verdict**: the purpose gate re-runs on the final sealed segments (after
   scaling/overlays). Certification of the pristine design does NOT exempt
   the transformed instance; the sealed segments are what the athlete rides.
   Transformed variants do not get manifest identities; they get the
   independent final-dose check.

#### 4.5 W3 — the selection rubric, with one normative registry

r1 found the three block-builder sources disagree (doc: 25 rules, 13
CRITICAL; scorer reference: R01–R26 with a CRITICAL R26, R18/R22
NOT_IMPLEMENTED; skill: a different 14-item list; R03's reference band has an
undefined 40–49% zone). Therefore:

1. **Rule registry**: `athletes/config/rule_registry.yaml` — the single
   normative source. For every rule: ID, severity, applicability conditions,
   exact inputs, algorithm reference, owner, and disposition of the known
   discrepancies (R26 adopted or rejected; R18/R22 implemented or explicitly
   deferred with status; R03's 40–49% boundary closed; skill-list severities
   reconciled). The block-builder docs become descriptive projections; a
   consistency test fails if they and the registry disagree on ID/severity.
2. **Parity audit, not missing-ID patch.** Every currently "implemented" rule
   is audited against the registry semantics: R08/R11's unconditional passes
   are replaced with real checks or explicit delegation that merges the
   delegate's result into the rubric output; R03's dynamic range is
   reconciled to the registry's band. Per-rule current-vs-target semantics go
   in the implementation notes.
3. **Execution matrix.** Per rule: exact sealed input artifact (canonical
   sessions / strength artifacts / fueling artifacts / guide text /
   historical block state), execution stage (post-overlay, pre-seal — the
   rubric runs after ALL content mutations, immediately before canonical
   model finalization, closing the pre-overlay gap documented in
   `docs/MONIKA_RENK_PIPELINE_FINDINGS.md`), NOT_APPLICABLE vs UNAVAILABLE
   semantics (first order ⇒ R22 NOT_APPLICABLE, never a fabricated pass;
   missing monitoring ⇒ R25 NOT_APPLICABLE), crash behavior (rubric crash =
   `STATE_UNAVAILABLE`-class blocker, fail closed), and output code.
4. CRITICAL → blocker (waivable, per §2 Q5); WARNING → quality finding
   (§4.8). `GG_STRICT_COMPLIANCE` is removed in Mode B — not because
   "strictness is the only mode" but because hard-fail-at-generation is
   replaced by fulfilment blockers; tests inject blocker fixtures directly.

#### 4.6 Waiver policy (resolves r1's contradiction)

Two classes, following the fulfilment spec's closed non-waivable set:

- **Integrity gates — non-waivable** (join `SEAL_MISMATCH` in the closed
  set): `LIBRARY_UNCERTIFIED`, `WORKOUT_DOSE_MISMATCH`, `WORKOUT_ORIGIN_
  UNKNOWN` (§4.5a below), plus manifest-pin failures (§5.2). Remediation is
  always fix-and-regenerate. Negative approval tests for each: approval with
  the blocker present must be refused even with a waiver document covering it.
- **Structural judgments — waivable**: rubric CRITICALs (R-rules), where a
  coach can legitimately decide the rule doesn't fit this athlete. Waivers
  name the rule ID, the workout(s), and the reason, per fulfilment waiver
  rules.

`WORKOUT_OVERCOOKED` is not a separate code (folded into
`WORKOUT_DOSE_MISMATCH` with the metric in the payload).

#### 4.5a Workout-origin union (closes the Q1/W2 coverage gap)

Every cycling workout in a plan is classified into exactly one origin:

| Origin | Gate contract |
|---|---|
| Nate archetype render | §4.4 two-part gate |
| Handcrafted endurance renderer (`workout_mapper.py` bypass) | Registered as pseudo-archetypes with IDs in the manifest; same two-part gate |
| Bespoke B-race / travel-day ZWOs (`generate_athlete_package.py`) | FreeRide/`free` contract (§4.3) or, if power-prescribed, final-dose gate with purpose class from the overlay type |
| Assessments / field tests | `assessment` class: duration + structure sanity only, never dose-gated |
| Legacy overlay path | Removed or classified into the above before Mode B; until then its outputs carry origin labels |
| Anything else | `WORKOUT_ORIGIN_UNKNOWN` — non-waivable blocker |

Coverage fixtures exist per branch.

#### 4.7 W4 — one methodology source of truth

1. `select_methodology.py`'s inline four-method fallback is **deleted**; the
   selector fails closed on unavailable/invalid config.
2. Nate's `TRAINING_METHODOLOGIES` dict: the four render styles actually
   reachable via the package's 4-ID→render map are frozen as named render
   styles with the mapping (`time_crunched→POLARIZED`, `g_spot→G_SPOT`,
   `polarized_80_20→POLARIZED`, `traditional_pyramidal→PYRAMIDAL`) checked
   into config; unreachable entries are deleted. **Avoid-lists and variation
   offsets keyed by render style are selection-affecting: they are preserved
   exactly**, protected by selection goldens (same profile ⇒ same selected
   archetype IDs before/after W4), so W4 is behavior-preserving. Any
   intentional selection change is out of scope for W4 and must arrive as
   its own reviewed change.
3. `validate_workout_distribution.METHODOLOGY_TARGETS` legacy IDs deleted;
   targets come from `methodologies.yaml` only; classification moves from
   filenames to canonical segments (consistent with Phase 3 accounting).
4. Consistency test: every methodology ID referenced anywhere resolves to
   `methodologies.yaml`; every distribution number used by any check equals
   the config value; the selector docstring's 13-method narration is fixed.

#### 4.8 W-review — quality findings as a defined review type

New versioned review-item type `quality_finding/v1`, specified end-to-end:

- **State schema**: id, rule/gate code, severity (`warning`), subject
  (workout id(s) / week / plan), metric payload, scorer or registry version.
- **Catalog construction**: appended to the review catalog after blockers and
  confirmations; included in the catalog digest (so approval binds to the
  findings the coach saw).
- **Review page**: rendered in its own section, coach-facing only; requires
  no acknowledgment; approval semantics unchanged by findings.
- **Approval snapshot**: findings present at approval are archived in the
  snapshot.
- **Redaction**: subject to the same sensitivity rules as verified facts;
  design-power metrics for null-FTP athletes are coach-only (§4.10).
- **Email projection: none.** The Phase 1 state-aware email contract is
  untouched (resolves r1 open question 3).
- Mode A results (including gate results while bands are hypotheses) surface
  as quality findings.

#### 4.9 HR/RPE and null-FTP (exact)

- The neutral intensity axis for non-power content is **Phase 3's piecewise
  normalization tables in `canonical_training_model.py`** (RPE→intensity and
  %LTHR/%HRmax→intensity mappings) — referenced as the single normalization
  authority, not re-derived. r1's "RPE/10" description was wrong and is
  withdrawn.
- Aggregation for non-power dose sanity: same trace construction as §1 with
  normalized intensity in place of power fraction; TSS-equivalent =
  duration_hours × IF² × 100 on that trace. Gates for non-power content are
  duration + TSS-equivalent sanity per purpose class only — **no W′bal, no
  T@VO2max** (both are power-trace constructs; HR kinetics make short-rep HR
  prescriptions non-tracelike, so interval-geometry gates are power-only by
  construction).
- Missing anchors (no LTHR/HRmax where required): already a Phase 3 gate
  concern; this spec adds no new inference — the workout is not dose-gated
  and the absence is already visible on the review surface.
- Library certification runs on the power-rendered archetype form (archetypes
  are authored in %FTP): the certification claim is about the design.
  Athlete-facing projections remain governed by Phase 3's projection-equality
  validators.
- Fixtures: HR-LTHR, HRmax-only, RPE-only, interval, ramp, mixed/free — each
  asserting zero power assertions in any athlete-visible output.

#### 4.10 Metric ownership and the derived-value registry

Per-workout metrics do NOT become individual derived-value entries (that
would flood the coach catalog — every entry projects as a verified fact).
Instead:

- New schema-owned artifact `workout_quality_report.json` (registered in the
  derived-registry artifact-schema coverage like Phase 3's other artifacts):
  per-session rows keyed by canonical session id — origin, archetype_id,
  level, transformation parameters, metrics, gate verdicts, scorer version.
  Sensitivity: coach/internal. Never copied into athlete artifacts (Q0).
- Exactly two plan-level derived entries: `QUALITY_GATE_SUMMARY` (counts by
  verdict, manifest version, rubric version; class `computed`) and
  `QUALITY_MANIFEST_PIN` (manifest digest + snapshot reference; class
  `verified`). These are what project to the review surface as facts.
- Redaction fixtures prove design-power values never appear in athlete-pane
  renders for null-FTP athletes.

---

## 5. Certification manifest and the seal

### 5.1 Contents and generation

`athletes/config/workout_certification.json` (in-repo, versioned): per entry —
`archetype_id`, level, purpose contract, normative metrics, verdict, source
file digests, scorer version, gates version, generated-at. Regenerated by
`athletes/scripts/certify_workout_library.py` (promoted from the untracked
`experimental-workout-library/score_library.py`, rewritten to §1 normative
equations and run over the production registry, not the experimental model).
**Owner/regeneration contract:** any commit changing archetype sources,
scorer, or gate config MUST regenerate the manifest in the same commit; CI
recomputes and fails on mismatch (atomicity — a stale manifest cannot exist
on a green build).

### 5.2 Seal integration (resolves r1 open questions 1 and 4)

- At generation, the pipeline **snapshots the full manifest payload into the
  generation revision** (per-revision pinning) and records its digest.
- The model seal gains the manifest digest as a new input: this is a **seal
  schema version bump**, applied identically to both independent seal
  constructors (`apply_contract.py` and `webhook/fulfillment_state.py`
  release finalization) and to every verifier. Older seal versions verify
  under their own schema (backward verification test); new approvals require
  the new version.
- The snapshot joins the release artifact inventory, so approval binds to the
  exact certification evidence — no read of mutable repo-global state during
  later verification. Stale-manifest test: mutate the in-repo manifest after
  sealing; verification of the sealed order must be unaffected; regeneration
  must pick up the new manifest.

### 5.3 Disposition, retirement, and in-flight orders

- Initial certification failures are dispositioned per §3 by the owner:
  **fix** (changes workout bytes — a reviewed content change with golden
  rebaselines, Phase E2 only), **re-class** (purpose contract was wrong),
  **retire** (tombstoned).
- **Tombstones, not reindexing:** retirement marks the ID retired in the
  registry with an optional explicit `replacement_id`. Because r1 showed
  variation selection uses list-order modulo indexing, W1 includes migrating
  variation selection to stable ID-keyed ordering **with selection goldens
  proving byte identity for existing profiles before any retirement occurs**.
  Series coherence (R14) fixtures prove a retirement mid-catalog cannot
  reshuffle other athletes' series.
- **In-flight policy:** an order keeps the manifest snapshot sealed at its
  generation revision. Later retirements do not invalidate a sealed approval
  (grandfathered). Any regeneration (which always re-seals, per fulfilment
  rules) uses the current manifest. A blocked-not-yet-approved order whose
  content references a since-retired entry simply fails `LIBRARY_UNCERTIFIED`
  on regeneration and is fixed by regeneration itself.

---

## 6. Fixtures and acceptance

1. **Scorer goldens**: hand-computed normative TSS/kJ/W′bal/T@VO2max for each
   segment kind and known 40/20, 30/30, 5×3, threshold, endurance, recovery
   designs — one golden answer each (no cross-implementation agreement
   clause).
2. **Certification snapshot test**: manifest committed; CI recomputes (§5.1).
3. **Progression fixtures**: §4.1's list.
4. **Origin coverage**: one fixture per §4.5a branch, including the
   `WORKOUT_ORIGIN_UNKNOWN` negative test.
5. **Golden orders** (`GG_RUN_ACCEPTANCE=1`): (a) every emitted workout has
   an origin classification and, where applicable, a manifest entry + final-
   dose verdict; (b) Mode A: quality findings present in the review bundle
   and approval snapshot; (c) Mode B: a deliberately mis-dosed fixture
   workout produces `WORKOUT_DOSE_MISMATCH` and approval is refused even with
   a covering waiver (non-waivable negative test); (d) **Q0 byte-identity:
   athlete-facing artifacts (ZWOs, guide, athlete-visible preview payloads)
   are byte-identical before/after Phase E1** (audit-only plumbing changes
   nothing an athlete sees). Phase E2 content fixes are the ONLY permitted
   byte changes, each enumerated and rebaselined.
6. **athlete-m replay**: Mode A run asserts rubric + scorer execute, findings
   report, sealed outputs unchanged.
7. **Methodology consistency + selection goldens** (§4.7) in the unit suite.
8. **Seal tests**: version-bump dual-constructor equality, backward
   verification, stale-manifest (§5.2).
9. **Redaction fixtures** (§4.10).

---

## 7. Rollout (resolves r1's phase contradictions)

- **Phase E1 — audit-only plumbing.** Archetype IDs, provenance propagation,
  ID-keyed variation selection (byte-identity goldens), scorer, manifest
  generation, rule registry + parity audit, quality findings on the review
  surface, origin classification. **No content changes; Q0 byte-identity
  holds throughout.** Baseline report quantifies: manifest verdicts across
  all 600 entries, metric churn vs the old scorecard, rubric findings across
  golden orders.
- **Phase E2 — content dispositions.** Owner works the failure backlog per
  §3/§5.3. Every fix is a reviewed change with enumerated golden rebaselines.
  Byte identity explicitly does NOT hold here — that is the point — and each
  change is attributable.
- **Phase E3 — enforce (Mode B).** Entry criteria: **all selectable manifest
  rows PASS** (not a "critical subset"), gate bands promoted to `calibrated`
  per §3, zero unexplained golden-order regressions in E1/E2, seal version
  bump landed, `GG_STRICT_COMPLIANCE` removed. Non-waivable gates active.
- Mode transitions are explicit commits.

---

## 8. Explicit non-goals

- **No replanning.** E1 is provably behavior-preserving (goldens). E2 changes
  workout content only through owner-reviewed dispositions. No runtime
  substitution, ever.
- **No athlete-facing changes** (Q0). No justification copy, no metric
  surfacing, no description-format changes.
- **No estate-wide convergence** (TP curated library, master plans, Endure
  stock library) — follow-up program; this spec certifies the pipeline
  generator space.
- **No per-athlete W′ estimation**; the W′bal diagnostic is a reference-model
  design property only.
- **No LLM judgment in the gate path**; `judge_plan.py` stays advisory.
- **No new training-science authority without calibration** (§3).

---

## 9. Open questions for review

1. §4.1's epsilon values (1.0 TSS, 0.05 TSS/min) are proposed, not sacred —
   reviewer should attack whether they encode the right progression
   philosophy.
2. Whether the handcrafted endurance renderer should be migrated into Nate
   archetypes instead of pseudo-registered (§4.5a) — proposed: pseudo-register
   now, migrate later.
3. Whether rubric CRITICALs should become non-waivable at some post-E3 point
   once waiver telemetry exists.

---

## Appendix 1 — R1 blocker disposition map

| R1 blocker | Disposition in r2 |
|---|---|
| 1 false "nothing verifies" | §0.3 coverage matrix; existing tests retained as regressions |
| 2 bands not calibrated | §3 hypothesis→calibrated protocol, owner, dispositions, sensitivity |
| 3 dose-equation contradiction | §1 single normative equation; migration statement; golden answers |
| 4 T@VO2max main-set/geometry | §4.2 authored main-set boundary; per-geometry subtype bands; §3 gating |
| 5 W′bal safety overclaim | §1 renamed reference diagnostic; prohibited wording; sensitivity grid |
| 6 FreeRide non-evidentiary | §4.3 `free` contract; excluded from power gates; enumerated treatments |
| 7 manifest can't attest shipped workout | §4.4 immutable IDs, provenance, two-part gate incl. final-dose on sealed segments |
| 8 Q1/W2 coverage gap | §4.5a origin union; `WORKOUT_ORIGIN_UNKNOWN` non-waivable |
| 9 Q3 underspecified | §4.1 exact semantics + fixtures |
| 10 waiver contradiction | §4.6 integrity gates non-waivable; structural rules waivable; negative tests |
| 11 seal/manifest unresolved | §5.2 per-revision snapshot, seal version bump, dual constructors, stale test |
| 12 "findings" undefined | §4.8 `quality_finding/v1` end-to-end |
| 13 registry cardinality | §4.10 schema-owned artifact + two plan-level entries |
| 14 rule sources disagree | §4.5(1) rule registry as single source; discrepancies dispositioned |
| 15 existing rules no-ops | §4.5(2) parity audit |
| 16 post-overlay contract | §4.5(3) execution matrix, stage, N/A semantics, fail-closed |
| 17 selector fallback / Nate authority | §4.7 fallback deleted, render styles frozen, selection goldens |
| 18 HR/RPE wrong+vague | §4.9 Phase 3 tables as authority; exact aggregation; power-only geometry gates |
| 19 rollout contradictions | §7 E1/E2/E3 split; §5.3 tombstones, in-flight policy, all-rows Mode B entry |

Owner corrections folded in: §0.1 invisible rigor (Q0), §0.2 workout estate.
