# SPEC_EARNED_SELECTION adversarial review — Codex R2

## Verdict: NO-GO

r2 is materially better than r1. It corrects the greenfield premise, demotes
the experimental bands to hypotheses, separates audit-only plumbing from
content changes, adds final-segment gating, and states the 100/600, 524, and
14,840 estate counts correctly. It is still not safe to implement as the
normative release contract.

The principal remaining problem is that several disposition entries name the
artifact that ought to resolve an issue without supplying the normative content
that artifact must contain. The rule registry, execution matrix, quality-finding
state rail, derived artifact registration, seal-v2 input, and stable-ID selection
algorithm are still decisions left to the implementer. The new dose equation
also has undefined FreeRide and sampling behavior, and Q0's acceptance list does
not cover the actual athlete-facing estate.

This review has **14 blockers**.

## R1 blocker verification

| R1 | Status | Verification and evidence |
|---:|---|---|
| 1 | **RESOLVED** | §0.3 replaces the false “nothing verifies” premise with an accurate partial-coverage matrix and requires the protections to remain (`docs/SPEC_EARNED_SELECTION.md:55-70`). The cited endpoint, advanced-subset, named-design, and registry checks exist at the cited lines (`athletes/scripts/test_workout_generation.py:1203-1216,2263-2347,2855-2910`; `athletes/scripts/archetype_registry.py:178-209`). |
| 2 | **PARTIAL** | §3 correctly calls the bands hypotheses and requires full-library disposition and W′ sensitivity (`docs/SPEC_EARNED_SELECTION.md:150-178`). It does not define an enforceable promotion record/signature or distinguish observed hypothesis failures from effective manifest verdicts; §5.1 has one undifferentiated `verdict` (`:410-415`). Blocker R2-02. |
| 3 | **RE-OPENED** | §1 chooses fourth-power trace math, but its 1 Hz ramp endpoint and FreeRide duration semantics remain undefined (`docs/SPEC_EARNED_SELECTION.md:76-93`). Its claim that this matches Phase 3 is false: Phase 3 represents a complete ramp by one arithmetic-average sample (`build/trustworthy-phase3:athletes/scripts/zwo_parser.py:78-91`) and stores that result as canonical session TSS (`build/trustworthy-phase3:athletes/scripts/canonical_training_model.py:280-299,500-520`). Blocker R2-01. |
| 4 | **RESOLVED** | §4.2 adds an authored main-set boundary, explicitly dispositions primers/hard starts/finishers, and keys bands by rep geometry (`docs/SPEC_EARNED_SELECTION.md:211-218`). The calibration prerequisite prevents the old universal band from immediately blocking. |
| 5 | **RESOLVED** | §1 accurately limits W′bal to a fixed reference-design diagnostic, prohibits athlete-safety wording, and §3 adds the requested FTP/W′ sensitivity grid (`docs/SPEC_EARNED_SELECTION.md:94-100,164-171`). |
| 6 | **RE-OPENED** | §4.3 correctly refuses invented FreeRide watts, but the normative equation and Q3 do not define zero-trace or mixed free/prescribed workouts. Six production Rest Day rows are pure FreeRide; the other 11 FreeRide rows are mixed testing designs. “Excluded from all power-dose gates” (`docs/SPEC_EARNED_SELECTION.md:220-230`) conflicts with the all-archetype TSS ladder in §4.1 (`:198-207`). Blocker R2-01. |
| 7 | **PARTIAL** | §4.4 now propagates the selected identity and separately checks the pristine manifest row and final transformed segments (`docs/SPEC_EARNED_SELECTION.md:232-253`). That closes the post-render-dose hole. The stable-ID assignment and selection migration needed to make the identity reliable remain unspecified (§5.3), so attestation is only partly resolved. Blocker R2-11. |
| 8 | **PARTIAL** | §4.5a adds a fail-closed catch-all, but it does not semantically classify all reachable branches. Production also emits progressive interval/endurance blocks, standard template blocks, a one-second Rest ZWO, and fixed external cycling sessions (`athletes/scripts/generate_athlete_package.py:2448-2484,2792-2855`; `build/trustworthy-phase3:athletes/scripts/canonical_training_model.py:333-351`). “Legacy overlay path” is not an origin contract for all of them. Blocker R2-04. |
| 9 | **RESOLVED** | §4.1 now states unrounded metrics, both inequalities, epsilons, transition scope, archetype propagation, and fixtures (`docs/SPEC_EARNED_SELECTION.md:196-209`). The new mismatch between native ladders and differently scaled shipped series is a separate r2 defect (R2-03), not the old underspecification. |
| 10 | **PARTIAL** | §4.6 makes the three named integrity codes non-waivable and requires negative tests (`docs/SPEC_EARNED_SELECTION.md:289-304`). “Manifest-pin failures” remain unnamed, and the required server-owned remediation entries and fulfilment-policy amendment are absent. Blocker R2-05. |
| 11 | **RE-OPENED** | §5.2 selects per-revision snapshotting and a seal bump, but still does not specify the snapshot path/schema, digest algorithm, exact new seal-source key, or new version identifier (`docs/SPEC_EARNED_SELECTION.md:421-435`). Both real constructors hash an exact four-key object and independently reconstruct it (`build/trustworthy-phase3:athletes/scripts/apply_contract.py:693-708`; `build/trustworthy-phase3:webhook/fulfillment_state.py:802-829`). Blocker R2-07. |
| 12 | **RE-OPENED** | §4.8 lists the intended behavior of `quality_finding/v1`, but no authoritative state collection/write operation or snapshot disposition is defined (`docs/SPEC_EARNED_SELECTION.md:342-360`). Phase 3 rebuilds the catalog from four fixed source collections and requires one approval-snapshot record per catalog item (`build/trustworthy-phase3:webhook/fulfillment_state.py:344-408,411-458`). Blocker R2-06. |
| 13 | **RE-OPENED** | §4.10 chooses an artifact plus two aggregate entries, which is the right shape, but keys rows by a nonexistent “canonical session id” and omits the two derived entries' required field/basis/inputs/time/revision contract (`docs/SPEC_EARNED_SELECTION.md:386-402`). Canonical sessions currently have no `id` (`build/trustworthy-phase3:athletes/scripts/canonical_training_model.py:500-533`), and the registry rejects incomplete or extra coverage (`build/trustworthy-phase3:athletes/scripts/derived_registry.py:361-415,431-475`). Blocker R2-08. |
| 14 | **RE-OPENED** | §4.5 says the future registry will decide whether R26 is adopted, whether R18/R22 are implemented, the R03 boundary, and severity reconciliation (`docs/SPEC_EARNED_SELECTION.md:255-274`). Those are the unresolved normative choices from R1, not their dispositions. The claimed single normative rubric still does not exist. Blocker R2-09. |
| 15 | **RESOLVED** | §4.5(2) requires an all-rule semantic parity audit and specifically forbids leaving R08/R11 as unmerged passes (`docs/SPEC_EARNED_SELECTION.md:269-274`). Current no-ops remain visible at `athletes/scripts/block_compliance.py:272-281`; r2 now clearly requires their replacement or merged delegation. |
| 16 | **RE-OPENED** | §4.5(3) lists the columns a future execution matrix needs but supplies no per-rule rows, artifacts, algorithms, or final ordering relative to catalog/contract construction (`docs/SPEC_EARNED_SELECTION.md:275-287`). An implementer still decides the contract R1 required the spec to settle. Blocker R2-09. |
| 17 | **PARTIAL** | §4.7 gives the four-ID mapping and protects avoid lists/offsets (`docs/SPEC_EARNED_SELECTION.md:321-340`). It deletes only `select_methodology.py`'s config fallback. The package still defaults unknown IDs to POLARIZED and Nate still defaults unknown render styles to POLARIZED (`athletes/scripts/generate_athlete_package.py:592-593`; `athletes/scripts/nate_workout_generator.py:728-735`), and r2 does not require those boundaries to fail closed. Blocker R2-10. |
| 18 | **PARTIAL** | The Phase 3 piecewise normalization reference is now factually correct (`docs/SPEC_EARNED_SELECTION.md:362-384`; `build/trustworthy-phase3:athletes/scripts/canonical_training_model.py:119-147`). Missing-anchor behavior is not: Phase 3 deliberately projects HR-without-anchor to `rpe_pending_lthr`, then authors RPE targets; r2 simultaneously says RPE content is sanity-gated and that the workout is not dose-gated. Blocker R2-12. |
| 19 | **PARTIAL** | The E1/E2/E3 split, all-selectable-row entry bar, manifest pin, tombstones, and in-flight grandfathering are substantial fixes (`docs/SPEC_EARNED_SELECTION.md:437-455,488-505`). The promised ID-keyed selection algorithm and universal equivalence proof are not defined; finite golden profiles cannot establish Q0 for the current modulo selector. Blocker R2-11. |

## Blocking findings

### R2-01. The normative dose function is not total, and it creates a second incompatible “TSS”

**Claim.** §1 defines one exact authority for every workout and says its
fourth-power result matches Phase 3 (`docs/SPEC_EARNED_SELECTION.md:76-93`).

**Evidence.** “Linear interpolation low→high” at 1 Hz does not say whether an
N-second ramp samples `i/N`, `i/(N-1)`, interval endpoints, or interval
midpoints. More importantly, `free_ride` is removed from the trace while TSS
still uses an undefined `duration_hours`: trace duration and whole-workout
duration produce different answers for mixed tests, and a pure-FreeRide workout
has no mean at all. A production render sweep found 17 FreeRide rows and six
zero-prescribed-trace rows (Rest Day L1–L6). The source structures make Rest Day
legitimately zero-duration (`athletes/scripts/new_archetypes.py:3022-3094`) and
its renderer emits only a zero-second FreeRide
(`athletes/scripts/nate_workout_generator.py:2465-2471`). §4.3 exempts all free
segments from power-dose gates, while §4.1
requires TSS progression for every archetype (`docs/SPEC_EARNED_SELECTION.md:
198-207,220-230`).

The alleged Phase 3 match is also wrong. Its ZWO parser collapses a ramp to
`(low + high) / 2` before the fourth-power mean
(`build/trustworthy-phase3:athletes/scripts/zwo_parser.py:78-91,163-183`) and
includes 55%/65% FreeRide estimates (`:126-137`). That TSS is already stored in
canonical sessions and projected as planned TSS
(`build/trustworthy-phase3:athletes/scripts/canonical_training_model.py:280-299,
500-520`). r2 neither migrates that field nor gives the new internal quantity a
different name.

**Why it blocks.** Golden implementers can disagree on ramps, mixed FreeRide,
pure FreeRide, duration, and which TSS feeds Q3/rubric/reporting. A quality gate
can contradict the sealed canonical TSS while both claim authority.

**Minimal textual fix.** Define an exact sample index formula, valid/invalid
durations, trace-duration semantics, empty-trace sentinel/result, mixed-free
aggregation, and Q3 treatment for non-dose archetypes. Explicitly choose either
to migrate canonical `tss` (and address Q0/TP churn) or name the internal metric
distinctly and state which consumers use each.

### R2-02. Hypothesis and promotion semantics are not enforceable, and Q3 bypasses calibration

**Claim.** A hypothesis is findings-only until an owner-signed full-library
calibration promotes it (`docs/SPEC_EARNED_SELECTION.md:150-178`).

**Evidence.** The proposed gate config has a status flag, while the manifest has
one undifferentiated `verdict` (`docs/SPEC_EARNED_SELECTION.md:160-171,410-415`).
No schema binds a promotion to the disposition log, no signature/approval form
or digest is defined, and no CI rule proves that every affected row and the
accepted false-positive/negative policy were reviewed. The text says Mode A is
report-only and E3 requires calibrated bands, but it does not define what a new
or remaining `hypothesis` does after Mode B is active, nor whether its observed
FAIL can make a manifest row uncertified.

Separately, §4.1 hard-codes `+1.0 TSS` and `−0.05 TSS/min` as a library-retiring
gate while §9 concedes they are merely proposed (`docs/SPEC_EARNED_SELECTION.md:
196-209,526-530`). A 0.05 TSS/min density regression equals 3 TSS/hour; no
evidence or calibration protocol is supplied for treating that exact boundary
as authoritative.

**Why it blocks.** A status edit can silently turn experimental science into a
paid-order blocker, and two implementations can give hypothesis failures
different effective verdicts. Q3 can force fixes/retirements without passing the
authority protocol r2 correctly requires for other physiological thresholds.

**Minimal textual fix.** Define separate `observed_verdict` and
`effective_verdict`, with hypothesis always effective-NOT_ENFORCED in every
mode. Add a machine-valid promotion artifact (owner identity, reviewed row set,
dispositions digest, policy, timestamp, gate version) required by CI and sealed
into the manifest. Put Q3 epsilons through that protocol or provide their
settled owner disposition and evidence.

### R2-03. Native-library Q3 does not prove progression in the series the athlete rides

**Claim.** Failing one L1→L6 transition invalidates the archetype because the
production series advances one level per load week
(`docs/SPEC_EARNED_SELECTION.md:198-207`).

**Evidence.** Production does advance a named series by one level
(`athletes/scripts/series_tracker.py:112-148,178-185`), but day-cap fitting and
the weekly budget can down-level or hard-cap the workout *after* the tracker has
recorded that assignment (`athletes/scripts/block_builder.py:261-284,348-362,
473-495`). The resulting workout is then independently rescaled to that block
target (`athletes/scripts/generate_athlete_package.py:2274-2285`). §4.4 re-runs
only the purpose gate on the final segments
(`docs/SPEC_EARNED_SELECTION.md:247-253`); it does not compare final adjacent
series instances. Thus pristine L1 and L2 can both be certified while the
emitted series repeats/down-levels under a cap, or two transformed sessions both
pass purpose bands while final TSS is flat or decreasing.

**Why it blocks.** The rationale for archetype-wide failure is series safety,
but the certified relation is discarded by the very post-render scaling r2 is
designed to account for. Q3 is true of source designs and potentially false of
the sealed plan.

**Minimal textual fix.** Either narrow Q3 explicitly to native library design
and stop using emitted-series progression as its justification, or add a
post-transformation plan-level series gate over final sealed sessions keyed by
stable series identity, with cap/plateau semantics and review behavior.

### R2-04. The origin union has a catch-all, not exhaustive production contracts

**Claim.** Every cycling workout belongs to exactly one enumerated origin, with
fixtures per branch (`docs/SPEC_EARNED_SELECTION.md:306-319`).

**Evidence.** Besides the named Nate, simple Endurance, B-race/travel,
assessment, and generic legacy entries, production emits:

- a bespoke one-second 30% Rest ZWO (`athletes/scripts/
  generate_athlete_package.py:2448-2484`);
- progressive interval and progressive endurance generators, plus the standard
  `create_workout_blocks` path (`:2792-2855`);
- legacy Nate renders whose `_record_tp_session` call carries no selected
  archetype identity (`:2717-2787`); and
- Phase 3 `athlete_fixed` cycling sessions with no segments/archetype
  (`build/trustworthy-phase3:athletes/scripts/canonical_training_model.py:
  333-351`).

The table's “legacy overlay path” does not give these branches a purpose or
gate contract; “anything else” merely turns them into non-waivable unknowns.
E3 requires passing manifest rows but does not require a reachability sweep
showing zero known production path can emit `WORKOUT_ORIGIN_UNKNOWN`
(`docs/SPEC_EARNED_SELECTION.md:501-504`).

**Why it blocks.** Mode B can be enabled with known paid-order paths guaranteed
to become non-waivable blockers. That is fail-closed in the narrow sense but an
order-killer, not an implementable exhaustive union.

**Minimal textual fix.** Inventory every reachable renderer/overlay/fixed
session as a stable origin discriminant with its contract. Add a production
reachability sweep (not one synthetic catch-all fixture) and make zero reachable
unknown origins an E3 entry criterion.

### R2-05. The closed non-waivable policy is only partly extended

**Claim.** Integrity codes join the fulfilment policy's closed non-waivable set
and approval-negative tests cover them (`docs/SPEC_EARNED_SELECTION.md:289-304`).

**Evidence.** Phase 3 owns an exact `NON_WAIVABLE_RULES` set and a matching
remediation map (`build/trustworthy-phase3:webhook/fulfillment_state.py:47-71`).
r2 names three new codes, but then says “plus manifest-pin failures” without
naming their stable IDs or remediations. The depended-on fulfilment spec still
enumerates its closed set without these extensions
(`docs/SPEC_TRUSTWORTHY_FULFILMENT.md:207-224`).

**Why it blocks.** A pin-missing, pin-digest-mismatch, or snapshot-unavailable
case can default to waivable, collide with `SEAL_MISMATCH`, or be implemented as
different codes. Negative approval tests cannot cover unnamed codes.

**Minimal textual fix.** Enumerate every pin/snapshot failure code, exact
waivability and remediation, amend the closed policy normatively, and require
set-equality between the spec registry, `NON_WAIVABLE_RULES`, the remediation
map, and the negative-test parameter set.

### R2-06. `quality_finding/v1` does not fit the actual state/catalog/snapshot rail

**Claim.** §4.8 specifies the new type end to end, requires no acknowledgment,
and archives it in the approval snapshot
(`docs/SPEC_EARNED_SELECTION.md:342-360`).

**Evidence.** Phase 3 has four allowed types
(`build/trustworthy-phase3:webhook/fulfillment_state.py:37-44`). More
importantly, `review_items` is not appendable authority: it is deterministically
rebuilt from `blocking_issues`, two confirmation lists, derived values, and
release facts (`:344-408`), and state validation rejects any other catalog
(`:519-530`). Approval requires a snapshot entry for every catalog item; only
the four known types have disposition rules (`:411-458`). r2 defines fields of
an individual finding but no state-owned `quality_findings` collection,
validator, namespaced merge/write operation, regeneration semantics, automatic
snapshot disposition, or state/catalog/snapshot version bumps. “After blockers
and confirmations” also leaves its rank relative to verified facts ambiguous.

**Why it blocks.** A literal implementation either loses findings when the
catalog refreshes, fails state validation, or silently invents acknowledgment
semantics. Catalog-digest binding alone does not solve the source-of-truth and
approval issues.

**Minimal textual fix.** Specify the authoritative state field and validator,
revision-aware merge API, exact rank, snapshot disposition (for example
`observed`, generated server-side), and required `SCHEMA_VERSION`,
`REVIEW_CATALOG_VERSION`, and `APPROVAL_SNAPSHOT_VERSION` migrations. Add
round-trip/regeneration/catalog-digest/approval tests.

### R2-07. The new seal input is still not an exact schema

**Claim.** A per-revision manifest snapshot is added to a bumped seal schema in
both constructors, with backward verification (`docs/SPEC_EARNED_SELECTION.md:
421-435`).

**Evidence.** The apply constructor currently hashes exactly
`canonical_model`, `review_items`, `guide_sources`, and `operation_payloads`
(`build/trustworthy-phase3:athletes/scripts/apply_contract.py:693-708`). Release
finalization independently reconstructs the same exact object
(`build/trustworthy-phase3:webhook/fulfillment_state.py:802-829`) and accepts
only named seal-version constants during verification (`:917-924`). r2 does not
state:

- the snapshot's revision-local path and schema/version;
- whether the digest is SHA-256 of canonical JSON payload, pretty-printed file
  bytes, or another envelope;
- the exact new key/value in `model_seal_sources`;
- the new seal-version string and reader compatibility rule; or
- whether the manifest payload, its digest, or both enter canonical sources.

JSON key sorting makes prose “ordering” irrelevant, but exact membership and
canonicalization are mandatory.

**Why it blocks.** The two constructors and future verifiers can make different
reasonable choices and produce different seals. Backward verification cannot
be implemented against an unnamed version.

**Minimal textual fix.** Give the snapshot an exact pathname and JSON schema,
define one canonical digest expression, publish the complete new
`model_seal_sources/v2` object and version string, and list every verifier that
must dispatch v1 versus v2.

### R2-08. `workout_quality_report.json` has no stable row key or complete registry contract

**Claim.** The report is schema-owned and keyed by canonical session ID; two
aggregate derived entries project to review (`docs/SPEC_EARNED_SELECTION.md:
386-402`).

**Evidence.** Phase 3 canonical sessions contain week, phase, date,
`daily_ordinal`, title, and projection metadata, but no session `id`
(`build/trustworthy-phase3:athletes/scripts/canonical_training_model.py:
500-533`). The report schema/version and collision behavior are not defined.
The proposed `QUALITY_GATE_SUMMARY` and `QUALITY_MANIFEST_PIN` give only IDs and
classes. Real registry entries require field, class, basis, inputs, sensitivity,
timestamp and revision, and artifact coverage is exact/closed
(`build/trustworthy-phase3:athletes/scripts/derived_registry.py:361-415,
431-475`).

**Why it blocks.** Regeneration, same-day double sessions, title changes, and
overlays can re-key or collide. Implementers must invent the artifact schema and
the exact derived provenance that Phase 3 is designed to reject when missing.

**Minimal textual fix.** First define an immutable canonical session ID and its
generation grammar. Then publish `workout_quality_report/v1`'s closed output
schema and both complete derived-entry records (field paths, basis, inputs,
sensitivity, materialization time, revision), including artifact-coverage and
collision fixtures.

### R2-09. The “normative registry” and execution matrix still defer normative decisions

**Claim.** §4.5 resolves the conflicting reference rubrics with one registry
and exact execution matrix (`docs/SPEC_EARNED_SELECTION.md:255-287`).

**Evidence.** The text directs implementation to decide whether R26 is adopted
or rejected, whether R18/R22 are implemented or deferred, how R03's undefined
range closes, and how severities reconcile (`:262-268`). It then lists desired
matrix columns without supplying a single per-rule row (`:275-283`). Current
production still has 11 entries, including unconditional R08/R11 passes and a
different dynamic R03 range (`athletes/scripts/block_compliance.py:156-199,
272-281,376-403`). The contradictory upstream facts reverified in R1 remain at
`docs/reviews/SPEC_EARNED_SELECTION_CODEX_R1.md:351-425`.

**Why it blocks.** Rule inclusion, severity, applicability, and unavailable
behavior control release and waiver semantics. Requiring the implementer to
write the normative rubric during implementation is the same unresolved choice
under a new filename.

**Minimal textual fix.** Check in or append the complete initial registry and
execution matrix as a reviewed normative attachment before implementation:
every ID, settled severity/status, algorithm, exact sealed input, stage,
NA/unavailable behavior, output code, and ordering relative to catalog refresh,
contract build, and seal finalization.

### R2-10. Q4 still permits silent POLARIZED fallbacks at two production boundaries

**Claim.** Config is authoritative and invalid/unavailable methodology state
fails closed (`docs/SPEC_EARNED_SELECTION.md:134-136,321-340`).

**Evidence.** r2 explicitly deletes only `select_methodology.py`'s inline
fallback. The package currently maps an unknown customer methodology to
POLARIZED (`athletes/scripts/generate_athlete_package.py:592-593`), and Nate maps
an unknown render style to POLARIZED (`athletes/scripts/
nate_workout_generator.py:728-735`). The proposed static consistency test for
referenced IDs does not exercise malformed runtime artifact values.

**Why it blocks.** A corrupt or new methodology ID can still silently select and
render the wrong workouts while Q4 reports one source of truth and Q0 goldens
remain green for known profiles.

**Minimal textual fix.** Require both mapping boundaries to reject unknown IDs,
with negative fixtures for bad `methodology.yaml`, unknown render style, missing
mapping, and invalid config. Route the resulting generation failure through the
existing loud-to-coach order failure path.

### R2-11. The ID-keyed migration is not defined well enough to prove E1 byte identity or safe retirement

**Claim.** Stable ID-keyed ordering plus goldens preserves selection before any
retirement and prevents later reshuffles (`docs/SPEC_EARNED_SELECTION.md:
437-449,488-500`).

**Evidence.** Current selection is `index % len(category_list)`
(`athletes/scripts/nate_workout_generator.py:530-542,791-798`), and callers add
methodology and block/usage offsets (`athletes/scripts/
generate_athlete_package.py:2199-2212`; `athletes/scripts/workout_mapper.py:
217-234`). r2 does not define ID assignment for the existing name-keyed public
catalog, the stable ordering function, whether tombstones retain slots, what an
unreplaced retired slot returns, or how replacements affect series identity.
“Same profile” selection goldens and a finite golden-order set
(`docs/SPEC_EARNED_SELECTION.md:331-332,469-481`) do not prove equivalence for
all methodology × discipline × workout type × offset × level combinations.

**Why it blocks.** E1 can change workout names/descriptions/bytes outside the
fixture fleet, and retirement can still shift modulo selection or strand an
index. That violates both Q0 and the public archetype-identity contract.

**Minimal textual fix.** Publish the one-time name/category→ID map, an explicit
ordered-slot/tombstone/replacement algorithm, and an exhaustive equivalence test
over every reachable selection tuple and several counter cycles. Define the
behavior of an unreplaced retired slot without reindexing.

### R2-12. Missing HR anchors have contradictory gate behavior

**Claim.** Non-power content uses Phase 3 normalization; missing HR anchors mean
the workout “is not dose-gated,” with the absence already visible
(`docs/SPEC_EARNED_SELECTION.md:362-384`).

**Evidence.** Phase 3's table reference is correct
(`build/trustworthy-phase3:athletes/scripts/canonical_training_model.py:
119-147`). But requested HR without LTHR/HRmax becomes control basis
`rpe_pending_lthr` (`:43-65`), and the canonical target becomes `rpe`
(`:164-194`). r2's preceding rule says RPE content receives duration and
TSS-equivalent sanity gates (`docs/SPEC_EARNED_SELECTION.md:369-375`), then says
the missing-anchor workout is not dose-gated (`:376-378`).

**Why it blocks.** The same canonical RPE session can be gated or exempted based
on an implementer's reading of its requested metric, producing different
manifest/finding outcomes.

**Minimal textual fix.** State explicitly whether `rpe_pending_lthr` is gated as
the canonical RPE prescription or is NOT_AVAILABLE/NOT_APPLICABLE, and define
the resulting verdict/review item. Add the missing-HR-anchor case to the named
fixtures.

### R2-13. The estate counts are right, but “master instances inherit library validation” is not honest

**Claim.** The 14,840 master-plan ZWOs inherit validation from the 524 curated
library designs (`docs/SPEC_EARNED_SELECTION.md:38-53`).

**Evidence.** Filesystem recounts produced exactly 524
`workout-library/**/*.zwo` and 14,840 `master_plans/**/*.zwo`. However, none of
the 14,840 files is byte-identical to a library file, and only 7,656 (51.59%)
has an exactly matching normalized `<workout>` body; 7,184 do not. The sibling
physiology tool scores generated-plan workouts independently and returns flags
(`/Users/mattirowe/Documents/GravelGod/gravel-god-training-plans/tools/
validate_physiology.py:33-62`); it is not evidence that all stored instances
inherit a passing verdict. The scorer itself says it scores the same rendered
segments (`.../engine/physiology.py:3-14,99-127`).

**Why it blocks.** The owner directive requires the full estate to be stated
honestly. Dose-affecting rendered variants cannot inherit a design verdict by
assertion—the exact post-render problem §4.4 correctly identifies inside this
pipeline.

**Minimal textual fix.** Keep the verified counts, but change the validation
cell to: curated library has a physiology scorer/audit tool; master instances
have separate QC tooling and cannot be assumed to inherit dose validation when
their executable bodies differ. Do not claim complete validation without a
stored full-estate run and dispositions.

### R2-14. Q0's byte-identity acceptance omits actual athlete-facing surfaces

**Claim.** Athlete-facing artifacts are byte-unchanged and the acceptance test
covers ZWOs, guide, and athlete-visible preview payloads
(`docs/SPEC_EARNED_SELECTION.md:23-36,469-478`).

**Evidence.** On the Phase 3 target, the actual customer deliverable list also
contains guide PDF, dashboard, `plan_preview.html`, and `fueling.yaml`, and the
customer ZIP includes those plus workouts
(`build/trustworthy-phase3:webhook/app.py:1794-1809,2095-2104`). TrainingPeaks
athlete-visible payloads include workout title/description/TSS/structure and a
calendar note for every session
(`build/trustworthy-phase3:athletes/scripts/apply_contract.py:263-302`). The
fulfilment contract also defines the athlete-addressed Gmail draft with guide
attachment (`docs/SPEC_TRUSTWORTHY_FULFILMENT.md:908-938`), and production has
customer day-1/3/7 follow-up copy (`webhook/email_templates.py:37-105`). None is
in the Q0 byte comparison. “Guide” does not specify HTML and PDF, and “preview
payloads” does not assert the emitted HTML or ZIP bytes.

**Why it blocks.** Provenance/model/ID changes can leave ZWOs green while
changing TP notes, apply payloads, ZIP/PDF/dashboard/preview, or athlete email.
The binding owner directive is therefore not testable as stated.

**Minimal textual fix.** Define a closed athlete-surface inventory and compare
every byte-bearing projection before/after E1: all customer deliverables and ZIP
entries, ZWOs, TP workout/calendar-note/attachment payloads, Endure payload when
enabled, published guide components, Gmail draft MIME/body/attachments, and
fixed follow-up templates. Use a fixed clock and deterministic PDF/ZIP/MIME; if
any surface cannot be byte-deterministic, resolve that conflict with the owner
directive rather than silently weakening the test.

## Non-blocking findings

1. **The headline estate counts are verified.** Runtime registry validation
   returned 100 archetypes, 24 categories, and 600 levels. Filesystem recounts
   returned 524 curated-library ZWOs and 14,840 master-plan ZWOs. The canonical
   Endure validator exists at
   `/Users/mattirowe/Documents/GravelGod/endurelabs/scripts/
   validate-stock-workouts.ts`. The validation-inheritance wording is blocker
   R2-13; the scale itself is correct.
2. **The §0.3 file:line claims are materially accurate.** The imported check is
   endpoint-only, the advanced checks cover 16 archetypes, the cited three
   named designs have adjacent monotonic tests, registry validation checks six
   levels, R08/R11 are no-ops, and the distribution validator is filename-based
   with advisory deviations plus catastrophic shape failures. Minor wording:
   the advanced tests compare L1 with L6 rather than every adjacent level.
3. **The Phase 3 normalization-table correction is verified.** RPE, %LTHR, and
   %HRmax use distinct piecewise mappings at
   `build/trustworthy-phase3:athletes/scripts/canonical_training_model.py:
   119-147`; r2 no longer claims RPE/10.
4. **The two-part §4.4 gate handles both verdict directions.** Manifest PASS +
   final FAIL produces `WORKOUT_DOSE_MISMATCH`; final PASS + manifest FAIL
   retains `LIBRARY_UNCERTIFIED`. Because both are independently required and
   declared non-waivable, neither direction can authorize release. The stable
   identity and policy-integration defects are separate blockers.
5. **The E3 all-selectable-row criterion is conceptually correct.** It fixes
   r1's “critical subset” contradiction. It becomes achievable only after the
   calibration, origin-reachability, and stable retirement contracts above are
   made executable; no evidence currently demonstrates the 600-row entry bar.
6. **The in-flight manifest policy is coherent.** A sealed revision is
   grandfathered, while regeneration uses the current manifest
   (`docs/SPEC_EARNED_SELECTION.md:450-455`). This aligns with fulfilment's
   revision/re-review model and avoids retroactively invalidating approval.
7. **Q0's “no justification copy” rule is clear.** The defect is coverage, not
   intent. §4.8 correctly gives quality findings no email projection and §4.10
   keeps the detailed report coach/internal.

## What I verified and how

- Read the complete r2 spec, the complete R1 review, `CLAUDE.md`, and the three
  task-relevant handover skills before inspecting implementation.
- Reviewed this worktree at `8c0046d` and Phase 3 at
  `build/trustworthy-phase3` commit `d291eb4` with `git show`, including
  `canonical_training_model.py`, `zwo_parser.py`, `plan_ir.py`,
  `derived_registry.py`, `apply_contract.py`, `fulfillment_state.py`, and the
  webhook artifact paths.
- Re-traced production selection/rendering through `series_tracker.py`,
  `workout_mapper.py`, `nate_workout_generator.py`, and
  `generate_athlete_package.py`, including post-render scaling, bespoke race/
  travel/rest paths, legacy generators, and TP session recording.
- Executed the production registry validator: 100 archetypes, 24 categories,
  600 rows, all registry checks passing.
- Rendered all 600 registry rows read-only and classified FreeRide presence: 17
  rows across three archetypes; six Rest Day rows have no prescribed-power
  segment after FreeRide exclusion.
- Recounted sibling estates with filesystem reads: 524 curated-library ZWOs and
  14,840 master-plan ZWOs. Compared full-file and normalized workout-body hashes
  to test the claimed validation inheritance.
- Re-read the experimental `score_library.py` and scorecard from the main
  checkout at `95d238a` (234 rows, 155 PASS / 79 FAIL) without modifying them.
- Reverified sibling physiology/scoring code at `gravel-god-training-plans`
  `50af6e15`, compliance references at `gravel-god-training-engine` `22a8b41`,
  and the Endure validator at `endurelabs` `a2ebe1e7f`.
- Used only source inspection and read-only probes. I did not run a paid order,
  mutate external services, or use customer data.

## What I could not verify

1. No r2 implementation, 600-row production certification manifest,
   `quality_gates.yaml`, signed disposition log, rule registry, execution
   matrix, quality report, or Mode A replay output exists, so their runtime
   correctness and throughput cannot be tested.
2. I could not verify scientific validity of the proposed bands or Q3 epsilons
   from repository evidence. This review verifies specification authority and
   determinism, not external exercise-physiology truth.
3. I could not verify that all 14,840 sibling master instances have passed an
   independent current physiology run; no complete stored verdict set was cited.
4. I did not test a real TrainingPeaks/Endure apply, Gmail draft/send, or live
   in-flight order. The surface and payload conclusions come from the sealed
   Phase 3 constructors and contracts.
5. I could not prove the E3 entry bar achievable because r2 has no calibrated
   production baseline and no stable-ID retirement implementation.

The spec should not enter implementation until the 14 items above are resolved
in normative text or reviewed versioned attachments. In particular, do not let
future implementation notes become the place where release policy is invented.

**VERDICT: NO-GO — 14 blockers.**
