# Latest Cycling Workout Trends — 2026 ZWO Pack

Seven trending structured sessions, one per dominant energy system. Built to the
Gravel God ZWO Skill v6.0 format (TrainingPeaks- and Zwift-safe). All powers are
% of FTP; set your FTP in the app before importing. Import the `.zwo` files
directly into TrainingPeaks or Zwift (drop into the Zwift `Workouts` folder).

| # | File | Trains | Time | Source / Trend |
|---|------|--------|------|----------------|
| 1 | `01_Ronnestad_30-15_VO2max` | VO2max micro-intervals | ~61 min | Bent Rønnestad 30/15s |
| 2 | `02_Seiler_4x8_Threshold-VO2` | Upper threshold / VO2max | ~68 min | Stephen Seiler 4×8, polarized 80/20 |
| 3 | `03_KolieMoore_Threshold_TTE` | Threshold / Time-to-Exhaustion | ~75 min | Kolie Moore / Empirical Cycling |
| 4 | `04_Over-Unders_Lactate-Tolerance` | Lactate clearance / tolerance | ~71 min | TrainerRoad / FasCat / CTS |
| 5 | `05_Almquist_Z2-plus-Sprints` | Sprint power + aerobic base | ~98 min | Almquist et al. "Z2 with sprints" |
| 6 | `06_Durability_Fatigued-Threshold` | Fatigue resistance / durability | ~176 min | CTS / TrainingPeaks durability |
| 7 | `07_BigGear_Torque_Strength-Endurance` | Strength endurance / force | ~65 min | EF / EVOQ low-cadence torque |

## How each was built
- **Power** is stored as a decimal fraction of FTP (`1.10` = 110%).
- **Cadence** ranges are stored where the trainer can target them. Two caveats the
  `.zwo` format can't enforce, so they live in the description/interval names:
  - #5 sprints are **maximal** (encoded ~200% as a placeholder — just go full gas).
  - #7 is done in a **big gear at 50–60 rpm**; shift manually and hold the cadence.
- #2 (Seiler) and #3 (Kolie Moore) are **self-paced by feel** — pick the hardest
  effort you can repeat for all reps rather than chasing the displayed watt.

## Regenerate / tweak
```
python3 generate.py        # rewrites all 7 .zwo files
```
Edit intensities or durations in `generate.py`; `build_zwo.py` guarantees the
TrainingPeaks-safe XML formatting (single-quote declaration, 2/4-space indents,
self-closing blocks, textevents only inside IntervalsT).

## Sources
Rønnestad 30/15 (TrainingPeaks) · Seiler 4×8 (Wattkg, Roadman) · Kolie Moore TTE
(Empirical Cycling, TrainerRoad) · Over-unders (TrainerRoad, FasCat) · Almquist
sprints-in-Z2 (Frontiers in Physiology 2020) · Durability (CTS, TrainingPeaks,
PMC) · Low-cadence torque (EF Pro Cycling, EVOQ.bike).
