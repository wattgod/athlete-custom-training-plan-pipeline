# Athlete OS Testing Guide

## Quick Test Process

### 1. Create Test Athlete Profile

```bash
cd ~/athlete-profiles

# Create new athlete directory
mkdir -p athletes/test-athlete

# Copy template
cp athletes/templates/profile_template.yaml athletes/test-athlete/profile.yaml
```

### 2. Fill Out Profile

Edit `athletes/test-athlete/profile.yaml` with test data:
- Name, email
- Target race (date must be in future)
- Training history
- Availability
- Equipment
- Injuries/limitations (optional)

**Quick test values:**
- Race date: `2026-06-07` (or any future date)
- Cycling hours: `12-15` (for "compete" tier)
- Strength sessions max: `2`
- Key days: `monday, tuesday, thursday, saturday`

### 3. Run Full Workflow

```bash
cd ~/athlete-profiles

# Step 1: Validate profile
python3 athletes/scripts/validate_profile.py test-athlete

# Step 2: Derive classifications (tier, phase, exclusions, etc.)
python3 athletes/scripts/derive_classifications.py test-athlete

# Step 3: Build weekly structure
python3 athletes/scripts/build_weekly_structure.py test-athlete

# Step 4: Generate plan
python3 athletes/scripts/generate_athlete_plan.py test-athlete

# Step 5: Generate guide (optional)
python3 athletes/scripts/generate_athlete_guide.py test-athlete
```

### 4. Review Outputs

```bash
# Check derived values
cat athletes/test-athlete/derived.yaml

# Check weekly structure
cat athletes/test-athlete/weekly_structure.yaml

# Check calendar
cat athletes/test-athlete/plans/*/calendar/training_calendar.md

# Check plan summary
cat athletes/test-athlete/plans/*/plan_summary.json

# Count generated workouts
ls -1 athletes/test-athlete/plans/*/workouts/*.zwo | wc -l
```

---

## What Each Step Does

### `validate_profile.py`
- Checks required fields are present
- Validates email format
- Validates dates (race date must be future)
- Validates enum values
- Warns on suspicious values

**Expected output:**
```
✅ Profile is valid!
```

### `derive_classifications.py`
- Calculates tier (ayahuasca/finisher/compete/podium)
- Calculates plan weeks (race date - start date)
- Determines starting phase
- Determines strength frequency
- Classifies equipment tier
- Identifies exercise exclusions (from injuries)
- Identifies key days (best for hard sessions)
- Identifies strength days (respects 48h recovery rule)

**Expected output:**
```
✅ Derived classifications saved to athletes/test-athlete/derived.yaml

Derived Values:
  Tier: compete
  Plan Weeks: 24
  Starting Phase: base_2
  Strength Frequency: 2x/week
  Equipment Tier: moderate
  Exercise Exclusions: 2 exercises
  Key Days: monday, tuesday, thursday, saturday
  Strength Days: sunday, saturday
```

### `build_weekly_structure.py`
- Creates custom weekly schedule from athlete preferences
- Respects availability and time constraints
- Places key sessions appropriately
- Avoids strength before key days
- Assigns strength to identified strength days

**Expected output:**
```
✅ Weekly structure saved to athletes/test-athlete/weekly_structure.yaml

Weekly Structure:
  Monday 🔑:    AM=intervals, PM=—
  Tuesday 🔑:   AM=—, PM=intervals
  Wednesday:    AM=easy_ride, PM=—
  Thursday 🔑:  AM=—, PM=intervals
  Friday:       AM=easy_ride, PM=—
  Saturday 🔑:  AM=long_ride, PM=—
  Sunday:       AM=strength, PM=—
```

### `generate_athlete_plan.py`
- Loads profile, derived values, and weekly structure
- Calls unified generator with athlete-specific overrides
- Generates cycling + strength workouts
- Creates unified calendar
- Saves plan config

**Expected output:**
```
Generating plan for test-athlete...
  Tier: compete
  Plan Weeks: 24
  Race: Unbound Gravel 200
  Race Date: 2026-06-07

✅ Plan generated successfully!
   Output: athletes/test-athlete/plans/2026-unbound_gravel_200
   Cycling workouts: 0
   Strength workouts: 42
```

### `generate_athlete_guide.py`
- Creates personalized training guide
- Includes schedule, exclusions, equipment
- Adds risk factors and considerations

**Expected output:**
```
✅ Guide generated successfully!
   Output: athletes/test-athlete/plans/*/guide.md
```

---

## Verification Checklist

After running the workflow, verify:

- [ ] **Profile validation passes** - No errors
- [ ] **Derived values make sense** - Tier matches hours, strength days are correct
- [ ] **Weekly structure shows strength** - Strength sessions appear on identified days
- [ ] **Calendar uses custom structure** - Not default template
- [ ] **Workouts generated** - ZWO files created
- [ ] **Calendar shows correct schedule** - Matches weekly structure
- [ ] **Exercise exclusions applied** - If injuries specified, exercises removed

---

## Common Issues

### "Invalid or non-future date"
- **Fix**: Update race date in profile to future date
- Check: `date +"%Y-%m-%d"` to see current date

### "Profile not found"
- **Fix**: Run from `~/athlete-profiles/` directory
- Or use absolute paths

### "Derived values not found"
- **Fix**: Run `derive_classifications.py` before `build_weekly_structure.py`

### "Weekly structure not found"
- **Fix**: Run `build_weekly_structure.py` before `generate_athlete_plan.py`

### Calendar uses default template
- **Fix**: Ensure `weekly_structure.yaml` exists and is valid
- Check that `generate_athlete_plan.py` passes `weekly_structure_override`

---

## Test with Existing Profile

To test with the existing `matti-rowe` profile:

```bash
cd ~/athlete-profiles

# Re-run workflow
python3 athletes/scripts/validate_profile.py matti-rowe
python3 athletes/scripts/derive_classifications.py matti-rowe
python3 athletes/scripts/build_weekly_structure.py matti-rowe
python3 athletes/scripts/generate_athlete_plan.py matti-rowe

# Review outputs
cat athletes/matti-rowe/plans/*/calendar/training_calendar.md | head -40
```

---

## Quick One-Liner Test

```bash
cd ~/athlete-profiles && \
python3 athletes/scripts/validate_profile.py matti-rowe && \
python3 athletes/scripts/derive_classifications.py matti-rowe && \
python3 athletes/scripts/build_weekly_structure.py matti-rowe && \
python3 athletes/scripts/generate_athlete_plan.py matti-rowe && \
echo "✅ Full workflow complete!" && \
cat athletes/matti-rowe/plans/*/calendar/training_calendar.md | head -30
```

---

## Expected File Structure After Testing

```
athletes/test-athlete/
├── profile.yaml              # Questionnaire responses
├── derived.yaml              # Auto-calculated values
├── weekly_structure.yaml      # Custom weekly schedule
└── plans/
    └── 2026-unbound_gravel_200/
        ├── workouts/          # ZWO files
        │   ├── W01_STR_Learn_to_Lift_A.zwo
        │   ├── W01_STR_Learn_to_Lift_B.zwo
        │   └── ...
        ├── calendar/
        │   ├── training_calendar.json
        │   └── training_calendar.md
        ├── plan_summary.json
        ├── plan_config.yaml
        └── guide.md
```

---

**Ready to test?** Start with step 1 above!

