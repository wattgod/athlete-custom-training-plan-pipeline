"""Fail-closed voice lint for athlete-facing calendar copy.

Reads athletes/config/voice_rules.yaml (the contract) and checks weekly notes
and Day Off cards: banned phrases, framework/AI patterns, word caps, blank
rest days, and sentences repeated across a plan's notes. This is the
enforcement half of the self-improving voice loop: when the judge or the
coach flags copy that reads wrong, the phrase or pattern is added to the
rules file and every future plan fails closed on it.
"""
from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List

import yaml

_RULES_PATH = Path(__file__).resolve().parent.parent / "config" / "voice_rules.yaml"
_SENTENCE = re.compile(r"(?<=[.!?])\s+")

# AE-9.3 / AE-9.4 (2026-08-24 TP review, round-2 addendum): fixed-form coach
# templates -- story_notes.SELF_REVIEW_TITLE / COMMENT_PROTOCOL_TITLE --
# ship verbatim by ratification, never rotated/reworded/truncated. They are
# exempt from the word cap and the cross-week sentence-dupe check below
# (both are heuristics for freely-authored coach prose; a mandated verbatim
# template is neither variable content nor an unintentional repeat). This
# is a narrow allowlist keyed on the exact fixed-template titles -- it does
# NOT weaken either rule for any other note.
_FIXED_TEMPLATE_TITLES = {
    "Week Self Review - 3 Qs",
    "How To Comment On Workouts",
}


def load_rules(path: Path = _RULES_PATH) -> Dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _words(text: str) -> int:
    return len(re.findall(r"\S+", text or ""))


def _sentences(text: str) -> List[str]:
    """Real sentences only (>= 6 words): a session-name lead-in such as
    "Ronnestad 30-15 Monday." legitimately recurs when the same session sits
    on the same weekday in several weeks."""
    return [s.strip() for s in _SENTENCE.split(text or "") if _words(s) >= 6]


def check_copy(text: str, *, rules: Dict[str, Any], where: str) -> List[str]:
    """Phrase/pattern findings for one piece of copy."""
    findings: List[str] = []
    lowered = (text or "").lower()
    for phrase in rules.get("banned_phrases") or []:
        if str(phrase).lower() in lowered:
            findings.append(f"{where}: banned phrase {phrase!r}")
    for pattern in rules.get("banned_patterns") or []:
        if re.search(pattern, text or "", re.M):
            findings.append(f"{where}: banned pattern {pattern!r}")
    return findings


def lint_notes(notes: Iterable[Dict[str, Any]], *, rules: Dict[str, Any] | None = None) -> List[str]:
    rules = rules or load_rules()
    limits = rules.get("limits") or {}
    cap = int(limits.get("weekly_note_max_words") or 130)
    max_dupe = int(limits.get("max_identical_sentences_across_weeks") or 1)
    findings: List[str] = []
    sentences: Counter = Counter()
    for note in notes:
        where = f"note {note.get('date')} {note.get('title')!r}"
        body = str(note.get("body") or "")
        if not body.strip():
            findings.append(f"{where}: empty body")
            continue
        is_fixed_template = str(note.get("title") or "") in _FIXED_TEMPLATE_TITLES
        if not is_fixed_template and _words(body) > cap:
            findings.append(f"{where}: {_words(body)} words exceeds cap {cap}")
        findings.extend(check_copy(body, rules=rules, where=where))
        if is_fixed_template:
            continue
        for sentence in _sentences(body):
            sentences[sentence] += 1
    for sentence, count in sentences.items():
        if count > max_dupe:
            findings.append(f"sentence repeated in {count} weeks: {sentence[:80]!r}")
    return findings


def lint_rest_cards(sessions: Iterable[Any], *, rules: Dict[str, Any] | None = None) -> List[str]:
    """Every Day Off card must carry a body (no blank calendar days) within the cap."""
    rules = rules or load_rules()
    cap = int((rules.get("limits") or {}).get("rest_card_max_words") or 80)
    findings: List[str] = []
    for session in sessions:
        get = session.get if isinstance(session, dict) else lambda k, d=None: getattr(session, k, d)
        if str(get("tp_kind") or "") != "day_off":
            continue
        where = f"day off {get('date')} {get('title')!r}"
        body = str(get("description") or "")
        if not body.strip():
            findings.append(f"{where}: blank calendar day (no active-recovery body)")
            continue
        if _words(body) > cap:
            findings.append(f"{where}: {_words(body)} words exceeds cap {cap}")
        findings.extend(check_copy(body, rules=rules, where=where))
    return findings
