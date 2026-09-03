# Improvement backlog — 2026-09-03

**Quality 1.8** · avg coach 5.75/10 · contract pass 100% · load 12.38/plan · 11 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×1  (mtb/ambitious_first_timer)
> Discipline mismatch — the athlete is registered for an MTB Gran Fondo, but the table of contents and body text include 'Road Race Strategy' and a 'Category 5 to Category 1 Pathway' section. These are road-racing constructs (USA Cycling licensing categories) that are irrelevant and potentially confusing for an MTB rider. This content must be replaced with MTB-specific material (trail skills, singletrack cornering, body position, technical descending, etc.).

### 2. [critical] ×1  (mtb/ambitious_first_timer)
> Equipment checklist specifies 'road bike, in good working order' as the mandatory training bike. The athlete's event is an MTB race — the checklist must reference an MTB, appropriate tire widths, tubeless setup, dropper post considerations, and MTB-specific repair kit items (e.g., tire plugs, tubeless sealant).

### 3. [critical] ×1  (gravel/masters_returner)
> Race countdown is wrong: the guide states '63 days from today' but plan_start_date is 2026-09-07 and race date is 2026-11-05 — that is 59 days, not 63. If this number was generated on a different reference date it will be stale and misleading to the athlete, who may cross-check it. Either make it dynamic or remove the hard-coded countdown.

### 4. [critical] ×1  (gravel/masters_returner)
> 'Road Race Strategy' and 'Category 5 to Category 1 Pathway' sections appear in the table of contents and presumably in the full guide. This athlete is doing a gravel gran fondo, not a criterium or road race with USA Cycling categories. This content is completely wrong for the discipline and will confuse or embarrass the athlete.

### 5. [critical] ×1  (gravel/masters_returner)
> 'Road Skills' section is listed in the table of contents. While some road skills overlap with gravel, a dedicated road skills section (rather than gravel-specific skills: loose surface cornering, descending on gravel, river crossings, mechanical self-sufficiency) is the wrong content for a gravel racer and signals a copy-paste from a road template.

### 6. [critical] ×1  (gravel/ambitious_first_timer)
> 'Road Race Strategy' section is included in a gravel gran fondo guide. Road racing tactics (attacks, echelon positioning, surge dynamics, etc.) are wrong-discipline content and would actively mislead this athlete — embarrassing to send.

### 7. [critical] ×1  (gravel/ambitious_first_timer)
> 'Category 5 to Category 1 Pathway' section has no relevance to a UCI Gran Fondo participant. Gran Fondos use mass-start/timed formats, not USA Cycling or UCI category upgrade pathways. This is copy-pasted road racing content that does not belong here.

### 8. [critical] ×1  (road/weekend_warrior)
> 'Category 5 to Category 1 Pathway' section is listed in the table of contents and presumably appears in the full guide. This is a USA Cycling amateur racing category ladder concept that is entirely irrelevant to a weekend warrior whose stated goal is simply to 'finish' a gran fondo. It implies competitive racing advancement, contradicts the athlete's persona and goal, and would confuse or mislead this customer.

### 9. [critical] ×1  (road/veteran_podium_chaser)
> Section titled 'Category 5 to Category 1 Pathway' appears in the table of contents (and presumably later in the guide). This athlete is a veteran podium chaser — a Cat 5 progression pathway is completely wrong for their persona and experience level, and would be embarrassing or confusing to a paying customer of this caliber.

### 10. [critical] ×1  (mtb/weekend_warrior)
> Discipline mismatch — sections titled 'Road Skills,' 'Road Race Strategy,' and 'Category 5 to Category 1 Pathway' appear in the table of contents for an MTB athlete targeting a Gran Fondo. The Gran Fondo Guadeloupe is a road/gran-fondo event, not an MTB race, yet the plan persona is tagged 'mtb' and these sections add confusion. If the athlete is actually doing a road gran fondo, the discipline field is wrong and every MTB-specific skill reference would be incorrect; if the athlete truly rides MTB the road race strategy content is irrelevant. Either way the discipline inconsistency must be resolved before sending.

### 11. [critical] ×1  (mtb/weekend_warrior)
> 'Category 5 to Category 1 Pathway' section is completely inappropriate for a 53-year-old weekend warrior whose stated goal is simply to 'finish.' Cat upgrade pathways apply to licensed road racers chasing upgrade points — this has no place in a gran fondo completion plan and will confuse or mislead the customer.

### 12. [major] ×2  (gravel/masters_returner, mtb/weekend_warrior)
> Long-ride duration range is cited as '2.1–3.5 hours' in the Weekly Structure section. For a 7 h/week athlete targeting a ~8.8-hour race (per the fueling duration), a 3.5-hour ceiling on the longest long ride is plausible but on the low end; more importantly the fueling section targets 59 g carbs/hour over 8.85 hours, which implies the athlete expects to be on course far longer than any training ride. The guide never explicitly bridges this gap for the athlete — a brief note that race duration will far exceed any single training ride and that fueling rehearsal is therefore critical is missing and relevant.

### 13. [major] ×1  (mtb/ambitious_first_timer)
> The guide includes a 'Road Skills' section heading (visible in the table of contents). For an MTB Gran Fondo in the Negev Desert, skills content should cover MTB-specific terrain handling — loose over hardpack, rocky descents, sandy corners — not road cycling skills. Sending road skills content to an MTB rider is embarrassing.

### 14. [major] ×1  (mtb/ambitious_first_timer)
> Fueling duration of ~5.7 hours and 273g total carbs at 48g/hr is internally consistent, but for a first-timer doing 85 miles of MTB in Eilat's desert terrain (significant climbing, technical sections), a ~5.7-hour finish estimate likely underestimates race duration. A beginner MTB rider on this course could easily take 6.5–8 hours, which would make the fueling plan dangerously short. The coach should flag this prominently and instruct the athlete to plan for a longer duration with a larger carb reserve.

### 15. [major] ×1  (gravel/masters_returner)
> FTP test zones retention period is stated as 'the next 6 weeks' in the warning box, but this is a 9-week plan with (per the WARN flag) potentially unusual FTP test frequency. Telling a 9-week athlete their test result governs only 6 weeks is inconsistent with the plan length and may confuse them about when to retest.

### 16. [major] ×1  (gravel/masters_returner)
> The athlete's weight (193 lbs / 87.5 kg) and height (5'6") are displayed in the profile section but were never supplied in the athlete JSON — the plan JSON contains only age, FTP, and hours. These figures appear fabricated by the generator and must not be sent to a real paying customer; they could be embarrassingly wrong.

### 17. [major] ×1  (gravel/masters_returner)
> Off days listed as Saturday AND Sunday, with the long ride on Friday. A 9-hour/week masters athlete losing both weekend days to rest and doing the long ride mid-week is an unusual and unexplained structure. Weekend long rides are the norm for working athletes; this needs explicit justification or it reads as a template error.

### 18. [major] ×1  (gravel/masters_returner)
> FTP Test Frequency check returned WARN in the preview but the guide text says the test result 'sets ALL your training zones for the next 6 weeks' — in a 9-week plan that framing is inconsistent and may mislead the athlete about when zones should be updated.

### 19. [major] ×1  (gravel/masters_returner)
> Elevation listed as '650 ft' in the header for a Cozumel 96-mile course. Cozumel is a famously flat island; 650 ft over 96 miles is plausible, but the figure appears in the plan header without any source attribution and the race-data note says only distance is verified — a suspiciously round number for elevation should either be confirmed or flagged to the athlete rather than stated as fact.

### 20. [major] ×1  (gravel/ambitious_first_timer)
> Long ride duration range cited in the Weekly Structure section is '3.2–5.3 hours,' but the verified race duration estimate is ~4.6 hours and the event is 68 miles. A peak long ride of 5.3 hours overshoots the race estimate by ~15% without explanation, and the low end of 3.2 hours in context reads as a Week 1 target, which may confuse athletes given the 9-week compressed timeline.

### 21. [major] ×1  (road/weekend_warrior)
> Athlete weight (157 lbs / 71.2 kg) and height (5'8") appear in the profile card, but neither field exists in the provided athlete JSON — the source data only contains age, sex, ftp (null), and hours_target. These values appear to have been fabricated or hallucinated by the generator, which is embarrassing if wrong and a trust issue regardless.

### 22. [major] ×1  (road/weekend_warrior)
> 'Strength training: Included (dumbbells)' is listed in the weekly-at-a-glance summary, but the athlete JSON contains no mention of strength preferences, equipment availability, or a strength training flag. Prescribing dumbbell strength work without any questionnaire basis is an unsupported assumption that could conflict with the athlete's actual situation.

### 23. [major] ×1  (road/veteran_podium_chaser)
> Fueling recommendation of 68 g carbs/hour is on the low end for a ~4.4-hour race effort at podium intensity (current evidence supports 80-100+ g/hr for trained athletes with gut adaptation). For a podium-goal athlete, under-fueling is a direct race risk — the number should either be higher or explicitly caveated as a starting point to train the gut upward.

### 24. [major] ×1  (road/veteran_podium_chaser)
> Three preview checks flagged WARN (Zone Distribution, FTP Test Frequency, Taper Intensity) but none of these warnings are addressed or explained anywhere in the visible guide text. The taper intensity WARN in particular could mean the taper is insufficiently sharp for a 9-week plan ending on race day — this must be resolved or acknowledged before sending.

### 25. [major] ×1  (mtb/weekend_warrior)
> Taper Intensity flagged WARN by the automated preview check, yet the guide text contains no explanation of what the taper intensity concern is or how the athlete should adjust. A paying customer reading this will have no visibility into a known issue that directly affects their peak-week execution.
