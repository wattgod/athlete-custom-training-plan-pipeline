# Improvement backlog — 2026-08-30

**Quality 1.73** · avg coach 5.62/10 · contract pass 88% · load 11.62/plan · 9 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×1  (gravel/veteran_podium_chaser)
> Wrong discipline content included: the table of contents lists 'Road Skills,' 'Road Race Strategy,' and 'Category 5 to Category 1 Pathway' — this is a GRAVEL plan. Road racing category progression and road race cornering/tactics sections have zero relevance to a gravel racer and will confuse or embarrass the athlete.

### 2. [critical] ×1  (gravel/veteran_podium_chaser)
> Persona label mismatch: the guide internally calls the athlete 'Intermediate level' ('18 years of cycling experience at Intermediate level') but the persona is 'veteran_podium_chaser / Experienced racer chasing a podium.' An 18-year rider with a 385W FTP targeting a podium must NOT be labeled Intermediate — this is contradictory and will destroy the athlete's confidence in the plan.

### 3. [critical] ×1  (road/masters_returner)
> The table of contents and (by implication) the guide body includes a 'Category 5 to Category 1 Pathway' section. This athlete is a masters gran fondo finisher — not a USA Cycling licensed road racer pursuing category upgrades. This content is completely irrelevant to his goal, discipline context, and experience profile, and it will read as confusing or embarrassing to him. It must be removed or replaced before sending.

### 4. [critical] ×1  (mtb/ambitious_first_timer)
> Discipline mismatch: the plan JSON declares discipline = 'mtb' yet GFNY Miami is a road/gran fondo event. The guide includes sections titled 'Road Skills,' 'Road Race Strategy,' and a 'Category 5 to Category 1 Pathway' — all road-racing content. If the discipline is truly MTB these sections are completely wrong; if the event is correctly road, the plan was generated under the wrong discipline flag. Either way the content is incoherent and embarrassing.

### 5. [critical] ×1  (mtb/ambitious_first_timer)
> Zone Distribution preview check explicitly FAILED. The guide is being sent despite a known zone-distribution error — the training stimulus balance that underpins the entire G Spot methodology cannot be verified as correctly applied.

### 6. [critical] ×1  (gravel/time_crunched_parent)
> Wrong-discipline content included: 'Road Race Strategy' and 'Category 5 to Category 1 Pathway' sections appear in the table of contents for a GRAVEL athlete. These are road-racing constructs (Cat 5–1 is a USA Cycling road/crit licensing ladder) and have no place in a gravel plan. Sending this will undermine credibility immediately.

### 7. [critical] ×1  (gravel/time_crunched_parent)
> Zone chart is missing the '% FTP' column values for Zones 1 and 6, and the LTHR column is blank for Zone 1 and Zone 6. Zone 1 shows '0-107W' with no % FTP listed; Zone 6 shows '>235W / >120% FTP' but no LTHR. Inconsistent formatting erodes trust in the data.

### 8. [critical] ×1  (gravel/veteran_podium_chaser)
> The guide contains a 'Category 5 to Category 1 Pathway' section — this is road-racing licence/category content that is entirely irrelevant to a gravel gran fondo athlete. It should not exist in this plan and will confuse or embarrass the athlete.

### 9. [critical] ×1  (gravel/veteran_podium_chaser)
> The 'Road Race Strategy' section (and likely 'Road Skills') is road-discipline copy pasted into a gravel plan. Gravel racing requires different tactics (self-seeding, loose-surface descending, hydration-point strategy, isolation from the peloton). Wrong-discipline content for a podium-goal athlete is a serious credibility failure.

### 10. [major] ×2  (gravel/time_crunched_parent, gravel/veteran_podium_chaser)
> Three automated preview checks flagged WARN (Weekly Volume, TSS Progression, Taper Intensity) and none are acknowledged or explained in the guide text. For a paying athlete at this level, unexplained volume or taper anomalies are a red flag that something in the calendar may be wrong — these need resolution before sending.

### 11. [major] ×1  (gravel/veteran_podium_chaser)
> Fueling number inconsistency: the plan JSON specifies 73g carbs/hour for a ~4.8-hour estimated race duration, but no fueling guidance visible in the truncated guide references these numbers. If the Nutrition Strategy section uses a different figure or omits the per-hour target entirely, this is a critical gap for a podium-goal athlete at 102 miles.

### 12. [major] ×1  (road/masters_returner)
> Zone Distribution check flagged WARN in the preview checks. The guide's text asserts '~70% easy' but this was not validated by the automated gate. For a masters returner without a known FTP, an over-intensity distribution is a real injury/overtraining risk. The actual weekly workout mix should be audited before the plan is sent to confirm the 70/30 claim holds across all 14 weeks.

### 13. [major] ×1  (road/veteran_podium_chaser)
> 'Category 5 to Category 1 Pathway' section heading appears in the table of contents for an athlete described as a veteran podium chaser — this is generic boilerplate for a beginner racer pathway and is completely incongruent with this athlete's profile (11 years riding, 285W FTP, A-race podium goal). It will erode trust immediately if the athlete reads it.

### 14. [major] ×1  (road/veteran_podium_chaser)
> The guide labels the athlete as 'Intermediate level' in the methodology rationale ('11 years of cycling experience at Intermediate level'), which directly contradicts the persona tag 'veteran_podium_chaser / Experienced racer chasing a podium.' An 11-year racer chasing a podium should be categorised as Advanced/Experienced — calling them Intermediate is factually wrong relative to their own data and will feel insulting.

### 15. [major] ×1  (mtb/ambitious_first_timer)
> 'Category 5 to Category 1 Pathway' section is included for an athlete whose stated goal is simply 'Finish' her first big event. Cat upgrade pathway content is irrelevant, potentially confusing, and undermines the plan's credibility with this persona.

### 16. [major] ×1  (mtb/ambitious_first_timer)
> Long ride peak duration is stated as '2.9–4.8 hours' in the weekly structure section. The upper bound of 4.8 hours for an 8 h/week athlete with a single long ride day is extremely high and would leave almost no time for the rest of the week's sessions; this number needs verification against the actual calendar.

### 17. [major] ×1  (mtb/ambitious_first_timer)
> Equipment checklist under 'Training Equipment / MANDATORY' lists 'road bike, in good working order' — appropriate for a road gran fondo but wrong if this is an MTB plan. The mandatory equipment call-out should match the discipline unambiguously.

### 18. [major] ×1  (gravel/time_crunched_parent)
> The 'Road Skills' section listed in the table of contents is ambiguous — if it contains road-specific cornering, paceline, or criterium content rather than gravel-specific skills (loose surface descending, off-camber cornering, singletrack entry), it is wrong-discipline content for this athlete.

### 19. [major] ×1  (gravel/time_crunched_parent)
> Long ride duration range cited as '3.1–5.2 hours' in the Weekly Structure section. For an 8 h/week athlete targeting a ~4.8 h race (per fueling duration), a 5.2 h ceiling long ride is very aggressive and would consume 65% of weekly volume in one session — this needs reconciliation with the Weekly Volume WARN flag.

### 20. [major] ×1  (road/veteran_podium_chaser)
> 'Category 5 to Category 1 Pathway' appears in the table of contents. This athlete is a 32-year-old experienced racer ('veteran podium chaser', 9 years riding) targeting a Gran Fondo podium — GFNY Cozumel is not a USA Cycling cat-upgrade event and this section is irrelevant and potentially confusing or embarrassing to a serious athlete.

### 21. [major] ×1  (road/veteran_podium_chaser)
> The table of contents lists 'Women-Specific Considerations' as a section but the truncated guide never surfaces it for review — if it exists it must be checked; if it was dropped from generation it is a broken TOC link. Either way it signals an assembly error visible to the customer.

### 22. [major] ×1  (gravel/veteran_podium_chaser)
> The preview flagged 'Taper Intensity: WARN' but the guide text gives no acknowledgement or resolution of a taper intensity anomaly. A podium-chasing athlete needs confidence that the taper is correct; an unresolved flag is a coaching error.

### 23. [major] ×1  (gravel/veteran_podium_chaser)
> The preview flagged 'Weekly Volume: WARN' and the guide does not address it. At 13 h/week for a veteran racer, any volume anomaly (e.g., weeks spiking over cap or under-delivering) must be surfaced or corrected before sending.

### 24. [major] ×1  (gravel/veteran_podium_chaser)
> Long-ride duration range is stated as '2.7-4.6 hours' in the Weekly Structure section. The race is ~4 hours (fueling duration 3.98 h); a maximum long ride of 4.6 h is acceptable, but 2.7 h as a floor seems low for a 13 h/week athlete in a 15-week plan — this range should be verified against the actual calendar and, if correct, briefly justified.

### 25. [minor] ×1  (gravel/veteran_podium_chaser)
> The athlete's weight (189 lbs / 85.7 kg) yields a power-to-weight ratio of ~4.5 W/kg at 385W FTP — an elite-level figure. The guide should acknowledge this context (e.g., gravel podium is realistic) rather than remaining silent on it, especially since the goal is explicitly 'podium.'
