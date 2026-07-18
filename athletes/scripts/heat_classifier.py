#!/usr/bin/env python3
"""
Heat risk classifier for the custom athlete pipeline.

VENDORED implementation of the research doc §3 contract
(gravel-god-training-plans/docs/research/heat-training-gating.md). H1 of the
heat-gating spec (gravel-god-training-plans/specs/heat-gating/SPEC.md) builds
the canonical `tools/heat_classifier.py` in that repo with its own fixture
suite; this module is a faithful port so the custom pipeline (a separate
repo) never has to hardcode `needs_heat_training = True` again. When H1
lands, dedupe: this module should import/delegate to the canonical one
instead of re-implementing the contract.

Contract (research doc §3):
- Usable prose = race.climate.{description,challenges} or race_weather
  (gravel: nested race.guide_variables.race_weather). Road/road-schema
  profiles in this codebase carry climate.overview / climate.average_temp_f
  instead of description/challenges — both shapes are handled.
- climate.primary is a keyword SUPPLEMENT only — it can never establish
  `high` on its own (Pomerode lesson: primary "Hot" over a "mild spring"
  description is a CONTRADICTION, not a heat race).
- Canonical unit is °F; °C is converted. Parses F/C ranges, degree symbol
  variants (°, &deg;, &#176;), decimals, decade words ("upper 80s"),
  "triple digits". Negation ("not hot") and modality ("can be hot",
  "record year") are respected — they don't count as declarative heat
  evidence. Idioms ("hot start", "goes out hot") are filtered.
- RAAM rule: any credible max temp >= 95.0F is `high` REGARDLESS of a
  cold-mix signal (desert heat + freezing passes is still a heat race).
- Ötztaler rule: 85.0-94.9F WITH a cold/alpine mixed signal dampens to
  `moderate` instead of `high`.
- Unitless temps, unclear referents, or contradictory prose -> `unknown`.

Returns {heat_risk, evidence, reason} — never a bare label.
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

HEAT_RISKS = ("high", "moderate", "low", "unknown")

# ---------------------------------------------------------------------------
# Race-data resolution (mirrors the gravel/road sibling-repo lookup pattern
# already used by training_guide_builder.py's _resolve_race_data /
# _gravel_race_dirs / _road_race_dirs).
# ---------------------------------------------------------------------------


def _repo_root() -> Path:
    """athlete-custom-training-plan-pipeline/ (this file is athletes/scripts/)."""
    return Path(__file__).resolve().parent.parent.parent


def _ecosystem_root() -> Path:
    """GravelGod/ — parent of every sibling repo."""
    return _repo_root().parent


def _candidate_race_data_dirs(discipline: Optional[str]) -> List[Path]:
    root = _ecosystem_root()
    gravel_dir = root / "gravel-race-automation" / "race-data"
    road_dir = root / "road-race-automation" / "race-data"
    if (discipline or "").strip().lower() == "road":
        return [road_dir, gravel_dir]
    return [gravel_dir, road_dir]


def load_race_profile(race_id: Optional[str], discipline: Optional[str] = None) -> Optional[Dict]:
    """Load the raw race-data JSON for a slug (race repo resolved by
    discipline). race_id may be a bare slug or a 'discipline:slug' snapshot
    key (known_races.py shape) — only the slug part is used as filename."""
    if not race_id:
        return None
    slug = str(race_id).strip().split(":", 1)[-1]
    if not slug:
        return None
    for race_dir in _candidate_race_data_dirs(discipline):
        candidate = race_dir / f"{slug}.json"
        if candidate.exists():
            try:
                return json.loads(candidate.read_text())
            except (OSError, json.JSONDecodeError):
                continue
    return None


# ---------------------------------------------------------------------------
# Manual override escape hatch (data/heat_overrides.json, race-slug keyed).
# Canonical location is the gravel-god-training-plans repo (H1's home); this
# module also checks a local copy if the custom pipeline ever needs its own.
# ---------------------------------------------------------------------------


def _override_paths() -> List[Path]:
    root = _ecosystem_root()
    return [
        root / "gravel-god-training-plans" / "data" / "heat_overrides.json",
        _repo_root() / "data" / "heat_overrides.json",
    ]


def _load_overrides() -> Dict[str, Any]:
    for path in _override_paths():
        if path.exists():
            try:
                return json.loads(path.read_text())
            except (OSError, json.JSONDecodeError):
                continue
    return {}


# ---------------------------------------------------------------------------
# Prose extraction
# ---------------------------------------------------------------------------


def extract_usable_prose(race: Dict) -> List[Tuple[str, str]]:
    """Return [(source_label, text), ...] for every usable-prose field.

    Handles both schema variants seen in the two sibling repos:
      - gravel-style: climate.description, climate.challenges (list or str)
      - road-style:   climate.overview, climate.average_temp_f / avg_temp_f
      - both:         guide_variables.race_weather (gravel-nested) /
                       top-level race_weather
    """
    climate = race.get("climate") or {}
    if not isinstance(climate, dict):
        climate = {}
    parts: List[Tuple[str, str]] = []

    for key in ("description", "overview"):
        val = climate.get(key)
        if val:
            parts.append((f"climate.{key}", str(val)))

    challenges = climate.get("challenges")
    if isinstance(challenges, list):
        for item in challenges:
            if item:
                parts.append(("climate.challenges", str(item)))
    elif challenges:
        parts.append(("climate.challenges", str(challenges)))

    guide_vars = race.get("guide_variables") or {}
    race_weather = (guide_vars.get("race_weather") if isinstance(guide_vars, dict) else None) \
        or race.get("race_weather")
    if race_weather:
        parts.append(("race_weather", str(race_weather)))

    return parts


def extract_primary(race: Dict) -> Optional[str]:
    climate = race.get("climate") or {}
    if not isinstance(climate, dict):
        return None
    val = climate.get("primary")
    return str(val) if val else None


# ---------------------------------------------------------------------------
# Numeric temperature parsing (°F canonical; °C converted; decade words;
# "triple digits"). Duplicated/overlapping matches are harmless — only
# max() is used downstream.
# ---------------------------------------------------------------------------

_DEG = r"(?:°|&deg;|&#176;)?"
_NUM = r"-?\d+(?:\.\d+)?"  # signed — "-40C" is a real (very cold) mention
_SEP = r"(?:-|–|—|\s+to\s+)"

_RANGE_RE = re.compile(rf"({_NUM}){_SEP}({_NUM})\s*{_DEG}\s*([FC])\b", re.IGNORECASE)
_SINGLE_RE = re.compile(rf"({_NUM})\s*{_DEG}\s*([FC])\b", re.IGNORECASE)
_DASH_RANGE_RE = re.compile(rf"({_NUM})\s*(?:-|–|—)\s*({_NUM})")


def extract_declared_temps_f(race: Dict) -> List[float]:
    """climate.average_temp_f / avg_temp_f are guaranteed-Fahrenheit by field
    name (int, float, or a 'N-M' range string with no embedded unit letter —
    e.g. "59–77", 75) — parsed directly rather than through the generic
    unit-suffix regex, which would otherwise miss them."""
    climate = race.get("climate") or {}
    if not isinstance(climate, dict):
        return []
    temps: List[float] = []
    for key in ("average_temp_f", "avg_temp_f"):
        val = climate.get(key)
        if val is None or val == "":
            continue
        if isinstance(val, (int, float)):
            temps.append(float(val))
            continue
        text = str(val)
        m = _DASH_RANGE_RE.search(text)
        if m:
            temps.extend([float(m.group(1)), float(m.group(2))])
            continue
        try:
            temps.append(float(text.strip()))
        except ValueError:
            pass
    return temps
_DECADE_RE = re.compile(r"\b(low|mid|upper)?\s*(30|40|50|60|70|80|90)s\b", re.IGNORECASE)
_TRIPLE_DIGITS_RE = re.compile(r"\btriple digits\b", re.IGNORECASE)

_DECADE_OFFSETS = {"low": 2, "mid": 5, "upper": 8, None: 5}


def _c_to_f(c: float) -> float:
    return c * 9.0 / 5.0 + 32.0


def _iter_temp_matches(text: str):
    """Yield (fahrenheit_value, match_start_index) for every temperature
    mention in text — the position lets callers apply a LOCAL negation/
    modality check (a modal clause elsewhere in a long sentence must not
    poison an unrelated, unmodified number earlier in the same sentence —
    e.g. '40-75F swings, potential heat, or wildfires' should keep the
    range; only a number the modal/negation word actually precedes/governs
    should be dropped)."""
    for m in _RANGE_RE.finditer(text):
        lo, hi, unit = float(m.group(1)), float(m.group(2)), m.group(3).upper()
        if unit == "C":
            lo, hi = _c_to_f(lo), _c_to_f(hi)
        yield lo, m.start()
        yield hi, m.start()

    for m in _SINGLE_RE.finditer(text):
        val, unit = float(m.group(1)), m.group(2).upper()
        if unit == "C":
            val = _c_to_f(val)
        yield val, m.start()

    for m in _DECADE_RE.finditer(text):
        qualifier = (m.group(1) or "").lower() or None
        base = int(m.group(2))
        yield float(base + _DECADE_OFFSETS.get(qualifier, 5)), m.start()

    for m in _TRIPLE_DIGITS_RE.finditer(text):
        yield 100.0, m.start()


def extract_temps_f(text: str) -> List[float]:
    """Every credible temperature mention in text, canonicalized to °F.
    No negation/modality filtering — see extract_credible_temps_f for that."""
    return [val for val, _ in _iter_temp_matches(text)]


# ---------------------------------------------------------------------------
# Keyword tally with negation / modality / idiom handling
# ---------------------------------------------------------------------------

_SENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")

# Strong heat words drive `high` (declarative, non-negated, non-modal).
# Weak heat words ("warm/humid ... without hot evidence") only ever drive
# `moderate` — the contract explicitly distinguishes the two registers.
_STRONG_HEAT_WORDS = [
    "scorching", "sweltering", "sizzling", "desert heat", "triple digit",
    "triple digits", "heat", "hot",
]
_WEAK_HEAT_WORDS = ["warm", "humid", "humidity", "muggy"]
_HEAT_WORDS = _STRONG_HEAT_WORDS + _WEAK_HEAT_WORDS  # combined, for primary-field direction only
_COLD_WORDS = [
    "hypothermia", "wind chill", "below freezing", "freezing", "freeze",
    "frigid", "chilly", "frost", "alpine", "snow", "icy", "ice", "cold",
    "cool", "rain", "rainy", "wet",
]
_NEGATION_WORDS = ["not ", "isn't", "isnt", "won't", "wont", "n't ", "no ",
                    "without", "never", "rarely", "unlikely"]
_MODAL_WORDS = ["can be", "may be", "could be", "might be", "possibly",
                "possible", "potential", "occasionally", "sometimes",
                "record", "one-off", "some years", "rare years", "in rare"]
_IDIOM_PHRASES = [
    "goes out hot", "go out hot", "went out hot", "hot start", "hot food",
    "hot lap", "red hot", "hot take", "hot property", "piping hot",
    "hot streak", "hot drink", "hot coffee", "hot meal", "hot shower",
]
# Neutral/non-hot descriptive words. Used ONLY for primary/description
# contradiction detection — a race whose primary field claims heat but whose
# prose only ever describes "mild"/"typical"/"temperate" conditions (no
# explicit cold keyword either) is still a contradiction, not silence.
_MILD_WORDS = ["mild", "temperate", "typical weather", "average temperatures",
               "moderate temperatures", "unremarkable"]


def _word_re(word: str) -> "re.Pattern":
    """Word-boundary-anchored pattern for a single keyword/phrase — prevents
    substring false positives ('terrain' containing 'rain', 'Nice'
    containing 'ice')."""
    return re.compile(r"\b" + re.escape(word) + r"\b")


_STRONG_HEAT_RES = [(w, _word_re(w)) for w in _STRONG_HEAT_WORDS]
_WEAK_HEAT_RES = [(w, _word_re(w)) for w in _WEAK_HEAT_WORDS]
_COLD_RES = [(w, _word_re(w)) for w in _COLD_WORDS]


def _sentence_has_idiom(sentence_lower: str) -> bool:
    return any(idiom in sentence_lower for idiom in _IDIOM_PHRASES)


def _word_negated(sentence_lower: str, match_start: int) -> bool:
    window = sentence_lower[max(0, match_start - 20):match_start]
    return any(neg in window for neg in _NEGATION_WORDS)


def keyword_tally(prose_parts: List[Tuple[str, str]]) -> Dict[str, Any]:
    """Tally declarative ('strong') vs modal/occasional ('weak') heat-word
    hits, and declarative cold-word hits, with negation/idiom filtering.
    All matches are word-boundary-anchored — no substring false positives."""
    heat_strong, heat_weak, cold_hits = 0, 0, 0
    evidence: List[str] = []

    for source, text in prose_parts:
        for sentence in _SENT_SPLIT_RE.split(text):
            sent_lower = sentence.lower()
            if _sentence_has_idiom(sent_lower):
                continue
            is_modal = any(m in sent_lower for m in _MODAL_WORDS)

            for hw, pattern in _STRONG_HEAT_RES:
                for m in pattern.finditer(sent_lower):
                    if _word_negated(sent_lower, m.start()):
                        continue
                    if is_modal:
                        heat_weak += 1
                    else:
                        heat_strong += 1
                    evidence.append(f"{source}: …{sentence.strip()[:120]}…")
                    break  # one hit per word per sentence is enough signal

            for hw, pattern in _WEAK_HEAT_RES:
                for m in pattern.finditer(sent_lower):
                    if _word_negated(sent_lower, m.start()):
                        continue
                    heat_weak += 1  # warm/humid never escalate to strong
                    evidence.append(f"{source}: …{sentence.strip()[:120]}…")
                    break

            for cw, pattern in _COLD_RES:
                for m in pattern.finditer(sent_lower):
                    if _word_negated(sent_lower, m.start()):
                        continue
                    cold_hits += 1
                    evidence.append(f"{source}: …{sentence.strip()[:120]}…")
                    break

    return {
        "heat_strong": heat_strong,
        "heat_weak": heat_weak,
        "cold_hits": cold_hits,
        "evidence": evidence,
    }


def _primary_direction(primary_text: Optional[str]) -> Optional[str]:
    """'heat' | 'cold' | None — keyword-only direction of the primary field."""
    if not primary_text:
        return None
    lower = primary_text.lower()
    if _sentence_has_idiom(lower):
        return None
    has_heat = any(pattern.search(lower) for _, pattern in _STRONG_HEAT_RES + _WEAK_HEAT_RES)
    has_cold = any(pattern.search(lower) for _, pattern in _COLD_RES)
    if has_heat and not has_cold:
        return "heat"
    if has_cold and not has_heat:
        return "cold"
    return None


def _prose_is_non_hot(prose_parts: List[Tuple[str, str]]) -> bool:
    """True if usable prose describes conditions with neutral/mild language
    ("mild spring weather", "temperate") and never asserts heat. Used only
    for primary/description contradiction detection (Pomerode lesson) —
    'mild' isn't a cold keyword, but it does contradict a primary field that
    claims 'Hot'."""
    for _, text in prose_parts:
        lower = text.lower()
        if any(w in lower for w in _MILD_WORDS):
            if not any(pattern.search(lower) for _, pattern in _STRONG_HEAT_RES + _WEAK_HEAT_RES):
                return True
    return False


_TEMP_CONTEXT_WINDOW = 30  # chars immediately before a temp match to scan


def extract_credible_temps_f(prose_parts: List[Tuple[str, str]]) -> List[float]:
    """Numeric temperature mentions from prose, filtered for credibility:
    idiom sentences are dropped entirely; a number preceded (within a short
    local window) by a modality cue ("record year saw 100F", "can be 95F")
    or a negation cue ("not 95F", "isn't 95F") is dropped — LOCALLY, not for
    the whole sentence, so a modal clause about a DIFFERENT number/claim
    elsewhere in a long sentence ("40-75F swings, potential heat, or
    wildfires") doesn't poison an unrelated, unmodified range earlier in
    the same sentence. Conservative on the matched number itself: a false
    'unknown'/lower register is far cheaper than a false RAAM/high trigger
    from a negated or record-year number."""
    temps: List[float] = []
    for _, text in prose_parts:
        for sentence in _SENT_SPLIT_RE.split(text):
            sent_lower = sentence.lower()
            if _sentence_has_idiom(sent_lower):
                continue
            for value, start in _iter_temp_matches(sentence):
                window = sent_lower[max(0, start - _TEMP_CONTEXT_WINDOW):start]
                if any(neg in window for neg in _NEGATION_WORDS):
                    continue
                if any(mod in window for mod in _MODAL_WORDS):
                    continue
                temps.append(value)
    return temps


# ---------------------------------------------------------------------------
# Decision
# ---------------------------------------------------------------------------


def _result(heat_risk: str, evidence: List[str], reason: str) -> Dict[str, Any]:
    return {"heat_risk": heat_risk, "evidence": evidence, "reason": reason}


def classify_race_dict(race: Dict) -> Dict[str, Any]:
    """Classify a raw race-data `race` dict per the §3 contract."""
    prose_parts = extract_usable_prose(race)
    primary = extract_primary(race)
    declared_temps = extract_declared_temps_f(race)

    if not prose_parts and not primary and not declared_temps:
        return _result("unknown", [], "no usable prose in race-data profile")

    # Prose-derived temps go through sentence-level credibility filtering
    # (idiom/modal/negated sentences dropped) — declared average_temp_f
    # fields are structured data, not prose, so they bypass that filter.
    temps: List[float] = extract_credible_temps_f(prose_parts)
    temps.extend(declared_temps)

    tally = keyword_tally(prose_parts)
    heat_strong, heat_weak = tally["heat_strong"], tally["heat_weak"]
    cold_signal = tally["cold_hits"] > 0
    evidence = tally["evidence"]

    primary_dir = _primary_direction(primary)
    prose_dir = "heat" if (heat_strong or heat_weak) and not cold_signal else (
        "cold" if cold_signal and not (heat_strong or heat_weak) else None
    )
    # climate.primary alone is a supplement — it can corroborate, but a
    # primary/description contradiction forces `unknown` (Pomerode lesson),
    # UNLESS a numeric trigger below already resolves the race unambiguously
    # (checked first, so RAAM-style multi-climate races aren't punished).
    # A primary heat claim against prose that only ever describes "mild"/
    # "temperate" conditions (no cold keyword either) is ALSO a
    # contradiction — that's the actual Pomerode-shape case.
    contradiction = bool(
        primary_dir and (
            (prose_dir and primary_dir != prose_dir)
            or (primary_dir == "heat" and prose_dir is None and _prose_is_non_hot(prose_parts))
        )
    )

    max_temp = max(temps) if temps else None

    # RAAM rule — a numeric >=95F trigger wins regardless of cold-mix or
    # primary/description contradiction.
    if max_temp is not None and max_temp >= 95.0:
        return _result("high", evidence, f"max credible temp {max_temp:.1f}F >= 95.0F (RAAM rule)")

    if contradiction:
        return _result("unknown", evidence, "primary/description contradiction")

    if max_temp is not None and max_temp >= 85.0:
        if cold_signal:
            return _result("moderate", evidence,
                            f"max temp {max_temp:.1f}F in 85-94.9F with cold-mix signal (Ötztaler rule)")
        return _result("high", evidence, f"max credible temp {max_temp:.1f}F >= 85.0F, no cold-mix")

    if max_temp is not None and 75.0 <= max_temp < 85.0:
        return _result("moderate", evidence, f"max credible temp {max_temp:.1f}F in 75.0-84.9F")

    if max_temp is not None and max_temp < 75.0:
        if heat_strong and not cold_signal:
            return _result("unknown", evidence,
                            "numeric temps say cool but prose asserts heat — contradiction")
        return _result("low", evidence, f"max credible temp {max_temp:.1f}F < 75.0F")

    # No numeric temps at all — keyword-only path.
    if heat_strong and not cold_signal:
        return _result("high", evidence, "heat keywords dominant in usable prose, no cold signal")
    if heat_strong and cold_signal:
        return _result("unknown", evidence, "contradictory heat/cold keywords, no numeric anchor")
    if heat_weak and not cold_signal:
        return _result("moderate", evidence, "warm/humid keywords without confirmed hot evidence")
    if cold_signal and not heat_strong and not heat_weak:
        return _result("low", evidence, "cold/alpine keywords dominant, no heat signal")

    return _result("unknown", evidence, "unparseable / no clear signal in usable prose")


def classify_heat_risk(race_id: Optional[str], discipline: Optional[str] = None) -> Dict[str, Any]:
    """Top-level entry point: race_id (slug) + discipline -> {heat_risk,
    evidence, reason}. Manual overrides beat the classifier. No profile
    found -> unknown (never defaults to high)."""
    overrides = _load_overrides()
    slug = str(race_id).strip().split(":", 1)[-1] if race_id else ""
    if slug and slug in overrides:
        val = overrides[slug]
        if isinstance(val, dict):
            return _result(val.get("heat_risk", "unknown"), val.get("evidence", []), "manual override")
        if val in HEAT_RISKS:
            return _result(val, [], "manual override")

    profile = load_race_profile(race_id, discipline)
    if profile is None:
        return _result("unknown", [], "no race-data profile found for this race")

    race = profile.get("race", profile) if isinstance(profile, dict) else {}
    if not isinstance(race, dict):
        return _result("unknown", [], "race-data profile malformed")

    return classify_race_dict(race)
