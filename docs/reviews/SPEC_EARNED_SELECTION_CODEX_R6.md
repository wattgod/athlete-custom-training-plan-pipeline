# Adversarial Review: `SPEC_EARNED_SELECTION` — Round 6

Review target: `docs/SPEC_EARNED_SELECTION.md` at `b270b20`

## Verdict

**GO — 0 blockers.**

r6 resolves both R5 blockers without reopening any previously settled contract.
The new legacy projection is D1-bound, contains the complete value set read by
the nine real `block_compliance.py` rules, and preserves production's asymmetric
R02 race-week behavior. The three R5-02 target constructions are now
deterministic: both R02 edges use the complete exemption, R06 has an exhaustive
applicability set, and R04 consumes a named per-session `progression_level` whose
only live non-native value is traced to the actual mapper parameter.

The requested registry, identity, report, seal, state, and TrainingPeaks surfaces
remain intact. The remaining observations are editorial or are acceptance work
already required by the spec; none requires policy invention.

## R5 blocker verification

| R5 blocker | r6 disposition | Verification |
|---|---|---|
| R5-01 — legacy verdict not D1-closed and R02 not production-equivalent | **RESOLVED** | Appendix 7 now defines `legacy_compliance_projection/v1` with the three validator arguments, ordered weeks/days, raw `plan_week`, `phase`, `week_type`, `total_tss`, `total_duration`, raw day/name/role/durations, nested fixed-session intensity, and root `all_violations` (`docs/SPEC_EARNED_SELECTION.md:3137-3163`). Its source, absence materialization, embedded digest, and exclusive A3.0 authority are explicit (`docs/SPEC_EARNED_SELECTION.md:3281-3309`). D1 includes it and every E1/E2 legacy row binds its metric to its digest (`docs/SPEC_EARNED_SELECTION.md:485-490,532-537`). A3.0 now separates R02's applicable-week count from its stimulus scan exactly as production does, and explicitly retains race-typed stimulus (`docs/SPEC_EARNED_SELECTION.md:1568,1587`). The finite differential corpus is mandatory and inequality fails E1/E2 (`docs/SPEC_EARNED_SELECTION.md:1596-1624`). I re-executed the R5 construction: four base/load weeks without VO2 plus one base/race week named `VO2max 30/30`; production returned `True` and the literal r6 adapter returned `True`. |
| R5-02 — R02/R06 ambiguity and missing R04 non-native level path | **RESOLVED** | R02 now applies the same complete exemption to both edge selectors and includes the exact transition-suffix counterexample; January 10 to January 25 is 15 days and passes while the February 8 transition/load week is excluded (`docs/SPEC_EARNED_SELECTION.md:1646-1682`). R06 is exactly paid, non-transition, exact-load, with positive/negative fixtures for load plus every excluded type, transition/load, and W00 (`docs/SPEC_EARNED_SELECTION.md:1740-1768,1905`). `progression_level` is required and nullable on every candidate session (`docs/SPEC_EARNED_SELECTION.md:3203,3320-3323`); R04 consumes only that field (`docs/SPEC_EARNED_SELECTION.md:1709-1738,1903`). Appendix 8 supplies the value for every non-native contract and correctly makes `MAPPER_SIMPLE_ENDURANCE` the sole non-native non-null case (`docs/SPEC_EARNED_SELECTION.md:3404-3422`). Phase 3 reads `bb_level=bb_day.get('level',3)` and passes it unchanged as `level=bb_level` (`build/trustworthy-phase3:athletes/scripts/generate_athlete_package.py:2173-2180,2269-2277`); `workout_mapper` passes that level into `_render_simple_endurance`, whose 1–6 table controls the rendered duration (`athletes/scripts/workout_mapper.py:208-215,256-275`). Null for contracts with no level concept is a closed value and explicitly yields `UNAVAILABLE`, not invented L1. |

## R5-01 field-read audit

I compared the projection against every `.get(...)` used by the live helpers and
nine verdict functions in `athletes/scripts/block_compliance.py`:

| Production read family | Projection field(s) | Result |
|---|---|---|
| Validator inputs/root | `target_hours`, `off_days`, `max_intensity`, `weeks`, `all_violations` plus presence | Complete |
| Week classification/accounting | `plan_week`, `phase`, `week_type`, `total_tss`, `total_duration`, ordered `days` | Complete |
| Day classification | `day`, `name`, `role`, ordered `sessions[].intensity` | Complete |
| R06 duration fallback | nullable `workout.duration` and top-level `duration` | Complete |

Those are exactly the decision inputs read at
`athletes/scripts/block_compliance.py:58-75,78-90,93-269,284-344` and the three
arguments supplied at
`build/trustworthy-phase3:athletes/scripts/generate_athlete_package.py:814-822`.
The source producer always supplies the normal week/day shape; fixed sessions
append only the raw `sessions` entries and update the two totals
(`build/trustworthy-phase3:athletes/scripts/availability_ledger.py:88-118`). No
legacy evaluator needs normalized candidate purpose, title, archetype, or segment
data.

The R02 adapter is now verdict-equivalent on the disputed branch:

- Production excludes `week_type=race` from `non_racing_weeks` but does not skip
  it in the separate VO2 scan
  (`athletes/scripts/block_compliance.py:117-135`).
- r6 publishes the same asymmetry and names it explicitly
  (`docs/SPEC_EARNED_SELECTION.md:1568`).
- The required golden records production `True` equal to adapter `True`
  (`docs/SPEC_EARNED_SELECTION.md:1587`).

## R5-02 adversarial constructions

### R02 trailing transition/load week

Using the R5 dates, r6 selects the January 25 end of the last non-exempt
base/load week, not the February 8 transition/load week. The suffix is
`2026-01-25 - 2026-01-10 = 15` days, so it passes. The literal text both states
the shared predicate and fixes this expected result
(`docs/SPEC_EARNED_SELECTION.md:1667-1682`). There is no remaining conforming
29-day interpretation.

### R06 testing-week disagreement

The applicable set is no longer inferential. A paid, non-transition load week
returns PASS or FAIL from the exact long-ride disjunction; `testing`, `recovery`,
`taper`, `race`, `medium`, `uber_load`, transition/load, and unpaid W00 all return
`NOT_APPLICABLE` regardless of whether a qualifying session is present
(`docs/SPEC_EARNED_SELECTION.md:1740-1768`). I replayed the R5 testing-week case;
the r6 result is unambiguously `NOT_APPLICABLE`.

### R04 non-native endurance

The live block path obtains `bb_level` before render and passes the same value to
the mapper. The Endurance special case consumes that exact parameter and selects
the corresponding 1–6 duration row. r6 assigns that value to
`session.progression_level` for `MAPPER_SIMPLE_ENDURANCE`; it does not misuse the
generic transformation map or fabricate a native manifest row
(`docs/SPEC_EARNED_SELECTION.md:3360,3406,3419-3422`). All other Appendix 8
contracts state `null` because their producer has no 1–6 progression concept.
That distinction matches the live mapper/generator paths and makes every R04
input derivation closed.

## New blocking findings

None.

## Regression audit of the r6 edit

I extracted each requested section from r5 (`3cdf40a`) and r6 (`b270b20`) by
heading and compared its exact bytes.

| Surface | Result | Additional check |
|---|---|---|
| Purpose registry / Appendix 5 | **Intact; byte-identical** | 600 rows, 600 unique row IDs, 100 bases with six levels each, 24 `is_assessment=true`, and 18 `long_ride_registered=true` (`docs/SPEC_EARNED_SELECTION.md:2095-2873`). |
| Appendix 6 gate registry | **Intact; byte-identical** | The ordered nine VO2 IDs, eight W′ IDs, 480–840 second band, and 0–6 kJ band still exactly translate the sibling scorer at `experimental-workout-library/score_library.py:28-45` (`docs/SPEC_EARNED_SELECTION.md:2875-3061`). |
| TrainingPeaks inventory | **Intact; byte-identical** | The seven kinds and their complete payload comparisons remain at `docs/SPEC_EARNED_SELECTION.md:976-1000`; they exactly equal Phase 3's four dated, two singleton, and one entitlement kinds at `build/trustworthy-phase3:athletes/scripts/apply_contract.py:23-31,97-147`. |
| Seal v2 | **Intact; byte-identical** | Five-key source object, v1/v2 dispatch, backward verification, and stale-global-manifest behavior remain at `docs/SPEC_EARNED_SELECTION.md:907-949`. |
| `quality_findings` rail | **Intact; byte-identical** | v3 state ownership, replacement merge, rank, observation snapshot, and v2 migration remain at `docs/SPEC_EARNED_SELECTION.md:652-721`. |
| Session IDs/report roots | **Intact; byte-identical** | `wNN.date.ordinal`, collision failure, regeneration stability, and exactly two derived report roots remain at `docs/SPEC_EARNED_SELECTION.md:753-823`. |
| Appendix 4 ID map | **Intact; byte-identical** | Parsed 24 categories and 100 ordered names; exact category/name order matches live `archetype_registry.ALL_ARCHETYPES`, and every slug ID remains active with null replacement (`docs/SPEC_EARNED_SELECTION.md:1933-2093`). |
| Combined disposition map | **Consistent** | R4-04/R4-05 and both R5 rows describe the actual r6 changes without overclaiming (`docs/SPEC_EARNED_SELECTION.md:1170-1186`). |

The r6 diff changes only the legacy projection/verdict contract, the three R5-02
target closures, their acceptance fixtures, the disposition map, and one prior
R5 non-blocking authority link. It does not touch the byte-identical surfaces
above.

## Whole-spec consistency

- **Body ↔ appendices:** §4.5 freezes the projection into D1, A3.0 consumes only
  it, Appendix 7 defines and derives it, Appendix 2 carries the candidate digest
  plus per-row metric evidence, and Appendix 1 records the same disposition.
  These links are closed (`docs/SPEC_EARNED_SELECTION.md:485-537,1181-1186,
  1445-1457,3137-3163,3281-3309`).
- **Mode A/B:** Mode A still records observations as non-enforced while Mode B
  enforces calibrated gates (`docs/SPEC_EARNED_SELECTION.md:202-218,248-254`).
  The projection changes only how the nine pre-existing rubric verdicts are
  reproduced; it does not promote a hypothesis or activate an E3 target.
- **E1 audit-only:** E1/E2 keep only the nine existing production-equivalent
  blockers; every new or E3-target result remains a finding until E3
  (`docs/SPEC_EARNED_SELECTION.md:523-547,1072-1090`). The projection is an
  internal candidate/report field, and §6 explicitly excludes internal
  report/manifest/provenance data from athlete surfaces
  (`docs/SPEC_EARNED_SELECTION.md:1012-1015`). Q0 still requires byte identity
  for the full athlete-surface inventory (`docs/SPEC_EARNED_SELECTION.md:515-521,
  962-1023`).
- **Rollout authority:** r6 also closes R5's prior non-blocking note by requiring
  report `rollout_phase` to equal the digest-checked rollout file rather than a
  caller value (`docs/SPEC_EARNED_SELECTION.md:1520-1530`).

## Non-blocking findings

### NB-01 — Several revision labels still say r5

The live status is r6, but seven sentences still scope their statement to r5:
`docs/SPEC_EARNED_SELECTION.md:316,561,1019,1108,1917,1921,2262`. The governing
algorithms and dispositions are unambiguous, and the labels do not change a
verdict. Update these to r6 during ordinary editorial cleanup; do not alter
Appendix 6's `r4_*` evidence-basis identifiers, which intentionally identify the
evidence revision.

## What I verified and how

- Read `CLAUDE.md` and the order-safety, archetype/catalog, and generator
  handover skills before the review.
- Read the full r5 review and inspected the complete `3cdf40a..b270b20` spec
  diff (197 insertions, 52 deletions).
- Enumerated the `.get(...)` field reads in the two live compliance helpers and
  all nine production verdict functions, then mapped them to Appendix 7.
- Re-executed the R5-01 race-week object through production
  `r02_vo2max_frequency` and a literal r6 adapter: `True == True`.
- Re-executed the R5-02 transition suffix and R06 type/phase/paid applicability
  constructions from the normative r6 predicates.
- Traced native/non-native progression-level authority through Appendix 7,
  Appendix 8, the Phase 3 block path, and `workout_mapper`'s Endurance special
  case.
- Hashed the requested r5/r6 regression sections; all seven were byte-identical.
- Parsed Appendix 4 and compared ordered category/name tuples to the live
  registry; parsed all 600 Appendix 5 rows and their two boolean columns.
- Parsed Appendix 6 and compared its named sets/bands with the sibling
  experimental scorer; parsed Phase 3's exact seven TP kinds.
- Checked Mode A/B, E1/E2/E3 routing, Q0 inventory, report equations, and the
  combined disposition map after the new projection was added.

## What I could not verify

- r6 is a specification commit, not an implementation. The required generated
  differential corpus, its committed case count/vectors, the D1 projection
  builder, target-rule fixtures, Q0 byte comparisons, and full E1 acceptance
  suite do not yet exist to execute. Their absence is implementation work
  explicitly governed by `docs/SPEC_EARNED_SELECTION.md:1029-1068,1596-1624`,
  not an underspecified policy decision.
- I did not execute live TrainingPeaks, Endure, email, or delivery operations;
  this review verified their closed spec inventory against Phase 3 code only.

**Final verdict: GO — 0 blockers.**
