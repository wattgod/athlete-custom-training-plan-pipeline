#!/usr/bin/env python3
"""
============================================================================
  PRIMARY PIPELINE ENTRY POINT — production webhook + manual CLI
============================================================================

This is THE file that runs in production for every paid order.
The Stripe webhook (`webhook/app.py::run_pipeline`) invokes this script
with the athlete's questionnaire piped to stdin. See PIPELINE.md for the
full map of which script does what.

Related scripts (do NOT confuse for the entry point):
  - generate_full_package.py     internal 9-step orchestrator (called by THIS)
  - generate_athlete_package.py  internal ZWO workout generator
  - generate_html_guide.py       internal HTML guide renderer

----------------------------------------------------------------------------

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
from known_races import (KNOWN_RACES, RACE_ALIASES, match_race,
                         match_race_scored, lookup_by_slug,
                         build_generic_race_profile)

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

    # The ONLY hard requirement is a race to train for — that's the one thing
    # we genuinely cannot build a plan without. Everything else (age, sex,
    # weight, FTP, weekly hours, the whole basic_info/current_fitness/schedule
    # sections) is OPTIONAL: build_profile fills missing values with sane,
    # flagged assumptions and week-1 testing dials them in. Requiring more than
    # this just turns recoverable gaps into refunded orders.
    goals_data = parsed.get('goals', {})
    race_list = []
    if isinstance(goals_data, dict):
        races_val = goals_data.get('races', '')
        if isinstance(races_val, str) and races_val.strip():
            race_list = [r.strip() for r in races_val.split('\n') if r.strip()]
    if not race_list:
        errors.append(
            "At least one race must be listed in Goals — it's the one field we "
            "can't build a plan without. (Everything else is optional and "
            "estimated.)"
        )

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


# Patterns that indicate FTP is unknown / athlete has no power meter
_FTP_UNKNOWN_PATTERNS = re.compile(
    r'^\s*(?:unknown|n/?a|none|no\s*power|no\s*power\s*meter|'
    r'don.?t\s*know|not\s*sure|not\s*tested|untested|no\s*data|'
    r'no\s*ftp|haven.?t\s*tested|unsure|idk|-)\s*$',
    re.IGNORECASE,
)


def _parse_ftp_with_unknown_handling(raw: str) -> Optional[int]:
    """Parse FTP value, returning None if unknown/missing/no power meter.

    Detects patterns like 'unknown', 'N/A', 'no power meter', 'not tested'
    and returns None instead of crashing on non-numeric input.
    """
    if not raw or not raw.strip():
        return None
    if _FTP_UNKNOWN_PATTERNS.match(raw.strip()):
        return None
    return parse_watts(raw)


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
# Race Line Parsing
# ===========================================================================

_RACE_PRIORITY_RE = re.compile(r'priority\s+([A-D])\b', re.IGNORECASE)
_RACE_DATE_RE = re.compile(r'\b(\d{4}-\d{2}-\d{2})\b')

_COMPETITIVE_GOAL_KEYWORDS = (
    'podium', 'win', 'victory', 'top 3', 'top-3', 'top 5', 'top-5',
    'top 10', 'top-10', 'compete', 'competitive', 'qualify', 'age group',
)

_TRAVEL_RANGE_RE = re.compile(
    r'(\d{4}-\d{2}-\d{2})\s*(?:to|through|–|-)\s*(\d{4}-\d{2}-\d{2})')


def parse_travel_dates(text: str) -> List[str]:
    """Parse travel dates from intake text into a sorted list of ISO dates.

    Accepts comma-separated single dates and ranges:
    '2026-09-03 to 2026-09-08, 2026-10-15' → every date in the range plus
    the single date. Ranges longer than 14 days are ignored (likely a typo
    or a relocation, not a travel disruption).
    """
    from datetime import datetime as _dt, timedelta as _td
    if not text:
        return []
    dates = set()
    remaining = text
    for m in _TRAVEL_RANGE_RE.finditer(text):
        try:
            start = _dt.strptime(m.group(1), '%Y-%m-%d')
            end = _dt.strptime(m.group(2), '%Y-%m-%d')
        except ValueError:
            continue
        if start <= end and (end - start).days <= 14:
            d = start
            while d <= end:
                dates.add(d.strftime('%Y-%m-%d'))
                d += _td(days=1)
        remaining = remaining.replace(m.group(0), ' ')
    for m in re.finditer(r'\b(\d{4}-\d{2}-\d{2})\b', remaining):
        try:
            _dt.strptime(m.group(1), '%Y-%m-%d')
            dates.add(m.group(1))
        except ValueError:
            continue
    return sorted(dates)


def derive_goal_type(success_text: str) -> str:
    """Map the athlete's stated success definition to a goal type.

    'podium' unlocks advanced methodologies and penalizes zero-intensity
    systems in methodology scoring. Previously this was hardcoded to
    'finish' for everyone, so a podium-chasing Cat 3 got scored as a
    finish-focused beginner (MAF / Low-HR selected over Polarized).
    """
    text = (success_text or '').lower()
    if any(k in text for k in _COMPETITIVE_GOAL_KEYWORDS):
        return 'podium'
    return 'finish'


def parse_race_line(line: str) -> Dict[str, Any]:
    """
    Parse one race line from the markdown intake.

    Expected shape: ``Name (YYYY-MM-DD, miles, priority X)`` — each field in
    the parens is optional, athletes may omit any combination.

    Returns: ``{'name': str, 'date': str, 'distance_miles': int, 'priority': str|None}``.
    Priority is uppercased ('A'|'B'|'C'|'D') when present, else None.
    """
    raw = line.strip()
    if not raw:
        return {'name': '', 'date': '', 'distance_miles': 0, 'priority': None}

    # Pull metadata out of the trailing parenthesis (if present)
    meta = ''
    name = raw
    paren_match = re.search(r'\s*\(([^)]*)\)\s*$', raw)
    if paren_match:
        meta = paren_match.group(1)
        name = raw[:paren_match.start()].strip()

    date = ''
    distance = 0
    priority = None

    if meta:
        date_match = _RACE_DATE_RE.search(meta)
        if date_match:
            date = date_match.group(1)

        priority_match = _RACE_PRIORITY_RE.search(meta)
        if priority_match:
            priority = priority_match.group(1).upper()

        # Numeric distance: bare integer in the meta string (not the date).
        for part in [p.strip() for p in meta.split(',')]:
            if part.isdigit() and 1 <= int(part) <= 999:
                distance = int(part)
                break

    return {
        'name': name,
        'date': date,
        'distance_miles': distance,
        'priority': priority,
    }


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
    nutrition_intake = parsed.get('nutrition', {})

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

    # ── Forgiving defaults ──────────────────────────────────────────────
    # An athlete must be able to get a custom plan without filling in
    # everything. Missing demographics get sane, clearly-flagged assumptions
    # rather than failing the order. The plan stays custom to the race + hours
    # + whatever they DID provide; week-1 testing dials in the rest.
    if not age or age <= 0:
        age = 40
        print(f"{YELLOW}NOTE: age not provided — assuming {age}.{RESET}")
    if sex not in ('male', 'female'):
        sex = 'male'
    if not weight_kg or weight_kg <= 0:
        weight_kg = 75.0 if sex == 'male' else 62.0
        print(f"{YELLOW}NOTE: weight not provided — assuming {weight_kg}kg for "
              f"FTP/fueling estimates. Update for precise fueling.{RESET}")

    ftp_raw = fitness.get('ftp', '')
    ftp_estimated = False
    ftp_watts = _parse_ftp_with_unknown_handling(ftp_raw)
    if ftp_watts is None and weight_kg > 0:
        # Estimate FTP from weight: 2.5 W/kg for males, 2.2 W/kg for females
        # Conservative estimate suitable for plan generation
        default_wkg = 2.5 if sex == 'male' else 2.2
        # Adjust for age: reduce by 0.5% per year over 40
        age_factor = 1.0
        if age > 40:
            age_factor = max(0.7, 1.0 - 0.005 * (age - 40))
        ftp_watts = int(round(default_wkg * age_factor * weight_kg))
        ftp_estimated = True
        print(f"{YELLOW}WARNING: FTP unknown — estimated {ftp_watts}W "
              f"from {default_wkg} W/kg × {weight_kg}kg × {age_factor:.2f} age factor. "
              f"FTP test should be scheduled in week 1.{RESET}")

    wkg_raw = fitness.get('w_kg', fitness.get('w/kg', ''))
    w_kg = parse_wkg(wkg_raw)
    if w_kg is None and ftp_watts and weight_kg > 0:
        w_kg = round(ftp_watts / weight_kg, 2)

    resting_hr = parse_hr(recovery.get('resting_hr', ''))
    # Real measured HR markers from Current Fitness — drive HR zones instead of
    # an age-estimated HRmax. (These used to be dropped; an HR-based athlete
    # then got generic %HRmax zones off a formula, not their own numbers.)
    max_hr = parse_hr(fitness.get('hr_max', '')) or parse_hr(recovery.get('hr_max', ''))
    lthr = (parse_hr(fitness.get('hr_threshold', ''))
            or parse_hr(fitness.get('lthr', '')))
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

    # Parse each race line into structured fields (name, date, distance, priority)
    parsed_races = [parse_race_line(r) for r in race_list]

    # Target race = first explicit priority A; fall back to first race if none.
    target_idx = next(
        (i for i, r in enumerate(parsed_races) if r['priority'] == 'A'),
        0 if parsed_races else -1,
    )

    a_events = []
    b_events = []
    target_race_info = {}

    goal_type = derive_goal_type(success_text)

    # The customer picked a specific race on the site, so the questionnaire
    # carries its SLUG. For the target race we resolve by slug (exact) — this
    # is the preferred path and removes the whole name-matching bug class.
    target_slug = (goals.get('race_slug') or '').strip()

    for i, parsed in enumerate(parsed_races):
        race_name_clean = parsed['name']
        is_target = (i == target_idx)
        # Athlete-supplied priority wins. If absent, target gets A and the rest B.
        priority = parsed['priority'] or ('A' if is_target else 'B')

        # Prefer an exact slug match for the target race; fall back to fuzzy
        # name-matching (manual intakes / B-races with no slug).
        matched = None
        match_meta = None
        matched_by_slug = False
        if is_target and target_slug:
            matched = lookup_by_slug(target_slug)
            matched_by_slug = matched is not None
            if matched:
                match_meta = {
                    'method': 'slug',
                    'score': 1.0,
                    'matched_slug': matched[0].split(':', 1)[-1],
                    'near_misses': [],
                }
        if not matched:
            matched, match_meta = match_race_scored(race_name_clean)
        event = {
            'name': race_name_clean,
            'date': parsed['date'],
            'distance_miles': parsed['distance_miles'],
            'goal': goal_type if is_target else 'compete',
            'priority': priority,
        }

        if matched:
            race_id, info = matched
            # The slug nails the race IDENTITY (exactly which event) — that's
            # what kills the wrong-edition / not-in-database / date-mismatch
            # order-killers. The athlete's own date/distance still win when
            # given (their date drives the plan length they were priced on, and
            # their distance is the route they're actually doing); we only fall
            # back to the DB for anything they left blank.
            if not event['date']:
                event['date'] = info.get('date', '')
            if not event['distance_miles']:
                event['distance_miles'] = info.get('distance_miles', 0)
            event['name'] = info['name']
            if is_target:
                target_race_info = {
                    'name': info['name'],
                    # clean slug (snapshot keys are 'discipline:slug')
                    'race_id': race_id.split(':', 1)[-1],
                    'date': event['date'],
                    'distance_miles': event['distance_miles'],
                    'elevation_ft': info.get('elevation_ft', 0),
                    'goal_type': goal_type,
                    'goal': goal_type,
                    'goal_description': success_text,
                    # How the race was resolved — audited by the coach brief
                    # and the pre-delivery checklist.
                    'race_match': match_meta,
                }
                # Verified venue from the DB (used by the guide, and lets the
                # integrity check trust the date instead of re-deriving it).
                if info.get('location'):
                    target_race_info['location'] = info['location']
                # Discipline from the race DB drives guide branding (road ->
                # Roadie Labs + road skills). Only set when the DB knows it.
                if info.get('discipline'):
                    target_race_info['discipline'] = info['discipline']
        else:
            # UNMATCHED race — build the plan from what the athlete actually
            # told us (never map to a real race by default: a fondo rider
            # must not get an Unbound-shaped plan). Loud to the coach (brief
            # + checklist flag), invisible to the athlete (their race name
            # is used verbatim; no fabricated course data).
            near = (match_meta or {}).get('near_misses', [])
            near_str = ', '.join(
                f"{n['name']} ({n['score']})" for n in near) or 'none'
            print(f"{YELLOW}WARNING: Race '{race_name_clean}' did not match any "
                  f"race in the database — building a GENERIC profile from the "
                  f"athlete's own intake. Near misses: {near_str}. "
                  f"Verify before delivery (see coaching brief).{RESET}")

            if not event['distance_miles']:
                event['distance_miles'] = extract_distance_from_name(race_name_clean)

            if not event['date']:
                goals_text = ' '.join(str(v) for v in goals.values() if v)
                event['date'] = extract_date_from_text(goals_text)

            if is_target:
                generic = build_generic_race_profile(
                    race_name_clean,
                    date=event['date'],
                    distance_miles=event['distance_miles'],
                )
                target_race_info = {
                    'name': race_name_clean,   # athlete's name, verbatim
                    'race_id': re.sub(r'[^a-z0-9]+', '_', race_name_clean.lower()).strip('_'),
                    'date': event['date'],
                    'distance_miles': event['distance_miles'],
                    'elevation_ft': generic['elevation_ft'],
                    'goal_type': goal_type,
                    'goal': goal_type,
                    'goal_description': success_text,
                    'generic_profile': True,
                    # Neutral demand assumptions (race_category_scorer shape)
                    # — disclosed to the coach, never shown to the athlete.
                    'generic_demands': generic['demands'],
                    'race_match': match_meta,
                }

        if priority == 'A':
            a_events.append(event)
        else:
            b_events.append(event)

    # -- Schedule --
    weekly_hours_raw = schedule.get('weekly_hours_available', '0')
    hours_min, hours_max = parse_range(weekly_hours_raw)
    cycling_hours_target = hours_max or hours_min or 0
    if not cycling_hours_target or cycling_hours_target <= 0:
        # Volume is the biggest driver of plan shape, but a missing value must
        # not fail the order — assume a common recreational load and flag it.
        cycling_hours_target = 8
        print(f"{YELLOW}NOTE: weekly hours not provided — assuming "
              f"{cycling_hours_target}h/wk.{RESET}")

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

    # "Flexible" athletes name no long-ride day, so the designated long day
    # fell through to the generic weekend cap (240min) — contradicting a
    # stated 4-5h longest ride and capping every long ride at 4h. The long
    # day always gets long-ride treatment unless it's an off day.
    if preferred_long_day not in off_days:
        preferred_days[preferred_long_day] = {
            'availability': 'available',
            'time_slots': ['am'],
            'max_duration_min': 600,
            'is_key_day_ok': True,
        }

    # -- Volume capacity check --
    # Warn if cycling_hours_target exceeds what the schedule can support
    schedule_capacity_min = sum(
        day_info['max_duration_min']
        for day_info in preferred_days.values()
        if day_info.get('availability') != 'unavailable'
    )
    schedule_capacity_hrs = schedule_capacity_min / 60.0
    volume_warning = None
    if cycling_hours_target > 0 and schedule_capacity_hrs > 0:
        if cycling_hours_target > schedule_capacity_hrs:
            volume_warning = (
                f"Target volume ({cycling_hours_target}h/wk) exceeds schedule capacity "
                f"({schedule_capacity_hrs:.0f}h/wk). Available days cannot support this volume."
            )
            print(f"{YELLOW}WARNING: {volume_warning}{RESET}")

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

    # Brand discipline hint (from the questionnaire's `- Discipline:` line, set
    # by the webhook from the buying brand). This is the LOWEST-priority signal:
    # derive_discipline uses the race's own DB discipline, then the race-name
    # keyword, and only falls back to this hint instead of the gravel default —
    # so an unknown race on Roadie Labs builds a ROAD plan, but a known gravel
    # race a road customer picked still resolves gravel.
    _disc_hint = (goals.get('discipline', '') or '').strip().lower()
    _disc_hint = _disc_hint if _disc_hint in ('road', 'gravel', 'mtb') else ''

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
        # lowest-priority discipline fallback (brand hint); see derive_discipline
        'discipline_default': _disc_hint,
        # (generic_demands for an unmatched race are refined with the derived
        # discipline right after this dict is assembled — see below)
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
            'ftp_estimated': ftp_estimated,
            'ftp_date': today.isoformat(),
            'weight_kg': weight_kg,
            'height_cm': height_cm,
            'sex': sex,
            'w_kg': w_kg,
            'resting_hr': resting_hr,
            'max_hr': max_hr,
            'lthr': lthr,
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
            'volume_warning': volume_warning,
        },
        'preferred_days': preferred_days,
        'travel_dates': parse_travel_dates(
            schedule.get('travel_dates', '') or additional.get('travel_dates', '')
        ),
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
            # Preserve the athlete's demonstrated carbohydrate intake when the
            # questionnaire supplies it. Fueling policy parses numeric g/hr;
            # blank/free-text remains a documented unknown rather than a block.
            'training_fuel': nutrition_intake.get('training_fuel',
                nutrition_intake.get('current_carbs_g_per_hour',
                additional.get('training_fuel', ''))),
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

    # Unmatched race: refine the neutral demand assumptions with the DERIVED
    # discipline (race-name keywords + brand hint) — a "fondo" in the name or
    # a Roadie Labs order shapes the generic profile as road, not gravel.
    if target_race_info.get('generic_profile'):
        try:
            from archetype import derive_discipline
            from known_races import generic_race_demands
            disc = derive_discipline(profile)
            target_race_info['generic_discipline'] = disc
            target_race_info['generic_demands'] = generic_race_demands(
                target_race_info.get('distance_miles', 0), disc)
        except ImportError:
            pass  # keep the discipline-neutral demands already set

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
        'time_crunched': 3,
        'g_spot': 3,
        'polarized': 3,
        'pyramidal': 3,
        'preferred_approach': '',
        'past_success_with': '',
        'past_failure_with': '',
    }

    # Map training-approach keywords → the FOUR methodology names (for matching
    # past-failure vetoes / past-success endorsements in select_methodology).
    # NB: "sweet spot" is deliberately NOT mapped to G Spot — they're different
    # (rigid % vs read-the-room), so a failed-sweet-spot athlete may thrive on
    # G Spot. A "sweet spot didn't work" mention simply vetoes nothing now.
    approach_keywords = {
        'time crunch': 'Time-Crunched',
        'time-crunch': 'Time-Crunched',
        'g spot': 'G Spot (Read the Room)',
        'g-spot': 'G Spot (Read the Room)',
        'read the room': 'G Spot (Read the Room)',
        'polarized': 'Polarized (80/20)',
        '80/20': 'Polarized (80/20)',
        'pyramidal': 'Traditional (Pyramidal)',
        'traditional': 'Traditional (Pyramidal)',
        'base building': 'Traditional (Pyramidal)',
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
    athlete_dir: Optional[Path] = None,
) -> str:
    """Generate comprehensive coaching brief from all pipeline output YAMLs.

    Reads methodology.yaml, derived.yaml, plan_dates.yaml, fueling.yaml,
    weekly_structure.yaml to produce a complete decision-tracing document.
    Every questionnaire input is mapped to its implementation choice.
    """
    import yaml

    name = profile['name']
    athlete_id = profile['athlete_id']
    target = profile.get('target_race', {})
    ftp = profile.get('fitness_markers', {}).get('ftp_watts', '?')
    w_kg = profile.get('fitness_markers', {}).get('w_kg', '?')
    weight_kg = profile.get('weight_kg', '?')
    cycling_hours = profile.get('weekly_availability', {}).get('cycling_hours_target', '?')

    # -- Load pipeline output YAMLs --
    methodology_data = {}
    derived_data = {}
    plan_dates_data = {}
    fueling_data = {}
    weekly_structure_data = {}

    if athlete_dir:
        ad = Path(athlete_dir)
        for fname, target_dict in [
            ('methodology.yaml', 'methodology_data'),
            ('derived.yaml', 'derived_data'),
            ('plan_dates.yaml', 'plan_dates_data'),
            ('fueling.yaml', 'fueling_data'),
            ('weekly_structure.yaml', 'weekly_structure_data'),
        ]:
            fpath = ad / fname
            if fpath.exists():
                with open(fpath) as f:
                    data = yaml.safe_load(f) or {}
                if target_dict == 'methodology_data':
                    methodology_data = data
                elif target_dict == 'derived_data':
                    derived_data = data
                elif target_dict == 'plan_dates_data':
                    plan_dates_data = data
                elif target_dict == 'fueling_data':
                    fueling_data = data
                elif target_dict == 'weekly_structure_data':
                    weekly_structure_data = data

    # -- Extract key values from pipeline outputs --
    meth_name = methodology_data.get('selected_methodology', 'Unknown')
    meth_id = methodology_data.get('methodology_id', 'unknown')
    meth_score = methodology_data.get('score', '?')
    meth_reasons = methodology_data.get('reasons', [])
    meth_warnings = methodology_data.get('warnings', [])
    meth_alternatives = methodology_data.get('alternatives', [])
    meth_config = methodology_data.get('configuration', {})
    meth_confidence = methodology_data.get('confidence', '?')

    tier = derived_data.get('tier', 'unknown')
    plan_weeks = derived_data.get('plan_weeks', '?')
    starting_phase = derived_data.get('starting_phase', '?')
    risk_factors_derived = derived_data.get('risk_factors', [])
    key_day_candidates = derived_data.get('key_day_candidates', [])
    plan_start = derived_data.get('plan_start', '?')
    plan_end = derived_data.get('plan_end', '?')

    race_date = target.get('date', 'TBD')
    race_name = target.get('name', 'TBD')
    goal_type = target.get('goal_type', target.get('goal', '?'))

    # -- Intensity distribution from methodology config --
    # Some methodologies use a string distribution ("readiness_dependent",
    # "block_dependent") rather than fixed fractions — guard for that.
    intensity = meth_config.get('intensity_distribution', {})
    if not isinstance(intensity, dict):
        intensity = {}
    z1_z2_pct = intensity.get('z1_z2', '?')
    z3_pct = intensity.get('z3', '?')
    z4_z5_pct = intensity.get('z4_z5', '?')

    # =====================================================================
    # SECTION 1: PLAN OVERVIEW
    # =====================================================================
    md = f"# Coaching Brief: {name}\n"
    md += f"*INTERNAL DOCUMENT — Coach eyes only*\n\n"

    # If the automatic compliance checks flagged the plan, surface it LOUDLY at
    # the very top — the plan was still delivered, but it should be reviewed and
    # adjusted before it goes to the athlete. (Written by the compliance gate.)
    if athlete_dir:
        _review = Path(athlete_dir) / 'NEEDS_REVIEW.txt'
        if _review.exists():
            try:
                _detail = _review.read_text()
            except Exception:
                _detail = ''
            md += "> ## ⚠️ NEEDS REVIEW BEFORE SENDING\n"
            md += "> The automatic coach checks flagged this plan. It was built "
            md += "and delivered, but **review and adjust the flagged weeks "
            md += "before sending it to the athlete.**\n>\n"
            for _ln in _detail.splitlines():
                md += f"> {_ln}\n"
            md += "\n"

    # If the athlete's race did NOT confidently match the race database, the
    # plan was built from a GENERIC profile — the coach must verify the race
    # before this goes out. Loud here, invisible to the athlete (their guide
    # uses their race name verbatim and no fabricated course data).
    _rm = (target.get('race_match') or {})
    if _rm.get('method') == 'none':
        _raw_name = target.get('name', '(no race name)')
        _gd = target.get('generic_demands') or {}
        _gdisc = target.get('generic_discipline', 'unknown')
        md += "> ## 🚨 UNMATCHED RACE — VERIFY BEFORE SENDING\n"
        md += (f"> The athlete's race **\"{_raw_name}\"** did not confidently "
               f"match any race in the database (best score: "
               f"{_rm.get('score', 0)}, threshold: 0.85).\n>\n")
        md += ("> The plan was built from a **generic profile** using the "
               "athlete's own intake — it was NOT mapped to any real race:\n")
        md += f"> - Race name (used verbatim, athlete-facing): {_raw_name}\n"
        md += f"> - Date: {target.get('date') or 'NOT PROVIDED'} (from athlete intake)\n"
        md += (f"> - Distance: "
               f"{target.get('distance_miles') or 'NOT PROVIDED'} miles "
               f"(athlete-provided / extracted from name)\n")
        md += ("> - Elevation: none assumed (no fabricated course data in "
               "the athlete guide)\n")
        md += (f"> - Demand assumptions: neutral {_gdisc} demands for the "
               f"given distance ({_gd})\n>\n")
        _near = _rm.get('near_misses') or []
        if _near:
            md += ("> Closest database candidates — verify none of these is "
                   "the actual race:\n")
            for _i, _n in enumerate(_near, 1):
                md += (f"> {_i}. {_n.get('name')} (`{_n.get('slug')}`) — "
                       f"score {_n.get('score')}\n")
        else:
            md += "> No close database candidates found.\n"
        md += (">\n> **Action:** confirm race identity, date, and distance "
               "with the athlete. If it IS a known race, add an alias to "
               "known_races.py and regenerate.\n\n")

    md += f"## 1. Plan Overview\n"
    md += f"| Field | Value |\n"
    md += f"|-------|-------|\n"
    md += f"| Athlete ID | {athlete_id} |\n"
    md += f"| Email | {profile.get('email', '')} |\n"
    md += f"| Plan Duration | {plan_weeks} weeks ({plan_start} to {plan_end}) |\n"
    md += f"| Methodology | {meth_name} (score: {meth_score}/100, confidence: {meth_confidence}) |\n"
    md += f"| Methodology ID | `{meth_id}` |\n"
    md += f"| Tier | {tier} |\n"
    md += f"| Starting Phase | {starting_phase} |\n"
    md += f"| Target Race | {race_name} ({race_date}) |\n"
    md += f"| Goal | {goal_type} |\n"
    md += f"| FTP | {ftp}W ({w_kg} W/kg) at {weight_kg}kg |\n"
    md += f"| Age | {profile.get('health_factors', {}).get('age', '?')} |\n"
    md += f"| Sex | {profile.get('sex', '?')} |\n"
    md += f"| Cycling Hours | {cycling_hours} hrs/week target |\n"
    md += f"| Current Hours | {profile.get('training_history', {}).get('current_weekly_hours', '?')} hrs/week |\n"
    md += f"| Experience | {profile.get('training_history', {}).get('years_cycling', '?')}yr cycling, {profile.get('training_history', {}).get('years_structured', '?')}yr structured |\n"
    md += f"| Recovery | {profile.get('health_factors', {}).get('recovery_capacity', '?')} |\n"
    md += f"| Stress | {profile.get('health_factors', {}).get('stress_level', '?')} |\n"
    md += f"\n"

    # =====================================================================
    # SECTION 2: QUESTIONNAIRE -> DECISION MAPPING TABLE
    # =====================================================================
    md += f"## 2. Questionnaire -> Implementation Mapping\n"
    md += f"| # | Questionnaire Input | Pipeline Decision | Rationale |\n"
    md += f"|---|---------------------|-------------------|-----------|\n"

    row_num = 0

    def _add_row(q_input: str, decision: str, rationale: str) -> str:
        nonlocal row_num
        row_num += 1
        qi = q_input.replace('|', '/').replace('\n', ' ')
        de = decision.replace('|', '/').replace('\n', ' ')
        ra = rationale.replace('|', '/').replace('\n', ' ')
        return f"| {row_num} | {qi} | {de} | {ra} |\n"

    # Hours -> tier
    md += _add_row(
        f"Weekly hours: {cycling_hours}",
        f"Tier: {tier}",
        f"Derived by derive_classifications.py from cycling_hours_target",
    )

    # FTP -> W/kg
    if ftp and ftp != '?' and w_kg and w_kg != '?':
        md += _add_row(
            f"FTP: {ftp}W at {weight_kg}kg",
            f"W/kg: {w_kg}",
            "Calculated: ftp_watts / weight_kg",
        )

    # Experience -> methodology eligibility
    yrs_structured = profile.get('training_history', {}).get('years_structured', '?')
    yrs_cycling = profile.get('training_history', {}).get('years_cycling', '?')
    md += _add_row(
        f"Experience: {yrs_cycling}yr cycling, {yrs_structured}yr structured",
        f"Methodology: {meth_name}",
        f"select_methodology.py scored 13 options; experience contributes ±15 pts",
    )

    # Hours -> methodology
    md += _add_row(
        f"Available hours: {cycling_hours}/wk",
        f"Methodology hours match: +30 if in sweet spot",
        f"Primary scoring factor (±30 pts). {cycling_hours}hr → {meth_name}",
    )

    # Stress -> methodology
    stress = profile.get('health_factors', {}).get('stress_level', '?')
    recovery_cap = profile.get('health_factors', {}).get('recovery_capacity', '?')
    md += _add_row(
        f"Stress: {stress}, Recovery: {recovery_cap}",
        f"Stress handling score: ±15 pts",
        f"High stress + slow recovery → favor stress-tolerant methodologies",
    )

    # Past failure -> veto
    past_failure = profile.get('methodology_preferences', {}).get('past_failure_with', '')
    if past_failure:
        md += _add_row(
            f"Past failure: \"{past_failure}\"",
            f"VETO: -50 pts on matching methodologies",
            "Hard exclusion — athlete explicitly rejected this approach",
        )

    # Race distance -> methodology
    race_dist = target.get('distance_miles', '?')
    md += _add_row(
        f"Race distance: {race_dist} miles",
        f"Ultra-distance bonus: +15 pts for durability methodologies",
        f"200mi event favors Polarized, MAF, HVLI for long-event durability",
    )

    # Goal type
    md += _add_row(
        f"Goal: {goal_type}",
        f"Goal type scoring: ±10 pts",
        f"Finish goal → favor endurance/durability methodologies",
    )

    # Preferred days -> weekly structure
    pref_days = profile.get('preferred_days', {})
    off_days = profile.get('schedule_constraints', {}).get('preferred_off_days', [])
    long_day = profile.get('schedule_constraints', {}).get('preferred_long_day', '?')
    off_str = ', '.join(d.title() for d in off_days) if off_days else 'None'
    md += _add_row(
        f"Off days: {off_str}",
        f"No workouts on {off_str}",
        "Respected exactly as stated by athlete",
    )
    md += _add_row(
        f"Long ride day: {long_day}",
        f"{long_day.title() if isinstance(long_day, str) else long_day} = long Z2 ride",
        f"Max duration: {pref_days.get(long_day, {}).get('max_duration_min', '?')}min",
    )

    # Key days from weekly structure
    ws_days = weekly_structure_data.get('days', {})
    key_days_actual = [d.title() for d, info in ws_days.items() if info and info.get('is_key_day')]
    md += _add_row(
        f"Key day candidates: {', '.join(d.title() for d in key_day_candidates)}",
        f"Key days assigned: {', '.join(key_days_actual)}",
        "build_weekly_structure.py assigns intervals/long ride to key days",
    )

    # Interval day assignments
    for day_name, day_info in ws_days.items():
        if day_info and day_info.get('pm') == 'intervals':
            md += _add_row(
                f"{day_name.title()} available PM, key day OK",
                f"{day_name.title()} PM = Intervals ({day_info.get('max_duration', '?')}min max)",
                day_info.get('notes', 'Key session assigned'),
            )
        elif day_info and day_info.get('am') == 'intervals':
            md += _add_row(
                f"{day_name.title()} available AM, key day OK",
                f"{day_name.title()} AM = Intervals ({day_info.get('max_duration', '?')}min max)",
                day_info.get('notes', 'Key session assigned'),
            )

    # Easy day assignments
    for day_name, day_info in ws_days.items():
        slot = day_info.get('pm') or day_info.get('am') if day_info else None
        if slot == 'easy_ride':
            time_slot = 'PM' if day_info.get('pm') == 'easy_ride' else 'AM'
            md += _add_row(
                f"{day_name.title()} available, not key day",
                f"{day_name.title()} {time_slot} = Easy ride ({day_info.get('max_duration', '?')}min max)",
                "Fill day — active recovery / Z2 endurance",
            )

    # Long ride assignment
    for day_name, day_info in ws_days.items():
        if day_info and (day_info.get('am') == 'long_ride' or day_info.get('pm') == 'long_ride'):
            md += _add_row(
                f"{day_name.title()} = preferred long ride day",
                f"{day_name.title()} AM = Long ride ({day_info.get('max_duration', '?')}min max)",
                "Most important workout in polarized plan",
            )

    # Strength
    strength_include = profile.get('strength', {}).get('include_in_plan', False)
    strength_sessions = profile.get('strength', {}).get('sessions_per_week', 0)
    ankle_issue = any(
        i.get('area') == 'ankle'
        for i in profile.get('injury_history', {}).get('past_injuries', [])
    )
    md += _add_row(
        f"Strength training: {'yes' if strength_include else 'no'}",
        f"{strength_sessions} sessions/week",
        f"{'Ankle limitation restricts exercises' if ankle_issue else 'Per athlete preference'}",
    )

    # Medical conditions
    conditions = profile.get('health_factors', {}).get('medical_conditions', '')
    if conditions and conditions.lower() not in ('none', 'n/a', ''):
        meds = profile.get('health_factors', {}).get('medications', '')
        md += _add_row(
            f"Medical: {conditions}",
            f"Risk flag: monitor recovery",
            f"Medications: {meds}" if meds and meds.lower() not in ('none', 'n/a', '') else "No medications listed",
        )

    # Indoor tolerance -> workout design
    indoor_tol = profile.get('training_environment', {}).get('indoor_riding_tolerance', '?')
    longest_indoor = profile.get('workout_preferences', {}).get('longest_indoor_tolerable', '?')
    md += _add_row(
        f"Indoor tolerance: {indoor_tol}, max indoor: {longest_indoor}min",
        f"Weeknight trainer cap: {longest_indoor}min",
        "Workout durations respect indoor tolerance limit",
    )

    # Coaching style
    autonomy = profile.get('coaching_style', {}).get('autonomy_preference', '?')
    md += _add_row(
        f"Coaching style: {autonomy}",
        f"Guide includes workout rationale",
        "Athlete wants to understand WHY behind each workout",
    )

    # B events
    b_events = profile.get('b_events', [])
    for ev in b_events:
        ev_name = ev.get('name', '?')
        ev_date = ev.get('date', 'TBD')
        md += _add_row(
            f"B event: {ev_name} ({ev_date})",
            f"B-race overlay on race week: opener + RACE_DAY ZWO",
            "Training race — 90-95% effort, no phase change",
        )

    md += f"\n"

    # =====================================================================
    # SECTION 3: METHODOLOGY SELECTION (full breakdown)
    # =====================================================================
    md += f"## 3. Methodology Selection\n"
    md += f"### Selected: {meth_name}\n"
    md += f"- **Score**: {meth_score}/100\n"
    md += f"- **Confidence**: {meth_confidence}\n"
    md += f"- **Methodology ID**: `{meth_id}`\n\n"

    if meth_reasons:
        md += f"**Why this methodology won:**\n"
        for r in meth_reasons:
            md += f"- {r}\n"
        md += f"\n"

    if meth_warnings:
        md += f"**Warnings:**\n"
        for w in meth_warnings:
            md += f"- {w}\n"
        md += f"\n"

    if meth_alternatives:
        md += f"**Alternatives considered:**\n"
        md += f"| Rank | Methodology | Score | Key Reason |\n"
        md += f"|------|-------------|-------|------------|\n"
        for i, alt in enumerate(meth_alternatives, 1):
            alt_name = alt.get('name', '?')
            alt_score = alt.get('score', '?')
            alt_reason = alt.get('key_reason', '').replace('|', '/')
            md += f"| {i} | {alt_name} | {alt_score} | {alt_reason} |\n"
        md += f"\n"

    # Intensity distribution
    if intensity:
        md += f"### Zone Distribution Targets\n"
        md += f"| Zone | Target % |\n"
        md += f"|------|----------|\n"
        if z1_z2_pct != '?':
            md += f"| Z1-Z2 (endurance) | {int(z1_z2_pct * 100)}% |\n"
        if z3_pct != '?':
            md += f"| Z3 (tempo/sweet spot) | {int(z3_pct * 100)}% |\n"
        if z4_z5_pct != '?':
            md += f"| Z4-Z5 (threshold/VO2max) | {int(z4_z5_pct * 100)}% |\n"
        md += f"\n"

    # Key workouts
    key_workouts = meth_config.get('key_workouts', [])
    if key_workouts:
        md += f"### Key Workout Types\n"
        for kw in key_workouts:
            md += f"- {kw.replace('_', ' ').title()}\n"
        md += f"\n"

    testing_freq = meth_config.get('testing_frequency', '?')
    progression = meth_config.get('progression_style', '?')
    md += f"- **Testing Frequency**: {testing_freq}\n"
    md += f"- **Progression Style**: {progression.replace('_', ' ').title() if isinstance(progression, str) else progression}\n\n"

    # =====================================================================
    # SECTION 4: PHASE STRUCTURE (week-by-week)
    # =====================================================================
    md += f"## 4. Phase Structure\n"
    weeks = plan_dates_data.get('weeks', [])
    if weeks:
        md += f"| Week | Dates | Phase | B-Race | Notes |\n"
        md += f"|------|-------|-------|--------|-------|\n"
        for w in weeks:
            wk = w.get('week', '?')
            mon = w.get('monday_short', '?')
            sun = w.get('sunday_short', '?')
            phase = w.get('phase', '?')
            is_race_wk = w.get('is_race_week', False)
            b_race_info = w.get('b_race', {})
            b_race_str = ''
            if b_race_info:
                b_race_str = f"{b_race_info.get('name', '?')} ({b_race_info.get('date', '?')})"
            notes = ''
            if is_race_wk:
                notes = 'A-RACE WEEK'
            # Check for FTP test days
            for d in w.get('days', []):
                if d.get('is_b_race_day'):
                    notes += ' B-race day' if notes else 'B-race day'
            md += f"| W{wk:02d} | {mon}-{sun} | {phase.upper()} | {b_race_str} | {notes} |\n"
        md += f"\n"
    else:
        md += f"*No plan_dates.yaml found*\n\n"

    # =====================================================================
    # SECTION 5: WEEKLY STRUCTURE
    # =====================================================================
    md += f"## 5. Weekly Structure\n"
    if ws_days:
        md += f"| Day | Slot | Workout Type | Key Day | Max Duration |\n"
        md += f"|-----|------|--------------|---------|-------------|\n"
        day_order = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        for day_name in day_order:
            day_info = ws_days.get(day_name, {})
            if not day_info:
                md += f"| {day_name.title()} | — | OFF | — | — |\n"
                continue
            am = day_info.get('am')
            pm = day_info.get('pm')
            is_key = day_info.get('is_key_day', False)
            max_dur = day_info.get('max_duration', 0)
            if am and pm:
                workout = f"AM: {am}, PM: {pm}"
                slot = "AM+PM"
            elif am:
                workout = am.replace('_', ' ').title()
                slot = "AM"
            elif pm:
                workout = pm.replace('_', ' ').title()
                slot = "PM"
            else:
                workout = "OFF"
                slot = "—"
            key_str = "YES" if is_key else "no"
            dur_str = f"{max_dur}min" if max_dur else "—"
            md += f"| {day_name.title()} | {slot} | {workout} | {key_str} | {dur_str} |\n"
        md += f"\n"
    else:
        md += f"*No weekly_structure.yaml found*\n\n"

    # =====================================================================
    # SECTION 6: FUELING PLAN
    # =====================================================================
    md += f"## 6. Fueling Plan\n"
    if fueling_data:
        from fueling_policy import prescription_from_fueling
        prescription = prescription_from_fueling(fueling_data)
        carbs = fueling_data.get('carbohydrates', {})
        cals = fueling_data.get('calories', {})
        hydration = prescription.get('hydration', fueling_data.get('recommendations', {}).get('hydration', {}))

        md += f"| Field | Value |\n"
        md += f"|-------|-------|\n"
        md += f"| Race Duration | {cals.get('duration_hours', '?')} hrs |\n"
        md += f"| Total Calories | {cals.get('total_calories', '?')} kcal |\n"
        md += f"| Calories/Hour | {cals.get('calories_per_hour', '?')} kcal/hr |\n"
        carb_range = prescription.get('race_range_g_per_hour', carbs.get('hourly_range', ['?','?']))
        md += f"| Carb Target | {prescription.get('race_target_g_per_hour', carbs.get('hourly_target', '?'))}g/hr |\n"
        md += f"| Carb Range | {carb_range[0]}-{carb_range[1]}g/hr |\n"
        md += f"| Total Carbs | {prescription.get('total_g', carbs.get('total_grams', '?'))}g |\n"
        md += f"| Hydration | {hydration.get('target_ml_per_hour', '?')}ml/hr |\n"
        md += f"| Electrolytes | {hydration.get('electrolytes', '?')} |\n"
        md += f"\n"

        # Gut training phases
        gut = fueling_data.get('gut_training', {}).get('phases', {})
        if gut:
            md += f"### Gut Training Progression\n"
            md += f"| Phase | Weeks | Target (g/hr) | Guidance |\n"
            md += f"|-------|-------|---------------|----------|\n"
            for phase_name in ['base', 'build', 'peak', 'race']:
                phase_info = gut.get(phase_name, {})
                if phase_info:
                    wks = phase_info.get('weeks', '?')
                    tgt = phase_info.get('target_range', ['?', '?'])
                    guidance = phase_info.get('guidance', '').replace('|', '/').replace('\n', ' ')
                    md += f"| {phase_name.upper()} | {wks} | {tgt[0]}-{tgt[1]} | {guidance} |\n"
            md += f"\n"
    else:
        md += f"*No fueling.yaml found*\n\n"

    # =====================================================================
    # SECTION 7: B-RACE HANDLING
    # =====================================================================
    b_events = profile.get('b_events', [])
    if b_events:
        md += f"## 7. B-Race Handling\n"
        for ev in b_events:
            ev_name = ev.get('name', '?')
            ev_date = ev.get('date', 'TBD')
            md += f"### {ev_name} ({ev_date})\n"
            md += f"- **Priority**: B (training race)\n"
            md += f"- **Overlay**: Replaces existing workout on race day with RACE_DAY ZWO\n"
            md += f"- **Day before**: Openers (40min cap, 4x30sec @ 120% FTP)\n"

            # Find which week this B-race falls in
            for w in weeks:
                b_race_info = w.get('b_race', {})
                if b_race_info and b_race_info.get('name') == ev_name:
                    phase = b_race_info.get('phase', '?')
                    wk = w.get('week', '?')
                    md += f"- **Week**: W{wk:02d} ({phase} phase)\n"
                    if phase in ('build', 'peak'):
                        md += f"- **2 days before**: Easy ride (45min cap) — deeper mini-taper in {phase}\n"
                    break
            md += f"- **Post-race**: Resume normal training within 2 days\n\n"

    # =====================================================================
    # SECTION 8: RISK FACTORS
    # =====================================================================
    md += f"## 8. Risk Factors\n"
    risks = []
    # From derived.yaml
    for rf in risk_factors_derived:
        risks.append(rf.replace('_', ' ').title())
    # From profile
    if conditions and conditions.lower() not in ('none', 'n/a', ''):
        meds = profile.get('health_factors', {}).get('medications', '')
        risk_str = f"Medical: {conditions}"
        if meds and meds.lower() not in ('none', 'n/a', ''):
            risk_str += f" (meds: {meds})"
        risks.append(risk_str)
    for inj in profile.get('injury_history', {}).get('past_injuries', []):
        area = inj.get('area', '')
        desc = inj.get('description', '')
        side = inj.get('side', '')
        if area:
            risk_str = f"Chronic {side + ' ' if side else ''}{area}"
            if desc:
                truncated = desc[:100].rsplit(' ', 1)[0] if len(desc) > 100 else desc
                risk_str += f" — {truncated}"
            risks.append(risk_str)
    work_hrs = profile.get('schedule_constraints', {}).get('work_hours', '')
    if str(profile.get('work', {}).get('stress_level', '')).lower() == 'high':
        risks.append(f"High work stress ({work_hrs}hr weeks)" if work_hrs else "High work stress")
    family = profile.get('schedule_constraints', {}).get('family_commitments', '')
    if family:
        risks.append(f"Family commitments: {family}")
    if not risks:
        risks.append("No major risk factors identified")
    for r in risks:
        md += f"- {r}\n"
    md += f"\n"

    # =====================================================================
    # SECTION 9: KEY COACHING NOTES
    # =====================================================================
    md += f"## 9. Key Coaching Notes\n"
    notes = []

    # From athlete's own words
    anything_else = profile.get('personal', {}).get('anything_else', '')
    if anything_else:
        # Extract key themes
        lower = anything_else.lower()
        if 'base' in lower:
            notes.append("Athlete explicitly wants BASE BUILDING, not sweet spot")
        if 'sweet spot' in lower:
            notes.append("Previous failure: dedicated sweet spot block — lacked durability")
        if 'trainer' in lower:
            max_indoor = profile.get('workout_preferences', {}).get('longest_indoor_tolerable', '?')
            notes.append(f"Willing to do up to {max_indoor}min trainer sessions on weeknights")
        if 'zone 2' in lower or 'z2' in lower:
            notes.append("Specifically asked for long Z2 rides — validates Polarized selection")
        if 'durability' in lower:
            notes.append("Durability is primary concern — key metric for plan success")
        if 'nutrition' in lower or 'fuel' in lower:
            notes.append("Wants to dial in nutrition alongside training")

    # Coaching experience
    if profile.get('coaching', {}).get('previous_coach'):
        coach_exp = profile.get('coaching', {}).get('experience', '')
        if coach_exp:
            notes.append(f"Previous coaching experience: {coach_exp[:100]}")

    # Motivation
    quit_reasons = profile.get('motivation', {}).get('past_quit_reasons', '')
    if quit_reasons:
        notes.append(f"Past quit reasons: {quit_reasons}")

    best_block = profile.get('mental_game', {}).get('best_training_block', '')
    if best_block:
        notes.append(f"Best training block: {best_block}")

    # B-events without dates
    for ev in b_events:
        if not ev.get('date'):
            notes.append(f"B event '{ev.get('name', '?')}' has no date — needs follow-up")

    if not notes:
        notes.append("No special coaching notes")
    for n in notes:
        md += f"- {n}\n"
    md += f"\n"

    # =====================================================================
    # SECTION 10: PIPELINE OUTPUT FILES
    # =====================================================================
    md += f"## 10. Pipeline Output Files\n"
    md += f"| File | Status |\n"
    md += f"|------|--------|\n"
    if athlete_dir:
        ad = Path(athlete_dir)
        expected_files = [
            'profile.yaml', 'derived.yaml', 'weekly_structure.yaml',
            'methodology.yaml', 'fueling.yaml', 'plan_dates.yaml',
            'coaching_brief.md', 'training_guide.html', 'training_guide.pdf',
        ]
        for fname in expected_files:
            exists = (ad / fname).exists()
            status = 'OK' if exists else 'MISSING'
            md += f"| {fname} | {status} |\n"
        # Check workouts dir
        workouts_dir = ad / 'workouts'
        if workouts_dir.exists():
            zwo_count = len(list(workouts_dir.glob('*.zwo')))
            md += f"| workouts/*.zwo | {zwo_count} files |\n"
        else:
            md += f"| workouts/*.zwo | MISSING |\n"
    md += f"\n"

    # =====================================================================
    # FOOTER
    # =====================================================================
    md += f"---\n"
    md += f"*Generated by intake_to_plan.py on {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n"

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
    # 'Generate HTML Guide' step RETIRED Jun 2026 — the shipped guide is
    # written by training_guide_builder inside the Generate Workouts step;
    # generate_html_guide.py only produced an unused shadow copy.
    # 'Generate Dashboard' step RETIRED Jun 2026 (Phase 3) — the dashboard was
    # an extra artifact customers didn't use; the two deliverables that matter
    # are the ZWO workouts and the training guide (PDF). One fewer thing to
    # break per order.
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

    # -- Post-pipeline verification: the two deliverables that matter are the
    # ZWO workouts and the training guide. (Dashboard retired in Phase 3.) --
    athlete_dir = get_athlete_dir(athlete_id)
    guide_path = athlete_dir / 'training_guide.html'
    if not guide_path.exists():
        print(f"\n  {RED}[ERROR]{RESET} training_guide.html was NOT generated despite pipeline success")
        print(f"    Expected at: {guide_path}")
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
        ('Guide Quality', 'validate_guide_quality.py'),
    ]

    # ONE severity model (Phase 4): a quality issue FLAGS the plan for the
    # coach's pre-send review — it does NOT block/refund the order. Delivery is
    # not auto-send: the coach reviews coaching_brief.md + the plan before it
    # reaches the athlete, so a flagged plan never surprises the customer. This
    # matches the compliance gate's behaviour, so the checks stop fighting each
    # other (the integrity date-mismatch used to refund whole races here).
    flagged = []
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
            blob = (result.stdout or "") + (result.stderr or "")
            if 'CRITICAL' in blob:
                print(f"{YELLOW}NEEDS REVIEW{RESET}")
                # capture the critical lines for the coach
                crit = [ln.strip() for ln in blob.splitlines()
                        if 'CRITICAL' in ln or 'should be' in ln][:4]
                flagged.append((name, crit))
            else:
                print(f"{YELLOW}WARN{RESET}")  # non-critical advisory only

    if flagged:
        try:
            from constants import get_athlete_file
            review = get_athlete_dir(athlete_id) / 'NEEDS_REVIEW.txt'
            existing = review.read_text() if review.exists() else ""
            lines = [existing, "", "QUALITY GATES FLAGGED (review before sending):"]
            for name, crit in flagged:
                lines.append(f"  • {name}")
                for c in crit:
                    lines.append(f"      {c}")
            review.write_text("\n".join(lines).lstrip() + "\n")
        except Exception:
            pass
        # CI / debugging can restore hard-blocking.
        if os.environ.get('GG_STRICT_QUALITY') == '1':
            print(f"\n{RED}GG_STRICT_QUALITY: quality gate flagged — blocking.{RESET}")
            return False

    # Always True — the order delivers; flags go to the coach, not a refund.
    return True


# ===========================================================================
# Personal Email Generator
# ===========================================================================

def generate_personal_email(
    profile: Dict[str, Any],
    parsed: Dict[str, Any],
    athlete_dir: Optional[Path] = None,
) -> str:
    """Generate a personalized plan delivery email from questionnaire + plan data.

    This email demonstrates that the coach read the questionnaire and made
    thoughtful decisions. It references specific details the athlete provided
    and explains key plan decisions tied to their situation.

    Output is markdown — coach reviews/edits before sending.
    """
    import yaml

    name = profile.get('name', 'there')
    first_name = name.split()[0] if name else 'there'
    target = profile.get('target_race', {})
    race_name = target.get('name', 'your race')
    race_date = target.get('date', '')
    race_goal = target.get('goal_description', target.get('goal', ''))
    ftp = profile.get('fitness_markers', {}).get('ftp_watts')
    ftp_estimated = profile.get('fitness_markers', {}).get('ftp_estimated', False)
    cycling_hours = profile.get('weekly_availability', {}).get('cycling_hours_target', '')
    age = profile.get('age', profile.get('health_factors', {}).get('age', ''))
    years_cycling = profile.get('training_history', {}).get('years_cycling', '')

    # Load plan output for plan-specific details
    plan_weeks = None
    methodology_name = None
    if athlete_dir:
        ad = Path(athlete_dir)
        for fname, loader in [
            ('plan_dates.yaml', lambda d: d.get('plan_weeks')),
            ('methodology.yaml', lambda d: d.get('selected_methodology', d.get('name', ''))),
        ]:
            fpath = ad / fname
            if fpath.exists():
                try:
                    with open(fpath) as f:
                        data = yaml.safe_load(f) or {}
                    if fname == 'plan_dates.yaml':
                        plan_weeks = loader(data)
                    elif fname == 'methodology.yaml':
                        methodology_name = loader(data)
                except Exception:
                    pass

    # Count workouts
    workouts_dir = Path(athlete_dir) / 'workouts' if athlete_dir else None
    workout_count = 0
    if workouts_dir and workouts_dir.exists():
        workout_count = len(list(workouts_dir.glob('*.zwo')))

    # --- Extract questionnaire signals for personalization ---
    notes = profile.get('notes', parsed.get('additional', {}).get('other', ''))
    injuries_raw = profile.get('injury_history', {}).get('current_injuries', [])
    injuries_text = parsed.get('health', {}).get('current_injuries', '')
    stress_level = profile.get('health_factors', {}).get('stress_level', '')
    sleep_raw = profile.get('health_factors', {}).get('sleep_hours_avg', '')
    strength_current = profile.get('strength', {}).get('routine',
                                   parsed.get('strength', {}).get('current', ''))
    strength_include = profile.get('strength', {}).get('include_in_plan', False)

    # Preferred days
    preferred_days = profile.get('preferred_days', {})
    off_days = [d.title() for d, v in preferred_days.items()
                if v.get('availability') in ('unavailable', 'rest')]
    interval_days = [d.title() for d, v in preferred_days.items()
                     if v.get('is_key_day_ok')]
    long_day = profile.get('schedule_constraints', {}).get('preferred_long_day', '')

    # Weaknesses / blindspots from questionnaire
    weaknesses = parsed.get('basic_info', {}).get('weaknesses',
                 parsed.get('current_fitness', {}).get('weaknesses', ''))
    blindspots_list = profile.get('blindspots', [])
    blindspots = ', '.join(blindspots_list) if isinstance(blindspots_list, list) else str(blindspots_list)

    # Training background
    background = parsed.get('basic_info', {}).get('background',
                 parsed.get('goals', {}).get('background', ''))
    if not background:
        # Try to extract from notes
        for section in ('basic_info', 'goals', 'work_life', 'additional'):
            section_data = parsed.get(section, {})
            for k, v in section_data.items():
                if isinstance(v, str) and len(v) > 50:
                    background = v
                    break
            if background:
                break

    # --- Build email sections ---
    lines = []
    lines.append(f"**Subject:** Your {race_name} plan is live on TrainingPeaks\n")
    lines.append(f"Hey {first_name},\n")

    # Plan summary
    week_str = f"{plan_weeks}-week " if plan_weeks else ""
    lines.append(f"Your {week_str}plan is built and loaded on TrainingPeaks. "
                 f"Here's what I want you to know about how it's structured.\n")

    # --- Personal acknowledgment (the "I see you" paragraph) ---
    # Build a clean, human summary from structured fields — never dump raw notes.
    ack_parts = []

    # Sport background (short, structured)
    sport_bg = parsed.get('basic_info', {}).get('primary_sport', '')
    experience_level = parsed.get('basic_info', {}).get('experience_level', '')
    strengths_raw = parsed.get('basic_info', {}).get('strengths', '')
    # Extract first strength only (before the first comma)
    first_strength = strengths_raw.split(',')[0].strip().lower() if strengths_raw else ''

    if years_cycling and int(str(years_cycling).replace('+', '') or 0) >= 10:
        ack_parts.append(f"{years_cycling} years in the sport")
    if sport_bg and sport_bg.lower() not in ('cycling', 'gravel', 'gravel cycling', 'bike'):
        ack_parts.append(f"a {sport_bg.lower()} background")
    if first_strength and len(first_strength) < 40:
        ack_parts.append(f"an {first_strength}" if first_strength[0] in 'aeiou' else f"a {first_strength}")

    if ack_parts:
        lines.append(f"You're coming in with {', '.join(ack_parts[:2])}. "
                     "The plan accounts for that. ")
    if race_goal:
        lines[-1] = lines[-1].rstrip() + f" Everything in it points at one goal: {race_goal.lower().rstrip('.')}.\n"
    else:
        lines[-1] = lines[-1].rstrip() + "\n"

    lines.append("A few things specific to your plan:\n")

    # --- FTP status ---
    if ftp_estimated:
        lines.append(f"**FTP test in Week 1.** Your FTP is estimated right now ({ftp}W) since "
                     "we don't have test data yet. The plan has a test scheduled early so we "
                     "establish your real zones. Everything after that will be calibrated to your "
                     "actual numbers.\n")
    elif ftp:
        lines.append(f"**Your zones are set.** FTP of {ftp}W gives us clean power targets "
                     "across every workout. The plan includes a retest mid-plan to adjust as "
                     "you get fitter.\n")

    # --- Intensity cap explanation ---
    is_masters = isinstance(age, (int, float)) and int(age) >= 50
    if is_masters or stress_level in ('high', 'very_high'):
        reasons = []
        if is_masters:
            reasons.append("recovery needs at this stage")
        if stress_level in ('high', 'very_high'):
            reasons.append("your high-stress job")
        sleep_str = str(sleep_raw) if sleep_raw else ''
        # Extract lower bound from ranges like "6-7" or "6-7 hours"
        try:
            sleep_num = float(sleep_str.split('-')[0].split()[0])
        except (ValueError, IndexError):
            sleep_num = 8
        if sleep_num < 7:
            reasons.append(f"{sleep_str.split()[0] if ' ' in sleep_str else sleep_str} hours of sleep")
        reason_str = ' and '.join(reasons)
        lines.append(f"**Two intensity sessions per week, max.** Given {reason_str}, "
                     "recovery is the priority — not volume. "
                     f"{'Your key days are ' + ' and '.join(d for d in interval_days[:2]) + '.' if interval_days else ''} "
                     "Everything else is easy endurance or rest.\n")

    # --- Specific concerns from their questionnaire ---
    concern_sections = []

    # Heat / weather
    if any(w in notes.lower() for w in ['heat', 'hot', 'acclim', 'kansas', 'weather']):
        concern_sections.append(
            "**Heat prep is built in.** The plan includes heat acclimation cues starting "
            "4 weeks out — sauna post-ride or extra layers during warmup. Your long rides "
            "have practice fueling targets so race day isn't the first time you test nutrition "
            "at effort in the heat."
        )

    # VO2/cadence weakness
    if any(w in (weaknesses + ' ' + blindspots).lower() for w in ['vo2', 'cadence', 'top end', 'high intensity']):
        concern_sections.append(
            "**VO2 and cadence work.** You flagged these as weaknesses. The plan includes "
            "targeted sessions but keeps them short and structured — not suffer-fests. "
            "The goal is consistent stimulus, not destroying yourself."
        )

    # Climbing
    if any(w in (weaknesses + ' ' + blindspots + ' ' + notes).lower() for w in ['climb', 'ascent', 'hill']):
        concern_sections.append(
            "**Climbing.** The plan builds climbing-specific work into your key sessions. "
            "If you're limited on hills locally, trainer intervals at climbing cadence "
            "(60-70 RPM) are a strong substitute."
        )

    # Trainer vs outdoor
    if any(w in (weaknesses + ' ' + blindspots + ' ' + notes).lower() for w in ['trainer', 'zwift', 'indoor', 'outdoor']):
        concern_sections.append(
            "**Trainer vs. outdoor.** As weather opens up, push your long rides outside. "
            "The fitness transfers, but bike handling and fueling-at-speed don't build on "
            "the trainer. Weekday intervals can stay indoors."
        )

    # Family/schedule accommodation
    schedule_notes = parsed.get('schedule', {}).get('notes',
                     parsed.get('work_life', {}).get('notes', ''))
    additional_notes = notes + ' ' + schedule_notes
    # Look for specific events (graduation, wedding, travel, etc.)
    event_keywords = ['graduat', 'wedding', 'travel', 'vacation', 'trip', 'conference']
    for kw in event_keywords:
        if kw in additional_notes.lower():
            # Extract the sentence containing the keyword
            for sentence in additional_notes.replace('. ', '.\n').split('\n'):
                if kw in sentence.lower() and len(sentence) > 15:
                    concern_sections.append(
                        f"**Schedule note.** {sentence.strip().rstrip('.')} — "
                        "this falls during taper, so the plan is already light that week. "
                        "No conflicts."
                    )
                    break
            break

    # Health / medical
    if injuries_text and 'none' not in injuries_text.lower():
        concern_sections.append(
            "**Health considerations noted.** Your medical history is in the coaching brief. "
            "If anything changes or flares up, let me know and we'll adjust."
        )

    for section in concern_sections:
        lines.append(f"{section}\n")

    # --- Strength ---
    if strength_include and strength_current:
        lines.append(
            "**Strength stays.** Your current gym work is solid. The plan keeps strength "
            "on non-intensity days so it doesn't compete with your key cycling sessions.\n"
        )

    # --- Off days ---
    if off_days:
        lines.append(f"**{', '.join(off_days)} {'is' if len(off_days) == 1 else 'are'} off.** "
                     "Completely. No guilt.\n")

    # --- CTA ---
    lines.append(
        "Connect with me on TrainingPeaks using this link — that's where your workouts live:\n"
        "https://home.trainingpeaks.com/attachtocoach?sharedKey=2OTEPC6BXNVQU\n"
    )

    if plan_weeks:
        lines.append(f"Week 1 starts soon. Do {'the FTP test' if ftp_estimated else 'the first workout'} "
                     "and we're rolling.\n")

    lines.append("Questions anytime — just reply to this email.\n")
    lines.append("— Matti\nGravel God Coaching\ngravelgodcycling.com")

    return '\n'.join(lines)


# ===========================================================================
# Deliverables Copier
# ===========================================================================

def copy_to_downloads(athlete_id: str, coaching_brief_md: str) -> Path:
    """
    Copy deliverables to ~/Downloads/{athlete_id}-training-plan/.

    Contents:
    - workouts/ (all .zwo files)
    - training_guide.html + training_guide.pdf
    - coaching_brief.md
    - plan_summary.yaml (derived.yaml)
    - fueling.yaml
    """
    athlete_dir = get_athlete_dir(athlete_id)
    # GG_DELIVERY_DIR lets tests/CI redirect deliverables out of the real
    # ~/Downloads. Default is unchanged for normal coach runs.
    _delivery_root = os.environ.get('GG_DELIVERY_DIR')
    base = Path(_delivery_root) if _delivery_root else (Path.home() / 'Downloads')
    downloads_dir = base / f'{athlete_id}-training-plan'

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

    # 3. Dashboard — RETIRED (Phase 3). The deliverables that matter are the
    # ZWO workouts and the training guide; the dashboard was an unused extra.

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

    # 6b. Personal email (coach reviews before sending)
    personal_email = athlete_dir / 'personal_email.md'
    if personal_email.exists():
        shutil.copy2(personal_email, downloads_dir / 'personal_email.md')
        print(f"  {GREEN}Copied:{RESET} personal_email.md (REVIEW before sending)")
        delivered.append('personal_email.md')

    # 7. Plan preview
    preview = athlete_dir / 'plan_preview.html'
    if preview.exists():
        shutil.copy2(preview, downloads_dir / 'plan_preview.html')
        print(f"  {GREEN}Copied:{RESET} plan_preview.html (verification dashboard)")
        delivered.append('plan_preview.html')

    # 8. Generate PDF from the training guide — BEST EFFORT. The PDF needs
    # Chromium; if that's unavailable the order must NOT fail, because the
    # HTML guide (already delivered above) carries the same content. A missing
    # PDF is a clean degradation the coach can fill by hand, never a gap that
    # reads as a broken order.
    guide_html = downloads_dir / 'training_guide.html'
    if guide_html.exists():
        pdf_path = downloads_dir / 'training_guide.pdf'
        pdf_done = False
        try:
            from pdf_generator import generate_pdf
            pdf_ok, pdf_msg = generate_pdf(guide_html, pdf_path)
            if pdf_ok:
                print(f"  {GREEN}Generated:{RESET} training_guide.pdf ({pdf_path.stat().st_size // 1024} KB)")
                delivered.append('training_guide.pdf')
                pdf_done = True
            else:
                print(f"  {YELLOW}[WARN]{RESET} PDF not generated ({pdf_msg}) — "
                      f"the HTML guide ships as the guide deliverable.")
        except Exception as e:
            print(f"  {YELLOW}[WARN]{RESET} PDF not generated ({type(e).__name__}) — "
                  f"the HTML guide ships as the guide deliverable.")
        if not pdf_done:
            # ensure the guide is unmistakably present as the delivered guide
            if 'training_guide.html' not in delivered:
                delivered.append('training_guide.html (PDF unavailable)')

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

    # If the compliance checks flagged the plan, the order STILL delivered, but
    # emit a machine-readable marker so the webhook can tell the coach "needs
    # review" (vs a clean delivery) and so the coach reviews it first.
    _review = Path(__file__).resolve().parent.parent / athlete_id / 'NEEDS_REVIEW.txt'
    if _review.exists():
        print(f"\n  {YELLOW}{BOLD}NEEDS_REVIEW: plan delivered but flagged by "
              f"auto-checks — review coaching_brief.md before sending.{RESET}")
        print("GG_NEEDS_REVIEW=1")  # machine marker for the webhook

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

    # -- Pre-flight: PDF engine availability --
    try:
        from pdf_generator import find_chrome, has_weasyprint
        has_chrome = bool(find_chrome())
        has_wp = has_weasyprint()
        if not has_chrome and not has_wp:
            print(f"{YELLOW}[WARN]{RESET} No PDF engine found — PDF generation will be skipped.")
            print(f"       Install Chrome or WeasyPrint (pip install weasyprint)")
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

    # -- Step 3b: Quality gates (flag-for-review, never block) --
    # A quality issue flags the plan for the coach's pre-send review (written to
    # NEEDS_REVIEW.txt → coaching brief banner → "needs review" coach email). It
    # does NOT refund the order. The coach reviews before the plan reaches the
    # athlete, so nothing unreviewed surprises the customer. (GG_STRICT_QUALITY=1
    # restores hard-blocking for CI/debugging.)
    if not args.skip_quality_gates:
        if not run_quality_gates(athlete_id):
            # Only reachable under GG_STRICT_QUALITY=1 (CI/debugging).
            sys.exit(1)

    # -- Step 4: Generate coaching brief --
    print(f"\n{BOLD}Step 4: Generating coaching brief...{RESET}")
    coaching_brief = generate_coaching_brief(profile, parsed, athlete_dir=athlete_dir)
    print(f"  {GREEN}Generated{RESET} coaching_brief.md")

    # Also write to athlete directory
    brief_path = athlete_dir / 'coaching_brief.md'
    with open(brief_path, 'w') as f:
        f.write(coaching_brief)
    print(f"  {GREEN}Written:{RESET} {brief_path}")

    # -- Step 4b: Generate plan preview --
    print(f"\n{BOLD}Step 4b: Generating plan preview...{RESET}")
    try:
        from generate_plan_preview import build_preview_data, render_preview_html
        preview_data = build_preview_data(athlete_dir)
        preview_html = render_preview_html(preview_data)
        preview_path = athlete_dir / 'plan_preview.html'
        with open(preview_path, 'w') as f:
            f.write(preview_html)
        checks_pass = sum(1 for c in preview_data['checks'] if c['status'] == 'PASS')
        checks_total = len(preview_data['checks'])
        print(f"  {GREEN}Generated{RESET} plan_preview.html ({checks_pass}/{checks_total} checks pass)")
        for c in preview_data['checks']:
            icon = GREEN + '✓' if c['status'] == 'PASS' else (YELLOW + '⚠' if c['status'] == 'WARN' else RED + '✗')
            print(f"    {icon}{RESET} {c['name']}: {c['detail']}")
    except Exception as e:
        print(f"  {YELLOW}Preview generation failed: {e}{RESET}")

    # -- Step 4c: Generate personal delivery email --
    print(f"\n{BOLD}Step 4c: Generating personal email...{RESET}")
    try:
        personal_email = generate_personal_email(profile, parsed, athlete_dir=athlete_dir)
        email_path = athlete_dir / 'personal_email.md'
        with open(email_path, 'w') as f:
            f.write(personal_email)
        print(f"  {GREEN}Generated{RESET} personal_email.md")
        print(f"  {GREEN}Written:{RESET} {email_path}")
    except Exception as e:
        personal_email = ''
        print(f"  {YELLOW}Personal email generation failed: {e}{RESET}")

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
    preview_exists = (downloads_path / 'plan_preview.html').exists()
    print(f"\n  {BOLD}Package contents:{RESET}")
    print(f"    workouts/            {zwo_count} ZWO files")
    print(f"    training_guide.html  (open in browser)")
    if pdf_exists:
        print(f"    training_guide.pdf   (send to athlete)")
    if preview_exists:
        print(f"    plan_preview.html    (verification — open FIRST)")
    print(f"    coaching_brief.md    (PRIVATE — coach only)")
    print(f"    plan_summary.yaml")
    print(f"    fueling.yaml")

    print(f"\n  {CYAN}Next steps:{RESET}")
    print(f"  1. Open plan_preview.html — verify all checks pass, scan week-by-week grid")
    print(f"  2. Review coaching_brief.md (questionnaire → decision mapping)")
    print(f"  3. Open training_guide.html in browser, spot-check weeks 1/6/12")
    print(f"  4. Push delivery/ repo to deploy hosted guide URL")
    print(f"  5. Send PDF + workouts.zip to athlete")
    print()


if __name__ == '__main__':
    main()
