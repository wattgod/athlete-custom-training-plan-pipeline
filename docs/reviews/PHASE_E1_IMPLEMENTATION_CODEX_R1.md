# Phase E1 implementation adversarial review — Codex R1

Date: 2026-08-13

Reviewed branch: `build/earned-selection-e1`

Reviewed range: `19a7b4c..aa24e67`, plus the current Appendix 4/selection state at the merge base

Binding contract: `docs/SPEC_EARNED_SELECTION.md` §7.2 E1 and `docs/reviews/SPEC_EARNED_SELECTION_CODEX_R6.md`

## Verdict

**NO-GO — 6 blockers.**

The implementation establishes useful Mode-A registries, scoring, report, state-v3,
quality-finding, and v2-seal components, and the ordinary test suite is green. It does
not, however, implement the binding §4.5 authority/order graph, does not make the
frozen A3.0 projection the fulfillment-blocker authority, does not establish the
revision-local manifest pin before D1, and does not supply the contractually required
selection-byte or Q0 surface proofs. Two Appendix 3 post-guide evaluators also do not
implement their specified algorithms. Those are release-contract failures rather than
optional hardening.

## Numbered blockers

### 1. The §4.5 D1/D2 authority and stage order is not implemented

**Claim.** The implementation notes claim that the pre-D1 order, D2 binding, complete
pre/post-guide evaluation, and single report merge/catalog refresh are fixed
(`docs/reviews/PHASE_E1_IMPLEMENTATION_NOTES.md:27`).

**Evidence.** The contract requires: freeze the complete candidate; run dose/final-series
and all `PRE_GUIDE` rules on that frozen candidate; finalize the canonical model from
the candidate; generate one guide; run only the two `POST_GUIDE` rules and existing
post-render validators; then create one merged report and perform one state merge and
one catalog refresh (`docs/SPEC_EARNED_SELECTION.md:485-513`). The implementation instead:

- finalizes the canonical model before it constructs or freezes the candidate
  (`athletes/scripts/generate_athlete_package.py:3320-3339`);
- constructs the candidate from that already-finalized canonical model
  (`athletes/scripts/generate_athlete_package.py:3333-3337`);
- runs all 26 rules together only after the guide exists
  (`athletes/scripts/generate_athlete_package.py:3355-3363`,
  `athletes/scripts/workout_quality_report.py:146-159`);
- writes the quality report before the existing PlanIR/package post-render validation,
  which runs later and cannot be merged into that report
  (`athletes/scripts/generate_athlete_package.py:3360-3363,3542-3572`); and
- refreshes the review catalog once inside `write_generation`, again inside
  `merge_quality_findings_v1`, and potentially again for package-consistency blockers
  (`webhook/fulfillment_state.py:865`, `webhook/fulfillment_state.py:969`,
  `webhook/fulfillment_state.py:1016`).

The guide does have one production invocation (`athletes/scripts/generate_athlete_package.py:3355`),
but that does not cure the reversed authority graph or missing staged report merge.
The current tests assert end-state identity, not the required call/stage order.

**Why this blocks E1.** D1 is supposed to be the immutable content authority read by
every validator and projected into the canonical model. Here the candidate is derived
from an earlier authority, pre-guide rules are not run at the mandated stage, and the
report cannot contain the required post-render results. This defeats the audit trail
the phase exists to establish.

**Minimal fix.** Build and freeze the complete candidate first; run the explicitly
staged pre-guide evaluations against it; project the canonical model/PlanIR from it;
build the guide once; run R07/R25 and post-render validators; then atomically emit one
merged report and update state/catalog once. Add an order-spy fixture covering every
§7.1 item 13 boundary.

### 2. Fulfillment blockers do not come through the frozen A3.0 report rail

**Claim.** The notes state that the only approval blockers are the nine pre-existing
rules evaluated through A3.0-equivalent verdicts, and that fulfillment merges those
rubric blockers (`docs/reviews/PHASE_E1_IMPLEMENTATION_NOTES.md:9-14,24,31`).

**Evidence.** A live `block_compliance.validate_plan` call evaluates the mutable
block-builder plan before D1 and immediately converts failures to fulfillment issues
with source `block_compliance` (`athletes/scripts/generate_athlete_package.py:847-901`).
The report separately and correctly creates `quality_blockers` from frozen-projection
A3.0 rows (`athletes/scripts/workout_quality_report.py:153-159`), and the pipeline
receives that value (`athletes/scripts/generate_athlete_package.py:3360-3362`), but
never uses it. `write_generation` receives only
`generate_zwo_files.last_fulfillment_issues` (`athletes/scripts/generate_athlete_package.py:3527-3533`).

The differential tests prove equivalence for a generated corpus, but they do not make
the report result authoritative. The athlete-m test compares state blockers with its
old expected fixture and merely checks that any report-routed rows are pre-existing
(`athletes/scripts/test_athlete_m_phase1.py:120-122,152-158`); it does not assert exact
report-routed-blocker/state-blocker equality.

**Why this blocks E1.** §7.2 says that the nine pre-existing rules remain blockers
*through their A3.0 production-equivalent verdict functions*. §4.2 further requires
each evaluator to read the frozen projection. A separate pre-D1 live-plan rail can
diverge from D1, while the contractually authoritative result is dead data.

**Minimal fix.** Use only the report's A3.0-routed rows as the generated compliance
blockers after D1. Retain live evaluation only as an asserted parity check if useful.
Add a failing fixture that asserts exact blocker ID, source, result, and subject parity
between report and fulfillment state for all nine rules.

### 3. The revision-local manifest pin is neither established before D1 nor validated fail-closed

**Claim.** The notes claim a revision snapshot/pin before D1 and seal-v2 coverage
(`docs/reviews/PHASE_E1_IMPLEMENTATION_NOTES.md:23,25,27`).

**Evidence.** `snapshot_manifest` writes to the mutable athlete work directory
(`athletes/scripts/final_plan_candidate.py:72-94`), while the required path is the
revision directory outside `artifacts` before candidate freeze
(`docs/SPEC_EARNED_SELECTION.md:884-905`). The actual revision directory is not created
until persistence, and the snapshot is copied there only then
(`webhook/app.py:2167-2185`), after candidate/report/state/apply-contract construction.

There is a correct-looking `validate_manifest_pin` helper
(`athletes/scripts/earned_selection.py:299-308`), but it has no caller. A supplied
manifest and pin are accepted by `build_candidate` without comparing them
(`athletes/scripts/final_plan_candidate.py:268-282`), and candidate validation checks
only root keys, mode/vector, ordering, and uniqueness
(`athletes/scripts/final_plan_candidate.py:520-535`). R21 validates origin tuples and
source-digest syntax but never the candidate pin
(`athletes/scripts/earned_selection_rules.py:371-398`), despite R21's exact input and
algorithm requiring it (`docs/SPEC_EARNED_SELECTION.md:1920`).

The two seal constructors do use the same fifth-key formula when a v2 contract exists
(`athletes/scripts/apply_contract.py:708-732`, `webhook/fulfillment_state.py:1044-1085`),
and the synthetic equality test passes
(`webhook/tests/test_earned_selection_state.py:117-149`). But `build_contract` silently
emits legacy v1 whenever the snapshot digest is absent
(`athletes/scripts/apply_contract.py:775-793`), and the release reconstructor hashes
whatever later snapshot is present without comparing it to D1's pin. The required
missing-pin and mismatched-pin negatives are absent; the test only covers a missing v2
snapshot and unknown contract version.

**Why this blocks E1.** A mutable or substituted certification manifest can be frozen
into D1 and later sealed under a different digest without the specified
`MANIFEST_PIN_*` failure. New E1 generations can also downgrade to seal v1 rather than
fail closed.

**Minimal fix.** Create the exact revision directory/snapshot before D1, canonicalize
and validate the snapshot and full ordered pin, require it in candidate/R21/report and
v2 contract construction, and compare that same pin during seal reconstruction. Keep
v1 only behind an explicit legacy-reader path. Add stale-global, missing snapshot,
missing pin, mismatch, and unknown-version integration tests through both constructors.

### 4. Appendix 7/8 enforcement and Appendix 3 execution are not contract-complete

**Claim.** The notes claim closed candidate/provenance coverage and complete Appendix 3
execution (`docs/reviews/PHASE_E1_IMPLEMENTATION_NOTES.md:21,24,29`).

**Evidence.** `validate_candidate` does not validate the nested closed Appendix 7
schema: beyond root equality it checks only mode/version and session identity/order
(`athletes/scripts/final_plan_candidate.py:520-535`). It does not validate nested
week/session/segment/provenance fields, the manifest pin, exact producer tuples, or
source digests. The candidate's `guide_inputs` also lists six athlete files plus staged
JSON (`athletes/scripts/final_plan_candidate.py:472-483`), while the guide independently
calls `chain_blocks` (`athletes/scripts/training_guide_builder.py:4043-4060`), which
consumes repo configuration not represented in the D1 guide-input inventory.

Two concrete target-rule implementations differ from the binding Appendix 3 matrix:

- R07 searches the whole normalized guide for one week-type phrase and cannot prove
  exactly one Monday note or bind the registered note type for each paid week
  (`athletes/scripts/earned_selection_rules.py:192-203` versus
  `docs/SPEC_EARNED_SELECTION.md:1906`).
- R25 passes if either readiness marker appears anywhere once in the whole guide; it
  does not apply the closed marker test to each paid week's Monday note
  (`athletes/scripts/earned_selection_rules.py:424-431` versus
  `docs/SPEC_EARNED_SELECTION.md:1924`).

Report validation checks aggregate count equations, not exact applicable gate-ID
coverage per session (`athletes/scripts/workout_quality_report.py:240-274`). The four
dedicated files contain no one-fixture-per-origin/all-four-W00 reachability suite, no
complete nested candidate-schema fixture, and no R07/R25 present/absent/per-week
goldens; their test inventory is visible at
`athletes/scripts/test_earned_selection.py:51-275`,
`athletes/scripts/test_earned_selection_rules.py:49-95`, and
`webhook/tests/test_earned_selection_state.py:61-152`.

**Why this blocks E1.** §7.2 requires the Appendix 5–8 schema/producer rail and Appendix
3, not merely documents with those version labels. Invalid candidate/provenance data can
pass the validator, and real R07/R25 failures can be reported as PASS, so the claimed
complete audit result is false even though those results are non-blocking in E1.

**Minimal fix.** Enforce the full closed Appendix 7 schema and Appendix 8 tuple/digest
contracts, content-address every repo input actually read by D2, implement R07/R25 per
paid week/note, validate exact applicable gate sets, and add the §7.1 origin/W00,
candidate, unavailable, and rule fixtures.

### 5. Selection migration lacks the mandated exhaustive rendered-ZWO-byte proof

**Claim.** The notes call the migration exhaustive and byte-equivalent
(`docs/reviews/PHASE_E1_IMPLEMENTATION_NOTES.md:20`).

**Evidence.** The first migration test iterates every category slot, one wrap, and
levels 1–6, but compares only the selected dictionaries and the block-list result of
`generate_blocks_from_archetype` (`athletes/scripts/test_earned_selection.py:152-165`).
The second is explicitly a factorized test. It iterates mapper names, three disciplines,
four render values, and offsets, but compares selected **names only**, omits
methodology IDs and phases from the enumeration, and does not render complete ZWO bytes
(`athletes/scripts/test_earned_selection.py:168-218`).

The binding corpus is every reachable
`(methodology_id, render_style, discipline, phase, workout_type, base_variation,
variation_offset, level)` tuple, including methodology/block/usage offsets and
`0..N`, with pre/post selected category/name and final rendered ZWO bytes compared
(`docs/SPEC_EARNED_SELECTION.md:875-882`).

**Why this blocks E1.** The current factorization may be useful evidence, but it is not
the explicitly required migration proof. Branches outside the helper-level comparison
can change filenames or serialized bytes while both current tests remain green.

**Minimal fix.** Commit a deterministic exhaustive tuple generator with a pinned case
count. Invoke the actual pre-migration and ID-resolved render paths and compare category,
name, filename, and complete ZWO bytes for every tuple, including the wrap boundary.

### 6. Q0 is asserted, not proven, for the closed athlete-surface inventory

**Claim.** The notes declare Q0 fixed using helper comparisons, an athlete-m replay,
existing regressions, and the full suite
(`docs/reviews/PHASE_E1_IMPLEMENTATION_NOTES.md:30`).

**Evidence.** §6 requires deterministic pre-E1 versus E1 byte comparisons for all ZWO
names/bytes; guide HTML/PDF; dashboard, preview, and fueling; every customer-bundle
member and ZIP byte; every field/byte and disposition of all seven TrainingPeaks kinds;
Endure payload; athlete Gmail RFC 5322/MIME bytes; day-1/3/7 followups; and published
guide bytes (`docs/SPEC_EARNED_SELECTION.md:962-1023`).

No such before/after surface harness exists in the four dedicated files. The only Q0
TP assertion is set equality for the seven kind names
(`webhook/tests/test_earned_selection_state.py:152-159`). Athlete-m generates only the
new pipeline, checks selected semantics/internal relationships, and never compares a
Phase-3 baseline for ZIP, MIME, email, Endure, publishing, PDF, or complete apply
payload bytes (`athletes/scripts/test_athlete_m_phase1.py:34-267`). The selection helper
tests cited by the notes are not surface comparisons (blocker 5).

Static inspection found no direct `quality_findings`, rubric, manifest-pin, or gate
copy passed into the production guide builder, ZWO renderer, email templates, or
apply-payload construction. That is useful leak evidence but cannot prove byte equality
after the W00/fueling/guide-order changes. The existing chaos renderer really does use
process-randomized `hash()` (`athletes/scripts/nate_workout_generator.py:2250-2259`);
pinning `PYTHONHASHSEED=0` makes a fixed test run possible, but there is still no
before/after Q0 run.

**Why this blocks E1.** “No content changes,” zero new athlete-facing justification
copy, and Q0 on every surface are explicit E1 MUSTs. The green full suite and a single
post-change replay are not substitutes for the closed pre/post byte inventory.

**Minimal fix.** Add the §6 deterministic baseline/current harness, with exact
seven-kind field/byte comparators and fixed PDF/ZIP/MIME inputs, then run it for every
golden order. Keep the hash seed pinned for E1 or obtain the owner-signed narrow
exception described in §6; do not convert other surfaces to semantic-only checks.

## §7.2 E1 MUST inventory

| # | E1 MUST | Enforcing code and test/evidence | Result |
|---:|---|---|---|
| 1 | Commit Appendix 4 exactly as `archetype_ids.json` | Byte comparison against the spec fence was exact (13,139 bytes); `archetype_identity.validate_live_registry` rejects category/name/order drift, and `athletes/scripts/test_earned_selection.py:152-165` exercises slots/wrap/levels. The live registry command reports 100 archetypes, 24 categories, 600 variations. | **Verified** |
| 2 | Migrate selection with exhaustive byte equivalence | Helper-level slot/block and factorized name tests at `athletes/scripts/test_earned_selection.py:152-218`. | **Blocked by 5** |
| 3 | Add Appendix 5 purpose registry | `athletes/config/purpose_registry.yaml`, manifest materialization, and deterministic 600-row regeneration test at `athletes/scripts/test_earned_selection.py:131-149`. | **Verified for E1 manifest use** |
| 4 | Add Appendix 6 gate registry and pure scorer | `athletes/config/quality_gates.yaml`; pure evaluation in `athletes/scripts/earned_selection.py:235-292`; trace/dose/W′bal goldens at `athletes/scripts/test_earned_selection.py:51-127`. | **Verified** |
| 5 | Add Appendix 7 complete FinalPlanCandidate schema/derivation | Builder exists, but the closed nested schema, manifest pin, guide-input closure, and derivation/reachability fixtures are not enforced. | **Blocked by 1, 3, 4** |
| 6 | Add Appendix 8 producer registry and producer-only origins | Registry/provenance projection exists, but the closed tuple/pin validation and required origin/W00 reachability fixtures do not. | **Blocked by 3, 4** |
| 7 | Produce complete hypothesis results | Stored manifest has 600 rows, 1,800 gate records, all six gate IDs, no empty rows, and all effective `NOT_ENFORCED`; deterministic regeneration is tested at `athletes/scripts/test_earned_selection.py:131-149`. Final-instance coverage is checked on athlete-m at `athletes/scripts/test_athlete_m_phase1.py:143-151`. Exact per-session applicable-ID validation remains incomplete. | **Partial; blocked by 4** |
| 8 | Produce certification manifest and merged report | Both artifacts are emitted and report identity/count equations are checked at `athletes/scripts/workout_quality_report.py:226-277`; the report is built at the wrong stage and omits later post-render results. | **Blocked by 1** |
| 9 | Execute Appendix 3 completely | All 26 registry IDs appear and the nine A3.0 differential corpus tests pass; R07/R25 and required edge/reachability coverage are incomplete. | **Blocked by 4** |
| 10 | State/catalog/snapshot v3 | `webhook/fulfillment_state.py` uses state schema 3, quality-findings v1, review catalog v2, and approval snapshot v3; replacement/regeneration/coach-disposition tests pass at `webhook/tests/test_earned_selection_state.py:61-115`. | **Verified as data structures; merge ordering blocked by 1** |
| 11 | Seal v2 with dual-constructor equality and v1 backward verification | v2 fifth-key formulas match and synthetic v2/v1 equality passes at `webhook/tests/test_earned_selection_state.py:117-149`; new-generation fail-closed pin/path behavior is absent. | **Blocked by 3** |
| 12 | Every applicable purpose/gate result observed, none missing, all effective `NOT_ENFORCED` | Stored-manifest counts above and athlete-m assertions at `athletes/scripts/test_athlete_m_phase1.py:147-151`; total/exclusive purpose selection is enforced at `athletes/scripts/earned_selection.py:246-271`. Exact final applicable-ID set validation is absent. | **Partial; blocked by 4** |
| 13 | Only nine pre-existing rules are blockers through A3.0-equivalent verdicts | Report routing is restricted at `athletes/scripts/earned_selection_rules.py:462-483`, and A3.0 parity tests pass, but state is populated from the separate live validator. | **Blocked by 2** |
| 14 | Every new/E3 result is a quality finding | Non-routed FAIL/WARNING/UNAVAILABLE rows receive `QUALITY_Rxx` findings at `athletes/scripts/earned_selection_rules.py:469-483`; closed replacement/observation behavior is tested at `webhook/tests/test_earned_selection_state.py:61-115`. | **Verified for emitted report rows; row correctness blocked by 4** |
| 15 | Persist W00 and align fueling before D1 | W00 insertion and `align_fueling_to_plan` occur before candidate freeze at `athletes/scripts/generate_athlete_package.py:3302-3339`; athlete-m checks final fueling labels at `athletes/scripts/test_athlete_m_phase1.py:123-129`. | **Verified order locally; byte neutrality blocked by 6** |
| 16 | Snapshot/pin before D1 at the revision-local path | Athlete-local snapshot is before D1, but the required revision-local snapshot is copied after generation/persistence. | **Blocked by 3** |
| 17 | Exactly one guide build | One production call at `athletes/scripts/generate_athlete_package.py:3355`; repository search found no second production call. | **Verified** |
| 18 | No content changes | Static diff/call-graph inspection found E1 metadata/report additions and no direct quality/justification copy injection. There is no complete baseline/current byte proof. | **Blocked by 6** |
| 19 | Zero new approval blockers | Report routing marks only pre-existing rows blocking, and the six E1 codes are non-waivable taxonomy entries rather than Mode-A findings; actual state authority is nevertheless the wrong rail. | **Blocked by 2** |
| 20 | Q0 passes on every athlete-facing surface | No closed pre/post byte harness exists. | **Blocked by 6** |
| 21 | Mode A only; no Mode B/content dispositions | `athletes/config/earned_selection_rollout.yaml` is exactly `mode: A` / `rollout_phase: E1`; `build_candidate` rejects any other rollout at `athletes/scripts/final_plan_candidate.py:277-279`. No E3 promotion artifacts or content deletions were found in the reviewed diff. | **Verified statically** |
| 22 | Methodology authorities fail closed | Unknown methodology/style paths raise at `athletes/scripts/final_plan_candidate.py:285-288` and selection tests cover missing/malformed/unknown inputs at `athletes/scripts/test_earned_selection.py:221-256`. | **Verified** |

## Audit-only and athlete-surface conclusions

- **No Mode B:** verified statically. The rollout file is Mode A/E1 and candidate
  construction rejects a different rollout.
- **New/E3 rail:** emitted non-blocking failures/warnings/unavailable results are mapped
  to `quality_findings`, and the state-v3 replacement/observation behavior is tested.
  Their correctness is limited by blocker 4.
- **Nine legacy rules:** report routing is correctly limited to the nine pre-existing
  IDs, but those report blockers never become the authoritative fulfillment blockers
  (blocker 2).
- **No athlete-facing quality/justification copy:** targeted static searches found no
  report/finding/gate fields passed into guide, ZWO, email, or apply payload producers.
  Internal artifacts are excluded from customer deliverables. Exact non-leak/byte
  equality for guide, ZWO, email, TP, Endure, bundle, and published outputs remains
  unverified because Q0 is missing (blocker 6).
- **No content disposition found:** the reviewed changes preserve the second recovery
  strength file and record the contradiction rather than deleting it. The real chaos
  `hash()` dependency is documented and the tests were run with `PYTHONHASHSEED=0`.

## Non-blocking findings

1. `git diff --check 19a7b4c..aa24e67` is not clean: implementation-notes lines 3 and
   4 have trailing whitespace and the file has an extra blank line at EOF. This
   contradicts a general “clean diff” expectation but does not affect E1 behavior.
2. The implementation-notes acceptance totals (`39 passed, 6 skipped`) describe the
   acceptance slice, while a full-suite run with `GG_PDF_DISABLE=1` produces
   2,670 passed and 49 skipped. The underlying PDF limitation is accurately described;
   the scope of the number should be labeled to prevent confusion.
3. `athletes/scripts/nate_workout_generator.py:2252` uses Python's process-randomized
   `hash()` for chaos workouts. Pinning `PYTHONHASHSEED=0` is a workable deterministic
   E1 fixture condition, but the E2 stable-seed/rebaseline follow-up in the notes should
   remain explicit.

## What I verified

- Read `CLAUDE.md` and the order-safety, archetype/catalog, and generator-conventions
  handover skills before review.
- Inspected the complete commit range and current selection/Appendix 4 state.
- Mechanically compared Appendix 4's fenced JSON with
  `athletes/config/archetype_ids.json`: exact byte match, 13,139 bytes.
- Ran `python3 athletes/scripts/archetype_registry.py`: all checks passed; 100
  archetypes, 24 categories, 600 variations.
- Inspected guide, ZWO, email, apply-contract, persistence, state, report, candidate,
  registry, scorer, and seal paths for Mode-B or internal-copy leakage.
- Confirmed the stored certification manifest has 600 rows and 1,800 results across
  all six gate IDs, with no empty gate rows and all effective verdicts
  `NOT_ENFORCED`.
- Confirmed one production guide-builder invocation.
- Confirmed the apply-contract and fulfillment constructors hash the same five-source
  v2 object when the v2 preconditions are supplied, while retaining a v1 verifier.

## Tests run and verification limits

1. Dedicated earned-selection collection:

   `PYTHONHASHSEED=0 python3 -m pytest -q athletes/scripts/test_earned_selection.py athletes/scripts/test_earned_selection_rules.py webhook/tests/test_earned_selection_state.py athletes/scripts/test_athlete_m_phase1.py`

   Result: **41 passed** in 13.08s.

2. Full repository suite:

   `PYTHONHASHSEED=0 python3 -m pytest -q`

   Result: **2,632 passed, 87 skipped, 21 warnings** in 49.37s.

3. Full suite with acceptance enabled:

   `PYTHONHASHSEED=0 GG_RUN_ACCEPTANCE=1 python3 -m pytest -q`

   Result: **4 failed, 2,668 passed, 47 skipped, 21 warnings** in 64.43s. All four
   failures were the two mandatory-PDF fixtures' PDF-presence and structural checks;
   this sandbox produced no `training_guide.pdf`.

4. Full suite with the repository's sandbox PDF switch:

   `PYTHONHASHSEED=0 GG_RUN_ACCEPTANCE=1 GG_PDF_DISABLE=1 python3 -m pytest -q`

   Result: **2,670 passed, 49 skipped, 21 warnings** in 56.36s.

I could not verify PDF generation/byte equality in this environment. More importantly,
the repository contains no required pre-E1/current Q0 comparator to run, so ZIP, MIME,
Gmail, Endure, published-guide, complete TP operation, and all other §6 before/after
byte claims remain unverified independent of sandbox capability.

**Final verdict: NO-GO — 6 blockers.**
