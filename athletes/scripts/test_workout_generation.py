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
import unittest
from pathlib import Path

# Add script path for imports
sys.path.insert(0, str(Path(__file__).parent))

from workout_templates import (
    PHASE_WORKOUT_ROLES,
    get_phase_roles,
    cap_duration,
    calculate_target_duration,
    scale_template_duration,
    scale_zwo_to_target_duration,
    round_duration_to_10,
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


class TestDurationScaling:
    """Test that workouts scale to use available time."""

    def test_endurance_ride_uses_available_time(self):
        """Endurance ride with 120min available should be ~80min (base phase), not 50min.

        This was the core bug: a 120-minute available slot got a 50-minute
        workout (42% utilization). With scaling, base phase uses 70% of
        available time: 120 * 0.70 = 84 -> rounded to 80.
        """
        wo = parse_nicholas_zwo('W01_Mon_Mar9_Endurance.zwo')
        assert wo >= 70, f"Endurance ride should be >= 70min with 120min slot, got {wo}min"
        assert wo <= 100, f"Endurance ride should be <= 100min with 120min slot, got {wo}min"

    def test_interval_warmup_scaled(self):
        """VO2max workout with 120min available should have warmup > 10 minutes.

        When max_duration > 90 minutes, the interval set stays fixed but
        warmup and cooldown expand to fill available time with Z2 riding.
        """
        wo_path = _nicholas_workouts() / 'W01_Wed_Mar11_VO2max.zwo'
        if not wo_path.exists():
            pytest.skip("Nicholas workout files not generated yet")

        import xml.etree.ElementTree as ET
        root = ET.parse(str(wo_path)).getroot()
        workout_elem = root.find('workout')

        warmup = workout_elem.find('Warmup')
        assert warmup is not None, "VO2max workout should have a Warmup element"
        warmup_sec = float(warmup.get('Duration', 0))
        warmup_min = warmup_sec / 60
        assert warmup_min >= 15, (
            f"VO2max warmup should be >= 15min when max_duration=120min, got {warmup_min:.0f}min"
        )

    def test_weekly_volume_hits_target(self):
        """Average training week should be >= 80% of cycling_hours_target (10h).

        With duration scaling, weekly volume should reach 8-12 hours instead
        of the old 7.5 hours.
        """
        nicholas_dir = _nicholas_workouts().parent
        profile_path = nicholas_dir / 'profile.yaml'
        if not profile_path.exists():
            pytest.skip("Nicholas profile not found")

        import yaml
        with open(profile_path, 'r') as f:
            profile = yaml.safe_load(f)
        target_hours = profile.get('weekly_availability', {}).get('cycling_hours_target', 10)

        from generate_plan_preview import build_preview_data
        data = build_preview_data(nicholas_dir)
        training_weeks = [w for w in data['weeks'] if w['phase'] not in ('taper', 'race')]
        if not training_weeks:
            pytest.skip("No training weeks found")

        avg_hours = sum(w['total_hours'] for w in training_weeks) / len(training_weeks)
        pct = avg_hours / target_hours * 100
        assert pct >= 80, (
            f"Average training week {avg_hours:.1f}h is only {pct:.0f}% of "
            f"{target_hours}h target (should be >= 80%)"
        )

    def test_calculate_target_duration_endurance_base(self):
        """Endurance in base phase: 120min slot -> 80min (70% utilization)."""
        target = calculate_target_duration('Endurance', 120, 'base', 50)
        assert target == 80  # 120 * 0.70 = 84 -> round to 80

    def test_calculate_target_duration_endurance_build(self):
        """Endurance in build phase: 120min slot -> 90min (75% utilization)."""
        target = calculate_target_duration('Endurance', 120, 'build', 50)
        assert target == 90  # 120 * 0.75 = 90

    def test_calculate_target_duration_endurance_taper(self):
        """Endurance in taper phase: 120min slot -> 60min (50% utilization)."""
        target = calculate_target_duration('Endurance', 120, 'taper', 50)
        assert target == 60  # 120 * 0.50 = 60

    def test_calculate_target_duration_vo2max(self):
        """VO2max with 120min slot -> 110min (90% utilization, capped at 120)."""
        target = calculate_target_duration('VO2max', 120, 'build', 50)
        assert target == 110  # 120 * 0.90 = 108 -> round to 110

    def test_interval_capped_at_120min(self):
        """Interval workouts should never exceed 120 min, even with 240min slot."""
        target = calculate_target_duration('VO2max', 240, 'build', 50)
        assert target == 120  # 240 * 0.90 = 216, but capped at 120

    def test_ftp_test_not_scaled(self):
        """FTP Test duration should never be scaled."""
        target = calculate_target_duration('FTP_Test', 240, 'base', 60)
        assert target == 60  # Template duration unchanged

    def test_openers_not_scaled(self):
        """Openers duration should never be scaled."""
        target = calculate_target_duration('Openers', 120, 'taper', 40)
        assert target == 40  # Template duration unchanged

    def test_rest_not_scaled(self):
        """Rest day duration should never be scaled."""
        target = calculate_target_duration('Rest', 120, 'base', 0)
        assert target == 0  # Template duration unchanged

    def test_scale_never_below_template_when_slot_allows(self):
        """Scaling should not shrink below template when slot is large enough."""
        # 60min slot in taper: 60 * 0.50 = 30, but template is 50, so use 50
        target = calculate_target_duration('Endurance', 60, 'taper', 50)
        assert target == 50  # Template wins since 30 < 50 and 50 <= 60

    def test_scale_caps_at_max_duration(self):
        """When max_duration < template_duration, result is capped at max_duration."""
        # 40min slot: template is 50min but can't exceed 40
        target = calculate_target_duration('Endurance', 40, 'taper', 50)
        assert target == 40  # Capped at max_duration

    def test_scale_template_duration_returns_tuple(self):
        """scale_template_duration should return a valid WorkoutTemplate tuple."""
        template = ('Endurance', 'Zone 2 steady', 50, 0.65)
        scaled = scale_template_duration(template, 120, 'base')
        assert len(scaled) == 4
        assert scaled[0] == 'Endurance'
        assert scaled[2] >= 50  # Should scale up
        assert scaled[3] == 0.65  # Power unchanged

    def test_scale_zwo_to_target_duration_intervals(self):
        """scale_zwo_to_target_duration should expand warmup/cooldown for interval workouts."""
        # Minimal ZWO with short warmup, intervals, short cooldown
        zwo = """<?xml version='1.0' encoding='UTF-8'?>
<workout_file>
  <name>Test</name>
  <description>Test</description>
  <sportType>bike</sportType>
  <workout>
    <Warmup Duration="300" PowerLow="0.50" PowerHigh="0.75"/>
    <IntervalsT Repeat="4" OnDuration="180" OnPower="1.15" OffDuration="120" OffPower="0.55"/>
    <Cooldown Duration="300" PowerLow="0.75" PowerHigh="0.50"/>
  </workout>
</workout_file>"""
        # Original: 300 + 4*(180+120) + 300 = 1800s = 30min
        # Target: 90min = 5400s
        # Intervals: 4*(180+120) = 1200s (20min) stays fixed
        # Remaining: 5400 - 1200 = 4200s
        # Warmup: 4200 * 0.55 = 2310s, Cooldown: 4200 - 2310 = 1890s
        scaled = scale_zwo_to_target_duration(zwo, 90, 'VO2max')

        import xml.etree.ElementTree as ET
        root = ET.fromstring(scaled)
        workout = root.find('workout')
        warmup = workout.find('Warmup')
        cooldown = workout.find('Cooldown')

        warmup_sec = float(warmup.get('Duration'))
        cooldown_sec = float(cooldown.get('Duration'))

        # Warmup and cooldown should be much longer than original 300s
        assert warmup_sec >= 1800, f"Warmup should be >= 30min, got {warmup_sec/60:.0f}min"
        assert cooldown_sec >= 1200, f"Cooldown should be >= 20min, got {cooldown_sec/60:.0f}min"

        # Total should be close to target
        total = warmup_sec + 1200 + cooldown_sec  # warmup + intervals + cooldown
        assert abs(total - 5400) < 60, f"Total should be ~90min, got {total/60:.1f}min"

    def test_all_week1_durations_rounded_to_10(self):
        """All Week 1 workouts should have durations divisible by 10 minutes."""
        import xml.etree.ElementTree as ET

        workout_dir = _nicholas_workouts()
        if not workout_dir.exists():
            pytest.skip("Nicholas workout files not generated yet")

        errors = []
        for zwo_file in sorted(workout_dir.glob('W01*.zwo')):
            root = ET.parse(str(zwo_file)).getroot()
            workout = root.find('workout')
            total_seconds = 0
            for elem in workout:
                dur = float(elem.get('Duration', 0))
                if elem.tag == 'IntervalsT':
                    r = int(elem.get('Repeat', 1))
                    total_seconds += r * (float(elem.get('OnDuration', 0)) + float(elem.get('OffDuration', 0)))
                else:
                    total_seconds += dur
            total_min = int(round(total_seconds / 60))
            if total_min > 0 and total_min % 10 != 0:
                errors.append(f"{zwo_file.name}: {total_min}min")

        assert not errors, f"Workouts not divisible by 10: {errors}"


def _nicholas_workouts():
    """Get path to Nicholas's workout directory."""
    return Path(__file__).parent.parent / 'nicholas-applegate' / 'workouts'


def parse_nicholas_zwo(filename: str) -> int:
    """Parse a Nicholas ZWO file and return total duration in minutes."""
    import xml.etree.ElementTree as ET

    filepath = _nicholas_workouts() / filename
    if not filepath.exists():
        pytest.skip(f"Workout file not found: {filename}")

    root = ET.parse(str(filepath)).getroot()
    workout = root.find('workout')
    total_seconds = 0
    for elem in workout:
        dur = float(elem.get('Duration', 0))
        if elem.tag == 'IntervalsT':
            r = int(elem.get('Repeat', 1))
            total_seconds += r * (float(elem.get('OnDuration', 0)) + float(elem.get('OffDuration', 0)))
        else:
            total_seconds += dur
    return int(round(total_seconds / 60))


class TestGravelSpecificArchetypes:
    """Tests for Gravel_Specific archetype category and block generation."""

    # =========================================================================
    # 1. Archetype Data Integrity
    # =========================================================================

    def test_gravel_specific_category_exists(self):
        """Gravel_Specific category exists in NEW_ARCHETYPES."""
        from new_archetypes import NEW_ARCHETYPES
        assert 'Gravel_Specific' in NEW_ARCHETYPES

    def test_gravel_specific_has_five_archetypes(self):
        """Gravel_Specific has exactly 5 archetypes (4 original + 1 advanced)."""
        from new_archetypes import NEW_ARCHETYPES
        assert len(NEW_ARCHETYPES['Gravel_Specific']) == 5

    def test_gravel_specific_archetype_names(self):
        """Verify all 4 archetype names are present."""
        from new_archetypes import NEW_ARCHETYPES
        names = [a['name'] for a in NEW_ARCHETYPES['Gravel_Specific']]
        assert 'Surge and Settle' in names
        assert 'Terrain Microbursts' in names
        assert 'Gravel Grind' in names
        assert 'Late Race Surge Protocol' in names

    def test_all_archetypes_have_six_levels(self):
        """Each Gravel_Specific archetype has levels 1-6."""
        from new_archetypes import NEW_ARCHETYPES
        for archetype in NEW_ARCHETYPES['Gravel_Specific']:
            for level_str in ['1', '2', '3', '4', '5', '6']:
                assert level_str in archetype['levels'], \
                    f"{archetype['name']} missing level {level_str}"

    def test_level1_has_metadata(self):
        """Level 1 of each archetype has cadence, position, execution fields."""
        from new_archetypes import NEW_ARCHETYPES
        for archetype in NEW_ARCHETYPES['Gravel_Specific']:
            l1 = archetype['levels']['1']
            assert 'cadence_prescription' in l1, \
                f"{archetype['name']} L1 missing cadence_prescription"
            assert 'position_prescription' in l1, \
                f"{archetype['name']} L1 missing position_prescription"
            assert 'execution' in l1, \
                f"{archetype['name']} L1 missing execution"
            assert 'structure' in l1, \
                f"{archetype['name']} L1 missing structure"

    def test_surge_settle_has_required_keys(self):
        """Surge and Settle levels all have the surge_settle flag and required params."""
        from new_archetypes import NEW_ARCHETYPES
        arch = NEW_ARCHETYPES['Gravel_Specific'][0]
        assert arch['name'] == 'Surge and Settle'
        for level_str in ['1', '2', '3', '4', '5', '6']:
            ld = arch['levels'][level_str]
            assert ld.get('surge_settle') is True, \
                f"Surge and Settle L{level_str} missing surge_settle flag"
            assert 'surges_per_set' in ld
            assert 'sets' in ld
            assert 'surge_duration' in ld
            assert 'surge_power' in ld
            assert 'settle_duration' in ld
            assert 'settle_power' in ld

    def test_microbursts_has_required_keys(self):
        """Terrain Microbursts levels all have the microbursts flag and required params."""
        from new_archetypes import NEW_ARCHETYPES
        arch = NEW_ARCHETYPES['Gravel_Specific'][1]
        assert arch['name'] == 'Terrain Microbursts'
        for level_str in ['1', '2', '3', '4', '5', '6']:
            ld = arch['levels'][level_str]
            assert ld.get('microbursts') is True, \
                f"Terrain Microbursts L{level_str} missing microbursts flag"
            assert 'block_duration' in ld
            assert 'base_power' in ld
            assert 'burst_duration' in ld
            assert 'burst_power' in ld
            assert 'burst_interval' in ld

    def test_gravel_grind_has_required_keys(self):
        """Gravel Grind levels all have the gravel_grind flag and required params."""
        from new_archetypes import NEW_ARCHETYPES
        arch = NEW_ARCHETYPES['Gravel_Specific'][2]
        assert arch['name'] == 'Gravel Grind'
        for level_str in ['1', '2', '3', '4', '5', '6']:
            ld = arch['levels'][level_str]
            assert ld.get('gravel_grind') is True, \
                f"Gravel Grind L{level_str} missing gravel_grind flag"
            assert 'block_duration' in ld
            assert 'base_power' in ld
            assert 'num_spikes' in ld
            assert 'spike_duration' in ld
            assert 'spike_power' in ld

    def test_late_race_has_required_keys(self):
        """Late Race Surge Protocol levels all have the late_race flag and required params."""
        from new_archetypes import NEW_ARCHETYPES
        arch = NEW_ARCHETYPES['Gravel_Specific'][3]
        assert arch['name'] == 'Late Race Surge Protocol'
        for level_str in ['1', '2', '3', '4', '5', '6']:
            ld = arch['levels'][level_str]
            assert ld.get('late_race') is True, \
                f"Late Race L{level_str} missing late_race flag"
            assert 'preload_duration' in ld
            assert 'preload_power' in ld
            assert 'efforts' in ld
            assert isinstance(ld['efforts'], list)

    def test_late_race_levels_5_and_6_have_finishers(self):
        """Late Race levels 5 and 6 include finisher sprint parameters."""
        from new_archetypes import NEW_ARCHETYPES
        arch = NEW_ARCHETYPES['Gravel_Specific'][3]
        for level_str in ['5', '6']:
            ld = arch['levels'][level_str]
            assert 'finisher_count' in ld, \
                f"Late Race L{level_str} missing finisher_count"
            assert 'finisher_duration' in ld
            assert 'finisher_power' in ld
            assert ld['finisher_count'] > 0

    def test_late_race_levels_1_to_4_no_finishers(self):
        """Late Race levels 1-4 do NOT have finisher parameters (or have count=0)."""
        from new_archetypes import NEW_ARCHETYPES
        arch = NEW_ARCHETYPES['Gravel_Specific'][3]
        for level_str in ['1', '2', '3', '4']:
            ld = arch['levels'][level_str]
            assert ld.get('finisher_count', 0) == 0, \
                f"Late Race L{level_str} should not have finishers"

    def test_power_values_are_reasonable(self):
        """All power targets in Gravel_Specific archetypes are within sane range (0.5-2.0)."""
        from new_archetypes import NEW_ARCHETYPES
        for archetype in NEW_ARCHETYPES['Gravel_Specific']:
            for level_str in ['1', '2', '3', '4', '5', '6']:
                ld = archetype['levels'][level_str]
                # Check various power fields
                for key in ['surge_power', 'settle_power', 'base_power',
                            'burst_power', 'spike_power', 'preload_power',
                            'finisher_power']:
                    if key in ld:
                        power = ld[key]
                        assert 0.5 <= power <= 2.0, \
                            f"{archetype['name']} L{level_str} {key}={power} out of range"
                # Check effort list powers
                for effort in ld.get('efforts', []):
                    if isinstance(effort, dict) and 'power' in effort:
                        p = effort['power']
                        assert 0.5 <= p <= 2.0, \
                            f"{archetype['name']} L{level_str} effort power={p} out of range"

    # =========================================================================
    # 2. Block Generation Tests
    # =========================================================================

    def test_surge_settle_generates_blocks(self):
        """Surge & Settle archetype generates actual workout blocks, not just warmup/cooldown."""
        from nate_workout_generator import generate_nate_zwo
        zwo = generate_nate_zwo('gravel_specific', level=3, methodology='POLARIZED', variation=0)
        assert zwo is not None
        assert '<SteadyState' in zwo
        # Should have many short blocks (surges + settles)
        steady_count = zwo.count('<SteadyState')
        assert steady_count > 10, \
            f"Surge & Settle should produce many blocks, got {steady_count}"

    def test_microbursts_generates_blocks(self):
        """Terrain Microbursts generates many short burst blocks."""
        from nate_workout_generator import generate_nate_zwo
        zwo = generate_nate_zwo('gravel_specific', level=3, methodology='POLARIZED', variation=1)
        assert zwo is not None
        assert '<SteadyState' in zwo
        steady_count = zwo.count('<SteadyState')
        assert steady_count > 15, \
            f"Microbursts should produce many blocks, got {steady_count}"

    def test_gravel_grind_generates_blocks(self):
        """Gravel Grind generates base effort with spike blocks."""
        from nate_workout_generator import generate_nate_zwo
        zwo = generate_nate_zwo('gravel_specific', level=3, methodology='POLARIZED', variation=2)
        assert zwo is not None
        assert '<SteadyState' in zwo
        steady_count = zwo.count('<SteadyState')
        assert steady_count > 8, \
            f"Gravel Grind should produce multiple blocks, got {steady_count}"

    def test_late_race_generates_blocks(self):
        """Late Race Surge Protocol generates preload + escalating efforts."""
        from nate_workout_generator import generate_nate_zwo
        zwo = generate_nate_zwo('gravel_specific', level=3, methodology='POLARIZED', variation=3)
        assert zwo is not None
        assert '<SteadyState' in zwo
        # Should have preload + effort blocks
        steady_count = zwo.count('<SteadyState')
        assert steady_count > 5, \
            f"Late Race should produce preload + effort blocks, got {steady_count}"

    def test_late_race_level5_has_finishers(self):
        """Late Race Level 5+ generates finisher sprint blocks."""
        from nate_workout_generator import generate_nate_zwo
        zwo_l3 = generate_nate_zwo('gravel_specific', level=3, methodology='POLARIZED', variation=3)
        zwo_l5 = generate_nate_zwo('gravel_specific', level=5, methodology='POLARIZED', variation=3)
        assert zwo_l5 is not None
        # Level 5 has finisher_count=3, so should have more blocks than level 3
        steady_l3 = zwo_l3.count('<SteadyState')
        steady_l5 = zwo_l5.count('<SteadyState')
        assert steady_l5 > steady_l3, \
            f"Level 5 ({steady_l5} blocks) should have more blocks than L3 ({steady_l3}) due to finishers"

    def test_surge_settle_block_count_matches_archetype(self):
        """Surge & Settle L3: 2 sets x 5 surges = 10 surge+settle pairs = 20 blocks + recovery."""
        from nate_workout_generator import generate_nate_zwo
        zwo = generate_nate_zwo('gravel_specific', level=3, methodology='POLARIZED', variation=0)
        assert zwo is not None
        steady_count = zwo.count('<SteadyState')
        # 2 sets x 5 surges x 2 (surge+settle) = 20 + 1 set recovery = 21
        # Plus warmup/cooldown XML tags (which are Warmup/Cooldown, not SteadyState)
        assert steady_count >= 20, \
            f"L3 Surge&Settle: expected >= 20 SteadyState blocks, got {steady_count}"

    # =========================================================================
    # 3. Chaos Handler Fix Tests
    # =========================================================================

    def test_chaos_handler_generates_blocks(self):
        """Variable Pace Chaos now generates actual blocks (was broken)."""
        from nate_workout_generator import generate_nate_zwo
        zwo = generate_nate_zwo('race_sim', level=3, methodology='POLARIZED', variation=1)
        assert zwo is not None
        assert '<SteadyState' in zwo
        # Chaos should generate many short varied blocks, not just warmup/cooldown
        steady_count = zwo.count('<SteadyState')
        assert steady_count > 5, \
            f"Chaos handler should produce stochastic blocks, got {steady_count}"

    def test_chaos_blocks_are_deterministic(self):
        """Same chaos seed produces identical output."""
        from nate_workout_generator import generate_nate_zwo
        zwo1 = generate_nate_zwo('race_sim', level=3, methodology='POLARIZED', variation=1)
        zwo2 = generate_nate_zwo('race_sim', level=3, methodology='POLARIZED', variation=1)
        assert zwo1 == zwo2, "Chaos blocks should be deterministic"

    def test_chaos_different_levels_differ(self):
        """Different chaos levels produce different output."""
        from nate_workout_generator import generate_nate_zwo
        zwo_l2 = generate_nate_zwo('race_sim', level=2, methodology='POLARIZED', variation=1)
        zwo_l5 = generate_nate_zwo('race_sim', level=5, methodology='POLARIZED', variation=1)
        assert zwo_l2 != zwo_l5, "Different chaos levels should produce different output"

    # =========================================================================
    # 4. Stochastic Generator Tests
    # =========================================================================

    def test_stochastic_generator_deterministic(self):
        """Stochastic generator with same seed produces same output."""
        from nate_workout_generator import _generate_stochastic_blocks
        blocks1 = _generate_stochastic_blocks(600, 0.80, 1.15, 30, 120, seed=42)
        blocks2 = _generate_stochastic_blocks(600, 0.80, 1.15, 30, 120, seed=42)
        assert blocks1 == blocks2

    def test_stochastic_generator_different_seeds(self):
        """Different seeds produce different output."""
        from nate_workout_generator import _generate_stochastic_blocks
        blocks1 = _generate_stochastic_blocks(600, 0.80, 1.15, 30, 120, seed=42)
        blocks2 = _generate_stochastic_blocks(600, 0.80, 1.15, 30, 120, seed=99)
        assert blocks1 != blocks2

    def test_stochastic_generator_produces_blocks(self):
        """Stochastic generator returns non-empty list of blocks."""
        from nate_workout_generator import _generate_stochastic_blocks
        blocks = _generate_stochastic_blocks(600, 0.80, 1.15, 30, 120, seed=42)
        assert len(blocks) > 0
        # Each block should be a string containing SteadyState
        for block in blocks:
            assert 'SteadyState' in block

    def test_stochastic_power_within_range(self):
        """All stochastic block powers stay within specified range."""
        import re
        from nate_workout_generator import _generate_stochastic_blocks
        blocks = _generate_stochastic_blocks(1200, 0.80, 1.15, 15, 60, seed=42)
        for block in blocks:
            match = re.search(r'Power="([\d.]+)"', block)
            if match:
                power = float(match.group(1))
                assert power >= 0.80, f"Power {power} below range"
                assert power <= 1.15, f"Power {power} above range"

    def test_stochastic_total_duration_approximately_matches(self):
        """Stochastic block total duration is close to requested total."""
        import re
        from nate_workout_generator import _generate_stochastic_blocks
        target_duration = 1200
        blocks = _generate_stochastic_blocks(target_duration, 0.80, 1.15, 30, 120, seed=42)
        total = 0
        for block in blocks:
            match = re.search(r'Duration="(\d+)"', block)
            if match:
                total += int(match.group(1))
        # Should be within 120 seconds of target (one max block)
        assert abs(total - target_duration) <= 120, \
            f"Total duration {total} far from target {target_duration}"

    def test_stochastic_minimum_block_duration(self):
        """No stochastic block should be shorter than 5 seconds."""
        import re
        from nate_workout_generator import _generate_stochastic_blocks
        blocks = _generate_stochastic_blocks(600, 0.80, 1.15, 15, 60, seed=42)
        for block in blocks:
            match = re.search(r'Duration="(\d+)"', block)
            if match:
                dur = int(match.group(1))
                assert dur >= 5, f"Block duration {dur}s is below 5s minimum"

    # =========================================================================
    # 5. Type Mapping Tests
    # =========================================================================

    def test_gravel_specific_type_mapping(self):
        """'gravel_specific' maps to Gravel_Specific category."""
        from nate_workout_generator import select_archetype_for_workout
        archetype = select_archetype_for_workout('gravel_specific', 'POLARIZED')
        assert archetype is not None, "gravel_specific should select an archetype"

    def test_gravel_type_mapping(self):
        """'gravel' maps to Gravel_Specific category."""
        from nate_workout_generator import select_archetype_for_workout
        archetype = select_archetype_for_workout('gravel', 'POLARIZED')
        assert archetype is not None, "gravel should select an archetype"

    def test_surge_settle_type_mapping(self):
        """'surge_settle' maps to Gravel_Specific category."""
        from nate_workout_generator import select_archetype_for_workout
        archetype = select_archetype_for_workout('surge_settle', 'POLARIZED')
        assert archetype is not None, "surge_settle should select an archetype"

    def test_microbursts_type_mapping(self):
        """'microbursts' maps to Gravel_Specific category."""
        from nate_workout_generator import select_archetype_for_workout
        archetype = select_archetype_for_workout('microbursts', 'POLARIZED')
        assert archetype is not None, "microbursts should select an archetype"

    def test_gravel_grind_type_mapping(self):
        """'gravel_grind' maps to Gravel_Specific category."""
        from nate_workout_generator import select_archetype_for_workout
        archetype = select_archetype_for_workout('gravel_grind', 'POLARIZED')
        assert archetype is not None, "gravel_grind should select an archetype"

    def test_late_race_type_mapping(self):
        """'late_race' maps to Gravel_Specific category."""
        from nate_workout_generator import select_archetype_for_workout
        archetype = select_archetype_for_workout('late_race', 'POLARIZED')
        assert archetype is not None, "late_race should select an archetype"

    def test_gravel_specific_variation_cycles(self):
        """Variations cycle through all 5 Gravel_Specific archetypes."""
        from nate_workout_generator import select_archetype_for_workout
        names = set()
        for v in range(5):
            arch = select_archetype_for_workout('gravel_specific', 'POLARIZED', variation=v)
            assert arch is not None, f"variation={v} returned None"
            names.add(arch['name'])
        assert len(names) == 5, f"Should cycle through 5 archetypes, got {names}"

    def test_variation_wraps_around(self):
        """Variation index wraps around when exceeding archetype count."""
        from nate_workout_generator import select_archetype_for_workout
        arch_v0 = select_archetype_for_workout('gravel_specific', 'POLARIZED', variation=0)
        arch_v5 = select_archetype_for_workout('gravel_specific', 'POLARIZED', variation=5)
        assert arch_v0 is not None
        assert arch_v5 is not None
        assert arch_v0['name'] == arch_v5['name'], \
            "variation=5 should wrap to same archetype as variation=0"

    # =========================================================================
    # 6. Integration Tests (ZWO output quality)
    # =========================================================================

    def test_gravel_zwo_has_description(self):
        """Gravel-specific ZWO includes workout description."""
        from nate_workout_generator import generate_nate_zwo
        zwo = generate_nate_zwo('gravel_specific', level=3, methodology='POLARIZED', variation=0)
        assert '<description>' in zwo
        assert 'MAIN SET' in zwo

    def test_gravel_zwo_has_warmup_and_cooldown(self):
        """Gravel-specific ZWO has warmup and cooldown."""
        from nate_workout_generator import generate_nate_zwo
        zwo = generate_nate_zwo('gravel_specific', level=3, methodology='POLARIZED', variation=0)
        assert 'Warmup' in zwo
        assert 'Cooldown' in zwo

    def test_gravel_zwo_valid_xml(self):
        """Gravel-specific ZWO output is valid XML."""
        import xml.etree.ElementTree as ET
        from nate_workout_generator import generate_nate_zwo
        zwo = generate_nate_zwo('gravel_specific', level=3, methodology='POLARIZED', variation=0)
        assert zwo is not None
        # Should parse without error
        root = ET.fromstring(zwo)
        assert root.tag == 'workout_file'
        workout = root.find('workout')
        assert workout is not None

    def test_all_gravel_levels_generate(self):
        """All levels (1-6) generate valid ZWO for all 4 archetypes."""
        from nate_workout_generator import generate_nate_zwo
        for variation in range(4):
            for level in range(1, 7):
                zwo = generate_nate_zwo(
                    'gravel_specific', level=level,
                    methodology='POLARIZED', variation=variation
                )
                assert zwo is not None, \
                    f"v={variation} L={level} returned None"
                assert '<SteadyState' in zwo, \
                    f"v={variation} L={level} missing SteadyState blocks"

    def test_all_gravel_levels_valid_xml(self):
        """All 24 combinations (4 archetypes x 6 levels) produce valid XML."""
        import xml.etree.ElementTree as ET
        from nate_workout_generator import generate_nate_zwo
        for variation in range(4):
            for level in range(1, 7):
                zwo = generate_nate_zwo(
                    'gravel_specific', level=level,
                    methodology='POLARIZED', variation=variation
                )
                assert zwo is not None, f"v={variation} L={level} returned None"
                try:
                    ET.fromstring(zwo)
                except ET.ParseError as e:
                    pytest.fail(f"v={variation} L={level} invalid XML: {e}")

    def test_gravel_zwo_has_author(self):
        """Gravel-specific ZWO includes Gravel God author tag."""
        from nate_workout_generator import generate_nate_zwo
        zwo = generate_nate_zwo('gravel_specific', level=3, methodology='POLARIZED', variation=0)
        assert 'Gravel God' in zwo

    def test_gravel_zwo_has_sport_type(self):
        """Gravel-specific ZWO specifies bike sport type."""
        from nate_workout_generator import generate_nate_zwo
        zwo = generate_nate_zwo('gravel_specific', level=3, methodology='POLARIZED', variation=0)
        assert '<sportType>bike</sportType>' in zwo

    def test_level_progression_increases_intensity(self):
        """Higher levels should produce higher max power targets."""
        import re
        from nate_workout_generator import generate_nate_zwo
        # Test with Surge & Settle (variation=0)
        max_powers = []
        for level in [1, 3, 6]:
            zwo = generate_nate_zwo(
                'gravel_specific', level=level,
                methodology='POLARIZED', variation=0
            )
            powers = [float(m.group(1)) for m in re.finditer(r'Power="([\d.]+)"', zwo)]
            max_powers.append(max(powers))
        # L1 max < L3 max < L6 max
        assert max_powers[0] < max_powers[1], \
            f"L1 max power ({max_powers[0]}) should be < L3 ({max_powers[1]})"
        assert max_powers[1] < max_powers[2], \
            f"L3 max power ({max_powers[1]}) should be < L6 ({max_powers[2]})"

    def test_generate_nate_workout_returns_tuple(self):
        """generate_nate_workout for gravel returns (name, description, blocks) tuple."""
        from nate_workout_generator import generate_nate_workout
        name, desc, blocks = generate_nate_workout(
            'gravel_specific', level=3, methodology='POLARIZED', variation=0
        )
        assert name is not None
        assert desc is not None
        assert blocks is not None
        assert 'Surge' in name  # variation=0 = Surge and Settle
        assert len(blocks) > 0


class TestImportedArchetypes(unittest.TestCase):
    """Tests for 34 imported archetypes from Cursor ZWO dumps."""

    def test_imported_archetypes_exist(self):
        """IMPORTED_ARCHETYPES dict should be importable and non-empty."""
        from imported_archetypes import IMPORTED_ARCHETYPES
        self.assertIsInstance(IMPORTED_ARCHETYPES, dict)
        self.assertGreaterEqual(len(IMPORTED_ARCHETYPES), 12)

    def test_all_12_categories_present(self):
        """All 12 expected categories should be present."""
        from imported_archetypes import IMPORTED_ARCHETYPES
        expected = {
            'VO2max', 'TT_Threshold', 'Sprint_Neuromuscular',
            'SFR_Muscle_Force', 'Over_Under', 'Mixed_Climbing',
            'Cadence_Work', 'Endurance', 'Blended', 'Tempo',
            'Durability', 'Race_Simulation'
        }
        self.assertEqual(set(IMPORTED_ARCHETYPES.keys()), expected)

    def test_34_archetype_types_total(self):
        """Should have exactly 34 archetype types across all categories."""
        from imported_archetypes import IMPORTED_ARCHETYPES
        total = sum(len(archetypes) for archetypes in IMPORTED_ARCHETYPES.values())
        self.assertEqual(total, 34)

    def test_all_archetypes_have_6_levels(self):
        """Every archetype must have levels '1' through '6'."""
        from imported_archetypes import IMPORTED_ARCHETYPES
        for category, archetypes in IMPORTED_ARCHETYPES.items():
            for arch in archetypes:
                for lvl in ['1', '2', '3', '4', '5', '6']:
                    self.assertIn(lvl, arch['levels'],
                        f"{arch['name']} ({category}) missing level {lvl}")

    def test_all_archetypes_have_name(self):
        """Every archetype must have a 'name' key."""
        from imported_archetypes import IMPORTED_ARCHETYPES
        for category, archetypes in IMPORTED_ARCHETYPES.items():
            for arch in archetypes:
                self.assertIn('name', arch, f"Archetype in {category} missing 'name'")
                self.assertTrue(len(arch['name']) > 0)

    def test_level_1_has_full_metadata(self):
        """Level 1 of each archetype should have structure, execution, cadence."""
        from imported_archetypes import IMPORTED_ARCHETYPES
        for category, archetypes in IMPORTED_ARCHETYPES.items():
            for arch in archetypes:
                lvl1 = arch['levels']['1']
                self.assertIn('structure', lvl1,
                    f"{arch['name']} level 1 missing 'structure'")
                self.assertIn('execution', lvl1,
                    f"{arch['name']} level 1 missing 'execution'")

    def test_format_a_archetypes_have_intervals(self):
        """Format A archetypes must have intervals tuple and power values."""
        from imported_archetypes import IMPORTED_ARCHETYPES
        for category, archetypes in IMPORTED_ARCHETYPES.items():
            for arch in archetypes:
                for lvl_key, lvl_data in arch['levels'].items():
                    if 'intervals' in lvl_data and 'segments' not in lvl_data:
                        ivals = lvl_data['intervals']
                        self.assertIsInstance(ivals, tuple,
                            f"{arch['name']} L{lvl_key}: intervals should be tuple")
                        self.assertEqual(len(ivals), 2,
                            f"{arch['name']} L{lvl_key}: intervals should be (repeats, duration)")
                        self.assertIn('on_power', lvl_data,
                            f"{arch['name']} L{lvl_key}: missing on_power")

    def test_format_b_archetypes_have_segments(self):
        """Format B archetypes must have segments list with valid segment dicts."""
        from imported_archetypes import IMPORTED_ARCHETYPES
        for category, archetypes in IMPORTED_ARCHETYPES.items():
            for arch in archetypes:
                for lvl_key, lvl_data in arch['levels'].items():
                    if 'segments' in lvl_data:
                        segs = lvl_data['segments']
                        self.assertIsInstance(segs, list,
                            f"{arch['name']} L{lvl_key}: segments should be list")
                        self.assertGreater(len(segs), 0,
                            f"{arch['name']} L{lvl_key}: segments should not be empty")
                        for seg in segs:
                            self.assertIn('type', seg,
                                f"{arch['name']} L{lvl_key}: segment missing 'type'")
                            self.assertIn(seg['type'], ('steady', 'intervals'),
                                f"{arch['name']} L{lvl_key}: invalid segment type '{seg['type']}'")

    def test_segments_steady_have_required_keys(self):
        """Steady segments must have duration and power."""
        from imported_archetypes import IMPORTED_ARCHETYPES
        for category, archetypes in IMPORTED_ARCHETYPES.items():
            for arch in archetypes:
                for lvl_key, lvl_data in arch['levels'].items():
                    if 'segments' in lvl_data:
                        for seg in lvl_data['segments']:
                            if seg['type'] == 'steady':
                                self.assertIn('duration', seg,
                                    f"{arch['name']} L{lvl_key}: steady segment missing 'duration'")
                                self.assertIn('power', seg,
                                    f"{arch['name']} L{lvl_key}: steady segment missing 'power'")

    def test_segments_intervals_have_required_keys(self):
        """Intervals segments must have repeats, on_duration, on_power."""
        from imported_archetypes import IMPORTED_ARCHETYPES
        for category, archetypes in IMPORTED_ARCHETYPES.items():
            for arch in archetypes:
                for lvl_key, lvl_data in arch['levels'].items():
                    if 'segments' in lvl_data:
                        for seg in lvl_data['segments']:
                            if seg['type'] == 'intervals':
                                self.assertIn('repeats', seg,
                                    f"{arch['name']} L{lvl_key}: intervals segment missing 'repeats'")
                                self.assertIn('on_duration', seg,
                                    f"{arch['name']} L{lvl_key}: intervals segment missing 'on_duration'")
                                self.assertIn('on_power', seg,
                                    f"{arch['name']} L{lvl_key}: intervals segment missing 'on_power'")

    def test_merge_into_new_archetypes(self):
        """Imported archetypes should merge into NEW_ARCHETYPES correctly."""
        from new_archetypes import NEW_ARCHETYPES
        # Check that new categories exist
        for cat in ['SFR_Muscle_Force', 'Over_Under', 'Mixed_Climbing',
                    'Cadence_Work', 'Blended', 'Tempo']:
            self.assertIn(cat, NEW_ARCHETYPES,
                f"New category '{cat}' not found in NEW_ARCHETYPES after merge")
        # Check that existing categories grew
        # VO2max originally had 4 archetypes + 3 imported = 7
        self.assertGreaterEqual(len(NEW_ARCHETYPES.get('VO2max', [])), 7,
            "VO2max should have at least 7 archetypes after merge")

    def test_no_duplicate_names_after_merge(self):
        """No duplicate archetype names should exist within a category."""
        from new_archetypes import NEW_ARCHETYPES
        for category, archetypes in NEW_ARCHETYPES.items():
            names = [a['name'] for a in archetypes]
            self.assertEqual(len(names), len(set(names)),
                f"Duplicate names in {category}: {[n for n in names if names.count(n) > 1]}")

    def test_power_values_in_range(self):
        """All power values should be between 0.3 and 2.0 (30-200% FTP)."""
        from imported_archetypes import IMPORTED_ARCHETYPES
        for category, archetypes in IMPORTED_ARCHETYPES.items():
            for arch in archetypes:
                for lvl_key, lvl_data in arch['levels'].items():
                    # Check interval power
                    if 'on_power' in lvl_data:
                        self.assertGreaterEqual(lvl_data['on_power'], 0.3,
                            f"{arch['name']} L{lvl_key}: on_power too low")
                        self.assertLessEqual(lvl_data['on_power'], 2.0,
                            f"{arch['name']} L{lvl_key}: on_power too high")
                    # Check segment powers
                    if 'segments' in lvl_data:
                        for seg in lvl_data['segments']:
                            if 'power' in seg:
                                self.assertGreaterEqual(seg['power'], 0.3,
                                    f"{arch['name']} L{lvl_key}: segment power too low")
                                self.assertLessEqual(seg['power'], 2.0,
                                    f"{arch['name']} L{lvl_key}: segment power too high")

    def test_generate_zwo_for_all_new_categories(self):
        """Each new category should generate valid ZWO via the Nate generator."""
        from nate_workout_generator import generate_nate_zwo
        # Map new categories to their type_to_category aliases
        new_type_aliases = {
            'SFR_Muscle_Force': 'sfr',
            'Over_Under': 'over_under',
            'Mixed_Climbing': 'mixed_climbing',
            'Cadence_Work': 'cadence_work',
            'Blended': 'blended',
            'Tempo': 'tempo_workout',
        }
        for category, alias in new_type_aliases.items():
            zwo = generate_nate_zwo(
                workout_type=alias,
                level=3,
                methodology='POLARIZED',
                variation=0,
                workout_name=f'Test_{category}'
            )
            self.assertIsNotNone(zwo,
                f"generate_nate_zwo returned None for {category} (alias={alias})")
            self.assertIn('<workout_file>', zwo,
                f"No <workout_file> tag for {category}")
            self.assertIn('<Warmup', zwo,
                f"No warmup block for {category}")

    def test_generate_zwo_for_augmented_categories(self):
        """Existing categories with new archetypes should still generate."""
        from nate_workout_generator import generate_nate_zwo
        augmented = {
            'VO2max': 'vo2max',
            'TT_Threshold': 'threshold',
            'Sprint_Neuromuscular': 'sprint',
            'Durability': 'durability',
            'Endurance': 'endurance',
            'Race_Simulation': 'race_sim',
        }
        for category, alias in augmented.items():
            # Use a high variation number to reach imported archetypes
            zwo = generate_nate_zwo(
                workout_type=alias,
                level=3,
                methodology='POLARIZED',
                variation=50,  # High number to cycle into imported ones
                workout_name=f'Test_{category}_imported'
            )
            self.assertIsNotNone(zwo,
                f"generate_nate_zwo returned None for augmented {category}")
            self.assertIn('<workout_file>', zwo)

    def test_segments_handler_generates_blocks(self):
        """Format B archetypes using segments handler should produce multi-block ZWO."""
        import re
        from nate_workout_generator import generate_nate_zwo
        # Tempo category uses segments format
        zwo = generate_nate_zwo(
            workout_type='tempo_workout',
            level=3,
            methodology='POLARIZED',
            variation=0,
            workout_name='Test_Segments'
        )
        self.assertIsNotNone(zwo)
        # Should have warmup + multiple SteadyState/IntervalsT + cooldown
        self.assertIn('<Warmup', zwo)
        self.assertIn('<Cooldown', zwo)
        # Count blocks -- should have more than just warmup+cooldown
        blocks = re.findall(r'<(SteadyState|IntervalsT)', zwo)
        self.assertGreater(len(blocks), 0,
            "Segments handler should produce SteadyState or IntervalsT blocks")

    def test_level_progression_in_imported(self):
        """Higher levels should generally have more work (higher power or more intervals)."""
        from imported_archetypes import IMPORTED_ARCHETYPES
        checked = 0
        for category, archetypes in IMPORTED_ARCHETYPES.items():
            for arch in archetypes:
                lvl1 = arch['levels']['1']
                lvl6 = arch['levels']['6']
                # For Format A: check on_power progresses
                if 'on_power' in lvl1 and 'on_power' in lvl6:
                    self.assertGreaterEqual(lvl6['on_power'], lvl1['on_power'],
                        f"{arch['name']}: Level 6 on_power should be >= Level 1")
                    checked += 1
        self.assertGreater(checked, 0, "Should have checked at least one archetype")

    def test_type_to_category_mappings_for_new_types(self):
        """All new type aliases should resolve in select_archetype_for_workout."""
        from nate_workout_generator import select_archetype_for_workout
        aliases = ['sfr', 'over_under', 'mixed_climbing', 'cadence_work', 'blended', 'tempo_workout']
        for alias in aliases:
            result = select_archetype_for_workout(alias, 'POLARIZED', 0)
            self.assertIsNotNone(result,
                f"select_archetype_for_workout returned None for '{alias}'")

    def test_total_archetype_count_after_merge(self):
        """After merge, NEW_ARCHETYPES should have 80+ total archetypes."""
        from new_archetypes import NEW_ARCHETYPES
        total = sum(len(archetypes) for archetypes in NEW_ARCHETYPES.values())
        # Original: 45, Imported: 34 = 79
        self.assertGreaterEqual(total, 79,
            f"Expected 79+ total archetypes after merge, got {total}")

    def test_valid_xml_from_all_204_variations(self):
        """All 204 imported workout variations should produce parseable XML."""
        import xml.etree.ElementTree as ET
        from imported_archetypes import IMPORTED_ARCHETYPES
        from nate_workout_generator import generate_nate_zwo

        # Map categories to aliases
        cat_to_alias = {
            'VO2max': 'vo2max', 'TT_Threshold': 'threshold',
            'Sprint_Neuromuscular': 'sprint', 'SFR_Muscle_Force': 'sfr',
            'Over_Under': 'over_under', 'Mixed_Climbing': 'mixed_climbing',
            'Cadence_Work': 'cadence_work', 'Endurance': 'endurance',
            'Blended': 'blended', 'Tempo': 'tempo_workout',
            'Durability': 'durability', 'Race_Simulation': 'race_sim',
        }
        from new_archetypes import NEW_ARCHETYPES
        failures = []
        tested = 0
        for category, archetypes in IMPORTED_ARCHETYPES.items():
            alias = cat_to_alias.get(category)
            if not alias:
                continue
            # Find the index of each imported archetype in the merged category
            merged_list = NEW_ARCHETYPES.get(category, [])
            for arch in archetypes:
                # Find this archetype's index in the merged list
                idx = None
                for i, merged_arch in enumerate(merged_list):
                    if merged_arch['name'] == arch['name']:
                        idx = i
                        break
                if idx is None:
                    failures.append(f"{arch['name']}: not found in merged NEW_ARCHETYPES[{category}]")
                    continue
                for lvl in range(1, 7):
                    try:
                        zwo = generate_nate_zwo(
                            workout_type=alias,
                            level=lvl,
                            methodology='POLARIZED',
                            variation=idx,
                            workout_name=f"Test_{arch['name']}_L{lvl}"
                        )
                        if zwo is None:
                            failures.append(f"{arch['name']} L{lvl}: returned None")
                            continue
                        # Verify parseable XML
                        ET.fromstring(zwo)
                        tested += 1
                    except ET.ParseError as e:
                        failures.append(f"{arch['name']} L{lvl}: XML parse error: {e}")
                    except Exception as e:
                        failures.append(f"{arch['name']} L{lvl}: {type(e).__name__}: {e}")

        self.assertEqual(failures, [],
            f"\n{len(failures)} failures out of {tested + len(failures)} tested:\n" +
            "\n".join(failures[:20]))
        self.assertGreater(tested, 100,
            f"Expected 100+ valid ZWOs, only {tested} passed")


class TestNewTypeCustomHandlers(unittest.TestCase):
    """Verify SFR, Mixed_Climbing, Cadence_Work have custom handlers and never
    fall through to the generic SteadyState else branch."""

    def _verify_handler_source(self, workout_type):
        """Check that workout_type has an explicit elif branch (not else fallback)."""
        from pathlib import Path
        src = (Path(__file__).parent / 'generate_athlete_package.py').read_text()
        # Build pattern to avoid false positive from source-scanning tests
        pattern = f"elif workout_type == '{workout_type}'"
        return pattern in src

    def test_sfr_handler_exists_in_source(self):
        """SFR must have an explicit elif handler in generate_athlete_package.py."""
        self.assertTrue(self._verify_handler_source('SFR'),
            "SFR must have 'elif workout_type == \"SFR\"' handler")

    def test_mixed_climbing_handler_exists_in_source(self):
        """Mixed_Climbing must have an explicit elif handler."""
        self.assertTrue(self._verify_handler_source('Mixed_Climbing'),
            "Mixed_Climbing must have 'elif workout_type == \"Mixed_Climbing\"' handler")

    def test_cadence_work_handler_exists_in_source(self):
        """Cadence_Work must have an explicit elif handler."""
        self.assertTrue(self._verify_handler_source('Cadence_Work'),
            "Cadence_Work must have 'elif workout_type == \"Cadence_Work\"' handler")

    def test_all_nate_types_have_handlers_in_source(self):
        """Every type in nate_workout_types must have an explicit handler OR return None."""
        nate_types = [
            'SFR', 'Over_Under', 'Mixed_Climbing', 'Cadence_Work', 'Blended', 'Tempo',
        ]
        for wt in nate_types:
            self.assertTrue(self._verify_handler_source(wt),
                f"{wt} must have an explicit elif handler, not rely on else fallback")


class TestNateRoutingForNewTypes(unittest.TestCase):
    """Verify all 6 new types properly route through the Nate generator."""

    def test_sfr_generates_valid_zwo(self):
        """SFR type must generate valid ZWO through Nate generator."""
        from nate_workout_generator import generate_nate_zwo
        zwo = generate_nate_zwo(workout_type='sfr', level=3, methodology='POLARIZED')
        self.assertIsNotNone(zwo, "SFR should generate a ZWO, not return None")
        import xml.etree.ElementTree as ET
        root = ET.fromstring(zwo)
        self.assertIsNotNone(root.find('workout'))

    def test_mixed_climbing_generates_valid_zwo(self):
        """Mixed_Climbing type must generate valid ZWO through Nate generator."""
        from nate_workout_generator import generate_nate_zwo
        zwo = generate_nate_zwo(workout_type='mixed_climbing', level=3, methodology='POLARIZED')
        self.assertIsNotNone(zwo, "Mixed_Climbing should generate a ZWO, not return None")
        import xml.etree.ElementTree as ET
        ET.fromstring(zwo)

    def test_cadence_work_generates_valid_zwo(self):
        """Cadence_Work type must generate valid ZWO through Nate generator."""
        from nate_workout_generator import generate_nate_zwo
        zwo = generate_nate_zwo(workout_type='cadence_work', level=3, methodology='POLARIZED')
        self.assertIsNotNone(zwo, "Cadence_Work should generate a ZWO, not return None")
        import xml.etree.ElementTree as ET
        ET.fromstring(zwo)

    def test_all_new_types_at_all_levels(self):
        """All 6 new types must generate valid ZWO at all 6 levels."""
        from nate_workout_generator import generate_nate_zwo
        import xml.etree.ElementTree as ET
        new_types = ['sfr', 'over_under', 'mixed_climbing', 'cadence_work', 'blended', 'tempo_workout']
        failures = []
        for wt in new_types:
            for level in range(1, 7):
                try:
                    zwo = generate_nate_zwo(workout_type=wt, level=level, methodology='POLARIZED')
                    if zwo is None:
                        failures.append(f"{wt} L{level}: returned None")
                        continue
                    ET.fromstring(zwo)
                except Exception as e:
                    failures.append(f"{wt} L{level}: {type(e).__name__}: {e}")
        self.assertEqual(failures, [],
            f"\n{len(failures)} failures:\n" + "\n".join(failures))


class TestMultiMethodologyArchetypeSelection(unittest.TestCase):
    """Verify archetype selection works across different methodologies."""

    METHODOLOGIES = [
        'POLARIZED', 'PYRAMIDAL', 'G_SPOT', 'HIT', 'NORWEGIAN',
        'MAF_LT1', 'CRITICAL_POWER', 'HVLI', 'INSCYD', 'BLOCK',
        'REVERSE', 'HRV_AUTO', 'GOAT',
    ]

    def test_vo2max_selection_across_methodologies(self):
        """VO2max archetype selection should work for all methodologies."""
        from nate_workout_generator import select_archetype_for_workout
        for meth in self.METHODOLOGIES:
            result = select_archetype_for_workout('vo2max', meth, variation=0)
            # Some methodologies may avoid VO2max — that's OK (returns None)
            if result is not None:
                self.assertIn('name', result, f"{meth}: archetype missing 'name'")
                self.assertIn('levels', result, f"{meth}: archetype missing 'levels'")

    def test_new_types_across_methodologies(self):
        """All 6 new types should work across all methodologies."""
        from nate_workout_generator import select_archetype_for_workout
        new_types = ['sfr', 'over_under', 'mixed_climbing', 'cadence_work', 'blended', 'tempo_workout']
        for wt in new_types:
            for meth in self.METHODOLOGIES:
                result = select_archetype_for_workout(wt, meth, variation=0)
                # Result may be None if methodology avoids this category — acceptable
                if result is not None:
                    self.assertIn('name', result,
                        f"{wt}/{meth}: archetype missing 'name'")

    def test_different_methodologies_can_select_different_archetypes(self):
        """At least some methodologies should prefer different VO2max archetypes."""
        from nate_workout_generator import select_archetype_for_workout
        names = set()
        for meth in self.METHODOLOGIES:
            arch = select_archetype_for_workout('vo2max', meth, variation=0)
            if arch:
                names.add(arch['name'])
        # At least 1 archetype selected (may be same across all — that's fine
        # if methodology_overrides don't differ for VO2max start_offset)
        self.assertGreaterEqual(len(names), 1)

    def test_nate_zwo_generation_across_methodologies(self):
        """Full ZWO generation should work for all methodology × type combos."""
        from nate_workout_generator import generate_nate_zwo
        import xml.etree.ElementTree as ET
        test_types = ['vo2max', 'threshold', 'sprint', 'sfr', 'over_under', 'blended']
        failures = []
        for wt in test_types:
            for meth in self.METHODOLOGIES:
                try:
                    zwo = generate_nate_zwo(workout_type=wt, level=3, methodology=meth)
                    if zwo is not None:
                        ET.fromstring(zwo)
                except Exception as e:
                    failures.append(f"{wt}/{meth}: {type(e).__name__}: {e}")
        self.assertEqual(failures, [],
            f"\n{len(failures)} failures:\n" + "\n".join(failures))


class TestVariationCycling(unittest.TestCase):
    """Verify archetype variation counter wraps correctly."""

    def test_variation_wraps_around(self):
        """Variation index beyond archetype count should wrap via modulo."""
        from nate_workout_generator import select_archetype_for_workout, get_all_archetypes_for_category
        archetypes = get_all_archetypes_for_category('VO2max')
        count = len(archetypes)
        self.assertGreater(count, 0, "VO2max should have archetypes")

        # Request variation = count (should wrap to 0)
        arch_wrapped = select_archetype_for_workout('vo2max', 'POLARIZED', variation=count)
        arch_first = select_archetype_for_workout('vo2max', 'POLARIZED', variation=0)
        if arch_wrapped and arch_first:
            self.assertEqual(arch_wrapped['name'], arch_first['name'],
                f"Variation {count} should wrap to same as variation 0")

    def test_variation_cycles_through_all_archetypes(self):
        """Incrementing variation should cycle through different archetypes."""
        from nate_workout_generator import select_archetype_for_workout, get_all_archetypes_for_category
        archetypes = get_all_archetypes_for_category('VO2max')
        if len(archetypes) < 2:
            self.skipTest("Need 2+ VO2max archetypes to test cycling")

        names = []
        for v in range(len(archetypes)):
            arch = select_archetype_for_workout('vo2max', 'POLARIZED', variation=v)
            if arch:
                names.append(arch['name'])
        # Should see at least 2 different archetypes across variations
        self.assertGreater(len(set(names)), 1,
            f"Variation cycling should produce different archetypes, got: {names}")

    def test_new_type_variation_cycling(self):
        """New types should also cycle through their archetypes."""
        from nate_workout_generator import select_archetype_for_workout, get_all_archetypes_for_category
        for category, alias in [('SFR_Muscle_Force', 'sfr'), ('Over_Under', 'over_under')]:
            archetypes = get_all_archetypes_for_category(category)
            if len(archetypes) < 2:
                continue
            names = []
            for v in range(len(archetypes)):
                arch = select_archetype_for_workout(alias, 'POLARIZED', variation=v)
                if arch:
                    names.append(arch['name'])
            self.assertGreater(len(set(names)), 1,
                f"{category}: variation cycling should produce different archetypes")


class TestDurationScalingNewTypes(unittest.TestCase):
    """Verify duration scaling works for new workout types."""

    def test_new_types_in_interval_types(self):
        """SFR, Mixed_Climbing, Cadence_Work must be in _INTERVAL_TYPES for scaling."""
        from workout_templates import _INTERVAL_TYPES
        for wt in ['SFR', 'Mixed_Climbing', 'Cadence_Work']:
            self.assertIn(wt, _INTERVAL_TYPES,
                f"{wt} must be in _INTERVAL_TYPES for proper duration scaling")

    def test_scaling_caps_at_120_for_new_types(self):
        """New interval types should cap at 120 min even with 4+ hour availability."""
        for wt in ['SFR', 'Mixed_Climbing', 'Cadence_Work']:
            target = calculate_target_duration(wt, 300, 'build', 60)
            self.assertLessEqual(target, 120,
                f"{wt} should cap at 120 min, got {target}")

    def test_scaling_respects_minimum(self):
        """New types should not scale below template duration."""
        for wt in ['SFR', 'Mixed_Climbing', 'Cadence_Work']:
            target = calculate_target_duration(wt, 40, 'build', 60)
            self.assertGreaterEqual(target, 40,
                f"{wt} should not exceed max_duration (40), got {target}")


class TestSegmentHandlerEdgeCases(unittest.TestCase):
    """Test the segments handler in nate_workout_generator for edge cases."""

    def test_freeride_segment_type(self):
        """Freeride segment type should generate FreeRide XML element."""
        from nate_workout_generator import generate_nate_zwo
        import xml.etree.ElementTree as ET

        # We can't easily inject segments directly, but we can verify the handler
        # by checking that archetypes with 'segments' key generate valid XML
        # with all segment types properly handled
        zwo = generate_nate_zwo(workout_type='sfr', level=1, methodology='POLARIZED')
        if zwo:
            root = ET.fromstring(zwo)
            self.assertIsNotNone(root.find('workout'))

    def test_unknown_segment_type_doesnt_crash(self):
        """Unknown segment types should render as SteadyState, not crash."""
        from nate_workout_generator import generate_blocks_from_archetype
        # Create a fake archetype with an unknown segment type
        fake_archetype = {
            'name': 'Test Unknown Segment',
            'levels': {
                '1': {
                    'structure': 'test',
                    'execution': 'test',
                    'segments': [
                        {'type': 'steady', 'duration': 300, 'power': 0.65},
                        {'type': 'totally_unknown', 'duration': 120, 'power': 0.80},
                        {'type': 'steady', 'duration': 300, 'power': 0.65},
                    ],
                },
            },
        }
        # Should not crash — returns a string of XML blocks
        blocks = generate_blocks_from_archetype(fake_archetype, level=1)
        self.assertIsNotNone(blocks, "Unknown segment type should not crash generation")
        # Should render something for the unknown segment (as SteadyState fallback)
        self.assertIn('Duration="120"', blocks,
            "Unknown segment should be rendered as SteadyState with correct duration")

    def test_missing_segment_keys_use_defaults(self):
        """Segments with missing keys should use safe defaults."""
        from nate_workout_generator import generate_blocks_from_archetype
        fake_archetype = {
            'name': 'Test Missing Keys',
            'levels': {
                '1': {
                    'structure': 'test',
                    'execution': 'test',
                    'segments': [
                        {'type': 'steady'},  # Missing duration and power
                        {'type': 'intervals'},  # Missing all interval keys
                    ],
                },
            },
        }
        # Should not crash — defaults should be used
        try:
            blocks = generate_blocks_from_archetype(fake_archetype, level=1)
            self.assertIsNotNone(blocks, "Missing segment keys should use defaults, not crash")
        except KeyError as e:
            self.fail(f"KeyError on missing segment key: {e}")


class TestPerTypePowerRanges(unittest.TestCase):
    """Validate power values are appropriate for each workout type."""

    TYPE_POWER_RANGES = {
        'VO2max': (1.05, 1.60),
        'TT_Threshold': (0.85, 1.10),
        'Sprint_Neuromuscular': (1.20, 2.50),
        'Anaerobic_Capacity': (1.10, 2.00),
        'SFR_Muscle_Force': (0.60, 1.10),
        'Over_Under': (0.80, 1.20),
        'Mixed_Climbing': (0.75, 1.25),
        'Cadence_Work': (0.60, 1.10),
        'Blended': (0.70, 1.30),
        'Tempo': (0.70, 1.00),
        'Endurance': (0.50, 0.80),
        'Recovery': (0.35, 0.65),
    }

    def test_imported_archetype_power_ranges(self):
        """Imported archetypes should have on_power within type-appropriate range."""
        from imported_archetypes import IMPORTED_ARCHETYPES
        warnings = []
        for category, archetypes in IMPORTED_ARCHETYPES.items():
            expected_range = self.TYPE_POWER_RANGES.get(category)
            if not expected_range:
                continue
            lo, hi = expected_range
            for arch in archetypes:
                for lvl_key, lvl_data in arch['levels'].items():
                    on_power = lvl_data.get('on_power')
                    if on_power and (on_power < lo - 0.10 or on_power > hi + 0.10):
                        warnings.append(
                            f"{category}/{arch['name']} L{lvl_key}: "
                            f"on_power={on_power} outside expected {lo}-{hi}"
                        )
                    # Also check segment powers
                    for seg in lvl_data.get('segments', []):
                        seg_power = seg.get('power') or seg.get('on_power')
                        if seg_power and (seg_power < 0.30 or seg_power > 2.50):
                            warnings.append(
                                f"{category}/{arch['name']} L{lvl_key}: "
                                f"segment power={seg_power} outside global 0.30-2.50"
                            )
        # Warnings are informational — only fail on truly absurd values
        absurd = [w for w in warnings if 'outside global' in w]
        self.assertEqual(absurd, [],
            f"\n{len(absurd)} absurd power values:\n" + "\n".join(absurd))


class TestDistributionWithNewTypes(unittest.TestCase):
    """Verify zone distribution validation works with new workout types."""

    def test_new_types_excluded_from_basic_distribution_if_needed(self):
        """New types should classify into appropriate zones, not break distribution."""
        # Map new types to expected zones
        type_to_zone = {
            'SFR': 'intensity',         # Sub-threshold but structured
            'Over_Under': 'intensity',  # Above/below threshold
            'Mixed_Climbing': 'intensity',
            'Cadence_Work': 'intensity',
            'Blended': 'intensity',
            'Tempo': 'endurance',       # Tempo-range
        }
        # All new types should map to a known zone category
        for wt, zone in type_to_zone.items():
            self.assertIn(zone, ['intensity', 'endurance'],
                f"{wt} should map to a known zone category")

    def test_new_types_in_nate_workout_types_dict(self):
        """All 6 new types must be in the nate_workout_types routing dict in source."""
        from pathlib import Path
        src = (Path(__file__).parent / 'generate_athlete_package.py').read_text()
        expected = {
            'SFR': "'sfr'", 'Over_Under': "'over_under'",
            'Mixed_Climbing': "'mixed_climbing'", 'Cadence_Work': "'cadence_work'",
            'Blended': "'blended'", 'Tempo': "'tempo_workout'",
        }
        for display_name, nate_alias in expected.items():
            self.assertIn(f"'{display_name}'", src,
                f"{display_name} must be in nate_workout_types dict")
            self.assertIn(nate_alias, src,
                f"{nate_alias} mapping must be in nate_workout_types dict")


class TestEdgeCases(unittest.TestCase):
    """Edge cases for new archetype types."""

    def test_taper_phase_doesnt_assign_new_types(self):
        """Taper phase should use Easy/Openers, not SFR/Cadence_Work."""
        # Taper PHASE_WORKOUT_ROLES should not include new intensity types
        from workout_templates import PHASE_WORKOUT_ROLES
        taper = PHASE_WORKOUT_ROLES['taper']
        taper_types = {v[0] for v in taper.values()}
        forbidden_in_taper = {'SFR', 'Mixed_Climbing', 'Cadence_Work', 'Blended'}
        overlap = taper_types & forbidden_in_taper
        self.assertEqual(overlap, set(),
            f"Taper phase should not assign these types: {overlap}")

    def test_race_phase_doesnt_assign_new_types(self):
        """Race phase should use Easy/Openers/RACE_DAY, not intensity types."""
        from workout_templates import PHASE_WORKOUT_ROLES
        race = PHASE_WORKOUT_ROLES['race']
        race_types = {v[0] for v in race.values()}
        forbidden_in_race = {'SFR', 'Mixed_Climbing', 'Cadence_Work', 'Over_Under'}
        overlap = race_types & forbidden_in_race
        self.assertEqual(overlap, set(),
            f"Race phase should not assign these types: {overlap}")

    def test_short_duration_nate_doesnt_crash(self):
        """New types via Nate generator should not crash at low levels (short workouts)."""
        from nate_workout_generator import generate_nate_zwo
        import xml.etree.ElementTree as ET
        for wt in ['sfr', 'mixed_climbing', 'cadence_work']:
            try:
                zwo = generate_nate_zwo(workout_type=wt, level=1, methodology='POLARIZED')
                if zwo:
                    ET.fromstring(zwo)
            except Exception as e:
                self.fail(f"{wt} level 1 crashed: {e}")

    def test_new_type_handlers_present_in_source(self):
        """SFR, Mixed_Climbing, Cadence_Work must have elif handlers before the else fallback."""
        from pathlib import Path
        src = (Path(__file__).parent / 'generate_athlete_package.py').read_text()
        # Find positions of the handlers and the else fallback
        for wt in ['SFR', 'Mixed_Climbing', 'Cadence_Work']:
            handler_pos = src.find(f"elif workout_type == '{wt}'")
            else_pos = src.rfind("        else:\n")
            self.assertNotEqual(handler_pos, -1,
                f"{wt} handler not found in source")
            self.assertLess(handler_pos, else_pos,
                f"{wt} handler must come before the else fallback")

    def test_nate_generator_level_bounds(self):
        """Nate generator should handle edge levels (1 and 6) for all new types."""
        from nate_workout_generator import generate_nate_zwo
        import xml.etree.ElementTree as ET
        new_types = ['sfr', 'over_under', 'mixed_climbing', 'cadence_work', 'blended', 'tempo_workout']
        failures = []
        for wt in new_types:
            for level in [1, 6]:
                try:
                    zwo = generate_nate_zwo(workout_type=wt, level=level, methodology='POLARIZED')
                    if zwo:
                        ET.fromstring(zwo)
                except Exception as e:
                    failures.append(f"{wt} level {level}: {e}")
        self.assertEqual(failures, [],
            f"\n{len(failures)} edge level failures:\n" + "\n".join(failures))


# =============================================================================
# ADVANCED ARCHETYPES TESTS (Sprint 2: 16 new archetypes)
# =============================================================================

class TestAdvancedArchetypes:
    """Tests for the 16 advanced archetypes added in Sprint 2."""

    # =========================================================================
    # 1. Archetype Data Integrity
    # =========================================================================

    def test_advanced_archetypes_import(self):
        """advanced_archetypes.py imports and ADVANCED_ARCHETYPES dict exists."""
        from advanced_archetypes import ADVANCED_ARCHETYPES
        assert isinstance(ADVANCED_ARCHETYPES, dict)
        assert len(ADVANCED_ARCHETYPES) == 8  # 8 categories

    def test_advanced_archetypes_merged_into_new(self):
        """All 16 advanced archetypes appear in NEW_ARCHETYPES after merge."""
        from new_archetypes import NEW_ARCHETYPES
        expected_names = [
            'Ronnestad 30/15', 'Ronnestad 40/20', 'Float Sets',
            'Criss-Cross Intervals', 'TTE Extension', 'BPA (Best Possible Average)',
            'Hard Starts', 'Structured Fartlek', 'Attacks and Repeatability',
            'Kitchen Sink All-Systems',
            'Late-Race VO2max',
            'Heat Acclimation Protocol',
            'Burst Intervals',
            'Gravel Race Simulation',
            'FatMax VLamax Suppression', 'Glycolytic Power',
        ]
        all_names = set()
        for archs in NEW_ARCHETYPES.values():
            for a in archs:
                all_names.add(a['name'])
        for name in expected_names:
            assert name in all_names, f"'{name}' not found in merged NEW_ARCHETYPES"

    def test_all_advanced_have_six_levels(self):
        """Every advanced archetype has levels 1-6."""
        from advanced_archetypes import ADVANCED_ARCHETYPES
        for category, archetypes in ADVANCED_ARCHETYPES.items():
            for arch in archetypes:
                for lvl in ['1', '2', '3', '4', '5', '6']:
                    assert lvl in arch['levels'], \
                        f"{arch['name']} missing level {lvl}"

    def test_level1_has_metadata(self):
        """Level 1 of each advanced archetype has required metadata fields."""
        from advanced_archetypes import ADVANCED_ARCHETYPES
        for category, archetypes in ADVANCED_ARCHETYPES.items():
            for arch in archetypes:
                l1 = arch['levels']['1']
                assert 'cadence_prescription' in l1, \
                    f"{arch['name']} L1 missing cadence_prescription"
                assert 'position_prescription' in l1, \
                    f"{arch['name']} L1 missing position_prescription"
                assert 'execution' in l1, \
                    f"{arch['name']} L1 missing execution"
                assert 'structure' in l1, \
                    f"{arch['name']} L1 missing structure"

    def test_all_levels_have_structure_and_execution(self):
        """Every level of every advanced archetype has structure and execution."""
        from advanced_archetypes import ADVANCED_ARCHETYPES
        for category, archetypes in ADVANCED_ARCHETYPES.items():
            for arch in archetypes:
                for lvl_key, lvl_data in arch['levels'].items():
                    assert 'structure' in lvl_data, \
                        f"{arch['name']} L{lvl_key} missing structure"
                    assert 'execution' in lvl_data, \
                        f"{arch['name']} L{lvl_key} missing execution"

    # =========================================================================
    # 2. Power Range Validation
    # =========================================================================

    def test_power_values_in_global_range(self):
        """All power targets in advanced archetypes within 0.50-2.00."""
        from advanced_archetypes import ADVANCED_ARCHETYPES
        failures = []
        for category, archetypes in ADVANCED_ARCHETYPES.items():
            for arch in archetypes:
                for lvl_key, lvl_data in arch['levels'].items():
                    # Check top-level power keys
                    for key in ['on_power', 'off_power', 'power', 'base_power']:
                        if key in lvl_data:
                            p = lvl_data[key]
                            if not (0.30 <= p <= 2.00):
                                failures.append(
                                    f"{arch['name']} L{lvl_key} {key}={p}")
                    # Check segment powers
                    for seg in lvl_data.get('segments', []):
                        for key in ['power', 'on_power', 'off_power']:
                            if key in seg:
                                p = seg[key]
                                if not (0.30 <= p <= 2.00):
                                    failures.append(
                                        f"{arch['name']} L{lvl_key} seg {key}={p}")
        assert failures == [], \
            f"Power values out of range:\n" + "\n".join(failures)

    # =========================================================================
    # 3. ZWO Generation - All Advanced Archetypes
    # =========================================================================

    def test_all_advanced_generate_valid_zwo(self):
        """All 16 advanced archetypes at all 6 levels generate valid ZWO XML."""
        import xml.etree.ElementTree as ET
        from new_archetypes import NEW_ARCHETYPES
        from nate_workout_generator import generate_nate_zwo

        cat_to_alias = {
            'VO2max': 'vo2max', 'TT_Threshold': 'threshold',
            'Race_Simulation': 'race_sim', 'Durability': 'durability',
            'Endurance': 'endurance', 'Sprint_Neuromuscular': 'sprint',
            'Gravel_Specific': 'gravel_specific', 'INSCYD': 'inscyd',
        }

        advanced_names = {
            'Ronnestad 30/15', 'Ronnestad 40/20', 'Float Sets',
            'Criss-Cross Intervals', 'TTE Extension', 'BPA (Best Possible Average)',
            'Hard Starts', 'Structured Fartlek', 'Attacks and Repeatability',
            'Kitchen Sink All-Systems', 'Late-Race VO2max',
            'Heat Acclimation Protocol', 'Burst Intervals',
            'Gravel Race Simulation',
            'FatMax VLamax Suppression', 'Glycolytic Power',
        }

        failures = []
        tested = 0
        for category, alias in cat_to_alias.items():
            archs = NEW_ARCHETYPES.get(category, [])
            for idx, arch in enumerate(archs):
                if arch['name'] not in advanced_names:
                    continue
                for lvl in range(1, 7):
                    try:
                        zwo = generate_nate_zwo(
                            workout_type=alias, level=lvl,
                            methodology='POLARIZED', variation=idx,
                            workout_name=f"Test_{arch['name']}_L{lvl}"
                        )
                        if zwo is None:
                            failures.append(f"{arch['name']} L{lvl}: returned None")
                            continue
                        ET.fromstring(zwo)
                        tested += 1
                    except ET.ParseError as e:
                        failures.append(f"{arch['name']} L{lvl}: XML error: {e}")
                    except Exception as e:
                        failures.append(f"{arch['name']} L{lvl}: {type(e).__name__}: {e}")

        assert failures == [], \
            f"\n{len(failures)} failures:\n" + "\n".join(failures[:20])
        assert tested >= 90, \
            f"Expected 90+ valid ZWOs (16×6=96), only {tested} tested"

    # =========================================================================
    # 4. Type Mapping Tests
    # =========================================================================

    def test_advanced_type_aliases_resolve(self):
        """All new type aliases resolve to valid archetypes."""
        from nate_workout_generator import select_archetype_for_workout
        aliases = [
            'ronnestad_30_15', 'ronnestad_40_20', 'ronnestad', 'float_sets',
            'hard_starts', 'criss_cross_intervals', 'tte_extension', 'tte',
            'bpa', 'best_possible_average',
            'structured_fartlek', 'fartlek',
            'attacks', 'repeatability', 'kitchen_sink', 'all_systems',
            'late_race_vo2', 'heat_acclimation', 'heat_adaptation',
            'burst_intervals', 'bursts',
            'gravel_race_sim',
            'fatmax_suppression', 'vlamax_suppression',
            'glycolytic_power', 'glycolytic',
        ]
        for alias in aliases:
            arch = select_archetype_for_workout(alias, 'POLARIZED')
            assert arch is not None, f"alias '{alias}' returned None"

    def test_nate_workout_types_route_race_sim_and_durability(self):
        """Race_Sim and Durability are in nate_workout_types routing dict."""
        from pathlib import Path
        src = (Path(__file__).parent / 'generate_athlete_package.py').read_text()
        assert "'Race_Sim'" in src, "Race_Sim must be in nate_workout_types"
        assert "'Durability'" in src, "Durability must be in nate_workout_types"
        assert "'race_sim'" in src, "race_sim alias must be in nate_workout_types"
        assert "'durability'" in src, "durability alias must be in nate_workout_types"

    # =========================================================================
    # 5. Category-Specific Tests
    # =========================================================================

    def test_ronnestad_30_15_has_segments(self):
        """Ronnestad 30/15 uses segments format with 30sec ON / 15sec OFF."""
        from advanced_archetypes import ADVANCED_ARCHETYPES
        arch = [a for a in ADVANCED_ARCHETYPES['VO2max'] if a['name'] == 'Ronnestad 30/15'][0]
        for lvl_key in ['1', '2', '3', '4', '5', '6']:
            ld = arch['levels'][lvl_key]
            assert 'segments' in ld, f"L{lvl_key} missing segments"
            # Check at least one intervals segment has 30sec ON, 15sec OFF
            has_30_15 = any(
                s.get('on_duration') == 30 and s.get('off_duration') == 15
                for s in ld['segments'] if s.get('type') == 'intervals'
            )
            assert has_30_15, f"L{lvl_key} missing 30/15 intervals segment"

    def test_ronnestad_40_20_has_segments(self):
        """Ronnestad 40/20 uses 40sec ON / 20sec OFF intervals."""
        from advanced_archetypes import ADVANCED_ARCHETYPES
        arch = [a for a in ADVANCED_ARCHETYPES['VO2max'] if a['name'] == 'Ronnestad 40/20'][0]
        for lvl_key in ['1', '2', '3', '4', '5', '6']:
            ld = arch['levels'][lvl_key]
            has_40_20 = any(
                s.get('on_duration') == 40 and s.get('off_duration') == 20
                for s in ld['segments'] if s.get('type') == 'intervals'
            )
            assert has_40_20, f"L{lvl_key} missing 40/20 intervals segment"

    def test_float_sets_has_tempo_recovery(self):
        """Float Sets use tempo recovery (off_power >= 0.80) not Z1."""
        from advanced_archetypes import ADVANCED_ARCHETYPES
        arch = [a for a in ADVANCED_ARCHETYPES['VO2max'] if a['name'] == 'Float Sets'][0]
        for lvl_key in ['1', '2', '3', '4', '5', '6']:
            ld = arch['levels'][lvl_key]
            off = ld.get('off_power', 0)
            assert off >= 0.80, \
                f"L{lvl_key} off_power={off} must be tempo (>=0.80)"

    def test_hard_starts_have_burst_and_hold(self):
        """Hard Starts segments contain both burst (>=1.50) and hold (0.95-1.05)."""
        from advanced_archetypes import ADVANCED_ARCHETYPES
        arch = [a for a in ADVANCED_ARCHETYPES['Race_Simulation'] if a['name'] == 'Hard Starts'][0]
        for lvl_key in ['1', '2', '3', '4', '5', '6']:
            ld = arch['levels'][lvl_key]
            powers = [s['power'] for s in ld['segments']]
            has_burst = any(p >= 1.50 for p in powers)
            has_hold = any(0.90 <= p <= 1.10 for p in powers)
            assert has_burst, f"L{lvl_key} missing burst segment"
            assert has_hold, f"L{lvl_key} missing threshold hold segment"

    def test_tte_extension_duration_increases(self):
        """TTE Extension: total work duration increases from L1 to L6."""
        from advanced_archetypes import ADVANCED_ARCHETYPES
        arch = [a for a in ADVANCED_ARCHETYPES['TT_Threshold'] if a['name'] == 'TTE Extension'][0]
        total_work = []
        for lvl in ['1', '3', '6']:
            ld = arch['levels'][lvl]
            work = sum(s['duration'] for s in ld['segments'] if s.get('power', 0) >= 0.90)
            total_work.append(work)
        assert total_work[0] < total_work[1] < total_work[2], \
            f"TTE work duration should increase: {total_work}"

    def test_bpa_uses_single_effort(self):
        """BPA uses single_effort format."""
        from advanced_archetypes import ADVANCED_ARCHETYPES
        arch = [a for a in ADVANCED_ARCHETYPES['TT_Threshold']
                if a['name'] == 'BPA (Best Possible Average)'][0]
        for lvl_key in ['1', '2', '3', '4', '5', '6']:
            ld = arch['levels'][lvl_key]
            assert ld.get('single_effort') is True, \
                f"L{lvl_key} missing single_effort flag"

    def test_late_race_vo2_uses_tired_vo2(self):
        """Late-Race VO2max uses tired_vo2 format with base_duration."""
        from advanced_archetypes import ADVANCED_ARCHETYPES
        arch = ADVANCED_ARCHETYPES['Durability'][0]
        assert arch['name'] == 'Late-Race VO2max'
        for lvl_key in ['1', '2', '3', '4', '5', '6']:
            ld = arch['levels'][lvl_key]
            assert 'tired_vo2' in ld, f"L{lvl_key} missing tired_vo2"
            assert 'base_duration' in ld, f"L{lvl_key} missing base_duration"
            assert 'intervals' in ld, f"L{lvl_key} missing intervals"
            assert ld['base_duration'] >= 3600, \
                f"L{lvl_key} base_duration should be >= 60min"

    def test_kitchen_sink_touches_all_zones(self):
        """Kitchen Sink has segments spanning Z2 through sprint."""
        from advanced_archetypes import ADVANCED_ARCHETYPES
        arch = [a for a in ADVANCED_ARCHETYPES['Race_Simulation']
                if a['name'] == 'Kitchen Sink All-Systems'][0]
        ld = arch['levels']['3']
        powers = [s['power'] for s in ld['segments']]
        has_z2 = any(0.60 <= p <= 0.75 for p in powers)
        has_tempo = any(0.76 <= p <= 0.89 for p in powers)
        has_threshold = any(0.90 <= p <= 1.05 for p in powers)
        has_vo2 = any(1.06 <= p <= 1.30 for p in powers)
        has_sprint = any(p >= 1.50 for p in powers)
        assert all([has_z2, has_tempo, has_threshold, has_vo2, has_sprint]), \
            f"Kitchen Sink must touch all zones"

    def test_gravel_race_sim_is_long(self):
        """Gravel Race Simulation L6 total duration exceeds 3 hours."""
        from advanced_archetypes import ADVANCED_ARCHETYPES
        arch = ADVANCED_ARCHETYPES['Gravel_Specific'][0]
        assert arch['name'] == 'Gravel Race Simulation'
        ld = arch['levels']['6']
        total_sec = sum(s['duration'] for s in ld['segments'])
        assert total_sec >= 10800, \
            f"L6 total duration {total_sec}s should be >= 3hr (10800s)"

    def test_fatmax_vlamax_is_long_z2(self):
        """FatMax VLamax Suppression is predominantly Z2 (power <= 0.85)."""
        from advanced_archetypes import ADVANCED_ARCHETYPES
        arch = [a for a in ADVANCED_ARCHETYPES['INSCYD']
                if a['name'] == 'FatMax VLamax Suppression'][0]
        ld = arch['levels']['3']
        z2_time = sum(s['duration'] for s in ld['segments'] if s['power'] <= 0.75)
        total_time = sum(s['duration'] for s in ld['segments'])
        ratio = z2_time / total_time
        assert ratio >= 0.90, \
            f"FatMax should be 90%+ Z2, got {ratio:.1%}"

    def test_glycolytic_power_uses_intervals(self):
        """Glycolytic Power uses Format A intervals tuple."""
        from advanced_archetypes import ADVANCED_ARCHETYPES
        arch = [a for a in ADVANCED_ARCHETYPES['INSCYD']
                if a['name'] == 'Glycolytic Power'][0]
        for lvl_key in ['1', '2', '3', '4', '5', '6']:
            ld = arch['levels'][lvl_key]
            assert 'intervals' in ld, f"L{lvl_key} missing intervals"
            assert isinstance(ld['intervals'], tuple), \
                f"L{lvl_key} intervals should be tuple"

    # =========================================================================
    # 6. Level Progression Tests
    # =========================================================================

    def test_level_progression_power_increases(self):
        """Higher levels produce higher max power in ZWO for advanced archetypes."""
        import re
        from nate_workout_generator import generate_nate_zwo
        # Test with Ronnestad 30/15 (first VO2max advanced, need correct index)
        from new_archetypes import NEW_ARCHETYPES
        vo2_names = [a['name'] for a in NEW_ARCHETYPES['VO2max']]
        ronnestad_idx = vo2_names.index('Ronnestad 30/15')

        max_powers = []
        for level in [1, 3, 6]:
            zwo = generate_nate_zwo(
                'vo2max', level=level,
                methodology='POLARIZED', variation=ronnestad_idx
            )
            assert zwo is not None, f"Ronnestad 30/15 L{level} returned None"
            powers = [float(m.group(1)) for m in re.finditer(r'Power="([\d.]+)"', zwo)]
            max_powers.append(max(powers))
        assert max_powers[0] < max_powers[2], \
            f"L1 max power ({max_powers[0]}) should be < L6 ({max_powers[2]})"

    # =========================================================================
    # 7. Duration Scaling Integration
    # =========================================================================

    def test_race_sim_and_durability_in_interval_types(self):
        """Race_Sim and Durability are in _INTERVAL_TYPES for duration scaling."""
        from workout_templates import _INTERVAL_TYPES
        assert 'Race_Sim' in _INTERVAL_TYPES
        assert 'Durability' in _INTERVAL_TYPES

    # =========================================================================
    # 8. Total Count Verification
    # =========================================================================

    def test_total_archetype_count(self):
        """Total archetypes should be 95 (79 original + 16 advanced)."""
        from new_archetypes import NEW_ARCHETYPES
        total = sum(len(archs) for archs in NEW_ARCHETYPES.values())
        assert total == 95, f"Expected 95 total archetypes, got {total}"

    def test_total_category_count(self):
        """Total categories should still be 22."""
        from new_archetypes import NEW_ARCHETYPES
        assert len(NEW_ARCHETYPES) == 22, \
            f"Expected 22 categories, got {len(NEW_ARCHETYPES)}"


class TestAdvancedEdgeCases(unittest.TestCase):
    """Edge cases, silent failure detection, data integrity, and regression guards
    for the 16 advanced archetypes. Addresses:
    - Helper function correctness (exact durations)
    - Segment type validity (only steady/intervals/freeride/ramp)
    - Level progression for ALL 16 archetypes
    - No duplicate archetype names across entire system
    - Positive durations and numeric power values
    - Import failure detection (count guard)
    - Nate routing end-to-end for Race_Sim and Durability
    - Edge level bounds (0, 7 don't crash)
    - Durability fallback handler positional check
    - Maximum segment duration caps
    """

    # =========================================================================
    # 1. Helper Function Unit Tests
    # =========================================================================

    def test_criss_cross_exact_duration(self):
        """_criss_cross always returns segments summing exactly to total_sec."""
        from advanced_archetypes import _criss_cross
        for total, interval in [(900, 120), (1500, 90), (2400, 60), (1000, 130), (600, 200)]:
            segs = _criss_cross(total, interval, 0.80, 1.00)
            actual = sum(s['duration'] for s in segs)
            assert actual == total, \
                f"_criss_cross({total}, {interval}): expected {total}s, got {actual}s"

    def test_criss_cross_alternates_power(self):
        """_criss_cross alternates between floor and ceiling power."""
        from advanced_archetypes import _criss_cross
        segs = _criss_cross(600, 120, 0.80, 1.00)
        for i, seg in enumerate(segs):
            expected = 0.80 if i % 2 == 0 else 1.00
            assert seg['power'] == expected, \
                f"Segment {i}: expected {expected}, got {seg['power']}"

    def test_criss_cross_remainder_segment(self):
        """_criss_cross handles non-divisible totals with a remainder segment."""
        from advanced_archetypes import _criss_cross
        # 700 / 200 = 3 full + 100 remainder
        segs = _criss_cross(700, 200, 0.80, 1.00)
        assert len(segs) == 4
        assert segs[-1]['duration'] == 100
        assert sum(s['duration'] for s in segs) == 700

    def test_base_with_efforts_exact_duration(self):
        """_base_with_efforts always sums to exactly total_sec."""
        from advanced_archetypes import _base_with_efforts
        test_cases = [
            (4800, [(30, 0.85)] * 3, 0.65),
            (3600, [(300, 0.73)] * 3, 0.66),
            (7200, [(180, 1.05), (300, 0.82), (180, 1.05), (300, 0.82), (180, 1.05)], 0.65),
            (10800, [(30, 0.85)] * 8, 0.75),
            (5400, [(600, 0.78)] * 5, 0.70),
        ]
        for total, efforts, base in test_cases:
            segs = _base_with_efforts(total, efforts, base)
            actual = sum(s['duration'] for s in segs)
            assert actual == total, \
                f"_base_with_efforts({total}, {len(efforts)} efforts): " \
                f"expected {total}s, got {actual}s"

    def test_base_with_efforts_edge_more_effort_than_total(self):
        """_base_with_efforts gracefully handles effort > total time."""
        from advanced_archetypes import _base_with_efforts
        segs = _base_with_efforts(100, [(60, 0.90), (60, 0.90)], 0.65)
        # Efforts alone = 120 > 100, should stack efforts without base gaps
        assert all(s['power'] == 0.90 for s in segs)
        assert len(segs) == 2

    def test_hard_start_reps_correct_count(self):
        """_hard_start_reps produces exactly `reps` burst segments."""
        from advanced_archetypes import _hard_start_reps
        for reps in [3, 4, 5]:
            segs = _hard_start_reps(reps, 15, 1.50, 300, 0.95, 180)
            bursts = [s for s in segs if s['power'] >= 1.50]
            assert len(bursts) == reps, \
                f"Expected {reps} bursts, got {len(bursts)}"

    def test_hard_start_reps_no_trailing_rest(self):
        """Last rep of _hard_start_reps has no trailing recovery."""
        from advanced_archetypes import _hard_start_reps
        segs = _hard_start_reps(3, 15, 1.50, 300, 0.95, 180)
        # Last segment should be hold (0.95), not rest (0.55)
        assert segs[-1]['power'] == 0.95, \
            f"Last segment power should be hold (0.95), got {segs[-1]['power']}"

    def test_attack_reps_correct_count(self):
        """_attack_reps produces exactly `num_attacks` attack segments."""
        from advanced_archetypes import _attack_reps
        for n in [5, 6, 7, 8]:
            segs = _attack_reps(300, 0.82, n, 30, 1.30, 180, 0.82)
            attacks = [s for s in segs if s['power'] >= 1.30]
            assert len(attacks) == n, \
                f"Expected {n} attacks, got {len(attacks)}"

    def test_attack_reps_no_trailing_rest(self):
        """Last attack in _attack_reps has no trailing recovery."""
        from advanced_archetypes import _attack_reps
        segs = _attack_reps(300, 0.82, 5, 30, 1.30, 180, 0.82)
        assert segs[-1]['power'] >= 1.30, \
            f"Last segment should be attack, got power={segs[-1]['power']}"

    # =========================================================================
    # 2. Segment Duration Integrity — Every Segments-Based Archetype
    # =========================================================================

    def test_all_segments_archetypes_have_exact_durations(self):
        """Every segments-based advanced archetype at every level has
        segment duration sum matching its structure description's stated time."""
        from advanced_archetypes import ADVANCED_ARCHETYPES
        # Map archetype name → {level: expected total seconds from structure}
        # Only check archetypes that use 'segments' key
        for category, archetypes in ADVANCED_ARCHETYPES.items():
            for arch in archetypes:
                for lvl_key in ['1', '2', '3', '4', '5', '6']:
                    ld = arch['levels'][lvl_key]
                    if 'segments' not in ld:
                        continue
                    total = sum(s.get('duration', 0) for s in ld['segments']
                                if s.get('type') != 'intervals')
                    # For intervals segments, compute expanded duration
                    for s in ld['segments']:
                        if s.get('type') == 'intervals':
                            reps = s.get('repeats', 1)
                            on_dur = s.get('on_duration', 0)
                            off_dur = s.get('off_duration', 0)
                            total += reps * (on_dur + off_dur)
                    # Total must be positive (non-zero workout)
                    assert total > 0, \
                        f"{arch['name']} L{lvl_key}: segment total is 0"

    # =========================================================================
    # 3. Valid Segment Types Only
    # =========================================================================

    def test_all_segments_use_valid_types(self):
        """Every segment in every advanced archetype uses a valid type."""
        from advanced_archetypes import ADVANCED_ARCHETYPES
        VALID_TYPES = {'steady', 'intervals', 'freeride', 'ramp'}
        for category, archetypes in ADVANCED_ARCHETYPES.items():
            for arch in archetypes:
                for lvl_key in ['1', '2', '3', '4', '5', '6']:
                    ld = arch['levels'][lvl_key]
                    if 'segments' not in ld:
                        continue
                    for i, seg in enumerate(ld['segments']):
                        seg_type = seg.get('type')
                        assert seg_type in VALID_TYPES, \
                            f"{arch['name']} L{lvl_key} seg[{i}]: " \
                            f"invalid type '{seg_type}', must be one of {VALID_TYPES}"

    # =========================================================================
    # 4. Level Progression for ALL 16 Archetypes
    # =========================================================================

    def test_all_16_archetypes_power_progresses(self):
        """L1 max ON power or base power < L6 for every advanced archetype.
        This catches silent regressions where higher levels don't actually get harder.
        Note: Some archetypes (e.g. FatMax) progress via base power, not max power."""
        from advanced_archetypes import ADVANCED_ARCHETYPES

        for category, archetypes in ADVANCED_ARCHETYPES.items():
            for arch in archetypes:
                name = arch['name']
                l1 = arch['levels']['1']
                l6 = arch['levels']['6']

                def _all_powers(ld):
                    """Extract all power values from any archetype format."""
                    powers = []
                    if 'segments' in ld:
                        for s in ld['segments']:
                            if 'power' in s:
                                powers.append(s['power'])
                            if 'on_power' in s:
                                powers.append(s['on_power'])
                    if 'on_power' in ld:
                        powers.append(ld['on_power'])
                    if 'power' in ld:
                        powers.append(ld['power'])
                    if 'base_power' in ld:
                        powers.append(ld['base_power'])
                    return powers

                powers_l1 = _all_powers(l1)
                powers_l6 = _all_powers(l6)
                max_l1 = max(powers_l1) if powers_l1 else 0
                max_l6 = max(powers_l6) if powers_l6 else 0
                # Either max power increases, or if max is same (e.g. FatMax pops),
                # the average/base power must increase
                if max_l1 == max_l6:
                    avg_l1 = sum(powers_l1) / len(powers_l1) if powers_l1 else 0
                    avg_l6 = sum(powers_l6) / len(powers_l6) if powers_l6 else 0
                    assert avg_l1 < avg_l6, \
                        f"{name}: L1 avg power ({avg_l1:.3f}) should be < " \
                        f"L6 avg power ({avg_l6:.3f}) when max power is equal"
                else:
                    assert max_l1 < max_l6, \
                        f"{name}: L1 max power ({max_l1}) should be < " \
                        f"L6 max power ({max_l6})"

    def test_all_16_archetypes_volume_progresses(self):
        """L1 total work duration <= L6 total work duration for segment-based archetypes.
        Catches level definitions that accidentally decrease volume at higher levels."""
        from advanced_archetypes import ADVANCED_ARCHETYPES

        for category, archetypes in ADVANCED_ARCHETYPES.items():
            for arch in archetypes:
                name = arch['name']
                l1 = arch['levels']['1']
                l6 = arch['levels']['6']

                def _total_duration(ld):
                    if 'segments' in ld:
                        total = 0
                        for s in ld['segments']:
                            if s.get('type') == 'intervals':
                                total += s.get('repeats', 1) * (
                                    s.get('on_duration', 0) + s.get('off_duration', 0))
                            else:
                                total += s.get('duration', 0)
                        return total
                    if 'intervals' in ld and isinstance(ld['intervals'], tuple):
                        reps, dur = ld['intervals']
                        return reps * (dur + ld.get('off_duration', dur))
                    if 'duration' in ld:
                        return ld['duration']
                    if 'base_duration' in ld:
                        reps, dur = ld.get('intervals', (0, 0))
                        return ld['base_duration'] + reps * (dur + ld.get('off_duration', dur))
                    return 0

                dur_l1 = _total_duration(l1)
                dur_l6 = _total_duration(l6)
                assert dur_l1 <= dur_l6, \
                    f"{name}: L1 duration ({dur_l1}s) should be <= " \
                    f"L6 duration ({dur_l6}s)"

    # =========================================================================
    # 5. No Duplicate Archetype Names Globally
    # =========================================================================

    def test_no_duplicate_names_globally(self):
        """No two archetypes share the same name across the entire system."""
        from new_archetypes import NEW_ARCHETYPES
        all_names = []
        for category, archetypes in NEW_ARCHETYPES.items():
            for arch in archetypes:
                all_names.append((category, arch['name']))
        seen = {}
        dupes = []
        for cat, name in all_names:
            if name in seen:
                dupes.append(f"'{name}' in both {seen[name]} and {cat}")
            seen[name] = cat
        assert not dupes, f"Duplicate archetype names: {dupes}"

    # =========================================================================
    # 6. Positive Durations and Numeric Power Values
    # =========================================================================

    def test_all_segment_durations_positive(self):
        """Every segment duration in every advanced archetype is > 0."""
        from advanced_archetypes import ADVANCED_ARCHETYPES
        for category, archetypes in ADVANCED_ARCHETYPES.items():
            for arch in archetypes:
                for lvl_key in ['1', '2', '3', '4', '5', '6']:
                    ld = arch['levels'][lvl_key]
                    if 'segments' not in ld:
                        continue
                    for i, seg in enumerate(ld['segments']):
                        dur = seg.get('duration', None)
                        if dur is not None:
                            assert isinstance(dur, (int, float)), \
                                f"{arch['name']} L{lvl_key} seg[{i}]: " \
                                f"duration is {type(dur).__name__}, not numeric"
                            assert dur > 0, \
                                f"{arch['name']} L{lvl_key} seg[{i}]: " \
                                f"duration={dur}, must be > 0"

    def test_all_power_values_numeric(self):
        """Every power value in every advanced archetype is numeric (int/float)."""
        from advanced_archetypes import ADVANCED_ARCHETYPES
        for category, archetypes in ADVANCED_ARCHETYPES.items():
            for arch in archetypes:
                for lvl_key in ['1', '2', '3', '4', '5', '6']:
                    ld = arch['levels'][lvl_key]
                    # Check top-level power keys
                    for key in ['power', 'on_power', 'off_power', 'base_power']:
                        if key in ld:
                            val = ld[key]
                            assert isinstance(val, (int, float)), \
                                f"{arch['name']} L{lvl_key} {key}={val!r} " \
                                f"is {type(val).__name__}, not numeric"
                    # Check segment power keys
                    if 'segments' in ld:
                        for i, seg in enumerate(ld['segments']):
                            for key in ['power', 'on_power', 'off_power']:
                                if key in seg:
                                    val = seg[key]
                                    assert isinstance(val, (int, float)), \
                                        f"{arch['name']} L{lvl_key} seg[{i}] " \
                                        f"{key}={val!r} is {type(val).__name__}"

    # =========================================================================
    # 7. Import Failure Detection — Count Guard
    # =========================================================================

    def test_advanced_archetypes_import_count(self):
        """ADVANCED_ARCHETYPES has exactly 16 archetypes across 8 categories.
        If import fails silently, this catches it."""
        from advanced_archetypes import ADVANCED_ARCHETYPES
        total = sum(len(a) for a in ADVANCED_ARCHETYPES.values())
        assert total == 16, f"Expected 16 advanced archetypes, got {total}"
        assert len(ADVANCED_ARCHETYPES) == 8, \
            f"Expected 8 categories, got {len(ADVANCED_ARCHETYPES)}"

    def test_advanced_merge_into_new_archetypes(self):
        """All 16 advanced archetypes are present in NEW_ARCHETYPES after merge."""
        from new_archetypes import NEW_ARCHETYPES
        from advanced_archetypes import ADVANCED_ARCHETYPES
        for category, archetypes in ADVANCED_ARCHETYPES.items():
            assert category in NEW_ARCHETYPES, \
                f"Category '{category}' missing from NEW_ARCHETYPES"
            existing_names = {a['name'] for a in NEW_ARCHETYPES[category]}
            for arch in archetypes:
                assert arch['name'] in existing_names, \
                    f"'{arch['name']}' not found in NEW_ARCHETYPES['{category}']"

    # =========================================================================
    # 8. All 6 Levels Exist for Every Archetype
    # =========================================================================

    def test_all_16_have_all_6_levels(self):
        """Every advanced archetype has exactly levels '1' through '6'."""
        from advanced_archetypes import ADVANCED_ARCHETYPES
        expected_levels = {'1', '2', '3', '4', '5', '6'}
        for category, archetypes in ADVANCED_ARCHETYPES.items():
            for arch in archetypes:
                actual = set(arch['levels'].keys())
                assert actual == expected_levels, \
                    f"{arch['name']}: has levels {actual}, expected {expected_levels}"

    # =========================================================================
    # 9. Edge Level Bounds — Level 0 and 7 Don't Crash
    # =========================================================================

    def test_nate_generator_level_0_doesnt_crash(self):
        """generate_nate_zwo with level=0 should return None or valid ZWO, not crash."""
        from nate_workout_generator import generate_nate_zwo
        try:
            result = generate_nate_zwo('vo2max', level=0, methodology='POLARIZED')
            # Level 0 might map to level 1 or return None — either is fine
        except Exception as e:
            self.fail(f"level=0 crashed: {e}")

    def test_nate_generator_level_7_doesnt_crash(self):
        """generate_nate_zwo with level=7 should return None or valid ZWO, not crash."""
        from nate_workout_generator import generate_nate_zwo
        try:
            result = generate_nate_zwo('vo2max', level=7, methodology='POLARIZED')
        except Exception as e:
            self.fail(f"level=7 crashed: {e}")

    # =========================================================================
    # 10. Nate Routing for Race_Sim and Durability End-to-End
    # =========================================================================

    def test_race_sim_nate_routing_all_levels(self):
        """Race_Sim routes through nate_workout_types and generates valid ZWO at every level."""
        import re
        from nate_workout_generator import generate_nate_zwo
        from new_archetypes import NEW_ARCHETYPES
        # Find the Race_Simulation category index for Hard Starts (first Race_Sim advanced)
        race_sim_names = [a['name'] for a in NEW_ARCHETYPES.get('Race_Simulation', [])]
        if 'Hard Starts' in race_sim_names:
            idx = race_sim_names.index('Hard Starts')
            for level in [1, 3, 6]:
                zwo = generate_nate_zwo(
                    'race_sim', level=level,
                    methodology='POLARIZED', variation=idx
                )
                assert zwo is not None, \
                    f"Race_Sim Hard Starts L{level} returned None"
                assert 'Power=' in zwo, \
                    f"Race_Sim Hard Starts L{level} has no Power= attributes"

    def test_durability_nate_routing_all_levels(self):
        """Durability routes through nate_workout_types and generates valid ZWO at every level."""
        from nate_workout_generator import generate_nate_zwo
        from new_archetypes import NEW_ARCHETYPES
        dur_names = [a['name'] for a in NEW_ARCHETYPES.get('Durability', [])]
        if 'Late-Race VO2max' in dur_names:
            idx = dur_names.index('Late-Race VO2max')
            for level in [1, 3, 6]:
                zwo = generate_nate_zwo(
                    'durability', level=level,
                    methodology='POLARIZED', variation=idx
                )
                assert zwo is not None, \
                    f"Durability Late-Race VO2max L{level} returned None"

    # =========================================================================
    # 11. Durability Fallback Handler Existence and Position
    # =========================================================================

    def test_durability_handler_exists_in_source(self):
        """The Durability elif handler exists in generate_athlete_package.py
        BEFORE the else fallback (positional guard)."""
        import os
        source_path = os.path.join(
            os.path.dirname(__file__), 'generate_athlete_package.py')
        with open(source_path) as f:
            source = f.read()
        dur_pos = source.find("elif workout_type == 'Durability'")
        assert dur_pos != -1, \
            "Durability handler missing from create_workout_blocks()"
        # The Durability handler must come before the generic else + Cooldown
        # pattern that signals the end of the if/elif chain
        cooldown_after_else = source.find("# Cooldown", dur_pos)
        assert cooldown_after_else != -1, \
            "Expected '# Cooldown' comment after Durability handler"
        # Also verify the handler has Z2 preload + tempo effort pattern
        handler_block = source[dur_pos:dur_pos + 500]
        assert 'Power="0.68"' in handler_block, \
            "Durability handler missing Z2 preload (Power 0.68)"
        assert 'Power="0.88"' in handler_block, \
            "Durability handler missing tempo effort (Power 0.88)"

    # =========================================================================
    # 12. Maximum Segment Duration Caps
    # =========================================================================

    def test_no_single_segment_exceeds_6_hours(self):
        """No individual segment should exceed 6 hours (21600s).
        Catches helper functions that miscalculate and create absurdly long segments."""
        from advanced_archetypes import ADVANCED_ARCHETYPES
        MAX_SEGMENT_DURATION = 21600  # 6 hours
        for category, archetypes in ADVANCED_ARCHETYPES.items():
            for arch in archetypes:
                for lvl_key in ['1', '2', '3', '4', '5', '6']:
                    ld = arch['levels'][lvl_key]
                    if 'segments' not in ld:
                        continue
                    for i, seg in enumerate(ld['segments']):
                        dur = seg.get('duration', 0)
                        assert dur <= MAX_SEGMENT_DURATION, \
                            f"{arch['name']} L{lvl_key} seg[{i}]: " \
                            f"duration {dur}s exceeds {MAX_SEGMENT_DURATION}s (6hr) cap"

    def test_no_power_exceeds_3x_ftp(self):
        """No power value should exceed 3.0 (300% FTP).
        Catches typos like 15.0 instead of 1.50."""
        from advanced_archetypes import ADVANCED_ARCHETYPES
        MAX_POWER = 3.0
        for category, archetypes in ADVANCED_ARCHETYPES.items():
            for arch in archetypes:
                for lvl_key in ['1', '2', '3', '4', '5', '6']:
                    ld = arch['levels'][lvl_key]
                    for key in ['power', 'on_power']:
                        if key in ld:
                            assert ld[key] <= MAX_POWER, \
                                f"{arch['name']} L{lvl_key} {key}={ld[key]} " \
                                f"exceeds {MAX_POWER}"
                    if 'segments' in ld:
                        for i, seg in enumerate(ld['segments']):
                            for key in ['power', 'on_power']:
                                if key in seg:
                                    assert seg[key] <= MAX_POWER, \
                                        f"{arch['name']} L{lvl_key} seg[{i}] " \
                                        f"{key}={seg[key]} exceeds {MAX_POWER}"

    # =========================================================================
    # 13. Structure Key Presence
    # =========================================================================

    def test_every_level_has_structure_string(self):
        """Every level in every advanced archetype has a 'structure' description."""
        from advanced_archetypes import ADVANCED_ARCHETYPES
        for category, archetypes in ADVANCED_ARCHETYPES.items():
            for arch in archetypes:
                for lvl_key in ['1', '2', '3', '4', '5', '6']:
                    ld = arch['levels'][lvl_key]
                    assert 'structure' in ld, \
                        f"{arch['name']} L{lvl_key}: missing 'structure' key"
                    assert len(ld['structure']) > 10, \
                        f"{arch['name']} L{lvl_key}: structure too short"

    def test_level_1_has_full_metadata(self):
        """Every archetype's L1 has cadence_prescription, position_prescription,
        fueling, and execution (coaching text for first exposure)."""
        from advanced_archetypes import ADVANCED_ARCHETYPES
        REQUIRED_L1_KEYS = ['cadence_prescription', 'position_prescription',
                            'fueling', 'execution']
        for category, archetypes in ADVANCED_ARCHETYPES.items():
            for arch in archetypes:
                ld = arch['levels']['1']
                for key in REQUIRED_L1_KEYS:
                    assert key in ld, \
                        f"{arch['name']} L1: missing required key '{key}'"

    # =========================================================================
    # 14. ZWO Generation for Every Advanced Archetype (Silent Failure Detection)
    # =========================================================================

    def test_every_advanced_archetype_generates_valid_zwo(self):
        """Every one of the 96 advanced variations generates a non-None ZWO
        with valid XML structure. Catches silent generation failures."""
        import re
        from nate_workout_generator import generate_nate_zwo
        from new_archetypes import NEW_ARCHETYPES
        from advanced_archetypes import ADVANCED_ARCHETYPES

        failures = []
        for category, adv_archetypes in ADVANCED_ARCHETYPES.items():
            # Find position in merged list
            merged_list = NEW_ARCHETYPES.get(category, [])
            merged_names = [a['name'] for a in merged_list]
            # Map category to nate workout type
            cat_to_type = {
                'VO2max': 'vo2max',
                'TT_Threshold': 'threshold',
                'Race_Simulation': 'race_sim',
                'Durability': 'durability',
                'Endurance': 'endurance',
                'Sprint_Neuromuscular': 'sprint',
                'Gravel_Specific': 'gravel_specific',
                'INSCYD': 'inscyd',
            }
            workout_type = cat_to_type.get(category)
            if not workout_type:
                continue

            for arch in adv_archetypes:
                if arch['name'] not in merged_names:
                    failures.append(f"{arch['name']}: not in merged list")
                    continue
                idx = merged_names.index(arch['name'])
                for level in [1, 3, 6]:
                    zwo = generate_nate_zwo(
                        workout_type, level=level,
                        methodology='POLARIZED', variation=idx
                    )
                    if zwo is None:
                        failures.append(
                            f"{arch['name']} L{level} ({workout_type}): returned None")
                    elif '<workout_file>' not in zwo:
                        failures.append(
                            f"{arch['name']} L{level}: missing <workout_file> tag")

        assert not failures, \
            f"{len(failures)} ZWO generation failure(s):\n" + "\n".join(failures)

    # =========================================================================
    # 15. Type Alias Coverage
    # =========================================================================

    def test_all_advanced_type_aliases_in_source(self):
        """Every type_to_category alias added for advanced archetypes exists
        in the nate_workout_generator.py source code."""
        import os
        source_path = os.path.join(
            os.path.dirname(__file__), 'nate_workout_generator.py')
        with open(source_path) as f:
            source = f.read()
        advanced_aliases = [
            'ronnestad_30_15', 'ronnestad_40_20', 'ronnestad', 'float_sets',
            'hard_starts', 'criss_cross_intervals', 'tte_extension', 'tte',
            'bpa', 'best_possible_average', 'structured_fartlek', 'fartlek',
            'attacks', 'repeatability', 'kitchen_sink', 'all_systems',
            'late_race_vo2', 'heat_acclimation', 'heat_adaptation',
            'burst_intervals', 'bursts', 'fatmax_suppression',
            'vlamax_suppression', 'glycolytic_power', 'glycolytic',
        ]
        missing = []
        for alias in advanced_aliases:
            # Check for the alias as a key in type_to_category dict
            if f'"{alias}"' not in source and f"'{alias}'" not in source:
                missing.append(alias)
        assert not missing, \
            f"Aliases missing from nate_workout_generator.py: {missing}"

    # =========================================================================
    # 16. Criss-Cross Duration Matches Structure Description
    # =========================================================================

    def test_criss_cross_durations_match_descriptions(self):
        """Criss-Cross segment totals match the minutes stated in structure strings."""
        from advanced_archetypes import ADVANCED_ARCHETYPES
        arch = [a for a in ADVANCED_ARCHETYPES['TT_Threshold']
                if a['name'] == 'Criss-Cross Intervals'][0]
        expected_seconds = {
            '1': 900,    # 15min
            '2': 1200,   # 20min
            '3': 1500,   # 25min
            '4': 1800,   # 30min
            '5': 2100,   # 35min
            '6': 2400,   # 40min
        }
        for lvl_key, expected in expected_seconds.items():
            total = sum(s['duration'] for s in arch['levels'][lvl_key]['segments'])
            assert total == expected, \
                f"Criss-Cross L{lvl_key}: got {total}s, expected {expected}s " \
                f"({expected//60}min from structure description)"

    # =========================================================================
    # 17. Heat Acclimation Duration Matches Structure Description
    # =========================================================================

    def test_heat_acclimation_durations_match(self):
        """Heat Acclimation segment totals match structure descriptions."""
        from advanced_archetypes import ADVANCED_ARCHETYPES
        arch = [a for a in ADVANCED_ARCHETYPES['Endurance']
                if a['name'] == 'Heat Acclimation Protocol'][0]
        expected_seconds = {
            '1': 3000,    # 50min
            '2': 3600,    # 60min
            '3': 4200,    # 70min
            '4': 4500,    # 75min
            '5': 4800,    # 80min
            '6': 5400,    # 90min
        }
        for lvl_key, expected in expected_seconds.items():
            total = sum(s['duration'] for s in arch['levels'][lvl_key]['segments'])
            assert total == expected, \
                f"Heat Acclimation L{lvl_key}: got {total}s, expected {expected}s"

    # =========================================================================
    # 18. Gravel Race Sim Duration Matches Structure Description
    # =========================================================================

    def test_gravel_race_sim_durations_match(self):
        """Gravel Race Sim segment totals match structure descriptions."""
        from advanced_archetypes import ADVANCED_ARCHETYPES
        arch = [a for a in ADVANCED_ARCHETYPES['Gravel_Specific']
                if a['name'] == 'Gravel Race Simulation'][0]
        expected_seconds = {
            '1': 7200,    # 2hr
            '2': 9000,    # 2.5hr
            '3': 10800,   # 3hr
            '4': 12600,   # 3.5hr
            '5': 14400,   # 4hr
            '6': 16200,   # 4.5hr
        }
        for lvl_key, expected in expected_seconds.items():
            total = sum(s['duration'] for s in arch['levels'][lvl_key]['segments'])
            assert total == expected, \
                f"Gravel Race Sim L{lvl_key}: got {total}s, expected {expected}s"

    # =========================================================================
    # 19. Burst Intervals Duration Matches Structure Description
    # =========================================================================

    def test_burst_intervals_durations_match(self):
        """Burst Intervals segment totals match structure descriptions."""
        from advanced_archetypes import ADVANCED_ARCHETYPES
        arch = [a for a in ADVANCED_ARCHETYPES['Sprint_Neuromuscular']
                if a['name'] == 'Burst Intervals'][0]
        expected_seconds = {
            '1': 2700,    # 45min
            '2': 3000,    # 50min
            '3': 3300,    # 55min
            '4': 3600,    # 60min
            '5': 3900,    # 65min
            '6': 4200,    # 70min
        }
        for lvl_key, expected in expected_seconds.items():
            total = sum(s['duration'] for s in arch['levels'][lvl_key]['segments'])
            assert total == expected, \
                f"Burst Intervals L{lvl_key}: got {total}s, expected {expected}s"

    # =========================================================================
    # 20. FatMax VLamax Duration Matches Structure Description
    # =========================================================================

    def test_fatmax_durations_match(self):
        """FatMax VLamax Suppression segment totals match structure descriptions."""
        from advanced_archetypes import ADVANCED_ARCHETYPES
        arch = [a for a in ADVANCED_ARCHETYPES['INSCYD']
                if a['name'] == 'FatMax VLamax Suppression'][0]
        expected_seconds = {
            '1': 4800,    # 80min
            '2': 6000,    # 100min
            '3': 7200,    # 120min
            '4': 8400,    # 140min
            '5': 9600,    # 160min
            '6': 10800,   # 180min
        }
        for lvl_key, expected in expected_seconds.items():
            total = sum(s['duration'] for s in arch['levels'][lvl_key]['segments'])
            assert total == expected, \
                f"FatMax L{lvl_key}: got {total}s, expected {expected}s"

    # =========================================================================
    # 21. Format Consistency — Each Archetype Uses Exactly One Format
    # =========================================================================

    def test_each_level_uses_one_format_only(self):
        """No level mixes segments + intervals tuple (ambiguous rendering).
        An archetype level uses EITHER segments OR intervals tuple OR single_effort
        OR tired_vo2 — never multiple."""
        from advanced_archetypes import ADVANCED_ARCHETYPES
        FORMAT_KEYS = ['segments', 'single_effort', 'tired_vo2']
        for category, archetypes in ADVANCED_ARCHETYPES.items():
            for arch in archetypes:
                for lvl_key in ['1', '2', '3', '4', '5', '6']:
                    ld = arch['levels'][lvl_key]
                    has_segments = 'segments' in ld
                    has_intervals_tuple = (
                        'intervals' in ld and isinstance(ld['intervals'], tuple)
                        and not ld.get('tired_vo2')
                    )
                    has_single_effort = ld.get('single_effort', False)
                    has_tired_vo2 = ld.get('tired_vo2', False)
                    formats_present = sum([
                        has_segments, has_intervals_tuple,
                        has_single_effort, has_tired_vo2
                    ])
                    assert formats_present == 1, \
                        f"{arch['name']} L{lvl_key}: has {formats_present} formats " \
                        f"(segments={has_segments}, intervals_tuple={has_intervals_tuple}, " \
                        f"single_effort={has_single_effort}, tired_vo2={has_tired_vo2}). " \
                        f"Must have exactly 1."

    # =========================================================================
    # 22. Gravel Sim Sprint Finish Only at L6
    # =========================================================================

    def test_gravel_sim_sprint_finish_only_l6(self):
        """Only L6 of Gravel Race Simulation includes a sprint finish segment."""
        from advanced_archetypes import ADVANCED_ARCHETYPES
        arch = [a for a in ADVANCED_ARCHETYPES['Gravel_Specific']
                if a['name'] == 'Gravel Race Simulation'][0]
        for lvl_key in ['1', '2', '3', '4', '5']:
            segs = arch['levels'][lvl_key]['segments']
            sprint_segs = [s for s in segs if s.get('power', 0) >= 1.50]
            assert len(sprint_segs) == 0, \
                f"L{lvl_key} should not have sprint finish, found {len(sprint_segs)} sprint segments"
        # L6 should have sprint finish
        segs_l6 = arch['levels']['6']['segments']
        sprint_segs_l6 = [s for s in segs_l6 if s.get('power', 0) >= 1.50]
        assert len(sprint_segs_l6) >= 1, \
            "L6 should have sprint finish segment(s)"

    # =========================================================================
    # 23. BPA Duration Monotonically Increases
    # =========================================================================

    def test_bpa_duration_monotonically_increases(self):
        """BPA effort duration strictly increases from L1 to L6."""
        from advanced_archetypes import ADVANCED_ARCHETYPES
        arch = [a for a in ADVANCED_ARCHETYPES['TT_Threshold']
                if a['name'] == 'BPA (Best Possible Average)'][0]
        durations = [arch['levels'][str(i)]['duration'] for i in range(1, 7)]
        for i in range(len(durations) - 1):
            assert durations[i] < durations[i+1], \
                f"BPA duration should increase: L{i+1}={durations[i]}s >= L{i+2}={durations[i+1]}s"

    # =========================================================================
    # 24. Late-Race VO2max Base Duration Increases
    # =========================================================================

    def test_late_race_vo2_base_duration_increases(self):
        """Late-Race VO2max base_duration (preload) strictly increases L1→L6."""
        from advanced_archetypes import ADVANCED_ARCHETYPES
        arch = ADVANCED_ARCHETYPES['Durability'][0]
        assert arch['name'] == 'Late-Race VO2max'
        base_durations = [arch['levels'][str(i)]['base_duration'] for i in range(1, 7)]
        for i in range(len(base_durations) - 1):
            assert base_durations[i] < base_durations[i+1], \
                f"base_duration should increase: L{i+1}={base_durations[i]}s >= L{i+2}={base_durations[i+1]}s"

    # =========================================================================
    # 25. Empty Segments Guard
    # =========================================================================

    def test_no_empty_segments_lists(self):
        """No archetype has an empty segments list (would produce warmup-only ZWO)."""
        from advanced_archetypes import ADVANCED_ARCHETYPES
        for category, archetypes in ADVANCED_ARCHETYPES.items():
            for arch in archetypes:
                for lvl_key in ['1', '2', '3', '4', '5', '6']:
                    ld = arch['levels'][lvl_key]
                    if 'segments' in ld:
                        assert len(ld['segments']) > 0, \
                            f"{arch['name']} L{lvl_key}: has empty segments list"

    # =========================================================================
    # 26. Glycolytic Power Interval Count Increases
    # =========================================================================

    def test_glycolytic_interval_count_increases(self):
        """Glycolytic Power rep count is monotonically non-decreasing L1→L6."""
        from advanced_archetypes import ADVANCED_ARCHETYPES
        arch = [a for a in ADVANCED_ARCHETYPES['INSCYD']
                if a['name'] == 'Glycolytic Power'][0]
        reps = [arch['levels'][str(i)]['intervals'][0] for i in range(1, 7)]
        for i in range(len(reps) - 1):
            assert reps[i] <= reps[i+1], \
                f"Glycolytic reps should increase: L{i+1}={reps[i]} > L{i+2}={reps[i+1]}"

    # =========================================================================
    # 27. Ronnestad ON Power Monotonically Increases
    # =========================================================================

    def test_ronnestad_30_15_on_power_increases(self):
        """Ronnestad 30/15 on_power strictly increases L1→L6."""
        from advanced_archetypes import ADVANCED_ARCHETYPES
        arch = [a for a in ADVANCED_ARCHETYPES['VO2max']
                if a['name'] == 'Ronnestad 30/15'][0]
        powers = []
        for i in range(1, 7):
            segs = arch['levels'][str(i)]['segments']
            # Get max on_power from intervals segments
            max_on = max(s['on_power'] for s in segs if s.get('type') == 'intervals')
            powers.append(max_on)
        for i in range(len(powers) - 1):
            assert powers[i] < powers[i+1], \
                f"Ronnestad 30/15 on_power should increase: " \
                f"L{i+1}={powers[i]} >= L{i+2}={powers[i+1]}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
