# Improvement backlog — 2026-07-15

**Quality 4.21** · avg coach 6.75/10 · contract pass 88% · load 8.25/plan · 5 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×1  (gravel/time_crunched_parent)
> The zone chart omits the % LTHR column values for Zone 3 (Tempo) in the rendered text — the LTHR range '84–94% LTHR' appears in the JSON zone definition but its absence in the displayed chart means a heart-rate-only athlete has no anchor for their hardest steady-state zone. If this is a rendering gap rather than a true omission it must be confirmed before send.

### 2. [critical] ×1  (mtb/weekend_warrior)
> 'Gravel Skills' appears as a dedicated section in the table of contents for an MTB athlete. This is the wrong discipline — gravel cornering and handling drills do not belong in an MTB plan and will immediately undermine athlete confidence in the plan's specificity.

### 3. [critical] ×1  (mtb/weekend_warrior)
> The guide explicitly states the peak long ride is only 1.5 hours for a 62-mile MTB race with an estimated finish time of ~5.2 hours. The plan's own fueling section acknowledges a 5.2 h duration. A 1.5 h ceiling is not a minor gap — it is less than 30% of race duration and falls far below any accepted standard for endurance event preparation, even under Time-Crunched methodology.

### 4. [critical] ×1  (gravel/veteran_podium_chaser)
> The athlete's profile block lists '129 lbs Weight (58.5 kg)' — the athlete's FTP (129W) has been copy-pasted into the weight field. No weight data exists in the source JSON, so this is a hallucinated and factually wrong value that will confuse the athlete (is 129 her FTP or her weight?) and looks embarrassing.

### 5. [critical] ×1  (gravel/veteran_podium_chaser)
> Height '5'8"' is also presented in the profile block but no height data exists in the source JSON — this is a second fabricated personal data point that could directly contradict the athlete's actual height and destroys trust in the plan's personalisation claims.

### 6. [major] ×1  (road/masters_returner)
> Zone Distribution automated check is marked FAIL. The guide states ~65% easy (Z1-Z2), which is correct for the methodology, but if the actual calendar intervals contradict this (too much Z3/tempo prescribed) the text and the workouts are misaligned. This must be resolved before sending — either the calendar needs fixing or the FAIL flag needs a confirmed-waived note.

### 7. [major] ×1  (road/masters_returner)
> Off-day conflict: the guide lists 'Off days: Sunday, Thursday' in the 'Your Week at a Glance' section, but Sunday is also listed as the long-ride day in standard G Spot plans and is GFNY Chile's race day. If the athlete genuinely has Sunday as an off day, the long-ride day assignment is internally contradictory with 'Long rides: Saturday' also being listed — this is confusing and needs clarification.

### 8. [major] ×1  (gravel/veteran_podium_chaser)
> Experience level mislabeled: the guide text states '9 Years Riding at Intermediate level,' but the persona is 'veteran_podium_chaser' — a racer with 9 years and an FTP of 300 W targeting a podium at a UCI gravel event is not an Intermediate. This label contradicts the persona, undersells the athlete, and could erode trust if they notice it.

### 9. [major] ×1  (gravel/veteran_podium_chaser)
> Height/weight profile is inconsistent with the athlete data: the guide displays '176 lbs / 5'6"' but the athlete JSON provides only age, FTP, and hours — no height or weight was supplied. The weight figure of 176 lbs (79.8 kg) appears fabricated or pulled from a wrong profile, and 5'6" height was never given. Fabricated biometric data sent to a paying customer is a credibility and accuracy failure.

### 10. [major] ×1  (gravel/time_crunched_parent)
> Zone 2 power range is missing from the zone chart. Every other zone shows a watt range (e.g., Zone 1: 0–74 W, Zone 4: 126–141 W) but Zone 2 only shows '75–101W' without the % FTP or % LTHR columns filled in — the % FTP column reads '56–75% FTP' and LTHR '69–83% LTHR', which are actually correct numbers, so this is not a data error. On re-read the data IS there. Flagging instead: the Zone 3 row is missing its watt range entirely in the truncated text shown — only '102–117W' appears with no LTHR % listed, which may confuse athletes who train by heart rate.

### 11. [major] ×1  (gravel/time_crunched_parent)
> The long-ride duration ceiling stated in the guide ('1.5–2.5 hours') is very short for a 75-mile gravel race estimated at ~4.7 hours (per the fueling data). The guide does flag this as a 'Biggest Opportunity' caveat, but the plan's own prescribed maximum long-ride duration of 2.5 hours represents only ~53% of anticipated race duration. For a podium-goal athlete this gap should be more forcefully addressed — the current framing undersells the risk and may leave the athlete underprepared for late-race durability demands.

### 12. [major] ×1  (road/veteran_podium_chaser)
> The guide simultaneously describes the athlete as having '13 Years Riding' and labels them 'Intermediate level' in the methodology rationale. A 30-year-old with 13 years of cycling experience and a 345 W FTP is emphatically not an intermediate — this is contradictory and will undermine the athlete's trust in the plan's personalisation.

### 13. [major] ×1  (mtb/weekend_warrior)
> The 'YOUR BIGGEST OPPORTUNITY' callout suggests a single 3–4 hour ride is worth more than two 1.5-hour rides, yet the calendar (per the plan's own statement) caps long rides at 1.5 hours. This creates a direct internal contradiction: the guide acknowledges the 1.5 h ceiling is inadequate and recommends 3–4 h rides, but the prescribed long-ride duration is never reconciled or updated.

### 14. [major] ×1  (gravel/masters_returner)
> Zone 1 power is listed as '0-110W' but at FTP=200W that is 0-55% FTP, a range far too wide — it swallows most of what should be Zone 2 (56-75% FTP). Standard practice at this FTP puts Z1 at roughly 0-55% (~0-110W) only if Zone 2 starts immediately above it; but the Zone 2 entry of '111-150W' is correct, meaning the Z1 upper bound of 110W is technically consistent yet the label '0-110W' spans 55% of FTP and will confuse a rider who sees the RPE descriptor 'barely working' applied to efforts they'd consider easy riding. More critically, the '0-110W' figure is numerically printed without a % FTP column entry, making it the only zone missing its % FTP anchor — an embarrassing omission on a chart that lists % FTP for every other zone.

### 15. [major] ×1  (gravel/masters_returner)
> The long-ride duration bracket printed in the Weekly Structure section reads '3.3-5.5 hours.' For a 9h/week athlete at masters level in the base phase, 5.5 hours is a very large single-day commitment (61% of weekly budget) and the plan offers no caveat or build trajectory to justify the upper bound. Combined with a 'finish' goal and masters-returner persona, this number should either be explained or capped lower, or it risks alarming (or injuring) the athlete.

### 16. [major] ×1  (gravel/veteran_podium_chaser)
> The guide includes a 'Gravel Skills' section (listed in the table of contents) which is appropriate for the discipline, but the excerpt also lists 'Women-Specific Considerations' as a standalone section — while not inherently wrong, if this section contains generic boilerplate not tied to any athlete-provided data (e.g. menstrual cycle phasing, bone density) without any such data being collected in the questionnaire, it risks being patronising or factually unsupported. Needs review before sending.

### 17. [minor] ×1  (road/masters_returner)
> FTP Test Frequency check is WARN. The guide says 'The test result sets ALL your training zones for the next 6 weeks' but a 9-week plan with a single mid-plan test could leave 6+ weeks on stale zones. The text should either confirm a second test is scheduled or explicitly acknowledge one test is sufficient for this plan length.

### 18. [minor] ×1  (road/masters_returner)
> Long-ride duration range of '3.4–5.8 hours' is cited in the Weekly Structure section. 5.8 hours would exceed the expected race duration (~5 h at completion pace for 79.5 mi) and seems high for a 9 h/week athlete; worth verifying the peak long-ride cap in the calendar doesn't breach the Per-Day Duration Cap or create unsustainable week volume.

### 19. [minor] ×1  (gravel/veteran_podium_chaser)
> TSS Progression check flagged WARN in the preview but no acknowledgment or mitigation appears anywhere in the guide text. A coach reviewing the plan should at minimum confirm the TSS ramp is acceptable or note where the anomaly sits in the schedule.

### 20. [minor] ×1  (gravel/time_crunched_parent)
> The guide says 'Your week has 5 training days, 3 of which are key sessions' but the athlete profile is 6 h/week time-crunched — 5 training days on 6 hours averages only 72 min/session, which is plausible but tight. The guide should confirm how the 6 hours are distributed across 5 days so the athlete can sanity-check it against their schedule; no explicit per-day breakdown is given in the truncated text.

### 21. [minor] ×1  (gravel/time_crunched_parent)
> Countdown reads '94 days from today' — this is a dynamic field that will be stale the moment the email is not sent on the generation date. It should either be removed or replaced with a static 'as of [generation date]' label to avoid confusion if the athlete opens the email days later.

### 22. [minor] ×1  (gravel/veteran_podium_chaser)
> The zone chart omits the % FTP columns for Zone 1 (Active Recovery) and the LTHR columns for Zone 1, leaving those cells blank, which is inconsistent with every other row. Athletes referencing the chart will notice the gap and may question the document's completeness.

### 23. [minor] ×1  (gravel/veteran_podium_chaser)
> The custom 'GS G Spot' zone (270–288W, 88–93% FTP) is labeled with an informal/slang name that could read as unprofessional in a paid coaching product delivered to a podium-caliber athlete expecting a serious document. At minimum it needs a brief parenthetical explaining it is a proprietary zone label.

### 24. [minor] ×1  (gravel/veteran_podium_chaser)
> The interval-execution example cites '4×4min at 110% FTP with 4min recovery' as a generic illustration, but the prescribed execution rule then says start the first rep at 105%. Starting VO2max intervals 5% below target is defensible, but for a 310W athlete that is a ~16W reduction — coaches differ on this and the conservative-start advice should at least be flagged as optional so a strong experienced racer doesn't sandbag unnecessarily.

### 25. [minor] ×1  (gravel/veteran_podium_chaser)
> Recovery protocol instructs '150% of fluid lost (weigh before/after)' but gives no guidance on how to interpret that across a multi-hour outdoor gravel ride where weighing before/after may not be practical. A brief outdoor-ride alternative (e.g., urine color check) would make this actionable.
