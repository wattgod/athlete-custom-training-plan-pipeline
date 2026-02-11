# Athlete Custom Training Plan Pipeline - Lessons Learned

**Date:** February 2026
**Status:** CRITICAL - DO NOT IGNORE
**Impact:** ZWO files that don't follow these rules WILL NOT IMPORT into TrainingPeaks

---

## THE PROBLEM

TrainingPeaks ZWO import is EXTREMELY sensitive to whitespace/indentation. Files that are valid XML can still fail to import if the indentation is wrong.

## THE SOLUTION

### Exact Format Required

```xml
<?xml version='1.0' encoding='UTF-8'?>
<workout_file>
  <author>Gravel God Training</author>
  <name>{name}</name>
  <description>{description}</description>
  <sportType>bike</sportType>
  <workout>
    <Warmup Duration="300" PowerLow="0.50" PowerHigh="0.68"/>
    <SteadyState Duration="600" Power="0.65"/>
    <Cooldown Duration="300" PowerLow="0.60" PowerHigh="0.45"/>
  </workout>
</workout_file>
```

### Critical Rules

| Element | Indent | Example |
|---------|--------|---------|
| XML declaration | 0 spaces | `<?xml version='1.0'...` |
| workout_file | 0 spaces | `<workout_file>` |
| author, name, etc | 2 spaces | `  <author>` |
| workout tag | 2 spaces | `  <workout>` |
| Warmup, SteadyState, etc | 4 spaces | `    <Warmup ...` |
| textevent (nested) | 6 spaces | `      <textevent ...` |

### What BREAKS Import

- **8-space indent for workout blocks** - FATAL
- **6-space indent for workout tag** - FATAL
- **Double quotes in XML declaration** - May break on some systems
- **Inconsistent indentation** - Unpredictable failures
- **Nested textevent inside SteadyState, Warmup, or Cooldown** - FATAL (see below)

### CRITICAL: No Nested Elements in SteadyState/Warmup/Cooldown

**Only `<IntervalsT>` can have nested `<textevent>` elements.**

WRONG (breaks import):
```xml
<SteadyState Duration="600" Power="0.65">
    <textevent timeoffset="0" message="Stay steady"/>
</SteadyState>
```

CORRECT (works):
```xml
<SteadyState Duration="600" Power="0.65"/>
```

ALSO CORRECT (IntervalsT CAN have nested elements):
```xml
<IntervalsT Repeat="4" OnDuration="60" OffDuration="60" OnPower="1.20" OffPower="0.50">
    <textevent timeoffset="0" message="Go hard!"/>
</IntervalsT>
```

### Strength Workouts Must Have Content

Strength workout descriptions MUST include:
- **FOCUS**: Muscle group/purpose (e.g., "Lower body + core")
- **EXERCISES**: Full list with sets/reps
- **VIDEO LINKS**: Use `exercise_lookup.py` to get Vimeo/YouTube URLs from the 404-exercise library
- **EXECUTION**: Instructions for completing the workout

Example:
```
• FOCUS: Lower body + core

• EXERCISES:
• Goblet Squat - 3x12
  Video: https://vimeo.com/111035086
• Romanian Deadlift - 3x10
  Video: https://vimeo.com/111043979
...

• EXECUTION:
Complete all sets with good form. Rest 60-90 sec between sets.
```

## Files That Must Be Checked

1. `generate_athlete_package.py` - Contains `ZWO_TEMPLATE` and `create_workout_blocks()`
2. `workout_library.py` - Contains `generate_progressive_interval_blocks()`, `generate_progressive_endurance_blocks()`, and `generate_strength_zwo()`
3. `exercise_lookup.py` - Fuzzy matching for exercise video URLs
4. `exercise_video_library.json` - 404 exercises with Vimeo/YouTube video links

## Regression Tests

Run before ANY deployment:

```bash
cd /Users/mattirowe/Documents/GravelGod/athlete-profiles/athletes/scripts
python3 -m pytest test_zwo_format.py -v
```

All tests MUST pass, especially:
- `test_no_8_space_indent_in_generate_athlete_package`
- `test_no_8_space_indent_in_workout_library`
- `test_no_nested_textevent_in_steadystate`
- `test_all_benjy_workouts`

## Reference Files

Working reference file that imports correctly:
- `/Users/mattirowe/Downloads/Drop_Down_1_Updated.zwo`

Documentation:
- `/Users/mattirowe/Documents/GravelGod/reference-docs/Gravel God ZWO File Creation Skill v6.0...pdf`

## History of This Bug

### Bug #1: 8-Space Indent (Feb 2026)
1. Code was written with 8-space indent for workout blocks
2. Files looked valid (passed XML validation)
3. TrainingPeaks silently rejected them with "cannot process your workout"
4. Hours wasted debugging
5. Root cause: Indentation mismatch between template and library functions
6. Fix: Changed all 8-space to 4-space in both files

### Bug #2: Nested textevent in SteadyState (Feb 2026)
1. SteadyState elements had nested `<textevent>` tags for coaching cues
2. Files looked valid XML, but TrainingPeaks rejected them
3. Discovery: W15_Tue_May26_Anaerobic.zwo uploaded (self-closing SteadyState)
4. W01_Tue_Feb17_Endurance.zwo failed (had nested textevent in SteadyState)
5. Root cause: Only IntervalsT can have nested elements
6. Fix: Made ALL SteadyState, Warmup, Cooldown self-closing (end with `/>`)

### Bug #3: Empty Strength Workout Descriptions (Feb 2026)
1. Strength workout descriptions only showed workout name, no exercises
2. `generate_strength_zwo()` returned workout name but not full workout data
3. Fix: Return full workout dict, build description with exercises + video links
4. Added: `exercise_lookup.py` integration for 404-exercise video library

### Bug #4: Special Characters in Filenames (Feb 2026)
1. Filenames like `W10_Wed_Strength_Mobility_&_Stability.zwo` failed to upload
2. TrainingPeaks cannot handle `&` (ampersand) in filenames
3. Fix: Changed "Mobility & Stability" to "Mobility and Stability" in workout_library.py
4. Rule: **NO special characters in workout names/filenames** (no `&`, no `•`, no unicode)

### Bug #5: Special Characters in Descriptions (Feb 2026)
1. Bullet character (•) in workout descriptions may cause upload issues
2. Removed all • characters from description templates in generate_athlete_package.py
3. Rule: **Use plain ASCII only** - dashes (-) instead of bullets, standard quotes, no unicode symbols

## Prevention

1. **ALWAYS run regression tests** before generating athlete packages
2. **NEVER change indentation** in ZWO-generating code without testing actual import
3. **Compare against working reference file** when in doubt
4. **Check BOTH files** - generate_athlete_package.py AND workout_library.py

---

**Remember:** Valid XML != Valid TrainingPeaks ZWO

The only test that matters is: **CAN IT IMPORT?**
