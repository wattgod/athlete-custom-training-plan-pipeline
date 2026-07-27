# Improvement backlog — 2026-07-27

**Quality 0.13** · avg coach 5.33/10 · contract pass 50% · load 13.0/plan · 11 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×1  (mtb/weekend_warrior)
> Discipline mismatch: the Table of Contents lists a 'Gravel Skills' chapter. This is an MTB race plan — the chapter should cover MTB-specific technical skills (cornering on singletrack, rock gardens, drops, climbing traction). Sending a gravel skills chapter to an MTB racer is embarrassing and signals the wrong template was partially applied.

### 2. [critical] ×1  (gravel/ambitious_first_timer)
> FTP listed as '118 lbs Weight' in the athlete profile card — the plan has swapped the athlete's FTP value (118W) into the Weight field. The actual weight is nowhere shown. This is a glaring factual error that will confuse and embarrass.

### 3. [critical] ×1  (gravel/ambitious_first_timer)
> Sections titled 'Road Skills,' 'Road Race Strategy,' and 'Category 5 to Category 1 Pathway' appear in the table of contents for a GRAVEL event. These are road-racing constructs (USA Cycling cat system, criterium/road tactics) that are irrelevant and wrong for a gravel athlete. A gravel-specific skills section (descending on loose surface, gravel cornering, hydration pack/bag setup, puncture management) should replace them.

### 4. [critical] ×1  (gravel/time_crunched_parent)
> Road race content injected into a gravel plan: the table of contents explicitly lists 'Road Race Strategy' and 'Category 5 to Category 1 Pathway' sections. Neither belongs in a gravel gran fondo guide. The Category 1–5 upgrade pathway is a USA Cycling road racing construct with zero relevance to GFNY Miami. This would confuse and embarrass us with a paying gravel athlete.

### 5. [critical] ×1  (gravel/time_crunched_parent)
> Fueling numbers in the Recovery Protocol are inconsistent with the plan's own fueling data. The plan JSON specifies 59 g carbs/hour and a 4.6-hour estimated duration, which implies ~271 g total race carbs — but the post-ride recovery carb target of '84–101 g' is not cross-referenced to any ride duration and appears to be a generic body-weight formula output dropped in without reconciliation with the prescribed in-ride fueling strategy. More importantly, the guide never surfaces the athlete's race-day fueling target (59 g/hr) anywhere in the truncated text, which is a significant omission for a nutrition-focused section.

### 6. [critical] ×1  (gravel/weekend_warrior)
> Table of contents and plan body include a 'Category 5 to Category 1 Pathway' section — this is road-racing/USA Cycling category upgrade content that has zero relevance to a gravel athlete whose only goal is 'finish.' It is the wrong discipline and wrong context entirely, and would confuse or embarrass the business.

### 7. [critical] ×1  (gravel/weekend_warrior)
> Table of contents also includes a 'Road Race Strategy' section. This athlete is doing a gravel event; road race tactics (peloton positioning, road sprinting, etc.) are incorrect content for this plan and suggest template bleed-in from a road-racing variant.

### 8. [critical] ×1  (road/veteran_podium_chaser)
> Experience level is labeled 'Intermediate' in the plan text ('7 years of cycling experience at Intermediate level') but the persona is 'veteran_podium_chaser' — an experienced racer chasing a podium. Calling a 7-year veteran with a 265W FTP 'Intermediate' is factually wrong and will immediately undermine the athlete's trust in the entire document.

### 9. [critical] ×1  (road/veteran_podium_chaser)
> Weekly Volume check flagged FAIL in the preview checks, yet the guide text is being sent without any visible resolution or coach note explaining the discrepancy. A volume FAIL means at least one week violates the stated 15h target — this must be corrected in the calendar before sending.

### 10. [critical] ×1  (road/veteran_podium_chaser)
> 'Category 5 to Category 1 Pathway' section listed in the Table of Contents is completely irrelevant and actively misleading for a UCI Gran Fondo athlete. Cat 5–1 is USA Cycling road licensing terminology that has no bearing on gran fondo competition. A 43-year-old podium-chasing woman reading this will either be confused or insulted. This section must be removed or replaced with gran-fondo-specific content (e.g., mass-start tactics, KOM segment strategy, age-category podium dynamics).

### 11. [critical] ×1  (road/veteran_podium_chaser)
> Fueling numbers are internally inconsistent and potentially wrong. The plan data states 66g carbs/hour for a 3.3h event, yet the Recovery Protocol instructs '69-83g carbs within 30 minutes post-ride.' The post-ride carb window figure (69–83g) appears to be auto-generated from a body-weight formula (roughly 1g/kg × 69kg), but the text does not explain this, making it look like the same per-hour race fueling number — directly contradicting the 66g/hr figure stated elsewhere. This will confuse the athlete and must be disambiguated with clear labels.

### 12. [major] ×1  (mtb/weekend_warrior)
> Long ride duration stated as 1.5 hours peak, which the plan itself admits is undersized for a 30-mile MTB race (estimated ~2.8 h finish). Worse, the same section says 'peak duration of 1.5 hours' as a hard ceiling while simultaneously telling the athlete a single 3-4 hour ride would be ideal. These two statements are in direct conflict and will confuse the athlete about what the plan actually prescribes.

### 13. [major] ×1  (mtb/weekend_warrior)
> Internal contradiction in Weekly Structure: the text states 'Your week has 4 training days, 4 of which are key sessions' — claiming ALL 4 days are key sessions. That is inconsistent with the Time-Crunched model described elsewhere (2 key intensity sessions + long ride + easy/recovery ride) and would leave zero recovery-purpose rides in the week.

### 14. [major] ×1  (gravel/ambitious_first_timer)
> The athlete's experience is described as '1 Years Riding' in the profile but labelled 'Intermediate level' in the methodology rationale. One year of riding is not intermediate — this contradiction undermines trust in the personalisation claim.

### 15. [major] ×1  (gravel/ambitious_first_timer)
> TSS Progression flagged WARN in the preview checks, but the guide text contains no acknowledgement or mitigation note to the athlete. A WARN on TSS ramp rate should either be resolved in the calendar or disclosed with context so the coach-of-record is not blindsided.

### 16. [major] ×1  (gravel/time_crunched_parent)
> Zone 2 lower power boundary is missing from the zone chart. Zone 1 shows '0–129W' and Zone 2 shows '130–176W / 56–75% FTP' — the percentage column for Zone 1 is blank. Minor in isolation, but the zone chart is a reference the athlete will consult constantly; a blank cell looks like an error and undermines trust.

### 17. [major] ×1  (gravel/time_crunched_parent)
> The 'Road Skills' section appears in the table of contents. For a gravel event like GFNY Miami (paved and hard-pack mixed course), some skills content is appropriate, but the adjacent 'Road Race Strategy' and Category ladder headings suggest the skills section may also be generic road-crit content rather than gravel-specific (e.g., gravel cornering, surface transitions, tire pressure management). This cannot be confirmed from the truncated text but is a high-probability contamination risk given the other road-content errors.

### 18. [minor] ×2  (gravel/time_crunched_parent, road/veteran_podium_chaser)
> The long-ride duration range cited in the Weekly Structure section ('3.1–5.2 hours') should be verified against the athlete's 8h/week cap and the race's estimated finish time. At FTP 235W targeting a 'finish' goal over 71 miles, a 5.2-hour long ride would represent 65% of the weekly hour budget in a single session — plausible but tight, and the figure should be confirmed against the actual calendar rather than stated as a static range in the guide text.

### 19. [major] ×1  (gravel/weekend_warrior)
> The per-day duration cap check explicitly FAILED in the preview_checks JSON, yet the plan was passed to QA without resolution. At least one day in the calendar exceeds the prescribed cap for a 6 h/week athlete — this must be identified and corrected before sending.

### 20. [major] ×1  (gravel/weekend_warrior)
> Fueling section states post-ride recovery carbs of '56-67g' (visible in the truncated text). The plan's own fueling data shows 52 g/hour for a 2.8-hour estimated race duration (~146 g total race carbs). The post-ride carb number appears inconsistently sourced and does not align with the athlete's calibrated fueling profile — needs reconciliation.

### 21. [major] ×1  (gravel/weekend_warrior)
> The athlete profile displays '123 lbs / 5'8"' — weight and height data are not present anywhere in the input JSON. These values appear to be fabricated or pulled from a default template. Sending a plan with made-up physical stats to a paying customer is a trust and accuracy failure.

### 22. [major] ×1  (road/veteran_podium_chaser)
> 'Category 5 to Category 1 Pathway' section appears in the table of contents. Levi's GranFondo is a mass-participation Gran Fondo, not a USAC road race with cat upgrades. Cat upgrade pathways are irrelevant and discipline-mismatched content — it does not belong in a Gran Fondo plan and will confuse or annoy the athlete.

### 23. [major] ×1  (road/veteran_podium_chaser)
> Zone Distribution flagged WARN and TSS Progression flagged WARN are both unresolved. For a podium-goal athlete on a polarized plan, zone distribution integrity is central to the methodology — sending with an unacknowledged WARN on both is a coaching quality issue.

### 24. [major] ×1  (road/veteran_podium_chaser)
> The athlete is described as 'Intermediate level' in the methodology justification ('8 years of cycling experience at Intermediate level'), yet this is a veteran podium chaser with a 285W FTP (likely ~4.1 W/kg at the stated 69kg) targeting a UCI-sanctioned event. Calling her 'Intermediate' is factually inconsistent with the persona_label 'Experienced racer chasing a podium' and will undermine athlete confidence in the plan's calibration.

### 25. [major] ×1  (road/veteran_podium_chaser)
> Zone 1 and Zone 6 rows in the zone chart are missing the '% FTP' column values. Zone 1 shows '1-2' under RPE but no FTP percentage range; Zone 6 shows '>343W' in power but no FTP percentage label in the % FTP column. Every other zone has both. This is inconsistent and looks like a template fill failure.
