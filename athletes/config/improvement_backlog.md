# Improvement backlog — crank-v1

**Quality 0.4** · avg coach 6.0/10 · contract pass 50% · load 14.0/plan · 8 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×1  (mtb/ambitious_first_timer)
> Discipline mismatch — the Table of Contents lists a 'Gravel Skills' section, and the Workout Execution section explicitly coaches 'Gravel racing requires both — you need to grind up climbs and spin on flats' and references being 'on the bike for 6+ hours' in a gravel context. This athlete is racing a 60-mile MTB event (discipline: mtb). Gravel-specific skills, language, and references must be replaced with MTB-appropriate content (trail skills, technical descending, climbing traction, etc.).

### 2. [critical] ×1  (mtb/ambitious_first_timer)
> Zone 1 power band is missing from the zone chart — the table lists Zone 1 as '0-94W' with no %FTP column entry, while all other zones show % FTP. More critically, Zone 1 has no HRmax % listed at all, making it inconsistent and incomplete. For an athlete without deep zone experience this is a coaching gap.

### 3. [critical] ×1  (road/time_crunched_parent)
> WRONG DISCIPLINE CUE: Section 6 states 'Gravel racing requires both — you need to grind up climbs and spin on flats.' This athlete is racing GFNY Cozumel, a road event. Gravel racing copy has leaked into a road plan. This is the most embarrassing error — a paying customer will immediately notice the plan is calling them a gravel racer.

### 4. [critical] ×1  (road/time_crunched_parent)
> FUELING DURATION MISMATCH: The fueling block sets duration_h = 8.0 hours for a 96-mile road race. GFNY Cozumel is a relatively flat, fast course; an intermediate male with 280 W FTP will finish in roughly 5–6 hours. An 8-hour fueling window implies he is racing at a pace consistent with ~12 mph average, which contradicts his profile. Either the race duration estimate is wrong or the fueling parameters were pulled from the wrong athlete record. This will result in incorrect carbohydrate totals being communicated to the athlete.

### 5. [critical] ×1  (road/time_crunched_parent)
> LONG RIDE DURATION RANGE IS NONSENSICAL FOR THE EVENT: Section 4 states long rides peak at '1.5–2.5 hours.' A 96-mile race will take this athlete ~5–6 hours. A peak long ride of 2.5 hours is less than half race duration. Even accounting for time-crunched constraints, the guide should be flagging 3–4 hour peak long rides (which it actually does in the 'Biggest Opportunity' callout) — the stated peak range of 1.5–2.5 h directly contradicts that same callout and will leave the athlete dangerously underprepared.

### 6. [critical] ×1  (gravel/ambitious_first_timer)
> Off Days check FAILED (preview_checks.Off_Days_Respected = FAIL). The guide tells the athlete 'Off days: Tuesday' but the automated check flagged this as violated somewhere in the calendar. This is a direct contradiction between the guide text and the actual schedule — the athlete will follow the guide and get a wrong-day-off prescription.

### 7. [critical] ×1  (gravel/ambitious_first_timer)
> Fueling section is broken: fueling.duration_h = 0.0, meaning no fueling window was computed. The guide recommends 70g carbs/hour but has no valid duration to anchor that to — the race distance is also 0 miles, so there is no basis for any fueling duration or total carb targets. Any per-ride fueling numbers in the plan are fabricated from a zero.

### 8. [critical] ×1  (gravel/veteran_podium_chaser)
> The automated preview check flags 'Weekly Volume: FAIL'. This is not explained or resolved anywhere in the plan text. For a 14h/week athlete, if actual scheduled weekly hours materially deviate from the stated target, the plan is mis-calibrated at its core and should not be sent until the root cause is identified and corrected.

### 9. [major] ×1  (gravel/masters_returner)
> HIIT-Focused methodology (50% hard / 20% tempo / 30% easy) is a poor fit for a 57-year-old masters returner at 6h/week targeting a 'finish' goal. Masters athletes and goal=finish profiles almost universally warrant a polarized or pyramidal approach with more Z2 volume. The methodology mismatch risks overreaching and injury for this persona and will look wrong to any experienced eye.

### 10. [major] ×1  (gravel/masters_returner)
> Taper Intensity flagged WARN by the automated preview check, yet the guide text contains no mention of taper intensity specifics — it only says 'short, sharp efforts keep the engine awake.' The WARN was never resolved and the plan is being sent without a human sign-off on what taper intensity actually looks like in the calendar. This must be reviewed before sending.

### 11. [major] ×1  (gravel/masters_returner)
> Long ride duration language is internally contradictory and potentially alarming: the guide states peak long rides are '1.5–2.5 hours,' but the race is 83 miles with 8,100 ft of climbing and an estimated finish time around 6–7 hours. A 2.5-hour peak long ride is grossly inadequate for race-day durability, and the 'Biggest Opportunity' sidebar acknowledges this without resolving it. A 57-year-old finishing a 6-7 hour gravel event on a 2.5h peak long ride is a significant under-preparation risk.

### 12. [major] ×1  (mtb/ambitious_first_timer)
> Intensity distribution contradiction: the guide states '50% easy / 35% tempo / 15% hard' but the preview flags Zone Distribution and TSS Progression as WARN. A Sweet Spot / Threshold methodology for a 9h/week athlete should sit closer to 70-75% easy / 20-25% sweet spot+threshold / 5% hard (polarized-lite). 35% tempo is unusually high and risks the exact gray-zone accumulation the guide warns against — the stated split should be verified against the actual calendar or the description corrected.

### 13. [major] ×1  (mtb/ambitious_first_timer)
> Off-days listed as 'Friday, Thursday' — listing Thursday second after Friday reads as two non-consecutive off days but the ordering is confusing and potentially implies Friday is the primary off day mid-week while Thursday is secondary. For a plan whose long ride falls on Sunday and intervals mid-week, having both Thursday AND Friday off back-to-back is unusual and should be explicitly justified or corrected.

### 14. [major] ×1  (road/time_crunched_parent)
> INTENSITY DISTRIBUTION CLAIM IS INTERNALLY INCONSISTENT: The guide states '50% easy / 35% tempo / 15% hard' and calls this the Sweet Spot/Threshold distribution. However, a true Sweet Spot/Threshold methodology for a time-crunched athlete should show a meaningful proportion of time in Sweet Spot/Zone 4, not 35% in Tempo (Zone 3) — the very zone the guide warns against as the 'gray zone' two pages later. This creates a direct contradiction between the stated distribution and the zone-execution guidance.

### 15. [major] ×1  (road/time_crunched_parent)
> INDOOR WORKOUT RATIONALE REFERENCES '6+ HOURS' ON THE BIKE AS A ROAD CONDITION: Section 6 says 'the mental challenge of being on the bike for 6+ hours' when justifying outdoor rides. While the race may take ~5–6 h, this phrasing suggests the plan was templated from a longer-event guide (possibly gravel/gran fondo ultra) and not fully adapted, and it reinforces the fueling duration concern.

### 16. [major] ×1  (gravel/ambitious_first_timer)
> Race distance is 0 miles. Prosecco Cycling is a real event with a defined distance; a zero means the data pull failed. The guide references '5118 ft' of climbing and a location (Valdobbiadene, Veneto) but never states a distance, so the athlete has no idea what they're training for in terms of duration. Long-ride targets ('3.4–5.8 hours') are floating without a distance anchor.

### 17. [major] ×1  (gravel/ambitious_first_timer)
> Intensity distribution claim is suspicious: '50% easy / 35% tempo / 15% hard' is described as what Sweet Spot/Threshold methodology calls for, but canonical SST methodology is polarised toward easy and sweet-spot work with tempo making up a much smaller fraction. 35% tempo contradicts the plan's own warning about Zone 3 being the 'gray zone' to avoid — this is internally inconsistent and would confuse a thoughtful athlete.

### 18. [major] ×1  (gravel/ambitious_first_timer)
> Zone 3 power label conflict: the zone chart lists Zone 3 as 'Tempo' at 76–87% FTP, but the guide body repeatedly warns against spending time in Zone 3 ('the gray zone') while simultaneously prescribing 35% of training there in the intensity distribution. This is a direct logical contradiction within the same document.

### 19. [major] ×1  (gravel/veteran_podium_chaser)
> The long ride duration range cited in the guide ('6.3–10.5 hours') is extremely wide and the upper end (10.5h) appears disproportionate for an 81-mile gravel race with an expected finish time around 5–6 hours. Even for a high-volume athlete, a long ride nearly double race duration raises overreach concerns and contradicts the 'Long Ride vs Race Duration: PASS' check — those two data points need to be reconciled.

### 20. [major] ×1  (gravel/veteran_podium_chaser)
> TSS Progression is flagged as 'WARN' in the preview checks, meaning week-over-week TSS ramp is outside acceptable bounds at some point in the plan. This is not acknowledged or explained in the guide text, leaving a structural training load risk unaddressed.

### 21. [minor] ×1  (gravel/masters_returner)
> The methodology rationale states '6 hours/week matches the HIIT-Focused approach' without explanation. Six hours per week is conventionally associated with polarized or sweet-spot approaches; HIIT-Focused is typically reserved for athletes with very limited time (3-5h) or strong interval backgrounds. The justification feels auto-generated and unconvincing.

### 22. [minor] ×1  (gravel/masters_returner)
> Post-ride recovery nutrition specifies '28g protein + 69-83g carbs within 30 minutes' — the carb range appears to be derived from the hourly fueling target (70 g/h) rather than standard post-ride recovery guidelines (typically 1–1.2 g/kg carbs = ~70-84g for this athlete, which happens to be in range, but the protein figure of 28g is low for a 57-year-old masters athlete where 30-40g is increasingly recommended for muscle protein synthesis). Minor but worth flagging for a masters-specific plan.

### 23. [minor] ×1  (gravel/masters_returner)
> The guide references 'Road Skills' as a section in the table of contents. While this may be innocuous, for a gravel-specific plan this section should be verified to contain gravel-relevant skills (loose surface cornering, descending on gravel, bike handling on mixed terrain) and not road-racing content such as criterium cornering or peloton positioning.

### 24. [minor] ×1  (mtb/ambitious_first_timer)
> Fueling section references 'being on the bike for 6+ hours' in the indoor/outdoor balance paragraph, but the race fueling data shows an expected duration of 5.0 hours. This inconsistency could confuse the athlete about their projected race time.

### 25. [minor] ×1  (mtb/ambitious_first_timer)
> The guide references 'Avatar crankv11' as the athlete's name/handle in the header. If this is a placeholder or internal username rather than the athlete's actual name, it will appear unprofessional and confusing when the customer receives the email.
