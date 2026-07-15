# Handoff → GPT-5.6-sol: review the Plan-Truth slice + gate the next ticket

Run me read-only against the repo:
`codex exec -m gpt-5.6-sol -s read-only -C <athlete-custom-training-plan-pipeline> < docs/PLAN_TRUTH_HANDOFF.md`

## Where we are (context, verified)

The first real custom-plan fulfillment (Heather Gray, UCI Gravel Worlds/Nannup)
shipped only after heavy hand-fixing. The root cause we landed on: **the pipeline
has no canonical plan model** — it independently authors the block schedule, ZWO
XML, workout prose, fueling YAML, guide, coaching brief, and (today) the human-
built TrainingPeaks content. Those are parallel interpretations of the athlete,
so each artifact can be internally valid while the delivered product is
collectively false (four different race-fuel numbers; description prose that
didn't match the XML; "day before race" on random openers; a Week-8 retest
labelled "Week 1/12"; a stale race record 112mi/8202ft/Heerlen for a
75mi/10,171ft Nannup race; a plan counting ~half her real training load; a
"READY FOR REVIEW" email on a plan that had failed a critical compliance rule).

**Full spec:** `docs/PLAN_TRUTH_SPEC.md` — north star `PlanIR` (one versioned
source-of-truth; ZWO/guide/notes/TP become serializers, not authors), tickets
G1-G6 / H1 / I1-I2 / J1, and a build-first order. It reprioritizes the Jul-13
`PIPELINE_HARDENING_AND_INTELLIGENCE_SPEC.md` (B13→P0 rewrite as G4; WS-E
premature; A4/C5 don't gate "flagged-but-shipped"; D10 needs semantic comparison).

## What just shipped — branch `plan-truth-fixes` (off main, NOT merged)

An executor (gpt-5.6-terra) implemented **G1 + G2 + G6** with tests. `git diff
origin/main` and `IMPLEMENTATION_NOTES.md` on that branch show it. Summary:
- **G1** — new `athletes/scripts/fueling_policy.py::FuelingPrescription`.
  `calculate_fueling.py` serializes it to `fueling.yaml` as `prescription` while
  keeping legacy `carbohydrates` fields. Carb target now scales by duration, body
  mass, FTP×goal-IF (absolute work rate), goal, tolerance; sex → energy-
  availability warning only; missing tolerance ⇒ conservative ceiling (≤70 g/hr
  sub-65 kg) + assumption flag. (Heather 61kg/230W/podium now resolves 63 g/hr,
  range 56-70, total 353 — not 90.)
- **G2** — `constants.py::FUEL_TAGS` literals removed (now `{}`); per-workout
  fuel tags + the guide's personalized fuel card render from the prescription.
  Generic educational ranges left as-is.
- **G6** — steady endurance/recovery warm-up end power capped at the main steady
  power; cooldown monotonic-down; nonzero-main-set check. Interval warm-ups
  untouched.
- Tests: `test_calculate_fueling.py`, `test_artifact_facts.py`,
  `test_steady_workout_invariants.py` added; `test_compliance_rules.py` updated
  (old tests asserted the removed FUEL_TAGS literals). Suite: **1126 passed, 53
  skipped** (independently re-run). Run: `.venv/bin/python -m pytest athletes/scripts/ -q`.

## Your job (be adversarial, cite file:line)

1. **Merge gate on `plan-truth-fixes`.** Review the diff for correctness and
   regressions. Specifically:
   - Does the fueling truly flow from ONE source now, or did any independent fuel
     literal survive (per-workout tags, guide card, race-day workout, coaching
     brief, notes-adjacent copy)? Is `FUEL_TAGS == {}` safe — any caller still
     expecting keys?
   - Is the carb MODEL sound? Check the work-rate estimate, the sub-65 kg ceiling,
     the goal-IF assumptions, and that a heavier/higher-work athlete scales up
     while goal-only can't reach 90. Any athlete class where it now UNDER-fuels
     dangerously (big rider, hot race, ultra-distance)?
   - Did `test_compliance_rules.py` (and any other test) get WEAKENED to pass,
     vs legitimately updated for removed behavior?
   - Backward-compat: does `generate_athlete_package` / `training_guide_builder`
     still render, and do the legacy `carbohydrates` fields stay consistent with
     the new `prescription`? Any consumer of `fueling.yaml` that breaks?
   - G6: is the warm-up cap scoped correctly (steady only, not neutering interval
     activation)? Any endurance archetype it mis-handles?
   - **Give GO / NO-GO to merge, with must-fix items.**

2. **Gate the next ticket — J1 (enforced review/fulfillment state machine).** Per
   the spec's build-first order, J1 is next. Validate the J1 design against the
   real code (`generate_athlete_package.py` compliance gate ~line 579;
   `webhook/app.py` `/api/confirm` ~1775 and the "READY FOR REVIEW" email ~360;
   `intake_to_plan.py` delivery). Produce a precise, executor-ready implementation
   plan: exact files, the state file + transitions, where BLOCKED_REVIEW is set,
   how `/api/confirm` enforces it, the waiver shape, and the named tests — tight
   enough that gpt-5.6-terra can implement without guessing. Flag anything in the
   spec's J1 that's wrong or underspecified given the live code.

3. **Sanity-check the remaining order** (G3 segment-first descriptions → G4
   recurring-session ledger → G5 consistency gate → H1 → I1/I2). Anything that
   should move earlier/later, or a dependency the spec missed?

Deliver: (1) branch GO/NO-GO + must-fix; (2) the executor-ready J1 plan; (3) any
reordering. Don't rubber-stamp — the whole point of this exercise is that the
last plan shipped broken.
