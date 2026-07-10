---
name: archetype-and-catalog
description: Load when touching workout archetypes, race-to-archetype mapping, or the sellable plan catalog.
---

# Archetype system and plan catalog

## 1. The archetype system (production, live)

Ground truth is code, not docs: `python3 athletes/scripts/archetype_registry.py`
prints a live summary. Verified 2026-07-09: **100 archetypes, 24 categories,
600 total variations (6 progression levels each)**. Source files:
`new_archetypes.py` (50) + `imported_archetypes.py` (34) +
`advanced_archetypes.py` (16), merged by `archetype_registry.py` — treat the
registry as the single source of truth for catalog/lookup/validation, not the
source files individually.

Root `CLAUDE.md` is internally inconsistent: its summary line (~L19) says
"100 archetypes × 6 levels = 600" (matches the registry), but later prose
(~L292, ~L420-429, "Workout Archetype System") says "95 archetypes across 22
categories = 570 variations." That prose is stale, superseded by the live
registry output above. Don't propagate the 95/570 figure.

Two archetype formats: Format A (`intervals` tuple + on/off power) and
Format B (list of segment dicts: steady/intervals/freeride/ramp). All 11 Nate
workout types have custom handlers in `generate_athlete_package.py` — no
generic SteadyState fallback.

**Do not confuse this with the root-level `archetypes/` directory.** Per
`.gitmodules` it is the git submodule `nate-workout-archetypes`, and it is
currently UNINITIALIZED (empty on disk; `git submodule status` shows it
unchecked-out). Per the sibling marketplace architecture doc, that submodule
is a different, smaller legacy set (31 archetypes × 6 levels, ~2,576 real
Nate Wilson reference workouts + a white paper) used historically as a
quality reference, not the production selection system.
`tests/archetypes/validate_archetypes.py` and
`.github/workflows/validate-archetypes.yml` validate that submodule's
structure — separately from the `athletes/scripts/` archetype tests.

## 2. Race-to-archetype mapping — treat IDs as a public contract

`race_category_scorer.py` (this repo, `athletes/scripts/`) holds
`DEMAND_TO_CATEGORY_WEIGHTS`: 8 demand dimensions (durability, climbing,
vo2_power, threshold, technical, heat_resilience, altitude,
race_specificity; each 0-10) weighted 1.0-3.0 against archetype categories.
`race_pack_generator.py` (also here) is the CLI orchestrator: race JSON →
demand vector → category scores → workout pack → ZWO files → coaching brief.

Verified today: `gravel-race-automation/scripts/race_demand_analyzer.py` and
`gravel-race-automation/web/race-packs/*.json` (757 files) both exist in the
sibling repo — this is the parity-tested twin of the weight matrix that
actually renders the "Train for [Race Name]" section on gravelgodcycling.com
race pages. [UNVERIFIED — session memory, Jul 2026]: the exact live page
count (memory says 686); not re-checked against the deployed site this
session.

Because a sibling repo's consumer code and JSON caches key off archetype and
category names, **renaming or removing an archetype/category here can
silently break the consumer side with no local test to catch it.**

## 3. Plan catalog — source of truth

The REAL sellable plan set is
**`../gravel-race-automation/plans/{N. Tier Level (weeks)}/template.json`**
— verified 15 dirs on disk (Ayahuasca/Finisher/Compete/Podium tiers ×
Beginner/Intermediate/Advanced/Masters/Save-My-Race levels; not a strict
4×5 grid — e.g. no Ayahuasca-Advanced, no Compete-Beginner, Podium has only
2 levels). Each `template.json` is a full periodized plan with a named
workout every day, no gaps. Plan of record:
`gravel-race-automation/docs/TRAINING_PLAN_MARKETPLACE_ARCHITECTURE.md`.

**`tp-skus/` in THIS repo is the WRONG source for sellable plans** — thin
generic "demand-family" SKUs. It was already used by mistake once to build a
real customer plan (all-endurance, gaps, no guide attached). Do not build TP
plans from it.

The architecture doc §2 (2026-07-04) revises the *forward* catalog strategy:
cut from 15 plans/race down to a leaner self-serve set (Time-Crunched /
Finisher / Compete / Masters + Save My Race) and kill Podium as a
self-serve template (route those athletes to coaching instead). The on-disk
15-SKU `template.json` set is still the current content source of truth for
what a plan's workouts/structure look like; §2 is the standing decision for
which tiers ship as self-serve going forward.

## 4. Testing week — verified current, no conflict

Every base plan opens with the full 360 Testing Week (source: TP plan
230732, 352 TSS / 6:22, 7-day RPE-anchored protocol + education layer).
Confirmed CURRENT in `TRAINING_PLAN_MARKETPLACE_ARCHITECTURE.md` §4
(revised 2026-07-04) — matches the standalone testing-week memory note, no
conflict between the two sources. Mid-plan retest is a single compressed
20-minute aerobic day (~week 7), never a second full test week. §4 leaves
the 8-week / Save-My-Race testing-week length as an open decision.

## 5. Where else to look

Root `CLAUDE.md`'s "Workout Archetype System" and "Intake-to-Plan Pipeline"
sections cover the selection flow (`archetype.py` → `workout_selector.py` →
`series_tracker.py` → `block_compliance.py`) — read those for block-builder
mechanics. This file only covers archetype identity, race-mapping weights,
and plan-catalog sourcing.

## When NOT to use this

Skip this skill for webhook/Stripe/checkout work, block-builder phase or
compliance-rule logic, ZWO rendering internals, or HTML/PDF guide
generation — none of those touch archetype identity, race-mapping weights,
or plan-catalog sourcing. Use CLAUDE.md's Block-Builder and Intake-to-Plan
sections instead.
