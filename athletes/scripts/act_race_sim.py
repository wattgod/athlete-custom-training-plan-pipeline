"""Race-fact-aware, Act-structured long-ride simulations.

The block builder owns the calendar, ride day, and duration budget.  This
module only composes the *contents* of eligible build/peak long rides.  It is
deliberately fact-conservative: terrain and altitude language is emitted only
when those facts are present in ``target_race`` / ``race_metadata``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
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
        """Use route density, not a race-name guess, to set Act 2 emphasis.

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


def compose_act_simulation(duration_min: int, index: int, total: int,
                           facts: RaceFacts) -> List[Dict[str, Any]]:
    """Return exact-duration ZWO-ready segments for the three coach Acts."""
    total_seconds = max(120 * 60, int(duration_min) * 60)
    progression = max(0, index - 1)
    high_altitude = facts.high_altitude

    # Act 1 is deliberately punchy.  Longer/later simulations add attacks,
    # while a low-climbing race keeps that opening emphasis rather than
    # pretending it has long mountain grinds.
    attack_count = min(6, 3 + progression + (1 if facts.climbing_emphasis == "flat" else 0))
    attack_seconds = attack_count * 90
    # Attacks contain legitimate 20/30/40s work. Keep the *long* Z2 pieces
    # on whole minutes so the generated athlete description never says a
    # distracting "65:30" endurance segment.
    act1_short_settle = (60 - attack_seconds % 60) % 60
    # Warm-up, high-cadence Z3, 30/30s, attacks/holds, then settle.
    act1_seconds = (2 * 600) + (5 * 60) + attack_seconds + 600 + act1_short_settle
    pyramid_count = 2 if duration_min >= 285 or index >= 3 else 1
    act3_seconds = pyramid_count * 15 * 60 + max(0, pyramid_count - 1) * 5 * 60
    cooldown_seconds = 10 * 60
    act2_seconds = total_seconds - act1_seconds - act3_seconds - cooldown_seconds

    # Preserve every Act even for constrained long-day budgets.  Normal
    # production long rides exceed this floor; it prevents malformed negative
    # segments in direct callers and keeps the composition coherent.
    if act2_seconds < 35 * 60:
        act3_seconds = 15 * 60
        act2_seconds = max(35 * 60, total_seconds - act1_seconds - act3_seconds - cooldown_seconds)
        cooldown_seconds = max(5 * 60, total_seconds - act1_seconds - act2_seconds - act3_seconds)

    if facts.climbing_emphasis == "high":
        climb_minutes = 20 + min(8, progression * 2)
        climb_power = 0.80
    elif facts.climbing_emphasis == "moderate":
        climb_minutes = 16 + min(6, progression * 2)
        climb_power = 0.77
    else:  # flat or no supplied ratio: short, controlled climb exposure
        climb_minutes = 10 + min(4, progression * 2)
        climb_power = 0.74
    if high_altitude:
        climb_minutes += 4
        climb_power = min(0.80, climb_power + 0.01)

    climb_seconds = climb_minutes * 60
    # A later/higher-budget sim grows the number of Act 2 grind blocks.  Z2
    # fills the rest of the allotted budget, keeping total time exact.
    grind_count = max(1, min(3, act2_seconds // max(1, (40 * 60 + climb_seconds))))
    while grind_count > 1 and act2_seconds // grind_count <= climb_seconds + 20 * 60:
        grind_count -= 1
    z2_per_grind = max(
        20 * 60,
        ((act2_seconds - grind_count * climb_seconds) // grind_count // 60) * 60,
    )
    assigned_act2 = grind_count * (z2_per_grind + climb_seconds)
    remainder = max(0, act2_seconds - assigned_act2)

    segments: List[Dict[str, Any]] = []
    _append_steady(segments, 10 * 60, 0.58, "Warm-up")
    _append_steady(segments, 10 * 60, 0.82, "Part 1 — high-cadence Z3", cadence=105)
    _append_intervals(segments, 5, 30, 1.20, 30, 0.50, "Part 1 — 30/30s")
    for _ in range(attack_count):
        _append_steady(segments, 20, 1.60, "Part 1 — short attack")
        _append_steady(segments, 30, 1.08, "Part 1 — hard hold")
        _append_steady(segments, 40, 0.55, "Part 1 — reset")
    _append_steady(segments, 10 * 60, 0.65, "Part 1 — settle")
    _append_steady(segments, act1_short_settle, 0.65, "Part 1 — settle into the grind")

    for block in range(int(grind_count)):
        _append_steady(segments, z2_per_grind, 0.68,
                       f"Part 2 — Z2 grind {block + 1}")
        _append_steady(segments, climb_seconds, climb_power,
                       f"Part 2 — seated low-cadence climb {block + 1}", cadence=55)
    _append_steady(segments, remainder, 0.68, "Part 2 — Z2 to finale")

    for pyramid in range(pyramid_count):
        for power in (0.80, 0.90, 1.00, 0.90, 0.80):
            _append_steady(segments, 3 * 60, power,
                           f"Part 3 — tired-legs pyramid {pyramid + 1}")
        if pyramid + 1 < pyramid_count:
            _append_steady(segments, 5 * 60, 0.65, "Part 3 — pyramid reset")
    _append_steady(segments, cooldown_seconds, 0.50, "Cooldown")

    # Keep the caller's duration budget exact.  Under normal long-ride budgets
    # this is zero; the guard makes a direct constrained caller safe too.
    delta = total_seconds - sum(
        item.get("seconds", 0) if item["kind"] == "steady"
        else item["repeat"] * (item["on_seconds"] + item["off_seconds"])
        for item in segments)
    if delta:
        _append_steady(segments, delta, 0.68, "Part 2 — Z2 to duration")
    return segments


def act_sim_description(index: int, total: int, facts: RaceFacts,
                        dress_rehearsal: bool = False,
                        race_rate_g_per_hour: Optional[float] = None) -> str:
    """Coach-facing execution copy that names all Acts without invented facts."""
    climb_line = {
        "high": "The course density supports long seated climbs: make each low-cadence block patient and unbroken.",
        "moderate": "The course carries sustained climbing: keep the low-cadence blocks smooth rather than muscling them.",
        "flat": "This is a rolling course: keep Part 1 punchy and make the low-cadence blocks short, controlled strength work.",
        "unknown": "Use the supplied route facts, not a made-up terrain story: keep Part 2 controlled and repeatable.",
    }[facts.climbing_emphasis]
    altitude_line = ""
    if facts.high_altitude:
        altitude_line = (
            "\n\nALTITUDE: This route's supplied above-sea-level elevation is over 5,000 ft. "
            "On the seated grinds, ride to RPE rather than chasing home-altitude power."
        )
    rehearsal_line = ""
    if dress_rehearsal:
        rate = f" ({round(race_rate_g_per_hour)}g carbs/hr)" if race_rate_g_per_hour else ""
        rehearsal_line = (
            "\n\nDRESS REHEARSAL: Ride in race kit, on the race bike and tyre pressure. "
            f"Use race food at the ladder's race rate{rate}; nothing on race day should be new."
        )
    return (
        f"RACE SIMULATION — ACT {index} OF {total}\n\n"
        "PART 1 — punchy start: high-cadence Z3, 30/30s, then short attacks and hard holds.\n"
        "PART 2 — the grind: long Z2 blocks, each ending in a 50-60 rpm seated climbing block.\n"
        "PART 3 — finale: 3-minute pyramid steps at 80/90/100/90/80% on tired legs, then Z2 to the cooldown.\n\n"
        f"{climb_line}{altitude_line}{rehearsal_line}\n\n"
        "Ride Parts 1 and 3 at their targets; ride Part 2 disciplined and bored. Boredom is the skill."
    )


def render_act_sim_zwo(*, workout_name: str, display_name: str,
                       duration_min: int, index: int, total: int,
                       facts: RaceFacts, author: str,
                       dress_rehearsal: bool = False,
                       race_rate_g_per_hour: Optional[float] = None) -> str:
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
    description = act_sim_description(index, total, facts, dress_rehearsal,
                                      race_rate_g_per_hour)
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
