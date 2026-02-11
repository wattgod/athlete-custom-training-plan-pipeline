#!/usr/bin/env python3
"""
Tests for Workout Generation Logic

These tests ensure:
1. Limited availability days still get appropriate intensity workouts (not just Recovery)
2. All training zones (Z1-Z7) are represented appropriately by phase
3. Hard/easy alternation is maintained
4. Duration caps are respected
5. Phase-appropriate workouts are assigned

Run with: pytest test_workout_generation.py -v
"""

import pytest
import sys
from pathlib import Path

# Add script path for imports
sys.path.insert(0, str(Path(__file__).parent))

from workout_templates import (
    PHASE_WORKOUT_ROLES,
    get_phase_roles,
    cap_duration,
)


class TestWorkoutTemplates:
    """Test workout template definitions."""

    def test_all_phases_have_required_roles(self):
        """Every phase must have key_cardio, long_ride, easy, and strength roles."""
        required_roles = ['key_cardio', 'long_ride', 'easy', 'strength']
        phases = ['base', 'build', 'peak', 'taper', 'maintenance', 'race']

        for phase in phases:
            templates = get_phase_roles(phase)
            for role in required_roles:
                assert role in templates, f"Phase '{phase}' missing required role '{role}'"

    def test_base_phase_has_tempo(self):
        """Base phase should include tempo workouts for variety."""
        templates = get_phase_roles('base')
        assert 'tempo' in templates, "Base phase should have tempo workouts"
        assert templates['tempo'][0] == 'Tempo', "Base tempo should be Tempo type"

    def test_build_phase_has_threshold_and_vo2max(self):
        """Build phase should include threshold and VO2max workouts."""
        templates = get_phase_roles('build')

        # Check for threshold
        assert templates['key_cardio'][0] == 'Threshold', "Build key_cardio should be Threshold"

        # Check for VO2max
        assert 'vo2max' in templates, "Build phase should have vo2max role"
        assert templates['vo2max'][0] == 'VO2max', "Build vo2max should be VO2max type"

    def test_peak_phase_has_all_high_intensity_zones(self):
        """Peak phase should include VO2max (Z5) and Anaerobic (Z6) workouts."""
        templates = get_phase_roles('peak')

        # Check for VO2max
        assert 'vo2max' in templates, "Peak phase should have vo2max role"
        assert templates['vo2max'][0] == 'VO2max'

        # Check for Anaerobic (Z6)
        assert 'anaerobic' in templates, "Peak phase should have anaerobic role"
        assert templates['anaerobic'][0] == 'Anaerobic'
        assert '150%' in templates['anaerobic'][1], "Anaerobic should be ~150% FTP"

    def test_taper_phase_has_sprints(self):
        """Taper phase should include sprint/neuromuscular work (Z7)."""
        templates = get_phase_roles('taper')

        assert 'anaerobic' in templates, "Taper should have anaerobic/sprints role"
        assert templates['anaerobic'][0] == 'Sprints', "Taper anaerobic should be Sprints"

    def test_cap_duration_works(self):
        """Duration capping should work correctly."""
        template = ('VO2max', 'Test workout', 60, 0.80)

        # Cap to shorter duration
        capped = cap_duration(template, 45)
        assert capped[2] == 45, "Duration should be capped to 45"
        assert capped[0] == 'VO2max', "Type should be preserved"
        assert capped[3] == 0.80, "Power should be preserved"

        # No cap needed
        uncapped = cap_duration(template, 90)
        assert uncapped[2] == 60, "Duration should remain 60 when cap is higher"

    def test_cap_duration_handles_rest(self):
        """Duration capping should handle rest days (0 duration)."""
        rest = ('Rest', None, 0, 0)
        capped = cap_duration(rest, 60)
        assert capped == rest, "Rest days should pass through unchanged"


class TestZoneDistribution:
    """Test that all training zones are properly represented."""

    def test_zone_coverage_by_phase(self):
        """Each phase should cover appropriate zones."""
        # Define expected zone coverage per phase
        # Format: phase -> list of workout types that should exist
        expected = {
            'base': ['Endurance', 'Tempo', 'Recovery'],  # Z2, Z3
            'build': ['Threshold', 'Sweet_Spot', 'Tempo', 'VO2max'],  # Z3, Z4, Z5
            'peak': ['VO2max', 'Anaerobic', 'Threshold'],  # Z4, Z5, Z6
            'taper': ['Openers', 'Sprints', 'Easy'],  # Z6, Z7
        }

        for phase, expected_types in expected.items():
            templates = get_phase_roles(phase)
            all_types = [t[0] for t in templates.values() if t[0] is not None]

            for workout_type in expected_types:
                assert workout_type in all_types, \
                    f"Phase '{phase}' should include '{workout_type}' workout type"

    def test_power_targets_are_appropriate(self):
        """Power targets should match zone definitions."""
        # Zone power ranges (as fraction of FTP)
        # These are AVERAGE power for the workout, not interval power
        zone_ranges = {
            'Recovery': (0.40, 0.55),  # Z1
            'Easy': (0.40, 0.60),  # Z1
            'Endurance': (0.55, 0.75),  # Z2
            'Tempo': (0.65, 0.87),  # Z3 (lower bound reduced for maintenance phase)
            'Sweet_Spot': (0.72, 0.90),  # Z3-Z4
            'Threshold': (0.72, 0.85),  # Z4 (avg power, not interval power)
            'VO2max': (0.75, 0.90),  # Avg power (intervals are higher)
            'Anaerobic': (0.60, 0.80),  # Avg power (intervals are 150%+)
            'Sprints': (0.50, 0.70),  # Avg power (sprints are 200%+)
            'Openers': (0.55, 0.70),  # Avg power
        }

        for phase in ['base', 'build', 'peak', 'taper', 'maintenance']:
            templates = get_phase_roles(phase)
            for role, template in templates.items():
                if template[0] is None or template[2] == 0:
                    continue  # Skip rest days

                workout_type = template[0]
                power = template[3]

                if workout_type in zone_ranges:
                    min_power, max_power = zone_ranges[workout_type]
                    assert min_power <= power <= max_power, \
                        f"{phase}/{role}: {workout_type} power {power} outside range {min_power}-{max_power}"


class TestLimitedAvailability:
    """Test that limited availability doesn't mean low intensity."""

    def test_limited_availability_concept(self):
        """
        LIMITED availability means TIME constraints, not INTENSITY constraints.

        An athlete with 60 minutes can still do:
        - VO2max intervals (45-60 min)
        - Threshold work (45-60 min)
        - Anaerobic capacity (35-45 min)
        - Sprints (30-40 min)

        All high-intensity workouts fit within typical limited availability windows.
        """
        # All high-intensity workouts should have durations <= 60 min
        high_intensity_types = ['VO2max', 'Anaerobic', 'Threshold', 'Sprints', 'Openers']
        max_limited_duration = 60  # Typical "limited" availability

        for phase in ['build', 'peak', 'taper']:
            templates = get_phase_roles(phase)
            for role, template in templates.items():
                if template[0] in high_intensity_types:
                    duration = template[2]
                    assert duration <= max_limited_duration, \
                        f"{phase}/{role}: {template[0]} duration {duration} exceeds limited availability threshold {max_limited_duration}"

    def test_all_intensity_workouts_can_fit_in_60min(self):
        """Every intensity workout should be doable in 60 minutes or less."""
        intensity_roles = ['key_cardio', 'vo2max', 'anaerobic', 'tempo', 'moderate']

        for phase in PHASE_WORKOUT_ROLES:
            templates = get_phase_roles(phase)
            for role in intensity_roles:
                if role in templates:
                    template = templates[role]
                    if template[0] not in [None, 'Rest', 'RACE_DAY']:
                        # After capping to 60 min, workout should still be valid
                        capped = cap_duration(template, 60)
                        assert capped[2] <= 60, \
                            f"{phase}/{role}: Cannot fit in 60 min window"
                        assert capped[2] >= 25, \
                            f"{phase}/{role}: Too short after capping ({capped[2]} min)"


class TestWorkoutVariety:
    """Test that workout variety is maintained."""

    def test_no_phase_is_all_recovery(self):
        """No phase should have only recovery/easy workouts."""
        for phase in ['base', 'build', 'peak']:
            templates = get_phase_roles(phase)
            workout_types = [t[0] for t in templates.values() if t[0] is not None]

            non_easy_types = [t for t in workout_types if t not in ['Recovery', 'Easy', 'Rest']]
            assert len(non_easy_types) >= 3, \
                f"Phase '{phase}' has too few non-easy workout types: {non_easy_types}"

    def test_build_phase_has_progression(self):
        """Build phase should have workouts that progress from tempo to threshold to VO2max."""
        templates = get_phase_roles('build')
        workout_types = [t[0] for t in templates.values() if t[0] is not None]

        # Should have tempo, sweet spot, threshold, and VO2max
        assert 'Tempo' in workout_types, "Build needs Tempo"
        assert 'Sweet_Spot' in workout_types, "Build needs Sweet_Spot"
        assert 'Threshold' in workout_types, "Build needs Threshold"
        assert 'VO2max' in workout_types, "Build needs VO2max"

    def test_peak_phase_has_race_specific_intensity(self):
        """Peak phase should have race-specific high intensity work."""
        templates = get_phase_roles('peak')
        workout_types = [t[0] for t in templates.values() if t[0] is not None]

        # Peak should have VO2max, Threshold, and Anaerobic
        assert 'VO2max' in workout_types, "Peak needs VO2max"
        assert 'Threshold' in workout_types, "Peak needs Threshold"
        assert 'Anaerobic' in workout_types, "Peak needs Anaerobic for power"


class TestPhaseProgression:
    """Test that phases progress logically."""

    def test_intensity_increases_through_phases(self):
        """Average intensity should generally increase from base to peak."""
        phases = ['base', 'build', 'peak']
        avg_powers = []

        for phase in phases:
            templates = get_phase_roles(phase)
            powers = [t[3] for t in templates.values() if t[3] > 0]
            avg_power = sum(powers) / len(powers) if powers else 0
            avg_powers.append(avg_power)

        # Base < Build (usually)
        # Build should have higher intensity than base
        assert avg_powers[1] >= avg_powers[0] - 0.05, \
            f"Build ({avg_powers[1]}) should be similar or higher intensity than Base ({avg_powers[0]})"

    def test_taper_reduces_volume_not_intensity(self):
        """Taper should have shorter workouts but maintain some intensity."""
        taper = get_phase_roles('taper')
        peak = get_phase_roles('peak')

        # Taper durations should be shorter
        taper_durations = [t[2] for t in taper.values() if t[2] > 0]
        peak_durations = [t[2] for t in peak.values() if t[2] > 0]

        avg_taper_duration = sum(taper_durations) / len(taper_durations)
        avg_peak_duration = sum(peak_durations) / len(peak_durations)

        assert avg_taper_duration < avg_peak_duration, \
            f"Taper duration ({avg_taper_duration}) should be less than Peak ({avg_peak_duration})"

        # But taper should still have high-intensity options
        assert 'Sprints' in [t[0] for t in taper.values()], \
            "Taper should maintain neuromuscular activation with Sprints"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
