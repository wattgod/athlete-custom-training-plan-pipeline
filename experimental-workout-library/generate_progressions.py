#!/usr/bin/env python3
"""Generate 4-level progression ladders for the 2026 trends pack.

Each of the 7 workout families gets Level 1 (entry) -> Level 4 (peak), built with
the TrainingPeaks-safe builder. Files land in ./progressions/. Run:
    python3 generate_progressions.py
Periodization map is printed at the end and written to progressions/INDEX.md.
"""
from pathlib import Path
from xml.sax.saxutils import escape
import build_zwo as B

OUTDIR = Path(__file__).resolve().parent / "progressions"
OUTDIR.mkdir(exist_ok=True)
# point the builder's writer at the subfolder
B.OUT = OUTDIR


def desc(intro, level, warm, main, purpose, execute, fuel, hydrate):
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

NUTRITION:
{fuel}

HYDRATION:
{hydrate}"""


written = []


def emit(name, d, blocks):
    p = B.build(name, d, blocks)
    written.append(p.name)


# ============================================================ 1. Rønnestad 30/15 (VO2max)
# progress: reps per set + intensity.  (sets, reps, on_power)
RON = [(1, 3, 9, 1.08), (2, 3, 11, 1.10), (3, 3, 13, 1.10), (4, 3, 13, 1.13)]
for lvl, sets, reps, pwr in RON:
    blocks = [B.warmup(720, 0.50, 0.70, 85, 95),
              B.intervals(2, 60, 1.13, 60, 0.50, 95, 105, msg="Primers: 2x1min to open the legs")]
    for s in range(1, sets + 1):
        blocks.append(B.intervals(reps, 30, pwr, 15, 0.50, 95, 110,
                      msg=f"Set {s}/{sets}: {reps}x 30s@{int(pwr*100)}% / 15s float"))
        if s < sets:
            blocks.append(B.steady(180, 0.50, 85, 95))
    blocks.append(B.cooldown(600, 0.70, 0.50, 85, 95))
    emit(f"01_Ronnestad-30-15_L{lvl}_{sets}x{reps}reps",
         desc("[VO2max micro-intervals - Bent Ronnestad 30/15s]", lvl,
              "-12min ramp Z1->Z2, then 2x1min @113% with 1min easy",
              f"-{sets} sets of {reps}x (30s @{int(pwr*100)}% FTP / 15s @50%)\n-3min @50% between sets\n-Cadence: 90-110rpm, seated and smooth",
              "VO2max. The 15s float keeps O2 uptake near max for far more total time at >90% VO2max.",
              "-Hit target on every 30s. The float is a true easy spin. End a set if you can't hold the 30s power in its back third.",
              "-30-60g carbs/hr.", "-500-750ml/hr with electrolytes."),
         blocks)


# ============================================================ 2. Seiler 4x8 (threshold/VO2)
# progress: reps + intensity.  (reps, on_power)
SEI = [(1, 4, 1.04), (2, 4, 1.07), (3, 5, 1.06), (4, 5, 1.08)]
for lvl, reps, pwr in SEI:
    blocks = [B.warmup(900, 0.50, 0.75, 85, 95),
              B.intervals(2, 30, 1.10, 60, 0.50, 95, 105, msg="Openers: 2x30s to prime"),
              B.intervals(reps, 480, pwr, 120, 0.50, 90, 100,
                          msg=f"{reps}x8min @ MAX SUSTAINABLE (~{int(pwr*100)}%). Pace so all hold."),
              B.cooldown(600, 0.70, 0.50, 85, 95)]
    emit(f"02_Seiler-4x8_L{lvl}_{reps}x8min",
         desc("[Upper threshold / VO2max - Stephen Seiler 4x8]", lvl,
              "-15min building Z1->Z2, with 2x30s openers @110%",
              f"-{reps}x 8min @ highest sustainable power (~{int(pwr*100)}% FTP)\n-2min @50% recovery between\n-Cadence: 90-100rpm",
              "Upper threshold + VO2max ceiling. The flagship single HIT session of polarized 80/20.",
              "-Paced by FEEL, not a fixed watt. If the last rep collapses you went too hard; if it was easy, go harder next time.",
              "-60g carbs/hr from minute 20.", "-500-750ml/hr with electrolytes."),
         blocks)


# ============================================================ 3. Kolie Moore TTE (threshold)
# progress: rep length + reps.  (reps, minutes, power)
KM = [(1, 2, 18, 0.96), (2, 2, 22, 0.97), (3, 2, 25, 0.98), (4, 3, 20, 0.98)]
for lvl, reps, mins, pwr in KM:
    blocks = [B.warmup(900, 0.50, 0.75, 85, 95)]
    for r in range(1, reps + 1):
        blocks.append(B.steady(mins * 60, pwr, 85, 95))
        if r < reps:
            blocks.append(B.steady(600, 0.55, 85, 95))
    blocks.append(B.cooldown(600, 0.70, 0.50, 85, 95))
    emit(f"03_KolieMoore-TTE_L{lvl}_{reps}x{mins}min",
         desc("[Threshold / Time-to-Exhaustion - Kolie Moore, Empirical Cycling]", lvl,
              "-15min building Z1->Z2",
              f"-{reps}x {mins}min @{int(pwr*100)}% FTP (self-paced: start ~96%, float to 100-102% late)\n-10min @55% between\n-Cadence: 85-95rpm, relaxed",
              "Threshold / TTE at MLSS. Extends how LONG you hold FTP. Total time-at-threshold climbs each level.",
              "-Ride on feel, let power drift up at the end. Accumulating time near threshold matters more than a flat line.",
              "-60-80g carbs/hr from 30-45min.", "-500-750ml/hr."),
         blocks)


# ============================================================ 4. Over-unders (lactate tolerance)
# progress: blocks, sub-reps, over power.  (blocks, ou_reps, over_power)
OU = [(1, 3, 2, 1.03), (2, 3, 3, 1.05), (3, 4, 3, 1.05), (4, 3, 4, 1.06)]
for lvl, blks, ourep, over in OU:
    blocks = [B.warmup(900, 0.50, 0.80, 85, 95)]
    for b in range(1, blks + 1):
        blocks.append(B.intervals(ourep, 120, 0.95, 120, over, 90, 100,
                      msg=f"Block {b}/{blks}: under 95% -> over {int(over*100)}%, x{ourep}"))
        if b < blks:
            blocks.append(B.steady(300, 0.55, 85, 95))
    blocks.append(B.cooldown(600, 0.70, 0.50, 85, 95))
    emit(f"04_Over-Unders_L{lvl}_{blks}x{ourep*4}min",
         desc("[Lactate clearance / tolerance - over-unders]", lvl,
              "-15min building Z1->Z2",
              f"-{blks} blocks of {ourep*4}min: 2min @95% (under) / 2min @{int(over*100)}% (over), x{ourep}\n-5min @55% between blocks\n-Cadence: 90-100rpm",
              "Lactate clearance + threshold tolerance. Trains reprocessing lactate while still working hard.",
              "-Ramp into the over, don't surge. The unders are working recoveries - keep pressure on the pedals.",
              "-60g carbs/hr.", "-500-750ml/hr with electrolytes."),
         blocks)


# ============================================================ 5. Almquist Z2 + sprints
# progress: sprint sets + Z2 body.  (sets, lead_z2_s, tail_z2_s)
ALM = [(1, 2, 600, 600), (2, 3, 900, 900), (3, 3, 1200, 1200), (4, 4, 1200, 1500)]
for lvl, sets, lead, tail in ALM:
    blocks = [B.warmup(600, 0.50, 0.60, 85, 95), B.steady(lead, 0.62, 85, 95)]
    for s in range(1, sets + 1):
        blocks.append(B.intervals(3, 30, 2.00, 240, 0.60, 95, 110,
                      msg=f"Sprint set {s}/{sets}: 3x 30s ALL-OUT, spin easy between"))
        if s < sets:
            blocks.append(B.steady(360, 0.60, 85, 95))
    blocks += [B.steady(tail, 0.62, 85, 95), B.cooldown(300, 0.55, 0.45, 85, 95)]
    emit(f"05_Z2-Sprints_L{lvl}_{sets}sets",
         desc("[Sprint power + aerobic base - Almquist 'Z2 with sprints']", lvl,
              "-10min easing into Zone 2",
              f"-Zone 2 body @60-65% FTP\n-{sets} sets of 3x 30s ALL-OUT sprints (encoded ~200%; just go MAX)\n-~4min @60% between sprints, ~6min @60% between sets\n-Cadence: free; wind up big",
              "Neuromuscular sprint power + aerobic base in one ride, without adding a true hard day.",
              "-Sprints are genuinely maximal, out of the saddle. Keep the rest of the ride strictly easy.",
              "-60-90g carbs/hr on the Z2 body.", "-500-750ml/hr; long ride."),
         blocks)


# ============================================================ 6. Durability (fatigued threshold)
# progress: bridge length + fatigued block.  (bridge_s, fat_reps, fat_min, fat_pwr)
DUR = [(1, 3600, 2, 10, 0.95), (2, 5400, 2, 12, 0.96), (3, 7200, 2, 12, 0.98), (4, 9000, 3, 10, 0.98)]
for lvl, bridge, freps, fmin, fpwr in DUR:
    blocks = [B.warmup(600, 0.50, 0.65, 85, 95),
              B.intervals(2, 600, 0.95, 300, 0.55, 85, 95, msg="FRESH block: 2x10min @95% - note the feel"),
              B.steady(bridge, 0.60, 85, 95),
              B.intervals(freps, fmin * 60, fpwr, 360, 0.55, 85, 95,
                          msg=f"FATIGUED block: {freps}x{fmin}min @{int(fpwr*100)}% after the long Z2. The point of the session."),
              B.cooldown(600, 0.65, 0.50, 85, 95)]
    hrs = round((600 + 2 * 900 + bridge + freps * (fmin * 60 + 360) + 600) / 3600, 1)
    emit(f"06_Durability_L{lvl}_{hrs}hr",
         desc("[Fatigue resistance / durability - power AFTER fatigue]", lvl,
              "-10min easing to Z2",
              f"-FRESH: 2x10min @95%, 5min @55% between\n-BRIDGE: {bridge//60}min @60% FTP (accumulate kJ)\n-FATIGUED: {freps}x{fmin}min @{int(fpwr*100)}%, 6min @55% between\n-Cadence: 85-95rpm",
              "Durability. Identical efforts before and after a long Z2 block train the late-ride power fade that decides long events.",
              "-Compare fresh vs fatigued honestly. If the fatigued block craters, fix fueling first - it's usually the limiter, not fitness.",
              "-HIGH FUEL: 80-100g carbs/hr. Eat early, eat often.", "-750ml/hr+ with electrolytes."),
         blocks)


# ============================================================ 7. Big-gear torque (strength endurance)
# progress: reps, rep length, power, cadence.  (reps, minutes, power, rpm_low, rpm_high)
TRQ = [(1, 4, 4, 0.88, 55, 60), (2, 5, 5, 0.90, 50, 60), (3, 6, 5, 0.92, 50, 55), (4, 5, 6, 0.95, 48, 52)]
for lvl, reps, mins, pwr, rlo, rhi in TRQ:
    blocks = [B.warmup(900, 0.50, 0.70, 85, 95),
              B.intervals(reps, mins * 60, pwr, 180, 0.55, rlo, rhi,
                          msg=f"{reps}x{mins}min @{int(pwr*100)}% at {rlo}-{rhi}rpm BIG GEAR. Off: spin ~90rpm."),
              B.cooldown(600, 0.70, 0.50, 85, 95)]
    emit(f"07_BigGear-Torque_L{lvl}_{reps}x{mins}min",
         desc("[Strength endurance / force - low-cadence torque]", lvl,
              "-15min building Z1->Z2 at normal cadence",
              f"-{reps}x {mins}min @{int(pwr*100)}% FTP at {rlo}-{rhi}rpm (big gear)\n-3min @55% at free cadence between\n-NOTE: .zwo can't enforce rpm - shift to a big gear yourself",
              "Strength endurance / force production. Bridges gym to bike; doing the intervals at low cadence drives bigger FTP gains.",
              "-Seated, smooth, no rocking. Engage glutes/core. Stop a rep if knees complain - high joint load.",
              "-40-60g carbs/hr.", "-500-750ml/hr."),
         blocks)


print(f"Wrote {len(written)} progression files to {OUTDIR}")
for n in written:
    print(f"  - {n}")
