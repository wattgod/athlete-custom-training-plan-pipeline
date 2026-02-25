# Coaching Brief: Nicholas Clift Shaw Applegate
*INTERNAL DOCUMENT — Coach eyes only*

## 1. Plan Overview
| Field | Value |
|-------|-------|
| Athlete ID | nicholas-applegate |
| Email | applen@gmail.com |
| Plan Duration | 12 weeks (2026-03-09 to 2026-05-31) |
| Methodology | Polarized (80/20) (score: 100/100, confidence: high) |
| Methodology ID | `polarized_80_20` |
| Tier | finisher |
| Starting Phase | base_1 |
| Target Race | Unbound Gravel 200 (2026-05-30) |
| Goal | finish |
| FTP | 315W (3.56 W/kg) at 88.5kg |
| Age | 44 |
| Sex | male |
| Cycling Hours | 10 hrs/week target |
| Current Hours | 5 hrs/week |
| Experience | 10yr cycling, 4yr structured |
| Recovery | slow |
| Stress | high |

## 2. Questionnaire -> Implementation Mapping
| # | Questionnaire Input | Pipeline Decision | Rationale |
|---|---------------------|-------------------|-----------|
| 1 | Weekly hours: 10 | Tier: finisher | Derived by derive_classifications.py from cycling_hours_target |
| 2 | FTP: 315W at 88.5kg | W/kg: 3.56 | Calculated: ftp_watts / weight_kg |
| 3 | Experience: 10yr cycling, 4yr structured | Methodology: Polarized (80/20) | select_methodology.py scored 13 options; experience contributes ±15 pts |
| 4 | Available hours: 10/wk | Methodology hours match: +30 if in sweet spot | Primary scoring factor (±30 pts). 10hr → Polarized (80/20) |
| 5 | Stress: high, Recovery: slow | Stress handling score: ±15 pts | High stress + slow recovery → favor stress-tolerant methodologies |
| 6 | Past failure: "Sweet Spot / Threshold" | VETO: -50 pts on matching methodologies | Hard exclusion — athlete explicitly rejected this approach |
| 7 | Race distance: 200 miles | Ultra-distance bonus: +15 pts for durability methodologies | 200mi event favors Polarized, MAF, HVLI for long-event durability |
| 8 | Goal: finish | Goal type scoring: ±10 pts | Finish goal → favor endurance/durability methodologies |
| 9 | Off days: Tuesday | No workouts on Tuesday | Respected exactly as stated by athlete |
| 10 | Long ride day: sunday | Sunday = long Z2 ride | Max duration: 600min |
| 11 | Key day candidates: Wednesday, Saturday, Sunday | Key days assigned: Wednesday, Saturday, Sunday | build_weekly_structure.py assigns intervals/long ride to key days |
| 12 | Wednesday available PM, key day OK | Wednesday PM = Intervals (120min max) | Key session - intervals PM |
| 13 | Saturday available AM, key day OK | Saturday AM = Intervals (240min max) | Key session - intervals or threshold |
| 14 | Monday available, not key day | Monday PM = Easy ride (120min max) | Fill day — active recovery / Z2 endurance |
| 15 | Thursday available, not key day | Thursday PM = Easy ride (120min max) | Fill day — active recovery / Z2 endurance |
| 16 | Friday available, not key day | Friday PM = Easy ride (120min max) | Fill day — active recovery / Z2 endurance |
| 17 | Sunday = preferred long ride day | Sunday AM = Long ride (600min max) | Most important workout in polarized plan |
| 18 | Strength training: no | 0 sessions/week | Ankle limitation restricts exercises |
| 19 | Medical: Mild hemophilia B | Risk flag: monitor recovery | Medications: Recombinant factor IX |
| 20 | Indoor tolerance: tolerate_it, max indoor: 120min | Weeknight trainer cap: 120min | Workout durations respect indoor tolerance limit |
| 21 | Coaching style: general_guidance | Guide includes workout rationale | Athlete wants to understand WHY behind each workout |
| 22 | B event: Boulder Roubaix (2026-04-11) | B-race overlay on race week: opener + RACE_DAY ZWO | Training race — 90-95% effort, no phase change |

## 3. Methodology Selection
### Selected: Polarized (80/20)
- **Score**: 100/100
- **Confidence**: high
- **Methodology ID**: `polarized_80_20`

**Why this methodology won:**
- Ideal hours match (10h in 10-15h sweet spot)
- Experience exceeds requirements
- Handles high life stress well
- Excellent for ultra-distance events
- Appropriate for finish-focused goal

**Alternatives considered:**
| Rank | Methodology | Score | Key Reason |
|------|-------------|-------|------------|
| 1 | MAF / Low-HR (LT1) | 100 | Ideal hours match (10h in 10-15h sweet spot) |
| 2 | Autoregulated (HRV-Based) | 95.0 | Ideal hours match (10h in 8-15h sweet spot) |
| 3 | GOAT (Gravel Optimized Adaptive Training) | 85.0 | Ideal hours match (10h in 10-18h sweet spot) |

### Zone Distribution Targets
| Zone | Target % |
|------|----------|
| Z1-Z2 (endurance) | 80% |
| Z3 (tempo/sweet spot) | 0% |
| Z4-Z5 (threshold/VO2max) | 20% |

### Key Workout Types
- Long Z2
- Vo2Max Intervals
- Threshold Repeats

- **Testing Frequency**: 4_6_weeks
- **Progression Style**: Increase Hard Work Maintain Ratio

## 4. Phase Structure
| Week | Dates | Phase | B-Race | Notes |
|------|-------|-------|--------|-------|
| W01 | Mar9-Mar15 | BASE |  |  |
| W02 | Mar16-Mar22 | BASE |  |  |
| W03 | Mar23-Mar29 | BASE |  |  |
| W04 | Mar30-Apr5 | BASE |  |  |
| W05 | Apr6-Apr12 | BASE | Boulder Roubaix (2026-04-11) | B-race day |
| W06 | Apr13-Apr19 | BUILD |  |  |
| W07 | Apr20-Apr26 | BUILD |  |  |
| W08 | Apr27-May3 | BUILD |  |  |
| W09 | May4-May10 | PEAK |  |  |
| W10 | May11-May17 | PEAK |  |  |
| W11 | May18-May24 | TAPER |  |  |
| W12 | May25-May31 | RACE |  | A-RACE WEEK |

## 5. Weekly Structure
| Day | Slot | Workout Type | Key Day | Max Duration |
|-----|------|--------------|---------|-------------|
| Monday | PM | Easy Ride | no | 120min |
| Tuesday | — | OFF | no | — |
| Wednesday | PM | Intervals | YES | 120min |
| Thursday | PM | Easy Ride | no | 120min |
| Friday | PM | Easy Ride | no | 120min |
| Saturday | AM | Intervals | YES | 240min |
| Sunday | AM | Long Ride | YES | 600min |

## 6. Fueling Plan
| Field | Value |
|-------|-------|
| Race Duration | 16.7 hrs |
| Total Calories | 15667 kcal |
| Calories/Hour | 938 kcal/hr |
| Carb Target | 66g/hr |
| Carb Range | 57-76g/hr |
| Total Carbs | 1111g |
| Hydration | 600ml/hr |
| Electrolytes | 500-1000mg sodium per hour depending on sweat rate |

### Gut Training Progression
| Phase | Weeks | Target (g/hr) | Guidance |
|-------|-------|---------------|----------|
| BASE | 1-6 | 40-50 | Practice fueling on ALL rides over 90 minutes. Start with familiar products. |
| BUILD | 7-14 | 50-70 | Gradually increase carb intake on long rides. Test race-day products. |
| PEAK | 15-18 | 60-80 | Simulate race fueling on long rides. Lock in your race-day products. |
| RACE | Race day | 70-90 | Stick to the plan. Nothing new on race day. |

## 7. B-Race Handling
### Boulder Roubaix (2026-04-11)
- **Priority**: B (training race)
- **Overlay**: Replaces existing workout on race day with RACE_DAY ZWO
- **Day before**: Openers (40min cap, 4x30sec @ 120% FTP)
- **Week**: W05 (base phase)
- **Post-race**: Resume normal training within 2 days

## 8. Risk Factors
- High Stress
- Medical: Mild hemophilia B (meds: Recombinant factor IX)
- Chronic left ankle — Chronic injury in left ankle that limits range of motion - can be an issue with weight lifting
- High work stress (50hr weeks)
- Family commitments: Married, 1 kid

## 9. Key Coaching Notes
- Athlete explicitly wants BASE BUILDING, not sweet spot
- Previous failure: dedicated sweet spot block — lacked durability
- Willing to do up to 120min trainer sessions on weeknights
- Specifically asked for long Z2 rides — validates Polarized selection
- Durability is primary concern — key metric for plan success
- Wants to dial in nutrition alongside training
- Previous coaching experience: I like flexibility / adaptability. I like to understand how what I'm doing will affect my goals / pl
- Past quit reasons: Work time requirements
- Best training block: Consistent & put in the time, early season stage races

## 10. Pipeline Output Files
| File | Status |
|------|--------|
| profile.yaml | OK |
| derived.yaml | OK |
| weekly_structure.yaml | OK |
| methodology.yaml | OK |
| fueling.yaml | OK |
| plan_dates.yaml | OK |
| coaching_brief.md | OK |
| training_guide.html | OK |
| training_guide.pdf | MISSING |
| dashboard.html | OK |
| workouts/*.zwo | 72 files |

---
*Generated by intake_to_plan.py on 2026-02-24 15:14*
