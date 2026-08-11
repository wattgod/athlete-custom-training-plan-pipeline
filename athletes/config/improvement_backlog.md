# Improvement backlog — 2026-08-11

**Quality 1.25** · avg coach 6.0/10 · contract pass 75% · load 13.12/plan · 10 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×1  (mtb/weekend_warrior)
> Discipline mismatch throughout: the athlete's discipline is MTB, but the plan title, race name framing, and a dedicated 'Gravel Skills' section all treat this as a gravel event. A gravel-specific skills section should not exist in an MTB plan — cornering, bike-handling, and technical trail skills are categorically different disciplines.

### 2. [critical] ×1  (mtb/weekend_warrior)
> Long-ride duration guidance of '1.5–2.5 hours' is dangerously undersized for a 75-mile race with a projected finish time of ~6.9 hours. Even with a Time-Crunched methodology, the guide itself flags the problem but then fails to correct the number — the ceiling cited in the guide is far too low and will leave the athlete without the durability needed to finish.

### 3. [critical] ×1  (mtb/weekend_warrior)
> The plan is titled 'Flanders Legacy Gravel' and the guide repeatedly uses 'gravel' framing (gravel skills section heading visible in the table of contents), but the discipline field is MTB. If this is genuinely an MTB event, the entire race-specific skills and race-simulation content is wrong. If it is a gravel event, the discipline tag in the system is wrong — either way, this is a critical data mismatch that must be resolved before sending.

### 4. [critical] ×1  (road/time_crunched_parent)
> Contents page lists 'Category 5 to Category 1 Pathway' as a guide section. This is a USA Cycling road-racing licence category progression concept that is completely irrelevant to a UCI Gran Fondo — gran fondos are mass-participation events with no upgrade categories. Including it will confuse or mislead the athlete and looks like copy-paste contamination from a criterium/road-race template. It must be removed or replaced with gran-fondo-specific content.

### 5. [critical] ×1  (road/veteran_podium_chaser)
> A 'Gravel Skills' chapter appears in the table of contents for a road discipline athlete targeting a road race (Around the Bay in a Day). This is wrong-discipline content and is embarrassing — a paying road racer should never see gravel skills drills in their plan.

### 6. [critical] ×1  (gravel/masters_returner)
> Wrong discipline content — 'Road Race Strategy' and 'Category 5 to Category 1 Pathway' sections appear in the table of contents (and presumably in the full document) for a GRAVEL gran fondo athlete. Cat 5–1 road licensing pathways are entirely irrelevant and confusing for a gravel finisher. This is the most embarrassing discipline mismatch possible.

### 7. [critical] ×1  (gravel/masters_returner)
> Wrong discipline content — 'Road Skills' section listed in the table of contents is mismatched to a gravel event. The skills section should cover gravel-specific skills: loose-surface cornering, descent line choice on gravel, tire pressure management, and navigation. A road-skills module signals the plan was not built for this rider.

### 8. [critical] ×1  (gravel/veteran_podium_chaser)
> 'Category 5 to Category 1 Pathway' section appears in the table of contents and body — this is road-racing licensing content that is completely irrelevant to a gravel gran fondo. It is wrong-discipline content that will confuse and embarrass in front of a podium-level gravel athlete.

### 9. [critical] ×1  (gravel/veteran_podium_chaser)
> 'Road Race Strategy' section is listed in the contents and appears in the guide — this is road-criterium/road-race tactical content, not gravel fondo strategy. A paying gravel racer will immediately notice this is copied from a road-racing template.

### 10. [critical] ×1  (road/veteran_podium_chaser)
> 'Category 5 to Category 1 Pathway' appears in the Table of Contents. This is a USA Cycling license-category progression concept that is entirely irrelevant to a gran fondo athlete. GFNY Cozumel is not a USA Cycling-category road race; there are no Cat 1–5 upgrade points. This section either belongs to a different plan template or was included in error and will confuse or mislead this paying customer.

### 11. [major] ×1  (gravel/time_crunched_parent)
> Zone Distribution check FAILED in the automated preview. The guide text claims '~70% of riding stays genuinely easy,' but the failed check implies the actual week-by-week zone distribution in the calendar does not match this stated target. The guide and the calendar are contradicting each other — a customer following the guide's expectation will be confused or misled when they look at the actual workouts.

### 12. [major] ×1  (gravel/time_crunched_parent)
> Long ride duration ceiling is stated as '1.5–2.5 hours' in the Weekly Structure section. For a 62-mile gravel race with an estimated 5.6-hour finish duration (per fueling data), a 2.5-hour long ride cap is severely inadequate. The 'Biggest Opportunity' callout acknowledges this but then recommends 3–4 hour rides — which directly contradicts the 1.5–2.5 hour figure given two paragraphs earlier. The document cannot contain both numbers without creating confusion.

### 13. [major] ×1  (mtb/weekend_warrior)
> Zone distribution and TSS progression both flagged WARN by the automated preview checks, yet no compensating explanation or coaching note appears in the guide text to acknowledge or address these warnings for the athlete or reviewer.

### 14. [major] ×1  (mtb/weekend_warrior)
> Fueling recommendation of 59 g/hr is presented without any explanation of how it was derived. For a 55-year-old weekend warrior at 5 hrs/week, 59 g/hr is at the lower end of modern guidance (60–90 g/hr for mixed carb sources) — the number itself may be defensible, but the guide provides no rationale, no mention of gut training, and no progression strategy across the 6.9-hour race duration, which is a meaningful omission for a masters athlete.

### 15. [major] ×1  (mtb/weekend_warrior)
> The 'Masters Training Considerations' section is listed in the table of contents but is entirely absent from the truncated guide text provided. For a 55-year-old athlete, this section is not optional — recovery timelines, hormonal context, and injury risk are materially different and must be present.

### 16. [major] ×1  (road/time_crunched_parent)
> Zone 1 (Active Recovery) power range is listed as '0-72W' but the percentage of FTP column is blank for Z1 — this breaks the table's internal consistency and leaves the athlete without a % FTP anchor for that zone. At 132 W FTP, Z1 should read ≤55% FTP (≤72 W), which should be stated.

### 17. [major] ×1  (road/time_crunched_parent)
> Zone 6 (Anaerobic) lists '>159W / >120% FTP' but the LTHR column reads 'N/A LTHR' with no explanation. For a 48-year-old athlete who may be using HR as primary feedback (no power meter confirmed), a brief note that HR is unreliable at Zone 6 durations and RPE 10 is the only practical guide is needed — the current blank reads as a production error.

### 18. [major] ×1  (road/veteran_podium_chaser)
> Three preview checks flagged WARN (Weekly Volume, Zone Distribution, TSS Progression) with no explanation or mitigation anywhere in the visible guide text. If the generated plan has volume, zone-distribution, or TSS issues, the guide should at minimum acknowledge the trade-offs; leaving them silent means either the plan is genuinely miscalibrated or the guide is incomplete.

### 19. [major] ×1  (road/veteran_podium_chaser)
> The zone chart is missing power ranges for Zones 1, 5, and 6 in the % FTP / % LTHR columns — only Zones 2, 3, GS, and 4 show those values. For a power-meter user with a known FTP this is a usability failure; the athlete cannot confirm their zones are set correctly on their head unit.

### 20. [major] ×1  (road/veteran_podium_chaser)
> The 'GS G Spot' zone (253-269 W, 88-93% FTP) is presented as a standard zone between Tempo and Threshold. While some coaches use a sweetspot zone, the colloquial label 'G Spot' is unprofessional and potentially embarrassing in a client-facing document.

### 21. [major] ×1  (gravel/masters_returner)
> FTP zone table is missing the power percentage column entries for Zone 1 and Zone 2 (the '% FTP' cells appear blank in the rendered text for those rows), making the zone chart incomplete and inconsistent — a paying customer will notice the gap.

### 22. [major] ×1  (gravel/masters_returner)
> Weekly Volume and Zone Distribution preview checks are both flagged WARN but the guide text never acknowledges or explains these warnings to the coach-reviewer or athlete. At minimum, the QA output should surface what triggered the WARNs so a human can confirm they are acceptable before sending.

### 23. [major] ×1  (gravel/masters_returner)
> The guide states the plan is '25 Years Riding' at 'Intermediate level' — those two descriptors are contradictory on their face (25 years of riding is not intermediate experience) and will undermine athlete confidence. The persona is 'masters returner,' meaning the layoff context should be explained, not quietly classified as intermediate.

### 24. [major] ×1  (gravel/veteran_podium_chaser)
> Weekly Volume check flagged WARN and TSS Progression flagged WARN by the automated gate — at 14h/week for a 38-year-old with a 365W FTP chasing a podium, these warnings must be resolved or explicitly explained in the guide before sending; unresolved WARN flags on a high-stakes A-race plan are not acceptable.

### 25. [major] ×1  (gravel/veteran_podium_chaser)
> The guide states '6 Years Riding' at 'Intermediate level' in the methodology rationale, but the persona is 'Experienced racer chasing a podium' — labeling a podium-hunting veteran as 'Intermediate' is inconsistent and could undermine athlete confidence in the plan's calibration.
