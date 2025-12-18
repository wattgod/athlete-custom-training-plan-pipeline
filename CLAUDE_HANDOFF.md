# Athlete OS System - Explanation for Claude

## What We Built

**Athlete OS** is an individualized coaching system that transforms the unified cycling + strength training system into personalized plans for each athlete. Instead of one-size-fits-all plans, each athlete gets a plan tailored to their:
- Schedule constraints (when they can train)
- Equipment access (what they have available)
- Injury history (exercises to avoid)
- Training preferences (key days, strength frequency)
- Race goals (target race, tier)

---

## The Problem We Solved

### Before
- Unified training system generated generic plans
- All athletes got the same weekly structure
- No way to customize for individual schedules
- No exercise exclusions for injuries
- No equipment filtering

### After
- Athlete fills out questionnaire → personalized plan
- Custom weekly structure based on actual availability
- Automatic exercise exclusions from injury history
- Equipment-aware exercise selection (ready for implementation)
- Unified calendar showing athlete's actual schedule

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    ATHLETE QUESTIONNAIRE                     │
│  (profile.yaml: schedule, equipment, injuries, goals)       │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              DERIVATION & CLASSIFICATION                     │
│  • Tier (ayahuasca/finisher/compete/podium)                 │
│  • Plan weeks (race date - start date)                      │
│  • Starting phase (may skip "Learn to Lift")                 │
│  • Strength frequency (tier + athlete max)                  │
│  • Exercise exclusions (from injuries)                      │
│  • Key days (best days for hard sessions)                   │
│  • Strength days (respects 48h recovery rule)              │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              CUSTOM WEEKLY STRUCTURE BUILDER                │
│  • Respects athlete availability                            │
│  • Places key sessions on identified key days               │
│  • Assigns strength to strength days                       │
│  • Avoids strength within 48h before key sessions            │
│  • Creates day-by-day schedule (AM/PM slots)               │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              UNIFIED PLAN GENERATOR                          │
│  (from gravel-landing-page-project)                          │
│                                                              │
│  Inputs:                                                     │
│  • weekly_structure_override (custom schedule)              │
│  • exercise_exclusions (injuries)                           │
│  • equipment_available (equipment list)                     │
│                                                              │
│  Outputs:                                                    │
│  • Cycling workouts (ZWO files)                            │
│  • Strength workouts (ZWO files)                           │
│  • Unified calendar (JSON + Markdown)                       │
│  • Plan summary                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Key Components

### 1. Questionnaire System
**Location**: `athletes/templates/questionnaire_schema.yaml` + `profile_template.yaml`

Athletes fill out a structured questionnaire covering:
- **Basics & Goals**: Name, email, target race, goal type
- **Current State**: Training history, fitness markers
- **Availability**: Weekly hours, preferred days, time slots
- **Equipment**: What they have access to
- **Injuries/Limitations**: What to avoid
- **Preferences**: Strength frequency, key day preferences

### 2. Derivation Logic
**Location**: `athletes/scripts/derive_classifications.py`

Automatically calculates:
- **Tier**: Based on `cycling_hours_target` + `goal_type` + `years_structured`
  - Ayahuasca: < 8 hours/week
  - Finisher: 8-12 hours/week
  - Compete: 12-18 hours/week
  - Podium: 18+ hours/week

- **Plan Weeks**: `race_date - plan_start.preferred_start`

- **Starting Phase**: May skip "Learn to Lift" if athlete has strength background

- **Strength Frequency**: Min of `strength_sessions_max` and tier-based frequency

- **Exercise Exclusions**: From `injury_history` and `movement_limitations`
  - Example: Knee injury → excludes "Jump Squat", "Box Jump"

- **Key Days**: Days where `is_key_day_ok = true` and availability allows

- **Strength Days**: Days that can handle strength, avoiding days immediately before key sessions

### 3. Weekly Structure Builder
**Location**: `athletes/scripts/build_weekly_structure.py`

Creates a custom weekly schedule that:
- Uses athlete's day preferences (`preferred_days`)
- Places key sessions on identified `key_days`
- Assigns strength to `strength_days`
- Respects `time_slots` (AM/PM) and `max_duration`
- Avoids conflicts (no strength within 48h before key sessions)

**Output format**:
```yaml
days:
  monday:
    am: intervals
    pm: null
    is_key_day: true
    notes: Key session - intervals or threshold
  sunday:
    am: strength
    pm: null
    is_key_day: false
    notes: Strength session
```

### 4. Unified Generator Integration
**Location**: `gravel-landing-page-project/races/unified_plan_generator.py`

**What we added**:
- `weekly_structure_override` parameter - Uses custom structure instead of default template
- `exercise_exclusions` parameter - Filters excluded exercises from descriptions
- `equipment_available` parameter - Ready for equipment-based filtering

**How it works**:
1. Unified generator receives athlete-specific overrides
2. Uses custom weekly structure to determine strength days
3. Applies exercise exclusions when generating workout descriptions
4. Generates calendar using athlete's actual schedule (not default template)

### 5. Exercise Exclusion Logic
**Location**: `unified_plan_generator.py` → `_apply_exercise_exclusions()`

When exercises are excluded:
1. Removes excluded exercises from workout descriptions
2. Cleans up extra blank lines
3. Adds note explaining the exclusion

**Example**:
- Excluded: "Jump Squat", "Box Jump"
- Workout description has these exercises removed
- Note added: "⚠️ Note: Some exercises have been excluded based on your injury history/limitations."

---

## Workflow

### Step-by-Step Process

1. **Create Profile**
   ```bash
   cp athletes/templates/profile_template.yaml athletes/john-doe/profile.yaml
   # Edit profile.yaml
   ```

2. **Validate**
   ```bash
   python3 athletes/scripts/validate_profile.py john-doe
   ```
   - Checks required fields
   - Validates dates (race date must be future)
   - Validates email format
   - Warns on suspicious values

3. **Derive Classifications**
   ```bash
   python3 athletes/scripts/derive_classifications.py john-doe
   ```
   - Calculates tier, phase, exclusions, days
   - Saves to `derived.yaml`

4. **Build Weekly Structure**
   ```bash
   python3 athletes/scripts/build_weekly_structure.py john-doe
   ```
   - Creates custom schedule
   - Saves to `weekly_structure.yaml`

5. **Generate Plan**
   ```bash
   python3 athletes/scripts/generate_athlete_plan.py john-doe
   ```
   - Calls unified generator with overrides
   - Generates workouts + calendar
   - Saves to `plans/[year]-[race-id]/`

6. **Generate Guide** (optional)
   ```bash
   python3 athletes/scripts/generate_athlete_guide.py john-doe
   ```
   - Creates personalized training guide

---

## Recent Fixes & Enhancements

### 1. Date Validation Fix
**Issue**: Validation failed for future dates due to datetime comparison  
**Fix**: Updated to compare dates only (not datetime), allows today or future dates

### 2. Weekly Structure Display
**Issue**: Strength sessions not shown in weekly structure output  
**Fix**: Updated builder to properly assign strength sessions, including Sunday

### 3. Unified Generator Integration
**Enhancement**: Added support for athlete-specific overrides
- `weekly_structure_override` - Custom schedule
- `exercise_exclusions` - Exercises to exclude
- `equipment_available` - Available equipment

### 4. Exercise Exclusion Application
**Enhancement**: Excluded exercises are now removed from workout descriptions with a note

---

## Integration Points

### Athlete OS → Unified System

The Athlete OS system integrates with the unified training system from `gravel-landing-page-project`:

1. **Phase Alignment**: Uses `phase_alignment.py` to map cycling phases to strength phases
2. **Tier Variation**: Uses `tier_config.py` for tier-specific volume/frequency
3. **Race Profiles**: Uses `race_strength_profiles.py` for race-specific customization
4. **Unified Generator**: Calls `unified_plan_generator.py` with athlete-specific overrides

### Data Flow

```
athlete-profiles/
  athletes/john-doe/
    profile.yaml              # Questionnaire responses
    ↓
    derived.yaml               # Auto-calculated (tier, phase, exclusions)
    ↓
    weekly_structure.yaml      # Custom schedule
    ↓
    plans/2026-unbound_200/
      workouts/               # ZWO files (cycling + strength)
      calendar/               # Unified calendar (JSON + Markdown)
      plan_summary.json        # Plan metadata
      guide.md                 # Personalized guide
```

---

## Key Features

### Personalization
- **Custom Weekly Structure**: Not a default template, but athlete's actual schedule
- **Exercise Exclusions**: Automatic based on injury history
- **Tier Classification**: Based on availability + goals, not just hours
- **Strength Day Selection**: Respects 48h recovery rule

### Integration
- **Unified Calendar**: Shows both cycling and strength in one view
- **Phase Alignment**: Strength phases follow cycling phases (no double-peaking)
- **Race-Specific**: Exercise emphasis based on race demands
- **Equipment-Aware**: Ready for equipment-based filtering

### Automation
- **Auto-Derivation**: Tier, phase, exclusions calculated automatically
- **Schedule Building**: Custom schedule built from preferences
- **Plan Generation**: One command generates everything

---

## Example: How It Works

### Input (Athlete Profile)
```yaml
target_race:
  date: "2026-06-07"
  goal_type: compete

weekly_availability:
  cycling_hours_target: 15
  preferred_days:
    monday:
      availability: available
      time_slots: ["am"]
      is_key_day_ok: true
    sunday:
      availability: available
      time_slots: ["am"]
      is_key_day_ok: false

injury_history:
  - type: knee
    exercises_to_avoid: ["Jump Squat", "Box Jump"]
```

### Output (Derived Values)
```yaml
tier: compete
plan_weeks: 24
strength_frequency: 2
exercise_exclusions:
  - Jump Squat
  - Box Jump
key_day_candidates:
  - monday
strength_day_candidates:
  - sunday
```

### Output (Weekly Structure)
```yaml
days:
  monday:
    am: intervals
    is_key_day: true
  sunday:
    am: strength
    is_key_day: false
```

### Output (Calendar)
```markdown
## Week 1: Base 1
*Strength: Learn to Lift (2x/week)*

| Day | Date | AM | PM | Strength | Notes |
|-----|------|----|----|----------|-------|
| Monday 🔑 | 2025-12-21 | intervals | — | None | Key session |
| Sunday | 2025-12-27 | strength | — | W01_STR_Learn_to_Lift_A.zwo | Strength session |
```

**Note**: Calendar uses custom structure (Monday = intervals, Sunday = strength), not default template.

---

## Testing

See `TESTING_GUIDE.md` for full testing instructions.

**Quick test**:
```bash
cd ~/athlete-profiles
python3 athletes/scripts/validate_profile.py matti-rowe
python3 athletes/scripts/derive_classifications.py matti-rowe
python3 athletes/scripts/build_weekly_structure.py matti-rowe
python3 athletes/scripts/generate_athlete_plan.py matti-rowe
```

---

## Repository Structure

```
athlete-profiles/
├── README.md
├── TESTING_GUIDE.md
├── INTEGRATION_ENHANCEMENTS.md
├── athletes/
│   ├── templates/
│   │   ├── questionnaire_schema.yaml    # Question definitions
│   │   └── profile_template.yaml         # Blank template
│   ├── scripts/
│   │   ├── validate_profile.py           # Profile validation
│   │   ├── derive_classifications.py     # Auto-derive tier/phase
│   │   ├── build_weekly_structure.py      # Custom schedule builder
│   │   ├── generate_athlete_plan.py      # Main generator
│   │   └── generate_athlete_guide.py     # Guide generator
│   └── [athlete-id]/
│       ├── profile.yaml                   # Questionnaire responses
│       ├── derived.yaml                   # Auto-calculated
│       ├── weekly_structure.yaml          # Custom schedule
│       └── plans/                         # Generated plans
└── .gitignore                            # Excludes generated plans
```

---

## What's Next

### High Priority
1. **Exercise Substitution** - Replace excluded exercises with alternatives
2. **Equipment-Based Filtering** - Filter exercises by available equipment
3. **More Test Athletes** - Validate with different profiles

### Medium Priority
4. **Web Form** - Build form to collect questionnaire
5. **GitHub Actions** - Auto-generate on profile update
6. **Exercise Library Integration** - Use exercise library for substitutions

---

## Key Takeaways

1. **Athlete OS** = Personalized coaching at scale
2. **Questionnaire** → **Derivation** → **Custom Schedule** → **Personalized Plan**
3. **Integration** with unified system via override parameters
4. **Automation** - One command generates everything
5. **Customization** - Respects schedule, equipment, injuries, preferences

---

**Status**: ✅ Production-ready for personalized plan generation

