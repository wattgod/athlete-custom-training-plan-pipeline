"""Coach-facing TrainingPeaks delivery steps.

Automated apply is not live. These instructions are the fulfillment path:
approve the sealed plan, then load it in TrainingPeaks by hand.
"""

from __future__ import annotations

from typing import Any, Mapping


def trainingpeaks_delivery_steps(
    *,
    plan_start: str = "",
    race_week_monday: str = "",
) -> list[str]:
    """Return ordered coach steps. No athlete email or account id."""
    week1 = f" Place week 1 on {plan_start}." if plan_start else ""
    race = (
        f" Race week starts {race_week_monday}." if race_week_monday else ""
    )
    return [
        "Search Athletes in TrainingPeaks Coach for the order email "
        "(coaching brief or order notification).",
        "If no account: Add athlete with that email and send the TrainingPeaks invite.",
        "Import dated ZWO files from the full package download, not the "
        "review bundle. The review bundle is for reading; workouts live in "
        "the full package.",
        f"Drop each ZWO on its calendar day.{week1}{race} "
        "Do not place sessions before the generation date.",
        "Spot-check week 1, one mid-plan week, and race week.",
        "Send the athlete email only after the calendar is loaded.",
    ]


def trainingpeaks_delivery_markdown(
    *,
    plan_start: str = "",
    race_week_monday: str = "",
) -> str:
    steps = trainingpeaks_delivery_steps(
        plan_start=plan_start, race_week_monday=race_week_monday)
    lines = [
        "## TrainingPeaks delivery",
        "",
        "Automated calendar apply is not live. After you Approve the sealed "
        "revision, load the plan in TrainingPeaks:",
        "",
    ]
    for index, step in enumerate(steps, 1):
        lines.append(f"{index}. {step}")
    lines.append("")
    return "\n".join(lines)


def trainingpeaks_delivery_html(
    *,
    plan_start: str = "",
    race_week_monday: str = "",
) -> str:
    from html import escape

    steps = trainingpeaks_delivery_steps(
        plan_start=plan_start, race_week_monday=race_week_monday)
    items = "".join(f"<li>{escape(step)}</li>" for step in steps)
    return (
        "<p>Automated calendar apply is not live. After you Approve the "
        "sealed revision, load the plan in TrainingPeaks:</p>"
        f"<ol>{items}</ol>"
    )


def plan_dates_for_delivery(plan_dates: Mapping[str, Any] | None) -> dict[str, str]:
    data = plan_dates or {}
    return {
        "plan_start": str(data.get("plan_start") or ""),
        "race_week_monday": str(data.get("race_week_monday") or ""),
    }
