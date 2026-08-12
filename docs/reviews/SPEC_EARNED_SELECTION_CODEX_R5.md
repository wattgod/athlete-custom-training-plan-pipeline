# Adversarial Review: `SPEC_EARNED_SELECTION` — Round 5

Review target: `docs/SPEC_EARNED_SELECTION.md` at `5f899f5`

## Verdict

**NO-GO — 2 blockers.**

r5 resolves four of the six R4 blockers and preserves the previously settled
registry, identity, seal, state, and TrainingPeaks contracts. The W00 correction
is faithful even to the producer's odd 35→40 and 45→40 minute rounding; the
candidate's five disputed authorities are now real and explicit; and the
report-root routing equation is replayable.

The remaining defects are concentrated in the rule transition. The E1 legacy
verdicts are not derivable from the supposedly complete frozen candidate and the
published R02 adapter is not actually verdict-equivalent to production. The E3
target registry also still admits decision-changing disagreement for R02/R06 and
does not give R04 a candidate path for the non-native level it requires. Those
are release decisions, not calibration backlog or editorial polish.

## R4 blocker verification

| R4 blocker | r5 disposition | Verification |
|---|---|---|
| R4-01 — two W00 producers omitted | **RESOLVED** | §4.4 and A8 now register `pre_plan_easy`, `pre_plan_endurance`, `pre_plan_strength_prep`, and `pre_plan_rest` (`docs/SPEC_EARNED_SELECTION.md:367,3270,3371-3393`). Phase 3 emits exactly those four branches (`build/trustworthy-phase3:athletes/scripts/generate_athlete_package.py:1828-1922`). The common positive-duration path rounds then calls `create_workout_blocks(..., 'Easy')` (`...:1942-1954`). `round_duration_to_10` is Python `round(minutes/10)*10` (`build/trustworthy-phase3:athletes/scripts/workout_templates.py:168-188`), so 45→40 and 35→40 are correctly recorded. The published endurance and strength-prep segments reproduce from `create_workout_blocks` (`...generate_athlete_package.py:1276-1319`). |
| R4-02 — false/absent candidate derivations | **RESOLVED for the five cited fields** | A7 now reads `profile.yaml`, the separate `methodology.yaml.methodology_id`, and `weekly_structure.yaml` (`docs/SPEC_EARNED_SELECTION.md:3202,3205,3207,3212`). Those match Phase 3 loads/keys (`build/trustworthy-phase3:athletes/scripts/generate_athlete_package.py:595-602,3091-3096`), guide reads (`...training_guide_builder.py:3911-3953,4050-4055`), weekly-structure shape (`...build_weekly_structure.py:56-151`), and profile strength producer (`...intake_to_plan.py:1280-1286,1609-1614`). Appendix 5 contains 600 unique rows, exactly 24 `is_assessment=true` and 18 `long_ride_registered=true`, while every prior purpose/status field is unchanged. Variation is explicitly zero-based (`docs/SPEC_EARNED_SELECTION.md:3142,3220`) and matches the live counter (`build/trustworthy-phase3:athletes/scripts/generate_athlete_package.py:2732-2755`). `strength_declined` now has an exact derivation and conservative false fallback (`docs/SPEC_EARNED_SELECTION.md:3212`). The separate R04 level-path omission is recorded under R5-02 rather than reopening these five corrections. |
| R4-03 — D1 did not bind manifest/guide inputs or real flow | **RESOLVED** | The revision snapshot and complete `manifest_pin` are constructed before D1, are embedded in the candidate, and are projected byte-for-byte to the report (`docs/SPEC_EARNED_SELECTION.md:479-489,1468-1470,3006-3017,3204`). The `repo:`/`athlete:` namespace covers generated and repository inputs, including staging outside-root guide data (`docs/SPEC_EARNED_SELECTION.md:3187-3196`). W00 persistence and fueling alignment move before D1, followed by one post-canonical guide build (`docs/SPEC_EARNED_SELECTION.md:471-503`). The spec makes byte-neutrality against the Phase 3 final two-guide result a mandatory Q0 predicate (`docs/SPEC_EARNED_SELECTION.md:513-519`), rather than assuming the reorder is neutral. |
| R4-04 — E1 changed pre-existing verdicts | **PARTIAL** | The architecture is corrected: E1/E2 use separate legacy evaluators; E3 atomically dispatches to targets; all nine differential goldens are required (`docs/SPEC_EARNED_SELECTION.md:521-538,1529-1574`). Four of the five R4 examples now agree with production: R01 resets by week; R03 retains the 0.30/dynamic ceiling; R06 retains 60 below 7 hours and 90 otherwise; R20 retains the race-role exemption. R02 retains recovery/race-overlay exemptions in the common case. But the candidate cannot reproduce several legacy inputs, and the R02 race-week scan differs from the code (R5-01). |
| R4-05 — five open target predicates | **PARTIAL** | R13's key predicate and R23's every-adjacent-pair rule are closed (`docs/SPEC_EARNED_SELECTION.md:1837,1847`). R04 now has explicit tuples and a segment predicate, and R06 has an explicit registry boolean/disjunction (`docs/SPEC_EARNED_SELECTION.md:1652-1693`). R02 has exact date arithmetic and edge tests (`docs/SPEC_EARNED_SELECTION.md:1607-1625`). However, R02's last-edge definition contradicts its complete exemption predicate, R06 never defines “applicable week,” and R04's non-native level has no candidate field/path (R5-02). |
| R4-06 — `rubric_blockers` not report-derivable | **RESOLVED** | Report root now carries `rollout_phase`; every rubric row carries `routed_to_blocking_issues`; validation recomputes the exact boolean and count (`docs/SPEC_EARNED_SELECTION.md:1330-1334,1425-1438,1486-1507`). Re-evaluating the golden gives 0 for an E3-since CRITICAL FAIL in E1 and 1 in E3; a pre-existing CRITICAL FAIL gives 1 in E1/E2/E3. No external phase or mode is needed to replay the published count. |

## Named E1 divergence audit

| R4 named divergence | Production | r5 E1/E2 | Result |
|---|---|---|---|
| R01 Sunday→Monday | `prev_was_intensity` resets inside each week (`athletes/scripts/block_compliance.py:93-109`) | Same weekly reset (`docs/SPEC_EARNED_SELECTION.md:1544,1561`) | Equivalent for this case. |
| R02 race overlays/recovery endpoints | Both are skipped in the production applicability and normal VO2 scan (`athletes/scripts/block_compliance.py:117-135`) | Both named as skipped (`docs/SPEC_EARNED_SELECTION.md:1545,1562-1563`) | Equivalent for the named cases, but not for a `week_type=race` stimulus; see R5-01. |
| R03 40% recovery at 250 TSS load | Production floor 0.30 and ceiling 0.85 below 300 (`athletes/scripts/block_compliance.py:184-199`) | Same (`docs/SPEC_EARNED_SELECTION.md:1546,1564`) | Equivalent. |
| R06 hour thresholds | Production uses 60 iff truthy hours `<7`, otherwise 90, and passes a present zero-duration long-role day (`athletes/scripts/block_compliance.py:245-269`) | Same, including the zero-duration oddity (`docs/SPEC_EARNED_SELECTION.md:1549,1567`) | Equivalent. |
| R20 race on off day | Production exempts roles `off|race` (`athletes/scripts/block_compliance.py:328-344`) | Same (`docs/SPEC_EARNED_SELECTION.md:1552,1570`) | Equivalent. |

The other four legacy rows also describe the production verdicts: R04 uses
current role/name behavior; R05 uses the exact load/racing/race-overlay count;
R14 keys only from `all_violations`; and R19 preserves the current tolerance,
floor, exclusions, and first-base exemption
(`docs/SPEC_EARNED_SELECTION.md:1547-1551`;
`athletes/scripts/block_compliance.py:202-242,284-325`). Their
problem is input closure, not the stated boolean logic.

## Blocking findings

### R5-01 — The E1 legacy verdict is neither D1-closed nor exactly production-equivalent

**Claim.** r5 says every rule consumes the frozen `FinalPlanCandidate/v1`, but
several A3.0 legacy algorithms require live `_bb_plan` fields absent from that
closed schema. In addition, the published R02 algorithm changes one production
verdict.

**Evidence.**

- §4.5 freezes D1, then runs every pre-guide rule against that candidate
  (`docs/SPEC_EARNED_SELECTION.md:484-491`). Appendix 3 repeats that every rule
  consumes the candidate's exact later-canonical fields
  (`docs/SPEC_EARNED_SELECTION.md:1522-1527`). Appendix 7 forbids extra keys
  (`docs/SPEC_EARNED_SELECTION.md:2988-2992`).
- Production `_day_is_intensity` first reads nested
  `day_data.sessions[].intensity`, then day role, then the raw day name
  (`athletes/scripts/block_compliance.py:58-75`). A7 has flat final sessions but
  no legacy day object or nested external-session intensity token
  (`docs/SPEC_EARNED_SELECTION.md:3062-3173`). R01/R04/R05 therefore cannot
  necessarily reproduce the production classifier from D1.
- Production R02 classifies the raw `day.name` against `VO2MAX_TYPES`
  (`athletes/scripts/block_compliance.py:124-135`). The candidate has `title`,
  `session_type`, purpose, and (only for some series) a raw display name, but no
  required raw block-day `name` field (`docs/SPEC_EARNED_SELECTION.md:3086-3153`).
- Production R14 is exactly `bool(plan['all_violations'])`
  (`athletes/scripts/block_compliance.py:284-289`). No candidate root/week/session
  field stores `all_violations`. Two executions with the same D1 but different
  live `_bb_plan.all_violations` can therefore write different pre-existing R14
  verdicts.
- A3.0 R02 says `week_type=race` is excluded before both applicability and the
  VO2 scan (`docs/SPEC_EARNED_SELECTION.md:1545`). Production excludes race
  weeks from `non_racing_weeks` at lines 117-120, but its separate VO2 scan at
  lines 125-135 skips recovery, racing/taper, and race-role overlay—not
  `week_type=race`. A conforming legacy plan with four load weeks without VO2
  plus a base-phase race-typed week containing `VO2max 30/30` passes production
  (the race-week stimulus is recorded) and fails the literal r5 adapter (no
  recorded stimulus with four applicable weeks). I executed this construction:
  production returned `True`; the literal r5 function returned `False`.

**Why it blocks.** The same candidate digest can acquire different approval-
blocking legacy results, and even a fully populated legacy object has a published
R02 counterexample. That breaks D1 replayability, the zero-new-E1-blockers
promise, and the required nine-boolean differential harness. An implementer must
either violate the candidate-only rule, add forbidden schema fields, or choose
which contradictory R02 behavior to honor.

**Minimal fix.** Add a closed, D1-bound legacy compliance projection (or the
exact nine production verdict records plus their complete input digest) that
contains every raw field used by current `block_compliance.py`, including nested
fixed-session intensity, raw day names/order, and root `all_violations`. Define
the report projection from that bound value. Correct R02's legacy scan to retain
production's asymmetric `week_type=race` handling, then require exhaustive
differential equality over branch/boundary fixtures rather than only the listed
goldens.

### R5-02 — The E3 target registry still lacks one decision and one required candidate input

**Claim.** R02 and R06 still allow conforming implementations to disagree, and
R04 requires a non-native level that the candidate cannot address.

**Evidence and adversarial constructions.**

1. **R02 last edge.** The “complete exemption predicate” excludes
   `cycling_phase=transition` (`docs/SPEC_EARNED_SELECTION.md:1596-1605`).
   `p_first` is explicitly the first **non-exempt** load week, but `p_last` is
   instead defined as the last load week merely not `racing`
   (`docs/SPEC_EARNED_SELECTION.md:1617-1622`). A transition/load week is a valid
   contemplated state—R05 explicitly gives transition load weeks a 0–3 range
   (`docs/SPEC_EARNED_SELECTION.md:1829`). With VO2 on January 10, last base load
   day January 25, and a trailing transition/load day February 8, applying the
   complete exemption gives a 15-day suffix PASS; applying the literal `p_last`
   gives a 29-day FAIL.
2. **R06 applicability.** A3.1 says only “each applicable week” and A3.6 says
   “No applicable week → NA,” but nowhere defines the applicable week types
   (`docs/SPEC_EARNED_SELECTION.md:1680-1693,1830`). On a testing week without a
   qualifying long ride, an exact-load-only implementation returns NA while an
   implementation retaining r4's every-non-recovery/non-race scope returns FAIL.
   Both obey every r5 duration/boolean sentence. The choice also affects taper,
   medium, uber-load, transition, and unpaid W00 handling.
3. **R04 non-native level.** The target explicitly admits native/non-native
   template level and makes missing level unavailable
   (`docs/SPEC_EARNED_SELECTION.md:1652-1663,1828`). A7 exposes `level` only
   inside the nullable `archetype` object
   (`docs/SPEC_EARNED_SELECTION.md:3138-3144`), which non-native producers cannot truthfully populate with a
   manifest row. Yet `MAPPER_SIMPLE_ENDURANCE` is a non-native contract with a
   level 1–6 parameter (`docs/SPEC_EARNED_SELECTION.md:3266`), and the live
   producer reads `bb_level` and passes it to the mapper
   (`build/trustworthy-phase3:athletes/scripts/generate_athlete_package.py:2173-2180,2269-2277`).
   `provenance.transformation_parameters` is generic JSON,
   not a named R04 level path. A normal non-native endurance row can therefore
   be judged only by inventing a field path or by returning `UNAVAILABLE`.

R13 resisted disagreement: its conjunction of intensity role and exact purpose
class is complete. R23 also resisted the R4 construction: `[100,120,90]` checks
both adjacent pairs and fails, with no tolerance
(`docs/SPEC_EARNED_SELECTION.md:1837,1847`). R04's segment predicate itself is now deterministic once a level is
available.

**Why it blocks.** R02 and R06 are CRITICAL target rules and can produce
different E3 approval state from the same valid candidate. R04 is also CRITICAL,
but r5 routes `UNAVAILABLE` only to findings
(`docs/SPEC_EARNED_SELECTION.md:540-545`); the missing field silently prevents the promised target purity check
from becoming an approval decision. These are not purpose/gate hypotheses and
are not settled by E2 calibration.

**Minimal fix.** Make both R02 edges select non-exempt load weeks; enumerate the
exact R06 applicable `week_type`/paid/phase set and add one positive/negative
fixture for every included/excluded type; add a nullable generic
`progression_level` (or an equally exact producer-specific path) to each session,
define it for every Appendix 8 contract, and make R04 consume that named field.

## Regression audit of previously resolved content

- **Purpose registry:** parsed 600 rows, 600 unique IDs, six levels for each of
  100 bases. Removing the two new boolean columns produces exact equality with
  r4 for row ID, class, subtype, `main_set_rule`, and assignment status. The new
  truth counts are exactly 24 assessment rows (four bases × six) and 18 long-
  design rows (three bases × six).
- **Gate registry:** Appendix 6 is byte-for-byte identical to r4. Its ordered
  nine VO2 IDs, eight W′ IDs, bands, dose/identity fallbacks, and Q3 gates remain
  intact. I compared the named sets with the sibling working-copy
  `experimental-workout-library/score_library.py:28-42`; translations remain
  exact. The generated-manifest byte-equality requirement also remains at
  `docs/SPEC_EARNED_SELECTION.md:829-833`.
- **TrainingPeaks inventory:** §6 still contains all seven Phase 3 kinds and
  every payload field (`docs/SPEC_EARNED_SELECTION.md:967-991`). I parsed Phase
  3's `DATED_KINDS`, `SINGLETON_KINDS`, and entitlement constant and obtained
  exactly the same seven names
  (`build/trustworthy-phase3:athletes/scripts/apply_contract.py:23-31,97-147`).
- **Seal v2:** §5.4 is byte-for-byte identical to r4. The five-key source object,
  v1/v2 dispatch inventory, backward verification, and stale-global-manifest
  behavior survive (`docs/SPEC_EARNED_SELECTION.md:898-940`).
- **`quality_findings` rail:** §4.8 is byte-for-byte identical to r4. The v3
  state, replacing generation-only merge, five-source rank, automatic `observed`
  snapshot, and v2 backward read survive
  (`docs/SPEC_EARNED_SELECTION.md:643-721`).
- **Session IDs/report-derived roots:** §4.10 is byte-for-byte identical to r4.
  The `wNN.date.ordinal` identity, collision failure, regeneration stability,
  and exact two derived roots survive (`docs/SPEC_EARNED_SELECTION.md:744-814`).
- **Appendix 4:** byte-for-byte identical to r4 and mechanically exact against
  the live registry: 24 categories, 100 names/ordered slots, matching slug IDs,
  all active with null replacement (`docs/SPEC_EARNED_SELECTION.md:1858-2020`).
- **Combined disposition map:** R1/R2/R3 text survives. R4-01/02/03/06 are
  accurate; R4-04 and R4-05 overclaim complete resolution for the reasons above
  (`docs/SPEC_EARNED_SELECTION.md:1157-1166`).

## Non-blocking findings

### NB-01 — The report phase is replayable but its authority link should be explicit

A7.1 labels a derivation row “mode, rollout phase, and version vector,” while the
candidate schema carries `mode` and the rollout-file digest but no parsed
`rollout_phase` (`docs/SPEC_EARNED_SELECTION.md:2994-3058,3203`). The report does
carry the phase, so R4-06's count is closed. The implementation should still
validate `report.rollout_phase` against the digest-checked rollout file rather
than accept a caller-supplied phase. This is an implementation-discoverable
authority check and does not reopen the report equation itself.

### NB-02 — R04 now requires one opener, not merely permits one

The target says zero qualifying openers fails
(`docs/SPEC_EARNED_SELECTION.md:1663-1677`). That is stricter than a pure “no sustained intensity except
openers” reading, but it is explicit and therefore not an implementer ambiguity.
It should be visible in E2 regression evidence before E3 activation.

### NB-03 — `uber_load` remains registered future vocabulary

The current calendar adapter emits load/recovery/taper/race, while `uber_load`
comes only from the block-note vocabulary
(`docs/SPEC_EARNED_SELECTION.md:1586-1593`). Its target branches are deterministic reserved behavior. It should
not be reported as currently production-reachable until a producer emits it.

### NB-04 — r4 labels inside evidence-basis strings are provenance, not stale policy

Appendix 6 retains identifiers such as `r4_assessment_and_free_contract` and
`r4_initial_q3_hypothesis` (`docs/SPEC_EARNED_SELECTION.md:2913,2930,2947,2964`).
Because Appendix 6 is intentionally byte-identical and these values identify the
evidence revision, changing them merely to say r5 would be counterproductive.

## What I verified and how

- Read `CLAUDE.md` and all three applicable repository handover skills before
  auditing generation, catalog, compliance, and failure behavior.
- Compared the full `5f899f5^..5f899f5` edit and hashed/extracted the r4/r5
  sections for Appendix 4, Appendix 6, §4.8, §4.10, §5.4, and §6.
- Parsed Appendix 4 JSON and compared ordered category/name/slug tuples against
  `archetype_registry.ALL_ARCHETYPES`: exact 24/100 match.
- Parsed both r4 and r5 Appendix 5 tables and compared all 600 pre-existing
  fields. Counted and enumerated the new boolean truth sets.
- Inspected all four W00 branches, the common body, duration rounder, fueling
  behavior, and final TP-kind recording on `build/trustworthy-phase3`.
- Traced every disputed A7 authority to the actual Phase 3 YAML loader/writer,
  live zero-based variation counter, guide reads, and weekly-structure schema.
- Compared A3.0 line by line with all nine real production functions in
  `athletes/scripts/block_compliance.py`; executed the R02 race-week
  counterexample and the R4 boundary examples.
- Attempted conforming disagreement for each of R02/R04/R06/R13/R23. Only R13
  and R23 fully resisted it; R04's predicate is exact but lacks its non-native
  candidate input.
- Recomputed the routing formula for E1/E2/E3 and pre-existing/E3-since CRITICAL
  FAIL rows. All published blocker counts reproduced.
- Parsed Phase 3's seven TP kinds and compared its payload schemas with §6.

## What could not be verified

- r5 is still a specification. There is no E1 candidate builder, legacy adapter,
  report validator, manifest snapshotter, rule dispatcher, state v3 merger, or v2
  sealer to execute. Q0 byte identity, dual-constructor seal equality, and final
  state/catalog behavior therefore cannot yet be run.
- The sibling experimental scorer is an untracked working-copy evidence source,
  not a pinned Git object. I verified its present bytes and the unchanged
  Appendix 6 translation, not historical immutability.
- No E2 owner dispositions or promotion artifacts exist, so physiological
  correctness and Mode B library readiness were not reviewed.
- External TrainingPeaks, Endure, Gmail, PDF, ZIP, and publishing behavior was
  not exercised. The review checked the committed Phase 3 schemas and the spec's
  deterministic comparison contract only.

## Final assessment

r5 is close and the large edit did not regress the hard-won bulk contracts. The
remaining work is smaller than in prior rounds, but it sits exactly at the
approval boundary: what E1 reports as an existing blocker and what E3 decides
for R02/R04/R06. Closing the frozen legacy input and the three target-rule edges
requires explicit spec text before two implementations can agree without policy
invention.

**Verdict: NO-GO — 2 blockers.**
