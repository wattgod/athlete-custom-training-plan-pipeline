#!/usr/bin/env python3
"""Distinctive TORQUE / low-cadence pack — 8 sessions, each from a named source.

NOT the generic 5x5 @90% 50-60rpm. Covers the full force spectrum:
strength-endurance, supra-threshold, torque->power transfer, neuromuscular
force, structural contrast, cadence manipulation.

Format: Gravel God ZWO v6.0 (TrainingPeaks-safe). Cadence is a PROMPT, not an
ERG target - shift to the gear that lets you hold the prescribed rpm. SteadyState
can't carry textevents (only IntervalsT), so multi-power sessions put per-segment
cues in the <description>. Run: python3 generate_torque.py
"""
from pathlib import Path
import build_zwo as B

OUTDIR = Path(__file__).resolve().parent / "torque-pack"
OUTDIR.mkdir(exist_ok=True)
B.OUT = OUTDIR

written = []


def desc(intro, warm, main, purpose, execute, cite, fuel="-40-60g carbs/hr.", hyd="-500-750ml/hr."):
    return f"""{intro}

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
{fuel}

HYDRATION:
{hyd}"""


def emit(name, d, blocks):
    written.append(B.build(name, d, blocks).name)


# ============================================================ 1. Muscle Tension Intervals (FasCat)
emit("T1_MuscleTension_Intervals_FasCat",
     desc("[TORQUE 1/8: Muscle Tension Intervals - FasCat. Strength-endurance, power-AGNOSTIC]",
          "-15min easy building to endurance pace",
          "-4x 8min in a BIG GEAR at 50-55rpm, seated\n-Power is capped ~85% FTP on purpose - the limiter is TORQUE per stroke, not watts. Don't chase power.\n-4min easy spin (self-selected cadence) between\n-Push quads, pull hamstrings, consciously engage glutes",
          "Force-endurance / fast-twitch recruitment with full aerobic control. The off-season big-gear masher base. Builds the platform TorqueMax (T3) progresses beyond.",
          "-Stay seated, quiet upper body, no bar-pulling. If you can spin >60rpm the gear's too small. Progress reps/length over a 5-week block (3x7 -> 5x9 -> 4x10).",
          "-FasCat Coaching, 'Muscle Tension Intervals' (fascatcoaching.com). Oct-Feb, 1-2x/wk. CAUTION: ease in with any knee-injury history."),
     [B.warmup(900, 0.50, 0.70, 85, 95),
      B.intervals(4, 480, 0.85, 240, 0.50, 50, 55, msg="4x8min @50-55rpm BIG GEAR. Torque, not watts. Off: spin easy."),
      B.cooldown(600, 0.70, 0.50, 85, 95)])


# ============================================================ 2. SFR (Italian aerobic-strength)
emit("T2_SFR_Salite-Forza-Resistenza",
     desc("[TORQUE 2/8: SFR / Salite Forza Resistenza - Italian tradition (Sassi/Moser)]",
          "-20min building, a couple of cadence ramps",
          "-6x 4min at 45-50rpm, 80-90% FTP (mid-upper Zone 3), seated\n-NEVER below 40rpm\n-4min easy spin between (self-selected cadence)\n-On a 5-8% climb or trainer in a big gear",
          "Aerobic strength: trains the torque demand of high-power efforts WITHOUT the aerobic strain. Shorter/higher-rep than MTI - 'feel the chain'.",
          "-Seated only, hands on the tops, DO NOT pull with the arms. Smooth, even pressure. Build from 4 toward 6-8 reps across the block.",
          "-Catalyst Coaching / Hero Dolomites SFR guides. Classic Italian off-season strength climbs."),
     [B.warmup(1200, 0.50, 0.72, 80, 90),
      B.intervals(6, 240, 0.88, 240, 0.50, 45, 50, msg="6x4min @45-50rpm @88%. Seated, hands on tops, don't pull bars."),
      B.cooldown(600, 0.70, 0.50, 85, 95)])


# ============================================================ 3. TorqueMax (EVOQ supra-threshold)
emit("T3_TorqueMax_SupraThreshold_EVOQ",
     desc("[TORQUE 3/8: TorqueMax - EVOQ.bike. Supra-threshold low-cadence = VO2 power AND max torque]",
          "-20min with several cadence ramps",
          "-6x (build to 8) 2.5min at 108% FTP (105-110%) at 50-55rpm, big gear\n-Equal recovery: easy spin self-selected cadence between\n-Target ~1 Nm/kg bodyweight if your head unit shows torque",
          "Hits VO2max power and maximal torque simultaneously - makes high wattages feel easy. The spicy end of the spectrum; highest injury risk.",
          "-Smooth rounded stroke, engage core, no rocking. EARN this first: do weeks of MTI/SFR before TorqueMax. Late base / early build only.",
          "-EVOQ.bike, 'Low Cadence Cycling: How Torque Training Makes You Faster' (Brendan Housler). Roadman VO2 variant: 5x4min @110-115% @~50rpm.",
          "-50-70g carbs/hr.", "-500-750ml/hr."),
     [B.warmup(1200, 0.50, 0.75, 85, 95),
      B.intervals(6, 150, 1.08, 150, 0.50, 50, 55, msg="6x2.5min @105-110% at 50-55rpm. Build to 8. Earn it first."),
      B.cooldown(600, 0.70, 0.50, 85, 95)])


# ============================================================ 4. Rüegg Torque->Power Release (EF)
# per rep: 5min torque @1.15/55rpm -> 1min MAX spin-up high cadence -> full recovery
ruegg = [B.warmup(1200, 0.50, 0.75, 85, 95)]
for r in range(1, 5):
    ruegg += [
        B.steady(300, 1.15, 50, 58),   # big-gear torque at VO2 power
        B.steady(60, 1.40, 95, 110),   # shift DOWN, max spin-up (torque -> velocity)
        B.steady(300, 0.50, 85, 95),   # full recovery
    ]
ruegg.append(B.cooldown(600, 0.70, 0.50, 85, 95))
emit("T4_Ruegg_Torque-to-Power-Release_EF",
     desc("[TORQUE 4/8: Noemi Ruegg Torque->Power - EF Pro Cycling. Build torque, then SPIN it into power]",
          "-20min building, 2-3 short openers",
          "-4 rounds, each = 5min @~115% FTP at 50-58rpm (big gear, ideally a climb)\n  -> IMMEDIATELY shift to a lighter gear and 1min MAX effort, high cadence (the 'release')\n-Full recovery (5min easy) between rounds",
          "Sprint/bunch-finish strength: push the big gear (torque) then spin it up (velocity). Trains transferring built-up torque into actual leg speed.",
          "-Seated for the 5min torque block; the 1min release is all-out, free/high cadence. Target a fixed Nm number on the torque block so it stays even over undulations.",
          "-EF Pro Cycling, 'Pro Workouts: Torque Efforts with Noemi Ruegg'.",
          "-50-70g carbs/hr.", "-500-750ml/hr."),
     ruegg)


# ============================================================ 5. Pogačar/UAE Torque-VO2 + Sprint Stack
# per rep: 2.5min torque @1.10/50rpm -> 15s sprint @1.80 -> INCOMPLETE high-Z2 recovery
uae = [B.warmup(1200, 0.50, 0.75, 85, 95)]
for r in range(1, 8):
    uae += [
        B.steady(150, 1.10, 48, 55),   # torque at VO2 power, low cadence
        B.steady(15, 1.80, 95, 110),   # 15s max sprint cap
        B.steady(180, 0.70, 85, 95),   # deliberately INCOMPLETE recovery (high Z2)
    ]
uae.append(B.cooldown(900, 0.70, 0.50, 85, 95))
emit("T5_Pogacar-UAE_Torque-VO2-Sprint-Stack",
     desc("[TORQUE 5/8: UAE / Pogacar Torque-VO2 + Sprint. Three demands, incomplete recovery]",
          "-20min building, 2-3 openers",
          "-7 reps, each = 2.5min at ~110% FTP at 48-55rpm (torque, steep climb)\n  -> straight into a 15s ALL-OUT sprint\n-Recovery = HIGH Zone 2 (~70% FTP), NOT full rest, 3min\n-Team baseline variant: 8x4min @40-50rpm @90-100% FTP",
          "Stacks high torque + VO2 power + a neuromuscular spike, with incomplete recovery. Trains explosive transfer under accumulating fatigue. Advanced only.",
          "-Seated for the torque portion, stand into the sprint. The short Z2 'recovery' is part of the stimulus - keep pedalling. Build phase, experienced riders.",
          "-UAE Team Emirates-XRG (perf. head Jeroen Swart); Cycling Weekly / Cinch Cycling.",
          "-60-90g carbs/hr.", "-500-750ml/hr."),
     uae)


# ============================================================ 6. Force Reps / Stomps (CTS / Pez)
emit("T6_ForceReps_Stomps_Standing-Starts_CTS",
     desc("[TORQUE 6/8: Stomps / Standing-Start Force Reps - CTS / PezCycling. Neuromuscular, alactic]",
          "-20min FULLY warmed up (this loads connective tissue hard)",
          "-8x ~12s MAX-torque drives from near-standstill in a HUGE gear (53x12/14)\n-Seated, cadence climbs 0 -> ~100rpm as you spin the gear out\n-5min easy (~50% FTP) FULL recovery between - this is neuromuscular, rest matters",
          "Maximal fast-twitch fibre recruitment / acceleration-torque from low speed. Completely different system from steady grinding. Pre-season explosive primer.",
          "-Stomp the downstroke, pull through the bottom, upper body dead still, let the legs drive. Low volume, long rests, huge gear. Stop if knees complain.",
          "-CTS / trainright.com (Stomps & PowerStarts); PezCycling 'On-Bike Strength'.",
          "-40-60g carbs/hr.", "-500-750ml/hr."),
     [B.warmup(1200, 0.50, 0.75, 85, 95),
      B.intervals(8, 12, 1.90, 288, 0.50, 60, 85, msg="12s MAX stomp, huge gear, near-standstill. 5min FULL recovery."),
      B.cooldown(600, 0.70, 0.50, 85, 95)])


# ============================================================ 7. Sit-Stand Efforts (Rouleur)
# 3x 12min interval = 4 cycles of (2min seated 50rpm / 1min standing 85rpm) at SAME watts
sse = [B.warmup(900, 0.50, 0.72, 85, 95)]
for block in range(1, 4):
    for cyc in range(4):
        sse.append(B.steady(120, 0.90, 48, 52))   # SEATED big gear, low cadence
        sse.append(B.steady(60, 0.90, 82, 90))     # STANDING, higher cadence, same watts
    if block < 3:
        sse.append(B.steady(300, 0.55, 85, 95))    # 5min easy between intervals
sse.append(B.cooldown(600, 0.70, 0.50, 85, 95))
emit("T7_Sit-Stand-Efforts_Rouleur",
     desc("[TORQUE 7/8: Sit-Stand Efforts (SSE) - Rouleur. Seated/standing contrast at CONSTANT watts]",
          "-15min building Z1->Z2",
          "-3x 12min intervals, each repeating: 2min SEATED big-gear @48-52rpm / 1min OUT-OF-SADDLE @82-90rpm\n-Hold ~90% FTP CONSTANT across both seated and standing portions\n-5min easy between intervals",
          "Bridges strength and high-cadence power: seated = big-gear torque, standing-at-higher-cadence = rapid motor-unit recruitment (the attack response).",
          "-The trick is keeping WATTS flat while only cadence/posture change. Smooth transitions, no power spike standing up. Introduce after 6-8wk base.",
          "-Rouleur Performance, 'Sit-Stand Efforts: the best way to build functional bike strength?'",
          "-50-70g carbs/hr.", "-500-750ml/hr."),
     sse)


# ============================================================ 8. Descending-Cadence Torque Ladder
# same power 0.85, cadence steps DOWN each rep: 70 -> 60 -> 50 -> 45 rpm
ladder = [B.warmup(900, 0.50, 0.72, 85, 95)]
rungs = [(68, 72), (58, 62), (48, 52), (43, 47)]
for i, (lo, hi) in enumerate(rungs):
    ladder.append(B.steady(300, 0.85, lo, hi))
    if i < len(rungs) - 1:
        ladder.append(B.steady(180, 0.55, 85, 95))
ladder.append(B.cooldown(600, 0.70, 0.50, 85, 95))
emit("T8_Descending-Cadence_Torque-Ladder",
     desc("[TORQUE 8/8: Descending-Cadence Ladder - Gear & Grit / CTS. Same watts, torque climbs each rep]",
          "-15min building Z1->Z2",
          "-4x 5min ALL at 85% FTP, but cadence steps DOWN each rep: 70 -> 60 -> 50 -> 45rpm\n-Torque rises every rung because power is held flat as rpm drops\n-3min easy spin between rungs",
          "Trains force application across a range of recruitment patterns. Because watts stay constant, only torque changes - a clean progressive overload of pedal force.",
          "-Seated, smooth, keep power flat - shift to a bigger gear each rung, don't push harder. Watch the knees on the 45rpm rung; bail if they protest.",
          "-Gear & Grit, 'Big Gear, Big Gains'; CTS cadence material."),
     ladder)


print(f"Wrote {len(written)} torque files to {OUTDIR}")
for n in written:
    print(f"  - {n}")
