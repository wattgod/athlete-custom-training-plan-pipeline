# Improvement backlog — 2026-08-05

**Quality -0.54** · avg coach 5.25/10 · contract pass 88% · load 16.38/plan · 13 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×4  (mtb/ambitious_first_timer, road/time_crunched_parent, road/veteran_podium_chaser, road/weekend_warrior)
> 'Category 5 to Category 1 Pathway' section appears in the table of contents and (implied) body. This is a licensed road-racing licence progression framework — it is completely irrelevant to a Gran Fondo finish-goal athlete and would confuse or mislead the customer.

### 2. [critical] ×1  (mtb/ambitious_first_timer)
> Discipline mismatch: the athlete's persona discipline is 'mtb' but the plan is unmistakably built for gravel — it includes a 'Gravel Skills' section, references 'gravel cornering / gravel-specific' content, and the race itself ('Gravel Roll - Pecan Shaker') is a gravel event. The header, methodology framing, and skills content all need to be audited for MTB vs gravel alignment. If the athlete intended gravel, the discipline field is wrong and the customer was onboarded incorrectly; if MTB, the plan content is wrong. Either way this must be resolved before sending.

### 3. [critical] ×1  (mtb/ambitious_first_timer)
> Race-discipline contradiction: the plan is titled and flagged internally as an 'MTB' plan (persona discipline = mtb) yet the race 'Gravel Roll - Pecan Shaker' is clearly a gravel event in the verified database. A customer receiving an 'MTB plan' for a gravel race — or vice versa — is a serious coaching error and an embarrassing product failure.

### 4. [critical] ×1  (road/weekend_warrior)
> 'Road Race Strategy' section is listed in the contents. A Gran Fondo is a mass-participation timed event, not a road race with tactics, attacks, or field sprints. Providing road-race tactical advice (breakaways, positioning, lead-outs) is wrong for this discipline/goal and undermines the guide's credibility.

### 5. [critical] ×1  (gravel/masters_returner)
> Discipline mismatch — the guide contains a 'Road Race Strategy' section and a 'Category 5 to Category 1 Pathway' section. This athlete is racing a gravel gran fondo, not a road criterium or road stage race. Cat 5–1 upgrade pathways are a USA Cycling road racing concept with zero relevance here. These sections must be removed or replaced with gravel-specific content (e.g., loose-surface cornering, pacing on mixed terrain, group dynamics in a gran fondo).

### 6. [critical] ×1  (gravel/masters_returner)
> Athlete weight contradiction — the athlete's profile card inside the guide states '175 lbs / 79.4 kg / 5'6"', but no weight was provided in the plan JSON. The system has either fabricated or pulled weight/height from a wrong source. If these numbers are invented, they are being presented as fact to the customer ('Every number … is calibrated to your specific situation'), which is materially misleading and embarrassing.

### 7. [critical] ×1  (gravel/ambitious_first_timer)
> Wrong-discipline content: The guide contains a 'Road Race Strategy' section and a 'Category 5 to Category 1 Pathway' section. This athlete is a gravel racer targeting a finish, not a licensed road racer chasing category upgrades. These sections are completely irrelevant and would seriously undermine trust in the plan.

### 8. [critical] ×1  (gravel/ambitious_first_timer)
> The Zone 1 Active Recovery row in the zone chart has no %FTP or %LTHR values listed (only raw watts 0–103W), while all other zones show both. For an athlete without deep zone literacy this is confusing and inconsistent — it looks like a template rendering failure.

### 9. [critical] ×1  (road/veteran_podium_chaser)
> Fueling section states a race duration of 4.1 hours (from plan JSON: fueling.duration_h = 4.1) and 68g/hr carbs, but nowhere in the visible guide text is the athlete told his estimated race duration is ~4.1 hours or given a per-hour target tied to that number. The recovery nutrition recommendation (73-88g carbs post-ride) incidentally uses numbers that could be confused with race fueling. The race nutrition strategy section must explicitly state the 4.1h estimate and ~68g/hr target to be actionable.

### 10. [critical] ×1  (mtb/ambitious_first_timer)
> Section titled 'Road Skills' and 'Road Race Strategy' are included in an MTB discipline plan. These are explicitly road-racing sections and have zero relevance to a mountain bike gran fondo — this is an embarrassing discipline mismatch.

### 11. [critical] ×1  (mtb/ambitious_first_timer)
> Discipline mismatch throughout: the plan JSON flags discipline as 'mtb' but the race is 'Flanders Legacy Gravel' — a verified gravel event in Flanders, Belgium. The guide itself contradicts the discipline tag by including a 'Gravel Skills' section, confirming the event is gravel. Every reference to MTB persona framing, MTB-specific skill content, or MTB methodology calibration is therefore wrong for this athlete's actual event.

### 12. [critical] ×1  (mtb/ambitious_first_timer)
> Zone Distribution preview check FAILED. The guide repeatedly states ~75% of riding stays 'genuinely easy' (Pyramidal), but the automated gate flagged zone distribution as non-compliant. Sending a plan where the prescribed zone split contradicts the stated methodology is a coaching error that will produce wrong adaptations.

### 13. [critical] ×1  (mtb/ambitious_first_timer)
> The race name in the document header reads 'Flanders Legacy Gravel 75mi' and the discipline is gravel, yet the athlete persona and plan metadata are tagged 'mtb'. This internal contradiction means either the wrong plan template was applied to this athlete, or the wrong race was loaded. Either way the plan cannot be sent until the discipline is reconciled.

### 14. [major] ×2  (mtb/ambitious_first_timer)
> FTP Test Frequency check returned WARN in preview checks but is never explained or resolved in the guide text. With only a 9-week plan and a 6-week zone-validity window called out in the guide itself, the athlete needs clarity on exactly how many tests are scheduled and when; a silent WARN passed to the customer is not acceptable.

### 15. [major] ×1  (mtb/ambitious_first_timer)
> Long ride duration range cited as '3.4–5.8 hours' in the Weekly Structure section but the fueling section specifies a race duration of 6.7 hours. The longest training ride is substantially shorter than race duration, yet no explanation is given for this gap — a first-timer needs to understand why their longest ride is ~87% of race time, or the numbers should be reconciled.

### 16. [major] ×1  (mtb/ambitious_first_timer)
> The guide states '1 Years Riding' and calls the athlete 'Intermediate level' in the same breath — these are contradictory. One year of riding is typically beginner/novice, not intermediate. This will undermine athlete trust if they notice it.

### 17. [major] ×1  (road/weekend_warrior)
> The fueling section in the guide text visible here omits the race-day carbohydrate rate entirely. The plan JSON specifies 58 g/h over a 4.6-hour estimated duration — this is a concrete, personalised number that must appear in the Nutrition Strategy section; its absence means the athlete has no actionable fueling target for race day.

### 18. [major] ×1  (gravel/masters_returner)
> Race date verification language is hedged incorrectly — the guide tells the athlete to 'Triple-check: Confirm this is the correct date by visiting the official race website' for a race that is in a verified database (race_in_verified_db: true). This creates unwarranted doubt about data the business has already verified, eroding confidence in the plan. The caveat about confirming distance/elevation is fine, but the alarming triple-check language around the date should be removed or softened.

### 19. [major] ×1  (gravel/masters_returner)
> Zone 1 power range is missing from the zone chart — the table shows '0-112W' for Zone 1 but omits the % FTP and % LTHR columns (they are blank), which is inconsistent with every other zone row and looks like a rendering/generation error that slipped through.

### 20. [major] ×1  (gravel/ambitious_first_timer)
> TSS Progression flagged WARN in the preview checks but the guide contains zero acknowledgement or explanation for the athlete. A paying customer who notices week-over-week TSS jumps with no coaching rationale will lose confidence; the guide should either explain the non-linear ramp or include a one-line coach's note.

### 21. [major] ×1  (gravel/ambitious_first_timer)
> 'Road Skills' section (referenced in the Contents) is listed without gravel-specific content visible in the truncated text. If it contains road-race cornering or criterium tactics rather than gravel-specific skills (loose surface cornering, hike-a-bike, tubeless repair, pacing on mixed terrain), it is wrong-discipline content for this athlete.

### 22. [major] ×1  (road/veteran_podium_chaser)
> FTP Test Frequency check flagged WARN in the automated preview but the guide text states 'The test result sets ALL your training zones for the next 6 weeks' — implying only one test in a 17-week plan. For a 17-week plan a single mid-plan retest is standard practice; the guide must either schedule a second test explicitly or explain the rationale for the single-test approach so it does not look like an oversight.

### 23. [major] ×1  (road/veteran_podium_chaser)
> Weekly Volume also flagged WARN in the automated preview checks. The guide claims 15h/week but gives a long-ride range of only 2.8–4.7 hours, which is plausible for one session but leaves ~10+ hours to other sessions. No explicit per-day or per-session volume breakdown is provided in the guide to validate that 15h is actually achievable across 6 days without per-day cap violations — the athlete has no way to sanity-check the calendar against their stated availability.

### 24. [major] ×1  (road/veteran_podium_chaser)
> 'Masters Training Considerations' appears in the table of contents but is not present in the truncated guide text provided for review. For a 42-year-old athlete this section is specifically relevant (recovery, hormonal factors, injury risk) and must not be missing or empty in the final deliverable.

### 25. [major] ×1  (road/time_crunched_parent)
> Long-ride duration caps described as '1.5–2.2 hours' peak are very low for a race estimated at ~4 hours (78.3 miles at gran fondo pace). The plan itself acknowledges this in the 'Biggest Opportunity' box, but then still anchors the expectation at 2.2 h max. For a 5 h/week athlete the long ride should realistically be pushed to 2.5–3 h at peak, with at least one or two 3–3.5 h outlier rides called out as optional stretch targets. Framing 2.2 h as the ceiling, even with a caveat, leaves the athlete underprepared for a 4-hour effort.
