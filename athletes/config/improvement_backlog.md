# Improvement backlog — 2026-08-21

**Quality 2.61** · avg coach 6.0/10 · contract pass 88% · load 10.38/plan · 8 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×1  (road/masters_returner)
> 'Category 5 to Category 1 Pathway' section is listed in the table of contents and presumably appears in the full document. This is entirely inapplicable — the athlete is a 63-year-old masters returner targeting a finish at a gran fondo-style KOM event, not a USA Cycling road racer seeking a license upgrade. This content is wrong for the discipline context, the persona, and the goal, and is the most embarrassing possible inclusion.

### 2. [critical] ×1  (road/masters_returner)
> Saturday is listed as an OFF day. For a 7h/week athlete doing a 93-mile mountain event, Saturday is the natural second long/medium ride day. Blocking it forces all volume onto Sunday, Thursday, and Friday — a structurally awkward and suboptimal layout that is hard to justify and likely to confuse or frustrate the athlete.

### 3. [critical] ×1  (mtb/weekend_warrior)
> Discipline mismatch: the athlete's discipline is 'mtb' but the plan's table of contents explicitly includes a 'Gravel Skills' section, and the overall template language skews gravel throughout. An MTB-specific plan should address MTB skills (technical descending, switchbacks, rock gardens, body position off-road) — not gravel cornering or gravel-specific content. This suggests the wrong plan template was rendered.

### 4. [critical] ×1  (mtb/weekend_warrior)
> Race name vs. athlete discipline conflict: the race is called 'Alentejo Gravel' and the plan correctly names it, but the athlete's registered discipline is MTB. The plan never reconciles this — it should either confirm the athlete is racing a gravel event on an MTB (and adjust content accordingly) or flag the mismatch. Silently inheriting gravel content because the race name contains the word 'Gravel' is a logic error that could mislead the athlete about equipment, skills, and tactics.

### 5. [critical] ×1  (gravel/time_crunched_parent)
> Section titled 'Road Race Strategy' and 'Category 5 to Category 1 Pathway' appear in the Table of Contents and (implied) in the body. This athlete is racing a GRAVEL event (El Tour de Tucson). Road race tactics and a USA Cycling cat upgrade pathway are completely wrong discipline content and would embarrass the business if sent.

### 6. [critical] ×1  (gravel/time_crunched_parent)
> Off-day list contradiction: the 'At a Glance' block lists 'Off days: Tuesday, Thursday, Monday' — that is THREE off days in a 7-day week, leaving only 4 training days, which is plausible BUT Monday appearing alongside Tuesday and Thursday is an unusual triplet that almost certainly reflects a copy-paste error (Monday is typically a training or off day, not listed alongside the two mid-week off days). More critically, listing Monday as an off day conflicts with standard Time-Crunched scheduling where Monday is often an easy/recovery ride; if wrong it will confuse the athlete immediately when they open the calendar.

### 7. [critical] ×1  (mtb/ambitious_first_timer)
> Discipline mismatch: the athlete is an MTB rider but the entire plan — title, skills section header ('Gravel Skills'), equipment checklist language ('gravel or similar'), and event-specific coaching — is framed around a gravel race. The race 'Gravel Revival' happens to be the target event, but the athlete's chosen discipline is MTB. The plan must either (a) be re-labelled as a gravel plan if that is intentional, or (b) replace gravel-specific content (gravel cornering, tire/surface notes) with MTB-appropriate skills and equipment guidance. Sending a gravel plan to an MTB athlete is confusing and undermines credibility.

### 8. [critical] ×1  (mtb/ambitious_first_timer)
> Per-Day Duration Caps check returned FAIL in the automated preview and is unresolved. At 10 h/week over 6 training days, some sessions likely exceed safe single-day caps for a first-timer. The guide text references long rides of 3.4–5.8 hours, which at the upper end would be an enormous single day for a rider with 1 year of experience. This must be audited and capped before sending.

### 9. [major] ×2  (mtb/ambitious_first_timer, mtb/weekend_warrior)
> The FTP Test Frequency check returned WARN in the preview checks, meaning there may be an FTP retest scheduled too soon or too infrequently for a 9-week plan — but the guide text says 'The test result sets ALL your training zones for the next 6 weeks' which is inconsistent with a 9-week plan that presumably has at least one mid-plan retest. This internal contradiction needs resolution before sending.

### 10. [major] ×1  (road/masters_returner)
> 'Road Race Strategy' section is listed in the contents. The Taiwan KOM Challenge is a hillclimb/gran fondo format (Yilan to Wuling Pass), not a criterium or road race with tactical positioning, drafting, or sprint finishes. Road race strategy content is discipline-mismatched for this event type and goal (finish).

### 11. [major] ×1  (road/masters_returner)
> Zone Distribution check flagged WARN but the guide text contains no explanation or acknowledgment of the deviation. A paying athlete deserves to understand if their zone balance is unusual or intentional — silence on a known flag is a coaching credibility gap.

### 12. [major] ×1  (road/masters_returner)
> FTP Test Frequency flagged WARN and is similarly unaddressed in the guide. For a 9-week plan the testing cadence should be explicitly justified, especially for a masters athlete where unnecessary maximal efforts carry more recovery cost.

### 13. [major] ×1  (mtb/weekend_warrior)
> The Weekly Structure section states the long ride peaks at '2.1-3.5 hours' — but for a 7 h/week athlete targeting an ~7.35 h race, a long ride cap of 3.5 h is on the low end and should be explained or justified; more importantly the range is oddly wide (2.1 to 3.5 h spans a 67% difference) and reads like a template placeholder that wasn't tightened to this athlete's specific plan data.

### 14. [major] ×1  (gravel/time_crunched_parent)
> Equipment checklist lists 'road bike, in good working order' as the mandatory bike under MANDATORY. This is a gravel race — the checklist should specify a gravel bike (or at minimum 'gravel/road bike suitable for the course'). Sending a 102-mile gravel event athlete a plan that tells them to bring a road bike is a meaningful error.

### 15. [major] ×1  (gravel/time_crunched_parent)
> The athlete's stated goal is 'podium' — a highly specific, aggressive objective. The plan's goal/blindspot section reduces this to simply 'Compete' and never addresses podium-specific demands (race tactics, positioning, finishing kick, gravel-specific pack dynamics). A paying customer targeting the podium deserves to see that goal reflected.

### 16. [major] ×1  (gravel/time_crunched_parent)
> Header avatar date mismatch: the document header reads 'Avatar 202608215' but the plan_start_date is 2026-08-24 — the avatar ID embeds '20260821' (August 21), a 3-day discrepancy. This looks like a stale ID generated before the start date was finalised. It won't break the plan but is visibly inconsistent and looks unprofessional.

### 17. [major] ×1  (gravel/time_crunched_parent)
> TSS Progression and Taper Intensity both flagged WARN by the automated preview checks, yet the guide text contains no compensating coach's note explaining the deviation. Sending a plan with known automated warnings without any acknowledgement leaves the coach exposed if the athlete notices irregular load jumps or an insufficiently reduced taper week.

### 18. [major] ×1  (mtb/ambitious_first_timer)
> Experience/persona contradiction: the plan simultaneously states '1 years of cycling experience at Intermediate level' in the methodology rationale but the persona is 'ambitious_first_timer.' A first-timer is not an intermediate — this inconsistency in the generated copy will confuse the athlete and erode trust.

### 19. [minor] ×1  (road/masters_returner)
> The long ride duration range cited in the Weekly Structure section ('2.5–4.2 hours') is oddly precise and the upper end (4.2h) is unusual phrasing — likely a raw computed value that should be rounded to '4–4.5 hours' for readability and coaching authenticity.

### 20. [minor] ×1  (road/masters_returner)
> Strength training is listed as 'Included (minimal)' in the at-a-glance block but the truncated text gives no indication of what the strength sessions actually involve beyond generic single-leg/core references. For a 63-year-old masters returner, even brief specificity here (e.g., frequency per week, when in the week relative to bike sessions) is expected.

### 21. [minor] ×1  (gravel/ambitious_first_timer)
> TSS Progression flagged WARN by the automated gate — the guide text does not expose TSS numbers to the athlete, so this cannot be verified from the truncated text. Needs calendar/data-layer check before send to confirm no spike week exceeds ~10% above the prior build week.

### 22. [minor] ×1  (gravel/ambitious_first_timer)
> Taper Intensity flagged WARN — the guide correctly describes 'short, sharp efforts' in the taper narrative, but the actual taper interval prescriptions are in the calendar (not shown). The calendar should be spot-checked to confirm intensity is not inadvertently stripped to Z1/Z2 only, which would conflict with the guide's own taper guidance.

### 23. [minor] ×1  (gravel/ambitious_first_timer)
> FTP Test Frequency flagged WARN — with no known FTP and only a Week 1 field test mentioned, there is no second re-test called out in the visible guide text. For an 8-week plan this is borderline acceptable, but a brief mention of a mid-plan or post-build check-in test (even optional) would strengthen the plan and resolve the flag.

### 24. [minor] ×1  (gravel/ambitious_first_timer)
> Nutrition section is truncated mid-sentence ('1-2g ca...') in the supplied text — this must be confirmed complete in the actual deliverable PDF; an incomplete nutrition section reaching the athlete would be embarrassing and potentially harmful for race-day fueling.

### 25. [minor] ×1  (mtb/weekend_warrior)
> The post-ride nutrition guidance is cut off mid-sentence ('0.3-0.4g protein/kg + 1.0-1.2g carbs/kg' followed by a line break and no completion). Even if this is a truncation artifact in the QA preview, the final delivered document must not have an incomplete sentence in a customer-facing section.
