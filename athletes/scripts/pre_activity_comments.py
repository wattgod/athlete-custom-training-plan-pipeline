"""AE-9.2 (2026-08-24 TP review): TP `preActivityComments` for key sessions.

TP's workout model carries a `preActivityComments` field alongside the
description -- a short note the athlete sees before starting the session,
separate from the executable brief. This module renders that field from the
AE-3.8 phase-gated discretion rules ("bounded athlete discretion in workout
notes") so a key session gives the athlete room to pivot without sabotaging
the pattern: how far they may push if it feels great, and what to do if a
set falls apart. Short (2-3 lines), phase-correct, key sessions only -- an
easy ride or rest day needs no in-session discretion rule.
"""
from __future__ import annotations

from typing import Any, Optional


def _get(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default)


# AE-3.8: base -> extend duration at same power, never add power. Final
# 4-5-week peak -> one watt harder on the last effort, never add reps
# (AE-4.4's phase-conditional "more left" rule). Build sits with base's
# "add a rep" family until the plan enters that closing peak window.
_BASE_PIVOT = "Feels great? Extend the duration at the same power -- never add power."
_PEAK_PIVOT = "Feels great? One watt harder on the last effort -- never add reps."
_FAILED_SET = ("Failed a set? Resume after 5-10min easy only if the early reps "
               "weren't already a struggle. Struggling from rep one: spin home "
               "easy and tell me.")


def is_key_session(session: Any) -> bool:
    """Whether this session is a candidate for a pre-activity comment.

    Key = bike, and either a field test, a race simulation, or carrying
    dominant structured work >=88% FTP (mirrors delivery_notes.py's
    _is_quality_session core check -- a session hard enough that "how far
    can I push it" is a real question, unlike an easy spin or rest day).
    """
    if str(_get(session, "tp_kind") or "") != "bike":
        return False
    if _get(session, "is_field_test") or _get(session, "is_simulation"):
        return True
    from delivery_render import _dominant_work_percent, has_structured_work
    return has_structured_work(session) and _dominant_work_percent(session) >= 88


def pre_activity_comment(session: Any, *, phase: str = "",
                         is_final_peak_block: bool = False) -> Optional[str]:
    """A 2-3 line bounded-pivot note for one key session, or None."""
    if not is_key_session(session):
        return None
    phase_norm = str(phase or "").strip().lower()
    pivot = _PEAK_PIVOT if (phase_norm == "peak" or is_final_peak_block) else _BASE_PIVOT
    return f"{pivot}\n{_FAILED_SET}"
