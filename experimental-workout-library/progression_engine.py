#!/usr/bin/env python3
"""
PROGRESSION ENGINE — axis-driven structured-workout generator.

Difficulty is not one knob. A workout is a SPEC (warm-up template + a main set of
named parameters); progression happens by turning one or more NAMED AXES. Each axis
maps to a distinct physiological lever (see FUNDAMENTALS_interval-manipulation.md).

House pattern (from athlete-custom-training-plan-pipeline/advanced-archetypes.py):
"compute segments programmatically, never enumerate by hand." Everything here is a
list of segment dicts -> rendered to ZWO via build_zwo.py, with TSS/kJ computed from
the same segments so prefatigue can be sized by ENERGY BURNED, not just minutes.

Axes (registry below): intensity, work_duration, recovery_duration,
recovery_intensity, reps, sets, density, cadence, prefatigue_kj, shape.

Run `python3 progression_engine.py` to generate engine_demo/ and print a TSS/kJ
table proving each axis changes the dose in the expected direction.
"""
from copy import deepcopy
from pathlib import Path
import build_zwo as B

FTP_REF = 250  # watts, for kJ math only (TSS is FTP-independent)


# ======================================================================
# SEGMENT MODEL  — one flat list of dicts describes warm-up + main + cooldown
# ======================================================================
# kinds: 'warmup'/'cooldown' (ramp plo->phi), 'steady' (pwr), 'interval' (reps on/off)

def seg_steady(dur, pwr, clo=85, chi=95):
    return {'kind': 'steady', 'dur': dur, 'pwr': pwr, 'clo': clo, 'chi': chi}

def seg_warm(dur, plo, phi, clo=85, chi=95):
    return {'kind': 'warmup', 'dur': dur, 'plo': plo, 'phi': phi, 'clo': clo, 'chi': chi}

def seg_cool(dur, plo, phi, clo=85, chi=95):
    return {'kind': 'cooldown', 'dur': dur, 'plo': plo, 'phi': phi, 'clo': clo, 'chi': chi}

def seg_int(reps, on_dur, on_pwr, off_dur, off_pwr, clo=90, chi=100, msg=None):
    return {'kind': 'interval', 'reps': reps, 'on_dur': on_dur, 'on_pwr': on_pwr,
            'off_dur': off_dur, 'off_pwr': off_pwr, 'clo': clo, 'chi': chi, 'msg': msg}


def render_block(s):
    if s['kind'] == 'warmup':
        return B.warmup(s['dur'], s['plo'], s['phi'], s['clo'], s['chi'])
    if s['kind'] == 'cooldown':
        return B.cooldown(s['dur'], s['plo'], s['phi'], s['clo'], s['chi'])
    if s['kind'] == 'steady':
        return B.steady(s['dur'], s['pwr'], s['clo'], s['chi'])
    if s['kind'] == 'interval':
        return B.intervals(s['reps'], s['on_dur'], s['on_pwr'], s['off_dur'],
                           s['off_pwr'], s['clo'], s['chi'], s.get('msg'))
    raise ValueError(s['kind'])


# ======================================================================
# DOSE MATH  — TSS and kJ from segments (steady-state IF == power fraction)
# ======================================================================

def _seg_tss_kj(s, ftp):
    """Return (tss, kj) for one segment."""
    if s['kind'] in ('warmup', 'cooldown'):
        avg = (s['plo'] + s['phi']) / 2
        tss = (s['dur'] / 3600) * avg ** 2 * 100
        kj = avg * ftp * s['dur'] / 1000
        return tss, kj
    if s['kind'] == 'steady':
        tss = (s['dur'] / 3600) * s['pwr'] ** 2 * 100
        kj = s['pwr'] * ftp * s['dur'] / 1000
        return tss, kj
    if s['kind'] == 'interval':
        on_t = (s['on_dur'] / 3600) * s['on_pwr'] ** 2 * 100 * s['reps']
        off_t = (s['off_dur'] / 3600) * s['off_pwr'] ** 2 * 100 * s['reps']
        kj = (s['on_pwr'] * s['on_dur'] + s['off_pwr'] * s['off_dur']) * s['reps'] * ftp / 1000
        return on_t + off_t, kj
    return 0, 0


def dose(segments, ftp=FTP_REF):
    tss = kj = secs = 0
    for s in segments:
        t, k = _seg_tss_kj(s, ftp)
        tss += t; kj += k
        secs += s['dur'] if s['kind'] != 'interval' else s['reps'] * (s['on_dur'] + s['off_dur'])
    return {'tss': round(tss), 'kj': round(kj), 'min': round(secs / 60)}


def kj_to_minutes(target_kj, pwr_frac, ftp=FTP_REF):
    """How long to ride at pwr_frac to burn target_kj — sizes prefatigue by ENERGY."""
    watts = pwr_frac * ftp
    return round(target_kj * 1000 / watts / 60)


# ----- the two accounting backbones (FUNDAMENTALS levers 1-9) -----

def _expand_to_power_trace(segments, dt=1):
    """Flatten segments into a list of per-dt power fractions (intervals unrolled)."""
    trace = []
    for s in segments:
        if s['kind'] in ('warmup', 'cooldown'):
            n = max(1, s['dur'] // dt)
            for i in range(n):
                trace.append(s['plo'] + (s['phi'] - s['plo']) * i / max(1, n - 1))
        elif s['kind'] == 'steady':
            trace += [s['pwr']] * max(1, s['dur'] // dt)
        elif s['kind'] == 'interval':
            for _ in range(s['reps']):
                trace += [s['on_pwr']] * max(1, s['on_dur'] // dt)
                trace += [s['off_pwr']] * max(1, s['off_dur'] // dt)
    return trace


def wbal_nadir(segments, cp_frac=None, w_prime_kj=20.0, ftp=FTP_REF,
               tau_a=546.0, tau_b=316.0, tau_c=0.01, dt=1):
    """Skiba differential W'bal — returns the minimum (nadir) W'bal in kJ.

    Drains linearly above CP, refills exponentially below with
    tau = tau_a*exp(-tau_c*D_CP) + tau_b  (D_CP = CP watts - P watts).
    CP defaults to FTP/0.96. A nadir near 0 means the last rep is the limiter
    (good design); a large negative means the set is over-cooked. tau is tunable
    (constants fit to a 7-subject 2012 cohort).
    """
    cp = (cp_frac if cp_frac is not None else 1 / 0.96) * ftp
    w_prime = w_prime_kj * 1000.0
    bal = w_prime
    nadir = w_prime
    for p_frac in _expand_to_power_trace(segments, dt):
        p = p_frac * ftp
        if p > cp:
            bal -= (p - cp) * dt
        else:
            d_cp = cp - p
            tau = tau_a * (2.718281828 ** (-tau_c * d_cp)) + tau_b
            bal += (w_prime - bal) * (1 - 2.718281828 ** (-dt / tau))
        nadir = min(nadir, bal)
    return round(nadir / 1000, 1)  # kJ


def t_at_vo2max_proxy(segments, vo2_floor=1.06, dt=1):
    """PROXY for T@VO2max: seconds spent >= vo2_floor (default 106% FTP).

    Honest caveat: true T@VO2max depends on VO2 ON-kinetics (it takes ~1-2min to
    arrive), so this power-threshold proxy OVER-counts short reps and UNDER-counts
    the post-rep VO2 tail. Use it to compare designs, not as a physiological truth.
    """
    return sum(1 for p in _expand_to_power_trace(segments, dt) if p >= vo2_floor) * dt


# ======================================================================
# WARM-UP TEMPLATE LIBRARY  (research-backed; 11-19 min; keyed to main set)
# ======================================================================

def _wu_z2_lift():                                        # 10min — aerobic work needs no primer, just a lift
    return [seg_warm(600, 0.50, 0.65, 85, 92)]            # Z1 -> Z2, that's it

def _wu_easy_raise():                                     # 11min — sub-threshold that wants a touch more prep
    return [seg_warm(300, 0.50, 0.60, 85, 90), seg_steady(240, 0.65, 90, 90),
            seg_steady(60, 0.65, 90, 110), seg_steady(60, 0.55, 90, 90)]

def _wu_vo2_primer():                                     # 19min — VO2 / 30-15 / hard start (priming)
    return [seg_warm(300, 0.50, 0.70, 90, 95), seg_steady(360, 0.88, 90, 95),
            seg_steady(180, 0.50, 95, 100),
            seg_int(3, 20, 1.25, 40, 0.50, 100, 105, "Potentiation bursts: 3x20s, speeds VO2 on-kinetics"),
            seg_steady(120, 0.50, 95, 100)]                # MUST settle — never end on a burst

def _wu_threshold_feel():                                 # 12min — threshold/over-under/FTP test
    return [seg_warm(360, 0.50, 0.75, 90, 95), seg_steady(90, 0.90, 90, 95),
            seg_steady(30, 0.55, 95, 100), seg_steady(90, 0.95, 90, 95),
            seg_steady(30, 0.55, 95, 100), seg_steady(120, 0.60, 90, 95)]

def _wu_sprint_primer():                                  # ~13min — sprint / peak power
    return [seg_warm(300, 0.50, 0.65, 90, 95), seg_steady(90, 0.60, 100, 110),
            seg_steady(10, 1.50, 95, 105), seg_steady(110, 0.50, 90, 95),
            seg_steady(10, 1.80, 100, 110), seg_steady(110, 0.50, 90, 95),
            seg_steady(8, 2.20, 105, 115), seg_steady(140, 0.50, 90, 95)]

def _wu_torque_contrast():                                # 12min — low-cadence torque
    return [seg_warm(240, 0.50, 0.65, 90, 95), seg_steady(180, 0.80, 100, 110),
            seg_steady(120, 0.70, 75, 95), seg_steady(120, 0.75, 58, 62),
            seg_steady(60, 0.55, 95, 100)]

def _wu_tt_short():                                       # 15min — TT / prologue / test
    return [seg_steady(300, 0.50, 90, 95), seg_warm(240, 0.60, 1.00, 90, 95),
            seg_steady(60, 0.50, 95, 100),
            seg_int(3, 6, 1.60, 54, 0.50, 100, 110, "PAP sprints: 3x6s"),
            seg_steady(120, 0.50, 90, 95)]

def _wu_legspeed():                                       # 13min — high-cadence / efficiency
    return [seg_warm(240, 0.50, 0.60, 90, 95),
            seg_int(3, 45, 0.60, 75, 0.60, 110, 125, "Leg-speed spin-ups: 3x45s @110-125rpm"),
            seg_steady(120, 0.55, 95, 100), seg_steady(60, 0.55, 90, 95)]

def _wu_crit_opener():                                    # 19min — crit/CX/fast mass-start
    return [seg_warm(300, 0.50, 0.70, 90, 95), seg_steady(60, 0.80, 90, 95),
            seg_warm(300, 0.80, 0.90, 90, 95),
            seg_steady(45, 1.20, 95, 100), seg_steady(75, 0.50, 90, 95),
            seg_steady(20, 1.60, 100, 105), seg_steady(100, 0.50, 90, 95),
            seg_steady(8, 2.20, 105, 110), seg_steady(82, 0.50, 90, 95),
            seg_steady(150, 0.50, 90, 95)]

WARMUPS = {
    'z2_lift': _wu_z2_lift, 'easy_raise': _wu_easy_raise, 'vo2_primer': _wu_vo2_primer,
    'threshold_feel': _wu_threshold_feel, 'sprint_primer': _wu_sprint_primer,
    'torque_contrast': _wu_torque_contrast, 'tt_short': _wu_tt_short,
    'legspeed': _wu_legspeed, 'crit_opener': _wu_crit_opener,
}

# auto-match warm-up to the main set's energy system.
# Aerobic/sub-threshold work just lifts Z1->Z2 (no primer); only hard work gets a real warm-up.
WU_FOR = {
    'endurance': 'z2_lift', 'tempo': 'z2_lift', 'sweetspot': 'z2_lift', 'durability': 'z2_lift',
    'threshold': 'threshold_feel', 'over_under': 'threshold_feel',
    'vo2max': 'vo2_primer', 'anaerobic': 'vo2_primer',
    'sprint': 'sprint_primer', 'neuromuscular': 'sprint_primer',
    'torque': 'torque_contrast', 'strength_endurance': 'torque_contrast',
    'test': 'tt_short', 'legspeed': 'legspeed',
}


# ======================================================================
# MAIN-SET BUILDER  — a spec's main set -> segments (supports sets, prefatigue, shape)
# ======================================================================

# --- shape handlers (one set's worth of segments) — ported from house helpers ---

def _sh_constant(m, tag):           # IntervalsT; 'micro' (30/15) is the same renderer
    return [seg_int(m['reps'], m['on_dur'], m['on_pwr'], m['off_dur'], m['off_pwr'],
                    m['clo'], m['chi'], m.get('msg', f"{m['reps']}x main set{tag}"))]

def _sh_over_under(m, tag):         # under/over saw-tooth (reps = #pairs)
    return [seg_int(m['reps'], m['on_dur'], m['under_pwr'], m['on_dur'], m['over_pwr'],
                    m['clo'], m['chi'],
                    f"Over-under{tag}: under {int(m['under_pwr']*100)}% / over {int(m['over_pwr']*100)}%")]

def _sh_fast_start(m, tag):         # each rep: hard surge -> settle, then recovery
    segs = []
    for i in range(m['reps']):
        segs.append(seg_steady(m['surge_dur'], m['surge_pwr'], m['clo'], m['chi']))
        segs.append(seg_steady(m['on_dur'], m['on_pwr'], m['clo'], m['chi']))
        if i < m['reps'] - 1:
            segs.append(seg_steady(m['off_dur'], m['off_pwr'], 85, 95))
    return segs

def _sh_descending_power(m, tag):   # same dur, power steps DOWN each rep
    segs = []
    for i in range(m['reps']):
        segs.append(seg_steady(m['on_dur'], round(m['on_pwr'] - m['step'] * i, 3), m['clo'], m['chi']))
        if i < m['reps'] - 1:
            segs.append(seg_steady(m['off_dur'], m['off_pwr'], 85, 95))
    return segs

def _sh_descending_dur(m, tag):     # same power, duration steps DOWN each rep (max-repeatable ladder)
    segs = []
    for i in range(m['reps']):
        segs.append(seg_steady(max(10, m['on_dur'] - m['step'] * i), m['on_pwr'], m['clo'], m['chi']))
        if i < m['reps'] - 1:
            segs.append(seg_steady(m['off_dur'], m['off_pwr'], 85, 95))
    return segs

def _sh_sustained(m, tag):          # one long block (TTE / single sustained)
    return [seg_steady(m['on_dur'], m['on_pwr'], m['clo'], m['chi'])]

def _sh_surges(m, tag):             # base ride with short surges evenly distributed
    total, eff = m['on_dur'], m['surge_dur']      # on_dur = total block; surge_dur each
    n = m['reps']; base_p = m.get('base_pwr', 0.65)
    gap = (total - eff * n) // (n + 1)
    segs = [seg_steady(gap, base_p, m['clo'], m['chi'])]
    for i in range(n):
        segs.append(seg_steady(eff, m['surge_pwr'], m['clo'], m['chi']))
        segs.append(seg_steady(gap, base_p, m['clo'], m['chi']))
    return segs

SHAPES = {'constant': _sh_constant, 'micro': _sh_constant, 'over_under': _sh_over_under,
          'fast_start': _sh_fast_start, 'descending_power': _sh_descending_power,
          'descending_dur': _sh_descending_dur, 'sustained': _sh_sustained, 'surges': _sh_surges}


def build_main(m):
    segs = []
    # prefatigue Z2 block (durability axis) — sized in minutes (set directly or via kJ)
    if m.get('prefatigue_dur', 0) > 0:
        segs.append(seg_steady(m['prefatigue_dur'], m.get('prefatigue_pwr', 0.62), 85, 95))
    sets = m.get('sets', 1)
    handler = SHAPES[m.get('shape', 'constant')]
    for si in range(sets):
        tag = f" (set {si+1}/{sets})" if sets > 1 else ""
        segs += handler(m, tag)
        if si < sets - 1:
            segs.append(seg_steady(m.get('between_sets_dur', 180),
                                   m.get('between_sets_pwr', 0.50), 85, 95))
    return segs


def assemble_parts(spec):
    """spec -> (warmup_segs, main_segs, cooldown_segs, warmup_key)."""
    wu_key = spec.get('warmup') or WU_FOR.get(spec['system'], 'easy_raise')
    wu = list(WARMUPS[wu_key]())
    main = build_main(spec['main'])
    cool = [seg_cool(spec.get('cooldown_dur', 600), 0.70, 0.50, 85, 95)]
    return wu, main, cool, wu_key


def assemble(spec):
    """spec -> full segment list (warm-up + main + cooldown)."""
    wu, main, cool, wu_key = assemble_parts(spec)
    return wu + main + cool, wu_key


# ======================================================================
# RPE + %FTP DESCRIPTION  — house v6.0 bands (workouts are %FTP, never absolute watts)
# ======================================================================

def rpe(pwr):
    """Power fraction -> RPE band (Gravel God / Coggan zone mapping)."""
    if pwr < 0.56:  return "RPE 1-2"   # recovery / Z1
    if pwr < 0.76:  return "RPE 2-3"   # endurance / Z2
    if pwr < 0.88:  return "RPE 3-4"   # tempo / Z3
    if pwr <= 0.94: return "RPE 5-6"   # sweet spot
    if pwr <= 1.05: return "RPE 6-7"   # threshold / Z4
    if pwr <= 1.20: return "RPE 8-9"   # VO2max / Z5
    if pwr <= 1.50: return "RPE 9-10"  # anaerobic / Z6
    return "RPE 10"                    # neuromuscular / sprint


def _fmt(sec):
    if sec < 60:        return f"{sec}s"
    if sec % 60 == 0:   return f"{sec // 60}min"
    return f"{sec // 60}:{sec % 60:02d}"


def _pct(p):
    return f"{round(p * 100)}%"


def zone(p):
    """Coggan classic level label."""
    if p < 0.56:  return "Z1"
    if p < 0.76:  return "Z2"
    if p < 0.91:  return "Z3"
    if p <= 1.05: return "Z4"
    if p <= 1.20: return "Z5"
    if p <= 1.50: return "Z6"
    return "Z7"


def _rng(p):
    """Target as a Coggan-zone range (or single % for Z6/Z7)."""
    b = B.band(p)
    return _pct(p) if b is None else f"{_pct(b[0])}-{_pct(b[1])}"


def _line(s):
    """One human-readable line per segment — Coggan-zone %FTP range + RPE + cadence."""
    if s['kind'] in ('warmup', 'cooldown'):
        verb = 'ramp' if s['kind'] == 'warmup' else 'spin-down'
        return f"-{_fmt(s['dur'])} {verb} {_pct(s['plo'])}->{_pct(s['phi'])} FTP ({rpe((s['plo']+s['phi'])/2)})"
    if s['kind'] == 'steady':
        return f"-{_fmt(s['dur'])} @ {_rng(s['pwr'])} FTP ({zone(s['pwr'])}, {rpe(s['pwr'])}, {s['clo']}-{s['chi']}rpm)"
    # interval
    return (f"-{s['reps']}x {_fmt(s['on_dur'])} @ {_rng(s['on_pwr'])} FTP ({zone(s['on_pwr'])}, {rpe(s['on_pwr'])}, {s['clo']}-{s['chi']}rpm)"
            f" / {_fmt(s['off_dur'])} @ {_rng(s['off_pwr'])} ({zone(s['off_pwr'])}, {rpe(s['off_pwr'])})")


def cad_label(clo, chi):
    """Cadence dimension (Rule #15): low <70, normal 85-95, high >100."""
    c = (clo + chi) / 2
    if c < 70:   return "low cadence"
    if c >= 100: return "high cadence"
    return "normal cadence"


def zones_touched(main):
    """Power-zone dimension — which Coggan zones the MAIN set hits (warm-up excluded)."""
    zs = set()
    for s in main:
        if s['kind'] == 'steady':
            zs.add(zone(s['pwr']))
        elif s['kind'] == 'interval':
            zs.add(zone(s['on_pwr'])); zs.add(zone(s['off_pwr']))
    order = ['Z1', 'Z2', 'Z3', 'Z4', 'Z5', 'Z6', 'Z7']
    present = [z for z in order if z in zs]
    if not present:
        return "-"
    return present[0] if len(present) == 1 else f"{present[0]}-{present[-1]}"


def describe(spec):
    """Structured WARM-UP / MAIN SET / COOL-DOWN text in %FTP + RPE, plus dimension data."""
    wu, main, cool, _ = assemble_parts(spec)
    rng = [rpe(p) for p in _expand_to_power_trace(main)]
    work = max(main, key=lambda s: s.get('on_pwr', s.get('pwr', 0)))    # the hardest block
    out = {
        'warmup': "\n".join(_line(s) for s in wu),
        'main': "\n".join(_line(s) for s in main),
        'cooldown': "\n".join(_line(s) for s in cool),
        'rpe_peak': max(rng, key=lambda r: int(r.split()[-1].split('-')[-1])) if rng else "RPE 1",
        'zones': zones_touched(main),
        'cadence': cad_label(work['clo'], work['chi']),
    }
    return out


# ======================================================================
# AXES REGISTRY  — each turns ONE physiological lever. (main_dict, level, step) -> mutate
# level 1 == base (no change); level n applies (n-1)*step.
# ======================================================================

def _ax_intensity(m, lvl, step):        m['on_pwr'] = round(m['on_pwr'] + step * (lvl - 1), 3)
def _ax_work_duration(m, lvl, step):    m['on_dur'] = int(m['on_dur'] + step * (lvl - 1))
def _ax_recovery_duration(m, lvl, step):m['off_dur'] = max(5, int(m['off_dur'] - step * (lvl - 1)))
def _ax_recovery_intensity(m, lvl, step):m['off_pwr'] = round(m['off_pwr'] + step * (lvl - 1), 3)
def _ax_reps(m, lvl, step):             m['reps'] = int(m['reps'] + step * (lvl - 1))
def _ax_sets(m, lvl, step):             m['sets'] = int(m.get('sets', 1) + step * (lvl - 1))
def _ax_cadence(m, lvl, step):          m['clo'] = int(m['clo'] - step*(lvl-1)); m['chi'] = int(m['chi'] - step*(lvl-1))
def _ax_prefatigue_time(m, lvl, step):  # step = SECONDS of Z2 pre-load added per level (FTP-independent)
    m['prefatigue_dur'] = m.get('prefatigue_dur', 0) + int(step * (lvl - 1))
def _ax_prefatigue_kj(m, lvl, step):    # step = kJ/level; needs a real FTP (pipeline) — illustrative at FTP_REF
    add_kj = step * (lvl - 1)
    m['prefatigue_dur'] = m.get('prefatigue_dur', 0) + kj_to_minutes(add_kj, m.get('prefatigue_pwr', 0.62)) * 60
def _ax_density(m, lvl, step):          # shrink recovery AND add a rep each level (work:rest up)
    m['off_dur'] = max(5, int(m['off_dur'] - step * (lvl - 1))); m['reps'] = int(m['reps'] + (lvl - 1))
def _ax_over_ceiling(m, lvl, step):     # over-unders: raise the 'over' ceiling each level
    m['over_pwr'] = round(m['over_pwr'] + step * (lvl - 1), 3)
def _ax_surge_intensity(m, lvl, step):  # surges/fast-start: raise the surge power each level
    m['surge_pwr'] = round(m['surge_pwr'] + step * (lvl - 1), 3)

AXES = {
    'intensity': _ax_intensity, 'work_duration': _ax_work_duration,
    'recovery_duration': _ax_recovery_duration, 'recovery_intensity': _ax_recovery_intensity,
    'reps': _ax_reps, 'sets': _ax_sets, 'cadence': _ax_cadence,
    'prefatigue_time': _ax_prefatigue_time, 'prefatigue_kj': _ax_prefatigue_kj,
    'density': _ax_density, 'over_ceiling': _ax_over_ceiling, 'surge_intensity': _ax_surge_intensity,
}


def progress(spec, axis, levels, step):
    """Return [spec_L1 .. spec_Ln], each with `axis` advanced one notch."""
    out = []
    for lvl in range(1, levels + 1):
        s = deepcopy(spec)
        AXES[axis](s['main'], lvl, step)
        s['_axis'] = axis; s['_level'] = lvl
        out.append(s)
    return out


# ======================================================================
# RENDER
# ======================================================================

def render(spec, out_dir, filename, description):
    B.OUT = Path(out_dir); B.OUT.mkdir(parents=True, exist_ok=True)
    segs, wu_key = assemble(spec)
    blocks = [render_block(s) for s in segs]
    B.build(filename, description, blocks)
    return dose(segs), wu_key


# ======================================================================
# DEMO — prove each axis moves the dose
# ======================================================================
if __name__ == '__main__':
    OUT = Path(__file__).resolve().parent / 'engine_demo'

    # base: classic 4x4min VO2max @106%, 4min recovery
    base = {
        'system': 'vo2max', 'cooldown_dur': 600,
        'main': {'reps': 4, 'on_dur': 240, 'on_pwr': 1.06, 'off_dur': 240,
                 'off_pwr': 0.50, 'clo': 90, 'chi': 100, 'sets': 1},
    }

    demos = [
        ('intensity', 4, 0.04),          # 106 -> 118% FTP
        ('work_duration', 4, 30),        # 4 -> 5.5 min reps
        ('recovery_duration', 4, 45),    # 4min -> 1.75min recovery (denser)
        ('reps', 4, 1),                  # 4 -> 7 reps
        ('prefatigue_kj', 4, 300),       # +0 -> +900 kJ of Z2 before the set (durability)
    ]

    print(f"{'axis':<20}{'L':>2}  {'min':>4} {'TSS':>4} {'kJ':>5} {'TVO2':>5} {'Wbal':>6}   what changed")
    print('-' * 86)
    for axis, levels, step in demos:
        for s in progress(base, axis, levels, step):
            lvl = s['_level']
            wu = s.get('warmup') or WU_FOR.get(s['system'], 'easy_raise')
            segs, _ = assemble(s)
            d = dose(segs)
            tvo2 = t_at_vo2max_proxy(segs)
            wb = wbal_nadir(segs)
            render(s, OUT, f"DEMO_{axis}_L{lvl}",
                   f"[ENGINE DEMO] axis={axis} level={lvl}/{levels} step={step}\n"
                   f"Base 4x4min VO2max @106%. Warm-up: {wu}.\n"
                   f"TSS {d['tss']} | kJ {d['kj']} | T@VO2max-proxy {tvo2//60}min | W'bal nadir {wb}kJ.\n"
                   f"Only the '{axis}' axis is advanced; all other levers held constant.")
            m = s['main']
            note = {
                'intensity': f"on_pwr={m['on_pwr']:.2f}",
                'work_duration': f"on_dur={m['on_dur']}s",
                'recovery_duration': f"off_dur={m['off_dur']}s",
                'reps': f"reps={m['reps']}",
                'prefatigue_kj': f"prefatigue={m.get('prefatigue_dur',0)//60}min Z2",
            }[axis]
            print(f"{axis:<20}{lvl:>2}  {d['min']:>4} {d['tss']:>4} {d['kj']:>5} {tvo2//60:>4}m {wb:>6}   {note}")
        print()
