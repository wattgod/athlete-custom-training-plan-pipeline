# SPEC: Earned Selection — workout quality and selection as verified claims

Status: DRAFT r4 — resolves R1 blockers 1–19, R2 blockers R2-01–R2-14,
and R3 blockers R3-01–R3-08.
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
| Endure Labs stock library | Separate repository | Its own schema/content validator (`endurelabs/scripts/validate-stock-workouts.ts:27-108`). No validation inheritance is claimed. |

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

- **W′bal reference diagnostic:** let `dt = 1 s`, `CP = FTP/0.96`, initial
  `bal_0 = W′`, and `nadir_0 = W′`. For each prescribed power sample `p_i` in
  order, use the complete recurrence below, then set
  `nadir_i = min(nadir_(i-1), bal_i)`:

  ```
  if p_i > CP:
      bal_i = bal_(i-1) - (p_i - CP) * dt
  else:
      tau_i = tau_a * exp(-tau_c * (CP - p_i)) + tau_b
      bal_i = bal_(i-1) + (W′ - bal_(i-1)) * (1 - exp(-dt / tau_i))
  ```

  Constants are exactly `tau_a = 546.0 s`, `tau_b = 316.0 s`,
  `tau_c = 0.01 W^-1`, reference `FTP = 250 W`, and reference `W′ = 20,000 J`;
  output is `min(nadir_i)/1000` kJ with no intermediate rounding. This is the
  sibling implementation’s differential form
  (`gravel-god-training-plans/engine/physiology.py:69-84`). It is a
  deterministic design diagnostic, never an athlete reserve or safety claim.
  FreeRide seconds do not enter the recurrence. Invalid/non-power samples make
  this diagnostic `UNAVAILABLE`. Calibration also renders the sensitivity grid
  FTP ∈ `{200,250,300}` and W′ ∈ `{15,20,25}` kJ.

  Numeric goldens, all with the reference constants and binary64 arithmetic:

  | Prescribed trace | final `bal` | nadir |
  |---|---:|---:|
  | 60 s at 250 W | 20.000000000000 kJ | 20.000000000000 kJ |
  | 60 s at 300 W | 17.625000000000 kJ | 17.625000000000 kJ |
  | 60 s at 300 W, then 60 s at 150 W | 17.895093337774 kJ | 17.625000000000 kJ |
  | 600 s at 300 W | -3.750000000000 kJ | -3.750000000000 kJ |

  For the third golden, `tau(150 W) = 496.991905465051 s`. Implementations MUST
  compare these values within `1e-9 kJ`; stored manifest values remain unrounded.
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
never effective blockers in either mode. “Complete observed coverage” means
that every applicable gate was evaluated and recorded as observed `PASS`,
`FAIL`, `NOT_APPLICABLE`, or `UNAVAILABLE`; a missing result is never complete.

- **Q0 — invisible rigor:** every surface in §6 is unchanged through E1.
- **Q1 — final prescribed dose:** in Mode B/E3, every final power-, HR-, or
  RPE-prescribed non-assessment cycling session has an applicable calibrated
  purpose gate with effective `PASS`; mismatch is non-waivable. In Mode A/E1–E2,
  every applicable final session instead requires complete observed coverage,
  with every observed result effective `NOT_ENFORCED`. Free-only,
  `is_assessment: true`, and external-fixed sessions use their explicit
  non-dose contracts.
- **Q2 — native library certification:** in Mode B/E3, a selected native
  archetype row must be effective `PASS` in the revision-pinned manifest
  independently of its final instance verdict. In Mode A/E1–E2, all 600 rows
  require complete observed coverage and effective `NOT_ENFORCED`. A manifest
  PASS never exempts transformed segments.
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

Appendix 5 is the complete initial `purpose_registry/v1`; Appendix 6 is the
complete initial `quality_gates/v1`. Implementations write their exact semantic
content to `athletes/config/purpose_registry.yaml` and
`athletes/config/quality_gates.yaml`. Every initial purpose assignment and every
threshold, including both Q3 epsilons, begins as `hypothesis`. Required gate
fields are `gate_id`, `gate_version`, `purpose_subtype`, `metric`, `operator`,
`threshold`, `unit`, `applicability`, `aggregation`, `evidence_basis`,
`owner_id`, `status`, and `effective_from`. `status` is exactly `hypothesis` or
`calibrated`.

Every gate result stores separate `observed_verdict` and `effective_verdict`:

| Registry status | Observed verdict | Effective verdict in Mode A | Effective verdict in Mode B |
|---|---|---|---|
| `hypothesis` | `PASS`, `FAIL`, `NOT_APPLICABLE`, or `UNAVAILABLE` | `NOT_ENFORCED` for every observed value | `NOT_ENFORCED` for every observed value; hypotheses never enforce |
| `calibrated` | same observed set | `NOT_ENFORCED` for every observed value | observed verdict |

Mode A may therefore expose observed failures as quality findings without
authorizing a new blocker. A purpose assignment is enforcing only when both its
assignment and applicable gate are calibrated; otherwise its effective verdict
is `NOT_ENFORCED`. A status edit alone MUST NOT promote a purpose assignment or
gate. CI permits
`status: calibrated` only when a valid `quality_gate_promotion/v1` artifact from
Appendix 2 is present, its gate/version match, its reviewed row set covers every
applicable production row, all dispositions are digest-bound, and its owner is
the configured owner. Purpose promotion likewise requires the Appendix 2
`purpose_registry_promotion/v1`, covering all 600 exact row assignments. The
full artifacts and their canonical digests are included in the certification
manifest.

Calibration occurs during E2 and requires the full 600-row render, owner
signature over the purpose registry, owner dispositions (`fix`,
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
`quality_finding/v1` warnings, never blockers in r4, and are promotable only by a
later reviewed gate-version change.

Progression fixtures include flat, rounded-flat, mixed-direction, one-transition
failure, duration-led progression, pure-free exemption, mixed FreeRide scoring,
cap plateau, cap regression, and missing-dose series rows.

### 4.2 Main-set boundary

Every native purpose contract carries one Appendix 5 `main_set_rule`. During E1
the renderer assigns immutable segment IDs before projection and applies that
rule to materialize `main_set_segment_ids`. The rule, its selected IDs, and the
rendered segment provenance are stored in the manifest; runtime never re-infers
the boundary by position or title. Warmup, cooldown, primers, hard starts,
finishers, and assessment efforts are included only when the published rule
selects their source role. T@VO2max is computed only over listed prescribed
samples. A missing/duplicate segment ID or a rule selecting no segment where its
contract requires one is `UNAVAILABLE`. Bands remain per rep-geometry subtype
and enter through §3.

### 4.3 FreeRide contract

Free seconds never receive assumed power. Race-day and assessment free efforts
are checked for identity, declared duration, intended structure, and truthful
`free` targets. Mixed workouts receive the prescribed-portion calculation in
§1.2 and `has_free_segments: true`. Pure-free workouts receive the exact
`NOT_APPLICABLE` sentinel. Legacy 55%/65% preview estimates remain canonical
planned/display estimates only and MUST NOT enter `design_*`, W′bal, T@VO2max,
or a gate.

### 4.4 Exhaustive workout-origin union and final-instance gate

Origin is classified **only by the emitting producer**, stored in the naming
manifest and candidate, and never inferred from title, purpose, or content.
Producer branches are mutually exclusive by construction: exactly one branch
creates a session record and writes exactly one discriminant before any common
projection code runs. Assessment is not an origin. `is_assessment` is an
orthogonal required boolean on every session; the producer sets it from an
explicit template/archetype contract, never from display text. Any origin may
carry `is_assessment: true`, and assessment semantics—identity/structure checks,
no purpose-dose gate, and no W′bal/T@VO2max gate on the self-paced effort—key
only from that attribute. Every session has exactly one of these closed producer
discriminants:

| Discriminant | Reachable producer | Required contract |
|---|---|---|
| `NATIVE_ARCHETYPE` | Block-builder mapper → Nate render | Immutable `archetype_id` + level must PASS pinned manifest; final prescribed segments independently pass purpose gate unless `is_assessment`. |
| `MAPPER_SIMPLE_ENDURANCE` | `workout_mapper._render_simple_endurance` (`athletes/scripts/workout_mapper.py:208-215,256-313`) | Versioned renderer/source digest + final `endurance` gate; no native-row fiction. |
| `LEGACY_NATE_ARCHETYPE` | Direct legacy `generate_nate_zwo` (`athletes/scripts/generate_athlete_package.py:2693-2787`) | Resolve and record selected immutable ID before render, then the same two-part native gate. A missing identity is not tolerated. |
| `PROGRESSIVE_INTERVAL_GENERATOR` | `generate_progressive_interval_blocks` (`athletes/scripts/generate_athlete_package.py:2792-2802`) | Generator/source digest, `threshold` or `vo2max/<geometry>` purpose from returned template ID, final purpose gate. |
| `PROGRESSIVE_ENDURANCE_GENERATOR` | `generate_progressive_endurance_blocks` (`athletes/scripts/generate_athlete_package.py:2803-2809`) | Generator/source digest and final `endurance` gate. |
| `STANDARD_BLOCK_GENERATOR` | `create_workout_blocks`, including B-race opener/easy overlays (`athletes/scripts/generate_athlete_package.py:1237-1553,2333-2439,2810-2855`) | Versioned template ID, overlay parameters, source digest, and final gate for its explicit purpose. `FTP_Test` sets `is_assessment: true`; the training template `Anaerobic` does not. |
| `PRE_PLAN_GENERATOR` | W00 easy/rest emitter (`athletes/scripts/generate_athlete_package.py:1900-1974`) | Exact `pre_plan_easy` or `pre_plan_rest` tuple; the easy variant records the nested standard-block body, while the outer origin remains producer-only. |
| `REST_SENTINEL_ZWO` | Bespoke one-segment, 60-second 30% Rest ZWO (`athletes/scripts/generate_athlete_package.py:2442-2482`) | Exact rest-sentinel structure/duration target plus truthful rest identity; `design_*` recorded but no Q3/library pin. |
| `A_RACE_FREERIDE` | Bespoke A-race ZWO (`athletes/scripts/generate_athlete_package.py:2569-2665`) | Pure-free race identity, declared duration, race priority A; dose `NOT_APPLICABLE`. |
| `B_RACE_FREERIDE` | Bespoke B-race ZWO (`athletes/scripts/generate_athlete_package.py:2024-2082`) | Pure-free race identity, declared duration, race priority B; dose `NOT_APPLICABLE`. |
| `TRAVEL_SHAKEOUT` | Bespoke travel renderer (`athletes/scripts/generate_athlete_package.py:2084-2128`) | Versioned template/source digest and final recovery/endurance gate. |
| `ATHLETE_FIXED` | Locked recurring cycling session materialized by canonical builder | Athlete-reported title, duration and planned TSS sanity; no invented segments; dose `NOT_APPLICABLE`. Phase 3 creates this origin at `build/trustworthy-phase3:athletes/scripts/canonical_training_model.py:333-351`. |
| `CANONICAL_REST` | Calendar day with no emitted ZWO | Exact zero duration/TSS, no segments, day-off TP kind; dose `NOT_APPLICABLE` (`build/trustworthy-phase3:athletes/scripts/plan_ir.py:467-481`). |
| `STRENGTH_TEMPLATE` | Strength ZWO/template path | Outside cycling dose; enters R11–R13 and retains template provenance. |

Anything else emits `WORKOUT_ORIGIN_UNKNOWN`, a non-waivable blocker. A known
branch MUST NOT deliberately route to unknown; that is an order-killer, not a
completed union.

Appendix 7 is the complete `FinalPlanCandidate/v1` consumed by all checks.
Appendix 8 is the exact non-native producer/template registry consumed by R21.
An emitter must resolve its `(origin, producer_id, producer_version,
template_id, template_version)` tuple there before D1; an unregistered tuple is
not recoverable through title matching.

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

#### 4.4.1 Internal fueling classification

`FinalPlanCandidate/v1` and `workout_quality_report/v1` carry the internal enum
`fueling_class = HIGH | LONG_RIDE | RACE | NONE` on every cycling session. It is
not athlete copy. E1 derives it from the existing fueling-policy tier selected
by `_get_fuel_tag_for_type`; that producer selects `race_sim`, `quality`, or
`long_ride`, and deliberately returns an empty string for recovery/easy/
shakeout/rest/openers and endurance shorter than 90 minutes
(`athletes/scripts/generate_athlete_package.py:188-229`). The existing renderer
labels those three tiers `RACE FUEL`, `HIGH FUEL`, and `LONG-RIDE FUEL`
(`athletes/scripts/fueling_policy.py:189-204`). The closed mapping is:

| Existing producer state | Internal class |
|---|---|
| tier `quality` | `HIGH` |
| tier `long_ride` | `LONG_RIDE` |
| tier `race_sim`, or A/B race-event producer | `RACE` |
| existing empty-string case | `NONE` |

Precedence is race event → `RACE`; explicit policy tier → its row; otherwise an
enumerated empty-string case → `NONE`; no match is `UNAVAILABLE`, never guessed.
Within cycling sessions, the closed `NONE` predicate is: origin
`REST_SENTINEL_ZWO`, `TRAVEL_SHAKEOUT`, or `ATHLETE_FIXED`; tuple
`PRE_PLAN_GENERATOR/pre_plan_rest`; normalized session type
`recovery|easy|shakeout|rest|off|openers`; purpose class `recovery|openers`; or
purpose class `endurance` with final `duration_s < 5400`. No other session may
carry `NONE`. `CANONICAL_REST` is non-cycling and therefore carries the
candidate's required null class. An assessment follows its producer’s existing
tier—quality assessments such as FTP are `HIGH`, while no tier is inferred from
the assessment attribute itself.

R08 requires exactly one internal class on every cycling session and fails if
`NONE` occurs outside that closed set. R09 requires exact projection of the
candidate's frozen source tier: `quality→HIGH`, `long_ride→LONG_RIDE`,
`race_sim→RACE`, and `empty→NONE`. This preserves the existing openers empty
case even when an opener occupies a block-builder intensity slot. R10 fails `RACE`
outside race simulation/event and fails `LONG_RIDE` outside long-ride-role or
at-least-90-minute endurance. Missing/malformed class is `UNAVAILABLE`.

E1 MUST NOT add this enum to descriptions, ZWOs, `fueling.yaml`, guides, or any
other athlete surface. Existing athlete-facing fueling prose and
`fueling.yaml` remain byte-identical; only the candidate/report receive the new
field.

### 4.5 R01–R26 registry, execution, and ordering

Appendix 3 is the complete initial `rule_registry/v1`; implementation writes it
verbatim to `athletes/config/rule_registry.yaml`. It settles stage,
`blocking_since`, severity, applicability, algorithm, exact final input,
NA/unavailable behavior, and output code for every R01–R26. Its normative source
rules are verified at
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

The registry is split into `PRE_GUIDE` and `POST_GUIDE`; R07 and R25 are the only
post-guide rules. The exact order is:

1. Finish selection, day-cap fitting, overlays, all duration scaling, and every
   authored-session mutation. Assign immutable session IDs, producer-only
   origin/provenance, purpose, role, internal fueling class, and week fields.
2. Freeze the complete Appendix 7 `FinalPlanCandidate/v1` and compute **D1** as
   SHA-256 of its canonical JSON bytes. D1 includes every root/plan/week/session/
   segment/provenance field, its sorted four-entry version vector, all config and
   source digests, and guide *input* digests. It excludes the canonical model,
   emitted guide, report, catalog, apply contract, and seal. No code may mutate
   candidate training content after D1.
3. Run final-instance dose gates, the final-series warning, and every
   `PRE_GUIDE` Appendix 3 rule against the frozen candidate.
4. Finalize `canonical_training_model.json` from that same candidate and build
   its PlanIR projections. Finalization is a projection, not a candidate
   mutation.
5. Generate `training_guide.html` deterministically from the finalized canonical
   model and D1 guide inputs. The guide consumes but never changes the candidate.
   Compute **D2** as SHA-256 canonical JSON of exactly
   `{"candidate_sha256":D1,"guide_sha256":SHA256(raw emitted guide bytes),
   "guide_source_digests":<the sorted path→digest map consumed by the builder>}`.
6. Run R07 and R25 (`POST_GUIDE`) against the emitted guide bytes pinned by D2,
   then run the existing Phase 3 post-render validators. No second content
   mutation or guide generation is permitted.
7. Create one merged `workout_quality_report.json` containing pre-guide and
   post-guide results, D1, D2, and post-render results. Perform exactly one state
   merge for this report revision, then exactly one review-catalog refresh.
8. Assert the report’s ordered session IDs and content digests equal the
   canonical model’s ordered session IDs and candidate-derived content digests;
   any difference is `VALIDATOR_CRASH`. Build `apply_contract.json` from the
   finalized model and final catalog, persist revision files/bundles, and seal
   with v2. No catalog mutation is permitted after contract build.

The nine rules with real blocking behavior before this spec—R01–R06, R14, R19,
and R20—have `blocking_since: pre-existing` and keep that approval-blocking
behavior in every mode and rollout phase. This preserves the existing
compliance path, which executes all nine plus the R08/R11 no-op delegations
(`athletes/scripts/block_compliance.py:373-403`). “Blocking” here retains the
order-safety behavior: a built plan is delivered as needs-review rather than
discarded.

Every other Appendix 3 rule has `blocking_since: E3`. Through E1/E2, its FAIL,
WARNING, or unavailable result is a `quality_finding/v1` whose severity exactly
matches the registry (`critical` or `warning`); it does not enter
`blocking_issues`. At E3, a `blocking_since: E3` CRITICAL FAIL/UNAVAILABLE enters
`blocking_issues`, while WARNING results remain findings. Thus E1 adds zero new
approval blockers and remains audit-only.

A rule crash produces the existing non-waivable `VALIDATOR_CRASH` or
`POST_RENDER_VALIDATOR_CRASH`, not a pass. Missing required input for an active
CRITICAL rule produces `<OUTPUT_CODE>_UNAVAILABLE` and is routed according to
that row’s `blocking_since` and current rollout phase; a WARNING row produces a
quality finding. `NOT_APPLICABLE` is used only when the registry’s applicability
is false or its status is explicitly `DEFERRED`.

### 4.6 Closed non-waivable policy amendment

This specification normatively amends the fulfilment specification’s closed
non-waivable set. The pre-earned-selection set and remediation map being amended are verified
at `build/trustworthy-phase3:webhook/fulfillment_state.py:47-71`. The complete
set after r4 is:

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


The fulfilment `NON_WAIVABLE_RULES` is its pre-earned-selection set union this exact extension.
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
(exactly `warning` or `critical`), `subject` (object containing exactly `kind`
and `ids`),
`metric` (canonical JSON object), `basis`, `sensitivity`, `message`, and the
exact four-entry `version_vector` from Appendix 2.

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
                      "version_vector": finding.version_vector}
display_unit       = null
resolution_choices = []
```

No field is accepted from a coach. `_review_item` then supplies `item_id`,
`type`, canonical `value`, `value_type`, `revision`, and the other common
catalog keys exactly as it does for existing sources.

A `critical` quality finding is still a finding, not an approval blocker. It is
used only for a `blocking_since: E3` CRITICAL rule before E3, as §4.5 requires;
the catalog rank and automatic `observed` disposition remain unchanged.

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
    "guide_evidence_sha256": "<report.guide_evidence_sha256>",
    "version_vector": "<report.version_vector, keys in Appendix 2 order>",
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
    "version_vector": "<report.manifest_pin.version_vector, keys in Appendix 2 order>",
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
promotion artifacts, source/render digests, and the sorted version vector for
purpose registry, gate registry, scorer, and rule registry.

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
5. TrainingPeaks apply-contract projections for the complete closed kind set.
   Phase 3 defines `KINDS` as four dated kinds, two singleton kinds, and the
   entitlement kind (`build/trustworthy-phase3:athletes/scripts/apply_contract.py:
   23-31`) and defines their closed payload fields at lines 97–146. Q0 compares
   operation count/order plus `logical_id`, `kind`, `disposition`, payload null
   versus present, every payload field, and expected payload digest for each:

   | Allowed kind | Byte/field comparison |
   |---|---|
   | `workout_upsert` | `date`, `title`, `description`, `tp_workout_type`, `total_seconds`, `tss_planned`, and canonical structure bytes |
   | `calendar_note_upsert` | `date`, `title`, and exact body bytes |
   | `attachment_upsert` | parent logical ID, filename, SHA-256, bytes reference, and raw bytes for **every** generic attachment—not only the guide |
   | `mental_task_upsert` | `date`, `title`, and exact body bytes |
   | `course_entitlement_grant` | exact `product_id` |
   | `threshold_update` | `metric`, typed `after_value`, and `unit` |
   | `zone_update` | `zone_set` and canonical JSON bytes of `after_table` |

   No allowed kind is excluded. Adapter bookkeeping that is not sent to the
   athlete (`op_id`, predecessor proof, rollback strategy, remote marker, and
   provider-assigned remote ID) is excluded from the athlete-visible byte claim,
   but Q0 still compares it structurally to prove the same operation would be
   applied. Create/update/keep/delete dispositions are all covered. A fixture
   asserts exact set equality between this seven-kind inventory and
   `apply_contract.KINDS`; adding an allowed adapter kind without adding its Q0
   comparator fails E1.
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
set MIME boundaries/headers. **No semantic-only exception is approved by r4.**
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
   invalid calibrated-without-promotion; purpose/gate promotion digest/coverage/
   policy tests; exact 600-row purpose coverage and exact version-vector pins.
4. Q3 and final-series fixtures in §4.1.
5. One fixture per §4.4 producer origin plus native/standard assessments,
   producer-registry rejection, complete candidate schema/derivation coverage,
   and the complete reachability sweep.
6. Complete Appendix 3 row fixtures, including R02 exemptions; R03 block
   adjacency and four bands; R11’s state table; R12/R17 tables; R14 grammar;
   R18/R22 NA; R08–R10 integrations; R25 present/absent goldens; active-rule
   unavailable; crash; and R26 race sums.
7. State/catalog/snapshot tests in §4.8 and exact derived-report coverage.
8. Six non-waivable code negatives and complete set-equality test in §4.6.
9. Session ID round-trip, same-day doubles, missing date, duplicate week/date/
   ordinal collision, stable regeneration, and report/model ID equality.
10. Methodology malformed/unknown/missing fixtures and exhaustive ID-selection
    equivalence.
11. Dual-constructor v2 seal equality, canonical-v1 backward verification,
    transitional-v1 verification, stale global manifest, missing snapshot,
    missing pin, mismatched digest, and unknown version.
12. The complete §6 surface comparison, exact TP-kind inventory set-equality,
    athlete-m Mode A replay, and null-FTP redaction/no-power-leak checks.
13. D1 freeze/no-mutation, D2 guide binding, pre/post-guide stage order, single
    report merge/catalog refresh, session aggregate precedence, and every count
    equation in Appendix 2.

### 7.2 Rollout

- **E1 — audit-only plumbing:** commit Appendix 4 as
  `athletes/config/archetype_ids.json`; migrate selection with exhaustive byte
  equivalence; add the Appendix 5–8 registries/schema, producer-only origins,
  scorer, complete hypothesis results, manifest/report, Appendix 3,
  state/catalog/snapshot v3, and seal v2. Every applicable purpose/gate result
  must be observed with none missing and all effective `NOT_ENFORCED`. Only the
  nine pre-existing rules remain blockers; every new rule is a finding. No
  content changes and zero new approval blockers. Q0 must pass on every surface.
- **E2 — owner dispositions:** fix/re-class/retire/band-adjust the observed
  backlog. Content byte changes are allowed only here, each enumerated and
  rebaselined. The owner signs the complete purpose assignment and gate
  promotions through §3 artifacts.
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
- No automatic promotion of the final-series warning in r4.

---

## Appendix 1 — combined R1 + R2 + R3 blocker disposition map

### A1.1 R1 blockers

| R1 | r4 disposition |
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

| R2 | r4 disposition |
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

### A1.3 R3 blockers

| R3 | r4 disposition |
|---|---|
| R3-01 | §1.3, §3, Appendix 5, and Appendix 6 publish the complete provisional 600-row purpose assignment, deterministic derivation/overrides, exact initial gate registry, W′bal recurrence/goldens, and pinned version vector. |
| R3-02 | §4.4 and Appendices 7–8 make origin producer-only, make assessment orthogonal, close `FinalPlanCandidate/v1`, and publish the non-native producer/template registry. |
| R3-03 | §4.4.1 defines the closed internal fueling enum/mapping/applicability and preserves athlete fueling bytes in E1. |
| R3-04 | Appendix 3 closes R02, R03, R11, R12, R14, R17, R21, and R25 with exact sets, tables, grammars, algorithms, and goldens. |
| R3-05 | §4.5 splits pre/post-guide stages and fixes D1 → canonical model → guide/D2 → single report/catalog → seal order with no post-D1 content mutation. |
| R3-06 | §4.10 and Appendix 2 define session aggregation precedence, named collection counters/equations, and one four-entry version vector. |
| R3-07 | §6 enumerates and compares all seven apply-contract kinds and requires exact inventory set equality. |
| R3-08 | §2, §4.5, Appendix 3, and §7 scope effective PASS to Mode B, require complete Mode A observations, preserve nine existing blockers, and keep all new rules findings-only until E3. |

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

### A2.1b `purpose_registry_promotion/v1`

No extra keys are allowed. It is structurally parallel to a gate promotion but
signs the complete assignment authority rather than one threshold:

```
{
  "schema_version": "purpose_registry_promotion/v1",
  "purpose_registry_version": "purpose_registry/v1",
  "purpose_registry_digest": sha256,
  "owner": {"owner_id": string, "display_name": string},
  "reviewed_row_set": {
    "row_ids": [exactly all 600 Appendix 5 row IDs],
    "digest": sha256
  },
  "dispositions_digest": sha256,
  "false_positive_policy": string,
  "false_negative_policy": string,
  "promoted_at": ISO-8601-UTC string
}
```

`row_ids` is unique and lexicographically sorted;
`reviewed_row_set.digest` is SHA-256 canonical JSON of exactly
`{"purpose_registry_digest":...,"row_ids":[...]}`. `dispositions_digest` is
SHA-256 of the exact UTF-8 bytes of
`athletes/config/purpose_registry_dispositions.md`. Empty policies are invalid.
The promotion digest covers the entire object.

### A2.2 `certification_manifest/v1`

No extra keys are allowed at any level. Arrays are ordered as stated.

```
{
  "schema_version": "certification_manifest/v1",
  "generated_at": ISO-8601-UTC string,
  "registry_digest": sha256,
  "id_map_digest": sha256,
  "version_vector": {
    "purpose_registry_version": "purpose_registry/v1",
    "gate_registry_version": "quality_gates/v1",
    "scorer_version": "earned_selection_scorer/v1",
    "rule_registry_version": "rule_registry/v1"
  },
  "promotion_artifacts": [
    {"digest": sha256, "artifact": quality_gate_promotion/v1 | purpose_registry_promotion/v1}, ...
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
        "assignment_status": "hypothesis" | "calibrated",
        "main_set_rule": string,
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

The four `version_vector` keys MUST appear in the canonical order shown everywhere
that vector is serialized. `promotion_artifacts` sorts by `(schema_version,
gate_id-or-purpose_registry_version, gate_version-or-empty)`;
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
  "canonical_candidate_sha256": sha256,
  "guide_evidence_sha256": sha256,
  "version_vector": {
    "purpose_registry_version": "purpose_registry/v1",
    "gate_registry_version": "quality_gates/v1",
    "scorer_version": "earned_selection_scorer/v1",
    "rule_registry_version": "rule_registry/v1"
  },
  "gate_summary": {
    "counts": {
      "sessions": integer,
      "pass": integer,
      "fail": integer,
      "pass_with_observed_fail": integer,
      "not_applicable": integer,
      "unavailable": integer
    },
    "artifact_counts": {
      "quality_findings": integer,
      "rubric_blockers": integer
    },
    "gate_result_counts": {
      "manifest_gates": {
        "total": integer,
        "observed": {"PASS":integer,"FAIL":integer,"NOT_APPLICABLE":integer,"UNAVAILABLE":integer},
        "effective": {"PASS":integer,"FAIL":integer,"NOT_ENFORCED":integer,"NOT_APPLICABLE":integer,"UNAVAILABLE":integer}
      },
      "final_gates": {
        "total": integer,
        "observed": {"PASS":integer,"FAIL":integer,"NOT_APPLICABLE":integer,"UNAVAILABLE":integer},
        "effective": {"PASS":integer,"FAIL":integer,"NOT_ENFORCED":integer,"NOT_APPLICABLE":integer,"UNAVAILABLE":integer}
      },
      "rubric": {
        "total": 26,
        "results": {"PASS":integer,"FAIL":integer,"WARNING":integer,"NOT_APPLICABLE":integer,"UNAVAILABLE":integer}
      }
    },
    "sessions": [
      {
        "session_id": string,
        "week": integer,
        "date": YYYY-MM-DD string,
        "daily_ordinal": positive integer,
        "sport": string,
        "origin": "<one §4.4 discriminant>",
        "is_assessment": boolean,
        "fueling_class": "HIGH" | "LONG_RIDE" | "RACE" | "NONE" | null,
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
        "aggregate_verdict": "PASS" | "FAIL" | "PASS_WITH_OBSERVED_FAIL" | "NOT_APPLICABLE" | "UNAVAILABLE",
        "quality_finding_ids": [string, ...]
      }, ...
    ],
    "rubric": [{
      "rule_id": "R01".."R26",
      "registry_status": "ACTIVE" | "DEFERRED",
      "stage": "PRE_GUIDE" | "POST_GUIDE",
      "blocking_since": "pre-existing" | "E3",
      "severity": "CRITICAL" | "WARNING",
      "result": "PASS" | "FAIL" | "WARNING" | "NOT_APPLICABLE" | "UNAVAILABLE",
      "output_code": string,
      "subject_ids": [string, ...],
      "metric": canonical-JSON object,
      "message": string,
      "finding_id": string | null
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
    "version_vector": {
      "purpose_registry_version": "purpose_registry/v1",
      "gate_registry_version": "quality_gates/v1",
      "scorer_version": "earned_selection_scorer/v1",
      "rule_registry_version": "rule_registry/v1"
    },
    "promotion_digests": [sha256, ...]
  }
}
```

Here `verdict` is `PASS|FAIL|NOT_APPLICABLE|UNAVAILABLE` and
`effective-verdict` additionally permits `NOT_ENFORCED`. Sessions sort by
`(week,date,daily_ordinal)`; source digests by path; gates by ID; finding IDs and
promotion digests lexicographically. The same canonical-order four-entry
`version_vector` is byte-equal in the manifest, report root, report pin,
candidate, and both derived records.

For each session, aggregate the one `manifest_gate` plus every `final_gates`
entry with this exact precedence:

1. any effective `FAIL` → `FAIL`;
2. else any effective or observed `UNAVAILABLE` → `UNAVAILABLE`;
3. else any observed `FAIL` whose effective verdict is `NOT_ENFORCED` →
   `PASS_WITH_OBSERVED_FAIL`;
4. else every observed result is `NOT_APPLICABLE` → `NOT_APPLICABLE`;
5. else → `PASS`.

Every counter in `gate_summary.counts` counts **sessions**: `sessions` is the
total and each other counter is one aggregate-verdict partition. Non-session
artifact counters are deliberately separate. The required equations are:

```
counts.sessions == len(gate_summary.sessions)
counts.pass + counts.fail + counts.pass_with_observed_fail
  + counts.not_applicable + counts.unavailable == counts.sessions
artifact_counts.quality_findings == count(unique non-null IDs in
  sessions[].quality_finding_ids + rubric[].finding_id + plan_series[].finding_id)
artifact_counts.rubric_blockers == count(rubric rows routed to blocking_issues)
```

`gate_result_counts.manifest_gates` counts the named one-per-session collection;
`final_gates` counts the flattened session `final_gates` arrays; `rubric` counts
the exact 26 rule results. For each of the first two collections, observed sums
and effective sums independently equal `total`; manifest `total == sessions`.
Final-gate `total == sum(len(s.final_gates) for s in sessions)`. Rubric result
sums equal `26`. A missing evaluation cannot be hidden by a session aggregate:
the collection totals and applicable-ID coverage are validated separately.
Report canonical digest excludes no fields.

---

## Appendix 3 — normative `rule_registry/v1` and execution matrix

All ACTIVE `PRE_GUIDE` rules run at §4.5 step 3; R07/R25 run at step 6. Every
rule consumes Appendix 7’s frozen candidate, with post-guide rules additionally
consuming D2. Candidate session fields are the exact fields later serialized to
canonical model. Common NA: no applicable week/session yields
`NOT_APPLICABLE`, never PASS. Common unavailable: an ACTIVE rule’s named input
is missing/malformed. Output code is stable and uppercase.

### A3.1 Calendar vocabulary and R02/R03 block algorithm

Candidate `cycling_phase` is exactly
`transition|base|build|race_prep|maintenance|racing`. E1 maps current calendar
phases `base→base`, `build→build`, `peak→race_prep`, `maintenance→maintenance`,
`taper→racing`, `race→racing`, and W00/pre-plan→`transition`. The current
calendar emits `base|build|peak|maintenance|taper|race`
(`athletes/scripts/calculate_plan_dates.py:193-216`), while its builder adapter
already maps `peak→race_prep` (`athletes/scripts/block_chain.py:25-33`).

Candidate `week_type` is exactly
`load|testing|recovery|taper|race|medium|uber_load`. The calendar adapter emits
`load|recovery|taper|race` (`athletes/scripts/block_chain.py:36-60`), E1’s
existing week-one assessment override emits `testing`
(`athletes/scripts/generate_athlete_package.py:704-716`), and `medium` is the
existing closed block-note/scorer value (`athletes/config/block_notes.yaml:
17-25`); `uber_load` is the other registered non-calendar note value at
`athletes/config/block_notes.yaml:52-61` and is not R02-exempt. Unknown
phase/week values are `UNAVAILABLE`.

R02’s complete exemption predicate is:

```
cycling_phase in {transition, racing}
or week_type in {taper, race, medium}
```

No “off-season” alias or other implicit exemption exists. `recovery` pauses the
calendar-day counter but is not itself an exempt endpoint. `testing` is
trainable and an assessment with VO2-character prescribed setup may count only
when its purpose contract explicitly contains `vo2max` character.

For R03, parse the configured `meso_pattern` with the same
`load_weeks,recovery_weeks` grammar used by calendar recovery marking; its cycle
length is their sum and calendar position is `(week_number-1) % cycle_length`
(`athletes/scripts/calculate_plan_dates.py:245-268`). Iterate paid weeks in
ascending week number. Start a new `meso_block_id` at week 1, after a completed
cycle, or when `cycling_phase` changes; the latter matches the builder’s
phase-transition block close (`athletes/scripts/block_chain.py:137-152`). Within
one block, a recovery week is adjacent to every earlier exact
`week_type=load` position in that same block. A testing or uber-load position is
not included in the mean but does not create a new block; a phase boundary or
completed meso cycle does. Taper/race/medium cannot be an R03 recovery target.
The exact ratio is:

```
recovery_week.reported_cycling_tss
  / mean(w.reported_cycling_tss for w in same_meso_block_load_weeks)
```

Both numerator and denominator use the candidate’s `reported_cycling_tss`
(materialized from the block-builder `total_tss`, whose emitted field is at
`athletes/scripts/block_builder.py:555-561`), never recomputed final-session TSS
and never `design_tss`. Empty same-block load set → `NOT_APPLICABLE`; missing/non-finite value or
mean `<=0` → `UNAVAILABLE`. Bands are `<0.50 FAIL`, `0.50..0.65 PASS`,
`>0.65..0.75 WARNING`, `>0.75 FAIL`, inclusive exactly as written.

### A3.2 R11/R12 strength tables

R11 evaluates each paid week with this complete state table:

| Weekly-structure state | Strength artifact state | Verdict |
|---|---|---|
| explicit athlete-declined-strength disposition | absent | `NOT_APPLICABLE` |
| explicit decline | present | `UNAVAILABLE` (contradictory authority) |
| valid and prescribes strength | present and schema-valid | `PASS` after protocol/frequency completeness check; mismatch is `FAIL` |
| valid and prescribes strength | absent | `FAIL` |
| valid and does not prescribe strength | absent | `NOT_APPLICABLE` |
| valid and does not prescribe strength | present and schema-valid | `PASS` (R12/R13 judge alignment/scheduling) |
| missing/malformed weekly structure or malformed strength artifact | any | `UNAVAILABLE` |

“Schema-valid” means non-empty phase, protocol, frequency, intensity class, and
registered template/version, with emitted count equal to the prescribed weekly
frequency. `weekly_structure.yaml` exposes AM/PM strength slots in its day map
(`athletes/scripts/build_weekly_structure.py:58-148`); E1 materializes the
week-specific prescription and any explicit decline in Appendix 7.

R12 first applies the recovery override, then this complete mapping:

| Candidate cycling state | Required strength phase | Intensity/frequency contract |
|---|---|---|
| any `week_type=recovery` | `deload` | bodyweight/mobility, no loaded work, 1×/week |
| `transition` | `deload` | bodyweight/mobility, 0–1×/week |
| `base`, first meso block | `AA` | 50–60% 1RM, 2–3×/week |
| `base`, subsequent meso block | `max_strength` | 65–85% 1RM, 2–3×/week |
| `build` | `maintenance` | about 75% 1RM, 2×/week |
| `maintenance` | `maintenance` | 70–75% 1RM, 1–2×/week |
| `race_prep` (calendar `peak`) | `maintenance_reduced` | key lifts, 70–75% 1RM, 1–2×/week |
| `racing` (calendar `taper` or `race`) | `key_lifts` | 65–70% 1RM, at most 1×/week |

This adapts the source phase table’s base AA→max-strength, build maintenance,
race-prep reduced maintenance, racing key-lifts, and recovery deload contract
(`gravel-god-training-engine/docs/block-builder-strength.md:5-20,42-56`) to the
pipeline vocabulary: calendar `peak` is `race_prep`, while calendar `taper` and
`race` are `racing`. Unknown phase/template/intensity is `UNAVAILABLE`; a known
mismatch is `FAIL`.

### A3.3 R14 normalization grammar

Normalize a series display name by the following exact transform. Set
`s = unicodedata.normalize("NFKC", raw).casefold()`. Replace a character with
ASCII space iff it is `_` or `unicodedata.category(character) == "Pd"` (the
complete Unicode dash-punctuation category). Then remove every standalone level token
matching `(?i)(?<![a-z0-9])(?:level|lvl|l)\s*0*[1-6](?![a-z0-9])`; repeatedly
remove a trailing series suffix matching
`(?i)\s+(?:#\s*)?\d+(?:\s+(?:of|/)\s+\d+)?\s*$` or
`(?i)\s*\(\s*\d+\s*(?:of|/)\s*\d+\s*\)\s*$`; replace remaining
`[^a-z0-9]+` with one space; trim. Each removal substitutes one ASCII space;
the suffix loop stops only when neither regex changes `s`. Intrinsic numbers without a preceding space
(for example `5x3`, `30/30`, `4x8`) survive.

After that transform, the exact Kitchen-Sink immutable-ID equivalence set
`{race-simulation--kitchen-sink-all-systems,
kitchen-sink--drain-cleaner, kitchen-sink--la-balanguera,
kitchen-sink--hyttevask}` returns the literal family key `kitchen sink`. The
complete accepted raw display aliases are `Kitchen Sink All-Systems`,
`Kitchen Sink - Drain Cleaner`, `Drain Cleaner`, `La Balanguera`,
`La Balanguera 1`, `La Balanguera 2`, `La Balanguera 3`, `Hyttevask`,
`Hyttevask 1`, `Hyttevask 2`, and `Hyttevask 3`; the current family list is at
`athletes/scripts/series_tracker.py:18-35`. No other title joins the family.
Examples: `Thunder Quads L2 (2 of 3)→thunder quads`; `VO2max 30/30 Level 4
→vo2max 30 30`; `Drain Cleaner 2→kitchen sink`; `5x3 VO2 Classic L3→5x3 vo2
classic`. Outside the published Kitchen-Sink set, both family key and immutable
archetype ID must remain constant. Inside that one set, any listed ID/title may
follow another and the family key is the coherence identity. A tombstone
replacement resolved before series start is the only other cross-ID allowance;
mere normalized-name equality never authorizes one.

### A3.4 R17 phase-purpose table and inclusion algorithm

The base allowed set is selected by `cycling_phase`, then a week-type override
replaces it when present:

| State | Allowed purpose classes | Required inclusion for each applicable paid week |
|---|---|---|
| `transition` | `free,recovery,endurance` | at least one `recovery|endurance`, unless every day is rest |
| `base` | `free,recovery,endurance,threshold,vo2max,wprime_drain,openers,assessment` | at least one `endurance` and one of `threshold|vo2max|wprime_drain` |
| `build` | `free,recovery,endurance,threshold,vo2max,wprime_drain,mixed,openers,assessment` | at least one of `threshold|vo2max` |
| `maintenance` | `free,recovery,endurance,threshold,vo2max,openers,assessment` | at least one of `threshold|vo2max|openers` |
| `race_prep` | `free,recovery,endurance,threshold,vo2max,wprime_drain,mixed,race_sim,openers,assessment` | at least one of `race_sim|vo2max|threshold` |
| `racing` | `free,recovery,endurance,threshold,race_sim,openers,assessment` | at least one of `race_sim|openers|threshold` |
| `week_type=recovery` override | `free,recovery,endurance,openers` | at least one `recovery|endurance`; R04 separately constrains intensity |
| `week_type=testing` override | `free,recovery,endurance,assessment` | at least one `assessment` |
| `week_type=taper` override | `free,recovery,endurance,openers` | at least one `openers` |
| `week_type=race` override | `free,recovery,endurance,openers,race_sim,assessment` | exactly one race-event session with `fueling_class=RACE` |
| `week_type=medium` override | phase allowed set | no inclusion minimum; class allow-list still enforced |
| `week_type=uber_load` override | phase allowed set | retain the selected phase row's inclusion minimum |

Algorithm: group cycling sessions by candidate week; ignore canonical rest and
`ATHLETE_FIXED` only for the inclusion minimum (their classes must still be
allowed); fail once for every disallowed class and once for a missing required
inclusion. In `race_prep`, subtypes rooted `threshold/sfr`,
`threshold/cadence`, or `endurance/cadence` are base-only and disallowed even
though their class appears in the set. Missing phase, purpose, or registry digest
is `UNAVAILABLE`; a week with no applicable generated cycling session is
`NOT_APPLICABLE` except race/testing weeks, where absence is `FAIL`.

### A3.5 R25 deterministic marker grammar

For each paid week, select the exact block-note template named by its week type,
then inspect the emitted guide’s corresponding Monday note text. Normalize both
with NFKC, case-fold, and collapse `\s+` to one space. PASS only if emitted text
contains at least one of these complete normalized markers, the closed action
phrases actually present in `block_notes.yaml`:

```
don't be afraid to shorten workouts
if anything feels wrong (sharp pain, illness), stop immediately
```

The source phrases are at `athletes/config/block_notes.yaml:27-37,52-61`.
There is no keyword expansion, stemming, fuzzy matching, semantic parser, or
LLM. A well-formed note with no marker is `FAIL`; absent/malformed guide or
config is `UNAVAILABLE`. Present golden: the recovery template containing
“Don't be afraid to shorten workouts” → PASS. Absent golden: the load template
with only “Prioritize sleep (8+ hours)” → FAIL. Initial load/medium/race notes
therefore honestly produce observed findings until their E2 disposition; the
rule does not invent guidance.

| ID | Stage | `blocking_since` | Status / severity | Applicability and exact algorithm | Exact frozen/sealed input | NA / unavailable | Output code |
|---|---|---|---|---|---|---|---|
| R01 | PRE_GUIDE | pre-existing | ACTIVE / CRITICAL | All cycling days: no consecutive calendar dates both containing intensity-role sessions, including week boundaries. Athlete-fixed hard sessions count. | candidate `sessions[].{id,date,sport,role,origin}` | <2 intensity dates → NA; missing date/role → unavailable | `R01_BACK_TO_BACK_INTENSITY` |
| R02 | PRE_GUIDE | pre-existing | ACTIVE / CRITICAL | Apply A3.1’s exact exemption predicate. Across remaining dates, consecutive VO2 stimuli may be at most 16 non-recovery calendar days apart; ≥2 trainable weeks with none fails; recovery weeks pause elapsed count. | candidate session purpose/role/date + copied week type/cycling phase | Exempt plan slice or <2 trainable weeks → NA; missing purpose/date/week type/phase → unavailable | `R02_VO2_GAP` |
| R03 | PRE_GUIDE | pre-existing | ACTIVE / CRITICAL with warning band | Apply A3.1’s same-meso-block adjacency and exact reported-TSS ratio/bands. No volume-specific boundary and no final-session/design TSS substitution. | candidate `weeks[].{week_type,cycling_phase,meso_block_id,reported_cycling_tss}` | Empty adjacent load run → NA; missing/non-finite/≤0 denominator → unavailable | `R03_RECOVERY_TSS_RATIO` |
| R04 | PRE_GUIDE | pre-existing | ACTIVE / CRITICAL | Recovery weeks contain only rest, plain Endurance L1–L2, and Openers whose individual efforts are ≤30 s. Any tempo, cadence/SFR, threshold, VO2, race-sim, mixed, sustained >30 s, or other type fails. | candidate session purpose, level, segments, week type | No recovery week → NA; missing segment/purpose → unavailable | `R04_RECOVERY_PURITY` |
| R05 | PRE_GUIDE | pre-existing | ACTIVE / CRITICAL | Load and uber-load weeks have 2–3 intensity sessions. Transition allows 0–3; training age <1 or ≤3 available cycling days allows 1–3. Recovery, race, and medium weeks are excluded. | candidate roles; training age/off days; week type | No applicable load week → NA; missing role/week type → unavailable | `R05_INTENSITY_COUNT` |
| R06 | PRE_GUIDE | pre-existing | ACTIVE / CRITICAL | Every non-recovery/non-race week has ≥90 min ride when target hours ≤8, otherwise ≥120 min. A registered structured-endurance long design may satisfy at ≥75 min. | candidate cycling duration/purpose + available hours + week type | No applicable week → NA; missing duration/hours → unavailable | `R06_LONG_RIDE_MISSING` |
| R07 | POST_GUIDE | E3 | ACTIVE / WARNING | Every paid week’s emitted guide has exactly one Monday block note and its registered note type equals candidate week type. | D2 guide bytes + candidate weeks + block-notes digest | No paid weeks → NA; well-formed missing/mismatch → FAIL; malformed guide/config → unavailable | `R07_BLOCK_NOTE` |
| R08 | PRE_GUIDE | E3 | ACTIVE / CRITICAL | Every cycling session has exactly one §4.4.1 internal class; `NONE` is legal only for the closed enumerated session set. | candidate `sessions[].{sport,origin,session_type,purpose,duration_s,fueling_class}` | No cycling sessions → NA; missing/malformed class → unavailable | `R08_FUEL_TAG_MISSING` |
| R09 | PRE_GUIDE | E3 | ACTIVE / WARNING | Enforce §4.4.1's exact source-tier projection, including the enumerated empty tier. | candidate `fueling_source_tier` + `fueling_class` | No cycling sessions → NA; missing source/class → unavailable | `R09_INTENSITY_FUEL` |
| R10 | PRE_GUIDE | E3 | ACTIVE / WARNING | Enforce §4.4.1 scope: RACE only on race simulation/event; LONG_RIDE only on long-ride-role or ≥90-min endurance. | candidate purpose/role/origin/duration/fueling class | Neither class occurs → NA; missing purpose/class → unavailable | `R10_FUEL_SCOPE` |
| R11 | PRE_GUIDE | E3 | ACTIVE / CRITICAL | Evaluate every paid week through A3.2’s complete weekly-structure/artifact state table and validity check. | candidate week strength prescription/decline + strength artifacts/provenance | Exactly A3.2; malformed or contradictory → unavailable | `R11_STRENGTH_TRACK` |
| R12 | PRE_GUIDE | E3 | ACTIVE / WARNING | Apply A3.2’s recovery override and complete cycling-phase→strength-phase/intensity/frequency table. | candidate cycling phase, week type, meso block, strength contract + config digest | Declined/no prescribed strength → NA; unknown state → unavailable; known mismatch → FAIL | `R12_STRENGTH_PHASE` |
| R13 | PRE_GUIDE | E3 | ACTIVE / WARNING | Max/heavy strength cannot share a date with key threshold/VO2/race-sim intervals. Maintenance/deload/bodyweight is exempt. | candidate same-date strength intensity and cycling roles | No max/heavy strength → NA; missing template intensity → unavailable | `R13_STRENGTH_INTERVAL_CONFLICT` |
| R14 | PRE_GUIDE | pre-existing | ACTIVE / CRITICAL | Apply A3.3 normalization inside each tracker slot/block; family key and immutable ID stay constant except for the exact Kitchen-Sink equivalence set or a tombstone replacement resolved before series start. | candidate series tracker identity, raw display name, selected immutable ID | <2 assignments → NA; missing tracker/ID → unavailable | `R14_SERIES_COHERENCE` |
| R15 | PRE_GUIDE | E3 | ACTIVE / WARNING | Across applicable load-week pairs in one series, level delta 0, 1, or 2 passes; decrease or jump >2 fails. | candidate series ID, level, week type | No pair or non-native series → NA; missing level → unavailable | `R15_LEVEL_PROGRESSION` |
| R16 | PRE_GUIDE | E3 | ACTIVE / WARNING | Each non-race week’s sum of canonical planned session TSS is within ±15% of candidate target cycling TSS. | candidate session `tss` + week target TSS | No target/race week → NA; malformed target → unavailable | `R16_TSS_GUARDRAIL` |
| R17 | PRE_GUIDE | E3 | ACTIVE / CRITICAL | Apply A3.4’s exact phase/week allowed-set, subtype exclusion, and per-week inclusion algorithm. | candidate purpose/subtype/cycling phase/week type + phase-purpose digest | Only A3.4 NA cases; missing input/registry → unavailable | `R17_PHASE_MISMATCH` |
| R18 | PRE_GUIDE | E3 | DEFERRED / WARNING | Phase zone-time distribution against registered targets. No filename approximation. | required future per-session zone-duration data | Always `NOT_APPLICABLE` in r4 because required zone data does not exist; never unavailable/pass | `R18_PHASE_DISTRIBUTION` |
| R19 | PRE_GUIDE | pre-existing | ACTIVE / CRITICAL | Every load/medium/uber-load week cycling duration ≤ athlete available hours ×1.10 +5 min. Recovery/race are excluded. | candidate final cycling duration + available hours + week type | No applicable week → NA; missing hours/duration → unavailable | `R19_HOURS_EXCEEDED` |
| R20 | PRE_GUIDE | pre-existing | ACTIVE / CRITICAL | No generated cycling or strength training occurs on an athlete-declared off day; rest/day-off is allowed. Locked athlete-fixed activity remains visible and triggers review rather than erasure. | candidate sessions/date + preferred off days | No declared off day → NA; invalid day/date → unavailable | `R20_OFF_DAY_VIOLATION` |
| R21 | PRE_GUIDE | E3 | ACTIVE / CRITICAL | Every native session resolves to the pinned manifest row required by current mode; every non-native tuple resolves exactly in Appendix 8. No display-name matching. | candidate origin/provenance + manifest pin + producer-registry digest | Canonical rest/athlete-fixed use their registered identity contracts; unresolved/mismatched tuple → FAIL; malformed registry/pin → unavailable | `R21_WORKOUT_EXISTS` |
| R22 | PRE_GUIDE | E3 | DEFERRED / WARNING | Compare total hours and percent time above threshold to previous block; both may not increase simultaneously. | required future previous-block state + zone-duration data | Always `NOT_APPLICABLE` in r4 because both inputs are absent; never unavailable/pass | `R22_DUAL_ESCALATION` |
| R23 | PRE_GUIDE | E3 | ACTIVE / WARNING | Second applicable load week canonical planned cycling TSS must be ≥ first. No hidden tolerance. | candidate session `tss` grouped by meso load week | <2 load weeks → NA; missing TSS/week type → unavailable | `R23_PROGRESSIVE_OVERLOAD` |
| R24 | PRE_GUIDE | E3 | ACTIVE / WARNING | Training age <1 year forbids native levels 5–6; age <2 forbids Uber Load weeks. | candidate training age + final levels + week types | Missing training age → unavailable; no restricted level/week → PASS | `R24_TRAINING_AGE` |
| R25 | POST_GUIDE | E3 | ACTIVE / WARNING | For every paid week, apply A3.5’s exact normalized closed-marker substring test to its emitted Monday block-note text. | D2 guide bytes + candidate week/note IDs + block-notes digest | No paid weeks → NA; no marker → FAIL; missing/malformed guide/config → unavailable | `R25_READINESS_GUIDANCE` |
| R26 | PRE_GUIDE | E3 | ACTIVE / CRITICAL | For each paid week, absolute difference between reported cycling TSS and sum of final session canonical planned TSS ≤15. Race week uses min(sum including race, sum excluding race). | candidate week reported TSS + session `tss` and race flag | No paid weeks → NA; missing/non-finite reported total → unavailable | `R26_TSS_INTEGRITY` |

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

## Appendix 5 — complete initial `purpose_registry/v1`

The schema and 600 explicit row assignments below are normative. Their initial
scientific assignments are provisional hypotheses: every row has
`assignment_status=hypothesis` until the owner signs the complete Appendix 2
purpose promotion during E2. E1 writes the semantic equivalent to
`athletes/config/purpose_registry.yaml`; CI expands it and requires exact
row-for-row equality with this appendix.

### A5.1 Deterministic derivation

Production registry records have a category plus six level dictionaries; they
do not carry a separate top-level `system` field. The registry itself documents
its level structural formats and tags (`intervals`, `segments`,
`single_effort`, and `tired_vo2`) at
`athletes/scripts/archetype_registry.py:27-35,155-174`. Therefore “system tag”
here means the first key present in the union of all six level dictionaries,
using this exact precedence:

```
testing, maf_test, rest_day, openers, recovery, tired_vo2, loaded_recovery,
w_prime, above_cp, peak_fade, criss_cross, pyramid, descending,
single_effort, ramp, segments, intervals, category_default
```

`category_default` is selected only when no prior key occurs. Default subtype is
`<derived-class>/<system-tag>` with underscores preserved. Category determines
the default class exactly as follows:

| Registry category | Default purpose class |
|---|---|
| `VO2max` | `vo2max` |
| `TT_Threshold` | `threshold` |
| `Sprint_Neuromuscular` | `wprime_drain` |
| `Anaerobic_Capacity` | `wprime_drain` |
| `Durability` | `mixed` |
| `Endurance` | `endurance` |
| `Race_Simulation` | `race_sim` |
| `G_Spot` | `threshold` |
| `LT1_MAF` | `endurance` |
| `Critical_Power` | `wprime_drain` |
| `Norwegian_Double` | `threshold` |
| `HVLI_Extended` | `endurance` |
| `Testing` | `assessment` |
| `Recovery` | `recovery` |
| `INSCYD` | `mixed` |
| `Gravel_Specific` | `race_sim` |
| `SFR_Muscle_Force` | `threshold` |
| `Over_Under` | `threshold` |
| `Mixed_Climbing` | `mixed` |
| `Cadence_Work` | `endurance` |
| `Blended` | `mixed` |
| `Tempo` | `threshold` |
| `Kitchen_Sink` | `mixed` |
| `SFR_Series` | `threshold` |

After final class/subtype overrides below, derive `main_set_rule` as
`ASSESSMENT_BODY` for class `assessment`, `NONE` for class `free`, and
`SOURCE_BODY` otherwise. E1 assigns every rendered segment the immutable ID
`seg-{one-based-index:04d}` in final order and one provenance role:
`renderer_warmup`, `source_body`, or `renderer_cooldown`. `SOURCE_BODY` and
`ASSESSMENT_BODY` select every `source_body` ID, including source-authored
between-effort recoveries, and exclude the two renderer roles. `NONE` selects
zero IDs and is valid only for a pure-free contract. The native renderer’s
source-body construction is explicit in its structural branches at
`athletes/scripts/nate_workout_generator.py:1669-1784`; positional inference
after rendering is forbidden.

### A5.2 Explicit overrides

Only the rows below differ from category-class plus system-tag derivation. This
is the complete override set; an implementation may not add a title heuristic.

| Archetype ID | Final class/subtype | Rationale |
|---|---|---|
| `vo2max--5x3-vo2-classic` | `vo2max/steady` | Close the long-repetition VO2 geometry. |
| `vo2max--descending-vo2-pyramid` | `vo2max/pyramid` | Pyramid effort durations are not a generic interval subtype. |
| `vo2max--norwegian-4x8` | `vo2max/long_intervals` | Long VO2/threshold-border efforts need their own comparison family. |
| `vo2max--vo2max-with-loaded-recovery` | `vo2max/loaded_recovery` | Loaded recoveries are part of the intended geometry. |
| `vo2max--vo2max-30-30` | `vo2max/30_30` | Exact 30/30 geometry. |
| `vo2max--vo2max-40-20` | `vo2max/40_20` | Exact 40/20 geometry. |
| `vo2max--vo2max-extended` | `vo2max/steady` | Extended steady VO2 repetitions compare with steady geometry. |
| `vo2max--ronnestad-30-15` | `vo2max/30_15` | Exact Rønnestad 30/15 geometry. |
| `vo2max--ronnestad-40-20` | `vo2max/40_20` | Exact Rønnestad 40/20 geometry. |
| `vo2max--float-sets` | `wprime_drain/over_under` | Experimental authority classifies the float-set main set by W′ drain. |
| `tt-threshold--criss-cross-intervals` | `wprime_drain/over_under` | Alternating above/below-CP work is in the adopted W′ set. |
| `sprint-neuromuscular--peak-and-fade` | `wprime_drain/peak_fade` | Peak/fade is in the adopted W′ set rather than generic sprint dose. |
| `durability--tired-vo2max` | `vo2max/durability` | Fatigue preload does not change the VO2 main-set purpose. |
| `durability--progressive-fatigue-threshold` | `threshold/durability` | Threshold work after preload is the main purpose. |
| `durability--vo2-bookend` | `vo2max/durability` | VO2 efforts bookend endurance preload. |
| `durability--tired-30-30s` | `vo2max/30_30` | Adopted VO2 gate and exact 30/30 geometry. |
| `durability--tired-40-20s` | `vo2max/40_20` | VO2 40/20 work after preload. |
| `durability--tired-threshold` | `threshold/durability` | Sustained threshold is the trained system. |
| `durability--tired-threshold-repeats` | `threshold/durability` | Repeated threshold after preload is the trained system. |
| `durability--g-spot-into-threshold` | `threshold/blended` | Both components accumulate threshold-adjacent work. |
| `durability--tempo-into-threshold` | `threshold/blended` | Threshold finish controls the purpose. |
| `durability--full-simulation-combo` | `race_sim/durability` | Multi-system race sequence is a simulation contract. |
| `durability--late-race-vo2max` | `vo2max/durability` | Adopted VO2 gate after a long preload. |
| `endurance--pre-race-openers` | `openers/short` | Short activation efforts are not endurance dose. |
| `endurance--endurance-with-surges` | `mixed/endurance_surges` | Source segments intentionally mix endurance and surges. |
| `race-simulation--hard-starts` | `vo2max/hard_start` | Adopted VO2 gate; hard-start geometry is explicit. |
| `race-simulation--kitchen-sink-all-systems` | `mixed/kitchen_sink` | All-systems design is mixed, not a single simulation-dose class. |
| `g-spot--g-spot-criss-cross` | `wprime_drain/over_under` | Adopted W′ gate for alternating over/under work. |
| `lt1-maf--maf-test-protocol` | `assessment/maf` | It is a field assessment, not training-dose endurance. |
| `testing--ftp-ramp-test` | `assessment/ramp` | Self-limiting ramp assessment. |
| `testing--20min-ftp-test` | `assessment/20min` | Twenty-minute field assessment. |
| `testing--cp-test-protocol` | `assessment/cp` | Critical-power field assessment. |
| `recovery--rest-day` | `free/rest` | All six rows are pure FreeRide and use the empty-dose contract. |
| `inscyd--vlamax-reduction` | `endurance/vlamax_reduction` | Aerobic suppression protocol with brief sprints, not mixed race work. |
| `inscyd--fatmax-development` | `endurance/fatmax` | Steady FatMax development is endurance. |
| `inscyd--fatmax-vlamax-suppression` | `endurance/fatmax` | Aerobic suppression sequence remains endurance-purpose. |
| `inscyd--glycolytic-power` | `wprime_drain/anaerobic` | Adopted W′ gate for glycolytic-power intervals. |

The author inspected all six level structures for all 100 archetypes against the
category and structural-tag result. This table is the complete set whose
default result was ambiguous or physiologically wrong; no ambiguity remains
implicit and no additional override is authorized.

### A5.3 Explicit 600-row assignment

The columns are `row_id | class | subtype | main_set_rule | assignment_status`.
Rows are in Appendix 4 category/slot order, then L1–L6. Repetition is deliberate:
the manifest is row-addressed and no level may inherit an unstated contract.

| Row ID | Purpose class | Subtype | Main-set rule | Status |
|---|---|---|---|---|
| `vo2max--5x3-vo2-classic@L1` | `vo2max` | `vo2max/steady` | `SOURCE_BODY` | `hypothesis` |
| `vo2max--5x3-vo2-classic@L2` | `vo2max` | `vo2max/steady` | `SOURCE_BODY` | `hypothesis` |
| `vo2max--5x3-vo2-classic@L3` | `vo2max` | `vo2max/steady` | `SOURCE_BODY` | `hypothesis` |
| `vo2max--5x3-vo2-classic@L4` | `vo2max` | `vo2max/steady` | `SOURCE_BODY` | `hypothesis` |
| `vo2max--5x3-vo2-classic@L5` | `vo2max` | `vo2max/steady` | `SOURCE_BODY` | `hypothesis` |
| `vo2max--5x3-vo2-classic@L6` | `vo2max` | `vo2max/steady` | `SOURCE_BODY` | `hypothesis` |
| `vo2max--descending-vo2-pyramid@L1` | `vo2max` | `vo2max/pyramid` | `SOURCE_BODY` | `hypothesis` |
| `vo2max--descending-vo2-pyramid@L2` | `vo2max` | `vo2max/pyramid` | `SOURCE_BODY` | `hypothesis` |
| `vo2max--descending-vo2-pyramid@L3` | `vo2max` | `vo2max/pyramid` | `SOURCE_BODY` | `hypothesis` |
| `vo2max--descending-vo2-pyramid@L4` | `vo2max` | `vo2max/pyramid` | `SOURCE_BODY` | `hypothesis` |
| `vo2max--descending-vo2-pyramid@L5` | `vo2max` | `vo2max/pyramid` | `SOURCE_BODY` | `hypothesis` |
| `vo2max--descending-vo2-pyramid@L6` | `vo2max` | `vo2max/pyramid` | `SOURCE_BODY` | `hypothesis` |
| `vo2max--norwegian-4x8@L1` | `vo2max` | `vo2max/long_intervals` | `SOURCE_BODY` | `hypothesis` |
| `vo2max--norwegian-4x8@L2` | `vo2max` | `vo2max/long_intervals` | `SOURCE_BODY` | `hypothesis` |
| `vo2max--norwegian-4x8@L3` | `vo2max` | `vo2max/long_intervals` | `SOURCE_BODY` | `hypothesis` |
| `vo2max--norwegian-4x8@L4` | `vo2max` | `vo2max/long_intervals` | `SOURCE_BODY` | `hypothesis` |
| `vo2max--norwegian-4x8@L5` | `vo2max` | `vo2max/long_intervals` | `SOURCE_BODY` | `hypothesis` |
| `vo2max--norwegian-4x8@L6` | `vo2max` | `vo2max/long_intervals` | `SOURCE_BODY` | `hypothesis` |
| `vo2max--vo2max-with-loaded-recovery@L1` | `vo2max` | `vo2max/loaded_recovery` | `SOURCE_BODY` | `hypothesis` |
| `vo2max--vo2max-with-loaded-recovery@L2` | `vo2max` | `vo2max/loaded_recovery` | `SOURCE_BODY` | `hypothesis` |
| `vo2max--vo2max-with-loaded-recovery@L3` | `vo2max` | `vo2max/loaded_recovery` | `SOURCE_BODY` | `hypothesis` |
| `vo2max--vo2max-with-loaded-recovery@L4` | `vo2max` | `vo2max/loaded_recovery` | `SOURCE_BODY` | `hypothesis` |
| `vo2max--vo2max-with-loaded-recovery@L5` | `vo2max` | `vo2max/loaded_recovery` | `SOURCE_BODY` | `hypothesis` |
| `vo2max--vo2max-with-loaded-recovery@L6` | `vo2max` | `vo2max/loaded_recovery` | `SOURCE_BODY` | `hypothesis` |
| `vo2max--vo2max-30-30@L1` | `vo2max` | `vo2max/30_30` | `SOURCE_BODY` | `hypothesis` |
| `vo2max--vo2max-30-30@L2` | `vo2max` | `vo2max/30_30` | `SOURCE_BODY` | `hypothesis` |
| `vo2max--vo2max-30-30@L3` | `vo2max` | `vo2max/30_30` | `SOURCE_BODY` | `hypothesis` |
| `vo2max--vo2max-30-30@L4` | `vo2max` | `vo2max/30_30` | `SOURCE_BODY` | `hypothesis` |
| `vo2max--vo2max-30-30@L5` | `vo2max` | `vo2max/30_30` | `SOURCE_BODY` | `hypothesis` |
| `vo2max--vo2max-30-30@L6` | `vo2max` | `vo2max/30_30` | `SOURCE_BODY` | `hypothesis` |
| `vo2max--vo2max-40-20@L1` | `vo2max` | `vo2max/40_20` | `SOURCE_BODY` | `hypothesis` |
| `vo2max--vo2max-40-20@L2` | `vo2max` | `vo2max/40_20` | `SOURCE_BODY` | `hypothesis` |
| `vo2max--vo2max-40-20@L3` | `vo2max` | `vo2max/40_20` | `SOURCE_BODY` | `hypothesis` |
| `vo2max--vo2max-40-20@L4` | `vo2max` | `vo2max/40_20` | `SOURCE_BODY` | `hypothesis` |
| `vo2max--vo2max-40-20@L5` | `vo2max` | `vo2max/40_20` | `SOURCE_BODY` | `hypothesis` |
| `vo2max--vo2max-40-20@L6` | `vo2max` | `vo2max/40_20` | `SOURCE_BODY` | `hypothesis` |
| `vo2max--vo2max-extended@L1` | `vo2max` | `vo2max/steady` | `SOURCE_BODY` | `hypothesis` |
| `vo2max--vo2max-extended@L2` | `vo2max` | `vo2max/steady` | `SOURCE_BODY` | `hypothesis` |
| `vo2max--vo2max-extended@L3` | `vo2max` | `vo2max/steady` | `SOURCE_BODY` | `hypothesis` |
| `vo2max--vo2max-extended@L4` | `vo2max` | `vo2max/steady` | `SOURCE_BODY` | `hypothesis` |
| `vo2max--vo2max-extended@L5` | `vo2max` | `vo2max/steady` | `SOURCE_BODY` | `hypothesis` |
| `vo2max--vo2max-extended@L6` | `vo2max` | `vo2max/steady` | `SOURCE_BODY` | `hypothesis` |
| `vo2max--ronnestad-30-15@L1` | `vo2max` | `vo2max/30_15` | `SOURCE_BODY` | `hypothesis` |
| `vo2max--ronnestad-30-15@L2` | `vo2max` | `vo2max/30_15` | `SOURCE_BODY` | `hypothesis` |
| `vo2max--ronnestad-30-15@L3` | `vo2max` | `vo2max/30_15` | `SOURCE_BODY` | `hypothesis` |
| `vo2max--ronnestad-30-15@L4` | `vo2max` | `vo2max/30_15` | `SOURCE_BODY` | `hypothesis` |
| `vo2max--ronnestad-30-15@L5` | `vo2max` | `vo2max/30_15` | `SOURCE_BODY` | `hypothesis` |
| `vo2max--ronnestad-30-15@L6` | `vo2max` | `vo2max/30_15` | `SOURCE_BODY` | `hypothesis` |
| `vo2max--ronnestad-40-20@L1` | `vo2max` | `vo2max/40_20` | `SOURCE_BODY` | `hypothesis` |
| `vo2max--ronnestad-40-20@L2` | `vo2max` | `vo2max/40_20` | `SOURCE_BODY` | `hypothesis` |
| `vo2max--ronnestad-40-20@L3` | `vo2max` | `vo2max/40_20` | `SOURCE_BODY` | `hypothesis` |
| `vo2max--ronnestad-40-20@L4` | `vo2max` | `vo2max/40_20` | `SOURCE_BODY` | `hypothesis` |
| `vo2max--ronnestad-40-20@L5` | `vo2max` | `vo2max/40_20` | `SOURCE_BODY` | `hypothesis` |
| `vo2max--ronnestad-40-20@L6` | `vo2max` | `vo2max/40_20` | `SOURCE_BODY` | `hypothesis` |
| `vo2max--float-sets@L1` | `wprime_drain` | `wprime_drain/over_under` | `SOURCE_BODY` | `hypothesis` |
| `vo2max--float-sets@L2` | `wprime_drain` | `wprime_drain/over_under` | `SOURCE_BODY` | `hypothesis` |
| `vo2max--float-sets@L3` | `wprime_drain` | `wprime_drain/over_under` | `SOURCE_BODY` | `hypothesis` |
| `vo2max--float-sets@L4` | `wprime_drain` | `wprime_drain/over_under` | `SOURCE_BODY` | `hypothesis` |
| `vo2max--float-sets@L5` | `wprime_drain` | `wprime_drain/over_under` | `SOURCE_BODY` | `hypothesis` |
| `vo2max--float-sets@L6` | `wprime_drain` | `wprime_drain/over_under` | `SOURCE_BODY` | `hypothesis` |
| `tt-threshold--single-sustained-threshold@L1` | `threshold` | `threshold/single_effort` | `SOURCE_BODY` | `hypothesis` |
| `tt-threshold--single-sustained-threshold@L2` | `threshold` | `threshold/single_effort` | `SOURCE_BODY` | `hypothesis` |
| `tt-threshold--single-sustained-threshold@L3` | `threshold` | `threshold/single_effort` | `SOURCE_BODY` | `hypothesis` |
| `tt-threshold--single-sustained-threshold@L4` | `threshold` | `threshold/single_effort` | `SOURCE_BODY` | `hypothesis` |
| `tt-threshold--single-sustained-threshold@L5` | `threshold` | `threshold/single_effort` | `SOURCE_BODY` | `hypothesis` |
| `tt-threshold--single-sustained-threshold@L6` | `threshold` | `threshold/single_effort` | `SOURCE_BODY` | `hypothesis` |
| `tt-threshold--threshold-ramps@L1` | `threshold` | `threshold/ramp` | `SOURCE_BODY` | `hypothesis` |
| `tt-threshold--threshold-ramps@L2` | `threshold` | `threshold/ramp` | `SOURCE_BODY` | `hypothesis` |
| `tt-threshold--threshold-ramps@L3` | `threshold` | `threshold/ramp` | `SOURCE_BODY` | `hypothesis` |
| `tt-threshold--threshold-ramps@L4` | `threshold` | `threshold/ramp` | `SOURCE_BODY` | `hypothesis` |
| `tt-threshold--threshold-ramps@L5` | `threshold` | `threshold/ramp` | `SOURCE_BODY` | `hypothesis` |
| `tt-threshold--threshold-ramps@L6` | `threshold` | `threshold/ramp` | `SOURCE_BODY` | `hypothesis` |
| `tt-threshold--descending-threshold@L1` | `threshold` | `threshold/descending` | `SOURCE_BODY` | `hypothesis` |
| `tt-threshold--descending-threshold@L2` | `threshold` | `threshold/descending` | `SOURCE_BODY` | `hypothesis` |
| `tt-threshold--descending-threshold@L3` | `threshold` | `threshold/descending` | `SOURCE_BODY` | `hypothesis` |
| `tt-threshold--descending-threshold@L4` | `threshold` | `threshold/descending` | `SOURCE_BODY` | `hypothesis` |
| `tt-threshold--descending-threshold@L5` | `threshold` | `threshold/descending` | `SOURCE_BODY` | `hypothesis` |
| `tt-threshold--descending-threshold@L6` | `threshold` | `threshold/descending` | `SOURCE_BODY` | `hypothesis` |
| `tt-threshold--threshold-accumulation@L1` | `threshold` | `threshold/intervals` | `SOURCE_BODY` | `hypothesis` |
| `tt-threshold--threshold-accumulation@L2` | `threshold` | `threshold/intervals` | `SOURCE_BODY` | `hypothesis` |
| `tt-threshold--threshold-accumulation@L3` | `threshold` | `threshold/intervals` | `SOURCE_BODY` | `hypothesis` |
| `tt-threshold--threshold-accumulation@L4` | `threshold` | `threshold/intervals` | `SOURCE_BODY` | `hypothesis` |
| `tt-threshold--threshold-accumulation@L5` | `threshold` | `threshold/intervals` | `SOURCE_BODY` | `hypothesis` |
| `tt-threshold--threshold-accumulation@L6` | `threshold` | `threshold/intervals` | `SOURCE_BODY` | `hypothesis` |
| `tt-threshold--threshold-touch@L1` | `threshold` | `threshold/intervals` | `SOURCE_BODY` | `hypothesis` |
| `tt-threshold--threshold-touch@L2` | `threshold` | `threshold/intervals` | `SOURCE_BODY` | `hypothesis` |
| `tt-threshold--threshold-touch@L3` | `threshold` | `threshold/intervals` | `SOURCE_BODY` | `hypothesis` |
| `tt-threshold--threshold-touch@L4` | `threshold` | `threshold/intervals` | `SOURCE_BODY` | `hypothesis` |
| `tt-threshold--threshold-touch@L5` | `threshold` | `threshold/intervals` | `SOURCE_BODY` | `hypothesis` |
| `tt-threshold--threshold-touch@L6` | `threshold` | `threshold/intervals` | `SOURCE_BODY` | `hypothesis` |
| `tt-threshold--criss-cross-intervals@L1` | `wprime_drain` | `wprime_drain/over_under` | `SOURCE_BODY` | `hypothesis` |
| `tt-threshold--criss-cross-intervals@L2` | `wprime_drain` | `wprime_drain/over_under` | `SOURCE_BODY` | `hypothesis` |
| `tt-threshold--criss-cross-intervals@L3` | `wprime_drain` | `wprime_drain/over_under` | `SOURCE_BODY` | `hypothesis` |
| `tt-threshold--criss-cross-intervals@L4` | `wprime_drain` | `wprime_drain/over_under` | `SOURCE_BODY` | `hypothesis` |
| `tt-threshold--criss-cross-intervals@L5` | `wprime_drain` | `wprime_drain/over_under` | `SOURCE_BODY` | `hypothesis` |
| `tt-threshold--criss-cross-intervals@L6` | `wprime_drain` | `wprime_drain/over_under` | `SOURCE_BODY` | `hypothesis` |
| `tt-threshold--tte-extension@L1` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |
| `tt-threshold--tte-extension@L2` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |
| `tt-threshold--tte-extension@L3` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |
| `tt-threshold--tte-extension@L4` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |
| `tt-threshold--tte-extension@L5` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |
| `tt-threshold--tte-extension@L6` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |
| `tt-threshold--bpa-best-possible-average@L1` | `threshold` | `threshold/single_effort` | `SOURCE_BODY` | `hypothesis` |
| `tt-threshold--bpa-best-possible-average@L2` | `threshold` | `threshold/single_effort` | `SOURCE_BODY` | `hypothesis` |
| `tt-threshold--bpa-best-possible-average@L3` | `threshold` | `threshold/single_effort` | `SOURCE_BODY` | `hypothesis` |
| `tt-threshold--bpa-best-possible-average@L4` | `threshold` | `threshold/single_effort` | `SOURCE_BODY` | `hypothesis` |
| `tt-threshold--bpa-best-possible-average@L5` | `threshold` | `threshold/single_effort` | `SOURCE_BODY` | `hypothesis` |
| `tt-threshold--bpa-best-possible-average@L6` | `threshold` | `threshold/single_effort` | `SOURCE_BODY` | `hypothesis` |
| `sprint-neuromuscular--attack-repeats@L1` | `wprime_drain` | `wprime_drain/intervals` | `SOURCE_BODY` | `hypothesis` |
| `sprint-neuromuscular--attack-repeats@L2` | `wprime_drain` | `wprime_drain/intervals` | `SOURCE_BODY` | `hypothesis` |
| `sprint-neuromuscular--attack-repeats@L3` | `wprime_drain` | `wprime_drain/intervals` | `SOURCE_BODY` | `hypothesis` |
| `sprint-neuromuscular--attack-repeats@L4` | `wprime_drain` | `wprime_drain/intervals` | `SOURCE_BODY` | `hypothesis` |
| `sprint-neuromuscular--attack-repeats@L5` | `wprime_drain` | `wprime_drain/intervals` | `SOURCE_BODY` | `hypothesis` |
| `sprint-neuromuscular--attack-repeats@L6` | `wprime_drain` | `wprime_drain/intervals` | `SOURCE_BODY` | `hypothesis` |
| `sprint-neuromuscular--sprint-buildups@L1` | `wprime_drain` | `wprime_drain/category_default` | `SOURCE_BODY` | `hypothesis` |
| `sprint-neuromuscular--sprint-buildups@L2` | `wprime_drain` | `wprime_drain/category_default` | `SOURCE_BODY` | `hypothesis` |
| `sprint-neuromuscular--sprint-buildups@L3` | `wprime_drain` | `wprime_drain/category_default` | `SOURCE_BODY` | `hypothesis` |
| `sprint-neuromuscular--sprint-buildups@L4` | `wprime_drain` | `wprime_drain/category_default` | `SOURCE_BODY` | `hypothesis` |
| `sprint-neuromuscular--sprint-buildups@L5` | `wprime_drain` | `wprime_drain/category_default` | `SOURCE_BODY` | `hypothesis` |
| `sprint-neuromuscular--sprint-buildups@L6` | `wprime_drain` | `wprime_drain/category_default` | `SOURCE_BODY` | `hypothesis` |
| `sprint-neuromuscular--peak-and-fade@L1` | `wprime_drain` | `wprime_drain/peak_fade` | `SOURCE_BODY` | `hypothesis` |
| `sprint-neuromuscular--peak-and-fade@L2` | `wprime_drain` | `wprime_drain/peak_fade` | `SOURCE_BODY` | `hypothesis` |
| `sprint-neuromuscular--peak-and-fade@L3` | `wprime_drain` | `wprime_drain/peak_fade` | `SOURCE_BODY` | `hypothesis` |
| `sprint-neuromuscular--peak-and-fade@L4` | `wprime_drain` | `wprime_drain/peak_fade` | `SOURCE_BODY` | `hypothesis` |
| `sprint-neuromuscular--peak-and-fade@L5` | `wprime_drain` | `wprime_drain/peak_fade` | `SOURCE_BODY` | `hypothesis` |
| `sprint-neuromuscular--peak-and-fade@L6` | `wprime_drain` | `wprime_drain/peak_fade` | `SOURCE_BODY` | `hypothesis` |
| `sprint-neuromuscular--ilt-single-leg-training@L1` | `wprime_drain` | `wprime_drain/intervals` | `SOURCE_BODY` | `hypothesis` |
| `sprint-neuromuscular--ilt-single-leg-training@L2` | `wprime_drain` | `wprime_drain/intervals` | `SOURCE_BODY` | `hypothesis` |
| `sprint-neuromuscular--ilt-single-leg-training@L3` | `wprime_drain` | `wprime_drain/intervals` | `SOURCE_BODY` | `hypothesis` |
| `sprint-neuromuscular--ilt-single-leg-training@L4` | `wprime_drain` | `wprime_drain/intervals` | `SOURCE_BODY` | `hypothesis` |
| `sprint-neuromuscular--ilt-single-leg-training@L5` | `wprime_drain` | `wprime_drain/intervals` | `SOURCE_BODY` | `hypothesis` |
| `sprint-neuromuscular--ilt-single-leg-training@L6` | `wprime_drain` | `wprime_drain/intervals` | `SOURCE_BODY` | `hypothesis` |
| `sprint-neuromuscular--stomps@L1` | `wprime_drain` | `wprime_drain/intervals` | `SOURCE_BODY` | `hypothesis` |
| `sprint-neuromuscular--stomps@L2` | `wprime_drain` | `wprime_drain/intervals` | `SOURCE_BODY` | `hypothesis` |
| `sprint-neuromuscular--stomps@L3` | `wprime_drain` | `wprime_drain/intervals` | `SOURCE_BODY` | `hypothesis` |
| `sprint-neuromuscular--stomps@L4` | `wprime_drain` | `wprime_drain/intervals` | `SOURCE_BODY` | `hypothesis` |
| `sprint-neuromuscular--stomps@L5` | `wprime_drain` | `wprime_drain/intervals` | `SOURCE_BODY` | `hypothesis` |
| `sprint-neuromuscular--stomps@L6` | `wprime_drain` | `wprime_drain/intervals` | `SOURCE_BODY` | `hypothesis` |
| `sprint-neuromuscular--burst-intervals@L1` | `wprime_drain` | `wprime_drain/segments` | `SOURCE_BODY` | `hypothesis` |
| `sprint-neuromuscular--burst-intervals@L2` | `wprime_drain` | `wprime_drain/segments` | `SOURCE_BODY` | `hypothesis` |
| `sprint-neuromuscular--burst-intervals@L3` | `wprime_drain` | `wprime_drain/segments` | `SOURCE_BODY` | `hypothesis` |
| `sprint-neuromuscular--burst-intervals@L4` | `wprime_drain` | `wprime_drain/segments` | `SOURCE_BODY` | `hypothesis` |
| `sprint-neuromuscular--burst-intervals@L5` | `wprime_drain` | `wprime_drain/segments` | `SOURCE_BODY` | `hypothesis` |
| `sprint-neuromuscular--burst-intervals@L6` | `wprime_drain` | `wprime_drain/segments` | `SOURCE_BODY` | `hypothesis` |
| `anaerobic-capacity--2min-killers@L1` | `wprime_drain` | `wprime_drain/intervals` | `SOURCE_BODY` | `hypothesis` |
| `anaerobic-capacity--2min-killers@L2` | `wprime_drain` | `wprime_drain/intervals` | `SOURCE_BODY` | `hypothesis` |
| `anaerobic-capacity--2min-killers@L3` | `wprime_drain` | `wprime_drain/intervals` | `SOURCE_BODY` | `hypothesis` |
| `anaerobic-capacity--2min-killers@L4` | `wprime_drain` | `wprime_drain/intervals` | `SOURCE_BODY` | `hypothesis` |
| `anaerobic-capacity--2min-killers@L5` | `wprime_drain` | `wprime_drain/intervals` | `SOURCE_BODY` | `hypothesis` |
| `anaerobic-capacity--2min-killers@L6` | `wprime_drain` | `wprime_drain/intervals` | `SOURCE_BODY` | `hypothesis` |
| `anaerobic-capacity--90sec-repeats@L1` | `wprime_drain` | `wprime_drain/intervals` | `SOURCE_BODY` | `hypothesis` |
| `anaerobic-capacity--90sec-repeats@L2` | `wprime_drain` | `wprime_drain/intervals` | `SOURCE_BODY` | `hypothesis` |
| `anaerobic-capacity--90sec-repeats@L3` | `wprime_drain` | `wprime_drain/intervals` | `SOURCE_BODY` | `hypothesis` |
| `anaerobic-capacity--90sec-repeats@L4` | `wprime_drain` | `wprime_drain/intervals` | `SOURCE_BODY` | `hypothesis` |
| `anaerobic-capacity--90sec-repeats@L5` | `wprime_drain` | `wprime_drain/intervals` | `SOURCE_BODY` | `hypothesis` |
| `anaerobic-capacity--90sec-repeats@L6` | `wprime_drain` | `wprime_drain/intervals` | `SOURCE_BODY` | `hypothesis` |
| `anaerobic-capacity--1min-all-out-repeats@L1` | `wprime_drain` | `wprime_drain/intervals` | `SOURCE_BODY` | `hypothesis` |
| `anaerobic-capacity--1min-all-out-repeats@L2` | `wprime_drain` | `wprime_drain/intervals` | `SOURCE_BODY` | `hypothesis` |
| `anaerobic-capacity--1min-all-out-repeats@L3` | `wprime_drain` | `wprime_drain/intervals` | `SOURCE_BODY` | `hypothesis` |
| `anaerobic-capacity--1min-all-out-repeats@L4` | `wprime_drain` | `wprime_drain/intervals` | `SOURCE_BODY` | `hypothesis` |
| `anaerobic-capacity--1min-all-out-repeats@L5` | `wprime_drain` | `wprime_drain/intervals` | `SOURCE_BODY` | `hypothesis` |
| `anaerobic-capacity--1min-all-out-repeats@L6` | `wprime_drain` | `wprime_drain/intervals` | `SOURCE_BODY` | `hypothesis` |
| `durability--tired-vo2max@L1` | `vo2max` | `vo2max/durability` | `SOURCE_BODY` | `hypothesis` |
| `durability--tired-vo2max@L2` | `vo2max` | `vo2max/durability` | `SOURCE_BODY` | `hypothesis` |
| `durability--tired-vo2max@L3` | `vo2max` | `vo2max/durability` | `SOURCE_BODY` | `hypothesis` |
| `durability--tired-vo2max@L4` | `vo2max` | `vo2max/durability` | `SOURCE_BODY` | `hypothesis` |
| `durability--tired-vo2max@L5` | `vo2max` | `vo2max/durability` | `SOURCE_BODY` | `hypothesis` |
| `durability--tired-vo2max@L6` | `vo2max` | `vo2max/durability` | `SOURCE_BODY` | `hypothesis` |
| `durability--double-day-simulation@L1` | `mixed` | `mixed/category_default` | `SOURCE_BODY` | `hypothesis` |
| `durability--double-day-simulation@L2` | `mixed` | `mixed/category_default` | `SOURCE_BODY` | `hypothesis` |
| `durability--double-day-simulation@L3` | `mixed` | `mixed/category_default` | `SOURCE_BODY` | `hypothesis` |
| `durability--double-day-simulation@L4` | `mixed` | `mixed/category_default` | `SOURCE_BODY` | `hypothesis` |
| `durability--double-day-simulation@L5` | `mixed` | `mixed/category_default` | `SOURCE_BODY` | `hypothesis` |
| `durability--double-day-simulation@L6` | `mixed` | `mixed/category_default` | `SOURCE_BODY` | `hypothesis` |
| `durability--progressive-fatigue-threshold@L1` | `threshold` | `threshold/durability` | `SOURCE_BODY` | `hypothesis` |
| `durability--progressive-fatigue-threshold@L2` | `threshold` | `threshold/durability` | `SOURCE_BODY` | `hypothesis` |
| `durability--progressive-fatigue-threshold@L3` | `threshold` | `threshold/durability` | `SOURCE_BODY` | `hypothesis` |
| `durability--progressive-fatigue-threshold@L4` | `threshold` | `threshold/durability` | `SOURCE_BODY` | `hypothesis` |
| `durability--progressive-fatigue-threshold@L5` | `threshold` | `threshold/durability` | `SOURCE_BODY` | `hypothesis` |
| `durability--progressive-fatigue-threshold@L6` | `threshold` | `threshold/durability` | `SOURCE_BODY` | `hypothesis` |
| `durability--vo2-bookend@L1` | `vo2max` | `vo2max/durability` | `SOURCE_BODY` | `hypothesis` |
| `durability--vo2-bookend@L2` | `vo2max` | `vo2max/durability` | `SOURCE_BODY` | `hypothesis` |
| `durability--vo2-bookend@L3` | `vo2max` | `vo2max/durability` | `SOURCE_BODY` | `hypothesis` |
| `durability--vo2-bookend@L4` | `vo2max` | `vo2max/durability` | `SOURCE_BODY` | `hypothesis` |
| `durability--vo2-bookend@L5` | `vo2max` | `vo2max/durability` | `SOURCE_BODY` | `hypothesis` |
| `durability--vo2-bookend@L6` | `vo2max` | `vo2max/durability` | `SOURCE_BODY` | `hypothesis` |
| `durability--buffer-workout@L1` | `mixed` | `mixed/segments` | `SOURCE_BODY` | `hypothesis` |
| `durability--buffer-workout@L2` | `mixed` | `mixed/segments` | `SOURCE_BODY` | `hypothesis` |
| `durability--buffer-workout@L3` | `mixed` | `mixed/segments` | `SOURCE_BODY` | `hypothesis` |
| `durability--buffer-workout@L4` | `mixed` | `mixed/segments` | `SOURCE_BODY` | `hypothesis` |
| `durability--buffer-workout@L5` | `mixed` | `mixed/segments` | `SOURCE_BODY` | `hypothesis` |
| `durability--buffer-workout@L6` | `mixed` | `mixed/segments` | `SOURCE_BODY` | `hypothesis` |
| `durability--tired-30-30s@L1` | `vo2max` | `vo2max/30_30` | `SOURCE_BODY` | `hypothesis` |
| `durability--tired-30-30s@L2` | `vo2max` | `vo2max/30_30` | `SOURCE_BODY` | `hypothesis` |
| `durability--tired-30-30s@L3` | `vo2max` | `vo2max/30_30` | `SOURCE_BODY` | `hypothesis` |
| `durability--tired-30-30s@L4` | `vo2max` | `vo2max/30_30` | `SOURCE_BODY` | `hypothesis` |
| `durability--tired-30-30s@L5` | `vo2max` | `vo2max/30_30` | `SOURCE_BODY` | `hypothesis` |
| `durability--tired-30-30s@L6` | `vo2max` | `vo2max/30_30` | `SOURCE_BODY` | `hypothesis` |
| `durability--tired-40-20s@L1` | `vo2max` | `vo2max/40_20` | `SOURCE_BODY` | `hypothesis` |
| `durability--tired-40-20s@L2` | `vo2max` | `vo2max/40_20` | `SOURCE_BODY` | `hypothesis` |
| `durability--tired-40-20s@L3` | `vo2max` | `vo2max/40_20` | `SOURCE_BODY` | `hypothesis` |
| `durability--tired-40-20s@L4` | `vo2max` | `vo2max/40_20` | `SOURCE_BODY` | `hypothesis` |
| `durability--tired-40-20s@L5` | `vo2max` | `vo2max/40_20` | `SOURCE_BODY` | `hypothesis` |
| `durability--tired-40-20s@L6` | `vo2max` | `vo2max/40_20` | `SOURCE_BODY` | `hypothesis` |
| `durability--tired-threshold@L1` | `threshold` | `threshold/durability` | `SOURCE_BODY` | `hypothesis` |
| `durability--tired-threshold@L2` | `threshold` | `threshold/durability` | `SOURCE_BODY` | `hypothesis` |
| `durability--tired-threshold@L3` | `threshold` | `threshold/durability` | `SOURCE_BODY` | `hypothesis` |
| `durability--tired-threshold@L4` | `threshold` | `threshold/durability` | `SOURCE_BODY` | `hypothesis` |
| `durability--tired-threshold@L5` | `threshold` | `threshold/durability` | `SOURCE_BODY` | `hypothesis` |
| `durability--tired-threshold@L6` | `threshold` | `threshold/durability` | `SOURCE_BODY` | `hypothesis` |
| `durability--tired-threshold-repeats@L1` | `threshold` | `threshold/durability` | `SOURCE_BODY` | `hypothesis` |
| `durability--tired-threshold-repeats@L2` | `threshold` | `threshold/durability` | `SOURCE_BODY` | `hypothesis` |
| `durability--tired-threshold-repeats@L3` | `threshold` | `threshold/durability` | `SOURCE_BODY` | `hypothesis` |
| `durability--tired-threshold-repeats@L4` | `threshold` | `threshold/durability` | `SOURCE_BODY` | `hypothesis` |
| `durability--tired-threshold-repeats@L5` | `threshold` | `threshold/durability` | `SOURCE_BODY` | `hypothesis` |
| `durability--tired-threshold-repeats@L6` | `threshold` | `threshold/durability` | `SOURCE_BODY` | `hypothesis` |
| `durability--g-spot-into-threshold@L1` | `threshold` | `threshold/blended` | `SOURCE_BODY` | `hypothesis` |
| `durability--g-spot-into-threshold@L2` | `threshold` | `threshold/blended` | `SOURCE_BODY` | `hypothesis` |
| `durability--g-spot-into-threshold@L3` | `threshold` | `threshold/blended` | `SOURCE_BODY` | `hypothesis` |
| `durability--g-spot-into-threshold@L4` | `threshold` | `threshold/blended` | `SOURCE_BODY` | `hypothesis` |
| `durability--g-spot-into-threshold@L5` | `threshold` | `threshold/blended` | `SOURCE_BODY` | `hypothesis` |
| `durability--g-spot-into-threshold@L6` | `threshold` | `threshold/blended` | `SOURCE_BODY` | `hypothesis` |
| `durability--tempo-into-threshold@L1` | `threshold` | `threshold/blended` | `SOURCE_BODY` | `hypothesis` |
| `durability--tempo-into-threshold@L2` | `threshold` | `threshold/blended` | `SOURCE_BODY` | `hypothesis` |
| `durability--tempo-into-threshold@L3` | `threshold` | `threshold/blended` | `SOURCE_BODY` | `hypothesis` |
| `durability--tempo-into-threshold@L4` | `threshold` | `threshold/blended` | `SOURCE_BODY` | `hypothesis` |
| `durability--tempo-into-threshold@L5` | `threshold` | `threshold/blended` | `SOURCE_BODY` | `hypothesis` |
| `durability--tempo-into-threshold@L6` | `threshold` | `threshold/blended` | `SOURCE_BODY` | `hypothesis` |
| `durability--full-simulation-combo@L1` | `race_sim` | `race_sim/durability` | `SOURCE_BODY` | `hypothesis` |
| `durability--full-simulation-combo@L2` | `race_sim` | `race_sim/durability` | `SOURCE_BODY` | `hypothesis` |
| `durability--full-simulation-combo@L3` | `race_sim` | `race_sim/durability` | `SOURCE_BODY` | `hypothesis` |
| `durability--full-simulation-combo@L4` | `race_sim` | `race_sim/durability` | `SOURCE_BODY` | `hypothesis` |
| `durability--full-simulation-combo@L5` | `race_sim` | `race_sim/durability` | `SOURCE_BODY` | `hypothesis` |
| `durability--full-simulation-combo@L6` | `race_sim` | `race_sim/durability` | `SOURCE_BODY` | `hypothesis` |
| `durability--late-race-vo2max@L1` | `vo2max` | `vo2max/durability` | `SOURCE_BODY` | `hypothesis` |
| `durability--late-race-vo2max@L2` | `vo2max` | `vo2max/durability` | `SOURCE_BODY` | `hypothesis` |
| `durability--late-race-vo2max@L3` | `vo2max` | `vo2max/durability` | `SOURCE_BODY` | `hypothesis` |
| `durability--late-race-vo2max@L4` | `vo2max` | `vo2max/durability` | `SOURCE_BODY` | `hypothesis` |
| `durability--late-race-vo2max@L5` | `vo2max` | `vo2max/durability` | `SOURCE_BODY` | `hypothesis` |
| `durability--late-race-vo2max@L6` | `vo2max` | `vo2max/durability` | `SOURCE_BODY` | `hypothesis` |
| `endurance--pre-race-openers@L1` | `openers` | `openers/short` | `SOURCE_BODY` | `hypothesis` |
| `endurance--pre-race-openers@L2` | `openers` | `openers/short` | `SOURCE_BODY` | `hypothesis` |
| `endurance--pre-race-openers@L3` | `openers` | `openers/short` | `SOURCE_BODY` | `hypothesis` |
| `endurance--pre-race-openers@L4` | `openers` | `openers/short` | `SOURCE_BODY` | `hypothesis` |
| `endurance--pre-race-openers@L5` | `openers` | `openers/short` | `SOURCE_BODY` | `hypothesis` |
| `endurance--pre-race-openers@L6` | `openers` | `openers/short` | `SOURCE_BODY` | `hypothesis` |
| `endurance--terrain-simulation-z2@L1` | `endurance` | `endurance/category_default` | `SOURCE_BODY` | `hypothesis` |
| `endurance--terrain-simulation-z2@L2` | `endurance` | `endurance/category_default` | `SOURCE_BODY` | `hypothesis` |
| `endurance--terrain-simulation-z2@L3` | `endurance` | `endurance/category_default` | `SOURCE_BODY` | `hypothesis` |
| `endurance--terrain-simulation-z2@L4` | `endurance` | `endurance/category_default` | `SOURCE_BODY` | `hypothesis` |
| `endurance--terrain-simulation-z2@L5` | `endurance` | `endurance/category_default` | `SOURCE_BODY` | `hypothesis` |
| `endurance--terrain-simulation-z2@L6` | `endurance` | `endurance/category_default` | `SOURCE_BODY` | `hypothesis` |
| `endurance--endurance-with-surges@L1` | `mixed` | `mixed/endurance_surges` | `SOURCE_BODY` | `hypothesis` |
| `endurance--endurance-with-surges@L2` | `mixed` | `mixed/endurance_surges` | `SOURCE_BODY` | `hypothesis` |
| `endurance--endurance-with-surges@L3` | `mixed` | `mixed/endurance_surges` | `SOURCE_BODY` | `hypothesis` |
| `endurance--endurance-with-surges@L4` | `mixed` | `mixed/endurance_surges` | `SOURCE_BODY` | `hypothesis` |
| `endurance--endurance-with-surges@L5` | `mixed` | `mixed/endurance_surges` | `SOURCE_BODY` | `hypothesis` |
| `endurance--endurance-with-surges@L6` | `mixed` | `mixed/endurance_surges` | `SOURCE_BODY` | `hypothesis` |
| `endurance--endurance-blocks@L1` | `endurance` | `endurance/segments` | `SOURCE_BODY` | `hypothesis` |
| `endurance--endurance-blocks@L2` | `endurance` | `endurance/segments` | `SOURCE_BODY` | `hypothesis` |
| `endurance--endurance-blocks@L3` | `endurance` | `endurance/segments` | `SOURCE_BODY` | `hypothesis` |
| `endurance--endurance-blocks@L4` | `endurance` | `endurance/segments` | `SOURCE_BODY` | `hypothesis` |
| `endurance--endurance-blocks@L5` | `endurance` | `endurance/segments` | `SOURCE_BODY` | `hypothesis` |
| `endurance--endurance-blocks@L6` | `endurance` | `endurance/segments` | `SOURCE_BODY` | `hypothesis` |
| `endurance--heat-acclimation-protocol@L1` | `endurance` | `endurance/segments` | `SOURCE_BODY` | `hypothesis` |
| `endurance--heat-acclimation-protocol@L2` | `endurance` | `endurance/segments` | `SOURCE_BODY` | `hypothesis` |
| `endurance--heat-acclimation-protocol@L3` | `endurance` | `endurance/segments` | `SOURCE_BODY` | `hypothesis` |
| `endurance--heat-acclimation-protocol@L4` | `endurance` | `endurance/segments` | `SOURCE_BODY` | `hypothesis` |
| `endurance--heat-acclimation-protocol@L5` | `endurance` | `endurance/segments` | `SOURCE_BODY` | `hypothesis` |
| `endurance--heat-acclimation-protocol@L6` | `endurance` | `endurance/segments` | `SOURCE_BODY` | `hypothesis` |
| `race-simulation--breakaway-simulation@L1` | `race_sim` | `race_sim/intervals` | `SOURCE_BODY` | `hypothesis` |
| `race-simulation--breakaway-simulation@L2` | `race_sim` | `race_sim/intervals` | `SOURCE_BODY` | `hypothesis` |
| `race-simulation--breakaway-simulation@L3` | `race_sim` | `race_sim/intervals` | `SOURCE_BODY` | `hypothesis` |
| `race-simulation--breakaway-simulation@L4` | `race_sim` | `race_sim/intervals` | `SOURCE_BODY` | `hypothesis` |
| `race-simulation--breakaway-simulation@L5` | `race_sim` | `race_sim/intervals` | `SOURCE_BODY` | `hypothesis` |
| `race-simulation--breakaway-simulation@L6` | `race_sim` | `race_sim/intervals` | `SOURCE_BODY` | `hypothesis` |
| `race-simulation--variable-pace-chaos@L1` | `race_sim` | `race_sim/category_default` | `SOURCE_BODY` | `hypothesis` |
| `race-simulation--variable-pace-chaos@L2` | `race_sim` | `race_sim/category_default` | `SOURCE_BODY` | `hypothesis` |
| `race-simulation--variable-pace-chaos@L3` | `race_sim` | `race_sim/category_default` | `SOURCE_BODY` | `hypothesis` |
| `race-simulation--variable-pace-chaos@L4` | `race_sim` | `race_sim/category_default` | `SOURCE_BODY` | `hypothesis` |
| `race-simulation--variable-pace-chaos@L5` | `race_sim` | `race_sim/category_default` | `SOURCE_BODY` | `hypothesis` |
| `race-simulation--variable-pace-chaos@L6` | `race_sim` | `race_sim/category_default` | `SOURCE_BODY` | `hypothesis` |
| `race-simulation--sector-simulation@L1` | `race_sim` | `race_sim/category_default` | `SOURCE_BODY` | `hypothesis` |
| `race-simulation--sector-simulation@L2` | `race_sim` | `race_sim/category_default` | `SOURCE_BODY` | `hypothesis` |
| `race-simulation--sector-simulation@L3` | `race_sim` | `race_sim/category_default` | `SOURCE_BODY` | `hypothesis` |
| `race-simulation--sector-simulation@L4` | `race_sim` | `race_sim/category_default` | `SOURCE_BODY` | `hypothesis` |
| `race-simulation--sector-simulation@L5` | `race_sim` | `race_sim/category_default` | `SOURCE_BODY` | `hypothesis` |
| `race-simulation--sector-simulation@L6` | `race_sim` | `race_sim/category_default` | `SOURCE_BODY` | `hypothesis` |
| `race-simulation--race-simulation@L1` | `race_sim` | `race_sim/segments` | `SOURCE_BODY` | `hypothesis` |
| `race-simulation--race-simulation@L2` | `race_sim` | `race_sim/segments` | `SOURCE_BODY` | `hypothesis` |
| `race-simulation--race-simulation@L3` | `race_sim` | `race_sim/segments` | `SOURCE_BODY` | `hypothesis` |
| `race-simulation--race-simulation@L4` | `race_sim` | `race_sim/segments` | `SOURCE_BODY` | `hypothesis` |
| `race-simulation--race-simulation@L5` | `race_sim` | `race_sim/segments` | `SOURCE_BODY` | `hypothesis` |
| `race-simulation--race-simulation@L6` | `race_sim` | `race_sim/segments` | `SOURCE_BODY` | `hypothesis` |
| `race-simulation--hard-starts@L1` | `vo2max` | `vo2max/hard_start` | `SOURCE_BODY` | `hypothesis` |
| `race-simulation--hard-starts@L2` | `vo2max` | `vo2max/hard_start` | `SOURCE_BODY` | `hypothesis` |
| `race-simulation--hard-starts@L3` | `vo2max` | `vo2max/hard_start` | `SOURCE_BODY` | `hypothesis` |
| `race-simulation--hard-starts@L4` | `vo2max` | `vo2max/hard_start` | `SOURCE_BODY` | `hypothesis` |
| `race-simulation--hard-starts@L5` | `vo2max` | `vo2max/hard_start` | `SOURCE_BODY` | `hypothesis` |
| `race-simulation--hard-starts@L6` | `vo2max` | `vo2max/hard_start` | `SOURCE_BODY` | `hypothesis` |
| `race-simulation--structured-fartlek@L1` | `race_sim` | `race_sim/intervals` | `SOURCE_BODY` | `hypothesis` |
| `race-simulation--structured-fartlek@L2` | `race_sim` | `race_sim/intervals` | `SOURCE_BODY` | `hypothesis` |
| `race-simulation--structured-fartlek@L3` | `race_sim` | `race_sim/intervals` | `SOURCE_BODY` | `hypothesis` |
| `race-simulation--structured-fartlek@L4` | `race_sim` | `race_sim/intervals` | `SOURCE_BODY` | `hypothesis` |
| `race-simulation--structured-fartlek@L5` | `race_sim` | `race_sim/intervals` | `SOURCE_BODY` | `hypothesis` |
| `race-simulation--structured-fartlek@L6` | `race_sim` | `race_sim/intervals` | `SOURCE_BODY` | `hypothesis` |
| `race-simulation--attacks-and-repeatability@L1` | `race_sim` | `race_sim/segments` | `SOURCE_BODY` | `hypothesis` |
| `race-simulation--attacks-and-repeatability@L2` | `race_sim` | `race_sim/segments` | `SOURCE_BODY` | `hypothesis` |
| `race-simulation--attacks-and-repeatability@L3` | `race_sim` | `race_sim/segments` | `SOURCE_BODY` | `hypothesis` |
| `race-simulation--attacks-and-repeatability@L4` | `race_sim` | `race_sim/segments` | `SOURCE_BODY` | `hypothesis` |
| `race-simulation--attacks-and-repeatability@L5` | `race_sim` | `race_sim/segments` | `SOURCE_BODY` | `hypothesis` |
| `race-simulation--attacks-and-repeatability@L6` | `race_sim` | `race_sim/segments` | `SOURCE_BODY` | `hypothesis` |
| `race-simulation--kitchen-sink-all-systems@L1` | `mixed` | `mixed/kitchen_sink` | `SOURCE_BODY` | `hypothesis` |
| `race-simulation--kitchen-sink-all-systems@L2` | `mixed` | `mixed/kitchen_sink` | `SOURCE_BODY` | `hypothesis` |
| `race-simulation--kitchen-sink-all-systems@L3` | `mixed` | `mixed/kitchen_sink` | `SOURCE_BODY` | `hypothesis` |
| `race-simulation--kitchen-sink-all-systems@L4` | `mixed` | `mixed/kitchen_sink` | `SOURCE_BODY` | `hypothesis` |
| `race-simulation--kitchen-sink-all-systems@L5` | `mixed` | `mixed/kitchen_sink` | `SOURCE_BODY` | `hypothesis` |
| `race-simulation--kitchen-sink-all-systems@L6` | `mixed` | `mixed/kitchen_sink` | `SOURCE_BODY` | `hypothesis` |
| `g-spot--g-spot-intervals@L1` | `threshold` | `threshold/intervals` | `SOURCE_BODY` | `hypothesis` |
| `g-spot--g-spot-intervals@L2` | `threshold` | `threshold/intervals` | `SOURCE_BODY` | `hypothesis` |
| `g-spot--g-spot-intervals@L3` | `threshold` | `threshold/intervals` | `SOURCE_BODY` | `hypothesis` |
| `g-spot--g-spot-intervals@L4` | `threshold` | `threshold/intervals` | `SOURCE_BODY` | `hypothesis` |
| `g-spot--g-spot-intervals@L5` | `threshold` | `threshold/intervals` | `SOURCE_BODY` | `hypothesis` |
| `g-spot--g-spot-intervals@L6` | `threshold` | `threshold/intervals` | `SOURCE_BODY` | `hypothesis` |
| `g-spot--g-spot-criss-cross@L1` | `wprime_drain` | `wprime_drain/over_under` | `SOURCE_BODY` | `hypothesis` |
| `g-spot--g-spot-criss-cross@L2` | `wprime_drain` | `wprime_drain/over_under` | `SOURCE_BODY` | `hypothesis` |
| `g-spot--g-spot-criss-cross@L3` | `wprime_drain` | `wprime_drain/over_under` | `SOURCE_BODY` | `hypothesis` |
| `g-spot--g-spot-criss-cross@L4` | `wprime_drain` | `wprime_drain/over_under` | `SOURCE_BODY` | `hypothesis` |
| `g-spot--g-spot-criss-cross@L5` | `wprime_drain` | `wprime_drain/over_under` | `SOURCE_BODY` | `hypothesis` |
| `g-spot--g-spot-criss-cross@L6` | `wprime_drain` | `wprime_drain/over_under` | `SOURCE_BODY` | `hypothesis` |
| `g-spot--g-spot-progressive@L1` | `threshold` | `threshold/ramp` | `SOURCE_BODY` | `hypothesis` |
| `g-spot--g-spot-progressive@L2` | `threshold` | `threshold/ramp` | `SOURCE_BODY` | `hypothesis` |
| `g-spot--g-spot-progressive@L3` | `threshold` | `threshold/ramp` | `SOURCE_BODY` | `hypothesis` |
| `g-spot--g-spot-progressive@L4` | `threshold` | `threshold/ramp` | `SOURCE_BODY` | `hypothesis` |
| `g-spot--g-spot-progressive@L5` | `threshold` | `threshold/ramp` | `SOURCE_BODY` | `hypothesis` |
| `g-spot--g-spot-progressive@L6` | `threshold` | `threshold/ramp` | `SOURCE_BODY` | `hypothesis` |
| `lt1-maf--lt1-capped-endurance@L1` | `endurance` | `endurance/category_default` | `SOURCE_BODY` | `hypothesis` |
| `lt1-maf--lt1-capped-endurance@L2` | `endurance` | `endurance/category_default` | `SOURCE_BODY` | `hypothesis` |
| `lt1-maf--lt1-capped-endurance@L3` | `endurance` | `endurance/category_default` | `SOURCE_BODY` | `hypothesis` |
| `lt1-maf--lt1-capped-endurance@L4` | `endurance` | `endurance/category_default` | `SOURCE_BODY` | `hypothesis` |
| `lt1-maf--lt1-capped-endurance@L5` | `endurance` | `endurance/category_default` | `SOURCE_BODY` | `hypothesis` |
| `lt1-maf--lt1-capped-endurance@L6` | `endurance` | `endurance/category_default` | `SOURCE_BODY` | `hypothesis` |
| `lt1-maf--maf-test-protocol@L1` | `assessment` | `assessment/maf` | `ASSESSMENT_BODY` | `hypothesis` |
| `lt1-maf--maf-test-protocol@L2` | `assessment` | `assessment/maf` | `ASSESSMENT_BODY` | `hypothesis` |
| `lt1-maf--maf-test-protocol@L3` | `assessment` | `assessment/maf` | `ASSESSMENT_BODY` | `hypothesis` |
| `lt1-maf--maf-test-protocol@L4` | `assessment` | `assessment/maf` | `ASSESSMENT_BODY` | `hypothesis` |
| `lt1-maf--maf-test-protocol@L5` | `assessment` | `assessment/maf` | `ASSESSMENT_BODY` | `hypothesis` |
| `lt1-maf--maf-test-protocol@L6` | `assessment` | `assessment/maf` | `ASSESSMENT_BODY` | `hypothesis` |
| `critical-power--above-cp-repeats@L1` | `wprime_drain` | `wprime_drain/above_cp` | `SOURCE_BODY` | `hypothesis` |
| `critical-power--above-cp-repeats@L2` | `wprime_drain` | `wprime_drain/above_cp` | `SOURCE_BODY` | `hypothesis` |
| `critical-power--above-cp-repeats@L3` | `wprime_drain` | `wprime_drain/above_cp` | `SOURCE_BODY` | `hypothesis` |
| `critical-power--above-cp-repeats@L4` | `wprime_drain` | `wprime_drain/above_cp` | `SOURCE_BODY` | `hypothesis` |
| `critical-power--above-cp-repeats@L5` | `wprime_drain` | `wprime_drain/above_cp` | `SOURCE_BODY` | `hypothesis` |
| `critical-power--above-cp-repeats@L6` | `wprime_drain` | `wprime_drain/above_cp` | `SOURCE_BODY` | `hypothesis` |
| `critical-power--w-prime-depletion@L1` | `wprime_drain` | `wprime_drain/w_prime` | `SOURCE_BODY` | `hypothesis` |
| `critical-power--w-prime-depletion@L2` | `wprime_drain` | `wprime_drain/w_prime` | `SOURCE_BODY` | `hypothesis` |
| `critical-power--w-prime-depletion@L3` | `wprime_drain` | `wprime_drain/w_prime` | `SOURCE_BODY` | `hypothesis` |
| `critical-power--w-prime-depletion@L4` | `wprime_drain` | `wprime_drain/w_prime` | `SOURCE_BODY` | `hypothesis` |
| `critical-power--w-prime-depletion@L5` | `wprime_drain` | `wprime_drain/w_prime` | `SOURCE_BODY` | `hypothesis` |
| `critical-power--w-prime-depletion@L6` | `wprime_drain` | `wprime_drain/w_prime` | `SOURCE_BODY` | `hypothesis` |
| `norwegian-double--norwegian-4x8-classic@L1` | `threshold` | `threshold/intervals` | `SOURCE_BODY` | `hypothesis` |
| `norwegian-double--norwegian-4x8-classic@L2` | `threshold` | `threshold/intervals` | `SOURCE_BODY` | `hypothesis` |
| `norwegian-double--norwegian-4x8-classic@L3` | `threshold` | `threshold/intervals` | `SOURCE_BODY` | `hypothesis` |
| `norwegian-double--norwegian-4x8-classic@L4` | `threshold` | `threshold/intervals` | `SOURCE_BODY` | `hypothesis` |
| `norwegian-double--norwegian-4x8-classic@L5` | `threshold` | `threshold/intervals` | `SOURCE_BODY` | `hypothesis` |
| `norwegian-double--norwegian-4x8-classic@L6` | `threshold` | `threshold/intervals` | `SOURCE_BODY` | `hypothesis` |
| `norwegian-double--norwegian-double-am@L1` | `threshold` | `threshold/intervals` | `SOURCE_BODY` | `hypothesis` |
| `norwegian-double--norwegian-double-am@L2` | `threshold` | `threshold/intervals` | `SOURCE_BODY` | `hypothesis` |
| `norwegian-double--norwegian-double-am@L3` | `threshold` | `threshold/intervals` | `SOURCE_BODY` | `hypothesis` |
| `norwegian-double--norwegian-double-am@L4` | `threshold` | `threshold/intervals` | `SOURCE_BODY` | `hypothesis` |
| `norwegian-double--norwegian-double-am@L5` | `threshold` | `threshold/intervals` | `SOURCE_BODY` | `hypothesis` |
| `norwegian-double--norwegian-double-am@L6` | `threshold` | `threshold/intervals` | `SOURCE_BODY` | `hypothesis` |
| `norwegian-double--norwegian-double-pm@L1` | `threshold` | `threshold/intervals` | `SOURCE_BODY` | `hypothesis` |
| `norwegian-double--norwegian-double-pm@L2` | `threshold` | `threshold/intervals` | `SOURCE_BODY` | `hypothesis` |
| `norwegian-double--norwegian-double-pm@L3` | `threshold` | `threshold/intervals` | `SOURCE_BODY` | `hypothesis` |
| `norwegian-double--norwegian-double-pm@L4` | `threshold` | `threshold/intervals` | `SOURCE_BODY` | `hypothesis` |
| `norwegian-double--norwegian-double-pm@L5` | `threshold` | `threshold/intervals` | `SOURCE_BODY` | `hypothesis` |
| `norwegian-double--norwegian-double-pm@L6` | `threshold` | `threshold/intervals` | `SOURCE_BODY` | `hypothesis` |
| `hvli-extended--hvli-extended-z2@L1` | `endurance` | `endurance/category_default` | `SOURCE_BODY` | `hypothesis` |
| `hvli-extended--hvli-extended-z2@L2` | `endurance` | `endurance/category_default` | `SOURCE_BODY` | `hypothesis` |
| `hvli-extended--hvli-extended-z2@L3` | `endurance` | `endurance/category_default` | `SOURCE_BODY` | `hypothesis` |
| `hvli-extended--hvli-extended-z2@L4` | `endurance` | `endurance/category_default` | `SOURCE_BODY` | `hypothesis` |
| `hvli-extended--hvli-extended-z2@L5` | `endurance` | `endurance/category_default` | `SOURCE_BODY` | `hypothesis` |
| `hvli-extended--hvli-extended-z2@L6` | `endurance` | `endurance/category_default` | `SOURCE_BODY` | `hypothesis` |
| `hvli-extended--hvli-terrain-simulation@L1` | `endurance` | `endurance/category_default` | `SOURCE_BODY` | `hypothesis` |
| `hvli-extended--hvli-terrain-simulation@L2` | `endurance` | `endurance/category_default` | `SOURCE_BODY` | `hypothesis` |
| `hvli-extended--hvli-terrain-simulation@L3` | `endurance` | `endurance/category_default` | `SOURCE_BODY` | `hypothesis` |
| `hvli-extended--hvli-terrain-simulation@L4` | `endurance` | `endurance/category_default` | `SOURCE_BODY` | `hypothesis` |
| `hvli-extended--hvli-terrain-simulation@L5` | `endurance` | `endurance/category_default` | `SOURCE_BODY` | `hypothesis` |
| `hvli-extended--hvli-terrain-simulation@L6` | `endurance` | `endurance/category_default` | `SOURCE_BODY` | `hypothesis` |
| `testing--ftp-ramp-test@L1` | `assessment` | `assessment/ramp` | `ASSESSMENT_BODY` | `hypothesis` |
| `testing--ftp-ramp-test@L2` | `assessment` | `assessment/ramp` | `ASSESSMENT_BODY` | `hypothesis` |
| `testing--ftp-ramp-test@L3` | `assessment` | `assessment/ramp` | `ASSESSMENT_BODY` | `hypothesis` |
| `testing--ftp-ramp-test@L4` | `assessment` | `assessment/ramp` | `ASSESSMENT_BODY` | `hypothesis` |
| `testing--ftp-ramp-test@L5` | `assessment` | `assessment/ramp` | `ASSESSMENT_BODY` | `hypothesis` |
| `testing--ftp-ramp-test@L6` | `assessment` | `assessment/ramp` | `ASSESSMENT_BODY` | `hypothesis` |
| `testing--20min-ftp-test@L1` | `assessment` | `assessment/20min` | `ASSESSMENT_BODY` | `hypothesis` |
| `testing--20min-ftp-test@L2` | `assessment` | `assessment/20min` | `ASSESSMENT_BODY` | `hypothesis` |
| `testing--20min-ftp-test@L3` | `assessment` | `assessment/20min` | `ASSESSMENT_BODY` | `hypothesis` |
| `testing--20min-ftp-test@L4` | `assessment` | `assessment/20min` | `ASSESSMENT_BODY` | `hypothesis` |
| `testing--20min-ftp-test@L5` | `assessment` | `assessment/20min` | `ASSESSMENT_BODY` | `hypothesis` |
| `testing--20min-ftp-test@L6` | `assessment` | `assessment/20min` | `ASSESSMENT_BODY` | `hypothesis` |
| `testing--cp-test-protocol@L1` | `assessment` | `assessment/cp` | `ASSESSMENT_BODY` | `hypothesis` |
| `testing--cp-test-protocol@L2` | `assessment` | `assessment/cp` | `ASSESSMENT_BODY` | `hypothesis` |
| `testing--cp-test-protocol@L3` | `assessment` | `assessment/cp` | `ASSESSMENT_BODY` | `hypothesis` |
| `testing--cp-test-protocol@L4` | `assessment` | `assessment/cp` | `ASSESSMENT_BODY` | `hypothesis` |
| `testing--cp-test-protocol@L5` | `assessment` | `assessment/cp` | `ASSESSMENT_BODY` | `hypothesis` |
| `testing--cp-test-protocol@L6` | `assessment` | `assessment/cp` | `ASSESSMENT_BODY` | `hypothesis` |
| `recovery--active-recovery-spin@L1` | `recovery` | `recovery/recovery` | `SOURCE_BODY` | `hypothesis` |
| `recovery--active-recovery-spin@L2` | `recovery` | `recovery/recovery` | `SOURCE_BODY` | `hypothesis` |
| `recovery--active-recovery-spin@L3` | `recovery` | `recovery/recovery` | `SOURCE_BODY` | `hypothesis` |
| `recovery--active-recovery-spin@L4` | `recovery` | `recovery/recovery` | `SOURCE_BODY` | `hypothesis` |
| `recovery--active-recovery-spin@L5` | `recovery` | `recovery/recovery` | `SOURCE_BODY` | `hypothesis` |
| `recovery--active-recovery-spin@L6` | `recovery` | `recovery/recovery` | `SOURCE_BODY` | `hypothesis` |
| `recovery--rest-day@L1` | `free` | `free/rest` | `NONE` | `hypothesis` |
| `recovery--rest-day@L2` | `free` | `free/rest` | `NONE` | `hypothesis` |
| `recovery--rest-day@L3` | `free` | `free/rest` | `NONE` | `hypothesis` |
| `recovery--rest-day@L4` | `free` | `free/rest` | `NONE` | `hypothesis` |
| `recovery--rest-day@L5` | `free` | `free/rest` | `NONE` | `hypothesis` |
| `recovery--rest-day@L6` | `free` | `free/rest` | `NONE` | `hypothesis` |
| `inscyd--vlamax-reduction@L1` | `endurance` | `endurance/vlamax_reduction` | `SOURCE_BODY` | `hypothesis` |
| `inscyd--vlamax-reduction@L2` | `endurance` | `endurance/vlamax_reduction` | `SOURCE_BODY` | `hypothesis` |
| `inscyd--vlamax-reduction@L3` | `endurance` | `endurance/vlamax_reduction` | `SOURCE_BODY` | `hypothesis` |
| `inscyd--vlamax-reduction@L4` | `endurance` | `endurance/vlamax_reduction` | `SOURCE_BODY` | `hypothesis` |
| `inscyd--vlamax-reduction@L5` | `endurance` | `endurance/vlamax_reduction` | `SOURCE_BODY` | `hypothesis` |
| `inscyd--vlamax-reduction@L6` | `endurance` | `endurance/vlamax_reduction` | `SOURCE_BODY` | `hypothesis` |
| `inscyd--fatmax-development@L1` | `endurance` | `endurance/fatmax` | `SOURCE_BODY` | `hypothesis` |
| `inscyd--fatmax-development@L2` | `endurance` | `endurance/fatmax` | `SOURCE_BODY` | `hypothesis` |
| `inscyd--fatmax-development@L3` | `endurance` | `endurance/fatmax` | `SOURCE_BODY` | `hypothesis` |
| `inscyd--fatmax-development@L4` | `endurance` | `endurance/fatmax` | `SOURCE_BODY` | `hypothesis` |
| `inscyd--fatmax-development@L5` | `endurance` | `endurance/fatmax` | `SOURCE_BODY` | `hypothesis` |
| `inscyd--fatmax-development@L6` | `endurance` | `endurance/fatmax` | `SOURCE_BODY` | `hypothesis` |
| `inscyd--fatmax-vlamax-suppression@L1` | `endurance` | `endurance/fatmax` | `SOURCE_BODY` | `hypothesis` |
| `inscyd--fatmax-vlamax-suppression@L2` | `endurance` | `endurance/fatmax` | `SOURCE_BODY` | `hypothesis` |
| `inscyd--fatmax-vlamax-suppression@L3` | `endurance` | `endurance/fatmax` | `SOURCE_BODY` | `hypothesis` |
| `inscyd--fatmax-vlamax-suppression@L4` | `endurance` | `endurance/fatmax` | `SOURCE_BODY` | `hypothesis` |
| `inscyd--fatmax-vlamax-suppression@L5` | `endurance` | `endurance/fatmax` | `SOURCE_BODY` | `hypothesis` |
| `inscyd--fatmax-vlamax-suppression@L6` | `endurance` | `endurance/fatmax` | `SOURCE_BODY` | `hypothesis` |
| `inscyd--glycolytic-power@L1` | `wprime_drain` | `wprime_drain/anaerobic` | `SOURCE_BODY` | `hypothesis` |
| `inscyd--glycolytic-power@L2` | `wprime_drain` | `wprime_drain/anaerobic` | `SOURCE_BODY` | `hypothesis` |
| `inscyd--glycolytic-power@L3` | `wprime_drain` | `wprime_drain/anaerobic` | `SOURCE_BODY` | `hypothesis` |
| `inscyd--glycolytic-power@L4` | `wprime_drain` | `wprime_drain/anaerobic` | `SOURCE_BODY` | `hypothesis` |
| `inscyd--glycolytic-power@L5` | `wprime_drain` | `wprime_drain/anaerobic` | `SOURCE_BODY` | `hypothesis` |
| `inscyd--glycolytic-power@L6` | `wprime_drain` | `wprime_drain/anaerobic` | `SOURCE_BODY` | `hypothesis` |
| `gravel-specific--surge-and-settle@L1` | `race_sim` | `race_sim/category_default` | `SOURCE_BODY` | `hypothesis` |
| `gravel-specific--surge-and-settle@L2` | `race_sim` | `race_sim/category_default` | `SOURCE_BODY` | `hypothesis` |
| `gravel-specific--surge-and-settle@L3` | `race_sim` | `race_sim/category_default` | `SOURCE_BODY` | `hypothesis` |
| `gravel-specific--surge-and-settle@L4` | `race_sim` | `race_sim/category_default` | `SOURCE_BODY` | `hypothesis` |
| `gravel-specific--surge-and-settle@L5` | `race_sim` | `race_sim/category_default` | `SOURCE_BODY` | `hypothesis` |
| `gravel-specific--surge-and-settle@L6` | `race_sim` | `race_sim/category_default` | `SOURCE_BODY` | `hypothesis` |
| `gravel-specific--terrain-microbursts@L1` | `race_sim` | `race_sim/category_default` | `SOURCE_BODY` | `hypothesis` |
| `gravel-specific--terrain-microbursts@L2` | `race_sim` | `race_sim/category_default` | `SOURCE_BODY` | `hypothesis` |
| `gravel-specific--terrain-microbursts@L3` | `race_sim` | `race_sim/category_default` | `SOURCE_BODY` | `hypothesis` |
| `gravel-specific--terrain-microbursts@L4` | `race_sim` | `race_sim/category_default` | `SOURCE_BODY` | `hypothesis` |
| `gravel-specific--terrain-microbursts@L5` | `race_sim` | `race_sim/category_default` | `SOURCE_BODY` | `hypothesis` |
| `gravel-specific--terrain-microbursts@L6` | `race_sim` | `race_sim/category_default` | `SOURCE_BODY` | `hypothesis` |
| `gravel-specific--gravel-grind@L1` | `race_sim` | `race_sim/category_default` | `SOURCE_BODY` | `hypothesis` |
| `gravel-specific--gravel-grind@L2` | `race_sim` | `race_sim/category_default` | `SOURCE_BODY` | `hypothesis` |
| `gravel-specific--gravel-grind@L3` | `race_sim` | `race_sim/category_default` | `SOURCE_BODY` | `hypothesis` |
| `gravel-specific--gravel-grind@L4` | `race_sim` | `race_sim/category_default` | `SOURCE_BODY` | `hypothesis` |
| `gravel-specific--gravel-grind@L5` | `race_sim` | `race_sim/category_default` | `SOURCE_BODY` | `hypothesis` |
| `gravel-specific--gravel-grind@L6` | `race_sim` | `race_sim/category_default` | `SOURCE_BODY` | `hypothesis` |
| `gravel-specific--late-race-surge-protocol@L1` | `race_sim` | `race_sim/category_default` | `SOURCE_BODY` | `hypothesis` |
| `gravel-specific--late-race-surge-protocol@L2` | `race_sim` | `race_sim/category_default` | `SOURCE_BODY` | `hypothesis` |
| `gravel-specific--late-race-surge-protocol@L3` | `race_sim` | `race_sim/category_default` | `SOURCE_BODY` | `hypothesis` |
| `gravel-specific--late-race-surge-protocol@L4` | `race_sim` | `race_sim/category_default` | `SOURCE_BODY` | `hypothesis` |
| `gravel-specific--late-race-surge-protocol@L5` | `race_sim` | `race_sim/category_default` | `SOURCE_BODY` | `hypothesis` |
| `gravel-specific--late-race-surge-protocol@L6` | `race_sim` | `race_sim/category_default` | `SOURCE_BODY` | `hypothesis` |
| `gravel-specific--gravel-race-simulation@L1` | `race_sim` | `race_sim/segments` | `SOURCE_BODY` | `hypothesis` |
| `gravel-specific--gravel-race-simulation@L2` | `race_sim` | `race_sim/segments` | `SOURCE_BODY` | `hypothesis` |
| `gravel-specific--gravel-race-simulation@L3` | `race_sim` | `race_sim/segments` | `SOURCE_BODY` | `hypothesis` |
| `gravel-specific--gravel-race-simulation@L4` | `race_sim` | `race_sim/segments` | `SOURCE_BODY` | `hypothesis` |
| `gravel-specific--gravel-race-simulation@L5` | `race_sim` | `race_sim/segments` | `SOURCE_BODY` | `hypothesis` |
| `gravel-specific--gravel-race-simulation@L6` | `race_sim` | `race_sim/segments` | `SOURCE_BODY` | `hypothesis` |
| `sfr-muscle-force--5x4-sfr@L1` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |
| `sfr-muscle-force--5x4-sfr@L2` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |
| `sfr-muscle-force--5x4-sfr@L3` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |
| `sfr-muscle-force--5x4-sfr@L4` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |
| `sfr-muscle-force--5x4-sfr@L5` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |
| `sfr-muscle-force--5x4-sfr@L6` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |
| `sfr-muscle-force--sfr-cadence-contrast@L1` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |
| `sfr-muscle-force--sfr-cadence-contrast@L2` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |
| `sfr-muscle-force--sfr-cadence-contrast@L3` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |
| `sfr-muscle-force--sfr-cadence-contrast@L4` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |
| `sfr-muscle-force--sfr-cadence-contrast@L5` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |
| `sfr-muscle-force--sfr-cadence-contrast@L6` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |
| `over-under--climbing-over-under@L1` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |
| `over-under--climbing-over-under@L2` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |
| `over-under--climbing-over-under@L3` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |
| `over-under--climbing-over-under@L4` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |
| `over-under--climbing-over-under@L5` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |
| `over-under--climbing-over-under@L6` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |
| `over-under--overunder-threshold@L1` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |
| `over-under--overunder-threshold@L2` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |
| `over-under--overunder-threshold@L3` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |
| `over-under--overunder-threshold@L4` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |
| `over-under--overunder-threshold@L5` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |
| `over-under--overunder-threshold@L6` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |
| `mixed-climbing--mixed-climbing@L1` | `mixed` | `mixed/segments` | `SOURCE_BODY` | `hypothesis` |
| `mixed-climbing--mixed-climbing@L2` | `mixed` | `mixed/segments` | `SOURCE_BODY` | `hypothesis` |
| `mixed-climbing--mixed-climbing@L3` | `mixed` | `mixed/segments` | `SOURCE_BODY` | `hypothesis` |
| `mixed-climbing--mixed-climbing@L4` | `mixed` | `mixed/segments` | `SOURCE_BODY` | `hypothesis` |
| `mixed-climbing--mixed-climbing@L5` | `mixed` | `mixed/segments` | `SOURCE_BODY` | `hypothesis` |
| `mixed-climbing--mixed-climbing@L6` | `mixed` | `mixed/segments` | `SOURCE_BODY` | `hypothesis` |
| `mixed-climbing--mixed-climbing-variations@L1` | `mixed` | `mixed/segments` | `SOURCE_BODY` | `hypothesis` |
| `mixed-climbing--mixed-climbing-variations@L2` | `mixed` | `mixed/segments` | `SOURCE_BODY` | `hypothesis` |
| `mixed-climbing--mixed-climbing-variations@L3` | `mixed` | `mixed/segments` | `SOURCE_BODY` | `hypothesis` |
| `mixed-climbing--mixed-climbing-variations@L4` | `mixed` | `mixed/segments` | `SOURCE_BODY` | `hypothesis` |
| `mixed-climbing--mixed-climbing-variations@L5` | `mixed` | `mixed/segments` | `SOURCE_BODY` | `hypothesis` |
| `mixed-climbing--mixed-climbing-variations@L6` | `mixed` | `mixed/segments` | `SOURCE_BODY` | `hypothesis` |
| `cadence-work--high-cadence-intervals@L1` | `endurance` | `endurance/segments` | `SOURCE_BODY` | `hypothesis` |
| `cadence-work--high-cadence-intervals@L2` | `endurance` | `endurance/segments` | `SOURCE_BODY` | `hypothesis` |
| `cadence-work--high-cadence-intervals@L3` | `endurance` | `endurance/segments` | `SOURCE_BODY` | `hypothesis` |
| `cadence-work--high-cadence-intervals@L4` | `endurance` | `endurance/segments` | `SOURCE_BODY` | `hypothesis` |
| `cadence-work--high-cadence-intervals@L5` | `endurance` | `endurance/segments` | `SOURCE_BODY` | `hypothesis` |
| `cadence-work--high-cadence-intervals@L6` | `endurance` | `endurance/segments` | `SOURCE_BODY` | `hypothesis` |
| `blended--blended-30-30-sfr@L1` | `mixed` | `mixed/segments` | `SOURCE_BODY` | `hypothesis` |
| `blended--blended-30-30-sfr@L2` | `mixed` | `mixed/segments` | `SOURCE_BODY` | `hypothesis` |
| `blended--blended-30-30-sfr@L3` | `mixed` | `mixed/segments` | `SOURCE_BODY` | `hypothesis` |
| `blended--blended-30-30-sfr@L4` | `mixed` | `mixed/segments` | `SOURCE_BODY` | `hypothesis` |
| `blended--blended-30-30-sfr@L5` | `mixed` | `mixed/segments` | `SOURCE_BODY` | `hypothesis` |
| `blended--blended-30-30-sfr@L6` | `mixed` | `mixed/segments` | `SOURCE_BODY` | `hypothesis` |
| `blended--blended-vo2-g-spot@L1` | `mixed` | `mixed/segments` | `SOURCE_BODY` | `hypothesis` |
| `blended--blended-vo2-g-spot@L2` | `mixed` | `mixed/segments` | `SOURCE_BODY` | `hypothesis` |
| `blended--blended-vo2-g-spot@L3` | `mixed` | `mixed/segments` | `SOURCE_BODY` | `hypothesis` |
| `blended--blended-vo2-g-spot@L4` | `mixed` | `mixed/segments` | `SOURCE_BODY` | `hypothesis` |
| `blended--blended-vo2-g-spot@L5` | `mixed` | `mixed/segments` | `SOURCE_BODY` | `hypothesis` |
| `blended--blended-vo2-g-spot@L6` | `mixed` | `mixed/segments` | `SOURCE_BODY` | `hypothesis` |
| `blended--blended-endurance-threshold-sprints@L1` | `mixed` | `mixed/segments` | `SOURCE_BODY` | `hypothesis` |
| `blended--blended-endurance-threshold-sprints@L2` | `mixed` | `mixed/segments` | `SOURCE_BODY` | `hypothesis` |
| `blended--blended-endurance-threshold-sprints@L3` | `mixed` | `mixed/segments` | `SOURCE_BODY` | `hypothesis` |
| `blended--blended-endurance-threshold-sprints@L4` | `mixed` | `mixed/segments` | `SOURCE_BODY` | `hypothesis` |
| `blended--blended-endurance-threshold-sprints@L5` | `mixed` | `mixed/segments` | `SOURCE_BODY` | `hypothesis` |
| `blended--blended-endurance-threshold-sprints@L6` | `mixed` | `mixed/segments` | `SOURCE_BODY` | `hypothesis` |
| `tempo--tempo-accelerations@L1` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |
| `tempo--tempo-accelerations@L2` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |
| `tempo--tempo-accelerations@L3` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |
| `tempo--tempo-accelerations@L4` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |
| `tempo--tempo-accelerations@L5` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |
| `tempo--tempo-accelerations@L6` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |
| `tempo--tempo-sprints@L1` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |
| `tempo--tempo-sprints@L2` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |
| `tempo--tempo-sprints@L3` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |
| `tempo--tempo-sprints@L4` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |
| `tempo--tempo-sprints@L5` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |
| `tempo--tempo-sprints@L6` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |
| `tempo--3x15-tempo@L1` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |
| `tempo--3x15-tempo@L2` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |
| `tempo--3x15-tempo@L3` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |
| `tempo--3x15-tempo@L4` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |
| `tempo--3x15-tempo@L5` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |
| `tempo--3x15-tempo@L6` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |
| `tempo--bookend-tempo@L1` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |
| `tempo--bookend-tempo@L2` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |
| `tempo--bookend-tempo@L3` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |
| `tempo--bookend-tempo@L4` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |
| `tempo--bookend-tempo@L5` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |
| `tempo--bookend-tempo@L6` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |
| `tempo--tempo-lift@L1` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |
| `tempo--tempo-lift@L2` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |
| `tempo--tempo-lift@L3` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |
| `tempo--tempo-lift@L4` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |
| `tempo--tempo-lift@L5` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |
| `tempo--tempo-lift@L6` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |
| `tempo--tired-tempo@L1` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |
| `tempo--tired-tempo@L2` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |
| `tempo--tired-tempo@L3` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |
| `tempo--tired-tempo@L4` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |
| `tempo--tired-tempo@L5` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |
| `tempo--tired-tempo@L6` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |
| `kitchen-sink--drain-cleaner@L1` | `mixed` | `mixed/segments` | `SOURCE_BODY` | `hypothesis` |
| `kitchen-sink--drain-cleaner@L2` | `mixed` | `mixed/segments` | `SOURCE_BODY` | `hypothesis` |
| `kitchen-sink--drain-cleaner@L3` | `mixed` | `mixed/segments` | `SOURCE_BODY` | `hypothesis` |
| `kitchen-sink--drain-cleaner@L4` | `mixed` | `mixed/segments` | `SOURCE_BODY` | `hypothesis` |
| `kitchen-sink--drain-cleaner@L5` | `mixed` | `mixed/segments` | `SOURCE_BODY` | `hypothesis` |
| `kitchen-sink--drain-cleaner@L6` | `mixed` | `mixed/segments` | `SOURCE_BODY` | `hypothesis` |
| `kitchen-sink--la-balanguera@L1` | `mixed` | `mixed/segments` | `SOURCE_BODY` | `hypothesis` |
| `kitchen-sink--la-balanguera@L2` | `mixed` | `mixed/segments` | `SOURCE_BODY` | `hypothesis` |
| `kitchen-sink--la-balanguera@L3` | `mixed` | `mixed/segments` | `SOURCE_BODY` | `hypothesis` |
| `kitchen-sink--la-balanguera@L4` | `mixed` | `mixed/segments` | `SOURCE_BODY` | `hypothesis` |
| `kitchen-sink--la-balanguera@L5` | `mixed` | `mixed/segments` | `SOURCE_BODY` | `hypothesis` |
| `kitchen-sink--la-balanguera@L6` | `mixed` | `mixed/segments` | `SOURCE_BODY` | `hypothesis` |
| `kitchen-sink--hyttevask@L1` | `mixed` | `mixed/segments` | `SOURCE_BODY` | `hypothesis` |
| `kitchen-sink--hyttevask@L2` | `mixed` | `mixed/segments` | `SOURCE_BODY` | `hypothesis` |
| `kitchen-sink--hyttevask@L3` | `mixed` | `mixed/segments` | `SOURCE_BODY` | `hypothesis` |
| `kitchen-sink--hyttevask@L4` | `mixed` | `mixed/segments` | `SOURCE_BODY` | `hypothesis` |
| `kitchen-sink--hyttevask@L5` | `mixed` | `mixed/segments` | `SOURCE_BODY` | `hypothesis` |
| `kitchen-sink--hyttevask@L6` | `mixed` | `mixed/segments` | `SOURCE_BODY` | `hypothesis` |
| `sfr-series--thunder-quads@L1` | `threshold` | `threshold/intervals` | `SOURCE_BODY` | `hypothesis` |
| `sfr-series--thunder-quads@L2` | `threshold` | `threshold/intervals` | `SOURCE_BODY` | `hypothesis` |
| `sfr-series--thunder-quads@L3` | `threshold` | `threshold/intervals` | `SOURCE_BODY` | `hypothesis` |
| `sfr-series--thunder-quads@L4` | `threshold` | `threshold/intervals` | `SOURCE_BODY` | `hypothesis` |
| `sfr-series--thunder-quads@L5` | `threshold` | `threshold/intervals` | `SOURCE_BODY` | `hypothesis` |
| `sfr-series--thunder-quads@L6` | `threshold` | `threshold/intervals` | `SOURCE_BODY` | `hypothesis` |
| `sfr-series--blood-pistons@L1` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |
| `sfr-series--blood-pistons@L2` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |
| `sfr-series--blood-pistons@L3` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |
| `sfr-series--blood-pistons@L4` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |
| `sfr-series--blood-pistons@L5` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |
| `sfr-series--blood-pistons@L6` | `threshold` | `threshold/segments` | `SOURCE_BODY` | `hypothesis` |

## Appendix 6 — complete initial `quality_gates/v1`

The YAML below is the complete initial content of
`athletes/config/quality_gates.yaml`, including ordering. It translates the
experimental scorer's named VO2 and W′ sets and its inclusive 8–14 minute and
0–6 kJ bands (`experimental-workout-library/score_library.py:28-42,45-82`)
to Appendix 4 IDs. The reference scorer is Appendix 6 plus §1; the experimental
program is evidence, not a runtime dependency. Every initial record is a
hypothesis. Apart from the two named diagnostic sets, every non-assessment,
non-free row is dose-only. Assessment and pure-free rows are identity/structure
only and are never dose-gated.

```yaml
schema_version: quality_gates/v1
registry_version: quality_gates/v1
purpose_registry_version: purpose_registry/v1
scorer_version: earned_selection_scorer/v1
rule_registry_version: rule_registry/v1
owner_id: matti-gravel-god
evaluation_order:
  - PURPOSE_T_AT_VO2MAX/v1
  - PURPOSE_WBAL_NADIR/v1
  - PURPOSE_DOSE_TOTALITY/v1
  - PURPOSE_IDENTITY_STRUCTURE/v1
  - Q3_MIN_DESIGN_TSS_DELTA/v1
  - Q3_MIN_DENSITY_DELTA/v1
gates:
  - gate_id: PURPOSE_T_AT_VO2MAX
    gate_version: v1
    purpose_subtype: vo2max/*
    metric: t_at_vo2max_seconds
    operator: inclusive_between
    threshold: {minimum: 480, maximum: 840}
    unit: seconds
    applicability:
      scope: native_row_and_final_cycling_session
      archetype_ids:
        - vo2max--5x3-vo2-classic
        - vo2max--vo2max-30-30
        - vo2max--ronnestad-40-20
        - race-simulation--hard-starts
        - vo2max--descending-vo2-pyramid
        - durability--tired-vo2max
        - vo2max--vo2max-with-loaded-recovery
        - durability--late-race-vo2max
        - durability--tired-30-30s
      levels: [1, 2, 3, 4, 5, 6]
      require_power_control: true
      exclude_is_assessment: true
    aggregation: per_row_or_session_main_set
    evidence_basis: experimental_scorer_vo2_set_and_band
    owner_id: matti-gravel-god
    status: hypothesis
    effective_from: null

  - gate_id: PURPOSE_WBAL_NADIR
    gate_version: v1
    purpose_subtype: wprime_drain/*
    metric: wbal_nadir_kj
    operator: inclusive_between
    threshold: {minimum: 0.0, maximum: 6.0}
    unit: kilojoules
    applicability:
      scope: native_row_and_final_cycling_session
      archetype_ids:
        - g-spot--g-spot-criss-cross
        - vo2max--float-sets
        - tt-threshold--criss-cross-intervals
        - critical-power--above-cp-repeats
        - critical-power--w-prime-depletion
        - anaerobic-capacity--2min-killers
        - inscyd--glycolytic-power
        - sprint-neuromuscular--peak-and-fade
      levels: [1, 2, 3, 4, 5, 6]
      require_power_control: true
      exclude_is_assessment: true
    aggregation: per_row_or_session_main_set
    evidence_basis: experimental_scorer_wbal_set_band_and_sibling_recurrence
    owner_id: matti-gravel-god
    status: hypothesis
    effective_from: null

  - gate_id: PURPOSE_DOSE_TOTALITY
    gate_version: v1
    purpose_subtype: '*'
    metric: prescribed_dose_record
    operator: totality_and_native_adjacent_nonregression
    threshold: {minimum_trace_seconds: 1, require_design_if: true, require_design_tss: true, require_design_kj: true, native_min_design_tss_delta: 0.0, native_min_trace_seconds_delta: 0}
    unit: canonical_dose_record
    applicability:
      scope: native_row_and_final_cycling_session
      include_purpose_classes: [vo2max, wprime_drain, threshold, endurance, recovery, openers, race_sim, mixed]
      exclude_archetype_ids:
        - vo2max--5x3-vo2-classic
        - vo2max--vo2max-30-30
        - vo2max--ronnestad-40-20
        - race-simulation--hard-starts
        - vo2max--descending-vo2-pyramid
        - durability--tired-vo2max
        - vo2max--vo2max-with-loaded-recovery
        - durability--late-race-vo2max
        - durability--tired-30-30s
        - g-spot--g-spot-criss-cross
        - vo2max--float-sets
        - tt-threshold--criss-cross-intervals
        - critical-power--above-cp-repeats
        - critical-power--w-prime-depletion
        - anaerobic-capacity--2min-killers
        - inscyd--glycolytic-power
        - sprint-neuromuscular--peak-and-fade
      exclude_is_assessment: true
      exclude_pure_free: true
    aggregation: native_L1_totality_then_each_adjacent_level;final_session_totality
    evidence_basis: experimental_scorer_dose_only_plus_r4_totality_contract
    owner_id: matti-gravel-god
    status: hypothesis
    effective_from: null

  - gate_id: PURPOSE_IDENTITY_STRUCTURE
    gate_version: v1
    purpose_subtype: assessment/*|free/*
    metric: identity_structure_record
    operator: exact_contract_match
    threshold: {require_declared_duration: true, require_intended_structure: true, require_truthful_free_targets: true}
    unit: contract_record
    applicability:
      scope: native_row_and_final_cycling_session
      include_purpose_classes: [assessment, free]
      dose_gate: false
    aggregation: per_row_or_session
    evidence_basis: r4_assessment_and_free_contract
    owner_id: matti-gravel-god
    status: hypothesis
    effective_from: null

  - gate_id: Q3_MIN_DESIGN_TSS_DELTA
    gate_version: v1
    purpose_subtype: '*'
    metric: next_design_tss_minus_prior_design_tss
    operator: greater_than_or_equal
    threshold: 1.0
    unit: design_tss
    applicability:
      scope: native_adjacent_level_transition
      levels: [L1_to_L2, L2_to_L3, L3_to_L4, L4_to_L5, L5_to_L6]
      require_both_prescribed_traces_nonempty: true
    aggregation: fail_archetype_and_all_six_rows_on_any_failed_transition
    evidence_basis: r4_initial_q3_hypothesis
    owner_id: matti-gravel-god
    status: hypothesis
    effective_from: null

  - gate_id: Q3_MIN_DENSITY_DELTA
    gate_version: v1
    purpose_subtype: '*'
    metric: next_design_tss_per_minute_minus_prior_design_tss_per_minute
    operator: greater_than_or_equal
    threshold: -0.05
    unit: design_tss_per_minute
    applicability:
      scope: native_adjacent_level_transition
      levels: [L1_to_L2, L2_to_L3, L3_to_L4, L4_to_L5, L5_to_L6]
      require_both_prescribed_traces_nonempty: true
    aggregation: fail_archetype_and_all_six_rows_on_any_failed_transition
    evidence_basis: r4_initial_q3_hypothesis
    owner_id: matti-gravel-god
    status: hypothesis
    effective_from: null
```

Applicability is closed and ordered. For each native row or final cycling session,
select the first matching one of `PURPOSE_T_AT_VO2MAX`,
`PURPOSE_WBAL_NADIR`, `PURPOSE_DOSE_TOTALITY`, and
`PURPOSE_IDENTITY_STRUCTURE`; exactly one MUST match. Zero or multiple matches
is `UNAVAILABLE`. Q3 records additionally apply to every defined adjacent native
transition. The four-entry version vector in Appendix 2 pins this registry,
purpose registry, scorer, and rule registry together; a consumer MUST reject a
component-wise mismatch.

For `PURPOSE_DOSE_TOTALITY`, L1 passes observation only when its complete dose
record is finite/non-empty; each L2–L6 row additionally requires its unrounded
`design_tss >=` the prior level and its `trace_seconds >=` the prior level.
This is the experimental scorer's “everything else = dose-only” comparison,
translated from its TSS/minute fields to the normative §1 dose. A final session
has no adjacent library meaning and therefore applies only the totality part.
The separate Q3 hypotheses still apply to native transitions and neither gate
substitutes for the other.

## Appendix 7 — closed `FinalPlanCandidate/v1`

This is the immutable D1 input schema. No extra keys are allowed at any level;
arrays have the orders stated below. `sha256` means a lower-case 64-character
SHA-256. Nullable fields are present with `null`; omission is invalid.

```
{
  "schema_version": "FinalPlanCandidate/v1",
  "generation_revision": positive integer,
  "generated_at": ISO-8601-UTC string,
  "mode": "A" | "B",
  "version_vector": {
    "purpose_registry_version": "purpose_registry/v1",
    "gate_registry_version": "quality_gates/v1",
    "scorer_version": "earned_selection_scorer/v1",
    "rule_registry_version": "rule_registry/v1"
  },
  "athlete": {
    "athlete_id": string,
    "training_age_years": non-negative number | null,
    "available_cycling_hours": positive number | null,
    "available_cycling_days": integer 0..7 | null,
    "preferred_off_days": [lower-case weekday, ...],
    "strength_declined": boolean,
    "requested_metric": "power" | "hr" | "rpe",
    "control_metric": "power" | "hr" | "rpe",
    "control_basis": "ftp" | "lthr" | "hrmax" | "rpe" | "rpe_pending_lthr"
  },
  "race": {
    "race_id": string | null,
    "race_date": YYYY-MM-DD string,
    "discipline": "gravel" | "road" | "mtb",
    "priority": "A"
  },
  "plan": {
    "methodology_id": string,
    "render_style": "POLARIZED" | "G_SPOT" | "PYRAMIDAL",
    "calendar_start": YYYY-MM-DD string,
    "calendar_end": YYYY-MM-DD string,
    "weekly_structure_prescribes_strength": boolean
  },
  "config_digests": {
    "archetype_ids": sha256,
    "purpose_registry": sha256,
    "quality_gates": sha256,
    "rule_registry": sha256,
    "producer_registry": sha256,
    "phase_purpose_registry": sha256,
    "methodologies": sha256,
    "methodology_profiles": sha256,
    "fueling_policy": sha256,
    "plan_dates": sha256,
    "weekly_structure": sha256,
    "block_notes": sha256,
    "strength_periodization": sha256,
    "tss_guardrails": sha256
  },
  "guide_inputs": [
    {"path": repo-relative string, "sha256": sha256}, ...
  ],
  "weeks": [
    {
      "week": integer including 0,
      "monday": YYYY-MM-DD string,
      "sunday": YYYY-MM-DD string,
      "cycling_phase": "transition" | "base" | "build" | "race_prep" | "maintenance" | "racing" | null,
      "week_type": "load" | "testing" | "recovery" | "taper" | "race" | "medium" | "uber_load" | null,
      "meso_block_id": string | null,
      "meso_block_index": non-negative integer within cycling phase | null,
      "ordinal_in_meso_block": positive integer | null,
      "is_paid": boolean,
      "is_race_week": boolean,
      "block_note_template_id": "load" | "medium" | "recovery" | "race" | "uber_load" | null,
      "available_cycling_hours": positive number | null,
      "target_cycling_tss": non-negative number | null,
      "reported_cycling_tss": non-negative number | null,
      "strength_prescribed": boolean,
      "weekly_structure_state": "DECLINED" | "PRESCRIBES_STRENGTH" | "DOES_NOT_PRESCRIBE" | "MISSING" | "MALFORMED",
      "strength_artifact_state": "VALID" | "ABSENT" | "MALFORMED" | "CONTRADICTORY",
      "strength_phase": "AA" | "max_strength" | "maintenance" | "maintenance_reduced" | "key_lifts" | "deload" | null,
      "strength_frequency": integer 0..3,
      "session_ids": [string, ...]
    }, ...
  ],
  "sessions": [
    {
      "id": "wNN.YYYY-MM-DD.OO",
      "week": integer including 0,
      "date": YYYY-MM-DD string,
      "daily_ordinal": positive integer,
      "title": string,
      "description": string,
      "sport": "cycling" | "strength" | "rest",
      "session_type": string,
      "role": "intensity" | "long_ride" | "filler" | "off" | "strength" | "race" | "travel" | "athlete_fixed" | null,
      "origin": one §4.4 discriminant,
      "is_assessment": boolean,
      "fueling_source_tier": "quality" | "long_ride" | "race_sim" | "empty" | null,
      "fueling_class": "HIGH" | "LONG_RIDE" | "RACE" | "NONE" | null,
      "duration_s": non-negative integer | null,
      "tss": non-negative number | null,
      "tss_planned": non-negative number | null,
      "total_time_planned": non-negative number,
      "tp_kind": "bike" | "strength" | "race" | "day_off",
      "workout_type_value_id": integer | null,
      "control_metric": "power" | "hr" | "rpe" | "none" | null,
      "control_basis": string | null,
      "target_summary": string | null,
      "purpose": {
        "class": string,
        "subtype": string,
        "assignment_status": "hypothesis" | "calibrated",
        "main_set_rule": string,
        "main_set_segment_ids": [string, ...]
      } | null,
      "segments": [
        {
          "id": "seg-NNNN",
          "name": string,
          "seconds": non-negative integer,
          "kind": "steady" | "ramp" | "warmup" | "cooldown" | "intervals" | "free_ride",
          "provenance_role": "renderer_warmup" | "source_body" | "renderer_cooldown",
          "target": {
            "type": "power_pct_ftp" | "pct_lthr" | "pct_hrmax" | "rpe" | "free",
            "value": number | null,
            "low": number | null,
            "high": number | null,
            "on": number | null,
            "off": number | null
          },
          "repeat": positive integer | null,
          "on_seconds": non-negative integer | null,
          "off_seconds": non-negative integer | null
        }, ...
      ],
      "archetype": {
        "archetype_id": string,
        "level": integer 1..6,
        "category": string,
        "variation": positive integer,
        "manifest_row_id": string
      } | null,
      "series": {
        "series_id": string,
        "series_index": positive integer,
        "series_total": positive integer,
        "tracker_slot": string,
        "raw_display_name": string,
        "family_key": string,
        "resolved_replacement_id": string | null
      } | null,
      "strength": {
        "artifact_present": boolean,
        "artifact_valid": boolean,
        "template_id": string | null,
        "phase": "AA" | "max_strength" | "maintenance" | "maintenance_reduced" | "key_lifts" | "deload" | null,
        "intensity": "adaptation" | "max" | "heavy" | "maintenance" | "reduced" | "key_lifts" | "deload" | null,
        "frequency": integer 0..3
      } | null,
      "race": {"priority": "A" | "B", "race_id": string | null} | null,
      "provenance": {
        "producer_id": string,
        "producer_version": string,
        "template_id": string,
        "template_version": string,
        "source_digests": [{"path": repo-relative string, "sha256": sha256}, ...],
        "transformation_parameters": canonical-JSON object,
        "overlay_ids": [string, ...]
      }
    }, ...
  ]
}
```

Weeks sort by `week`; sessions and each week's `session_ids` sort by
`(week,date,daily_ordinal)`; segments retain final emitted order; digest lists
sort by path and overlays lexicographically. A non-cycling session has
`fueling_source_tier:null` and `fueling_class:null`; every cycling session has
one non-null source tier and one non-null class. A
non-strength session has `strength:null`; only an actually emitted strength
artifact becomes a session. A prescribed-but-absent artifact is represented by
the week's `strength_artifact_state:ABSENT`, so R11 fails without inventing a
training session or athlete-visible operation.

### A7.1 Exact field derivation

| Candidate field(s) | Derivation authority |
|---|---|
| generation revision/time, athlete/race facts | Copy the same keys from `profile.json.fulfillment`, athlete facts, and target race used by Phase 3 canonical construction; the current builder reads revision/time at `build/trustworthy-phase3:athletes/scripts/canonical_training_model.py:529-539`. |
| mode and version vector | E1 materializes mode from rollout config and copies the exact Appendix 2 vector; component digests are checked before freeze. |
| methodology/render style | Exact §4.7 lookup from `profile.json.methodology.id`; unknown/missing is a generation failure. |
| control fields | Copy Phase 3's selected control contract; its HR/RPE selection is at `build/trustworthy-phase3:athletes/scripts/canonical_training_model.py:43-65`. |
| config digests and guide inputs | **NEW E1:** hash the exact bytes loaded by selection, scoring, block notes, strength, and guide generation. `guide_inputs` is the complete consumed path set, not an allow-list; D2 must repeat the same path→digest map. |
| week, dates, phase, week type, block-note template | Copy calendar week number/dates and normalize phase/week type by Appendix 3 A3.1. Resolve `block_note_template_id` by exact key in `block_notes.yaml`; an intentionally unsupported testing/taper key is null and makes R07/R25 unavailable, not guessed. Calendar creation and recovery marking are at `athletes/scripts/calculate_plan_dates.py:193-216,245-268`; block-chain peak normalization is at `athletes/scripts/block_chain.py:25-60`. |
| meso block fields | **NEW E1:** materialize A3.1's maximal contiguous block and globally stable ID `meso-{zero-based-plan-index:03d}`; `meso_block_index` resets to 0 on each cycling-phase change, and `ordinal_in_meso_block` resets to 1 on each new block. Thus “first base meso block” in R12 is exactly base index 0. |
| reported weekly TSS | Copy the final block-builder week's `total_tss`, after fixed-session and overlay materialization and before D1. The builder writes that field at `athletes/scripts/block_builder.py:555-561`. It is never recomputed from report gates. |
| target weekly TSS | **NEW E1:** select the guardrail row from available hours using half-open boundaries `0≤h<8→time_crunched`, `8≤h<12→specialist`, `12≤h<15→volume`, and `h≥15→goat`; these resolve the touching ranges in `athletes/config/tss_guardrails.yaml:7-39` without hard-failing an above-range athlete. For load/testing/medium use the midpoint of its `load_tss` band, for `uber_load` use its upper bound, for recovery use the midpoint of `recovery_tss`, and for taper/race use `null`. No rounding precedes R16. |
| strength prescription/frequency/state | **NEW E1 projection:** for each paid week, validate the chosen `weekly_structure.json`, materialize the five-state `weekly_structure_state`, and inspect `days.*.{am,pm}` only when valid; count exact value `strength` after scheduling, capped at the source table's 3. Independently validate emitted strength artifacts into the four-state `strength_artifact_state`. The source builder emits slots at `athletes/scripts/build_weekly_structure.py:58-148`. Copy `strength_declined` before applying the R11 table. |
| strength phase/intensity | **NEW E1:** materialize Appendix 3 A3.2's complete table and the resolved strength artifact/template; do not use display text. |
| session identity/order and legacy session fields | Copy the final `_bb_plan.weeks[].days[]`/overlay record after all mutations. Assign ID by §4.10. **NEW E1 sport normalization:** emitted bike/race/rest-sentinel ZWO → `cycling`, emitted strength artifact → `strength`, and zero-artifact `CANONICAL_REST` → `rest`; retain the original TP distinction in `tp_kind`. Phase 3's corresponding canonical projection fields are at `build/trustworthy-phase3:athletes/scripts/canonical_training_model.py:481-533`. |
| role | Copy block-builder `day.role` for block sessions (the producer writes intensity/long_ride/filler/off at `athletes/scripts/block_builder.py:348-405`). **NEW E1:** each Appendix 8 non-block template supplies its closed fallback role; no title inference. |
| origin/is_assessment | **NEW E1:** the emitting branch writes exactly one §4.4 origin and copies Appendix 5/8's boolean assessment contract before common projection. |
| fueling source tier/class | **NEW E1:** refactor `_get_fuel_tag_for_type` to return its already-selected tier alongside the existing rendered string, then project that tier through §4.4.1. A/B event producers write `race_sim`; the enumerated no-prose cases write `empty`. Athlete fueling bytes are not parsed or changed. |
| purpose/main-set IDs | Native: copy the exact Appendix 5 row then materialize its rule over segment provenance. Non-native: copy Appendix 8. Assessment status keys only from `is_assessment`. |
| segment/target fields | Copy the final typed source structure, assign IDs/provenance before projection, then use Phase 3's canonical target transform (`build/trustworthy-phase3:athletes/scripts/canonical_training_model.py:148-194`). All nullable target keys shown in the schema are materialized, even when unused. |
| archetype/series | Native identity comes from Appendix 4 before render. Series copies the block-builder tracker tuple now created from block/day/name at `athletes/scripts/generate_athlete_package.py:2227-2244,2309-2321`; **NEW E1** also stores tracker slot, raw name, A3.3 family key, and the exact tombstone replacement resolved before series start (null otherwise). |
| provenance | **NEW E1:** the selected Appendix 8/native contract supplies producer/template IDs and versions; hash exact producer/template source bytes and record every dose-affecting scale/cap/overlay parameter. Empty arrays/objects remain present. |
| race and TP projection fields | Copy the final emitter record and PlanIR values; Phase 3 defines these session fields at `build/trustworthy-phase3:athletes/scripts/plan_ir.py:78-121`. |

D1 is the SHA-256 of canonical JSON of exactly this object. E1 MUST prove that
freezing the candidate and building the canonical model preserves ordered
session-ID equality and every content field consumed by a TP operation.

## Appendix 8 — closed non-native producer/template registry

E1 writes the exact semantic content below to
`athletes/config/non_native_producers.yaml` with
`registry_version: non_native_producers/v1`. Producer versions identify code
contracts; template versions identify closed structural data. Runtime source
digests still pin exact bytes. IDs are case-sensitive. Native and legacy-Nate
sessions resolve through Appendix 4/5 and the manifest instead and MUST NOT be
entered here.

| Origin | producer ID / version | Allowed template IDs / version | Purpose; role; assessment |
|---|---|---|---|
| `MAPPER_SIMPLE_ENDURANCE` | `workout_mapper.simple_endurance` / `v1` | `simple_endurance` / `v1`; level parameter 1–6 | `endurance/steady`; `filler`; false |
| `PROGRESSIVE_INTERVAL_GENERATOR` | `workout_library.progressive_interval` / `v1` | the 11 exact A8.1 interval IDs / `v1` | A8.1; `intensity`; false |
| `PROGRESSIVE_ENDURANCE_GENERATOR` | `workout_library.progressive_endurance` / `v1` | the six exact A8.1 endurance IDs / `v1` | A8.1; `filler`; false |
| `STANDARD_BLOCK_GENERATOR` | `generate_athlete_package.standard_blocks` / `v1` | the 22 exact A8.2 IDs / `v1` | A8.2 |
| `PRE_PLAN_GENERATOR` | `generate_athlete_package.pre_plan` / `v1` | `pre_plan_easy`, `pre_plan_rest` / `v1` | A8.3 |
| `REST_SENTINEL_ZWO` | `generate_athlete_package.rest_sentinel` / `v1` | `rest_60s_30pct` / `v1` | `recovery/rest_sentinel`; `off`; false |
| `A_RACE_FREERIDE` | `generate_athlete_package.a_race` / `v1` | `a_race_freeride` / `v1` | `free/race_event`; `race`; false |
| `B_RACE_FREERIDE` | `generate_athlete_package.b_race` / `v1` | `b_race_freeride` / `v1` | `free/race_event`; `race`; false |
| `TRAVEL_SHAKEOUT` | `generate_athlete_package.travel_shakeout` / `v1` | `travel_shakeout_30m` / `v1` | `recovery/shakeout`; `travel`; false |
| `ATHLETE_FIXED` | `canonical_training_model.athlete_fixed` / `v1` | `athlete_fixed` / `v1` | `free/external_fixed`; `athlete_fixed`; copied explicit assessment flag, initially false |
| `CANONICAL_REST` | `plan_ir.canonical_rest` / `v1` | `canonical_rest_zero` / `v1` | `free/rest`; `off`; false |
| `STRENGTH_TEMPLATE` | `generate_athlete_package.strength_template` / `v2` | the 12 exact A8.3 strength IDs / `strength_periodization/v2` | no cycling purpose; `strength`; false |

Every cycling contract above also carries
`assignment_status:hypothesis`. Its `main_set_rule` is `ASSESSMENT_BODY` only
for `STANDARD_BLOCK_GENERATOR/FTP_Test`; it is `NONE` for `pre_plan_rest`, both
race FreeRides, `ATHLETE_FIXED`, and `CANONICAL_REST`; it is `SOURCE_BODY` for
every other cycling tuple. Strength has null cycling purpose/rule. E1
materializes segment provenance before applying these rules exactly as it does
for Appendix 5; no non-native title heuristic is permitted.

### A8.1 Progressive template assignments

The interval names and phase fallback are the executable lists at
`athletes/scripts/workout_library.py:18-39,131-143`; any phase other than
`peak` selects the build list. E1 translates calendar `race_prep` to producer
phase `peak` before selection and records that transformation.

| Template ID | Returned producer name | Purpose |
|---|---|---|
| `tempo_intervals` | Tempo Intervals | `threshold/long_intervals` |
| `sweet_spot_blocks` | Sweet Spot Blocks | `threshold/sweet_spot` |
| `threshold_builders` | Threshold Builders | `threshold/long_intervals` |
| `over_unders` | Over-Unders | `wprime_drain/over_under` |
| `threshold_classics` | Threshold Classics | `threshold/long_intervals` |
| `race_pace_blocks` | Race Pace Blocks | `threshold/race_pace` |
| `vo2_starters` | VO2 Starters | `vo2max/steady` |
| `vo2_builders` | VO2 Builders | `vo2max/steady` |
| `vo2_classics` | VO2 Classics | `vo2max/steady` |
| `vo2_extended` | VO2 Extended | `vo2max/steady` |
| `vo2_race_prep` | VO2 Race Prep | `vo2max/steady` |

The endurance list is exact at
`athletes/scripts/workout_library.py:41-49,150-158`:

| Template ID | Returned producer name | Purpose |
|---|---|---|
| `z2_steady` | Z2 Steady | `endurance/steady` |
| `z2_cadence` | Z2 Cadence | `endurance/cadence` |
| `z2_single_leg` | Z2 Single Leg | `endurance/drills` |
| `z2_big_gear` | Z2 Big Gear | `endurance/strength_endurance` |
| `z2_spin_ups` | Z2 Spin Ups | `endurance/spinups` |
| `z2_tempo_touch` | Z2 Tempo Touch | `mixed/endurance_surges` |

### A8.2 Standard-block template assignments

These are all non-null branches of `create_workout_blocks` at
`athletes/scripts/generate_athlete_package.py:1237-1553`.
`Intervals` and `VO2max` return `None` and MUST resolve to the progressive
producer, so they are deliberately excluded. The former unknown-type steady
fallback is no longer an allowed contract: E1 rejects an ID outside this table
before render.

| Template ID | Purpose | Role | `is_assessment` |
|---|---|---|---|
| `Recovery` | `recovery/steady` | `filler` | false |
| `Easy` | `recovery/easy` | `filler` | false |
| `Shakeout` | `recovery/shakeout` | `filler` | false |
| `Endurance` | `endurance/steady` | `filler` | false |
| `Tempo` | `threshold/tempo` | `intensity` | false |
| `Openers` | `openers/short` | `intensity` | false |
| `FTP_Test` | `assessment/ftp` | `intensity` | true |
| `Long_Ride` | `endurance/long` | `long_ride` | false |
| `Race_Sim` | `race_sim/standard` | `intensity` | false |
| `Sweet_Spot` | `threshold/sweet_spot` | `intensity` | false |
| `G_Spot` | `threshold/g_spot` | `intensity` | false |
| `Over_Under` | `wprime_drain/over_under` | `intensity` | false |
| `Blended` | `mixed/blended` | `intensity` | false |
| `Threshold` | `threshold/steady` | `intensity` | false |
| `Anaerobic` | `wprime_drain/anaerobic` | `intensity` | false |
| `Sprints` | `wprime_drain/sprint` | `intensity` | false |
| `Over_Unders` | `wprime_drain/over_under` | `intensity` | false |
| `SFR` | `threshold/sfr` | `intensity` | false |
| `Mixed_Climbing` | `mixed/climbing` | `intensity` | false |
| `Cadence_Work` | `endurance/cadence` | `filler` | false |
| `Durability` | `mixed/durability` | `intensity` | false |
| `Pre_Plan_Easy_Blocks` | `recovery/easy` | `filler` | false |

The last ID denotes only the standard block body reused by
`PRE_PLAN_GENERATOR/pre_plan_easy`; the emitting origin remains
`PRE_PLAN_GENERATOR`, so R21 resolves the pre-plan tuple in A8.3 rather than
serializing two origins. B-race opener/easy overlays remain
`STANDARD_BLOCK_GENERATOR/Openers` and `STANDARD_BLOCK_GENERATOR/Easy`;
their required `overlay_ids` are `b_race_opener/v1` and
`b_race_easy/v1`, respectively.

### A8.3 Bespoke, fixed, and strength assignments

`PRE_PLAN_GENERATOR/pre_plan_easy` uses
`STANDARD_BLOCK_GENERATOR/Pre_Plan_Easy_Blocks/v1` as a nested source contract;
`pre_plan_rest` is exactly one 60-second FreeRide. The current pre-plan branch
is at `athletes/scripts/generate_athlete_package.py:1900-1974`.
The rest sentinel is one 60-second 30% steady segment
(`athletes/scripts/generate_athlete_package.py:2442-2482`); the B-race
FreeRide and travel structures are at
`athletes/scripts/generate_athlete_package.py:2024-2128`; A-race is at
`:2569-2665`. Athlete-fixed has no invented segments
(`build/trustworthy-phase3:athletes/scripts/canonical_training_model.py:333-351`).

The complete strength template ID set introduced by E1 for Appendix 3 A3.2 is:

```
aa_a
aa_b
aa_c
max_strength_a
max_strength_b
max_strength_c
maintenance_a
maintenance_b
maintenance_reduced_a
maintenance_reduced_b
key_lifts_a
deload_a
```

Frequency two uses `_a` then `_b`; frequency three additionally uses `_c`, only
for AA/max-strength where it is listed. Key-lifts/deload are capped at one.
`maintenance_b` and `maintenance_reduced_b` are **NEW E1**;
the current helper has only one maintenance reference and caps taper/race
(`athletes/scripts/generate_athlete_package.py:125-160`). The other new
phase-specific IDs adapt the owner-approved cycling→strength table rather than
reusing the current base/build/peak names.

R21 exact-matches all five provenance fields. A producer may consume another
registered structural body, as pre-plan easy does, but only the outer emitter's
origin tuple is serialized. Unknown producer/template/version, a template under
the wrong producer, missing source digest, or template purpose/assessment
mismatch is `FAIL`; malformed registry bytes are `UNAVAILABLE`. The
reachability fixture enumerates every tuple above and fails on either an
unreached allowed tuple or an emitted unregistered tuple.
