#!/usr/bin/env python3
"""
ZWO Format Regression Tests

CRITICAL: These tests ensure ZWO files can be imported into TrainingPeaks.
DO NOT MODIFY these tests without testing actual imports.

Reference: Gravel God ZWO File Creation Skill v6.0
Working reference file: Drop_Down_1_Updated.zwo

THE RULES (learned the hard way):
1. XML declaration MUST use single quotes: <?xml version='1.0' encoding='UTF-8'?>
2. 2-space indent for metadata tags (author, name, description, sportType)
3. 2-space indent for <workout> tag
4. 4-space indent for workout blocks (Warmup, SteadyState, IntervalsT, Cooldown)
5. NO 8-space indents anywhere - this BREAKS TrainingPeaks import
6. NO nested textevent in SteadyState, Warmup, or Cooldown - BREAKS TrainingPeaks
7. ONLY IntervalsT can have nested textevent elements
8. All SteadyState, Warmup, Cooldown must be SELF-CLOSING (end with />)
"""

import pytest
import sys
import re
from pathlib import Path

# Add script path
sys.path.insert(0, str(Path(__file__).parent))


class TestZWOFormat:
    """Test ZWO file format compliance."""

    # The EXACT format that works with TrainingPeaks
    VALID_XML_DECLARATION = "<?xml version='1.0' encoding='UTF-8'?>"

    # These indent patterns are REQUIRED
    VALID_PATTERNS = [
        (r'^<\?xml', 'XML declaration at start'),
        (r'^<workout_file>', 'workout_file at column 0'),
        (r'^  <author>', 'author with 2-space indent'),
        (r'^  <name>', 'name with 2-space indent'),
        (r'^  <description>', 'description with 2-space indent'),
        (r'^  <sportType>bike</sportType>', 'sportType bike with 2-space indent'),
        (r'^  <workout>', 'workout with 2-space indent'),
        (r'^    <Warmup ', 'Warmup with 4-space indent'),
        (r'^    <SteadyState ', 'SteadyState with 4-space indent'),
        (r'^    <Cooldown ', 'Cooldown with 4-space indent'),
        (r'^  </workout>', 'closing workout with 2-space indent'),
        (r'^</workout_file>', 'closing workout_file at column 0'),
    ]

    # These patterns MUST NOT appear - they break TrainingPeaks
    INVALID_PATTERNS = [
        (r'^        <Warmup', '8-space indent Warmup BREAKS IMPORT'),
        (r'^        <SteadyState', '8-space indent SteadyState BREAKS IMPORT'),
        (r'^        <Cooldown', '8-space indent Cooldown BREAKS IMPORT'),
        (r'^        <IntervalsT', '8-space indent IntervalsT BREAKS IMPORT'),
        (r'^      <workout>', '6-space indent workout BREAKS IMPORT'),
        (r'^    <workout>', '4-space indent workout BREAKS IMPORT'),
        (r'<?xml version="1.0"', 'Double quotes in XML declaration MAY break import'),
    ]

    def test_xml_declaration_single_quotes(self):
        """XML declaration MUST use single quotes."""
        from generate_athlete_package import generate_zwo_files

        # Check the template directly
        # Import the module and check ZWO_TEMPLATE
        import generate_athlete_package as gap

        # Find ZWO_TEMPLATE in the function (it's defined inside generate_zwo_files)
        # We'll test by generating a sample file
        pass  # Covered by integration test below

    def test_no_8_space_indent_in_generate_athlete_package(self):
        """generate_athlete_package.py must not have 8-space indented XML strings."""
        script_path = Path(__file__).parent / 'generate_athlete_package.py'
        content = script_path.read_text()

        # Check for 8-space indent in string literals for XML elements
        bad_patterns = [
            "'        <Warmup",
            "'        <SteadyState",
            "'        <Cooldown",
            "'        <IntervalsT",
            '"        <Warmup',
            '"        <SteadyState',
            '"        <Cooldown',
            '"        <IntervalsT',
        ]

        for pattern in bad_patterns:
            assert pattern not in content, \
                f"FATAL: Found {pattern} in generate_athlete_package.py - this breaks TrainingPeaks import!"

    def test_no_8_space_indent_in_workout_library(self):
        """workout_library.py must not have 8-space indented XML strings."""
        script_path = Path(__file__).parent / 'workout_library.py'
        content = script_path.read_text()

        bad_patterns = [
            "'        <Warmup",
            "'        <SteadyState",
            "'        <Cooldown",
            "'        <IntervalsT",
            '"        <Warmup',
            '"        <SteadyState',
            '"        <Cooldown',
            '"        <IntervalsT',
        ]

        for pattern in bad_patterns:
            assert pattern not in content, \
                f"FATAL: Found {pattern} in workout_library.py - this breaks TrainingPeaks import!"

    def test_no_nested_textevent_in_steadystate(self):
        """SteadyState must NOT have nested textevent - BREAKS TrainingPeaks.

        Only IntervalsT can have nested textevent elements.
        SteadyState, Warmup, Cooldown must be self-closing.
        """
        for script_name in ['generate_athlete_package.py', 'workout_library.py']:
            script_path = Path(__file__).parent / script_name
            content = script_path.read_text()

            # Check for non-self-closing SteadyState followed by textevent
            # Pattern: <SteadyState ...> (not ending with />) followed by textevent
            lines = content.split('\n')
            in_steadystate = False
            for i, line in enumerate(lines):
                if '<SteadyState' in line and '/>' not in line and '</SteadyState>' not in line:
                    in_steadystate = True
                    steadystate_line = i + 1
                elif in_steadystate and '<textevent' in line:
                    assert False, \
                        f"FATAL: {script_name} line {steadystate_line}: SteadyState with nested textevent BREAKS TrainingPeaks!"
                elif '</SteadyState>' in line:
                    in_steadystate = False

    def test_4_space_indent_in_generate_athlete_package(self):
        """generate_athlete_package.py must use 4-space indent for workout blocks."""
        script_path = Path(__file__).parent / 'generate_athlete_package.py'
        content = script_path.read_text()

        # These patterns MUST exist (4-space indent)
        good_patterns = [
            "'    <Warmup",
            "'    <SteadyState",
            "'    <Cooldown",
        ]

        for pattern in good_patterns:
            assert pattern in content, \
                f"Missing {pattern} in generate_athlete_package.py - workout blocks need 4-space indent"

    def test_4_space_indent_in_workout_library(self):
        """workout_library.py must use 4-space indent for workout blocks."""
        script_path = Path(__file__).parent / 'workout_library.py'
        content = script_path.read_text()

        good_patterns = [
            "'    <Warmup",
            "'    <SteadyState",
            "'    <Cooldown",
        ]

        for pattern in good_patterns:
            assert pattern in content, \
                f"Missing {pattern} in workout_library.py - workout blocks need 4-space indent"

    def test_zwo_template_structure(self):
        """ZWO template must have correct structure."""
        script_path = Path(__file__).parent / 'generate_athlete_package.py'
        content = script_path.read_text()

        # Extract ZWO_TEMPLATE
        template_match = re.search(r'ZWO_TEMPLATE = """(.+?)"""', content, re.DOTALL)
        assert template_match, "ZWO_TEMPLATE not found in generate_athlete_package.py"

        template = template_match.group(1)

        # Check critical elements
        assert "<?xml version='1.0' encoding='UTF-8'?>" in template, \
            "XML declaration must use single quotes"
        assert "\n  <workout>\n" in template, \
            "workout tag must have 2-space indent"
        assert "  </workout>" in template, \
            "closing workout tag must have 2-space indent"


class TestZWOFileGeneration:
    """Integration tests for generated ZWO files."""

    @pytest.fixture
    def sample_zwo_content(self):
        """Generate a sample ZWO file content."""
        import yaml
        sys.path.insert(0, str(Path(__file__).parent))
        from generate_athlete_package import generate_zwo_files

        # Create minimal test data
        athlete_dir = Path(__file__).parent.parent / 'benjy-duke'
        if not athlete_dir.exists():
            pytest.skip("Test athlete benjy-duke not found")

        plan_dates = yaml.safe_load((athlete_dir / 'plan_dates.yaml').read_text())
        methodology = yaml.safe_load((athlete_dir / 'methodology.yaml').read_text())
        derived = yaml.safe_load((athlete_dir / 'derived.yaml').read_text())
        profile = yaml.safe_load((athlete_dir / 'profile.yaml').read_text())

        # Generate files
        files = generate_zwo_files(athlete_dir, plan_dates, methodology, derived, profile)

        if files:
            return Path(files[0]).read_text()
        return None

    def test_generated_file_has_single_quote_xml_declaration(self, sample_zwo_content):
        """Generated files must use single quotes in XML declaration."""
        if sample_zwo_content is None:
            pytest.skip("No sample content generated")

        assert sample_zwo_content.startswith("<?xml version='1.0' encoding='UTF-8'?>"), \
            "XML declaration must use single quotes"

    def test_generated_file_has_2_space_workout_tag(self, sample_zwo_content):
        """Generated files must have 2-space indent for workout tag."""
        if sample_zwo_content is None:
            pytest.skip("No sample content generated")

        assert "\n  <workout>\n" in sample_zwo_content, \
            "workout tag must have exactly 2-space indent"

    def test_generated_file_has_4_space_blocks(self, sample_zwo_content):
        """Generated files must have 4-space indent for workout blocks."""
        if sample_zwo_content is None:
            pytest.skip("No sample content generated")

        # At least one of these must be present with 4-space indent
        has_4_space = any([
            "\n    <Warmup " in sample_zwo_content,
            "\n    <SteadyState " in sample_zwo_content,
            "\n    <Cooldown " in sample_zwo_content,
            "\n    <IntervalsT " in sample_zwo_content,
        ])
        assert has_4_space, "Workout blocks must have 4-space indent"

    def test_generated_file_no_8_space_blocks(self, sample_zwo_content):
        """Generated files must NOT have 8-space indent for workout blocks."""
        if sample_zwo_content is None:
            pytest.skip("No sample content generated")

        bad_patterns = [
            "\n        <Warmup ",
            "\n        <SteadyState ",
            "\n        <Cooldown ",
            "\n        <IntervalsT ",
        ]

        for pattern in bad_patterns:
            assert pattern not in sample_zwo_content, \
                f"FATAL: Found 8-space indent in generated file - this breaks TrainingPeaks!"


class TestAllGeneratedFiles:
    """Test all generated ZWO files in a directory."""

    def test_all_benjy_workouts(self):
        """Test all generated workouts for Benjy."""
        workout_dir = Path(__file__).parent.parent / 'benjy-duke' / 'workouts'
        if not workout_dir.exists():
            pytest.skip("Benjy workouts directory not found")

        zwo_files = list(workout_dir.glob('*.zwo'))
        if not zwo_files:
            pytest.skip("No ZWO files found")

        errors = []
        for zwo_file in zwo_files:
            content = zwo_file.read_text()

            # Check XML declaration
            if not content.startswith("<?xml version='1.0' encoding='UTF-8'?>"):
                errors.append(f"{zwo_file.name}: Wrong XML declaration")

            # Check for 8-space indent (FATAL)
            if "\n        <Warmup" in content or \
               "\n        <SteadyState" in content or \
               "\n        <Cooldown" in content or \
               "\n        <IntervalsT" in content:
                errors.append(f"{zwo_file.name}: Has 8-space indent - BREAKS IMPORT")

            # Check workout tag has 2-space indent
            if "\n  <workout>\n" not in content:
                errors.append(f"{zwo_file.name}: workout tag wrong indent")

        assert not errors, f"ZWO format errors:\n" + "\n".join(errors)


class TestDurationRounding:
    """Test that all workout durations are rounded to nearest 10 minutes.

    Durations like 67min, 94min, 107min break the clean training plan feel.
    All workouts should have durations that are multiples of 10 (e.g., 70, 90, 110).
    """

    def _parse_zwo_total_minutes(self, zwo_path: Path) -> int:
        """Parse a ZWO file and return total duration in minutes."""
        import xml.etree.ElementTree as ET

        tree = ET.parse(zwo_path)
        root = tree.getroot()
        workout = root.find('workout')
        if workout is None:
            return 0

        total_seconds = 0
        for elem in workout:
            dur = float(elem.get('Duration', 0))
            if elem.tag == 'IntervalsT':
                repeats = int(elem.get('Repeat', 1))
                on_dur = float(elem.get('OnDuration', 0))
                off_dur = float(elem.get('OffDuration', 0))
                total_seconds += repeats * (on_dur + off_dur)
            else:
                total_seconds += dur

        return int(total_seconds / 60)

    def test_all_nicholas_workout_durations_divisible_by_10(self):
        """Every ZWO in nicholas-applegate/workouts should have duration divisible by 10."""
        workout_dir = Path(__file__).parent.parent / 'nicholas-applegate' / 'workouts'
        if not workout_dir.exists():
            pytest.skip("nicholas-applegate workouts directory not found")

        zwo_files = sorted(workout_dir.glob('*.zwo'))
        if not zwo_files:
            pytest.skip("No ZWO files found")

        errors = []
        for zwo_file in zwo_files:
            total_min = self._parse_zwo_total_minutes(zwo_file)
            if total_min > 0 and total_min % 10 != 0:
                errors.append(f"{zwo_file.name}: {total_min}min (not divisible by 10)")

        assert not errors, (
            f"{len(errors)} workout(s) have durations not divisible by 10:\n"
            + "\n".join(errors)
        )

    def test_round_duration_to_10_function(self):
        """Test the round_duration_to_10 helper."""
        from workout_templates import round_duration_to_10

        # Standard rounding (away from midpoint)
        assert round_duration_to_10(67) == 70
        assert round_duration_to_10(94) == 90
        assert round_duration_to_10(107) == 110
        assert round_duration_to_10(121) == 120
        assert round_duration_to_10(136) == 140
        assert round_duration_to_10(56) == 60
        assert round_duration_to_10(44) == 40
        assert round_duration_to_10(36) == 40
        assert round_duration_to_10(24) == 20

        # Exact multiples stay the same
        assert round_duration_to_10(60) == 60
        assert round_duration_to_10(90) == 90
        assert round_duration_to_10(120) == 120
        assert round_duration_to_10(180) == 180

        # Result is always a multiple of 10
        for val in [67, 94, 107, 121, 135, 55, 45, 35, 25, 15, 5]:
            result = round_duration_to_10(val)
            assert result % 10 == 0, f"round_duration_to_10({val}) = {result}, not a multiple of 10"

        # Zero and negative pass through
        assert round_duration_to_10(0) == 0
        assert round_duration_to_10(-1) == -1

        # Very small rounds to minimum 10
        assert round_duration_to_10(1) == 10
        assert round_duration_to_10(4) == 10

    def test_ftp_test_duration_is_60(self):
        """FTP test protocol must sum to exactly 60 minutes."""
        from constants import FTP_TEST_DURATION_MIN
        assert FTP_TEST_DURATION_MIN == 60, \
            f"FTP_TEST_DURATION_MIN should be 60, got {FTP_TEST_DURATION_MIN}"


class TestZWOPowerSanity:
    """Ensure workout power targets make physiological sense.

    Rules (learned the hard way):
    1. Warmup must NOT ramp above main set power for Easy/Recovery/Endurance
    2. Cooldown must ramp DOWN (or at least not ramp UP)
    3. Easy rides = Z2 low (0.56-0.65), NOT Z1 (0.45-0.55)
    4. Recovery rides = Z1 high (0.50-0.55)
    5. Endurance rides = Z2 (0.56-0.75)
    6. Main set power must always be >= warmup end power for easy workouts
    """

    def _parse_blocks(self, zwo_content: str) -> list:
        """Parse ZWO content into list of (tag, attrs) tuples."""
        import xml.etree.ElementTree as ET
        root = ET.fromstring(zwo_content)
        workout = root.find('workout')
        if workout is None:
            return []
        return [(elem.tag, elem.attrib) for elem in workout]

    def test_easy_warmup_never_exceeds_main_set(self):
        """For Easy/Recovery workouts, warmup end power <= main set power."""
        sys.path.insert(0, str(Path(__file__).parent))
        from generate_athlete_package import generate_zwo_files

        # Test create_workout_blocks directly via its enclosing function
        # We'll test the principle by generating a sample
        workout_dir = Path(__file__).parent.parent / 'benjy-duke' / 'workouts'
        if not workout_dir.exists():
            pytest.skip("benjy-duke workouts not found")

        errors = []
        for zwo_file in sorted(workout_dir.glob('*.zwo')):
            name = zwo_file.stem
            # Only check Easy/Endurance/Recovery workouts (not intensity)
            is_easy = any(t in name for t in ['Easy', 'Endurance', 'Pre_Plan_Easy', 'Shakeout'])
            if not is_easy:
                continue

            blocks = self._parse_blocks(zwo_file.read_text())
            if not blocks:
                continue

            # Find warmup end power and highest main set power
            # Nate-generated endurance has structured blocks (e.g., alternating 65%/75%)
            # so compare warmup against the HIGHEST main set power
            warmup_high = None
            max_main_power = 0
            for tag, attrs in blocks:
                if tag == 'Warmup':
                    warmup_high = float(attrs.get('PowerHigh', 0))
                elif tag == 'SteadyState':
                    p = float(attrs.get('Power', 0))
                    if p > max_main_power:
                        max_main_power = p

            if warmup_high and max_main_power > 0:
                # Endurance workouts use structured Z2 blocks — warmup can be
                # slightly above individual blocks (e.g., 75% warmup into 65%/72% blocks)
                # Allow 5% tolerance for Endurance, 2% for Easy/Recovery
                tolerance = 0.05 if 'Endurance' in name else 0.02
                if warmup_high > max_main_power + tolerance:
                    errors.append(
                        f"{name}: warmup ends at {warmup_high:.0%} but max main set is {max_main_power:.0%} "
                        f"(warmup should NOT ramp above main set for easy workouts)"
                    )

        assert not errors, "Warmup > main set violations:\n" + "\n".join(errors)

    def test_easy_power_is_zone2_not_zone1(self):
        """Easy workout main set must be Z2 (>=0.56), not Z1 recovery."""
        workout_dir = Path(__file__).parent.parent / 'benjy-duke' / 'workouts'
        if not workout_dir.exists():
            pytest.skip("benjy-duke workouts not found")

        errors = []
        for zwo_file in sorted(workout_dir.glob('*.zwo')):
            name = zwo_file.stem
            is_easy = any(t in name for t in ['Easy', 'Pre_Plan_Easy'])
            if not is_easy or 'Strength' in name:
                continue

            blocks = self._parse_blocks(zwo_file.read_text())
            for tag, attrs in blocks:
                if tag == 'SteadyState':
                    power = float(attrs.get('Power', 0))
                    if 0 < power < 0.56:
                        errors.append(
                            f"{name}: main set at {power:.0%} FTP — "
                            f"that's Z1 recovery, not Easy. Must be >= 56% (Z2)."
                        )
                    break  # Only check first SteadyState

        assert not errors, "Easy rides in Z1 (should be Z2):\n" + "\n".join(errors)

    def test_endurance_power_is_zone2(self):
        """Endurance workout main set must be solidly in Z2 (>=0.60)."""
        workout_dir = Path(__file__).parent.parent / 'benjy-duke' / 'workouts'
        if not workout_dir.exists():
            pytest.skip("benjy-duke workouts not found")

        errors = []
        for zwo_file in sorted(workout_dir.glob('*Endurance*.zwo')):
            name = zwo_file.stem
            if 'Strength' in name:
                continue

            blocks = self._parse_blocks(zwo_file.read_text())
            for tag, attrs in blocks:
                if tag == 'SteadyState':
                    power = float(attrs.get('Power', 0))
                    if 0 < power < 0.58:
                        errors.append(
                            f"{name}: main set at {power:.0%} FTP — "
                            f"Endurance should be >= 58% (Z2 low-mid)."
                        )
                    break

        assert not errors, "Endurance rides below Z2:\n" + "\n".join(errors)

    def test_cooldown_does_not_ramp_up(self):
        """Cooldown power must decrease or stay flat, never increase."""
        workout_dir = Path(__file__).parent.parent / 'benjy-duke' / 'workouts'
        if not workout_dir.exists():
            pytest.skip("benjy-duke workouts not found")

        errors = []
        for zwo_file in sorted(workout_dir.glob('*.zwo')):
            name = zwo_file.stem
            blocks = self._parse_blocks(zwo_file.read_text())
            for tag, attrs in blocks:
                if tag == 'Cooldown':
                    low = float(attrs.get('PowerLow', 0))
                    high = float(attrs.get('PowerHigh', 0))
                    # In ZWO, Cooldown renders PowerLow→PowerHigh
                    # So PowerLow should be higher (start) and PowerHigh lower (end)
                    if low > 0 and high > 0 and high > low + 0.02:
                        errors.append(
                            f"{name}: cooldown ramps UP from {low:.0%} to {high:.0%} "
                            f"(should decrease)"
                        )

        assert not errors, "Cooldown ramp-up violations:\n" + "\n".join(errors)

    def test_template_power_values_in_valid_range(self):
        """All power template values in generate_athlete_package.py must be
        in valid zones: 0.45-1.60 FTP, and Easy/Recovery types >= 0.55."""
        script_path = Path(__file__).parent / 'generate_athlete_package.py'
        content = script_path.read_text()

        # Find all template tuples: ('Type', 'desc', duration, power)
        pattern = r"template\s*=\s*\('(\w+)',\s*'[^']+',\s*\d+,\s*([\d.]+)\)"
        matches = re.findall(pattern, content)

        errors = []
        for wtype, power_str in matches:
            power = float(power_str)
            # Rest templates legitimately have power=0 (no riding)
            if wtype == 'Rest':
                continue
            if power < 0.45 or power > 1.60:
                errors.append(f"template ({wtype}, power={power}) outside valid range 0.45-1.60")
            if wtype in ('Easy', 'Recovery', 'Shakeout') and power < 0.55:
                errors.append(f"template ({wtype}, power={power}) below Z1 high (0.55) — too low")

        assert not errors, "Invalid template power values:\n" + "\n".join(errors)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
