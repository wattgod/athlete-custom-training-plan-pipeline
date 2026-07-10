# Improvement backlog — 2026-07-10

**Quality 5.88** · avg coach 7.43/10 · contract pass 75% · load 5.12/plan · 1 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×1  (gravel/veteran_podium_chaser)
> Athlete weight is stated as '121 lbs (54.9 kg)' in the profile, but the Recovery Protocol uses '55kg body weight' to calculate post-ride protein/carb targets (22 g protein, 55-66 g carbs). The weight figure itself may be fabricated — no weight field exists in the provided athlete JSON (which lists only sex, age, ftp, hours_target). Presenting a specific weight the athlete never provided is a data-integrity error that will erode trust the moment the athlete reads it.

### 2. [major] ×2  (gravel/time_crunched_parent, gravel/veteran_podium_chaser)
> Long ride peak duration is stated as '2.7–4.5 hours.' For a 92-mile A-priority gravel race with a podium goal, the upper end of the long ride window appears low — a 92-mile gravel event at competitive pace will likely take this athlete 5.5–7+ hours. Even accounting for time-crunched constraints, the guide should acknowledge the gap between peak long-ride duration and expected race duration, and explain the mitigation strategy (e.g. back-to-back days, race-day fueling rehearsal). Without that explanation, the numbers look like an error.

### 3. [major] ×1  (road/time_crunched_parent)
> Zone 2 power range is wrong: the chart lists Zone 2 as 100–135 W with '56–75% FTP' at FTP=180 W. But 56% of 180 W = 100.8 W and 75% of 180 W = 135 W, so the watts ARE internally consistent — however, the Zone 2 LTHR label reads '69–83% LTHR' and the zone is described as the 'bulk of your riding,' yet the standard Coggan/Time-Crunched upper boundary for Z2 is 75% FTP (135 W). The deeper problem: Zone 1 is listed as '0–99 W' and Zone 2 starts at 100 W, leaving a 1-watt gap at 99–100 W that is cosmetically fine, but the %FTP column for Zone 1 is blank — it should read '<56% FTP' for completeness and athlete clarity. As written it looks like an omission/error in the table.

### 4. [major] ×1  (road/time_crunched_parent)
> Fueling section in the guide body has not yet appeared in the truncated text, but the plan JSON specifies 70 g carbs/hour for a 4.3-hour estimated finish. The recovery protocol visible in the text recommends '69–83 g carbs within 30 minutes post-ride' — that range happens to overlap with the per-hour race fueling figure, which could confuse an athlete reading both sections. The two contexts (post-ride recovery window vs. on-bike race fueling) must be clearly labeled so the athlete doesn't conflate them.

### 5. [major] ×1  (gravel/masters_returner)
> Zone Distribution check FAILED (per preview_checks). The zone chart is present but the power ranges for Zone 1 (listed as '0-103W' with no % FTP shown) and Zone 2 (104-141W, 56-75% FTP) appear to cover only 55 watts of Zone 2, while the GS 'G Spot' zone (164-174W) is an unlabeled extra zone inserted between Tempo and Threshold. The automated gate already flagged this — the zone distribution as written does not cleanly parse to a standard 6-zone model aligned with the stated FTP of 188W. This must be reconciled before sending.

### 6. [major] ×1  (gravel/masters_returner)
> Plan duration vs. weeks_until_race mismatch not explained to the athlete. The plan is 9 weeks but the race is 10 weeks away (plan_note explains this is intentional — the athlete starts one week later), yet nowhere in the guide does it tell the athlete when to actually start (i.e., 'begin this plan on 2026-07-20, one week from today'). Without that explicit start-date instruction, the athlete may start immediately, misalign the taper, and arrive at race day having completed only 8 of 9 weeks.

### 7. [minor] ×2  (gravel/masters_returner, gravel/veteran_podium_chaser)
> The long-ride duration range cited in the Weekly Structure section ('1.5-2.5 hours') is quite short for a 55-mile gravel race estimated at ~4.6 hours. The plan does flag this as 'Your Biggest Opportunity' and encourages 3-4 hour rides, but the baseline stated range of 1.5-2.5 h risks anchoring the athlete too low, particularly given the Time-Crunched 6 h/week constraint.

### 8. [major] ×1  (gravel/veteran_podium_chaser)
> The guide states '10 Years Riding' at 'Intermediate level' in the same breath. A rider with 10 years of experience chasing a podium at an A-priority race should be labelled 'Advanced' or 'Experienced'; calling a 10-year veteran 'Intermediate' is inconsistent with the persona label 'Experienced racer chasing a podium' and could feel dismissive or inaccurate to the athlete.

### 9. [major] ×1  (gravel/time_crunched_parent)
> The guide includes a 'Road Skills' section in the table of contents. This is a gravel-discipline plan — gravel-specific skills (loose surface cornering, technical descending, singletrack confidence, bike handling on mixed terrain) should be covered instead. A road skills section is wrong-discipline content that would confuse or mislead this athlete.

### 10. [major] ×1  (gravel/veteran_podium_chaser)
> The guide states '13 years of cycling experience at Intermediate level' — a rider with 13 years of experience should not be labeled Intermediate; this is almost certainly a template fill error and will read as insulting or careless to a veteran podium-chasing athlete.

### 11. [major] ×1  (gravel/veteran_podium_chaser)
> The TSS Progression check returned WARN in the preview checks, yet there is no acknowledgment, explanation, or mitigation of this in the guide. A TSS progression warning in an 8-week plan targeting a 125-mile A-race is a meaningful flag that should either be resolved or noted for the coach to manually verify.

### 12. [major] ×1  (road/veteran_podium_chaser)
> Experience level mislabeled: the guide text calls this athlete 'Intermediate level' ('9 years of cycling experience at Intermediate level') but the persona is 'veteran_podium_chaser — Experienced racer chasing a podium.' Nine years plus a podium goal is unambiguously experienced/advanced. Calling a podium-chasing veteran with 9 years' riding 'Intermediate' is factually wrong and potentially insulting to a paying customer.

### 13. [minor] ×1  (road/time_crunched_parent)
> The countdown banner reads '72 days from today' — this is a dynamically computed field that should resolve to a specific generation date. If the plan is generated and emailed on a different day than assumed, this number will be stale or wrong. It would be safer to display the static generation date rather than a live countdown that may mismatch delivery.

### 14. [minor] ×1  (road/time_crunched_parent)
> '7 Years Riding' appears in the athlete profile card, but the source JSON contains no years-riding field — this value appears to have been inferred or fabricated by the generator. If it came from the questionnaire it is fine, but if it was assumed it should be flagged as unverified athlete data shown to the customer.

### 15. [minor] ×1  (gravel/time_crunched_parent)
> The fueling section references 90 g/h carbs over a 4.2 h duration (from plan facts), but the truncated guide text does not surface this number in the visible Nutrition Strategy content. Consistency between the guide text and the plan facts should be confirmed in the full document — if the guide states a different duration or carb target it will contradict the athlete's data.

### 16. [minor] ×1  (gravel/time_crunched_parent)
> 'Women-Specific Considerations' and 'Masters Training Considerations' both appear as separate table-of-contents sections. These are legitimate and good to include for a 44-year-old female athlete, but the truncated text does not show their content — QA should confirm these sections contain substantive, relevant guidance rather than generic placeholder text before sending.

### 17. [minor] ×1  (gravel/veteran_podium_chaser)
> The guide references a 'home gym' for strength training in the 'Your Week at a Glance' section, but no questionnaire field in the plan facts confirms the athlete has a home gym — this appears to be a default or hallucinated detail that could be wrong.

### 18. [minor] ×1  (road/veteran_podium_chaser)
> Zone 1 power range is missing from the zone chart. The table shows Zone 1 as '0–189W' but omits the %FTP column entry (should be roughly ≤55% FTP) and the %LTHR entry, leaving two cells blank while all other zones are fully populated. Looks like a rendering gap and is inconsistent.

### 19. [minor] ×1  (road/veteran_podium_chaser)
> Zone Distribution flagged WARN by the automated preview check, but the guide text makes no mention of any caveat or adjustment to account for this. For a veteran racer the coach should at minimum acknowledge why the distribution was chosen or flag it — leaving a WARN unexplained is a quality gap even if not technically wrong.
