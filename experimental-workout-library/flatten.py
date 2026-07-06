#!/usr/bin/env python3
"""
Flatten every ridable .zwo into ~/Downloads/Cycling-Workouts-ALL with TrainingPeaks-
friendly names so each PROGRESSION groups together in the workout library.

TrainingPeaks sorts by the <name> tag, so titles are written as:
    "{Group} - {Name} - L{n} of {N} - {min}min - {RPE}"
Leading with the Group word (never a number) keeps all levels of one archetype
adjacent. The <name> tag inside each file is rewritten to match the filename.

The 234 archetype-library files already follow this scheme (Category-led) and are
copied verbatim. Only the trend (0x_) and torque (T#_) packs are relabelled.
engine_demo/ (axis-mechanics, not ridable) is excluded.

Run: python3 flatten.py
"""
import glob, os, re

SRC = os.path.dirname(os.path.abspath(__file__))
DEST = os.path.expanduser("~/Downloads/Cycling-Workouts-ALL")

TREND = {'01': ('VO2max', 'Ronnestad 30-15'), '02': ('VO2max', 'Seiler 4x8'),
         '03': ('Threshold', 'Kolie Moore TTE'), '04': ('Threshold', 'Over-Unders'),
         '05': ('Endurance', 'Z2 + Sprints'), '06': ('Durability', 'Fatigued Threshold'),
         '07': ('Torque', 'Big-Gear Torque')}
TORQUE = {'1': ('Torque', 'Muscle Tension Intervals'), '2': ('Torque', 'SFR'),
          '3': ('Torque', 'TorqueMax'), '4': ('Torque', 'Ruegg Torque-Power'),
          '5': ('Torque', 'Pogacar Stack'), '6': ('Torque', 'Force Reps (Stomps)'),
          '7': ('Torque', 'Sit-Stand Efforts'), '8': ('Torque', 'Descending-Cadence Ladder')}
TREND_N, TORQUE_N = 4, 4


def rpe(p):
    if p < 0.56:  return "RPE1-2"
    if p < 0.76:  return "RPE2-3"
    if p < 0.88:  return "RPE3-4"
    if p <= 0.94: return "RPE5-6"
    if p <= 1.05: return "RPE6-7"
    if p <= 1.20: return "RPE8-9"
    if p <= 1.50: return "RPE9-10"
    return "RPE10"


def dur_peak(text):
    total = 0; peak = 0.0
    for m in re.finditer(r'<(?:Warmup|Cooldown|SteadyState)\b([^>]*)>', text):
        a = m.group(1)
        d = re.search(r'Duration="(\d+)"', a)
        if d: total += int(d.group(1))
        for pw in re.findall(r'Power(?:Low|High)?="([0-9.]+)"', a):
            peak = max(peak, float(pw))
    for m in re.finditer(r'<IntervalsT\b([^>]*?)/?>', text):
        a = m.group(1)
        rep = int(re.search(r'Repeat="(\d+)"', a).group(1))
        on = int(re.search(r'OnDuration="(\d+)"', a).group(1))
        off = int(re.search(r'OffDuration="(\d+)"', a).group(1))
        total += rep * (on + off)
        for pw in re.findall(r'(?:On|Off)Power="([0-9.]+)"', a):
            peak = max(peak, float(pw))
    return round(total / 60), peak


def title_for(path, text):
    base = os.path.basename(path)
    rel = os.path.relpath(path, SRC)
    if rel.startswith('library' + os.sep):                 # already grouping-friendly
        return re.search(r'<name>(.*?)</name>', text).group(1)
    mins, peak = dur_peak(text); R = rpe(peak)
    m = re.match(r'(\d{2})_.*?_L(\d)_', base)               # trend ladder
    if m:
        g, n = TREND[m.group(1)]
        return f"{g} - {n} - {int(m.group(2))} - {mins}min - {R}"
    m = re.match(r'(\d{2})_', base)                         # trend single
    if m and m.group(1) in TREND:
        g, n = TREND[m.group(1)]
        return f"{g} - {n} - ref - {mins}min - {R}"
    m = re.match(r'T(\d)_.*?_L(\d)_', base)                 # torque ladder
    if m:
        g, n = TORQUE[m.group(1)]
        return f"{g} - {n} - {int(m.group(2))} - {mins}min - {R}"
    m = re.match(r'T(\d)_', base)                           # torque single
    if m and m.group(1) in TORQUE:
        g, n = TORQUE[m.group(1)]
        return f"{g} - {n} - ref - {mins}min - {R}"
    return os.path.splitext(base)[0]


# Rule #15 dimension profiles for the hand-built packs (library files already carry their own)
TREND_DIMS = {
    '01': "zones Z1-Z5 · normal cadence · seated · climbing · micro-bursts (3 sets)",
    '02': "zones Z1-Z5 · normal cadence · seated/aero · climbing · long intervals",
    '03': "zones Z1-Z4 · normal cadence · seated/aero · climbing · sustained (TTE)",
    '04': "zones Z1-Z4 · normal cadence · seated · climbing · over/under blocks",
    '05': "zones Z1-Z7 · normal+high cadence · seated/standing · flat/rolling · Z2 + sprints",
    '06': "zones Z1-Z4 · normal cadence · seated · rolling/mixed · fatigued blocks",
    '07': "zones Z1-Z3 · low cadence · seated · climbing · low-cadence intervals",
}
TORQUE_DIMS = {
    '1': "zones Z1-Z3 · low cadence · seated · climbing · strength-endurance",
    '2': "zones Z1-Z3 · low cadence · seated · climbing · strength-endurance",
    '3': "zones Z1-Z5 · low cadence · seated · climbing · supra-threshold torque",
    '4': "zones Z1-Z5 · low+high cadence · seated/standing · climbing · torque->spin contrast",
    '5': "zones Z1-Z6 · low+high cadence · seated/standing · climbing · torque+sprint stack",
    '6': "zones Z1-Z7 · low cadence · seated · flat · neuromuscular force",
    '7': "zones Z1-Z3 · low+normal cadence · seated/standing · climbing · sit-stand contrast",
    '8': "zones Z1-Z3 · low cadence · seated · climbing · descending-cadence",
}


def dims_for(base):
    m = re.match(r'(\d{2})_', base)
    if m and m.group(1) in TREND_DIMS:
        return TREND_DIMS[m.group(1)]
    m = re.match(r'T(\d)_', base)
    if m and m.group(1) in TORQUE_DIMS:
        return TORQUE_DIMS[m.group(1)]
    return None


# headers whose blocks are justification/marketing — stripped from descriptions
_DROP = ('PURPOSE', 'PROGRESSION', 'SOURCE', 'NOTE', 'DOSE')


def clean_description(text):
    """Remove justification blocks + bracket marketing intros from <description>."""
    m = re.search(r'<description>(.*?)</description>', text, re.DOTALL)
    if not m:
        return text
    blocks = m.group(1).strip().split('\n\n')
    keep = []
    for b in blocks:
        first = b.strip().split('\n', 1)[0].strip()
        if first.startswith('[') or first.startswith('-[') or first.startswith('GG -') or first.startswith('Avatar'):
            continue                                       # bracket / week-context marketing
        if any(first.startswith(h) for h in _DROP):
            continue                                       # justification sections
        keep.append(b)
    return text[:m.start(1)] + "\n\n".join(keep) + text[m.end(1):]


def main():
    os.makedirs(DEST, exist_ok=True)
    for old in glob.glob(DEST + "/*.zwo"):
        os.unlink(old)
    srcs = [f for f in glob.glob(SRC + "/**/*.zwo", recursive=True)
            if os.sep + "engine_demo" + os.sep not in f and not f.startswith(DEST)]
    seen = {}; n = 0
    for f in sorted(srcs):
        text = open(f, encoding="utf-8").read()
        title = title_for(f, text)
        text = clean_description(text)                     # strip justification/marketing
        dims = dims_for(os.path.basename(f))               # propagate Rule #15 dimensions to trend/torque
        if dims and 'DIMENSIONS:' not in text:
            text = text.replace('</description>', f"\n\nDIMENSIONS:\n-{dims}</description>", 1)
        # rewrite the in-app <name> to match the grouping title
        text = re.sub(r'<name>.*?</name>', f'<name>{title}</name>', text, count=1)
        out = title
        if out in seen:                                    # guard collisions
            seen[out] += 1; out = f"{out} ({seen[out]})"
        else:
            seen[out] = 1
        open(os.path.join(DEST, out + ".zwo"), "w", encoding="utf-8").write(text)
        n += 1
    print(f"Flattened {n} workouts -> {DEST}")


if __name__ == '__main__':
    main()
