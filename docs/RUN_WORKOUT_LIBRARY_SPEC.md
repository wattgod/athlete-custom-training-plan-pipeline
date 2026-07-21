# RUN-LIB v1 — Run Workout Library Spec

**Status:** v2 DRAFT (Fable, 2026-07-20) — sol NO-GO on v1; all 11 findings folded. Pending Matti go.
**Repo home:** `athlete-custom-training-plan-pipeline`
**Origin:** Anthony Robinson dual-sport build (Jul 2026). Every run session was
hand-authored because the engine has no run library. This spec makes run
workouts selectable system content, like the bike archetypes.

## Why (northstar tie)

The pipeline's moat is deterministic, coach-grade content at ~$0 marginal cost.
Runs are currently the one modality where a coached athlete gets freeform prose
— unversioned, unleveled, untested. Dual-sport athletes (trail-ultra + gravel)
are a real coaching segment (Anthony is the pilot), and Endure Labs needs run
support eventually anyway. v1 targets the COACHED-ATHLETE path (calendar
placement), not the self-serve plan SKU path.

## Scope v1 / non-goals

IN: run archetype data model + registry, 6-level progressions, run description
renderer, TP structure JSON export + committed fixture, rTSS estimation, the
dual-sport weekly template (Tue workout / Wed optional / Sat long), TP library
folder build ("GG Run | *"), run compliance gate, tests.

OUT (v2+): full run-plan periodization engine, run methodology scoring, ZWO
export, treadmill variants, run power (Stryd), self-serve run plan SKUs, brick
sessions, integrating runs into `block_compliance.py`'s cycling rules (see
"Compliance" — runs get their own gate).

## Data model

New files:
- `athletes/config/run_workout_library.yaml` — data
- `athletes/scripts/run_archetypes.py` — loader + registry (pattern copied from
  `archetype_registry.py`: catalog, lookup, validation, duplicate-ID guard)

**Canonical schema decisions (sol finding 2 — one shape, stated normalization):**
- YAML root is a mapping `run_workouts: {<id>: <def>}` (matches
  `workout_library.yaml` root-mapping style, not a list).
- IDs are stable, sport-namespaced: `run.<category>.<slug>`
  (e.g. `run.hills_powerhike.hike_the_damn_hill`). `display_name` is a separate
  field — display names never route logic (sol finding 10; existing bike
  routing keys on substrings like `openers`, so run items must never be
  identified by display text).
- Every def carries `sport: run` and `category: <category_id>` fields — ALL
  downstream helpers dispatch on these, never on name substrings (sol finding 9).
- Durations in YAML are **minutes** (library convention); the loader converts
  to seconds internally. Level keys are written as ints in YAML and normalized
  to strings at load, matching `archetype_registry.py` L178 and Nate
  `get_level_data` L998 behavior.
- TSS key is `tss` (library convention), computed per the rTSS section and
  stored.

**Format R (segments)** — block-style YAML (v1's flow-style example did not
parse; sol finding 1):

```yaml
run_workouts:
  run.hills_powerhike.hike_the_damn_hill:
    display_name: "Hike the Damn Hill"
    sport: run
    category: hills_powerhike
    levels:
      3:
        duration: 60            # minutes
        tss: 52
        segments:
          - type: warmup
            duration: 8         # minutes
            rpe: [2, 3]
          - type: repeat
            count: 5
            of:
              - type: steady
                duration: 6
                rpe: [3, 4]
                label: "Run easy"
              - type: hike
                duration: 3
                rpe: [4, 5]
                label: "POWER-HIKE climb"
          - type: cooldown
            duration: 7
            rpe: [1, 2]
        cadence_prescription: "170-180spm running; hike = hands-on-knees, strong steps"
        terrain_prescription: "Rolling trail with sustained climbs"
        execution: "Hike hard enough that running would only be marginally faster."
```

Segment `type` enum: `warmup | steady | stride | pickup | tempo | hike | race |
cooldown | repeat`. Intensity is **RPE (canonical)**; optional `hr_pct_lthr`
and `pace_pct_threshold` ranges are allowed but render as PROSE lines only in
v1 (never as TP targets — sol finding 4). Library-generic text uses RPE and
%LTHR; absolute BPM appears only at athlete placement time, rendered from the
athlete's LTHR (fallback: if LTHR absent, RPE-only rendering — no invented HR).

**Six levels** follow `get_progression_context` semantics (1 Introductory → 6
Peak). Progression axes per category: duration first (Endurance/Long), then
density (Hills/Tempo), never both in one level step. Long Run caps at 3:15
regardless of level. `race_day` briefs are the one exception to Format R:
`structure: null`, description-only (stated exception; sol finding 4d).

## Categories & seed archetypes

**15 archetypes: 13 leveled × 6 levels + 2 unleveled race briefs = 80 items**
(v1 said "12 × 6 = 72" while listing 15; sol finding 1 — this is the corrected
count and R1's scope).

| category_id | Archetypes (display names) | Notes |
|---|---|---|
| recovery_easy | "Shakeout", "Day-After Antidote" | 20–40min, RPE 2-3 |
| endurance_z2 | "Bread & Butter" | 30–90min, HR-capped |
| long_run | "Time on Feet", "Barn Builder" (dress-rehearsal w/ kit checklist) | run/hike rhythm in ALL levels |
| strides | "Quick Feet" | easy run + 4–8×20s |
| hills_powerhike | "Hike the Damn Hill" | run/hike intervals |
| hills_reps | "Hill Medicine" | 6–10×60-90s strong up, walk down |
| tempo_steady | "Steady Finish" | easy + last 10–25min steady |
| race_pace | "Loop One Rehearsal" | n×8min ultra effort, HR-gated |
| downhill_skills | "Brakes Off" | eccentric downhill exposure |
| openers | "Race Eve" | strides/pickups pre-race |
| pickups | "Wake-Up Call" | n×1min RPE 6-7 |
| race_day | "A-Race Brief", "B-Race Brief" | unleveled, description-only |

Names follow the product register: memorable, confident, still obviously a
workout; nothing that needs context on a stranger's calendar.

## Renderer — explicit authority decision (sol finding 3)

Two formatter lineages exist and they are NOT the same:
- Nate renderer (`nate_workout_generator.py` ~L3005): `WARM-UP / MAIN SET /
  COOL-DOWN / PROGRESSION / PURPOSE / EXECUTION / NUTRITION / HYDRATION` — no RPE.
- v6.0 formatter (`generate_athlete_package.py` L382): `STRUCTURE / PURPOSE /
  EXECUTION / RPE` only.

**Decision: the run renderer is the Nate section set PLUS a final `RPE:`
section.** This is a NEW, explicitly-defined contract (`render_run_description`
in `run_archetypes.py` or a small `run_renderer.py`), not "parity" with either
existing formatter. R2 ships golden-file outputs for one archetype per category
(15 golden files); any section-order change breaks the goldens.

Run dimension lines in MAIN SET: `-Cadence: <spm prescription>` and
`-Terrain: <prescription>`. New helpers `_get_default_run_cadence(category_id,
level)` and `_get_default_terrain(category_id, level)` dispatch on
`category_id`. Run nutrition/hydration come from NEW run-specific functions
(`get_run_nutrition`, `get_run_hydration`) keyed on category_id + duration —
the existing bike helpers classify by display-name substrings and are not
touched (sol finding 9). Tier table (aligned with existing bike tiers + ISSN):
<60min → "None needed at this duration."; 60–90min → optional; ≥90min Z2 →
40-60g/hr; dress rehearsal / race → 50-60g/hr; sodium noted >2hr.

## TP structure export (sol finding 4 — full contract)

`athletes/scripts/run_structure_export.py`: Format R → TP structure JSON.

- `rpe: [lo, hi]` → step `targets: [{minValue: lo, maxValue: hi}]` with
  `primaryIntensityMetric: "rpe"`, `primaryLengthMetric: "duration"`,
  `primaryIntensityTargetOrRange: "range"`, `polyline: []`.
- `repeat` blocks UNROLL into flat steps with cumulative `begin`/`end` seconds
  (TP API convention, proven live).
- `hr_pct_lthr` / `pace_pct_threshold` are NOT emitted as targets in v1 — prose
  only.
- Run workout type: `workoutTypeValueId: 3` (walk = 13). Race-day briefs:
  no `structure` field.
- **Fixture (R3):** commit `tests/fixtures/tp_run_structure_fixture.json` — an
  anonymized copy of a live-accepted payload from the 2026-07-20 Anthony builds
  (athleteId scrubbed). Round-trip test: export → compare to fixture shape →
  every step has targets, begin/end monotone, total seconds == level duration.
  This makes the "TP accepts this" claim reproducible from the repo.

## rTSS estimation (sol finding 8 — complete algorithm)

`tss = Σ over segments (segment_hours × IF² × 100)`, then rounded; stored in
YAML, never computed at runtime. Complete RPE→IF lookup (contiguous, no gaps):

| RPE band | IF |
|---|---|
| 1-2 | 0.55 |
| 2-3 | 0.62 |
| 3-4 | 0.70 |
| 4-5 | 0.78 |
| 5-6 | 0.83 |
| 6-7 | 0.88 |
| 7-8 | 0.93 |
| 8-9 | 1.00 |
| 9-10 | 1.05 |

A segment's band = its `rpe: [lo, hi]` pair; mixed bands like `[3,5]` are
disallowed by validation (must match a table row). Race briefs carry a
hand-set `tss` per brief. Validation test: stored `tss` within ±15% of the
formula for every leveled item. (Sanity: 60min @ IF 0.70 = 49 TSS.)

## Selection: dual-sport weekly template (coach directive, Jul 2026)

`athletes/config/dual_sport_week.yaml` + `athletes/scripts/dual_sport_selector.py`
— the ONLY selection logic in v1 (no methodology matrix).

- **Mon** rest — **Tue** run WORKOUT slot — **Wed** OPTIONAL run
  (recovery_easy/endurance_z2, `OPTIONAL:` title prefix, capped at ≤ the
  duration a Monday easy run would have had, ≤40min — sol B finding 1) —
  **Fri** bike (existing GG libraries) — **Sat** long_run or race — **Sun**
  athlete's own / Sunday-race overlay.
- Tue slot by phase: Base → strides/hills_powerhike; Build →
  tempo_steady/hills_reps; Peak → race_pace; Race-week → openers; A-race week
  Wed optional capped at 20min.
- **Post-race rule (selector-ENFORCED, not just prose — sol finding 6):** the
  selector never schedules a Tue workout containing intensity (any segment RPE
  ≥5) within 2 calendar days after a race, and the first run after ANY race
  (party-pace included) is recovery_easy/endurance_z2 with the stairs-test gate
  line in EXECUTION. Calendar-day granularity is acknowledged: 2 calendar days
  approximates the 48h intent; Sunday races therefore make Tuesday gated-easy.
- Race overlays follow the existing B-race pattern (overlay, not override).

## Compliance — separate run gate, explicit composability (sol finding 5)

The dual-sport template is an **overlay for the coached-athlete path**; it is
NOT fed through `block_compliance.py`, whose 11 CRITICAL rules are
cycling-plan invariants (long RIDE weekly, cycling-hours fit, etc.) and would
fail by construction on a dual-sport week. New `athletes/scripts/run_compliance.py`
validates run items + cross-sport adjacency only:

- R-C1 no run-intensity (segment RPE ≥5) within 2 calendar days after any race
  (bike or run) — enforced by the selector, verified by the gate.
- R-C2 long run present every non-race load week.
- R-C3 NUTRITION section present on every run ≥90min.
- R-C4 weekly REQUIRED run hours within ±10% of template; `OPTIONAL:` items are
  EXCLUDED from the floor and count only toward a weekly max cap (template
  hours + 45min) — resolves the optional-run paradox (sol finding 6).
- R-C5 optional items never contain a segment with RPE ≥5.
- R-C6 long-run level/duration may not jump >1 level between consecutive long
  runs.

**Failure behavior (sol finding 7):** the coached-athlete path hard-fails
(raise, no delivery) — no `GG_STRICT_COMPLIANCE` dependency; that env-gated
flagged-delivery behavior belongs to the self-serve path in
`generate_athlete_package.py` (L654-669) and is out of scope here. The raise
lives in the CALLER (dispatch script), outside any try/except around the
builder — same placement discipline as the self-serve gate (which lives in
`generate_athlete_package.py`, not `block_compliance.py`).

## TP library build

`athletes/scripts/build_run_tp_library.py` builds "GG Run | Workouts" folder(s)
via the exerciselibrary API (2026 bike-curation recipe; rx-invisibility rule).
Item names: `Run <Category> - <Display Name> - <level> - <min>min - RPE<band>`
(bike lib convention with a `Run` prefix). Library items contain NO absolute
BPM (generic text; BPM only at athlete placement). Placement uses items
verbatim (Anthony round-3 pattern).

## Tickets (sol finding 11 — paths, deps, safety)

- **R1** `run_workout_library.yaml` + `run_archetypes.py` (loader/registry/
  validation) — 13 leveled archetypes × 6 + 2 race briefs = 80 items; schema
  validation tests (ID format, sport/category present, band table membership,
  level keys normalize).
- **R2** run renderer (`run_renderer.py`) + run helpers — 15 golden-file
  description tests (one per archetype).
- **R3** `run_structure_export.py` + committed anonymized fixture
  `tests/fixtures/tp_run_structure_fixture.json` + round-trip tests.
- **R4** rTSS validation — every stored `tss` within ±15% of formula.
- **R5** `dual_sport_week.yaml` + `dual_sport_selector.py` (phase mapping,
  race overlays, post-race rule, optional caps) + tests. Emits a typed
  week-plan interface consumed by R6.
- **R6** `run_compliance.py` (R-C1..R-C6) + negative-case tests. DEPENDS on
  R5's week-plan interface — not parallel with R5.
- **R7** `build_run_tp_library.py` + reconcile check. DEPENDS on R3 (structure
  export), not merely R2.
- **R8** docs: CLAUDE.md section + pitfalls (schema normalization, no
  name-substring dispatch for runs, BPM-at-placement rule).
- **R9** pilot: regenerate Anthony's remaining weeks from the library; diff vs
  hand-authored; **idempotent upsert with pre-change snapshot (full JSON
  receipt), read-back verification, and documented rollback (receipt replay)**;
  Matti reviews the diff before any calendar overwrite. LTHR-absent fallback
  exercised in tests.

Build order: R1 → R2 → R3 → R4; R5 → R6; R7 after R3; R8 rolling; R9 last.
Every ticket sol-reviewed per global rule; codex executes.

## Research anchors

- Koop, *Training Essentials for Ultrarunning* — RPE-primary prescription on
  trail; power-hiking as trained skill; race-pace = "all-day effort".
- Daniels — strides/leg-speed maintenance at low cost.
- IOC load-management consensus (BJSM 2016) — ramp constraints → R-C6.
- ISSN ultra-endurance position stand (2019) — 30-50g/hr baseline, trained-gut
  upside; aligns with existing tiers (40-60/50-60).
- Masters recovery literature (mixed) — individual response overrides age rules;
  encoded as stairs-test gates + selector rule, not blanket volume cuts.
- Internal: `nate_workout_generator.py` (renderer lineage),
  `generate_athlete_package.py` L382 (v6.0 formatter) + L654-669 (gate
  placement + strict-env behavior), `archetype_registry.py` (registry pattern),
  `workout_library.yaml` (schema conventions), tp-plan-build-automation +
  Anthony receipts (TP API truth).

## sol review trail

v1 → NO-GO (5 blockers, 6 majors): invalid YAML example + wrong archetype
count; mixed schemas; contradictory renderer authority; underspecified TP
export; non-composable compliance; R-C1/R-C4 contradiction; wrong gate-placement
attribution; incomplete rTSS algorithm; name-substring helper hazard; missing
sport namespace; missing integration/safety tickets. All folded above.
Calendar-reshape companion review: GO with post-race-Tuesday gating conditions
(applied to Anthony's live calendar 2026-07-20).
