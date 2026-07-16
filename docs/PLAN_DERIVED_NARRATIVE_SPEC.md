# Spec: Plan-Derived Narrative (single source of truth for guide + descriptions)

## Problem

The daily E2E's codex-sol grader will not converge to GO by patching individual
findings. Root cause is architectural: the athlete-facing **narrative** (training
guide prose, ZWO workout descriptions, fueling copy) is largely **hardcoded /
templated**, while the **plan** (weeks, phases, recovery cadence, workouts,
fueling targets) is **generated**. Any diff-checker therefore finds an endless
supply of prose-vs-plan contradictions: the guide says "recovery every 3 weeks"
while the plan schedules every 4; a description says "15min warmup" while the XML
runs 6.6; the guide "mandates strength" the athlete opted out of; etc.

Four whack-a-mole rounds (2026-07-15/16) fixed ~23 real defects but each round
surfaced the next layer. This is an asymptote, not a backlog.

## North star

**Every athlete-facing claim about the plan is derived from the plan, not
authored independently.** The generated artifacts (`plan_dates.yaml`,
`plan_ir.json`, `fueling.yaml`, the final ZWO XML) are the single source of
truth; the guide and descriptions render *from* them.

## Scope (the narrative surfaces)

1. **`training_guide_builder.py`** — the largest offender. Enumerate every
   sentence/table cell that states a plan fact and replace the literal with a
   value read from the plan:
   - Recovery-week cadence + volume-drop % → from `plan_dates.yaml`
     `is_recovery_week` + `plan_ir.json` weekly `duration_s`.
   - Phase behavior claims ("peak volume starts to drop") → from the actual
     weekly-volume curve.
   - Strength claims → already gated on `strength_included`; audit for any
     remaining unconditional mention.
   - Fueling numbers (race target, hydration, duration buckets) → from
     `fueling.yaml` prescription, not static tables. Keep cited *general*
     education clearly labelled and non-numeric-for-this-athlete.
   - Masters recommendations → reconcile with what the plan actually delivers
     (or make the plan age-adapt, a separate decision).
2. **ZWO descriptions** (`nate_workout_generator.py` / `workout_spec.py`) —
   build the description text **from the final, scaled XML**, not the pre-scale
   template. Warmup/cooldown/interval-recovery minutes, rep counts, and the
   MAIN SET line must reproduce the emitted segments exactly. Fix the single-rep
   `0min recovery @ 0% FTP` degenerate render while here.
3. **Fueling narrative** — one canonical prescription (the personalized banner)
   drives both the workout tags and the guide's personalized card; general
   ranges stay explicitly general.

## Approach

- **Phase A — inventory.** A script that greps the guide/description code for
  numeric/plan claims and cross-references each against the generated artifacts
  for the E2E fixture; output a ranked list (athlete-visible first).
- **Phase B — derive.** Replace literals with plan-read values, section by
  section. Prefer passing the plan artifacts into the section builders over
  re-loading.
- **Phase C — gate.** Extend the G5 `validate_plan_package` semantic gate to
  cover the guide: assert no guide claim contradicts `plan_dates`/`plan_ir`/
  `fueling` (recovery cadence, volume trend, fuel numbers, strength inclusion,
  taper structure). This is the "narrative lint" that keeps it from regressing.

## Definition of done

The daily E2E's codex-sol pass trends to GO (or only advisory WATCH items on
genuine human-judgment calls like ramp-in aggressiveness), and the new
narrative-consistency gate is green — so future template edits can't
re-introduce prose-vs-plan drift.

## Sizing

Multi-step; best dispatched to executors per section with the parent reviewing.
Phase A is a day; Phase B is the bulk (the guide has ~30 sections); Phase C is
the durable payoff. Not a reactive fix — spec, schedule, dispatch.
