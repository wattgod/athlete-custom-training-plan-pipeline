# SPEC v2: Library-first selection (T23 — coach ruled "the harder one", 2026-08-17)

The pipeline stops synthesizing its own archetypes for standard training
sessions and instead SELECTS from the coach's curated TrainingPeaks
libraries (24 "GG |" bike libraries; 1,631 items, 1,593 bike-typed, 1,463
of those with structure). TP curation becomes the single source that
compounds into every custom order.

v2 folds a verified adversarial code review (2026-08-17). All rule IDs,
line references, and data numbers below were checked against the live
code and the real dump.

## Decisions (settled — executors do not relitigate these)

D1. **Selection at the PLANNING boundary.** After the block-builder
    assigns canonical (name, level, duration, role) per day, a resolution
    pass maps each in-scope bike day to a curated item. It writes the
    item's REAL duration/tss onto `day['duration']`/`day['tss']` and
    stashes everything else under a NEW key `day['library_resolution']`
    = {item_id, name_base, explicit_level, library_key, duration_min,
    tss, if_planned}. **`day['name']` and `day['role']` are NEVER
    overwritten** — R02 exact-matches `day['name']` against
    VO2MAX_TYPES (block_compliance.py:150), R08 classifies fuel tiers
    from the canonical name, R04 checks `name != 'Openers'`; curated
    display names would misfire all three. Only the renderer reads
    `library_resolution`.

D2. **Week aggregates are recomputed after resolution.** R19 (hours fit)
    reads `week['total_duration']`; R03 reads `week['total_tss']` — both
    computed once at plan build. The resolution pass ends by recomputing
    both per touched week, exactly as
    `availability_ledger.materialize_fixed_sessions` already does
    (availability_ledger.py:112-117). Ordering: resolution runs AFTER
    `materialize_fixed_sessions` (generate_athlete_package.py:1219) and
    BEFORE the compliance gate call. Without this, curated durations
    drift past R19 exactly as the spec's own rationale warns.

D3. **Curated voice survives — by bypassing the rewrite.**
    `workout_spec.rewrite_zwo_description` unconditionally regenerates
    MAIN SET prose from ZWO blocks (workout_spec.py:196-208; called at
    generate_athlete_package.py:2869/3352/3424). For library-resolved
    sessions that call is SKIPPED: the curated description and structure
    were authored together in TP and are inherently consistent, and the
    coach's description is precisely the dimension layer (cadence,
    position, terrain, drills) that sets these workouts apart. Fuel-tag
    and personal-header prepends still apply.

D4. **Athlete-facing placement is verbatim-curated.** The placed TP card
    for a library-resolved session uses the item's ORIGINAL structure and
    description from the index (keyed by `library_item_id` carried on the
    PlanIR session), not a re-projection. This preserves cadence targets
    (4,538 occurrences, unit roundOrStridePerMinute — a second target on
    power steps) which `project_tp_structure` cannot express. The
    structure→ZWO conversion (C2) is INTERNAL ONLY — it feeds preview,
    TSS calc, and plan_ir; cadence loss there is logged, not fatal.

D5. **Composed stays composed.** Race sims (Act composer), FTP/Anaerobic
    tests (360 protocol), openers/tune-ups, strength, rest days, pre-plan
    week keep the synthetic path. Phase 1 scope = intensity slots, long
    rides, endurance fillers.

D6. **Dimension-richness is a first-class ranking signal** (coach ruling).
    The index scores `dimension_score` per item: count of distinct
    dimension cues in the description (cadence/rpm prescriptions,
    position/posture cues, terrain/surface instructions, drill/technique
    blocks, standing/seated calls) plus presence of cadence targets in
    the structure. Among duration- and level-qualified candidates,
    dimension-rich outranks flat.

D7. **Many good fits, not one** (coach ruling). The selector builds the
    full qualifying pool and rotates via hash(athlete_id, series_key) —
    same intake regenerates byte-identically; different athletes draw
    different, equally good workouts. Repetition is required only inside
    a series.

D8. **Series in the library world**: when the chosen family has depth,
    progress within it (rung = explicit level digit if present, else IF
    rank). 71.5% of families are singletons, so the common case is:
    same library_key, monotone-increasing IF across the series, names
    may change week to week. R14 (series coherence) reads violations
    precomputed at plan build from planner keys (series_tracker via
    block_builder.py:376) and is unaffected. The changing-names feel is
    an intended consequence of the variety ruling — surfaced to the
    coach in the rollout report for veto.

D9. **Fallback is loud.** No qualifying item → synthetic render + a
    LIBRARY FALLBACK line in coaching_brief.md naming the slot. Note the
    compliance gate is NOT a hard stop by default
    (generate_athlete_package.py:1266-1294 writes NEEDS_REVIEW.txt and
    delivers unless GG_STRICT_COMPLIANCE=1) — D1's name-preservation is
    what keeps spurious flags from training the coach to ignore that
    file.

D10. **Kill switch**: `GG_LIBRARY_SELECTION=0` (env or profile) reverts
    entirely to synthetic. Default ON once the Sonja regrade grades A.

## Components

### C1 — Snapshot + normalized index (`athletes/scripts/tp_library_snapshot.py`)
- Input: raw dump (6.1MB, `gg_tp_library_full.json`, pulled from the
  coach's browser session — no TP credentials in repo; refresh is a
  browser-session job). Output: `athletes/config/tp_library_index.json.gz`.
- Per item: {item_id, library_key, name_raw, name_base, explicit_level
  (1-6 or null), duration_min, tss, if_planned (computed from tss/hours
  when missing), rpe_text, dimension_score, has_cadence_targets,
  structure, description, workout_type_id}.
- **Right-anchored name parser** (73% match a naive 4-dash pattern; do
  NOT split on dashes): from the right, strip an optional `RPE...`
  token, then an optional `NNmin`/`NNm` token, then an optional bare
  `ref` or digit 1-6 (capture the digit as explicit_level — 792 items
  carry one vs 483 'ref'), then strip a LEADING category word when it
  matches the library's category vocabulary; the remainder (which may
  itself contain dashes) is name_base. Unparseable names (~4%) fall back
  to name_base = full name and stay selectable as singletons.
- Exclusions logged with counts: non-bike (38), structureless bike
  (130), C2 round-trip failures.
- `--reconcile` compares a fresh raw dump against the index and prints
  drift (build_run_tp_library pattern).

### C2 — Structure→ZWO converter (`athletes/scripts/tp_structure_to_zwo.py`) — INTERNAL ONLY (D4)
- Steps → ZWO: single steps → SteadyState; repetition>1 with work+rest →
  IntervalsT; intensityClass warmUp/coolDown → Warmup/Cooldown ramps;
  openDuration or target-free → FreeRide.
- **Min-only power targets are ~50% of the corpus** (7,523 of 13,295
  power targets): a `{minValue: N}` target renders at Power = N/100.
  Midpoint applies only when both bounds exist.
- Cadence targets: emit ZWO CadenceLow/CadenceHigh attributes (the
  codebase already hand-authors these, workout_mapper.py:86-161); where
  a block type can't carry them, drop and count — the athlete-facing
  card is verbatim-curated (D4) so nothing user-visible is lost.
- Contract test over ALL selectable structures in the real index: total
  seconds exact; every power target within 1 %FTP. Failures excluded
  from the selectable set at index build (logged).

### C3 — Selector (`athletes/scripts/library_selector.py`)
- Routing table canonical-type → library_keys, test-enforced totality
  (every canonical bike type routes or is declared synthetic-only):
  VO2max 30/30 + Thirty-Fifteens → vo2_3030_micro; VO2max 40/20 +
  VO2max Steady Intervals + VO2max Extended → vo2_classic, vo2_blends;
  Threshold Accumulation/Progressive/Steady/Touch → threshold_intervals,
  threshold_sustained; over-under class → threshold_floats_ou; G-Spot →
  sweet_spot_gspot; Tempo* → tempo; SFR → torque_sfr; Stomps →
  torque_stomps; Cadence Work → torque_starts_cadence; Microbursts →
  sprint_attacks; Endurance + focus variants: slot budget < 150min →
  endurance_z2_short + endurance_with_work, >= 150min →
  endurance_z2_long + endurance_with_work; build/peak long-ride
  alternatives also draw durability_long_sims +
  durability_tired_intervals (closes T21); anaerobic_capacity +
  sprint_attacks join intensity rotation when race demands flag it
  (closes T22).
- `select(slot)`: duration fit [0.85 × budget, min(day_cap, 1.15 ×
  budget)]; level 1-6 mapped to explicit_level when the pool has them,
  else IF percentile band; rank by dimension_score desc within the
  qualifying pool; seeded rotation (D7); series per D8; `refit(slot,
  smaller_budget)` API for the week builder's trim step (next-shorter
  in-family/in-library candidate) instead of yaml down-leveling.
- Returns the resolution dict or None.

### C4 — Integration (`generate_athlete_package.py`)
- Resolution pass per D1/D2 (after materialize_fixed_sessions, before
  the compliance gate; exceptions raise — the gate stays OUTSIDE any
  try/except, Jesse Couch rule).
- Render branch: days with `library_resolution` render the C2 ZWO with
  curated name/description, SKIP rewrite_zwo_description (D3), keep
  fuel-tag/header packaging.
- PlanIR session + naming manifest carry `library_item_id`; the payload
  builder places verbatim-curated structure/description for those
  sessions (D4).
- Delivery titles: render_title with name = name_base; dims re-derived
  from emitted structure; the name's own RPE token is ignored.

### C5 — Tests
- Index: parser fixture set spanning the real shapes (4-dash, 5-dash,
  digit-rung, 'ref', bare names like "Just Ride"); family grouping;
  ladder monotonicity; routing totality; reconcile mode.
- Converter: round-trip property over all selectable structures in the
  REAL index (never synthetic fixtures alone); min-only target case;
  cadence attr emission.
- Selector: fit bounds; level mapping both modes; dimension-rich
  outranks flat at equal fit; two seeds diverge when pool >= 3; one
  seed regenerates identically; series monotone; refit shrinks; loud
  fallback.
- Integration: compliance gate green on real generation with resolution
  applied; week totals equal the sum of resolved days; R02/R04/R08
  unaffected (canonical names intact); NEEDS_REVIEW.txt absent.
- End-to-end golden: Sonja intake, library selection ON — all gates
  green, >=60% of in-scope sessions library-resolved, fallback list
  printed, placed payloads for resolved sessions byte-equal to index
  structure/description apart from the packaging prepends.

## Rollout
Wave 1 = C1+C2 (parallel), Wave 2 = C3, Wave 3 = C4 + E2E. Each wave
verified against the real dump / a real Sonja generation before merge.
Then v17 placement on athlete 6571304 and adversarial regrade: grader
verifies placed sessions ARE the curated items (byte-compare) and grades
vs the Monika standard. Loop continues until A.
