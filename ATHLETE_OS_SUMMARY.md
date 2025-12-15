# Athlete OS - System Summary

## What Was Built

A complete system for **individual coaching at scale**, powered by the unified training system.

---

## Repository Structure

```
athlete-profiles/
├── README.md                          # Overview and quick start
├── ATHLETE_OS_SUMMARY.md             # This file
├── .gitignore                        # Excludes generated workout files
│
├── athletes/
│   ├── templates/
│   │   ├── questionnaire_schema.yaml    # Complete question definitions
│   │   └── profile_template.yaml        # Blank template for athletes
│   │
│   ├── scripts/
│   │   ├── derive_classifications.py     # Auto-derive tier/phase/exclusions
│   │   ├── validate_profile.py           # Profile validation
│   │   ├── build_weekly_structure.py     # Custom schedule builder
│   │   ├── generate_athlete_plan.py      # Main plan generator
│   │   └── generate_athlete_guide.py     # Personalized guide
│   │
│   └── [athlete-id]/                    # Per-athlete folders
│       ├── profile.yaml                  # Questionnaire responses
│       ├── derived.yaml                  # Auto-calculated values
│       ├── weekly_structure.yaml         # Custom schedule
│       └── plans/                        # Generated plans
│           └── [year]-[race-id]/
│               ├── plan_config.yaml
│               ├── guide.md
│               ├── workouts/             # ZWO files
│               └── calendar/             # Training calendar
```

---

## Key Components

### 1. Questionnaire System

**`questionnaire_schema.yaml`** - Complete schema definition:
- 8 sections, 26+ fields
- Validation rules for each field
- Enum options for select fields
- Required vs optional fields

**`profile_template.yaml`** - Blank template:
- All questions with examples
- Comments explaining each section
- Ready for athlete to fill out

### 2. Derivation Logic

**`derive_classifications.py`** - Auto-calculates:

- **Tier Classification** (`derive_tier`)
  - Based on cycling hours available
  - Modifiers: goal type, training history
  - Returns: ayahuasca, finisher, compete, podium

- **Plan Duration** (`calculate_plan_weeks`)
  - Based on race date and start date
  - Clamped to 8-24 weeks

- **Starting Phase** (`determine_starting_phase`)
  - May skip "Learn to Lift" if athlete has strength background
  - Considers current training phase

- **Strength Frequency** (`determine_strength_frequency`)
  - Based on tier + athlete's max sessions
  - Capped by strength background

- **Equipment Tier** (`classify_equipment`)
  - minimal, moderate, full
  - Based on available equipment

- **Exercise Exclusions** (`get_exercise_exclusions`)
  - From current injuries
  - From movement limitations
  - Auto-excludes based on injury area

- **Key Days** (`identify_key_days`)
  - Best days for hard cycling sessions
  - Based on availability + is_key_day_ok

- **Strength Days** (`identify_strength_days`)
  - Best days for strength
  - Avoids days before key sessions (48h rule)
  - Prefers AM time slots

### 3. Profile Validation

**`validate_profile.py`** - Comprehensive validation:
- Required field checks
- Email format validation
- Date format validation
- Enum value validation
- Logical consistency checks
- Warnings for suspicious values

### 4. Weekly Structure Builder

**`build_weekly_structure.py`** - Custom schedule:
- Respects athlete's preferred_days
- Places key sessions on appropriate days
- Places strength on non-conflicting days
- Returns structure compatible with unified generator

### 5. Plan Generator

**`generate_athlete_plan.py`** - Main generator:
- Loads profile and derived values
- Calls unified generator with athlete-specific parameters
- Saves plan config with athlete metadata
- Generates workouts and calendar

### 6. Guide Generator

**`generate_athlete_guide.py`** - Personalized guide:
- Plan overview
- Phase progression explanation
- Weekly schedule table
- Exercise modifications (exclusions)
- Equipment list
- Key days and strength days
- Risk factors and considerations

---

## Workflow

### 1. Create Athlete Profile

```bash
cp athletes/templates/profile_template.yaml athletes/john-doe/profile.yaml
# Edit profile.yaml with athlete information
```

### 2. Validate Profile

```bash
python athletes/scripts/validate_profile.py john-doe
```

### 3. Derive Classifications

```bash
python athletes/scripts/derive_classifications.py john-doe
```

Output: `athletes/john-doe/derived.yaml`

### 4. Build Weekly Structure

```bash
python athletes/scripts/build_weekly_structure.py john-doe
```

Output: `athletes/john-doe/weekly_structure.yaml`

### 5. Generate Plan

```bash
python athletes/scripts/generate_athlete_plan.py john-doe
```

Output: `athletes/john-doe/plans/2025-unbound-200/`

### 6. Generate Guide

```bash
python athletes/scripts/generate_athlete_guide.py john-doe
```

Output: `athletes/john-doe/plans/2025-unbound-200/guide.md`

---

## Integration with Unified System

The Athlete OS system uses the unified training system from `gravel-landing-page-project`:

- **Phase Alignment** - Same configuration
- **Tier Variation** - Same logic, but personalized
- **Race Profiles** - Same race-specific customization
- **Unified Generator** - Called with athlete-specific overrides

**Key Differences**:
- Individual profiles vs batch generation
- Custom weekly structure vs templates
- Exercise exclusions based on injuries
- Equipment filtering
- Personalized guides

---

## Example: Tier Classification Logic

```python
def derive_tier(profile):
    hours = profile["weekly_availability"]["cycling_hours_target"]
    
    if hours <= 5:
        return "ayahuasca"
    elif hours <= 10:
        return "finisher"
    elif hours <= 16:
        return "compete"
    else:
        return "podium"
    
    # Modifiers:
    # - Goal type (podium goal but limited time)
    # - Training history (new athletes capped at compete)
```

---

## Example: Exercise Exclusions

```python
# From injury: knee, moderate severity
exclusions = [
    "Jump Squat",
    "Box Jump",
    "Split Squat Jump",
    "Bulgarian Split Squat"
]

# From limitation: overhead_reach = painful
exclusions += [
    "Overhead Press",
    "Turkish Get-Up"
]
```

---

## Example: Weekly Structure

```yaml
days:
  monday:
    am: "strength"
    pm: null
    is_key_day: false
    notes: "Strength session"
  
  tuesday:
    am: null
    pm: "intervals"
    is_key_day: true
    notes: "Key session - intervals"
  
  # ... etc
```

---

## Next Steps

### Immediate
1. **Test with example athlete** - Create test profile and generate plan
2. **Wire unified generator** - Ensure integration works
3. **Add exercise substitution** - Replace excluded exercises

### Short-term
1. **Web form** - Build form to collect questionnaire
2. **GitHub Actions** - Auto-generate on profile update
3. **Plan updates** - Regenerate plan when profile changes

### Long-term
1. **Coaching dashboard** - View all athletes
2. **Progress tracking** - Update fitness markers
3. **Plan adjustments** - Modify plan mid-cycle

---

## Status

✅ **Core System Complete**

- Questionnaire schema: ✅
- Profile template: ✅
- Derivation logic: ✅
- Validation: ✅
- Weekly structure builder: ✅
- Plan generator: ✅
- Guide generator: ✅

**Ready for**: Testing with example athlete, integration with unified system

---

**Repository**: `/Users/mattirowe/athlete-profiles`  
**Status**: Initial commit complete  
**Next**: Test workflow with example athlete

