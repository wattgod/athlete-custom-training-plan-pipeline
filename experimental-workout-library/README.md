# Cycling Workouts 2026 — Trends, Torque & a Progression Engine

A library of trending, source-attributed structured cycling workouts as
TrainingPeaks/Zwift-safe `.zwo` files, a **programmatic progression engine** that builds
them from named physiological axes, and one coherent 12-week plan that ties it together.

Set your FTP in-app before importing. Powers are % of FTP; cadence is a prompt, not an
ERG target — shift to the gear that holds the prescribed rpm.

## Read first
- **`MASTER_PLAN.md`** — the 12-week periodization (torque base → threshold build → VO2 peak)
  weaving both packs together, with the warm-up template named for every session.
- **`FUNDAMENTALS_interval-manipulation.md`** — the named taxonomy of *every* lever you can
  turn to change/progress a workout, and its physiological effect (tables + summaries, cited).
- **`WARMUPS.md`** — 8 warm-up templates (11–19 min) matched to main-set type, with the
  priming / VO2-on-kinetics science.
- **`RATIONALE.md`** — why each of the 7 trend workouts works, with citations.

## Workout files
| Folder | What | Count |
|--------|------|-------|
| `*.zwo` (top level) | 7 trend reference singles (Rønnestad, Seiler, Kolie Moore, over-unders, Z2+sprints, durability, torque) | 7 |
| `progressions/` | Those 7 as 4-level ladders (L1→L4) | 28 |
| `torque-pack/` | 8 distinctive torque sessions (FasCat, EVOQ, EF/Rüegg, UAE/Pogačar, CTS, Rouleur, Gear&Grit) | 8 |
| `torque-pack/progressions/` | Those 8 as 4-level ladders, each with a proper warm-up | 32 |
| `engine_demo/` | Engine output proving each axis moves the dose | 20 |
| `library/` | **Progressive archetype library** — 39 archetypes × **6 levels** across 9 energy-system categories (endurance, sweetspot, threshold, vo2max, anaerobic, sprint, **durability**, racesim, specialty), each driven by its primary axis; see `library/LIBRARY.md` | 234 |
| **Total** | | **329 .zwo** |

## The archetype library — `archetypes.py` → `library/`
The engine's real payoff: every workout archetype becomes a programmatic ladder. Each
entry in `ARCHETYPES` is a base spec + a **primary progression axis**; the generator emits
a **6-level ladder** (L1 entry → L6 elite) with auto-matched warm-up and a **%FTP + per-block RPE** description
(e.g. `12x 30s @ 112% FTP (RPE 8-9) / 30s @ 50%`). **Nothing is in absolute watts** —
power is % of FTP, RPE gives the feel, TSS is FTP-independent; kJ/W′bal are computed by the
engine only when a *real* FTP is supplied (pipeline), never baked at a fake reference.
**Durability is a first-class category** (9 archetypes: Progressive Fatigue Threshold,
Tired 30/30s, Tired VO2, Loaded Recovery, Double-Day Sim, Fatigued Sprints, Late-Race VO2…)
built on the `prefatigue_time` axis — efforts placed after a growing Z2 pre-load.
Names/structures align with the house catalog (95 archetypes / 22 categories). **Extensible:**
add one dict → get a validated ladder.

## The engine — `progression_engine.py`
Difficulty is many independent knobs, not one. A workout is a **spec** (warm-up template +
a main set of named parameters); progression turns one **axis** and holds the rest:

```
intensity · work_duration · recovery_duration · recovery_intensity ·
reps · sets · density · cadence · prefatigue_kj · shape
```

It computes **TSS and kJ** from the same segments it renders, so prefatigue can be sized by
*energy burned* (e.g. "do the reps after 900 kJ"), and you can hold dose constant while
changing *which* lever delivers it. Run it to regenerate `engine_demo/` and print the
axis→dose table:
```
python3 progression_engine.py
```

## Regenerate anything
```
python3 generate.py                      # 7 trend singles
python3 generate_progressions.py         # 28 trend ladders
python3 generate_torque.py               # 8 torque singles
python3 generate_torque_progressions.py  # 32 torque ladders (proper warm-ups)
python3 progression_engine.py            # 20 engine-demo files + dose table
python3 archetypes.py                     # 124 archetype-library files + LIBRARY.md
```
All builders share `build_zwo.py` (the TrainingPeaks-safe renderer: single-quote XML
declaration, 2/4-space indents, self-closing Warmup/SteadyState/Cooldown, textevents only
in IntervalsT, power 0.30–2.50). Every file in this repo has been validated against those
rules and parses as XML.

## Honest caveats
- **Cadence & "max sustainable" aren't enforceable** in `.zwo` — they live in the
  description/cadence attributes; you execute them.
- **Some named primary studies** (Rønnestad 2015, Almquist 2020, the 2024 low-cadence
  trial) are attributed via secondary coaching sources — verify DOIs before publishing.
- **TSS under-weights** neuromuscular and durability stress; don't coach by TSS alone.
- **The science is mixed** on low cadence (helps with *high* intensity, not moderate) —
  see `torque-pack/INDEX.md` and `FUNDAMENTALS`.
