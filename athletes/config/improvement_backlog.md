# Improvement backlog — 2026-09-23

**Quality 1.88** · avg coach 6.38/10 · contract pass 75% · load 12.5/plan · 8 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×2  (road/masters_returner, road/veteran_podium_chaser)
> 'Category 5 to Category 1 Pathway' section appears in the table of contents for a plan explicitly targeting a podium for a 43-year-old veteran with 370W FTP and 17 years of experience. This content is for a beginner road racer, not this athlete. It is embarrassing and will erode trust immediately.

### 2. [critical] ×1  (gravel/masters_returner)
> Section header 'Road Race Strategy' appears in the table of contents (and presumably the section body) for a GRAVEL event. This is the wrong discipline label — it should be 'Gravel Race Strategy' or 'Gran Fondo Strategy'. Sending a road-race strategy section to a gravel athlete is both embarrassing and potentially gives tactically wrong advice (e.g., road peloton positioning vs. gravel self-sufficiency, drafting norms, etc.).

### 3. [critical] ×1  (gravel/veteran_podium_chaser)
> Wrong-discipline content: the guide includes a 'Road Race Strategy' section (visible in the table of contents). This athlete is racing a GRAVEL gran fondo, not a road criterium or road race. Road-race tactics (e.g., sitting in a peloton, attacking on climbs in a massed-start road context) differ materially from gravel gran fondo pacing strategy. Sending road-race strategy to a gravel athlete is embarrassing and undermines trust.

### 4. [critical] ×1  (gravel/veteran_podium_chaser)
> Zone Distribution preview check is flagged FAIL. The guide goes out anyway with a known zone-distribution error — the polarized 80/20 split is likely miscalculated or misapplied in the weekly calendar. This is the core methodological promise of the plan and it is broken.

### 5. [critical] ×1  (gravel/masters_returner)
> The guide contains a 'Road Race Strategy' section in the Table of Contents. This athlete is racing a gravel gran fondo, not a road race. Road race strategy content (e.g., attacking breaks, sitting in a peloton, sprint positioning) is discipline-wrong and would confuse or mislead the athlete. It must be replaced with gravel/gran fondo pacing strategy.

### 6. [critical] ×1  (mtb/ambitious_first_timer)
> Discipline mismatch — section headers confirm 'Road Skills' and 'Road Race Strategy' sections in an MTB plan. The athlete signed up for MTB; road cornering, road bunch-riding tactics, and road-specific skills content is wrong content for this discipline and would embarrass the business.

### 7. [critical] ×1  (mtb/ambitious_first_timer)
> Experience level contradiction — the plan body states '1 years of cycling experience at Intermediate level,' but the persona is explicitly 'ambitious_first_timer.' A first-timer is a beginner, not Intermediate. This affects how the athlete perceives their own profile and whether the methodology justification holds.

### 8. [critical] ×1  (road/masters_returner)
> Weekly Volume check flagged FAIL in the preview and was never resolved. If the generated weekly volume is wrong, every TSS, load, and phase-progression number downstream may be miscalibrated for a 7h/week athlete. Sending a plan with a known-failed volume check is not acceptable.

### 9. [major] ×1  (road/veteran_podium_chaser)
> The guide explicitly calls the athlete 'Intermediate level' despite 13 years of riding experience and a veteran podium-chaser persona. This directly contradicts the athlete's profile and will undermine trust in the entire document — a 13-year racer chasing a podium is not an intermediate.

### 10. [major] ×1  (road/veteran_podium_chaser)
> The race countdown in the guide states '59 days from today,' which implies a generation date of approximately September 23, 2026, but the plan_start_date is September 28, 2026. The countdown figure is live-calculated and will be wrong (or misleading) by the time the athlete reads it on or after the start date — this should either be removed or expressed as a fixed date reference, not a dynamic day count baked into static text.

### 11. [major] ×1  (road/veteran_podium_chaser)
> The plan describes the athlete as 'Intermediate level' in the methodology rationale ('17 years of cycling experience at Intermediate level'). A 43-year-old with 17 years of riding, 370W FTP, 13 h/week, and a podium goal is clearly an advanced/elite amateur. Calling him Intermediate is factually wrong and undermines confidence in the plan's customization.

### 12. [major] ×1  (road/veteran_podium_chaser)
> Three preview checks (Weekly Volume, TSS Progression, Taper Intensity) returned WARN but the guide text provides no acknowledgment, explanation, or athlete-facing context for these warnings. A coach would address flagged items — e.g., why volume is set where it is, or how the taper was structured — rather than silently carry unresolved flags into a paying customer's document.

### 13. [major] ×1  (gravel/masters_returner)
> Weekly Volume and TSS Progression both flagged WARN by the automated preview but are not addressed or explained anywhere in the visible guide text. If volume or TSS ramps are outside acceptable bounds for a 61-year-old masters returner, this needs to be corrected in the calendar before sending — these flags should not be dismissed without resolution.

### 14. [major] ×1  (gravel/masters_returner)
> The TOC lists 'Road Skills' as a standalone section. For a gravel gran fondo the relevant skills are gravel-specific (loose surface cornering, tyre pressure management, rough terrain descending, self-sufficiency). If the section body contains road-crit or criterium cornering content it is wrong discipline content; even if generic, the label should be 'Gravel Skills'.

### 15. [major] ×1  (gravel/veteran_podium_chaser)
> Off days listed as 'Saturday, Friday' — ordering is non-chronological (Friday comes before Saturday in the week). More importantly, having BOTH Friday and Saturday off means the long Sunday ride is sandwiched between two rest days, which is acceptable, but the plan should confirm the athlete's availability data actually specifies these two days; stating them out of weekly order reads as a generation artifact.

### 16. [major] ×1  (gravel/veteran_podium_chaser)
> The 'Road Skills' section in the table of contents is ambiguous for a gravel event — if this covers road cornering, braking lines, or peloton positioning rather than gravel-specific skills (loose surface cornering, technical descending, tire pressure management, nutrition on rough terrain), it is wrong-discipline content.

### 17. [major] ×1  (road/time_crunched_parent)
> The guide includes a 'Road Race Strategy' section (visible in the Table of Contents). Gran Fondo Eilat is a gran fondo, not a road race — these are fundamentally different events. Tactics like attacking, sitting in a peloton, and sprint finishes are irrelevant and potentially misleading for an athlete whose goal is simply to finish an 85-mile gran fondo. This section must be replaced with gran-fondo-specific pacing and group-riding guidance.

### 18. [major] ×1  (gravel/masters_returner)
> Three automated preview checks flagged WARN — Weekly Volume, TSS Progression, and Taper Intensity — and none of them are addressed or acknowledged anywhere in the visible guide text. At minimum, Taper Intensity WARN is a red flag for a masters athlete: if taper efforts are too intense, freshness on race day is compromised. These should be resolved in the calendar or, if intentional, explained in the guide.

### 19. [major] ×1  (gravel/masters_returner)
> Long ride duration range stated as '3.8–6.2 hours' in the Weekly Structure section. For a 9 h/week athlete with a ~5.75 h estimated race time and a finish goal, a 6.2-hour long ride cap is plausible only in peak week — but presenting it as a general range without context implies the athlete might see 6+ hour rides early in the plan, which would be inappropriate for a masters returner and contradicts the Base phase guidance to build gradually.

### 20. [major] ×1  (mtb/ambitious_first_timer)
> Equipment checklist specifies a 'road bike, in good working order' as the mandatory training bike for an MTB plan. The athlete needs an MTB-specific checklist (dropper post, tubeless setup, MTB helmet, pads if applicable, MTB shoes/pedals).

### 21. [major] ×1  (mtb/ambitious_first_timer)
> Gran Fondo Guadeloupe is listed as an MTB discipline in the plan facts, yet the event is a road gran fondo (78 miles, road location). If the event is actually a road gran fondo, the discipline tag in the plan JSON is wrong and all MTB-specific workout content (trail skills, MTB drills implied by the section structure) would be inappropriate. This inconsistency needs resolution before sending — either the event is road (fix discipline throughout) or it is genuinely MTB (fix the Road Skills/Road Race Strategy sections and equipment list).

### 22. [major] ×1  (road/masters_returner)
> Fueling section states 57g carbs/hour for a projected race duration of ~6.73 hours (plan_facts). At that duration, current sports-science guidance and event-specific demands support 80–90 g/hour for trained athletes who have gut-trained. 57 g/hour is low for a ~7-hour effort and may leave the athlete significantly under-fueled late in the race — a meaningful risk for a finish-goal masters athlete.

### 23. [major] ×1  (road/masters_returner)
> TSS Progression check is flagged WARN. For a masters returner (age 59, returning after a layoff), TSS ramp rate is especially sensitive. A WARN state that was not reviewed or annotated before send is a liability — either it needs to be confirmed acceptable or corrected.

### 24. [major] ×1  (road/masters_returner)
> The guide includes a 'Road Skills' section and a 'Road Race Strategy' section alongside the Category 5–1 pathway. Race strategy content appropriate for a criterium or road race (e.g., positioning, attacking, breakaway tactics) is irrelevant and potentially confusing for an athlete riding a mass-participation gran fondo with a finish goal. Content should be replaced with gran fondo–specific strategy (pacing, aid stations, group dynamics on a 99-mile course).

### 25. [minor] ×1  (road/veteran_podium_chaser)
> TSS Progression and Taper Intensity both flagged WARN in preview checks. The guide text does not acknowledge or address these flags in any way (e.g., no note that TSS ramps may be irregular or that taper intensity was adjusted). A coach would at minimum be aware these exist — the silence leaves a latent quality risk.
