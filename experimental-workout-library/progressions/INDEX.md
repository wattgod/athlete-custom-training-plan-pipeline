# 2026 Trends — Progression Ladders + 8-Week Polarized Block

Each of the 7 trending workouts now has a **4-level ladder** (L1 entry → L4 peak),
all TrainingPeaks/Zwift-safe. The ladder is *what* progresses; the 8-week plan
below is *one route* through them. Set your FTP in-app before importing.

## How each ladder progresses
| Family | L1 → L4 progresses by |
|--------|------------------------|
| `01_Ronnestad-30-15` | reps/set + on-power: 3×9 @108% → 3×11 @110% → 3×13 @110% → 3×13 @113% |
| `02_Seiler-4x8` | reps + power: 4×8 @104% → 4×8 @107% → 5×8 @106% → 5×8 @108% |
| `03_KolieMoore-TTE` | time-at-threshold: 2×18 → 2×22 → 2×25 → 3×20 min @96–98% |
| `04_Over-Unders` | block length/count + over %: 3×8 → 3×12 → 4×12 → 3×16 min |
| `05_Z2-Sprints` | sprint sets + Z2 body: 2 → 3 → 3 → 4 sets |
| `06_Durability` | ride length + fatigued block: 2.4 → 2.9 → 3.4 → 4.1 hr |
| `07_BigGear-Torque` | reps/length/power/rpm: 4×4 @88%/55-60 → 5×6 @95%/48-52rpm |

## 8-Week Polarized Block (~80/20)
3 quality sessions/week + easy Z2 fill. Move the long ride to whatever day suits.

| Wk | Phase | Tue — VO2/thr | Thu — threshold/tolerance | Sat — long | Mid-week option |
|----|-------|---------------|---------------------------|------------|-----------------|
| 1 | Base build | `02_Seiler-4x8_L1` | `04_Over-Unders_L1` | `06_Durability_L1` | `07_BigGear-Torque_L1` |
| 2 | Base build | `02_Seiler-4x8_L2` | `03_KolieMoore-TTE_L1` | `05_Z2-Sprints_L1` | `07_BigGear-Torque_L2` |
| 3 | Base build | `02_Seiler-4x8_L3` | `04_Over-Unders_L2` | `06_Durability_L2` | `07_BigGear-Torque_L3` |
| 4 | **Recovery** | `05_Z2-Sprints_L1` | easy Z2 (no file) | easy endurance | rest |
| 5 | Build | `01_Ronnestad-30-15_L1` | `03_KolieMoore-TTE_L2` | `06_Durability_L3` | `07_BigGear-Torque_L4` |
| 6 | Build | `01_Ronnestad-30-15_L2` | `04_Over-Unders_L3` | `05_Z2-Sprints_L3` | easy Z2 |
| 7 | **Peak load** | `01_Ronnestad-30-15_L3` | `03_KolieMoore-TTE_L3` | `06_Durability_L4` | easy Z2 |
| 8 | Taper/Peak | `01_Ronnestad-30-15_L4` | `02_Seiler-4x8_L4` (sharp) | openers / event | rest |

**Logic:** torque + threshold tolerance build the engine in the base block (wks 1–3);
recovery week 4 absorbs it; VO2max (Rønnestad) sharpens through the build (wks 5–7)
while durability climbs its full ladder every other Saturday; week 8 tapers volume
but keeps top-end intensity sharp. Spare levels not in the table
(`04_L4`, `03_L4`, `05_L2/L4`) are there to swap in if you adapt faster or need an
easier/bigger week.

**Rules of thumb:** only progress a family's level when you *completed* the current
one on-target (every interval at prescribed power). If you miss targets two sessions
running, repeat the level or insert a recovery week. Never run two consecutive hard
days — keep an easy Z2 or rest between Tue/Thu/Sat quality.

## Regenerate
```
python3 ../generate_progressions.py   # rewrites all 28 ladder files
```
