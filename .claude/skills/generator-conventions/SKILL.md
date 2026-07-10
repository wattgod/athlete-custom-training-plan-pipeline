---
name: generator-conventions
description: Load when touching workout/plan generation, scheduling, or compliance logic.
---

# Generator Conventions

Read `CLAUDE.md` first (445 lines) — "Block-Builder Coaching Engine" (line 160) and
"Intake-to-Plan Pipeline" (line 264) already cover the pipeline diagram, the 11
CRITICAL compliance rules, key files, and the June 2026 overhaul pitfall list. This
file does not restate that; it adds what CLAUDE.md is silent or stale on, verified
against the code on 2026-07-09.

## Architecture — confirmed as documented, with two corrections

The calendar-driven chain in CLAUDE.md (archetype.py → calculate_plan_dates.py →
`block_chain.build_plan_from_calendar` → workout_selector.py → series_tracker.py →
block_compliance.py → workout_mapper.py) matches the code. `chain_blocks()`
(`athletes/scripts/block_chain.py:193`) is still present and still legacy — do not
call it for new work; use `build_plan_from_calendar` (`block_chain.py:63`).

**Correction 1 — the compliance gate no longer hard-kills the build.**
`athletes/scripts/generate_athlete_package.py:564-596`: as of commit `ddd13a7`
(2026-06-22, "never deliver NOTHING — flag-for-review instead of failing the
order"), a CRITICAL-rule failure no longer raises by default. It DELIVERS the plan
and writes `NEEDS_REVIEW.txt` into the athlete dir for coach review. Only
`GG_STRICT_COMPLIANCE=1` restores the hard-fail (use it in CI/debugging when you
need a build to actually stop). CLAUDE.md line 187 ("a failing plan raises and
kills the build") describes the pre-`ddd13a7` behavior — treat it as superseded by
this file. The block-builder-*exception* path (a crash, not a rule failure) still
raises unconditionally — that part of CLAUDE.md is accurate.

**Correction 2 — `block_compliance.py`'s own docstring is wrong.** It claims "25
rules (14 CRITICAL, 11 WARNING)" but only 11 `rXX_*` functions exist
(R01-R06, R08, R11, R14, R19, R20) and `validate_plan` wires all 11 as CRITICAL —
zero WARNING-severity rules are implemented. CLAUDE.md's "11 CRITICAL" count is the
accurate one; don't trust the module docstring.

**Variety enforcement** — `workout_selector.py`: `block_number` (docstring at
line 82) drives rotation through intensity/long-ride alternatives so adjacent
blocks don't repeat names, plus the filler level ladder. Filler slots can carry a
`pool` key (`workout_selector.py:272-274`, e.g. Endurance/Cadence Work) that the
week builder cycles across filler days for day-to-day variety, independent of the
block-keyed rotation used for intensity series (see CLAUDE.md's R01 note on
role-based classification).

**Discipline gating** — `athletes/config/workout_selection.yaml` `disciplines:`
block (line 150) overlays `extra_alternatives` onto `intensity_2`/`intensity_3` per
discipline (gravel: SFR/Microbursts/Mixed Climbing Variations; road: Tempo/
Threshold Progressive/Blended VO2max and G Spot/G-Spot; mtb: Stomps + others) —
never displacing the build-phase VO2 slot (CLAUDE.md already flags this). Discipline
itself comes from `archetype.py:derive_discipline` (line 204) via
`_DISCIPLINE_KEYWORDS` (line 157), race-name-keyword-matched, gravel-first when
ambiguous. Known residual limitation (not a bug to "fix" casually): genuinely
ambiguous or dual-listed race names (gravel DB mirrors some road events) can still
fall through to keyword guessing.

## Base-library engine is a DIFFERENT repo — don't confuse the two

The "brutal-review-hardened" base-library work (durability long-ride curves,
compound-ZWO handler fix, heat-protocol consolidation, variation/voice fixes) lives
in the sibling repo `gravel-god-training-plans` (the `ggtp` engine — see sibling
directory `/Users/mattirowe/Documents/GravelGod/gravel-god-training-plans`), not in
this pipeline. This repo has no `plan_builder.py`, `finalize_plan.py`, or
`workout_library.py`-as-TP-catalog-indexer matching that memory's description — its
own `athletes/scripts/workout_library.py` is a distinct module for this pipeline's
own selection system. If you're asked to touch durability blocks, compound-ZWO
correctness, heat protocol, or base-plan variation, confirm which repo the task
actually means before editing here — those fixes were made and verified in `ggtp`,
not in this one. [UNVERIFIED — session memory, Jul 2026: exact file layout inside
`gravel-god-training-plans`; not opened as part of this task.]

## Strength content is provisional — do not polish as final

`athletes/config/strength_periodization.yaml` (Foundation/Max Strength/Maintenance
phases, feeding `select_strength_days` in
`generate_athlete_package.py:345,2422,2441`) is unchanged since commit `2d0c073`
(2026-04-01) — it predates a ground-up strength rebuild Matti ordered on
2026-07-08 ("I don't know how confident I am in the strength program"), handoff at
`~/Documents/GravelGod/strength-overhaul/HANDOFF.md`. The session templates this
repo currently renders (Foundation Strength A/B, Power Development, Cycling-
Specific, Mobility and Stability) are the old set. [UNVERIFIED — session memory,
Jul 2026: whether/when the new philosophy (`gravel-god-cycling/docs/strength-
training-philosophy.md`) gets ported into this repo's YAML — not done as of this
file's writing.] Do not extend or "clean up" the current strength templates as if
they were the settled design; treat them as a placeholder pending that rebuild
landing here.

## Open items (verified still open against current code/tests, 2026-07-09)

- **Advisory-only preview WARNs by design, not bugs**: `generate_plan_preview.py`
  "TSS Progression" (line 436) and "Weekly Volume" (line 314) checks can WARN
  (e.g. build-phase TSS dipping below base for hour-capped athletes, or under-fill
  vs target hours) without failing the build — this is intentional advisory
  signal for the coach, not a defect to silence.
- **Discipline-detection residual misses** on genuinely ambiguous/dual-listed race
  names (see Discipline gating above) — inherent to keyword matching, not closed
  by a specific fix.

Items previously tracked as open in memory but now verified CLOSED and dropped:
MTB skills chapter now exists (`training_guide_builder.py:2157
_section_mtb_skills`); discipline-aware race-duration/fueling model shipped
(`calculate_fueling.py:130-155 _SPEED_BY_DISCIPLINE`); `test_plan_dates.py` is
12/12 passing (no date-drift failures as of this session).

## When NOT to use this

Skip this file for: intake questionnaire parsing/validation work (see
`intake_to_plan.py`, not covered here), PDF/HTML guide content or voice questions
(`training_guide_builder.py`, `validate_guide_quality.py`), webhook/order/delivery
plumbing, TrainingPeaks upload/library recipes, or anything in the sibling
`gravel-god-training-plans` (ggtp) repo — that engine has its own conventions and
is out of scope here.
