#!/usr/bin/env python3
"""
Tests for webhook/email_templates.py — the day 1/3/7 follow-up copy.

Enforces the brand voice contract:
- structure matches what process_followup_emails() consumes
- required elements present (TrainingPeaks + guide on day 1, reply invite
  on day 3, exactly one coaching link on day 7)
- banned hype/slop phrases and emoji are absent
- subjects are plain: no exclamation marks, no clickbait

Run with: pytest webhook/tests/test_email_templates.py -v
"""

import re
import sys
from pathlib import Path

import pytest

# Import the module directly — it has no Flask/app dependencies.
sys.path.insert(0, str(Path(__file__).parent.parent))

from email_templates import FOLLOWUP_SEQUENCE, SIGNATURE


# Phrases that must never appear in customer email copy (case-insensitive).
BANNED_PHRASES = [
    'thrilled',
    'journey',
    'crush',
    'dive in',
    "let's dive",
    'amazing',
    'excited',
    "can't wait",
    'remember:',
    'no spam',
    'unlock',
    'game-changer',
    'supercharge',
]


def _all_copy():
    """Yield (label, text) for every subject and body in the sequence."""
    for f in FOLLOWUP_SEQUENCE:
        yield f"day {f['day']} subject", f['subject']
        yield f"day {f['day']} body", f['template']


def _contains_emoji(text):
    """True if text contains emoji or pictographic symbols.

    Em dashes and typographic quotes are allowed; emoji blocks are not.
    """
    for ch in text:
        cp = ord(ch)
        if 0x1F000 <= cp <= 0x1FFFF:  # emoji, symbols, pictographs
            return True
        if 0x2600 <= cp <= 0x27BF:  # misc symbols + dingbats
            return True
        if cp in (0xFE0F, 0x200D):  # variation selector, ZWJ
            return True
    return False


class TestSequenceStructure:
    """Shape must match what app.py's process_followup_emails() consumes."""

    def test_three_emails_on_days_1_3_7(self):
        assert [f['day'] for f in FOLLOWUP_SEQUENCE] == [1, 3, 7]

    def test_required_fields(self):
        for f in FOLLOWUP_SEQUENCE:
            assert 'day' in f
            assert 'subject' in f
            assert 'template' in f
            assert f['day'] > 0

    def test_first_name_placeholder(self):
        for f in FOLLOWUP_SEQUENCE:
            assert '{first_name}' in f['template']

    def test_templates_format_cleanly(self):
        """No stray braces that would blow up str.format()."""
        for f in FOLLOWUP_SEQUENCE:
            body = f['template'].format(first_name='Jesse')
            assert 'Jesse' in body
            assert '{' not in body
            assert '}' not in body


class TestRequiredElements:
    def _get(self, day):
        return next(f for f in FOLLOWUP_SEQUENCE if f['day'] == day)

    def test_day1_names_the_deliverables(self):
        """Day 1 must reference the guide and the TrainingPeaks calendar."""
        body = self._get(1)['template']
        assert 'TrainingPeaks' in body
        assert 'guide' in body.lower()

    def test_day1_does_not_mention_zwo_import(self):
        """Plans are delivered pre-loaded on TP via coach attach — there is
        no customer-facing .zwo import step. The old copy got this wrong."""
        body = self._get(1)['template']
        assert '.zwo' not in body.lower()
        assert 'zwift' not in body.lower()
        assert 'wahoo' not in body.lower()

    def test_day1_has_single_clear_first_action(self):
        body = self._get(1)['template']
        assert 'One thing to do first' in body

    def test_day3_invites_a_reply(self):
        body = self._get(3)['template']
        assert 'reply' in body.lower()

    def test_day3_has_no_marketing_links(self):
        """Template only knows {first_name}; per-event links are impossible,
        and generic links are banned."""
        body = self._get(3)['template']
        assert 'http' not in body

    def test_day7_has_exactly_one_link_and_its_coaching(self):
        body = self._get(7)['template']
        links = re.findall(r'https?://\S+', body)
        assert len(links) == 1
        assert links[0].startswith('https://gravelgodcycling.com/coaching/')

    def test_day7_states_the_price(self):
        """Numbers-first: the coaching bridge names the price, no games."""
        body = self._get(7)['template']
        assert '$199' in body

    def test_every_email_supports_reply_to_a_human(self):
        for f in FOLLOWUP_SEQUENCE:
            assert 'reply' in f['template'].lower(), (
                f"day {f['day']} must tell the athlete a reply reaches a human"
            )

    def test_signature_identity(self):
        assert 'Matti' in SIGNATURE
        assert 'Gravel God Coaching' in SIGNATURE
        for f in FOLLOWUP_SEQUENCE:
            assert 'Matti' in f['template']
            assert 'Gravel God Coaching' in f['template']


class TestVoiceRules:
    @pytest.mark.parametrize('label,text', list(_all_copy()))
    def test_no_banned_phrases(self, label, text):
        lowered = text.lower()
        for phrase in BANNED_PHRASES:
            assert phrase not in lowered, f"banned phrase {phrase!r} in {label}"

    @pytest.mark.parametrize('label,text', list(_all_copy()))
    def test_no_emoji(self, label, text):
        assert not _contains_emoji(text), f"emoji found in {label}"

    def test_subjects_are_plain(self):
        for f in FOLLOWUP_SEQUENCE:
            assert '!' not in f['subject'], f"day {f['day']} subject has hype"
            assert not f['subject'].isupper()

    def test_no_exclamation_cheerleading_in_bodies(self):
        for f in FOLLOWUP_SEQUENCE:
            assert '!' not in f['template'], (
                f"day {f['day']} body uses exclamation-point cheerleading"
            )
