# Improvement backlog — 2026-08-02

**Quality -1.2** · avg coach 5.25/10 · contract pass 75% · load 17.38/plan · 15 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×2  (gravel/veteran_podium_chaser)
> Table of contents and body include a 'Road Race Strategy – Category 5 to Category 1 Pathway' section. This athlete is racing a gravel event (GFNY Maryland Cambridge), not a USA Cycling road criterium or road race. Cat 5→Cat 1 progression content is completely wrong-discipline boilerplate and would seriously undermine credibility with a veteran racer.

### 2. [critical] ×1  (gravel/veteran_podium_chaser)
> Table of contents lists 'Road Skills – Road Race Strategy' as a section. For a gravel-specific plan, this should be gravel-specific skills (loose-surface cornering, descending on dirt, dismounts, singletrack if applicable). Generic road race tactics are irrelevant and signal copy-paste error.

### 3. [critical] ×1  (gravel/veteran_podium_chaser)
> Weekly Volume flagged FAIL by the automated preview check, yet the guide confidently states '14 hours per week over 18 weeks' without any caveat. If the calendar weeks do not actually hit 14 h, the stated hours target is false and the entire volume narrative is misleading.

### 4. [critical] ×1  (gravel/time_crunched_parent)
> Wrong-discipline content: The table of contents lists 'Road Skills,' 'Road Race Strategy,' and 'Category 5 to Category 1 Pathway' — these are road-racing sections with no place in a gravel plan. A gravel athlete doesn't race a Cat 5–1 upgrade pathway; gravel has no USAC licensing ladder. This is copy-pasted road content that will confuse and embarrass.

### 5. [critical] ×1  (gravel/time_crunched_parent)
> Zone Distribution preview check is listed as FAIL. The guide is about to be emailed to a paying customer with a known zone-distribution error unresolved. This must be corrected before sending — it likely means the weekly workout mix doesn't match the stated ~65% easy / G-Spot + threshold + VO2 prescription.

### 6. [critical] ×1  (mtb/weekend_warrior)
> Discipline mismatch — the table of contents explicitly lists 'Road Skills,' 'Road Race Strategy,' and 'Category 5 to Category 1 Pathway' sections. This athlete is an MTB rider; road-racing tactics, road skills sections, and a Cat 5-to-1 upgrade pathway are irrelevant and actively misleading for mountain-bike riding.

### 7. [critical] ×1  (mtb/weekend_warrior)
> L'Étape Ciudad de México by Tour de France is a road/gran-fondo event (tarmac), yet the plan JSON discipline is 'mtb.' Either the race is mis-categorised in the system as MTB when it is clearly a road event, or the wrong plan template was applied. This contradiction must be resolved before sending — if the race is road, the discipline tag is wrong; if the athlete truly wants an MTB plan, the race is wrong.

### 8. [critical] ×1  (mtb/weekend_warrior)
> Discipline mismatch throughout: the athlete is registered under discipline 'mtb' yet the plan contains a 'Road Skills' section, a 'Road Race Strategy' section, and a 'Category 5 to Category 1 Pathway' section — all of which are road-racing content. However, the race itself (Granfondo Tre Valli Varesine) is a road gran fondo. The plan metadata says MTB but the race is road — one of these is wrong and the plan must not go out until reconciled. If the discipline tag is a data-entry error and the athlete is actually a road rider, all MTB-specific content must be removed; if the athlete truly rides MTB the race assignment is wrong.

### 9. [critical] ×1  (mtb/weekend_warrior)
> 'Category 5 to Category 1 Pathway' section is present. This is a USA Cycling road-racing license progression concept that is completely irrelevant to a 45-year-old weekend warrior whose stated goal is simply to finish a gran fondo. It implies a multi-year competitive road racing career trajectory this customer never asked for and will find confusing or off-putting.

### 10. [critical] ×1  (road/veteran_podium_chaser)
> The Table of Contents and guide body include a 'Category 5 to Category 1 Pathway' section. This is a USA Cycling road racing licensing concept entirely irrelevant to a Gran Fondo event in Italy. The Granfondo Tre Valli Varesine is a mass-participation gran fondo, not a USA Cycling category race. Including a Cat 5→Cat 1 upgrade pathway is wrong for the discipline format, wrong for the geography, and will immediately destroy credibility with an experienced international racer.

### 11. [critical] ×1  (road/veteran_podium_chaser)
> The persona is 'veteran podium chaser' (experienced racer, 17 years, FTP 245W, A-race goal = podium), yet the guide's 'Success looks like: Compete' goal statement is cut off but the word 'Compete' reads as a beginner/finisher-level goal frame. For this persona the language and goal framing throughout must consistently reflect podium-hunting specificity (race tactics, competition benchmarks, peak power targets), not generic participation language.

### 12. [critical] ×1  (road/time_crunched_parent)
> FTP value (157 W) is displayed under 'Weight' as '157 lbs (71.2 kg)' in the athlete profile table. The athlete's actual weight was never collected — the generator has substituted FTP watts for body weight, which is factually wrong and would immediately confuse or alarm the athlete.

### 13. [critical] ×1  (road/time_crunched_parent)
> Athlete goal is 'podium' per the race data, but the guide outputs 'Compete' under 'Your Goals & Blindspots.' A client paying for a plan aimed at a podium finish who reads 'Compete' as her stated goal will rightly feel the plan was built for someone else.

### 14. [critical] ×1  (road/weekend_warrior)
> Off-day schedule lists Saturday as an off day for a 'weekend warrior' persona — Saturday is almost certainly a key long-ride day for this athlete type. This is either a persona/schedule mismatch or a data-population error, but either way it directly contradicts the athlete's profile and will cause confusion about their most important training day.

### 15. [critical] ×1  (road/weekend_warrior)
> 'Category 5 to Category 1 Pathway' section appears in the table of contents and presumably in the body. This is a road-racing licensure progression entirely irrelevant to a 51-year-old weekend warrior whose sole goal is to finish a gran fondo. It signals the guide was assembled with wrong-athlete boilerplate and will confuse or alienate the customer.

### 16. [major] ×1  (gravel/veteran_podium_chaser)
> Fueling section references a 4.2-hour race duration (matches JSON: fueling.duration_h = 4.2) but the guide text does not surface the 69 g/hr carbohydrate target anywhere in the visible excerpt. The nutrition strategy section is cut off, but the ToC suggests it exists — if that number isn't prominently featured for a podium-goal athlete who needs precision fueling, it is a meaningful omission.

### 17. [major] ×1  (gravel/veteran_podium_chaser)
> The athlete's goal field is 'podium' and persona is 'veteran_podium_chaser,' yet the visible guide language repeatedly defaults to generic phrases like 'Success looks like: Compete' — this is clearly a placeholder that was never filled in. A 46-year-old with 310W FTP targeting a podium deserves explicit, goal-specific language.

### 18. [major] ×1  (gravel/veteran_podium_chaser)
> Preview checks show three WARNs (Weekly Volume, Zone Distribution, TSS Progression) with no acknowledgment or mitigation in the visible guide text. For a 12 h/week experienced racer these flags could indicate real problems (e.g., volume too low or polarization insufficient) that a coach would address in the brief.

### 19. [major] ×1  (gravel/veteran_podium_chaser)
> The guide describes the athlete's experience level as 'Intermediate' ('16 years of cycling experience at Intermediate level') — directly contradicting the persona label 'Experienced racer chasing a podium' (veteran_podium_chaser). A 16-year rider targeting a podium should never be called Intermediate; this erodes trust immediately.

### 20. [major] ×1  (gravel/veteran_podium_chaser)
> 'Road Skills' section appears in the table of contents — ambiguous at best for gravel, but combined with the explicit 'Road Race Strategy' entry it strongly suggests unfiltered road-plan template content was injected into this gravel guide.

### 21. [major] ×1  (gravel/time_crunched_parent)
> The guide states the race is '71 miles 1500 ft' in the header, but the verified race database entry only confirms distance (71 miles); elevation (1500 ft) does not appear in the plan JSON and is not marked as verified. Publishing an unverified elevation figure for a race that takes place in flat South Florida (Miami) is suspicious — GFNY Miami's elevation is well under 1500 ft of gain. This number appears fabricated or copied from another event.

### 22. [major] ×1  (gravel/time_crunched_parent)
> TSS Progression preview check is WARN. The guide never acknowledges or compensates for this — no note to the athlete about a flatter-than-ideal load ramp. At minimum the coach QA pass should confirm this is acceptable or the calendar should be adjusted before sending.

### 23. [major] ×1  (gravel/time_crunched_parent)
> The goal is listed as 'podium' but the guide's goal section is truncated to just 'Compete.' The plan narrative never addresses the podium ambition — no mention of race tactics, competition awareness, or what podium-level fitness looks like for a 71-mile gravel event. For an A-race with a podium goal this is a meaningful omission.

### 24. [major] ×1  (mtb/weekend_warrior)
> Athlete weight and height (158 lbs / 5'6") are stated as fact in the 'Your Profile' box but are not present anywhere in the plan JSON supplied. These figures appear to be fabricated or pulled from a wrong profile, which is embarrassing if the customer sees incorrect personal data.

### 25. [major] ×1  (mtb/weekend_warrior)
> Long ride ceiling is stated as '1.5–2 hours' in the Weekly Structure section, yet the race is 78.84 miles with an estimated finish time of ~5.7 hours (per the fueling data). Even with a Time-Crunched approach this cap is never reconciled with race duration — the 'biggest opportunity' callout suggests 3–4 hour rides but then the structural description contradicts it. The two passages contradict each other and will confuse the athlete.
