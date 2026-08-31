# Improvement backlog — 2026-08-31

**Quality -0.94** · avg coach 5.62/10 · contract pass 62% · load 17.0/plan · 14 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×2  (road/masters_returner)
> 'Category 5 to Category 1 Pathway' section appears in the table of contents and (implied) body of the guide. This athlete is a masters gran fondo finisher — she does not race in a USA Cycling category system, has no upgrade goal, and this section is actively misleading and embarrassing for a 'goal: finish' gran fondo customer.

### 2. [critical] ×1  (road/veteran_podium_chaser)
> Experience level mismatch: the guide body text labels the athlete 'Intermediate level' (Section 1, methodology rationale), but the persona is 'veteran podium chaser' with 7 years of riding. Calling a 7-year veteran chasing a podium 'Intermediate' is factually wrong and will immediately undermine trust with this paying customer.

### 3. [critical] ×1  (road/veteran_podium_chaser)
> 'Category 5 to Category 1 Pathway' section is listed in the table of contents and present in the guide. This content is entirely inappropriate for an experienced racer chasing a podium — it is beginner racing education. It signals the guide was not properly tailored and is potentially copied from a template for novice racers, which is embarrassing to send to this athlete.

### 4. [critical] ×1  (gravel/masters_returner)
> Wrong discipline content: the guide explicitly includes 'Road Race Strategy' and a 'Category 5 to Category 1 Pathway' section. This is a gravel event (GFNY Miami). Road race category progression (Cat 5–1) is USA Cycling road racing language and has zero relevance to a gravel finisher. This is the kind of content that destroys athlete trust immediately.

### 5. [critical] ×1  (gravel/masters_returner)
> Off-day count mismatch: the at-a-glance summary lists THREE off days (Friday, Thursday, Saturday) but the plan is built on 4 training days per week from an 8h/week target. Three off days in a 7-day week leaves only 4 training days, which is fine, but listing three named off days is internally inconsistent — standard week structure would have 3 off days only if one day is a double. More likely a template error where two separate off-day fields were concatenated, producing a nonsensical three-day list. Needs audit against the actual calendar.

### 6. [critical] ×1  (gravel/time_crunched_parent)
> 'Road Race Strategy' and 'Category 5 to Category 1 Pathway' sections appear in the table of contents. This athlete is a gravel racer — road racing categories (Cat 5–Cat 1) are a USA Cycling road construct that is irrelevant and confusing here. Sending this to a gravel athlete is embarrassing and suggests the wrong template was partially applied.

### 7. [critical] ×1  (gravel/time_crunched_parent)
> Athlete goal is stated as 'podium' in the race data but the guide downgrades it to 'Compete' under Goals & Blindspots with zero explanation. A paying customer targeting a podium finish at an A-priority race will notice this immediately and lose trust in the plan's personalization.

### 8. [critical] ×1  (road/masters_returner)
> Off-day listing says 'Off days: Saturday, Tuesday, Monday' — that is three off days, but the plan states 4 training days per week (7 days minus 3 off = 4 training days). Listing Monday as both an off day and implying a mid-week interval day creates a structural contradiction that will confuse the athlete about her actual weekly schedule.

### 9. [critical] ×1  (road/masters_returner)
> Athlete weight of 156 lbs / 70.7 kg / 5'6" is shown in 'Your Profile' but the athlete's data contains no weight or height fields — these numbers were fabricated or pulled from a default template. Presenting invented biometric data to a paying customer is a serious credibility failure.

### 10. [critical] ×1  (gravel/ambitious_first_timer)
> Wrong-discipline content included: the table of contents and guide body contain a 'Road Race Strategy' section and a 'Category 5 to Category 1 Pathway' section. This athlete is training for a gravel gran fondo with a goal of finishing — road racing category upgrades are completely irrelevant and will confuse or embarrass the business in front of a paying customer.

### 11. [critical] ×1  (gravel/ambitious_first_timer)
> Zone Distribution preview check explicitly FAILED. The plan was sent to QA with a known zone distribution problem — the actual weekly/workout zone splits do not conform to the stated 80/20 polarized methodology. This is a fundamental methodology integrity failure; the guide promises polarized training but the numbers do not deliver it.

### 12. [critical] ×1  (gravel/ambitious_first_timer)
> The guide contains a 'Road Race Strategy' section and a 'Category 5 to Category 1 Pathway' section. This is a GRAVEL event (GFNY Miami). Road race categories (Cat 5–Cat 1) are a USA Cycling road/criterium construct that is irrelevant and potentially confusing for a gravel racer. Sending this to a gravel athlete is embarrassing and undermines trust in the entire plan.

### 13. [critical] ×1  (gravel/ambitious_first_timer)
> 'Road Skills' section appears in the table of contents. Gravel-specific skills (loose surface cornering, technical descending, mud/sand handling, singletrack if applicable) are what this athlete needs — generic road skills content is mismatched to the discipline.

### 14. [critical] ×1  (road/veteran_podium_chaser)
> The guide contains a 'Category 5 to Category 1 Pathway' section. This athlete is a veteran podium chaser — a USA Cycling Cat system progression ladder is entirely irrelevant and condescending for this persona. It suggests boilerplate from a beginner template was accidentally included and will embarrass the business.

### 15. [major] ×1  (road/veteran_podium_chaser)
> Weekly Volume preview check is flagged FAIL and is unresolved in the guide. The guide makes no acknowledgment of any volume concern, caveat, or corrective guidance for the athlete. A coaching guide should either fix the underlying issue or transparently address why the prescribed volume is what it is — leaving a silent FAIL is a quality gap.

### 16. [major] ×1  (road/veteran_podium_chaser)
> TSS Progression is flagged WARN and Taper Intensity is flagged WARN, but neither is addressed or caveated anywhere in the truncated guide text. For a podium-goal athlete, both of these warrant at least a coach's note explaining the reasoning (e.g., deliberate conservative TSS ramp, or taper intensity justification).

### 17. [minor] ×2  (gravel/ambitious_first_timer, road/veteran_podium_chaser)
> The long ride duration range stated as '3.3–5.5 hours' in the Weekly Structure section should be cross-checked against the race's estimated finish time (~4.75h for this athlete). The upper bound of 5.5h is plausible for peak week, but the range is presented without context and may confuse an experienced athlete expecting more precision.

### 18. [major] ×1  (gravel/masters_returner)
> Weekly Volume flagged WARN and Zone Distribution flagged WARN by the automated preview — neither warning is resolved or acknowledged anywhere in the guide text. For an 8h/week masters athlete, unresolved volume and zone distribution anomalies could mean the athlete is being over- or under-loaded, which is the core of what this plan is supposed to get right.

### 19. [major] ×1  (gravel/masters_returner)
> FTP Test Frequency flagged WARN by automated preview with no explanation or mitigation in the guide. For a 9-week plan with no known FTP, testing cadence matters — the guide mentions only a Week 1 field test but gives no guidance on whether a mid-plan re-test is scheduled or intentionally omitted, leaving the athlete without a re-anchor if fitness changes significantly.

### 20. [major] ×1  (gravel/masters_returner)
> Weight shown as '157 lbs (71.2 kg)' in the athlete profile but no weight was provided in the plan JSON (the athlete object contains only sex, age, ftp, and hours_target). This number appears to have been fabricated or pulled from a default template. Displaying invented biometric data to a paying customer is a trust and accuracy failure.

### 21. [major] ×1  (gravel/time_crunched_parent)
> The fueling section (hourly_carbs 64 g, duration ~4.39 h) implies an estimated finish time of roughly 4 hours 23 minutes, but this number is never surfaced or explained in the visible guide text. The athlete needs to know the assumed finish time to validate fueling quantities and race-day pacing targets — omitting it leaves the nutrition strategy floating without an anchor.

### 22. [major] ×1  (gravel/time_crunched_parent)
> The plan_weeks (9) is shorter than weeks_until_race (10), meaning the athlete starts one week late. The guide never mentions this or tells the athlete when to begin. A confused start date could misalign the entire taper.

### 23. [major] ×1  (gravel/time_crunched_parent)
> FTP test frequency drew a WARN flag in automated checks, yet the guide text tells the athlete 'the test result sets ALL your training zones for the next 6 weeks' — implying a single test covers the whole plan. For a 9-week plan this may be fine, but the WARN is unresolved and the 6-week claim could contradict actual calendar placement of a retest; this needs to be consistent.

### 24. [major] ×1  (road/masters_returner)
> 'Road Race Strategy' section is listed in the table of contents. A gran fondo is not a road race; tactics like attacking, sitting in a peloton, or racing for position are irrelevant and potentially counterproductive for a finish-goal athlete. This content is for the wrong event type.

### 25. [major] ×1  (road/masters_returner)
> The guide states '14 Years Riding' under Your Profile, but the athlete data supplied does not include years riding — this figure appears fabricated or pulled from a template default. If wrong, it undermines trust in every other personalized number.
