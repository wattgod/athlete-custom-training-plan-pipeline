# Improvement backlog — 2026-07-17

**Quality 2.51** · avg coach 6.5/10 · contract pass 88% · load 11.88/plan · 9 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [major] ×3  (gravel/ambitious_first_timer, gravel/veteran_podium_chaser, gravel/weekend_warrior)
> Long ride duration range cited in the guide ('2.6-4.4 hours') is stated as a fact in the body text but is never sourced or explained to the athlete. The upper bound of 4.4h exceeds the expected race duration of ~3.8h by a meaningful margin — not necessarily wrong for a peaking long ride, but the discrepancy deserves a one-line rationale so it doesn't look like a data error.

### 2. [critical] ×1  (mtb/weekend_warrior)
> Discipline mismatch throughout: The athlete's discipline is 'mtb' yet the plan includes 'Road Race Strategy' and a 'Category 5 to Category 1 Pathway' section — content that is entirely irrelevant and potentially confusing for an MTB gran fondo participant. MTB-specific skills (trail braking, switchback technique, technical descending, singletrack pacing) are absent.

### 3. [critical] ×1  (mtb/weekend_warrior)
> Event type mismatch: The RBC GranFondo Whistler is a paved road gran fondo (Vancouver to Whistler on Highway 99), not an MTB race. The plan was generated for 'discipline: mtb' but the race is a road/gravel gran fondo. Either the discipline tag is wrong or the wrong race was assigned — this contradiction must be resolved before sending, as it affects every workout prescription.

### 4. [critical] ×1  (mtb/weekend_warrior)
> Zone Distribution check FAILED (preview_checks): The plan text does not address or acknowledge this failure anywhere, and no corrective note is provided to the athlete. Sending a plan with a known failed zone distribution check without explanation is a coaching error.

### 5. [critical] ×1  (gravel/weekend_warrior)
> Saturday is listed as an OFF day ('Off days: Tuesday, Thursday, Saturday') but Saturday is a normal riding day for most weekend warriors, and Sunday is the designated long ride day. A 7h/week athlete almost certainly needs Saturday as a key training day. If Saturday is genuinely off, the athlete has only Monday, Wednesday, Friday, and Sunday — 4 days — which is tight but possible; however the text also says 'Your week has 4 training days, 3 of which are key sessions,' which is internally consistent only if Saturday is truly off. The problem is that a weekend warrior persona almost always rides Saturday as their second long/key day, and this conflicts with common expectations for this persona. This must be intentionally verified before sending — if correct, the guide should explicitly explain why Saturday is off (e.g. family commitment flagged in questionnaire); if wrong, the schedule is broken.

### 6. [critical] ×1  (road/weekend_warrior)
> 'Category 5 to Category 1 Pathway' section is in the table of contents and presumably in the full document. This is completely irrelevant — this athlete is a weekend warrior whose goal is simply to finish a gran fondo. USAC category racing pathways have zero applicability here and will confuse or mislead the customer.

### 7. [critical] ×1  (road/weekend_warrior)
> 'Road Race Strategy' section (listed in TOC) is wrong for this event. Cycling Shimanami is a mass-participation gran fondo/sportive, not a road race with tactics, breakaways, or field dynamics. Including race tactics copy written for a criterium or road race context is factually wrong for this event type.

### 8. [critical] ×1  (gravel/ambitious_first_timer)
> The athlete profile box lists '119 lbs Weight (54.0 kg)' — but 119 is the athlete's FTP in watts, not her body weight. The FTP field and the weight field have been conflated. This is factually wrong and would immediately destroy athlete trust.

### 9. [critical] ×1  (gravel/ambitious_first_timer)
> The table of contents and guide body include 'Road Race Strategy' and 'Category 5 to Category 1 Pathway' sections. This athlete is a gravel rider targeting a gran fondo; road-racing category progression (Cat 5–1) is completely wrong for her discipline and event, and is likely to confuse or mislead her.

### 10. [critical] ×1  (road/time_crunched_parent)
> Table of contents lists 'Category 5 to Category 1 Pathway' — a USA Cycling road racing license category progression section — which is completely irrelevant and potentially confusing for an athlete whose sole goal is to finish a mass-participation Gran Fondo (L'Étape). This content belongs in a competitive racing plan, not a finish-goal event guide, and will embarrass the business if a customer sees it.

### 11. [major] ×1  (mtb/weekend_warrior)
> Fueling numbers conflict: Plan data specifies 53g carbs/hour for a 5.4-hour estimated duration, yet the recovery protocol prescribes '60-72g carbs within 30 minutes post-ride' without any reference to the race-day fueling figure. No in-ride fueling guidance (bottles, gels, aid stations on the Whistler corridor) appears in the truncated text, which is a significant omission for a 5+ hour goal event.

### 12. [major] ×1  (mtb/weekend_warrior)
> Zone 1 power band is missing: The zone chart lists Zone 1 as '0-69W' but omits the '% FTP' column value (it is blank), breaking the internal consistency of the chart. Every other zone has a % FTP range; Zone 1 should read '< 55% FTP'.

### 13. [major] ×1  (mtb/weekend_warrior)
> 'Road Skills' section is titled generically and, in the context of an MTB-tagged plan, will generate MTB-specific skill content (e.g., cornering on dirt, rock gardens) that is irrelevant if this is actually a road gran fondo — or vice versa. The section cannot be correct for both interpretations simultaneously.

### 14. [major] ×1  (gravel/weekend_warrior)
> The Zone Distribution automated check returned WARN but no explanation or mitigation is visible in the guide text. Given the Time-Crunched methodology's polarized/intensity-heavy nature, a coach reading this would want confirmation that the zone split is intentional and within acceptable bounds, not silently flagged.

### 15. [major] ×1  (gravel/weekend_warrior)
> Long ride peak duration is cited as '2.5–4.2 hours' in the Weekly Structure section. For a 75-mile gravel race with an estimated 7.1h finish time, a 4.2-hour peak long ride is well short of race duration. Time-Crunched methodology accepts this trade-off, but the guide never explicitly acknowledges the gap or explains why it is acceptable for a 'finish' goal — a paying customer could reasonably panic seeing this discrepancy.

### 16. [major] ×1  (road/weekend_warrior)
> The truncated guide shows Sunday listed as an off day, but Sunday is race day (October 25, 2026 is a Sunday). While the calendar is the 'source of truth,' the at-a-glance summary telling the athlete Sunday is always an off day is contradictory and could cause confusion in race week.

### 17. [major] ×1  (road/weekend_warrior)
> Post-ride recovery protocol calls for 'compression garments for rides > 3 hours' — the long ride range cited is 1.9–3.2 hours, meaning this threshold will rarely if ever be triggered and the instruction adds noise without value for this athlete's actual volume.

### 18. [major] ×1  (gravel/ambitious_first_timer)
> The guide references 'Road Skills' and 'Road Race Strategy' sections in the Contents. For a gravel gran fondo, this should be gravel-specific skills (cornering on loose surfaces, tire pressure management, technical descending, group riding on mixed terrain). Wrong-discipline content is embarrassing for a paying customer racing gravel.

### 19. [minor] ×2  (gravel/ambitious_first_timer, gravel/weekend_warrior)
> TSS Progression flagged WARN in preview checks but is not addressed or explained anywhere in the visible guide text. A coach note acknowledging the warn (e.g., acknowledging a slight ramp-rate exceedance) would be appropriate given the 8-week compressed timeline.

### 20. [major] ×1  (road/time_crunched_parent)
> The plan states the long ride peaks at '2.5–4.2 hours,' but the race is estimated at ~4.7 h (per fueling JSON). The peak long ride should reach or closely approach race duration (typically 80–100% of event time) — a ceiling of 4.2 h is meaningfully short for a 4.7 h event and contradicts best practice for a finish-goal athlete.

### 21. [major] ×1  (road/time_crunched_parent)
> The Training Plan Brief says 'Off days: Sunday, Tuesday, Thursday' — three off days — yet the Weekly Structure section states 'Your week has 4 training days, 3 of which are key sessions.' Four training days + three off days = 7 days, which is correct, but the guide then describes session types including a standalone 'Easy Ride' as one of the four, leaving only the Long Ride + 2 interval sessions as 'key' — this arithmetic is fine but the off-day list (Sun/Tue/Thu) conflicts with the guidance that 'intervals [are] mid-week': Tuesday is listed as an off day, so mid-week intervals would fall Mon/Wed, which is a tight back-to-back. This needs explicit clarification so the athlete isn't confused.

### 22. [major] ×1  (road/time_crunched_parent)
> 'Road Skills' and 'Road Race Strategy' are listed as ToC sections. The athlete's goal is purely to finish a Gran Fondo, not to race tactically. Including race-craft strategy content (attacks, positioning, sprint finishes) is misleading for this persona and event type — Gran Fondo-specific pacing and climbing strategy should replace it.

### 23. [major] ×1  (gravel/weekend_warrior)
> The header states '3000 ft' of elevation for the Soldier Cutoff Hillduro 60mi, but the verified race database entry provided to the plan generator contains no elevation figure — this number appears to have been fabricated or hallucinated. Sending an unverified elevation claim to a paying athlete is embarrassing and potentially misleading for pacing and nutrition planning.

### 24. [minor] ×1  (gravel/veteran_podium_chaser)
> The plan lists the athlete's off day as Saturday and long ride as Sunday, but the plan_start_date is 2026-07-27, which is a Monday. This internal calendar reference should be verified against the actual day-by-day schedule to ensure no mismatch that could confuse the athlete.

### 25. [minor] ×1  (gravel/veteran_podium_chaser)
> 17 years of experience is described as 'Intermediate level' in the methodology rationale. A rider with 17 years and a 265 W FTP is almost certainly advanced/experienced, not intermediate — this label could undermine the athlete's confidence in the plan's calibration.
