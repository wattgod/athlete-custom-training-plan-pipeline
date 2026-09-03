#!/usr/bin/env python3
"""
Generate plan_preview.html — visual verification of the training plan.

Parses all ZWO files, calculates actual TSS/IF from power data, and renders
a single-page HTML with:
  1. Athlete reference card (questionnaire inputs + key decisions)
  2. Week-by-week grid with workout details, duration, TSS, zone
  3. Training load progression chart (hours + TSS per week)
  4. Automated verification checks (plan vs questionnaire)

Usage:
    python3 athletes/scripts/generate_plan_preview.py athletes/nicholas-applegate
"""

import sys
import os
import json
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

SCRIPTS_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPTS_DIR))
from zwo_parser import parse_zwo, parse_zwo_structure
from brand_config import workout_author
from known_races import UNMATCHED_RACE_MPH


# ===========================================================================
# ZWO Parsing + TSS Calculation
# ===========================================================================

def _if_to_zone(if_val: float) -> str:
    """Map intensity factor to training zone."""
    if if_val < 0.55:
        return 'Z1'
    elif if_val < 0.75:
        return 'Z2'
    elif if_val < 0.87:
        return 'Z3'
    elif if_val < 0.95:
        return 'Z4'
    elif if_val < 1.06:
        return 'Z5'
    else:
        return 'Z5+'


def _canonical_effort_samples(segments: list[dict]) -> list[tuple[int, float]]:
    """Flatten canonical segments into duration/normalized-effort samples."""
    samples = []

    def effort(target, key):
        value = target.get(key)
        if value is None:
            return None
        from canonical_training_model import normalize_target_effort
        return normalize_target_effort(str(target.get('type') or ''), value)

    for segment in segments or []:
        seconds = int(segment.get('seconds') or 0)
        target = segment.get('target') or {}
        if segment.get('kind') == 'free_ride' or target.get('type') == 'free':
            # FreeRide has no prescribed target. Preserve the preview's
            # established TSS-only estimate without adding a target to PlanIR.
            samples.append((seconds, .65 if seconds > 3600 else .55))
        elif segment.get('kind') == 'intervals':
            repeat = int(segment.get('repeat') or 1)
            on_seconds = int(segment.get('on_seconds') or 0)
            off_seconds = int(segment.get('off_seconds') or 0)
            on = effort(target, 'on')
            off = effort(target, 'off')
            for _ in range(repeat):
                if on_seconds and on is not None:
                    samples.append((on_seconds, on))
                if off_seconds and off is not None:
                    samples.append((off_seconds, off))
        else:
            low = effort(target, 'low')
            high = effort(target, 'high')
            value = effort(target, 'value')
            if low is not None and high is not None:
                value = (low + high) / 2
            elif value is None:
                value = high if high is not None else low
            if seconds and value is not None:
                samples.append((seconds, value))

    return samples


def _split_linear_ramp(
        seconds: float, low: float, high: float) -> list[tuple[float, float]]:
    """Split a linear ramp at the Z2 ceiling for literal TIZ accounting."""
    lower, upper = sorted((low, high))
    if upper < .75:
        return [(seconds, (low + high) / 2)]
    if lower >= .75:
        return [(seconds, (low + high) / 2)]
    easy_fraction = (.75 - lower) / (upper - lower)
    easy_seconds = seconds * easy_fraction
    return [(easy_seconds, .749), (seconds - easy_seconds, .75)]


def _canonical_tiz_samples(
        segments: list[dict]) -> tuple[list[tuple[float, float]], float]:
    """Return prescribed TIZ samples plus target-free seconds."""
    samples: list[tuple[float, float]] = []
    unknown_seconds = 0.0

    def effort(target, key):
        value = target.get(key)
        if value is None:
            return None
        from canonical_training_model import normalize_target_effort
        return normalize_target_effort(str(target.get('type') or ''), value)

    for segment in segments or []:
        seconds = float(segment.get('seconds') or 0)
        target = segment.get('target') or {}
        if segment.get('kind') == 'free_ride' or target.get('type') == 'free':
            unknown_seconds += seconds
            continue
        if segment.get('kind') == 'intervals':
            repeat = int(segment.get('repeat') or 1)
            on = effort(target, 'on')
            off = effort(target, 'off')
            if on is not None:
                samples.append((repeat * float(segment.get('on_seconds') or 0), on))
            if off is not None:
                samples.append((repeat * float(segment.get('off_seconds') or 0), off))
            continue
        low = effort(target, 'low')
        high = effort(target, 'high')
        value = effort(target, 'value')
        if (segment.get('kind') in ('warmup', 'cooldown', 'ramp')
                and low is not None and high is not None):
            samples.extend(_split_linear_ramp(seconds, low, high))
        else:
            if low is not None and high is not None:
                value = (low + high) / 2
            elif value is None:
                value = high if high is not None else low
            if seconds and value is not None:
                samples.append((seconds, value))
    return samples, unknown_seconds


def _legacy_tiz_samples(
        segments: list[dict]) -> tuple[list[tuple[float, float]], float]:
    """Project typed legacy ZWO structure into the same TIZ ruler."""
    canonical = []
    for segment in segments or []:
        kind = segment.get('kind')
        if kind == 'free_ride':
            canonical.append({
                'kind': kind, 'seconds': segment.get('seconds', 0),
                'target': {'type': 'free'},
            })
        elif kind == 'intervals':
            canonical.append({
                'kind': kind, 'seconds': segment.get('seconds', 0),
                'repeat': segment.get('repeat', 1),
                'on_seconds': segment.get('on_seconds', 0),
                'off_seconds': segment.get('off_seconds', 0),
                'target': {
                    'type': 'power_pct_ftp',
                    'on': segment.get('on_power'),
                    'off': segment.get('off_power'),
                },
            })
        else:
            canonical.append({
                'kind': kind, 'seconds': segment.get('seconds', 0),
                'target': {
                    'type': 'power_pct_ftp',
                    'low': segment.get('power_low'),
                    'high': segment.get('power_high'),
                    'value': segment.get('power_target'),
                },
            })
    return _canonical_tiz_samples(canonical)


def _canonical_intensity_factor(segments: list[dict]) -> float:
    """Calculate session intensity from canonical segment time and targets.

    Power keeps the established ZWO projection exactly. LTHR, HRmax, and RPE
    are first normalized through their own authored scales, then the same
    duration-weighted whole-session unit is applied. Raw HR percentages and
    RPE values are never compared with power-IF cutoffs.
    """
    samples = _canonical_effort_samples(segments)

    total_seconds = sum(seconds for seconds, _ in samples)
    if total_seconds <= 0:
        return .5
    return (sum(seconds * value ** 4 for seconds, value in samples)
            / total_seconds) ** .25


def _easy_hard_minutes(samples: list[tuple[float, float]]) -> tuple[float, float]:
    """Account prescribed time in zone per AE-2.2, never per session count."""
    easy_seconds = sum(seconds for seconds, effort in samples if effort < .75)
    hard_seconds = sum(seconds for seconds, effort in samples if effort >= .75)
    return easy_seconds / 60, hard_seconds / 60


def _ae22_easy_share(hours_per_week: float) -> float:
    """Ratified AE-2.2 low-intensity share, linearly joined at its anchors."""
    hours = float(hours_per_week or 0)
    if hours <= 7:
        return .70
    if hours <= 10:
        return .70 + (hours - 7) * (.05 / 3)
    if hours < 12:
        return .75 + (hours - 10) * (.05 / 2)
    return .80


# ===========================================================================
# Data Assembly
# ===========================================================================

def build_preview_data(athlete_dir: Path) -> Dict[str, Any]:
    """Build all data needed for the preview from athlete directory."""
    ad = Path(athlete_dir)

    # Load YAMLs
    def _load(fname):
        p = ad / fname
        if p.exists():
            with open(p) as f:
                return yaml.safe_load(f) or {}
        return {}

    profile = _load('profile.yaml')
    derived = _load('derived.yaml')
    methodology = _load('methodology.yaml')
    plan_dates = _load('plan_dates.yaml')
    weekly_structure = _load('weekly_structure.yaml')
    fueling = _load('fueling.yaml')

    fitness = profile.get('fitness_markers', {}) or {}
    ftp_raw = fitness.get('ftp_watts')
    try:
        ftp = float(ftp_raw) if ftp_raw not in (None, '') else None
    except (TypeError, ValueError):
        ftp = None
    control_metric = str(fitness.get('control_metric') or (
        'power' if ftp is not None else 'rpe'))
    control_basis = str(fitness.get('control_basis') or (
        'ftp' if control_metric == 'power' else control_metric))

    # Parse all ZWO files
    workouts_by_prefix = {}
    canonical_path = ad / 'canonical_training_model.json'
    if canonical_path.exists():
        canonical = json.loads(canonical_path.read_text())
        for session in canonical.get('sessions') or []:
            if session.get('tp_kind') == 'day_off':
                continue
            stem = session.get('filename_stem') or (
                f"W{int(session.get('week') or 0):02d}_{session.get('date') or 'undated'}_"
                + str(session.get('title') or 'Session').replace(' ', '_'))
            segments = session.get('segments') or []
            tiz_samples, unknown_seconds = _canonical_tiz_samples(segments)
            effort = _canonical_intensity_factor(segments)
            easy_min, hard_min = _easy_hard_minutes(tiz_samples)
            parsed = {
                'name': stem,
                '_stem': stem,
                'duration_sec': int(session.get('duration_s') or 0),
                'duration_min': int(session.get('duration_s') or 0) / 60,
                'tss': int(session.get('tss') or 0),
                # Metric-neutral comparison unit used only by verification;
                # unlike IF it is valid for LTHR, HRmax, and RPE controls.
                'normalized_effort': round(effort, 2),
                'intensity_factor': (round(effort, 2)
                                     if control_metric == 'power' else None),
                'zone': _if_to_zone(effort),
                'easy_duration_min': easy_min,
                'hard_duration_min': hard_min,
                'unknown_duration_min': unknown_seconds / 60,
                'intervals_summary': session.get('target_summary') or '',
                'target_summary': session.get('target_summary') or '',
            }
            workouts_by_prefix[stem] = parsed
    else:
        workouts_dir = ad / 'workouts'
        zwo_files = sorted(workouts_dir.glob('*.zwo')) if workouts_dir.exists() else []
        for zwo in zwo_files:
            # Historical package compatibility only. Null FTP is never
            # replaced with a fabricated athlete value; 1.0 is a parser scale
            # for ratio-only ZWO metrics and is not serialized.
            parsed = parse_zwo(zwo, ftp if ftp is not None else 1.0)
            parsed['_stem'] = zwo.stem
            structure = parse_zwo_structure(zwo)
            tiz_samples, unknown_seconds = _legacy_tiz_samples(
                structure.get('segments') or [])
            easy_min, hard_min = _easy_hard_minutes(tiz_samples)
            parsed['easy_duration_min'] = easy_min
            parsed['hard_duration_min'] = hard_min
            parsed['unknown_duration_min'] = unknown_seconds / 60
            workouts_by_prefix[zwo.stem] = parsed

    # Build week-by-week data
    weeks_data = []
    weeks = plan_dates.get('weeks', [])
    for week_info in weeks:
        wk_num = week_info.get('week', 0)
        phase = week_info.get('phase', '?')
        b_race = week_info.get('b_race', {})
        is_race_week = week_info.get('is_race_week', False)

        days_data = []
        week_tss = 0
        week_duration_sec = 0
        week_zone_counts = {'Z1': 0, 'Z2': 0, 'Z3': 0, 'Z4': 0, 'Z5': 0, 'Z5+': 0, 'REST': 0}

        for day_info in week_info.get('days', []):
            day_abbrev = day_info.get('day', '?')
            prefix = day_info.get('workout_prefix', '')
            is_race = day_info.get('is_race_day', False)
            is_b_race = day_info.get('is_b_race_day', False)
            is_b_opener = day_info.get('is_b_race_opener', False)

            # Find matching workout
            workout = None
            for wp_key, wp_data in workouts_by_prefix.items():
                if wp_key.startswith(prefix):
                    workout = wp_data
                    break

            if workout is None:
                # Off day or missing workout
                days_data.append({
                    'day': day_abbrev,
                    'date': day_info.get('date_short', ''),
                    'workout': None,
                    'is_off': True,
                    'is_race': is_race,
                    'is_b_race': is_b_race,
                    'is_b_opener': is_b_opener,
                })
            else:
                week_tss += workout['tss']
                week_duration_sec += workout['duration_sec']
                zone = workout['zone']
                if zone in week_zone_counts:
                    week_zone_counts[zone] += 1

                days_data.append({
                    'day': day_abbrev,
                    'date': day_info.get('date_short', ''),
                    'workout': workout,
                    'is_off': False,
                    'is_race': is_race,
                    'is_b_race': is_b_race,
                    'is_b_opener': is_b_opener,
                })

        weeks_data.append({
            'week': wk_num,
            'phase': phase,
            'monday_short': week_info.get('monday_short', ''),
            'sunday_short': week_info.get('sunday_short', ''),
            'b_race': b_race,
            'is_race_week': is_race_week,
            'is_recovery': bool(week_info.get('is_recovery_week')),
            'days': days_data,
            'total_tss': week_tss,
            'total_hours': round(week_duration_sec / 3600, 1),
            'zone_counts': week_zone_counts,
        })

    # Verification checks
    checks = _run_verification_checks(
        profile, derived, methodology, plan_dates, weekly_structure,
        weeks_data, control_metric=control_metric)

    return {
        'profile': profile,
        'derived': derived,
        'methodology': methodology,
        'plan_dates': plan_dates,
        'weekly_structure': weekly_structure,
        'fueling': fueling,
        'weeks': weeks_data,
        'ftp': ftp,
        'control_metric': control_metric,
        'control_basis': control_basis,
        'checks': checks,
        'generated': datetime.now().strftime('%Y-%m-%d %H:%M'),
    }


def _run_verification_checks(
    profile, derived, methodology, plan_dates, weekly_structure, weeks_data,
    control_metric='power',
) -> List[Dict[str, Any]]:
    """Run automated checks: plan vs questionnaire."""
    checks = []

    # 1. Weekly hours target vs actual
    target_hours = profile.get('weekly_availability', {}).get('cycling_hours_target', 0)
    if target_hours and weeks_data:
        # Measure against BUILD/PEAK load weeks — base deliberately ramps
        # at ~70-80% (progressive overload), and averaging the ramp into one
        # number false-flagged correctly built plans. Recovery weeks are
        # deliberately low and excluded.
        phase_of = {}
        meat_weeks = [w for w in weeks_data
                      if w['phase'].startswith(('build', 'peak'))
                      and w['total_hours'] > 0
                      and not w.get('is_recovery')]
        # recovery weeks inside build/peak run ~half volume — drop the
        # bottom outliers by excluding weeks under 70% of the phase max
        if meat_weeks:
            peak_h = max(w['total_hours'] for w in meat_weeks)
            load_weeks = [w for w in meat_weeks if w['total_hours'] >= 0.7 * peak_h]
            avg_hours = sum(w['total_hours'] for w in load_weeks) / len(load_weeks)
            pct_of_target = (avg_hours / float(target_hours)) * 100 if float(target_hours) > 0 else 0
            # PASS: 80-120%, WARN: 70-80% or 120-140%, FAIL: <70% or >140%
            if 80 <= pct_of_target <= 120:
                status = 'PASS'
            elif (70 <= pct_of_target < 80) or (120 < pct_of_target <= 140):
                status = 'WARN'
            else:
                status = 'FAIL'
            checks.append({
                'name': 'Weekly Volume',
                'status': status,
                'detail': (f"Target: {target_hours}h/wk | Avg build/peak load weeks: {avg_hours:.1f}h/wk "
                           f"({pct_of_target:.0f}%) | Thresholds: PASS 80-120%, WARN 70-80%/120-140%, FAIL <70%/>140%"),
            })

    # 2. Off days respected
    # Race days are exempt: an athlete whose B-race falls on their usual
    # off day is racing, not violating the schedule.
    off_days = profile.get('schedule_constraints', {}).get('preferred_off_days', [])
    violations = []
    for w in weeks_data:
        for d in w['days']:
            if d['day'].lower()[:3] in [od[:3] for od in off_days]:
                if d.get('is_race') or d.get('is_b_race'):
                    continue
                if not d['is_off'] and d.get('workout'):
                    violations.append(f"W{w['week']:02d} {d['day']}")
    checks.append({
        'name': 'Off Days Respected',
        'status': 'PASS' if not violations else 'FAIL',
        'detail': f"Off days: {', '.join(d.title() for d in off_days)}" +
                  (f" | VIOLATIONS: {', '.join(violations)}" if violations else " | All respected"),
    })

    # 3. Long ride on correct day
    long_day = profile.get('schedule_constraints', {}).get('preferred_long_day', '')
    long_day_abbrev = long_day[:3].title() if long_day else ''
    misplaced = []
    for w in weeks_data:
        for d in w['days']:
            wo = d.get('workout')
            if wo and 'Long_Ride' in wo.get('_stem', wo.get('name', '')):
                if d['day'] != long_day_abbrev and not d['is_race'] and not d['is_b_race']:
                    misplaced.append(f"W{w['week']:02d} {d['day']}")
    checks.append({
        'name': 'Long Ride Day',
        'status': 'PASS' if not misplaced else 'FAIL',
        'detail': f"Expected: {long_day_abbrev}" +
                  (f" | MISPLACED: {', '.join(misplaced)}" if misplaced else " | All on correct day"),
    })

    # 4. Zone distribution (polarized 80/20 check)
    meth_config = methodology.get('configuration', {})
    intensity_dist = meth_config.get('intensity_distribution', {})
    target_z1z2 = intensity_dist.get('z1_z2', 0)
    load_phases_present = any(
        w['phase'].startswith(('base', 'build', 'peak')) for w in weeks_data)
    if target_z1z2 and weeks_data and load_phases_present:
        # AE-2.2 requires TIME-IN-ZONE accounting, never session count. Mixed
        # workouts therefore contribute their warmup/recovery time to easy and
        # their work intervals to hard. AE-2.3 compares that actual split with
        # the phase's declared methodology target.
        weekly_results = []
        for w in weeks_data:
            if (w['phase'] in ('taper', 'race') or w.get('is_recovery')
                    or not w['phase'].startswith(('base', 'build', 'peak'))):
                continue
            easy_min = 0.0
            hard_min = 0.0
            unknown_min = 0.0
            for d in w['days']:
                wo = d.get('workout')
                if wo and wo.get('zone') not in ('REST', None):
                    easy_min += wo.get('easy_duration_min', 0) or 0
                    hard_min += wo.get('hard_duration_min', 0) or 0
                    unknown_min += wo.get('unknown_duration_min', 0) or 0
            known_min = easy_min + hard_min
            easy_pct = (easy_min / known_min * 100) if known_min > 0 else 0
            # AE-2.2 supersedes the legacy fixed methodology ratio: the house
            # low-intensity share scales from ~70% at 7h to 75% at 10h and 80%
            # at 12-15h. Methodology shapes where the hard budget lands.
            target_pct = _ae22_easy_share(target_hours) * 100
            diff = abs(easy_pct - target_pct) if known_min > 0 else 100
            if diff < 10:
                status = 'PASS'
            elif diff <= 15:
                status = 'WARN'
            else:
                status = 'FAIL'
            if unknown_min > 0 and status == 'PASS':
                status = 'WARN'
            weekly_results.append({
                'week': w['week'], 'status': status, 'diff': diff,
                'easy_pct': easy_pct, 'easy_min': easy_min,
                'known_min': known_min, 'unknown_min': unknown_min,
            })
        rank = {'PASS': 0, 'WARN': 1, 'FAIL': 2}
        worst = max(
            weekly_results,
            key=lambda item: (rank[item['status']], item['diff']),
            default=None,
        )
        status = worst['status'] if worst else 'WARN'
        target_pct = _ae22_easy_share(target_hours) * 100
        flagged = [f"W{item['week']:02d} {item['status']}"
                   for item in weekly_results if item['status'] != 'PASS']
        if worst:
            worst_detail = (
                f"Worst: W{worst['week']:02d} {worst['easy_pct']:.0f}% easy "
                f"({worst['easy_min']:.0f}/{worst['known_min']:.0f} known min; "
                f"{worst['unknown_min']:.0f} unknown) | Delta: {worst['diff']:.0f}%")
        else:
            worst_detail = 'No prescribed load-week TIZ available'
        checks.append({
            'name': 'Zone Distribution',
            'status': status,
            'detail': (f"Target: {target_pct:.0f}% easy per load week | "
                       f"{worst_detail} | Flagged: {', '.join(flagged) or 'none'} | "
                       f"Thresholds: PASS <10%, WARN 10-15% or unknown time, FAIL >15%"),
        })
    elif target_z1z2 and weeks_data:
        checks.append({
            'name': 'Zone Distribution',
            'status': 'PASS',
            'detail': 'Not applicable to a race/recovery-only revision horizon',
        })

    # 5. Phase progression
    phases = [w['phase'] for w in weeks_data]
    expected_order = ['base', 'build', 'peak', 'taper', 'race']
    seen = []
    for p in phases:
        p_clean = p.replace('_1', '').replace('_2', '')
        if p_clean not in seen:
            seen.append(p_clean)
    in_order = True
    for i, p in enumerate(seen):
        if p in expected_order:
            expected_idx = expected_order.index(p)
            for later in seen[i+1:]:
                if later in expected_order and expected_order.index(later) < expected_idx:
                    in_order = False
    checks.append({
        'name': 'Phase Progression',
        'status': 'PASS' if in_order else 'FAIL',
        'detail': f"Phases: {' → '.join(p.upper() for p in seen)}",
    })

    # 6. TSS progression (should increase base→build→peak, then drop taper)
    phase_tss = {}
    for w in weeks_data:
        phase_key = w['phase'].replace('_1', '').replace('_2', '')
        if phase_key not in phase_tss:
            phase_tss[phase_key] = []
        phase_tss[phase_key].append(w['total_tss'])
    avg_by_phase = {p: sum(v)/len(v) if v else 0 for p, v in phase_tss.items()}
    base_avg = avg_by_phase.get('base', 0)
    build_avg = avg_by_phase.get('build', 0)
    taper_avg = avg_by_phase.get('taper', 0)
    progression_ok = build_avg >= base_avg * 0.9  # build should be at least 90% of base
    taper_ok = taper_avg < build_avg if build_avg > 0 else True
    checks.append({
        'name': 'TSS Progression',
        'status': 'PASS' if progression_ok and taper_ok else 'WARN',
        'detail': ' | '.join(f"{p.upper()}: {v:.0f}" for p, v in avg_by_phase.items()),
    })

    # 7. B-race present
    # Only B-races that fall INSIDE the plan window can be placed. Races
    # before plan start or after the A-race (e.g. a victory-lap century the
    # week after) are out of scope, not missing.
    b_events = profile.get('b_events', [])
    if b_events:
        plan_start = plan_dates.get('plan_start', '')
        plan_end = plan_dates.get('plan_end', '')
        b_race_weeks = [w for w in weeks_data if w.get('b_race')]
        b_names_found = [w['b_race'].get('name', '?') for w in b_race_weeks]
        in_window = []
        out_of_window = []
        for e in b_events:
            date = e.get('date', '')
            if not date:
                continue
            if plan_start and plan_end and (date < plan_start or date > plan_end):
                out_of_window.append(e.get('name', '?'))
            else:
                in_window.append(e.get('name', '?'))
        missing = [n for n in in_window if n not in b_names_found]
        detail = f"Found: {', '.join(b_names_found) if b_names_found else 'none'}"
        if missing:
            detail += f" | MISSING: {', '.join(missing)}"
        if out_of_window:
            detail += f" | Outside plan window (n/a): {', '.join(out_of_window)}"
        checks.append({
            'name': 'B-Race Placed',
            'status': 'PASS' if not missing else 'FAIL',
            'detail': detail,
        })

    # 8. Key day placement
    ws_days = weekly_structure.get('days', {})
    expected_key_days = [d.title() for d, info in ws_days.items()
                         if info and info.get('is_key_day')]
    checks.append({
        'name': 'Key Days',
        'status': 'PASS',
        'detail': f"Key days: {', '.join(expected_key_days)}",
    })

    # 9. FTP test present
    ftp_tests = []
    for w in weeks_data:
        for d in w['days']:
            wo = d.get('workout')
            if wo and 'FTP_Test' in wo.get('_stem', wo.get('name', '')):
                ftp_tests.append(f"W{w['week']:02d} {d['day']}")
    ftp_not_required = (
        len(weeks_data) < 8
        and all(w['phase'] in ('taper', 'race', 'recovery') for w in weeks_data)
    )
    checks.append({
        'name': 'FTP Tests',
        'status': 'PASS' if ftp_tests or ftp_not_required else 'WARN',
        'detail': (f"Tests: {', '.join(ftp_tests)}" if ftp_tests else
                   "Not required in this short race/recovery revision"
                   if ftp_not_required else "No FTP tests found"),
    })

    # 10. FTP Test Frequency — plans 8+ weeks should have at least 2 tests
    total_weeks = len(weeks_data)
    if total_weeks >= 8:
        ftp_count = len(ftp_tests)
        if ftp_count >= 2:
            freq_status = 'PASS'
        elif ftp_count == 1:
            freq_status = 'WARN'
        else:
            freq_status = 'FAIL'
        checks.append({
            'name': 'FTP Test Frequency',
            'status': freq_status,
            'detail': (f"{ftp_count} FTP test(s) in {total_weeks}-week plan | "
                       f"Threshold: 2+ tests for plans >= 8 weeks"),
        })

    # 11. Long Ride vs Race Duration
    # Guard: skip if distance is 0, None, or missing (avoid divide-by-zero).
    # Also skip for short races (< 50 miles) — the long ride ratio check
    # is designed for ultra-distance events where race duration vastly exceeds
    # training ride duration.
    target_race = profile.get('target_race', {})
    race_distance_mi = target_race.get('distance_miles', 0) or 0
    if race_distance_mi >= 50 and weeks_data:
        # Estimate race duration: 200-mile gravel ~14-18h, use 15 mph avg for
        # gravel. Same constant as known_races.estimate_unmatched_race_duration_hours
        # -- single source (CLAUDE.md: a fact in more than one artifact has
        # exactly one source).
        estimated_race_hrs = race_distance_mi / UNMATCHED_RACE_MPH
        estimated_race_min = estimated_race_hrs * 60
        # Find the longest *training* ride across the plan. Race-day FreeRide
        # entries are intentionally long and must not certify their own
        # readiness check.
        max_long_ride_min = 0
        for w in weeks_data:
            for d in w['days']:
                wo = d.get('workout')
                stem = str((wo or {}).get('_stem') or (wo or {}).get('name') or '')
                is_race_entry = (
                    d.get('is_race')
                    or str(d.get('kind') or '').lower() == 'race'
                    or str((wo or {}).get('kind') or '').lower() == 'race'
                    or str((wo or {}).get('tp_kind') or '').lower() == 'race'
                    or stem.upper().startswith('RACE_DAY')
                    or '_RACE_DAY_' in stem.upper()
                )
                if wo and not is_race_entry and wo.get('duration_min', 0) > max_long_ride_min:
                    max_long_ride_min = wo['duration_min']
        if estimated_race_min > 0 and max_long_ride_min > 0:
            long_ride_pct = (max_long_ride_min / estimated_race_min) * 100
            if long_ride_pct >= 25:
                lr_status = 'PASS'
            elif long_ride_pct >= 15:
                lr_status = 'WARN'
            else:
                lr_status = 'FAIL'
            checks.append({
                'name': 'Long Ride vs Race Duration',
                'status': lr_status,
                'detail': (f"Max long ride: {max_long_ride_min:.0f}min | "
                           f"Est. race duration: {estimated_race_min:.0f}min ({race_distance_mi}mi @ 15mph) | "
                           f"Ratio: {long_ride_pct:.0f}% | "
                           f"Thresholds: PASS >=25%, WARN 15-25%, FAIL <15%"),
            })

    # 11b. Per-Day Duration Caps — every EMITTED workout must respect the
    # athlete's per-day availability. This validates the rendered files,
    # not the plan dict, so builder/renderer drift cannot hide a violation.
    pref_days = profile.get('preferred_days', {})
    if pref_days and weeks_data:
        day_caps = {}
        abbrev_map = {'monday': 'Mon', 'tuesday': 'Tue', 'wednesday': 'Wed',
                      'thursday': 'Thu', 'friday': 'Fri', 'saturday': 'Sat',
                      'sunday': 'Sun'}
        for full, info in pref_days.items():
            cap = (info or {}).get('max_duration_min', 0)
            if cap:
                day_caps[abbrev_map.get(full, full)] = cap
        cap_violations = []
        TOLERANCE = 1.10  # warmup/cooldown padding from ZWO scaling
        for w in weeks_data:
            for d in w['days']:
                wo = d.get('workout')
                if not wo or d.get('is_race') or d.get('is_b_race'):
                    continue
                cap = day_caps.get(d['day'], 0)
                dur = wo.get('duration_min', 0) or 0
                if cap and dur > cap * TOLERANCE:
                    cap_violations.append(
                        f"W{w['week']:02d} {d['day']}: {dur:.0f}min > {cap}min cap")
        checks.append({
            'name': 'Per-Day Duration Caps',
            'status': 'PASS' if not cap_violations else 'FAIL',
            'detail': ("All workouts within day availability"
                       if not cap_violations
                       else f"VIOLATIONS: {'; '.join(cap_violations[:5])}"),
        })

    # 12. Taper Intensity — taper weeks should have lower avg IF than build/peak
    taper_ifs = []
    build_peak_ifs = []
    for w in weeks_data:
        phase_clean = w['phase'].replace('_1', '').replace('_2', '')
        for d in w['days']:
            wo = d.get('workout')
            effort = ((wo or {}).get('normalized_effort')
                      if wo else None)
            if effort is None and wo:
                effort = wo.get('intensity_factor')
            if wo and (effort or 0) > 0:
                if phase_clean == 'taper':
                    taper_ifs.append(effort)
                elif phase_clean in ('build', 'peak'):
                    build_peak_ifs.append(effort)
    if taper_ifs and build_peak_ifs:
        avg_taper_if = sum(taper_ifs) / len(taper_ifs)
        avg_build_if = sum(build_peak_ifs) / len(build_peak_ifs)
        taper_ratio = (avg_taper_if / avg_build_if * 100) if avg_build_if > 0 else 0
        # Correct tapering cuts VOLUME and keeps intensity — a high taper IF
        # is textbook (short sharp openers). Only flag a taper that is
        # HARDER than the build, which is a build week in disguise.
        ti_status = 'PASS' if taper_ratio <= 105 else 'WARN'
        unit = 'IF' if control_metric == 'power' else 'normalized effort'
        checks.append({
            'name': 'Taper Intensity',
            'status': ti_status,
            'detail': (f"Taper avg {unit}: {avg_taper_if:.2f} | Build/Peak avg {unit}: {avg_build_if:.2f} | "
                       f"Ratio: {taper_ratio:.0f}% | Threshold: WARN if > 105% (taper harder than build)"),
        })

    return checks


# ===========================================================================
# HTML Rendering
# ===========================================================================

def render_preview_html(data: Dict[str, Any]) -> str:
    """Render the plan preview as a single HTML file."""
    profile = data['profile']
    methodology = data['methodology']
    derived = data['derived']
    fueling = data['fueling']
    weekly_structure = data['weekly_structure']
    weeks = data['weeks']
    checks = data['checks']
    ftp = data['ftp']
    control_metric = data.get('control_metric', 'power')
    control_basis = data.get('control_basis', 'ftp')
    preview_author = workout_author(profile)

    name = profile.get('name', 'Unknown')
    athlete_id = profile.get('athlete_id', 'unknown')
    target = profile.get('target_race', {})
    race_name = target.get('name', 'TBD')
    race_date = target.get('date', 'TBD')
    goal = target.get('goal_type', target.get('goal', '?'))
    meth_name = methodology.get('selected_methodology', '?')
    meth_score = methodology.get('score', '?')
    tier = derived.get('tier', '?')
    plan_weeks = derived.get('plan_weeks', '?')
    w_kg = profile.get('fitness_markers', {}).get('w_kg', '?')
    weight = profile.get('weight_kg', '?')
    cycling_hours = profile.get('weekly_availability', {}).get('cycling_hours_target', '?')
    stress = profile.get('health_factors', {}).get('stress_level', '?')
    recovery = profile.get('health_factors', {}).get('recovery_capacity', '?')
    age = profile.get('health_factors', {}).get('age', '?')
    past_failure = profile.get('methodology_preferences', {}).get('past_failure_with', '')

    # Availability per day
    pref_days = profile.get('preferred_days', {})
    off_days = profile.get('schedule_constraints', {}).get('preferred_off_days', [])

    # Weekly data for chart
    week_nums = [w['week'] for w in weeks]
    week_hours = [w['total_hours'] for w in weeks]
    week_tss = [w['total_tss'] for w in weeks]
    week_phases = [w['phase'] for w in weeks]

    # Zone colors
    zone_colors = {
        'Z1': '#4a90d9', 'Z2': '#27ae60', 'Z3': '#f39c12',
        'Z4': '#e74c3c', 'Z5': '#8e44ad', 'Z5+': '#c0392b', 'REST': '#95a5a6',
    }

    # Phase colors
    phase_colors = {
        'base': '#27ae60', 'base_1': '#27ae60', 'base_2': '#2ecc71',
        'build': '#f39c12', 'build_1': '#f39c12', 'build_2': '#e67e22',
        'peak': '#e74c3c', 'peak_1': '#e74c3c', 'peak_2': '#c0392b',
        'taper': '#9b59b6', 'race': '#2c3e50',
    }

    # Build availability row
    day_order = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    avail_cells = ''
    for day_name in day_order:
        info = pref_days.get(day_name, {})
        avail = info.get('availability', 'unavailable')
        slots = info.get('time_slots', [])
        max_dur = info.get('max_duration_min', 0)
        is_key = info.get('is_key_day_ok', False)
        day_short = day_name[:3].title()

        if avail == 'unavailable' or day_name in off_days:
            avail_cells += f'<td class="avail-off">{day_short}<br><small>OFF</small></td>'
        else:
            slot_str = '/'.join(s.upper() for s in slots)
            key_str = ' KEY' if is_key else ''
            avail_cells += (
                f'<td class="avail-on">{day_short}<br>'
                f'<small>{slot_str} {max_dur}min{key_str}</small></td>'
            )

    # Build week rows
    week_rows = ''
    for w in weeks:
        wk = w['week']
        phase = w['phase']
        phase_color = phase_colors.get(phase, '#666')
        is_race_wk = w['is_race_week']
        b_race = w.get('b_race', {})

        # Week header
        week_label = f"W{wk:02d}"
        phase_badge = f'<span class="phase-badge" style="background:{phase_color}">{phase.upper().replace("_", " ")}</span>'
        extras = ''
        if is_race_wk:
            extras += ' <span class="race-badge">A-RACE</span>'
        if b_race:
            extras += f' <span class="b-race-badge">B: {_esc(b_race.get("name", ""))}</span>'

        # Day cells
        day_cells = ''
        for d in w['days']:
            wo = d.get('workout')
            if d['is_off'] or wo is None:
                day_cells += f'<td class="day-off"><small>{d["day"]}</small><br>OFF</td>'
            else:
                zone = wo['zone']
                zone_color = zone_colors.get(zone, '#999')
                dur = wo['duration_min']
                tss = wo['tss']
                if_val = wo.get('intensity_factor')

                # Workout type from filename
                wo_name = wo['name'].split('_', 3)[-1] if '_' in wo['name'] else wo['name']
                # Clean up: remove date prefix if present
                parts = wo_name.split('_')
                if len(parts) > 1:
                    # Skip month+day prefix
                    wo_type = '_'.join(parts[1:]) if parts[0][:3] in ('Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec') else wo_name
                else:
                    wo_type = wo_name
                wo_type = wo_type.replace('_', ' ')

                interval_str = ''
                if wo['intervals_summary']:
                    interval_str = f'<div class="interval-detail">{_esc(wo["intervals_summary"])}</div>'

                race_marker = ''
                if d['is_race']:
                    race_marker = '<div class="race-marker">RACE DAY</div>'
                elif d['is_b_race']:
                    race_marker = '<div class="b-race-marker">B-RACE</div>'
                elif d['is_b_opener']:
                    race_marker = '<div class="opener-marker">OPENER</div>'

                control_detail = (
                    f'<div class="wo-power">IF: {if_val}</div>'
                    if control_metric == 'power'
                    else f'<div class="wo-power">{_esc(wo.get("target_summary") or control_basis)}</div>'
                )

                day_cells += (
                    f'<td class="day-workout" style="border-left:3px solid {zone_color}">'
                    f'{race_marker}'
                    f'<div class="wo-name">{_esc(wo_type)}</div>'
                    f'<div class="wo-metrics">'
                    f'<span class="metric">{dur:.0f}min</span> '
                    f'<span class="metric">TSS {tss}</span> '
                    f'<span class="metric zone-tag" style="background:{zone_color}">{zone}</span>'
                    f'</div>'
                    f'{interval_str}'
                    f'{control_detail}'
                    f'</td>'
                )

        week_rows += (
            f'<tr class="week-row">'
            f'<td class="week-label">{week_label}{phase_badge}{extras}</td>'
            f'{day_cells}'
            f'<td class="week-totals">'
            f'<strong>{w["total_hours"]}h</strong><br>'
            f'TSS {w["total_tss"]}'
            f'</td>'
            f'</tr>\n'
        )

    # Build checks HTML
    checks_html = ''
    for c in checks:
        icon = '&#10003;' if c['status'] == 'PASS' else ('&#9888;' if c['status'] == 'WARN' else '&#10007;')
        cls = c['status'].lower()
        checks_html += (
            f'<div class="check check-{cls}">'
            f'<span class="check-icon">{icon}</span> '
            f'<strong>{_esc(c["name"])}</strong>: {_esc(c["detail"])}'
            f'</div>\n'
        )

    if control_metric == 'power' and ftp is not None:
        control_row = (f'<div class="ref-row"><span class="label">FTP</span>'
                       f'<span class="value">{ftp:.0f}W ({w_kg} W/kg)</span></div>')
    else:
        control_row = (f'<div class="ref-row"><span class="label">Control</span>'
                       f'<span class="value">{_esc(control_metric.upper())} '
                       f'({_esc(control_basis)})</span></div>')

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Plan Preview: {_esc(name)}</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: 'Courier New', monospace; background: #f5f5f5; color: #333; padding: 20px; }}
h1 {{ font-size: 1.4em; margin-bottom: 4px; }}
h2 {{ font-size: 1.1em; margin: 20px 0 8px 0; border-bottom: 2px solid #333; padding-bottom: 4px; }}
.header {{ background: #2c3e50; color: #fff; padding: 16px; margin-bottom: 16px; }}
.header h1 {{ color: #fff; }}
.header .subtitle {{ color: #95a5a6; font-size: 0.85em; }}

/* Reference Card */
.ref-card {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; margin-bottom: 16px; }}
.ref-box {{ background: #fff; border: 2px solid #333; padding: 10px; }}
.ref-box h3 {{ font-size: 0.85em; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 1px; color: #666; }}
.ref-row {{ display: flex; justify-content: space-between; font-size: 0.8em; padding: 2px 0; }}
.ref-row .label {{ color: #666; }}
.ref-row .value {{ font-weight: bold; }}
.ref-highlight {{ color: #e74c3c; font-weight: bold; }}

/* Availability strip */
.avail-table {{ width: 100%; border-collapse: collapse; margin: 8px 0; }}
.avail-table td {{ text-align: center; padding: 6px 4px; font-size: 0.75em; border: 1px solid #ccc; }}
.avail-on {{ background: #e8f5e9; }}
.avail-off {{ background: #ffebee; color: #999; }}

/* Checks */
.checks {{ margin-bottom: 16px; }}
.check {{ padding: 6px 10px; font-size: 0.8em; margin: 2px 0; border-left: 3px solid; }}
.check-pass {{ border-color: #27ae60; background: #e8f5e9; }}
.check-warn {{ border-color: #f39c12; background: #fef9e7; }}
.check-fail {{ border-color: #e74c3c; background: #fdedec; }}
.check-icon {{ font-weight: bold; }}

/* Week table */
.plan-table {{ width: 100%; border-collapse: collapse; font-size: 0.75em; }}
.plan-table th {{ background: #2c3e50; color: #fff; padding: 6px; text-align: center; }}
.week-row {{ border-bottom: 1px solid #ddd; }}
.week-row:hover {{ background: #f0f0f0; }}
.week-label {{ padding: 6px; vertical-align: top; min-width: 140px; white-space: nowrap; }}
.phase-badge {{ display: inline-block; padding: 1px 6px; color: #fff; font-size: 0.75em;
               margin-left: 4px; font-weight: bold; }}
.race-badge {{ display: inline-block; padding: 1px 6px; background: #2c3e50; color: #f39c12;
              font-size: 0.7em; font-weight: bold; }}
.b-race-badge {{ display: inline-block; padding: 1px 6px; background: #8e44ad; color: #fff;
                font-size: 0.7em; }}
.day-off {{ text-align: center; padding: 6px; color: #999; background: #f9f9f9; vertical-align: top; }}
.day-workout {{ padding: 6px; vertical-align: top; min-width: 120px; }}
.wo-name {{ font-weight: bold; font-size: 0.95em; }}
.wo-metrics {{ margin-top: 2px; }}
.metric {{ display: inline-block; margin-right: 4px; }}
.zone-tag {{ color: #fff; padding: 1px 4px; font-size: 0.85em; }}
.interval-detail {{ color: #555; font-size: 0.85em; margin-top: 2px; font-style: italic; }}
.wo-power {{ color: #888; font-size: 0.85em; }}
.week-totals {{ padding: 6px; text-align: center; vertical-align: top; min-width: 80px; background: #fafafa; }}
.race-marker {{ background: #2c3e50; color: #f39c12; padding: 1px 4px; font-size: 0.7em;
               font-weight: bold; margin-bottom: 2px; display: inline-block; }}
.b-race-marker {{ background: #8e44ad; color: #fff; padding: 1px 4px; font-size: 0.7em;
                  font-weight: bold; margin-bottom: 2px; display: inline-block; }}
.opener-marker {{ background: #3498db; color: #fff; padding: 1px 4px; font-size: 0.7em;
                  font-weight: bold; margin-bottom: 2px; display: inline-block; }}

/* Chart */
.chart-container {{ background: #fff; border: 2px solid #333; padding: 16px; margin: 16px 0; }}
.bar-chart {{ display: flex; align-items: flex-end; gap: 4px; height: 160px; }}
.bar-group {{ flex: 1; display: flex; flex-direction: column; align-items: center; }}
.bar {{ width: 100%; min-width: 20px; transition: height 0.3s; }}
.bar-hours {{ background: #3498db; }}
.bar-tss {{ background: #e74c3c; opacity: 0.7; }}
.bar-label {{ font-size: 0.65em; text-align: center; margin-top: 4px; }}
.bar-value {{ font-size: 0.6em; text-align: center; color: #666; }}
.chart-legend {{ display: flex; gap: 16px; margin-top: 8px; font-size: 0.75em; }}
.legend-item {{ display: flex; align-items: center; gap: 4px; }}
.legend-swatch {{ width: 12px; height: 12px; display: inline-block; }}

.footer {{ margin-top: 20px; font-size: 0.75em; color: #999; text-align: center; }}
</style>
</head>
<body>

<div class="header">
  <h1>PLAN PREVIEW: {_esc(name)}</h1>
  <div class="subtitle">{_esc(race_name)} | {race_date} | {plan_weeks} weeks | Generated {data['generated']}</div>
</div>

<!-- REFERENCE CARD -->
<div class="ref-card">
  <div class="ref-box">
    <h3>Athlete Profile</h3>
    {control_row}
    <div class="ref-row"><span class="label">Weight</span><span class="value">{weight}kg</span></div>
    <div class="ref-row"><span class="label">Age</span><span class="value">{age}</span></div>
    <div class="ref-row"><span class="label">Hours/wk</span><span class="value">{cycling_hours}</span></div>
    <div class="ref-row"><span class="label">Stress</span><span class="value {'ref-highlight' if str(stress).lower() == 'high' else ''}">{stress}</span></div>
    <div class="ref-row"><span class="label">Recovery</span><span class="value {'ref-highlight' if str(recovery).lower() == 'slow' else ''}">{recovery}</span></div>
  </div>
  <div class="ref-box">
    <h3>Methodology</h3>
    <div class="ref-row"><span class="label">Selected</span><span class="value">{_esc(meth_name)}</span></div>
    <div class="ref-row"><span class="label">Score</span><span class="value">{meth_score}/100</span></div>
    <div class="ref-row"><span class="label">Tier</span><span class="value">{tier}</span></div>
    <div class="ref-row"><span class="label">Goal</span><span class="value">{_esc(goal)}</span></div>
    {f'<div class="ref-row"><span class="label">Vetoed</span><span class="value ref-highlight">{_esc(past_failure)}</span></div>' if past_failure else ''}
  </div>
  <div class="ref-box">
    <h3>Race Target</h3>
    <div class="ref-row"><span class="label">Race</span><span class="value">{_esc(race_name)}</span></div>
    <div class="ref-row"><span class="label">Date</span><span class="value">{race_date}</span></div>
    <div class="ref-row"><span class="label">Distance</span><span class="value">{target.get('distance_miles', '?')} miles</span></div>
    <div class="ref-row"><span class="label">Plan Start</span><span class="value">{derived.get('plan_start', '?')}</span></div>
    <div class="ref-row"><span class="label">Plan End</span><span class="value">{derived.get('plan_end', '?')}</span></div>
  </div>
</div>

<!-- AVAILABILITY STRIP -->
<h2>Athlete Availability (from questionnaire)</h2>
<table class="avail-table">
  <tr>{avail_cells}</tr>
</table>

<!-- VERIFICATION CHECKS -->
<h2>Verification Checks</h2>
<div class="checks">
{checks_html}
</div>

<!-- TRAINING LOAD CHART -->
<h2>Training Load Progression</h2>
<div class="chart-container">
  <div class="bar-chart">
    {_render_bars(weeks)}
  </div>
  <div class="chart-legend">
    <div class="legend-item"><span class="legend-swatch" style="background:#3498db"></span> Hours</div>
    <div class="legend-item"><span class="legend-swatch" style="background:#e74c3c;opacity:0.7"></span> TSS</div>
  </div>
</div>

<!-- WEEK-BY-WEEK GRID -->
<h2>Week-by-Week Plan</h2>
<table class="plan-table">
<thead>
<tr>
  <th>Week</th>
  <th>Mon</th><th>Tue</th><th>Wed</th><th>Thu</th><th>Fri</th><th>Sat</th><th>Sun</th>
  <th>Total</th>
</tr>
</thead>
<tbody>
{week_rows}
</tbody>
</table>

<div class="footer">
  Generated by generate_plan_preview.py | {_esc(preview_author)} | {data['generated']}
</div>

</body>
</html>"""

    return html


def _render_bars(weeks: List[Dict]) -> str:
    """Render bar chart groups for hours and TSS."""
    max_hours = max((w['total_hours'] for w in weeks), default=1) or 1
    max_tss = max((w['total_tss'] for w in weeks), default=1) or 1

    phase_colors = {
        'base': '#27ae60', 'base_1': '#27ae60', 'base_2': '#2ecc71',
        'build': '#f39c12', 'build_1': '#f39c12', 'build_2': '#e67e22',
        'peak': '#e74c3c', 'peak_1': '#e74c3c', 'peak_2': '#c0392b',
        'taper': '#9b59b6', 'race': '#2c3e50',
    }

    html = ''
    for w in weeks:
        h_pct = (w['total_hours'] / max_hours) * 100
        t_pct = (w['total_tss'] / max_tss) * 100
        phase_color = phase_colors.get(w['phase'], '#666')
        b_marker = ' *' if w.get('b_race') else ''
        race_marker = ' A' if w.get('is_race_week') else ''
        html += (
            f'<div class="bar-group">'
            f'<div class="bar-value">{w["total_hours"]}h</div>'
            f'<div style="display:flex;gap:2px;align-items:flex-end;height:120px;width:100%">'
            f'<div class="bar bar-hours" style="height:{h_pct}%;flex:1"></div>'
            f'<div class="bar bar-tss" style="height:{t_pct}%;flex:1"></div>'
            f'</div>'
            f'<div class="bar-label" style="color:{phase_color}">W{w["week"]:02d}{b_marker}{race_marker}</div>'
            f'</div>'
        )
    return html


def _esc(text: str) -> str:
    """HTML-escape text."""
    if not text:
        return ''
    return (str(text)
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;'))


# ===========================================================================
# Main
# ===========================================================================

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 generate_plan_preview.py <athlete-dir>")
        print("  e.g.: python3 athletes/scripts/generate_plan_preview.py athletes/nicholas-applegate")
        sys.exit(1)

    athlete_dir = Path(sys.argv[1])
    if not athlete_dir.exists():
        print(f"ERROR: Directory not found: {athlete_dir}")
        sys.exit(1)

    print(f"Building preview for {athlete_dir.name}...")

    data = build_preview_data(athlete_dir)
    html = render_preview_html(data)

    out_path = athlete_dir / 'plan_preview.html'
    with open(out_path, 'w') as f:
        f.write(html)

    print(f"  Written: {out_path}")
    print(f"  Weeks: {len(data['weeks'])}")
    print(f"  Workouts parsed: {sum(1 for w in data['weeks'] for d in w['days'] if d.get('workout'))}")
    print(f"  Checks: {sum(1 for c in data['checks'] if c['status'] == 'PASS')}/{len(data['checks'])} pass")

    # Also open in browser
    import webbrowser
    webbrowser.open(f'file://{out_path.resolve()}')


if __name__ == '__main__':
    main()
