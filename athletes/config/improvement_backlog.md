# Improvement backlog — 2026-08-27

**Quality 0.71** · avg coach 5.25/10 · contract pass 88% · load 13.25/plan · 12 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×1  (road/masters_returner)
> 'Category 5 to Category 1 Pathway' appears in the table of contents and presumably as a full section. This is a USAC/USA Cycling road racing licence-upgrade pathway — it is completely irrelevant and potentially confusing for a masters athlete whose stated goal is simply to finish a gran fondo. It implies competitive racing categories that do not apply to this event or this athlete, and it is the wrong discipline content for a gran fondo finisher plan.

### 2. [critical] ×1  (mtb/ambitious_first_timer)
> Discipline mismatch — athlete is MTB but the guide contains 'Road Skills' and 'Road Race Strategy' sections, plus a 'Category 5 to Category 1 Pathway' section. These are wrong-discipline content that will confuse and mislead the athlete; a UCI Gran Fondo on a road course may involve road riding, but the registered discipline is MTB and road-racing category progression content is wholly irrelevant.

### 3. [critical] ×1  (mtb/ambitious_first_timer)
> Weekly Volume check FAILED per the preview_checks data. The guide never flags or explains this — it simply claims the plan is 'calibrated to your available time.' A volume failure means at least one week likely exceeds or undershoots the athlete's 11 h target in a way the automated gate caught; sending the plan as-is risks overtraining or under-preparation without any coach acknowledgment of the discrepancy.

### 4. [critical] ×1  (gravel/time_crunched_parent)
> 'Road Race Strategy' and 'Category 5 to Category 1 Pathway' sections appear in the table of contents and, by implication, in the body. This athlete is a gravel gran fondo finisher, not a road criterium/circuit racer. Cat 5–1 licensing pathway content is entirely wrong for the discipline and goal, and would be deeply confusing and embarrassing to send.

### 5. [critical] ×1  (gravel/time_crunched_parent)
> The fueling section states 53 g carbs/hour yet the plan_facts show a ~5.7 h estimated race duration. 53 g/h is notably below current evidence-based recommendations (typically 60–90 g/h for events of this length) and conflicts with the 'Nutrition Strategy' section that presumably advises higher intake. If 53 g/h is intentional (gut sensitivity, etc.) it must be explicitly flagged and justified; as presented it appears to be an uncorrected low default.

### 6. [critical] ×1  (gravel/weekend_warrior)
> The guide states '72 days from today' as a race countdown, but the plan start date is 2026-08-31 and the race is 2026-11-07 — that is 68 days from plan start, and 10 weeks is 70 days. '72 days' appears to be a stale or miscalculated dynamic field. If this email goes out on the wrong generation date, the countdown will be wrong and could undermine athlete trust in every other number in the document.

### 7. [critical] ×1  (mtb/weekend_warrior)
> Discipline mismatch: the athlete profile says 'mtb' but the race 'Wild Gravel' in Gnowangerup is a gravel event, and the guide explicitly includes a 'Gravel Skills' section. The plan must either (a) confirm this is a gravel bike event and relabel the discipline, or (b) confirm MTB and remove/replace the gravel skills content. Sending a gravel skills section to someone racing on an MTB — or vice versa — is a coaching error.

### 8. [critical] ×1  (mtb/weekend_warrior)
> Long ride duration is capped at 1.5 hours (per the guide's own text) for a race projected at ~5.5 hours. The guide acknowledges this is inadequate but offers no structural remedy — no adjusted schedule, no alternative long-ride guidance. This leaves the athlete with a plan the guide itself admits is under-preparing her for race-day durability.

### 9. [critical] ×1  (mtb/ambitious_first_timer)
> Table of Contents lists 'Road Race Strategy' and 'Category 5 to Category 1 Pathway' sections — these are pure road-racing content (USA Cycling licensing categories) and have zero relevance to an MTB gran fondo athlete. Sending this to an MTB rider is a significant credibility failure.

### 10. [critical] ×1  (mtb/ambitious_first_timer)
> 'Road Skills — Road Race Strategy' and 'Category 5 to Category 1 Pathway' sections (visible in the TOC) are wrong-discipline content. The athlete is registered for an MTB event; the plan must contain MTB-specific skills content (singletrack technique, braking, climbing/descending body position, etc.), not criterium or road race tactics and USA Cycling upgrade points.

### 11. [critical] ×1  (gravel/time_crunched_parent)
> Off-day listing is self-contradicting and nonsensical: 'Off days: Saturday, Friday, Sunday' lists three days off in a 7-hour, 4-training-day week, which leaves only Monday, Tuesday, Wednesday, Thursday as training days — but Saturday and Sunday cannot simultaneously be off days while the guide also says long rides are on Wednesday. More fundamentally, listing Friday AND Saturday AND Sunday as off days in the same sentence is almost certainly a generation error (two separate off-day slots merged into three days), and it will immediately confuse the athlete.

### 12. [critical] ×1  (gravel/time_crunched_parent)
> Countdown timer says '70 days from today' but the plan start date is 2026-08-31 and race date is 2026-11-05 — that is 66 days, not 70. The document also calls November 5 a Thursday, but 2026-11-05 is a Thursday, so that part is correct. However the 70-day figure is wrong and will make a detail-oriented athlete distrust every other number in the guide.

### 13. [major] ×1  (road/masters_returner)
> The zone table includes a non-standard row labelled 'GS G Spot' (88-93% FTP). While the concept of a threshold-adjacent stimulus zone exists in some methodologies, the name 'G Spot' is unprofessional and inappropriate in a document sent to a paying customer. It should be renamed (e.g. 'Sweet Spot' or 'Sub-Threshold') or removed.

### 14. [major] ×1  (road/masters_returner)
> The preview check flags 'Taper Intensity: WARN' but the guide text shows no evidence this was addressed or explained to the athlete. A 61-year-old masters returner needs correct taper guidance; an unresolved taper-intensity warning means the calendar may have erroneously high intensity in race week, which could send the athlete to the start line fatigued.

### 15. [major] ×1  (road/masters_returner)
> The preview check also flags 'Zone Distribution: WARN'. The guide body states '~70% easy riding' for Time-Crunched, but the WARN suggests the generated calendar may not actually honour that distribution. The discrepancy between the guide's claims and the underlying calendar numbers is not reconciled anywhere in the visible text.

### 16. [major] ×1  (mtb/ambitious_first_timer)
> Taper Intensity flagged WARN in preview_checks but is not addressed anywhere in the guide text. The taper section says 'short, sharp efforts keep the engine awake' with no qualification, yet the system flagged intensity may be too high or misstructured in the taper. A paying athlete deserves a plan where the taper is confirmed correct, not quietly flagged.

### 17. [major] ×1  (mtb/ambitious_first_timer)
> Equipment checklist lists 'road bike, in good working order' as the mandatory bike for an MTB athlete. An MTB athlete needs an MTB listed; a gran fondo on a road course might use a road or gravel bike, but the plan should explicitly address which bike is appropriate given the MTB discipline tag and road-course event — not silently default to 'road bike.'

### 18. [major] ×1  (gravel/time_crunched_parent)
> 'Road Skills' section in the table of contents is ambiguous — acceptable if it covers gravel-specific handling (loose surface, descending dirt, navigation), but if it contains road-crit cornering or bunch-sprint positioning content it is wrong for this athlete and discipline. Cannot approve without confirming content.

### 19. [major] ×1  (gravel/time_crunched_parent)
> The persona is 'time-crunched parent' yet the weekly structure section states '5 training days, 3 of which are key sessions' with a long ride up to 4.5 hours. No acknowledgment is made of the logistical difficulty a time-crunched parent faces fitting a 4.5-hour Saturday ride; the guide should at minimum flag this and offer a contingency split or indoor alternative.

### 20. [major] ×1  (gravel/time_crunched_parent)
> The 'Weekly Volume' preview check flagged WARN but the guide text contains no visible explanation or caveat to the athlete about what triggered that warning. A paying athlete receiving a WARN-flagged plan deserves an honest note (e.g., 'some weeks approach the upper edge of your stated 8-hour budget — treat those as targets, not minimums').

### 21. [major] ×1  (gravel/weekend_warrior)
> Weight (145 lbs / 65.8 kg) and height (5'4") appear in the athlete profile section, but the source JSON contains no weight or height fields for this athlete. These values appear to have been fabricated or pulled from a default template. Sending invented biometric data to a paying customer is both inaccurate and a credibility risk.

### 22. [major] ×1  (gravel/weekend_warrior)
> The Weekly Volume preview check returned WARN (not PASS). The guide text does not address or acknowledge any volume concern, and the truncated text prevents full verification. A WARN on weekly volume for a 54-year-old masters athlete at 7 hrs/week with high life stress is a flag that must be resolved before sending — either the volume is genuinely appropriate and the warning is a false positive that should be cleared, or the plan is over-volumed relative to the athlete's capacity.

### 23. [major] ×1  (mtb/weekend_warrior)
> Fueling recommendation of 54 g/hr carbohydrate is low for a 5+ hour effort. Current sports nutrition consensus for efforts of this duration is 80–90+ g/hr (with multi-transport carbohydrates). Recommending 54 g/hr for a ~5.5-hour race risks bonking and is an embarrassing number to put in a paid coaching guide.

### 24. [major] ×1  (mtb/weekend_warrior)
> The guide states 'the test result sets ALL your training zones for the next 6 weeks' in an 8-week plan. With only one FTP test flagged and a WARN on FTP Test Frequency, this phrasing is both internally inconsistent with the plan length and potentially misleading about when/whether to retest.

### 25. [major] ×1  (mtb/ambitious_first_timer)
> The TOC includes 'Women-Specific Considerations' as a named section, but the truncated guide text does not show it — cannot confirm it actually exists and is substantive rather than a placeholder heading, which would be another embarrassing gap for a paying female athlete.
