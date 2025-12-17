# Review Checklist - Matti Rowe Test Profile

## ✅ What to Review

### 1. Tier Classification
**Question**: Does `compete` tier match your reality?  
**Your Input**: 12 hours cycling/week  
**System Output**: `compete` tier  
**Expected**: ✅ Should be compete (12 hours = compete range)

**Review**: ✅ **CORRECT** - 12 hours falls in compete tier (12-16 hours)

---

### 2. Strength Days Placement
**Question**: Are strength days where you'd actually put them?

**System Output**: 
- Saturday (AM strength + PM long ride)
- Sunday (AM strength)

**Your Preferences**:
- Saturday: Available AM, 300 min max, is_key_day_ok=true (long ride day)
- Sunday: Available AM, 180 min max, is_key_day_ok=false (recovery)
- Wednesday: Limited AM, 60 min max, is_key_day_ok=false

**Review Questions**:
- ✅ Is Saturday strength AM + long ride PM acceptable? (Strength before long ride is OK)
- ✅ Is Sunday strength acceptable? (Recovery day, no conflicts)
- ⚠️ Would you prefer Wednesday + Sunday instead? (Wednesday is limited to 60 min)

**Current Logic**: 
- Avoids Monday (before Tuesday key)
- Avoids Friday (before Saturday key)  
- Allows Saturday (AM strength before PM long ride)
- Allows Sunday (recovery day)

**Status**: ⚠️ **REVIEW NEEDED** - Does this match your preferences?

---

### 3. Exercise Exclusions
**Question**: Are injury exclusions correct?

**System Output**: `["Jump Squat", "Box Jump"]`

**Your Injury**: Left knee, minor severity, affects_strength=true  
**Explicit Exclusions**: Jump Squat, Box Jump

**Review**: ✅ **CORRECT** - System correctly excluded jumping exercises

**Note**: System could also exclude "Bulgarian Split Squat" if severity was higher, but correctly left it for minor injury.

---

### 4. Weekly Structure
**Question**: Does the calendar make sense?

**Current Calendar Shows** (from unified generator default):
```
Monday:    Strength AM
Tuesday:   Intervals PM (key)
Wednesday: Easy ride PM
Thursday:  Strength AM + Easy ride PM
Friday:    Rest/Easy
Saturday:  Long ride AM (key)
Sunday:    Easy ride/Rest
```

**Your Custom Structure** (from build_weekly_structure.py):
```
Monday:    Intervals AM (key)
Tuesday:   Intervals PM (key)
Wednesday: Easy ride AM
Thursday:  Intervals PM (key)
Friday:    Easy ride AM
Saturday:  Long ride AM (key)
Sunday:    Easy ride/Rest
```

**Issue**: Calendar shows default template, not your custom structure.

**Reason**: Unified generator doesn't yet support `weekly_structure_override` parameter.

**Status**: ⚠️ **NEEDS INTEGRATION** - Custom structure built but not applied to calendar

---

### 5. Plan Duration
**Question**: Is 21 weeks correct?

**Your Input**: 
- Start: 2025-01-06
- Race: 2025-06-07

**System Output**: 21 weeks

**Calculation**: Jan 6 → June 7 = ~21 weeks

**Review**: ✅ **CORRECT**

---

### 6. Starting Phase
**Question**: Should you start at base_2?

**System Output**: `base_2`

**Your Input**:
- Current phase: base
- Strength background: intermediate
- Years structured: 8

**Logic**: Has strength background + currently in base → skip early Learn to Lift

**Review**: ✅ **CORRECT** - Makes sense to start at base_2

---

## ⚠️ Issues Found

### 1. Calendar Uses Default Template
**Problem**: Calendar shows Monday/Thursday strength (default), not Saturday/Sunday (custom)

**Fix Needed**: Update unified generator to accept `weekly_structure_override`

**Status**: ⚠️ **KNOWN ISSUE** - Documented for next iteration

### 2. Date Validation
**Problem**: Validation failed for future date (2025-06-07)

**Fix Needed**: Update `validate_profile.py` date validation logic

**Status**: ⚠️ **MINOR** - Doesn't block generation

### 3. Strength Days Could Be Optimized
**Current**: Saturday + Sunday  
**Alternative**: Wednesday + Sunday (if athlete prefers separate days)

**Enhancement**: Consider athlete's `time_of_day` preference (separate_day)

**Status**: ℹ️ **OPTIMIZATION** - Current works, could be better

---

## ✅ What Works

1. **Tier Classification** - Correctly identifies compete tier
2. **Plan Duration** - Correctly calculates 21 weeks
3. **Exercise Exclusions** - Correctly excludes jumping exercises
4. **Key Days** - Correctly identifies available key days
5. **Plan Generation** - Successfully generates 42 strength workouts
6. **Guide Generation** - Creates personalized guide
7. **Calendar Generation** - Creates calendar (uses default template)

---

## 📋 Review Your Plan

### Check These Files:

1. **Profile**: `athletes/matti-rowe/profile.yaml`
   - Review your inputs - are they accurate?

2. **Derived Values**: `athletes/matti-rowe/derived.yaml`
   - Tier: compete ✅
   - Strength days: saturday, sunday ⚠️ Review
   - Exclusions: Jump Squat, Box Jump ✅

3. **Weekly Structure**: `athletes/matti-rowe/weekly_structure.yaml`
   - Does this match your actual schedule?

4. **Calendar**: `athletes/matti-rowe/plans/2025-unbound_gravel_200/calendar/training_calendar.md`
   - Review day-by-day schedule
   - Note: Currently shows default template (not custom structure)

5. **Guide**: `athletes/matti-rowe/plans/2025-unbound_gravel_200/guide.md`
   - Review personalized guide
   - Check exercise modifications section

6. **Workouts**: `athletes/matti-rowe/plans/2025-unbound_gravel_200/workouts/`
   - Review a few ZWO files
   - Check if excluded exercises are actually excluded

---

## 🎯 Key Questions for You

1. **Strength Days**: Saturday + Sunday works for you, or prefer Wednesday + Sunday?

2. **Weekly Structure**: Does the custom structure match your reality?
   - Monday intervals AM ✅
   - Tuesday intervals PM ✅
   - Saturday long ride ✅
   - Does this work?

3. **Exercise Exclusions**: Are Jump Squat and Box Jump the only exclusions needed?

4. **Tier**: Does compete tier feel right for 12 hours/week?

---

**Next Steps**: Review the files above and provide feedback on what needs adjustment.

