#!/usr/bin/env python3
"""Generate a privacy-minimized coaching welcome guide from an approved case.

The case file remains private. The athlete-facing artifacts contain only the
operational details needed to use coaching; health disclosures and legal
receipts never flow into the guide.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import yaml

from brand_config import load_brands


def _status(case: dict, gate: str) -> str:
    if gate == "payment":
        return "confirmed" if case.get("receipts", {}).get("stripe_payment") else "pending"
    return str(case.get("verifications", {}).get(gate, {}).get("status") or "pending")


def _is_minor(case: dict) -> bool:
    return bool(case.get("athlete", {}).get("is_minor"))


def build_onboarding_context(case: dict, booking_url: str) -> dict:
    """Project a private onboarding case into an athlete-safe guide context."""
    if case.get("schema") != "coaching_onboarding_case/v1":
        raise ValueError("expected coaching_onboarding_case/v1")
    if not booking_url.startswith("https://"):
        raise ValueError("a verified HTTPS coaching booking URL is required")

    required = {
        "coach_fit": "approved",
        "identity": "verified",
        "health_clearance": ("cleared", "not_required"),
        "coaching_agreement": "signed",
        "data_consent": "signed",
        "payment": "confirmed",
    }
    if _is_minor(case):
        required["guardian_consent"] = "signed"
    blockers = []
    for gate, expected in required.items():
        accepted = expected if isinstance(expected, tuple) else (expected,)
        if _status(case, gate) not in accepted:
            blockers.append(gate)
    if blockers:
        raise ValueError("onboarding materials blocked by: " + ", ".join(blockers))

    registry = load_brands()
    brand_key = case.get("brand")
    brand = registry.get(brand_key)
    if not brand:
        raise ValueError("unknown coaching brand")
    coaching = brand.get("coaching", {})
    tier_key = case.get("tier")
    tier = coaching.get("tiers", {}).get(tier_key)
    if not tier:
        raise ValueError("unknown coaching tier")

    tiers = coaching.get("tiers", {})
    tier_order = ["min", "mid", "max"]
    services = []
    for inherited_key in tier_order[:tier_order.index(tier_key) + 1]:
        for service in tiers.get(inherited_key, {}).get("services", []):
            if str(service).lower().startswith("everything in "):
                continue
            if service not in services:
                services.append(service)

    questionnaire = case.get("questionnaire", {})
    return {
        "schema": "coaching_onboarding_materials/v1",
        "case_id": case["case_id"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "brand": brand_key,
        "brand_name": brand["name"],
        "athlete_name": case.get("athlete", {}).get("name", "Athlete"),
        "tier": tier_key,
        "tier_label": tier.get("label", tier_key.title()),
        "price_cents": tier.get("price_cents"),
        "billing_period_days": coaching.get("billing_period_days", 28),
        "services": services,
        "trainingpeaks_attach_url": coaching.get("trainingpeaks_attach_url", ""),
        "trainingpeaks_premium_included": bool(
            coaching.get("trainingpeaks_premium_included")),
        "booking_url": booking_url,
        "preferred_contact_channel": questionnaire.get(
            "preferred_contact_channel") or "TrainingPeaks comments",
        "desired_start_date": questionnaire.get("desired_start_date") or "To be confirmed",
        "home_timezone": questionnaire.get("home_timezone") or "To be confirmed",
        "minor_guardian_path": _is_minor(case),
        "response_target": "Usually within two business days",
    }


def render_onboarding_section(context: dict) -> str:
    """Render the shared athlete-facing onboarding chapter."""
    e = lambda value: html.escape(str(value or ""), quote=True)
    services = "".join(f"<li>{e(item)}</li>" for item in context.get("services", []))
    guardian = (
        "<p><strong>Parent/guardian:</strong> Your guardian is part of the "
        "setup and consent path. Include them when a schedule, communication, "
        "or safety decision needs their input.</p>"
        if context.get("minor_guardian_path") else ""
    )
    return f'''<section id="coaching-onboarding" class="gg-section" data-schema="coaching_onboarding_materials/v1">
  <h2>How Coaching Works</h2>
  <p>This is your operating guide for <strong>{e(context.get("tier_label"))} coaching</strong>. Your TrainingPeaks calendar is the source of truth for day-to-day training.</p>

  <div class="data-card">
    <div class="data-card__header">WHAT YOU GET</div>
    <div class="data-card__content"><ul>{services}</ul></div>
  </div>

  <h3>Your first 30 days</h3>
  <ol>
    <li><strong>Connect TrainingPeaks.</strong> <a href="{e(context.get("trainingpeaks_attach_url"))}">Attach your account to Matti</a>. Premium is included; do not buy it separately.</li>
    <li><strong>Book the kickoff call.</strong> <a href="{e(context.get("booking_url"))}">Choose a time here</a>. Start date: {e(context.get("desired_start_date"))}; timezone: {e(context.get("home_timezone"))}.</li>
    <li><strong>Run the first block.</strong> The opening weeks establish execution, recovery, and communication baselines before training gets more specific.</li>
    <li><strong>Close the loop.</strong> Your comments and completed files drive the next review and adjustment.</li>
  </ol>

  <h3>How to comment</h3>
  <p>Comment on the workout in TrainingPeaks after you finish. Include: how it felt; whether you completed the prescription; pain or unusual symptoms; fueling and hydration on longer sessions; and any schedule problem that changes the next few days. Short and specific beats a long recap.</p>
  <p>If you miss a workout, do not stack it onto the next day. Mark what happened and say when you can train next; I will decide whether it moves, changes, or disappears.</p>

  <h3>Calls, messages, and response time</h3>
  <p>Book calls through the private booking link above. Use {e(context.get("preferred_contact_channel"))} for time-sensitive coaching messages and TrainingPeaks comments for workout feedback. Normal coaching replies are <strong>{e(context.get("response_target"))}</strong>. Coaching messaging is not emergency monitoring; urgent medical or safety issues belong with local emergency or medical services.</p>
  {guardian}

  <h3>Billing and commitment</h3>
  <p>Coaching renews every {e(context.get("billing_period_days"))} days. There is no long-term commitment: cancel before the next renewal and access continues through the paid cycle. There is no cancellation fee.</p>
</section>'''


def render_standalone(context: dict) -> str:
    title = html.escape(f"{context['athlete_name']} — Coaching Welcome")
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title><style>body{{max-width:760px;margin:40px auto;padding:0 20px;font:18px/1.55 Georgia,serif;color:#1a1613}}h1,h2,h3{{line-height:1.15}}a{{color:#135f63}}.data-card{{border:2px solid #1a1613;margin:24px 0}}.data-card__header{{padding:10px 14px;background:#1a1613;color:white;font:700 13px monospace;letter-spacing:1px}}.data-card__content{{padding:8px 18px}}li{{margin:8px 0}}</style></head><body><h1>{html.escape(context['brand_name'])} Coaching Welcome</h1>{render_onboarding_section(context)}</body></html>'''


def render_onboarding_email(context: dict) -> tuple[str, str]:
    """Return an athlete-ready subject and plain-text operating guide."""
    first_name = str(context.get("athlete_name") or "there").split()[0]
    services = "\n".join(f"- {item}" for item in context.get("services", []))
    guardian = (
        "\nYour parent or guardian is included in setup, consent, and any "
        "schedule or safety decision that needs their input.\n"
        if context.get("minor_guardian_path") else ""
    )
    subject = f"Your {context.get('tier_label')} coaching guide"
    body = f"""Hey {first_name},

Here is the short version of how coaching works. Your TrainingPeaks calendar is the source of truth for day-to-day training.

WHAT YOU GET
{services}

YOUR FIRST STEPS
1. Connect TrainingPeaks if you are not already attached:
{context.get('trainingpeaks_attach_url')}
TrainingPeaks Premium is included. Do not purchase it separately.

2. Book the kickoff call:
{context.get('booking_url')}

3. Run the first block and leave a comment on each completed workout. Tell me how it felt, whether you completed the prescription, any pain or unusual symptoms, fueling on longer sessions, and anything that changes the next few days.

If you miss a workout, do not stack it onto the next day. Comment with what happened and when you can train next; I will decide whether it moves, changes, or disappears.

Use {context.get('preferred_contact_channel')} for time-sensitive coaching messages and TrainingPeaks comments for workout feedback. Normal coaching replies are usually within two business days. Coaching messaging is not emergency monitoring.
{guardian}
Coaching renews every {context.get('billing_period_days')} days. There is no long-term commitment: cancel before the next renewal and access continues through the paid cycle. There is no cancellation fee.

— Matti"""
    return subject, body


def inject_onboarding_section(guide_html: str, context: dict) -> str:
    """Idempotently add the shared onboarding chapter to a canonical guide."""
    guide_html = re.sub(
        r'\n*<section id="coaching-onboarding".*?</section>\n*',
        '\n\n', guide_html, count=1, flags=re.DOTALL)
    guide_html = guide_html.replace(
        '          <li><a href="#coaching-onboarding">How Coaching Works</a></li>\n',
        '', 1)
    guide_html = guide_html.replace(
        '<ol>\n',
        '<ol>\n          <li><a href="#coaching-onboarding">How Coaching Works</a></li>\n',
        1)
    return guide_html.replace(
        '<div class="gg-guide-content">',
        '<div class="gg-guide-content">\n\n' + render_onboarding_section(context),
        1)


def generate(case_path: Path, athlete_id: str, athletes_dir: Path,
             booking_url: str) -> tuple[Path, Path]:
    case = json.loads(case_path.read_text(encoding="utf-8"))
    return generate_from_case(case, athlete_id, athletes_dir, booking_url)


def generate_from_case(case: dict, athlete_id: str, athletes_dir: Path,
                       booking_url: str) -> tuple[Path, Path]:
    context = build_onboarding_context(case, booking_url)
    athlete_dir = athletes_dir / athlete_id
    if not (athlete_dir / "profile.yaml").is_file():
        raise ValueError(f"unknown athlete directory: {athlete_id}")
    context_path = athlete_dir / "coaching_onboarding.yaml"
    context_path.write_text(yaml.safe_dump(context, sort_keys=False), encoding="utf-8")
    welcome_path = athlete_dir / "coaching_welcome.html"
    welcome_path.write_text(render_standalone(context), encoding="utf-8")
    guide_path = athlete_dir / "training_guide.html"
    if guide_path.is_file():
        guide_path.write_text(inject_onboarding_section(
            guide_path.read_text(encoding="utf-8"), context), encoding="utf-8")
    return context_path, welcome_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("case_path", type=Path)
    parser.add_argument("athlete_id")
    parser.add_argument("--athletes-dir", type=Path,
                        default=Path(__file__).resolve().parents[1])
    parser.add_argument("--booking-url", default=os.environ.get("COACHING_BOOKING_URL", ""))
    args = parser.parse_args()
    context_path, welcome_path = generate(
        args.case_path, args.athlete_id, args.athletes_dir, args.booking_url)
    print(context_path)
    print(welcome_path)
