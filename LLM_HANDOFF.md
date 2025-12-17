# LLM Handoff: Athlete OS - Coaching Intake System

## Project Overview

**Athlete OS** is a comprehensive coaching intake and personalized training plan generation system. It enables individualized coaching at scale by collecting detailed athlete information via a web form, storing profiles in YAML format, and automatically generating personalized training plans using the existing unified plan generator from the `gravel-landing-page-project` repository.

**Repository:** `athlete-profiles` (https://github.com/wattgod/athlete-profiles)

---

## Current State: COMPLETE & DEPLOYED

### ✅ What's Built

1. **Comprehensive Coaching Intake Form** (`docs/athlete-questionnaire.html`)
   - 60+ questions across 16 sections
   - Neo-brutalist styling matching `survey.html` from main project
   - Progress bar with completion percentage
   - Collapsible sections (click header to expand/collapse)
   - Save/Resume functionality (localStorage)
   - Conditional field logic (show/hide based on answers)
   - Real-time progress tracking
   - Deployed on GitHub Pages: https://wattgod.github.io/athlete-profiles/athlete-questionnaire.html

2. **Profile Creation System** (`athletes/scripts/create_profile_from_form.py`)
   - Converts form JSON data to `profile.yaml` format
   - Handles all 60+ questions
   - Parses race lists, equipment, health conditions, etc.
   - Generates athlete IDs from names
   - Calculates age from birthday

3. **Derivation Logic** (`athletes/scripts/derive_classifications.py`)
   - `derive_tier()` - Classifies athlete (ayahuasca/finisher/compete/podium)
   - `calculate_plan_weeks()` - Determines plan duration
   - `determine_starting_phase()` - Sets initial training phase
   - `determine_strength_frequency()` - Sets strength sessions per week
   - `classify_equipment()` - Equipment tier classification
   - `get_exercise_exclusions()` - Auto-excludes exercises based on injuries
   - `identify_key_days()` - Finds suitable days for key cycling sessions
   - `identify_strength_days()` - Finds suitable days for strength sessions

4. **Weekly Structure Builder** (`athletes/scripts/build_weekly_structure.py`)
   - Creates custom weekly schedule based on athlete preferences
   - Respects availability, time slots, and duration constraints
   - Places strength sessions appropriately
   - Avoids conflicts with key cycling days

5. **Plan Generator** (`athletes/scripts/generate_athlete_plan.py`)
   - Orchestrates full workflow:
     1. Validates profile
     2. Derives classifications
     3. Builds weekly structure
     4. Calls unified plan generator with overrides
     5. Generates personalized guide
   - Integrates with `gravel-landing-page-project/races/unified_plan_generator.py`

6. **Profile Validator** (`athletes/scripts/validate_profile.py`)
   - Validates required fields
   - Checks enum values
   - Validates dates (allows today or future dates)
   - Warns on suspicious values

7. **Guide Generator** (`athletes/scripts/generate_athlete_guide.py`)
   - Creates personalized training guide markdown
   - Includes schedule, exclusions, phase progression, race-specific focus

8. **Documentation**
   - `QUESTIONNAIRE_QUESTIONS_AND_LOGIC.md` - Complete question reference
   - `QUESTIONNAIRE_ANALYSIS.md` - Question justification analysis
   - `ATHLETE_OS_SUMMARY.md` - System overview
   - `TESTING_GUIDE.md` - Testing process documentation

---

## Key Files & Structure

```
athlete-profiles/
├── docs/
│   └── athlete-questionnaire.html          # Public-facing intake form (GitHub Pages)
├── athletes/
│   ├── templates/
│   │   ├── questionnaire_schema.yaml        # Form field definitions
│   │   └── profile_template.yaml            # Profile structure template
│   ├── scripts/
│   │   ├── validate_profile.py             # Profile validation
│   │   ├── derive_classifications.py       # Auto-derive tier, phase, etc.
│   │   ├── build_weekly_structure.py       # Custom weekly schedule
│   │   ├── generate_athlete_plan.py        # Main plan generator
│   │   ├── generate_athlete_guide.py       # Guide generator
│   │   ├── create_profile_from_form.py     # Form → YAML converter
│   │   └── validate_submission.py          # Server-side form validation
│   └── {athlete-id}/
│       ├── profile.yaml                    # Athlete profile (YAML)
│       └── plans/
│           └── {plan-id}/
│               ├── plan_config.yaml
│               ├── guide.md
│               └── workouts/               # Generated ZWO files
├── .github/
│   └── workflows/
│       └── athlete-intake.yml              # GitHub Actions workflow (TODO: wire up)
└── QUESTIONNAIRE_QUESTIONS_AND_LOGIC.md    # Complete question reference
```

---

## Integration Points

### With `gravel-landing-page-project` Repository

The system integrates with the unified plan generator:

**File:** `gravel-landing-page-project/races/unified_plan_generator.py`

**Integration Parameters:**
- `weekly_structure_override` - Custom weekly schedule from athlete preferences
- `exercise_exclusions` - Exercises to exclude based on injuries
- `equipment_available` - Available equipment list for exercise filtering

**How it works:**
1. Athlete fills out form → `profile.yaml` created
2. `derive_classifications.py` → Calculates tier, phase, exclusions
3. `build_weekly_structure.py` → Creates custom weekly schedule
4. `generate_athlete_plan.py` → Calls `unified_plan_generator.generate_unified_plan()` with overrides
5. Unified generator creates cycling + strength workouts with athlete-specific customizations

---

## Form Structure (60+ Questions)

### 16 Sections:

1. **Basic Information** (4 questions)
   - Name, Email, Phone, Birthday (age calculated automatically)

2. **Racing Goals & Success** (7 questions)
   - Has racing goals? (conditional fields)
   - Race list, success metrics, obstacles, training goals

3. **Training History & Assessment** (11 questions)
   - Training summary, years cycling, strengths/weaknesses, FTP, weekly volume, etc.

4. **Strength & Mobility** (3 questions)
   - Strength training? (conditional), mobility rating

5. **Training Log & Devices** (2 questions)
   - Training log, devices (checkboxes)

6. **Weekly Schedule** (21 questions - 7 days × 3 fields)
   - Day-by-day: Can train? Time? Duration?

7. **Work & Life Balance** (11 questions)
   - Work status (conditional), stress, sleep, relationships, time commitments

8. **Equipment Access** (8 checkboxes)
   - Smart trainer, power meter, gym, home gym, etc.

9. **Health & Medications** (6 questions)
   - Medications, health conditions, injuries, movement limitations

10. **Nutrition** (7 questions)
    - Diet styles, fluid intake, caffeine, alcohol, fueling strategy

11. **Bike Fit & Pain** (3 questions)
    - Last bike fit, pain? (conditional)

12. **Social Training** (2 questions)
    - Group ride frequency, importance

13. **Coaching History** (2 questions)
    - Previous coach? (conditional)

14. **Preferences** (3 questions)
    - Communication style, workout length, strength interest

15. **Target Race** (4 questions)
    - Race name, date, distance, B-priority events

16. **Personal Context** (3 questions)
    - Important people, anything else, life affecting training

---

## Conditional Field Logic

Fields that show/hide based on answers:

1. **Race list & Success metrics** → Show if "Has racing goals?" = Yes
2. **Weather description** → Show if "Weather limits training?" = Yes
3. **Strength routine** → Show if "Strength trains?" = Yes
4. **Work hours & Job stress** → Show if "Works?" = Yes
5. **Pain description** → Show if "Bike pain?" = Yes
6. **Coach experience** → Show if "Previous coach?" = Yes

**Day schedule fields** (Time & Duration) → Enabled when "Can train?" checkbox is checked

---

## Data Flow

```
Form Submission (JSON)
    ↓
validate_submission.py (server-side validation)
    ↓
create_profile_from_form.py (JSON → profile.yaml)
    ↓
validate_profile.py (validate YAML structure)
    ↓
derive_classifications.py (calculate tier, phase, exclusions)
    ↓
build_weekly_structure.py (create custom weekly schedule)
    ↓
generate_athlete_plan.py (call unified_plan_generator)
    ↓
generate_athlete_guide.py (create personalized guide)
    ↓
Profile + Plan + Guide saved to athletes/{athlete-id}/plans/{plan-id}/
```

---

## Outstanding Work / TODO

### High Priority

1. **Wire up GitHub Actions Workflow** (`.github/workflows/athlete-intake.yml`)
   - Currently created but not connected to form submission
   - Need to set up webhook endpoint or use `repository_dispatch`
   - Configure email secrets (`EMAIL_USERNAME`, `EMAIL_PASSWORD`)

2. **Set up Webhook Endpoint**
   - Form currently points to placeholder: `https://your-webhook-endpoint.com/athlete-intake`
   - Options:
     - Use Zapier/Make.com/n8n to trigger GitHub Actions
     - Create Cloudflare Worker
     - Use GitHub webhook directly (requires authentication)

3. **Test End-to-End Workflow**
   - Submit form → Verify profile created
   - Verify plan generation works
   - Verify email notification sent

### Medium Priority

4. **Update `profile_template.yaml`**
   - Currently has basic structure
   - Could add all new fields from comprehensive intake
   - Not blocking (system works with current template)

5. **Race Matching Logic**
   - Currently defaults to `unbound_gravel_200`
   - Could add fuzzy matching to match race names to race IDs

6. **Exercise Exclusion Enhancement**
   - Currently basic text parsing
   - Could add NLP to extract specific exercises from injury descriptions

### Low Priority

7. **Form Analytics**
   - Track completion rates
   - Identify drop-off points

8. **A/B Testing**
   - Test different question orders
   - Test shorter vs. longer form

---

## Testing

### Manual Testing Process

1. **Test Form Submission:**
   ```bash
   # Fill out form at https://wattgod.github.io/athlete-profiles/athlete-questionnaire.html
   # Submit form
   # Verify profile.yaml created in athletes/{athlete-id}/
   ```

2. **Test Full Workflow:**
   ```bash
   cd ~/athlete-profiles/athletes/scripts
   
   # Validate profile
   python validate_profile.py {athlete-id}
   
   # Derive classifications
   python derive_classifications.py {athlete-id}
   
   # Build weekly structure
   python build_weekly_structure.py {athlete-id}
   
   # Generate plan
   python generate_athlete_plan.py {athlete-id}
   
   # Generate guide
   python generate_athlete_guide.py {athlete-id}
   ```

3. **Verify Outputs:**
   - Check `athletes/{athlete-id}/profile.yaml` has all fields
   - Check `athletes/{athlete-id}/plans/{plan-id}/plan_config.yaml`
   - Check `athletes/{athlete-id}/plans/{plan-id}/guide.md`
   - Check ZWO files generated in `workouts/` directory

### Test Athlete

There's a test athlete profile: `athletes/matti-rowe/profile.yaml`

---

## Key Technical Details

### Profile YAML Structure

Profiles are stored as YAML files with these main sections:
- `name`, `email`, `phone`, `birthday`, `athlete_id`
- `primary_goal`, `target_race`, `secondary_races`
- `racing` (goals, success metrics, obstacles)
- `training_history` (summary, years, strengths, weaknesses)
- `fitness_markers` (FTP, weight, etc.)
- `weekly_availability` (total hours, cycling hours, strength sessions)
- `preferred_days` (7 days with availability, time_slots, max_duration_min)
- `cycling_equipment`, `strength_equipment`
- `injury_history`, `movement_limitations`
- `health_factors` (age, sleep, stress, medications)
- `work`, `life_balance`, `nutrition`, `bike`, `social`, `coaching`, `personal`
- `methodology_preferences`, `workout_preferences`, `strength_preferences`
- `coaching_style`, `platforms`, `communication`, `plan_start`

### Tier Classification Logic

```python
def derive_tier(profile):
    cycling_hours = profile['weekly_availability']['cycling_hours_target']
    goal_type = profile['target_race']['goal_type'] if profile.get('target_race') else None
    years_structured = profile['training_history']['years_structured']
    
    if cycling_hours >= 15 and goal_type == 'podium':
        return 'podium'
    elif cycling_hours >= 12 and goal_type == 'compete':
        return 'compete'
    elif cycling_hours >= 8:
        return 'finisher'
    else:
        return 'ayahuasca'
```

### Weekly Structure Generation

The `build_weekly_structure.py` script:
1. Takes athlete's `preferred_days` (availability, time_slots, max_duration)
2. Takes derived `strength_days` and `key_days`
3. Creates a custom weekly template with:
   - AM/PM workout assignments
   - Strength session placement
   - Key cycling session placement
   - Recovery day assignments
4. Ensures no strength within 48 hours before key sessions

---

## Dependencies

### Python Packages
- `pyyaml` - YAML parsing
- `datetime` - Date calculations
- `re` - Regex for parsing
- `pathlib` - File operations

### External Dependencies
- `gravel-landing-page-project` repository (for unified plan generator)
  - Must be in same parent directory or path configured
  - Uses: `races/unified_plan_generator.py`

---

## Recent Changes

1. **Removed redundant age field** - Age now calculated from birthday only
2. **Removed age calculation helper text** - Cleaner UI
3. **Created comprehensive documentation** - `QUESTIONNAIRE_QUESTIONS_AND_LOGIC.md`
4. **Form deployed to GitHub Pages** - Publicly accessible

---

## Next Steps for New LLM

1. **Review `QUESTIONNAIRE_QUESTIONS_AND_LOGIC.md`** - Understand all questions and logic
2. **Review `create_profile_from_form.py`** - Understand data conversion
3. **Set up webhook** - Connect form to GitHub Actions
4. **Test end-to-end** - Submit form, verify profile creation, verify plan generation
5. **Handle edge cases** - Test with missing data, invalid inputs, etc.

---

## Questions to Ask User

1. **Webhook Setup:** How do you want to handle form submissions? (Zapier, Cloudflare Worker, GitHub webhook, etc.)
2. **Email Service:** What email service should be used for notifications? (Gmail SMTP, SendGrid, etc.)
3. **Race Matching:** Should we add fuzzy matching for race names to race IDs?
4. **Exercise Exclusion:** Should we enhance injury parsing to extract specific exercises?
5. **Form Length:** Is 60+ questions acceptable, or should we split into multiple pages?

---

## Contact / Context

- **User:** Matti Rowe
- **Project:** Gravel God Cycling Coaching
- **Current Clients:** 19 at $200-300/month
- **Goal:** Scale coaching with personalized plans at scale
- **Related Repo:** `gravel-landing-page-project` (training plan generation system)

---

## File Locations

- **Form:** `docs/athlete-questionnaire.html`
- **Profile Creator:** `athletes/scripts/create_profile_from_form.py`
- **Documentation:** `QUESTIONNAIRE_QUESTIONS_AND_LOGIC.md`
- **Test Athlete:** `athletes/matti-rowe/profile.yaml`

---

**Status:** System is functionally complete. Main outstanding work is connecting the form submission to the backend workflow via webhook/GitHub Actions.

