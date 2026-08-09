# SPEC: Earned Selection — workout quality and selection as verified claims

Status: DRAFT r3 — resolves R1 blockers 1–19 and R2 blockers R2-01–R2-14.
The combined disposition map is Appendix 1. All schemas, registries, algorithms,
and migration data required by this revision are normative content in this file;
implementation MUST NOT invent or defer a policy choice named here.

Depends on: `docs/SPEC_TRUSTWORTHY_FULFILMENT.md` (converged R9). Phases 1–3
exist on `build/trustworthy-phase3` at `d291eb496a77ad52c2a55b390b6917f41a4eb88a`.
Implementation of this spec MUST branch from that commit or its merged successor.

Normative terms **MUST**, **MUST NOT**, **SHOULD**, and **MAY** have their RFC
2119 meanings. “Released” means sealed and offered for approval under the
fulfilment spec.

---

## 0. Purpose and estate

SPEC_TRUSTWORTHY_FULFILMENT made delivery trustworthy. This specification makes
the training content earn the same trust: internally, every selected native
design is certified, every final prescribed workout is scored after mutation,
and every final plan is evaluated against one closed selection rubric.

### 0.1 Invisible rigor (owner directive — binding)

All validation in this specification is internal. It exists for the system and
reviewing coach, never as athlete-facing justification.

- Phase E1 MUST leave every athlete surface in the closed inventory in §6
  byte-identical. No dose metric, gate result, certification language,
  methodology footnote, or justification copy may enter an athlete surface.
- Workout names, descriptions, TrainingPeaks formatting, calendar notes,
  guides, previews, email copy, and delivery bundles retain their established
  content and shape.
- Gate results may appear only in the certification manifest, authenticated
  coach review, internal state, and internal reports.
- Failures remain invisible to the customer and loud to the coach through the
  existing clean / needs-review / failed order vocabulary. This spec creates no
  customer failure email and no new delivery channel.

### 0.2 The workout estate (scale and validation stated honestly)

| Body | Verified scale | Existing validation, without inheritance claims |
|---|---:|---|
| This pipeline’s Nate generator space | 100 archetypes × 6 levels = 600 entries in 24 categories | Partial structural/progression checks; this spec adds certification. Runtime guards are at `athletes/scripts/archetype_registry.py:178-209`. |
| Curated TrainingPeaks library | 524 ZWOs under `gravel-god-training-plans/workout-library/` | A physiology scorer/audit tool scores rendered segments (`gravel-god-training-plans/engine/physiology.py:3-14,99-127`). A stored, dispositioned full-corpus pass is not asserted. |
| Master-plan instances | 14,840 ZWOs under `gravel-god-training-plans/master_plans/` | Separate plan-instance QC exists (`gravel-god-training-plans/tools/validate_physiology.py:33-58`). These instances MUST NOT be said to inherit dose validation: only 7,656/14,840 (51.59%) matched a curated-library normalized `<workout>` body in the R2 audit; 7,184 differed. |
| Endure Labs stock library | Separate repository | Its own schema/content validator (`endurelabs/scripts/validate-stock-workouts.ts:1-27`). No validation inheritance is claimed. |

This specification governs only the first body and the other workout-emitting
paths reachable in this paid-order pipeline. Estate-wide convergence is a later
program. Certifying a design does not certify a dose-affecting rendered variant;
the final instance check in §4.4 remains mandatory.

### 0.3 Protections that already exist and MUST remain

| Protection | Verified location | Existing coverage | Added coverage |
|---|---|---|---|
| Imported archetype L1/L6 power endpoint | `athletes/scripts/test_workout_generation.py:1203-1216` | Endpoints only | All adjacent design-dose transitions |
| Advanced archetype L1/L6 power and volume | `athletes/scripts/test_workout_generation.py:2263-2347` | 16-archetype subset | All 100 archetypes |
| Named progression checks | `athletes/scripts/test_workout_generation.py:2855-2910` | BPA, Late-Race VO2max, Glycolytic Power | One common dose rule |
| Registry integrity | `athletes/scripts/archetype_registry.py:178-209` | Counts, unique names, six levels | Per-entry metrics and verdicts |
| Block rules | `athletes/scripts/block_compliance.py:156-199,272-289,373-403` | Nine real rules plus R08/R11 no-op delegation | R01–R26 registry and parity audit |
| Methodology distribution | `athletes/scripts/validate_workout_distribution.py:51-128,140-200` | Filename classification and fallback targets | Canonical-segment/config-only authority |

The actual gap is purpose-dose evidence, release-bound library certification,
exhaustive emitting-path provenance, and complete rubric execution—not an
absence of all prior quality work.

---

## 1. Normative dose model and vocabulary

### 1.1 Internal metric names and ownership

This specification does **not** migrate, overwrite, recompute, or reinterpret
canonical session `tss` or `tss_planned`. Those fields remain the athlete-facing
planned values used by TrainingPeaks payloads, calendar/preview display, weekly
budgeting, and existing rubric rules R03, R16, R23, and R26. Phase 3 currently
projects `tss` and `tss_planned` into canonical sessions at
`build/trustworthy-phase3:athletes/scripts/canonical_training_model.py:280-299,500-520`
and into TP operations at
`build/trustworthy-phase3:athletes/scripts/apply_contract.py:263-291`.

The new internal quantities are named only:

- `design_if`
- `design_tss`
- `design_kj`

Purpose gates, Q3, final-series comparison, certification manifests, and
`workout_quality_report.json` MUST use `design_*`. They MUST NOT read canonical
`tss` as a substitute. Athlete payloads and the four rubric rules named above
MUST continue to use canonical planned TSS and MUST NOT read `design_tss`.
W′bal and T@VO2max use the same prescribed trace but are separately named
diagnostics. This split is intentional and prevents a second internal score from
silently becoming an athlete-facing planned TSS.

### 1.2 Total 1 Hz trace function

Input is the final typed segment sequence. All segment seconds, repeats, and
targets MUST be finite and non-negative; durations and repeat counts MUST be
integers. Invalid or internally inconsistent input produces `UNAVAILABLE`, never
a partial score or fabricated pass.

For every prescribed segment, produce one sample per whole second:

1. Constant steady segment of `N` seconds and value `p`: samples `i = 0..N-1`
   are `p`.
2. Ramp/warmup/cooldown of `N` seconds from `low` to `high`: sample `i` is
   `low + (high - low) × i / max(1, N - 1)` for `i = 0..N-1`. Thus `N > 1`
   includes both endpoints; `N = 1` yields `low`; `N = 0` yields no sample.
   This is the same endpoint grammar used by the sibling physiology trace
   (`gravel-god-training-plans/engine/physiology.py:53-66`).
3. Interval segment: for each repetition in authored order, append exactly
   `on_seconds` samples at `on`, then `off_seconds` samples at `off`. The segment
   duration MUST equal `repeat × (on_seconds + off_seconds)`.
4. `free_ride` / target `free`: append no sample. Free seconds are excluded
   from both the numerator **and** duration of every `design_*` calculation.

Let the resulting prescribed trace be `P` and `N = len(P)`. For `N > 0`:

```
design_if  = (sum(p^4 for p in P) / N)^(1/4)
design_tss = (N / 3600) * design_if^2 * 100
design_kj  = sum(p * 250 W * 1 s / 1000 for p in P)
```

There is no intermediate rounding. Stored values retain IEEE-754 binary64
precision; presentation may round only after verdict computation. `250 W` is a
fixed design reference, not an athlete FTP.

For `N = 0`, the exact result is:

```
{"status":"NOT_APPLICABLE","reason":"EMPTY_PRESCRIBED_TRACE",
 "trace_seconds":0,"has_free_segments":true,
 "design_if":null,"design_tss":null,"design_kj":null}
```

For a mixed free/prescribed workout, score only the prescribed portion, set
`has_free_segments: true`, and set `trace_seconds` to prescribed seconds only.
For a wholly prescribed workout, set `has_free_segments: false`. The report also
stores `free_seconds`, so `trace_seconds + free_seconds` MUST equal the sum of
final segment durations.

The experimental per-segment `duration × p²` score and the Phase 3 ramp-average
parser are not this metric. They remain untouched for their existing consumers.
Golden fixtures have one expected answer from the function above.

### 1.3 Other diagnostics

- **W′bal reference diagnostic:** the minimum Skiba differential balance over
  the prescribed trace at FTP reference 250 W, CP = FTP/0.96, W′ = 20 kJ, and
  recovery `tau = 546 × exp(-0.01 × (CP-P)) + 316` seconds. It is a
  deterministic design diagnostic, never
  an athlete reserve or safety claim. Calibration includes FTP ∈ {200,250,300}
  and W′ ∈ {15,20,25} kJ sensitivity.
- **T@VO2max proxy:** prescribed main-set seconds at or above 106% FTP. It may
  compare only the same rep-geometry subtype and MUST NOT be presented as direct
  physiology or used for HR/RPE prescriptions.
- **Purpose contract:** `{class, subtype, main_set_segment_ids}`. Allowed initial
  classes are `vo2max`, `wprime_drain`, `threshold`, `endurance`, `recovery`,
  `openers`, `race_sim`, `assessment`, `free`, and `mixed`. Subtypes close the
  rep geometry, such as `vo2max/steady`, `vo2max/30_30`, and `vo2max/40_20`.

---

## 2. Release invariants

Mode A evaluates and reports. Mode B enforces calibrated gates. Hypotheses are
never effective blockers in either mode.

- **Q0 — invisible rigor:** every surface in §6 is unchanged through E1.
- **Q1 — final prescribed dose:** every final power-, HR-, or RPE-prescribed
  cycling session has an applicable calibrated purpose gate with effective
  `PASS`; mismatch is non-waivable. Free-only and external-fixed sessions use
  their explicit non-dose contracts.
- **Q2 — native library certification:** a selected native archetype row must be
  effective `PASS` in the revision-pinned manifest independently of its final
  instance verdict. A manifest PASS never exempts transformed segments.
- **Q3 — native design progression:** only native library level ladders with a
  non-empty prescribed trace are evaluated, exactly as §4.1 states. Q3 is a
  library sanity claim, not proof about the series an athlete ultimately rides.
- **Q4 — one methodology authority:** the four configured customer methodology
  IDs and render mapping in §4.7 are closed; unknown values fail generation.
- **Q5 — full rubric:** every R01–R26 row in Appendix 3 emits exactly one result,
  including explicit `NOT_APPLICABLE` rows.
- **Q6 — defined review rails:** blockers, confirmations, quality findings, and
  verified facts enter state/catalog/snapshot only through §4.8.
- **Q7 — truthful control:** no fabricated watts; `rpe_pending_lthr` is a real
  RPE prescription and is gated as RPE under §4.9.

---

## 3. Gate authority and promotion

Every threshold, including both Q3 epsilons, begins as a hypothesis in
`athletes/config/quality_gates.yaml`. Required fields are `gate_id`,
`gate_version`, `purpose_subtype`, `metric`, `operator`, `threshold`, `unit`,
`evidence_basis`, `owner_id`, `status`, and `effective_from`. `status` is exactly
`hypothesis` or `calibrated`.

Every gate result stores separate `observed_verdict` and `effective_verdict`:

| Registry status | Observed verdict | Effective verdict in Mode A | Effective verdict in Mode B |
|---|---|---|---|
| `hypothesis` | `PASS`, `FAIL`, `NOT_APPLICABLE`, or `UNAVAILABLE` | `NOT_ENFORCED` for every observed value | `NOT_ENFORCED` for every observed value; hypotheses never enforce |
| `calibrated` | same observed set | `NOT_ENFORCED` for observed PASS/FAIL; NA/unavailable retained | observed verdict |

Mode A may therefore expose observed failures as quality findings without
authorizing a blocker. A status edit alone MUST NOT promote a gate. CI permits
`status: calibrated` only when a valid `quality_gate_promotion/v1` artifact from
Appendix 2 is present, its gate/version match, its reviewed row set covers every
applicable production row, all dispositions are digest-bound, and its owner is
the configured owner. The full artifact and its canonical digest are included
in the certification manifest.

Calibration requires the full 600-row render, owner dispositions (`fix`,
`re-class`, `retire`, or `band-adjust`), documented false-positive and
false-negative policies, and the W′ sensitivity grid where relevant. The Q3
gates are initially:

- `Q3_MIN_DESIGN_TSS_DELTA/v1`: `next - prior >= 1.0 design_tss`
- `Q3_MIN_DENSITY_DELTA/v1`: `next_design_tss_per_minute -
  prior_design_tss_per_minute >= -0.05`

Both are hypotheses and follow the identical promotion protocol. There is no
owner-by-prose exception. Changing a threshold or algorithm requires a new gate
version, a new promotion artifact, manifest regeneration, and review.

---

## 4. Workstreams and runtime contracts

### 4.1 Q3 native-library progression and final-series finding

For each native archetype whose six rendered levels all have non-empty
prescribed traces, evaluate every L1→L2 … L5→L6 transition on unrounded values:

```
next.design_tss >= prior.design_tss + 1.0
next.design_tss / (next.trace_seconds / 60)
    >= prior.design_tss / (prior.trace_seconds / 60) - 0.05
```

One effective failure fails the archetype ladder and every row in it. Purpose
gates and Q3 are independent and both must pass after promotion. The only known
Q3-exempt archetype is `Recovery / Rest Day`, all six levels, because all six
render as one FreeRide and have empty prescribed traces. A verified full render
found six such rows and 11 mixed testing rows; mixed rows are **not** exempt
because their prescribed portions are non-empty. CI repeats this inventory and
fails if the exempt set changes without a reviewed update to this section.
An archetype with a mixture of empty and non-empty levels is not exempt: its Q3
result is `UNAVAILABLE` because an adjacent comparison is undefined, and it
cannot be certified until fixed or retired.

Q3 says nothing about post-selection caps or scaling. A separate plan-level
check groups final sealed cycling sessions by non-null canonical `series_id`,
which today is emitted from `(block_number, day_abbrev, resolved_display_name)`
at `athletes/scripts/generate_athlete_package.py:2227-2244,2309-2321`. Exact
string equality defines one series identity; replacement IDs do not merge old
and new series implicitly. Within each group, order load-week sessions by
`(week, date, daily_ordinal)` and require each later final `design_tss >=` the
previous value. Equality is allowed: a cap-induced plateau is non-regression.
A decrease emits `SERIES_DOSE_REGRESSION`; an empty/unavailable dose inside a
prescribed series emits `SERIES_DOSE_UNAVAILABLE`. Both are
`quality_finding/v1` warnings, never blockers in r3, and are promotable only by a
later reviewed gate-version change.

Progression fixtures include flat, rounded-flat, mixed-direction, one-transition
failure, duration-led progression, pure-free exemption, mixed FreeRide scoring,
cap plateau, cap regression, and missing-dose series rows.

### 4.2 Main-set boundary

Every native purpose contract lists immutable segment IDs in
`main_set_segment_ids`. The renderer assigns the IDs before projection. Warmup,
cooldown, primers, hard starts, finishers, and assessment efforts are included
only when explicitly named. T@VO2max is computed only over listed prescribed
samples. A missing/duplicate segment ID is `UNAVAILABLE`; positional inference
is forbidden. Bands remain per rep-geometry subtype and enter through §3.

### 4.3 FreeRide contract

Free seconds never receive assumed power. Race-day and assessment free efforts
are checked for identity, declared duration, intended structure, and truthful
`free` targets. Mixed workouts receive the prescribed-portion calculation in
§1.2 and `has_free_segments: true`. Pure-free workouts receive the exact
`NOT_APPLICABLE` sentinel. Legacy 55%/65% preview estimates remain canonical
planned/display estimates only and MUST NOT enter `design_*`, W′bal, T@VO2max,
or a gate.

### 4.4 Exhaustive workout-origin union and final-instance gate

Origin is assigned by the emitting branch, stored in the naming manifest and
canonical session, and never inferred from title. Every cycling session has
exactly one of these closed discriminants:

| Discriminant | Reachable producer | Required contract |
|---|---|---|
| `NATIVE_ARCHETYPE` | Block-builder mapper → Nate render | Immutable `archetype_id` + level must PASS pinned manifest; final prescribed segments independently pass purpose gate. |
| `MAPPER_SIMPLE_ENDURANCE` | `workout_mapper._render_simple_endurance` (`athletes/scripts/workout_mapper.py:208-215,256-313`) | Versioned renderer/source digest + final `endurance` gate; no native-row fiction. |
| `LEGACY_NATE_ARCHETYPE` | Direct legacy `generate_nate_zwo` (`athletes/scripts/generate_athlete_package.py:2693-2787`) | Resolve and record selected immutable ID before render, then the same two-part native gate. A missing identity is not tolerated. |
| `PROGRESSIVE_INTERVAL_GENERATOR` | `generate_progressive_interval_blocks` (`athletes/scripts/generate_athlete_package.py:2792-2802`) | Generator/source digest, `threshold` or `vo2max/<geometry>` purpose from returned template ID, final purpose gate. |
| `PROGRESSIVE_ENDURANCE_GENERATOR` | `generate_progressive_endurance_blocks` (`athletes/scripts/generate_athlete_package.py:2803-2809`) | Generator/source digest and final `endurance` gate. |
| `STANDARD_BLOCK_GENERATOR` | `create_workout_blocks`, including pre-plan and B-race opener/easy overlays (`athletes/scripts/generate_athlete_package.py:1237-1339,2333-2439,2810-2855`) | Versioned template ID, overlay parameters, source digest, and final gate for its explicit purpose. FTP/anaerobic assessment templates use assessment contract instead. |
| `REST_SENTINEL_ZWO` | Bespoke one-segment, 60-second 30% Rest ZWO (`athletes/scripts/generate_athlete_package.py:2442-2482`) | Exact rest-sentinel structure/duration target plus truthful rest identity; `design_*` recorded but no Q3/library pin. |
| `A_RACE_FREERIDE` | Bespoke A-race ZWO (`athletes/scripts/generate_athlete_package.py:2569-2665`) | Pure-free race identity, declared duration, race priority A; dose `NOT_APPLICABLE`. |
| `B_RACE_FREERIDE` | Bespoke B-race ZWO (`athletes/scripts/generate_athlete_package.py:2024-2082`) | Pure-free race identity, declared duration, race priority B; dose `NOT_APPLICABLE`. |
| `TRAVEL_SHAKEOUT` | Bespoke travel renderer (`athletes/scripts/generate_athlete_package.py:2084-2128`) | Versioned template/source digest and final recovery/endurance gate. |
| `ASSESSMENT` | FTP/anaerobic/CP/ramp field-test path, native or standard | Identity, duration, required prescribed setup/cooldown structure, truthful free effort; score prescribed portion only and never W′bal/T@VO2max-gate the self-paced effort. |
| `ATHLETE_FIXED` | Locked recurring cycling session materialized by canonical builder | Athlete-reported title, duration and planned TSS sanity; no invented segments; dose `NOT_APPLICABLE`. Phase 3 creates this origin at `build/trustworthy-phase3:athletes/scripts/canonical_training_model.py:333-351`. |
| `CANONICAL_REST` | Calendar day with no emitted ZWO | Exact zero duration/TSS, no segments, day-off TP kind; dose `NOT_APPLICABLE` (`build/trustworthy-phase3:athletes/scripts/plan_ir.py:467-481`). |
| `STRENGTH_TEMPLATE` | Strength ZWO/template path | Outside cycling dose; enters R11–R13 and retains template provenance. |

Anything else emits `WORKOUT_ORIGIN_UNKNOWN`, a non-waivable blocker. A known
branch MUST NOT deliberately route to unknown; that is an order-killer, not a
completed union.

The R2 review called the Rest artifact “one-second”; verified production code
emits one `SteadyState` segment whose duration is 60 seconds. The discriminant
and contract use the executable value, not that shorthand.

E3 requires a production reachability sweep: render the complete golden fleet,
then a synthetic cross-product of the four methodology IDs × `gravel|road|mtb`
× `transition|base|build|peak|taper|race`, with testing/recovery week types and
fixtures enabling A-race, B-race, travel, pre-plan, locked fixed sessions,
strength, missing HR anchor, every mapped workout type, Nate failure-to-standard
fallback, and rest. Every emitted session must resolve to one table row and the
aggregate count of `WORKOUT_ORIGIN_UNKNOWN` must be zero.

### 4.5 R01–R26 registry, execution, and ordering

Appendix 3 is the complete initial `rule_registry/v1`; implementation writes it
verbatim to `athletes/config/rule_registry.yaml`. It settles severity,
applicability, algorithm, exact final input, NA/unavailable behavior, and output
code for every R01–R26. Its normative source rules are verified at
`gravel-god-training-engine/docs/block-builder-compliance-rules.md:1-142`; the
reference scorer’s complete execution list is at
`gravel-god-training-engine/docs/block-builder-scorer-reference.py:1168-1195`.
The compliance-rules document controls severity and semantics where the
scorer/skill differ, except stricter recovery-week purity remains CRITICAL. R18
and R22 are explicitly `DEFERRED` and emit
`NOT_APPLICABLE` until their named inputs exist. R03 is intentionally changed
from the current dynamic implementation: `<50% FAIL`, `50–65% PASS`, `>65–75%
WARNING`, and `>75% FAIL`.

R26 is adopted as CRITICAL because the pipeline has two independently produced
values worth reconciling after mutation: candidate weekly reported cycling TSS
and the sum of final session canonical planned TSS. The check detects post-scale
or overlay accounting divergence and uses the scorer reference’s 15-TSS
tolerance; race weeks accept the closer sum with or without the race event
(`gravel-god-training-engine/docs/block-builder-scorer-reference.py:1056-1075`).

The exact order is:

1. Finish selection, day-cap fitting, overlays, all duration scaling, and final
   authored session mutation.
2. Assign immutable session IDs and origin/provenance. Freeze
   `FinalPlanCandidate/v1`; no later step may mutate training content.
3. Run final-instance dose gates, final-series warning, and all Appendix 3 rules
   against that frozen candidate and the exact ancillary artifacts named there.
4. Write `workout_quality_report.json`; merge rubric CRITICAL failures into
   `blocking_issues`, warnings into `quality_findings`, and its two derived
   entries into `derived_values`. Refresh the catalog.
5. Finalize `canonical_training_model.json` from the same frozen candidate,
   then build PlanIR/TP projections. The canonical finalizer MUST assert session
   ID/content equality with the report.
6. Run Phase 3 post-render validators. Merge their output and refresh the review
   catalog a final time.
7. Build `apply_contract.json` from the finalized model **and final catalog**;
   it consumes the manifest-pin digest. No catalog mutation is permitted after
   contract build.
8. Persist revision files, build deterministic bundles, and finalize the v2
   release seal.

A rule crash produces the existing non-waivable `VALIDATOR_CRASH` or
`POST_RENDER_VALIDATOR_CRASH`, not a pass. Missing required input for an active
CRITICAL rule produces a waivable structural blocker `<OUTPUT_CODE>_UNAVAILABLE`;
for a WARNING rule it produces a quality finding. `NOT_APPLICABLE` is used only
when the registry’s applicability is false or its status is explicitly
`DEFERRED`.

### 4.6 Closed non-waivable policy amendment

This specification normatively amends the fulfilment specification’s closed
non-waivable set. The pre-r3 set and remediation map being amended are verified
at `build/trustworthy-phase3:webhook/fulfillment_state.py:47-71`. The complete
set after r3 is:

```
APPLY_CONTRACT_INVALID
COURSE_UNRESOLVED
FTP_ESTIMATED
LIBRARY_UNCERTIFIED
MANIFEST_PIN_MISMATCH
MANIFEST_PIN_MISSING
MANIFEST_SNAPSHOT_UNAVAILABLE
POST_RENDER_VALIDATOR_CRASH
SEAL_MISMATCH
STATE_UNAVAILABLE
VALIDATOR_CRASH
WORKOUT_DOSE_MISMATCH
WORKOUT_ORIGIN_UNKNOWN
```

Server-owned remediation text is exact:

| Code | Remediation |
|---|---|
| `FTP_ESTIMATED` | Supply a measured FTP and regenerate this revision. |
| `COURSE_UNRESOLVED` | Regenerate in athlete-facts-only mode or resolve the exact course. |
| `STATE_UNAVAILABLE` | Repair durable state and regenerate the order. |
| `VALIDATOR_CRASH` | Repair the validator failure and regenerate the order. |
| `POST_RENDER_VALIDATOR_CRASH` | Repair the post-render validator failure and regenerate the order. |
| `SEAL_MISMATCH` | Regenerate from immutable source artifacts and review again. |
| `APPLY_CONTRACT_INVALID` | Repair the offline contract and regenerate this revision. |
| `LIBRARY_UNCERTIFIED` | Fix, re-classify, or retire the uncertified library entry and regenerate this revision. |
| `WORKOUT_DOSE_MISMATCH` | Fix the final workout or its purpose contract and regenerate this revision. |
| `WORKOUT_ORIGIN_UNKNOWN` | Classify or repair the workout-emitting path and regenerate this revision. |
| `MANIFEST_PIN_MISSING` | Generate and pin the current certified manifest, then regenerate this revision. |
| `MANIFEST_PIN_MISMATCH` | Repair manifest selection or digest construction and regenerate this revision. |
| `MANIFEST_SNAPSHOT_UNAVAILABLE` | Restore revision-local snapshot creation and regenerate this revision; do not copy evidence into a sealed revision manually. |

Every remediation is fix-and-regenerate. `WORKOUT_OVERCOOKED` is not a code;
it is a `WORKOUT_DOSE_MISMATCH` reason. CI MUST assert set equality among the
literal list above, `NON_WAIVABLE_RULES`, keys of
`NON_WAIVABLE_REMEDIATIONS`, and the parameter set for approval-negative tests.
The earned-selection extension is exactly this literal set; both the remediation
map and negative-test parameterization MUST spell these six keys independently
rather than derive one collection from another:

```
EARNED_SELECTION_NON_WAIVABLE_RULES = {
    "LIBRARY_UNCERTIFIED",
    "WORKOUT_DOSE_MISMATCH",
    "WORKOUT_ORIGIN_UNKNOWN",
    "MANIFEST_PIN_MISSING",
    "MANIFEST_PIN_MISMATCH",
    "MANIFEST_SNAPSHOT_UNAVAILABLE",
}
```

The fulfilment `NON_WAIVABLE_RULES` is its pre-r3 set union this exact extension.
Each negative test supplies a covering waiver and proves approval is still
refused.

Rubric CRITICAL failures are structural judgments and remain waivable under the
fulfilment rules; waivers name rule ID, affected session IDs, and reason.

### 4.7 Methodology authority and fail-closed boundaries

The only production customer methodology IDs and render styles are:

```
time_crunched          -> POLARIZED
g_spot                 -> G_SPOT
polarized_80_20        -> POLARIZED
traditional_pyramidal  -> PYRAMIDAL
```

The map currently appears at `athletes/scripts/generate_athlete_package.py:
355-366`; its source becomes the checked config. `select_methodology.py`’s
inline fallback is deleted. `generate_athlete_package.py` MUST replace
`METHODOLOGY_MAP.get(methodology_id, 'POLARIZED')` at lines 591–594 with an
exact-key lookup that rejects unknown/missing IDs. Nate’s render-style lookup
MUST replace its unknown→POLARIZED fallback at
`athletes/scripts/nate_workout_generator.py:728-735` with rejection.

Malformed `methodologies.yaml`/`methodology_profiles.yaml`, unknown customer ID,
unknown render style, missing map entry, and missing/invalid config each fail
generation through the existing order-failure path: no customer error message,
a loud failed-order coach notification, and no silent substitute plan. Negative
fixtures cover all five cases. Known methodology avoid lists, offsets, and
selection behavior remain byte-identical in E1. Distribution targets come only
from `athletes/scripts/config/methodologies.yaml`; filename and inline fallback
targets are removed.

### 4.8 Quality-finding state/catalog/snapshot rail

New generations use:

```
SCHEMA_VERSION = 3                    # from 2
REVIEW_CATALOG_VERSION = "review_catalog/v2"
APPROVAL_SNAPSHOT_VERSION = "approval_snapshot/v3"
```

The prior values and four existing item types are verified at
`build/trustworthy-phase3:webhook/fulfillment_state.py:22-43`.

The state-owned authoritative collection is `quality_findings`. It is a list of
closed `quality_finding/v1` objects with fields:

`schema_version`, `id`, `generation_revision`, `source`, `code`, `severity`
(exactly `warning`), `subject` (object containing exactly `kind` and `ids`),
`metric` (canonical JSON object), `basis`, `sensitivity`, `message`,
`scorer_version`, and `registry_version`.

Only the generation pipeline may write it, through
`merge_quality_findings_v1(state_path, expected_revision, source, findings,
replace_source=True)`. The lock owner validates state revision, validates every
field, keys records by `(generation_revision, id)`, rejects duplicate IDs, and
replaces the complete prior set for that `source` and revision when
`replace_source=True`. Regeneration creates a new revision with an empty
collection; its first merge replaces that revision’s collection and never
copies findings from a prior revision. Coach/web/API input has no write path.
Every new-state constructor, legacy-state normalization path, and regeneration
constructor initializes `quality_findings` to `[]` when absent; only the
versioned merge may subsequently populate it.

Catalog rebuild has five authoritative sources in order:
`blocking_issues`, `required_confirmations`, `soft_confirmations`,
`quality_findings`, then `derived_values` plus release facts. Type rank is
blocker 0, required confirmation 1, soft confirmation 2, quality finding 3,
verified fact 4. This extends the four-source construction at
`build/trustworthy-phase3:webhook/fulfillment_state.py:344-408`.

Each finding is projected through the existing review-item field names
(`build/trustworthy-phase3:webhook/fulfillment_state.py:296-341`) as:

```
id                 = finding.id
item_type          = "quality_finding"
source             = finding.source
basis              = finding.basis
sensitivity        = finding.sensitivity
message            = finding.message
review_value       = {"code": finding.code, "severity": finding.severity,
                      "subject": finding.subject, "metric": finding.metric,
                      "generation_revision": finding.generation_revision,
                      "scorer_version": finding.scorer_version,
                      "registry_version": finding.registry_version}
display_unit       = null
resolution_choices = []
```

No field is accepted from a coach. `_review_item` then supplies `item_id`,
`type`, canonical `value`, `value_type`, `revision`, and the other common
catalog keys exactly as it does for existing sources.

Approval snapshots include one entry for every catalog item. For a quality
finding the server writes `disposition: observed`; coach input cannot supply or
change it. Snapshot validation accepts exactly `observed` for that type. No
acknowledgment is required, no email projection exists, and standard sensitivity
redaction applies. Sealed schema-v2 revisions remain readable under v2 dispatch
without mutation; regeneration produces v3 and supersedes any old approval.

Required tests: v3 state round-trip, invalid finding rejection, same-revision
source replacement, regeneration isolation, five-source deterministic rebuild,
catalog digest change on add/remove/mutate, automatic `observed` snapshot,
coach-disposition rejection, complete approval round-trip, and v2 sealed-state
backward verification.

### 4.9 HR, RPE, and missing anchors

Non-power targets use Phase 3’s exact piecewise normalization authority at
`build/trustworthy-phase3:athletes/scripts/canonical_training_model.py:119-147`.
Their trace uses normalized intensity in §1.2; gates are duration and
`design_tss`-equivalent sanity by purpose. W′bal and T@VO2max are power-only.

When HR is requested without LTHR or HRmax, Phase 3 selects control basis
`rpe_pending_lthr` and authors canonical `rpe` targets
(`build/trustworthy-phase3:athletes/scripts/canonical_training_model.py:43-65,164-194`).
That authored RPE content **is the canonical prescription**. It is gated exactly
like any other RPE prescription:
duration plus RPE-normalized `design_tss` sanity. It is not exempt and does not
receive invented HR or power. The existing missing-anchor confirmation remains
visible. A named fixture asserts requested HR + no anchors →
`rpe_pending_lthr`, all non-free targets `rpe`, applicable RPE gate, no power
assertion, and identical athlete surfaces.

Library certification still renders the native %FTP design; athlete projection
equality remains a separate Phase 3 responsibility.

### 4.10 Canonical session ID and workout-quality report

Canonical model version bumps from the verified
`canonical_training_model/v1` constant
(`build/trustworthy-phase3:athletes/scripts/canonical_training_model.py:25-26`)
to exactly `canonical_training_model/v2` and adds required `id`. For every
session:

```
id = "w{week:02d}.{date}.{daily_ordinal:02d}"
```

`week` is the existing integer (including W00), `date` MUST be ISO `YYYY-MM-DD`,
and `daily_ordinal` is the existing 1-based ordinal assigned in final session
order (`build/trustworthy-phase3:athletes/scripts/canonical_training_model.py:481-505`).
The final candidate fixes order before ID assignment; title, display name, and
filename do not participate.
Missing/invalid date, non-positive ordinal, duplicate week/date/ordinal, duplicate
ID, or a later reordering is a generation failure. There is no suffix or
collision recovery. Regeneration may create a new revision with the same logical
IDs; IDs are immutable within and across byte-identical revisions.

`workout_quality_report.json` is the closed `workout_quality_report/v1` schema in
Appendix 2. No extra keys are permitted at any level. It contains internal
metadata plus two derived aggregates: `gate_summary` and `manifest_pin`. Exactly
two derived-registry records cover it, with no extra root fields:

```
{
  "id": "QUALITY_GATE_SUMMARY",
  "field": "gate_summary",
  "class": "inferred",
  "basis": "workout_quality_report/v1 results computed from frozen final sessions and rule_registry/v1",
  "inputs": {
    "artifact": "workout_quality_report.json",
    "artifact_sha256": "<sha256 of canonical JSON report payload>",
    "canonical_candidate_sha256": "<sha256 of canonical FinalPlanCandidate/v1>",
    "scorer_version": "<report.scorer_version>",
    "gate_registry_version": "<report.gate_registry_version>",
    "rule_registry_version": "rule_registry/v1",
    "session_ids": "<ordered array of every report session_id>"
  },
  "sensitivity": "internal",
  "at": "<report.generated_at>",
  "revision": "<report.generation_revision>"
}
{
  "id": "QUALITY_MANIFEST_PIN",
  "field": "manifest_pin",
  "class": "inferred",
  "basis": "revision-local certification_manifest/v1 snapshot selected and digest-verified before scoring",
  "inputs": {
    "artifact": "certification_manifest.json",
    "snapshot_path": "<report.manifest_pin.snapshot_path>",
    "snapshot_digest": "<report.manifest_pin.snapshot_digest>",
    "manifest_version": "<report.manifest_pin.manifest_version>",
    "gate_version": "<report.manifest_pin.gate_version>",
    "promotion_digests": "<ordered report.manifest_pin.promotion_digests>"
  },
  "sensitivity": "internal",
  "at": "<report.generated_at>",
  "revision": "<report.generation_revision>"
}
```

Angle-bracket values are runtime substitutions of the named field, not optional
text. `at` is the fixed generation timestamp, not call time. `class` values are
valid Phase 3 classes; r2’s invalid `computed`/`verified` labels are withdrawn.
`derived_registry.py` adds a closed artifact schema whose only derived roots are
`gate_summary` and `manifest_pin`; metadata is raw. Coverage must be exact under
`assert_registry_covers`, whose current closed behavior is at
`build/trustworthy-phase3:athletes/scripts/derived_registry.py:359-415,431-475`.

---

## 5. Certification, identity migration, and seal v2

### 5.1 Manifest generation and exact payload

`athletes/config/workout_certification.json` is generated atomically by
`athletes/scripts/certify_workout_library.py` over the production registry. Its
payload is exactly `certification_manifest/v1` in Appendix 2. It includes all
600 rows, separate observed/effective verdicts, gate authority status, complete
promotion artifacts, source/render digests, and scorer/gate versions.

Any commit changing archetype source, renderer, scorer, gate config, purpose
mapping, ID map, or promotion artifact MUST regenerate the manifest. CI
re-renders, canonicalizes, and requires byte equality after the fixed
`generated_at` is supplied by the build fixture. A stale manifest cannot be
green.

### 5.2 Immutable IDs, ordered slots, tombstones, and equivalence

Appendix 4 is the reviewed exact initial content of
`athletes/config/archetype_ids.json`; E1 commits it byte-for-byte. The slug
function is:

1. Unicode NFKD normalize.
2. Encode ASCII with non-ASCII code points ignored, then decode ASCII.
3. Unicode `casefold()` (ASCII result).
4. Extract maximal `[a-z0-9]+` runs and join them with `-`.
5. `archetype_id = slug(category) + "--" + slug(name)`.

An empty slug or duplicate ID fails generation; there is no numeric suffix.
Existing IDs are never recomputed after E1 and never reused.

Selection order is the explicit per-category array order in Appendix 4, frozen
from the current `NEW_ARCHETYPES[category]` order. For requested integer index
`k`, compute slot `k mod slot_count`. An active slot returns its ID. A retired
slot retains its position forever:

1. If `replacement_id` is non-null, follow it. Replacement targets MUST exist,
   be active, and have the same category and compatible purpose; replacement
   chains and cross-category replacement are invalid.
2. Otherwise scan `(slot+1) mod slot_count`, then subsequent slots, and return
   the first active ID. If no active slot exists, fail generation.

No slot is removed, inserted before an existing slot, or compacted. A
replacement changes only selections that landed on its tombstoned slot. Series
identity records the finally selected ID and does not pretend it is the retired
ID.

E1’s equivalence test is exhaustive, not profile-sampled: enumerate every
reachable `(methodology_id, render_style, discipline, phase, workout_type,
base_variation, variation_offset, level)` tuple. `variation_offset` spans
`0..N` inclusive where `N` is that category’s slot count, exercising one full
wrap plus the repeated zero slot; methodology/block/usage offsets are included.
Compare pre-migration selected category/name and rendered ZWO bytes with the
post-migration ID-resolved category/name and bytes. Every tuple must match.
Golden fleet tests are additional, not substitutes.

### 5.3 Revision snapshot path and digest

The actual Phase 3 order layout is
`${DATA_DIR}/deliveries/orders/<safe_order_id>/revisions/r<n>/`, created at
`build/trustworthy-phase3:webhook/app.py:1836-1842,2044-2055`. The snapshot path
is exactly:

```
${DATA_DIR}/deliveries/orders/<safe_order_id>/revisions/r<n>/certification_manifest.json
```

It is copied before bundle construction and seal finalization. It is included in
the revision’s release artifact inventory as `certification_manifest.json`; it
is not placed in the customer/review ZIP and is not nested under `artifacts/`.

`certification_manifest` digest means lower-case SHA-256 hex over canonical JSON
of the parsed snapshot payload: sorted keys, compact separators `(',', ':')`,
`ensure_ascii=False`, `allow_nan=False`, UTF-8. Pretty-file bytes and envelopes
are not hashed. Missing file → `MANIFEST_SNAPSHOT_UNAVAILABLE`; missing expected
pin → `MANIFEST_PIN_MISSING`; digest/payload/path/version mismatch →
`MANIFEST_PIN_MISMATCH`.

### 5.4 `canonical_model_apply_contract/v2`

The current `canonical_model_apply_contract/v1` four-key source object is at
`build/trustworthy-phase3:athletes/scripts/apply_contract.py:693-708` and is
independently reconstructed at
`build/trustworthy-phase3:webhook/fulfillment_state.py:802-829`. New generations
use exactly:

```
seal_version = "canonical_model_apply_contract/v2"
model_seal_sources = {
  "canonical_model": <parsed canonical_training_model.json>,
  "review_items": <final catalog excluding FACT_RELEASE_SEAL>,
  "guide_sources": <existing sorted name->sha256 map>,
  "operation_payloads": <existing ordered logical_id/kind/disposition/payload records>,
  "certification_manifest": <64-character snapshot digest string>
}
model_seal = sha256(canonical_json(model_seal_sources)).hexdigest()
```

Only the digest string enters the source object. The full manifest payload lives
in the revision inventory and is independently digest-checked. The apply
contract schema/version bumps to `apply_contract/v2` and carries
`seal_version`; v1 contracts remain readable.

Every constructor/verifier dispatch point is closed:

- `apply_contract.py`: `model_seal_sources`, `compute_model_seal`,
  `build_contract`, checked JSON schema, contract semantic validator, and
  predecessor/operation-provenance validation dispatch v1 versus v2.
- `webhook/fulfillment_state.py`: `CANONICAL_SEAL_VERSION` becomes the v2 string;
  `_canonical_model_seal_from_release` reconstructs by manifest seal version;
  `finalize_transitional_release` constructs v2 for new canonical releases;
  `verify_release_manifest` accepts transitional v1, canonical v1, or canonical
  v2 and reconstructs the matching exact object.
- `test_apply_contract.py`, `test_fulfillment_state.py`, athlete-m acceptance,
  and release-manifest tests carry fixtures for both canonical versions.

No other production seal-version references existed in the verified Phase 3
tree. Unknown versions fail closed. A sealed v1 revision never reads the new
snapshot retroactively; a v2 revision never reads the mutable repository-global
manifest after sealing. Mutating the global manifest leaves old verification
unchanged; regeneration selects the new manifest and creates a new v2 seal.

### 5.5 Retirement and in-flight orders

Initial failures are owner-dispositioned as fix, re-class, retire, or band
adjust. A sealed revision keeps its manifest snapshot and is grandfathered.
Later retirement does not invalidate its approval. Any regeneration uses the
current ID map and manifest, creates a new revision/seal, and requires review.
A blocked, unapproved revision is not mutated in place; fix-and-regenerate is
the only remediation.

---

## 6. Q0 closed athlete-surface inventory and deterministic comparison

E1 runs every golden order before and after with one fixed clock, timezone,
locale, random seed, order/athlete IDs, filesystem mtimes, renderer/container,
fonts, and dependency lock. It compares every item below:

1. Every emitted cycling ZWO byte and athlete-visible ZWO filename.
2. `training_guide.html` and `training_guide.pdf`.
3. `dashboard.html`, `plan_preview.html`, and `fueling.yaml`.
4. Every customer bundle entry and the complete
   `<order>-customer-bundle.zip` bytes. ZIP member order is the current
   `CUSTOMER_DELIVERABLES` order followed by sorted workout paths; member mtimes,
   permissions, compression level, and platform flags are fixed. The current
   list/path is at `build/trustworthy-phase3:webhook/app.py:1794-1809,2095-2104`.
5. TrainingPeaks apply-contract athlete projections: every
   `workout_upsert.payload` field (`date`, `title`, `description`, workout type,
   total seconds, planned TSS, structure), every session
   `calendar_note_upsert.payload`, and guide attachment filename/bytes/digest
   (`build/trustworthy-phase3:athletes/scripts/apply_contract.py:263-330`).
6. The equivalent Endure athlete plan/delivery payload when Endure is enabled,
   excluding provider-assigned IDs but including every athlete-visible field.
7. Athlete-addressed Gmail draft RFC 5322/MIME bytes, body, headers, attachment
   names/order, and attachment bytes. Harness sets Date/Message-ID, derives a
   fixed MIME boundary from order+revision, uses fixed CRLF and transfer
   encoding, and attaches the sealed guide. The contract is described at
   `docs/SPEC_TRUSTWORTHY_FULFILMENT.md:910-938`.
8. The canonical day-1/day-3/day-7 follow-up subjects and template bodies from
   `webhook/email_templates.py:31-105` after fixed `first_name` substitution.
9. Published guide HTML/PDF bytes if guide publishing is enabled.

Internal review/state/report/manifest/provenance fields are intentionally not
in this inventory. `coaching_brief.md` and review ZIP are coach surfaces and may
gain internal findings, but tests separately prove no athlete copy leaks into
them or from them.

PDF, ZIP, and MIME are byte-deterministic requirements, not assumed facts: pin
PDF metadata/clock/fonts/renderer, normalize input mtimes and ZIP metadata, and
set MIME boundaries/headers. **No semantic-only exception is approved by r3.**
If a surface demonstrably cannot be made byte-deterministic, E1 stops. A named
exception may be added only by owner-signed spec amendment identifying that one
surface, the irreducible nondeterministic bytes, the exact semantic comparator,
and accepted evidence. It MUST NOT weaken any other surface silently.

---

## 7. Acceptance and rollout

### 7.1 Required fixtures and tests

1. Trace goldens for zero/one-second ramps, both ramp directions, steady,
   intervals, mixed/pure FreeRide, invalid interval duration, and empty sentinel.
2. Known 40/20, 30/30, 5×3, threshold, endurance, recovery, assessment, and
   `rpe_pending_lthr` goldens.
3. Manifest regeneration equality; observed/effective verdict direction tests;
   invalid calibrated-without-promotion; promotion digest/coverage/policy tests.
4. Q3 and final-series fixtures in §4.1.
5. One fixture per §4.4 origin plus the complete reachability sweep.
6. Complete Appendix 3 row fixtures, including R03’s four bands, R18/R22 NA,
   R08/R11 real integrations, active-rule unavailable, crash, and R26 race sums.
7. State/catalog/snapshot tests in §4.8 and exact derived-report coverage.
8. Six non-waivable code negatives and complete set-equality test in §4.6.
9. Session ID round-trip, same-day doubles, missing date, duplicate week/date/
   ordinal collision, stable regeneration, and report/model ID equality.
10. Methodology malformed/unknown/missing fixtures and exhaustive ID-selection
    equivalence.
11. Dual-constructor v2 seal equality, canonical-v1 backward verification,
    transitional-v1 verification, stale global manifest, missing snapshot,
    missing pin, mismatched digest, and unknown version.
12. The complete §6 surface comparison, athlete-m Mode A replay, and null-FTP
    redaction/no-power-leak checks.

### 7.2 Rollout

- **E1 — audit-only plumbing:** commit Appendix 4 as
  `athletes/config/archetype_ids.json`; migrate selection with exhaustive byte
  equivalence; add origins, scorer, hypothesis results, manifest/report,
  Appendix 3, state/catalog/snapshot v3, and seal v2. No content changes. Q0
  must pass on every surface.
- **E2 — owner dispositions:** fix/re-class/retire/band-adjust the observed
  backlog. Content byte changes are allowed only here, each enumerated and
  rebaselined. Promotions use §3 artifacts.
- **E3 — Mode B:** requires every selectable native row effective PASS; every
  enforcing gate (including both Q3 epsilons) validly promoted; all six new
  non-waivable codes integrated; zero unknown origins in golden+synthetic
  reachability; exact rule registry parity; state/catalog/snapshot migrations;
  seal v2; Q0 green for E1; and no unexplained E2 regression.

Mode transitions are reviewed commits. `GG_STRICT_COMPLIANCE` is removed when
Mode B lands because fulfilment blockers, not generation-time order killing,
own structural review. A complete built package remains available to the coach;
only a crash with no usable package follows the loud failed-order path.

---

## 8. Explicit non-goals

- No E1 replanning or runtime substitution.
- No athlete-facing explanation or metric exposure.
- No certification claim for the curated TP library, master plans, or Endure
  library.
- No per-athlete W′ estimation or safety claim.
- No LLM judgment in a gate path.
- No unpromoted training-science authority.
- No automatic promotion of the final-series warning in r3.

---

## Appendix 1 — combined R1 + R2 blocker disposition map

### A1.1 R1 blockers

| R1 | r3 disposition |
|---:|---|
| 1 | §0.3 retains and accurately scopes existing progression/compliance checks. |
| 2 | §3 supplies hypothesis/effective semantics and an exact promotion artifact. |
| 3 | §1.1–1.2 supplies one total internal `design_*` function without migrating canonical TSS. |
| 4 | §1.3/§4.2 define authored main-set IDs and geometry-specific T@VO2max. |
| 5 | §1.3 limits W′bal to a reference diagnostic and requires sensitivity. |
| 6 | §1.2/§4.3 define pure and mixed FreeRide semantics. |
| 7 | §4.4, §5.1–§5.4 bind native identity and final transformed dose to the sealed revision. |
| 8 | §4.4 supplies the exhaustive origin union and unknown-origin failure. |
| 9 | §4.1 preserves exact adjacent-level inequalities/directions and adds fixtures. |
| 10 | §4.6 supplies the closed non-waivable policy and negatives. |
| 11 | §5.3–§5.4 supplies exact snapshot path, digest, source object, version, and dispatch. |
| 12 | §4.8 supplies authoritative state collection, catalog, and snapshot behavior. |
| 13 | §4.10/Appendix 2 supply stable IDs, closed report schema, and complete derived entries. |
| 14 | §4.5/Appendix 3 supplies the complete normative rubric. |
| 15 | §4.5 requires semantic parity and replaces R08/R11 no-op passes. |
| 16 | §4.5 fixes post-overlay/pre-finalization order and per-rule inputs/NA behavior. |
| 17 | §4.7 fails all methodology boundaries closed while preserving known selection. |
| 18 | §4.9 uses Phase 3 normalization and settles missing-anchor RPE gating. |
| 19 | §5.2/§5.5/§7 retain tombstones, exhaustive equivalence, E1/E2/E3, and in-flight pinning. |

### A1.2 R2 blockers

| R2 | r3 disposition |
|---|---|
| R2-01 | §1.1–§1.2: `design_*`, exact 1 Hz ramp, trace duration, empty sentinel, mixed FreeRide, known Rest Day exemption. |
| R2-02 | §3 and Appendix 2: observed/effective split, hypothesis never enforced, promotion schema, Q3 protocol. |
| R2-03 | §4.1 narrows Q3 to native designs and adds final-series warnings using existing series identity. |
| R2-04 | §4.4 names every reachable producer and makes zero unknown origins an E3 criterion. |
| R2-05 | §4.6 names six new codes/remediations, amends the closed set, and requires set equality. |
| R2-06 | §4.8 defines `quality_findings`, merge/regeneration, rank, observed snapshot, versions, and tests. |
| R2-07 | §5.3–§5.4 define real `r<n>` path, canonical digest, v2 source key/version, inventory, and dispatch. |
| R2-08 | §4.10 and Appendix 2 define session ID, collision failure, report schema, and both registry records. |
| R2-09 | Appendix 3 is the complete R01–R26 registry/matrix; §4.5 fixes execution order and contested decisions. |
| R2-10 | §4.7 rejects unknown IDs/styles/config at both POLARIZED fallback boundaries. |
| R2-11 | §5.2 and Appendix 4 define slug IDs, committed order, tombstone selection, and exhaustive equivalence. |
| R2-12 | §4.9 makes `rpe_pending_lthr` canonical RPE and gates it as RPE. |
| R2-13 | §0.2 removes master-instance inheritance and states separate QC honestly. |
| R2-14 | §6 supplies the closed athlete-surface inventory and deterministic/owner-exception rule. |

---

## Appendix 2 — closed artifact schemas

### A2.1 `quality_gate_promotion/v1`

No extra keys are allowed. All digests are lower-case 64-character SHA-256.

```
{
  "schema_version": "quality_gate_promotion/v1",
  "gate_id": string,
  "gate_version": string,
  "owner": {"owner_id": string, "display_name": string},
  "reviewed_row_set": {
    "manifest_input_digest": sha256,
    "row_ids": [string, ...],
    "digest": sha256
  },
  "dispositions_digest": sha256,
  "false_positive_policy": string,
  "false_negative_policy": string,
  "sensitivity_policy": string,
  "promoted_at": ISO-8601-UTC string
}
```

`row_ids` is unique and lexicographically sorted. `reviewed_row_set.digest` is
SHA-256 canonical JSON of exactly `{"manifest_input_digest":...,
"row_ids":[...]}`. `dispositions_digest` is SHA-256 of the exact UTF-8 bytes of
`athletes/config/quality_gates_dispositions.md`. Empty policies are invalid.
Promotion artifact digest is SHA-256 canonical JSON of the entire object.

### A2.2 `certification_manifest/v1`

No extra keys are allowed at any level. Arrays are ordered as stated.

```
{
  "schema_version": "certification_manifest/v1",
  "generated_at": ISO-8601-UTC string,
  "registry_digest": sha256,
  "id_map_digest": sha256,
  "purpose_registry_version": string,
  "scorer_version": string,
  "gate_registry_version": string,
  "gate_version": string,
  "promotion_artifacts": [
    {"digest": sha256, "artifact": quality_gate_promotion/v1}, ...
  ],
  "source_digests": [{"path": string, "sha256": sha256}, ...],
  "rows": [
    {
      "row_id": string,
      "archetype_id": string,
      "category": string,
      "name": string,
      "level": integer 1..6,
      "catalog_status": "active" | "retired",
      "replacement_id": string | null,
      "purpose": {
        "class": string,
        "subtype": string,
        "main_set_segment_ids": [string, ...]
      },
      "source": {
        "path": string,
        "sha256": sha256,
        "renderer_version": string,
        "rendered_zwo_sha256": sha256
      },
      "dose": {
        "status": "APPLICABLE" | "NOT_APPLICABLE" | "UNAVAILABLE",
        "reason": string | null,
        "trace_seconds": integer,
        "free_seconds": integer,
        "has_free_segments": boolean,
        "design_if": number | null,
        "design_tss": number | null,
        "design_kj": number | null,
        "t_at_vo2max_seconds": integer | null,
        "wbal_nadir_kj": number | null
      },
      "gates": [
        {
          "gate_id": string,
          "gate_version": string,
          "authority_status": "hypothesis" | "calibrated",
          "observed_verdict": "PASS" | "FAIL" | "NOT_APPLICABLE" | "UNAVAILABLE",
          "effective_verdict": "PASS" | "FAIL" | "NOT_ENFORCED" | "NOT_APPLICABLE" | "UNAVAILABLE",
          "measurement": canonical-JSON object,
          "criterion": canonical-JSON object,
          "promotion_digest": sha256 | null
        }, ...
      ],
      "observed_verdict": "PASS" | "FAIL" | "NOT_APPLICABLE" | "UNAVAILABLE",
      "effective_verdict": "PASS" | "FAIL" | "NOT_ENFORCED" | "NOT_APPLICABLE" | "UNAVAILABLE"
    }, ...
  ],
  "summary": {
    "row_count": 600,
    "active_row_count": integer,
    "retired_row_count": integer,
    "observed_counts": canonical-JSON object,
    "effective_counts": canonical-JSON object,
    "q3_exempt_archetype_ids": [string, ...]
  }
}
```

`promotion_artifacts` sorts by `(gate_id, gate_version)`;
`source_digests` sorts by path; rows sort by Appendix 4 category slot, then
level. `row_id` is `<archetype_id>@L<level>`. Gates sort by `gate_id`.
`effective_verdict` aggregation is FAIL/UNAVAILABLE if any enforcing gate has
that value, PASS if every applicable calibrated gate passes, NOT_ENFORCED if
only hypothesis observations exist, and NOT_APPLICABLE only if no gate applies.

### A2.3 `workout_quality_report/v1`

No extra keys are allowed. `gate_summary` is one derived aggregate; all detailed
session/rubric data is nested under it so one registry field covers its complete
descendant tree.

```
{
  "schema_version": "workout_quality_report/v1",
  "generation_revision": positive integer,
  "generated_at": ISO-8601-UTC string,
  "scorer_version": string,
  "gate_registry_version": string,
  "rule_registry_version": "rule_registry/v1",
  "gate_summary": {
    "counts": {
      "sessions": integer,
      "observed_pass": integer,
      "observed_fail": integer,
      "effective_pass": integer,
      "effective_fail": integer,
      "not_enforced": integer,
      "not_applicable": integer,
      "unavailable": integer,
      "quality_findings": integer,
      "rubric_blockers": integer
    },
    "sessions": [
      {
        "session_id": string,
        "week": integer,
        "date": YYYY-MM-DD string,
        "daily_ordinal": positive integer,
        "sport": string,
        "origin": "<one §4.4 discriminant>",
        "control_metric": "power" | "hr" | "rpe" | "none",
        "control_basis": string,
        "archetype": {
          "archetype_id": string,
          "level": integer,
          "category": string,
          "variation": integer,
          "manifest_row_id": string
        } | null,
        "series_identity": string | null,
        "transformation_parameters": canonical-JSON object,
        "source_digests": [{"path": string, "sha256": sha256}, ...],
        "dose": {
          "status": "APPLICABLE" | "NOT_APPLICABLE" | "UNAVAILABLE",
          "reason": string | null,
          "trace_seconds": integer,
          "free_seconds": integer,
          "has_free_segments": boolean,
          "design_if": number | null,
          "design_tss": number | null,
          "design_kj": number | null,
          "t_at_vo2max_seconds": integer | null,
          "wbal_nadir_kj": number | null
        },
        "manifest_gate": {
          "row_id": string | null,
          "row_digest": sha256 | null,
          "observed_verdict": verdict,
          "effective_verdict": effective-verdict
        },
        "final_gates": [{
          "gate_id": string,
          "gate_version": string,
          "authority_status": "hypothesis" | "calibrated",
          "observed_verdict": verdict,
          "effective_verdict": effective-verdict,
          "measurement": canonical-JSON object,
          "criterion": canonical-JSON object
        }, ...],
        "quality_finding_ids": [string, ...]
      }, ...
    ],
    "rubric": [{
      "rule_id": "R01".."R26",
      "registry_status": "ACTIVE" | "DEFERRED",
      "severity": "CRITICAL" | "WARNING",
      "result": "PASS" | "FAIL" | "WARNING" | "NOT_APPLICABLE" | "UNAVAILABLE",
      "output_code": string,
      "subject_ids": [string, ...],
      "metric": canonical-JSON object,
      "message": string
    }, exactly 26 entries],
    "plan_series": [{
      "series_identity": string,
      "session_ids": [string, ...],
      "design_tss": [number | null, ...],
      "result": "PASS" | "WARNING" | "NOT_APPLICABLE" | "UNAVAILABLE",
      "finding_id": string | null
    }, ...]
  },
  "manifest_pin": {
    "snapshot_path": "certification_manifest.json",
    "snapshot_digest": sha256,
    "manifest_version": "certification_manifest/v1",
    "gate_version": string,
    "promotion_digests": [sha256, ...]
  }
}
```

Here `verdict` is `PASS|FAIL|NOT_APPLICABLE|UNAVAILABLE` and
`effective-verdict` additionally permits `NOT_ENFORCED`. Sessions sort by
`(week,date,daily_ordinal)`; source digests by path; gates by ID; finding IDs and
promotion digests lexicographically. Count sums and the exact 26-row rubric are
validated. Report canonical digest excludes no fields.

---

## Appendix 3 — normative `rule_registry/v1` and execution matrix

All ACTIVE rules run at §4.5 step 3 against `FinalPlanCandidate/v1`, whose
session fields are the exact fields later serialized to canonical model. Common
NA: no applicable week/session yields `NOT_APPLICABLE`, never PASS. Common
unavailable: an ACTIVE rule’s named input is missing/malformed. Output code is
stable and uppercase.

| ID | Status / severity | Applicability and exact algorithm | Exact frozen/sealed input | NA / unavailable | Output code |
|---|---|---|---|---|---|
| R01 | ACTIVE / CRITICAL | All cycling days: no consecutive calendar dates both containing intensity-role sessions, including week boundaries. Athlete-fixed hard sessions count. | candidate `sessions[].{id,date,sport,role,origin}` | <2 intensity dates → NA; missing date/role → unavailable | `R01_BACK_TO_BACK_INTENSITY` |
| R02 | ACTIVE / CRITICAL | Outside transition/off-season/racing exemptions, consecutive VO2 stimuli may be at most 16 non-recovery calendar days apart; ≥2 trainable weeks with none fails. Recovery weeks pause elapsed count. | candidate sessions purpose/role/date + `plan_dates.yaml` week type/phase | Exempt phase or <2 trainable weeks → NA; missing purpose/date/week type → unavailable | `R02_VO2_GAP` |
| R03 | ACTIVE / CRITICAL with warning band | For each non-racing recovery week, ratio canonical planned cycling TSS / mean preceding applicable load-week TSS: `<.50 FAIL`, `.50..65 PASS`, `>.65..75 WARNING`, `>.75 FAIL`. No volume-specific dynamic boundary. | candidate `weeks[].{week_type,phase,reported_cycling_tss}` and final sessions `tss`; race excluded | No load/recovery pair → NA; zero/missing denominator → unavailable | `R03_RECOVERY_TSS_RATIO` |
| R04 | ACTIVE / CRITICAL | Recovery weeks contain only rest, plain Endurance L1–L2, and Openers whose individual efforts are ≤30 s. Any tempo, cadence/SFR, threshold, VO2, race-sim, mixed, sustained >30 s, or other type fails. | final session purpose, level, segments + plan week type | No recovery week → NA; missing segment/purpose → unavailable | `R04_RECOVERY_PURITY` |
| R05 | ACTIVE / CRITICAL | Load weeks have 2–3 intensity sessions. Transition allows 0–3; training age <1 or ≤3 available cycling days allows 1–3. Recovery, race, and medium weeks are excluded. | final roles; `profile.yaml` training age/off days; `plan_dates.yaml` week type | No applicable load week → NA; missing role/week type → unavailable | `R05_INTENSITY_COUNT` |
| R06 | ACTIVE / CRITICAL | Every non-recovery/non-race week has ≥90 min ride when target hours ≤8, otherwise ≥120 min. A registered structured-endurance long design may satisfy at ≥75 min. | final cycling duration/purpose + profile target hours + week type | No applicable week → NA; missing duration/hours → unavailable | `R06_LONG_RIDE_MISSING` |
| R07 | ACTIVE / WARNING | Every week has one Monday block note whose registered note type equals final week type. | Final `training_guide.html` week-note section + `plan_dates.yaml` dates/types + `athletes/config/block_notes.yaml` digest, all named/digested in the frozen report | No paid weeks → NA; missing Monday/note/config → unavailable | `R07_BLOCK_NOTE` |
| R08 | ACTIVE / CRITICAL | Every non-rest, non-race cycling workout has exactly one valid `HIGH|MODERATE|PRACTICE` fuel tag from final fueling projection. This replaces the current unconditional pass. | final sessions + final `fueling.yaml` workout tags | Only rest/race → NA; missing fueling projection/tag → unavailable | `R08_FUEL_TAG_MISSING` |
| R09 | ACTIVE / WARNING | Intensity requires HIGH; race simulation may use PRACTICE; Cadence Work may use MODERATE. | final role/purpose + fuel tag | No intensity → NA; missing tag → unavailable | `R09_INTENSITY_FUEL` |
| R10 | ACTIVE / WARNING | PRACTICE appears only on race simulation during race-prep or on a race event. | final purpose/tag + phase | No PRACTICE tag → NA; missing phase/purpose → unavailable | `R10_PRACTICE_FUEL_SCOPE` |
| R11 | ACTIVE / CRITICAL | Every paid week has a strength prescription with phase, protocol, frequency, or an explicit athlete-declined-strength disposition. This replaces the no-op. | final strength sessions/templates + profile strength preference + week list | Explicit decline → NA; missing both prescription and disposition → unavailable/fail as evidence dictates | `R11_STRENGTH_TRACK` |
| R12 | ACTIVE / WARNING | Strength phase follows registered periodization: base permits max/foundation, race prep maintenance, recovery deload/mobility; max strength in race phase fails. | strength template phase + cycling phase + `strength_periodization.yaml` digest | Declined/no strength → NA; unknown phase/template → unavailable | `R12_STRENGTH_PHASE` |
| R13 | ACTIVE / WARNING | Max/heavy strength cannot share a date with key threshold/VO2/race-sim intervals. Maintenance/deload/bodyweight is exempt. | final same-date strength intensity and cycling roles | No max/heavy strength → NA; missing template intensity → unavailable | `R13_STRENGTH_INTERVAL_CONFLICT` |
| R14 | ACTIVE / CRITICAL | Within each tracker slot/block, exact normalized series name is coherent; Kitchen Sink variants normalize to Kitchen Sink. Final selected immutable ID must stay constant unless an explicit tombstone replacement was selected before series start. | `series_tracker` assignments frozen into candidate + selected IDs | <2 assignment in series → NA; missing tracker identity → unavailable | `R14_SERIES_COHERENCE` |
| R15 | ACTIVE / WARNING | Across applicable load-week pairs in one series, level delta 0, 1, or 2 passes; decrease or jump >2 fails. This follows compliance-doc allowance of same level and scorer jump tolerance. | final `series_id`, level, week type | No pair or non-native series → NA; missing level → unavailable | `R15_LEVEL_PROGRESSION` |
| R16 | ACTIVE / WARNING | Each non-race week’s sum of canonical planned session TSS is within ±15% of configured target TSS. | final session `tss`; candidate weekly target TSS | No target/race week → NA; target present but malformed → unavailable | `R16_TSS_GUARDRAIL` |
| R17 | ACTIVE / CRITICAL | Purpose/type must be allowed by phase registry: base forbids kitchen-sink/race-sim; build must include threshold/VO2 character; race prep forbids base-only SFR/cadence and permits simulation/openers. | final purpose/type + final phase + phase-purpose mapping digest | Transition/recovery handled by their own allowed sets, not silent pass; missing mapping → unavailable | `R17_PHASE_MISMATCH` |
| R18 | DEFERRED / WARNING | Phase zone-time distribution against registered targets. No filename approximation. | Required future per-session zone-duration data | Always `NOT_APPLICABLE` in r3 because required zone data does not exist; never unavailable/pass | `R18_PHASE_DISTRIBUTION` |
| R19 | ACTIVE / CRITICAL | Every load/medium week cycling duration ≤ athlete available hours ×1.10 +5 min. Recovery/race naturally lower and excluded. | final cycling duration + profile available hours + week type | No applicable week → NA; missing hours/duration → unavailable | `R19_HOURS_EXCEEDED` |
| R20 | ACTIVE / CRITICAL | No generated cycling or strength training occurs on an athlete-declared off day; rest/day-off is allowed. Locked athlete-fixed activity remains visible and triggers review rather than being erased. | final sessions/date + profile preferred off days | No declared off day → NA; invalid day/date → unavailable | `R20_OFF_DAY_VIOLATION` |
| R21 | ACTIVE / CRITICAL | Every native session resolves to a PASS manifest row; every non-native origin resolves to a registered Appendix 4.4 producer/template version. Display-name substring matching is prohibited. | final origin/provenance + manifest pin + origin registry digest | Only canonical rest/athlete-fixed → NA; unresolved identity → unavailable/fail | `R21_WORKOUT_EXISTS` |
| R22 | DEFERRED / WARNING | Compare total hours and percent time above threshold to previous block; both may not increase simultaneously. | Required future previous-block state + zone-duration data | Always `NOT_APPLICABLE` in r3 because both inputs are absent; never unavailable/pass | `R22_DUAL_ESCALATION` |
| R23 | ACTIVE / WARNING | Second applicable load week canonical planned cycling TSS must be ≥ first. No 5% hidden tolerance. | final session `tss` grouped by load week | <2 load weeks → NA; missing TSS/week type → unavailable | `R23_PROGRESSIVE_OVERLOAD` |
| R24 | ACTIVE / WARNING | Training age <1 year forbids native levels 5–6; age <2 forbids Uber Load weeks. | profile training age + final levels + week types | Missing training age → unavailable; no restricted level/week → PASS | `R24_TRAINING_AGE` |
| R25 | ACTIVE / WARNING | Sealed guide contains at least one explicit readiness/autoregulation decision rule describing what to reduce/swap when readiness is low; keyword alone without an action fails. | final `training_guide.html` semantic section text and digest | No guide is unavailable, not NA | `R25_READINESS_GUIDANCE` |
| R26 | ACTIVE / CRITICAL | For each week with a reported total, absolute difference between reported cycling TSS and sum of final session TSS ≤15. Race week uses min(sum including race, sum excluding race). | candidate weekly reported TSS + final session canonical planned `tss` and race flag | No reported total → unavailable; no paid weeks → NA | `R26_TSS_INTEGRITY` |

Every row owner is Matti/Gravel God. Registry changes require owner review,
version bump, full semantic parity tests, and Appendix update. Generated docs may
project this table but cannot override it.

---

## Appendix 4 — exact initial `athletes/config/archetype_ids.json`

This JSON is both the name→ID map and the explicit ordered-slot registry. E1
commits these bytes with a trailing newline; CI regenerates from the live
registry and requires equality before any retirement edit.

```json
{
  "schema_version": "archetype_ids/v1",
  "categories": {
    "VO2max": [
      {"archetype_id":"vo2max--5x3-vo2-classic","name":"5x3 VO2 Classic","status":"active","replacement_id":null},
      {"archetype_id":"vo2max--descending-vo2-pyramid","name":"Descending VO2 Pyramid","status":"active","replacement_id":null},
      {"archetype_id":"vo2max--norwegian-4x8","name":"Norwegian 4x8","status":"active","replacement_id":null},
      {"archetype_id":"vo2max--vo2max-with-loaded-recovery","name":"VO2max with Loaded Recovery","status":"active","replacement_id":null},
      {"archetype_id":"vo2max--vo2max-30-30","name":"VO2max 30/30","status":"active","replacement_id":null},
      {"archetype_id":"vo2max--vo2max-40-20","name":"VO2max 40/20","status":"active","replacement_id":null},
      {"archetype_id":"vo2max--vo2max-extended","name":"VO2max Extended","status":"active","replacement_id":null},
      {"archetype_id":"vo2max--ronnestad-30-15","name":"Ronnestad 30/15","status":"active","replacement_id":null},
      {"archetype_id":"vo2max--ronnestad-40-20","name":"Ronnestad 40/20","status":"active","replacement_id":null},
      {"archetype_id":"vo2max--float-sets","name":"Float Sets","status":"active","replacement_id":null}
    ],
    "TT_Threshold": [
      {"archetype_id":"tt-threshold--single-sustained-threshold","name":"Single Sustained Threshold","status":"active","replacement_id":null},
      {"archetype_id":"tt-threshold--threshold-ramps","name":"Threshold Ramps","status":"active","replacement_id":null},
      {"archetype_id":"tt-threshold--descending-threshold","name":"Descending Threshold","status":"active","replacement_id":null},
      {"archetype_id":"tt-threshold--threshold-accumulation","name":"Threshold Accumulation","status":"active","replacement_id":null},
      {"archetype_id":"tt-threshold--threshold-touch","name":"Threshold Touch","status":"active","replacement_id":null},
      {"archetype_id":"tt-threshold--criss-cross-intervals","name":"Criss-Cross Intervals","status":"active","replacement_id":null},
      {"archetype_id":"tt-threshold--tte-extension","name":"TTE Extension","status":"active","replacement_id":null},
      {"archetype_id":"tt-threshold--bpa-best-possible-average","name":"BPA (Best Possible Average)","status":"active","replacement_id":null}
    ],
    "Sprint_Neuromuscular": [
      {"archetype_id":"sprint-neuromuscular--attack-repeats","name":"Attack Repeats","status":"active","replacement_id":null},
      {"archetype_id":"sprint-neuromuscular--sprint-buildups","name":"Sprint Buildups","status":"active","replacement_id":null},
      {"archetype_id":"sprint-neuromuscular--peak-and-fade","name":"Peak and Fade","status":"active","replacement_id":null},
      {"archetype_id":"sprint-neuromuscular--ilt-single-leg-training","name":"ILT Single Leg Training","status":"active","replacement_id":null},
      {"archetype_id":"sprint-neuromuscular--stomps","name":"Stomps","status":"active","replacement_id":null},
      {"archetype_id":"sprint-neuromuscular--burst-intervals","name":"Burst Intervals","status":"active","replacement_id":null}
    ],
    "Anaerobic_Capacity": [
      {"archetype_id":"anaerobic-capacity--2min-killers","name":"2min Killers","status":"active","replacement_id":null},
      {"archetype_id":"anaerobic-capacity--90sec-repeats","name":"90sec Repeats","status":"active","replacement_id":null},
      {"archetype_id":"anaerobic-capacity--1min-all-out-repeats","name":"1min All-Out Repeats","status":"active","replacement_id":null}
    ],
    "Durability": [
      {"archetype_id":"durability--tired-vo2max","name":"Tired VO2max","status":"active","replacement_id":null},
      {"archetype_id":"durability--double-day-simulation","name":"Double Day Simulation","status":"active","replacement_id":null},
      {"archetype_id":"durability--progressive-fatigue-threshold","name":"Progressive Fatigue Threshold","status":"active","replacement_id":null},
      {"archetype_id":"durability--vo2-bookend","name":"VO2 Bookend","status":"active","replacement_id":null},
      {"archetype_id":"durability--buffer-workout","name":"Buffer Workout","status":"active","replacement_id":null},
      {"archetype_id":"durability--tired-30-30s","name":"Tired 30/30s","status":"active","replacement_id":null},
      {"archetype_id":"durability--tired-40-20s","name":"Tired 40/20s","status":"active","replacement_id":null},
      {"archetype_id":"durability--tired-threshold","name":"Tired Threshold","status":"active","replacement_id":null},
      {"archetype_id":"durability--tired-threshold-repeats","name":"Tired Threshold Repeats","status":"active","replacement_id":null},
      {"archetype_id":"durability--g-spot-into-threshold","name":"G-Spot into Threshold","status":"active","replacement_id":null},
      {"archetype_id":"durability--tempo-into-threshold","name":"Tempo into Threshold","status":"active","replacement_id":null},
      {"archetype_id":"durability--full-simulation-combo","name":"Full Simulation Combo","status":"active","replacement_id":null},
      {"archetype_id":"durability--late-race-vo2max","name":"Late-Race VO2max","status":"active","replacement_id":null}
    ],
    "Endurance": [
      {"archetype_id":"endurance--pre-race-openers","name":"Pre-Race Openers","status":"active","replacement_id":null},
      {"archetype_id":"endurance--terrain-simulation-z2","name":"Terrain Simulation Z2","status":"active","replacement_id":null},
      {"archetype_id":"endurance--endurance-with-surges","name":"Endurance with Surges","status":"active","replacement_id":null},
      {"archetype_id":"endurance--endurance-blocks","name":"Endurance Blocks","status":"active","replacement_id":null},
      {"archetype_id":"endurance--heat-acclimation-protocol","name":"Heat Acclimation Protocol","status":"active","replacement_id":null}
    ],
    "Race_Simulation": [
      {"archetype_id":"race-simulation--breakaway-simulation","name":"Breakaway Simulation","status":"active","replacement_id":null},
      {"archetype_id":"race-simulation--variable-pace-chaos","name":"Variable Pace Chaos","status":"active","replacement_id":null},
      {"archetype_id":"race-simulation--sector-simulation","name":"Sector Simulation","status":"active","replacement_id":null},
      {"archetype_id":"race-simulation--race-simulation","name":"Race Simulation","status":"active","replacement_id":null},
      {"archetype_id":"race-simulation--hard-starts","name":"Hard Starts","status":"active","replacement_id":null},
      {"archetype_id":"race-simulation--structured-fartlek","name":"Structured Fartlek","status":"active","replacement_id":null},
      {"archetype_id":"race-simulation--attacks-and-repeatability","name":"Attacks and Repeatability","status":"active","replacement_id":null},
      {"archetype_id":"race-simulation--kitchen-sink-all-systems","name":"Kitchen Sink All-Systems","status":"active","replacement_id":null}
    ],
    "G_Spot": [
      {"archetype_id":"g-spot--g-spot-intervals","name":"G-Spot Intervals","status":"active","replacement_id":null},
      {"archetype_id":"g-spot--g-spot-criss-cross","name":"G-Spot Criss-Cross","status":"active","replacement_id":null},
      {"archetype_id":"g-spot--g-spot-progressive","name":"G-Spot Progressive","status":"active","replacement_id":null}
    ],
    "LT1_MAF": [
      {"archetype_id":"lt1-maf--lt1-capped-endurance","name":"LT1 Capped Endurance","status":"active","replacement_id":null},
      {"archetype_id":"lt1-maf--maf-test-protocol","name":"MAF Test Protocol","status":"active","replacement_id":null}
    ],
    "Critical_Power": [
      {"archetype_id":"critical-power--above-cp-repeats","name":"Above CP Repeats","status":"active","replacement_id":null},
      {"archetype_id":"critical-power--w-prime-depletion","name":"W-Prime Depletion","status":"active","replacement_id":null}
    ],
    "Norwegian_Double": [
      {"archetype_id":"norwegian-double--norwegian-4x8-classic","name":"Norwegian 4x8 Classic","status":"active","replacement_id":null},
      {"archetype_id":"norwegian-double--norwegian-double-am","name":"Norwegian Double AM","status":"active","replacement_id":null},
      {"archetype_id":"norwegian-double--norwegian-double-pm","name":"Norwegian Double PM","status":"active","replacement_id":null}
    ],
    "HVLI_Extended": [
      {"archetype_id":"hvli-extended--hvli-extended-z2","name":"HVLI Extended Z2","status":"active","replacement_id":null},
      {"archetype_id":"hvli-extended--hvli-terrain-simulation","name":"HVLI Terrain Simulation","status":"active","replacement_id":null}
    ],
    "Testing": [
      {"archetype_id":"testing--ftp-ramp-test","name":"FTP Ramp Test","status":"active","replacement_id":null},
      {"archetype_id":"testing--20min-ftp-test","name":"20min FTP Test","status":"active","replacement_id":null},
      {"archetype_id":"testing--cp-test-protocol","name":"CP Test Protocol","status":"active","replacement_id":null}
    ],
    "Recovery": [
      {"archetype_id":"recovery--active-recovery-spin","name":"Active Recovery Spin","status":"active","replacement_id":null},
      {"archetype_id":"recovery--rest-day","name":"Rest Day","status":"active","replacement_id":null}
    ],
    "INSCYD": [
      {"archetype_id":"inscyd--vlamax-reduction","name":"VLamax Reduction","status":"active","replacement_id":null},
      {"archetype_id":"inscyd--fatmax-development","name":"FatMax Development","status":"active","replacement_id":null},
      {"archetype_id":"inscyd--fatmax-vlamax-suppression","name":"FatMax VLamax Suppression","status":"active","replacement_id":null},
      {"archetype_id":"inscyd--glycolytic-power","name":"Glycolytic Power","status":"active","replacement_id":null}
    ],
    "Gravel_Specific": [
      {"archetype_id":"gravel-specific--surge-and-settle","name":"Surge and Settle","status":"active","replacement_id":null},
      {"archetype_id":"gravel-specific--terrain-microbursts","name":"Terrain Microbursts","status":"active","replacement_id":null},
      {"archetype_id":"gravel-specific--gravel-grind","name":"Gravel Grind","status":"active","replacement_id":null},
      {"archetype_id":"gravel-specific--late-race-surge-protocol","name":"Late Race Surge Protocol","status":"active","replacement_id":null},
      {"archetype_id":"gravel-specific--gravel-race-simulation","name":"Gravel Race Simulation","status":"active","replacement_id":null}
    ],
    "SFR_Muscle_Force": [
      {"archetype_id":"sfr-muscle-force--5x4-sfr","name":"5x4 SFR","status":"active","replacement_id":null},
      {"archetype_id":"sfr-muscle-force--sfr-cadence-contrast","name":"SFR Cadence Contrast","status":"active","replacement_id":null}
    ],
    "Over_Under": [
      {"archetype_id":"over-under--climbing-over-under","name":"Climbing Over/Under","status":"active","replacement_id":null},
      {"archetype_id":"over-under--overunder-threshold","name":"OverUnder Threshold","status":"active","replacement_id":null}
    ],
    "Mixed_Climbing": [
      {"archetype_id":"mixed-climbing--mixed-climbing","name":"Mixed Climbing","status":"active","replacement_id":null},
      {"archetype_id":"mixed-climbing--mixed-climbing-variations","name":"Mixed Climbing Variations","status":"active","replacement_id":null}
    ],
    "Cadence_Work": [
      {"archetype_id":"cadence-work--high-cadence-intervals","name":"High Cadence Intervals","status":"active","replacement_id":null}
    ],
    "Blended": [
      {"archetype_id":"blended--blended-30-30-sfr","name":"Blended 30/30 + SFR","status":"active","replacement_id":null},
      {"archetype_id":"blended--blended-vo2-g-spot","name":"Blended VO2 + G-Spot","status":"active","replacement_id":null},
      {"archetype_id":"blended--blended-endurance-threshold-sprints","name":"Blended Endurance/Threshold/Sprints","status":"active","replacement_id":null}
    ],
    "Tempo": [
      {"archetype_id":"tempo--tempo-accelerations","name":"Tempo Accelerations","status":"active","replacement_id":null},
      {"archetype_id":"tempo--tempo-sprints","name":"Tempo Sprints","status":"active","replacement_id":null},
      {"archetype_id":"tempo--3x15-tempo","name":"3x15 Tempo","status":"active","replacement_id":null},
      {"archetype_id":"tempo--bookend-tempo","name":"Bookend Tempo","status":"active","replacement_id":null},
      {"archetype_id":"tempo--tempo-lift","name":"Tempo Lift","status":"active","replacement_id":null},
      {"archetype_id":"tempo--tired-tempo","name":"Tired Tempo","status":"active","replacement_id":null}
    ],
    "Kitchen_Sink": [
      {"archetype_id":"kitchen-sink--drain-cleaner","name":"Drain Cleaner","status":"active","replacement_id":null},
      {"archetype_id":"kitchen-sink--la-balanguera","name":"La Balanguera","status":"active","replacement_id":null},
      {"archetype_id":"kitchen-sink--hyttevask","name":"Hyttevask","status":"active","replacement_id":null}
    ],
    "SFR_Series": [
      {"archetype_id":"sfr-series--thunder-quads","name":"Thunder Quads","status":"active","replacement_id":null},
      {"archetype_id":"sfr-series--blood-pistons","name":"Blood Pistons","status":"active","replacement_id":null}
    ]
  }
}
```
