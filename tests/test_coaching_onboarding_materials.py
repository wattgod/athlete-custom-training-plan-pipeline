import sys
from pathlib import Path

import pytest


SCRIPTS = Path(__file__).parents[1] / "athletes" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from coaching_onboarding_materials import (  # noqa: E402
    build_onboarding_context,
    inject_onboarding_section,
    render_onboarding_email,
    render_onboarding_section,
)


def _case(minor=False):
    verifications = {
        "coach_fit": {"status": "approved"},
        "identity": {"status": "verified"},
        "health_clearance": {"status": "not_required"},
        "coaching_agreement": {"status": "signed"},
        "data_consent": {"status": "signed"},
    }
    if minor:
        verifications["guardian_consent"] = {"status": "signed"}
    return {
        "schema": "coaching_onboarding_case/v1",
        "case_id": "case-1",
        "brand": "gravelgod",
        "tier": "mid",
        "athlete": {"name": "Test Rider", "is_minor": minor},
        "questionnaire": {
            "preferred_contact_channel": "TrainingPeaks",
            "desired_start_date": "2026-09-01",
            "home_timezone": "America/Denver",
            "injuries": "must not appear",
        },
        "verifications": verifications,
        "receipts": {"stripe_payment": {"session_id": "cs_test"}},
    }


def test_context_is_privacy_minimized_and_uses_canonical_tier_services():
    context = build_onboarding_context(
        _case(), "https://calendar.example.com/matti/coaching")
    assert context["tier_label"] == "Mid"
    assert "Weekly training review" in context["services"]
    assert "Weekly plan adjustments" in context["services"]
    assert not any(item.startswith("Everything in") for item in context["services"])
    assert "questionnaire" not in context
    assert "injuries" not in context
    assert context["response_target"] == "Usually within two business days"


def test_render_includes_operating_instructions_and_no_public_code():
    section = render_onboarding_section(build_onboarding_context(
        _case(), "https://calendar.example.com/matti/coaching"))
    assert "How Coaching Works" in section
    assert "How to comment" in section
    assert "do not stack it onto the next day" in section
    assert "TrainingPeaks Premium" not in section  # copy says Premium is included
    assert "Premium is included" in section
    assert "NOSETUP" not in section
    assert "two business days" in section


def test_minor_materials_require_guardian_receipt_and_include_guardian_path():
    case = _case(minor=True)
    del case["verifications"]["guardian_consent"]
    with pytest.raises(ValueError, match="guardian_consent"):
        build_onboarding_context(case, "https://calendar.example.com/coaching")
    case["verifications"]["guardian_consent"] = {"status": "signed"}
    section = render_onboarding_section(build_onboarding_context(
        case, "https://calendar.example.com/coaching"))
    assert "Your guardian is part of the setup" in section


def test_booking_url_must_be_configured_and_https():
    with pytest.raises(ValueError, match="booking URL"):
        build_onboarding_context(_case(), "")


def test_guide_injection_is_idempotent_and_adds_toc_entry():
    context = build_onboarding_context(
        _case(), "https://calendar.example.com/coaching")
    guide = ('<nav><ol>\n<li><a href="#section-1">Plan</a></li></ol></nav>'
             '<div class="gg-guide-content"><section id="section-1">Plan</section></div>')
    once = inject_onboarding_section(guide, context)
    twice = inject_onboarding_section(once, context)
    assert twice.count('id="coaching-onboarding"') == 1
    assert twice.count('href="#coaching-onboarding"') == 1
    assert 'id="section-1"' in twice


def test_onboarding_email_contains_booking_comments_and_full_tier():
    context = build_onboarding_context(
        _case(), "https://calendar.example.com/coaching")
    subject, body = render_onboarding_email(context)
    assert subject == "Your Mid coaching guide"
    assert "Weekly training review" in body
    assert "Weekly plan adjustments" in body
    assert "Book the kickoff call" in body
    assert "do not stack it onto the next day" in body
    assert "NOSETUP" not in body
