# Athlete OS - Individual Coaching at Scale

**Personalized training plans powered by the unified cycling + strength system.**

## Overview

Athlete OS transforms the unified training system into individualized coaching. Each athlete gets a personalized plan that respects their:
- Schedule constraints
- Equipment access
- Injury history
- Training preferences
- Race goals

## Quick Start

### 1. Create Athlete Profile

```bash
cp athletes/templates/profile_template.yaml athletes/john-doe/profile.yaml
# Edit profile.yaml with athlete information
```

### 2. Validate Profile

```bash
python athletes/scripts/validate_profile.py john-doe
```

### 3. Generate Plan

```bash
python athletes/scripts/generate_athlete_plan.py john-doe
```

### 4. Output

```
athletes/john-doe/
├── profile.yaml              # Questionnaire responses
├── derived.yaml              # Auto-calculated values
└── plans/2025-unbound-200/
    ├── workouts/             # ZWO files
    ├── calendar/             # Training calendar
    └── guide.md              # Personalized guide
```

## System Architecture

```
Athlete Questionnaire → GitHub Repo → Personalized Generator → ZWO Files + Calendar
         ↓                   ↓                    ↓
    (Form/intake)     (athlete.yaml)      (unified_plan_generator)
```

## Key Features

- **Personalized Tier Classification** - Based on availability, not just hours
- **Custom Weekly Structure** - Respects athlete's actual schedule
- **Exercise Exclusions** - Automatic based on injuries/limitations
- **Equipment Filtering** - Only exercises athlete can actually do
- **Race-Specific Customization** - Exercise emphasis by race demands
- **Phase Alignment** - Strength follows cycling (no double-peaking)

## Repository Structure

```
athlete-profiles/
├── athletes/
│   ├── [athlete-id]/
│   │   ├── profile.yaml           # Questionnaire responses
│   │   ├── derived.yaml           # Auto-calculated values
│   │   ├── plans/                 # Generated training plans
│   │   ├── history/               # Profile update history
│   │   ├── notes/                 # Coach/athlete notes
│   │   └── metrics/               # Fitness tracking
│   └── templates/
│       └── profile_template.yaml  # Blank template
├── scripts/
│   ├── generate_athlete_plan.py   # Main generator
│   ├── validate_profile.py        # Profile validator
│   ├── derive_classifications.py  # Auto-derive tier/phase
│   ├── build_weekly_structure.py  # Custom schedule builder
│   └── generate_athlete_guide.py  # Personalized guide
└── README.md
```

## Integration with Unified System

This system uses the unified training system from `gravel-landing-page-project`:
- Phase alignment configuration
- Tier variation logic
- Race-specific profiles
- Unified plan generator

## Documentation

- [Questionnaire Schema](athletes/templates/questionnaire_schema.yaml) - Complete question definitions
- [Profile Template](athletes/templates/profile_template.yaml) - Blank template for athletes
- [Derivation Logic](athletes/scripts/derive_classifications.py) - How tier/phase are calculated
- [Weekly Structure Builder](athletes/scripts/build_weekly_structure.py) - Custom schedule logic

## License

Private - Individual Coaching System

