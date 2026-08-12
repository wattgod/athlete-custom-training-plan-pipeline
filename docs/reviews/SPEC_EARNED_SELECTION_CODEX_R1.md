# SPEC_EARNED_SELECTION adversarial review — Codex R1

## Verdict: NO-GO

The proposed direction is valuable, but the specification is not safe to
implement as written. Its starting evidence is materially overstated, its
three supposed normative inputs disagree, and several core invariants cannot
be implemented or preserved by the described architecture. Most seriously,
the proposed certification cannot identify the actual archetype selected by
production, production mutates the rendered dose after selection, the new
blockers are waivable in ways that defeat Q1/Q2, and the manifest addition is
left as an open question even though the Phase 3 seal has two exact,
independently reconstructed input sets.

This review has **19 blockers**. These are specification blockers, not requests
for implementation polish.

## Blockers

### 1. The claimed absence of progression verification is factually false

**Claim.** The motivation says “Nothing verifies” level progression and calls
the production interval library “effectively unaudited”
(`docs/SPEC_EARNED_SELECTION.md:18-27`).

**Evidence.** Existing tests compare imported L1 and L6 power
(`athletes/scripts/test_workout_generation.py:1203-1216`), check power and
volume progression for every advanced archetype
(`athletes/scripts/test_workout_generation.py:2263-2347`), and contain
adjacent-level monotonic checks for individual designs such as BPA, Late-Race
VO2max, and Glycolytic Power
(`athletes/scripts/test_workout_generation.py:2855-2881,2899-2910`). The
registry also requires all six levels on all 100 archetypes
(`athletes/scripts/archetype_registry.py:178-209`). These checks are incomplete
and do not establish purpose-dose validity, but “nothing” and “effectively
unaudited” are not accurate.

**Why it blocks.** The spec is supposed to preserve and extend the real safety
baseline. A false greenfield premise lets an implementer replace existing
structural/progression coverage instead of inventorying it and adding the
missing adjacent-dose and purpose checks.

**Minimal textual fix.** Replace the absolute claim with a precise coverage
matrix: checks that already exist, archetypes/levels they cover, checks that
are endpoint-only, and the unverified claims this spec adds. Require existing
protections to remain as regression tests.

### 2. The “already-calibrated” gate bands are an exploratory audit, not a certified authority

**Claim.** The spec repeatedly calls the 8–14 minute and 0–6 kJ bands
“calibrated” and says no new training science is being introduced
(`docs/SPEC_EARNED_SELECTION.md:34,38-41,143-148,299-301`).

**Evidence.** `score_library.py` hardcodes two manually enumerated ID sets and
the two bands (`experimental-workout-library/score_library.py:28-42`). It runs
against a separate 39-archetype experimental model, not the production 100
archetypes (`experimental-workout-library/score_library.py:45-72,84-97`). Its
scorecard contains 234 entries, of which 79 fail
(`experimental-workout-library/_ENRICHMENT_SCORECARD.md:1-6`). All six “5x3
VO2 Classic” levels fail, with the proxy rising from 16 to 31 minutes, and most
higher Billat/Rønnestad levels fail too
(`experimental-workout-library/_ENRICHMENT_SCORECARD.md:452-465`). No calibration
dataset, expert disposition record, uncertainty analysis, or production
mapping is cited.

**Why it blocks.** Mode B would use these numbers to block paid-order content
and force fixes, reclassification, or retirement. That is a new normative
training-science decision, not enforcement of a demonstrated settled rule.

**Minimal textual fix.** Call the existing bands hypotheses. Add a required,
versioned calibration protocol with evidence, owner/approver, intended purpose
subclasses, sensitivity analysis, accepted false-positive/negative policy,
and signed dispositions against the full production library before any band
can block.

### 3. The normative dose equation contradicts the cited physiology implementation

**Claim.** Segment dose uses the preview’s fourth-power convention, while
acceptance requires the new scorer and `physiology.py` to agree for identical
segments (`docs/SPEC_EARNED_SELECTION.md:54-57,270-275`).

**Evidence.** The cited physiology implementation sums duration × power² for
each segment and represents a ramp by its arithmetic-average power
(`gravel-god-training-plans/engine/physiology.py:30-50,99-120`). The experimental
source does the same (`experimental-workout-library/progression_engine.py:63-88`).
Phase 3 preview accounting instead takes the fourth-power mean across power
samples and then squares normalized power for TSS
(`build/trustworthy-phase3:athletes/scripts/zwo_parser.py:163-183`). These
algorithms do not agree for variable-power workouts or ramps.

**Why it blocks.** TSS is a gate input and Q3 progression metric. Two compliant
implementations can produce different verdicts, and the acceptance clause
simultaneously requires both incompatible answers.

**Minimal textual fix.** Define one exact normative equation for every segment
kind, sampling/rounding rules, and ramp integration. State whether the legacy
scorer or Phase 3 accounting migrates, quantify expected manifest churn, and
replace “agree or justify” with one golden answer per fixture.

### 4. The T@VO2max gate does not implement its own “main-set” claim and is unsafe as one universal band

**Claim.** The 8–14 minute band is for “VO2-main-set work,” and the proxy’s
known short-rep over-count is said to be safely usable for band checking
(`docs/SPEC_EARNED_SELECTION.md:34,62-65,84-86`).

**Evidence.** The audit calls `E.assemble()` and passes every assembled segment
to `t_at_vo2max_proxy`; it has no main-set boundary
(`experimental-workout-library/score_library.py:45-60`). The proxy itself
explicitly says it over-counts short reps and under-counts the post-rep tail
(`experimental-workout-library/progression_engine.py:142-149`). The scorecard’s
systematic 5x3, 30/30, and 40/20 failures demonstrate format sensitivity rather
than a common purpose band
(`experimental-workout-library/_ENRICHMENT_SCORECARD.md:452-465`).

**Why it blocks.** An implementer must guess whether primers, hard starts,
finishers, repeated sets, and short-rep formats count. The same VO2 purpose can
fail merely because of rep geometry, not because it lacks the intended
stimulus.

**Minimal textual fix.** Define an authored main-set boundary in the canonical
model and manifest; specify treatment of primers/finishers; and provide
validated, versioned bands or transformations by purpose subtype and rep
geometry. Do not permit a single proxy band to block until those fixtures and
dispositions exist.

### 5. Reference W′bal is presented as a design/safety fact that the model cannot establish

**Claim.** A near-zero reference nadir means “well-designed,” recovery work
“cannot quietly drain a rider’s anaerobic reserves,” and fixed reference
constants certify the design rather than the individual
(`docs/SPEC_EARNED_SELECTION.md:23-24,58-61,84-89,156-162`).

**Evidence.** The implementation fixes W′ at 20 kJ, converts relative power to
absolute watts with FTP 250 W, sets CP to FTP/0.96, and makes recovery time
depend on the absolute CP-minus-power watt difference
(`gravel-god-training-plans/engine/physiology.py:19,69-84`). Thus the result is
not invariant to the reference FTP/W′ pair, and it cannot state the actual
rider’s reserve. The experimental source describes constants fitted to a
seven-subject cohort (`experimental-workout-library/progression_engine.py:116-139`).

**Why it blocks.** A deterministic reference-model diagnostic is defensible;
“well-designed” and “cannot drain a rider” are stronger physiological and
safety claims. Making them blockers without a sensitivity envelope smuggles
individual meaning into a reference simulation.

**Minimal textual fix.** Rename this a reference-model diagnostic, prohibit
athlete-safety or actual-reserve wording, define the exact reference model and
version, and require sensitivity/disposition evidence over a stated grid of
FTP, CP fraction, W′, and recovery constants before it can block.

### 6. FreeRide makes Q1 and library certification non-evidentiary

**Claim.** Every cycling workout passes a purpose contract, and every authored
archetype is certified in its power-rendered form
(`docs/SPEC_EARNED_SELECTION.md:84-90,250-260`).

**Evidence.** Phase 3 correctly gives a FreeRide segment target type `free`
(`build/trustworthy-phase3:athletes/scripts/canonical_training_model.py:164-194`).
The cited scorer invents 55% FTP for every FreeRide
(`gravel-god-training-plans/engine/physiology.py:99-120`), while Phase 3 preview
inventories use 55% or 65% depending on duration and explicitly call it a
TSS-only estimate (`build/trustworthy-phase3:athletes/scripts/zwo_parser.py:126-137`).
Production creates FreeRide testing segments
(`athletes/scripts/nate_workout_generator.py:2495-2528`) and a three-hour
B-race FreeRide overlay
(`athletes/scripts/generate_athlete_package.py:2024-2082`). A render sweep of
the 600 registry entries found 17 FreeRide entries across three archetypes.

**Why it blocks.** An assumed intensity does not certify a self-paced test or
race. Different existing assumptions can produce different dose verdicts for
content that has no prescribed power at all.

**Minimal textual fix.** Give `free` its own non-power contract (identity,
duration, intent, and truthful no-target semantics), exclude it from
power-dose blocking, and explicitly enumerate race/test/rest treatment. Where
a dose guarantee is required, replace FreeRide with an actual prescription.

### 7. The manifest cannot identify or attest the production workout that was selected and sealed

**Claim.** A manifest row keyed by archetype ID × level will gate generation
and bind the exact library that produced a plan
(`docs/SPEC_EARNED_SELECTION.md:91-95,174-181`).

**Evidence.** Production archetypes have names but no stable ID field; the
registry’s source map is keyed by name and its listing returns name/category/
source/levels/format only (`athletes/scripts/archetype_registry.py:72-118,137-175`).
The selector returns the chosen archetype dictionary
(`athletes/scripts/nate_workout_generator.py:550-798`), but the renderer returns
only name, description, and XML blocks
(`athletes/scripts/nate_workout_generator.py:3211-3219,3237-3283`). The package
then records the block-builder label `bb_name`, not the selected Nate archetype
(`athletes/scripts/generate_athlete_package.py:2253-2262,2316-2321`). Worse, it
changes segment durations after render to match a block target
(`athletes/scripts/generate_athlete_package.py:2274-2285`; scaling semantics at
`athletes/scripts/workout_templates.py:351-368,420-444`).

**Why it blocks.** The sealed model cannot prove which manifest row authorized
the workout, and the row’s native metrics need not describe the post-scale
segments. Q2 can pass while the sealed workout has a different dose.

**Minimal textual fix.** Establish immutable public archetype IDs; return and
propagate exact ID, category, level, source digest, renderer version, variation,
and transformation parameters into the canonical session. Gate the final
sealed segments, and define whether transformed variants receive their own
manifest identity or an independently checked final-dose verdict.

### 8. Q1 covers every cycling workout, but W2 covers only Nate archetype entries

**Claim.** Every cycling workout in a released plan is gated, while W2’s
certification source is the ~600 Nate archetype×level entries
(`docs/SPEC_EARNED_SELECTION.md:84-95,166-181`).

**Evidence.** `workout_mapper` bypasses Nate for a handcrafted Endurance
renderer (`athletes/scripts/workout_mapper.py:208-215,256-264`). The package
also writes bespoke B-race and travel-day ZWOs
(`athletes/scripts/generate_athlete_package.py:2024-2129`) and retains a legacy
overlay path after the block-builder render path
(`athletes/scripts/generate_athlete_package.py:2324-2415`). None is an
archetype×level manifest row as specified.

**Why it blocks.** The final invariant has unowned workout origins. An
implementer must either violate Q1, manufacture fake archetype IDs, or silently
exempt content the spec says must pass.

**Minimal textual fix.** Define an exhaustive workout-origin union and a gate
contract for every branch: Nate entry, handcrafted template, assessment,
race/self-paced, fixed athlete session, and overlay. Make an unclassified
cycling origin non-waivable, and add coverage fixtures for each branch.

### 9. Q3 is internally contradictory and differs from the proposed runner

**Claim.** Dose is “monotonically non-decreasing,” yet a flat progression
fails; “TSS/min at minimum” is also not defined as two metrics or a ratio
(`docs/SPEC_EARNED_SELECTION.md:96-98`).

**Evidence.** The proposed source compares rounded TSS and rounded duration
independently with `>=`, so a flat pair passes
(`experimental-workout-library/score_library.py:45-67`). It updates the prior
value even after a failure and applies a purpose gate instead of the dose gate
to enumerated VO2/W′ rows (`experimental-workout-library/score_library.py:58-70`).

**Why it blocks.** Strict versus non-strict monotonicity, rounding plateaus,
purpose-gated archetypes, multi-axis progression, and whether one failing
transition fails a row or the whole archetype are release-changing choices.

**Minimal textual fix.** Specify the exact unrounded metric vector or ratio,
epsilon, strict/non-strict relation, allowed plateaus, transition comparison,
purpose-gated behavior, and row/archetype verdict propagation. Add fixtures
for flat, rounded-flat, mixed-direction, and one-transition failures.

### 10. The waiver taxonomy permits the exact releases Q1 and Q2 forbid

**Claim.** Q1/Q2 say only passing, certified workouts may appear, W2 forbids a
library-level waiver, but all three new blockers are coach-waivable
(`docs/SPEC_EARNED_SELECTION.md:84-95,149-155,182-188`).

**Evidence.** The fulfilment policy says structural rules are waivable unless
explicitly in the closed non-waivable set
(`docs/SPEC_TRUSTWORTHY_FULFILMENT.md:207-224`). Phase 3 implements that exact
default and does not include any proposed earned-selection code in the
non-waivable set
(`build/trustworthy-phase3:webhook/fulfillment_state.py:47-70,194-200`).

**Why it blocks.** Waiving `LIBRARY_UNCERTIFIED` is a per-order library waiver.
Waiving `WORKOUT_DOSE_MISMATCH` releases content that did not earn selection.
Both directly falsify the stated invariants and make the certification gate
advisory.

**Minimal textual fix.** Choose one coherent policy. Either make certification
identity/integrity and purpose-dose gates non-waivable with fix-and-regenerate
remediation, or explicitly weaken Q1/Q2 to allow sealed, attributed exceptions
and define which codes/ranges a coach may waive. Add negative approval tests
for every non-waivable code.

### 11. The manifest-to-seal design is unresolved and cannot safely read a mutable repository-global file

**Claim.** The manifest digest joins the model seal, while its storage and
“exact seal-input ordering” remain open questions
(`docs/SPEC_EARNED_SELECTION.md:91-95,174-181,317-327`).

**Evidence.** The fulfilment spec defines an acyclic, exact seal input and
finalization sequence (`docs/SPEC_TRUSTWORTHY_FULFILMENT.md:135-170`). Phase 3’s
apply-contract code hashes exactly canonical model, review items, guide
sources, and operation payloads
(`build/trustworthy-phase3:athletes/scripts/apply_contract.py:693-708`), while
release finalization independently reconstructs the same object
(`build/trustworthy-phase3:webhook/fulfillment_state.py:802-829`). Artifact
finalization seals per-revision files and then freezes the release manifest
(`build/trustworthy-phase3:webhook/fulfillment_state.py:832-898`).

**Why it blocks.** “Ordering” is not editorial: adding a field requires a seal
version/schema migration and identical changes in both constructors and all
verifiers. Reading only the current in-repo manifest during later verification
would make an old approval depend on mutable global state.

**Minimal textual fix.** Resolve the question normatively: define a new seal
version and exact canonical key, copy/snapshot the certification manifest (or
its complete canonical payload) into each generation revision, include it in
the release artifact inventory, update both seal constructors/verifiers, and
specify backward verification and stale-manifest tests.

### 12. “Findings” do not ride an existing Phase 3 review-item rail

**Claim.** Warnings and Mode A results attach as “findings” through the
existing state machine and review surface
(`docs/SPEC_EARNED_SELECTION.md:106-114,204-207,233-236`).

**Evidence.** Phase 3 has only four review item types: blocker, required
confirmation, soft confirmation, and verified fact
(`build/trustworthy-phase3:webhook/fulfillment_state.py:41-43`). Its catalog is
built only from blockers, confirmations, derived values, and the release fact
(`build/trustworthy-phase3:webhook/fulfillment_state.py:344-402`). The review
page ordering in the fulfilment spec has the same closed categories
(`docs/SPEC_TRUSTWORTHY_FULFILMENT.md:406-416`). There is no generic finding
type or source named by this spec.

**Why it blocks.** An implementer must invent the type, acknowledgment
semantics, approval effect, ranking, sensitivity, and seal membership. Mode A
acceptance cannot assert a representation that is not defined.

**Minimal textual fix.** Map each earned-selection output to an existing exact
type (and say whether it requires acknowledgment) or specify a versioned new
review type end to end: state schema, catalog construction, page rendering,
approval snapshot, redaction, ordering, email projection, and seal input.

### 13. Q7 does not specify how per-workout metrics enter the enforced derived-value registry

**Claim.** Every quality metric is registered with source, basis, and
sensitivity (`docs/SPEC_EARNED_SELECTION.md:115-120`).

**Evidence.** Phase 3’s artifact coverage is schema-owned and rejects unknown
artifact schemas or extra/missing derived fields
(`build/trustworthy-phase3:athletes/scripts/derived_registry.py:234-348,431-475`).
The canonical model currently creates two plan-level derived entries, not a
per-workout quality collection
(`build/trustworthy-phase3:athletes/scripts/canonical_training_model.py:550-584`).
Every derived entry also becomes an individual verified fact on the review
surface (`build/trustworthy-phase3:webhook/fulfillment_state.py:356-364`).

**Why it blocks.** Six hundred library rows plus several metrics per emitted
session create unresolved ownership and cardinality. It is unknown whether
the manifest, canonical session, review catalog, or a new artifact owns the
value, and blindly registering each metric could flood the coach catalog or
leak design-power facts for null-FTP athletes.

**Minimal textual fix.** Define the registry artifact/schema, stable entry IDs
and field paths, value class, basis/input payload, sensitivity, revision,
materialization point, aggregation/cardinality, and which entries project to
coach versus athlete review surfaces. Add coverage and redaction fixtures.

### 14. The asserted “25 rules (14 CRITICAL)” normative rubric does not exist

**Claim.** The three cited block-builder assets jointly define R01–R25 with 14
CRITICAL rules and written severities
(`docs/SPEC_EARNED_SELECTION.md:35,73-74,192-203`).

**Evidence.** The compliance-rules document contains 25 rules but only 13 are
marked CRITICAL (`gravel-god-training-engine/docs/block-builder-compliance-rules.md:7-139`).
The scorer runs R01–R26, adds a CRITICAL R26 not in that document, and skips
R18 and R22 as NOT_IMPLEMENTED
(`gravel-god-training-engine/docs/block-builder-scorer-reference.py:856-860,1006-1010,1056-1075,1168-1205`).
The skill’s separate list of 14 “Critical Rules” is a coaching list with
different grouping/severity—for example, block notes are non-negotiable there
but R07 is WARNING in the rule document
(`gravel-god-training-engine/docs/block-builder-skill.md:335-352`;
`gravel-god-training-engine/docs/block-builder-compliance-rules.md:37-40`).

**Why it blocks.** “Use both as normative” gives incompatible rule counts,
severities, and executable coverage. Severity controls blocking and waiver
behavior, so implementation cannot choose harmlessly.

**Minimal textual fix.** Check in one versioned rule registry containing the
complete ID set, severity, applicability, exact inputs, algorithm, and owner.
Explicitly reconcile R26, R18/R22, the skill’s 14-rule list, and every severity;
make the other documents descriptive projections with a consistency test.

### 15. W3 treats the existing 11 rules as implemented even where they are no-ops or semantically different

**Claim.** W3 only requires implementing the listed missing rules and treats
R01–R06, R08, R11, R14, R19, and R20 as the existing base
(`docs/SPEC_EARNED_SELECTION.md:192-203`).

**Evidence.** Current R08 and R11 unconditionally pass with comments that they
are checked elsewhere, but no result is merged into this scorer
(`athletes/scripts/block_compliance.py:272-281,351-404`). Current R03 accepts a
dynamic 30–65/70/75/85% range
(`athletes/scripts/block_compliance.py:156-199`), while the cited rule says pass
at 50–65%, fail below 40% or above 65%, and leaves 40–49% undefined
(`gravel-god-training-engine/docs/block-builder-compliance-rules.md:17-20`).

**Why it blocks.** Adding only “missing” rules leaves false passes and
different algorithms under supposedly normative IDs. Mode B could advertise
full-rubric enforcement while not checking fuel or strength at all.

**Minimal textual fix.** Require an all-rule parity audit and reimplementation,
not a missing-ID patch. For each existing rule, document current versus target
semantics, close reference gaps, identify its authoritative post-render input,
and add pass/fail fixtures proving the result reaches fulfilment state.

### 16. “Run all 25 post-overlay” lacks the data and applicability contract several rules require

**Claim.** Every rule runs on every plan after overlays, against the content
that is sealed (`docs/SPEC_EARNED_SELECTION.md:106-110,196-213`).

**Evidence.** The reference skill declares monitoring and the previous block
required inputs (`gravel-god-training-engine/docs/block-builder-skill.md:12-23`).
The scorer admits R18 needs zone data and R22 needs previous-block data
(`gravel-god-training-engine/docs/block-builder-scorer-reference.py:856-860,1006-1010`),
while R25 passes when raw text is absent
(`gravel-god-training-engine/docs/block-builder-scorer-reference.py:1036-1054`).
Production currently validates `_bb_plan` before any ZWO is rendered
(`athletes/scripts/generate_athlete_package.py:796-849`), then adds race/travel
overlays, scales XML, injects fueling text, and follows additional legacy
overlays (`athletes/scripts/generate_athlete_package.py:2000-2129,2274-2303,2324-2415`).

**Why it blocks.** “Post-overlay plan” is not one existing object. Some rules
need canonical sessions, some guide/description text, some strength/fueling
artifacts, and R22 needs historical state. First orders and absent monitoring
also need explicit applicability—not invented passing results.

**Minimal textual fix.** Add a per-rule execution matrix specifying exact
sealed input artifact/path, required historical/intake inputs, execution stage,
not-applicable versus unavailable semantics, crash behavior, and output code.
Define the final ordering relative to canonical-model build, review-catalog
refresh, apply-contract construction, and seal finalization.

### 17. W4 leaves a second methodology authority in the selector and can silently change selection

**Claim.** `methodologies.yaml` becomes the single source, and W4’s selector
work is described as reconciling only its stale docstring/scoring
(`docs/SPEC_EARNED_SELECTION.md:99-105,215-229`).

**Evidence.** `select_methodology.py` contains a complete inline four-method
fallback and returns it when config is unavailable
(`athletes/scripts/select_methodology.py:47-59,72-141`). The YAML itself
explicitly defines four customer methods
(`athletes/scripts/config/methodologies.yaml:1-12`). Separately, Nate’s 14
methodologies drive avoid lists and variation selection
(`athletes/scripts/nate_workout_generator.py:183-225,722-798`), while the
package maps the four IDs to render IDs
(`athletes/scripts/generate_athlete_package.py:355-366`).

**Why it blocks.** Leaving the inline fallback violates Q4. Re-deriving Nate
behavior is also not copy-only: avoid lists and variation offsets select
different workouts, conflicting with the no-replanning and byte-identity
claims.

**Minimal textual fix.** Explicitly delete the inline fallback or generate it
from the YAML and fail closed on unavailable/invalid config. Specify the exact
four-ID→render-style mapping and preserve it with selection goldens before
removing legacy entries; document every intended selection change.

### 18. The HR/RPE gate is both factually inconsistent with Phase 3 and too vague to implement

**Claim.** HR/RPE content is gated on “duration × canonical effort scale
(RPE/10, HR ratio), consistent with the canonical intensity accounting the
Phase 3 preview uses” (`docs/SPEC_EARNED_SELECTION.md:115-120,245-264`).

**Evidence.** Phase 3 does not use RPE/10 as its neutral intensity axis. It
maps RPE through a piecewise table (for example, RPE 6→0.815 and RPE 10→1.30)
and maps %LTHR/%HRmax through separate piecewise tables
(`build/trustworthy-phase3:athletes/scripts/canonical_training_model.py:119-147`).
FreeRide has no effort value at all
(`build/trustworthy-phase3:athletes/scripts/canonical_training_model.py:164-166`).
The earned-selection spec supplies no aggregation formula for interval on/off,
ramps, low/high bands, HR kinetics, missing anchors, mixed targets, or gate
bands by purpose.

**Why it blocks.** Two implementers can produce different dose values and
PASS/FAIL results while claiming compliance. The asserted inheritance from
Phase 3 is factually wrong, and short-interval HR prescriptions need different
semantics from power traces.

**Minimal textual fix.** Reference one exact Phase 3 normalization function or
define a replacement migration. Specify formulas and bands for every target
shape/purpose, HR kinetics limitations, missing-anchor behavior, and FreeRide;
add HR-LTHR, HRmax-only, RPE-only, interval, ramp, and mixed/free fixtures with
zero athlete-facing power assertions.

### 19. Retirement/disposition, Mode B entry, in-flight orders, and byte identity contradict one another

**Claim.** Failed entries may be fixed, reclassified, or retired; Mode B needs
only zero “CRITICAL-class” disposition backlog; plan bytes do not change; and
the work is “no replanning” except removal from pools
(`docs/SPEC_EARNED_SELECTION.md:182-188,233-241,276-288,293-301`).

**Evidence.** Fixing interval structure changes workout bytes. Reclassification
changes gate meaning. Removing an archetype from an ordered category changes
modulo/index selection for later variations
(`athletes/scripts/nate_workout_generator.py:540-542,791-798`) and can break the
same-archetype series behavior production deliberately preserves
(`athletes/scripts/generate_athlete_package.py:2199-2244`). Archetype identity
is already treated as a public contract by the repository’s binding handover
rules, while the registry is name-keyed (`athletes/scripts/archetype_registry.py:72-118`).
The spec gives no policy for an order generated under manifest N but awaiting
review when manifest N+1 retires its selected entry, no tombstone/replacement
rules, no manifest-regeneration owner, and no atomic stale-manifest behavior.
Q2 requires every selectable emitted entry to pass, which is stronger than
Mode B’s “zero CRITICAL-class failures.”

**Why it blocks.** The rollout can strand paid orders, invalidate a sealed
approval, silently substitute a workout, reshuffle series/goldens, or enter
Mode B with failing selectable rows. The byte-identity acceptance criterion is
impossible during the same phase that fixes or retires content.

**Minimal textual fix.** Split audit-only plumbing from reviewed content and
selection migrations. Require all selectable rows—not an undefined critical
subset—to pass before Mode B. Define immutable tombstones and explicit
replacement IDs without list reindexing, manifest owner/regeneration command
and CI atomicity, per-revision manifest pinning, and in-flight policy
(grandfather sealed revision versus invalidate/regenerate/re-review). Enumerate
and rebaseline every intentional golden/content change and prove R14 series
coherence after each retirement.

## Non-blocking findings

1. **The Phase 3 sequencing dependency is stated clearly enough.** The header
   expressly depends on Phases 1–3 implemented on `build/trustworthy-phase3`
   (`docs/SPEC_EARNED_SELECTION.md:6-7`), and the fulfilment rollout confirms
   canonical model, registry, and offline contract are Phase 3 work
   (`docs/SPEC_TRUSTWORTHY_FULFILMENT.md:1086-1107`). Implementation still must
   branch from or merge that code; this is not a blocker in the current text.
2. **The 100/600 production count is correct.** Runtime registry validation
   reported 100 archetypes, 24 categories, and 600 level entries, matching
   `athletes/scripts/archetype_registry.py:62-65`. The registry module’s older
   prose still says 95/570 at `:12-19`; that stale local documentation should
   be cleaned separately.
3. **The “11 current rules” count is correct but their docstring is not.** The
   current scorer registers exactly 11 result IDs
   (`athletes/scripts/block_compliance.py:376-403`), while its header already
   claims 25/14 (`athletes/scripts/block_compliance.py:1-8`). The substantive
   false-pass/parity issue is blocker 15.
4. **Removing `GG_STRICT_COMPLIANCE` has no verified current CI dependency.** A
   repository search found the runtime branch at
   `athletes/scripts/generate_athlete_package.py:823-828` and prose elsewhere,
   but no CI/workflow setting it. Mode B should remove hard-fail behavior in
   favor of fulfilment blockers, not describe that as “strictness is the only
   mode”; tests should inject blocker fixtures directly.
5. **The Endure doctrine citation is accurate.** The cited whitepaper states
   calendar as the single truth and deterministic code before LLM prose
   (`endurelabs/docs/PLAN-GENERATOR-WHITEPAPER.md:15-58`). It does not validate
   the proposed physiological thresholds.
6. **The reference R03 itself has a gap.** It says PASS at 50–65% and FAIL only
   below 40% or above 65%, leaving 40–49% unspecified
   (`gravel-god-training-engine/docs/block-builder-compliance-rules.md:17-20`).
   The single rule registry required by blocker 14 should close this boundary.

## What I verified and how

- Read the complete `docs/SPEC_EARNED_SELECTION.md`, complete
  `docs/SPEC_TRUSTWORTHY_FULFILMENT.md`, `CLAUDE.md`, and all three task-relevant
  repository handover skills before reviewing code.
- Reviewed this worktree at `c168f6e` and the local Phase 3 target branch at
  `d291eb4` using `git show build/trustworthy-phase3:<path>` for
  `canonical_training_model.py`, `zwo_parser.py`, `derived_registry.py`,
  `apply_contract.py`, and `webhook/fulfillment_state.py`.
- Inspected every specifically named pipeline file: `block_compliance.py`,
  `nate_workout_generator.py`, `new_archetypes.py` and its imported registry,
  `validate_workout_distribution.py`, `select_methodology.py`, and
  `config/methodologies.yaml`; also traced the actual consumers through
  `generate_athlete_package.py`, `workout_mapper.py`, and
  `workout_templates.py`.
- Executed the production registry validator with `PYTHONPATH=athletes/scripts`:
  it returned valid, 100 archetypes, 24 categories, 600 entries. I also rendered
  every registry entry through `generate_blocks_from_archetype` to locate
  FreeRide output (17 entries across three archetypes).
- Read the sibling `gravel-god-training-plans/engine/physiology.py` at sibling
  HEAD `50af6e15`.
- Read the full block-builder compliance rule document and skill, and inspected
  every relevant scorer implementation and its R01–R26 execution list in
  `gravel-god-training-engine` at sibling HEAD `22a8b41`.
- Read the cited Endure whitepaper at `endurelabs` HEAD `a2ebe1e7f`; the spec’s
  table omits the parent `GravelGod/` path, but the file exists there.
- Located `experimental-workout-library/progression_engine.py`,
  `score_library.py`, and `_ENRICHMENT_SCORECARD.md` in the main pipeline
  checkout at `95d238a`. `progression_engine.py` is tracked there;
  `score_library.py` and `_ENRICHMENT_SCORECARD.md` are untracked, exactly as
  the task warned. I read them directly without modifying them.
- Used source inspection and small read-only registry/render probes. I did not
  run a production order, mutate external systems, or use customer data.

## What I could not verify from this sandbox

1. I could not verify that the two experimental bands were empirically or
   coach-calibrated: no calibration dataset, review log, acceptance rationale,
   or signed dispositions were present in the cited files.
2. I could not verify scientific validity beyond the repository’s equations
   and stated caveats (including the cited Skiba cohort/constants). No external
   literature review or athlete validation dataset was part of this task.
3. I could not verify Mode A runtime cost, coach usability, or disposition
   throughput for ~600 entries because no implementation, complete production
   manifest, owner/SLA, or replay output exists.
4. I could not verify live behavior for in-flight paid orders, approval across
   a manifest change, or retirement/regeneration because those policies and
   code do not exist.
5. I did not verify future Phase 3 changes beyond local branch `d291eb4`; this
   review targets the post-Phase-3 code explicitly named by the spec and task.

## Final assessment

Do not implement this draft. First reconcile the mathematical authority, rule
registry, waiver semantics, actual selected-workout identity, transformed
content attestation, review/registry schemas, and per-revision seal design.
Then make rollout and content migrations explicit, including in-flight orders
and stable archetype tombstones.

**VERDICT: NO-GO — 19 blockers.**
