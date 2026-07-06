#!/usr/bin/env python3
"""
ZWO builder for "Latest Cycling Workout Trends 2026" pack.

Follows Gravel God ZWO File Creation Skill v6.0 (TrainingPeaks-safe):
  1. XML declaration uses SINGLE quotes
  2. <workout_file> at column 0
  3. 2-space indent: author, name, description, sportType, workout
  4. 4-space indent: Warmup / SteadyState / IntervalsT / Cooldown
  5. NO 8-space indents anywhere
  6. Warmup / SteadyState / Cooldown are SELF-CLOSING (no nested textevent)
  7. ONLY IntervalsT may carry nested <textevent> (6-space indent)
  8. Power = decimal fraction of FTP (1.20 == 120%), Duration in seconds

Block helpers return correctly-indented strings. Power values are clamped/
formatted to 2 decimals. Validate output with the pipeline's test_zwo_format.py.
"""
from pathlib import Path
from xml.sax.saxutils import escape

OUT = Path(__file__).resolve().parent


def _p(x: float) -> str:
    return f"{x:.2f}"


def warmup(dur, low, high, clow=None, chigh=None):
    cad = f' CadenceLow="{clow}" CadenceHigh="{chigh}"' if clow else ""
    return f'    <Warmup Duration="{dur}" PowerLow="{_p(low)}" PowerHigh="{_p(high)}"{cad}/>'


def cooldown(dur, low, high, clow=None, chigh=None):
    cad = f' CadenceLow="{clow}" CadenceHigh="{chigh}"' if clow else ""
    return f'    <Cooldown Duration="{dur}" PowerLow="{_p(low)}" PowerHigh="{_p(high)}"{cad}/>'


def band(power):
    """Coggan-zone range band around a target, as (low, high) fractions of FTP.
    Returns None for Z6/Z7 (>120% FTP) — those stay single targets (sprints/accels).
    Wider band in the easy zones, tight near/above threshold."""
    if power > 1.20:
        return None
    tol = 0.05 if power < 0.76 else 0.03           # Z1-Z2 wider, Z3-Z5 tight
    return (max(0.30, round(power - tol, 2)), round(power + tol, 2))


def steady(dur, power, clow=None, chigh=None):
    cad = f' CadenceLow="{clow}" CadenceHigh="{chigh}"' if clow else ""
    b = band(power)                                 # keep mid Power (flat target) + Low/High (range)
    rng = f' PowerLow="{_p(b[0])}" PowerHigh="{_p(b[1])}"' if b else ""
    return f'    <SteadyState Duration="{dur}" Power="{_p(power)}"{rng}{cad}/>'


def intervals(repeat, on_dur, on_pwr, off_dur, off_pwr, clow=None, chigh=None, msg=None):
    cad = f' CadenceLow="{clow}" CadenceHigh="{chigh}"' if clow else ""
    ob, fb = band(on_pwr), band(off_pwr)
    on_rng = f' OnPowerLow="{_p(ob[0])}" OnPowerHigh="{_p(ob[1])}"' if ob else ""
    off_rng = f' OffPowerLow="{_p(fb[0])}" OffPowerHigh="{_p(fb[1])}"' if fb else ""
    head = (f'    <IntervalsT Repeat="{repeat}" OnDuration="{on_dur}" OnPower="{_p(on_pwr)}"{on_rng}'
            f' OffDuration="{off_dur}" OffPower="{_p(off_pwr)}"{off_rng}{cad}')
    if msg:
        return (head + '>\n'
                f'      <textevent timeoffset="0" message="{escape(msg)}"/>\n'
                '    </IntervalsT>')
    return head + '/>'


TEMPLATE = """<?xml version='1.0' encoding='UTF-8'?>
<workout_file>
  <author>Gravel God Training</author>
  <name>{name}</name>
  <description>{desc}</description>
  <sportType>bike</sportType>
  <workout>
{blocks}
  </workout>
</workout_file>"""


def build(name, desc, blocks):
    xml = TEMPLATE.format(name=name, desc=escape(desc), blocks="\n".join(blocks))
    path = OUT / f"{name}.zwo"
    path.write_text(xml, encoding="utf-8")
    return path


def total_minutes(blocks_meta):
    return round(sum(blocks_meta) / 60)
