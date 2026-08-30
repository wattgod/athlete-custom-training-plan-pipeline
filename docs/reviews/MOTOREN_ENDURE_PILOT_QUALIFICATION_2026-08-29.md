# Motoren to Endure pilot qualification — 2026-08-29

## Decision

Motoren is **not qualified as an automatic training-plan authority** for the
Gravel God to Endure launch. It may compile coach-reviewed drafts. A human-owned
Endure pilot does not wait for Motoren.

This decision keeps the product boundary explicit:

- Endure owns athlete delivery, approval, calendar activation, and execution.
- Motoren may propose deterministic plan content with provenance.
- A coach must review Motoren output until the gate below is met.
- A compliance receipt never substitutes for race identity, volume, or content
  correctness.

## Findings corrected in this change

1. **Race identity and weekday:** request race dates now determine their actual
   block week and race-week weekday. A named event replaces the generic
   `RACE_DAY` placeholder instead of being silently skipped.
2. **Race event semantics:** a race is emitted as a zero-load calendar event,
   not a fabricated three-hour, 190-TSS structured workout. Endure owns the
   existing dated athlete event. Endure does **not** yet model planned event
   TSS/load separately, so projected race-week load remains incomplete; that is
   an explicit automatic-authority blocker below.
3. **Contract truth:** `NEEDS_REVIEW.txt` now fails the daily deterministic
   contract. The prior report overstated send-worthy output.
4. **Failure diagnosis:** preview failures retain their check identity instead
   of all collapsing into `preview fail`.
5. **Discipline truth:** the historical gravel catalog bucket is refined for
   recognized MTB and road events before it becomes an explicit plan
   discipline. Synthetic judge metadata uses the same resolver.
6. **Road-guide relevance:** unlicensed road/fondo athletes no longer receive
   the Cat 5-to-1 campaign chapter. The strategy title reflects the actual
   event format.
7. **Intensity accounting:** preview verification now follows ratified AE-2.2
   volume-scaled, time-in-zone accounting (70% easy at 7h, 75% at 10h, 80%
   at 12-15h) and AE-2.3 declared-distribution comparison, rather than
   classifying an entire mixed session by one normalized IF or using one fixed
   ratio at every volume tier. The check is per load week, splits linear ramps
   at the Z2 boundary, and reports target-free time as unknown.
8. **Configuration integrity:** required YAML must be a non-empty mapping.
   Missing/offloaded configuration now fails with a named configuration error
   instead of cascading into an opaque `NoneType` engine failure.
9. **Authoritative review state:** preview FAIL results, plus weekly-volume WARN
   results below the 80% send-worthy floor, now enter the durable
   `BLOCKED_REVIEW` catalog. PlanIR and the TrainingPeaks projection are rebuilt
   after that merge; `NEEDS_REVIEW.txt` is compatibility output, not authority.
10. **Validator failure posture:** a preview crash invalidates any stale HTML,
    writes the non-waivable `VALIDATOR_CRASH_PLAN_PREVIEW` blocker, and cannot
    degrade to a clean disposition.
11. **Audience boundary:** `plan_preview.html` remains in the authenticated
    coach review bundle but is no longer included in the athlete/customer ZIP.
12. **Acceptance truth:** the four real-order fixtures now pin their exact
    clean or `BLOCKED_REVIEW` disposition. Three retain explicit intensity
    blockers and the 7-hour masters case retains its exact 79% volume debt;
    missing or additional findings fail the suite.

## Current no-go evidence

The 2026-08-29 committed quality history reported a `0.12` quality rate, a
`5.88/10` average coach score, and a nominal `0.62` deterministic contract
rate. Replay showed that the contract rate ignored durable review markers; the
true clean rate for that fixed eight-avatar set was 3/8. The failing examples
include real weekly-volume underfill and intensity-placement issues, not only
judge noise.

The current volume engine can underfill 9-hour and 15-hour athletes by roughly
one third. This change does not weaken R19 or silently inflate sessions to make
the metric green. That requires a separately ratified planning change.

## Qualification gate for automatic authority

All conditions are required:

1. A fixed road/gravel/MTB avatar matrix achieves 100% deterministic contract
   pass with no `NEEDS_REVIEW` marker.
2. No race is omitted, duplicated, assigned to the wrong date, or mapped to a
   structured workout. Include Saturday, Sunday, B+A weekend, and mis-bucketed
   descriptor cases.
3. Weekly volume, intensity placement, and time-in-zone distributions meet the
   ratified rules without gate weakening.
4. Missing age, experience, discipline, methodology, and race facts either
   fail closed or appear as explicit review assumptions.
5. Planned race load has an explicit event model; race-week PMC/target load is
   not inferred from a fabricated universal race prescription.
6. At least one complete season per supported discipline receives human coach
   signoff with zero P0/P1 findings.
7. Actual Motoren JSON passes a cross-repository golden path through Endure
   mapping, draft persistence, coach approval, activation, and athlete calendar
   execution.
8. Five consecutive production-safe Endure canaries succeed before any default
   provider flip.

## Verification

```bash
PYTHONPATH="$PWD:$PWD/athletes/scripts" python3 -m pytest -q \
  webhook/tests/test_engine_block.py \
  webhook/tests/test_engine_season.py \
  athletes/scripts/test_coverage_sweep.py \
  athletes/scripts/test_daily_avatar_run.py \
  athletes/scripts/test_discipline_detection.py \
  athletes/scripts/test_road_racing.py \
  athletes/scripts/test_plan_preview.py
```

Expected focused result for this change: `279 passed`.

The fail-closed configuration-loader regression is verified separately:

```bash
PYTHONPATH="$PWD:$PWD/athletes/scripts" python3 -m pytest -q \
  athletes/scripts/test_calendar_plan.py::test_required_config_loader_rejects_empty_or_non_mapping_yaml
```

Expected result: `1 passed`.

The full real-order disposition contract is verified separately:

```bash
GG_RUN_ACCEPTANCE=1 GG_PDF_DISABLE=1 \
PYTHONPATH="$PWD:$PWD/athletes/scripts:$PWD/webhook" \
python3 -m pytest -q athletes/scripts/test_order_acceptance.py
```

Expected result with PDF deliberately disabled: `41 passed, 8 skipped`.

This is source-level qualification evidence. No deployed Motoren request or
authenticated Endure delivery is claimed here.
