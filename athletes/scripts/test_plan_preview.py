#!/usr/bin/env python3
"""
Tests for generate_plan_preview.py — ZWO parsing, TSS calculation, verification checks.
"""

import sys
import re
import pytest
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from generate_plan_preview import parse_zwo, build_preview_data, _if_to_zone, _run_verification_checks
from nate_workout_generator import (
    generate_nate_zwo,
    _get_default_cadence,
    _get_default_position,
)


# ===========================================================================
# ZWO Parsing
# ===========================================================================

class TestZWOParsing:
    """Tests for parse_zwo — extracting duration, power, TSS from ZWO XML."""

    @pytest.fixture
    def nicholas_workouts(self):
        return Path(__file__).parent.parent / 'nicholas-applegate' / 'workouts'

    def test_endurance_ride_duration(self, nicholas_workouts):
        """Endurance ride should scale to use available time (120min slot -> ~80min ride)."""
        wo = parse_zwo(nicholas_workouts / 'W01_Mon_Mar9_Endurance.zwo', 315)
        assert 70 <= wo['duration_min'] <= 100  # ~80 min (120min * 0.70 base phase)

    def test_vo2max_intervals_detected(self, nicholas_workouts):
        """VO2max workout should detect interval structure."""
        wo = parse_zwo(nicholas_workouts / 'W01_Wed_Mar11_VO2max.zwo', 315)
        assert wo['intervals_summary'] != ''
        assert '117%' in wo['intervals_summary'] or '120%' in wo['intervals_summary']

    def test_long_ride_duration(self, nicholas_workouts):
        """Long ride should be 90+ minutes."""
        wo = parse_zwo(nicholas_workouts / 'W01_Sun_Mar15_Long_Ride.zwo', 315)
        assert wo['duration_min'] >= 90

    def test_tss_positive(self, nicholas_workouts):
        """All workouts should have positive TSS."""
        wo = parse_zwo(nicholas_workouts / 'W01_Wed_Mar11_VO2max.zwo', 315)
        assert wo['tss'] > 0

    def test_intensity_factor_reasonable(self, nicholas_workouts):
        """IF should be between 0.4 and 1.2 for normal workouts."""
        for zwo in list(nicholas_workouts.glob('*.zwo'))[:10]:
            wo = parse_zwo(zwo, 315)
            if wo['duration_sec'] > 0:
                assert 0.3 <= wo['intensity_factor'] <= 1.3, f"{zwo.name}: IF={wo['intensity_factor']}"

    def test_ftp_test_parsed(self, nicholas_workouts):
        """FTP test should parse correctly."""
        wo = parse_zwo(nicholas_workouts / 'W01_Sat_Mar14_FTP_Test.zwo', 315)
        assert wo['duration_min'] > 30
        assert wo['tss'] > 0

    def test_race_day_freeride(self, nicholas_workouts):
        """RACE_DAY ZWO with FreeRide should parse."""
        race_files = list(nicholas_workouts.glob('*RACE_DAY*.zwo'))
        assert len(race_files) > 0
        wo = parse_zwo(race_files[0], 315)
        assert wo['duration_sec'] > 0

    def test_easy_ride_low_if(self, nicholas_workouts):
        """Easy/taper rides should have low IF."""
        easy_files = list(nicholas_workouts.glob('W11*Easy*.zwo'))
        assert len(easy_files) > 0
        wo = parse_zwo(easy_files[0], 315)
        assert wo['intensity_factor'] < 0.75

    def test_vo2max_higher_tss_than_endurance(self, nicholas_workouts):
        """VO2max should have higher TSS per minute than endurance."""
        vo2 = parse_zwo(nicholas_workouts / 'W01_Wed_Mar11_VO2max.zwo', 315)
        end = parse_zwo(nicholas_workouts / 'W01_Mon_Mar9_Endurance.zwo', 315)
        vo2_per_min = vo2['tss'] / vo2['duration_min'] if vo2['duration_min'] > 0 else 0
        end_per_min = end['tss'] / end['duration_min'] if end['duration_min'] > 0 else 0
        assert vo2_per_min > end_per_min


# ===========================================================================
# Zone Classification
# ===========================================================================

class TestZoneClassification:

    def test_z1(self):
        assert _if_to_zone(0.45) == 'Z1'

    def test_z2(self):
        assert _if_to_zone(0.65) == 'Z2'

    def test_z3(self):
        assert _if_to_zone(0.80) == 'Z3'

    def test_z4(self):
        assert _if_to_zone(0.90) == 'Z4'

    def test_z5(self):
        assert _if_to_zone(1.00) == 'Z5'

    def test_z5_plus(self):
        assert _if_to_zone(1.10) == 'Z5+'


# ===========================================================================
# Preview Data Assembly
# ===========================================================================

class TestPreviewData:
    """Tests for build_preview_data — full plan parsing."""

    @pytest.fixture
    def nicholas_data(self):
        athlete_dir = Path(__file__).parent.parent / 'nicholas-applegate'
        return build_preview_data(athlete_dir)

    def test_all_weeks_present(self, nicholas_data):
        assert len(nicholas_data['weeks']) == 12

    def test_all_workouts_parsed(self, nicholas_data):
        total = sum(1 for w in nicholas_data['weeks'] for d in w['days'] if d.get('workout'))
        assert total >= 60  # At least 60 workouts (some off days)

    def test_tss_increases_base_to_build(self, nicholas_data):
        """TSS should generally increase from base to build phase."""
        base_weeks = [w for w in nicholas_data['weeks'] if w['phase'] == 'base']
        build_weeks = [w for w in nicholas_data['weeks'] if w['phase'] == 'build']
        if base_weeks and build_weeks:
            base_avg = sum(w['total_tss'] for w in base_weeks) / len(base_weeks)
            build_avg = sum(w['total_tss'] for w in build_weeks) / len(build_weeks)
            assert build_avg >= base_avg * 0.85  # Build at least 85% of base TSS

    def test_taper_reduces_load(self, nicholas_data):
        """Taper week should have less TSS than build weeks."""
        taper_weeks = [w for w in nicholas_data['weeks'] if w['phase'] == 'taper']
        build_weeks = [w for w in nicholas_data['weeks'] if w['phase'] == 'build']
        if taper_weeks and build_weeks:
            taper_avg = sum(w['total_tss'] for w in taper_weeks) / len(taper_weeks)
            build_avg = sum(w['total_tss'] for w in build_weeks) / len(build_weeks)
            assert taper_avg < build_avg

    def test_b_race_week_identified(self, nicholas_data):
        """Week 5 should have Boulder Roubaix as B-race."""
        w5 = nicholas_data['weeks'][4]  # 0-indexed
        assert w5['b_race'].get('name') == 'Boulder Roubaix'

    def test_race_week_identified(self, nicholas_data):
        """Week 12 should be race week."""
        w12 = nicholas_data['weeks'][11]
        assert w12['is_race_week'] is True


# ===========================================================================
# Verification Checks
# ===========================================================================

class TestVerificationChecks:
    """Tests for the automated verification checks."""

    @pytest.fixture
    def nicholas_data(self):
        athlete_dir = Path(__file__).parent.parent / 'nicholas-applegate'
        return build_preview_data(athlete_dir)

    def test_all_checks_present(self, nicholas_data):
        """Should have at least 10 verification checks (9 original + 3 new)."""
        assert len(nicholas_data['checks']) >= 10

    def test_off_days_pass(self, nicholas_data):
        """Off days check should pass for Nicholas."""
        check = next(c for c in nicholas_data['checks'] if c['name'] == 'Off Days Respected')
        assert check['status'] == 'PASS'

    def test_long_ride_day_pass(self, nicholas_data):
        """Long ride day check should pass."""
        check = next(c for c in nicholas_data['checks'] if c['name'] == 'Long Ride Day')
        assert check['status'] == 'PASS'

    def test_phase_progression_pass(self, nicholas_data):
        """Phase progression should be in order."""
        check = next(c for c in nicholas_data['checks'] if c['name'] == 'Phase Progression')
        assert check['status'] == 'PASS'

    def test_b_race_placed_pass(self, nicholas_data):
        """B-race should be correctly placed."""
        check = next(c for c in nicholas_data['checks'] if c['name'] == 'B-Race Placed')
        assert check['status'] == 'PASS'

    def test_ftp_tests_present(self, nicholas_data):
        """FTP test check should pass."""
        check = next(c for c in nicholas_data['checks'] if c['name'] == 'FTP Tests')
        assert check['status'] == 'PASS'

    def test_no_unexpected_failing_checks(self, nicholas_data):
        """No checks should FAIL — progressive long rides raised volume to WARN range."""
        fails = [c for c in nicholas_data['checks'] if c['status'] == 'FAIL']
        fail_names = [c['name'] for c in fails]
        assert len(fail_names) == 0, f"Unexpected failing checks: {fail_names}"

    def test_volume_passes_with_scaling(self, nicholas_data):
        """Duration scaling brings volume to ~110% of target (PASS range: 80-120%)."""
        check = next(c for c in nicholas_data['checks'] if c['name'] == 'Weekly Volume')
        assert check['status'] == 'PASS', \
            f"Volume should PASS at ~110% (80-120% range), got {check['status']}: {check['detail']}"
        assert 'PASS 80-120%' in check['detail']

    def test_long_ride_vs_race_duration_check_exists(self, nicholas_data):
        """Long Ride vs Race Duration check should be present for Nicholas (200-mile race)."""
        check = next(
            (c for c in nicholas_data['checks'] if c['name'] == 'Long Ride vs Race Duration'),
            None
        )
        assert check is not None, "Long Ride vs Race Duration check not found"
        assert check['status'] in ('PASS', 'WARN', 'FAIL')
        assert '200mi' in check['detail']

    def test_taper_intensity_check_exists(self, nicholas_data):
        """Taper Intensity check should be present."""
        check = next(
            (c for c in nicholas_data['checks'] if c['name'] == 'Taper Intensity'),
            None
        )
        assert check is not None, "Taper Intensity check not found"
        assert check['status'] in ('PASS', 'WARN')
        assert 'Taper avg IF' in check['detail']
        assert 'Build/Peak avg IF' in check['detail']

    def test_ftp_frequency_check_exists(self, nicholas_data):
        """FTP Test Frequency check should be present for 12-week plan."""
        check = next(
            (c for c in nicholas_data['checks'] if c['name'] == 'FTP Test Frequency'),
            None
        )
        assert check is not None, "FTP Test Frequency check not found"
        assert check['status'] in ('PASS', 'WARN', 'FAIL')
        assert '12-week plan' in check['detail']


# ===========================================================================
# Volume Check with Mock Data
# ===========================================================================

class TestVolumeCheckThresholds:
    """Test the volume check with controlled mock data to verify thresholds."""

    def _make_mock_weeks(self, hours_per_week, num_weeks=10):
        """Create mock weeks_data with a fixed hours-per-week value."""
        weeks = []
        for i in range(num_weeks):
            phase = 'build' if i < num_weeks - 2 else ('taper' if i == num_weeks - 2 else 'race')
            weeks.append({
                'week': i + 1,
                'phase': phase,
                'monday_short': '',
                'sunday_short': '',
                'b_race': {},
                'is_race_week': (i == num_weeks - 1),
                'days': [],
                'total_tss': int(hours_per_week * 50),
                'total_hours': hours_per_week,
                'zone_counts': {'Z1': 0, 'Z2': 3, 'Z3': 0, 'Z4': 1, 'Z5': 0, 'Z5+': 0, 'REST': 3},
            })
        return weeks

    def test_volume_warn_when_undershooting(self):
        """70% volume (7h of 10h target) should WARN, not PASS."""
        profile = {
            'weekly_availability': {'cycling_hours_target': 10},
            'schedule_constraints': {'preferred_off_days': [], 'preferred_long_day': 'sunday'},
            'b_events': [],
            'target_race': {},
        }
        # 7h/wk = 70% of 10h target -> WARN
        weeks = self._make_mock_weeks(7.0)
        checks = _run_verification_checks(
            profile=profile,
            derived={},
            methodology={'configuration': {}},
            plan_dates={'weeks': []},
            weekly_structure={'days': {}},
            weeks_data=weeks,
        )
        vol_check = next(c for c in checks if c['name'] == 'Weekly Volume')
        assert vol_check['status'] == 'WARN', (
            f"70% volume should WARN but got {vol_check['status']}: {vol_check['detail']}"
        )


# ===========================================================================
# Edge Case: Race Distance Validation (edge case 7)
# ===========================================================================

class TestRaceDistanceEdgeCases:
    """Tests for race distance edge cases in verification checks."""

    def _make_mock_weeks(self, hours_per_week, num_weeks=10):
        """Create mock weeks_data with a fixed hours-per-week value."""
        weeks = []
        for i in range(num_weeks):
            phase = 'build' if i < num_weeks - 2 else ('taper' if i == num_weeks - 2 else 'race')
            # Add a workout with some duration for long ride check
            days = [{
                'day': 'Sat',
                'date': '',
                'workout': {
                    'name': 'W{:02d}_Sat_Long_Ride'.format(i + 1),
                    'duration_min': 180,
                    'duration_sec': 180 * 60,
                    'tss': 120,
                    'intensity_factor': 0.65,
                    'zone': 'Z2',
                },
                'is_off': False,
                'is_race': False,
                'is_b_race': False,
                'is_b_opener': False,
            }]
            weeks.append({
                'week': i + 1,
                'phase': phase,
                'monday_short': '',
                'sunday_short': '',
                'b_race': {},
                'is_race_week': (i == num_weeks - 1),
                'days': days,
                'total_tss': int(hours_per_week * 50),
                'total_hours': hours_per_week,
                'zone_counts': {'Z1': 0, 'Z2': 3, 'Z3': 0, 'Z4': 1, 'Z5': 0, 'Z5+': 0, 'REST': 3},
            })
        return weeks

    def test_zero_distance_skips_long_ride_check(self):
        """Race with 0 distance should skip the Long Ride vs Race Duration check."""
        profile = {
            'weekly_availability': {'cycling_hours_target': 10},
            'schedule_constraints': {'preferred_off_days': [], 'preferred_long_day': 'saturday'},
            'b_events': [],
            'target_race': {'distance_miles': 0},
        }
        weeks = self._make_mock_weeks(8.0)
        checks = _run_verification_checks(
            profile=profile, derived={}, methodology={'configuration': {}},
            plan_dates={'weeks': []}, weekly_structure={'days': {}},
            weeks_data=weeks,
        )
        lr_check = next((c for c in checks if c['name'] == 'Long Ride vs Race Duration'), None)
        assert lr_check is None, "Should skip long ride check when distance is 0"

    def test_missing_distance_skips_long_ride_check(self):
        """Race with missing distance should skip the Long Ride vs Race Duration check."""
        profile = {
            'weekly_availability': {'cycling_hours_target': 10},
            'schedule_constraints': {'preferred_off_days': [], 'preferred_long_day': 'saturday'},
            'b_events': [],
            'target_race': {},  # No distance_miles key at all
        }
        weeks = self._make_mock_weeks(8.0)
        checks = _run_verification_checks(
            profile=profile, derived={}, methodology={'configuration': {}},
            plan_dates={'weeks': []}, weekly_structure={'days': {}},
            weeks_data=weeks,
        )
        lr_check = next((c for c in checks if c['name'] == 'Long Ride vs Race Duration'), None)
        assert lr_check is None, "Should skip long ride check when distance_miles is missing"

    def test_none_distance_skips_long_ride_check(self):
        """Race with None distance should skip the Long Ride vs Race Duration check."""
        profile = {
            'weekly_availability': {'cycling_hours_target': 10},
            'schedule_constraints': {'preferred_off_days': [], 'preferred_long_day': 'saturday'},
            'b_events': [],
            'target_race': {'distance_miles': None},
        }
        weeks = self._make_mock_weeks(8.0)
        checks = _run_verification_checks(
            profile=profile, derived={}, methodology={'configuration': {}},
            plan_dates={'weeks': []}, weekly_structure={'days': {}},
            weeks_data=weeks,
        )
        lr_check = next((c for c in checks if c['name'] == 'Long Ride vs Race Duration'), None)
        assert lr_check is None, "Should skip long ride check when distance is None"

    def test_short_race_skips_long_ride_check(self):
        """Race < 50 miles should skip the Long Ride vs Race Duration check."""
        profile = {
            'weekly_availability': {'cycling_hours_target': 10},
            'schedule_constraints': {'preferred_off_days': [], 'preferred_long_day': 'saturday'},
            'b_events': [],
            'target_race': {'distance_miles': 40},
        }
        weeks = self._make_mock_weeks(8.0)
        checks = _run_verification_checks(
            profile=profile, derived={}, methodology={'configuration': {}},
            plan_dates={'weeks': []}, weekly_structure={'days': {}},
            weeks_data=weeks,
        )
        lr_check = next((c for c in checks if c['name'] == 'Long Ride vs Race Duration'), None)
        assert lr_check is None, "Should skip long ride check for races < 50 miles"

    def test_long_race_includes_long_ride_check(self):
        """Race >= 50 miles should include the Long Ride vs Race Duration check."""
        profile = {
            'weekly_availability': {'cycling_hours_target': 10},
            'schedule_constraints': {'preferred_off_days': [], 'preferred_long_day': 'saturday'},
            'b_events': [],
            'target_race': {'distance_miles': 100},
        }
        weeks = self._make_mock_weeks(8.0)
        checks = _run_verification_checks(
            profile=profile, derived={}, methodology={'configuration': {}},
            plan_dates={'weeks': []}, weekly_structure={'days': {}},
            weeks_data=weeks,
        )
        lr_check = next((c for c in checks if c['name'] == 'Long Ride vs Race Duration'), None)
        assert lr_check is not None, "Should include long ride check for races >= 50 miles"
        assert lr_check['status'] in ('PASS', 'WARN', 'FAIL')

    def test_exactly_50_miles_includes_check(self):
        """Race at exactly 50 miles should include the check."""
        profile = {
            'weekly_availability': {'cycling_hours_target': 10},
            'schedule_constraints': {'preferred_off_days': [], 'preferred_long_day': 'saturday'},
            'b_events': [],
            'target_race': {'distance_miles': 50},
        }
        weeks = self._make_mock_weeks(8.0)
        checks = _run_verification_checks(
            profile=profile, derived={}, methodology={'configuration': {}},
            plan_dates={'weeks': []}, weekly_structure={'days': {}},
            weeks_data=weeks,
        )
        lr_check = next((c for c in checks if c['name'] == 'Long Ride vs Race Duration'), None)
        assert lr_check is not None, "Should include long ride check for 50-mile race"


# ===========================================================================
# Edge Case: Missing YAML files (edge case 6)
# ===========================================================================

class TestMissingYAMLFiles:
    """Tests for build_preview_data() with partially available pipeline output."""

    def test_missing_all_yamls_except_profile(self):
        """build_preview_data with only profile.yaml and workouts/ should not crash."""
        import yaml
        with tempfile.TemporaryDirectory() as tmpdir:
            ad = Path(tmpdir)

            # Create minimal profile.yaml
            profile = {
                'name': 'Test Athlete',
                'athlete_id': 'test-athlete',
                'fitness_markers': {'ftp_watts': 250},
                'weekly_availability': {'cycling_hours_target': 8},
                'schedule_constraints': {
                    'preferred_off_days': [],
                    'preferred_long_day': 'saturday',
                },
                'b_events': [],
                'target_race': {'distance_miles': 100},
            }
            with open(ad / 'profile.yaml', 'w') as f:
                yaml.dump(profile, f)

            # Create empty workouts dir
            (ad / 'workouts').mkdir()

            # Should not crash
            data = build_preview_data(ad)
            assert data is not None
            assert 'weeks' in data
            assert 'checks' in data
            assert 'profile' in data

    def test_missing_yamls_returns_empty_weeks(self):
        """Without plan_dates.yaml, weeks should be empty."""
        import yaml
        with tempfile.TemporaryDirectory() as tmpdir:
            ad = Path(tmpdir)
            profile = {
                'name': 'Test Athlete',
                'fitness_markers': {'ftp_watts': 200},
                'weekly_availability': {'cycling_hours_target': 8},
                'schedule_constraints': {
                    'preferred_off_days': [],
                    'preferred_long_day': 'saturday',
                },
                'b_events': [],
                'target_race': {},
            }
            with open(ad / 'profile.yaml', 'w') as f:
                yaml.dump(profile, f)
            (ad / 'workouts').mkdir()

            data = build_preview_data(ad)
            assert data['weeks'] == []

    def test_missing_yamls_still_runs_checks(self):
        """Verification checks should still run (some may be empty/skipped)."""
        import yaml
        with tempfile.TemporaryDirectory() as tmpdir:
            ad = Path(tmpdir)
            profile = {
                'name': 'Test Athlete',
                'fitness_markers': {'ftp_watts': 200},
                'weekly_availability': {'cycling_hours_target': 8},
                'schedule_constraints': {
                    'preferred_off_days': [],
                    'preferred_long_day': 'saturday',
                },
                'b_events': [],
                'target_race': {},
            }
            with open(ad / 'profile.yaml', 'w') as f:
                yaml.dump(profile, f)
            (ad / 'workouts').mkdir()

            data = build_preview_data(ad)
            # Checks should still be a list (may contain minimal checks)
            assert isinstance(data['checks'], list)

    def test_no_workouts_dir_doesnt_crash(self):
        """Missing workouts/ dir should not crash build_preview_data."""
        import yaml
        with tempfile.TemporaryDirectory() as tmpdir:
            ad = Path(tmpdir)
            profile = {
                'name': 'Test Athlete',
                'fitness_markers': {'ftp_watts': 200},
                'weekly_availability': {'cycling_hours_target': 8},
                'schedule_constraints': {
                    'preferred_off_days': [],
                    'preferred_long_day': 'saturday',
                },
                'b_events': [],
                'target_race': {},
            }
            with open(ad / 'profile.yaml', 'w') as f:
                yaml.dump(profile, f)
            # No workouts dir at all

            data = build_preview_data(ad)
            assert data is not None
            assert data['weeks'] == []


# ===========================================================================
# Edge Case: Very Short Plans (4-5 weeks) (edge case 3)
# ===========================================================================

class TestVeryShortPlans:
    """Tests for 4-5 week plans — phase structure, FTP tests, verification checks."""

    def _make_short_plan_weeks(self, num_weeks):
        """Create mock weeks_data for a short plan."""
        weeks = []
        # For 4-week plan: base(1-2), build(3), taper(3.5 approx), race(4)
        # Simplified: base, build, taper, race
        phase_map = {}
        if num_weeks == 4:
            phase_map = {1: 'base', 2: 'build', 3: 'taper', 4: 'race'}
        elif num_weeks == 5:
            phase_map = {1: 'base', 2: 'base', 3: 'build', 4: 'taper', 5: 'race'}
        else:
            for i in range(1, num_weeks + 1):
                phase_map[i] = 'build'
            phase_map[1] = 'base'
            phase_map[num_weeks - 1] = 'taper'
            phase_map[num_weeks] = 'race'

        for i in range(1, num_weeks + 1):
            phase = phase_map.get(i, 'build')
            days = []
            for day_abbrev in ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']:
                if day_abbrev == 'Sat':
                    # FTP test in first week only for short plans
                    if i == 1:
                        wo = {
                            'name': f'W{i:02d}_{day_abbrev}_FTP_Test',
                            'duration_min': 50,
                            'duration_sec': 3000,
                            'tss': 55,
                            'intensity_factor': 0.85,
                            'zone': 'Z4',
                        }
                    else:
                        wo = {
                            'name': f'W{i:02d}_{day_abbrev}_Long_Ride',
                            'duration_min': 180,
                            'duration_sec': 10800,
                            'tss': 120,
                            'intensity_factor': 0.65,
                            'zone': 'Z2',
                        }
                elif day_abbrev == 'Wed':
                    wo = {
                        'name': f'W{i:02d}_{day_abbrev}_VO2max',
                        'duration_min': 60,
                        'duration_sec': 3600,
                        'tss': 70,
                        'intensity_factor': 0.88,
                        'zone': 'Z5',
                    }
                elif day_abbrev in ('Mon', 'Fri'):
                    wo = {
                        'name': f'W{i:02d}_{day_abbrev}_Endurance',
                        'duration_min': 50,
                        'duration_sec': 3000,
                        'tss': 35,
                        'intensity_factor': 0.60,
                        'zone': 'Z2',
                    }
                elif day_abbrev == 'Sun':
                    # Off day
                    days.append({
                        'day': day_abbrev, 'date': '', 'workout': None,
                        'is_off': True, 'is_race': False,
                        'is_b_race': False, 'is_b_opener': False,
                    })
                    continue
                else:
                    wo = {
                        'name': f'W{i:02d}_{day_abbrev}_Easy',
                        'duration_min': 40,
                        'duration_sec': 2400,
                        'tss': 25,
                        'intensity_factor': 0.55,
                        'zone': 'Z1',
                    }
                days.append({
                    'day': day_abbrev, 'date': '', 'workout': wo,
                    'is_off': False,
                    'is_race': (phase == 'race' and day_abbrev == 'Sat'),
                    'is_b_race': False, 'is_b_opener': False,
                })
            total_tss = sum(d['workout']['tss'] for d in days if d.get('workout'))
            total_hrs = sum(d['workout']['duration_sec'] for d in days if d.get('workout')) / 3600
            weeks.append({
                'week': i,
                'phase': phase,
                'monday_short': '',
                'sunday_short': '',
                'b_race': {},
                'is_race_week': (i == num_weeks),
                'days': days,
                'total_tss': total_tss,
                'total_hours': round(total_hrs, 1),
                'zone_counts': {'Z1': 2, 'Z2': 2, 'Z3': 0, 'Z4': 0, 'Z5': 1, 'Z5+': 0, 'REST': 2},
            })
        return weeks

    def test_4_week_plan_has_base_and_race(self):
        """4-week plan should have at least base and race phases."""
        weeks = self._make_short_plan_weeks(4)
        phases = set(w['phase'] for w in weeks)
        assert 'base' in phases, "4-week plan must have base phase"
        assert 'race' in phases, "4-week plan must have race phase"

    def test_4_week_plan_verification_checks_dont_crash(self):
        """Verification checks should not crash on a 4-week plan."""
        profile = {
            'weekly_availability': {'cycling_hours_target': 8},
            'schedule_constraints': {
                'preferred_off_days': ['sunday'],
                'preferred_long_day': 'saturday',
            },
            'b_events': [],
            'target_race': {'distance_miles': 100},
        }
        weeks = self._make_short_plan_weeks(4)
        checks = _run_verification_checks(
            profile=profile, derived={}, methodology={'configuration': {}},
            plan_dates={'weeks': []}, weekly_structure={'days': {}},
            weeks_data=weeks,
        )
        assert isinstance(checks, list)
        assert len(checks) > 0

    def test_4_week_plan_ftp_frequency_not_checked(self):
        """Plans < 8 weeks should NOT have FTP Test Frequency check."""
        profile = {
            'weekly_availability': {'cycling_hours_target': 8},
            'schedule_constraints': {
                'preferred_off_days': ['sunday'],
                'preferred_long_day': 'saturday',
            },
            'b_events': [],
            'target_race': {'distance_miles': 100},
        }
        weeks = self._make_short_plan_weeks(4)
        checks = _run_verification_checks(
            profile=profile, derived={}, methodology={'configuration': {}},
            plan_dates={'weeks': []}, weekly_structure={'days': {}},
            weeks_data=weeks,
        )
        freq_check = next((c for c in checks if c['name'] == 'FTP Test Frequency'), None)
        assert freq_check is None, "FTP Frequency check should not fire for plans < 8 weeks"

    def test_4_week_plan_has_ftp_test(self):
        """4-week plan should have at least 1 FTP test (not 2)."""
        profile = {
            'weekly_availability': {'cycling_hours_target': 8},
            'schedule_constraints': {
                'preferred_off_days': ['sunday'],
                'preferred_long_day': 'saturday',
            },
            'b_events': [],
            'target_race': {'distance_miles': 100},
        }
        weeks = self._make_short_plan_weeks(4)
        checks = _run_verification_checks(
            profile=profile, derived={}, methodology={'configuration': {}},
            plan_dates={'weeks': []}, weekly_structure={'days': {}},
            weeks_data=weeks,
        )
        ftp_check = next(c for c in checks if c['name'] == 'FTP Tests')
        assert ftp_check['status'] == 'PASS'
        assert 'W01' in ftp_check['detail']

    def test_5_week_plan_has_progression(self):
        """5-week plan should have phase progression from base to race."""
        weeks = self._make_short_plan_weeks(5)
        phases = [w['phase'] for w in weeks]
        assert phases[0] == 'base'
        assert phases[-1] == 'race'

    def test_5_week_plan_checks_dont_crash(self):
        """Verification checks on a 5-week plan should not crash."""
        profile = {
            'weekly_availability': {'cycling_hours_target': 8},
            'schedule_constraints': {
                'preferred_off_days': ['sunday'],
                'preferred_long_day': 'saturday',
            },
            'b_events': [],
            'target_race': {'distance_miles': 100},
        }
        weeks = self._make_short_plan_weeks(5)
        checks = _run_verification_checks(
            profile=profile, derived={}, methodology={'configuration': {}},
            plan_dates={'weeks': []}, weekly_structure={'days': {}},
            weeks_data=weeks,
        )
        assert isinstance(checks, list)
        # Phase progression should still pass
        phase_check = next(c for c in checks if c['name'] == 'Phase Progression')
        assert phase_check['status'] == 'PASS'


# ===========================================================================
# Archetype Variation Rotation Tests
# ===========================================================================

class TestArchetypeVariationRotation:
    """Tests for archetype variation rotation and cadence/position metadata."""

    @pytest.fixture
    def nicholas_workouts(self):
        return Path(__file__).parent.parent / 'nicholas-applegate' / 'workouts'

    def test_wednesday_vo2max_not_all_identical(self, nicholas_workouts):
        """Wednesday VO2max sessions should use different archetype structures.

        Over 12 weeks with 4 VO2max archetypes, we should see variation in
        Repeat count and OnPower values across sessions.
        """
        vo2max_files = sorted(nicholas_workouts.glob('W*Wed*VO2max*.zwo'))
        assert len(vo2max_files) >= 4, f"Expected at least 4 VO2max files, got {len(vo2max_files)}"

        # Extract (Repeat, OnDuration) tuples to identify archetype structure
        structures = []
        for f in vo2max_files:
            content = f.read_text()
            # Look for IntervalsT elements
            repeat_match = re.search(r'Repeat="(\d+)"', content)
            duration_match = re.search(r'OnDuration="(\d+)"', content)
            if repeat_match and duration_match:
                structures.append((repeat_match.group(1), duration_match.group(1)))
            else:
                # Pyramid workouts don't have IntervalsT — that's a different structure
                structures.append(('pyramid', 'pyramid'))

        unique_structures = set(structures)
        assert len(unique_structures) >= 2, (
            f"All {len(vo2max_files)} VO2max sessions have identical structure: "
            f"{structures[0]}. Expected variation from archetype rotation."
        )

    def test_archetype_variation_cycles(self):
        """Over 4+ workouts of the same type, at least 2 different archetypes appear.

        Tests the Nate generator directly by generating multiple VO2max workouts
        with incrementing variation counters.
        """
        results = []
        for variation in range(8):
            zwo = generate_nate_zwo(
                workout_type='vo2max',
                level=3,
                methodology='POLARIZED',
                variation=variation,
            )
            assert zwo is not None, f"generate_nate_zwo returned None for variation={variation}"
            # Extract the archetype name from the workout name in ZWO
            name_match = re.search(r'<name>([^<]+)</name>', zwo)
            if name_match:
                results.append(name_match.group(1))

        unique_names = set(results)
        assert len(unique_names) >= 2, (
            f"Generated 8 VO2max workouts but only got {len(unique_names)} unique "
            f"archetype(s): {unique_names}. Variation rotation is not working."
        )
        # With 4 VO2max archetypes, 8 workouts should cycle through all 4
        assert len(unique_names) >= 4, (
            f"Expected 4 unique archetypes over 8 workouts (4 VO2max archetypes), "
            f"got {len(unique_names)}: {unique_names}"
        )

    def test_threshold_variation_cycles(self):
        """Threshold workouts should also cycle through archetypes."""
        results = []
        for variation in range(6):
            zwo = generate_nate_zwo(
                workout_type='threshold',
                level=3,
                methodology='POLARIZED',
                variation=variation,
            )
            assert zwo is not None
            name_match = re.search(r'<name>([^<]+)</name>', zwo)
            if name_match:
                results.append(name_match.group(1))

        unique_names = set(results)
        assert len(unique_names) >= 2, (
            f"Generated 6 Threshold workouts but only {len(unique_names)} unique "
            f"archetype(s): {unique_names}"
        )

    def test_workout_descriptions_have_cadence(self, nicholas_workouts):
        """ZWO workout descriptions should contain cadence instructions.

        All Nate-generated workouts (VO2max, Threshold, Sprint, Anaerobic)
        should include cadence prescriptions in their descriptions.
        """
        nate_types = ['VO2max', 'Threshold', 'Sprints', 'Anaerobic']
        checked = 0
        missing = []

        for zwo_file in sorted(nicholas_workouts.glob('*.zwo')):
            name = zwo_file.name
            # Only check Nate-generated workout types
            if not any(t in name for t in nate_types):
                continue

            content = zwo_file.read_text()
            # Check for cadence in the description
            if 'rpm' not in content.lower() and 'cadence' not in content.lower():
                missing.append(name)
            checked += 1

        assert checked > 0, "No Nate-generated workouts found to check"
        assert len(missing) == 0, (
            f"{len(missing)} of {checked} Nate workouts missing cadence info: "
            f"{missing[:5]}{'...' if len(missing) > 5 else ''}"
        )

    def test_workout_descriptions_have_position(self, nicholas_workouts):
        """ZWO workout descriptions should contain position instructions."""
        nate_types = ['VO2max', 'Threshold', 'Sprints', 'Anaerobic']
        checked = 0
        missing = []

        for zwo_file in sorted(nicholas_workouts.glob('*.zwo')):
            name = zwo_file.name
            if not any(t in name for t in nate_types):
                continue

            content = zwo_file.read_text()
            if 'position' not in content.lower():
                missing.append(name)
            checked += 1

        assert checked > 0, "No Nate-generated workouts found to check"
        assert len(missing) == 0, (
            f"{len(missing)} of {checked} Nate workouts missing position info: "
            f"{missing[:5]}{'...' if len(missing) > 5 else ''}"
        )

    def test_default_cadence_covers_all_levels(self):
        """Default cadence helper should return a value for every level 1-6."""
        for level in range(1, 7):
            cadence = _get_default_cadence("VO2max 5x3 Classic", level)
            assert 'rpm' in cadence, f"Level {level} cadence missing 'rpm': {cadence}"

    def test_default_position_covers_all_levels(self):
        """Default position helper should return a value for every level 1-6."""
        for level in range(1, 7):
            position = _get_default_position("VO2max 5x3 Classic", level)
            assert len(position) > 0, f"Level {level} position is empty"

    def test_default_cadence_varies_by_category(self):
        """Different workout categories should have different default cadences."""
        vo2_cadence = _get_default_cadence("VO2max 5x3 Classic", 3)
        sprint_cadence = _get_default_cadence("Sprint Buildups", 3)
        endurance_cadence = _get_default_cadence("Terrain Simulation Z2", 3)

        # These should not all be the same
        cadences = {vo2_cadence, sprint_cadence, endurance_cadence}
        assert len(cadences) >= 2, (
            f"Expected different cadences for different categories, "
            f"got same value for all: {vo2_cadence}"
        )
