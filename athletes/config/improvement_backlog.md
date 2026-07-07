# Improvement backlog — 2026-07-07

**Quality 2.02** · avg coach 6.12/10 · contract pass 75% · load 11.5/plan · 7 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×1  (gravel/veteran_podium_chaser)
> Weekly Volume preview check is flagged FAIL. The guide describes a 15 h/week plan for an experienced racer, but the automated gate detected a volume problem. This must be resolved before sending — if prescribed weekly hours are actually under- or over-target, every TSS and phase progression number downstream is wrong.

### 2. [critical] ×1  (mtb/ambitious_first_timer)
> Section 12 is titled 'Road Skills' — this athlete is preparing for an MTB Gran Fondo, not a road race. Road skills content (e.g., road cornering, road group dynamics framing) is the wrong discipline. The section must be replaced with MTB-specific trail skills: technical descending, switchback cornering, loose-surface braking, body position on climbs, and off-road group etiquette.

### 3. [critical] ×1  (road/veteran_podium_chaser)
> Zone Distribution check is a confirmed FAIL in the preview checks. The guide does not surface or explain this failure anywhere in the visible text. If the actual weekly zone distribution in the calendar contradicts the ~65% easy volume claim made in the methodology section, the athlete will be training under a false premise. This must be resolved before sending — either fix the distribution or explicitly note the deviation.

### 4. [critical] ×1  (mtb/ambitious_first_timer)
> Discipline mismatch: Athlete is an MTB rider but the plan is titled and built around 'Flanders Legacy Gravel' and includes a 'Gravel Skills' section. The persona discipline field is 'mtb', yet no MTB-specific skills content (technical descending, switchbacks, rooty/rocky terrain, body position on technical trails) appears anywhere — instead the guide promotes gravel-specific skills that are wrong for the athlete's discipline.

### 5. [critical] ×1  (mtb/ambitious_first_timer)
> Race discipline contradiction: The plan metadata says discipline='mtb' but the race is 'Flanders Legacy Gravel' — a gravel event. Either the athlete's discipline profile is wrong (they are actually a gravel rider) or the race has been mismatched to the athlete. This ambiguity is never resolved in the guide, meaning either the skills content or the discipline label will be wrong. This must be audited before sending.

### 6. [critical] ×1  (mtb/weekend_warrior)
> Discipline mismatch: the athlete's discipline is MTB, yet the plan includes a dedicated 'Gravel Skills' section (listed in the table of contents) and the plan title/race branding leans heavily on 'Gravel Challenge' framing throughout. MTB and gravel are distinct disciplines with different skills content (e.g., MTB needs trail/singletrack skills, body position for technical terrain, etc.). A gravel-skills section sent to an MTB rider is wrong and unprofessional.

### 7. [critical] ×1  (mtb/weekend_warrior)
> Race name vs. discipline contradiction: 'Montana Gravel Challenge' is the verified race name, but the athlete's registered discipline is MTB. The guide never acknowledges or reconciles this. If the race is genuinely a gravel event, the discipline field is wrong and the entire MTB framing is incorrect. If the athlete is doing the MTB version of the event, the race name and skills content need to reflect that. Either way, this contradiction must be resolved before sending.

### 8. [major] ×1  (gravel/veteran_podium_chaser)
> Experience level contradiction: the guide simultaneously says '11 Years Riding' and describes the athlete as 'Intermediate level' ('15 hours/week matches the Traditional (Pyramidal) approach — 11 years of cycling experience at Intermediate level'). An 11-year rider is not Intermediate by any standard coaching taxonomy. This will undermine athlete trust and reads as a copy-paste error from a lower-tier persona template.

### 9. [major] ×1  (gravel/masters_returner)
> Off days listed as 'Friday, Wednesday, Sunday' — that is THREE off days in a 7-day week, leaving only 4 training days. The guide itself states 'Your week has 4 training days, 3 of which are key sessions,' which is internally consistent, but 3 off days is unusually high for a 6h/week athlete and may be a template error. More critically, listing Sunday as an off day conflicts with 'Long rides: Saturday' — a single long ride day on Saturday with Sunday off is fine, but the off-day list should be verified against the actual calendar to ensure it was not auto-generated incorrectly (e.g. two consecutive off days mid-week killing interval spacing).

### 10. [major] ×1  (gravel/masters_returner)
> Athlete height is listed as 5'6" in the guide, but this field was not present in the plan JSON provided for QA — it appears to be a placeholder or fabricated value pulled from a default template rather than the athlete's actual questionnaire response. Sending a guide with a wrong height to a paying customer is embarrassing and undermines trust in the personalization claim.

### 11. [major] ×1  (road/weekend_warrior)
> Off-day list contradicts weekly structure: the guide states 'Off days: Saturday, Thursday, Tuesday' — that is THREE off days — but later claims 'Your week has 4 training days, 4 of which are key sessions.' Four training days with three off days leaves only one unaccounted day (Sunday), yet four sessions cannot fit into four days if three of those days are off. The numbers don't add up and will confuse the athlete immediately.

### 12. [major] ×1  (road/weekend_warrior)
> Weekly training days vs. key sessions claim is internally contradictory: stating '4 training days, 4 of which are key sessions' implies every training day is a key session with zero easy or recovery rides — which directly contradicts the Time-Crunched methodology described (long ride + intervals + easy rides + strength). At least one day should be an easy/recovery ride, not a key session.

### 13. [major] ×1  (mtb/ambitious_first_timer)
> The guide states '2 Years Riding' and simultaneously calls the athlete 'Intermediate level' in the methodology rationale. The persona is explicitly 'ambitious_first_timer,' which the guide's own opening correctly labels. Calling a first-timer with 2 years riding 'Intermediate' in one breath contradicts the persona framing and could set unrealistic expectations or incorrect training guardrails.

### 14. [major] ×1  (mtb/ambitious_first_timer)
> The long-ride duration range cited in the Weekly Structure section ('3.5–5.9 hours') does not reconcile cleanly with the fueling section's stated race duration of 4.9 hours and a 78.3-mile MTB course. A peak long ride exceeding race duration (5.9 h) may be intentional for an MTB event with technical terrain, but there is no explanation for why the upper bound exceeds the expected race time — this will confuse the athlete and needs a one-sentence rationale or the ceiling should be capped at ~5 h.

### 15. [major] ×1  (gravel/ambitious_first_timer)
> Experience level is mislabeled. The JSON persona is 'ambitious_first_timer' and the athlete has 1 year of riding experience, but the guide text states 'Intermediate level' in the methodology selection rationale ('1 years of cycling experience at Intermediate level'). A first-timer reading this will be confused or misled about how the plan was calibrated.

### 16. [major] ×1  (gravel/ambitious_first_timer)
> Race fueling duration mismatch. The fueling section in the JSON specifies a 6.3 h race duration, which should anchor the nutrition strategy section. The guide references 70 g/h carbs correctly, but the truncated nutrition text does not surface the 6.3 h total (or ~441 g total carbs) context. More critically, the post-ride recovery window references a generic '76g body weight' carb number but never connects it to the specific 6+ hour gravel race fueling demands that distinguish this event. This creates a material gap for an athlete whose primary fueling challenge is an all-day gravel effort, not a standard training ride.

### 17. [major] ×1  (road/veteran_podium_chaser)
> Zone 1 row in the zone chart is missing its FTP% and LTHR% columns (they are blank in the rendered text). Every other zone has these values. An athlete referencing this chart mid-plan will have an incomplete reference for their most-used recovery zone. Sloppy and inconsistent.

### 18. [major] ×1  (road/veteran_podium_chaser)
> Long ride duration ceiling stated as '4–6.8 hours' in the Weekly Structure section. At 10 hours/week total, a single 6.8-hour ride would consume 68% of the weekly budget, leaving only 3.2 hours for all other sessions. This upper bound is implausibly high and likely a template bleed-in from a higher-volume plan. It needs to be capped at a figure consistent with a 10h/week athlete.

### 19. [major] ×1  (mtb/ambitious_first_timer)
> Off-day / long-ride day structural incoherence: The guide states 'Off days: Saturday, Sunday — Long rides: Monday.' For a 7h/week amateur athlete, placing the long ride on Monday (the day after two consecutive rest days) and taking both weekend days off is highly atypical and will likely conflict with a normal working schedule. More importantly, this means the athlete does their biggest ride of the week at the start of the working week — a pattern that is rarely practical and is never explained or justified in the guide.

### 20. [major] ×1  (mtb/ambitious_first_timer)
> Zone Distribution flagged WARN by automated checks but the guide contains no acknowledgment or explanation of the zone distribution warning. A paying athlete seeing a 'WARN' flag (if exposed) or a coach reviewing the plan needs to understand why it was flagged and whether corrective action was taken.

### 21. [major] ×1  (mtb/ambitious_first_timer)
> Fueling section references a 6.2-hour race duration for a 75-mile gravel event in Flanders (a notoriously hilly region), and prescribes 70g carbs/hour — but the guide text visible here does not clearly communicate total carbohydrate targets or the race-day execution strategy in enough detail for a first-timer chasing a finish goal. The fueling plan needs to be made explicit in the Nutrition Strategy section.

### 22. [major] ×1  (mtb/weekend_warrior)
> Weight field shows '121 lbs / 54.9 kg' in the athlete profile, but the recovery protocol section references '55kg body weight' for protein/carb calculations — that is consistent — however, the source JSON does not include a weight field at all. The plan has fabricated a weight (121 lbs / 5'8") that was never provided by the athlete. Displaying invented biometric data to a paying customer is a trust-destroying error.

### 23. [major] ×1  (mtb/weekend_warrior)
> Height field ('5'8"') is also not present in the athlete JSON. Like weight, this has been hallucinated into the Your Profile block. Sending fabricated personal data is unacceptable.

### 24. [major] ×1  (mtb/weekend_warrior)
> plan_weeks (11) does not equal weeks_until_race (12), meaning the plan starts one week after today. The guide nowhere informs the athlete of this — it simply says '86 days from today' for the race date without explaining that training doesn't begin immediately. A confused athlete may think week 1 starts the day they receive this email.

### 25. [minor] ×1  (gravel/veteran_podium_chaser)
> Long ride duration range stated as '4.3–7.1 hours' in the Weekly Structure section. The upper bound (7.1 h) seems high relative to the race estimate of ~4.4 h and the Per-Day Duration Cap check passing — the guide should clarify whether 7.1 h refers to a peak long ride or is a data error, as it may confuse the athlete about what to actually execute.
