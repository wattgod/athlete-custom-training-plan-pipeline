# Master Plan — 12-Week Coherent Periodization

One plan that folds the **trends pack** and the **torque pack** into a single
progression: build force first, convert it to threshold/lactate tolerance, then
sharpen to VO2/peak. Three 4-week blocks (3 build + 1 recovery), ~3 quality sessions
+ endurance + a long ride per week. Each session names the file to load **and** the
warm-up template that suits it (see `WARMUPS.md`).

**Why this order:** torque/strength-endurance has the longest adaptation latency and
the least race-specificity, so it goes in the base; lactate tolerance and TTE bridge;
VO2/anaerobic — the most race-specific and the quickest to peak/fade — go last so they
land sharp on event day. Durability climbs its full ladder *across the whole plan*
(every block has a long fatigued day), because fatigue resistance underpins everything.

Files: trends ladders in `progressions/`, torque ladders in `torque-pack/progressions/`.

---

## Block 1 — STRENGTH / TORQUE BASE (weeks 1–4)
*Force production, strength-endurance, neuromuscular foundation. Warm-ups lean
`torque_contrast` (joint-safe) and `easy_raise`.*

| Wk | Tue (quality) | Thu (quality) | Sat (long/durability) | Mid-week opener |
|----|---------------|---------------|------------------------|-----------------|
| 1 | `T1_MuscleTension_L1` · *torque_contrast* | `T8_Descending-Cadence_L1` · *torque_contrast* | `06_Durability_L1` · *easy_raise* | `T6_ForceReps-Stomps_L1` · *sprint_primer* |
| 2 | `T1_MuscleTension_L2` | `T2_SFR_L1` | `05_Z2-Sprints_L1` · *easy_raise* | `T6_ForceReps-Stomps_L2` |
| 3 | `T1_MuscleTension_L3` | `T8_Descending-Cadence_L2` | `06_Durability_L2` | `T2_SFR_L2` |
| 4 | **Recovery:** `T2_SFR_L1` (light) | easy Z2 | easy endurance 90–120min | rest |

## Block 2 — THRESHOLD / LACTATE TOLERANCE (weeks 5–8)
*Threshold, TTE, lactate shuttling, sustained torque-at-power. Warm-ups lean
`threshold_feel`; torque maintained via `torque_contrast`.*

| Wk | Tue (quality) | Thu (quality) | Sat (long/durability) | Mid-week opener |
|----|---------------|---------------|------------------------|-----------------|
| 5 | `03_KolieMoore-TTE_L1` · *threshold_feel* | `04_Over-Unders_L1` · *threshold_feel* | `06_Durability_L3` · *easy_raise* | `T3_TorqueMax_L1` · *torque_contrast* |
| 6 | `03_KolieMoore-TTE_L2` | `04_Over-Unders_L2` | `T7_Sit-Stand_L2` · *torque_contrast* | `T3_TorqueMax_L2` |
| 7 | `03_KolieMoore-TTE_L3` | `04_Over-Unders_L3` | `06_Durability_L4` | `T7_Sit-Stand_L3` |
| 8 | **Recovery:** `03_KolieMoore-TTE_L1` (light) | easy Z2 | `05_Z2-Sprints_L1` | rest |

## Block 3 — VO2 / PEAK (weeks 9–12)
*VO2max, anaerobic power, torque→power transfer, race sharpness. Warm-ups lean
`vo2_primer` / `crit_opener` / `sprint_primer`. Volume drops, intensity stays sharp.*

| Wk | Tue (quality) | Thu (quality) | Sat (long/transfer) | Mid-week opener |
|----|---------------|---------------|----------------------|-----------------|
| 9 | `01_Ronnestad-30-15_L1` · *vo2_primer* | `02_Seiler-4x8_L2` · *vo2_primer* | `T4_Ruegg-Torque-Power_L2` · *sprint_primer* | endurance + strides |
| 10 | `01_Ronnestad-30-15_L2` | `02_Seiler-4x8_L3` | `T5_Pogacar-Stack_L2` · *crit_opener* | `T6_ForceReps-Stomps_L3` |
| 11 | `01_Ronnestad-30-15_L3` | `05_Z2-Sprints_L3` · *easy_raise* | `T5_Pogacar-Stack_L3` | easy Z2 |
| 12 | **Taper/Peak:** `01_Ronnestad-30-15_L4` (short, sharp) · *vo2_primer* | `02_Seiler-4x8_L4` | openers / **EVENT** | rest |

---

## Weekly load guidance (approx, FTP-relative)
- **Build weeks:** 3 quality + 2–3 endurance/long. Aim each quality day ~60–90 TSS,
  the long durability day 120–160 TSS, week total scaling 350 → 450 across a block.
- **Recovery weeks (4, 8):** cut volume ~40%, drop to 1 light quality, no durability day.
- **Taper (wk 12):** keep intensity (sharp short reps), halve volume; full rest 2 days pre-event.

## Progression rules
1. **Advance a ladder level only after completing the current level on target** (every
   interval at prescribed power AND cadence). Miss targets twice → repeat the level.
2. **Turn one axis at a time.** The ladders mostly move *intensity + cadence + volume*;
   if you plateau, switch the lever (e.g. hold power, shrink recovery — the `density`
   axis) rather than just adding watts. See `FUNDAMENTALS_interval-manipulation.md`.
3. **Never two hard days back-to-back.** Keep easy Z2 or rest between Tue/Thu/Sat.
4. **Fuel the durability days** (80–100g carbs/hr) — a fatigued block that craters is
   usually under-fuelling, not under-fitness.

## Retarget to a real event
This is a generic 12-week shell. To anchor it to a date/event, the engine can rebuild any
session at a chosen dose: pick a target TSS/kJ and the lever to deliver it
(`progression_engine.py` → `progress(spec, axis, levels, step)` + `dose()`), or hand the
calendar to the coaching pipeline's `build_block` for date-stamped, FTP-personalised output.
