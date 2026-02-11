# ZWO Format Lessons Learned

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

## Files That Must Be Checked

1. `generate_athlete_package.py` - Contains `ZWO_TEMPLATE` and `create_workout_blocks()`
2. `workout_library.py` - Contains `generate_progressive_interval_blocks()` and `generate_progressive_endurance_blocks()`

## Regression Tests

Run before ANY deployment:

```bash
cd /Users/mattirowe/Documents/GravelGod/athlete-profiles/athletes/scripts
python3 -m pytest test_zwo_format.py -v
```

All tests MUST pass, especially:
- `test_no_8_space_indent_in_generate_athlete_package`
- `test_no_8_space_indent_in_workout_library`
- `test_all_benjy_workouts`

## Reference Files

Working reference file that imports correctly:
- `/Users/mattirowe/Downloads/Drop_Down_1_Updated.zwo`

Documentation:
- `/Users/mattirowe/Documents/GravelGod/reference-docs/Gravel God ZWO File Creation Skill v6.0...pdf`

## History of This Bug

1. Code was written with 8-space indent for workout blocks
2. Files looked valid (passed XML validation)
3. TrainingPeaks silently rejected them with "cannot process your workout"
4. Hours wasted debugging
5. Root cause: Indentation mismatch between template and library functions
6. Fix: Changed all 8-space to 4-space in both files

## Prevention

1. **ALWAYS run regression tests** before generating athlete packages
2. **NEVER change indentation** in ZWO-generating code without testing actual import
3. **Compare against working reference file** when in doubt
4. **Check BOTH files** - generate_athlete_package.py AND workout_library.py

---

**Remember:** Valid XML != Valid TrainingPeaks ZWO

The only test that matters is: **CAN IT IMPORT?**
