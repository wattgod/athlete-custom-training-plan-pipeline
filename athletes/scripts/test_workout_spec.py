"""G3 executable-segment description regressions."""
from workout_spec import (calendar_safe_description, normalize_zwo_blocks,
                          render_main_set, rewrite_zwo_description)


def test_description_reproduces_interval_reps_on_off_and_power_from_segments():
    blocks = ('<Warmup Duration="600" PowerLow="0.5" PowerHigh="0.7" />'
              '<IntervalsT Repeat="5" OnDuration="180" OnPower="1.15" '
              'OffDuration="120" OffPower="0.55" />')
    rendered = render_main_set(normalize_zwo_blocks(blocks))
    assert '5x3min' in rendered and '115% FTP' in rendered
    assert '2min recovery' in rendered and '55% FTP' in rendered


def test_final_xml_description_round_trips_same_interval_structure():
    xml = """<?xml version='1.0' encoding='UTF-8'?><workout_file><name>x</name>
    <description>MAIN SET:\n-old</description><workout><IntervalsT Repeat="4" OnDuration="60" OnPower="1.2" OffDuration="60" OffPower="0.5" /></workout></workout_file>"""
    rewritten = rewrite_zwo_description(xml)
    assert '4x1min @ 120% FTP, 1min recovery @ 50% FTP' in rewritten
    assert 'Repeat="4"' in rewritten and 'OnDuration="60"' in rewritten


def test_week_eight_and_non_prerace_calendar_phrases_are_not_hardcoded():
    assert 'Week 8 FTP' in calendar_safe_description('Week 1 FTP retest', plan_week=8)
    assert 'day before race' not in calendar_safe_description(
        'Openers the day before race', session_date='2026-06-01', event_date='2026-06-05').lower()
