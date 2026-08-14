# Phase E1 implementation notes

Date: 2026-08-13  
Contract: `docs/SPEC_EARNED_SELECTION.md` §7.2, E1 only  
Rollout: Mode A / E1, audit only

## Outcome

E1 installs earned-selection identity, scoring, registry, report, state, seal,
and ordering plumbing without enabling Mode B or adding approval blockers. All
hypothesis and E3-target results remain effective `NOT_ENFORCED`. The only
approval blockers remain the nine pre-existing compliance checks, evaluated by
the A3.0 production-equivalent functions. New results are persisted as
`quality_finding` records.

## §7.2 gap inventory

| E1 definition-of-done item | Initial state | Final status | Evidence |
|---|---|---|---|
| Appendix 4 immutable IDs and exhaustive selection-byte equivalence | Partial | Fixed | `athletes/config/archetype_ids.json`, `archetype_identity.py`, `workout_selector.py`, `workout_mapper.py`, `nate_workout_generator.py`; exhaustive slot, level, wrap, mapper, discipline, and customer-render fixtures in `test_earned_selection.py` |
| Appendices 5–8 registries/schema and producer-only origins | Partial | Fixed | `purpose_registry.yaml`, `quality_gates.yaml`, `rule_registry.yaml`, `non_native_producers.yaml`, `phase_purpose_registry.yaml`, `final_plan_candidate.py`; closed provenance and origin projection in `generate_athlete_package.py` and `canonical_training_model.py` |
| Pure scorer and complete observed hypothesis results | Partial | Fixed | `earned_selection.py`, `workout_quality_report.py`; trace/dose/W′bal goldens and Mode A complete-result assertions in `test_earned_selection.py` and `test_athlete_m_phase1.py` |
| Manifest, revision snapshot/pin, report, and derived-report coverage | Partial | Fixed | `certify_workout_library.py`, `workout_certification.json`, `workout_quality_report.py`, `derived_registry.py`, `final_plan_candidate.py`; deterministic regeneration, candidate pin, model/report ID equality, and two-record derived coverage tests |
| Appendix 3 complete execution; nine existing blockers only through A3.0 equivalence | Partial | Fixed | `earned_selection_rules.py`, `rule_registry.yaml`; named edge goldens plus exhaustive finite branch/boundary differential corpus in `test_earned_selection_rules.py` |
| State/catalog/snapshot v3 and seal v2, with backward verification | Partial | Fixed | `webhook/fulfillment_state.py`, `webhook/app.py`, `apply_contract.py`; v3 replacement/regeneration isolation, closed finding validation, automatic observed snapshot, dual v2 constructors, and v1 compatibility fixtures in `test_earned_selection_state.py` |
| Six new non-waivable codes and closed set equality, without E1 enforcement | Missing dedicated coverage | Fixed | Exact six-code and full `NONWAIVABLE_CODES` equality assertions in `test_earned_selection_state.py`; athlete-m proves they do not enter fulfillment issues in Mode A |
| §4.5 pre-D1 W00/fueling/snapshot order, D2 binding, and exactly one guide build | Partial | Fixed | `generate_athlete_package.py`, `training_guide_builder.py`, `final_plan_candidate.py`; producer-selected fueling tier is carried separately from unchanged athlete prose; external race input is staged and content-addressed before D1; athlete-m replay verifies the frozen candidate/report/model relationship |
| Methodology authorities fail closed while known selection remains equivalent | Partial | Fixed | `select_methodology.py`, `methodology_profiles.yaml`; missing, malformed, unknown-ID, and unknown-style fixtures in `test_earned_selection.py` |
| Stable session IDs, doubles, collision failure, and report/model equality | Partial | Fixed | `canonical_training_model.py`, `final_plan_candidate.py`, `workout_quality_report.py`; identity/collision fixtures plus athlete-m equality assertions |
| Q0 athlete surfaces and Mode A replay | Partial | Fixed | Exact pre-migration native-render comparisons, TP-kind closed-set assertion, athlete-m Mode A replay, existing delivery/guide/IR/projection regression suites, and the full repository suite |
| E1 audit-only constraints: no Mode B, content disposition, or new blocker | Partial wiring | Fixed | `earned_selection_rollout.yaml` is exactly Mode A/E1; report gates are all `NOT_ENFORCED`; fulfillment merges only pre-existing rubric blockers; recovery strength content is retained and its contradiction is a finding |

## Decisions and deviations

- The E1 strength-template identity uses the exact Appendix 8 set
  (`aa_a` through `deload_a`). A pre-existing second recovery strength file is
  not deleted: both files bind to `deload_a`, and R11/R12 report the frequency
  contradiction. This follows §7.2's audit-only/no-content-change boundary.
- Fueling projection records the producer-selected closed tier while preserving
  the previously rendered athlete fueling text byte-for-byte, as required by
  §4.4.1 and §7.2.
- Optional external race-guide data is copied to a digest-named athlete-local
  input before D1. D2 consumes that staged object and verifies its digest; it
  does not re-read mutable external race data.
- The Appendix 4–6 fenced payloads are extracted by
  `materialize_earned_selection_configs.py`. Appendices 7–8 and Appendix 3 are
  table-defined, so the same materializer validates their schema versions and
  deterministically rewrites the reviewed semantic YAML rather than trying to
  infer policy from prose.
- The pre-existing `chaos` archetype renderer seeds itself with Python's
  process-randomized `hash()`. E1 certification and its Q0 fixture therefore
  pin `PYTHONHASHSEED=0`. Replacing that renderer seed would alter workout
  bytes, so it is deliberately deferred to E2 rebaselining under §7.2.
- No promotion artifact, owner content disposition, threshold calibration,
  Mode B behavior, or E3 enforcement was added.

## Verification

- Dedicated E1 collection: 41 tests collected across
  `test_earned_selection.py`, `test_earned_selection_rules.py`,
  `test_earned_selection_state.py`, and the athlete-m replay.
- E1 plus TrainingPeaks projection slice: 55 passed.
- Full repository suite: **2,632 passed, 87 skipped, 21 warnings**.
- Acceptance with `GG_RUN_ACCEPTANCE=1`: 37 passed, 4 skipped, 4 failed. All
  four failures were the two mandatory-PDF scenarios: the sandbox did not
  generate `training_guide.pdf`, so presence and structural validation failed.
- Acceptance with the repository's sandbox switch
  `GG_RUN_ACCEPTANCE=1 GG_PDF_DISABLE=1`: **39 passed, 6 skipped**. The six
  skips are PDF-only checks; all non-PDF acceptance surfaces passed.

## E2 follow-ups

1. Review and disposition the observed finding backlog; fix, reclassify,
   retire, or band-adjust only with the owner artifacts required by §3.
2. Replace the `chaos` renderer's process-randomized seed with a stable seed,
   enumerate the resulting content-byte change, and rebaseline certification.
3. Resolve the observed recovery-strength frequency contradiction as an
   explicit content disposition if the owner approves it.
4. Complete purpose-assignment ownership and gate-promotion evidence before
   considering any enforcing transition.
5. Run the PDF acceptance checks in an environment with the PDF browser engine
   available; this is an environment verification gap, not an E1 logic bypass.

