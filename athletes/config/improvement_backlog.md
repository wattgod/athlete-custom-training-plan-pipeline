# Improvement backlog — 2026-09-12

**Quality 1.93** · avg coach 5.88/10 · contract pass 75% · load 11.12/plan · 9 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×1  (gravel/veteran_podium_chaser)
> 'Road Race Strategy' and 'Category 5 to Category 1 Pathway' sections appear in the table of contents (and presumably in full later in the guide) for a gravel-discipline athlete. These are road-racing-specific concepts that are irrelevant and actively misleading for GFNY Cozumel — a gravel/gran-fondo event. This is the clearest discipline-content mismatch possible and is embarrassing to send.

### 2. [critical] ×1  (gravel/masters_returner)
> Weekly Volume check FAILED per the preview gate. The guide text does not surface the actual weekly hour breakdown, so it is impossible to verify whether the prescribed load matches the athlete's 9 h/week target — but the automated check already flagged this as a hard failure. Sending a plan with a known volume miscalibration to a paying masters athlete risks overtraining or under-preparation and is not acceptable.

### 3. [critical] ×1  (gravel/masters_returner)
> Off-day count vs. training-day count contradiction: the guide states 'Off days: Wednesday, Sunday, Thursday' (3 off days) yet also states 'Your week has 4 training days.' A 7-day week with 3 off days yields only 4 training days — that is arithmetically consistent — BUT listing three named off days while the athlete has a 9 h/week target with 4 riding days leaves no room for a fifth flex/easy day and makes the weekly structure confusing. More importantly, three scattered off days (Wed, Sun, Thu) breaks the week into isolated single-day blocks that make stacking a long ride + recovery + interval sequence very awkward, and the layout is never reconciled in the text. This will confuse the athlete immediately.

### 4. [critical] ×1  (gravel/time_crunched_parent)
> Road racing / criterium content included for a gravel athlete: the table of contents explicitly lists 'Road Race Strategy' and 'Category 5 to Category 1 Pathway.' These sections are discipline-wrong and would be baffling — and embarrassing — to a gravel gran fondo rider targeting a podium in Morocco.

### 5. [critical] ×1  (gravel/time_crunched_parent)
> Peak long-ride duration stated as 1.5 hours for a race projected at ~4.75 hours (99 miles, ~5,900 ft). The plan itself flags this as a concern but then caps the long ride at 1.5 h as if that is acceptable. A Time-Crunched plan for a 5 h/week athlete targeting a 5-hour event must push the long ride toward at least 2.5–3 hours in Peak; 1.5 hours leaves the athlete catastrophically underprepared and the guide contradicts its own 'biggest opportunity' warning.

### 6. [critical] ×1  (road/time_crunched_parent)
> The guide includes a 'Category 5 to Category 1 Pathway' section. This is a USA Cycling road racing category upgrade pathway and is entirely irrelevant — this athlete is targeting a gran fondo (mass-participation event), not a criterium/road race upgrade path. It is wrong-discipline content that will confuse the athlete and undermine credibility.

### 7. [critical] ×1  (road/time_crunched_parent)
> 'Category 5 to Category 1 Pathway' section is listed in the table of contents and presumably appears in the full guide. This is a road-racing category progression framework that is completely irrelevant to a gran fondo athlete — gran fondos have no USA Cycling category structure. Sending this to a paying customer targeting a podium at Atlas Gran Fondo is embarrassing and potentially confusing.

### 8. [critical] ×1  (road/time_crunched_parent)
> Taper Intensity check returned WARN and was never resolved. A flagged taper intensity issue means the actual workout prescription may have the wrong intensity during race week — exactly the phase where errors matter most. This must be reviewed and corrected before sending.

### 9. [critical] ×1  (road/masters_returner)
> 'Category 5 to Category 1 Pathway' section appears in the table of contents and presumably in the full guide. This is entirely irrelevant and misleading for a masters gran fondo athlete whose goal is simply to finish a 96-mile sportive. Cat 1–5 is a USA Cycling road racing categorization system; it has no meaning for GFNY Cozumel participants and will confuse or alienate this customer.

### 10. [major] ×1  (gravel/veteran_podium_chaser)
> The athlete has 16 years of riding experience and the persona is 'veteran podium chaser', yet the guide explicitly labels him 'Intermediate level' in the methodology rationale paragraph. This contradicts both the persona definition and the years-of-experience data point, and will erode athlete trust immediately.

### 11. [major] ×1  (gravel/veteran_podium_chaser)
> The FTP test section states 'The test result sets ALL your training zones for the next 6 weeks' — but this is an 8-week plan. With one FTP test at or near the start, the zones would govern the remaining 7-ish weeks, not 6. The number is copied from a different plan length template and is factually wrong for this athlete.

### 12. [major] ×1  (gravel/veteran_podium_chaser)
> Three preview checks are flagged WARN (Weekly Volume, FTP Test Frequency, Taper Intensity) but none of these warnings are acknowledged or explained anywhere in the visible guide text. A paying podium-chaser athlete deserves to know if volume, test frequency, or taper intensity are outside normal parameters — silence on flagged warnings is a coaching omission.

### 13. [major] ×1  (gravel/masters_returner)
> Fueling recommendation is undersized for the projected race duration. The plan correctly estimates race duration at ~7.15 hours but prescribes only 56 g carbs/hour. Current sports-science consensus and gravel-racing practice for efforts exceeding 3 hours recommends 80–100+ g/hour (with multi-transporter carbs). At 56 g/hour over 7+ hours this athlete is likely to bonk. The number should either be revised upward or explicitly caveated as a conservative starting point with a gut-training progression — neither appears in the visible text.

### 14. [major] ×1  (gravel/masters_returner)
> Cadence drill language ('Alternate between high cadence 95-105 rpm and low cadence 60-75 rpm intervals') is presented as a universal execution rule but is lifted verbatim from road/track interval coaching. For a gravel racer whose terrain constantly dictates cadence, prescribing structured cadence intervals as a standing rule — without gravel-specific context (climbs, loose surface, seated vs. standing) — is discipline-mismatched and could lead to dangerous low-cadence grinding on technical gravel descents or loose climbs.

### 15. [major] ×1  (gravel/time_crunched_parent)
> Fueling recommendation of 65 g carbs/hour is on the low end for a ~4.75-hour effort where modern sport-nutrition consensus (and the athlete's podium goal) supports 80–90 g/h with a multi-carb blend. Understating this for a competitive A-race is a meaningful coaching error.

### 16. [major] ×1  (gravel/time_crunched_parent)
> Zone 3 ('Tempo') LTHR range is listed as 84–94% LTHR, which runs right through what most established zone models place as the top of Zone 3 / bottom of Zone 4. The zone boundaries appear compressed in a way that could cause the athlete to under-stress threshold work.

### 17. [major] ×1  (gravel/time_crunched_parent)
> 'Road Skills' section appears in the table of contents. For a gravel event with elevation in the Atlas Mountains, gravel-specific descending, loose-surface cornering, and bike-handling skills are what the athlete needs — generic road skills content is at best irrelevant and at worst gives false confidence on technical gravel terrain.

### 18. [major] ×1  (road/time_crunched_parent)
> The plan is 13 weeks long but the race is 12 weeks away (weeks_until_race = 12). The plan_note explains this correctly internally, but the guide as written does not surface this to the athlete anywhere visible — the athlete may be confused about why the plan appears one week longer than expected and could start on the wrong date.

### 19. [major] ×1  (road/time_crunched_parent)
> Fueling section references an estimated race duration of ~4.76 hours (from the JSON) and 58 g carbs/hour, but the guide text does not appear to surface or explain this to the athlete. For a 99-mile gran fondo where nutrition is often the deciding factor between podium and DNF, omitting or burying the specific hourly carb target is a meaningful coaching gap.

### 20. [major] ×1  (road/time_crunched_parent)
> 'Road Race Strategy' section (listed in TOC) is potentially mismatched content. A gran fondo is not a mass-start road race with tactical team dynamics. If that section contains criterium or road-race-specific tactics (attacks, lead-outs, blocking), it is wrong discipline content for this event and athlete goal.

### 21. [major] ×1  (road/masters_returner)
> 'Road Skills' section listed in the table of contents is ambiguous and potentially mismatched: if it contains cornering drills, criterium tactics, or pack-riding skills calibrated to competitive road racing rather than gran fondo pacing and climbing/descending at endurance pace, it is wrong content for this athlete and event.

### 22. [major] ×1  (road/masters_returner)
> 'Road Race Strategy' section in the ToC needs verification: strategy content must be gran-fondo/sportive specific (aid station planning, self-seeding, pacing a hilly 96-mile effort) — not criterium or road race tactics. Given the Cat 1–5 pathway is also present, there is a real risk this section contains copied competitive road-racing strategy that is irrelevant or counterproductive for a finish-goal masters rider.

### 23. [minor] ×1  (gravel/veteran_podium_chaser)
> 'Road Skills' is listed as a standalone table-of-contents section without any gravel-specific context (e.g., loose-surface cornering, descending on gravel, technical terrain). If this section contains generic road-race cornering content it compounds the discipline mismatch; even if it is gravel-appropriate, the ToC label is ambiguous and should be verified before sending.

### 24. [minor] ×1  (gravel/veteran_podium_chaser)
> The guide references 'a 5am workout' as a colloquial example in the sleep-vs-training section — trivially fine — but the long-ride duration range given in Weekly Structure ('3-5 hours') should be cross-checked against the verified race duration of ~4.39 h. The upper bound is appropriate, but the lower bound of 3 h in peak weeks may be insufficient specificity for a podium goal; worth confirming the calendar reflects longer peak long rides.

### 25. [minor] ×1  (gravel/masters_returner)
> FTP Test Frequency was flagged as WARN by the preview gate. In the visible text the guide says 'The test result sets ALL your training zones for the next 6 weeks' — but in a 9-week plan that language implies only one retest window, which may leave the athlete's zones stale if the test falls in Week 1–2. The plan should explicitly state when the retest occurs or acknowledge the single-test approach is intentional.
