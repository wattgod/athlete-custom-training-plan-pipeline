#!/usr/bin/env python3
"""Build and reconcile the normalized index of the coach's curated TP libraries.

C1 of SPEC v2 (docs/SPEC_LIBRARY_SELECTION.md): the pipeline stops synthesizing
its own archetypes for standard training sessions and instead SELECTS from the
coach's 24 "GG |" bike libraries in TrainingPeaks. This module is the read-only
snapshot step: it turns the raw browser-exported dump into a normalized,
selectable item index that C3 (the selector, not built here) will query.

Input: the raw dump (a JSON object of {library_key: {libraryId, items: [...]}},
pulled from the coach's browser session -- no TP credentials belong in this
repo; refreshing the dump is a manual browser-session job). Output: a gzip'd
JSON index at ``athletes/config/tp_library_index.json.gz``.

Name parsing is RIGHT-ANCHORED, not a naive dash-split: 73% of names have
exactly 4 " - "-separated segments, but ~4% are unparseable and several real
shapes (5-dash names, category+modifier names with no internal dash, bare
names like "Just Ride") break a naive split. See ``parse_item_name``.
"""

from __future__ import annotations

import argparse
import gzip
import json
import re
import statistics
from collections.abc import Iterable, Mapping
from functools import lru_cache
from pathlib import Path
from typing import Any


DEFAULT_RAW_PATH = Path(
    "/Users/mattirowe/Downloads/guillermo-romero-delivery/gg_tp_library_full.json"
)
DEFAULT_INDEX_PATH = Path(__file__).parent.parent / "config" / "tp_library_index.json.gz"

# workoutTypeId 2 == Bike in this TP account's taxonomy (verified against the
# real dump: 1,593 of 1,631 items carry it; the remaining 38 are run/MTB/other
# non-bike types 0, 8, 10, 13 and are excluded outright).
BIKE_WORKOUT_TYPE_ID = 2

# Cadence targets live on structure steps as a second target entry with this
# unit (a second target alongside the power target on the same step).
CADENCE_TARGET_UNIT = "roundOrStridePerMinute"

# Leading category words observed across the real dump's item names, longest
# phrase first so "Sweet Spot"/"Race Sim"/"Group Ride" match before any
# shorter prefix could. This is a GLOBAL vocabulary (not scoped per
# library_key): several libraries file items under another library's category
# word (e.g. "Threshold"-named items appear inside sweet_spot_intervals), so a
# strict per-library vocabulary would under-strip. Judgment call -- flagged in
# the executor report.
CATEGORY_VOCAB = (
    "Sweet Spot",
    "Race Sim",
    "Group Ride",
    "VO2max",
    "Torque",
    "Endurance",
    "Threshold",
    "Durability",
    "Specialty",
    "Anaerobic",
    "Tempo",
    "Sprint",
    "Recovery",
)

# Right-anchored token patterns, applied in order: RPE, then duration, then
# level/ref. Each is optional; whatever token isn't present simply isn't
# stripped, and parsing stops early (the remaining text -- possibly the whole
# original name -- becomes name_base). Verified 100% of names that have an
# RPE suffix also have a duration suffix immediately before it (1,508/1,508
# in the real dump), so these two never appear independently.
_RPE_RE = re.compile(r"\s*-?\s*RPE\s*(\d{1,2})(?:\s*-\s*(\d{1,2}))?\s*\Z")
_DURATION_RE = re.compile(r"\s*-\s*(\d+)\s*m(?:in)?\s*\Z")
_LEVEL_RE = re.compile(r"\s*-\s*(ref|[1-6])\s*\Z")

# Dimension-cue keyword classes (D6). Deliberately coarse coach-level
# heuristics, not NLP -- "climb"/"descend" are filed under terrain_surface
# since climbing is a terrain feature in these descriptions. Judgment call --
# flagged in the executor report.
_DIMENSION_PATTERNS: dict[str, re.Pattern[str]] = {
    "cadence_rpm": re.compile(r"\bcadence\b|\brpm\b", re.IGNORECASE),
    "position_posture": re.compile(r"\bposition\b|\bhoods?\b|\bdrops\b|\baero\b", re.IGNORECASE),
    "terrain_surface": re.compile(
        r"\bterrain\b|\bgravel\b|\bdirt\b|\bpavement\b|\bsurface\b|\bclimb(?:ing|s)?\b|\bdescend(?:ing|s)?\b",
        re.IGNORECASE,
    ),
    "drill_technique": re.compile(r"\bdrills?\b|\btechnique\b|\bskills?\b|\bcorner(?:ing|s)?\b", re.IGNORECASE),
    "standing_seated": re.compile(r"\bstand(?:ing|s)?\b|\bseated\b", re.IGNORECASE),
}


# ---------------------------------------------------------------------------
# Name parsing
# ---------------------------------------------------------------------------

def _strip_leading_category(remainder: str) -> str:
    """Strip a leading category word/phrase from a right-stripped remainder.

    Two shapes appear in the real data: the category is its own leading
    " - "-separated segment ("Torque - Stutter Step" -> "Stutter Step"), or
    the category word is glued to a modifier with no dash ("Endurance with
    Surges" -> "with Surges"). Both are handled; if neither matches, the
    remainder passes through unchanged (this is what makes bare names like
    "Just Ride" fall back to name_base = full name).
    """
    first_segment = remainder.split(" - ", 1)[0]
    if first_segment in CATEGORY_VOCAB:
        rest = remainder[len(first_segment):]
        return rest.lstrip(" -")
    for category in CATEGORY_VOCAB:
        if remainder.startswith(category + " "):
            return remainder[len(category):].lstrip(" -")
    return remainder


def parse_item_name(name: str) -> dict[str, Any]:
    """Right-anchor-parse a raw TP item name into name_base/explicit_level/rpe_text.

    From the right: strip an optional RPE token, then an optional NNmin/NNm
    token, then an optional bare 'ref' or digit 1-6 (captured as
    explicit_level -- only 1-6 counts; other digits, e.g. an hour-count like
    "- 7 -" in "Endurance - (MxHr) - 7 - 180min", are NOT a level token and
    stay embedded in name_base). Then strip a leading category word. The
    remainder -- which may itself contain dashes -- is name_base. Names with
    none of these tokens (~5% of the real dump) fall back to name_base = the
    full original name and stay selectable as singletons.
    """
    remainder = name
    rpe_text = None
    match = _RPE_RE.search(remainder)
    if match:
        rpe_text = match.group(1) if match.group(2) is None else f"{match.group(1)}-{match.group(2)}"
        remainder = remainder[: match.start()]

    match = _DURATION_RE.search(remainder)
    if match:
        remainder = remainder[: match.start()]

    explicit_level = None
    match = _LEVEL_RE.search(remainder)
    if match:
        token = match.group(1)
        if token != "ref":
            explicit_level = int(token)
        remainder = remainder[: match.start()]

    name_base = _strip_leading_category(remainder)
    return {"name_base": name_base, "explicit_level": explicit_level, "rpe_text": rpe_text}


# ---------------------------------------------------------------------------
# Dimension scoring (D6)
# ---------------------------------------------------------------------------

def classify_dimension_cues(description: str | None) -> set[str]:
    """Return the distinct dimension-cue classes present in a description."""
    if not description:
        return set()
    return {name for name, pattern in _DIMENSION_PATTERNS.items() if pattern.search(description)}


def has_cadence_targets(structure: Mapping[str, Any] | None) -> bool:
    """Return True if any structure step carries a roundOrStridePerMinute target."""
    if not structure:
        return False
    for element in structure.get("structure", []) or []:
        for step in element.get("steps", []) or []:
            for target in step.get("targets", []) or []:
                if target.get("unit") == CADENCE_TARGET_UNIT:
                    return True
    return False


def compute_dimension_score(description: str | None, structure: Mapping[str, Any] | None) -> int:
    """Count of distinct description dimension-cue classes, plus 1 if the
    structure carries a cadence target (D6). Max possible score is 6."""
    return len(classify_dimension_cues(description)) + (1 if has_cadence_targets(structure) else 0)


# ---------------------------------------------------------------------------
# IF computation
# ---------------------------------------------------------------------------

def compute_if_planned(tss: float | None, hours: float | None, existing: float | None) -> float | None:
    """Return the item's IF, computed from TSS/hours when the dump omits it.

    Standard relationship TSS = 100 * hours * IF^2, verified against the real
    dump's 1,410 items that carry both tssPlanned and ifPlanned (mean abs
    error 0.0004). Returns None when TSS or hours aren't available to compute
    from (67 real items have neither -- unstructured "coach's discretion"
    briefs).
    """
    if existing is not None:
        return existing
    if tss is None or not hours:
        return None
    return (tss / (100 * hours)) ** 0.5


# ---------------------------------------------------------------------------
# T27: curation-consistency lint
#
# Items are placed BYTE-VERBATIM -- the authored description ships to the
# athlete untouched. A curated item whose description contradicts its own
# duration or its own title RPE ships wrong prose to a paying customer (the
# live catch: "Endurance - Atkins Revenge - 2 - 210min" and "- 3 - 240min"
# both carry level 1's description "Z2 for ~2.5 hours", correct only for the
# 150min level 1). These two lints compute PER-ITEM flags from the item's own
# fields; ``library_selector`` excludes flagged items from selection pools.
# Precision over recall throughout -- a false flag excludes a good item from
# selection, so every heuristic below is deliberately conservative.
# ---------------------------------------------------------------------------

# Duration-claim token: optional leading '~', a number (decimals allowed),
# an optional connecting space/tab/hyphen (NEVER a newline -- a bare '\s'
# connector let "2" on one line and an unrelated "Hour 2:" section label
# several lines below it glue into a garbage "2 ... Hour" match against the
# real dump), then hours or minutes. Matches "~2.5 hours", "3 hrs",
# "2-hour", "5min", "5 minutes".
_DURATION_CLAIM_RE = re.compile(
    r"~?(?P<value>\d+(?:\.\d+)?)[ \t]*-?[ \t]*(?P<unit>hours?|hrs?|min(?:ute)?s?)\b",
    re.IGNORECASE,
)

# A duration token immediately followed by '@'/'%' or the words power/watts/
# FTP, or immediately preceded by an interval-count "NxN" token, describes a
# single interval step ("5min @ 90%", "6x5min"), never the whole session.
_DURATION_INTERVAL_BEFORE_RE = re.compile(r"\d\s*[x×]\s*\Z", re.IGNORECASE)
_DURATION_INTERVAL_AFTER_RE = re.compile(r"\A\s*[@%]|\A\s*(?:power|watts?|ftp)\b", re.IGNORECASE)
# A duration token whose immediately preceding word is "first"/"last"/
# "final"/"remaining" is a temporal sub-segment qualifier ("First 2 hours Z2
# easy", "In the last 3 hours"), not a whole-session claim.
_DURATION_SUB_SEGMENT_BEFORE_RE = re.compile(r"\b(?:first|last|final|remaining)\s+\Z", re.IGNORECASE)
# A "STRUCTURE:" label or a "->"/unicode arrow is this dump's convention for
# a warmup->work->cooldown breakdown authored with prime-notation minutes
# (15', 20') that a plain min/hour regex can't see -- the prose sentence
# elsewhere in the same description ("40 minutes total work") is then a
# WORK-only summary, not a whole-session claim (real "G-Spot" fixtures).
_STRUCTURE_MARKER_RE = re.compile(r"\bstructure\s*:|->|→", re.IGNORECASE)

_DURATION_CLAIM_RELATIVE_TOLERANCE = 0.20
# A claim "plausibly describes the whole session" only when it's within
# 0.5x-1.5x of the item's own authored total. Real-dump evidence ruled out
# an additional "line opens with '<word> for'" bypass (as in "Z2 for ~2.5
# hours"): the exact same surface shape ("Z1/Z2 for 30 min", "Z1/Z2 Warm up
# for 20 min minimum") is also how these curated descriptions open their
# WARM-UP sub-segment inside a longer structured item ("Bakken", "La
# Balanguera") -- treating that as a whole-session claim produced false
# positives the range check alone correctly avoids (a 30min opener is nowhere
# near 0.5x-1.5x of a 150-300min authored total). The real Atkins Revenge
# catch is caught by the range check alone (150min claim vs 210/240min
# authored, both within 0.5x-1.5x). Precision over recall -- flagged as a
# deviation from the literal spec wording in the executor report.
_DURATION_CLAIM_PLAUSIBLE_LO = 0.5
_DURATION_CLAIM_PLAUSIBLE_HI = 1.5

# A description built from multiple dash/bullet/blank-line-divided segments,
# where MORE THAN ONE of those segments carries its own duration number, is a
# structured multi-part prescription (warmup + main + cooldown, or a
# multi-block torque/endurance ride) -- its FIRST segment's number is a piece
# of the total, not a claim about the whole session ("150 minutes Z2" opening
# a "Torque Toking" item whose 4 further segments add up the rest of the
# authored 300min; "40 minutes total" of G-Spot WORK inside a description
# that separately states a 15min warmup + 10min cooldown). A plain
# single-instruction description (Atkins Revenge: one Z2 duration, the rest
# fueling prose with no other exercise-duration numbers) has at most one such
# segment and is unaffected.
_SEGMENT_DIVIDER_RE = re.compile(r"\n[ \t]*[-•*★►=]{1,3}[ \t]*\n|\n{2,}")


def _duration_claim_is_interval_context(description: str, start: int, end: int) -> bool:
    """True when the duration token at [start, end) is attached to
    @/%/power/watts/FTP, an interval-count prefix, or a first/last/final/
    remaining temporal qualifier -- an interval- or sub-segment-level
    mention, never a whole-session claim."""
    before = description[max(0, start - 20):start]
    after = description[end:end + 20]
    if _DURATION_INTERVAL_BEFORE_RE.search(before):
        return True
    if _DURATION_SUB_SEGMENT_BEFORE_RE.search(before):
        return True
    if _DURATION_INTERVAL_AFTER_RE.search(after):
        return True
    return False


def _duration_claim_should_skip_description(description: str) -> bool:
    """True when the description reads as a structured multi-part
    prescription rather than a single whole-session instruction -- either
    more than one dash/bullet/blank-line-divided segment carries its own
    duration number (see _SEGMENT_DIVIDER_RE), or the description uses this
    dump's "STRUCTURE:"/arrow convention for a prime-notation (15', 20')
    warmup->work->cooldown breakdown that the min/hour regex can't see on
    its own."""
    if _STRUCTURE_MARKER_RE.search(description):
        return True
    segments_with_duration = sum(
        1 for segment in _SEGMENT_DIVIDER_RE.split(description) if _DURATION_CLAIM_RE.search(segment)
    )
    return segments_with_duration > 1


def compute_duration_claim_flag(description: str | None, authored_min: float | None) -> dict[str, Any] | None:
    """Return evidence when the description's whole-session duration claim
    differs from the item's own authored duration by more than 20%, else
    None.

    Interval- and sub-segment-level mentions ("5min @ 90%", "First 2 hours
    Z2 easy") are never candidates; only claims within 0.5x-1.5x of the
    authored total are read as plausibly describing the whole session (see
    _DURATION_CLAIM_PLAUSIBLE_* docstring above); a structured multi-part
    description is skipped entirely (see
    _duration_claim_should_skip_description); and if ANY qualifying claim in
    the description agrees with the authored duration, the description
    isn't lying about its own length even if another looser mention (a
    different unit style the regex missed, a race-context aside) would
    otherwise look like a contradiction -- no flag."""
    if not description or not authored_min:
        return None
    description = description.replace("\r\n", "\n").replace("\r", "\n")
    if _duration_claim_should_skip_description(description):
        return None
    qualifying: list[tuple[re.Match, float, float]] = []
    for match in _DURATION_CLAIM_RE.finditer(description):
        if _duration_claim_is_interval_context(description, match.start(), match.end()):
            continue
        value = float(match.group("value"))
        unit = match.group("unit").lower()
        claimed_min = value * 60 if unit.startswith("h") else value
        if not (_DURATION_CLAIM_PLAUSIBLE_LO * authored_min <= claimed_min <= _DURATION_CLAIM_PLAUSIBLE_HI * authored_min):
            continue
        rel_diff = abs(claimed_min - authored_min) / authored_min
        qualifying.append((match, claimed_min, rel_diff))
    if not qualifying:
        return None
    if any(rel_diff <= _DURATION_CLAIM_RELATIVE_TOLERANCE for _, _, rel_diff in qualifying):
        return None
    match, claimed_min, rel_diff = qualifying[0]
    return {
        "claim_text": match.group(0).strip(),
        "claimed_min": claimed_min,
        "authored_min": authored_min,
        "rel_diff": round(rel_diff, 3),
    }


# RPE mentions in the body ("RPE 2-3", "RPE: 6-7"). Reuses the title-token
# shape (bare int or int-int) but is not right-anchored -- it scans anywhere.
_RPE_BODY_RE = re.compile(r"\bRPE:?\s*(\d{1,2})(?:\s*-\s*(\d{1,2}))?\b", re.IGNORECASE)
_WARMUP_COOLDOWN_WORD_RE = re.compile(r"\bwarm[\s-]?up\b|\bcool[\s-]?down\b", re.IGNORECASE)
# Leading decoration ("★ ", "• ", "- ", "* ") stripped before testing a line
# against _SECTION_HEADER_RE -- real fixtures use "★ Warm-up:" / "► Main Set"
# style bullets, and a header regex that requires the line to START with a
# letter would silently miss every one of them.
_LINE_DECORATION_RE = re.compile(r"^[^A-Za-z0-9]+")
# A line that's just a section label ("WARM-UP:", "MAIN SET:", "COOL-DOWN:")
# -- everything under a warm-up/cool-down header is excluded until the next
# header, catching real fixtures where the warmup RPE sits several bullet
# lines below the header rather than glued to the mention itself.
_SECTION_HEADER_RE = re.compile(r"^([A-Za-z][A-Za-z0-9 /\-]{2,40}):\s*\Z")
# A body RPE mention on a line that also carries interval-structure cues
# (a specific %/zone/pace target, a rep count, or a hard/easy/recovery
# work-vs-rest label) describes ONE step of a structured interval set, not
# the whole session -- real fixtures ("AnCap Sets": "30s @ Z6 (Max Effort),
# RPE 9-10" against a title of RPE9-10, "60s @ Z1 (RPE 1-2) recovery")
# produced false whole-session-conflict flags without this exclusion.
_RPE_INTERVAL_LINE_RE = re.compile(
    r"@|\bZ\d\b|\bzone\s*\d\b|\d+\s*[x×]\s*\d+|\bsets?\b|\breps?\b"
    r"|\beasy\b|\bhard\b|\brecovery\b|\bmax\s*effort\b",
    re.IGNORECASE,
)

_RPE_CONFLICT_BAND_GAP = 2


def _parse_rpe_range(rpe_text: str) -> tuple[int, int]:
    parts = rpe_text.split("-")
    lo = int(parts[0])
    hi = int(parts[1]) if len(parts) > 1 else lo
    return lo, hi


def _body_rpe_mentions(description: str) -> list[tuple[int, int]]:
    """Whole-session RPE mentions in the body: skips anything under a
    warm-up/cool-down section header, on a line that itself names
    warm-up/cool-down, or on a line carrying interval-structure cues
    (a specific zone/pace/% target, a rep count, or a hard/easy/recovery
    work-vs-rest label)."""
    mentions: list[tuple[int, int]] = []
    section_excluded = False
    for line in description.splitlines():
        stripped = line.strip()
        header_candidate = _LINE_DECORATION_RE.sub("", stripped)
        header_match = _SECTION_HEADER_RE.match(header_candidate)
        if header_match:
            section_excluded = bool(_WARMUP_COOLDOWN_WORD_RE.search(header_match.group(1)))
            continue
        if (section_excluded or _WARMUP_COOLDOWN_WORD_RE.search(line)
                or _RPE_INTERVAL_LINE_RE.search(line)):
            continue
        for match in _RPE_BODY_RE.finditer(line):
            lo = int(match.group(1))
            hi = int(match.group(2)) if match.group(2) else lo
            mentions.append((lo, hi))
    return mentions


def compute_rpe_conflict_flag(rpe_text: str | None, description: str | None) -> dict[str, Any] | None:
    """Return evidence when the title's trailing RPE token contradicts an
    explicit whole-session RPE statement in the body by >=2 bands, else
    None. Warm-up/cool-down RPE mentions never count."""
    if not rpe_text or not description:
        return None
    title_lo, title_hi = _parse_rpe_range(rpe_text)
    for body_lo, body_hi in _body_rpe_mentions(description):
        if body_lo > title_hi:
            gap = body_lo - title_hi
        elif title_lo > body_hi:
            gap = title_lo - body_hi
        else:
            gap = 0
        if gap >= _RPE_CONFLICT_BAND_GAP:
            return {
                "title_rpe": rpe_text,
                "body_rpe": f"{body_lo}-{body_hi}" if body_lo != body_hi else str(body_lo),
                "gap": gap,
            }
    return None


# ---------------------------------------------------------------------------
# T29: bookend-intensity lint
#
# Coach ruling ("a warm up harder than the main set is a critical error"): a
# live delivered item (FatMax Development, main set ~55-65% FTP) had its
# cool-down START at 70% FTP -- above the ENTIRE main set -- so TP's chart
# rendered the cool-down as the hardest part of the ride. Scope is narrow by
# design (precision over recall, same as the two lints above): only items
# whose main content never exceeds 70% FTP are candidates at all, so a real
# hard-finish opener or crit-warmup (dominant non-bookend target > 70%) is
# exempt by construction, never reaching the comparison below.
# ---------------------------------------------------------------------------

_BOOKEND_INTENSITY_TOLERANCE_PCT = 2.0
_BOOKEND_INTENSITY_EASY_MAX_PCT = 70.0
_BOOKEND_INTENSITY_MIN_MAIN_BLOCKS = 3

# Field tests (FTP/anaerobic assessments) author their all-out effort as an
# untargeted (0%) leaf -- there is no %FTP number to describe "go as hard as
# you can" -- so the heuristic below only ever sees the test's easy
# reference-pace padding and reads the whole session as an easy main set.
# A real "Anaerobic Test" item's 50-75% warmup/cooldown around that padding
# is coach-appropriate ramp-into/out-of-a-near-maximal-effort design, not
# the FIX1 defect (an easy RIDE whose bookends outrun its own body); name-
# match the same way delivery_render._rpe already detects field tests.
_FIELD_TEST_NAME_RE = re.compile(r"\b(?:anaerobic|ftp|field)\b.*\btest\b", re.IGNORECASE)


def _bookend_intensity_elements(
    structure: Mapping[str, Any] | None,
) -> list[tuple[str, dict[str, float] | None]]:
    """[(zwo_tag, expected_power_dict_or_None), ...] in session order.

    Reuses tp_structure_to_zwo's already corpus-verified structure walker
    (warmUp/coolDown -> Ramp bounds, active/rest -> SteadyState/IntervalsT,
    target-free -> FreeRide) rather than re-deriving TP's structure shape.
    """
    if not structure:
        return []
    try:
        from tp_structure_to_zwo import _build as _tp_build
        xml_parts, expected, _dropped, _notes = _tp_build(structure)
    except Exception:
        return []
    elements = []
    for xml, exp in zip(xml_parts, expected):
        match = re.match(r"<(\w+)", xml.lstrip())
        elements.append((match.group(1) if match else "", exp))
    return elements


def compute_bookend_intensity_flag(
    structure: Mapping[str, Any] | None, name: str | None = None
) -> dict[str, Any] | None:
    """Return evidence when a bookend renders harder than its own main set.

    Flags when the session opens with a Warmup ramp whose peak, or closes
    with a Cooldown ramp whose start, exceeds the main set's hardest
    (non-bookend) target by more than _BOOKEND_INTENSITY_TOLERANCE_PCT
    points -- but only for items whose main content is itself easy
    (dominant non-bookend target <= 70% FTP; see module docstring above).
    Skips items with fewer than _BOOKEND_INTENSITY_MIN_MAIN_BLOCKS
    target-bearing blocks in the whole session (too little structure to
    call this a "main set" at all), and field tests (see
    _FIELD_TEST_NAME_RE above).
    """
    if name and _FIELD_TEST_NAME_RE.search(name):
        return None
    elements = _bookend_intensity_elements(structure)
    # A leaf targeted at exactly 0% FTP is TP's "no fixed target -- give it
    # everything" convention for open-ended field-test efforts (an
    # untargeted all-out block survives _build() as a 0% SteadyState). That
    # is not a real intensity prescription and must not read as this item's
    # "easy" main-set body.
    elements = [
        (tag, (exp if exp and any(v > 0 for v in exp.values()) else None))
        for tag, exp in elements
    ]
    # "Too little structure to call a main set" is a whole-session guard
    # (warmup + a single flat body + cooldown is exactly 3 target-bearing
    # blocks and IS the shape this lint exists to catch -- the machine-built
    # "Endurance Blocks" ladder is one flat SteadyState between two ramps),
    # not a main-set-only count.
    target_bearing_total = [exp for _tag, exp in elements if exp]
    if len(target_bearing_total) < _BOOKEND_INTENSITY_MIN_MAIN_BLOCKS:
        return None

    main = [(tag, exp) for tag, exp in elements if tag not in ("Warmup", "Cooldown")]
    main_values = [
        exp[key] for _tag, exp in main if exp
        for key in ("power_pct", "on_power_pct", "off_power_pct") if key in exp
    ]
    if not main_values:
        return None
    main_max = max(main_values)
    if main_max > _BOOKEND_INTENSITY_EASY_MAX_PCT:
        return None  # Hard main set (openers/crit-warmup/race-prep) -- exempt.

    first_tag, first_exp = elements[0]
    last_tag, last_exp = elements[-1]
    first_peak = first_exp.get("power_high_pct") if first_tag == "Warmup" and first_exp else None
    last_start = last_exp.get("power_low_pct") if last_tag == "Cooldown" and last_exp else None

    offenders = []
    if first_peak is not None and first_peak > main_max + _BOOKEND_INTENSITY_TOLERANCE_PCT:
        offenders.append({"block": "warmup", "target_pct": round(first_peak, 1)})
    if last_start is not None and last_start > main_max + _BOOKEND_INTENSITY_TOLERANCE_PCT:
        offenders.append({"block": "cooldown", "target_pct": round(last_start, 1)})
    if not offenders:
        return None
    return {"main_max_pct": round(main_max, 1), "offenders": offenders}


# ---------------------------------------------------------------------------
# Item selection + exclusion
# ---------------------------------------------------------------------------

def _is_bike(item: Mapping[str, Any]) -> bool:
    return item.get("workoutTypeId") == BIKE_WORKOUT_TYPE_ID


def _has_usable_structure(item: Mapping[str, Any]) -> bool:
    structure = item.get("structure")
    return bool(structure and structure.get("structure"))


def load_raw_dump(path: Path) -> dict[str, Any]:
    """Read and validate the documented {library_key: {libraryId, items}} dump format."""
    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not read raw TP library dump {path}: {exc}") from exc
    if not isinstance(document, dict):
        raise ValueError("Raw TP library dump JSON must be an object of {library_key: {...}}")
    return document


def _normalize_extra_exclusions(extra_exclusions: Any) -> dict[int, str]:
    """Normalize the extra_exclusions hook into {item_id: reason}.

    Accepts a mapping already in that shape, or an iterable of ints / of
    {"item_id": ..., "reason": ...} objects (the JSON sidecar shape loaded by
    --extra-exclusions on the CLI).
    """
    if extra_exclusions is None:
        return {}
    if isinstance(extra_exclusions, Mapping):
        return {int(item_id): str(reason) for item_id, reason in extra_exclusions.items()}
    normalized: dict[int, str] = {}
    for entry in extra_exclusions:
        if isinstance(entry, Mapping):
            normalized[int(entry["item_id"])] = str(entry.get("reason", "extra_exclusion"))
        else:
            normalized[int(entry)] = "extra_exclusion"
    return normalized


def build_items(
    raw: Mapping[str, Any], extra_exclusions: Any = None
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Turn the raw dump into (selectable items, exclusions report).

    Exclusion order: non-bike (workoutTypeId != 2), then structureless bike
    (bike but no usable ``structure.structure``), then the extra_exclusions
    hook (a documented escape valve for C2 round-trip failures discovered
    downstream -- this module never re-parses to apply them, it simply drops
    matching item_ids and logs why).
    """
    extra_exclusion_reasons = _normalize_extra_exclusions(extra_exclusions)

    items: list[dict[str, Any]] = []
    excluded_non_bike: list[dict[str, Any]] = []
    excluded_structureless: list[dict[str, Any]] = []
    excluded_extra: list[dict[str, Any]] = []

    for library_key, library in raw.items():
        for raw_item in library.get("items", []):
            item_id = raw_item.get("exerciseLibraryItemId")
            name_raw = raw_item.get("itemName", "")

            if not _is_bike(raw_item):
                excluded_non_bike.append({"item_id": item_id, "library_key": library_key, "name_raw": name_raw})
                continue
            if not _has_usable_structure(raw_item):
                excluded_structureless.append(
                    {"item_id": item_id, "library_key": library_key, "name_raw": name_raw}
                )
                continue
            if item_id in extra_exclusion_reasons:
                excluded_extra.append(
                    {
                        "item_id": item_id,
                        "library_key": library_key,
                        "name_raw": name_raw,
                        "reason": extra_exclusion_reasons[item_id],
                    }
                )
                continue

            parsed = parse_item_name(name_raw)
            hours = raw_item.get("totalTimePlanned")
            tss = raw_item.get("tssPlanned")
            structure = raw_item.get("structure")
            description = raw_item.get("description")
            duration_min = round(hours * 60) if hours else None

            items.append(
                {
                    "item_id": item_id,
                    "library_key": library_key,
                    "name_raw": name_raw,
                    "name_base": parsed["name_base"],
                    "explicit_level": parsed["explicit_level"],
                    "duration_min": duration_min,
                    "tss": tss,
                    "if_planned": compute_if_planned(tss, hours, raw_item.get("ifPlanned")),
                    "rpe_text": parsed["rpe_text"],
                    "dimension_score": compute_dimension_score(description, structure),
                    "has_cadence_targets": has_cadence_targets(structure),
                    "structure": structure,
                    "description": description,
                    "workout_type_id": raw_item.get("workoutTypeId"),
                    "lint_duration_claim": compute_duration_claim_flag(description, duration_min),
                    "lint_rpe_conflict": compute_rpe_conflict_flag(parsed["rpe_text"], description),
                    "lint_bookend_intensity": compute_bookend_intensity_flag(structure, name_raw),
                }
            )

    exclusions = {
        "non_bike": {"count": len(excluded_non_bike), "items": excluded_non_bike},
        "structureless_bike": {"count": len(excluded_structureless), "items": excluded_structureless},
        "extra": {"count": len(excluded_extra), "items": excluded_extra},
    }
    return items, exclusions


# ---------------------------------------------------------------------------
# Family grouping (D8)
# ---------------------------------------------------------------------------

def _family_key(item: Mapping[str, Any]) -> str:
    return f"{item['library_key']}||{item['name_base']}"


def build_family_index(items: Iterable[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    """Group selectable items into families by (library_key, name_base) and
    build each family's ladder (D8): rung = explicit_level when every member
    that's ranked carries one, else rank by if_planned ascending. Members
    lacking a usable rung key (no explicit_level in an explicit-level family,
    or no if_planned in an IF-ranked family) are still listed but excluded
    from the ladder.
    """
    members: dict[str, list[Mapping[str, Any]]] = {}
    for item in items:
        members.setdefault(_family_key(item), []).append(item)

    families: dict[str, dict[str, Any]] = {}
    for key, family_members in members.items():
        library_key = family_members[0]["library_key"]
        name_base = family_members[0]["name_base"]
        has_any_explicit_level = any(m["explicit_level"] is not None for m in family_members)

        ladder: list[dict[str, Any]] = []
        if has_any_explicit_level:
            rung_basis = "explicit_level"
            ranked = sorted(
                (m for m in family_members if m["explicit_level"] is not None),
                key=lambda m: m["explicit_level"],
            )
            for member in ranked:
                ladder.append(
                    {
                        "rung": member["explicit_level"],
                        "item_id": member["item_id"],
                        "explicit_level": member["explicit_level"],
                        "if_planned": member["if_planned"],
                    }
                )
        else:
            rung_basis = "if_rank"
            ranked = sorted(
                (m for m in family_members if m["if_planned"] is not None),
                key=lambda m: m["if_planned"],
            )
            for rung, member in enumerate(ranked, start=1):
                ladder.append(
                    {
                        "rung": rung,
                        "item_id": member["item_id"],
                        "explicit_level": member["explicit_level"],
                        "if_planned": member["if_planned"],
                    }
                )

        families[key] = {
            "library_key": library_key,
            "name_base": name_base,
            "members": [m["item_id"] for m in family_members],
            "ladder": ladder,
            "rung_basis": rung_basis,
        }
    return families


def family_stats(families: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    family_count = len(families)
    sizes = [len(family["members"]) for family in families.values()]
    singleton_count = sum(1 for size in sizes if size == 1)
    return {
        "family_count": family_count,
        "singleton_count": singleton_count,
        "singleton_share": (singleton_count / family_count) if family_count else 0.0,
        "max_family_size": max(sizes) if sizes else 0,
    }


# ---------------------------------------------------------------------------
# Index build / write / reconcile
# ---------------------------------------------------------------------------

def build_index(raw_path: Path, extra_exclusions: Any = None) -> dict[str, Any]:
    """Build the full normalized index document from a raw dump path."""
    raw = load_raw_dump(raw_path)
    items, exclusions = build_items(raw, extra_exclusions=extra_exclusions)
    families = build_family_index(items)

    per_library_counts: dict[str, int] = {}
    for item in items:
        per_library_counts[item["library_key"]] = per_library_counts.get(item["library_key"], 0) + 1

    explicit_level_count = sum(1 for item in items if item["explicit_level"] is not None)
    dimension_scores = [item["dimension_score"] for item in items]

    return {
        "source_path": str(raw_path),
        "counts": {
            "selectable": len(items),
            "per_library": per_library_counts,
            "explicit_level_coverage": (explicit_level_count / len(items)) if items else 0.0,
            "dimension_score_distribution": {
                "min": min(dimension_scores) if dimension_scores else 0,
                "median": statistics.median(dimension_scores) if dimension_scores else 0,
                "max": max(dimension_scores) if dimension_scores else 0,
            },
        },
        "exclusions": exclusions,
        "family_stats": family_stats(families),
        "families": families,
        "items": items,
    }


def write_index(index: Mapping[str, Any], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(index, indent=2, sort_keys=True).encode("utf-8")
    with gzip.open(out_path, "wb") as handle:
        handle.write(payload)


# ---------------------------------------------------------------------------
# T27 manual-review flags (applied at READ time, not baked into the file).
#
# These are curated-content defects a human (or a grader) verified but the
# automated lint heuristics cannot detect. The coach fixes them at the
# source in TrainingPeaks; entries here exclude the item from selection and
# put it on the --lint-report until the corrected item lands in a fresh
# snapshot (at which point the entry should be deleted). NEVER edit the
# authored description/structure inside the index instead -- the index
# mirrors the coach's library verbatim and hand-edits silently revert on
# the next rebuild.
_MANUAL_REVIEW: dict[int, str] = {
    # Aug 17 2026 adversarial grade (Sonja v23):
    14355843: "description says 'on the TT bike'/aero position in a gravel context; rep count '4x 5min' disagrees with structure",
    14355844: "description says 'on the TT bike'/aero position in a gravel context",
    # Aug 17 2026 adversarial grade (Sonja v24):
    14356288: "Cadence Work: desc lists a 5min @76-87% segment absent from structure; off-step targets 70% FTP @115rpm (harder cadence than the work step, no recovery floor); name RPE8-9 vs body RPE 6-7",
    14356260: "name says '(TT bike)' in a gravel context; whole-ride 0-75% open target derives a meaningless '8x7min @38%' title",
    # Aug 17 2026 adversarial grade (Sonja v25):
    14356246: "Base - + Heat Training: desc says '~150min' on a 180min item (under the 20% lint threshold), promises warm-up/cool-down absent from the single-block structure; title says Heat Training but desc carries no heat instructions",
    14356254: "Better Late Than Cadence: missing primaryIntensityTargetOrRange; min-only targets with no ceilings on the 90min block and the 10x60s reps",
}


def _apply_manual_review(index: dict) -> dict:
    for item in index.get("items", []):
        reason = _MANUAL_REVIEW.get(item.get("item_id"))
        if reason:
            item["lint_manual_review"] = {"reason": reason}
    return index


def read_index(path: Path) -> dict[str, Any]:
    with gzip.open(path, "rb") as handle:
        return _apply_manual_review(json.loads(handle.read().decode("utf-8")))


def reconcile(raw_path: Path, index_path: Path, extra_exclusions: Any = None) -> dict[str, Any]:
    """Compare a fresh raw dump against a previously built index and report drift.

    Mirrors the build_run_tp_library reconcile pattern: rebuild the expected
    document from the fresh source, diff it against the on-disk index by
    item_id, and report added/removed/changed items so a refreshed browser
    dump can be reviewed before it's committed.
    """
    fresh = build_index(raw_path, extra_exclusions=extra_exclusions)
    existing = read_index(index_path)

    fresh_by_id = {item["item_id"]: item for item in fresh["items"]}
    existing_by_id = {item["item_id"]: item for item in existing["items"]}

    added = sorted(set(fresh_by_id) - set(existing_by_id))
    removed = sorted(set(existing_by_id) - set(fresh_by_id))

    changed: list[dict[str, Any]] = []
    tracked_fields = (
        "name_base",
        "explicit_level",
        "duration_min",
        "tss",
        "if_planned",
        "dimension_score",
        "has_cadence_targets",
        "lint_duration_claim",
        "lint_rpe_conflict",
        "lint_bookend_intensity",
    )
    for item_id in sorted(set(fresh_by_id) & set(existing_by_id)):
        fresh_item, existing_item = fresh_by_id[item_id], existing_by_id[item_id]
        diffs = {
            field: {"old": existing_item.get(field), "new": fresh_item.get(field)}
            for field in tracked_fields
            if existing_item.get(field) != fresh_item.get(field)
        }
        if diffs:
            changed.append({"item_id": item_id, "fields": diffs})

    return {
        "added": added,
        "removed": removed,
        "changed": changed,
        "family_count_old": existing["family_stats"]["family_count"],
        "family_count_new": fresh["family_stats"]["family_count"],
    }


# ---------------------------------------------------------------------------
# Downstream loader API (cached)
# ---------------------------------------------------------------------------

@lru_cache(maxsize=None)
def _load_index_cached(path_str: str) -> dict[str, Any]:
    return read_index(Path(path_str))


def load_index(path: Path = DEFAULT_INDEX_PATH) -> dict[str, Any]:
    """Return the built index (items + families), cached per resolved path.

    Downstream code (C3, the selector) should use this rather than reading
    the gzip file directly. Returns the same dict shape written by
    ``build_index``/``write_index``: ``items`` (list) and ``families`` (dict
    keyed "library_key||name_base").
    """
    return _load_index_cached(str(Path(path).resolve()))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _load_extra_exclusions_file(path: Path | None) -> Any:
    if path is None:
        return None
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    return document


def _print_summary(index: Mapping[str, Any]) -> None:
    counts = index["counts"]
    stats = index["family_stats"]
    print(f"selectable items: {counts['selectable']}")
    print("per-library counts:")
    for library_key, count in sorted(counts["per_library"].items()):
        print(f"  {library_key}: {count}")
    print(f"excluded non-bike: {index['exclusions']['non_bike']['count']}")
    print(f"excluded structureless bike: {index['exclusions']['structureless_bike']['count']}")
    print(f"excluded extra: {index['exclusions']['extra']['count']}")
    print(f"families: {stats['family_count']}")
    print(f"singleton share: {stats['singleton_share']:.1%}")
    print(f"explicit-level coverage: {counts['explicit_level_coverage']:.1%}")
    dist = counts["dimension_score_distribution"]
    print(f"dimension_score min/median/max: {dist['min']}/{dist['median']}/{dist['max']}")


def lint_flagged_items(index: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Every item in ``index`` carrying a lint flag, in item_id order."""
    flagged = [
        item for item in index["items"]
        if item.get("lint_duration_claim") or item.get("lint_rpe_conflict")
        or item.get("lint_manual_review") or item.get("lint_bookend_intensity")
    ]
    return sorted(flagged, key=lambda item: item["item_id"])


def _print_lint_report(index: Mapping[str, Any]) -> None:
    flagged = lint_flagged_items(index)
    print(f"lint-flagged items: {len(flagged)} / {len(index['items'])}")
    for item in flagged:
        name = item.get("name_base") or item.get("name_raw")
        label = f"[{item['library_key']}] {name} (id={item['item_id']})"
        duration_claim = item.get("lint_duration_claim")
        if duration_claim:
            print(
                f"  {label}: lint_duration_claim -- claims ~{duration_claim['claimed_min']:.0f}min "
                f"('{duration_claim['claim_text']}'), authored {duration_claim['authored_min']}min "
                f"({duration_claim['rel_diff']:.0%} off)"
            )
        manual = item.get("lint_manual_review")
        if manual:
            print(f"  {label}: lint_manual_review -- {manual['reason']}")
        rpe_conflict = item.get("lint_rpe_conflict")
        if rpe_conflict:
            print(
                f"  {label}: lint_rpe_conflict -- title RPE{rpe_conflict['title_rpe']} vs "
                f"body RPE{rpe_conflict['body_rpe']} (gap {rpe_conflict['gap']})"
            )
        bookend = item.get("lint_bookend_intensity")
        if bookend:
            offenders = ", ".join(
                f"{o['block']} {o['target_pct']}%" for o in bookend["offenders"])
            print(
                f"  {label}: lint_bookend_intensity -- {offenders} vs main-set max "
                f"{bookend['main_max_pct']}%"
            )


def _print_reconcile_report(report: Mapping[str, Any]) -> None:
    for section in ("added", "removed", "changed"):
        print(f"{section}:")
        entries = report[section]
        if not entries:
            print("  none")
            continue
        for entry in entries:
            print(f"  {json.dumps(entry, sort_keys=True)}" if isinstance(entry, dict) else f"  {entry}")
    print(f"family_count: {report['family_count_old']} -> {report['family_count_new']}")


def main(argv: list[str] | None = None) -> int:
    """Build (default) or reconcile (--reconcile) the TP library snapshot index."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "raw_path",
        nargs="?",
        type=Path,
        default=DEFAULT_RAW_PATH,
        help=f"path to the raw TP library dump (default: {DEFAULT_RAW_PATH})",
    )
    parser.add_argument(
        "--out", type=Path, default=DEFAULT_INDEX_PATH, help="index path: write target, or reconcile target"
    )
    parser.add_argument(
        "--extra-exclusions",
        type=Path,
        default=None,
        help="JSON sidecar: a list of item_ids, or of {item_id, reason} objects, to exclude "
        "(e.g. C2 structure round-trip failures discovered downstream)",
    )
    parser.add_argument(
        "--reconcile",
        action="store_true",
        help="compare a fresh raw dump against the existing index at --out and print drift",
    )
    parser.add_argument(
        "--lint-report",
        action="store_true",
        help="print every T27 lint-flagged item in the existing index at --out and exit "
        "(does not rebuild the index)",
    )
    args = parser.parse_args(argv)

    if args.lint_report:
        _print_lint_report(read_index(args.out))
        return 0

    extra_exclusions = _load_extra_exclusions_file(args.extra_exclusions)

    if args.reconcile:
        report = reconcile(args.raw_path, args.out, extra_exclusions=extra_exclusions)
        _print_reconcile_report(report)
        return 1 if (report["added"] or report["removed"] or report["changed"]) else 0

    index = build_index(args.raw_path, extra_exclusions=extra_exclusions)
    write_index(index, args.out)
    _print_summary(index)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
