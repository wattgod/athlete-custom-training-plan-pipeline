# SPEC_EARNED_SELECTION adversarial review — Codex R3

## Verdict: NO-GO

r3 is a substantial improvement over r2. It supplies real normative content for
the design-dose function, verdict authority, promotion artifact, non-waivable
policy, state rail, seal v2, session IDs, report, rule table, and stable ID map.
The registry and render claims also survive direct machine checks.

It is not yet an implementable release contract. The remaining defects are no
longer mostly missing appendix names; they are contradictions and undecided
algorithms inside the new appendices. In particular, the spec omits the complete
purpose/gate registries needed to score the library, does not define the frozen
candidate the rules consume, makes the new fueling rules incompatible with the
actual final fueling projection, schedules guide-dependent rules before the guide
exists, leaves multiple R01–R26 algorithms open, underdefines report aggregation,
omits four TrainingPeaks operation surfaces from Q0, and requires effective PASS
in a mode where effective PASS is impossible.

This review has **8 blockers**.

## R2 blocker verification

| R2 | Status | Verification and evidence |
|---:|---|---|
| R2-01 | **RESOLVED** | The new metric is distinctly named `design_if/design_tss/design_kj`; exact ramp samples, duration, invalid input, mixed/pure FreeRide behavior, and the empty sentinel are specified (`docs/SPEC_EARNED_SELECTION.md:90-150`). A direct production-registry render produced all 600 rows and exactly the claimed six pure-FreeRide Rest rows plus 11 mixed testing rows. |
| R2-02 | **PARTIAL** | The observed/effective table, promotion preconditions, and Appendix 2's digest-bound artifact supply the content r2 lacked (`docs/SPEC_EARNED_SELECTION.md:197-231,942-969`). However, the applicable purpose/gate registries are absent and the effective-verdict table contradicts the unconditional Mode A invariants. See R3-01 and R3-08. |
| R2-03 | **RESOLVED** | Q3 is explicitly a native-design claim, while the final sealed series receives a separate non-blocking regression check with exact identity/order/plateau behavior (`docs/SPEC_EARNED_SELECTION.md:237-274`). |
| R2-04 | **PARTIAL** | §4.4 names the previously omitted producers and requires a reachability sweep (`docs/SPEC_EARNED_SELECTION.md:295-332`), but the union is not disjoint and its required frozen candidate/provenance registry is absent. See R3-02. |
| R2-05 | **RESOLVED** | The complete resulting set, six-code extension, remediation strings, four-way set-equality assertion, and negative-test independence are normative (`docs/SPEC_EARNED_SELECTION.md:386-448`). They match the shape of the Phase 3 closed policy at `build/trustworthy-phase3:webhook/fulfillment_state.py:47-71`. |
| R2-06 | **RESOLVED** | §4.8 supplies exact version bumps, authoritative `quality_findings`, a revision-aware replacing merge, fifth catalog source/rank, `_review_item` projection, server-owned `observed` disposition, old-version dispatch, and tests (`docs/SPEC_EARNED_SELECTION.md:481-555`). Those integrate with the actual four-source rebuild and snapshot validation at `build/trustworthy-phase3:webhook/fulfillment_state.py:296-341,344-530`. |
| R2-07 | **RESOLVED** | r3 gives the real revision path, canonical digest, exact fifth source key/value, exact v2 version, both constructors, verification dispatch, and v1 behavior (`docs/SPEC_EARNED_SELECTION.md:709-773`). The four existing keys match both Phase 3 constructors at `build/trustworthy-phase3:athletes/scripts/apply_contract.py:693-708` and `build/trustworthy-phase3:webhook/fulfillment_state.py:802-829`. |
| R2-08 | **PARTIAL** | The session-ID grammar and two complete derived records now exist (`docs/SPEC_EARNED_SELECTION.md:578-649`), and Appendix 2 supplies a closed report shape. Its counts and singular gate-version fields remain ambiguous. See R3-06. |
| R2-09 | **RE-OPENED** | Appendix 3 contains 26 rows and settles several contested choices, but multiple rows still defer their algorithm or verdict, and the execution order cannot provide two required inputs. See R3-03 through R3-05. |
| R2-10 | **RESOLVED** | Both unknown-to-POLARIZED fallbacks are expressly replaced by rejection, and malformed/missing config cases are enumerated (`docs/SPEC_EARNED_SELECTION.md:453-479`). |
| R2-11 | **RESOLVED** | Appendix 4 is an exact ordered map; §5.2 supplies slugging, immutable slots, tombstone/replacement selection, failure when no active slot exists, and exhaustive equivalence inputs (`docs/SPEC_EARNED_SELECTION.md:669-707,1211-1447`). Machine comparison against the live registry was exact. |
| R2-12 | **RESOLVED** | Missing HR anchors normatively become canonical RPE prescriptions and are gated as RPE without invented HR/power (`docs/SPEC_EARNED_SELECTION.md:557-576`), matching Phase 3 normalization at `build/trustworthy-phase3:athletes/scripts/canonical_training_model.py:43-65,119-194`. |
| R2-13 | **RESOLVED** | r3 now says the 14,840 plan instances require separate instance-level QC and do not inherit native certification (`docs/SPEC_EARNED_SELECTION.md:40-54`). The stated 524/14,840 counts match filesystem enumeration. |
| R2-14 | **PARTIAL** | §6 now covers ZWOs, named deliverables/ZIP, Endure, Gmail, follow-ups, and publishing with byte controls (`docs/SPEC_EARNED_SELECTION.md:786-827`), but its TrainingPeaks list is not closed against the actual apply contract. See R3-07. |

Result: **9 RESOLVED, 4 PARTIAL, 1 RE-OPENED**.

## Blocking findings

### R3-01. Certification has no complete purpose registry or gate registry

**Claim.** Every native row has an immutable purpose contract, an applicable
gate, and enough pinned configuration to generate the exact 600-row
certification manifest (`docs/SPEC_EARNED_SELECTION.md:163-166,176-182,278-283,
657-666`).

**Evidence.** r3 defines the shape of a purpose contract and lists allowed
classes, but never assigns `{class, subtype, main_set_segment_ids}` to any of the
100 archetypes or 600 rows. It likewise defines the fields of
`quality_gates.yaml` but supplies only the two Q3 gates
(`docs/SPEC_EARNED_SELECTION.md:199-231`). No appendix contains the initial
purpose mapping, the purpose-band thresholds/operators, or algorithms that map
each purpose subtype to its applicable gate. The experimental scorer makes the
missing policy concrete: it hard-codes nine VO2 IDs, eight W′bal IDs, all others
as dose-only, and the 8–14 minute/0–6 kJ bands
(`experimental-workout-library/score_library.py:28-67`). None of those ID sets or
bands is adopted or replaced by complete r3 content. Even W′bal is described by
parameters but not a complete per-sample recurrence in the spec
(`docs/SPEC_EARNED_SELECTION.md:152-166`).

**Why it blocks.** Two conforming implementers must invent which rows are VO2,
W′-drain, threshold, assessment, or mixed; which segments form their main set;
which gates apply; and what PASS means. Q1, Q2, §4.2, manifest generation, and E3
therefore cannot be implemented from the spec.

**Minimal textual fix.** Add closed, versioned, exact initial content for the
purpose registry and `quality_gates.yaml`: all 100 IDs/600 rows, subtype,
immutable segment IDs or an exact deterministic renderer rule that produces
them, every gate's algorithm/operator/threshold/unit/status, applicability, and
aggregation. Include the full W′bal recurrence and goldens. Make the manifest pin
the resulting version vectors/digests.

### R3-02. The closed origin union is overlapping and consumes an undefined candidate

**Claim.** Every cycling session has exactly one origin assigned by its emitting
branch, and all rules consume a frozen `FinalPlanCandidate/v1`
(`docs/SPEC_EARNED_SELECTION.md:295-320,357-370,1170-1174`).

**Evidence.** `ASSESSMENT` is defined as an FTP/anaerobic/CP/ramp path that may be
“native or standard” (`docs/SPEC_EARNED_SELECTION.md:313`). Such a native
assessment is simultaneously reachable under `NATIVE_ARCHETYPE`; a standard one
is simultaneously reachable under `STANDARD_BLOCK_GENERATOR`. No precedence or
producer-assignment algorithm closes that overlap. More fundamentally, r3 never
publishes a `FinalPlanCandidate/v1` schema. Appendix 3 assumes fields including
`role`, purpose, week type, weekly reported and target TSS, origin/template
versions, strength intensity, and guide/config digests
(`docs/SPEC_EARNED_SELECTION.md:1176-1203`). The Phase 3 canonical session
currently has no role, purpose, week type, template-version, or generic provenance
fields (`build/trustworthy-phase3:athletes/scripts/canonical_training_model.py:
501-533`); athlete-fixed sessions have only title/duration/TSS and empty segments
(`:333-351`). The naming manifest also records only its present projection fields,
not the required union contract.

**Why it blocks.** Reachability cannot prove “exactly one,” and implementers must
invent both classification precedence and the frozen data model on which every
rule, origin contract, report, and canonical-equality assertion depends.

**Minimal textual fix.** Publish a closed `FinalPlanCandidate/v1` schema with all
plan/week/session/provenance fields and derivation rules. Make origin predicates
mutually exclusive—for example, make assessment a contract subtype within a
producer origin, or state exact precedence and ensure only the winning
discriminant is serialized. Add the exact non-native producer/template version
registry and fixtures for native and standard assessments.

### R3-03. R08–R10 require a fueling projection that production does not emit

**Claim.** Every non-rest/non-race cycling workout has exactly one
`HIGH|MODERATE|PRACTICE` tag in final `fueling.yaml`, and R09/R10 consume it
(`docs/SPEC_EARNED_SELECTION.md:1185-1187`).

**Evidence.** Phase 3's per-workout fuel function returns athlete-specific prose,
not one of those enum values. It deliberately returns the empty string for
recovery/easy/shakeout/rest/openers and for endurance under 90 minutes
(`build/trustworthy-phase3:athletes/scripts/generate_athlete_package.py:191-232`).
Its only rendered labels are `HIGH FUEL`, `LONG-RIDE FUEL`, and `RACE FUEL`
(`build/trustworthy-phase3:athletes/scripts/fueling_policy.py:233-248`). The prose
is inserted into ZWO descriptions
(`build/trustworthy-phase3:athletes/scripts/generate_athlete_package.py:2302-2315`);
the athlete `fueling.yaml` contains the prescription/gut-progression data, not a
closed workout-tag collection. Appendix 3 names neither a new field/schema nor a
derivation from those existing labels. Adding tags to the athlete-visible file in
E1 would also conflict with Q0's required byte identity for `fueling.yaml` and
ZWOs (`docs/SPEC_EARNED_SELECTION.md:792-795,859-863`).

**Why it blocks.** A literal R08 makes ordinary recovery and short endurance
sessions unavailable or failing. A compatible implementation would have to
invent new tags, silently map different prose labels, or change athlete-facing
bytes during an audit-only rollout.

**Minimal textual fix.** Define a closed internal fueling classification in the
frozen candidate/report, its deterministic mapping from existing policy tiers,
and exact applicability for recovery, openers, short endurance, assessment, and
race sessions. Point R08–R10 to that internal field. State whether athlete-facing
fueling prose remains byte-identical in E1 and move any intended content change
to E2.

### R3-04. Appendix 3 still leaves active rule algorithms and verdicts open

**Claim.** Appendix 3 settles every rule's applicability, algorithm, exact input,
NA/unavailable behavior, severity, and output code
(`docs/SPEC_EARNED_SELECTION.md:334-348,1170-1176`).

**Evidence.** Several ACTIVE rows still require policy invention:

- R03 says “mean preceding applicable load-week TSS” without defining how many
  preceding weeks, adjacency, phase/block boundaries, or which reported versus
  summed value is the denominator (`docs/SPEC_EARNED_SELECTION.md:1180`).
- R11 explicitly says missing evidence becomes “unavailable/fail as evidence
  dictates,” leaving the result undecided (`:1188`).
- R12 names only some phase/template pairs and supplies no complete
  periodization table (`:1189`).
- R14 requires an “exact normalized series name” but gives no normalization
  grammar beyond one Kitchen Sink example (`:1191`).
- R17 refers to a phase-purpose mapping digest but supplies no complete mapping
  or precise per-week/build inclusion algorithm (`:1194`).
- R21 requires every non-native producer/template version to be registered, but
  §4.4 contains prose contracts, not that exact registry (`:1198`).
- R25 requires semantic action detection but supplies no deterministic grammar
  or parser; an LLM is explicitly forbidden (`:1202`; `:887`).

R02 also uses an open set of “transition/off-season/racing exemptions,” while its
inputs name only phase/week type (`:1179`). These are not mere implementation
details: each changes PASS/FAIL/UNAVAILABLE.

**Why it blocks.** The purported single normative rubric can produce different
release decisions from the same sealed inputs. That reopens the core R2-09
complaint despite the table's improved coverage.

**Minimal textual fix.** Replace every open phrase with complete tables,
windows, normalization/parsing grammars, and result precedence. In particular,
choose R11 FAIL versus UNAVAILABLE for every input state; publish the complete
phase/strength/purpose and producer-version registries; define R03's exact
window/denominator; and define a deterministic R25 rule with goldens.

### R3-05. The execution order runs guide-dependent rules before the guide exists

**Claim.** Step 3 runs every ACTIVE rule against the frozen candidate and exact
ancillary artifacts, then step 5 finalizes the canonical model
(`docs/SPEC_EARNED_SELECTION.md:357-370`). R07 and R25 require the final
`training_guide.html` (`docs/SPEC_EARNED_SELECTION.md:1184,1202`).

**Evidence.** The exact order never generates the guide before step 3. In Phase
3, guide construction expressly consumes the finalized canonical authority and
runs only after `build_canonical_model` and projection
(`build/trustworthy-phase3:athletes/scripts/generate_athlete_package.py:
3166-3189`). Step 4 has already written the report and merged all 26 rubric
results before r3's step 5 finalizes the model. There is no second rule pass or
report refresh after guide generation.

**Why it blocks.** R07 and R25 must be unavailable, must inspect a stale guide,
or require a cycle in which the final guide precedes the canonical model it is
required to consume. The mandated 26-row report cannot be produced in the stated
order.

**Minimal textual fix.** Put canonical finalization and deterministic guide
generation before guide-dependent rules while preserving the no-content-mutation
freeze, or split the registry into pre-guide and post-guide stages and define the
second report/catalog refresh. State exactly which digest is frozen at each
stage and retain the final report/model session-equality assertion.

### R3-06. `workout_quality_report/v1` does not define its summary aggregation

**Claim.** Appendix 2 is a closed report schema whose count sums are validated
(`docs/SPEC_EARNED_SELECTION.md:1055-1164`).

**Evidence.** `gate_summary.counts` contains observed/effective PASS/FAIL,
not-enforced, NA, and unavailable counts (`docs/SPEC_EARNED_SELECTION.md:
1069-1081`), but a session stores one `manifest_gate` and an arbitrary array of
`final_gates` without a session-level aggregate verdict (`:1082-1130`). The spec
does not say whether the counts count sessions, manifest results, final gate
results, or both, nor how a session with mixed results contributes. The
`quality_findings` and `rubric_blockers` counts are not part of the same verdict
partition, so “count sums” has no uniquely defined equation. Both the manifest
and report pin also contain singular `gate_version` fields despite multiple
versioned gates and sorted gate arrays (`:984,1021-1034,1150-1155`).

**Why it blocks.** Valid report bytes and the derived `gate_summary` digest can
differ across implementations while all obey the field schema. Validators cannot
enforce the promised count sums or decide what the singular gate version denotes.

**Minimal textual fix.** Define a session aggregate verdict and exact precedence,
then define every counter as a count over a named collection and publish the
validation equations. Replace singular `gate_version` with a sorted version
vector or an exact digest/registry-version meaning, consistently in manifest,
report pin, and derived inputs.

### R3-07. Q0 omits athlete-visible TrainingPeaks operation kinds

**Claim.** §6 is the closed athlete-surface inventory and compares every
TrainingPeaks athlete projection (`docs/SPEC_EARNED_SELECTION.md:786-816`).

**Evidence.** Item 5 lists workout upserts, per-session calendar notes, and the
guide attachment only (`docs/SPEC_EARNED_SELECTION.md:800-804`). The actual apply
contract also emits `mental_task_upsert`
(`build/trustworthy-phase3:athletes/scripts/apply_contract.py:293-302`),
`course_entitlement_grant` (`:332-341`), and singleton desires whose allowed
kinds include threshold and zone updates (`:343-349`). Attachments are generic,
not necessarily guide-only (`:304-330`). These payloads affect the athlete's
remote account but are absent from the supposedly closed comparison.

**Why it blocks.** E1 can pass Q0 while changing mental tasks, entitlements,
thresholds, zones, or a non-guide attachment. The audit-only no-visible-change
claim is therefore not established.

**Minimal textual fix.** Enumerate every allowed apply-contract operation kind
and compare all athlete-visible fields, logical ordering, attachment bytes, and
dispositions for each. If a kind is intentionally non-athlete-visible, name it
and justify the exclusion against the adapter. Add a fixture that fails when any
allowed kind is missing from the inventory.

### R3-08. Mode A cannot satisfy the unconditional release invariants and is not audit-only

**Claim.** Mode A evaluates/reports, E1 is audit-only, and every final/native row
must have effective PASS (`docs/SPEC_EARNED_SELECTION.md:170-182,857-863`).

**Evidence.** The gate-authority table requires every calibrated observed
PASS/FAIL in Mode A to become effective `NOT_ENFORCED`, while hypotheses are also
always `NOT_ENFORCED` (`docs/SPEC_EARNED_SELECTION.md:205-213`). Q1 and Q2,
without a Mode B qualifier, require effective PASS for every applicable final
session and native row (`:175-182`). Thus no applicable row can satisfy Q1/Q2 in
Mode A. Separately, §4.5 step 4 merges all rubric CRITICAL failures into
`blocking_issues` (`:365-367`), while only physiological hypotheses are protected
from enforcement. E1 adds Appendix 3 (`:859-863`), so it can create new approval
blockers even though it is labeled audit-only and promises no content changes.

**Why it blocks.** The rollout has no coherent E1 release predicate. One reading
makes all Mode A revisions fail Q1/Q2; another ignores stated invariants. The
rubric path can also block paid orders before E2 dispositions, contrary to the
mode's stated purpose.

**Minimal textual fix.** Scope Q1/Q2 effective-PASS requirements explicitly to
Mode B and define Mode A's release invariant in terms of complete observed
results plus `NOT_ENFORCED`. Define whether E1 rubric CRITICAL failures are
findings-only or approval blockers; if findings-only, give their state/report
routing and promotion boundary, and if blockers, stop calling E1 audit-only and
specify the required pre-rollout disposition gate.

## Non-blocking findings

1. The Appendix 4 map is correct. `archetype_registry.py` reported 100
   archetypes, 24 categories, and 600 variations with all checks passing. Parsing
   Appendix 4 and comparing ordered category/name pairs and slug IDs against
   `ALL_ARCHETYPES` found zero differences. Spot checks including punctuation and
   category boundaries also matched.

2. The tombstone algorithm is total over its stated states. An unreplaced middle
   tombstone selects the next active slot; an unreplaced last slot wraps to slot
   zero; all-retired deterministically fails because no active slot exists
   (`docs/SPEC_EARNED_SELECTION.md:684-698`). That last case is an intentional
   generation failure, not an undefined loop. A normative maximum-follow count
   would still make cycle-defense easier, but chains are already forbidden.

3. The 60-second Rest correction is accurate. Production writes one 30%
   `SteadyState` of duration 60 seconds at
   `athletes/scripts/generate_athlete_package.py:2442-2482`; it is distinct from
   the native Recovery/Rest Day pure-FreeRide rows.

4. Session-ID inputs exist on the Phase 3 golden path. A full athlete-m generation
   produced `canonical_training_model/v1` with 46 sessions; every session had an
   integer week, ISO date, positive daily ordinal, and no tuple collision. Phase
   3 assigns the ordinal at
   `build/trustworthy-phase3:athletes/scripts/canonical_training_model.py:481-505`.
   The builder can place unmatched authored documents at `date=None` (`:357-367`),
   but r3's explicit generation failure for a missing date makes that case closed
   rather than silently unstable.

5. R11 is a known migration/backlog issue: current Phase 3 skips strength outside
   configured strength phases, including taper and race
   (`build/trustworthy-phase3:athletes/scripts/generate_athlete_package.py:
   2946-2955`), whereas r3 requires a prescription or explicit decline every paid
   week. That policy can be implemented once R11's missing-evidence verdict is
   settled, but it reinforces why the E1 enforcement contradiction in R3-08
   matters.

6. `design_kj` uses 250 W even for normalized HR/RPE traces
   (`docs/SPEC_EARNED_SELECTION.md:122-132,559-569`). The spec labels it a design
   reference and does not currently use it as an athlete claim, so this is not a
   Q7 blocker. The report should nevertheless avoid presenting it without the
   reference qualifier.

7. Citation accounting does not reproduce the author's “44 verified” claim. I
   found 46 citation occurrences representing 45 unique file/range pairs. All 45
   targets and ranges exist, but two cited spans are materially imprecise:

   - the four-ID methodology map citation ends at
     `athletes/scripts/generate_athlete_package.py:355-366`, while the last two
     entries continue through line 369; and
   - `endurelabs/scripts/validate-stock-workouts.ts:1-27` reaches only the
     validator prologue/function start; the relevant assertions begin at line 31.

   The compliance-rules citation through line 142 also ends at R25, though the
   spec separately cites the scorer reference for R26. These are citation fixes,
   not independent policy blockers.

## Consistency pass

- Q3, §4.1, Appendix 2, and the R2 disposition map now agree that Q3 covers native
  design ladders only and that final-series regression is a warning.
- Q4 and §4.7 agree on four customer methodology IDs and both fail-closed
  boundaries. The cited source range is short, as noted above, but the normative
  four-entry map itself matches production.
- Q6, §4.8, Appendix 2's derived records, and seal v2 agree on state ownership and
  revision-local evidence. No contradiction was found in the fifth catalog source
  or `observed` snapshot disposition.
- Q7 and §4.9 agree that missing HR anchors produce authored RPE targets rather
  than fabricated power/HR.
- Q0 conflicts with its own “closed” claim through R3-07.
- Q1/Q2 conflict with Mode A and E1 through R3-08.
- §4.5's exact order conflicts with Appendix 3 inputs through R3-05.
- Appendix 1 overstates R2-04, R2-08, R2-09, and R2-14 as fully dispositioned
  (`docs/SPEC_EARNED_SELECTION.md:926,930-936`).

## What I verified and how

- Read `CLAUDE.md`, all three task-relevant handover skills, both prior Codex
  reviews, the complete r3 spec, and the cited Phase 3 state/seal/canonical/apply
  implementations.
- Ran `python3 athletes/scripts/archetype_registry.py`: all checks passed, with
  100 archetypes, 24 categories, and 600 variations.
- Parsed Appendix 4 JSON and compared category order, name order, generated IDs,
  and uniqueness against the live registry: exact match, zero discrepancies.
- Rendered every production archetype at L1–L6 directly through
  `generate_blocks_from_archetype`: 600/600 rendered, with exactly six pure
  FreeRide rows and 11 mixed FreeRide rows.
- Exercised tombstone selection for unreplaced middle, unreplaced final, and
  all-retired categories.
- Ran a Phase 3 athlete-m package generation in `/tmp` without writing bytecode;
  inspected all 46 canonical sessions for week/date/ordinal presence and tuple
  uniqueness.
- Compared the exact v1 seal-source object in both constructors and the current
  seal-version verification dispatch.
- Compared r3's proposed state/catalog/snapshot names, versions, projection, and
  dispositions against all Phase 3 constructors, catalog rebuild, snapshot
  creation, state normalization, and validation paths.
- Enumerated the sibling estate: 524 curated workout ZWOs and 14,840 master-plan
  ZWOs.
- Inspected every one of the 45 unique citation targets for file/range existence
  and surrounding context, with semantic checks concentrated on the new
  normative claims and every Phase 3 citation.

## What I could not verify

- There is no r3 implementation, generated certification manifest, purpose/gate
  config, report, or Mode A/Mode B replay to execute. This review therefore
  validates the proposed contracts against source and fixtures, not an
  implementation of them.
- I did not independently validate the scientific truth of any proposed
  physiology threshold or promotion disposition.
- I did not call live TrainingPeaks, Endure, Gmail, or guide-publishing services.
- I did not render all 14,840 master-plan instances or prove PDF/ZIP/MIME byte
  determinism across environments; r3 correctly makes those future acceptance
  tests rather than assuming them.
- Gmail typed-draft and Endure delivery behavior remain future fulfilment
  contracts on the Phase 3 branch, so only their specified payload surfaces and
  present local producers were inspectable.

**Verdict: NO-GO — 8 blockers.**
