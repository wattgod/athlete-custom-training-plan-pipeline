# Improvement backlog — 2026-09-15

**Quality 0.29** · avg coach 5.88/10 · contract pass 88% · load 15.88/plan · 13 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×2  (gravel/veteran_podium_chaser, road/time_crunched_parent)
> Three automated preview checks flagged WARN (TSS Progression, FTP Test Frequency, Taper Intensity) and none are addressed or explained in the guide text. A paying athlete should not receive a plan where the coaching system itself has unresolved warnings — either fix the underlying schedule issue or add a coach note explaining the intentional deviation.

### 2. [critical] ×2  (road/time_crunched_parent, road/weekend_warrior)
> 'Category 5 to Category 1 Pathway' section appears in the table of contents and presumably in the guide body. This is a road racing license-progression framework that has zero relevance to a weekend warrior whose only goal is to finish a gran fondo. It belongs in a competitive racer plan, not here — it's confusing, potentially misleading, and signals a template bleed-in from a different plan type.

### 3. [critical] ×1  (gravel/veteran_podium_chaser)
> Table of contents and body include a 'Road Race Strategy' section and a 'Category 5 to Category 1 Pathway' section. This athlete is doing a UCI Gran Fondo (gravel), not a road criterium or road stage race. These sections are wrong-discipline content that would actively mislead the athlete and embarrass the business.

### 4. [critical] ×1  (gravel/veteran_podium_chaser)
> Experience description reads '17 Years Riding' in the profile card but the methodology rationale then says 'Intermediate level.' A 17-year veteran targeting a podium is not Intermediate. These two statements contradict each other and will erode the athlete's confidence in the plan's personalisation.

### 5. [critical] ×1  (gravel/time_crunched_parent)
> Wrong discipline section included: 'Road Race Strategy' and 'Category 5 to Category 1 Pathway' are road-racing content that has no place in a gravel event plan. L'Étape Ciudad de México is a mass-participation gravel/gran fondo — there are no USA Cycling cat upgrades and no road-race tactical framing. This is the most embarrassing wrong-discipline content in the guide.

### 6. [critical] ×1  (gravel/time_crunched_parent)
> FTP zone table is missing power values for Zones 1 and 2: Zone 1 shows '0-129W' but no %FTP column entry, and Zone 2 shows '130-176W' with '56-75% FTP' but the %FTP cell for Zone 1 is blank in the rendered text. Minor in isolation, but athletes will use this table daily — gaps create confusion and undermine trust.

### 7. [critical] ×1  (gravel/ambitious_first_timer)
> Section titled 'Road Race Strategy' and a 'Category 5 to Category 1 Pathway' appear in the table of contents (and presumably in the full guide). This is a GRAVEL event — road race tactics and a Cat upgrade pathway are entirely wrong-discipline content that would confuse and embarrass the business.

### 8. [critical] ×1  (gravel/ambitious_first_timer)
> Section 'Road Skills' listed in the table of contents is also road-racing framing. For Gran Fondo Eilat on gravel, this section should cover gravel-specific skills (loose surface cornering, technical descents, tyre pressure management, pacing on mixed terrain) — not road race skill sets.

### 9. [critical] ×1  (road/weekend_warrior)
> Zone table is missing the power ranges for Zones 1 and 2 — the '%FTP' and '%LTHR' columns are blank for those rows in the excerpt. With FTP=240W the athlete needs concrete watt targets for the easy riding that makes up ~70% of this plan. Blank cells in the most-referenced table in the guide is a significant coaching credibility failure.

### 10. [critical] ×1  (road/masters_returner)
> "Category 5 to Category 1 Pathway" section is listed in the table of contents and presumably present in the full document. This is a USA Cycling road racing licensing concept that is entirely irrelevant — and potentially confusing/embarrassing — for a masters athlete entering a Gran Fondo (L'Étape) with a goal of finishing. It signals the plan was not properly filtered for event type and athlete profile.

### 11. [critical] ×1  (road/veteran_podium_chaser)
> The guide includes a 'Category 5 to Category 1 Pathway' section (visible in the table of contents). This athlete is a 44-year-old veteran podium chaser with 10 years of experience targeting a Gran Fondo — not a USA Cycling cat racer working through upgrade points. This section is wrong-discipline content that will confuse or embarrass the athlete and undermine trust in the plan.

### 12. [critical] ×1  (gravel/veteran_podium_chaser)
> Weekly Volume check FAILED in preview. The guide targets 14h/week but the automated gate flagged this. With off days on Saturday AND Thursday, only 5 days remain (Sun, Mon, Tue, Wed, Fri). The long ride is Sunday. Five days must deliver 14h — that is plausible only if the long ride is 4–5h and remaining days average ~2.25h each, which is aggressive for a pyramidal plan. The actual per-day numbers in the calendar must be verified to ensure they sum to ~14h; if they don't, the volume figure quoted throughout the guide is wrong and will mislead the athlete.

### 13. [critical] ×1  (gravel/veteran_podium_chaser)
> Off-day contradiction: the 'At a Glance' section lists BOTH Saturday AND Thursday as off days, yet the athlete profile states 14h/week with 5 training days. Listing two weekend-adjacent rest days (Saturday off, Sunday long ride) means the athlete has no back-to-back training window at the weekend — unusual and never explained. If Saturday is truly an off day, the guide should justify why the long ride is isolated on Sunday with a rest day immediately before it rather than after, especially since pre-long-ride rest is unconventional and could confuse the athlete.

### 14. [major] ×2  (road/time_crunched_parent, road/weekend_warrior)
> 'Road Race Strategy' is listed as a table-of-contents section. A UCI Gran Fondo is a timed mass-participation event, not a criterium or road race with tactics, attacks, and positioning. Generic road race strategy content (wheels, surges, leadouts) would be irrelevant or actively misleading for this athlete's goal of 'finish strong.'

### 15. [minor] ×3  (gravel/veteran_podium_chaser, road/time_crunched_parent, road/veteran_podium_chaser)
> Long ride duration range is cited as '2.7–4.6 hours' in the Weekly Structure section. The race is estimated at ~4.0 hours (per fueling data). A 4.6-hour ceiling on long rides is acceptable but tight — the guide should explicitly confirm the peak long ride is race-duration-matched, not just incidentally close to it.

### 16. [major] ×1  (gravel/veteran_podium_chaser)
> The FTP test protocol states 'The test result sets ALL your training zones for the next 6 weeks' but this is an 8-week plan and FTP Test Frequency is already flagged WARN. The '6 weeks' figure is copy-paste boilerplate that is factually inconsistent with the plan length and may conflict with however many retests are actually scheduled.

### 17. [major] ×1  (gravel/time_crunched_parent)
> Race goal is listed as 'podium' but the plan narrative only ever says 'Compete' under 'Success looks like.' A podium goal for a 68-mile mass-participation L'Étape event with FTP 235W requires specific race-winning tactical and intensity guidance (e.g., covering moves, VO2 ceiling work) that is not reflected in the training brief. The plan should either address the goal honestly or flag that podium at this event requires further context.

### 18. [major] ×1  (gravel/time_crunched_parent)
> Three off days listed as 'Sunday, Thursday, Tuesday' — that is an unusual and athlete-specific combination that needs to be verified against the actual calendar. More importantly, listing three full off days in a 7 h/week plan leaves only four riding days, which is fine, but the guide simultaneously says '4 training days, 3 of which are key sessions' — confirm the calendar actually reflects this and that the text is not copy-pasted from a different persona template.

### 19. [major] ×1  (gravel/time_crunched_parent)
> TSS Progression and Weekly Volume both flagged WARN by the automated preview checks, and Taper Intensity is also WARN. None of these flags are acknowledged or explained anywhere in the guide text. A paying athlete who notices the taper feels flat or the volume jumps too fast has no explanation. At minimum the coach notes should address the known warnings.

### 20. [major] ×1  (gravel/ambitious_first_timer)
> Athlete profile states '1 Years Riding' yet the methodology rationale calls them 'Intermediate level.' A 1-year rider is a beginner by any standard coaching definition. This is an internal contradiction and could cause the athlete to undertrain or overtrain relative to the prescribed intensities.

### 21. [major] ×1  (gravel/ambitious_first_timer)
> TSS Progression and Taper Intensity both flagged WARN in the preview checks, yet the guide text contains no acknowledgment or coaching note about these flags. The taper intensity WARN is particularly risky for race readiness — a coach would normally address this explicitly.

### 22. [major] ×1  (road/weekend_warrior)
> Four preview checks flagged WARN (Zone Distribution, TSS Progression, FTP Test Frequency, Taper Intensity) and none are meaningfully addressed or explained in the guide text provided. A paying athlete receiving a plan with known automated warnings that the coach never acknowledged or resolved is a trust and liability issue.

### 23. [major] ×1  (road/weekend_warrior)
> FTP Test Frequency is flagged WARN yet the guide states 'the test result sets ALL your training zones for the next 6 weeks' — in an 8-week plan that framing is arithmetically odd and may indicate either too many or too few tests are scheduled. This should be reconciled explicitly.

### 24. [major] ×1  (road/masters_returner)
> Three pre-send checks flagged WARN (Weekly Volume, TSS Progression, Taper Intensity) but the guide text contains no acknowledgment, explanation, or coaching rationale for these deviations. A paying customer deserves to understand why their volume or taper differs from a standard prescription, not silence on known anomalies.

### 25. [major] ×1  (road/masters_returner)
> The long ride peak duration stated in the Weekly Structure section is "2.5–4.2 hours." The lower bound (2.5 h) is plausible but the upper bound of 4.2 h on a 7 h/week Time-Crunched plan for a masters athlete is extremely aggressive — it would consume ~60% of the weekly hour budget in a single ride and is inconsistent with the Time-Crunched methodology's premise of short, intensity-dense sessions.
