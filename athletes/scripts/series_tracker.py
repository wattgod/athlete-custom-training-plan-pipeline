#!/usr/bin/env python3
"""
Series Tracker — enforces workout series coherence across blocks.

Block-builder rule: same workout TYPE (exact name) across load weeks in a block,
progresses according to AE-4.1's one-lever rule: the level either repeats when
volume is the progression lever or advances by one when intensity is the lever.
Recovery weeks have NO series progression.

"Same type" means the EXACT same workout name (minus level number).
- VO2max 30/30 and VO2max 40/20 are DIFFERENT types
- Kitchen Sink variants are ONE family (Drain Cleaner → La Balanguera is valid)

Source: block-builder SKILL.md Step 6, compliance-rules.md R14
"""

from typing import Dict, List, Optional, Any


# Kitchen Sink family — all interchangeable for coherence purposes
KITCHEN_SINK_FAMILY = {
    'Kitchen Sink - Drain Cleaner',
    'La Balanguera 1', 'La Balanguera 2', 'La Balanguera 3',
    'Hyttevask 1', 'Hyttevask 2', 'Hyttevask 3',
    'Kjokkenvask - De Tre Sostre', 'Kjokkenvask - Svake Knaer',
    'Haarsaar 1', 'Rema Tusen 1',
}


def _normalize_for_coherence(name: str) -> str:
    """Normalize workout name for series coherence comparison.

    Kitchen Sink variants all normalize to 'Kitchen Sink'.
    Everything else keeps its exact name.
    """
    if name in KITCHEN_SINK_FAMILY:
        return 'Kitchen Sink'
    return name


class SeriesTracker:
    """Tracks workout series across blocks for coherence enforcement.

    Usage:
        tracker = SeriesTracker()

        # Block 1
        tracker.start_block()
        tracker.assign('intensity_1', 'VO2max 30/30', level=2)  # Week 1
        tracker.advance_week()
        tracker.assign('intensity_1', 'VO2max 30/30', level=3)  # Week 2 (+1)
        tracker.end_block()

        # Block 2 — tracker knows intensity_1 was VO2max 30/30 ending at L3
        tracker.start_block()
        tracker.assign('intensity_1', 'VO2max 30/30', level=3)  # Continue
    """

    def __init__(self):
        # slot_name → {'name': str, 'last_level': int}
        self._active_series: Dict[str, Dict[str, Any]] = {}
        # History of completed blocks
        self._block_history: List[Dict[str, Any]] = []
        self._current_block: List[Dict[str, Any]] = []
        self._week_in_block: int = 0
        self._expected_delta: int = 1

    def start_block(self):
        """Begin a new 3-week block."""
        self._current_block = []
        self._week_in_block = 0
        self._expected_delta = 1

    def advance_week(self, level_delta: int = 1):
        """Move to next week and record the AE-4.1 level delta."""
        self._week_in_block += 1
        self._expected_delta = level_delta

    def end_block(self):
        """Complete the current block and save history."""
        if self._current_block:
            self._block_history.append({
                'assignments': list(self._current_block),
                'series': dict(self._active_series),
            })

    def assign(self, slot: str, name: str, level: int) -> Dict[str, Any]:
        """Assign a workout to a slot and check coherence.

        Returns dict with:
            name: str — the workout name
            level: int — the level (possibly adjusted)
            coherent: bool — whether this follows series rules
            note: str — explanation if not coherent
        """
        result = {
            'name': name,
            'level': level,
            'coherent': True,
            'note': '',
        }

        norm_name = _normalize_for_coherence(name)

        if slot in self._active_series:
            prev = self._active_series[slot]
            prev_norm = _normalize_for_coherence(prev['name'])

            # Check same series
            if norm_name != prev_norm:
                result['coherent'] = False
                result['note'] = (
                    f"Series break: {slot} was '{prev['name']}', "
                    f"now '{name}'. Should be same type across load weeks."
                )

            # Check level progression according to the active one-lever
            # delta.  A level ceiling at 6 remains a valid plateau.
            expected_level = prev['last_level'] + self._expected_delta
            if level != expected_level and self._week_in_block > 0:
                if level < prev['last_level']:
                    result['note'] += f" Level decreased ({prev['last_level']}→{level})."
                else:
                    result['note'] += (
                        f" Level delta +{level - prev['last_level']} "
                        f"(expected +{self._expected_delta}).")
                # Auto-correct to expected if within range
                if 1 <= expected_level <= 6:
                    result['level'] = expected_level

        # Update tracker
        self._active_series[slot] = {
            'name': name,
            'last_level': result['level'],
        }
        self._current_block.append({
            'slot': slot,
            'name': name,
            'level': result['level'],
            'week': self._week_in_block,
            'expected_delta': self._expected_delta,
        })

        return result

    def get_next_level(self, slot: str, max_level: int = 6) -> int:
        """Get the expected next level for a slot's series.

        For a new block, returns last_level from previous block.
        For continuing within a block, returns last_level + 1.
        """
        if slot not in self._active_series:
            return 1  # New series starts at L1

        last = self._active_series[slot]['last_level']
        next_level = (
            last + self._expected_delta
            if self._week_in_block > 0 else last
        )
        return min(next_level, max_level)

    def get_series_name(self, slot: str) -> Optional[str]:
        """Get the current series name for a slot, or None if not started."""
        if slot in self._active_series:
            return self._active_series[slot]['name']
        return None

    def validate_block(self) -> List[str]:
        """Validate current block for series coherence violations.

        Returns list of violation descriptions (empty = clean).
        """
        violations = []
        # Group assignments by slot
        slot_assignments = {}
        for a in self._current_block:
            slot_assignments.setdefault(a['slot'], []).append(a)

        for slot, assignments in slot_assignments.items():
            if len(assignments) < 2:
                continue

            # Check all assignments use the same series
            names = [_normalize_for_coherence(a['name']) for a in assignments]
            if len(set(names)) > 1:
                violations.append(
                    f"Series break in {slot}: {[a['name'] for a in assignments]}"
                )

            # Check level progression (level ceiling at 6 is not a violation).
            levels = [a['level'] for a in assignments]
            for i in range(1, len(levels)):
                delta = levels[i] - levels[i - 1]
                expected_delta = assignments[i].get('expected_delta', 1)
                if levels[i - 1] >= 6 and levels[i] == 6:
                    continue
                if delta != expected_delta:
                    violations.append(
                        f"Level progression in {slot}: {levels} "
                        f"(expected +{expected_delta})"
                    )
                    break

        return violations
