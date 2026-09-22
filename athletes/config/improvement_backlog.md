# Improvement backlog — 2026-09-22

**Quality 2.05** · avg coach 6.5/10 · contract pass 75% · load 12.38/plan · 6 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×3  (road/time_crunched_parent, road/veteran_podium_chaser)
> The 'Category 5 to Category 1 Pathway' section is listed in the Table of Contents. This athlete's goal is simply to FINISH a 102-mile gran fondo — there is no mention of racing categories anywhere in their profile. Cat 5–1 content belongs in a competitive road-racer plan, not a time-crunched finish-goal athlete's guide. Including it suggests the wrong template was partially merged.

### 2. [critical] ×2  (gravel/ambitious_first_timer, gravel/masters_returner)
> Table of Contents and guide body include a 'Road Race Strategy' section. This athlete is doing a gravel gran fondo, not a road race. Road race tactics (e.g., peloton dynamics, drafting strategy, attack/cover tactics) are irrelevant and potentially misleading for a gravel event. This must be replaced with gravel-specific race strategy (terrain management, self-pacing on dirt/gravel descents, hydration point planning for a solo effort).

### 3. [major] ×3  (gravel/ambitious_first_timer, gravel/time_crunched_parent, road/time_crunched_parent)
> TSS Progression check returned WARN in the preview but the guide contains no acknowledgment or mitigation note for the athlete (e.g., a brief callout that one week-over-week jump is higher than ideal and how to manage it). A coach would flag this proactively rather than silently pass it through.

### 4. [critical] ×1  (road/time_crunched_parent)
> Countdown says '60 days from today' but the plan start date is 2026-09-28 and the race is 2026-11-21 — that is 54 days from plan start, not 60. If 'today' is meant to be the generation date, it must be calculated correctly and locked; a hardcoded wrong number destroys athlete trust in the verification block that is specifically designed to catch date errors.

### 5. [critical] ×1  (gravel/time_crunched_parent)
> Wrong-discipline content: The table of contents explicitly lists 'Road Race Strategy' and a 'Category 5 to Category 1 Pathway' section. This athlete is a gravel racer with a finish goal — road racing category progression content is entirely irrelevant, potentially confusing, and embarrassing to send.

### 6. [critical] ×1  (gravel/time_crunched_parent)
> Zone Distribution check FAILED (preview_checks) but the guide never acknowledges or corrects it. Sending a plan with a known failed check without explanation means the athlete will be training in the wrong zone distribution — directly contradicting the guide's own extensive warnings about gray-zone riding.

### 7. [critical] ×1  (road/time_crunched_parent)
> Off days are listed as Saturday AND Sunday, with the long ride on Thursday. For a time-crunched parent persona, weekdays are typically the constrained days and weekends are when the long ride happens. Placing the long ride mid-week and giving the parent both weekend days off is almost certainly wrong and will make the plan unworkable for this athlete's life. This needs to match the athlete's actual schedule from the questionnaire.

### 8. [major] ×2  (gravel/time_crunched_parent, road/veteran_podium_chaser)
> The FTP test protocol states 'The test result sets ALL your training zones for the next 6 weeks' — but this is an 8-week plan, and the FTP Test Frequency check passed, implying there is only one test. The '6 weeks' figure is either a copy-paste artifact or arithmetically wrong for this plan length.

### 9. [major] ×1  (gravel/ambitious_first_timer)
> Athlete weight (176 lbs / 79.8 kg) and height (5'6") appear in the profile card but the source JSON shows no such fields — these values are not in the athlete object and were not provided in the questionnaire. Sending fabricated anthropometric data to a paying customer is embarrassing and undermines trust. If these fields are not collected, they must be omitted or shown as 'Not provided'.

### 10. [major] ×1  (gravel/ambitious_first_timer)
> Equipment Checklist mandatory item reads 'Bike — road bike, in good working order.' This athlete is doing a gravel event; the bike should be described as a gravel bike (or at minimum 'gravel or endurance bike'). Telling a gravel racer their mandatory equipment is a road bike is a discipline mismatch that erodes confidence in the plan.

### 11. [major] ×1  (road/time_crunched_parent)
> Off days listed as 'Monday, Friday, Wednesday' — three off days totals only 4 riding days, which is consistent with 5 h/week, but listing three non-consecutive off days in that order (Mon, Fri, Wed) is confusing and likely a rendering artifact; the natural reading implies Wed is sandwiched between two riding days (Tue, Thu) which undermines the stated mid-week interval structure. Should be presented in calendar order (Mon, Wed, Fri) for clarity.

### 12. [major] ×1  (road/time_crunched_parent)
> Long ride cap stated as '1.5–2.2 hours' in the Weekly Structure section. For a 102-mile race with an estimated ~6.7-hour finish duration (per fueling data), even the plan's own 'Biggest Opportunity' callout admits this is too short and recommends 3–4 hour rides. The body text then contradicts itself by framing 1.5–2.2 h as the expected peak long-ride range rather than the baseline floor — this will confuse the athlete about what the plan actually delivers.

### 13. [major] ×1  (road/time_crunched_parent)
> Fueling section references 59 g/hr carbs and a ~6.7-hour estimated race duration (from plan JSON) but the truncated guide text does not appear to surface the total carbohydrate target or the per-bottle/per-stop strategy for a 102-mile event. For a finish-goal athlete facing a potential 6–7 hour day, omitting actionable race-day fueling numbers in the Nutrition Strategy section (not visible in the excerpt) is a significant coaching gap — needs verification that it exists in the full document.

### 14. [major] ×1  (gravel/time_crunched_parent)
> Long-ride duration contradiction: The 'Weekly Structure' section states the peak long-ride duration is '1.5–2.2 hours,' but the 'Biggest Opportunity' callout immediately below recommends single rides of '3–4 hours.' For a 102-mile (~6.7 h) event, a 2.2-hour ceiling is inadequate and the internal contradiction will confuse the athlete about what the plan actually prescribes.

### 15. [major] ×1  (gravel/time_crunched_parent)
> Road Skills section is listed in the table of contents. For a gravel discipline this should be gravel-specific skills (loose surface cornering, descending on gravel, creek crossings, tire pressure management) — generic or road-biased skills content is mismatched to the event.

### 16. [major] ×1  (road/time_crunched_parent)
> The nutrition section is visibly truncated mid-sentence ('0.3-0.4g protein/kg + 1.0-1.2g carbs/kg afte'). The fueling guidance — including the race-day target of ~68g carbs/hour for a ~4-hour effort — never appears in the visible text. If the full document is also cut off, the athlete receives incomplete and potentially critical fueling information for a podium-goal A-race.

### 17. [minor] ×2  (road/time_crunched_parent, road/veteran_podium_chaser)
> Long ride duration is cited as '2.7-4.6 hours' in the Weekly Structure section. The upper end (4.6h) slightly exceeds the fueling-derived race duration of ~3.98h and the 8h/week cap would make a 4.6h single ride implausible without gutting the rest of the week. The range should be anchored more tightly to race duration and weekly hour budget.

### 18. [minor] ×2  (road/time_crunched_parent, road/weekend_warrior)
> TSS Progression is flagged WARN in the preview checks but there is no mention of this in the guide text, nor any coach note explaining it to the athlete. A podium-goal athlete paying for a premium plan deserves transparency if the progression deviates from the norm.

### 19. [major] ×1  (road/veteran_podium_chaser)
> Experience level contradiction: the athlete profile states '14 Years Riding' and the methodology section calls the athlete 'Intermediate level.' A 14-year veteran with a 255 W FTP targeting a podium at an A-race is emphatically not intermediate — the persona label is 'Experienced racer chasing a podium.' This undermines credibility and may cause the athlete to question whether the plan was built for her.

### 20. [major] ×1  (road/veteran_podium_chaser)
> Taper Intensity is flagged WARN in the preview checks and is unresolved. The guide text does not address or explain what the taper intensity issue is. Sending a plan with a known unresolved warning — especially in the taper, the most consequential phase for race-day performance — is not acceptable.

### 21. [major] ×1  (road/veteran_podium_chaser)
> The 'Women-Specific Considerations' section is listed in the table of contents but the truncated text does not show its content. Given that the athlete is female and 42 (peri/post-menopausal considerations, recovery, fueling differences are highly relevant), this section must be substantive and coach-written — if it is thin or generic boilerplate it is a significant miss for this persona.

### 22. [major] ×1  (gravel/masters_returner)
> Weekly Volume check is flagged FAIL by the automated preview. The guide never acknowledges, explains, or corrects this. A paying athlete who notices the discrepancy between the 9 h/week stated target and whatever the calendar actually schedules will lose confidence immediately. Either the volume in the calendar must be fixed, or the guide must transparently note the adjusted hours and why.

### 23. [major] ×1  (gravel/masters_returner)
> Hourly fueling recommendation is 59 g carbs/hour for a ~5.7-hour desert race in Eilat in December (still warm climate). Current sports-science consensus for efforts of this duration supports 80–100 g/hour (with gut training) for trained athletes. 59 g/hour is meaningfully below optimal for a 5+ hour event and could contribute to a DNF for a goal of 'finish'. The number should either be raised or accompanied by a clear explanation of why it is intentionally conservative.

### 24. [minor] ×1  (road/time_crunched_parent)
> Strength section says 'full gym' is included, but no context is given about how to handle gym sessions when they conflict with leg-heavy interval days — a common scheduling pain point for the time-crunched parent persona that deserves at least one sentence of guidance.

### 25. [minor] ×1  (gravel/time_crunched_parent)
> Strength training is listed as included ('dumbbells') in the at-a-glance week summary, but no strength prescription or rationale appears in the truncated guide. If the full guide also omits it, this is a dangling promise to a paying customer.
