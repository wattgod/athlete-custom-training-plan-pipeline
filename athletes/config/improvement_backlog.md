# Improvement backlog — 2026-08-22

**Quality 0.36** · avg coach 5.86/10 · contract pass 50% · load 13.75/plan · 10 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×1  (gravel/masters_returner)
> Wrong discipline content — sections titled 'Road Race Strategy' and 'Category 5 to Category 1 Pathway' appear in the table of contents of a GRAVEL plan. Cat 5–1 is a USA Cycling road racing classification system entirely irrelevant to a gravel finisher event. This is embarrassing and undermines credibility.

### 2. [critical] ×1  (gravel/masters_returner)
> Weight contradiction — the athlete's JSON contains no weight field, yet the plan states '176 lbs / 79.8 kg' as if it were sourced from the questionnaire. This is a fabricated or hallucinated data point that directly contradicts the athlete's profile and must not appear in a paid plan.

### 3. [critical] ×1  (gravel/weekend_warrior)
> Per-Day Duration Cap check is a known FAIL in the preview data, yet the guide was passed to QA without resolution. At least one day in the calendar exceeds the prescribed per-day duration limit for a 5 h/week athlete — this must be identified and corrected before sending.

### 4. [critical] ×1  (gravel/weekend_warrior)
> The guide states the long ride peak is '1.5 hours' but the athlete's projected race duration is ~2.7 hours (derived from the fueling data). A plan that never takes the athlete beyond 1.5 hours will leave them significantly underprepared for race-day durability — this is the single most important long-ride target to get right.

### 5. [critical] ×1  (road/veteran_podium_chaser)
> Weekly Volume check FAILED in the automated preview and the plan text never addresses or corrects it. The guide claims '15 hours/week' but if the flagged sessions don't add up to that target the athlete is getting a broken schedule. This must be resolved before sending — either the calendar hours are wrong or the stated target is wrong.

### 6. [critical] ×1  (road/veteran_podium_chaser)
> 'Category 5 to Category 1 Pathway' section heading appears in the table of contents. This is a beginner-racer progression section that has no place in a plan for an experienced 18-year veteran chasing a podium. It is both irrelevant and condescending to this athlete.

### 7. [critical] ×1  (gravel/time_crunched_parent)
> Road-racing content included for a gravel athlete: the guide contains a 'Road Race Strategy' section and a 'Category 5 to Category 1 Pathway' section. Neither applies to a gravel Gran Fondo. This is the wrong discipline's content and is embarrassing if a paying gravel athlete reads it.

### 8. [critical] ×1  (road/veteran_podium_chaser)
> The automated preview flagged 'Weekly Volume: FAIL' and this is never reconciled in the guide. The long-ride duration range quoted in the text ('2.3–3.8 hours') must be verified against the actual calendar sessions; if volume is out of spec for a 15 h/week athlete, the plan cannot be sent.

### 9. [critical] ×1  (road/veteran_podium_chaser)
> 'Category 5 to Category 1 Pathway' appears as a named section in the table of contents. This content is completely inappropriate for a veteran podium chaser — it belongs in a beginner/categorical-upgrade plan, not one targeting a podium at an A-race. Sending this to an experienced racer is embarrassing and undermines credibility.

### 10. [critical] ×1  (gravel/ambitious_first_timer)
> Table of Contents and guide body include 'Road Race Strategy' and 'Category 5 to Category 1 Pathway' sections. This athlete is doing a gravel gran fondo with a goal of finishing — road race tactics and a Cat 5–1 upgrade pathway are completely wrong-discipline content that will confuse and embarrass.

### 11. [major] ×2  (gravel/masters_returner, road/veteran_podium_chaser)
> 'Road Skills' section in the table of contents is listed generically; given the gravel discipline this should be gravel-specific skills (loose surface cornering, terrain reading, bike handling on mixed surfaces). If the body text contains road-specific cornering or criterium tactics, it is wrong for this athlete.

### 12. [major] ×1  (road/time_crunched_parent)
> Table of contents includes a 'Category 5 to Category 1 Pathway' section. This is a USA Cycling road racing license progression concept — it is completely irrelevant and potentially confusing for a gran fondo participant. Gran fondos are not licensed race categories. This content should not be in this plan and looks like a copy-paste error from a road crit/RR template.

### 13. [major] ×1  (gravel/masters_returner)
> FTP Test Frequency check flagged WARN in preview but the guide never explicitly addresses or explains this warning to the reader — a 9-week plan with a masters returner and no baseline FTP deserves a clear statement of when/whether a second test occurs, not silence.

### 14. [major] ×1  (gravel/weekend_warrior)
> The 'Biggest Opportunity' callout recommends 'a single 3–4 hour ride' for an athlete with only 5 hours per week total. A 3–4 hour ride would consume 60–80% of the entire weekly budget and violates both the Time-Crunched methodology and the athlete's stated availability. This recommendation is internally contradictory and could cause real harm.

### 15. [major] ×1  (gravel/weekend_warrior)
> The guide lists '5 Years Riding' as the athlete's experience under 'Your Profile,' but the source JSON contains no years-riding field. This appears to be a hallucinated or default-filled value that was never provided by the athlete and could be wrong.

### 16. [major] ×1  (gravel/weekend_warrior)
> The weekly structure section states 'Your plan places them on specific days — follow the calendar' and 'Your week has 5 training days,' but the athlete's hours target is 5 h/week — at Time-Crunched volumes, 5 training days is plausible only with very short sessions. This needs to be verified against the actual calendar days and durations to confirm it doesn't conflict with the Per-Day Duration Cap failure.

### 17. [major] ×1  (road/veteran_podium_chaser)
> The plan describes the athlete as 'Intermediate level' in the methodology justification ('18 years of cycling experience at Intermediate level'). An 18-year racer targeting a podium is not an intermediate — this contradicts the persona ('veteran_podium_chaser') and will erode the athlete's trust in the plan's calibration.

### 18. [major] ×1  (road/veteran_podium_chaser)
> Zone Distribution check returned WARN and is never acknowledged or explained in the guide. For a polarized plan the zone split is the entire methodological premise — a warning here needs either a correction in the calendar or a transparent note to the athlete.

### 19. [major] ×1  (road/veteran_podium_chaser)
> FTP Test Frequency returned WARN. A 9-week plan with an A-race podium goal needs a clear, deliberate FTP retest strategy. The guide mentions retesting in the zone chart but provides no specific week placement or rationale for frequency — this is especially important given the automated flag.

### 20. [major] ×1  (gravel/time_crunched_parent)
> Long-ride duration guidance (1.5–2.2 hours peak) is grossly insufficient for a 68-mile gravel event with an estimated ~4.6-hour finish time. Even acknowledging time constraints, telling the athlete their peak long ride is 2.2 hours — less than half race duration — without a stronger warning or mitigation strategy sets them up for a very hard day. The 'biggest opportunity' blurb is too soft; this needs to be a clear durability risk statement.

### 21. [major] ×1  (gravel/time_crunched_parent)
> 'Road Skills' section appears in the table of contents for a gravel racer — gravel-specific skills (loose surface cornering, descending on gravel, singletrack sections, hydration pack management) are absent or not evidenced in the truncated text, while road-specific skills framing persists.

### 22. [major] ×1  (road/veteran_podium_chaser)
> Taper intensity is flagged WARN by the automated gate and the guide text does not address or clarify the taper intensity prescription. A paying athlete targeting a podium needs explicit, correct taper guidance — a warn-level flag left unresolved is unacceptable for an A-race plan.

### 23. [major] ×1  (road/veteran_podium_chaser)
> The guide text truncates mid-sentence ('Cool r…'), strongly indicating the document delivered to the athlete is incomplete. The Recovery Protocol, Equipment Checklist, Nutrition Strategy, Mental Preparation, Race Week, Race Day, Road Skills, and Road Race Strategy sections are all either cut off or missing entirely.

### 24. [major] ×1  (gravel/ambitious_first_timer)
> Total race carbs stated as 366 g, but 62 g/hr × 5.908 h = ~366 g — the arithmetic is correct, yet the guide also lists a '5-hour' race duration implicitly in the pre-race meal section ('3-4 hours before start') without acknowledging the ~5.9 h estimated finish time. More importantly, the 366 g figure should be double-checked: at 83 miles on a gravel course with 8,100 ft of climbing, a 33-year-old first-timer is very likely to take longer than 5.9 h; if the duration estimate is too aggressive the carb total is dangerously low. The plan should either widen the estimate or flag the uncertainty explicitly.

### 25. [major] ×1  (gravel/ambitious_first_timer)
> TSS Progression check returned WARN and the guide text never addresses or acknowledges it. A coach must either confirm the progression is acceptable and note why, or fix the ramp rate before sending.
