# Pipeline Map — which script does what

If you only read one thing in this directory, read this.

## The current production pipeline

**`intake_to_plan.py`** — PRIMARY entry point.

This is the script the Stripe webhook runs for every paid order
(`webhook/app.py::run_pipeline`). It is also the script you run manually
to regenerate a plan from a markdown questionnaire.

```
questionnaire.md
   │
   ▼
intake_to_plan.py            ← THE ENTRY POINT (parses intake, builds profile)
   │
   ▼  (writes athletes/<id>/profile.yaml, then shells out to ↓)
   │
generate_full_package.py     ← internal 9-step orchestrator
   │
   ├─▶ validate_profile.py
   ├─▶ derive_classifications.py
   ├─▶ select_methodology.py
   ├─▶ calculate_fueling.py
   ├─▶ build_weekly_structure.py
   ├─▶ calculate_plan_dates.py
   ├─▶ generate_athlete_package.py   ← ZWO workout XML generator
   ├─▶ generate_html_guide.py
   └─▶ generate_dashboard.py
```

After the 9 steps, `intake_to_plan.py` runs the quality gates, generates
the coaching brief, builds the plan-preview verification dashboard, and
copies everything to `~/Downloads/<athlete-id>-training-plan/`.

## Running it

```bash
# From file:
python3 athletes/scripts/intake_to_plan.py --file intake.md

# From clipboard (macOS):
pbpaste | python3 athletes/scripts/intake_to_plan.py

# Dry run (parse + build profile, no plan generation):
python3 athletes/scripts/intake_to_plan.py --file intake.md --dry-run
```

## What lives where (don't confuse the entry point)

| File | Role |
| --- | --- |
| `intake_to_plan.py`         | **Primary entry point.** Production webhook + manual CLI. |
| `generate_full_package.py`  | Internal 9-step orchestrator. Also legacy webhook fallback. |
| `generate_athlete_package.py` | Internal. ZWO workout XML rendering (called in step 7). |
| `generate_html_guide.py`    | Internal. Data-driven HTML guide. |
| `generate_dashboard.py`     | Internal. Athlete-facing dashboard page. |
| `generate_plan_preview.py`  | Internal. Verification dashboard with 11 automated checks. |
| `nate_workout_generator.py` | Internal. 22 training systems, 95 archetypes, ZWO XML. |
| `known_races.py`            | Single source of truth for race dates and aliases. |
| `archetype_registry.py`     | Single source of truth for workout archetypes. |
| `constants.py`              | Validation bounds (FTP, weight, height, age, W/kg). |

## Tests

```bash
python3 -m pytest athletes/scripts/test_intake_to_plan.py -v
python3 -m pytest athletes/scripts/ -v
```

The CLAUDE.md at the repo root has the full count and category breakdown.

## Reasoning about pipeline failures

When the webhook reports a failure:

1. Get the intake JSON from the Railway volume:
   ```
   railway ssh --service stripe-webhook "cat /data/.intake/<intake-id>.json"
   ```
2. Replay locally:
   ```
   python3 -c "import json,sys; sys.path.insert(0,'webhook'); \
     from app import _questionnaire_to_markdown; \
     d=json.load(open('intake.json'))['data']; \
     open('intake.md','w').write(_questionnaire_to_markdown(d, name=d['name'], email=d['email']))"
   python3 athletes/scripts/intake_to_plan.py --file intake.md
   ```
3. Read the failure from the local terminal output (the webhook only logs
   the first 500 chars of stderr).
