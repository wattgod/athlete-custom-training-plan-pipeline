# Improvement backlog — 2026-07-23

**Quality 2.13** · avg coach 5.88/10 · contract pass 100% · load 11.88/plan · 10 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [major] ×3  (gravel/masters_returner, gravel/veteran_podium_chaser)
> Long ride duration range cited as '3.1–5.2 hours.' The race is estimated at 6.1 hours. The upper end of the long ride window (5.2 h) falls notably short of race duration, which is acceptable for a finish-goal plan, but the gap should be explicitly acknowledged so the athlete is not surprised. As written it could create a false expectation mismatch.

### 2. [critical] ×1  (gravel/masters_returner)
> 'Road Race Strategy' and 'Category 5 to Category 1 Pathway' sections appear in the table of contents (and presumably in the full document). This is a road-racing construct — categories, Cat 5-to-Cat 1 progression, and road race tactics are completely irrelevant and factually wrong for a gravel event. Sending this to a gravel athlete is embarrassing and undermines the plan's credibility.

### 3. [critical] ×1  (gravel/masters_returner)
> Elevation listed as '650 ft' for GFNY Cozumel 96 miles. Cozumel is a flat island; 650 ft for 96 miles is at the extreme low end and may simply be a database default or placeholder. It should be verified against the race DB and either confirmed or corrected — if it is genuinely ~650 ft it needs a note acknowledging the flat profile, because it affects training specificity (no climbing work needed).

### 4. [critical] ×1  (mtb/weekend_warrior)
> Discipline mismatch: the race is an MTB event, yet the guide explicitly includes a 'Gravel Skills' section (visible in the Contents) and references gravel-specific execution cues (e.g., 'gravel cornering drills', race-simulation language tuned to gravel). An MTB athlete needs trail/technical MTB skills content — body position through berms, rock gardens, switchback braking — not gravel-road handling tips. This is the most embarrassing possible error to put in front of a paying MTB racer.

### 5. [critical] ×1  (mtb/weekend_warrior)
> Off-day contradiction: the 'At a Glance' section lists THREE off days — Friday, Tuesday, AND Sunday — giving only 4 training days, yet the athlete's 7h/week target with a weekend-warrior profile almost certainly requires Saturday as the long-ride day and Sunday as a secondary ride day. Listing Sunday as an off day while also stating 'Long rides: Saturday' leaves only 4 days and makes hitting 7h implausible without extreme session lengths. This needs to be verified against the calendar and corrected if Sunday should be a training day.

### 6. [critical] ×1  (gravel/veteran_podium_chaser)
> Wrong-discipline content: The table of contents explicitly lists 'Road Race Strategy' and 'Category 5 to Category 1 Pathway' sections. This athlete is racing a gravel gran fondo, not a road criterium or road stage race. Cat 5–Cat 1 upgrade pathways are a USA Cycling road-racing construct that is irrelevant and confusing for a gravel racer. This content almost certainly bled in from a road-racing template and must be removed or replaced with gravel-specific race strategy.

### 7. [critical] ×1  (gravel/veteran_podium_chaser)
> Experience-level contradiction: The plan states '17 Years Riding' in the athlete profile but the methodology justification calls this athlete 'Intermediate level.' A 17-year rider with a podium goal and 14 h/week is unambiguously experienced/advanced. Labelling them 'Intermediate' undermines coach credibility and may have downstream effects on prescribed intensity or volume language elsewhere in the plan.

### 8. [critical] ×1  (mtb/weekend_warrior)
> Table of Contents lists a 'Gravel Skills' section — this is an MTB race (Walburg Dirty 30), not a gravel event. Gravel-specific cornering and bike-handling content is wrong-discipline material that will confuse and embarrass.

### 9. [critical] ×1  (mtb/weekend_warrior)
> Fueling section references a 2.7 h estimated race duration (from the JSON) but the guide text visible implies standard road/gravel fueling language. At 200W FTP on a 30-mile MTB course, a 43-year-old weekend warrior could easily be out 3.5–4+ hours; the duration estimate of 2.7 h appears systematically low and will cause the athlete to under-fuel on race day.

### 10. [critical] ×1  (gravel/veteran_podium_chaser)
> Table of contents and implied content includes 'Road Race Strategy' and 'Category 5 to Category 1 Pathway' sections. This is a gravel athlete targeting a gran fondo podium — road race category progression content is entirely wrong for the discipline and will confuse and embarrass.

### 11. [critical] ×1  (gravel/time_crunched_parent)
> The table of contents and document body contain a 'Road Race Strategy' section and a 'Category 5 to Category 1 Pathway' section. This athlete is doing a gravel gran fondo, not a road race. Cat 5–Cat 1 USA Cycling licensing pathways are entirely irrelevant — and actively misleading — for a gravel event. This is wrong-discipline content that would undermine confidence in the entire plan.

### 12. [major] ×1  (gravel/masters_returner)
> The weekly structure section states the athlete has '4 training days, 3 of which are key sessions,' but the 'at a glance' block lists THREE off days (Friday, Wednesday, Tuesday). Three off days from an 8 h/week target leaves only 4 riding days, which is coherent, but calling out three separate off days in that order reads oddly and may confuse the athlete — the days should be listed in calendar order (Tuesday, Wednesday, Friday).

### 13. [major] ×1  (gravel/masters_returner)
> 'Road Skills' section appears in the table of contents without qualification. For a gravel event this should be 'Gravel Skills' or 'Off-Road Skills' — cornering on loose surfaces, braking on gravel descents, line choice, and tire pressure management are what this athlete needs, not generic road skills.

### 14. [major] ×1  (mtb/weekend_warrior)
> Zone chart is missing power ranges for Zone 1 on the lower end and does not display %FTP columns for Zones 1, 5, and 6 consistently — Zone 1 shows only absolute watts (0-97W) with no %FTP figure, and Zone 6 shows '>214W / >120% FTP' but no LTHR. While partial, the inconsistency looks like a rendering/generation gap and will confuse athletes without a power meter who rely on %FTP labels.

### 15. [major] ×1  (mtb/weekend_warrior)
> Race name/discipline labelling: the plan header and throughout references 'JUST.GRAVEL' and styles it as a gravel event (50 miles, gravel skills, etc.), but the athlete's discipline field is explicitly 'mtb'. The verified race DB confirms it is JUST.GRAVEL in the Southern Lake District — a gravel event. The athlete may have selected the wrong discipline in the questionnaire, or the plan generator may have overridden it incorrectly. Either way, the plan must not contain MTB-specific sections (Masters MTB considerations, MTB skills) alongside Gravel Skills content — it must be internally consistent. The guide currently tries to serve both and fails at both.

### 16. [major] ×1  (gravel/veteran_podium_chaser)
> Weekly Volume check flagged WARN and unresolved: The automated preview check returned a WARNING on Weekly Volume, yet the guide was not corrected before reaching QA. At 14 h/week this is a high-volume athlete; if the generated plan weeks contain volume that is too low (or too high) relative to the 14 h target, the discrepancy must be identified and fixed — not silently passed through.

### 17. [major] ×1  (gravel/veteran_podium_chaser)
> Road Skills section is listed in the table of contents without any gravel-specific framing visible in the excerpt. For a gravel race in the Negev Desert (likely loose terrain, exposed climbs, technical descents), road-oriented cornering and peloton skills are insufficient and potentially misleading. The section must address gravel-specific skills: loose-surface cornering, tire pressure management, rough terrain descending, and self-sufficiency in remote conditions.

### 18. [major] ×1  (gravel/time_crunched_parent)
> The 'YOUR BIGGEST OPPORTUNITY' callout states peak long ride duration is 1.5 hours, yet the race is ~60 miles and the fueling section targets a 4.0-hour duration. A 1.5-hour long ride cap represents only ~37% of expected race duration — the text acknowledges the gap but the stated number makes the plan look severely under-prepared even for a time-crunched athlete. If the calendar actually has longer rides, this number is wrong in the guide; if it doesn't, this is a real methodology gap that needs addressing before sending.

### 19. [major] ×1  (mtb/weekend_warrior)
> Zone 2 (Endurance) is listed as '111–150W' but the lower bound of 111W is inconsistent with 56% of 200W FTP = 112W — a minor arithmetic slip — and more importantly Zone 1 upper bound of 110W and Zone 2 lower bound of 111W leave a 1W gap that creates a dead zone in the chart; should be a clean ≤110W / ≥111W split or expressed as 0–55% / 56–75%.

### 20. [major] ×1  (mtb/weekend_warrior)
> Zone Distribution check flagged WARN in the automated preview but no explanation or coach note addresses this in the guide. For a Time-Crunched plan the zone distribution is architecturally important; a silent WARN with no guidance is a quality gap.

### 21. [major] ×1  (mtb/weekend_warrior)
> The athlete's weight of 175 lbs / 79 kg appears in the profile section, but the questionnaire JSON contains no weight field — the plan has fabricated or carried over a weight from another athlete's template. If this is a default/placeholder value it could be wrong and will affect the post-ride nutrition targets (protein/carb grams) shown later.

### 22. [major] ×1  (gravel/veteran_podium_chaser)
> Athlete is described as '13 years of cycling experience at Intermediate level.' The persona is 'veteran podium chaser' (experienced racer), which directly contradicts 'Intermediate level.' This mislabeling could undermine the athlete's confidence in the plan's personalization.

### 23. [major] ×1  (gravel/veteran_podium_chaser)
> Zone 1 row in the zone chart is missing the % FTP and % LTHR columns (left blank), while all other zones have them. This is an inconsistency that looks like a generation error and will be noticed by a data-literate athlete.

### 24. [major] ×1  (gravel/time_crunched_parent)
> Post-ride protein recommendation is internally inconsistent: the text references '29g protein' derived from '72kg body weight,' but 72 kg ≈ 158 lbs is correct for this athlete. However, the standard 0.4 g/kg immediately post-ride formula yields ~29 g — that part is fine — yet the carb range given (72–86 g) implies a 1:2.5–3:1 carb-to-protein ratio at the low end; this is defensible but the stated rationale ('based on your 72kg body weight') implies the carbs are also weight-derived, which they are not at those numbers. The explanation is muddled enough to cause athlete confusion or distrust.

### 25. [minor] ×1  (gravel/masters_returner)
> The plan states '14 Years Riding' in the profile block, but the athlete's years riding were not present in the provided JSON. This figure appears to have been inferred or defaulted; if it came from the questionnaire it should be verified, otherwise it is a fabricated data point shown to the athlete as fact.
