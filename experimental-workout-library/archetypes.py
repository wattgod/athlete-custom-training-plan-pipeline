#!/usr/bin/env python3
"""
ARCHETYPE CATALOG — the progressive library.

Each archetype is a base spec + a PRIMARY progression axis. The engine turns the
axis to emit a 4-level ladder; warm-up is auto-matched to the energy system. Names
and structures align with the house catalog (athlete-custom-training-plan-pipeline:
new_/imported_/advanced_archetypes.py — 95 archetypes / 22 categories / 6 levels).

Extensible by design: add one dict to ARCHETYPES → get a full validated ladder.

Run `python3 archetypes.py` → writes library/<category>/<id>_L<n>.zwo + LIBRARY.md.
"""
from pathlib import Path
import progression_engine as E

LEVELS = 6
OUT = Path(__file__).resolve().parent / "library"


def M(shape, **kw):
    """Main-set dict with sane cadence defaults."""
    kw.setdefault('clo', 90); kw.setdefault('chi', 100); kw['shape'] = shape
    return kw


# id, name, category, system, primary axis, step, source, purpose, main
ARCHETYPES = [
    # ---------------- ENDURANCE / AEROBIC BASE ----------------
    ('endurance_blocks', 'Endurance Blocks', 'endurance', 'endurance', 'work_duration', 900,
     'Seiler LIT / Z2 base', 'Aerobic base: mitochondrial density, fat oxidation, capillarisation.',
     M('sustained', on_dur=3600, on_pwr=0.65, clo=85, chi=95)),
    ('fatmax', 'FatMax Development', 'endurance', 'endurance', 'work_duration', 1200,
     'San Millán / FatMax', 'Maximise fat-oxidation rate; long, strictly low Z2.',
     M('sustained', on_dur=4800, on_pwr=0.60, clo=85, chi=95)),
    ('tempo_3x15', '3x15 Tempo', 'endurance', 'tempo', 'work_duration', 120,
     'Classic tempo', 'Sub-threshold aerobic load; muscular endurance with low fatigue cost.',
     M('constant', reps=3, on_dur=900, on_pwr=0.82, off_dur=300, off_pwr=0.55)),
    ('structured_fartlek', 'Structured Fartlek', 'endurance', 'tempo', 'reps', 2,
     'Structured fartlek', 'Aerobic ride broken by repeatable surges — race-like variability.',
     M('surges', on_dur=2400, surge_dur=60, surge_pwr=1.00, reps=6, base_pwr=0.66)),
    ('endurance_surges', 'Endurance with Surges', 'endurance', 'endurance', 'reps', 3,
     'Almquist sprints-in-Z2', 'Aerobic base + neuromuscular sharpness in one ride.',
     M('surges', on_dur=3600, surge_dur=30, surge_pwr=1.40, reps=6, base_pwr=0.62)),

    # ---------------- SWEET SPOT / G-SPOT ----------------
    ('gspot_intervals', 'G-Spot Intervals', 'sweetspot', 'sweetspot', 'work_duration', 120,
     'Coggan sweet spot (GG: G-SPOT)', 'Best adaptation:fatigue ratio — most threshold gain per unit stress.',
     M('constant', reps=3, on_dur=600, on_pwr=0.90, off_dur=300, off_pwr=0.55, clo=85, chi=95)),
    ('gspot_progressive', 'G-Spot Progressive', 'sweetspot', 'sweetspot', 'intensity', 0.02,
     'GG G-SPOT', 'Progressive sweet-spot — climbs toward threshold as fitness builds.',
     M('constant', reps=3, on_dur=600, on_pwr=0.88, off_dur=240, off_pwr=0.55, clo=85, chi=95)),
    ('gspot_criss_cross', 'G-Spot Criss-Cross', 'sweetspot', 'over_under', 'over_ceiling', 0.02,
     'GG G-SPOT', 'Sweet-spot floor with surges toward threshold — early lactate-tolerance work.',
     M('over_under', reps=4, on_dur=120, under_pwr=0.88, over_pwr=0.98, clo=85, chi=95,
       sets=2, between_sets_dur=240, between_sets_pwr=0.55)),

    # ---------------- THRESHOLD ----------------
    ('threshold_accumulation', 'Threshold Accumulation', 'threshold', 'threshold', 'work_duration', 120,
     'Coggan L4', 'Raise FTP/LT by accumulating time at threshold.',
     M('constant', reps=3, on_dur=600, on_pwr=0.98, off_dur=300, off_pwr=0.55, clo=85, chi=95)),
    ('float_sets', 'Float Sets', 'threshold', 'over_under', 'reps', 1,
     'Empirical Cycling floats', 'Threshold with brief floats — extend time-at-threshold without full rest.',
     M('over_under', reps=4, on_dur=120, under_pwr=0.90, over_pwr=1.02, clo=85, chi=95,
       sets=2, between_sets_dur=240, between_sets_pwr=0.55)),
    ('descending_threshold', 'Descending Threshold', 'threshold', 'threshold', 'work_duration', 60,
     'Descending threshold', 'Front-loaded threshold; teaches pacing and back-end durability.',
     M('descending_power', reps=4, on_dur=420, on_pwr=1.04, step=0.02, off_dur=180, off_pwr=0.55, clo=85, chi=95)),
    ('single_sustained', 'Single Sustained Threshold', 'threshold', 'threshold', 'work_duration', 300,
     'Kolie Moore TTE', 'One long block at MLSS — extend time-to-exhaustion at FTP.',
     M('sustained', on_dur=1200, on_pwr=0.96, clo=85, chi=95)),

    # ---------------- VO2MAX ----------------
    ('vo2_5x3_classic', '5x3 VO2 Classic', 'vo2max', 'vo2max', 'reps', 1,
     'Coggan L5', 'Classic VO2max stimulus — stroke volume and O2 kinetics.',
     M('constant', reps=5, on_dur=180, on_pwr=1.12, off_dur=180, off_pwr=0.50)),
    ('billat_30_30', 'VO2max 30/30 (Billat)', 'vo2max', 'vo2max', 'reps', 1,
     'Billat 30/30', 'Short-short intervals in series — bank T@VO2max at lower RPE.',
     M('micro', reps=6, on_dur=30, on_pwr=1.15, off_dur=30, off_pwr=0.50,
       sets=3, between_sets_dur=180, between_sets_pwr=0.50)),
    ('ronnestad_40_20', 'Ronnestad 40/20', 'vo2max', 'vo2max', 'reps', 1,
     'Ronnestad 40/20', 'Series of micro-intervals — high cumulative time >90% VO2max.',
     M('micro', reps=6, on_dur=40, on_pwr=1.12, off_dur=20, off_pwr=0.50, sets=3,
       between_sets_dur=240, between_sets_pwr=0.50)),
    ('hard_starts', 'Hard Starts', 'vo2max', 'vo2max', 'reps', 1,
     'Hard-start VO2 (Spare Cycles)', 'Opening surge drives VO2 to max sooner → more time at VO2max.',
     M('fast_start', reps=4, surge_dur=30, surge_pwr=1.35, on_dur=210, on_pwr=1.05, off_dur=240, off_pwr=0.50)),
    ('descending_vo2_pyramid', 'Descending VO2 Pyramid', 'vo2max', 'vo2max', 'intensity', 0.02,
     'Descending VO2 pyramid', 'Max-repeatable ladder — rep length falls so power stays high.',
     M('descending_dur', reps=5, on_dur=300, on_pwr=1.10, step=30, off_dur=180, off_pwr=0.50)),

    # ---------------- ANAEROBIC / GLYCOLYTIC ----------------
    ('anaerobic_2min_killers', '2min Killers', 'anaerobic', 'anaerobic', 'reps', 1,
     'Coggan L6', 'Anaerobic capacity — tolerance to high lactate, repeatable hard efforts.',
     M('constant', reps=5, on_dur=120, on_pwr=1.25, off_dur=300, off_pwr=0.50)),
    ('glycolytic_power', 'Glycolytic Power', 'anaerobic', 'anaerobic', 'reps', 1,
     'Glycolytic power', 'Maximise anaerobic (glycolytic) power production.',
     M('constant', reps=6, on_dur=60, on_pwr=1.45, off_dur=240, off_pwr=0.45)),
    ('above_cp_90s', 'Above-CP 90s Repeats', 'anaerobic', 'anaerobic', 'recovery_duration', 30,
     'Above-CP repeats', 'Repeated efforts above critical power — W′ drain and reload.',
     M('constant', reps=6, on_dur=90, on_pwr=1.18, off_dur=270, off_pwr=0.50)),
    ('wprime_depletion', 'W-Prime Depletion', 'anaerobic', 'anaerobic', 'density', 10,
     'Skiba W′bal', 'Deliberately drain W′ to near-zero — trains anaerobic work capacity.',
     M('constant', reps=4, on_dur=60, on_pwr=1.30, off_dur=60, off_pwr=0.50,
       sets=2, between_sets_dur=300, between_sets_pwr=0.50)),

    # ---------------- NEUROMUSCULAR / SPRINT ----------------
    ('sprint_buildups', 'Sprint Buildups', 'sprint', 'sprint', 'reps', 2,
     'Peak-power sprints', 'Neuromuscular peak power — rate coding, fibre synchronisation.',
     M('constant', reps=6, on_dur=12, on_pwr=1.90, off_dur=288, off_pwr=0.50, clo=95, chi=110)),
    ('attacks_repeatability', 'Attacks and Repeatability', 'sprint', 'anaerobic', 'reps', 2,
     'Attacks/repeatability', 'Repeatable race-winning attacks off a tempo base.',
     M('surges', on_dur=2400, surge_dur=20, surge_pwr=1.60, reps=8, base_pwr=0.78)),
    ('tempo_sprints', 'Tempo Sprints', 'sprint', 'sprint', 'surge_intensity', 0.10,
     'Tempo sprints', 'Sprint freshness on tired legs — sprint off a sustained tempo load.',
     M('surges', on_dur=3000, surge_dur=15, surge_pwr=1.80, reps=6, base_pwr=0.80)),

    # ---------------- DURABILITY / RACE SIM ----------------
    ('gravel_race_sim', 'Gravel Race Simulation', 'racesim', 'durability', 'reps', 2,
     'Gravel race simulation', 'Variable race demands over a long aerobic base — durability + repeatability.',
     M('surges', on_dur=5400, surge_dur=60, surge_pwr=1.05, reps=8, base_pwr=0.68, clo=85, chi=95)),
    ('criss_cross', 'Criss-Cross Intervals', 'racesim', 'over_under', 'reps', 1,
     'Criss-cross', 'Sustained over-unders — the saw-tooth of a hard paceline or climb.',
     M('over_under', reps=4, on_dur=90, under_pwr=0.85, over_pwr=1.05, clo=85, chi=95,
       sets=3, between_sets_dur=300, between_sets_pwr=0.55)),
    ('peak_and_fade', 'Peak and Fade', 'racesim', 'threshold', 'work_duration', 30,
     'Peak and fade', 'Start hard, hold as power fades — pacing under accumulating fatigue.',
     M('descending_power', reps=5, on_dur=240, on_pwr=1.10, step=0.04, off_dur=180, off_pwr=0.55, clo=85, chi=95)),

    # ---------------- DURABILITY (the broad category — efforts after accumulated fatigue) ----------------
    ('progressive_fatigue_threshold', 'Progressive Fatigue Threshold', 'durability', 'durability', 'prefatigue_time', 1200,
     'Progressive fatigue (durability)', 'Threshold reps placed after a growing Z2 pre-load — train hour-3 power.',
     M('constant', reps=3, on_dur=600, on_pwr=0.97, off_dur=300, off_pwr=0.55, clo=85, chi=95,
       prefatigue_dur=1800, prefatigue_pwr=0.63)),
    ('tired_threshold_repeats', 'Tired Threshold Repeats', 'durability', 'durability', 'prefatigue_time', 1200,
     'Tired threshold (durability)', 'Hold FTP repeats with pre-fatigued legs — fatigue-resistant threshold.',
     M('constant', reps=4, on_dur=300, on_pwr=1.00, off_dur=180, off_pwr=0.55, clo=85, chi=95,
       prefatigue_dur=2400, prefatigue_pwr=0.62)),
    ('tired_30_30', 'Tired 30/30s', 'durability', 'durability', 'prefatigue_time', 1200,
     'Tired 30/30 (durability)', 'VO2 micro-intervals in series after a Z2 block — top-end you can still access deep in a race.',
     M('micro', reps=6, on_dur=30, on_pwr=1.12, off_dur=30, off_pwr=0.50, clo=90, chi=100,
       sets=2, between_sets_dur=180, between_sets_pwr=0.55, prefatigue_dur=2400, prefatigue_pwr=0.62)),
    ('tired_vo2max', 'Tired VO2max', 'durability', 'durability', 'prefatigue_time', 1200,
     'Tired VO2 (durability)', 'VO2 efforts on fatigued legs — de-rated targets, race-realistic.',
     M('constant', reps=4, on_dur=180, on_pwr=1.08, off_dur=180, off_pwr=0.50, clo=85, chi=95,
       prefatigue_dur=2400, prefatigue_pwr=0.62)),
    ('tired_tempo', 'Tired Tempo', 'durability', 'durability', 'prefatigue_time', 1500,
     'Tired tempo (durability)', 'Sustained tempo deep into a long ride — the gravel/marathon default.',
     M('constant', reps=3, on_dur=600, on_pwr=0.84, off_dur=180, off_pwr=0.55, clo=85, chi=95,
       prefatigue_dur=3600, prefatigue_pwr=0.63)),
    ('loaded_recovery_vo2', 'VO2max with Loaded Recovery', 'durability', 'durability', 'recovery_intensity', 0.03,
     'Loaded recovery VO2 (durability)', 'VO2 reps with the float kept HIGH — W′ never fully reloads, fatigue compounds.',
     M('constant', reps=5, on_dur=180, on_pwr=1.10, off_dur=180, off_pwr=0.75, clo=90, chi=100)),
    ('fatigued_sprints', 'Fatigued Sprints', 'durability', 'durability', 'prefatigue_time', 1200,
     'Fatigued sprints (durability)', 'Maximal sprints deep in a ride — finishing-kick power when empty.',
     M('constant', reps=6, on_dur=12, on_pwr=1.85, off_dur=288, off_pwr=0.50, clo=95, chi=110,
       prefatigue_dur=4800, prefatigue_pwr=0.64)),
    ('double_day_sim', 'Double Day Simulation', 'durability', 'durability', 'prefatigue_time', 1800,
     'Double-day sim (durability)', 'Big Z2 pre-load then a threshold block — back-to-back race-day fatigue.',
     M('constant', reps=2, on_dur=900, on_pwr=0.96, off_dur=300, off_pwr=0.55, clo=85, chi=95,
       prefatigue_dur=5400, prefatigue_pwr=0.62)),
    ('late_race_vo2', 'Late-Race VO2max', 'durability', 'durability', 'prefatigue_time', 1200,
     'Late-race VO2 (durability)', 'VO2 efforts after accumulated work — the race-winning move when tired.',
     M('constant', reps=4, on_dur=180, on_pwr=1.10, off_dur=180, off_pwr=0.50, clo=85, chi=95,
       prefatigue_dur=2400, prefatigue_pwr=0.62)),

    # ---------------- TEST / SPECIALTY ----------------
    ('pre_race_openers', 'Pre-Race Openers', 'specialty', 'vo2max', 'reps', 1,
     'Openers', 'Prime the legs the day before racing — short, sharp, no fatigue.',
     M('constant', reps=3, on_dur=30, on_pwr=1.15, off_dur=300, off_pwr=0.55)),
    ('high_cadence', 'High Cadence Intervals', 'specialty', 'legspeed', 'work_duration', 60,
     'High-cadence base', 'Neuromuscular firing rate and pedalling efficiency at 100-120rpm.',
     M('constant', reps=4, on_dur=300, on_pwr=0.80, off_dur=120, off_pwr=0.55, clo=110, chi=120)),
    ('heat_acclimation', 'Heat Acclimation Protocol', 'specialty', 'endurance', 'work_duration', 600,
     'Heat acclimation', 'Sustained moderate load to drive heat adaptation (run hot, overdress).',
     M('sustained', on_dur=3000, on_pwr=0.68, clo=85, chi=95)),
]


CAT_LABEL = {'endurance': 'Endurance', 'sweetspot': 'Sweet Spot', 'threshold': 'Threshold',
             'vo2max': 'VO2max', 'anaerobic': 'Anaerobic', 'sprint': 'Sprint',
             'durability': 'Durability', 'racesim': 'Race Sim', 'specialty': 'Specialty'}


def label(a, lvl, mins, rpe_peak):
    """Self-describing filename + in-app name: Category - Name - <level> - mins - RPE.
    Leads with the category word (never a number) so a progression's levels group
    in the TrainingPeaks library; level is a plain number (1, 2, 3...)."""
    cat = CAT_LABEL.get(a[2], a[2].title())
    name = a[1].replace('/', '-')                       # 30/30 -> 30-30 (filename-safe, XML-safe)
    prefix = "" if name.lower().startswith(cat.lower().split()[0]) else f"{cat} - "
    rpe = rpe_peak.replace('RPE ', 'RPE')               # "RPE 8-9" -> "RPE8-9"
    return f"{prefix}{name} - {lvl} - {mins}min - {rpe}"


# how to ride each system — plain instruction, no justification
SYSTEM_CUE = {
    'endurance': "Easy and conversational the whole way.",
    'tempo': "Steady and comfortable — hold the power, relax the upper body.",
    'sweetspot': "Comfortably hard. Settle in, stay smooth.",
    'threshold': "Pace it so the last rep matches the first. Controlled, not heroic.",
    'over_under': "Stay smooth across the under/over change; keep pressure on the pedals on the unders.",
    'vo2max': "Hit target from the start; easy, full recoveries. End the set if the power fades.",
    'anaerobic': "Commit to each effort, rest fully between.",
    'sprint': "Maximal on every sprint, spin easy between.",
    'durability': "Hold target on the efforts even on tired legs. Keep eating.",
    'legspeed': "Fast, smooth, quiet hips — let the legs spin.",
}


def fuel(mins):
    if mins >= 150: return "-High fuel: 80-100g carbs/hr, start early."
    if mins >= 90:  return "-60-90g carbs/hr."
    if mins >= 60:  return "-40-60g carbs/hr."
    return "-Hydrate well; light fuel."


# Rule #15 dimensions — position & terrain by system (zones/cadence/effort auto-derived)
POS = {'endurance': 'seated', 'tempo': 'seated', 'sweetspot': 'seated', 'threshold': 'seated/aero',
       'over_under': 'seated', 'vo2max': 'seated', 'anaerobic': 'seated/standing', 'sprint': 'standing',
       'durability': 'seated', 'legspeed': 'seated'}
TERR = {'endurance': 'flat/rolling', 'tempo': 'rolling', 'sweetspot': 'climbing', 'threshold': 'climbing',
        'over_under': 'climbing', 'vo2max': 'climbing', 'anaerobic': 'rolling', 'sprint': 'flat',
        'durability': 'rolling/mixed', 'legspeed': 'flat'}
EFFORT = {'sustained': 'steady', 'constant': 'intervals', 'micro': 'micro-bursts',
          'over_under': 'over/under surges', 'fast_start': 'fast-start', 'descending_power': 'descending',
          'descending_dur': 'descending', 'surges': 'attack/recover surges'}


def dims_line(a, dd):
    effort = EFFORT.get(a[8].get('shape', 'constant'), 'intervals')
    return (f"zones {dd['zones']} · {dd['cadence']} · {POS.get(a[3], 'seated')} · "
            f"{TERR.get(a[3], 'rolling')} · {effort}")


def desc(a, lvl, dd, mins):
    cue = SYSTEM_CUE.get(a[3], "Hold the targets, keep it smooth.")
    return (f"{a[1]} — level {lvl}\n\n"
            f"WARM-UP:\n{dd['warmup']}\n\n"
            f"MAIN SET:\n{dd['main']}\n\n"
            f"COOL-DOWN:\n{dd['cooldown']}\n\n"
            f"HOW TO RIDE IT:\n-{cue}\n\n"
            f"DIMENSIONS:\n-{dims_line(a, dd)}\n\n"
            f"FUEL:\n{fuel(mins)}")


def main():
    # clean stale .zwo (filenames changed) so the folder only holds current labels
    if OUT.exists():
        for f in OUT.rglob('*.zwo'):
            f.unlink()
    rows = []
    count = 0
    for a in ARCHETYPES:
        aid, name, cat, system, axis, step = a[0], a[1], a[2], a[3], a[4], a[5]
        base = {'system': system, 'cooldown_dur': 600, 'main': dict(a[8])}
        l1 = l4 = None
        for s in E.progress(base, axis, LEVELS, step):
            lvl = s['_level']
            segs, _ = E.assemble(s)
            d = E.dose(segs)
            dd = E.describe(s)
            E.render(s, OUT / cat, label(a, lvl, d['min'], dd['rpe_peak']), desc(a, lvl, dd, d['min']))
            count += 1
            info = {'tss': d['tss'], 'min': d['min'], 'rpe': dd['rpe_peak']}
            if lvl == 1: l1 = info
            if lvl == LEVELS: l4 = info
        rows.append((cat, name, system, axis, a[7], l1, l4))
    write_catalog(rows, count)
    print(f"Wrote {count} archetype files across {len(set(r[0] for r in rows))} categories to {OUT}")


def write_catalog(rows, count):
    cats = {}
    for r in rows:
        cats.setdefault(r[0], []).append(r)
    lines = ["# Progressive Archetype Library\n",
             f"{count} files — {len(rows)} archetypes × {LEVELS} levels — generated by `archetypes.py` "
             "via `progression_engine.py`. Aligned to the house catalog "
             "(95 archetypes / 22 categories in the coaching pipeline).\n",
             "**Everything is % of FTP** (set your FTP in-app); each block carries an **RPE** for feel. "
             "Each archetype progresses along ONE primary axis (see "
             "`FUNDAMENTALS_interval-manipulation.md`). **TSS is FTP-independent** "
             "(IF²·hrs·100); kJ and W′bal need a real FTP and are computed by the engine "
             "when the pipeline supplies one — never baked in at a fake reference.\n",
             "Extensible: add a dict to `ARCHETYPES` → get a validated ladder.\n"]
    for cat in sorted(cats):
        lines.append(f"\n## {cat.upper()}\n")
        lines.append(f"| Archetype | System | Primary axis | L1→L{LEVELS} TSS | L1→L{LEVELS} min | Peak RPE | Source |")
        lines.append("|-----------|--------|--------------|-----------|-----------|----------|--------|")
        for _, name, system, axis, src, l1, l4 in cats[cat]:
            lines.append(f"| {name} | {system} | `{axis}` | {l1['tss']}→{l4['tss']} | "
                         f"{l1['min']}→{l4['min']} | {l4['rpe']} | {src} |")
    (OUT).mkdir(parents=True, exist_ok=True)
    (OUT / "LIBRARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == '__main__':
    main()
