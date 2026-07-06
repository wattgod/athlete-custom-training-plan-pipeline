#!/usr/bin/env python3
"""Torque pack — 4-level progressions (L1->L4) for all 8 sessions = 32 files.

Two upgrades over the singles:
  1. PROPER WARM-UP on every file: 15-20min Z1->Z2 ramp + 1x10min high-cadence
     Z3 @100-120rpm (primes leg speed before the grind); openers added before the
     supra-threshold / neuromuscular sessions.
  2. Progression follows the research's cadence ramp-in: as you adapt, CADENCE
     DROPS and volume/intensity RISES (L1 ~60rpm entry -> L4 ~45rpm peak).

Format: Gravel God ZWO v6.0 (TrainingPeaks-safe). Output -> torque-pack/progressions/.
Run: python3 generate_torque_progressions.py
"""
from pathlib import Path
import build_zwo as B

OUTDIR = Path(__file__).resolve().parent / "torque-pack" / "progressions"
OUTDIR.mkdir(parents=True, exist_ok=True)
B.OUT = OUTDIR

written = []


def warmup(ramp_s=900, openers=0):
    """15-20min Z1->Z2 ramp + 1x10min high-cadence Z3 activation (+optional openers)."""
    b = [B.warmup(ramp_s, 0.50, 0.70, 85, 95),
         B.steady(600, 0.80, 100, 120)]                      # 1x10min Z3 @100-120rpm
    if openers:
        b.append(B.intervals(openers, 30, 1.10, 60, 0.50, 100, 110,
                             msg=f"{openers}x30s high-cadence spin-ups to prime the legs"))
        b.append(B.steady(120, 0.55, 90, 100))               # brief settle
    return b


WARM_TXT = "-15-20min progressing Z1->Z2\n-1x10min high-cadence Z3 @100-120rpm (wake up leg speed before the grind)"
WARM_TXT_O = WARM_TXT + "\n-then 2-3x30s spin-up openers"


def desc(intro, level, warm, main, purpose, execute, cite):
    return f"""{intro}
PROGRESSION: Level {level}/4

WARM-UP:
{warm}

MAIN SET:
{main}

PURPOSE:
{purpose}

EXECUTION:
{execute}

SOURCE:
{cite}

NUTRITION:
-40-70g carbs/hr.

HYDRATION:
-500-750ml/hr."""


def emit(name, d, blocks):
    written.append(B.build(name, d, blocks).name)


# ============================================================ T1 Muscle Tension Intervals (FasCat)
# (reps, dur_s, pwr, cad_lo, cad_hi, off_s)  — FasCat's 5-week ramp, cadence dropping
T1 = [(1, 3, 420, 0.82, 58, 62, 210), (2, 3, 600, 0.84, 54, 58, 300),
      (3, 4, 480, 0.85, 51, 55, 240), (4, 4, 600, 0.86, 48, 52, 300)]
for lvl, reps, dur, pwr, clo, chi, off in T1:
    blocks = warmup(900) + [
        B.intervals(reps, dur, pwr, off, 0.50, clo, chi,
                    msg=f"{reps}x{dur//60}min @{clo}-{chi}rpm BIG GEAR. Torque, not watts."),
        B.cooldown(600, 0.70, 0.50, 85, 95)]
    emit(f"T1_MuscleTension_L{lvl}_{reps}x{dur//60}min",
         desc("[Muscle Tension Intervals - FasCat. Strength-endurance, power-agnostic]", lvl,
              WARM_TXT,
              f"-{reps}x {dur//60}min big gear at {clo}-{chi}rpm, seated\n-Power capped ~{int(pwr*100)}% - limiter is TORQUE per stroke, don't chase watts\n-{off//60}min easy spin (free cadence) between\n-Push quads, pull hamstrings, engage glutes",
              "Force-endurance / fast-twitch recruitment, fully aerobic. The off-season big-gear masher base.",
              "-Seated, quiet upper body, no bar-pulling. If you can spin >60rpm the gear's too small.",
              "-FasCat Coaching, 'Muscle Tension Intervals'. Oct-Feb, 1-2x/wk. Ease in with knee history."),
         blocks)


# ============================================================ T2 SFR (Italian aerobic-strength)
T2 = [(1, 4, 180, 0.85, 55, 58, 180), (2, 5, 240, 0.87, 50, 54, 240),
      (3, 6, 240, 0.88, 47, 50, 240), (4, 8, 240, 0.90, 45, 48, 240)]
for lvl, reps, dur, pwr, clo, chi, off in T2:
    blocks = warmup(1200) + [
        B.intervals(reps, dur, pwr, off, 0.50, clo, chi,
                    msg=f"{reps}x{dur//60}min @{clo}-{chi}rpm @{int(pwr*100)}%. Seated, don't pull bars."),
        B.cooldown(600, 0.70, 0.50, 85, 95)]
    emit(f"T2_SFR_L{lvl}_{reps}x{dur//60}min",
         desc("[SFR / Salite Forza Resistenza - Italian tradition (Sassi/Moser)]", lvl,
              WARM_TXT,
              f"-{reps}x {dur//60}min at {clo}-{chi}rpm, {int(pwr*100)}% FTP, seated\n-NEVER below 40rpm\n-{off//60}min easy spin between\n-5-8% climb or big gear on the trainer",
              "Aerobic strength - the torque demand of high-power efforts without the aerobic strain.",
              "-Seated only, hands on tops, DO NOT pull with the arms. Smooth, even pressure.",
              "-Catalyst Coaching / Hero Dolomites SFR guides."),
         blocks)


# ============================================================ T3 TorqueMax (EVOQ supra-threshold)
T3 = [(1, 5, 120, 1.05, 58, 62, 120), (2, 6, 150, 1.08, 54, 58, 150),
      (3, 7, 150, 1.10, 51, 55, 150), (4, 8, 180, 1.12, 49, 52, 180)]
for lvl, reps, dur, pwr, clo, chi, off in T3:
    blocks = warmup(1200, openers=2) + [
        B.intervals(reps, dur, pwr, off, 0.50, clo, chi,
                    msg=f"{reps}x{dur//60}:{dur%60:02d} @{int(pwr*100)}% at {clo}-{chi}rpm. Earn it first."),
        B.cooldown(600, 0.70, 0.50, 85, 95)]
    emit(f"T3_TorqueMax_L{lvl}_{reps}x{dur}s",
         desc("[TorqueMax - EVOQ.bike. Supra-threshold low-cadence: VO2 power AND max torque]", lvl,
              WARM_TXT_O,
              f"-{reps}x {dur}s at {int(pwr*100)}% FTP at {clo}-{chi}rpm, big gear\n-{off}s easy spin (free cadence) between\n-~1 Nm/kg bodyweight if you have a torque readout",
              "Hits VO2max power and maximal torque at once - makes high wattages feel easy. Highest injury risk.",
              "-Smooth rounded stroke, engage core, no rocking. Do weeks of T1/T2 before this. Late base/early build.",
              "-EVOQ.bike (Brendan Housler). Roadman VO2 variant: 5x4min @110-115% @~50rpm."),
         blocks)


# ============================================================ T4 Rüegg Torque->Power Release (EF)
# (reps, torque_s, torque_pwr, cad_lo, cad_hi, spin_pwr)
T4 = [(1, 3, 240, 1.10, 56, 60, 1.35), (2, 4, 300, 1.13, 53, 57, 1.38),
      (3, 4, 300, 1.15, 50, 54, 1.40), (4, 5, 360, 1.15, 48, 52, 1.45)]
for lvl, reps, tdur, tpwr, clo, chi, spwr in T4:
    blocks = warmup(1200, openers=3)
    for r in range(reps):
        blocks += [B.steady(tdur, tpwr, clo, chi),     # big-gear torque
                   B.steady(60, spwr, 95, 110),        # shift down, 1min max spin-up
                   B.steady(300, 0.50, 85, 95)]        # full recovery
    blocks.append(B.cooldown(600, 0.70, 0.50, 85, 95))
    emit(f"T4_Ruegg-Torque-Power_L{lvl}_{reps}x{tdur//60}min",
         desc("[Noemi Ruegg Torque->Power - EF Pro Cycling. Build torque, then SPIN it into power]", lvl,
              WARM_TXT_O,
              f"-{reps} rounds, each = {tdur//60}min @{int(tpwr*100)}% at {clo}-{chi}rpm (big gear)\n  -> IMMEDIATELY shift lighter + 1min MAX spin-up (~{int(spwr*100)}%, high cadence)\n-5min easy full recovery between rounds",
              "Sprint/bunch-finish strength: push the big gear (torque) then spin it up (velocity).",
              "-Seated for the torque block; the 1min release is all-out, high cadence. Hold a steady Nm on the grind.",
              "-EF Pro Cycling, 'Torque Efforts with Noemi Ruegg'."),
         blocks)


# ============================================================ T5 Pogačar/UAE Torque-VO2 + Sprint Stack
# (reps, torque_s, torque_pwr, cad_lo, cad_hi, sprint_pwr, rec_s, rec_pwr)
T5 = [(1, 5, 120, 1.05, 53, 57, 1.60, 180, 0.70), (2, 6, 150, 1.08, 50, 54, 1.70, 180, 0.70),
      (3, 7, 150, 1.10, 48, 52, 1.80, 180, 0.70), (4, 8, 180, 1.12, 46, 50, 1.90, 150, 0.72)]
for lvl, reps, tdur, tpwr, clo, chi, spwr, rec, recp in T5:
    blocks = warmup(1200, openers=3)
    for r in range(reps):
        blocks += [B.steady(tdur, tpwr, clo, chi),     # torque at VO2 power
                   B.steady(15, spwr, 95, 110),        # 15s sprint cap
                   B.steady(rec, recp, 85, 95)]        # incomplete high-Z2 recovery
    blocks.append(B.cooldown(900, 0.70, 0.50, 85, 95))
    emit(f"T5_Pogacar-Stack_L{lvl}_{reps}reps",
         desc("[UAE / Pogacar Torque-VO2 + Sprint. Three demands, incomplete recovery]", lvl,
              WARM_TXT_O,
              f"-{reps} reps, each = {tdur//60}:{tdur%60:02d} @{int(tpwr*100)}% at {clo}-{chi}rpm\n  -> straight into a 15s ALL-OUT sprint (~{int(spwr*100)}%)\n-Recovery = high Zone 2 (~{int(recp*100)}%), NOT full rest, {rec//60}min",
              "Stacks high torque + VO2 power + a neuromuscular spike under accumulating fatigue. Advanced.",
              "-Seated for torque, stand into the sprint. The short Z2 'recovery' is part of the stimulus - keep pedalling.",
              "-UAE Team Emirates-XRG (Jeroen Swart); Cycling Weekly / Cinch."),
         blocks)


# ============================================================ T6 Force Reps / Stomps (CTS / Pez)
# (reps, dur_s, pwr, off_s) — neuromuscular: long rests, progress the count
T6 = [(1, 6, 8, 1.70, 300), (2, 8, 12, 1.85, 300), (3, 10, 12, 1.95, 240), (4, 12, 15, 2.00, 240)]
for lvl, reps, dur, pwr, off in T6:
    blocks = warmup(1200, openers=3) + [
        B.intervals(reps, dur, pwr, off, 0.50, 60, 90,
                    msg=f"{reps}x {dur}s MAX stomp, huge gear, near-standstill. {off//60}min FULL recovery."),
        B.cooldown(600, 0.70, 0.50, 85, 95)]
    emit(f"T6_ForceReps-Stomps_L{lvl}_{reps}x{dur}s",
         desc("[Stomps / Standing-Start Force Reps - CTS / PezCycling. Neuromuscular, alactic]", lvl,
              WARM_TXT_O,
              f"-{reps}x ~{dur}s MAX-torque drives from near-standstill in a HUGE gear (53x12/14)\n-Seated, cadence climbs 0 -> ~100rpm as you spin the gear out\n-{off//60}min easy (~50%) FULL recovery between - rest matters",
              "Maximal fast-twitch recruitment / acceleration-torque from low speed. Pre-season explosive primer.",
              "-Stomp the downstroke, pull through the bottom, upper body dead still. Low volume, long rests. Stop if knees complain.",
              "-CTS / trainright.com (Stomps & PowerStarts); PezCycling 'On-Bike Strength'."),
         blocks)


# ============================================================ T7 Sit-Stand Efforts (Rouleur)
# (intervals, cycles, seat_lo, seat_hi, stand_lo, stand_hi, pwr)
T7 = [(1, 3, 3, 55, 58, 82, 88, 0.88), (2, 3, 4, 50, 54, 84, 90, 0.90),
      (3, 4, 4, 48, 52, 85, 90, 0.90), (4, 4, 5, 46, 50, 86, 92, 0.92)]
for lvl, ivals, cycles, slo, shi, tlo, thi, pwr in T7:
    blocks = warmup(900)
    for iv in range(ivals):
        for c in range(cycles):
            blocks.append(B.steady(120, pwr, slo, shi))    # 2min SEATED big gear
            blocks.append(B.steady(60, pwr, tlo, thi))     # 1min STANDING, higher cadence
        if iv < ivals - 1:
            blocks.append(B.steady(300, 0.55, 85, 95))     # 5min easy between
    blocks.append(B.cooldown(600, 0.70, 0.50, 85, 95))
    emit(f"T7_Sit-Stand_L{lvl}_{ivals}x{cycles*3}min",
         desc("[Sit-Stand Efforts (SSE) - Rouleur. Seated/standing contrast at CONSTANT watts]", lvl,
              WARM_TXT,
              f"-{ivals}x {cycles*3}min, each repeating: 2min SEATED big-gear @{slo}-{shi}rpm / 1min OUT-OF-SADDLE @{tlo}-{thi}rpm\n-Hold ~{int(pwr*100)}% FTP CONSTANT across both\n-5min easy between intervals",
              "Bridges strength and high-cadence power: seated big-gear torque vs standing rapid recruitment (attack response).",
              "-Keep WATTS flat while only cadence/posture change. No power spike standing up. After 6-8wk base.",
              "-Rouleur Performance, 'Sit-Stand Efforts'."),
         blocks)


# ============================================================ T8 Descending-Cadence Torque Ladder
# (pwr, rep_s, [rungs])
T8 = [(1, 0.82, 240, [(73, 77), (63, 67), (53, 57), (48, 52)]),
      (2, 0.85, 300, [(68, 72), (58, 62), (48, 52), (43, 47)]),
      (3, 0.87, 300, [(68, 72), (58, 62), (50, 54), (45, 49), (41, 45)]),
      (4, 0.88, 300, [(73, 77), (63, 67), (56, 60), (48, 52), (43, 47), (40, 44)])]
for lvl, pwr, rep, rungs in T8:
    blocks = warmup(900)
    for i, (lo, hi) in enumerate(rungs):
        blocks.append(B.steady(rep, pwr, lo, hi))
        if i < len(rungs) - 1:
            blocks.append(B.steady(180, 0.55, 85, 95))
    blocks.append(B.cooldown(600, 0.70, 0.50, 85, 95))
    rpm_path = "->".join(str((lo + hi) // 2) for lo, hi in rungs)
    emit(f"T8_Descending-Cadence_L{lvl}_{len(rungs)}x{rep//60}min",
         desc("[Descending-Cadence Ladder - Gear & Grit / CTS. Same watts, torque climbs each rep]", lvl,
              WARM_TXT,
              f"-{len(rungs)}x {rep//60}min ALL at {int(pwr*100)}% FTP, cadence steps DOWN: {rpm_path}rpm\n-Torque rises every rung because power stays flat as rpm drops\n-3min easy spin between rungs",
              "Force application across recruitment patterns. Watts constant, so only torque changes - clean progressive overload.",
              "-Seated, smooth, keep power flat - shift to a bigger gear each rung, don't push harder. Watch knees on the lowest rung.",
              "-Gear & Grit 'Big Gear Big Gains'; CTS cadence material."),
         blocks)


print(f"Wrote {len(written)} torque progression files to {OUTDIR}")
for n in written:
    print(f"  - {n}")
