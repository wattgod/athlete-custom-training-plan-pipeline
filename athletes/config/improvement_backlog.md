# Improvement backlog — 2026-07-16

**Quality 2.14** · avg coach 6.0/10 · contract pass 62% · load 10.25/plan · 8 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×1  (mtb/ambitious_first_timer)
> Discipline mismatch: the JSON declares discipline = 'mtb', but the plan prominently includes a 'Gravel Skills' section (visible in the Table of Contents) and frames the event as a gravel event throughout. Gravel-specific cornering, terrain, and skills content is wrong for an MTB athlete preparing for this event on an MTB.

### 2. [critical] ×1  (mtb/ambitious_first_timer)
> FTP value (133 W) has been copied into the 'Weight' field in the athlete profile, displaying '133 lbs (60.3 kg)' — the athlete's actual weight is unknown and was never collected. Stating a fabricated weight to a paying customer is factually wrong and potentially embarrassing. The kg conversion (60.3 kg) is internally consistent with 133 lbs, confirming this is a data-field substitution bug, not a coincidence.

### 3. [critical] ×1  (mtb/ambitious_first_timer)
> The automated Weekly Volume check returned WARN and was never resolved before sending. The guide text claims 11 h/week is appropriate for this methodology and athlete, but the underlying volume concern is unaddressed — the coach cannot sign off on a plan with an unresolved volume warning.

### 4. [critical] ×1  (gravel/ambitious_first_timer)
> Zone Distribution check FAILED in preview. The guide text does not acknowledge or address this — it is sent to the athlete as-is with a known zone distribution problem. If Zone 3 (tempo) volume is over-prescribed relative to a pyramidal model, the methodology claim ('roughly 75% genuinely easy') may be false, which is directly contradicted by the guide's own text and undermines the entire methodology section.

### 5. [critical] ×1  (mtb/ambitious_first_timer)
> Wrong discipline content: The plan includes a 'Gravel Skills' section (visible in the table of contents) for an athlete whose discipline is MTB, not gravel. Gravel-specific skills coaching (e.g., loose-over-hard surface cornering, gravel bike handling) is the wrong content for an MTB rider. This is a discipline mismatch that will confuse and mislead the athlete.

### 6. [critical] ×1  (mtb/ambitious_first_timer)
> Wrong race name used throughout: The race in the verified database is 'Forbidden Gravel' — but the athlete's discipline is MTB. Either the race has been mis-categorised as MTB in the system, or the plan was generated for the wrong athlete profile. Regardless, the guide repeatedly labels this a gravel event while the persona/discipline field says MTB. This contradiction must be resolved before sending — if the race truly is a gravel event, the discipline field is wrong and the entire methodology and skills content needs review; if the athlete is an MTB rider doing a gravel race, that nuance must be explicitly addressed.

### 7. [critical] ×1  (mtb/ambitious_first_timer)
> Post-ride recovery window stated in miles instead of minutes: The guide reads '35g protein + 87-104g carbs within 30 mi[nutes?]' — the text is truncated but the unit shown is 'mi', which reads as miles. This is a nonsensical unit for a nutrition timing cue and will confuse or embarrass. Must read 'within 30 minutes.'

### 8. [critical] ×1  (gravel/ambitious_first_timer)
> Zone Distribution check FAILED (per preview_checks). The guide text never acknowledges this or explains a corrective adjustment. Sending a plan with a known-failed zone distribution check means the athlete will be training in the wrong zones — the core sin the guide itself warns against at length.

### 9. [major] ×1  (mtb/ambitious_first_timer)
> Race name is 'Trough Creek Gravel Grinder' but the discipline is MTB. The guide never clarifies whether the athlete is riding this event on a mountain bike (which the discipline field implies) or a gravel bike. Equipment checklist and skills sections need to match the actual bike being ridden.

### 10. [major] ×1  (mtb/ambitious_first_timer)
> Long ride peak duration is cited as '2.2-3.7 hours' in the Weekly Structure section. For a 50-mile gravel/MTB event with an estimated 4.2-hour finish time (per fueling data), the top end of the long ride range (3.7 h) covers only ~88% of race duration — borderline acceptable — but the low end (2.2 h) is suspiciously short for a peak long ride and may reflect the unresolved volume WARN.

### 11. [major] ×1  (gravel/ambitious_first_timer)
> Athlete weight (175 lbs / 79.4 kg) is displayed in the profile section, but no weight field exists in the athlete JSON provided. This number appears fabricated or carried over from a template/different athlete. If it is wrong, the recovery nutrition targets (protein and carb quantities explicitly tied to '79kg body weight') are also wrong.

### 12. [major] ×1  (gravel/ambitious_first_timer)
> TSS Progression check returned WARN. The guide contains no mention of TSS or load management for the athlete, meaning there is no transparency about the progression issue. A WARN-level flag should either be resolved in the plan or surfaced to the athlete with guidance.

### 13. [major] ×1  (road/weekend_warrior)
> Zone Distribution preview check explicitly FAILED, yet nowhere in the visible guide text is there any explanation or resolution. The guide claims 'roughly 70%' of riding stays easy (Zone 1-2), but if the automated check failed this distribution is not actually being delivered in the calendar. Sending a plan with a known failed check — especially one affecting the fundamental polarised/easy-hard split of a Time-Crunched methodology — is a coaching credibility risk.

### 14. [major] ×1  (road/weekend_warrior)
> FTP Test Frequency check returned WARN. For a 9-week plan with a known FTP, the guide says 'the test result sets ALL your training zones for the next 6 weeks' — implying one retest is expected. If only one test is scheduled across 9 weeks that may be acceptable, but the WARN status is unresolved and the guide text does not clarify how many tests are in the calendar or when, leaving the athlete without actionable guidance.

### 15. [minor] ×2  (mtb/ambitious_first_timer, road/weekend_warrior)
> The long-ride duration range cited in the guide ('1.5-2.5 hours' in Weekly Structure) feels low for a race estimated at ~4.1 hours. The guide itself acknowledges the gap via the 'Biggest Opportunity' callout and recommends 3-4 hour rides, which contradicts the 1.5-2.5 hour ceiling stated just paragraphs earlier. This inconsistency could confuse the athlete about what the plan actually prescribes.

### 16. [major] ×1  (mtb/ambitious_first_timer)
> TSS Progression flagged WARN in preview checks but is not acknowledged or explained anywhere in the guide. For a first-timer, an unexplained or irregular TSS ramp could mean a problematic week-to-week load spike that the athlete has no way to self-correct for.

### 17. [major] ×1  (gravel/ambitious_first_timer)
> Zone 1 power range is missing from the zone chart. Zone 1 is listed as '0-102W' in the table header row but the '% FTP' and '% LTHR' columns are blank for Zone 1, leaving the athlete without percentage anchors for their most-used recovery zone. Every other zone has those columns filled.

### 18. [major] ×1  (gravel/ambitious_first_timer)
> Experience label contradiction: the JSON shows 'ambitious_first_timer' / 1 year riding, yet the methodology rationale calls the athlete 'Intermediate level.' These must agree — calling a 1-year rider Intermediate is misleading and could set wrong expectations.

### 19. [major] ×1  (gravel/ambitious_first_timer)
> Fueling duration mismatch: the plan's fueling object specifies 7.2 h race duration, but an 87-mile gravel race in the Costa Brava for a first-timer targeting 'finish' is realistically 6-8+ hours — the guide should state the estimated finish time explicitly so the athlete can cross-check. More importantly, 58 g carbs/h × 7.2 h = ~418 g total carbs, which may be materially short if the actual finish time is longer; the guide gives the athlete no way to scale this.

### 20. [major] ×1  (gravel/ambitious_first_timer)
> TSS Progression check is WARN. The guide contains no week-by-week TSS or volume guidance visible in the truncated text, and there is no coaching commentary explaining how the athlete should interpret or manage the flagged TSS concern. A WARN should at minimum be noted for the coach's awareness.

### 21. [minor] ×1  (mtb/ambitious_first_timer)
> The plan says FTP test results 'set ALL your training zones for the next 6 weeks,' but in an 8-week plan with a single FTP test, this phrasing is inconsistent with the actual plan length and may confuse the athlete about when/whether to retest.

### 22. [minor] ×1  (gravel/ambitious_first_timer)
> The FTP test protocol states 'The test result sets ALL your training zones for the next 6 weeks' — but this is an 8-week plan, and the test presumably occurs near the start. The '6 weeks' figure is an apparent copy-paste artifact that is inconsistent with the plan length and may confuse the athlete.

### 23. [minor] ×1  (gravel/ambitious_first_timer)
> Strength training is referenced as 'Included (home gym)' in the weekly glance and discussed in session types, but no equipment checklist or home gym guidance appears in the truncated text — if the Equipment Checklist section is thin on strength equipment, this is a gap for a persona that apparently has a home gym.

### 24. [minor] ×1  (road/weekend_warrior)
> The fueling section (visible only in the JSON: 60g carbs/hr over 4.1 hours) is not surfaced in the truncated guide text under Nutrition Strategy — this section header appears in the TOC but its content is not present in the excerpt. Cannot confirm the correct race-day fueling numbers (60g/hr, ~246g total carbs) are communicated to the athlete.

### 25. [minor] ×1  (mtb/ambitious_first_timer)
> The guide states the FTP test result 'sets ALL your training zones for the next 6 weeks' — but this is an 8-week plan with only one retest cadence implied. The '6 weeks' figure appears to be a copy-paste artefact from a different plan length and is internally inconsistent.
