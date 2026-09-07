# Improvement backlog — 2026-09-07

**Quality 2.13** · avg coach 5.88/10 · contract pass 100% · load 11.88/plan · 9 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×1  (gravel/ambitious_first_timer)
> Sections titled 'Road Race Strategy' and 'Category 5 to Category 1 Pathway' appear in the table of contents and, by implication, in the body. These are road-racing constructs entirely irrelevant — and potentially confusing — for a gravel gran fondo athlete. Cat 5–1 licensing pathways do not exist in gran fondo / gravel events. This content must be removed or replaced with gravel-specific race-execution and skills guidance.

### 2. [critical] ×1  (mtb/ambitious_first_timer)
> Discipline mismatch: the plan JSON flags discipline as 'mtb', yet the event is unmistakably a paved-road Gran Fondo. The equipment checklist prescribes a 'road bike', the guide includes 'Road Race Strategy' and a 'Category 5 to Category 1 Pathway' section — content appropriate for a road racer, not an MTB rider. Either the discipline tag is wrong (and the athlete is a road rider, which is likely) or the wrong plan template was applied. Either way, the discipline label and any MTB-specific content that may appear later are a mismatch that must be resolved before sending.

### 3. [critical] ×1  (mtb/ambitious_first_timer)
> Road Race Strategy and 'Category 5 to Category 1 Pathway' sections are visible in the table of contents. Gran Fondo Guadeloupe is a mass-participation gran fondo, not a USA Cycling category road race — a Cat upgrade pathway is completely irrelevant and will confuse or mislead this athlete.

### 4. [critical] ×1  (mtb/ambitious_first_timer)
> Discipline mismatch: the athlete is flagged as 'mtb' in the plan JSON, but the race is the 'UCI Gravel Dustman' and every piece of guide content (Skills section titled 'Gravel Skills', equipment list calling for a 'gravel or similar' bike, terrain framing) is gravel-specific. Either the discipline tag is wrong and this athlete is actually a gravel racer, or the race assignment is wrong. This contradiction must be resolved — sending an MTB athlete a gravel plan (or vice-versa) is a fundamental coaching error.

### 5. [critical] ×1  (mtb/ambitious_first_timer)
> The guide's own 'Gravel Skills' section (listed in the Contents) is included in a plan whose JSON discipline is MTB. MTB-specific skills (technical descending, rooted singletrack, switchbacks, rock gardens) are completely absent. If this athlete is truly an MTB racer, gravel cornering and surface-reading drills are largely irrelevant and the missing MTB skills content is a serious gap.

### 6. [critical] ×1  (mtb/weekend_warrior)
> Discipline mismatch — the plan includes 'Road Race Strategy' and a 'Category 5 to Category 1 Pathway' section. This athlete is doing an MTB gran fondo, not a road category race. These sections are irrelevant, misleading, and embarrassing to send.

### 7. [critical] ×1  (mtb/weekend_warrior)
> 'Road Skills' section (visible in table of contents) is listed without MTB context. Road cornering/positioning skills are not the relevant skill set; MTB-specific technical skills (climbing traction, descending body position, braking, trail reading) should be addressed instead — or the section should be omitted entirely for a finish-goal weekend warrior.

### 8. [critical] ×1  (gravel/ambitious_first_timer)
> Road-race content injected into a gravel plan: the guide includes a 'Road Race Strategy' section and a 'Category 5 to Category 1 Pathway' section (visible in the table of contents). Neither belongs in a gravel gran fondo plan for a first-timer chasing a finish goal. This is wrong-discipline content and is embarrassing if sent.

### 9. [critical] ×1  (gravel/ambitious_first_timer)
> The Equipment Checklist lists 'road bike' under MANDATORY equipment for a GRAVEL event. A gravel athlete should be pointed toward a gravel bike (or at minimum 'gravel or road bike with wider tires'). Sending a gravel plan that tells the customer to race on a road bike is embarrassing and potentially dangerous on rough gravel terrain.

### 10. [major] ×1  (gravel/ambitious_first_timer)
> The profile states '1 Years Riding' but immediately labels the athlete 'Intermediate level.' The persona is 'ambitious_first_timer.' A rider with one year of experience targeting their first big event should not be described as Intermediate — this label could lead the athlete to skip foundational guidance they actually need, and it contradicts the persona definition.

### 11. [major] ×1  (gravel/ambitious_first_timer)
> The 'Road Skills' section listed in the contents is ambiguous — if it contains road-specific cornering, peloton, or drafting content, it is wrong for a gravel solo gran fondo. Even if partially applicable, it must be audited and replaced with gravel-specific skills (loose surface cornering, descent braking on gravel, self-sufficiency/mechanical readiness) before sending.

### 12. [major] ×1  (mtb/ambitious_first_timer)
> Taper Intensity flagged WARN by automated checks and not addressed or overridden anywhere in the guide text provided. The taper section only gives generic text ('short, sharp efforts keep the engine awake') without clarifying what the elevated taper intensity means in practice, leaving a known quality flag unresolved.

### 13. [major] ×1  (mtb/ambitious_first_timer)
> Weight (124 lbs / 56.2 kg) and height (5'4") appear in the athlete profile card but the source JSON athlete object contains no weight or height fields — these values appear to have been fabricated or injected from an unknown source, which is an embarrassing data-integrity issue if the athlete never provided them.

### 14. [major] ×1  (mtb/ambitious_first_timer)
> FTP Test Frequency flagged WARN in preview checks, and the guide acknowledges no FTP is known, yet the plan length is only 9 weeks. With a Week 1 field test consuming training time and potentially a retest mid-plan, the frequency warning should be explicitly addressed in the guide text so the athlete understands when and how often to test — it is currently only vaguely referenced.

### 15. [major] ×1  (mtb/ambitious_first_timer)
> Athlete experience is stated as '1 Years Riding' at 'Intermediate level' in the guide text, but the persona is 'ambitious_first_timer.' A first-timer being labeled Intermediate with 1 year of riding experience is internally inconsistent — the plan should resolve which framing is accurate, as it affects how the methodology selection rationale is communicated.

### 16. [major] ×1  (mtb/weekend_warrior)
> Zone 2 power range is missing from the zone chart — the '% FTP' column shows '56-75% FTP' but the raw watt range cell for Zone 2 appears blank/cut off (shown as '100-135W' without explicit % FTP label alignment). More critically, Zone 1 shows '0-99W' with NO % FTP listed, which is inconsistent with every other zone row and will confuse athletes using a power meter.

### 17. [major] ×1  (mtb/weekend_warrior)
> Off days listed as 'Wednesday, Tuesday, Thursday' — listing three off days for a 5h/week athlete with 4 training days is mathematically correct (4 + 3 = 7), but the order 'Wednesday, Tuesday, Thursday' is non-chronological and reads as a copy-paste error. It should read 'Tuesday, Wednesday, Thursday' and the unusual mid-week three-day block warrants a brief coach note explaining the structure.

### 18. [major] ×1  (mtb/weekend_warrior)
> Long ride duration callout states '1.5–2.2 hours' as the peak long ride range. For a 70-mile MTB event with an estimated race duration of ~4.6 hours (per fueling data), a max long ride of 2.2 hours is severely undersized. The 'Biggest Opportunity' sidebar acknowledges this but still codifies the low ceiling in the structure section — the plan text contradicts itself and may leave the athlete confused about what to actually target.

### 19. [major] ×1  (gravel/masters_returner)
> Long ride duration range is stated as '1.5–2.5 hours' in the Weekly Structure section, yet the race is 81 miles with a projected duration of ~7.15 hours. Even for a time-crunched athlete, capping the described long ride ceiling at 2.5 hours — without any caveat — badly undersells race-day demands and contradicts the very next sidebar that urges 3–4 hour rides. The two passages are internally inconsistent and the lower figure (2.5 h) is embarrassingly short relative to a 7-hour race.

### 20. [major] ×1  (gravel/masters_returner)
> The FTP test note states 'The test result sets ALL your training zones for the next 6 weeks' — but this is a 9-week plan and the FTP Test Frequency check returned a WARN flag, suggesting test spacing may already be marginal. Hardcoding '6 weeks' is factually inconsistent with the plan length and could mislead the athlete about when to retest.

### 21. [major] ×1  (gravel/ambitious_first_timer)
> The equipment checklist lists 'road bike, in good working order' as the mandatory bike. This athlete is preparing for a gravel event; the checklist should specify a gravel bike (or at minimum 'gravel or road bike with appropriate tires'), and gravel-specific tire/setup guidance is absent.

### 22. [major] ×1  (gravel/ambitious_first_timer)
> Taper Intensity flagged WARN by the automated gate but no explanation or mitigation is visible in the guide text. Before sending, the taper section must be reviewed to confirm short sharp efforts are prescribed correctly and the warn condition is understood.

### 23. [major] ×1  (road/weekend_warrior)
> The guide includes a 'Category 5 to Category 1 Pathway' section. This athlete's goal is simply to FINISH a 68-mile gran fondo (L'Étape). Cat 5–1 USA Cycling road racing classification content is entirely irrelevant to a finisher-goal gran fondo participant and could confuse or mislead the athlete about what this plan is preparing them for.

### 24. [major] ×1  (road/weekend_warrior)
> The high-stress guidance is self-contradictory: the Recovery Protocol section tells the athlete to 'eliminate all Zone 4+ work' during high-stress periods, but the plan elsewhere (Build/Peak phases) prescribes threshold and VO2max intervals without any conditional modification for this athlete's flagged high-stress status. The plan needs a consistent, integrated policy rather than a blanket override buried in the recovery section.

### 25. [major] ×1  (gravel/ambitious_first_timer)
> The Road Skills and Race Strategy sections are titled 'Road Race Strategy' and include a 'Category 5 to Category 1 Pathway' — both are road-racing constructs completely irrelevant to a gravel Gran Fondo finisher. Gran Fondos are not categorized mass-participation events; this content is copy-pasted from a road-racing template and should be replaced with gravel-specific skills (cornering on loose surfaces, mechanical self-sufficiency, aid station strategy).
