#!/usr/bin/env python3
"""Generate the 'Latest Cycling Workout Trends 2026' .zwo pack.

Seven trending structured sessions, one per dominant energy system, built with
the TrainingPeaks-safe builder in build_zwo.py. Run: python3 generate.py
"""
from build_zwo import warmup, cooldown, steady, intervals, build, OUT

files = []


def desc(intro, warm, main, purpose, execute, fuel, hydrate):
    return f"""{intro}

WARM-UP:
{warm}

MAIN SET:
{main}

PURPOSE:
{purpose}

EXECUTION:
{execute}

NUTRITION:
{fuel}

HYDRATION:
{hydrate}"""


# ------------------------------------------------------------------ 1. Rønnestad 30/15s
name = "01_Ronnestad_30-15_VO2max"
blocks = [
    warmup(720, 0.50, 0.70, 85, 95),
    intervals(2, 60, 1.15, 60, 0.50, 95, 105, msg="Primers: 2x1min @115% to open the legs"),
    intervals(13, 30, 1.10, 15, 0.50, 95, 110, msg="Set 1/3: 13x 30s@110% / 15s float. Hold form."),
    steady(180, 0.50, 85, 95),
    intervals(13, 30, 1.10, 15, 0.50, 95, 110, msg="Set 2/3: 13x 30s@110% / 15s float."),
    steady(180, 0.50, 85, 95),
    intervals(13, 30, 1.10, 15, 0.50, 95, 110, msg="Set 3/3: empty the tank, keep the 30s on target."),
    cooldown(600, 0.70, 0.50, 85, 95),
]
files.append((name, desc(
    "[TREND: Bent Ronnestad's 30/15 micro-intervals - the modern VO2max standard]",
    "-12min ramp Z1->Z2, then 2x1min @115% FTP with 1min easy between",
    "-3 sets of 13x (30s @110% FTP / 15s @50% FTP), 90-110rpm\n-3min @50% FTP easy spin between sets\n-Cadence: high turnover, stay seated and smooth",
    "VO2max. The 15s float keeps O2 uptake pinned near max, so you bank far more total time at >90% VO2max than long 5min reps - ~5% bigger FTP gain in Ronnestad's trials.",
    "-Don't hero rep 1. Target 110% on every 30s; the float is a true 50% spin, not a coast. If you can't hit 110% in the back third of a set, end that set.",
    "-30-60g carbs/hr. Top up before each set.",
    "-500-750ml/hr with electrolytes.",
), blocks))


# ------------------------------------------------------------------ 2. Seiler 4x8
name = "02_Seiler_4x8_Threshold-VO2"
blocks = [
    warmup(900, 0.50, 0.75, 85, 95),
    intervals(2, 30, 1.10, 60, 0.50, 95, 105, msg="Openers: 2x30s @110% to prime"),
    intervals(4, 480, 1.08, 120, 0.50, 90, 100, msg="4x8min @ MAX SUSTAINABLE (~108%). Pace so all 4 hold."),
    cooldown(600, 0.70, 0.50, 85, 95),
]
files.append((name, desc(
    "[TREND: Stephen Seiler's 4x8 - the highest-yield single HIT session in polarized 80/20]",
    "-15min building Z1->Z2, with 2x30s openers @110% FTP",
    "-4x 8min @ highest sustainable power (target 108% FTP, ~105-110%)\n-2min @50% FTP recovery between\n-Cadence: 90-100rpm",
    "Upper threshold + VO2max ceiling. ~16% threshold / ~10% VO2max lift over 7 weeks in Seiler's recreational cohort.",
    "-This is paced by FEEL, not a fixed watt. Pick an effort all 4 reps can hold. If rep 4 collapses you started too hard; if rep 4 was easy, go harder next time.",
    "-60g carbs/hr. Fuel from minute 20.",
    "-500-750ml/hr with electrolytes.",
), blocks))


# ------------------------------------------------------------------ 3. Kolie Moore threshold / TTE
name = "03_KolieMoore_Threshold_TTE"
blocks = [
    warmup(900, 0.50, 0.75, 85, 95),
    steady(1200, 0.98, 85, 95),
    steady(600, 0.55, 85, 95),
    steady(1200, 0.98, 85, 95),
    cooldown(600, 0.70, 0.50, 85, 95),
]
files.append((name, desc(
    "[TREND: Kolie Moore / Empirical Cycling - FTP as a DURATION (TTE), not a 20min number]",
    "-15min building Z1->Z2",
    "-2x 20min @ 98% FTP (self-paced: start ~96%, let it float to 100-102% in the final third)\n-10min @55% FTP between\n-Cadence: 85-95rpm, relaxed upper body",
    "Threshold / Time-to-Exhaustion at MLSS. Extends how LONG you can hold FTP, not just the number. Progress weekly toward 25-30min reps and 40-60min total TTE.",
    "-Resist ERG lock if you can - ride it on feel and let power drift up at the end. The goal is accumulating time at/near threshold, not a perfect flat line.",
    "-60-80g carbs/hr. Start at 30-45min, mix gels and drink mix.",
    "-500-750ml/hr. Adjust for heat.",
), blocks))


# ------------------------------------------------------------------ 4. Over-unders
name = "04_Over-Unders_Lactate-Tolerance"
ou = lambda n: intervals(3, 120, 0.95, 120, 1.05, 90, 100,
                         msg=f"Block {n}/3: under 95% (clear lactate) -> over 105% (build it). Repeat x3.")
blocks = [
    warmup(900, 0.50, 0.80, 85, 95),
    ou(1),
    steady(300, 0.55, 85, 95),
    ou(2),
    steady(300, 0.55, 85, 95),
    ou(3),
    cooldown(600, 0.70, 0.50, 85, 95),
]
files.append((name, desc(
    "[TREND: Over-unders - race-specific lactate shuttle work (TrainerRoad / FasCat / CTS staple)]",
    "-15min building Z1->Z2",
    "-3 blocks of 12min: alternate 2min @95% (under) / 2min @105% (over) x3\n-5min @55% FTP between blocks\n-Cadence: 90-100rpm",
    "Lactate clearance + threshold tolerance. Trains the body to reprocess lactate while still working hard - exactly how paceline surges and TT efforts hurt.",
    "-Stay smooth across the under->over transition; don't surge into the over, ramp into it. The unders are working recoveries, NOT rest - keep pressure on the pedals.",
    "-60g carbs/hr. Fuel steadily.",
    "-500-750ml/hr with electrolytes.",
), blocks))


# ------------------------------------------------------------------ 5. Almquist Z2 + sprints
name = "05_Almquist_Z2-plus-Sprints"
spr = lambda n: intervals(3, 30, 2.00, 240, 0.60, 95, 110,
                         msg=f"Sprint set {n}/3: 3x 30s ALL-OUT (max watts), spin easy between.")
blocks = [
    warmup(600, 0.50, 0.60, 85, 95),
    steady(900, 0.62, 85, 95),
    spr(1),
    steady(360, 0.60, 85, 95),
    spr(2),
    steady(360, 0.60, 85, 95),
    spr(3),
    steady(900, 0.62, 85, 95),
    cooldown(300, 0.55, 0.45, 85, 95),
]
files.append((name, desc(
    "[TREND: 'Z2 with sprints' - Almquist et al. Sprinkle MAX sprints into easy rides]",
    "-10min easing into Zone 2",
    "-~90min @ 60-65% FTP (Zone 2) as the body of the ride\n-3 sets of 3x 30s ALL-OUT sprints (encoded ~200% FTP; just go MAX)\n-~4min @60% between sprints, ~10min @60% between sets\n-Cadence: free; wind up big for each sprint",
    "Neuromuscular sprint power + aerobic base in one ride. Adding maximal sprints to LOW-intensity rides improved endurance 6 weeks later without adding a true hard day.",
    "-Sprints are genuinely maximal - out of the saddle, full gas for 30s. The .zwo target (~200%) is a placeholder; beat it. Keep the rest of the ride strictly easy.",
    "-60-90g carbs/hr on the long Z2 body.",
    "-500-750ml/hr; this is a long ride.",
), blocks))


# ------------------------------------------------------------------ 6. Durability / fatigued threshold
name = "06_Durability_Fatigued-Threshold"
blocks = [
    warmup(600, 0.50, 0.65, 85, 95),
    intervals(2, 600, 0.95, 300, 0.55, 85, 95, msg="FRESH block: 2x10min @95% - note how this feels."),
    steady(5400, 0.60, 85, 95),
    intervals(2, 720, 0.97, 360, 0.55, 85, 95, msg="FATIGUED block: 2x12min @97% AFTER 90min Z2. This is the workout."),
    cooldown(600, 0.65, 0.50, 85, 95),
]
files.append((name, desc(
    "[TREND: Durability - the defining training trait of 2024-2026. Train power AFTER fatigue]",
    "-10min easing to Z2",
    "-FRESH: 2x10min @95% FTP, 5min @55% between\n-BRIDGE: 90min @60% FTP (accumulate kJ/fatigue)\n-FATIGUED: 2x12min @95-100% FTP (target 97%), 6min @55% between\n-Cadence: 85-95rpm throughout",
    "Fatigue resistance / durability. FTP tested fresh says little about hour 4. Identical efforts before and after a long Z2 block expose and TRAIN the late-ride power fade that decides gravel/long road races.",
    "-Compare the fresh vs fatigued blocks honestly. If the fatigued block craters, your fueling (not fitness) is usually the limiter - fix that first.",
    "-HIGH FUEL: 80-100g carbs/hr. Eat early, eat often - this is a 3hr ride.",
    "-750ml/hr+ with electrolytes. Start hydrated.",
), blocks))


# ------------------------------------------------------------------ 7. Big-gear torque
name = "07_BigGear_Torque_Strength-Endurance"
blocks = [
    warmup(900, 0.50, 0.70, 85, 95),
    intervals(5, 300, 0.90, 180, 0.55, 50, 60, msg="5x5min @90% at 50-60rpm BIG GEAR. Off: spin easy ~90rpm."),
    cooldown(600, 0.70, 0.50, 85, 95),
]
files.append((name, desc(
    "[TREND: Low-cadence torque intervals - 2024 research shows low-rpm HIIT beats normal-cadence for FTP gains]",
    "-15min building Z1->Z2 at normal cadence",
    "-5x 5min @90% FTP at 50-60rpm (big gear, grinding torque)\n-3min @55% FTP at free/normal cadence between\n-NOTE: .zwo can't enforce cadence - shift to a big gear and hold 50-60rpm yourself",
    "Strength endurance / force production. Bridges the gym to the bike. The 2024 novelty: doing the INTERVALS (not just steady tempo) at low cadence drives bigger aerobic/FTP gains.",
    "-Stay seated, smooth, no rocking. Engage glutes/core; push through the whole pedal stroke. Stop a rep if your knees complain - this is high joint load.",
    "-40-60g carbs/hr.",
    "-500-750ml/hr.",
), blocks))


# ------------------------------------------------------------------ write all
written = []
for name, d, blocks in files:
    path = build(name, d, blocks)
    written.append(path.name)

print(f"Wrote {len(written)} .zwo files to {OUT}:")
for n in written:
    print(f"  - {n}")
