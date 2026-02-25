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


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
