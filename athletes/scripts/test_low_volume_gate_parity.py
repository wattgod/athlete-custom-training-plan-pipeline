"""Generator/gate parity for a low-volume, low-frequency athlete.

2026-09-22 order: a time-crunched rider (~5 h/wk, 2-3 rides, kettlebells 3x
a week, back from a crash and concussion, MidSouth B-race then Unbound 100)
got a 34-week plan the review gate blocked with 31 findings. Every one was
the generator producing something its own gate rejects:

  HARD_MINUTES_BELOW_FLOOR x26  gate ignored AE-2.1's ">=6 h/wk" scope
  R05                           gate ignored the registry's "<=3 available
                                cycling days allows 1" clause
  SHORT_SESSION_BELOW_FLOOR     B-race easy spin shipped with no recovery role
  UNRESOLVED_PAIN_MAX_...       generator scheduled FTP retests anyway
  VO2_DOSE_OUT_OF_RANGE         floor growth stretched a 4-min VO2 rep
  VOICE_CONTRACT                long plan repeated its notes' sentences

The profile below is synthetic. The end-to-end test runs the real intake
path once (~15 s) and asserts none of those classes come back.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

from block_compliance import r05_intensity_count, validate_plan  # noqa: E402

# ---------------------------------------------------------------------------
# R05 -- the rule
# ---------------------------------------------------------------------------

def _load_week(intensity_days):
    days = [{'day': d, 'role': 'intensity' if d in intensity_days else 'filler',
             'name': 'VO2max 30/30' if d in intensity_days else 'Endurance'}
            for d in ('Thu', 'Sat', 'Sun')]
    days[1]['role'] = 'long_ride'
    return {'plan_week': 1, 'week_type': 'load', 'phase': 'base', 'days': days}


def test_r05_allows_one_quality_day_with_three_available_days():
    ok, message = r05_intensity_count([_load_week({'Thu'})], max_per_week=2,
                                      available_days=3)
    assert ok, message


def test_r05_still_wants_two_quality_days_with_four_available_days():
    ok, _ = r05_intensity_count([_load_week({'Thu'})], max_per_week=2,
                                available_days=4)
    assert not ok


def test_validate_plan_counts_available_days_from_off_days():
    plan = {'weeks': [_load_week({'Thu'})]}
    result = validate_plan(plan, target_hours=5, max_intensity=2,
                           off_days=['Mon', 'Tue', 'Wed', 'Fri'])
    assert result['rules']['R05']['passed'], result['rules']['R05']['message']
    result = validate_plan(plan, target_hours=5, max_intensity=2,
                           off_days=['Mon', 'Tue', 'Wed'])
    assert not result['rules']['R05']['passed']
