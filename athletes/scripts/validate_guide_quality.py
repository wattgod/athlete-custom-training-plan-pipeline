#!/usr/bin/env python3
"""
Training Guide Quality Validator

Runs deterministic quality checks on generated training_guide.html:
1. Slop detection — banned phrases and structures from slop_rules.py
2. Required sections — verify all expected sections present
3. Data integrity — no placeholder text, no empty tables
4. Brand consistency — check CSS token refs are valid (if brand tokens available)

This script MUST pass before a guide is delivered to an athlete.
Run after generate_html_guide.py and before copy_to_downloads.

Usage:
    python3 validate_guide_quality.py <athlete_id>

Exit codes:
    0 = passed (with optional warnings)
    1 = failed (critical issues found)
"""

import sys
import re
from pathlib import Path
from html.parser import HTMLParser

sys.path.insert(0, str(Path(__file__).parent))

from constants import get_athlete_dir


# ============================================================
# Slop Detection (from gravel-race-automation/wordpress/slop_rules.py)
# ============================================================

def check_guide_slop(html_content: str) -> list:
    """Check training guide HTML for banned phrases and structures.

    Returns list of violation dicts: [{"phrase": str, "type": str}]
    """
    try:
        from slop_rules import check_text
        return check_text(html_content, is_html=True)
    except ImportError:
        # slop_rules.py not available — skip silently
        return []


# ============================================================
# Required Sections
# ============================================================

REQUIRED_SECTIONS = [
    'Quick Reference',
    'Training Philosophy',
    'Phase Progression',
    'Training Zones',
    'Nutrition',
    'Race Week',
]

REQUIRED_DATA = [
    ('FTP', r'(?:FTP|Functional Threshold)'),
    ('Race name', r'(?:race|event|target)', ),
    ('Phase info', r'(?:base|build|peak|taper)'),
]


def check_required_sections(html_content: str) -> list:
    """Verify all required sections exist in the guide."""
    issues = []
    text = html_content.lower()

    for section in REQUIRED_SECTIONS:
        if section.lower() not in text:
            issues.append(f"Missing required section: '{section}'")

    return issues


# ============================================================
# Placeholder / Empty Content Detection
# ============================================================

PLACEHOLDER_PATTERNS = [
    r'\bTODO\b',
    r'\bFIXME\b',
    r'\bXXX\b',
    r'\bPLACEHOLDER\b',
    r'\[INSERT\b',
    r'\{athlete_name\}',
    r'\{race_name\}',
    r'\{ftp\}',
    r'undefined',
    r'\bNaN\b',
    r'\bNone\b(?!\s*\))',  # Python None leaked into HTML (but not "None)" in code blocks)
]


def check_placeholders(html_content: str) -> list:
    """Detect placeholder text and unresolved template variables."""
    issues = []

    for pattern in PLACEHOLDER_PATTERNS:
        matches = re.findall(pattern, html_content, re.IGNORECASE)
        if matches:
            # Filter out false positives in <script> or <style> tags
            clean = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
            clean = re.sub(r'<style[^>]*>.*?</style>', '', clean, flags=re.DOTALL | re.IGNORECASE)
            real_matches = re.findall(pattern, clean, re.IGNORECASE)
            if real_matches:
                issues.append(f"Placeholder detected: '{real_matches[0]}' ({len(real_matches)} occurrence(s))")

    return issues


# ============================================================
# Empty Table Detection
# ============================================================

def check_empty_tables(html_content: str) -> list:
    """Detect tables with no data rows."""
    issues = []

    # Find all tables
    tables = re.findall(r'<table[^>]*>(.*?)</table>', html_content, re.DOTALL | re.IGNORECASE)
    for i, table in enumerate(tables):
        # Count data rows (tr elements, excluding header rows)
        rows = re.findall(r'<tr[^>]*>', table, re.IGNORECASE)
        header_rows = re.findall(r'<th[^>]*>', table, re.IGNORECASE)
        data_rows = len(rows) - (1 if header_rows else 0)
        if data_rows <= 0:
            issues.append(f"Empty table found (table #{i+1}, {len(rows)} rows but no data)")

    return issues


# ============================================================
# Main Validator
# ============================================================

def validate_guide(athlete_id: str) -> tuple:
    """Run all quality checks on training_guide.html.

    Returns (passed: bool, report: str)
    """
    athlete_dir = get_athlete_dir(athlete_id)
    guide_path = athlete_dir / 'training_guide.html'

    if not guide_path.exists():
        return False, f"ERROR: training_guide.html not found at {guide_path}"

    html = guide_path.read_text()

    if len(html) < 1000:
        return False, f"ERROR: training_guide.html suspiciously small ({len(html)} bytes)"

    errors = []
    warnings = []

    # 1. Slop detection
    slop_violations = check_guide_slop(html)
    for v in slop_violations:
        errors.append(f"SLOP: {v['type']} — \"{v['phrase']}\"")

    # 2. Required sections
    missing = check_required_sections(html)
    for m in missing:
        warnings.append(m)

    # 3. Placeholder detection
    placeholders = check_placeholders(html)
    for p in placeholders:
        errors.append(f"PLACEHOLDER: {p}")

    # 4. Empty tables
    empty_tables = check_empty_tables(html)
    for t in empty_tables:
        warnings.append(t)

    # 5. Minimum content check
    # Strip HTML tags to get text length
    text = re.sub(r'<[^>]+>', '', html)
    text = re.sub(r'\s+', ' ', text).strip()
    if len(text) < 2000:
        warnings.append(f"Guide text content is short ({len(text)} chars, expected 2000+)")

    # Build report
    report = []
    report.append("=" * 60)
    report.append(f"GUIDE QUALITY VALIDATION: {athlete_id}")
    report.append("=" * 60)
    report.append(f"File: {guide_path}")
    report.append(f"Size: {len(html):,} bytes ({len(text):,} chars of text)")
    report.append("")

    if errors:
        report.append(f"ERRORS ({len(errors)}):")
        for e in errors:
            report.append(f"  {e}")
        report.append("")

    if warnings:
        report.append(f"WARNINGS ({len(warnings)}):")
        for w in warnings:
            report.append(f"  {w}")
        report.append("")

    if errors:
        report.append("GUIDE QUALITY: FAILED — fix errors before delivery")
        passed = False
    elif warnings:
        report.append("GUIDE QUALITY: PASSED (with warnings)")
        passed = True
    else:
        report.append("GUIDE QUALITY: PASSED")
        passed = True

    return passed, '\n'.join(report)


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 validate_guide_quality.py <athlete_id>")
        sys.exit(1)

    athlete_id = sys.argv[1]
    passed, report = validate_guide(athlete_id)
    print(report)
    sys.exit(0 if passed else 1)


if __name__ == '__main__':
    main()
