# Improvement backlog — 2026-09-04

**Quality 3.12** · avg coach 6.12/10 · contract pass 100% · load 10.0/plan · 5 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×3  (mtb/weekend_warrior, road/masters_returner, road/veteran_podium_chaser)
> 'Category 5 to Category 1 Pathway' section appears in the table of contents. This is USA Cycling road-racing category content that has zero relevance to a weekend-warrior MTB gran fondo finisher goal and will confuse or mislead the athlete.

### 2. [critical] ×2  (gravel/masters_returner, gravel/weekend_warrior)
> 'Road Race Strategy' and 'Category 5 to Category 1 Pathway' sections appear in the table of contents and presumably in the full guide. This athlete is racing a gravel event (L'Étape Ciudad de México), not a road criterium or road race. Cat 5–Cat 1 upgrade pathway content is completely irrelevant and actively misleading for a gravel rider targeting a finish goal. These sections must be replaced with gravel-specific skills content (loose surface cornering, gravel descending, singletrack/doubletrack navigation, mechanical self-sufficiency).

### 3. [critical] ×2  (gravel/masters_returner, gravel/weekend_warrior)
> 'Road Skills' section is listed in the table of contents without gravel qualification. For a gravel race that likely includes unpaved terrain, this section needs to cover gravel-specific handling — not road racing skills. Sending road-cornering technique to a gravel racer is a discipline mismatch that undermines the plan's credibility.

### 4. [critical] ×1  (mtb/weekend_warrior)
> Discipline mismatch — multiple sections are written for a road racer, not an MTB rider. 'Road Skills' and 'Road Race Strategy' sections appear in the table of contents, and the equipment checklist specifies 'road bike, in good working order' as mandatory. This athlete is training for an MTB gran fondo and should receive MTB-specific skills, equipment, and tactical content (e.g., trail/technical cornering, tubeless setup, dropper post, MTB hydration pack).

### 5. [critical] ×1  (gravel/weekend_warrior)
> Off days listed as Saturday, Tuesday, AND Sunday — that is three off days, but the plan states '4 training days.' A 7-day week with 3 off days leaves only 4 training days, yet listing Sunday as an off day conflicts with Saturday already being off, making the weekend essentially empty for a 'weekend warrior' whose primary riding opportunity is typically Saturday/Sunday. This is incoherent for the persona and needs to be flagged or corrected.

### 6. [major] ×1  (gravel/masters_returner)
> The plan is 13 weeks long but weeks_until_race is 12. The plan_note explains this is intentional (athlete starts one week later), but the guide never communicates this to the athlete. The cover page simply says '13 weeks' with a race date of November 30, 2026 and a plan start date of September 7 — an athlete counting forward from Sep 7 will expect the plan to end December 7, one week after race day. The guide must explicitly tell the athlete when to begin so the taper lands on race week.

### 7. [major] ×1  (gravel/masters_returner)
> The fueling section states a race duration of approximately 4.67 hours (used to calculate 215 g total carbs). At 68 miles this implies roughly a 14.5 mph average — plausible for a masters returner on hilly gravel, but this number is never shown or explained to the athlete. If the athlete is faster, they will over-carry food; if slower, under-fuel. The assumed duration and its basis should be disclosed.

### 8. [major] ×1  (road/masters_returner)
> 'Category 5 to Category 1 Pathway' is listed as a guide section in the Table of Contents. This is a USA Cycling licensed road-racing category progression concept that is completely irrelevant to a masters athlete whose sole goal is to finish a gran fondo. It signals the plan may be pulling boilerplate from a road-racing template and will confuse or mislead this athlete.

### 9. [major] ×1  (mtb/weekend_warrior)
> Plan length contradiction in the athlete-facing text: the JSON confirms plan_weeks=14 and weeks_until_race=13 (athlete starts one week late), yet the guide header states '14-week plan' without any note that the athlete begins on 2026-09-07 with the race on 2026-12-07 — only 91 days away (~13 weeks). The athlete may believe they have a full 14 weeks and miscalculate their taper/race week.

### 10. [major] ×1  (mtb/weekend_warrior)
> Taper intensity flagged WARN in the preview checks but the guide text gives no specific taper guidance beyond 'volume drops sharply; short, sharp efforts keep the engine awake.' For a masters athlete (age 50) this is insufficient — concrete taper intensity prescription or at minimum an acknowledgement of the warning is needed.

### 11. [major] ×1  (mtb/weekend_warrior)
> Race duration estimate used for fueling (5.75 h) implies a ~13.6 mph average pace over 78 miles. For an MTB gran fondo with 9,462 ft of climbing in a tropical/hilly Caribbean venue this is plausible, but the guide never states this assumption explicitly. If the athlete is faster or slower the carb totals will be materially wrong, and there is no sensitivity note.

### 12. [major] ×1  (road/veteran_podium_chaser)
> The automated preview flagged 'Taper Intensity: WARN' but the guide text contains no corrective language or caveat about taper intensity execution. Whatever triggered the warning (likely intensity prescribed during taper being too high or structured incorrectly) is unresolved and will reach the athlete uncorrected.

### 13. [major] ×1  (road/veteran_podium_chaser)
> The 'Road Skills' and 'Road Race Strategy' sections listed in the table of contents are visible but not reviewed in the truncated text. For a Gran Fondo (mass-start, non-draft-legal or at minimum not a points-race format), generic road-race strategy content (e.g. breakaway tactics, field-sprint positioning) may be mismatched to the event format. These sections need to be verified or replaced with Gran Fondo-specific pacing and group-riding strategy.

### 14. [major] ×1  (gravel/weekend_warrior)
> Long ride day is assigned to Monday. For a self-described weekend warrior (persona: weekend_warrior), a Monday long ride is highly implausible — most weekend warriors have their extended free time on weekends, not Mondays. This contradicts the persona and will likely frustrate or confuse the athlete.

### 15. [major] ×1  (gravel/weekend_warrior)
> The nutrition section is visibly truncated mid-sentence ('Examples: oatmeal with'). If this reflects the actual email content, the athlete receives an incomplete guide — embarrassing and unprofessional.

### 16. [major] ×1  (road/masters_returner)
> Off days are listed as 'Thursday, Wednesday, Tuesday' — three days listed in reverse-chronological order with no logical grouping. A 4-training-day week with 6 h budget cannot have three separate off days that include both mid-week days; this contradicts the '4 training days' statement and will confuse the athlete about her actual schedule.

### 17. [major] ×1  (road/masters_returner)
> Zone 2 lower-bound power (97 W) implies a Zone 1 ceiling of 96 W, but the Zone 1 row shows '0-96W' with no % FTP label populated — the % FTP column is blank for Zones 1 and 4's upper end reads '105% FTP = 183 W' which is correct, but Zone 1 missing the % label is an inconsistency that undermines the zone chart's authority.

### 18. [major] ×1  (road/masters_returner)
> The guide states 'Strength training: Included (bodyweight)' and lists a strength section, but the Time-Crunched methodology at 6 h/week for a masters returner should treat strength as supplemental and flag the interference effect on limited recovery time. There is no caveat that strength days must not precede key bike sessions — an omission that could cause self-inflicted fatigue.

### 19. [minor] ×1  (gravel/masters_returner)
> The equipment checklist under 'MANDATORY' lists 'road bike, in good working order' for a gravel event. The athlete's discipline is gravel — the checklist should reference a gravel bike (or at minimum gravel/adventure bike) and should mention appropriate tire width, tubeless setup, and frame bag/feed bag considerations relevant to a 68-mile gravel race.

### 20. [minor] ×1  (gravel/masters_returner)
> Weekly Volume and TSS Progression both flagged WARN in the preview checks. While not automatically a blocker, the guide provides no qualitative acknowledgment of conservative volume or compensating density adjustments. A brief note explaining why the plan is calibrated slightly lower (masters returner, fatigue management) would pre-empt athlete concern.

### 21. [minor] ×1  (road/masters_returner)
> The plan is 14 weeks but only 13 weeks remain until race day, meaning the athlete must start immediately with no slack. The guide never explains this to the athlete — the plan_note clarification exists in the JSON for internal use but the athlete-facing text should acknowledge 'your plan starts this week' to avoid confusion about the mismatch.

### 22. [minor] ×1  (road/masters_returner)
> 'Road Race Strategy' is listed as a Table of Contents section. Gran fondos are not road races; strategy advice for mass-start criterions or peloton tactics is mismatched to this event and goal. At minimum the section should be reframed as 'Gran Fondo Pacing & Strategy'.

### 23. [minor] ×1  (mtb/weekend_warrior)
> The equipment checklist mandates 'two bottles for anything over 90 minutes outdoors' with no mention of a hydration pack, which is standard MTB gran fondo equipment, especially for a 5+ hour tropical ride where aid station spacing may be unpredictable.

### 24. [minor] ×1  (mtb/weekend_warrior)
> The 'How Adaptation Works' section references generic cycling prose that reads like boilerplate copy ('the cycling nutrition industry wants you to believe you need seventeen different products'). While not factually wrong, this promotional/editorial tone is inconsistent with the voice of a personal coach and dilutes trust.

### 25. [minor] ×1  (road/veteran_podium_chaser)
> Zone 1 row in the zone chart omits the % FTP range (only raw watts are shown: 0–154 W). Every other zone lists both watts and % FTP. For a coach-facing QA standard this is inconsistent and could confuse an athlete who updates their FTP and tries to recalculate Zone 1 boundaries.
