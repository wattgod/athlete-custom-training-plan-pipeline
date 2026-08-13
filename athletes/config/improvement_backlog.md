# Improvement backlog — 2026-08-13

**Quality 1.25** · avg coach 5.75/10 · contract pass 75% · load 12.5/plan · 9 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×2  (gravel/time_crunched_parent, mtb/weekend_warrior)
> Long ride duration stated as 'peak of 1.5 hours' — for an 81-mile gravel race with an estimated ~5.3-hour finish time, a 1.5-hour long ride is grossly inadequate and contradicts the plan's own disclaimer that urges 3–4 hour rides. If the plan calendar actually caps long rides at 1.5 hours it is race-preparation malpractice for an A-priority 81-mile event; if the 1.5-hour figure is a Week 1 starting point only, the text is ambiguous and will confuse athletes.

### 2. [critical] ×1  (road/veteran_podium_chaser)
> Weekly Volume preview check is flagged FAIL — the plan must not be sent until the volume issue is identified and corrected, as this is the core quantitative backbone of the plan.

### 3. [critical] ×1  (road/veteran_podium_chaser)
> 'Category 5 to Category 1 Pathway' appears in the table of contents and presumably in the body. This is a USA Cycling road racing licence upgrade pathway — completely irrelevant and potentially confusing for a gran fondo athlete targeting a podium finish. It has no place in this plan and is likely boilerplate bleed-through from a different template.

### 4. [critical] ×1  (mtb/weekend_warrior)
> Discipline mismatch: the race 'Wild Gravel' is flagged in the plan JSON as discipline='mtb', yet the guide is written throughout as a gravel plan. The section heading 'Gravel Skills' and all gravel-specific framing should reference MTB skills (e.g. technical singletrack, climbing traction, descending body position) — not gravel cornering or gravel-specific cues. Sending an MTB athlete a gravel guide is an embarrassing and trust-destroying error.

### 5. [critical] ×1  (mtb/ambitious_first_timer)
> Discipline mismatch — the Contents list includes a 'Gravel Skills' section for an MTB athlete racing Marys Mayhem. This is a mountain-bike event; gravel-specific skills content (likely covering gravel cornering, loose-surface descending technique framed around gravel riding) is wrong for this discipline and will confuse or mislead the athlete.

### 6. [critical] ×1  (gravel/time_crunched_parent)
> Table of contents and implied content includes 'Road Race Strategy' and 'Category 5 to Category 1 Pathway' — this is a GRAVEL event, not a road criterium or road race. Cat 5–1 licensing categories are USA Cycling road/track designations that are completely irrelevant to El Tour de Tucson gravel. Sending this to a gravel athlete is embarrassing and undermines coach credibility.

### 7. [critical] ×1  (gravel/time_crunched_parent)
> 'Road Skills' section heading appears in the TOC without gravel-specific qualification. For a 102-mile gravel event, this section must cover gravel-specific skills (loose surface cornering, tire pressure management, washboard/technical descending) — not road racing pack skills. As written it reads as copy-pasted from a road template.

### 8. [critical] ×1  (gravel/time_crunched_parent)
> Road-race content included for a gravel athlete: the table of contents lists 'Road Race Strategy' and 'Category 5 to Category 1 Pathway' — these sections are discipline-wrong and embarrassing for a gravel event. A gravel racer has no use for a road cat-upgrade pathway and it signals the template was not properly filtered.

### 9. [critical] ×1  (gravel/time_crunched_parent)
> Long-ride ceiling of 1.5–2.3 hours is dangerously low for a 44-mile gravel race. At a realistic gravel pace (12–14 mph on mixed terrain) this athlete will be on course for ~3–3.5 hours. The plan explicitly acknowledges the gap ('long rides are shorter than ideal') but then does nothing to correct it, capping rides at 2.3 hours. No single ride approaches race duration, virtually guaranteeing durability problems on race day.

### 10. [major] ×2  (gravel/time_crunched_parent, road/veteran_podium_chaser)
> Long ride duration range cited as '2.8-4.7 hours' in the Weekly Structure section but the race is estimated at ~4.1 hours (per fueling data). The upper bound of 4.7h is acceptable, but the range should be verified against the weekly TSS/volume figures — especially since the Volume check already failed.

### 11. [major] ×1  (gravel/time_crunched_parent)
> Race countdown stated as '93 days from today' — this is a hard-coded or stale calculation. The plan start date is 2026-08-24 and race date is 2026-11-14, which is 82 days. The figure '93 days' does not match any sensible reference point in the plan data and will immediately erode athlete trust if they count on a calendar.

### 12. [major] ×1  (gravel/time_crunched_parent)
> The plan repeatedly describes the athlete's experience level as 'Intermediate' and states '12 years of cycling experience' — but the athlete JSON contains no experience field. This data was either fabricated by the generator or pulled from a stale/wrong profile. If it is wrong, every methodology justification that cites 'Intermediate level' is built on a false premise.

### 13. [major] ×1  (road/masters_returner)
> A 'Category 5 to Category 1 Pathway' section appears in the table of contents and presumably in the body. This athlete's goal is simply to FINISH a mass-participation Gran Fondo (L'Étape), not to pursue USA Cycling category upgrades. This content is wrong for the persona, the event type, and the stated goal — it will confuse or mislead the athlete and looks like boilerplate pulled from a racing-category plan.

### 14. [major] ×1  (road/veteran_podium_chaser)
> The guide labels the athlete as 'Intermediate level' despite 14 years of cycling experience. A 14-year veteran, especially one with a 345W FTP chasing a podium, should be classified as Advanced or Expert. This mislabelling could undermine athlete confidence in the plan's calibration.

### 15. [major] ×1  (gravel/time_crunched_parent)
> Zone Distribution preview check is a hard FAIL. The guide claims '~70% of riding stays genuinely easy' (Zone 1-2) but the automated gate flagged this as failing — meaning the actual scheduled workouts likely skew too heavily into Zone 3+ for a Time-Crunched plan. This is a methodological contradiction between the stated philosophy and the delivered calendar, and it is the single most important thing to fix before sending.

### 16. [major] ×1  (gravel/time_crunched_parent)
> Long-ride duration cap is internally inconsistent. The 'Weekly Structure' section states the long-ride peak duration is '1.5–2.5 hours,' but the immediately following callout urges the athlete to target '3–4 hour' rides for race-day durability. For a 6 h/week athlete with a 62-mile gravel race, the 3–4 h recommendation is correct coaching — but the 1.5–2.5 h figure in the session-type description is wrong and contradicts both the advice below it and the 'Long Ride vs Race Duration: PASS' preview check. One of these numbers needs to be removed or reconciled.

### 17. [major] ×1  (mtb/weekend_warrior)
> Race name is 'Wild Gravel' but the plan JSON discipline is 'mtb'. Either the race has been mis-categorised in the system (it may genuinely be a gravel event), or the discipline field is wrong. This ambiguity must be resolved before sending — if the race is actually gravel, the discipline field is wrong and the plan is fine on that axis; if it is MTB, the content must change. The QA system cannot send until this is confirmed.

### 18. [major] ×1  (mtb/weekend_warrior)
> The 'Gravel Skills' chapter heading appears in the table of contents for an athlete whose discipline is MTB. Regardless of race-name ambiguity, a skills section must match the actual surface and bike type the athlete will race on.

### 19. [major] ×1  (mtb/ambitious_first_timer)
> Equipment checklist says 'Bike — gravel or similar' for an MTB race. Marys Mayhem is an off-road MTB event in Mudgee. The athlete needs a mountain bike, not a gravel bike. Recommending a gravel bike as the primary equipment option for a 65-mile MTB race is misleading and potentially dangerous.

### 20. [major] ×1  (mtb/ambitious_first_timer)
> Athlete weight is listed as '147 lbs (66.7 kg)' but the athlete data JSON contains no weight field — this figure appears to have been fabricated or pulled from a default template. Sending a made-up weight to a paying customer is unprofessional and undermines trust in the entire personalisation claim.

### 21. [major] ×1  (gravel/time_crunched_parent)
> Fueling section is incomplete or missing from the visible guide text. The plan JSON specifies 58 g carbs/hour for a 6.6-hour race effort — this specific, athlete-calculated number must appear in the Nutrition Strategy section. There is no mention of it in the truncated guide, and for a 102-mile gravel event where fueling execution is a primary finish risk, this omission is significant.

### 22. [major] ×1  (gravel/time_crunched_parent)
> Fueling section specifies a 2.0-hour duration target (59 g carbs/h × 2 h = ~118 g total), but the race will likely last 3–3.5 hours for this athlete. The nutrition strategy and race-day fueling plan built on 2.0 hours will leave her significantly under-fueled in the back half of the event.

### 23. [major] ×1  (gravel/time_crunched_parent)
> Zone 2 power range is missing from the zone chart as shown — the '56-75% FTP' percentage column is present but the absolute watt range (83–112 W) appears in the table yet the LTHR column entry is incomplete ('69-83% LTHR' shown, which is plausible, but Zone 1 has no % FTP or LTHR listed at all), making the chart inconsistent and harder for an athlete to use confidently.

### 24. [minor] ×1  (gravel/time_crunched_parent)
> The 'YOUR BIGGEST OPPORTUNITY' box recommends '3–4 hour rides' but the plan's own long-ride cap (per-day duration caps check: PASS) and the 5h/week budget make a 3–4 hour standalone ride essentially impossible without blowing the entire weekly volume. The advice is aspirational but practically incoherent within the plan's own constraints — a real coach would frame this as an optional monthly override, not a general recommendation.

### 25. [minor] ×1  (gravel/time_crunched_parent)
> Post-ride nutrition guidance ('0.3–0.4g protein/kg + 1.0–1.2g carbs/kg') is labeled 'General guidance, not your target' — but the athlete has a computed fueling profile (66g carbs/hr, 5.3h duration). The generic disclaimer should instead reference the athlete's specific fueling numbers from the Nutrition Strategy section, or at minimum cross-reference it; as written it feels like boilerplate that escaped personalisation.
