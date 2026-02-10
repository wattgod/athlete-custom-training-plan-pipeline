# Custom Training Plan Generation

Scripts for generating personalized training packages for Gravel God coaching clients.

## Quick Start

```bash
cd /Users/mattirowe/Documents/GravelGod/athlete-profiles/athletes/scripts
python3 generate_athlete_package.py <athlete_id>
```

---

## GENERATION CHECKLIST

Use this checklist for every custom plan delivery:

### Pre-Generation
- [ ] **Intake form completed** - All questionnaire data received from athlete
- [ ] **Profile created** - `profile.yaml` with all preferences
- [ ] **Day preferences set** - `preferred_days` section reflects athlete's schedule
  - [ ] Rest days marked as `availability: rest`
  - [ ] Key workout days have `is_key_day_ok: true`
  - [ ] Duration limits set via `max_duration_min`
  - [ ] Long ride day specified in `schedule_constraints.preferred_long_day`
- [ ] **Race data exists** - JSON file in `race_data/` directory

### Generation
- [ ] **Run pipeline scripts** (in order):
  ```bash
  python3 select_methodology.py <athlete-id>
  python3 calculate_fueling.py <athlete-id>
  python3 calculate_plan_dates.py <athlete-id>
  python3 generate_athlete_package.py <athlete-id>
  ```

### Quality Control
- [ ] **Run integrity test** - Must pass with 0 errors:
  ```bash
  python3 test_athlete_integrity.py <athlete-id>
  ```
- [ ] **Verify outputs**:
  - [ ] `training_guide.html` - Opens correctly, shows correct race name
  - [ ] `workouts/` - Contains ZWO files, FTP tests present
  - [ ] No Monday workouts (if Monday is rest day)
  - [ ] Key workouts only on key days (Sat/Sun for most athletes)
  - [ ] FTP test in Week 1 and before Build phase

### Delivery
- [ ] **Copy to delivery folder**:
  ```bash
  mkdir -p ~/Downloads/<athlete-id>-package/workouts
  cp /path/to/athlete/training_guide.html ~/Downloads/<athlete-id>-package/
  cp /path/to/athlete/workouts/*.zwo ~/Downloads/<athlete-id>-package/workouts/
  ```
- [ ] **Host guide for live URL** (GitHub Pages):
  ```bash
  # Copy to hosted guides repo
  cp training_guide.html /path/to/hosted-guides/<athlete-id>.html
  git add . && git commit -m "Add <athlete-name> training guide"
  git push
  ```
- [ ] **Send to athlete**:
  - [ ] Training guide URL: `https://<your-domain>/guides/<athlete-id>.html`
  - [ ] Workouts ZIP file (or folder)
  - [ ] TrainingPeaks import instructions

---

## Full Pipeline Details

### 1. Create Athlete Directory

```bash
mkdir -p /Users/mattirowe/Documents/GravelGod/athlete-profiles/athletes/<athlete-id>
```

### 2. Create profile.yaml from Intake Form

```yaml
# /athletes/<athlete-id>/profile.yaml
name: "First Last"
athlete_id: "first-last"

target_race:
  name: "SBT GRVL 75"
  race_id: "sbt_grvl_75"
  date: "2026-06-28"
  distance_miles: 75

fitness_markers:
  ftp_watts: 200
  weight_kg: 75

weekly_availability:
  cycling_hours_target: 5

# CRITICAL: Set day preferences from questionnaire
preferred_days:
  monday:
    availability: rest  # or available/limited/unavailable
    max_duration_min: 0
    is_key_day_ok: false
  tuesday:
    availability: limited
    max_duration_min: 60
    is_key_day_ok: false
  # ... etc for each day
  saturday:
    availability: available
    max_duration_min: 300
    is_key_day_ok: true
  sunday:
    availability: available
    max_duration_min: 300
    is_key_day_ok: true

schedule_constraints:
  preferred_long_day: "Saturday or Sunday"
  preferred_off_days: []
  end_heavy_training: "2026-06-01"  # Optional constraint
```

### 3. Create derived.yaml

```yaml
# /athletes/<athlete-id>/derived.yaml
athlete_id: "first-last"
tier: AYAHUASCA
ability_level: Intermediate
plan_weeks: 19
race_date: "2026-06-28"
plan_start: "2026-02-17"
heavy_training_end: "2026-06-01"  # Optional
```

### 4. Run Pipeline Scripts

```bash
# Methodology selection
python3 select_methodology.py <athlete-id>
# Creates: methodology.yaml

# Fueling calculation
python3 calculate_fueling.py <athlete-id>
# Creates: fueling.yaml

# Plan date calculation (respects constraints)
python3 calculate_plan_dates.py <athlete-id>
# Creates: plan_dates.yaml

# Generate complete package
python3 generate_athlete_package.py <athlete-id>
# Creates: training_guide.html, workouts/*.zwo, plan_summary.yaml
```

### 5. Run QC Tests

```bash
# REQUIRED: Run integrity check before delivery
python3 test_athlete_integrity.py <athlete-id>
```

**Must see:** `Critical: 0, Errors: 0`

Warnings are informational but should be reviewed.

---

## What the Tests Check

| Check | Level | Description |
|-------|-------|-------------|
| Race date consistency | CRITICAL | Profile, derived, plan_dates all match |
| Correct race data | CRITICAL | Guide shows correct race name |
| Plan weeks match | ERROR | derived.yaml matches plan_dates.yaml |
| FTP test Week 1 | ERROR | Baseline FTP test exists |
| No Monday workouts | ERROR | If Monday is rest day |
| Key workouts on key days | WARNING | Intervals/FTP only on is_key_day_ok days |
| Duration limits | WARNING | Workouts don't exceed max_duration_min |
| FTP test pre-Build | WARNING | Retest before intensity phase |

---

## Workout Schedule Logic

The generator respects athlete preferences from `preferred_days`:

| Availability | Result |
|--------------|--------|
| `rest` | No workout generated |
| `unavailable` | No workout generated |
| `available` + `is_key_day_ok: true` | Key workouts (intervals, FTP, etc.) |
| `available` + `is_key_day_ok: false` | Endurance only |
| `limited` | Recovery/easy workouts only |

**FTP Tests are scheduled on:**
- Week 1: First available key day (prefers Sat)
- Week before Build phase: First available key day

---

## Phase Progression

| Phase | Description | % of Plan |
|-------|-------------|-----------|
| base | Aerobic foundation | ~50% |
| build | Intensity introduction | 50-75% |
| peak | Race-specific sharpening | 75%+ |
| maintenance | Reduced load (if constrained) | Variable |
| taper | Final recovery | Last 2 weeks |
| race | Race week | Final week |

---

## Race Data

Race-specific data lives in:
```
/Users/mattirowe/Documents/GravelGod/guides/gravel-god-guides/race_data/
```

Example `sbt_grvl_75.json`:
```json
{
  "name": "SBT GRVL 75",
  "distance_miles": 75,
  "elevation_gain_feet": 5500,
  "avg_elevation_feet": 7500,
  "date": "2026-06-28",
  "terrain_description": "High-altitude gravel with technical descents"
}
```

---

## Known Race Dates (2026)

| Race | Date | Day |
|------|------|-----|
| SBT GRVL | June 28 | Sunday |
| Unbound 200 | May 30 | Saturday |

---

## Troubleshooting

**"Key workout on non-key day" warnings:**
- Check `preferred_days` in profile.yaml
- Ensure `is_key_day_ok: true` for days that should have intensity

**"Workout may exceed time limit" warnings:**
- Increase `max_duration_min` for that day, or
- Accept that long rides will exceed weekday limits

**FTP test missing:**
- Ensure at least one day has `is_key_day_ok: true`
- FTP test requires a key day to be scheduled

**Old workouts still present:**
- Generator now clears old workouts automatically
- If issues persist, manually delete `workouts/` folder
