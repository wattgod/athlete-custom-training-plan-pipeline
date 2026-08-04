# Improvement backlog — 2026-08-04

**Quality -0.43** · avg coach 5.62/10 · contract pass 75% · load 16.38/plan · 11 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×4  (gravel/veteran_podium_chaser, road/time_crunched_parent, road/veteran_podium_chaser, road/weekend_warrior)
> 'Category 5 to Category 1 Pathway' section listed in the Table of Contents is road-racing and USA Cycling categorization content — completely irrelevant and embarrassing for a gravel racer. Gravel racing has no Cat 1–5 licensing ladder. This must be removed or replaced with gravel-specific content (e.g., mass-start tactics, gravel-specific positioning, feed zone strategy).

### 2. [critical] ×2  (gravel/ambitious_first_timer, gravel/veteran_podium_chaser)
> 'Road Race Strategy' and 'Category 5 to Category 1 Pathway' sections appear in the table of contents (and presumably in the full guide). This athlete is a gravel gran fondo first-timer with a goal of 'finish' — road racing category progression (Cat 5→1) is entirely the wrong discipline and implies racing a licensed road criterium/road race circuit. It will confuse the athlete and makes the guide look auto-generated from a road-racing template.

### 3. [critical] ×1  (road/time_crunched_parent)
> Zone Distribution check is flagged FAIL in the preview checks, yet the guide contains no acknowledgment, correction, or explanation. Sending a plan where the internal QA gate has already caught a zone distribution failure — without resolving it — is indefensible.

### 4. [critical] ×1  (road/time_crunched_parent)
> Off days listed as 'Saturday, Thursday, Sunday' — that is THREE off days per week, leaving only four training days, which is borderline acceptable for 8 h/week, but Saturday is a primary long-ride day for almost every time-crunched parent persona and the combination of Saturday + Sunday off eliminates the weekend entirely. This is almost certainly a generation error and will confuse the athlete immediately.

### 5. [critical] ×1  (gravel/ambitious_first_timer)
> 'Road Skills' section listed in the contents is ambiguous but in context of 'Road Race Strategy' and 'Cat 5→1 Pathway' it reads as road-racing specific content. For a gravel event the athlete needs gravel-specific skills (loose surface cornering, descending on mixed terrain, self-sufficiency/mechanicals, riding in rough conditions) — not road race pack-riding tactics.

### 6. [critical] ×1  (road/veteran_podium_chaser)
> Weekly Volume check flagged FAIL in the preview checks but the guide is being sent anyway with no correction or caveat. A paying athlete at 15h/week with a podium goal must not receive a plan whose volume structure failed automated validation — this is the top reason to hold the document.

### 7. [critical] ×1  (road/veteran_podium_chaser)
> Athlete is labelled 'Intermediate level' in the methodology rationale ('11 years of cycling experience at Intermediate level'), but the persona is explicitly 'veteran_podium_chaser — Experienced racer chasing a podium.' Calling an 11-year veteran with a podium goal 'Intermediate' is factually wrong and will undermine the athlete's trust in the entire document.

### 8. [critical] ×1  (gravel/veteran_podium_chaser)
> Weekly Volume check flagged WARN in preview_checks and was never resolved or explained to the athlete. At 13h/week for a 36-year-old experienced racer on a gravel KOM plan this is a meaningful flag — the guide should not ship while this remains unresolved without at minimum an inline explanation or coach note.

### 9. [critical] ×1  (road/weekend_warrior)
> 'Road Race Strategy' section heading appears in the table of contents for an athlete entered in a gran fondo (a mass-participation endurance event), not a criterium or road race. Strategy content for pack racing, attacks, and positioning is inapplicable and potentially harmful — the athlete needs gran fondo pacing and climbing strategy, not race-tactics advice.

### 10. [critical] ×1  (gravel/time_crunched_parent)
> Table of contents and apparent guide body include a 'Road Race Strategy' section and a 'Category 5 to Category 1 Pathway' section. These are road-racing / USA Cycling categorization concepts that have zero relevance to a gravel gran fondo. A paying customer training for the Granfondo Tre Valli Varesine will reasonably question whether they received someone else's plan. These sections must be removed or replaced with gravel-specific content (e.g., pacing on loose descents, group dynamics in a gran fondo, nutrition on long climbs).

### 11. [critical] ×1  (gravel/time_crunched_parent)
> The 'Road Skills' section title appears alongside 'Road Race Strategy' in the ToC — for a gravel athlete this should cover gravel-specific skills (braking on gravel descents, cornering on loose surfaces, tire pressure management, riding in dust/mud). Leaving 'Road Skills' content designed for tarmac racing in a gravel plan is a discipline mismatch the athlete will notice immediately.

### 12. [major] ×2  (gravel/time_crunched_parent, road/weekend_warrior)
> TSS Progression check returned WARN in the preview but there is no acknowledgment, caveat, or corrective note anywhere in the visible guide text. A paying athlete deserves either a corrected progression or an explicit coach's note explaining why the TSS arc was intentionally shaped that way.

### 13. [major] ×1  (gravel/veteran_podium_chaser)
> 'Road Race Strategy' section is listed in the Table of Contents for a gravel event. While some tactics overlap, a dedicated road race strategy section signals wrong-discipline content was copy-pasted. It should be replaced with gravel race strategy (terrain reading, tire selection, pace management on mixed surfaces).

### 14. [major] ×1  (gravel/veteran_podium_chaser)
> Fueling: the guide states 69g carbs/hour for a 3.3h race. For a 330W FTP athlete targeting a podium (likely riding at 75–85% FTP for ~3+ hours), 69g/hr is on the low end of modern guidance (90–120g/hr is increasingly standard for trained athletes using glucose+fructose blends). At minimum the guide should acknowledge this is a conservative floor and encourage the athlete to train the gut toward higher intake, especially given the race goal is a podium finish.

### 15. [major] ×1  (road/time_crunched_parent)
> Goal field in 'Your Goals & Blindspots' reads only 'Compete' — the athlete's stated goal is 'podium.' This is a data-merge failure that undersells the athlete's ambition and makes the entire goal-setting section meaningless.

### 16. [major] ×1  (road/time_crunched_parent)
> Weekly Volume check is flagged WARN but the guide never surfaces this to the athlete or explains it. If volume is borderline for the hours target, the athlete deserves to know — silence is not the right handling.

### 17. [major] ×1  (road/time_crunched_parent)
> Long ride peak duration is stated as '2.3-3.8 hours' in the Weekly Structure section. For a 68-mile event estimated at roughly 3.3 h (per the fueling duration field), the low end of 2.3 h is only ~70% of race duration which is acceptable, but the range is oddly wide and the upper end of 3.8 h would exceed race duration — unusual for this event type and inconsistent with taper logic. Needs verification against the actual calendar.

### 18. [major] ×1  (road/time_crunched_parent)
> Race-day strategy section is titled 'Road Race Strategy' and the ToC includes discipline-specific content referencing road racing tactics. L'Étape is a mass-participation gran fondo, not a road race with tactics, attacks, or field dynamics in the traditional sense. Strategy content must be verified to ensure it isn't giving criterium/peloton tactics to a gran fondo athlete.

### 19. [major] ×1  (gravel/ambitious_first_timer)
> Zone distribution and TSS progression both flagged WARN in preview checks, yet the guide text contains no acknowledgment, caveat, or corrective guidance for the athlete about these deviations. A coach reviewing a plan with two training-load warnings should either fix the underlying schedule or explicitly address it.

### 20. [major] ×1  (gravel/ambitious_first_timer)
> The long-ride duration range quoted in the guide ('1.6–2.8 hours') is very short for a race estimated at ~4.6 hours. While the 'Biggest Opportunity' callout partially addresses this, the prescribed ceiling of 2.8 h is never reconciled against the fueling guide's 4.6 h race duration estimate — the athlete could reasonably conclude they never need to practice riding longer than 2.8 h, which is poor preparation for a 4.6 h event.

### 21. [major] ×1  (gravel/ambitious_first_timer)
> Hourly carb recommendation of 57 g/h is on the low end for a 4.6-hour gravel effort at race pace for a trained 28-year-old. Modern guidelines support 80–100+ g/h with multi-transportable carbs for efforts of this duration; 57 g/h could contribute to late-race bonking and reflects an outdated fueling model.

### 22. [major] ×1  (road/veteran_podium_chaser)
> Long ride duration range cited as '2.3-3.8 hours' in the Weekly Structure section. For a 68-mile race with ~3.3h expected finish time, the upper bound of 3.8h is barely adequate for a podium-level athlete at 15h/week, but the lower bound of 2.3h is oddly low and the range is never explained or tied to specific phases — reads like a placeholder formula output, not coached guidance.

### 23. [major] ×1  (road/veteran_podium_chaser)
> Road Skills and Road Race Strategy sections appear in the table of contents. While this is a road discipline, the race is a gran fondo (not a criterium or road race with a peloton finish). Generic 'road race strategy' content — if it covers attacks, sitting in, sprint lead-outs — is wrong-context advice for a timed gran fondo where the rider must execute a solo pacing effort. Needs to be gran-fondo-specific.

### 24. [major] ×1  (gravel/veteran_podium_chaser)
> 'Road Skills' section appears in the table of contents — this section title is ambiguous but in context likely contains road-cycling cornering/group-ride skills content rather than gravel-specific skills (climbing pacing, descending on loose gravel, nutrition execution on a 93-mile mountain stage). Needs verification and likely replacement.

### 25. [major] ×1  (gravel/veteran_podium_chaser)
> The fueling section specifies 68g carbs/hour for a 4.7-hour estimated duration, but the Taiwan KOM Challenge is a relentlessly climbing 93-mile mountain stage to Wuling Pass (~10,745 ft gain). The effort profile is almost entirely sustained climbing at threshold-to-VO2 intensity — fueling strategy should explicitly address high-intensity climbing nutrition, not just a flat hourly carb number. No mention of the extreme nature of the event's demands.
