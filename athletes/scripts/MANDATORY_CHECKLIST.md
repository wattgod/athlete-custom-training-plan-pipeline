# MANDATORY CHECKLIST FOR AI ASSISTANTS

**READ THIS DOCUMENT AT THE START OF EVERY SESSION**

This checklist exists because of documented failures (Bugs #16-18 in lessons learned).
Following this checklist is not optional.

---

## BEFORE DOING ANY WORK

- [ ] I have read `ATHLETE_CUSTOM_TRAINING_PLAN_PIPELINE_LESSONS_LEARNED.md`
- [ ] I understand the ZWO format requirements (4-space indent, no nested textevent in SteadyState)
- [ ] I understand the methodology distribution targets (G SPOT = 45/30/25)
- [ ] I know the 5 quality gates that must be run

---

## QUALITY GATE ORDER (MANDATORY)

You MUST run these in order. Do not skip any step.

### Gate 1: Pre-Regeneration Check
```bash
cd athletes/scripts
python3 pre_regenerate_check.py {athlete_id}
```
**DO NOT PROCEED if this fails.**

### Gate 2: Package Generation
```bash
python3 generate_athlete_package.py {athlete_id}
```
Only run after Gate 1 passes.

### Gate 3: Distribution Validation
```bash
python3 validate_workout_distribution.py {athlete_id}
```
**DO NOT DELIVER if distribution is off by >5%.**

### Gate 4: Integrity Check
```bash
python3 test_athlete_integrity.py {athlete_id}
```
Review any warnings.

### Gate 5: Pre-Delivery Checklist
```bash
python3 pre_delivery_checklist.py {athlete_id}
```
**Review the generated checklist before delivery.**

---

## COMMON MISTAKES TO AVOID

1. **Declaring victory without verification**
   - Don't say "Package complete" until all 5 gates pass
   - Run the validation scripts, don't just assume they'll pass

2. **Trusting your output**
   - Always verify distribution with `validate_workout_distribution.py`
   - Check actual percentages, not just "workouts are appearing"

3. **Modifying code without running tests**
   - Run `python3 -m pytest test_*.py -v` BEFORE and AFTER changes
   - All 67+ tests must pass

4. **Skipping lessons learned**
   - Read the full document, especially the bug history
   - Each bug has a fix and a rule - follow them

5. **Regenerating without understanding**
   - If distribution is wrong, understand WHY before changing code
   - Don't just tweak and regenerate repeatedly

---

## IF SOMETHING GOES WRONG

1. **Stop and read the error message**
2. **Check lessons learned for similar bugs**
3. **Run the tests to isolate the issue**
4. **Understand the root cause before fixing**
5. **Document the fix in lessons learned**

---

## DELIVERY PACKAGE CONTENTS

Every delivery must include:

```
{athlete-id}-training-plan/
  training_guide.pdf      (brand-styled, no emojis)
  plan_justification.md   (internal documentation)
  workouts/
    W01_Mon_Feb16_*.zwo   (ALL workout files)
    ...
```

---

## SIGNATURES

Before proceeding, acknowledge:

- [ ] I have read this entire checklist
- [ ] I will run all 5 quality gates in order
- [ ] I will not deliver until all gates pass
- [ ] I will add any new bugs to lessons learned

---

**Remember: The process exists because we failed before. Follow it.**
