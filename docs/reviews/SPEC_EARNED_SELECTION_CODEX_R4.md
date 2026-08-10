# Adversarial Review: `SPEC_EARNED_SELECTION` — Round 4

Review target: `docs/SPEC_EARNED_SELECTION.md` at `a6afb7b`

## Verdict

**NO-GO — 6 blockers.**

r4 materially improves the specification. The 600-row purpose registry is
complete and mechanically reproducible, both experimental gate ID sets translate
exactly, the W′bal goldens reproduce, the seven TrainingPeaks operation kinds are
complete, and the hypothesis/effective gate semantics are coherent in Mode A and
Mode B.

The release contract is still not implementable without policy invention. The
new producer registry omits two live W00 producers, several required
`FinalPlanCandidate/v1` fields cite nonexistent authorities, D1 does not bind the
certification manifest consumed by R21, E1 changes the verdicts of rules labelled
“pre-existing” while claiming zero new blockers, five rule algorithms retain
decision-changing ambiguities, and one published report counter cannot be
derived from the report content named by its equation.

## R3 blocker verification

| R3 blocker | r4 disposition | Verification |
|---|---|---|
| R3-01 — no complete purpose/gate registry | **RESOLVED** | Appendix 5 contains exactly 600 unique row IDs: 100 unique Appendix 4 archetypes × all six levels. An independent implementation of the category default, tag precedence, and 24 overrides reproduced every explicit row. Appendix 6's 9 VO2 and 8 W′ IDs exactly match the two sets in the experimental scorer. All four W′bal goldens reproduce under the stated recurrence and binary64 semantics. |
| R3-02 — overlapping origin and undefined candidate | **PARTIAL** | Producer-only origin and orthogonal `is_assessment` are sound as a model, and Appendices 7–8 provide much more structure. The live pre-plan producer has two reachable variants omitted from Appendix 8 (R4-01), while candidate derivation still names nonexistent fields/files and lacks an assessment authority for native rows (R4-02). |
| R3-03 — fueling classification incompatible with current behavior | **RESOLVED** | The internal enum and precedence reproduce `_get_fuel_tag_for_type`'s `quality`, `long_ride`, `race_sim`, and empty cases without changing athlete copy. The missing pre-plan variants create origin/provenance failures, but do not reopen the general fueling-model defect. |
| R3-04 — open rule algorithms | **PARTIAL** | R03, R11, R12, R14, R17, R21, and R25 are substantially more explicit. R02 still has a boundary/coverage ambiguity, and R04/R06/R13/R23 rely on undefined predicates or pair selection (R4-05). |
| R3-05 — guide ordering | **PARTIAL** | The abstract D1 → checks → canonical → guide/D2 → post-guide order is coherent. It does not bind the manifest used by a pre-guide rule and its guide-input path domain does not match production inputs; the Phase 3 flow also mutates W00/fueling and regenerates the guide after its first canonical guide build (R4-03). |
| R3-06 — report aggregation | **PARTIAL** | Session precedence and all session/gate collection equations uniquely determine their aggregates. `artifact_counts.rubric_blockers` is not derivable from the rubric rows or report root (R4-06). |
| R3-07 — incomplete TP operation-kind inventory | **RESOLVED** | The Q0 inventory is exact set equality with `apply_contract.py`: four dated kinds, two singleton kinds, and one entitlement kind. The payload fields also match the code's seven schemas. |
| R3-08 — Mode A impossible / rollout adds blockers | **RE-OPENED** | Gate hypothesis/effective semantics now make Mode A possible, but the asserted E1 release predicate is internally false: multiple `blocking_since: pre-existing` rules are normatively changed and can newly fail in E1 (R4-04). |

## Blocking findings

### R4-01 — The supposedly exhaustive producer registry omits two reachable W00 producers

**Claim.** `PRE_PLAN_GENERATOR` is registered only for `pre_plan_easy` and
`pre_plan_rest`, but production emits four distinct pre-plan variants.

**Evidence.**

- The origin union calls this the “W00 easy/rest emitter” and permits only the
  `pre_plan_easy` or `pre_plan_rest` tuple
  (`docs/SPEC_EARNED_SELECTION.md:367`). Appendix 8 repeats exactly those two
  template IDs (`docs/SPEC_EARNED_SELECTION.md:2984,3078-3081`).
- Phase 3 emits `Pre_Plan_Endurance` every reachable Saturday at 80 minutes
  (`build/trustworthy-phase3:athletes/scripts/generate_athlete_package.py:1828-1857`)
  and `Pre_Plan_Strength_Prep` every reachable Thursday at 35 minutes
  (`...:1885-1916`), in addition to rest and easy.
- Every positive-duration variant, including endurance and strength prep, is
  rendered through the common `create_workout_blocks(duration, power, 'Easy')`
  body (`...:1942-1954`). They are therefore real cycling ZWOs, not comments or
  unreachable labels.
- Appendix 8 requires any emitted unregistered tuple to fail R21, and the
  reachability test must fail on any such tuple
  (`docs/SPEC_EARNED_SELECTION.md:3114-3120`).

**Why it blocks.** An ordinary future-start order containing Thursday or
Saturday W00 produces either an unregistered tuple or a dishonest
`pre_plan_easy` identity. The former is an E3 CRITICAL failure and the latter
violates the producer/template contract. The new `PRE_PLAN_GENERATOR` origin is
therefore only partially integrated.

**Minimal textual fix.** Add exact `pre_plan_endurance` and
`pre_plan_strength_prep` contracts to Appendix 8, including purpose, role,
assessment, fueling source/class, nested body, structure, and reachability
fixtures; update §4.4 and A8.3 to enumerate all four live variants. If the intent
is to collapse them to one template, normatively change the producer first and
state the exact transformation rather than relabelling current output.

### R4-02 — `FinalPlanCandidate/v1` still has required fields with false or absent derivations

**Claim.** Appendix 7 is not a closed construction recipe. At least five required
values cannot be populated from the cited Phase 3 authorities as written.

**Evidence.**

1. A7.1 says generation facts come from `profile.json.fulfillment` and
   methodology from `profile.json.methodology.id`
   (`docs/SPEC_EARNED_SELECTION.md:2943-2945`). Phase 3 loads `profile.yaml` and a
   separate `methodology.yaml` (`build/trustworthy-phase3:athletes/scripts/generate_athlete_package.py:3091-3096`), then reads
   `methodology.methodology_id` (`...:595-602`). Repository and Phase 3 searches
   find no `profile.json` authority.
2. A7.1 requires validation of `weekly_structure.json`
   (`docs/SPEC_EARNED_SELECTION.md:2952`), while the spec itself and Phase 3 use
   `weekly_structure.yaml` (`docs/SPEC_EARNED_SELECTION.md:1534-1538`;
   `build/trustworthy-phase3:athletes/scripts/training_guide_builder.py:4050-4055`).
3. Native `is_assessment` must be copied from “Appendix 5/8's boolean assessment
   contract” (`docs/SPEC_EARNED_SELECTION.md:2956`), but Appendix 5 rows contain
   purpose class/subtype, main-set rule, and assignment status—not an
   `is_assessment` boolean. The body explicitly forbids deriving the boolean from
   purpose or content (`docs/SPEC_EARNED_SELECTION.md:347-355`). Appendix 8 has
   the boolean only for non-native templates.
4. The schema requires a positive `archetype.variation`
   (`docs/SPEC_EARNED_SELECTION.md:2890-2895`), but the live producer initializes
   and records variation at zero
   (`build/trustworthy-phase3:athletes/scripts/generate_athlete_package.py:2732-2748`).
   A7.1 specifies no `+1`, nullable, or zero-based conversion.
5. `strength_declined` is required in the candidate, but A7.1 only says “Copy
   `strength_declined`” without naming a source (`docs/SPEC_EARNED_SELECTION.md:2952`).
   Searches of the production and Phase 3 athlete code find no such source field.

**Why it blocks.** Two conforming implementers must either reject valid orders,
invent new source fields, infer assessment from a forbidden signal, or disagree
about variation numbering. Since D1 freezes these values and R11/R17/R21 consume
them, this is not harmless schema wording.

**Minimal textual fix.** Replace every false authority with exact existing YAML
path(s) and key(s), add a native assessment registry column, define the variation
index conversion, and define the source and precedence for explicit strength
decline. If a field is genuinely new, say which E1 producer writes it from which
existing authority and how missing/contradictory input is represented.

### R4-03 — D1 does not bind all inputs consumed before canonicalization

**Claim.** The staging model says D1 covers all rule/gate inputs, but the candidate
does not contain the certification-manifest pin consumed by R21; its guide-input
path contract also cannot name the athlete-local files the Phase 3 guide reads.

**Evidence.**

- Step 2 says D1 includes every candidate field, all config/source digests, and
  guide input digests; Step 3 immediately runs all pre-guide rules
  (`docs/SPEC_EARNED_SELECTION.md:469-479`).
- R21's exact frozen input includes “manifest pin”
  (`docs/SPEC_EARNED_SELECTION.md:1664`). Candidate `config_digests` contains no
  manifest snapshot/promotion digest, and `guide_inputs` follows it directly
  (`docs/SPEC_EARNED_SELECTION.md:2796-2814`). The first complete
  `manifest_pin` appears only in the later report
  (`docs/SPEC_EARNED_SELECTION.md:1398-1409`).
- `guide_inputs[].path` must be repo-relative
  (`docs/SPEC_EARNED_SELECTION.md:2812-2814`), while the Phase 3 guide reads
  athlete-local `profile.yaml`, `derived.yaml`, `plan_dates.yaml`,
  `methodology.yaml`, `fueling.yaml`, and conditionally
  `weekly_structure.yaml`
  (`build/trustworthy-phase3:athletes/scripts/training_guide_builder.py:3911-3953,4050-4055`).
- The actual package flow builds a first guide after canonical finalization
  (`build/trustworthy-phase3:athletes/scripts/generate_athlete_package.py:3158-3189`),
  then persists W00, rewrites fueling, and regenerates the guide
  (`...:3321-3347`). r4's desired order can replace that flow, but it does not
  say where those existing mutations move before D1.

**Why it blocks.** The same D1 can be scored against different certification
manifest bytes and promotion sets. Separately, implementations can omit or
invent path encodings for actual guide inputs. D2 then cannot prove that the
guide was built only from D1-bound inputs, and §4.5's no-post-D1-mutation
guarantee is not implementable against the cited flow.

**Minimal textual fix.** Freeze/copy the revision-local manifest before D1; put
its snapshot digest, version, and ordered promotion digests in the candidate and
R21 input. Define a canonical path namespace that covers both repo config and
athlete-local files. Explicitly move W00 persistence and fueling alignment before
the candidate freeze, with exactly one guide build after canonical finalization.

### R4-04 — E1 is not audit-only because “pre-existing” rule semantics change

**Claim.** The spec has no coherent E1 release predicate: it says the nine
existing blockers keep their behavior and E1 adds zero approval blockers, while
normatively changing several of their verdict functions.

**Evidence.**

- The promise appears in both §4.5 and rollout
  (`docs/SPEC_EARNED_SELECTION.md:500-513,1028-1035`).
- R03 is expressly changed to a fixed 50–65% pass band and >75% fail
  (`docs/SPEC_EARNED_SELECTION.md:455-457,1495-1518`). The live scorer uses a
  30% floor and a load-dependent 65–85% ceiling
  (`athletes/scripts/block_compliance.py:156-199`). A 250-TSS load mean and
  100-TSS recovery week (40%) passes production but fails r4.
- r4 R01 spans calendar week boundaries
  (`docs/SPEC_EARNED_SELECTION.md:1644`). Production resets
  `prev_was_intensity` at the start of every week
  (`athletes/scripts/block_compliance.py:93-109`). A Sunday/Monday intensity pair
  is a new E1 blocker.
- r4 R20 forbids generated training on an off day except rest
  (`docs/SPEC_EARNED_SELECTION.md:1663`). Production explicitly exempts race-role
  sessions on off days (`athletes/scripts/block_compliance.py:328-344`).
- r4 R06 requires 90 minutes at ≤8 available hours and 120 minutes above 8, with
  a separate structured-design exception (`docs/SPEC_EARNED_SELECTION.md:1649`).
  Production uses 60 minutes below 7 hours and otherwise 90
  (`athletes/scripts/block_compliance.py:245-269`).
- R02 also removes production's race-day overlay and recovery-week endpoint
  exemptions (`athletes/scripts/block_compliance.py:112-153` versus
  `docs/SPEC_EARNED_SELECTION.md:1483-1493,1645`).

**Why it blocks.** These examples turn currently approved plans into
needs-review orders during E1. That contradicts “zero new approval blockers,”
“no content changes,” and the claim that `blocking_since: pre-existing` preserves
behavior. Mode A's gate semantics do not repair this rubric contradiction.

**Minimal textual fix.** Define E1's nine rule evaluators as verdict-equivalent
to their current implementations and place all normative algorithm changes
behind E2 rebaselining/E3 activation, or relabel the changed semantics
`blocking_since: E3`. Add golden differential fixtures for each of the nine,
including cross-week R01, R02 race overlays, the R03 40% case, R06 boundaries,
and R20 race-on-off-day.

### R4-05 — Five rule algorithms still permit decision-changing disagreement

**Claim.** Appendix 3 calls its algorithms exact, but five of the weakest rows
still leave implementers to invent predicates or boundary policy.

**Evidence and conforming disagreements.**

1. **R02:** “at most 16 non-recovery calendar days apart” does not define whether
   the stimulus endpoints count, nor whether leading/trailing plan edges are
   gaps (`docs/SPEC_EARNED_SELECTION.md:1645`). For stimuli on January 1 and
   January 18, one implementation counts 16 intervening dates and passes; another
   uses date difference 17 and fails. The row also evaluates only consecutive
   stimuli, so a long trainable prefix or suffix after a single stimulus can pass
   unless an edge rule is invented.
2. **R04:** “plain Endurance L1–L2” is not a registry predicate
   (`docs/SPEC_EARNED_SELECTION.md:1647`). One implementation admits every
   `purpose.class=endurance` L1–L2 session; another admits only
   `endurance/steady`. Cadence, drills, and strength-endurance can therefore pass
   or fail from the same candidate. “Individual efforts” also lacks a segment
   predicate for opener ramps/interval containers.
3. **R06:** “registered structured-endurance long design” has no field or named
   registry set (`docs/SPEC_EARNED_SELECTION.md:1649`). One implementation treats
   `purpose=endurance/long` as registered; another treats any structured
   endurance archetype as registered. The same 80-minute session passes or fails.
4. **R13:** the candidate has roles and purposes but no `key` attribute. “key
   threshold/VO2/race-sim intervals” is undefined
   (`docs/SPEC_EARNED_SELECTION.md:1656`). One implementation equates
   `role=intensity` with key; another uses only the three purpose classes.
   Threshold-purpose filler and non-key intensity can disagree.
5. **R23:** “Second applicable load week ... ≥ first” does not say whether it
   checks only the first pair or every adjacent pair in a series
   (`docs/SPEC_EARNED_SELECTION.md:1666`). TSS `[100,120,90]` passes the literal
   first-versus-second reading and fails an all-pairs progressive-overload
   reading.

These are independent of the substantially improved R03/R11/R12/R14/R17/R21/R25
text. R25's two markers do exactly exist in
`athletes/config/block_notes.yaml:27-37,52-61`; the problem is not its literal
marker grammar.

**Why it blocks.** Each pair can produce different PASS/FAIL results from the
same valid candidate. R02/R04/R06 are immediately approval-blocking; R13/R23
become release-affecting at E3. The bar for a normative registry is stronger than
choosing whichever interpretation resembles the old scorer.

**Minimal textual fix.** Define R02 using an explicit date-difference formula and
edge coverage; publish an exact allowed `(purpose class, subtype, level,
segment predicate)` set for R04; add a candidate boolean or exact purpose-ID set
for R06; define `key` as a candidate field or exact role/purpose predicate for
R13; and state the ordered pair set evaluated by R23 with a three-week golden.

### R4-06 — `rubric_blockers` is not derivable from the report named by its equation

**Claim.** Most aggregation equations are closed, but the published
`artifact_counts.rubric_blockers` equation depends on routing state absent from
the report rows/root.

**Evidence.** The equation is “count(rubric rows routed to blocking_issues)”
(`docs/SPEC_EARNED_SELECTION.md:1438-1441`). Rubric rows carry rule ID, result,
severity, `blocking_since`, and finding ID, but not a routed/blocking boolean; the
report root does not expose rollout phase. Yet an E3 CRITICAL failure is a
blocker, while the identical rule result is a finding during E1/E2
(`docs/SPEC_EARNED_SELECTION.md:508-518`). A candidate hash is opaque and is not
a report field from which the equation can be evaluated.

**Adversarial construction.** Use one active E3 CRITICAL rule row with
`result=FAIL`, `blocking_since=E3`, and all other rows passing. With identical
rubric row content, `rubric_blockers=0` is correct in E1 and `=1` is correct in
E3. All session partition counts remain uniquely determined. Conversely, two
reports can legitimately have identical counts but different session/gate IDs
and measurements; that is acceptable because detailed content and the canonical
digest distinguish them. The defect is specifically same named content → two
valid blocker counts.

**Why it blocks.** An independent report verifier cannot enforce every published
count equation. State/catalog merges can therefore disagree about approval state
without a schema violation.

**Minimal textual fix.** Add rollout phase/mode and an exact routing formula to
the report, or add a required per-rubric-row `routed_to_blocking_issues` boolean
and derive it from a report-bound phase. Then define `rubric_blockers` as the
count of that explicit collection/field and add E1/E3 goldens.

## Non-blocking findings

### NB-01 — The purpose registry is mechanically complete, but several assignments deserve E2 reclassification

The derivation is deterministic and the explicit 600 rows agree with it. That
does not make every category-default hypothesis physiologically persuasive.
Examples include `ilt--ilt-single-leg` assigned `wprime_drain` even though its
source is low-power Z2 pedalling-efficiency work; `sprint--sprint-buildups`
assigned W′ drain despite being primarily neuromuscular; and
`tempo--tempo-sprints` assigned threshold despite its embedded sprint work.
Those are non-blocking in r4 because all assignments remain hypotheses and E2
requires owner disposition before Mode B. The spec should avoid calling the
override list a proof that every ambiguous row was resolved.

### NB-02 — `uber_load` is registered vocabulary, not an integrated current producer state

Repository and Phase 3 searches find `uber_load` only in
`athletes/config/block_notes.yaml:52-61` and the new spec. The calendar adapter
emits only load/recovery/taper/race (`athletes/scripts/block_chain.py:36-60`),
with testing added separately. Thus R24's Uber Load branch is currently
unreachable. Reserving a future enum is acceptable, but the text should call it
reserved/unreachable rather than “discovered” runtime state, and its reachability
test should reflect that fact.

### NB-03 — R25's markers are real, but the production guide does not currently project block notes

The exact recovery and Uber Load phrases in A3.5 match
`block_notes.yaml:33,61`. Searches show the production
`training_guide_builder.py` does not load that config; the separate
`generate_html_guide.py` path does. Therefore initial R07/R25 observations will
be unavailable or fail for more than merely load/medium/race weeks. This remains
non-blocking only because both rows are findings before E3 and E2 explicitly
allows the required guide content change.

### NB-04 — One native render is empty and the Rest structural edge is unusual but accounted for

All 600 rows invoked the live renderer without an exception. One row, CP Test
Protocol L3, produced an empty body; Rest Day produced a single zero-duration
`FreeRide` at every level. Eleven other rendered rows contained mixed FreeRide
and prescribed structure. r4's mixed/empty policy makes the CP row unavailable
rather than silently certifying it, and its Rest exception is explicit, so these
are evidence for the designed E2 backlog rather than new blockers.

### NB-05 — Same aggregate counts with different detailed content is not itself a schema defect

Two reports can have the same session verdict partition and gate-result counts
while referring to different sessions, gate IDs, or measurements. The report's
detailed arrays and canonical digest distinguish them. Except for R4-06, the
published session precedence and collection-total equations uniquely determine
their counters from detailed content.

### NB-06 — Sampled new citations were mostly accurate; three material citation errors are blockers above

The sampled `_get_fuel_tag_for_type`, fueling-label, W′ scorer, VO2 scorer,
block-note marker, block-chain phase, TSS, TrainingPeaks kind/schema, canonical
control, and guide-input citations point to the claimed behavior. The material
exceptions are the incomplete W00 range/description, nonexistent
`profile.json`, and nonexistent `weekly_structure.json`; they are incorporated in
R4-01/R4-02 rather than left as editorial notes.

## What was verified and how

### Purpose registry and native rendering

- Parsed Appendix 4: 100 rows, 100 unique immutable IDs, 24 categories, exact
  order/IDs matching `athletes/scripts/archetype_registry.py`.
- Parsed Appendix 5: 600 rows, 600 unique row IDs, 100 base IDs, exactly levels
  1–6 for each base ID.
- Independently implemented category default → tag precedence → explicit
  override precedence. It reproduced every Appendix 5 purpose class, subtype,
  main-set rule, and status; there were zero derivation/explicit-table mismatches.
- Invoked the live renderer for all 600 rows and inspected structure/free-ride
  composition. There were 599 non-empty bodies and the one CP L3 empty body noted
  above.
- Cross-checked more than 20 edge rows, including Rest Day L1/L6, FTP Ramp Test,
  20-Minute FTP Test, CP Test L3/L6, MAF Test, Pre-Race Openers, Float Sets,
  Loaded Recovery, Tired 30/30s, Hard Starts, Kitchen Sink All-Systems, Drain
  Cleaner, La Balanguera, Hyttevask, ILT Single Leg, Sprint Buildups, Tempo
  Sprints, Endurance Surges, Full Simulation, and Active Recovery. Every checked
  row agreed mechanically with the published derivation; the questionable
  scientific classifications are called out separately.

### Gate registry and W′bal

- Compared Appendix 6 against the untracked main-checkout
  `experimental-workout-library/score_library.py` sets. All nine VO2 translations
  and all eight W′ translations are exact; there are no extras or omissions.
- Reimplemented the stated one-second recurrence with `W′=20 kJ`, `CP=250 W`,
  `P_rec=150 W`, and binary64 exponentiation. The four published final/nadir
  results reproduced (within the specified `1e-9 kJ` tolerance):

  | Golden | Computed final W′bal (kJ) | Computed nadir (kJ) |
  |---|---:|---:|
  | 60 s @ 250 W | 20.000000000000 | 20.000000000000 |
  | 60 s @ 300 W | 17.625000000000 | 17.625000000000 |
  | then 60 s @ 150 W | 17.895093337774 | 17.625000000000 |
  | 600 s @ 300 W | -3.750000000000 | -3.750000000000 |

- Verified that hypothesis observations remain complete but
  `effective=NOT_ENFORCED` in Mode A, while only validly promoted enforcing gates
  can contribute effective PASS/FAIL in Mode B. This part of R3-08 is now sound.

### Candidate, staging, rules, aggregation, and TP inventory

- Compared each named A7.1 source with `build/trustworthy-phase3` generator,
  canonical model, PlanIR, and guide builder; R4-02/R4-03 record the gaps.
- Traced Phase 3 canonical finalization, first guide generation, W00 persistence,
  fueling alignment, second guide generation, report/catalog preparation.
- Compared the five weakest rule algorithms using explicit counterexamples, and
  compared R02 exemptions/R03/R06/R20 against the live compliance code.
- Checked R25's literal markers against `athletes/config/block_notes.yaml` and
  searched both guide implementations for projection of those templates.
- Recomputed all report partition equations and constructed E1/E3 rubric reports
  to test whether the same detailed rows uniquely determine counters.
- Compared §6/Q0 with Phase 3 `apply_contract.py:23-31,97-147`: exact kinds are
  `workout_upsert`, `calendar_note_upsert`, `attachment_upsert`,
  `mental_task_upsert`, `threshold_update`, `zone_update`, and
  `course_entitlement_grant`; no allowed kind is missing.
- Searched current and Phase 3 producers for `PRE_PLAN`, `uber_load`, `medium`,
  `profile.json`, `weekly_structure.json`, and `strength_declined` rather than
  accepting the new citations at face value.

## What could not be verified

- r4 is a specification, not an implementation. There is no E1 candidate
  builder, registry loader, merged scorer, report writer, manifest snapshotter,
  or v2 sealer to execute. Therefore Q0 byte-equivalence, full golden-fleet
  report generation, state/catalog single-merge behavior, and v2 dual-constructor
  equality could not be run.
- The experimental scorer is untracked in the sibling main checkout. Its current
  file contents were inspected and matched, but r4 does not pin a Git object for
  that evidence source.
- No E2 owner dispositions or promotion artifacts exist yet, so scientific
  purpose/gate approval and Mode B release readiness were not evaluated.
- External TrainingPeaks and Endure behavior was not exercised against live
  services; this review checked the committed Phase 3 operation schemas and
  inventory only.

## Final assessment

r4 has closed the bulk-data and mathematical portions that were missing in r3:
the purpose registry is truly 600 rows and deterministic, the gate translations
and W′bal recurrence are reproducible, and Q0's TrainingPeaks inventory is exact.
The remaining failures sit at the higher-risk integration boundaries—producer
reachability, frozen authority, approval behavior, and report replayability.
Those must be closed before implementation can proceed without inventing policy.

**Verdict: NO-GO — 6 blockers.**
