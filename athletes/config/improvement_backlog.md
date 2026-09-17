# Improvement backlog — 2026-09-17

**Quality 2.02** · avg coach 6.12/10 · contract pass 75% · load 11.5/plan · 7 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×2  (road/masters_returner, road/time_crunched_parent)
> The 'Category 5 to Category 1 Pathway' section listed in the Table of Contents (and presumably present in the full document) is entirely wrong for this athlete and event. The Atlas Gran Fondo is a mass-participation gran fondo, not a USAC-licensed road race with a category upgrade system. Including Cat 5–Cat 1 upgrade criteria is confusing, irrelevant, and signals the template was not properly stripped of road-race boilerplate.

### 2. [critical] ×2  (road/masters_returner)
> 'Category 5 to Category 1 Pathway' section appears in the table of contents and presumably in the guide body. This is a USA Cycling road-racing license progression concept that is entirely irrelevant to a 58-year-old masters returner whose goal is simply to finish a gran fondo. It signals the guide was assembled from a generic template and not properly sanitized for this persona.

### 3. [critical] ×1  (road/masters_returner)
> Off days list includes Friday ('Off days: Tuesday, Saturday, Friday') but Friday, December 11, 2026 is the race day — listing it as a rest day directly contradicts the event and will confuse the athlete at the most critical moment of the plan.

### 4. [critical] ×1  (road/masters_returner)
> Zone Distribution check = FAIL. The automated gate already flagged this, and the guide text never resolves it — pyramidal distribution should be ~75% Z1-2, ~20% Z3, ~5% Z4+. If the actual calendar contradicts this, the methodology claim is false and the plan will not produce the promised adaptation.

### 5. [critical] ×1  (road/time_crunched_parent)
> 'Category 5 to Category 1 Pathway' appears in the table of contents and presumably as a full section. This is a competitive road racing career-progression concept that has zero relevance to a gran fondo finisher goal. It is embarrassing and confusing content that was clearly injected from a racing-plan template.

### 6. [critical] ×1  (road/time_crunched_parent)
> Peak long-ride duration is stated as 1.5 hours for a race that the plan itself estimates will take ~6.7 hours. Even with the 'Biggest Opportunity' caveat, publishing 1.5 hours as the plan's peak long ride for a 99-mile event is indefensible — it will destroy athlete confidence and is a genuine preparation failure. The plan must either raise the long-ride ceiling meaningfully or restructure the caveat into a firm prescription.

### 7. [critical] ×1  (road/masters_returner)
> Multiple preview checks flagged WARN (Weekly Volume, Zone Distribution, TSS Progression, Taper Intensity) with no satisfactory explanation or mitigation visible in the guide text. These are not formatting flags — they indicate potential structural problems with the actual plan numbers. Sending a plan with unresolved WARN flags on TSS progression and taper intensity to a masters athlete with a goal race is a coaching liability.

### 8. [major] ×2  (road/masters_returner, road/time_crunched_parent)
> 'Road Race Strategy' section is listed in the table of contents. L'Étape is a mass-participation sportive (gran fondo format), not a competitive road race with tactical racing elements like attacking, sitting in a peloton, or sprint finishes. This section risks confusing the athlete or wasting their reading time with irrelevant tactical content.

### 9. [major] ×2  (road/masters_returner)
> Long ride duration range is stated as '2.1-3.5 hours' in the guide text. For a 54-year-old athlete targeting a ~4.67-hour event with a 7 hr/week cap, the upper long-ride ceiling of 3.5 hours is plausible but tight; the guide should explicitly acknowledge that the longest training rides will be shorter than race duration and coach the athlete on bridging that gap mentally and nutritionally — this is only partially addressed.

### 10. [major] ×1  (road/time_crunched_parent)
> The Zone Distribution preview check is flagged FAIL and is never acknowledged or explained in the guide. A paying athlete or a coach reviewing the plan has no idea what the distribution problem is or whether it was intentionally overridden. Either the issue should be fixed in the actual schedule or a clear coaching rationale should be stated in the guide.

### 11. [major] ×1  (road/time_crunched_parent)
> The total race carb figure of 343 g is inconsistent with the supplied data. At 72 g/hr over the calculated race duration of ~4.76 hours the correct figure is approximately 343 g — that actually checks out mathematically, but the guide states a race-day range of 65–79 g/hr without explaining that 72 g/hr is the midpoint. More critically, the guide never reconciles this range with the 343 g 'total' headline — a rider consuming 65 g/hr for 4.76 hours gets only ~309 g, not 343 g. The headline total should either be presented as a range (309–376 g) or the midpoint basis should be stated explicitly to avoid athlete confusion.

### 12. [major] ×1  (road/time_crunched_parent)
> The 'Road Race Strategy' section referenced in the Table of Contents is discipline-appropriate in name but the gran fondo context requires gran-fondo-specific pacing strategy (self-seeding, rolling starts, aid station planning, group dynamics without tactical race neutrality rules) — not criterium or road-race tactical advice. If this section mirrors typical road-race template content it will feel wrong and possibly give the athlete bad advice.

### 13. [major] ×1  (road/veteran_podium_chaser)
> The guide includes a 'Category 5 to Category 1 Pathway' section heading. This athlete is a 'veteran podium chaser' with 8 years of experience — a Cat 1 progression roadmap is irrelevant, condescending, and signals the wrong audience. It should be removed or replaced with advanced racing development content.

### 14. [minor] ×2  (gravel/masters_returner, road/veteran_podium_chaser)
> Long ride duration range is cited as '2.7-4.6 hours' in the Weekly Structure section. The verified race duration is approximately 4.0 hours (fueling duration field = 3.98 h). A ceiling of 4.6 hours for training long rides on a ~4 h race seems slightly high; the upper end should not meaningfully exceed race duration for a gran fondo target. Worth tightening to avoid overreach in late Build/Peak weeks.

### 15. [major] ×1  (gravel/masters_returner)
> FTP test protocol states 'The test result sets ALL your training zones for the next 6 weeks' — but this is an 8-week plan. The number '6 weeks' is factually wrong in this context and will confuse or alarm the athlete about how long their zones remain valid.

### 16. [major] ×1  (gravel/masters_returner)
> Zone 1 (Active Recovery) row in the zone chart shows no % FTP range (only '0-140W' with no percentage), and the % FTP column is blank for Zone 1 — inconsistent with every other zone row, looks like a data-fill error that a paying customer will notice.

### 17. [major] ×1  (road/masters_returner)
> Taper Intensity flagged WARN by the automated preview check, meaning the taper phase may have insufficient sharpening efforts or incorrect intensity targeting. This was not resolved before QA and must be reviewed in the calendar before the plan is sent, as a flat or overly suppressed taper would leave a 54-year-old masters athlete feeling dead-legged on race day.

### 18. [major] ×1  (road/masters_returner)
> Taper Intensity check = WARN. For a masters athlete (age 58, returning after layoff), incorrect taper intensity is disproportionately risky — arriving under-recovered is the single biggest race-day threat at this age. The issue must be resolved before sending.

### 19. [major] ×1  (road/masters_returner)
> Weekly Volume check = WARN and TSS Progression check = WARN simultaneously. Two volume/load flags together suggest the ramp rate or absolute weekly hours are outside acceptable bounds for a masters returner, yet the guide text contains no caveat or explanation acknowledging this.

### 20. [major] ×1  (road/time_crunched_parent)
> FTP Test Frequency flagged WARN and Taper Intensity flagged WARN in the preview checks, but the guide text provides no explanation or mitigation for either. A coach reviewing this has no visibility into what specifically triggered those warnings, and the athlete receives no guidance addressing them.

### 21. [major] ×1  (road/masters_returner)
> Off days are listed as Tuesday, Saturday, AND Sunday. For an 8 h/week athlete targeting a Sunday gran fondo, taking both weekend days off is structurally incoherent — the long ride (essential for a 70-mile event) is placed on Wednesday per the summary, which means the athlete has no weekend long ride. A masters returner needs her longest efforts close to race-day conditions, typically on a Saturday or Sunday.

### 22. [major] ×1  (road/masters_returner)
> 'Road Race Strategy' and 'Road Skills' sections are listed in the table of contents. A UCI Gran Fondo is a mass-participation timed event, not a road race. Tactical content about attacking, protecting a wheel, or sprint finishes is inappropriate and could actively mislead the athlete about what the event demands (pacing, fueling, terrain management).

### 23. [major] ×1  (road/masters_returner)
> Fueling section references a calculated race duration of ~4.65 hours and 56 g carbs/hour, but this is never surfaced or validated in the visible guide text. The 'Nutrition Strategy' section is listed in the contents but none of the truncated text shows the actual per-hour targets being communicated to the athlete — a critical omission for a goal-finish gran fondo athlete.

### 24. [minor] ×1  (road/time_crunched_parent)
> FTP Test Frequency is flagged WARN in the preview checks but the guide only mentions a single Week 1 field test with no mention of a mid-plan re-test. For a 9-week plan, one test is arguably acceptable, but the warn flag suggests the system expected a second test; if the plan calendar includes no re-test the guide should explicitly justify the single-test decision so the athlete isn't confused.

### 25. [minor] ×1  (road/time_crunched_parent)
> Long-ride duration language ('1.5–2.5 hours') is notably short for a 99-mile / ~4.75-hour event and the guide itself flags this as a limitation. While the 'biggest opportunity' callout is honest, the prescribed ceiling of 2.5 hours means the longest training ride is barely 50% of race duration — acceptable for a time-crunched plan but the guide should state this trade-off more directly rather than just encouraging the athlete to 'make more time.'
