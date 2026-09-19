# Improvement backlog — 2026-09-19

**Quality -0.91** · avg coach 5.75/10 · contract pass 62% · load 17.25/plan · 16 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×2  (gravel/masters_returner, road/time_crunched_parent)
> Zone Distribution check is flagged FAIL in the preview_checks but the guide text shows no sign of correction or acknowledgment. The G Spot methodology promises ~65% Z1-2 / remainder in GS-Threshold-VO2, but if the actual weekly distribution violates this, the plan's core methodology claim is broken and unverified.

### 2. [critical] ×1  (road/veteran_podium_chaser)
> "Category 5 to Category 1 Pathway" section is listed in the Table of Contents and appears in the guide for an athlete whose persona is 'veteran_podium_chaser' with 16 years of riding. This content is completely wrong for this athlete — it reads as a beginner racing progression guide and is deeply mismatched to someone chasing a podium at an A-priority 102-mile road event. It will undermine trust immediately.

### 3. [critical] ×1  (road/veteran_podium_chaser)
> The preview check flags 'Zone Distribution: FAIL' and the guide never acknowledges or corrects this. Sending a plan with a known failed zone distribution check without explanation means the athlete may be handed a workout schedule whose hard/easy split violates the stated Polarized 80/20 methodology.

### 4. [critical] ×1  (gravel/ambitious_first_timer)
> Wrong discipline content — 'Road Race Strategy' and 'Category 5 to Category 1 Pathway' sections appear in the table of contents for a GRAVEL event. Gran fondos are not mass-start road races with upgrade categories; Cat 5–Cat 1 pathway content is UCI road racing doctrine that is irrelevant and confusing to a gravel first-timer. This must be replaced with gravel-specific race execution guidance (starting position, terrain management, aid-station strategy, etc.).

### 5. [critical] ×1  (gravel/ambitious_first_timer)
> 'Road Skills' section listed in the TOC is ambiguous at best and wrong at worst for a gravel event — if it contains road-specific cornering or criterium-style skills content it is discipline-mismatched. Needs to be verified and replaced with gravel-specific skills (loose surface braking, tyre pressure, technical descending on mixed terrain).

### 6. [critical] ×1  (road/masters_returner)
> 'Category 5 to Category 1 Pathway' section included in the table of contents and (implied) body: this is a USA Cycling road racing category progression concept that is completely irrelevant to a masters athlete whose only goal is to finish a gran fondo. It signals the wrong athlete persona, could confuse or mislead the customer, and is embarrassing content that should not be in this plan.

### 7. [critical] ×1  (gravel/masters_returner)
> 'Category 5 to Category 1 Pathway' section is present in a gravel gran fondo plan. UCI category pathway is a road-racing concept entirely irrelevant to a gran fondo finisher goal — this is wrong-discipline content that would confuse and alarm the athlete.

### 8. [critical] ×1  (gravel/masters_returner)
> 'Road Race Strategy' section content is wrong-discipline material. This is a gravel gran fondo, not a road race. Strategy guidance should cover gravel-specific concerns (terrain management, mechanical self-sufficiency, pacing on mixed surfaces).

### 9. [critical] ×1  (gravel/veteran_podium_chaser)
> The guide contains a 'Road Race Strategy' section and a 'Category 5 to Category 1 Pathway' section. This athlete is racing gravel (L'Étape Ciudad de México), not a road criterium or road race. Cat 5–1 is a USA Cycling road licensing classification that is completely irrelevant to a gravel event. This is wrong-discipline content that would embarrass the business and confuse the athlete.

### 10. [critical] ×1  (gravel/veteran_podium_chaser)
> The 'Road Skills' section (visible in the table of contents) likely contains road-specific cornering, peloton, and draft tactics rather than gravel-specific skills (loose surface cornering, technical descending, singletrack, self-sufficiency). Sending road skills coaching to a gravel racer targeting a podium is a material coaching error.

### 11. [critical] ×1  (gravel/ambitious_first_timer)
> Table of Contents lists 'Road Race Strategy' and 'Category 5 to Category 1 Pathway' sections — these are road racing / USA Cycling category upgrade concepts that are completely irrelevant and inappropriate for a gravel gran fondo athlete. Sending this to a gravel rider is embarrassing and undermines trust in the entire plan.

### 12. [critical] ×1  (gravel/ambitious_first_timer)
> 'Road Skills' section in the ToC may be acceptable, but paired with 'Road Race Strategy' it strongly implies templated road-race boilerplate was injected. Gravel-specific skills (loose surface cornering, descending on gravel, navigation, mechanical self-sufficiency) are what this athlete needs, not road criterium or road race tactics.

### 13. [critical] ×1  (gravel/masters_returner)
> Table of Contents and body include 'Road Race Strategy' and 'Category 5 to Category 1 Pathway' sections — these are road-racing-specific content completely inappropriate for a gravel event. A gravel athlete targeting a 99-mile finish has zero use for a cat-upgrade pathway, and sending this is professionally embarrassing.

### 14. [critical] ×1  (road/time_crunched_parent)
> Weight is listed as 158 lbs / 71.7 kg, but the athlete never provided weight in the JSON profile — this number has been fabricated. Sending a plan with an invented body-weight to a paying customer is a trust-destroying error, especially because post-ride protein/carb targets in the Recovery section are calculated per-kg off this made-up figure.

### 15. [critical] ×1  (road/time_crunched_parent)
> Height is listed as 5'8" — again, not present anywhere in the athlete JSON. Invented demographic data must not appear in a customer-facing document.

### 16. [critical] ×1  (road/time_crunched_parent)
> The guide includes a 'Category 5 to Category 1 Pathway' section (visible in the Table of Contents). This athlete's goal is simply to finish a 102-mile gran fondo; she has no stated racing category ambition. Cat 5→Cat 1 progression content is irrelevant, potentially confusing, and makes the plan look like a generic template dump rather than a custom document.

### 17. [major] ×2  (gravel/ambitious_first_timer, gravel/masters_returner)
> Equipment checklist under MANDATORY lists 'road bike, in good working order' — for a gravel event the checklist should specify a gravel bike (or at minimum a road bike with wider/gravel-appropriate tyres), and tyre pressure/plug guidance should be elevated to mandatory given the surface demands of a gravel gran fondo.

### 18. [major] ×2  (gravel/ambitious_first_timer, road/masters_returner)
> TSS Progression and Taper Intensity both flagged WARN by the automated preview checks, yet no coach note or caveat addresses these in the guide text. Sending a plan with known unresolved structural warnings — especially a taper intensity warning for a 62-year-old masters returner — is a real quality risk.

### 19. [major] ×1  (road/veteran_podium_chaser)
> The guide describes the athlete's experience level as 'Intermediate level' in the methodology rationale section ('16 years of cycling experience at Intermediate level'), which directly contradicts the persona ('veteran_podium_chaser') and the athlete's 16-year riding history. This is a data-population error that will erode credibility.

### 20. [major] ×1  (road/veteran_podium_chaser)
> The FTP test formula note says 'The test result sets ALL your training zones for the next 6 weeks' — but this is a 9-week plan and tests may fall at various points. '6 weeks' is a generic placeholder that was not updated to match this plan's actual length and test schedule.

### 21. [major] ×1  (gravel/ambitious_first_timer)
> Athlete profile shows '1 Years Riding' and 'Intermediate level' in the same breath — the persona is 'ambitious_first_timer' which implies novice/beginner experience. Labelling a first-timer as Intermediate is contradictory and will erode trust if the athlete notices it.

### 22. [major] ×1  (gravel/ambitious_first_timer)
> The preview check flagged 'Taper Intensity: WARN' and 'FTP Test Frequency: WARN' but neither warning is acknowledged or explained anywhere in the guide text. Coach QA cannot resolve whether these are acceptable edge-cases or real problems without seeing the calendar; the guide should at minimum address the taper intensity situation so the athlete isn't blindsided.

### 23. [major] ×1  (road/masters_returner)
> Zone 1 row in the zone chart is missing the % FTP and % LTHR columns (both blank), while every other zone has them. This is inconsistent and will confuse an athlete trying to set up a head unit or Zwift profile.

### 24. [minor] ×2  (road/masters_returner, road/time_crunched_parent)
> Long ride duration range cited as '2.1–3.5 hours' for a 6 h/week athlete targeting a ~5.75 h race. The upper bound of 3.5 h is reasonable but the lower bound of 2.1 h in the same sentence undersells the range and may cause athletes to under-extend early long rides; the framing should be clearer about how this range evolves across phases.

### 25. [major] ×1  (gravel/masters_returner)
> Off days are listed as 'Friday, Thursday, Tuesday' — three off days totals only 4 riding days, which is consistent with 6 h/week, but presenting three off days in a comma-separated list without clear ordering reads as disorganised and mildly confusing. More importantly, the ordering (Friday, Thursday, Tuesday) is non-chronological and will confuse athletes trying to map it to a weekly calendar.
