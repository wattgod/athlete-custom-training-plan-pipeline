#!/usr/bin/env python3
"""
Intake-to-Plan: End-to-end pipeline from athlete questionnaire to deliverables.

Takes a markdown-formatted athlete questionnaire (pasted as stdin or from a file)
and runs the full pipeline, producing deliverables in ~/Downloads/.

Usage:
    # From file:
    python3 athletes/scripts/intake_to_plan.py --file intake.md

    # From stdin (pipe):
    cat intake.md | python3 athletes/scripts/intake_to_plan.py

    # From clipboard (macOS):
    pbpaste | python3 athletes/scripts/intake_to_plan.py
"""

import sys
import os
import re
import argparse
import shutil
import subprocess
from pathlib import Path
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple, Any

# Ensure scripts dir is on path
SCRIPTS_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPTS_DIR))

from constants import (
    ATHLETES_BASE_DIR,
    get_athlete_dir,
    get_athlete_file,
    DAY_ORDER_FULL,
    WEEKDAYS_FULL,
    WEEKEND_FULL,
    FTP_MIN_WATTS,
    FTP_MAX_WATTS,
    WEIGHT_MIN_KG,
    WEIGHT_MAX_KG,
    AGE_MIN,
    AGE_MAX,
)
from known_races import KNOWN_RACES, RACE_ALIASES, match_race

# ---------------------------------------------------------------------------
# ANSI colors for terminal output
# ---------------------------------------------------------------------------
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
CYAN = '\033[96m'
BOLD = '\033[1m'
DIM = '\033[2m'
RESET = '\033[0m'

# ===========================================================================
# Intake Validation
# ===========================================================================

class IntakeValidationError(Exception):
    """Raised when parsed intake data fails validation checks."""
    pass


# Height sanity bounds (not in constants.py -- specific to intake validation)
HEIGHT_MIN_CM: int = 120
HEIGHT_MAX_CM: int = 220

# W/kg sanity bounds
WKG_MIN: float = 0.5
WKG_MAX: float = 8.0

# Weekly hours sanity bounds
WEEKLY_HOURS_MIN: int = 1
WEEKLY_HOURS_MAX: int = 40

# Weight unit detection threshold -- values below this are too light for any unit
WEIGHT_TOO_LIGHT: float = 40.0


def validate_parsed_intake(parsed: Dict[str, Any]) -> None:
    """
    Validate parsed intake data BEFORE profile building.

    Checks:
    - Required sections exist and are non-empty dicts
    - Required fields within those sections have non-empty values

    Raises IntakeValidationError with an actionable message listing all problems.
    """
    errors: List[str] = []

    # --- Required sections ---
    required_sections = ['basic_info', 'goals', 'current_fitness', 'schedule']
    missing_sections = []
    for section in required_sections:
        val = parsed.get(section)
        if not isinstance(val, dict) or not val:
            missing_sections.append(section)

    if missing_sections:
        errors.append(
            f"Missing or empty required sections: {', '.join(missing_sections)}. "
            f"Check that the questionnaire has ## headings for: "
            f"{', '.join(s.replace('_', ' ').title() for s in missing_sections)}."
        )

    # --- Required fields (only check if section exists) ---
    required_fields = {
        'basic_info': {
            'age': 'Age is required in Basic Info.',
            'weight': 'Weight is required in Basic Info.',
            'sex': 'Sex is required in Basic Info.',
        },
        'goals': {
            'races': 'At least one race must be listed in Goals.',
        },
        'current_fitness': {
            'ftp': 'FTP is required in Current Fitness.',
        },
        'schedule': {
            'weekly_hours_available': 'Weekly hours available is required in Schedule.',
        },
    }

    missing_fields = []
    for section, fields in required_fields.items():
        section_data = parsed.get(section, {})
        if not isinstance(section_data, dict):
            continue  # Already caught by missing sections check
        for field, hint in fields.items():
            val = section_data.get(field)
            if val is None or (isinstance(val, str) and not val.strip()):
                missing_fields.append(hint)

    # Special check: races must have at least one entry
    goals_data = parsed.get('goals', {})
    if isinstance(goals_data, dict):
        races_val = goals_data.get('races', '')
        if isinstance(races_val, str) and races_val.strip():
            race_list = [r.strip() for r in races_val.split('\n') if r.strip()]
            if not race_list:
                missing_fields.append('At least one race must be listed in Goals.')

    if missing_fields:
        errors.append("Missing required fields:\n" + "\n".join(f"  - {f}" for f in missing_fields))

    if errors:
        raise IntakeValidationError(
            "Intake validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
        )


def validate_profile_sanity(profile: Dict[str, Any]) -> None:
    """
    Run sanity checks on a built profile dict BEFORE writing YAML.

    Checks FTP, weight, height, age, W/kg, and weekly hours against
    reasonable bounds. Collects ALL violations before raising.

    Raises IntakeValidationError with actionable messages for every violation.
    """
    violations: List[str] = []

    # --- FTP ---
    ftp = profile.get('fitness_markers', {}).get('ftp_watts')
    if ftp is not None:
        if ftp < FTP_MIN_WATTS:
            violations.append(
                f"FTP {ftp}W is below minimum ({FTP_MIN_WATTS}W). "
                f"Check the questionnaire FTP field."
            )
        elif ftp > FTP_MAX_WATTS:
            violations.append(
                f"FTP {ftp}W is above maximum ({FTP_MAX_WATTS}W). "
                f"Check the questionnaire FTP field."
            )

    # --- Weight ---
    weight_kg = profile.get('weight_kg')
    if weight_kg is not None and weight_kg > 0:
        if weight_kg < WEIGHT_MIN_KG:
            violations.append(
                f"Weight {weight_kg} kg is below minimum ({WEIGHT_MIN_KG} kg). "
                f"Was the unit lbs?"
            )
        elif weight_kg > WEIGHT_MAX_KG:
            violations.append(
                f"Weight {weight_kg} kg is above maximum ({WEIGHT_MAX_KG} kg). "
                f"Was the value entered in lbs without a unit?"
            )

    # --- Height ---
    height_cm = profile.get('height_cm')
    if height_cm is not None and height_cm > 0:
        if height_cm < HEIGHT_MIN_CM:
            violations.append(
                f"Height {height_cm} cm is below minimum ({HEIGHT_MIN_CM} cm). "
                f"Check the height format (e.g. 6'1\" or 185 cm)."
            )
        elif height_cm > HEIGHT_MAX_CM:
            violations.append(
                f"Height {height_cm} cm is above maximum ({HEIGHT_MAX_CM} cm). "
                f"Check the height format (e.g. 6'1\" or 185 cm)."
            )

    # --- Age ---
    age = profile.get('health_factors', {}).get('age')
    if age is not None and age > 0:
        if age < AGE_MIN:
            violations.append(
                f"Age {age} is below minimum ({AGE_MIN}). "
                f"Check the questionnaire age field."
            )
        elif age > AGE_MAX:
            violations.append(
                f"Age {age} is above maximum ({AGE_MAX}). "
                f"Check the questionnaire age field."
            )

    # --- W/kg ---
    w_kg = profile.get('fitness_markers', {}).get('w_kg')
    if w_kg is not None:
        if w_kg < WKG_MIN:
            violations.append(
                f"W/kg {w_kg} is below minimum ({WKG_MIN}). "
                f"This suggests a calculation error -- check FTP and weight."
            )
        elif w_kg > WKG_MAX:
            violations.append(
                f"W/kg {w_kg} is above maximum ({WKG_MAX}). "
                f"This is world-class or an error -- check FTP and weight."
            )

    # --- Weekly hours ---
    weekly_hours = profile.get('weekly_availability', {}).get('cycling_hours_target')
    if weekly_hours is not None and weekly_hours > 0:
        if weekly_hours < WEEKLY_HOURS_MIN:
            violations.append(
                f"Weekly hours {weekly_hours} is below minimum ({WEEKLY_HOURS_MIN}). "
                f"Check the schedule section."
            )
        elif weekly_hours > WEEKLY_HOURS_MAX:
            violations.append(
                f"Weekly hours {weekly_hours} is above maximum ({WEEKLY_HOURS_MAX}). "
                f"Check the schedule section."
            )

    if violations:
        raise IntakeValidationError(
            "Profile sanity check failed:\n"
            + "\n".join(f"  - {v}" for v in violations)
        )


# ===========================================================================
# Markdown Parser
# ===========================================================================

def parse_intake_markdown(text: str) -> Dict[str, Any]:
    """
    Parse a markdown-formatted athlete intake questionnaire.

    Returns a flat dict of section -> {key: value} pairs plus
    a top-level 'athlete_name' key.
    """
    result: Dict[str, Any] = {}
    current_section: Optional[str] = None

    lines = text.strip().splitlines()

    # Extract athlete name from first heading
    for line in lines:
        m = re.match(r'^#\s+Athlete Intake:\s*(.+)', line.strip())
        if m:
            result['athlete_name'] = m.group(1).strip()
            break

    if 'athlete_name' not in result:
        # Fallback: look for any # heading
        for line in lines:
            m = re.match(r'^#\s+(.+)', line.strip())
            if m:
                result['athlete_name'] = m.group(1).strip()
                break

    # Parse sections and key-value pairs
    current_section = '__header__'
    result[current_section] = {}
    last_key: Optional[str] = None

    for line in lines:
        stripped = line.strip()

        # Section header
        m = re.match(r'^##\s+(.+)', stripped)
        if m:
            section_name = m.group(1).strip()
            current_section = _normalize_section_name(section_name)
            if current_section not in result:
                result[current_section] = {}
            last_key = None
            continue

        # Key-value line: "- Key: Value"
        m = re.match(r'^-\s+(.+?):\s*(.*)', stripped)
        if m:
            key = m.group(1).strip()
            value = m.group(2).strip()
            normalized_key = _normalize_key(key)
            result[current_section][normalized_key] = value
            last_key = normalized_key
            continue

        # Also try "Key: Value" without leading dash (for Email, Submitted)
        m = re.match(r'^([A-Za-z][A-Za-z\s.]+?):\s*(.*)', stripped)
        if m and not stripped.startswith('#'):
            key = m.group(1).strip()
            value = m.group(2).strip()
            normalized_key = _normalize_key(key)
            result[current_section][normalized_key] = value
            last_key = normalized_key
            continue

        # Continuation line (multi-line value, e.g. race list)
        if stripped and last_key and current_section in result:
            existing = result[current_section].get(last_key, '')
            if existing:
                result[current_section][last_key] = existing + '\n' + stripped
            else:
                result[current_section][last_key] = stripped

    return result


def _normalize_section_name(name: str) -> str:
    """Normalize section name to a consistent key."""
    mapping = {
        'basic info': 'basic_info',
        'basic information': 'basic_info',
        'athlete info': 'basic_info',
        'athlete information': 'basic_info',
        'goals': 'goals',
        'goals racing': 'goals',
        'racing': 'goals',
        'race goals': 'goals',
        'current fitness': 'current_fitness',
        'current fitness markers': 'current_fitness',
        'fitness': 'current_fitness',
        'fitness markers': 'current_fitness',
        'recovery & baselines': 'recovery',
        'recovery baselines': 'recovery',
        'recovery and baselines': 'recovery',
        'recovery baseline': 'recovery',
        'recovery': 'recovery',
        'equipment & data': 'equipment',
        'equipment and data': 'equipment',
        'equipment data': 'equipment',
        'equipment': 'equipment',
        'schedule': 'schedule',
        'schedule availability': 'schedule',
        'availability': 'schedule',
        'training schedule': 'schedule',
        'work & life': 'work_life',
        'work and life': 'work_life',
        'work life': 'work_life',
        'work life balance': 'work_life',
        'lifestyle': 'work_life',
        'health': 'health',
        'health medical': 'health',
        'health history': 'health',
        'strength': 'strength',
        'strength training': 'strength',
        'coaching preferences': 'coaching',
        'coaching': 'coaching',
        'coaching style': 'coaching',
        'mental game': 'mental_game',
        'mental': 'mental_game',
        'mindset': 'mental_game',
        'additional': 'additional',
        'additional info': 'additional',
        'additional information': 'additional',
        'other': 'additional',
        'anything else': 'additional',
    }
    key = name.lower().strip()
    return mapping.get(key, key.replace(' ', '_').lower())


def _normalize_key(key: str) -> str:
    """Normalize a key name to snake_case."""
    k = key.lower().strip()
    # Remove parenthetical notes
    k = re.sub(r'\s*\(.*?\)\s*', '', k)
    # Replace spaces and special chars with underscores
    k = re.sub(r'[^a-z0-9]+', '_', k)
    k = k.strip('_')
    return k


# ===========================================================================
# Unit Conversions
# ===========================================================================

def lbs_to_kg(lbs_str: str) -> float:
    """Convert 'NNN lbs' or 'NNN' to kg."""
    m = re.search(r'([\d.]+)', lbs_str)
    if m:
        return round(float(m.group(1)) * 0.453592, 1)
    return 0.0


def height_to_cm(height_str: str) -> int:
    """Convert height strings like 6'1", 6'1, 6 ft 1 in, 185 cm, 73 in, etc."""
    # Already in cm
    m = re.match(r'([\d.]+)\s*cm', height_str, re.IGNORECASE)
    if m:
        return int(round(float(m.group(1))))

    # Feet and inches: 6'1", 6'1, 6' 1"
    m = re.match(r"(\d+)['\u2019]\s*(\d+)?[\"\u201D]?", height_str)
    if m:
        feet = int(m.group(1))
        inches = int(m.group(2)) if m.group(2) else 0
        return int(round((feet * 12 + inches) * 2.54))

    # "6 ft 1 in" or "6ft 1in"
    m = re.match(r'(\d+)\s*ft\.?\s*(\d+)?\s*(?:in\.?)?', height_str, re.IGNORECASE)
    if m:
        feet = int(m.group(1))
        inches = int(m.group(2)) if m.group(2) else 0
        return int(round((feet * 12 + inches) * 2.54))

    # Just inches
    m = re.match(r'(\d+)\s*in', height_str, re.IGNORECASE)
    if m:
        return int(round(float(m.group(1)) * 2.54))

    return 0


def parse_watts(val: str) -> Optional[int]:
    """Extract watts from '315 W' or '315'."""
    m = re.search(r'(\d+)', val)
    if m:
        return int(m.group(1))
    return None


def parse_wkg(val: str) -> Optional[float]:
    """Extract W/kg from '3.56' or '3.56 W/kg'."""
    m = re.search(r'([\d.]+)', val)
    if m:
        return float(m.group(1))
    return None


def parse_hr(val: str) -> Optional[int]:
    """Extract HR from '45 bpm' or '45'."""
    m = re.search(r'(\d+)', val)
    if m:
        return int(m.group(1))
    return None


def parse_hours(val: str) -> Optional[float]:
    """Extract hours from '7 hrs' or '7' or '7.5'."""
    m = re.search(r'([\d.]+)', val)
    if m:
        return float(m.group(1))
    return None


def parse_range(val: str) -> Tuple[Optional[int], Optional[int]]:
    """Parse '8-10' into (8, 10). Single value -> (val, val)."""
    m = re.match(r'(\d+)\s*[-\u2013]\s*(\d+)', val)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.match(r'(\d+)', val)
    if m:
        v = int(m.group(1))
        return v, v
    return None, None


def parse_years(val: str) -> int:
    """Parse years field to integer: '10+' -> 10, '4+' -> 4, '3' -> 3."""
    m = re.search(r'(\d+)', str(val))
    return int(m.group(1)) if m else 0


def parse_device_list(val: str) -> List[str]:
    """Parse comma-separated device list."""
    return [d.strip().lower() for d in re.split(r'[,\s]+', val) if d.strip()]


def parse_day_list(val: str) -> List[str]:
    """Parse day list: 'sunday, wednesday' or 'sunday wednesday'."""
    days = []
    for token in re.split(r'[,\s]+', val.lower()):
        token = token.strip()
        if token in DAY_ORDER_FULL:
            days.append(token)
    return days


# ===========================================================================
# Unknown Race Helpers
# ===========================================================================

def extract_date_from_text(text: str) -> str:
    """
    Try to extract a race date from free-form text.

    Handles patterns like:
    - "June 6" or "June 6, 2026"
    - "2026-05-30"
    - "May 30, 2026"
    - "5/30/2026" or "05/30/2026"

    Returns YYYY-MM-DD string or '' if nothing found.
    """
    if not text:
        return ''

    month_names = {
        'january': 1, 'february': 2, 'march': 3, 'april': 4,
        'may': 5, 'june': 6, 'july': 7, 'august': 8,
        'september': 9, 'october': 10, 'november': 11, 'december': 12,
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4,
        'jun': 6, 'jul': 7, 'aug': 8, 'sep': 9, 'sept': 9,
        'oct': 10, 'nov': 11, 'dec': 12,
    }

    # ISO format: 2026-05-30
    m = re.search(r'\b(\d{4})-(\d{1,2})-(\d{1,2})\b', text)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"

    # "Month Day, Year" or "Month Day Year" or "Month Day"
    month_pat = '|'.join(month_names.keys())
    m = re.search(
        rf'\b({month_pat})\s+(\d{{1,2}})(?:\s*,?\s*(\d{{4}}))?\b',
        text, re.IGNORECASE,
    )
    if m:
        month_num = month_names[m.group(1).lower()]
        day = int(m.group(2))
        year = int(m.group(3)) if m.group(3) else date.today().year
        if 1 <= day <= 31:
            return f"{year}-{month_num:02d}-{day:02d}"

    # US date format: M/D/YYYY or MM/DD/YYYY
    m = re.search(r'\b(\d{1,2})/(\d{1,2})/(\d{4})\b', text)
    if m:
        month_num = int(m.group(1))
        day = int(m.group(2))
        year = int(m.group(3))
        if 1 <= month_num <= 12 and 1 <= day <= 31:
            return f"{year}-{month_num:02d}-{day:02d}"

    return ''


def extract_distance_from_name(name: str) -> int:
    """
    Try to extract a distance in miles from a race name.

    Examples:
    - "Steamboat 100" -> 100
    - "Unbound 200" -> 200
    - "Gravel Growler 50K" -> 31  (km -> miles)
    - "Big Race" -> 0 (no distance found)

    Returns distance in miles, or 0 if not extractable.
    """
    if not name:
        return 0

    # Check for explicit km/K suffix first: "50K" or "100km"
    m = re.search(r'\b(\d+)\s*(?:km|k)\b', name, re.IGNORECASE)
    if m:
        km = int(m.group(1))
        return round(km * 0.621371)

    # Check for a trailing number (e.g., "Steamboat 100", "Unbound 200")
    m = re.search(r'\b(\d+)\s*(?:miles?|mi)?\s*$', name.strip(), re.IGNORECASE)
    if m:
        return int(m.group(1))

    # Check for number anywhere in the name (common: "Gravel 100", "XYZ 50")
    m = re.search(r'\b(\d{2,3})\b', name)
    if m:
        return int(m.group(1))

    return 0


# ===========================================================================
# Race Matching
# ===========================================================================

# ===========================================================================
# Athlete ID Generation
# ===========================================================================

def generate_athlete_id(full_name: str) -> str:
    """
    Generate athlete_id from full name.
    Uses first + last name only (skip middle names).
    Lowercase, hyphens, no special chars.
    E.g. 'Nicholas Clift Shaw Applegate' -> 'nicholas-applegate'
    """
    parts = full_name.strip().split()
    if len(parts) == 0:
        raise ValueError("Cannot generate athlete_id from empty name")
    if len(parts) == 1:
        return re.sub(r'[^a-z0-9-]', '', parts[0].lower())

    first = parts[0]
    last = parts[-1]
    raw = f"{first}-{last}".lower()
    return re.sub(r'[^a-z0-9-]', '', raw)


# ===========================================================================
# Profile Builder
# ===========================================================================

def build_profile(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a profile.yaml dict from parsed questionnaire data.
    Follows the exact structure used by existing athlete profiles.
    """
    athlete_name = parsed.get('athlete_name', 'Unknown Athlete')
    athlete_id = generate_athlete_id(athlete_name)

    # Pull section dicts with safe defaults
    header = parsed.get('__header__', {})
    basic = parsed.get('basic_info', {})
    goals = parsed.get('goals', {})
    fitness = parsed.get('current_fitness', {})
    recovery = parsed.get('recovery', {})
    equipment = parsed.get('equipment', {})
    schedule = parsed.get('schedule', {})
    work_life = parsed.get('work_life', {})
    health = parsed.get('health', {})
    strength = parsed.get('strength', {})
    coaching = parsed.get('coaching', {})
    mental = parsed.get('mental_game', {})
    additional = parsed.get('additional', {})

    email = header.get('email', basic.get('email', ''))
    submitted = header.get('submitted', '')

    # -- Unit conversions --
    sex = basic.get('sex', 'male').lower()
    age = _safe_int(basic.get('age', '0'))

    weight_raw = basic.get('weight', '')
    if 'lbs' in weight_raw.lower() or 'lb' in weight_raw.lower():
        # Explicit lbs/lb unit -- convert to kg
        weight_kg = lbs_to_kg(weight_raw)
    elif 'kg' in weight_raw.lower():
        # Explicit kg unit -- use as-is
        m = re.search(r'([\d.]+)', weight_raw)
        weight_kg = float(m.group(1)) if m else 0.0
    else:
        # No explicit unit -- infer from value
        m = re.search(r'([\d.]+)', weight_raw)
        if m:
            val = float(m.group(1))
            if val < WEIGHT_TOO_LIGHT:
                # Too light for any unit -- flag as error (will be caught by sanity check)
                weight_kg = val
            elif val <= 100:
                # 40-100 range with no unit: assume kg
                weight_kg = val
            else:
                # > 100 with no unit: assume lbs, convert
                weight_kg = lbs_to_kg(weight_raw)
        else:
            weight_kg = 0.0

    height_raw = basic.get('height', '')
    height_cm = height_to_cm(height_raw) if height_raw else 0

    ftp_raw = fitness.get('ftp', '')
    ftp_watts = parse_watts(ftp_raw)

    wkg_raw = fitness.get('w_kg', fitness.get('w/kg', ''))
    w_kg = parse_wkg(wkg_raw)
    if w_kg is None and ftp_watts and weight_kg > 0:
        w_kg = round(ftp_watts / weight_kg, 2)

    resting_hr = parse_hr(recovery.get('resting_hr', ''))
    sleep_hours = parse_hours(recovery.get('typical_sleep', ''))
    sleep_quality = recovery.get('sleep_quality', 'good').lower()
    recovery_speed = recovery.get('recovery_speed', 'normal').lower()
    hrv = recovery.get('hrv_baseline', '')

    # -- Goals / Races --
    primary_goal = goals.get('primary_goal', 'specific_race').lower()
    races_raw = goals.get('races', '')
    race_list = [r.strip() for r in races_raw.split('\n') if r.strip()]
    success_text = goals.get('success', '')
    obstacles_text = goals.get('obstacles', '')

    # Match races
    a_events = []
    b_events = []
    target_race_info = {}

    for i, race_name in enumerate(race_list):
        matched = match_race(race_name)
        event = {
            'name': race_name,
            'date': '',
            'distance_miles': 0,
            'goal': 'finish' if i == 0 else 'compete',
            'priority': 'A' if i == 0 else 'B',
        }
        if matched:
            race_id, info = matched
            event['date'] = info['date']
            event['distance_miles'] = info['distance_miles']
            if i == 0:
                target_race_info = {
                    'name': info['name'],
                    'race_id': race_id,
                    'date': info['date'],
                    'distance_miles': info['distance_miles'],
                    'elevation_ft': info.get('elevation_ft', 0),
                    'goal_type': 'finish',
                    'goal': 'finish',
                    'goal_description': success_text,
                }
                event['name'] = info['name']
        else:
            # Unknown race — extract what we can from athlete-provided data
            print(f"{YELLOW}WARNING: Race '{race_name}' not in known_races.py "
                  f"— using athlete-provided data. Consider adding to known_races.py.{RESET}")

            # Try to extract distance from race name (e.g., "Steamboat 100" -> 100)
            extracted_distance = extract_distance_from_name(race_name)
            event['distance_miles'] = extracted_distance

            # Try to extract date from the full questionnaire text
            # Look in goals section first (most likely location for race dates)
            goals_text = ' '.join(str(v) for v in goals.values() if v)
            extracted_date = extract_date_from_text(goals_text)
            if extracted_date:
                event['date'] = extracted_date

            if i == 0:
                target_race_info = {
                    'name': race_name,
                    'race_id': re.sub(r'[^a-z0-9]+', '_', race_name.lower()).strip('_'),
                    'date': extracted_date,
                    'distance_miles': extracted_distance,
                    'elevation_ft': 0,
                    'goal_type': 'finish',
                    'goal': 'finish',
                    'goal_description': success_text,
                }

        if i == 0:
            a_events.append(event)
        else:
            b_events.append(event)

    # -- Schedule --
    weekly_hours_raw = schedule.get('weekly_hours_available', '0')
    hours_min, hours_max = parse_range(weekly_hours_raw)
    cycling_hours_target = hours_max or hours_min or 0

    current_vol_raw = schedule.get('current_volume', '0')
    vol_min, vol_max = parse_range(current_vol_raw)
    current_weekly_hours = vol_max or vol_min or 0

    long_ride_days = parse_day_list(schedule.get('long_ride_days', 'saturday'))
    interval_days = parse_day_list(schedule.get('interval_days', ''))
    off_days = parse_day_list(schedule.get('off_days', ''))

    preferred_long_day = long_ride_days[0] if long_ride_days else 'saturday'

    # Build preferred_days
    preferred_days = {}
    for day in DAY_ORDER_FULL:
        if day in off_days:
            preferred_days[day] = {
                'availability': 'unavailable',
                'time_slots': [],
                'max_duration_min': 0,
                'is_key_day_ok': False,
            }
        elif day in long_ride_days:
            preferred_days[day] = {
                'availability': 'available',
                'time_slots': ['am'],
                'max_duration_min': 600,
                'is_key_day_ok': True,
            }
        elif day in interval_days:
            preferred_days[day] = {
                'availability': 'available',
                'time_slots': ['pm'],
                'max_duration_min': 120,
                'is_key_day_ok': True,
            }
        elif day in WEEKEND_FULL:
            preferred_days[day] = {
                'availability': 'available',
                'time_slots': ['am', 'pm'],
                'max_duration_min': 240,
                'is_key_day_ok': True,
            }
        else:
            # Regular weekday
            preferred_days[day] = {
                'availability': 'available',
                'time_slots': ['pm'],
                'max_duration_min': 120,
                'is_key_day_ok': False,
            }

    # -- Strength --
    strength_current = strength.get('current', 'none').lower()
    strength_include = strength.get('include', 'no').lower()
    strength_equip_raw = strength.get('equipment', 'minimal').lower()
    currently_training = strength_current not in ('none', 'no', '')
    include_in_plan = strength_include in ('yes', 'true', '1')
    strength_sessions = 0 if not include_in_plan else 2
    strength_equipment = [s.strip() for s in strength_equip_raw.split(',') if s.strip()]
    if not strength_equipment:
        strength_equipment = ['minimal']

    total_hours = cycling_hours_target + (2 if include_in_plan else 0)

    # -- Equipment --
    devices_raw = equipment.get('devices', '')
    device_list = parse_device_list(devices_raw)
    platform = equipment.get('platform', 'trainingpeaks').lower()
    intervals_id = equipment.get('intervals_icu_id', equipment.get('intervals_icu', ''))
    if intervals_id and intervals_id.lower() in ('n/a', 'na', 'none', ''):
        intervals_id = ''
    indoor_trainer = equipment.get('indoor_trainer', 'none').lower()
    indoor_tolerance_raw = equipment.get('indoor_tolerance', 'tolerate').lower()

    smart_trainer = 'smart_trainer' in device_list or 'smart' in indoor_trainer
    power_meter = 'power_meter' in device_list
    hr_monitor = 'hr_strap' in device_list or 'hr_monitor' in device_list

    indoor_tolerance_map = {
        'love': 'excellent',
        'love_it': 'excellent',
        'tolerate': 'tolerate_it',
        'tolerate_it': 'tolerate_it',
        'hate': 'hate_it',
        'hate_it': 'hate_it',
    }
    indoor_tolerance = indoor_tolerance_map.get(indoor_tolerance_raw, 'tolerate_it')

    # -- Health --
    current_injuries_raw = health.get('current_injuries', 'None')
    past_injuries_raw = health.get('past_injuries', '')
    medical_conditions = health.get('medical_conditions', '')
    medications = health.get('medications', '')

    current_injuries = []
    if current_injuries_raw and current_injuries_raw.lower() not in ('none', 'n/a', ''):
        current_injuries.append({
            'area': 'general',
            'description': current_injuries_raw,
            'status': 'active',
        })

    past_injuries = []
    if past_injuries_raw and past_injuries_raw.lower() not in ('none', 'n/a', ''):
        # Try to extract body part
        area = 'general'
        for body_part in ['ankle', 'knee', 'back', 'shoulder', 'hip', 'neck', 'wrist']:
            if body_part in past_injuries_raw.lower():
                area = body_part
                break
        side = None
        for s in ['left', 'right', 'both']:
            if s in past_injuries_raw.lower():
                side = s
                break
        entry = {
            'area': area,
            'description': past_injuries_raw,
            'status': 'chronic' if 'chronic' in past_injuries_raw.lower() else 'recovered',
            'management': past_injuries_raw,
        }
        if side:
            entry['side'] = side
        past_injuries.append(entry)

    # -- Work / Life --
    work_hours = _safe_int(work_life.get('work_hours', '40'))
    job_stress = work_life.get('job_stress', 'moderate').lower()
    life_stress = work_life.get('life_stress', 'moderate').lower()
    family = work_life.get('family', '')
    overall_stress = 'high' if job_stress == 'high' or life_stress == 'high' else job_stress

    # -- Coaching --
    checkin = coaching.get('check_in_frequency', coaching.get('check-in_frequency', 'weekly')).lower()
    feedback = coaching.get('feedback_detail', 'moderate').lower()
    autonomy_raw = coaching.get('autonomy', 'guided').lower()
    comm_style = coaching.get('communication_style', 'flexible').lower()

    autonomy_map = {
        'guided': 'general_guidance',
        'general_guidance': 'general_guidance',
        'tell_me': 'tell_me_exactly',
        'tell_me_exactly': 'tell_me_exactly',
        'autonomous': 'high_autonomy',
        'high_autonomy': 'high_autonomy',
        'high': 'high_autonomy',
    }
    autonomy = autonomy_map.get(autonomy_raw, 'general_guidance')

    # -- Mental Game --
    missed_workout = mental.get('missed_workout_response', 'move_on').lower()
    best_block = mental.get('best_training_block', '')
    quit_triggers = mental.get('quit_triggers', '')
    accountability = mental.get('accountability_style', 'self').lower()

    # -- Additional --
    previous_coach_raw = additional.get('previous_coach', 'no')
    previous_coach = previous_coach_raw.lower().startswith('yes')
    coach_experience = previous_coach_raw if previous_coach else ''
    # Strip leading "Yes." or "Yes," etc.
    if previous_coach and re.match(r'^[Yy]es[.,;:!]?\s*', coach_experience):
        coach_experience = re.sub(r'^[Yy]es[.,;:!]?\s*', '', coach_experience).strip()
    other_notes = additional.get('other', '')

    # -- Methodology preferences (derived from text) --
    all_text = ' '.join([
        success_text, obstacles_text, other_notes, coach_experience,
        str(additional), fitness.get('strengths', ''), fitness.get('weaknesses', ''),
    ]).lower()

    methodology = _derive_methodology(all_text)

    # -- Fitness category --
    years_cycling = parse_years(fitness.get('years_cycling', '0'))
    years_structured = parse_years(fitness.get('years_structured', '0'))
    longest_recent = fitness.get('longest_recent_ride', '')
    estimated_cat = fitness.get('estimated_category', '')

    # -- Training history summary --
    strengths = fitness.get('strengths', '')
    weaknesses = fitness.get('weaknesses', '')
    overtraining = recovery.get('overtraining_history', 'never').lower()

    # -- Plan start --
    today = date.today()
    # Next Monday
    days_until_monday = (7 - today.weekday()) % 7
    if days_until_monday == 0:
        days_until_monday = 7
    plan_start = today + __import__('datetime').timedelta(days=days_until_monday)
    plan_start_str = plan_start.isoformat()

    # Calculate weeks to target race (with clamping to 4-26 range)
    MIN_PLAN_WEEKS = 4
    MAX_PLAN_WEEKS = 26
    race_date_str = target_race_info.get('date', '')
    plan_notes = f"Submitted {submitted}." if submitted else ''
    if race_date_str:
        race_dt = datetime.strptime(race_date_str, '%Y-%m-%d').date()
        weeks_to_race_raw = (race_dt - plan_start).days // 7
        weeks_to_race = max(MIN_PLAN_WEEKS, min(MAX_PLAN_WEEKS, weeks_to_race_raw))
        if weeks_to_race_raw < MIN_PLAN_WEEKS:
            print(f"{YELLOW}WARNING: Only {weeks_to_race_raw} weeks to race — "
                  f"clamping plan to minimum {MIN_PLAN_WEEKS} weeks. "
                  f"Race is very soon; plan will be compressed.{RESET}")
        elif weeks_to_race_raw > MAX_PLAN_WEEKS:
            print(f"{YELLOW}WARNING: {weeks_to_race_raw} weeks to race — "
                  f"clamping plan to maximum {MAX_PLAN_WEEKS} weeks (6 months). "
                  f"Extra lead time will not be structured.{RESET}")
        if plan_notes:
            plan_notes += f" ~{weeks_to_race} weeks to {target_race_info.get('name', 'target race')} on {race_date_str}."
        else:
            plan_notes = f"~{weeks_to_race} weeks to {target_race_info.get('name', 'target race')} on {race_date_str}."

    # Build training_goals and goals_notes from parsed text
    training_goals = ''
    goals_notes = ''
    if 'base' in all_text or 'zone 2' in all_text:
        training_goals = 'Build durability through base volume.'
    if 'sweet spot' in all_text and ('didn' in all_text or 'not' in all_text or 'fail' in all_text):
        training_goals += ' NOT sweet spot.' if training_goals else 'NOT sweet spot.'
        goals_notes = 'Athlete explicitly states sweet spot approach did not work previously.'

    # -- Build the profile dict --
    profile = {
        'name': athlete_name,
        'email': email,
        'athlete_id': athlete_id,
        'sex': sex,
        'height_cm': height_cm,
        'weight_kg': weight_kg,
        'primary_goal': primary_goal.replace(' ', '_'),
        'target_race': target_race_info,
        'a_events': a_events,
        'b_events': b_events,
        'c_events': [],
        'secondary_races': [],
        'racing': {
            'has_goals': True,
            'race_list': '\n'.join(race_list),
            'success_metrics': success_text,
            'obstacles': obstacles_text,
            'training_goals': training_goals,
            'goals_notes': goals_notes,
        },
        'training_history': {
            'summary': _build_training_summary(fitness, additional),
            'years_cycling': years_cycling,
            'years_structured': years_structured,
            'strength_background': strength_current if strength_current != 'none' else 'none',
            'highest_weekly_hours': cycling_hours_target,
            'current_weekly_hours': current_weekly_hours,
            'strengths': strengths,
            'weaknesses': weaknesses,
        },
        'fitness_markers': {
            'ftp_watts': ftp_watts,
            'ftp_date': today.isoformat(),
            'weight_kg': weight_kg,
            'height_cm': height_cm,
            'sex': sex,
            'w_kg': w_kg,
            'resting_hr': resting_hr,
            'max_hr': None,
        },
        'recent_training': {
            'last_12_weeks': 'sporadic',
            'current_phase': 'base',
            'coming_off_injury': bool(current_injuries),
            'days_since_last_ride': None,
        },
        'weekly_availability': {
            'total_hours_available': total_hours,
            'cycling_hours_target': cycling_hours_target,
            'strength_sessions_max': strength_sessions,
            'notes': f"{weekly_hours_raw} hours/week available. Currently doing {current_vol_raw}.",
        },
        'preferred_days': preferred_days,
        'schedule_constraints': {
            'work_schedule': '9-5',
            'work_hours': work_hours,
            'travel_frequency': 'none',
            'family_commitments': family,
            'seasonal_changes': '',
            'preferred_off_days': off_days,
            'preferred_long_day': preferred_long_day,
        },
        'cycling_equipment': {
            'smart_trainer': smart_trainer,
            'power_meter_bike': power_meter,
            'hr_monitor': hr_monitor,
            'indoor_setup': 'smart_trainer' if smart_trainer else 'none',
            'bike_computer': 'garmin' if 'garmin' in device_list else '',
        },
        'strength_equipment': strength_equipment,
        'training_environment': {
            'primary_location': 'home',
            'gym_type': 'none' if not include_in_plan else 'home_gym',
            'outdoor_riding_access': 'good',
            'indoor_riding_tolerance': indoor_tolerance,
        },
        'injury_history': {
            'current_injuries': current_injuries,
            'past_injuries': past_injuries,
        },
        'movement_limitations': _build_movement_limitations(past_injuries),
        'health_factors': {
            'age': age,
            'sleep_quality': sleep_quality,
            'sleep_hours_avg': int(sleep_hours) if sleep_hours else 7,
            'stress_level': overall_stress,
            'recovery_capacity': recovery_speed,
            'medical_conditions': medical_conditions,
            'medications': medications,
            'health_notes': _build_health_notes(recovery, health, work_life),
        },
        'strength': {
            'currently_training': currently_training,
            'routine': '',
            'include_in_plan': include_in_plan,
            'sessions_per_week': strength_sessions,
            'mobility_rating': 3,
        },
        'devices': {
            'training_log': True,
            'platforms': [platform] if platform else ['trainingpeaks'],
            'devices': device_list if device_list else [],
        },
        'work': {
            'employed': True,
            'hours_per_week': work_hours,
            'stress_level': job_stress,
        },
        'life_balance': {
            'relationships': family,
            'time_commitments': 'Family time' if family else '',
            'time_management_challenge': job_stress == 'high' or life_stress == 'high',
        },
        'nutrition': {
            'diet_styles': [],
            'fluid_intake_rating': None,
            'restrictions': '',
            'training_fuel': '',
            'post_workout': '',
            'notes': '',
        },
        'bike': {
            'last_fit': '',
            'pain': False,
            'pain_description': '',
        },
        'social': {
            'group_rides_per_week': 0,
            'group_ride_importance': None,
            'training_partners': '',
        },
        'coaching': {
            'previous_coach': previous_coach,
            'experience': coach_experience,
        },
        'personal': {
            'important_people': family,
            'anything_else': other_notes,
            'life_affecting_training': _build_life_summary(work_life),
        },
        'methodology_preferences': methodology,
        'workout_preferences': {
            'longest_indoor_tolerable': 120,
            'preferred_interval_style': 'mixed',
            'music_or_entertainment': 'preferred',
            'group_rides_available': False,
            'outdoor_interval_friendly': True,
        },
        'strength_preferences': {
            'experience_level': strength_current if strength_current != 'none' else 'none',
            'comfort_with_barbell': 'none' if not currently_training else 'moderate',
            'comfort_with_kettlebells': 'none' if not currently_training else 'moderate',
            'preferred_session_length': 0 if not include_in_plan else 45,
            'time_of_day': None if not include_in_plan else 'separate_day',
        },
        'coaching_style': {
            'communication_frequency': checkin,
            'feedback_detail': feedback,
            'accountability_need': 'moderate',
            'autonomy_preference': autonomy,
            'communication_style': comm_style,
        },
        'motivation': {
            'primary_driver': 'achievement',
            'what_excites_you': success_text,
            'what_scares_you': '',
            'past_quit_reasons': quit_triggers,
            'accountability_style': accountability,
        },
        'mental_game': {
            'race_anxiety': 'mild',
            'training_consistency': 'good',
            'handles_failure': 'well',
            'perfectionist': False,
            'missed_workout_response': missed_workout.replace(' ', '_'),
            'best_training_block': best_block,
        },
        'lifestyle': {
            'occupation': '',
            'active_job': False,
            'commute_bikeable': False,
            'family_support': 'neutral',
            'weight_goal': 'maintain',
        },
        'platforms': {
            'primary': platform,
            'secondary': '',
            'calendar_integration': '',
        },
        'communication': {
            'preferred_method': 'email',
            'timezone': '',
            'best_time_to_reach': '',
        },
        'plan_start': {
            'preferred_start': plan_start_str,
            'current_commitments': '',
            'notes': plan_notes,
        },
    }

    return profile


def _derive_methodology(text: str) -> Dict[str, Any]:
    """Extract explicit methodology exclusions from free-text answers.

    Methodology selection is handled by select_methodology.py based on
    objective criteria (hours, experience, stress, race demands).
    This function does NOT set preference scores — all stay neutral at 3.

    It ONLY extracts:
    - past_failure_with: explicit rejections ("sweet spot didn't work") → hard veto
    - past_success_with: explicit endorsements ("polarized worked well")
    """
    prefs = {
        'polarized': 3,
        'pyramidal': 3,
        'threshold_focused': 3,
        'hiit_focused': 3,
        'high_volume': 3,
        'time_crunched': 3,
        'preferred_approach': '',
        'past_success_with': '',
        'past_failure_with': '',
    }

    # Map training approach keywords → methodology display names
    # These are used for matching against methodology names in select_methodology.py
    approach_keywords = {
        'sweet spot': 'Sweet Spot / Threshold',
        'threshold': 'Threshold',
        'hiit': 'HIIT',
        'high intensity': 'HIIT',
        'polarized': 'Polarized',
        '80/20': 'Polarized',
        'base only': 'MAF',
        'maf': 'MAF',
        'low hr': 'Low-HR',
        'high volume': 'volume',
        'block': 'Block',
    }

    # Negative context patterns (within ~80 chars of keyword)
    negative_pats = [
        r"(?:didn.?t|did not|doesn.?t|does not|not|never|fail|lack|poor|"
        r"struggle|quit|gave up|dropped|stop|worse|bad|wrong|didn.?t work|"
        r"didn.?t help|didn.?t build|doesn.?t seem|doesn.?t build)"
    ]

    # Positive context patterns (within ~80 chars of keyword)
    positive_pats = [
        r"(?:success|worked|strong|good|loved|enjoy|best|great|benefit|"
        r"helped|built|gained|improved|effective)"
    ]

    failures = []
    successes = []

    for keyword, label in approach_keywords.items():
        if keyword not in text:
            continue

        # Search all occurrences of the keyword
        start = 0
        while True:
            idx = text.find(keyword, start)
            if idx == -1:
                break
            # Window: 80 chars before and after keyword
            window = text[max(0, idx - 80):idx + len(keyword) + 80]

            if any(re.search(pat, window, re.IGNORECASE) for pat in negative_pats):
                if label not in failures:
                    failures.append(label)
            elif any(re.search(pat, window, re.IGNORECASE) for pat in positive_pats):
                if label not in successes:
                    successes.append(label)

            start = idx + len(keyword)

    # Remove contradictions: if something is both success and failure, failure wins
    successes = [s for s in successes if s not in failures]

    if failures:
        prefs['past_failure_with'] = '; '.join(failures)
    if successes:
        prefs['past_success_with'] = '; '.join(successes)

    return prefs


def _build_training_summary(fitness: Dict, additional: Dict) -> str:
    """Build a training history summary string."""
    parts = []
    years = fitness.get('years_cycling', '')
    if years:
        parts.append(f"{years} years cycling")
    yrs_struct = fitness.get('years_structured', '')
    if yrs_struct:
        parts.append(f"{yrs_struct} years structured")
    cat = fitness.get('estimated_category', '')
    if cat:
        parts.append(f"{cat}")
    return ', '.join(parts) + '.' if parts else ''


def _build_movement_limitations(past_injuries: List) -> Dict:
    """Build movement limitations from injury data."""
    limitations = {
        'deep_squat': None,
        'hip_hinge': None,
        'overhead_reach': None,
        'single_leg_balance': None,
        'push_up_position': None,
        'notes': '',
    }
    notes = []
    for inj in past_injuries:
        area = inj.get('area', '')
        desc = inj.get('description', '')
        if area in ('ankle', 'knee', 'hip'):
            limitations['deep_squat'] = 'limited'
            notes.append(f"{area} issue - limits ROM")
        if area in ('back', 'shoulder'):
            limitations['hip_hinge'] = 'limited'
    limitations['notes'] = '; '.join(notes) if notes else ''
    return limitations


def _build_health_notes(recovery: Dict, health: Dict, work_life: Dict) -> str:
    """Build health notes from multiple sections."""
    parts = []
    conditions = health.get('medical_conditions', '')
    if conditions and conditions.lower() not in ('none', 'n/a', ''):
        parts.append(conditions)
    rec_speed = recovery.get('recovery_speed', '')
    if rec_speed and rec_speed.lower() == 'slow':
        parts.append('Slow recovery self-assessment')
    stress = work_life.get('job_stress', '')
    life_stress = work_life.get('life_stress', '')
    if stress == 'high' or life_stress == 'high':
        stress_parts = []
        if stress == 'high':
            stress_parts.append('work')
        if life_stress == 'high':
            stress_parts.append('life')
        hrs = work_life.get('work_hours', '')
        stress_str = f"High {' and '.join(stress_parts)} stress"
        if hrs:
            stress_str += f" ({hrs}hr work weeks"
            fam = work_life.get('family', '')
            if fam:
                stress_str += f", {fam})"
            else:
                stress_str += ")"
        parts.append(stress_str)
    ot = recovery.get('overtraining_history', '')
    if ot and ot.lower() != 'never':
        parts.append(f"Overtraining history: {ot}")
    else:
        parts.append('Never overtrained')
    return '. '.join(parts) + '.' if parts else ''


def _build_life_summary(work_life: Dict) -> str:
    """Build a life-affecting-training summary."""
    parts = []
    hrs = work_life.get('work_hours', '')
    if hrs:
        parts.append(f"{hrs}hr work weeks")
    stress = work_life.get('job_stress', '')
    if stress == 'high':
        parts.append('high stress')
    fam = work_life.get('family', '')
    if fam:
        parts.append(fam.lower())
    return ', '.join(parts) if parts else ''


def _safe_int(val: str) -> int:
    """Safely parse an integer from string."""
    m = re.search(r'(\d+)', str(val))
    return int(m.group(1)) if m else 0


def _safe_int_or_str(val: str) -> Any:
    """Return int if purely numeric, else keep as string (e.g. '4+')."""
    try:
        return int(val)
    except (ValueError, TypeError):
        return val


# ===========================================================================
# YAML Writer
# ===========================================================================

def write_profile_yaml(profile: Dict[str, Any], output_path: Path) -> None:
    """Write profile dict to YAML file with comments."""
    import yaml

    # Custom representer to handle None as null
    class CustomDumper(yaml.SafeDumper):
        pass

    def str_representer(dumper, data):
        if '\n' in data:
            return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
        return dumper.represent_scalar('tag:yaml.org,2002:str', data)

    CustomDumper.add_representer(str, str_representer)

    header_comment = (
        f"# Athlete Profile: {profile['name']}\n"
        f"# Generated by intake_to_plan.py on {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
        f"# Source: intake questionnaire\n\n"
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        f.write(header_comment)
        yaml.dump(profile, f, Dumper=CustomDumper, default_flow_style=False,
                  sort_keys=False, allow_unicode=True, width=120)

    print(f"  {GREEN}Written:{RESET} {output_path}")


# ===========================================================================
# Coaching Brief Generator
# ===========================================================================

def generate_coaching_brief(
    profile: Dict[str, Any],
    parsed: Dict[str, Any],
) -> str:
    """Generate private coaching brief markdown."""
    name = profile['name']
    athlete_id = profile['athlete_id']
    target = profile.get('target_race', {})
    ftp = profile.get('fitness_markers', {}).get('ftp_watts', '?')
    w_kg = profile.get('fitness_markers', {}).get('w_kg', '?')
    weight_kg = profile.get('weight_kg', '?')
    cycling_hours = profile.get('weekly_availability', {}).get('cycling_hours_target', '?')
    methodology = profile.get('methodology_preferences', {})

    # Determine tier heuristic
    try:
        hrs = int(cycling_hours)
    except (ValueError, TypeError):
        hrs = 0
    if hrs <= 5:
        tier = 'Ayahuasca (<=5hrs)'
    elif hrs <= 10:
        tier = 'Finisher (<=10hrs)'
    elif hrs <= 16:
        tier = 'Compete (<=16hrs)'
    else:
        tier = 'Podium (>16hrs)'

    # Determine methodology name
    meth_scores = {
        'Polarized': methodology.get('polarized', 3),
        'Pyramidal': methodology.get('pyramidal', 3),
        'Threshold': methodology.get('threshold_focused', 3),
        'HIIT': methodology.get('hiit_focused', 3),
    }
    top_meth = max(meth_scores, key=meth_scores.get)
    if meth_scores[top_meth] >= 4:
        meth_name = f"{top_meth} (80/20)" if top_meth == 'Polarized' else top_meth
    else:
        meth_name = "Balanced / Structured"

    # Race date
    race_date = target.get('date', 'TBD')
    race_name = target.get('name', 'TBD')

    # Plan duration estimate
    plan_weeks = '?'
    if race_date and race_date != 'TBD':
        try:
            rd = datetime.strptime(race_date, '%Y-%m-%d').date()
            today = date.today()
            days_until_monday = (7 - today.weekday()) % 7
            if days_until_monday == 0:
                days_until_monday = 7
            start = today + __import__('datetime').timedelta(days=days_until_monday)
            plan_weeks = str((rd - start).days // 7)
        except (ValueError, TypeError):
            pass

    # Build the questionnaire -> decision mapping table
    schedule = parsed.get('schedule', {})
    recovery = parsed.get('recovery', {})
    health = parsed.get('health', {})
    additional = parsed.get('additional', {})
    goals = parsed.get('goals', {})
    strength_sec = parsed.get('strength', {})
    work_life = parsed.get('work_life', {})
    coaching_sec = parsed.get('coaching', {})
    fitness = parsed.get('current_fitness', {})

    mappings = []

    # Hours -> tier
    hrs_raw = schedule.get('weekly_hours_available', '?')
    mappings.append((
        f"Weekly Hours: {hrs_raw}",
        f"Tier: {tier}",
        f"{hrs_raw} hrs maps to {tier.lower()} tier",
    ))

    # FTP -> ability
    if ftp and w_kg:
        ability = 'Intermediate' if float(w_kg) < 4.0 else 'Advanced'
        mappings.append((
            f"FTP: {ftp}W at {weight_kg}kg",
            f"{ability} ability",
            f"{w_kg} W/kg = solid {fitness.get('estimated_category', 'Cat 4')}",
        ))

    # Long ride day
    long_days = schedule.get('long_ride_days', '')
    if long_days:
        mappings.append((
            f"Long Ride: {long_days.title()}",
            f"{long_days.title()} long Z2 ride",
            "Respected as-is, ramping to 8+ hrs",
        ))

    # Off days
    off_days = schedule.get('off_days', '')
    if off_days:
        mappings.append((
            f"Off Days: {off_days.title()}",
            f"No workouts {off_days.title()}",
            "Full rest day",
        ))

    # Interval days
    int_days = schedule.get('interval_days', '')
    if int_days:
        mappings.append((
            f"Interval Days: {int_days.title()}",
            f"{int_days.title()} key day",
            "VO2max/Anaerobic assigned here",
        ))

    # Recovery speed
    rec_speed = recovery.get('recovery_speed', '')
    if rec_speed and rec_speed.lower() == 'slow':
        mappings.append((
            "Recovery Speed: slow",
            "High stress flag",
            "Reduced intensity frequency",
        ))

    # Methodology from text
    other_text = additional.get('other', '')
    if 'sweet spot' in other_text.lower() or 'base' in other_text.lower():
        mappings.append((
            "Past: sweet spot didn't work",
            f"{top_meth} methodology",
            "Explicitly base-focused, not threshold",
        ))

    # Strength
    include = strength_sec.get('include', 'no')
    mappings.append((
        f"Include Strength: {include}",
        f"{profile.get('strength', {}).get('sessions_per_week', 0)} strength sessions",
        "Ankle limitation noted" if any(i.get('area') == 'ankle' for i in profile.get('injury_history', {}).get('past_injuries', [])) else "Per athlete preference",
    ))

    # Medical
    conditions = health.get('medical_conditions', '')
    if conditions and conditions.lower() not in ('none', 'n/a', ''):
        mappings.append((
            conditions,
            "Medical flag",
            "Monitor recovery, adjust intensity accordingly",
        ))

    # Coaching style
    autonomy_raw = coaching_sec.get('autonomy', '')
    if autonomy_raw:
        mappings.append((
            f"Autonomy: {autonomy_raw}",
            f"{profile.get('coaching_style', {}).get('autonomy_preference', '')}",
            "Wants to understand WHY behind each workout",
        ))

    # Build risk factors
    risks = []
    if work_life.get('job_stress', '').lower() == 'high':
        work_hrs = work_life.get('work_hours', '')
        risks.append(f"High work stress ({work_hrs}hr weeks)" if work_hrs else "High work stress")
    if work_life.get('life_stress', '').lower() == 'high':
        fam = work_life.get('family', '')
        risks.append(f"High life stress ({fam})" if fam else "High life stress")
    if recovery.get('recovery_speed', '').lower() == 'slow':
        risks.append("Slow recovery")
    if conditions and conditions.lower() not in ('none', 'n/a', ''):
        med = health.get('medications', '')
        risk_str = conditions
        if med and med.lower() not in ('none', 'n/a', ''):
            risk_str += f" -- monitor for complications"
        risks.append(risk_str)
    for inj in profile.get('injury_history', {}).get('past_injuries', []):
        area = inj.get('area', '')
        desc = inj.get('description', '')
        side = inj.get('side', '')
        if area:
            risk_str = f"Chronic {side + ' ' if side else ''}{area}"
            if desc:
                risk_str += f" -- {desc[:80]}"
            risks.append(risk_str)

    # Build key notes
    notes = []
    other = additional.get('other', '')
    prev = additional.get('previous_coach', '')
    if 'base' in other.lower():
        notes.append("Athlete explicitly wants BASE BUILDING, not sweet spot")
    if 'sweet spot' in other.lower():
        notes.append("Previous failure: dedicated sweet spot block -- lacked durability")
    if 'trainer' in other.lower():
        notes.append("Willing to do 2hr trainer sessions on weeknights")
    if prev and prev.lower().startswith('yes'):
        notes.append("Has worked with a coach before -- likes flexibility")
    if 'understand' in (prev + other).lower() or 'why' in (prev + other).lower():
        notes.append("Wants to understand WHY behind each workout (motivation driver)")

    b_events_data = profile.get('b_events', [])
    for ev in b_events_data:
        if not ev.get('date'):
            notes.append(f"{ev['name']} is a B event -- no date provided, needs follow-up")

    # Render
    md = f"# Coaching Brief: {name}\n\n"
    md += f"## Plan Overview\n"
    md += f"| Field | Value |\n"
    md += f"|-------|-------|\n"
    md += f"| Athlete ID | {athlete_id} |\n"
    md += f"| Plan Duration | {plan_weeks} weeks |\n"
    md += f"| Methodology | {meth_name} |\n"
    md += f"| Tier | {tier} |\n"
    md += f"| Target Race | {race_name} ({race_date}) |\n"
    md += f"| FTP | {ftp}W ({w_kg} W/kg) |\n"
    md += f"| Cycling Hours | {cycling_hours} hrs/week |\n"
    md += f"| Email | {profile.get('email', '')} |\n"
    md += f"\n"

    md += f"## Questionnaire -> Plan Mapping\n"
    md += f"| Questionnaire Input | Coaching Decision | Rationale |\n"
    md += f"|---------------------|-------------------|-----------|\n"
    for qinput, decision, rationale in mappings:
        # Escape pipe chars in table cells
        qi = qinput.replace('|', '/').replace('\n', ' ')
        de = decision.replace('|', '/').replace('\n', ' ')
        ra = rationale.replace('|', '/').replace('\n', ' ')
        md += f"| {qi} | {de} | {ra} |\n"
    md += f"\n"

    if risks:
        md += f"## Risk Factors\n"
        for r in risks:
            md += f"- {r}\n"
        md += f"\n"

    if notes:
        md += f"## Key Coaching Notes\n"
        for n in notes:
            md += f"- {n}\n"
        md += f"\n"

    return md


# ===========================================================================
# Pipeline Runner
# ===========================================================================

PIPELINE_STEPS = [
    ('Validate Profile', 'validate_profile.py'),
    ('Derive Classifications', 'derive_classifications.py'),
    ('Build Weekly Structure', 'build_weekly_structure.py'),
    ('Select Methodology', 'select_methodology.py'),
    ('Calculate Fueling', 'calculate_fueling.py'),
    ('Calculate Plan Dates', 'calculate_plan_dates.py'),
    ('Generate Workouts', 'generate_athlete_package.py'),
    ('Generate HTML Guide', 'generate_html_guide.py'),
    ('Generate Dashboard', 'generate_dashboard.py'),
]


def run_pipeline(athlete_id: str) -> bool:
    """
    Run the full training plan pipeline.
    Returns True if all steps succeed.
    """
    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}RUNNING PIPELINE: {athlete_id}{RESET}")
    print(f"{BOLD}{'='*60}{RESET}\n")

    total = len(PIPELINE_STEPS)
    for i, (name, script) in enumerate(PIPELINE_STEPS, 1):
        script_path = SCRIPTS_DIR / script

        if not script_path.exists():
            print(f"  [{i}/{total}] {name}... {RED}SCRIPT NOT FOUND{RESET}: {script}")
            return False

        print(f"  [{i}/{total}] {name}...", end=' ', flush=True)
        start = datetime.now()

        result = subprocess.run(
            [sys.executable, str(script_path), athlete_id],
            capture_output=True,
            text=True,
            cwd=str(SCRIPTS_DIR),
            timeout=300,
        )

        elapsed = (datetime.now() - start).total_seconds()

        if result.returncode == 0:
            print(f"{GREEN}OK{RESET} ({elapsed:.1f}s)")
        else:
            print(f"{RED}FAILED{RESET} ({elapsed:.1f}s)")
            stderr = result.stderr.strip() if result.stderr else ''
            stdout = result.stdout.strip() if result.stdout else ''
            error_msg = stderr or stdout or f"Exit code {result.returncode}"
            # Show last 500 chars of error
            if len(error_msg) > 500:
                error_msg = '...' + error_msg[-500:]
            print(f"    {DIM}{error_msg}{RESET}")
            return False

    # -- Post-pipeline verification: check critical deliverables --
    athlete_dir = get_athlete_dir(athlete_id)
    dashboard_path = athlete_dir / 'dashboard.html'
    if not dashboard_path.exists():
        print(f"\n  {RED}[ERROR]{RESET} dashboard.html was NOT generated despite pipeline success")
        print(f"    Expected at: {dashboard_path}")
        print(f"    The generate_dashboard.py step may have exited 0 without producing output.")
        return False

    print(f"\n{GREEN}Pipeline completed successfully.{RESET}")
    return True


def run_quality_gates(athlete_id: str) -> bool:
    """Run GENERATE_PACKAGE.py quality gates (excluding the generate step since we already ran it)."""
    generate_pkg = SCRIPTS_DIR / 'GENERATE_PACKAGE.py'
    if not generate_pkg.exists():
        print(f"\n{YELLOW}[WARN]{RESET} GENERATE_PACKAGE.py not found, skipping quality gates")
        return True

    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}RUNNING QUALITY GATES{RESET}")
    print(f"{BOLD}{'='*60}{RESET}\n")

    # Run individual quality gate scripts
    gates = [
        ('Workout Distribution', 'validate_workout_distribution.py'),
        ('Athlete Integrity', 'test_athlete_integrity.py'),
        ('Pre-Delivery Checklist', 'pre_delivery_checklist.py'),
    ]

    all_ok = True
    for name, script in gates:
        script_path = SCRIPTS_DIR / script
        if not script_path.exists():
            print(f"  {YELLOW}[SKIP]{RESET} {name} -- script not found")
            continue

        print(f"  {name}...", end=' ', flush=True)
        result = subprocess.run(
            [sys.executable, str(script_path), athlete_id],
            capture_output=True,
            text=True,
            cwd=str(SCRIPTS_DIR),
            timeout=120,
        )

        if result.returncode == 0:
            print(f"{GREEN}OK{RESET}")
        else:
            print(f"{YELLOW}WARN{RESET}")
            # Quality gates are advisory -- don't block
            if 'CRITICAL' in (result.stdout + result.stderr):
                all_ok = False
                print(f"    {RED}Critical issues found -- review output above{RESET}")

    return all_ok


# ===========================================================================
# Deliverables Copier
# ===========================================================================

def copy_to_downloads(athlete_id: str, coaching_brief_md: str) -> Path:
    """
    Copy deliverables to ~/Downloads/{athlete_id}-training-plan/.

    Contents:
    - workouts/ (all .zwo files)
    - training_guide.html
    - dashboard.html
    - coaching_brief.md
    - plan_summary.yaml (derived.yaml)
    - fueling.yaml
    """
    athlete_dir = get_athlete_dir(athlete_id)
    downloads_dir = Path.home() / 'Downloads' / f'{athlete_id}-training-plan'

    # Clean existing
    if downloads_dir.exists():
        shutil.rmtree(downloads_dir)
    downloads_dir.mkdir(parents=True)

    print(f"\n{BOLD}Copying deliverables to {downloads_dir}{RESET}")

    delivered = []
    delivery_gaps = []

    # 1. Workouts
    workouts_src = athlete_dir / 'workouts'
    if workouts_src.exists():
        workouts_dst = downloads_dir / 'workouts'
        shutil.copytree(workouts_src, workouts_dst)
        zwo_count = len(list(workouts_dst.glob('*.zwo')))
        print(f"  {GREEN}Copied:{RESET} workouts/ ({zwo_count} .zwo files)")
        delivered.append(f"workouts/ ({zwo_count} .zwo files)")
    else:
        print(f"  {YELLOW}[WARN]{RESET} No workouts/ directory found")
        delivery_gaps.append('workouts/')

    # 2. Training guide
    guide = athlete_dir / 'training_guide.html'
    if guide.exists():
        shutil.copy2(guide, downloads_dir / 'training_guide.html')
        print(f"  {GREEN}Copied:{RESET} training_guide.html")
        delivered.append('training_guide.html')
    else:
        print(f"  {YELLOW}[WARN]{RESET} training_guide.html not found")
        delivery_gaps.append('training_guide.html')

    # 3. Dashboard
    dashboard = athlete_dir / 'dashboard.html'
    if dashboard.exists():
        shutil.copy2(dashboard, downloads_dir / 'dashboard.html')
        print(f"  {GREEN}Copied:{RESET} dashboard.html")
        delivered.append('dashboard.html')
    else:
        print(f"  {RED}[ERROR]{RESET} dashboard.html not found -- generate_dashboard.py may have failed silently")
        delivery_gaps.append('dashboard.html')

    # 4. Coaching brief
    brief_path = downloads_dir / 'coaching_brief.md'
    with open(brief_path, 'w') as f:
        f.write(coaching_brief_md)
    print(f"  {GREEN}Written:{RESET} coaching_brief.md (PRIVATE -- for coach only)")
    delivered.append('coaching_brief.md')

    # 5. Plan summary (derived.yaml)
    derived = athlete_dir / 'derived.yaml'
    if derived.exists():
        shutil.copy2(derived, downloads_dir / 'plan_summary.yaml')
        print(f"  {GREEN}Copied:{RESET} plan_summary.yaml")
        delivered.append('plan_summary.yaml')

    # 6. Fueling
    fueling = athlete_dir / 'fueling.yaml'
    if fueling.exists():
        shutil.copy2(fueling, downloads_dir / 'fueling.yaml')
        print(f"  {GREEN}Copied:{RESET} fueling.yaml")
        delivered.append('fueling.yaml')

    # 7. Generate PDF from training guide
    guide_html = downloads_dir / 'training_guide.html'
    if guide_html.exists():
        pdf_path = downloads_dir / 'training_guide.pdf'
        try:
            from pdf_generator import generate_pdf
            pdf_ok, pdf_msg = generate_pdf(guide_html, pdf_path)
            if pdf_ok:
                print(f"  {GREEN}Generated:{RESET} training_guide.pdf ({pdf_path.stat().st_size // 1024} KB)")
                delivered.append('training_guide.pdf')
            else:
                print(f"  {RED}[ERROR]{RESET} PDF generation failed: {pdf_msg}")
                print(f"    Install Google Chrome for PDF output")
                delivery_gaps.append('training_guide.pdf')
        except ImportError:
            print(f"  {RED}[ERROR]{RESET} PDF generation failed -- install Google Chrome for PDF output")
            delivery_gaps.append('training_guide.pdf')

    # 8. Copy guide to delivery folder for hosting
    try:
        from config_loader import get_config
        cfg = get_config()
        delivery_base = cfg.get_path('delivery_dir') or (athlete_dir.parent.parent / 'delivery')
        guides_dir = delivery_base / 'guides' / 'athletes' / athlete_id
        guides_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(guide_html, guides_dir / 'index.html')
        github_pages_base = cfg.get('hosting.github_pages_base', 'https://wattgod.github.io')
        guides_repo = cfg.get('hosting.guides_repo_name', 'gravel-god-guides')
        guide_url = f"{github_pages_base}/{guides_repo}/athletes/{athlete_id}/"
        print(f"  {GREEN}Staged:{RESET} guide for hosting at {guide_url}")
        print(f"  {DIM}(Push delivery/ repo to deploy){RESET}")
    except (ImportError, Exception) as e:
        guide_url = None
        print(f"  {YELLOW}[WARN]{RESET} Could not stage guide for hosting: {e}")

    # -- Delivery Summary --
    print(f"\n  {BOLD}DELIVERY SUMMARY{RESET}")
    print(f"  {'─' * 40}")
    for item in delivered:
        print(f"  {GREEN}[OK]{RESET}    {item}")
    if delivery_gaps:
        for item in delivery_gaps:
            print(f"  {RED}[MISS]{RESET}  {item}")
        print(f"\n  {RED}{BOLD}{len(delivery_gaps)} deliverable(s) missing -- review errors above{RESET}")
    else:
        print(f"\n  {GREEN}All deliverables present.{RESET}")

    return downloads_dir


# ===========================================================================
# Main
# ===========================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Convert athlete intake questionnaire to a complete training plan.",
        epilog=(
            "Examples:\n"
            "  python3 intake_to_plan.py --file intake.md\n"
            "  cat intake.md | python3 intake_to_plan.py\n"
            "  pbpaste | python3 intake_to_plan.py\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        '--file', '-f',
        type=str,
        help='Path to markdown intake file',
    )
    parser.add_argument(
        '--skip-pipeline',
        action='store_true',
        help='Only generate profile.yaml (skip pipeline execution)',
    )
    parser.add_argument(
        '--skip-quality-gates',
        action='store_true',
        help='Skip quality gate checks after pipeline',
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Parse and show profile without writing files',
    )

    args = parser.parse_args()

    # -- Pre-flight: Chrome availability --
    try:
        from pdf_generator import find_chrome
        if not find_chrome():
            print(f"{YELLOW}[WARN]{RESET} Google Chrome not found — PDF generation will be skipped.")
            print(f"       Install Chrome for PDF output: https://www.google.com/chrome/")
    except ImportError:
        print(f"{YELLOW}[WARN]{RESET} pdf_generator.py not found — PDF generation will be skipped.")

    # -- Read input --
    if args.file:
        filepath = Path(args.file)
        if not filepath.exists():
            print(f"{RED}ERROR:{RESET} File not found: {filepath}")
            sys.exit(1)
        with open(filepath, 'r') as f:
            raw_text = f.read()
        print(f"Reading from file: {filepath}")
    elif not sys.stdin.isatty():
        raw_text = sys.stdin.read()
        print("Reading from stdin...")
    else:
        print(f"{RED}ERROR:{RESET} No input provided.")
        print("Usage:")
        print("  python3 intake_to_plan.py --file intake.md")
        print("  cat intake.md | python3 intake_to_plan.py")
        print("  pbpaste | python3 intake_to_plan.py")
        sys.exit(1)

    if not raw_text.strip():
        print(f"{RED}ERROR:{RESET} Input is empty.")
        sys.exit(1)

    # -- Step 1: Parse markdown --
    print(f"\n{BOLD}Step 1: Parsing questionnaire...{RESET}")
    parsed = parse_intake_markdown(raw_text)

    athlete_name = parsed.get('athlete_name', 'Unknown')
    print(f"  Athlete: {athlete_name}")

    sections = [k for k in parsed if k not in ('athlete_name', '__header__')]
    print(f"  Sections found: {len(sections)} ({', '.join(sections)})")

    # -- Step 1b: Validate parsed data --
    try:
        validate_parsed_intake(parsed)
        print(f"  {GREEN}Intake validation passed.{RESET}")
    except IntakeValidationError as e:
        print(f"\n{RED}VALIDATION ERROR:{RESET}\n{e}")
        sys.exit(1)

    # -- Step 2: Build profile --
    print(f"\n{BOLD}Step 2: Building profile.yaml...{RESET}")
    profile = build_profile(parsed)
    athlete_id = profile['athlete_id']

    print(f"  Athlete ID: {athlete_id}")
    print(f"  Target Race: {profile.get('target_race', {}).get('name', 'N/A')}")
    print(f"  Race Date: {profile.get('target_race', {}).get('date', 'N/A')}")
    print(f"  FTP: {profile.get('fitness_markers', {}).get('ftp_watts', 'N/A')}W")
    print(f"  W/kg: {profile.get('fitness_markers', {}).get('w_kg', 'N/A')}")
    print(f"  Weight: {profile.get('weight_kg', 'N/A')} kg")
    print(f"  Height: {profile.get('height_cm', 'N/A')} cm")
    print(f"  Cycling Hours: {profile.get('weekly_availability', {}).get('cycling_hours_target', 'N/A')}")
    print(f"  Methodology: {profile.get('methodology_preferences', {}).get('preferred_approach', 'N/A')}")

    # -- Step 2b: Sanity check profile --
    try:
        validate_profile_sanity(profile)
        print(f"  {GREEN}Profile sanity check passed.{RESET}")
    except IntakeValidationError as e:
        print(f"\n{RED}VALIDATION ERROR:{RESET}\n{e}")
        sys.exit(1)

    if args.dry_run:
        import yaml
        print(f"\n{BOLD}--- DRY RUN: Profile YAML ---{RESET}")
        print(yaml.dump(profile, default_flow_style=False, sort_keys=False, width=120))
        sys.exit(0)

    # -- Write profile --
    athlete_dir = get_athlete_dir(athlete_id)
    profile_path = get_athlete_file(athlete_id, 'profile.yaml')

    if profile_path.exists():
        print(f"\n  {YELLOW}[WARN]{RESET} Profile already exists at {profile_path}")
        print(f"  Overwriting with new intake data.")

    write_profile_yaml(profile, profile_path)

    if args.skip_pipeline:
        print(f"\n{GREEN}Profile written. Pipeline skipped (--skip-pipeline).{RESET}")
        print(f"Output: {profile_path}")
        sys.exit(0)

    # -- Step 3: Run pipeline --
    print(f"\n{BOLD}Step 3: Running pipeline...{RESET}")
    pipeline_ok = run_pipeline(athlete_id)

    if not pipeline_ok:
        print(f"\n{RED}Pipeline failed. Fix errors above and re-run.{RESET}")
        sys.exit(1)

    # -- Step 3b: Quality gates --
    if not args.skip_quality_gates:
        gates_ok = run_quality_gates(athlete_id)
        if not gates_ok:
            print(f"\n{YELLOW}Quality gates had issues. Review above.{RESET}")

    # -- Step 4: Generate coaching brief --
    print(f"\n{BOLD}Step 4: Generating coaching brief...{RESET}")
    coaching_brief = generate_coaching_brief(profile, parsed)
    print(f"  {GREEN}Generated{RESET} coaching_brief.md")

    # Also write to athlete directory
    brief_path = athlete_dir / 'coaching_brief.md'
    with open(brief_path, 'w') as f:
        f.write(coaching_brief)
    print(f"  {GREEN}Written:{RESET} {brief_path}")

    # -- Step 5: Copy to Downloads --
    print(f"\n{BOLD}Step 5: Copying to Downloads...{RESET}")
    downloads_path = copy_to_downloads(athlete_id, coaching_brief)

    # -- Done --
    print(f"\n{BOLD}{GREEN}{'='*60}{RESET}")
    print(f"{BOLD}{GREEN}INTAKE-TO-PLAN COMPLETE{RESET}")
    print(f"{BOLD}{GREEN}{'='*60}{RESET}")
    print(f"\n  Athlete: {athlete_name}")
    print(f"  ID: {athlete_id}")
    print(f"  Profile: {profile_path}")
    print(f"  Deliverables: {downloads_path}")

    # Show what's in the package
    pdf_exists = (downloads_path / 'training_guide.pdf').exists()
    zwo_count = len(list((downloads_path / 'workouts').glob('*.zwo'))) if (downloads_path / 'workouts').exists() else 0
    print(f"\n  {BOLD}Package contents:{RESET}")
    print(f"    workouts/          {zwo_count} ZWO files")
    print(f"    training_guide.html  (open in browser)")
    if pdf_exists:
        print(f"    training_guide.pdf   (send to athlete)")
    print(f"    coaching_brief.md    (PRIVATE — coach only)")
    print(f"    plan_summary.yaml")
    print(f"    fueling.yaml")

    print(f"\n  {CYAN}Next steps:{RESET}")
    print(f"  1. Review coaching_brief.md (questionnaire → decision mapping)")
    print(f"  2. Open training_guide.html in browser, spot-check weeks 1/6/12")
    print(f"  3. Push delivery/ repo to deploy hosted guide URL")
    print(f"  4. Send PDF + workouts.zip to athlete")
    print()


if __name__ == '__main__':
    main()
