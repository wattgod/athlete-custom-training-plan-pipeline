# Warm-Up Template Library

Eight research-backed warm-ups (11–19 min), each matched to the main set that follows.
Implemented in `progression_engine.py` (`WARMUPS` dict); the engine auto-selects one via
`WU_FOR[energy_system]`. Warm-up is a **primer lever**, not filler — for hard sets it
changes how fast you reach VO2max in rep 1.

## The priming science (why hard-day warm-ups have a heavy block + bursts)
**Prior heavy-intensity exercise** (above gas-exchange threshold, *not* all-out) speeds the
VO2 on-kinetics of the next hard effort: shorter time constant, higher primary amplitude,
reduced/eliminated slow component → you hit VO2max faster and spend more of rep 1 at VO2max.
- Dose that works: **~6 min heavy/sweet-spot + ~10 min easy** before the set.
- **Never end on a burst:** residual lactate from a too-close/too-hard primer impairs rep 1
  — always keep the trailing easy settle.
- Framework: **RAMP** (Raise, Activate, Mobilise, Potentiate — Jeffreys 2007).

## Templates

| # | Key (`WARMUPS`) | Pairs with | Time | Key feature |
|---|-----------------|------------|------|-------------|
| 1 | `easy_raise` | Endurance / tempo / sweet-spot / strength-endurance | 11 min | Pure "Raise," no priming needed |
| 2 | `vo2_primer` | VO2max, 30/15s, hard-start races | 19 min | 6-min heavy + 3×20s bursts → speeds VO2 on-kinetics |
| 3 | `threshold_feel` | Threshold, over-unders, FTP test | 12 min | 2 sub-threshold "feel" efforts (Trek-Segafredo) |
| 4 | `sprint_primer` | Sprints, peak power | ~13 min | Spin-ups + building accels, full recovery |
| 5 | `torque_contrast` | Low-cadence big-gear strength | 12 min | High-cadence first (joint safety) → low-cadence primer |
| 6 | `tt_short` | TT / prologue / test | 15 min | Graded ramp to Z5 + PAP 6s sprints (Team Sky) |
| 7 | `legspeed` | High-cadence / efficiency days | 13 min | 110–125 rpm spin-ups + leg-isolation prep |
| 8 | `crit_opener` | Crit / CX / fast mass-start | 19 min | Descending-duration bursts, 120→220% FTP |

## Block detail (the two load-bearing ones)
**`vo2_primer` (19 min):** 5min ramp 50→70% · **6min @88% (heavy primer)** · 3min @50% ·
3×(20s @125% / 40s @50%) potentiation bursts · **2min @50% settle**.

**`torque_contrast` (12 min):** 4min ramp 50→65% · 3min @80% **@100rpm** (warm joints at
*high* cadence first) · 2min @70% stepping 95→75rpm · 2min @75% **@58–62rpm** low-cadence
primer · 1min @55% spin-out.

## Matching logic
The engine keys off the main set's `system` field:
`endurance/tempo/sweetspot→easy_raise · threshold/over_under→threshold_feel ·
vo2max/anaerobic→vo2_primer · sprint/neuromuscular→sprint_primer ·
torque/strength_endurance→torque_contrast · durability→easy_raise · test→tt_short ·
legspeed→legspeed`. Override per-workout with `spec['warmup'] = '<key>'`.

## Sources
Priming/VO2 kinetics: Bailey et al. (PLOS ONE), Burnley/Jones (PubMed 15746165, 21552161),
PMC3989295, PMC11709320 · Practitioner dose: PezCycling "VO2 Priming" · RAMP: Jeffreys 2007
(scottishathletics) · Threshold: Trek-Segafredo/Saris · Sprint/TT: Team Sky/British Cycling
(cycletechreview, britishcycling.org.uk) · Crit/CX: TrainerRoad "Pahrah/Laurel" · Torque:
CTS/trainright · Leg-speed: TrainingPeaks/VeloVostra. (Full URLs in research notes.)

> Conversion caveat: where a named source gave HR-zone or RPE language, block structure /
> durations / burst counts are verbatim but the absolute %FTP is a standard Coggan-zone
> mapping for programmatic use, not a verbatim source figure.
