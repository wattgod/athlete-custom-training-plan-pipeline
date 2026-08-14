"""Deterministic E1 pre/post immutable-ID selection proof corpus."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

from archetype_registry import ALL_ARCHETYPES, get_archetype
from nate_workout_generator import select_archetype_for_workout
from workout_mapper import WORKOUT_MAP, _resolve_for_discipline


METHODOLOGY_RENDER_STYLES = {
    "time_crunched": "POLARIZED",
    "g_spot": "G_SPOT",
    "polarized_80_20": "POLARIZED",
    "traditional_pyramidal": "PYRAMIDAL",
}
REACHABLE_PHASES = ("base", "build", "race_prep", "racing")
DISCIPLINES = ("gravel", "road", "mtb")
PINNED = {"Openers", "FTP Test", "Rest Day", "Endurance with Surges",
          "NP/IF Target", "Race Simulation", "Kitchen Sink - Drain Cleaner",
          "La Balanguera", "Hyttevask", "Thunder Quads", "Blood Pistons"}


@dataclass(frozen=True)
class SelectionCase:
    methodology_id: str
    render_style: str
    discipline: str
    phase: str
    workout_type: str
    base_variation: int
    variation_offset: int
    level: int

    @property
    def filename(self) -> str:
        safe = self.workout_type.replace(" ", "_").replace("/", "_")
        return (f"proof_{self.methodology_id}_{self.discipline}_{self.phase}_"
                f"{safe}_b{self.base_variation}_o{self.variation_offset}_"
                f"L{self.level}.zwo")


def _selection(name: str, discipline: str, style: str, offset: int):
    mapping = _resolve_for_discipline(name, discipline)
    if mapping is None or name == "Endurance":
        return None
    nate_type, base = mapping
    variation = base if name in PINNED else base + offset
    selected = select_archetype_for_workout(nate_type, style, variation)
    if selected is None and style != "POLARIZED":
        selected = select_archetype_for_workout(nate_type, "POLARIZED", variation)
    return selected


def projected_filename(case: SelectionCase, selected: dict) -> str:
    """Exercise the athlete-visible filename projection on both sides.

    Immutable archetype identity is deliberately not part of the Phase 3
    filename.  Requiring a resolved selection here prevents the proof from
    accidentally comparing filenames for unreachable tuples.
    """
    if not selected or not selected.get("name"):
        raise ValueError("reachable selection required for filename projection")
    return case.filename


def iter_reachable_selection_cases() -> Iterator[SelectionCase]:
    """Enumerate the closed tuple corpus, including offset N wrap."""
    for methodology_id, render_style in METHODOLOGY_RENDER_STYLES.items():
        for discipline in DISCIPLINES:
            for phase in REACHABLE_PHASES:
                for workout_type in WORKOUT_MAP:
                    if workout_type == "Endurance":
                        continue  # Appendix 8 non-native, outside ID migration.
                    mapping = _resolve_for_discipline(workout_type, discipline)
                    selected = _selection(workout_type, discipline, render_style, 0)
                    if mapping is None or selected is None:
                        continue
                    category, _ = get_archetype(selected["name"])
                    base_variation = mapping[1]
                    for variation_offset in range(len(ALL_ARCHETYPES[category]) + 1):
                        for level in range(1, 7):
                            yield SelectionCase(
                                methodology_id, render_style, discipline, phase,
                                workout_type, base_variation, variation_offset, level)


def selection_case_count() -> int:
    return sum(1 for _ in iter_reachable_selection_cases())
