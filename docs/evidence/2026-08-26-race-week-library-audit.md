# Race-week / taper library audit — AE-1.12 caps vs. AE-1.17 touches

**Generated:** 2026-08-26 against `athletes/config/tp_library_index.json.gz`
(1458 selectable items, 24 libraries), queried live via
`tp_library_snapshot.load_index()` — see Method for the exact eligible set
(523 of 1458 selectable curated items).

**Status: REPORT ONLY.** Nothing in this document has been applied to the
coach's TrainingPeaks library, to the index, or to any selection/generator
code. Matti reviews and dispositions each row below; archive-never-delete
rules apply to any violator he decides to retire.

**Context (Matti, 2026-08-26, ratifying AE-1.17):** "if you look at my
workout library, I almost certainly violate the taper intensity rules
there." This audit tests that claim against the actual curated content and
the actual selection-layer code, item by item.

## The two caps under test (AE-1.12, ratified)

- No single ≥92%-FTP rep longer than **120 s** (a ramp's crossing of 92%
  counts by its **excursion time above 92%**, not the ramp's average power
  or its full duration).
- No more than **900 s (15 min) total** ≥92%-FTP work in one session.

AE-1.17 (ratified tonight) legalizes short-burst **touches** inside these
caps for race week specifically — the caps bind BLOCKS (sustained hard
work), never a 20/30/40s-style sharpener.

## Method

**Eligible set.** "Every curated library workout Motoren can route into
taper/race weeks" is derived from the actual routing code, not guessed:

- **Taper** (`workout_selection.yaml` `racing` phase, weeks_to_race \<4):
  `intensity_1` → "Openers" (synthetic, no curated item); `intensity_2` →
  "Threshold Touch" (conditional, \>2 weeks out) → routes to
  `threshold_intervals`, `threshold_sustained`, `threshold_floats_ou`
  (`library_selector.ROUTING_TABLE`); `long_ride` → "Endurance" (reduced
  duration, L2-3) → routes to `endurance_z2_short`/`endurance_z2_long`,
  `endurance_with_work`, `skills` (`_endurance_library_keys`); `filler` →
  "Rest Day" (synthetic).
- **Race week** (`block_builder._build_race_week`, a distinct `week_type`
  from taper): the sharpener day is always "Stars In Your Eyes"
  (role=`intensity`) → routes to `anaerobic_capacity` (+ `sprint_attacks`
  when `race_demands` is set); the mid-week easy day is "Endurance" L1
  (role=`filler`, 50min) → same endurance/skills libraries as taper's
  long_ride; plus "Openers" and "Rest Day" (both synthetic).

Union of those library_keys: `anaerobic_capacity`, `sprint_attacks`,
`threshold_intervals`, `threshold_sustained`, `threshold_floats_ou`,
`endurance_z2_short`, `endurance_z2_long`, `endurance_with_work`, `skills`
— **523 of 1458** selectable curated items. Routing in this codebase is not
gated by item name, only by `library_key` + duration fit + the ceilings
below, so every item in these 9 libraries is a genuine candidate, not just
the ones whose names suggest a taper role.

**Per-item computation.** For every eligible item's TP `structure`, walked
with the same corpus-verified block/leaf logic `tp_structure_to_zwo._build`
uses (so warmUp/coolDown ramps, on/off `IntervalsT` pairs, and flat
active/rest steady blocks are all classified exactly as they'd render):

- A flat (steady or interval on/off) leaf whose target is ≥92% counts its
  **full leaf duration** as one rep.
- A warmUp/coolDown **ramp** whose peak crosses 92% counts only the
  **excursion time above 92%** (linear interpolation across the ramp), per
  AE-1.12's explicit ramp rule — not the full ramp duration.
- RPE-metric items (`primaryIntensityMetric: rpe`) are decoded through the
  same `_RPE_TO_PCT_FTP` table the renderer uses before the 92% comparison
  (RPE 8–10 → 95–130% FTP), except the two authored assessment items and
  any leaf marked no-power/leg-speed, which ship unstructured and carry no
  %FTP claim to test.
- Classification: **CAP-VIOLATION** (worst rep \>120s OR total \>900s),
  **CLEAN-TOUCH** (≥92% content present, every rep ≤120s, total ≤900s —
  the AE-1.17-blessed class), **NO-92** (no ≥92% content at all).

**Selection-layer cross-check.** For every item, also ran the ACTUAL
production functions `library_selector._max_hard_rep_seconds` and
`_hard_work_seconds` — the same code `_passes_role_ceiling` calls whenever
`slot.week_type in ("taper", "race")` — to test whether today's selection
code would already reject the item from a taper/race slot, independent of
this audit's own (more careful, RPE-aware, ramp-excursion-aware) numbers.

## Summary

| Class | Count |
|---|---|
| CLEAN-TOUCH (≥92% present, AE-1.17-legal) | 157 |
| CAP-VIOLATION | 165 |
| NO-92 (no ≥92% content) | 200 |
| NO-92, unstructured/RPE-exempt (assessment-shaped) | 1 |
| **Total eligible** | **523** |

Violations by library: {'anaerobic_capacity': 9, 'endurance_with_work': 1, 'endurance_z2_long': 1, 'endurance_z2_short': 5, 'skills': 15, 'sprint_attacks': 6, 'threshold_floats_ou': 10, 'threshold_intervals': 64, 'threshold_sustained': 54}

**Of the 165 CAP-VIOLATION items, 163 are already
blocked from ever reaching a taper/race slot by the existing selection-layer
ceiling** (`library_selector._passes_role_ceiling`, gated on
`_TAPER_GATED_WEEK_TYPES = ("taper", "race")`, `_TAPER_MAX_HARD_REP_SECONDS
= 120`, `_TAPER_HARD_WORK_SECONDS = 900`). Matti's instinct was right about
the *library content* (most of it is far over these caps — full 20–49min
sustained-threshold sessions sit in the same libraries the taper/race slots
query) but the *selection layer already built the guard* he was worried was
missing: none of those 163 items
can currently land on an athlete's taper/race calendar. Only
**2 items** are a genuine live gap — see below.

## "Stars in your eyes" — the blessed exemplar (Matti, AE-1.17)

**14355544 — "Stars in your eyes - 20/30/40"** (`anaerobic_capacity`, 62min,
ref level): **CLEAN-TOUCH**. Worst rep 40s, total ≥92% work 420s (7min).
This is the item AE-1.17 was ratified to legalize, and it is fully
compliant with the AE-1.12 caps as authored — no code or content change
needed. It is the item `block_builder._build_race_week`'s sharpener day
resolves to whenever the pool preference favors it.

**14355561 — "Stars In Your Eyes - 2"** (`anaerobic_capacity`, 78min,
explicit level 2) is a **different name_base family** (not grouped with the
20/30/40 item on the family ladder) that IS a CAP-VIOLATION: three unlabeled
180s reps at ~104% FTP (worst rep 180s \>120s cap), total 840s. This is the
exact item `library_selector.py`'s own code comments (lines 568–575)
already document as the motivating case for adding `"race"` to
`_TAPER_GATED_WEEK_TYPES` — and the guard now correctly blocks it (`sel_max
= 180.0 > 120`). Non-issue for routing; flagged here only so the coach has
the full family picture next to the exemplar.

## The live gap: RPE-metric items bypass the ceiling entirely

`library_selector._max_hard_rep_seconds` and `_hard_work_seconds` compare a
structure leaf's raw target `minValue`/`maxValue` against the 92.0 floor.
For a `percentOfFtp`-metric item that's correct (targets are already %FTP
points). For an **`rpe`-metric item, the raw target is a 1–10 RPE integer**
— it can never reach 92, so these two functions silently read 0s of hard
work and 0s worst-rep for ANY RPE-metric item, no matter how hard it
actually is. This mirrors the exact defect AE-9c already fixed in the
renderer (`tp_structure_to_zwo._RPE_TO_PCT_FTP`) and in
`_has_ae_3_14_violation` (which explicitly skips RPE-metric structures
rather than mis-reading them) — but `_passes_role_ceiling`'s taper/race gate
was never given the same fix.

Two real items are caught by this gap, both filed in the `skills` library
(eligible for taper/race Endurance long_ride/filler slots):

- **14416937 — "Power Test (12min)"**: RPE-metric, one 720s (12min) ALL-OUT
  leaf, decodes to ~112.5% FTP. Selector reads `sel_max=0.0, sel_total=0.0`
  — would NOT be rejected by today's ceiling.
- **14416939 — "Power Test (3min)"**: RPE-metric, one 180s ALL-OUT leaf,
  same ~112.5% decode. Same gap.

(Their sibling `percentOfFtp`-metric items — 14416938 "Power Test (20min)"
and 14416940 "Power Test (5min)" — carry the identical ALL-OUT-test shape
but ARE correctly caught, because their targets are already raw %FTP
numbers ≥92.)

**Disposition proposal:** these are genuine max-effort TEST protocols
(warmup → progressively-hard build → named-duration ALL-OUT → recovery),
not endurance filler content, sitting in the general-purpose `skills`
library that taper AND race week both draw Endurance long_ride/filler
candidates from. Two independent fixes close this, either is sufficient,
Matti's call:
1. Fix `_max_hard_rep_seconds`/`_hard_work_seconds` to decode RPE through
   `_RPE_TO_PCT_FTP` before the 92% comparison (parity with the renderer and
   with `_has_ae_3_14_violation`), or
2. Exclude the four "Power Test" items (and similarly-shaped test-named
   items) from filler/long_ride routing altogether — the same treatment
   `PINNED_TEST_ITEM_IDS`/`ASSESSMENT_ITEM_IDS` already give "FTP Test" and
   "Anaerobic Test".

Fix (1) is the more durable one: it closes the gap for any future RPE-metric
item added to an eligible library, not just these four.

## "Threshold Touch" — the family the taper matrix names, but can never place

`workout_selection.yaml`'s `racing` phase (taper) `intensity_2` slot says:
*"Maybe Threshold Touch L1-2 if \>2 weeks out."* All **6** curated items
literally named "Threshold Touch" (levels 1–6, ids 14357136–14357141) are
**CAP-VIOLATION** — including **Level 1** (worst rep 300s/5min, well over
the 120s cap) and **Level 2** (worst rep 300s). Every level is guarded
(`sel_would_reject=True` for all 6), so no ship risk — but the practical
effect is that the taper matrix's own named intent can **never** resolve to
itself: `_qualifying_pool` queries the whole `threshold_intervals` /
`threshold_sustained` / `threshold_floats_ou` pool (154 items, not just
"Threshold Touch"-named ones), finds 23 CLEAN-TOUCH cousins (mostly 30/30
over/under and short-progression items), and silently substitutes one of
those instead. That's arguably fine behavior (the athlete still gets a
compliant touch), but it means "Threshold Touch" as authored content is
dead weight for the one slot named after it.

**Disposition proposal: (b) needs a taper-safe variant.** A genuine
short-touch "Threshold Touch" (≤120s reps, e.g. 30/30s in the 88–98% band)
would let the slot's own name mean what it says instead of relying on an
unrelated family to cover for it.

## Other named items worth flagging

- **14355829/830/831 — "Dark is the Night"** (`endurance_z2_short`, levels
  1–3): CAP-VIOLATION (worst rep 480s/8min, well over cap) — already
  guarded. This is the same item `library_selector.py`'s own comments (line
  582) cite as the motivating case for the separate BASE-phase long-ride
  ceiling (`_BASE_LONG_RIDE_MAX_HARD_REP_SECONDS`); it shows up here too
  because it's also `endurance_z2_short`, one of the taper/race eligible
  libraries.
- **14356002 — "Structured Fartlek"** (`endurance_with_work`):
  CAP-VIOLATION, but also independently excluded from EVERY selection pool
  (not just taper/race) by the AE-3.11 name purge
  (`library_selector._PURGED_CONCEPT_NAMES` matches "fartlek"). Doubly
  guarded; no action needed here specifically, flagged only for
  completeness.
- **14416932–36 — "FTP Test"** (`skills`, `percentOfFtp`-metric): the same
  test-in-`skills` shape as "Power Test" above, but caught correctly by the
  ceiling (targets are raw %FTP ≥92, e.g. 1200s/20min ALL-OUT). Grouped
  here as the same class of content-tagging issue — test protocols filed in
  the general endurance/skills pool — even though the intensity cap happens
  to save these five.

## Full violation table (165 rows)

Sorted by library, then worst rep length descending. Disposition key: **(a)**
fine outside taper, guard already blocks it, no content change — **(b)**
needs a taper-safe variant — **(a-DEFECT)** selection-layer gap, guard does
NOT block it today.

| item_id | library | name | metric | worst rep (s) | total ≥92% (s) | dur (min) | selection guard | disposition |
|---|---|---|---|---|---|---|---|---|
| 14355540 | anaerobic_capacity | FRC Intensives | percentoffp | 180 | 600 | 145 | BLOCKS | (a) |
| 14355541 | anaerobic_capacity | The Krueger | percentoffp | 180 | 630 | 130 | BLOCKS | (a) |
| 14355561 | anaerobic_capacity | Stars in Your Eyes | percentoffp | 180 | 840 | 78 | BLOCKS | (a) |
| 14355647 | anaerobic_capacity | 2min Killers | percentoffp | 120 | 1260 | 99 | BLOCKS | (a) |
| 14355649 | anaerobic_capacity | 2min Killers | percentoffp | 120 | 1140 | 92 | BLOCKS | (a) |
| 14355650 | anaerobic_capacity | 2min Killers | percentoffp | 120 | 1020 | 85 | BLOCKS | (a) |
| 14355539 | anaerobic_capacity | The Psycho | percentoffp | 60 | 1400 | 90 | BLOCKS | (a) |
| 14355628 | anaerobic_capacity | W-Prime Depletion | percentoffp | 60 | 1140 | 55 | BLOCKS | (a) |
| 14355630 | anaerobic_capacity | W-Prime Depletion | percentoffp | 60 | 1020 | 55 | BLOCKS | (a) |
| 14356002 | endurance_with_work | Structured Fartlek [also AE-3.11-purged by name] | percentoffp | 60 | 960 | 60 | BLOCKS | (a) |
| 14355845 | endurance_z2_long | Delayed Sorrow | percentoffp | 1200 | 1200 | 240 | BLOCKS | (a) |
| 14355829 | endurance_z2_short | Dark is the Night | percentoffp | 480 | 1920 | 90 | BLOCKS | (a) |
| 14355830 | endurance_z2_short | Dark is the Night | percentoffp | 480 | 2880 | 112 | BLOCKS | (a) |
| 14355831 | endurance_z2_short | Dark is the Night | percentoffp | 480 | 4020 | 137 | BLOCKS | (a) |
| 14355933 | endurance_z2_short | RLP Compressed Endurance - Prep Session V2 | percentoffp | 300 | 300 | 60 | BLOCKS | (a) |
| 14355940 | endurance_z2_short | Steady State | percentoffp | 240 | 1920 | 90 | BLOCKS | (a) |
| 14416932 | skills | FTP Test | percentoffp | 1200 | 1260 | 56 | BLOCKS | (a) |
| 14416933 | skills | FTP Test | percentoffp | 1200 | 1260 | 56 | BLOCKS | (a) |
| 14416934 | skills | FTP Test | percentoffp | 1200 | 1260 | 56 | BLOCKS | (a) |
| 14416935 | skills | FTP Test | percentoffp | 1200 | 1260 | 56 | BLOCKS | (a) |
| 14416936 | skills | FTP Test | percentoffp | 1200 | 1260 | 56 | BLOCKS | (a) |
| 14416938 | skills | Power Test (20min) | percentoffp | 1200 | 1200 | 75 | BLOCKS | (a) |
| 14356278 | skills | Mixed Climbing Variations | percentoffp | 900 | 1275 | 104 | BLOCKS | (a) |
| 14356279 | skills | Mixed Climbing Variations | percentoffp | 900 | 1200 | 84 | BLOCKS | (a) |
| 14356281 | skills | Mixed Climbing Variations | percentoffp | 900 | 1140 | 80 | BLOCKS | (a) |
| 14356282 | skills | Mixed Climbing Variations | percentoffp | 900 | 2205 | 102 | BLOCKS | (a) |
| 14356283 | skills | Mixed Climbing Variations | percentoffp | 900 | 1155 | 80 | BLOCKS | (a) |
| 14416937 | skills | Power Test (12min) | rpe | 720 | 720 | 69 | **GAP — DOES NOT BLOCK** | (a-DEFECT) |
| 14416940 | skills | Power Test (5min) | percentoffp | 300 | 300 | 60 | BLOCKS | (a) |
| 14356232 | skills | CX Race Start Practice, 2 Hot Laps | percentoffp | 240 | 840 | 60 | BLOCKS | (a) |
| 14416939 | skills | Power Test (3min) | rpe | 180 | 180 | 60 | **GAP — DOES NOT BLOCK** | (a-DEFECT) |
| 14355537 | sprint_attacks | Pyramids Buffers Bookend SS | percentoffp | 600 | 1330 | 88 | BLOCKS | (a) |
| 14355603 | sprint_attacks | Bookend Power Intervals [retained 14355603] | percentoffp | 600 | 3600 | 240 | BLOCKS | (a) |
| 14355607 | sprint_attacks | 1 Thing Per Hour – ALL OUT (Z7 TP-Description + TextEvents) | percentoffp | 240 | 540 | 198 | BLOCKS | (a) |
| 14355601 | sprint_attacks | Bookend Power Intervals | percentoffp | 120 | 1440 | 220 | BLOCKS | (a) |
| 14355604 | sprint_attacks | Sunset Loop Over-Unders | percentoffp | 40 | 1200 | 130 | BLOCKS | (a) |
| 14355536 | sprint_attacks | NM: Microbursts and Sprints | percentoffp | 15 | 1000 | 120 | BLOCKS | (a) |
| 14357096 | threshold_floats_ou | 2x20 Over/Under (4/1) | percentoffp | 240 | 1920 | 90 | BLOCKS | (a) |
| 14357108 | threshold_floats_ou | Sunset Loop Over-Unders | percentoffp | 240 | 1440 | 93 | BLOCKS | (a) |
| 14357215 | threshold_floats_ou | Floats 3x4min/3min (1 of 3) | percentoffp | 240 | 720 | 46 | BLOCKS | (a) |
| 14357217 | threshold_floats_ou | Floats 4x4min/3min (2 of 3) | percentoffp | 240 | 960 | 53 | BLOCKS | (a) |
| 14357219 | threshold_floats_ou | Floats 4x4min/2min (3 of 3) | percentoffp | 240 | 960 | 51 | BLOCKS | (a) |
| 14357172 | threshold_floats_ou | Over-Unders | percentoffp | 120 | 1080 | 71 | BLOCKS | (a) |
| 14357174 | threshold_floats_ou | Over-Unders | percentoffp | 120 | 1440 | 83 | BLOCKS | (a) |
| 14357175 | threshold_floats_ou | Over-Unders | percentoffp | 120 | 1440 | 88 | BLOCKS | (a) |
| 14357176 | threshold_floats_ou | Over-Unders | percentoffp | 120 | 1080 | 71 | BLOCKS | (a) |
| 14357088 | threshold_floats_ou | WTF?!…Lactate Clearance: Over-Unders | percentoffp | 60 | 1020 | 73 | BLOCKS | (a) |
| 14357053 | threshold_intervals | Old SKOOL | percentoffp | 1200 | 2400 | 90 | BLOCKS | (a) |
| 14357054 | threshold_intervals | Old SKOOL | percentoffp | 1200 | 3600 | 115 | BLOCKS | (a) |
| 14357126 | threshold_intervals | Capacity LT | percentoffp | 960 | 2160 | 180 | BLOCKS | (a) |
| 14357052 | threshold_intervals | Old SKOOL | percentoffp | 900 | 2700 | 90 | BLOCKS | (a) |
| 14357056 | threshold_intervals | Pie Plate | percentoffp | 900 | 3840 | 118 | BLOCKS | (a) |
| 14357061 | threshold_intervals | Hurtimat | percentoffp | 900 | 1220 | 90 | BLOCKS | (a) |
| 14357064 | threshold_intervals | Hurtimat | percentoffp | 900 | 2000 | 87 | BLOCKS | (a) |
| 14357075 | threshold_intervals | 15/4 TT Efforts (Gila) | percentoffp | 900 | 1140 | 79 | BLOCKS | (a) |
| 14357079 | threshold_intervals | Hurtimat | percentoffp | 900 | 2200 | 97 | BLOCKS | (a) |
| 14357085 | threshold_intervals | TT Yeeet | percentoffp | 900 | 1500 | 120 | BLOCKS | (a) |
| 14357111 | threshold_intervals | Capacity LT (2x20) | percentoffp | 900 | 2040 | 150 | BLOCKS | (a) |
| 14357114 | threshold_intervals | Gila Stage 1 TT Prep | percentoffp | 900 | 2100 | 109 | BLOCKS | (a) |
| 14357119 | threshold_intervals | Mixed Climbs | percentoffp | 900 | 1875 | 75 | BLOCKS | (a) |
| 14357135 | threshold_intervals | Short 2x15 Z4 | percentoffp | 900 | 1800 | 55 | BLOCKS | (a) |
| 14416956 | threshold_intervals | TT Send | percentoffp | 900 | 1500 | 120 | BLOCKS | (a) |
| 14357134 | threshold_intervals | Short 2x13 Z4 | percentoffp | 780 | 1560 | 51 | BLOCKS | (a) |
| 14357080 | threshold_intervals | Gila Stage 1 TT Prep | percentoffp | 720 | 1500 | 97 | BLOCKS | (a) |
| 14357084 | threshold_intervals | TT Yeeet | percentoffp | 720 | 1200 | 120 | BLOCKS | (a) |
| 14416955 | threshold_intervals | TT Send | percentoffp | 720 | 1200 | 120 | BLOCKS | (a) |
| 14357107 | threshold_intervals | Rhythm Change / LT Mix (3x12') | percentoffp | 690 | 720 | 90 | BLOCKS | (a) |
| 14357044 | threshold_intervals | Space Jams - LT Up | percentoffp | 600 | 3240 | 132 | BLOCKS | (a) |
| 14357045 | threshold_intervals | FTP - Thresh Reaper | percentoffp | 600 | 1800 | 125 | BLOCKS | (a) |
| 14357046 | threshold_intervals | Apertif | percentoffp | 600 | 1200 | 86 | BLOCKS | (a) |
| 14357055 | threshold_intervals | Pie Plate | percentoffp | 600 | 2640 | 98 | BLOCKS | (a) |
| 14357065 | threshold_intervals | Short 2x10 Z4 | percentoffp | 600 | 1200 | 45 | BLOCKS | (a) |
| 14357066 | threshold_intervals | TT: LT Cutdown (8/6/4/2) | percentoffp | 600 | 1680 | 90 | BLOCKS | (a) |
| 14357083 | threshold_intervals | TT Yeeet | percentoffp | 600 | 900 | 90 | BLOCKS | (a) |
| 14357129 | threshold_intervals | Red Carpet | percentoffp | 600 | 2880 | 107 | BLOCKS | (a) |
| 14416954 | threshold_intervals | TT Send | percentoffp | 600 | 900 | 90 | BLOCKS | (a) |
| 14357095 | threshold_intervals | Aerobic Load Sprints + LT Builder (3x8) | percentoffp | 480 | 1440 | 150 | BLOCKS | (a) |
| 14357097 | threshold_intervals | 3x8 LT Push Climbs | percentoffp | 480 | 1440 | 90 | BLOCKS | (a) |
| 14357113 | threshold_intervals | TT: LT Cutdown (8/6/4/2) - 10/20/10 LT pyramid climbs | percentoffp | 480 | 1200 | 62 | BLOCKS | (a) |
| 14357120 | threshold_intervals | Supra Threshold 2 Sets | percentoffp | 480 | 2880 | 122 | BLOCKS | (a) |
| 14357124 | threshold_intervals | Rhythm Change Tempo + PoP + 8min Z4 climb | percentoffp | 480 | 620 | 90 | BLOCKS | (a) |
| 14357137 | threshold_intervals | Threshold Touch | percentoffp | 480 | 1440 | 58 | BLOCKS | (b) |
| 14357131 | threshold_intervals | Block Training 5x6min (Threshold Range %FTP) | percentoffp | 360 | 1800 | 73 | BLOCKS | (a) |
| 14357136 | threshold_intervals | Threshold Touch | percentoffp | 360 | 1080 | 52 | BLOCKS | (b) |
| 14357138 | threshold_intervals | Threshold Touch | percentoffp | 360 | 720 | 45 | BLOCKS | (b) |
| 14357059 | threshold_intervals | Fish and Chips | percentoffp | 300 | 3000 | 100 | BLOCKS | (a) |
| 14357060 | threshold_intervals | Fish and Chips | percentoffp | 300 | 4500 | 120 | BLOCKS | (a) |
| 14357086 | threshold_intervals | TT Yeeet | percentoffp | 300 | 720 | 120 | BLOCKS | (a) |
| 14357094 | threshold_intervals | Rhythm Change + VO2 wake up | percentoffp | 300 | 840 | 90 | BLOCKS | (a) |
| 14357139 | threshold_intervals | Threshold Touch | percentoffp | 300 | 600 | 43 | BLOCKS | (b) |
| 14357140 | threshold_intervals | Threshold Touch | percentoffp | 300 | 300 | 30 | BLOCKS | (b) |
| 14357141 | threshold_intervals | Threshold Touch | percentoffp | 300 | 900 | 49 | BLOCKS | (b) |
| 14416957 | threshold_intervals | TT Send | percentoffp | 300 | 720 | 120 | BLOCKS | (a) |
| 14357070 | threshold_intervals | Pro Ardennes | percentoffp | 250 | 1250 | 360 | BLOCKS | (a) |
| 14357043 | threshold_intervals | 1:15: 1x20 + 4x6 + 4x4 | percentoffp | 240 | 960 | 157 | BLOCKS | (a) |
| 14357050 | threshold_intervals | TT: 6/4/90 (2x) | percentoffp | 240 | 750 | 72 | BLOCKS | (a) |
| 14357051 | threshold_intervals | TT: Strength/LT/Strength Sandwich (2x12') + 4x90 supra LT | percentoffp | 240 | 840 | 64 | BLOCKS | (a) |
| 14357062 | threshold_intervals | TT Sim | percentoffp | 240 | 1920 | 90 | BLOCKS | (a) |
| 14357068 | threshold_intervals | TT2: Duration in Position (3/2) + Maximal | percentoffp | 240 | 1680 | 78 | BLOCKS | (a) |
| 14357076 | threshold_intervals | 3x6+3x4+3x90 | percentoffp | 240 | 990 | 87 | BLOCKS | (a) |
| 14357115 | threshold_intervals | to Vo2 Ramps | percentoffp | 240 | 1260 | 64 | BLOCKS | (a) |
| 14357116 | threshold_intervals | Bridging the Gap | percentoffp | 240 | 1500 | 65 | BLOCKS | (a) |
| 14357117 | threshold_intervals | Strong Finish | percentoffp | 240 | 1500 | 70 | BLOCKS | (a) |
| 14357058 | threshold_intervals | Fish and Chips | percentoffp | 180 | 2700 | 90 | BLOCKS | (a) |
| 14357067 | threshold_intervals | TT1: Duration in Position (3/2) | percentoffp | 180 | 1440 | 81 | BLOCKS | (a) |
| 14357090 | threshold_intervals | Accel<Tempo<LT (3x20') | percentoffp | 180 | 840 | 150 | BLOCKS | (a) |
| 14357099 | threshold_intervals | Pre-Load Z3-Z4 | percentoffp | 180 | 720 | 120 | BLOCKS | (a) |
| 14357127 | threshold_intervals | Red Carpet | percentoffp | 180 | 1080 | 102 | BLOCKS | (a) |
| 14357128 | threshold_intervals | Red Carpet | percentoffp | 180 | 1440 | 126 | BLOCKS | (a) |
| 14357130 | threshold_intervals | Red Carpet - 0 | percentoffp | 180 | 720 | 83 | BLOCKS | (a) |
| 14357106 | threshold_intervals | TT: Broken LT | percentoffp | 120 | 1800 | 90 | BLOCKS | (a) |
| 14357218 | threshold_sustained | Sustained Threshold 49min (3 of 3) | percentoffp | 2940 | 2940 | 79 | BLOCKS | (a) |
| 14357188 | threshold_sustained | Single Sustained Threshold | percentoffp | 2700 | 2790 | 67 | BLOCKS | (a) |
| 14357216 | threshold_sustained | Sustained Threshold 43min (2 of 3) | percentoffp | 2580 | 2580 | 73 | BLOCKS | (a) |
| 14357189 | threshold_sustained | Single Sustained Threshold | percentoffp | 2400 | 2490 | 62 | BLOCKS | (a) |
| 14357190 | threshold_sustained | Single Sustained Threshold | percentoffp | 2100 | 2190 | 57 | BLOCKS | (a) |
| 14357214 | threshold_sustained | Sustained Threshold 35min (1 of 3) | percentoffp | 2100 | 2100 | 65 | BLOCKS | (a) |
| 14357191 | threshold_sustained | Single Sustained Threshold | percentoffp | 1800 | 1890 | 52 | BLOCKS | (a) |
| 14357179 | threshold_sustained | Kolie Moore TTE | percentoffp | 1500 | 3000 | 85 | BLOCKS | (a) |
| 14357192 | threshold_sustained | Single Sustained Threshold | percentoffp | 1500 | 1590 | 47 | BLOCKS | (a) |
| 14357180 | threshold_sustained | Kolie Moore TTE | percentoffp | 1320 | 2640 | 79 | BLOCKS | (a) |
| 14357173 | threshold_sustained | 03_KolieMoore_Threshold_TTE | percentoffp | 1200 | 2400 | 75 | BLOCKS | (a) |
| 14357178 | threshold_sustained | Kolie Moore TTE | percentoffp | 1200 | 3600 | 105 | BLOCKS | (a) |
| 14357182 | threshold_sustained | Accumulation | percentoffp | 1200 | 3690 | 97 | BLOCKS | (a) |
| 14357193 | threshold_sustained | Single Sustained Threshold | percentoffp | 1200 | 1290 | 42 | BLOCKS | (a) |
| 14416953 | threshold_sustained | Kolie Moore TTE | percentoffp | 1200 | 2400 | 75 | BLOCKS | (a) |
| 14357181 | threshold_sustained | Kolie Moore TTE | percentoffp | 1080 | 2160 | 71 | BLOCKS | (a) |
| 14357183 | threshold_sustained | Accumulation | percentoffp | 1080 | 3330 | 91 | BLOCKS | (a) |
| 14357184 | threshold_sustained | Accumulation | percentoffp | 960 | 2970 | 85 | BLOCKS | (a) |
| 14357143 | threshold_sustained | Threshold Progressive | percentoffp | 900 | 4800 | 110 | BLOCKS | (a) |
| 14357144 | threshold_sustained | Threshold Progressive | percentoffp | 900 | 1800 | 55 | BLOCKS | (a) |
| 14357146 | threshold_sustained | Threshold Progressive | percentoffp | 900 | 3600 | 90 | BLOCKS | (a) |
| 14357147 | threshold_sustained | Threshold Progressive | percentoffp | 900 | 3000 | 80 | BLOCKS | (a) |
| 14357149 | threshold_sustained | Steady | percentoffp | 900 | 2700 | 79 | BLOCKS | (a) |
| 14357164 | threshold_sustained | Week 4 - Threshold Steady (2×15min) | percentoffp | 900 | 1800 | 60 | BLOCKS | (a) |
| 14357185 | threshold_sustained | Accumulation | percentoffp | 840 | 2610 | 79 | BLOCKS | (a) |
| 14357142 | threshold_sustained | Threshold Progressive | percentoffp | 720 | 1440 | 49 | BLOCKS | (a) |
| 14357148 | threshold_sustained | Steady | percentoffp | 720 | 2160 | 70 | BLOCKS | (a) |
| 14357150 | threshold_sustained | Steady | percentoffp | 720 | 2880 | 85 | BLOCKS | (a) |
| 14357152 | threshold_sustained | Steady | percentoffp | 720 | 2160 | 73 | BLOCKS | (a) |
| 14357165 | threshold_sustained | Week 3 - Threshold Steady (3×12min) | percentoffp | 720 | 2160 | 71 | BLOCKS | (a) |
| 14357186 | threshold_sustained | Accumulation | percentoffp | 720 | 2250 | 73 | BLOCKS | (a) |
| 14357200 | threshold_sustained | Descending Threshold | percentoffp | 720 | 2970 | 79 | BLOCKS | (a) |
| 14357166 | threshold_sustained | Week 2 - Threshold Steady (3×11min) | percentoffp | 660 | 1980 | 68 | BLOCKS | (a) |
| 14357201 | threshold_sustained | Descending Threshold | percentoffp | 660 | 2730 | 75 | BLOCKS | (a) |
| 14357145 | threshold_sustained | Threshold Progressive | percentoffp | 600 | 1200 | 45 | BLOCKS | (a) |
| 14357151 | threshold_sustained | Steady | percentoffp | 600 | 1200 | 55 | BLOCKS | (a) |
| 14357153 | threshold_sustained | Steady | percentoffp | 600 | 1800 | 67 | BLOCKS | (a) |
| 14357160 | threshold_sustained | Week 4 - Threshold Progressive (2×20min) | percentoffp | 600 | 2400 | 70 | BLOCKS | (a) |
| 14357167 | threshold_sustained | Week 1 - Threshold Steady (3×10min) | percentoffp | 600 | 1800 | 65 | BLOCKS | (a) |
| 14357187 | threshold_sustained | Accumulation | percentoffp | 600 | 1890 | 67 | BLOCKS | (a) |
| 14357202 | threshold_sustained | Descending Threshold | percentoffp | 600 | 2490 | 71 | BLOCKS | (a) |
| 14357203 | threshold_sustained | Descending Threshold | percentoffp | 540 | 2250 | 67 | BLOCKS | (a) |
| 14357204 | threshold_sustained | Descending Threshold | percentoffp | 480 | 2010 | 63 | BLOCKS | (a) |
| 14357205 | threshold_sustained | Descending Threshold | percentoffp | 420 | 1770 | 59 | BLOCKS | (a) |
| 14357157 | threshold_sustained | Accumulation | percentoffp | 210 | 2520 | 79 | BLOCKS | (a) |
| 14357159 | threshold_sustained | Accumulation | percentoffp | 210 | 3150 | 89 | BLOCKS | (a) |
| 14357154 | threshold_sustained | Accumulation | percentoffp | 180 | 2700 | 81 | BLOCKS | (a) |
| 14357155 | threshold_sustained | Accumulation | percentoffp | 180 | 1800 | 65 | BLOCKS | (a) |
| 14357156 | threshold_sustained | Accumulation | percentoffp | 180 | 2160 | 73 | BLOCKS | (a) |
| 14357158 | threshold_sustained | Accumulation | percentoffp | 180 | 1440 | 57 | BLOCKS | (a) |
| 14357168 | threshold_sustained | Week 4 - Threshold Accumulation (15×3min) | percentoffp | 180 | 2700 | 85 | BLOCKS | (a) |
| 14357169 | threshold_sustained | Week 3 - Threshold Accumulation (14×3min) | percentoffp | 180 | 2520 | 81 | BLOCKS | (a) |
| 14357170 | threshold_sustained | Week 2 - Threshold Accumulation (13×3min) | percentoffp | 180 | 2340 | 77 | BLOCKS | (a) |
| 14357171 | threshold_sustained | Week 1 - Threshold Accumulation (12×3min) | percentoffp | 180 | 2160 | 73 | BLOCKS | (a) |

## Cross-check answer (item 4)

**Yes, for 163/165
violators** — `library_selector._passes_role_ceiling` already applies the
identical AE-1.12 caps (120s/900s) to every slot where `week_type in
("taper", "race")`, regardless of role, and it is actually wired into the
pool-filtering path (`_qualifying_pool`, called from both `select()` and
`refit()`). This is not a stale/unused function — it's on the hot path.

**The 2 exceptions** (14416937, 14416939) are a real gap, not a
`(week_type not gated)` miss like the historical "Stars In Your Eyes" case
the code comments describe — they're an RPE-decode gap in the ceiling math
itself. See "The live gap" section above for the fix proposal.

## Questions for Matti

1. For the "Power Test" RPE-decode gap: fix the selector's ceiling math
   (durable, covers future items) or pin/exclude the four Power Test items
   like the two existing test items (faster, narrower)?
2. Is a taper-safe "Threshold Touch" variant (≤120s reps) worth authoring,
   or is silently substituting a cousin threshold item acceptable taper
   behavior as-is?
