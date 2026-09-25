# Improvement backlog — 2026-09-25

**Quality 2.83** · avg coach 6.38/10 · contract pass 100% · load 11.38/plan · 9 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×1  (gravel/ambitious_first_timer)
> Wrong-discipline content: Section titled 'Road Race Strategy' and 'Category 5 to Category 1 Pathway' are road-racing constructs that have zero relevance to a gravel event. USA Cycling cat designations do not apply to gravel racing, and road-race tactics (mass-start criterium/road-race strategy) are actively misleading for a gravel rider. This is a blatant template bleed-in that a paying gravel customer will notice immediately.

### 2. [critical] ×1  (gravel/ambitious_first_timer)
> Race countdown is wrong: The guide states '66 days from today' but the plan start date is 2026-09-28 and race date is 2026-11-30 — that is 63 days from plan start, not 66. If 'today' means plan-generation date the number still needs to be verified; a hard-coded wrong countdown directly contradicts the plan's own dates and erodes trust in all other numbers.

### 3. [critical] ×1  (mtb/weekend_warrior)
> Discipline mismatch throughout the guide: the athlete is an MTB rider, but the Equipment Checklist prescribes a 'road bike in good working order,' and the Road Skills and Road Race Strategy sections are written entirely for road racing. An MTB athlete needs trail-specific skills content (cornering, technical descending, traction management) and an MTB-appropriate equipment list (tubeless setup, dropper post, gloves, trail helmet, etc.).

### 4. [critical] ×1  (mtb/weekend_warrior)
> 'Category 5 to Category 1 Pathway' section appears in the table of contents and presumably in the full document. This is a USA Cycling road racing licensing pathway — it is entirely irrelevant to a 50-year-old weekend warrior doing a finish-goal MTB gran fondo. It signals the wrong athlete profile and undermines trust in the whole plan.

### 5. [critical] ×1  (mtb/ambitious_first_timer)
> Discipline mismatch — the plan JSON flags discipline = 'mtb' yet the guide contains a 'Road Skills' and 'Road Race Strategy' section. Gran Fondo Eilat is a road/paved gran fondo; if the plan was generated under an MTB flag these sections are for the wrong discipline entirely. Either the discipline tag is wrong and MTB-specific content (trail skills, suspension setup, technical descending) is missing, or the race is correctly a road event and the 'mtb' tag caused an internal logic error. Either way the guide as written is self-contradictory and cannot be sent.

### 6. [critical] ×1  (mtb/ambitious_first_timer)
> Equipment checklist says 'Bike — road bike, in good working order' but the discipline is tagged MTB. If the athlete owns an MTB and intends to ride it, this instruction is actively wrong and potentially dangerous (road tires vs. MTB tires, suspension setup, etc.). If the race requires a road bike the discipline tag must be corrected before any content is finalised.

### 7. [critical] ×1  (gravel/masters_returner)
> 'Road Race Strategy' appears as a dedicated section in the table of contents for a gravel discipline athlete. This is the wrong discipline content — it should be Gravel Race Strategy. Sending a road race strategy section to a gravel racer is both embarrassing and potentially harmful to race execution.

### 8. [critical] ×1  (road/weekend_warrior)
> The table of contents and guide body include a 'Category 5 to Category 1 Pathway' section. This athlete is a 48-year-old weekend warrior whose sole goal is to finish a gran fondo — not a competitive road racer pursuing a USA Cycling upgrade pathway. This content is completely irrelevant, potentially confusing, and signals a template bleed from a different athlete profile. It must be removed entirely.

### 9. [critical] ×1  (road/weekend_warrior)
> Weight (139 lbs / 63.0 kg) and height (5'6") appear in the 'Your Profile' section, but neither field is present in the athlete data JSON. The plan fabricated biometric data for this athlete. This is a factual error that could seriously erode trust if the customer notices the numbers don't match reality.

### 10. [major] ×1  (gravel/ambitious_first_timer)
> Plan length vs. weeks_until_race discrepancy is unexplained to the athlete: The plan is 10 weeks but the race is 9 weeks away, meaning Week 1 of the plan has already passed before the athlete even receives it. The plan_note explains this is intentional (athlete starts later), but the guide never tells the athlete which week to start on. Without that instruction the athlete will either start from Week 1 (misaligned taper) or be confused.

### 11. [major] ×1  (gravel/ambitious_first_timer)
> Section heading 'Road Skills' appears in the contents — for a gravel event this should be 'Gravel Skills' or 'Bike Handling.' Combined with the Road Race Strategy section, the guide reads as a repurposed road-racing template, which undermines confidence in the plan's specificity and is incongruent with the stated discipline.

### 12. [major] ×1  (mtb/weekend_warrior)
> 'Road Race Strategy' section (listed in the table of contents) is inappropriate for an MTB event. L'Étape Ciudad de México is an MTB gran fondo; road race tactics (drafting, pack dynamics, positioning) do not apply and could actively mislead the athlete.

### 13. [major] ×1  (mtb/weekend_warrior)
> The 'Masters Training Considerations' section is listed in the table of contents but the truncated text never delivers it — for a 50-year-old athlete this is one of the highest-value sections. If it is missing or generic boilerplate in the full document, that is a significant gap for this specific persona.

### 14. [major] ×1  (mtb/ambitious_first_timer)
> Taper Intensity flagged WARN by automated checks and is never acknowledged or explained in the guide text. A paying athlete deserves to know why their taper looks the way it does; leaving a known warning unaddressed is a coaching quality failure.

### 15. [major] ×1  (mtb/ambitious_first_timer)
> 'Road Race Strategy' section is inappropriate for a Gran Fondo target regardless of discipline. Gran Fondos are not mass-start road races; drafting tactics, attacking, and field positioning advice is misleading for a first-timer whose goal is simply to finish.

### 16. [major] ×1  (mtb/ambitious_first_timer)
> The guide text is truncated mid-sentence ('If workout was long (2.5+ hours) AND hard, A') — the post-workout nutrition guidance is cut off. This is a content completeness failure that would reach the customer in an unfinished state.

### 17. [major] ×1  (gravel/ambitious_first_timer)
> Road Race Strategy section: the plan includes a 'Road Race Strategy' chapter (visible in the table of contents) for a GRAVEL discipline athlete. Road race tactics (e.g., draft dynamics, peloton positioning, attacks) are discipline-wrong for a gravel gran fondo and will confuse or mislead the athlete. This should be replaced with Gravel-Specific Race Strategy.

### 18. [major] ×1  (gravel/ambitious_first_timer)
> Road Skills section: similarly listed in the contents as 'Road Skills', which typically covers road-racing cornering and bunch-riding skills. For a gravel event this should address gravel-specific skills — loose-surface descending, technical terrain, varied surface transitions — not road race skills.

### 19. [major] ×1  (gravel/masters_returner)
> Hardcoded '60 mi' text fragment appears at the very end of the visible guide text ('No screens 60 mi') — this is almost certainly a corrupted merge or truncation artifact from a road-distance template bleed-in. Even if it's a truncation boundary issue, it reads as a nonsensical data error that would confuse the athlete.

### 20. [major] ×1  (gravel/masters_returner)
> 'Road Skills' section in the TOC is ambiguous/mismatched for gravel — gravel-specific skills (loose surface cornering, technical descending, tire pressure management, re-mounting after hike-a-bike) are meaningfully different from road skills and the section title should reflect the discipline.

### 21. [major] ×1  (road/weekend_warrior)
> The long-ride duration stated in the Weekly Structure section ('peak duration of 1.5–2.2 hours') is contradicted within the same paragraph, which then advises the athlete to aim for 3–4 hour rides. For a 68-mile event estimated at ~4.7 hours, a peak long ride of 2.2 hours is genuinely inadequate, and the internal contradiction makes the plan look confused and uncoached. The guidance should be reconciled: either the hours budget is acknowledged as a hard constraint with a clear workaround strategy, or the athlete is told directly what the realistic long-ride ceiling is.

### 22. [major] ×1  (road/weekend_warrior)
> 'Women-Specific Considerations' appears in the table of contents but the truncated text does not allow verification of its content. Given that other template-bleed errors exist (Cat 5–1 pathway), there is meaningful risk this section contains generic or mismatched content. It must be reviewed before sending.

### 23. [minor] ×1  (gravel/ambitious_first_timer)
> FTP Test Frequency flagged WARN in preview checks but the guide offers no explanation or mitigation to the athlete — a single Week 1 test with no retest scheduled across a 10-week plan may be insufficient; the guide should at minimum acknowledge this and suggest a mid-plan check-in if fitness changes noticeably.

### 24. [minor] ×1  (gravel/ambitious_first_timer)
> Taper Intensity flagged WARN in preview checks but the guide's taper section gives only generic guidance ('short, sharp efforts') with no specificity about what zones or durations are acceptable during taper — for a first-timer this ambiguity could lead to either over-training or complete inactivity in race week.

### 25. [minor] ×1  (gravel/ambitious_first_timer)
> Long ride duration reference ('2.9-4.8 hours') is a reasonable range for a ~4.7-hour target event, but the lower bound of 2.9 hours in Week 1 may be aggressive for someone whose base fitness is unknown; this could have been flagged but the guide presents it without any caveat about starting conservatively if current long ride is well below that range.
