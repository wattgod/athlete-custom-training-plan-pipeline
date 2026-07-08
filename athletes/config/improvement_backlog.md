# Improvement backlog — 2026-07-08

**Quality 3.77** · avg coach 6.62/10 · contract pass 75% · load 8.38/plan · 4 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×1  (gravel/masters_returner)
> Off-day error: The 'Your Week at a Glance' section states off days are Sunday AND Wednesday, but Sunday is the race day (2026-09-20) for this athlete's A-race. Listing race day as a standing off day will confuse the athlete and undermine trust in the entire schedule.

### 2. [critical] ×1  (mtb/ambitious_first_timer)
> Discipline mismatch: the athlete's discipline is MTB, but the plan explicitly includes a 'Gravel Skills' section and frames the event throughout as a gravel event. The race name contains 'Gravel Grinder,' but the athlete registered as an MTB rider — the guide should be written for MTB-specific skills (technical singletrack, rock gardens, drops, MTB body position) not gravel cornering or gravel-specific content.

### 3. [critical] ×1  (mtb/ambitious_first_timer)
> Plan length gap not communicated to athlete: the plan is 9 weeks but the race is 11 weeks away. The plan_note explains this is intentional (athlete starts later), but the guide text never tells the athlete when to actually start or that there are 2 unstructured weeks before the plan begins. A paying customer reading this guide has no idea what to do for the first 2 weeks.

### 4. [critical] ×1  (gravel/time_crunched_parent)
> Preview check 'Zone Distribution' is flagged FAIL. This is unresolved and the guide is going to a paying customer. The text claims '~70% easy riding' but the calendar data apparently contradicts this. The specific mismatch is not visible in the truncated guide text, but the automated gate caught it — the guide cannot be sent until the underlying zone distribution in the calendar is corrected and the check re-run.

### 5. [major] ×1  (gravel/weekend_warrior)
> Road Skills section heading appears in the table of contents for a GRAVEL discipline athlete. A gravel plan should feature gravel-specific skills content (loose surface cornering, tire pressure management, off-camber handling, descent technique on dirt) — not generic road skills. If the section body (not shown in the truncated text) contains road-only content, this is a discipline mismatch that would embarrass the business.

### 6. [minor] ×2  (gravel/time_crunched_parent, gravel/weekend_warrior)
> The weekly structure section states 'Your week has 4 training days, 2 of which are key sessions' but off days listed are Sunday, Monday, and Thursday — leaving 4 riding days (Tue, Wed, Fri, Sat). This arithmetic is consistent, but the guide never explicitly names the two non-key riding days as 'easy' or 'strength' days, which could leave the athlete confused about what to do on those days without cross-referencing the calendar.

### 7. [major] ×1  (gravel/masters_returner)
> Zone 1 power range is missing from the zone chart. The table lists Zone 1 as '0-93W' but omits the % FTP and % LTHR columns (shown as blank), making it inconsistent with every other zone row. A paying athlete using a heart-rate monitor has no HR anchor for Zone 1.

### 8. [major] ×1  (gravel/masters_returner)
> The 'GS G Spot' zone (148-158W, 88-93% FTP) overlaps with the stated Zone 4 Threshold lower bound (159-178W, 94-105% FTP) but its LTHR range (92-96%) actually overlaps with Zone 3 Tempo's upper LTHR bound (84-94% LTHR). The HR boundaries are internally inconsistent and could send the athlete into the wrong zone when using heart rate.

### 9. [minor] ×2  (gravel/masters_returner, road/veteran_podium_chaser)
> Weight (146 lbs / 66.2 kg) and height (5'2") appear in the profile section but were not fields in the athlete JSON provided — these values cannot be verified against source data and may be fabricated or carried over from a template, which is an embarrassment risk if wrong.

### 10. [major] ×1  (gravel/masters_returner)
> Plan duration contradiction in hero section: The opening title line reads '9 weeks' and the brief confirms 9 weeks, but the race date is 11 weeks out from today and the plan starts 2026-07-20 — the guide never explains that the athlete begins 2 weeks later than 'today,' and the '74 days from today' countdown implies the plan starts immediately. A reader will think the plan is 11 weeks long, not 9, and miscalculate their start date.

### 11. [major] ×1  (gravel/masters_returner)
> FTP test result validity window stated as '6 weeks' in two places ('sets ALL your training zones for the next 6 weeks'), but the plan is only 9 weeks long and the preview check flagged FTP Test Frequency as WARN. For a masters returner on a 9-week plan, quoting a 6-week validity window conflicts with the plan's own test scheduling and may cause the athlete to skip a retest that the calendar likely prescribes.

### 12. [major] ×1  (mtb/ambitious_first_timer)
> Race name vs. discipline contradiction unaddressed: the verified race is 'Trough Creek Gravel Grinder' at Trough Creek State Park, PA. If the athlete is in the MTB discipline, the coach should either (a) note the event is a gravel grinder and switch the discipline framing, or (b) confirm the athlete is racing it on an MTB. Sending a guide that says 'Gravel Skills' to someone whose profile says MTB is confusing and unprofessional.

### 13. [major] ×1  (mtb/ambitious_first_timer)
> Zone distribution preview check flagged WARN and FTP Test Frequency flagged WARN — neither issue is acknowledged or explained anywhere in the guide text. A coach would at minimum note why the zone distribution skews the way it does or flag the FTP retest cadence to the athlete.

### 14. [major] ×1  (mtb/ambitious_first_timer)
> Fueling strategy references a 4.2-hour race duration and 70 g carbs/hour (visible in plan JSON), but the truncated guide text does not surface these numbers in a nutrition section visible to the athlete. If the Nutrition Strategy section is missing or blank, the athlete has no race-day fueling guidance for what is described as a 4+ hour effort — a significant safety and performance gap.

### 15. [minor] ×2  (mtb/ambitious_first_timer, road/veteran_podium_chaser)
> Long ride duration range cited as '2.2-3.8 hours' in the Weekly Structure section — for a 50-mile gravel/MTB event estimated at 4.2 hours, the upper bound of 3.8 hours is borderline short but acceptable for a finish-goal athlete; however, it should be explicitly tied to the race duration estimate so the athlete understands the rationale.

### 16. [major] ×1  (gravel/veteran_podium_chaser)
> FTP test validity window is stated as 6 weeks ('The test result sets ALL your training zones for the next 6 weeks'), but the plan is only 8 weeks long with a taper at the end. Depending on test placement, this could imply zones are valid through or past the race without a retest — but more critically, '6 weeks' is a hardcoded generic number that does not match this athlete's plan length or structure. It should reference the plan's actual inter-test interval or simply say 'until your next scheduled test.'

### 17. [major] ×1  (gravel/time_crunched_parent)
> Fueling section (not yet visible in truncated text) specifies 70g carbs/hour over an estimated 4.6-hour race duration, but the guide's Recovery Protocol is for a 77 kg athlete while the profile lists weight as 169 lbs (76.6 kg) — these are consistent. However, the 4.6-hour race duration estimate should be validated against a 55-mile gravel course in Sheridan WY for a goal-finish athlete at 235W FTP; the guide never states this assumption explicitly to the athlete, which could lead to under-fueling if their actual finish time differs materially.

### 18. [major] ×1  (gravel/time_crunched_parent)
> The Zone chart is missing % FTP and % LTHR columns for Zone 1 (Active Recovery) — only power (0-129W) is shown, with no RPE anchor beyond 'Very easy.' Every other zone has % FTP and % LTHR. This looks like a rendering/generation dropout and will confuse athletes who cross-reference zones.

### 19. [major] ×1  (road/veteran_podium_chaser)
> The guide describes the athlete as 'Intermediate level' in the methodology rationale section ('10 years of cycling experience at Intermediate level'), but the persona is 'veteran_podium_chaser' — an experienced racer chasing a podium. Labelling a 10-year veteran with a podium goal as 'Intermediate' is contradictory and will undermine athlete confidence. The language should reflect his actual experience tier.

### 20. [major] ×1  (road/veteran_podium_chaser)
> The Weekly Volume preview check flagged a WARN, yet the guide text contains no acknowledgment, explanation, or mitigation of this flag. At 15 h/week for a 10-week plan a volume warning is significant; if any weeks breach a reasonable per-day cap or spike rule, the guide should surface it so the athlete understands what to expect rather than silently omitting it.

### 21. [minor] ×1  (gravel/weekend_warrior)
> The zone chart omits the power percentage column for Zone 1 (Active Recovery). Every other zone lists '% FTP' but Z1 only shows the absolute watt range (0-118W). A reader who retests and gets a new FTP cannot self-calculate Z1 bounds without the percentage, creating inconsistency.

### 22. [minor] ×1  (gravel/weekend_warrior)
> The fueling strategy in the plan JSON calls for 70 g carbs/hour over an estimated 4.8-hour race, yet the truncated guide text does not show this figure being communicated to the athlete in the visible Nutrition Strategy section. The Race-Day fueling numbers must appear explicitly in the guide — if they are missing from the full document this is a meaningful omission for a finish-goal athlete covering 76 hilly miles.

### 23. [minor] ×1  (gravel/masters_returner)
> The fueling section of the guide text is truncated mid-sentence ('No hard training for 48') and the Nutrition Strategy section — which should reference the plan-specified 70 g/h carb target and 5-hour race duration — is not visible in the excerpt. If it is absent from the full document, this is a significant gap for a goal-finisher who needs race-day fueling guidance.

### 24. [minor] ×1  (gravel/masters_returner)
> Long ride peak duration cited as '2.1-3.5 hours' in the Weekly Structure section. For a 68.8-mile gran fondo with an estimated 4.3h race duration, a 3.5h ceiling for the longest training ride is on the low side and should at minimum be explained (e.g., weekly hour budget constraint), otherwise it looks like the plan is under-preparing the athlete for race duration.

### 25. [minor] ×1  (gravel/masters_returner)
> The 'Road Skills' section is listed in the Table of Contents but the truncated guide text does not include it. For a gravel event the skills content must be gravel-specific (loose surface cornering, descending on mixed terrain, tyre pressure management) — if the full section contains road-racing skills copy it would be a discipline mismatch embarrassment.
