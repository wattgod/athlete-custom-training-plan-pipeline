# Improvement backlog — 2026-08-03

**Quality 2.45** · avg coach 6.0/10 · contract pass 75% · load 10.12/plan · 6 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×1  (gravel/veteran_podium_chaser)
> Table of contents and body both include 'Road Race Strategy' and 'Category 5 to Category 1 Pathway' sections — this is a GRAVEL race plan. Road-race tactics and a Cat 5→Cat 1 upgrade pathway are wrong-discipline boilerplate that will confuse and embarrass in front of a podium-focused gravel racer targeting La Ruta.

### 2. [critical] ×1  (gravel/veteran_podium_chaser)
> Table of contents lists 'Road Skills' as a section. La Ruta de los Conquistadores is a multi-day gravel/mountain event famous for technical off-road terrain; road-skills content is irrelevant and signals the plan was not customized to the discipline.

### 3. [critical] ×1  (road/time_crunched_parent)
> Table of contents includes a 'Gravel Skills' section. This is a road-discipline plan for a road race (Bowral Classic). Gravel skills content has no place here and will immediately undermine the athlete's trust in the plan's personalisation.

### 4. [critical] ×1  (road/time_crunched_parent)
> Per-Day Duration Caps check is flagged FAIL in the preview but the plan was not corrected before QA. At least one workout in the calendar almost certainly exceeds the allowable per-session cap for a 5 h/week athlete — sending this risks prescribing an unachievable or injury-inducing session.

### 5. [critical] ×1  (road/time_crunched_parent)
> The athlete's stated goal is 'podium' but the plan silently substitutes 'Compete' under 'Your Goals & Blindspots.' For an A-priority race this is a significant mismatch: the training language, intensity distribution, and motivational framing should reflect a competitive/podium target, not a participation goal. If the system judged podium unrealistic it must say so explicitly, not quietly swap goals.

### 6. [critical] ×1  (road/veteran_podium_chaser)
> A 'Gravel Skills' section appears in the table of contents and presumably in the body of the guide. This athlete is a road racer targeting a road event (Cyclotour du Léman). Gravel cornering, technical gravel skills content has zero relevance and is actively embarrassing — a veteran racer will immediately lose confidence in the plan.

### 7. [major] ×2  (gravel/time_crunched_parent, gravel/veteran_podium_chaser)
> Long-ride duration range given in the Weekly Structure section is '4.6–7.8 hours.' For a 12 h/week athlete targeting a ~9-hour race, a long ride approaching 7.8 hours would consume 65% of the weekly budget in one session, leaving almost nothing for interval work — this figure needs verification against the actual calendar and likely reflects a template error.

### 8. [major] ×1  (gravel/veteran_podium_chaser)
> Fueling copy references '69 g/h' (from plan JSON) but the guide body never surfaces the per-hour target clearly — more importantly, for a 9-hour effort like La Ruta the hourly figure must be front-and-center with gut-training guidance. A podium-chaser at this event lives or dies by nutrition; the guide buries it.

### 9. [major] ×1  (gravel/veteran_podium_chaser)
> The guide calls the athlete 'Intermediate level' despite 7 years of riding, 310 W FTP, 12 h/week, and a podium goal at an elite gravel stage race. The persona is explicitly 'veteran_podium_chaser.' Labeling this athlete 'Intermediate' is inaccurate and condescending — a real coach would not write that.

### 10. [major] ×1  (gravel/masters_returner)
> Zone chart is missing power watt values for Zone 1 (Active Recovery) and Zone 2 (Endurance). Zone 1 shows '0-85W' but Zone 2 only shows '%FTP' and '%LTHR' columns with no watt range (the athlete's FTP is 155W, so Z2 = ~87–116W and should be listed). An athlete without a power meter reading in watts cannot self-calibrate. This is likely a rendering/template gap but it makes the zone chart incomplete and potentially confusing.

### 11. [major] ×1  (gravel/masters_returner)
> Sleep environment temperature is given as '65-68°F / 18-20°C'. The race is in Victoria, Australia — the entire athlete interaction is in an Australian context. Listing Fahrenheit first (an almost exclusively US convention) before Celsius reads as a template localisation failure and will undermine trust with this customer. For an Australian athlete, Celsius should appear alone or at minimum first.

### 12. [major] ×1  (road/time_crunched_parent)
> Long-ride peak duration is stated as 1.5–2.5 hours for a race estimated at 9.1 hours. While the Time-Crunched methodology inherently limits volume, stating a hard ceiling of 2.5 hours without any explanation of how race-day durability will be achieved beyond 'make more time' is insufficient. The guide should either raise the ceiling for this specific race distance or provide a more robust mitigation strategy (e.g., back-to-back days, once-monthly longer ride mandate).

### 13. [major] ×1  (road/time_crunched_parent)
> Long-ride duration is capped at 1.5 hours in the plan text, yet the race is 68.35 miles — likely 3–4 hours for this athlete at race pace. The 'YOUR BIGGEST OPPORTUNITY' callout acknowledges the gap but only vaguely suggests '1-3 longer rides per month.' For an A-priority podium goal, the structured plan itself should prescribe those longer rides; outsourcing it to athlete initiative is insufficient coaching.

### 14. [major] ×1  (road/time_crunched_parent)
> Zone Distribution check is WARN and is never addressed in the guide. A coach-authored document should either explain the intentional skew (e.g., elevated Zone 4/5 is expected in Time-Crunched methodology) or flag it for the athlete. Silence on a known warning is a quality gap.

### 15. [major] ×1  (road/time_crunched_parent)
> 'Category 5 to Category 1 Pathway' appears in the table of contents and presumably in the full plan. This athlete is a time-crunched parent targeting a gran fondo (L'Étape), not a USA Cycling road racer seeking upgrade points. Cat 5–1 content is completely wrong-discipline/wrong-context material and will confuse or mislead the athlete.

### 16. [major] ×1  (road/veteran_podium_chaser)
> The table of contents and apparent content includes a 'Category 5 to Category 1 Pathway' section. This is a USA Cycling licensing/upgrade pathway concept and is completely irrelevant to a Gran Fondo (GFNY Miami) — GFNDs have no upgrade categories. This content is either leftover boilerplate from a criterium/road race template or is misleading to the athlete and must be removed.

### 17. [major] ×1  (road/veteran_podium_chaser)
> The guide recommends '68g carbs/hour' in the fueling JSON but the recovery protocol specifies '84-101g carbs within 30 minutes post-ride' — while post-ride carb repletion and on-bike fueling are different things, the guide text never clarifies this distinction. An athlete reading both numbers in close proximity could conflate them, leading to significant under-fueling on the bike (68g/h) or over-interpreting the post-ride window figure. The guide should explicitly label these as separate protocols.

### 18. [major] ×1  (road/veteran_podium_chaser)
> The methodology blurb labels the athlete as 'Intermediate level' ('11 years of cycling experience at Intermediate level'). The persona is 'veteran_podium_chaser' — an experienced racer chasing a podium. Calling them Intermediate contradicts their profile and will offend a serious athlete.

### 19. [major] ×1  (road/veteran_podium_chaser)
> Fueling is set at 71 g carbs/hour for a 7-hour event. For a 355W FTP athlete racing 109 miles, current best-practice guidance for trained athletes with gut training is 90–120 g/hr. 71 g/hr is below even older 60–90 g/hr guidelines and is likely to result in a bonk in the final hours — directly undermining the podium goal.

### 20. [major] ×1  (road/veteran_podium_chaser)
> The Zone 1 row in the zone chart lists power as '0-195W' but omits a % FTP column entry, and Zone 6 similarly omits a % FTP lower bound (shows only '>427W / >120% FTP'). More critically, Zone 1's upper bound of 195W is 54.9% of 355W FTP, but the table header implies the % FTP column starts at Zone 2 (56%). The gap and missing cells will confuse a data-oriented athlete.

### 21. [major] ×1  (gravel/time_crunched_parent)
> Zone 1 and Zone 2 rows in the zone chart are missing their explicit power ranges in watts (Z1 shows '0-129W' but Z2 shows only '130-176W' with no % FTP figures filled in for Z1, and the % LTHR columns for Z1 and Z2 appear blank in the excerpt) — the table is inconsistently populated and a paying athlete will be confused about what power to target in Z1 and Z2.

### 22. [minor] ×1  (gravel/veteran_podium_chaser)
> The guide states the FTP test result 'sets your training zones for the next 6 weeks,' but the plan is only 11 weeks long and the JSON shows FTP tests are already gated by FTP Test Frequency check (PASS). Saying '6 weeks' feels like generic boilerplate copy-pasted rather than tailored to this specific 11-week plan.

### 23. [minor] ×1  (gravel/masters_returner)
> The FTP Test Frequency automated check returned WARN. The guide text states 'The test result sets ALL your training zones for the next 6 weeks' — in a 10-week plan this implies roughly one retest, which is reasonable, but the guide never explicitly tells the athlete when (which week) the retest occurs. A masters athlete with a known FTP should be told clearly when to retest so they can plan freshness accordingly.

### 24. [minor] ×1  (gravel/masters_returner)
> The plan start date is 2026-08-17, but the race is 2026-10-25 (12 weeks away) and the plan is only 10 weeks — the guide never explains the 2-week gap to the athlete. The JSON note clarifies this is intentional (athlete starts later), but the guide text should include a brief sentence telling the athlete to begin the calendar on August 17 and that two unstructured pre-base weeks precede it, otherwise the athlete may be confused about what to do in the interim.

### 25. [minor] ×1  (gravel/masters_returner)
> Long ride peak duration is cited as '3.3–5.5 hours' in the Weekly Structure section. For an 80-mile gravel event at an estimated ~7.4-hour finish time, a 5.5-hour ceiling long ride is reasonable but the lower bound of 3.3 hours early in the plan should be contextualised — without that framing a 59-year-old returning athlete may wonder why Week 1 long rides feel short relative to race distance.
