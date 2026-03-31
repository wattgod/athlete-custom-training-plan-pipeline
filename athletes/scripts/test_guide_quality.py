#!/usr/bin/env python3
"""Tests for training guide quality validation."""

import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent))

from validate_guide_quality import (
    check_guide_slop,
    check_required_sections,
    check_placeholders,
    check_empty_tables,
)


class TestSlopDetection:
    def test_clean_text_passes(self):
        html = "<p>Your training plan is structured around 3 key sessions per week.</p>"
        violations = check_guide_slop(html)
        assert len(violations) == 0

    def test_banned_phrase_caught(self):
        html = "<p>This revolutionary plan will transform your cycling.</p>"
        violations = check_guide_slop(html)
        phrases = [v['phrase'] for v in violations]
        assert any('revolutionary' in p for p in phrases)

    def test_banned_structure_caught(self):
        html = "<p>Whether you're a beginner or a seasoned pro, this plan works.</p>"
        violations = check_guide_slop(html)
        assert len(violations) > 0

    def test_unlock_potential_caught(self):
        html = "<p>Unlock your potential with structured training.</p>"
        violations = check_guide_slop(html)
        assert len(violations) > 0

    def test_html_tags_stripped(self):
        html = "<div><strong>cutting-edge</strong> training methodology</div>"
        violations = check_guide_slop(html)
        phrases = [v['phrase'] for v in violations]
        assert any('cutting-edge' in p for p in phrases)


class TestRequiredSections:
    def test_all_present(self):
        html = """
        <h2>Quick Reference</h2>
        <h2>Training Philosophy</h2>
        <h2>Phase Progression</h2>
        <h2>Training Zones</h2>
        <h2>Nutrition</h2>
        <h2>Race Week</h2>
        """
        issues = check_required_sections(html)
        assert len(issues) == 0

    def test_missing_section(self):
        html = "<h2>Quick Reference</h2><h2>Training Zones</h2>"
        issues = check_required_sections(html)
        assert len(issues) > 0
        assert any('Training Philosophy' in i for i in issues)


class TestPlaceholders:
    def test_no_placeholders(self):
        html = "<p>Your FTP is 280W. Target race: Unbound 200.</p>"
        issues = check_placeholders(html)
        assert len(issues) == 0

    def test_todo_caught(self):
        html = "<p>TODO: Add race-specific tips here.</p>"
        issues = check_placeholders(html)
        assert len(issues) > 0

    def test_template_var_caught(self):
        html = "<p>Welcome {athlete_name}, your race is {race_name}.</p>"
        issues = check_placeholders(html)
        assert len(issues) >= 2

    def test_nan_caught(self):
        html = "<td>NaN</td><td>NaN watts</td>"
        issues = check_placeholders(html)
        assert len(issues) > 0

    def test_none_in_script_ignored(self):
        html = "<script>if (x === None) {}</script><p>Normal text.</p>"
        issues = check_placeholders(html)
        assert len(issues) == 0


class TestEmptyTables:
    def test_normal_table_passes(self):
        html = "<table><tr><th>Week</th></tr><tr><td>1</td></tr><tr><td>2</td></tr></table>"
        issues = check_empty_tables(html)
        assert len(issues) == 0

    def test_empty_table_caught(self):
        html = "<table><tr><th>Week</th><th>Phase</th></tr></table>"
        issues = check_empty_tables(html)
        assert len(issues) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
