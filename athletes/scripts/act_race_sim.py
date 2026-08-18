"""Race-fact-aware, Act-structured long-ride simulations.

The block builder owns the calendar, ride day, and duration budget.  This
module only composes the *contents* of eligible build/peak long rides.  It is
deliberately fact-conservative: terrain and altitude language is emitted only
when those facts are present in ``target_race`` / ``race_metadata``.

DEMAND-UNIT DESIGN (docs/SPEC_DEMAND_UNIT_COMPOSER.md, Aug 17 2026 coach
mandate): every Act sim is ONE demand unit -- the crux shape of the race,
keyed off ``climbing_emphasis`` -- repeated over a long Z2 spine.  Only the
unit COUNT and the SPACING between units change across a series; the unit's
own power/duration never do.  A "repo-NP" (duration-weighted 4th-power mean,
same formula as generate_plan_preview.py's IF calc) intensity ceiling is the
structural belief guard: it is what stops a sim from creeping toward "as hard
as the race" for an athlete who doesn't have the CTL to absorb it.

D6 (curated race-matched sims): three races have a hand-built TP library
series (Natty Specific, Black Canyon (Waffles), Leather Bound) that takes
precedence over the composer -- see ``RACE_SIM_SERIES`` and
``resolve_race_sim_series``.  Every other race composes from race facts.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import html


@dataclass(frozen=True)
class RaceFacts:
    """Facts the intake snapshot actually supplied for a race."""

    distance_miles: Optional[float] = None
    elevation_ft: Optional[float] = None
    altitude_asl_ft: Optional[float] = None

    @property
    def climbing_ft_per_mile(self) -> Optional[float]:
        if self.distance_miles and self.distance_miles > 0 and self.elevation_ft is not None:
            return self.elevation_ft / self.distance_miles
        return None

    @property
    def high_altitude(self) -> bool:
        return bool(self.altitude_asl_ft and self.altitude_asl_ft >= 5000)

    @property
    def climbing_emphasis(self) -> str:
        """Use route density, not a race-name guess, to set the unit shape.

        Big Sugar's roughly 62 ft/mi is intentionally in the ``flat`` band:
        meaningful rolling gain, but not a sustained-climb race.
        """
        density = self.climbing_ft_per_mile
        if density is None:
            return "unknown"
        if density >= 100:
            return "high"
        if density >= 75:
            return "moderate"
        return "flat"


def _number(value: Any) -> Optional[float]:
    if isinstance(value, bool) or value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def race_facts_from_profile(profile: Dict[str, Any]) -> RaceFacts:
    """Extract only snapshot/profile facts; no name lookup or invented data."""
    race = (profile or {}).get("target_race") or {}
    metadata = race.get("race_metadata") or {}
    altitude_values = [
        _number(metadata.get(key))
        for key in ("start_elevation_feet", "avg_elevation_feet", "asl_feet",
                    "start_elevation_asl_ft", "avg_elevation_asl_ft", "altitude_asl_ft")
    ]
    altitude_values = [value for value in altitude_values if value is not None]
    return RaceFacts(
        distance_miles=_number(race.get("distance_miles", race.get("distance_mi"))),
        elevation_ft=_number(race.get("elevation_ft", race.get("elevation_feet"))),
        altitude_asl_ft=max(altitude_values) if altitude_values else None,
    )


def is_act_sim_eligible(phase: str, week_type: str, role: str) -> bool:
    """Build and peak load-week long rides become Act simulations."""
    return phase in {"build", "peak"} and week_type == "load" and role == "long_ride"


def act_sim_title(index: int, total: int, dress_rehearsal: bool = False) -> str:
    suffix = " — Dress Rehearsal" if dress_rehearsal else ""
    return f"Race Simulation — Act {index} of {total}{suffix}"


def _append_steady(segments: List[Dict[str, Any]], seconds: int, power: float,
                   label: str, cadence: Optional[int] = None) -> None:
    if seconds <= 0:
        return
    segments.append({"kind": "steady", "seconds": int(seconds), "power": power,
                     "label": label, "cadence": cadence})


def _append_intervals(segments: List[Dict[str, Any]], repeat: int,
                      on_seconds: int, on_power: float, off_seconds: int,
                      off_power: float, label: str) -> None:
    if repeat <= 0:
        return
    segments.append({"kind": "intervals", "repeat": repeat,
                     "on_seconds": on_seconds, "on_power": on_power,
                     "off_seconds": off_seconds, "off_power": off_power,
                     "label": label})


def composed_if(segments: List[Dict[str, Any]]) -> float:
    """Duration-weighted 4th-power mean over ``segments`` (repo-NP/IF).

    Same math as generate_plan_preview.py's IF calc (a duration-weighted
    4th-power mean of each sampled effort) -- reimplemented locally (not
    imported) so this module stays free of the preview's heavier import
    surface.  D3's belief guard is expressed entirely in these units.
    """
    total_seconds = 0
    weighted = 0.0
    for segment in segments:
        if segment["kind"] == "intervals":
            on_total = segment["repeat"] * segment["on_seconds"]
            off_total = segment["repeat"] * segment["off_seconds"]
            total_seconds += on_total + off_total
            weighted += on_total * (segment["on_power"] ** 4)
            weighted += off_total * (segment["off_power"] ** 4)
        else:
            seconds = segment["seconds"]
            total_seconds += seconds
            weighted += seconds * (segment["power"] ** 4)
    if total_seconds <= 0:
        return 0.0
    return (weighted / total_seconds) ** 0.25


def _segment_duration(segment: Dict[str, Any]) -> int:
    if segment["kind"] == "intervals":
        return segment["repeat"] * (segment["on_seconds"] + segment["off_seconds"])
    return segment["seconds"]


# =============================================================================
# D1 — DEMAND UNIT DERIVATION
#
# One table, keyed on the existing climbing_emphasis property. Unit power and
# duration are fixed per emphasis and never change across a series -- only
# the unit COUNT and SPACING do (D2).
# =============================================================================

@dataclass(frozen=True)
class _UnitPiece:
    """One sequential (or repeated) leg of a demand unit."""

    seconds: int
    power: float
    band_lo_pct: float
    band_hi_pct: float
    tag: str


@dataclass(frozen=True)
class DemandUnit:
    emphasis: str
    unit_label: str
    is_rhythm: bool          # True for the flat/unknown 4x[...] compound unit
    pieces: Tuple[_UnitPiece, ...]
    unit_seconds: int


_HIGH_UNIT = DemandUnit(
    emphasis="high",
    unit_label="climb set: attack the base, sustain, tempo over the top",
    is_rhythm=False,
    pieces=(
        _UnitPiece(30, 1.23, 120, 127, "attack the base"),
        _UnitPiece(270, 1.10, 106, 113, "sustain the climb"),
        _UnitPiece(600, 0.85, 83, 88, "tempo over the top"),
    ),
    unit_seconds=30 + 270 + 600,
)

_MODERATE_UNIT = DemandUnit(
    emphasis="moderate",
    unit_label="climb set: attack the base, sustain, tempo over the top",
    is_rhythm=False,
    pieces=(
        _UnitPiece(30, 1.20, 116, 124, "attack the base"),
        _UnitPiece(180, 1.05, 102, 109, "sustain the climb"),
        _UnitPiece(480, 0.85, 83, 88, "tempo over the top"),
    ),
    unit_seconds=30 + 180 + 480,
)

_FLAT_UNIT = DemandUnit(
    emphasis="flat",
    unit_label="tempo rhythm with surges — race-pace texture on rough roads",
    is_rhythm=True,
    pieces=(
        _UnitPiece(170, 0.83, 76, 90, "tempo rhythm"),
        _UnitPiece(10, 1.65, 150, 180, "micro-surge"),
    ),
    unit_seconds=4 * (170 + 10),
)


def demand_unit(facts: RaceFacts) -> DemandUnit:
    """D1: the ONE unit shape for this race's crux demand.

    ``high``/``moderate`` climbing density gets the climb-set unit (attack /
    sustain / tempo-over-the-top); ``flat`` and ``unknown`` share the tempo-
    rhythm-with-surges unit -- fact-conservative, no invented terrain for an
    unknown course.
    """
    emphasis = facts.climbing_emphasis
    if emphasis == "high":
        return _HIGH_UNIT
    if emphasis == "moderate":
        return _MODERATE_UNIT
    return _FLAT_UNIT


def _unit_segments(unit: DemandUnit, rep_index: int) -> List[Dict[str, Any]]:
    """One repetition of ``unit`` as ZWO-ready segment dict(s)."""
    if unit.is_rhythm:
        on, off = unit.pieces
        return [{
            "kind": "intervals", "repeat": 4,
            "on_seconds": on.seconds, "on_power": on.power,
            "off_seconds": off.seconds, "off_power": off.power,
            "label": f"Unit {rep_index} — {unit.unit_label}",
        }]
    segments = []
    for piece in unit.pieces:
        segments.append({
            "kind": "steady", "seconds": piece.seconds, "power": piece.power,
            "label": f"Unit {rep_index} — {piece.tag}", "cadence": None,
        })
    return segments


# =============================================================================
# D2/D3 — DENSITY SCHEDULE + THE BELIEF GUARD
#
# Warm-up 15:00 @0.65, cooldown 10:00 @0.50; units(k) = 3 + k units of the
# fixed demand unit, hard-capped at 8; Z2 spacing 40:00 between units, except
# the final act tightens the LAST gap to 15:00 (the Natty 4 move); a single
# Z2 filler absorbs whatever's left to keep duration exact on whole minutes.
# The guard: while composing, add units only while composed repo-NP stays
# <= 0.77 (non-final) / <= 0.79 (final) -- if the next unit would exceed
# that, or drop spacing below 15:00 (never happens by construction here),
# the unit is not added.
# =============================================================================

_WARMUP_SECONDS = 15 * 60
_COOLDOWN_SECONDS = 10 * 60
_Z2_SPACING_SECONDS = 40 * 60
_Z2_TIGHT_SPACING_SECONDS = 15 * 60
_Z2_POWER = 0.66
_WARMUP_POWER = 0.65
_COOLDOWN_POWER = 0.50

GUARD_CEILING_NORMAL = 0.77
GUARD_CEILING_FINAL = 0.79
GUARD_IF_FLOOR = 0.68

_MAX_UNITS = 8


def _units_target(index: int) -> int:
    return min(_MAX_UNITS, 3 + max(0, index))


def _z2_filler_segments(filler_seconds: int, label_prefix: str = "Z2 spine") -> List[Dict[str, Any]]:
    """Split ``filler_seconds`` into a whole-minute Z2 block plus a <60s
    settle segment (same settle-remainder technique as before) so every
    Z2 spacer/filler segment other than the tiny remainder lands on a whole
    minute."""
    segments: List[Dict[str, Any]] = []
    if filler_seconds <= 0:
        return segments
    whole_minutes = (filler_seconds // 60) * 60
    remainder = filler_seconds - whole_minutes
    if whole_minutes:
        _append_steady(segments, whole_minutes, _Z2_POWER, f"{label_prefix} — fill")
    if remainder:
        _append_steady(segments, remainder, _Z2_POWER, f"{label_prefix} — settle")
    return segments


def _compose_with_units(n_units: int, is_final: bool, unit: DemandUnit,
                        total_seconds: int) -> Optional[List[Dict[str, Any]]]:
    """Full Act composition with exactly ``n_units`` units, or ``None`` if
    it doesn't fit ``total_seconds``."""
    if n_units < 1:
        return None
    gaps = []
    for i in range(n_units - 1):
        if is_final and i == n_units - 2:
            gaps.append(_Z2_TIGHT_SPACING_SECONDS)
        else:
            gaps.append(_Z2_SPACING_SECONDS)
    fixed = _WARMUP_SECONDS + _COOLDOWN_SECONDS + n_units * unit.unit_seconds + sum(gaps)
    filler = total_seconds - fixed
    if filler < 0:
        return None

    segments: List[Dict[str, Any]] = []
    _append_steady(segments, _WARMUP_SECONDS, _WARMUP_POWER, "Warm-up")
    for i in range(n_units):
        segments.extend(_unit_segments(unit, i + 1))
        if i < n_units - 1:
            _append_steady(segments, gaps[i], _Z2_POWER, f"Z2 spine {i + 1}")
    segments.extend(_z2_filler_segments(filler))
    _append_steady(segments, _COOLDOWN_SECONDS, _COOLDOWN_POWER, "Cooldown")
    return segments


def _compose_stats(duration_min: int, index: int, total: int, facts: RaceFacts) -> Dict[str, Any]:
    """The guarded composition for Act ``index`` of ``total``.

    Returns segments plus the bookkeeping (unit shape, units placed, total
    Z2 spine seconds) the description builder needs -- computed once so
    ``compose_act_simulation`` and ``act_sim_description`` never disagree.
    """
    # A direct/constrained caller is kept safe by a 120min floor -- normal
    # production long-ride budgets exceed it by a wide margin.
    total_seconds = max(120 * 60, int(round(duration_min)) * 60)
    unit = demand_unit(facts)
    is_final = index >= total
    ceiling = GUARD_CEILING_FINAL if is_final else GUARD_CEILING_NORMAL
    target_units = _units_target(index)

    chosen_segments: Optional[List[Dict[str, Any]]] = None
    chosen_n = 1
    for n in range(target_units, 0, -1):
        segments = _compose_with_units(n, is_final, unit, total_seconds)
        if segments is None:
            continue
        # Guard comparison at spec precision (0.769/0.787-style figures) --
        # the ceiling is a coaching intent, not a bit-exact float boundary.
        if round(composed_if(segments), 3) <= ceiling:
            chosen_segments = segments
            chosen_n = n
            break
    if chosen_segments is None:
        # The 120min floor guarantees n=1 always fits both duration and the
        # guard (a single unit diluted into a mostly-Z2 ride never gets
        # near either ceiling); this is the last-resort path.
        chosen_segments = _compose_with_units(1, is_final, unit, total_seconds)
        chosen_n = 1

    z2_seconds = sum(
        seg["seconds"] for seg in chosen_segments
        if seg["kind"] == "steady" and seg["power"] == _Z2_POWER
    )
    return {
        "segments": chosen_segments,
        "unit": unit,
        "n_units": chosen_n,
        "z2_seconds": z2_seconds,
        "is_final": is_final,
    }


def compose_act_simulation(duration_min: int, index: int, total: int,
                           facts: RaceFacts) -> List[Dict[str, Any]]:
    """Return exact-duration ZWO-ready segments for one demand-unit Act."""
    return _compose_stats(duration_min, index, total, facts)["segments"]


# =============================================================================
# D5 — DESCRIPTION REWRITE (product voice: professional, one wink max)
# =============================================================================

def _fmt_time(seconds: int) -> str:
    minutes, secs = divmod(int(seconds), 60)
    return f"{minutes}:{secs:02d}"


def _fmt_piece(piece: _UnitPiece, ftp: Optional[int]) -> str:
    band = f"{_fmt_time(piece.seconds)} @{int(piece.band_lo_pct)}-{int(piece.band_hi_pct)}%"
    if ftp:
        lo_w = round(piece.band_lo_pct / 100.0 * ftp)
        hi_w = round(piece.band_hi_pct / 100.0 * ftp)
        band += f" / {lo_w}-{hi_w}w"
    return f"{band} ({piece.tag})"


def _fmt_unit(unit: DemandUnit, ftp: Optional[int]) -> str:
    if unit.is_rhythm:
        pieces = " + ".join(_fmt_piece(p, ftp) for p in unit.pieces)
        return f"4x[{pieces}]"
    return " → ".join(_fmt_piece(p, ftp) for p in unit.pieces)


# Fact-conservative: RaceFacts carries no race NAME (only distance/elevation/
# altitude), so the description never invents one -- "the race" stands in
# for the spec's "{race name}" placeholder.
_EMPHASIS_CLAUSE = {
    "high": "attack the base of the climb, sustain it, then hold tempo over the top",
    "moderate": "attack a shorter climb, sustain it, then hold tempo over the top",
    "flat": "hold tempo on rough roads and answer sudden surges",
    "unknown": "hold tempo and answer sudden surges — no supplied climbing profile to shape this any other way",
}


def _altitude_line() -> str:
    return (
        "ALTITUDE: This route's supplied above-sea-level elevation is over "
        "5,000 ft. On the unit's hard efforts, ride to RPE rather than "
        "chasing home-altitude power."
    )


def _audible_line(unit: DemandUnit, n_units: int, dress_rehearsal: bool) -> str:
    if unit.is_rhythm:
        noun, terrain = "surges", "ride the tempo blocks steady"
    else:
        noun, terrain = "attacks", "ride the climbs at tempo"
    line = (
        f"AUDIBLE: if the legs are gone after unit {max(1, n_units - 1)}, "
        f"skip the remaining {noun} and {terrain} — then finish the Z2. "
        "The spine of this ride is the point."
    )
    if dress_rehearsal:
        line += "\nFueling practice continues at race rate no matter what you audible."
    return line


def _dress_rehearsal_block(race_rate_g_per_hour: Optional[float]) -> str:
    rate = f" ({round(race_rate_g_per_hour)}g carbs/hr)" if race_rate_g_per_hour else ""
    return (
        "DRESS REHEARSAL: Ride in race kit, on the race bike and tyre "
        f"pressure. Use race food at the ladder's race rate{rate}; nothing "
        "on race day should be new."
    )


_CLOSING_LINE = (
    "Ride the units at their targets; ride the spine disciplined and bored. "
    "Boredom is the skill."
)


def act_sim_description(index: int, total: int, facts: RaceFacts,
                        duration_min: int, dress_rehearsal: bool = False,
                        race_rate_g_per_hour: Optional[float] = None,
                        ftp: Optional[int] = None) -> str:
    """Coach-facing execution copy: THE UNIT, THE SHAPE, ALTITUDE, AUDIBLE,
    DRESS REHEARSAL (final act only)."""
    stats = _compose_stats(duration_min, index, total, facts)
    unit: DemandUnit = stats["unit"]
    n_units: int = stats["n_units"]
    z2_hours = round(stats["z2_seconds"] / 3600.0, 1)
    clause = _EMPHASIS_CLAUSE[facts.climbing_emphasis]

    sections = [
        f"RACE SIMULATION — ACT {index} OF {total}",
        (f"THE UNIT: {_fmt_unit(unit, ftp)} — this is the crux demand of "
         f"the race: {clause}."),
        (f"THE SHAPE: {n_units} units across {z2_hours}hr of Z2 — Act "
         f"{index} of {total}. Each act packs them tighter; race day is "
         "the only day you do the full count."),
    ]
    if facts.high_altitude:
        sections.append(_altitude_line())
    sections.append(_audible_line(unit, n_units, dress_rehearsal))
    if dress_rehearsal:
        sections.append(_dress_rehearsal_block(race_rate_g_per_hour))
    sections.append(_CLOSING_LINE)
    return "\n\n".join(sections)


def render_act_sim_zwo(*, workout_name: str, display_name: str,
                       duration_min: int, index: int, total: int,
                       facts: RaceFacts, author: str,
                       dress_rehearsal: bool = False,
                       race_rate_g_per_hour: Optional[float] = None,
                       ftp: Optional[int] = None) -> str:
    """Render an exact-duration Act sim as valid ZWO XML."""
    lines = []
    for segment in compose_act_simulation(duration_min, index, total, facts):
        label = html.escape(segment["label"], quote=True)
        if segment["kind"] == "intervals":
            lines.append(
                f'    <IntervalsT Repeat="{segment["repeat"]}" OnDuration="{segment["on_seconds"]}" '
                f'OnPower="{segment["on_power"]:.2f}" OffDuration="{segment["off_seconds"]}" '
                f'OffPower="{segment["off_power"]:.2f}" />')
        else:
            cadence = (f' Cadence="{segment["cadence"]}"'
                       if segment.get("cadence") else "")
            lines.append(
                f'    <SteadyState Duration="{segment["seconds"]}" Power="{segment["power"]:.2f}"{cadence} />'
                f'<!-- {label} -->')
    description = act_sim_description(index, total, facts, duration_min,
                                      dress_rehearsal, race_rate_g_per_hour, ftp)
    return f'''<?xml version='1.0' encoding='UTF-8'?>
<workout_file>
  <author>{html.escape(author)}</author>
  <name>{html.escape(display_name)}</name>
  <description>{html.escape(description)}</description>
  <sportType>bike</sportType>
  <workout>
{chr(10).join(lines)}
  </workout>
</workout_file>'''


# =============================================================================
# D6 — CURATED RACE-MATCHED SIMS TAKE PRECEDENCE (direct mapping, not the
# general selector)
#
# "Natty Specific 1-4" / "Black Canyon (Waffles)" / "Leather Bound" are
# hand-built TP library series that don't parse into a family ladder the
# general selector could drive (singleton name_bases -- no leading dash
# before the digit -- or shared name_bases across 4 distinct items). The
# standing invariant "act_simulation days never reach the selector" stays
# true; this is a direct race_id -> item-name lookup in the ACT PATH.
# Values are the item's ``name_raw`` (unique per item) from
# athletes/config/tp_library_index.json.gz, verified at test time against
# the checked-in index.
# =============================================================================

RACE_SIM_SERIES: Dict[str, Tuple[str, ...]] = {
    # USA Cycling Gravel Nationals (snapshot slug, discipline prefix
    # stripped -- see intake_to_plan.py's target_race.race_id assignment).
    "usa-cycling-gravel-nationals": (
        "Natty Specific 1 - 4hr (4x5 VO2)",
        "Natty Specific 2 - 4hr (full climb set)",
        "Natty Specific 3 - 5hr (full climb set)",
        "Natty Specific 4 - 5hr Dress Rehearsal (6 climbs)",
    ),
    # Black Canyon (Waffles): the coach named this series in the Aug 17
    # mandate ("I have other sims in the workout library, like Leather
    # Bound") but no race by this name exists yet in known_races.py or the
    # 1,185-race snapshot (config/races.json) -- verified during this
    # implementation. Seeded per the spec's literal instruction; this entry
    # is currently unreachable (no profile can ever carry this race_id)
    # until a matching race is added to the database. Flagged for coach
    # review.
    "black_canyon": (
        "Race Sim - Black Canyon (Waffles) - 1 - 180min - RPE6-7",
        "Race Sim - Black Canyon (Waffles) - 2 - 225min - RPE6-7",
        "Race Sim - Black Canyon (Waffles) - 3 - 240min - RPE6-7",
        "Race Sim - Black Canyon (Waffles) - 4 - 255min - RPE6-7",
    ),
    "unbound_gravel_200": (
        "Durability - Leather Bound - 1 - 128min - RPE6-7",
        "Durability - Leather Bound - 2 - 203min - RPE6-7",
        "Durability - Leather Bound - 3 - 278min - RPE6-7",
        "Durability - Leather Bound - 4 - 361min - RPE6-7",
    ),
}


def resolve_race_sim_series(race_id: Optional[str], index: int, total: int,
                            day_cap_min: Optional[float] = None,
                            index_data: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """D6: direct race_id -> curated TP library item for Act ``index`` of ``total``.

    Returns a resolution dict shaped like ``library_selector.select()``'s
    (item_id, name_base, library_key, duration_min, tss, if_planned,
    structure, description) or ``None`` when there's no series entry for
    this race, the named item doesn't resolve to exactly one index item, or
    the item's authored duration exceeds ``day_cap_min`` by more than 15%
    (the caller falls back to the composer for that act and should record
    it in the D9-style fallback report).

    Entry selection: ``round(index * len(names) / total)`` (1-based entry
    number), with the last act explicitly forced to the last entry.
    """
    if not race_id:
        return None
    names = RACE_SIM_SERIES.get(race_id)
    if not names:
        return None

    entry_number = round(index * len(names) / max(1, total))
    entry_number = max(1, min(len(names), entry_number))
    if index >= total:
        entry_number = len(names)
    name = names[entry_number - 1]

    from tp_library_snapshot import load_index
    idx = index_data if index_data is not None else load_index()
    matches = [item for item in idx["items"] if item.get("name_raw") == name]
    if len(matches) != 1:
        return None
    item = matches[0]

    item_duration = item.get("duration_min")
    if day_cap_min and item_duration and item_duration > day_cap_min * 1.15:
        return None

    return {
        "item_id": item["item_id"],
        "name_base": item["name_base"],
        "library_key": item["library_key"],
        "duration_min": item["duration_min"],
        "tss": item["tss"],
        "if_planned": item["if_planned"],
        "structure": item["structure"],
        "description": item["description"],
        "dimension_score": item.get("dimension_score"),
    }


# =============================================================================
# D7 — MIDWEEK (COMPRESSED) RACE SIMULATION
#
# compose_act_simulation refuses to render under a 120min floor -- it owns
# the long-ride slot, where that floor is correct. A "Race Simulation" bb_name
# also gets selected onto ordinary midweek intensity slots (intensity_1/2/3
# in build/peak/race_prep, ~45-90min) via workout_selection.yaml. This
# composer keeps the SAME demand unit as the long-ride Acts, sized to a
# normal midweek quality-day budget: warm-up + 2 units + Z2 spine +
# cooldown, same IF guard band, dropping to 1 unit under a 45min budget.
# =============================================================================

_MIDWEEK_TIGHT_BUDGET_MIN = 45


def _midweek_warmup_cooldown(total_seconds: int) -> Tuple[int, int]:
    warmup = min(600, max(300, (int(total_seconds * 0.10) // 60) * 60))
    cooldown = min(480, max(300, (int(total_seconds * 0.08) // 60) * 60))
    return warmup, cooldown


def _compose_midweek_with_units(n_units: int, unit: DemandUnit, total_seconds: int,
                                warmup_seconds: int, cooldown_seconds: int) -> Optional[List[Dict[str, Any]]]:
    if n_units < 1:
        return None
    gap = _Z2_SPACING_SECONDS if n_units >= 2 else 0
    gaps = [gap] * max(0, n_units - 1)
    fixed = warmup_seconds + cooldown_seconds + n_units * unit.unit_seconds + sum(gaps)
    filler = total_seconds - fixed
    if filler < 0:
        return None

    segments: List[Dict[str, Any]] = []
    _append_steady(segments, warmup_seconds, _WARMUP_POWER, "Warm-up")
    for i in range(n_units):
        segments.extend(_unit_segments(unit, i + 1))
        if i < n_units - 1:
            _append_steady(segments, gaps[i], _Z2_POWER, f"Z2 spine {i + 1}")
    segments.extend(_z2_filler_segments(filler))
    _append_steady(segments, cooldown_seconds, _COOLDOWN_POWER, "Cooldown")
    return segments


def _compose_midweek_stats(duration_min: int, facts: RaceFacts) -> Dict[str, Any]:
    total_seconds = max(30 * 60, int(round(duration_min)) * 60)
    unit = demand_unit(facts)
    warmup_seconds, cooldown_seconds = _midweek_warmup_cooldown(total_seconds)
    target_units = 1 if total_seconds < _MIDWEEK_TIGHT_BUDGET_MIN * 60 else 2

    chosen_segments: Optional[List[Dict[str, Any]]] = None
    chosen_n = 1
    for n in range(target_units, 0, -1):
        segments = _compose_midweek_with_units(n, unit, total_seconds, warmup_seconds, cooldown_seconds)
        if segments is None:
            continue
        if round(composed_if(segments), 3) <= GUARD_CEILING_NORMAL:
            chosen_segments = segments
            chosen_n = n
            break
    if chosen_segments is None:
        # The 30min floor guarantees n=1 fits even the largest single unit
        # (900s/15min, the high-emphasis climb set) alongside a minimal
        # warm-up/cooldown.
        chosen_segments = _compose_midweek_with_units(1, unit, total_seconds, warmup_seconds, cooldown_seconds)
        chosen_n = 1

    z2_seconds = sum(
        seg["seconds"] for seg in chosen_segments
        if seg["kind"] == "steady" and seg["power"] == _Z2_POWER
    )
    return {"segments": chosen_segments, "unit": unit, "n_units": chosen_n, "z2_seconds": z2_seconds}


def compose_midweek_sim(duration_min: int, facts: RaceFacts) -> List[Dict[str, Any]]:
    """Return exact-duration ZWO-ready segments for a compressed midweek sim."""
    return _compose_midweek_stats(duration_min, facts)["segments"]


def midweek_sim_description(facts: RaceFacts, duration_min: int,
                            ftp: Optional[int] = None) -> str:
    """Coach-facing execution copy for the compressed midweek rehearsal."""
    stats = _compose_midweek_stats(duration_min, facts)
    unit: DemandUnit = stats["unit"]
    n_units: int = stats["n_units"]
    clause = _EMPHASIS_CLAUSE[facts.climbing_emphasis]

    sections = [
        "RACE SIMULATION — MIDWEEK",
        (f"THE UNIT: {_fmt_unit(unit, ftp)} — this is the crux demand of "
         f"the race: {clause}."),
    ]
    if facts.high_altitude:
        sections.append(_altitude_line())
    sections.append(_audible_line(unit, n_units, dress_rehearsal=False))
    sections.append(
        "Same unit as your long-ride simulations, compressed for a "
        "midweek slot: ride the unit at its targets, ride the spine "
        "disciplined and bored."
    )
    return "\n\n".join(sections)


def render_midweek_sim_zwo(*, workout_name: str, display_name: str,
                           duration_min: int, facts: RaceFacts, author: str,
                           ftp: Optional[int] = None) -> str:
    """Render an exact-duration compressed midweek sim as valid ZWO XML."""
    lines = []
    for segment in compose_midweek_sim(duration_min, facts):
        label = html.escape(segment["label"], quote=True)
        if segment["kind"] == "intervals":
            lines.append(
                f'    <IntervalsT Repeat="{segment["repeat"]}" OnDuration="{segment["on_seconds"]}" '
                f'OnPower="{segment["on_power"]:.2f}" OffDuration="{segment["off_seconds"]}" '
                f'OffPower="{segment["off_power"]:.2f}" />')
        else:
            cadence = (f' Cadence="{segment["cadence"]}"' if segment.get("cadence") else "")
            lines.append(
                f'    <SteadyState Duration="{segment["seconds"]}" Power="{segment["power"]:.2f}"{cadence} />'
                f'<!-- {label} -->')
    description = midweek_sim_description(facts, duration_min, ftp)
    return f'''<?xml version='1.0' encoding='UTF-8'?>
<workout_file>
  <author>{html.escape(author)}</author>
  <name>{html.escape(display_name)}</name>
  <description>{html.escape(description)}</description>
  <sportType>bike</sportType>
  <workout>
{chr(10).join(lines)}
  </workout>
</workout_file>'''
