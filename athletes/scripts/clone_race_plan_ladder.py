#!/usr/bin/env python3
"""Seed a seven-plan race ladder from the canonical tier profiles."""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
CELLS = (
    ("finisher", "12wk", "Finisher", "finish"),
    ("finisher", "8wk", "Finisher", "finish"),
    ("time-crunched", "12wk", "Time-Crunched", "finish"),
    ("time-crunched", "8wk", "Time-Crunched", "finish"),
    ("compete", "12wk", "Compete", "compete"),
    ("masters", "12wk", "Masters 50+", "finish"),
    ("save-my-race", "6wk", "Save My Race", "finish"),
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slug", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--date", required=True)
    parser.add_argument("--distance", required=True, type=float)
    parser.add_argument("--elevation", required=True, type=int)
    parser.add_argument("--discipline", choices=("gravel", "road"), required=True)
    parser.add_argument("--terrain", required=True)
    args = parser.parse_args()

    for cell, length, tier, goal in CELLS:
        source = ROOT / f"west-coast-gravel-{cell}-{length}" / "profile.yaml"
        athlete_id = f"{args.slug}-{cell}-{length}"
        target = ROOT / athlete_id / "profile.yaml"
        if target.exists():
            raise SystemExit(f"refusing to overwrite {target}")

        profile = yaml.safe_load(source.read_text())
        profile["name"] = f"{tier} {args.discipline.title()} Store Plan ({args.name})"
        profile["email"] = f"base@{'roadielabs' if args.discipline == 'road' else 'gravelgod'}.internal"
        profile["athlete_id"] = athlete_id
        profile["discipline_default"] = args.discipline
        profile["plan_duration_weeks_override"] = int(length.removesuffix("wk"))
        profile["plan_tier"] = tier
        climbing_clause = (
            f" and {args.elevation:,} feet of climbing"
            if args.elevation > 0
            else ""
        )
        profile["target_race"] = {
            "name": args.name,
            "race_id": args.slug,
            "date": args.date,
            "distance_miles": args.distance,
            "elevation_ft": args.elevation,
            "goal_type": goal,
            "goal": goal,
            "goal_description": (
                f"Execute {args.name}'s long route with controlled pacing across "
                f"{args.terrain}{climbing_clause}."
            ),
        }
        profile["a_events"] = [{
            "name": args.name,
            "date": args.date,
            "distance_miles": args.distance,
            "goal": goal,
            "priority": "A",
        }]
        profile["racing"]["race_list"] = f"{args.name} ({args.date}, {args.distance:g}, priority A)"
        profile["racing"]["success_metrics"] = (
            f"Pace {args.terrain}, fuel consistently, descend cleanly, and retain enough "
            f"strength to race the final kilometers."
        )
        profile["motivation"]["what_excites_you"] = f"Race {args.name} strong and healthy."
        profile["plan_start"]["notes"] = f"Weeks to {args.name} computed by the pipeline."

        target.parent.mkdir(parents=True)
        target.write_text(yaml.safe_dump(profile, sort_keys=False, allow_unicode=True))
        print(target)


if __name__ == "__main__":
    main()
