# Improvement backlog — 2026-09-14

**Quality 1.9** · avg coach 6.0/10 · contract pass 100% · load 12.75/plan · 9 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×1  (mtb/weekend_warrior)
> Discipline mismatch — the table of contents lists 'Road Skills,' 'Road Race Strategy,' and 'Category 5 to Category 1 Pathway' sections. This athlete is an MTB rider; road racing categories and road race tactics are irrelevant and wrong. These sections must be replaced with MTB-specific content (trail skills, cornering, technical descending, group-start strategy for a mass-start gran fondo on MTB terrain).

### 2. [critical] ×1  (mtb/weekend_warrior)
> The plan is titled and positioned as an MTB plan but the guide text consistently frames outdoor riding around road-race dynamics ('group rides,' 'wind,' 'Strava segment') without any MTB-specific skill or terrain language anywhere in the visible text. For a discipline where technical skills are a primary limiter, this omission is a coaching failure.

### 3. [critical] ×1  (gravel/time_crunched_parent)
> Table of contents and (presumably) a full section titled 'Road Race Strategy' and 'Category 5 to Category 1 Pathway' appear in the guide. This athlete is a gravel racer with a finish goal — road race tactics and a cat-upgrade pathway are completely wrong discipline content and will confuse or embarrass.

### 4. [critical] ×1  (gravel/masters_returner)
> Discipline mismatch — the guide contains a 'Road Race Strategy' section and a 'Category 5 to Category 1 Pathway' section. This is a gravel gran fondo with a goal of 'finish.' Road race tactical strategy and a Cat upgrade pathway are entirely irrelevant content that was clearly carried over from a road-racing template. Sending this to a gravel gran fondo athlete is embarrassing and undermines trust in the plan's customization.

### 5. [critical] ×1  (road/masters_returner)
> A 'Category 5 to Category 1 Pathway' section is listed in the table of contents. This is road-racing category progression content that is completely irrelevant to a gran fondo finish-goal athlete. It would confuse and alarm her — she is not entering USA Cycling category racing — and is a significant credibility embarrassment.

### 6. [critical] ×1  (road/weekend_warrior)
> The guide includes a 'Category 5 to Category 1 Pathway' section. This athlete is a 44-year-old weekend warrior with a finish goal — competitive USA Cycling category progression is completely irrelevant and will confuse or mislead her. It must be removed entirely.

### 7. [critical] ×1  (mtb/ambitious_first_timer)
> Discipline mismatch — equipment checklist mandates a 'road bike in good working order' for an MTB athlete. This is factually wrong and embarrassing; an MTB athlete needs an appropriate mountain bike. MTB-specific gear (trail-ready tires, dropper post, flat pedal or clipless MTB shoe considerations, pack/hydration vest) is entirely absent.

### 8. [critical] ×1  (mtb/ambitious_first_timer)
> Discipline mismatch — the table of contents and body text include 'Road Skills,' 'Road Race Strategy,' and 'Category 5 to Category 1 Pathway' sections. These are pure road-racing content and have no place in an MTB gran fondo plan. They signal the wrong template was used or discipline filtering failed.

### 9. [critical] ×1  (gravel/veteran_podium_chaser)
> Wrong discipline content included: The table of contents and body text contain 'Road Skills,' 'Road Race Strategy,' and a 'Category 5 to Category 1 Pathway' section. This athlete is preparing for a gravel gran fondo, not a road criterium or road race. Category pathways are a USA Cycling road/track concept entirely irrelevant to a gravel event. This is embarrassing and will confuse or alarm the athlete.

### 10. [major] ×1  (mtb/weekend_warrior)
> Zone Distribution and TSS Progression both flagged WARN in the preview checks, yet the guide text makes no acknowledgment of these warnings or any compensating coaching note. A paying athlete receiving a plan with known distribution or load-progression issues deserves an explanation or correction, not silence.

### 11. [major] ×1  (mtb/weekend_warrior)
> FTP Test Frequency flagged WARN — the guide states 'The test result sets ALL your training zones for the next 6 weeks,' but this is an 8-week plan. That figure is either copied from a longer template or is simply wrong for this plan length, and it may mislead the athlete about when to retest.

### 12. [major] ×1  (mtb/weekend_warrior)
> The race is a UCI Gran Fondo (road-paved gran fondo in Greece), yet the athlete's discipline is listed as 'mtb.' If the race is genuinely a paved gran fondo and the athlete intends to race it on an MTB, the plan should explicitly acknowledge the equipment choice and adjust skills/tactics accordingly. If this is a gravel/MTB gran fondo, the road-specific sections are doubly wrong. Either way, the disconnect is unresolved and confusing.

### 13. [major] ×1  (gravel/time_crunched_parent)
> The section heading 'Road Skills' feeds into 'Road Race Strategy' and the Cat 1–5 pathway. Even if the Road Skills content itself is generic, the adjacent road-racing framing makes it inappropriate for a gravel event guide and needs to be replaced with gravel-specific skills content (e.g., loose surface cornering, descent braking on gravel, pacing a 100-mile gravel event).

### 14. [major] ×1  (gravel/time_crunched_parent)
> Zone distribution flagged WARN by the automated gate and FTP Test Frequency flagged WARN — neither issue is explained or mitigated anywhere in the visible guide text. The coach's note should acknowledge the zone distribution skew (or confirm it is intentional pyramidal weighting) so the athlete isn't confused if they track their own zones.

### 15. [major] ×1  (gravel/masters_returner)
> Taper intensity flagged WARN in preview checks but is not addressed or corrected in the guide text. A 63-year-old masters athlete with a goal of 'finish' needs a taper that is conservatively managed; leaving a known taper intensity problem unresolved before sending is unacceptable.

### 16. [major] ×1  (gravel/masters_returner)
> Fueling section states a race duration of ~5.7 hours (from the JSON), but the guide text does not surface this number explicitly to the athlete. At 60 g carbs/hour over ~5.7 hours that is ~340 g carbs total — a significant logistical requirement for a desert gran fondo that should be spelled out clearly so the athlete can plan bottles, gels, and feed-zone strategy for a hot Eilat course.

### 17. [major] ×1  (road/masters_returner)
> Off days listed in the guide are 'Friday, Tuesday' but the plan JSON does not confirm these days; more importantly, the plan start date is 2026-09-21 (a Monday) and race day is a Sunday (2026-11-15). The guide should be checked to ensure the stated off days are actually consistent with the generated calendar — the guide text appears auto-inserted and must match the real schedule.

### 18. [major] ×1  (road/masters_returner)
> The FTP test result is stated to 'set ALL your training zones for the next 6 weeks,' but this is an 8-week plan with one test. The stated 6-week figure is internally inconsistent with the plan length and will confuse the athlete about when/whether to retest.

### 19. [major] ×1  (road/masters_returner)
> The 'Road Race Strategy' section is listed in the table of contents. Gran fondos are timed participation events, not road races with tactical racing strategy (attacks, lead-outs, field sprints). This content is discipline-adjacent but contextually wrong for a finish-goal gran fondo rider and will read as irrelevant or misleading.

### 20. [major] ×1  (road/weekend_warrior)
> The long-ride duration stated in the Weekly Structure section is '1.5 hours' as the peak long ride. For a 68-mile race with an estimated 4.67-hour finish time, a 1.5-hour cap is grossly inadequate and directly contradicts the plan's own 'YOUR BIGGEST OPPORTUNITY' call-out, which tells the athlete a 3-4 hour ride is worth more. The plan cannot simultaneously warn that long rides are too short AND prescribe 1.5 h as the target ceiling — this needs reconciliation with a realistic, achievable long-ride ceiling that fits her 4 h/week budget.

### 21. [major] ×1  (road/weekend_warrior)
> The preview check flags a 'WARN' on Taper Intensity, but the guide text makes no acknowledgment of this and offers no corrective guidance. A known taper-intensity issue should either be resolved in the calendar or explicitly flagged to the athlete; sending without addressing it is a coaching error.

### 22. [major] ×1  (road/weekend_warrior)
> 'Women-Specific Considerations' appears in the table of contents but the truncated text never delivers meaningful content under that heading — if the section is present in the full document it must contain substantive, relevant guidance; if it is a placeholder or boilerplate it must be removed or completed before sending.

### 23. [major] ×1  (gravel/ambitious_first_timer)
> Weight (159 lbs / 72.1 kg) appears in the athlete profile section but the intake JSON records no weight field — this value was almost certainly fabricated by the generation system. Sending a made-up body weight to a paying customer is embarrassing and will undermine trust immediately. Verify the source or remove the weight line entirely.

### 24. [major] ×1  (gravel/ambitious_first_timer)
> The fueling model projects a race duration of ~7 h 9 min (7.155 h) for an 81-mile gravel race — roughly 11:25/mile average pace. For a 39-year-old male riding 8 h/week, this is on the very slow end but not impossible on a hilly gravel course. However, this duration is never surfaced to the athlete anywhere in the guide, so he cannot sanity-check it. The carb target and total (54 g/hr × 7.15 h = 386 g) are only defensible if the projected duration is visible and the athlete agrees with it. Add a 'Projected finish window' line to the Nutrition card.

### 25. [major] ×1  (gravel/ambitious_first_timer)
> TSS Progression check flagged WARN in the preview gate. The guide text is truncated so the actual weekly TSS ramp cannot be verified here, but a TSS ramp warning on a first-timer's only A-race plan is a meaningful injury/overtraining risk. This must be manually confirmed acceptable before sending — do not suppress the warning without a documented rationale.
