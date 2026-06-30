# Improvement backlog — 2026-06-30

**Quality 2.59** · avg coach 7.0/10 · contract pass 62% · load 11.62/plan · 8 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×1  (gravel/weekend_warrior)
> Long ride peak duration is cited as '1.5 hours' in the Weekly Structure section for a 54-mile gravel race likely taking 4–5 hours. This is internally contradictory — the plan itself warns the athlete that 'a single 3–4 hour ride is worth more than two 1.5-hour rides,' yet the prescribed peak long ride is only 1.5 hours. Even for a 5 h/week athlete this number is too low and will undermine race-day confidence and durability. The number should reflect the realistic long-ride ceiling given the weekly hours budget (likely 2.5–3 hours), not 1.5 hours.

### 2. [critical] ×1  (road/veteran_podium_chaser)
> Zone Distribution preview check is marked FAIL. This is unresolved in the guide text — the distribution described ('roughly 65% easy') is mentioned qualitatively but the underlying weekly zone allocation apparently fails the automated check. A plan sent to a paying podium-chaser with a known zone distribution error is a coaching credibility risk and could result in wrong-zone training across the full 17 weeks.

### 3. [critical] ×1  (road/time_crunched_parent)
> Zone 1 is missing its FTP% and LTHR% columns entirely — the table shows '0-145W' with no percentage values listed, while every other zone has them. This leaves the athlete with no percentage anchor for Zone 1 and creates an obvious gap a paying customer will notice and question.

### 4. [critical] ×1  (road/time_crunched_parent)
> Zone 2 lower bound (146W) implies Zone 1 ceiling is 145W, which is only 54.7% of 265W FTP — below the conventional ~55-56% boundary and inconsistent with the 56-75% FTP range listed for Zone 2 (whose lower bound at 56% FTP would be ~148W, not 146W). The one-watt rounding is minor, but the Zone 1 upper boundary being unlabeled compounded with a Zone 2 start of 146W (55.1% FTP) contradicts the stated 56% lower bound for Zone 2. The numbers do not reconcile cleanly and will confuse a data-literate athlete.

### 5. [critical] ×1  (mtb/weekend_warrior)
> Section header 'Road Skills' is present in the table of contents for an MTB discipline plan. MTB-specific skills (trail braking, switchback technique, rock garden line choice, loose-surface cornering) should replace road-skills content. Sending a road-skills section to an MTB racer is an embarrassing discipline mismatch.

### 6. [critical] ×1  (mtb/weekend_warrior)
> Long ride duration is capped at 1.5 hours, but the race is estimated at ~3.3 hours (per fueling data) over 52.2 miles of mountainous Norwegian terrain. A 1.5-hour long ride is only ~45% of race duration. The guide acknowledges the gap in a single sidebar but still frames 1.5 h as the plan ceiling. For a finish-goal athlete on this event, at least one 2.5–3 h ride must be a hard prescription, not an optional footnote — the durability risk is race-defining.

### 7. [critical] ×1  (road/time_crunched_parent)
> Long ride duration ceiling stated as 1.5 hours is wholly inadequate for a 102-mile (~6.4 h) road event. Even for a time-crunched athlete the plan's own fueling data sets estimated race duration at 6.4 h. Calling out '1.5 hours' as the peak long-ride length — without qualification — will leave the athlete completely unprepared for race-day duration and undermines every other credible statement in the guide. The adjacent 'biggest opportunity' box hints at 3–4 h rides but then contradicts the 1.5 h figure rather than resolving it.

### 8. [critical] ×1  (road/time_crunched_parent)
> Zone Distribution automated check returned FAIL, yet the guide was passed to this QA stage. The guide text cannot be approved while a known zone-distribution defect exists in the underlying plan — this is the most common cause of 'gray zone' overtraining the guide itself warns against.

### 9. [major] ×1  (gravel/weekend_warrior)
> The zone chart omits power ranges for Zones 1 and 3 in the printed table. Zone 1 shows '0–102W' but no % FTP or % LTHR columns are filled, and Zone 3 is missing its % LTHR value entirely. An athlete using HR as their primary tool (no power meter confirmed) will be unable to calibrate Zone 3 or Zone 1 by heart rate.

### 10. [major] ×1  (gravel/weekend_warrior)
> The '14 Years Riding' experience entry is used to justify 'Intermediate level' in the methodology rationale, but 14 years of riding experience does not automatically equal intermediate training capacity — and more importantly, the plan never reconciles this with the weekend-warrior persona. A rider with 14 years of experience at 5 h/week is likely well-aerobically developed but time-limited; the guide should acknowledge this nuance rather than defaulting to a generic intermediate label.

### 11. [minor] ×2  (gravel/weekend_warrior, road/time_crunched_parent)
> The athlete's weight (176 lbs / 79.8 kg) and height (5'6") appear in the profile section but were not fields in the submitted athlete JSON — these figures cannot be verified and may be hallucinated or pulled from an incorrect profile, which would be embarrassing if wrong.

### 12. [major] ×1  (road/veteran_podium_chaser)
> FTP test warmup sequence contains a contradictory internal step: the guide prescribes a '5-minute hard opener at RPE 8-9' followed by '10 minutes easy recovery' before the 20-minute test. While a pre-load effort is a legitimate technique, RPE 8-9 is described in the zone chart as Zone 5 / VO2max — that is far too hard for a pre-load opener and contradicts best-practice (typically RPE 6-7 / Zone 3-4 for 3-5 min). This could cause the athlete to blow up before the actual test, producing an artificially low FTP and 6 weeks of under-zoned training.

### 13. [major] ×1  (road/veteran_podium_chaser)
> The 'off days' copy reads 'Off days: Wednesday, Monday' — listing Wednesday before Monday is confusing and non-chronological. More importantly, this gives the athlete two consecutive-or-near-consecutive off days mid-week and at the start of the week, which needs to be confirmed as intentional given the 5-training-day / 10h target; it may simply be a field-population error (days listed in wrong order or wrong days pulled from the questionnaire).

### 14. [major] ×1  (road/time_crunched_parent)
> The fueling section references a 4.6-hour race duration (from plan JSON) and 90 g/hr carbs, but the truncated guide text never explicitly presents this to the athlete in the visible excerpt. More importantly, the guide states the long ride peaks at '2.1-3.5 hours' — for a 102-mile podium goal on a rider averaging ~7 h/week, 3.5 hours is a reasonable cap, but the guide should explicitly bridge this to the ~4.5-5 hour race duration so the athlete understands the intentional gap and doesn't panic.

### 15. [major] ×1  (road/time_crunched_parent)
> The athlete's goal is listed as 'podium' for a 102-mile mass-participation event (Tour de Tucson regularly draws 2,000+ starters). The guide text says 'Success looks like: Compete' — this directly contradicts the athlete's stated goal of podium and will feel dismissive to a motivated, FTP-265W athlete who paid for a goal-specific plan.

### 16. [minor] ×2  (gravel/time_crunched_parent, road/time_crunched_parent)
> The 'Road Skills' section is listed in the Table of Contents but is not present in the truncated guide text — if its content includes anything beyond road-specific skills (e.g. gravel cornering, MTB body position), that would be a discipline mismatch. Cannot confirm from excerpt alone, but flags for review.

### 17. [major] ×1  (gravel/time_crunched_parent)
> Zone 2 power range is missing its lower percentage label in the zone chart (only '56-75% FTP' is shown without the watts-to-% cross-check row being complete for Zone 1 — Zone 1 shows watts only, no % FTP or LTHR columns). This inconsistency means an athlete using a different FTP after retesting cannot self-calculate Zone 1 boundaries, and it looks like a data-render drop-out.

### 18. [major] ×1  (gravel/masters_returner)
> Zone Distribution check FAILED in the automated preview. The guide describes the distribution as 'roughly 70% easy,' which is directionally correct for Time-Crunched methodology, but the system flagged an actual zone-distribution violation in the calendar. This contradiction — the guide text reassuring the athlete that zones are managed correctly while the calendar fails the check — means the athlete could be handed miscalibrated zone prescriptions. The calendar data must be audited and reconciled before sending.

### 19. [major] ×1  (gravel/masters_returner)
> FTP test frequency flagged WARN. Time-Crunched methodology over 17 weeks should include at least two retest points; if the calendar has only one (or the spacing is wrong for this athlete's phase structure), the guide's statement that 'the test result sets ALL your training zones for the next 6 weeks' could leave the athlete training on stale zones for most of the plan. The calendar must confirm correct retest placement.

### 20. [major] ×1  (mtb/weekend_warrior)
> Birkebeinerrittet is a famous, physically demanding mountain MTB race with significant climbing (Rena to Lillehammer includes major sustained ascents). The plan guide never mentions climbing, seated power production on long gradients, or descending technique — all central skills for this specific event. Generic 'MTB' framing undersells what the athlete is signing up for.

### 21. [major] ×1  (mtb/weekend_warrior)
> TSS Progression check returned WARN in preview checks, yet the guide text contains no acknowledgment of this flag or any coaching note explaining why the progression is irregular or how the athlete should interpret it. A WARN-level issue should be surfaced to the athlete or resolved before sending.

### 22. [major] ×1  (road/time_crunched_parent)
> The claim that 'roughly 70% of riding stays genuinely easy' directly contradicts the Time-Crunched methodology. Time-Crunched training is explicitly characterised by a higher proportion of intensity (typically 20–25% or more) and fewer total hours — that is its entire raison d'être. Citing a traditional 80/20 or polarised split as the distribution for a Time-Crunched plan is factually wrong and will confuse an experienced (11-year) athlete who may already know the methodology.

### 23. [major] ×1  (road/time_crunched_parent)
> Off days listed as 'Saturday and Tuesday' — yet the plan JSON states the long ride is on Sunday. Protecting a Sunday long ride while making Saturday a full off day is defensible, but for a time-crunched parent with only 5 h/week this is a significant structural choice that is never explained or justified in the guide text, creating potential confusion.

### 24. [minor] ×1  (gravel/weekend_warrior)
> The 'G Spot' zone label (zone GS between Tempo and Threshold) uses informal branding that some athletes — particularly older or more conservative ones — may find unprofessional or confusing. While it has precedent in some coaching systems, it should be flagged for the 53-year-old weekend-warrior audience.

### 25. [minor] ×1  (gravel/time_crunched_parent)
> Countdown states '81 days from today' — this is a hard-coded number that will be wrong the moment the email is sent on any day other than the generation date. Either dynamically compute it at send time or remove it entirely to avoid confusing the athlete.
