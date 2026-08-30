# Improvement backlog — 2026-08-29

**Quality 0.12** · avg coach 5.88/10 · contract pass 62% · load 15.0/plan · 12 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×1  (road/time_crunched_parent)
> The table of contents and guide body include a 'Category 5 to Category 1 Pathway' section. This athlete's goal is simply to FINISH a 102-mile gran fondo/road event — he is not a licensed racer seeking upgrade points. This section is flatly irrelevant and risks confusing or misleading the customer about what they signed up for.

### 2. [critical] ×1  (mtb/ambitious_first_timer)
> Discipline mismatch — Equipment Checklist specifies 'road bike, in good working order' for an MTB athlete. The correct entry should be a mountain bike. Sending this to an MTB racer is embarrassing and confusing.

### 3. [critical] ×1  (mtb/ambitious_first_timer)
> Discipline mismatch — 'Road Race Strategy' and 'Category 5 to Category 1 Pathway' sections appear in the table of contents (and presumably in the full document). These are road-racing concepts entirely irrelevant to an MTB/gran-fondo athlete and signal that road-race boilerplate was injected wholesale.

### 4. [critical] ×1  (mtb/ambitious_first_timer)
> Fueling math is wrong. The plan states '45g/hr × race duration = 256g total race carbs.' The computed race duration from the JSON is ~5.7 hours. 45 × 5.7 ≈ 257g — that checks out. However, the stated race-day range is '38–52g/hr,' yet 45g/hr is already at the low end of current sports-science recommendations for a ~5.7h effort (most guidelines now suggest 60–90g/hr for efforts over ~2.5h). While the hourly target is a coach's choice, calling 45g/hr a race-day target for a nearly 6-hour event without flagging that it is conservative risks athlete under-fueling — and the range given (38–52) skews even lower. At minimum the guide should acknowledge this is a starter/conservative target.

### 5. [critical] ×1  (mtb/ambitious_first_timer)
> Discipline mismatch — plan JSON declares discipline 'mtb', yet the guide includes 'Road Race Strategy' and a 'Category 5 to Category 1 Pathway' section. These are road-racing constructs that have no place in an MTB plan and will confuse or mislead the athlete.

### 6. [critical] ×1  (mtb/ambitious_first_timer)
> Race vs. discipline mismatch — Cycling Shimanami is a verified paved road/island-hopping event (Imabari to Onomichi). Calling this an MTB plan is wrong regardless of what the JSON says; the guide should reconcile the discipline to match the actual event or flag the conflict rather than silently propagate 'mtb' framing.

### 7. [critical] ×1  (road/masters_returner)
> Weekly Volume check is a hard FAIL per the automated preview. The guide text does not surface a corrected or explained volume figure, meaning the prescribed weekly hours almost certainly deviate from the athlete's 9 h/week target in the actual calendar. This is the single most important number in a training plan and it cannot go out unresolved.

### 8. [critical] ×1  (road/masters_returner)
> 'Category 5 to Category 1 Pathway' is listed as a content section in the table of contents. This is a USA Cycling road racing license-upgrade framework that is completely irrelevant to a masters athlete whose stated goal is simply to 'finish' a gran fondo (L'Étape). It belongs to a competitive road-racing plan, not this one, and will confuse or mislead the customer.

### 9. [critical] ×1  (gravel/veteran_podium_chaser)
> Table of contents and guide body include a 'Road Race Strategy' section and a 'Category 5 to Category 1 Pathway' section — these are road-racing constructs that have no place in a gravel gran fondo plan. Sending cat-upgrade pathway content to a gravel athlete is factually wrong and embarrassing.

### 10. [critical] ×1  (gravel/veteran_podium_chaser)
> The automated Weekly Volume check hard-FAILed and the guide is being reviewed for send — the volume issue must be diagnosed and corrected (or explicitly overridden with justification) before the plan reaches the athlete.

### 11. [critical] ×1  (gravel/time_crunched_parent)
> Section titled 'Road Race Strategy' and the 'Category 5 to Category 1 Pathway' are listed in the table of contents and apparently present in the guide body. These sections are entirely wrong for a gravel gran fondo athlete — road-race tactics and USA Cycling category upgrade pathways are irrelevant and will confuse or embarrass the customer.

### 12. [critical] ×1  (gravel/time_crunched_parent)
> 'Road Skills' section header in the TOC likely maps to road-specific cornering/peloton content rather than gravel-specific skills (loose surface cornering, technical descending, gravel line choice). For a gravel event this content must be discipline-correct.

### 13. [major] ×2  (gravel/time_crunched_parent, mtb/ambitious_first_timer)
> Equipment checklist specifies 'road bike, in good working order' under MANDATORY gear — correct for this event, but this directly contradicts the MTB discipline label on the cover, creating an internal contradiction the athlete will notice.

### 14. [major] ×1  (road/time_crunched_parent)
> The High Life Stress callout says 'reduce training volume by 20% and eliminate all Zone 4+ work' — but the athlete's persona and health note flag high stress as a baseline condition, not an acute event. Applied literally, this instruction would gut the Build and Peak phases for the entire plan. The guide needs to clarify that this is a week-by-week judgment call, not a blanket instruction for the full 12 weeks.

### 15. [major] ×1  (road/time_crunched_parent)
> TSS Progression and Taper Intensity both flagged WARN in the preview checks but the guide text contains no acknowledgment or coaching note about them. A paying customer deserves to know if the TSS ramp is non-standard or if taper intensity deviates from norms — even a brief coach's note would suffice.

### 16. [major] ×1  (mtb/ambitious_first_timer)
> Gran Fondo Eilat is a road/pavement gran fondo, yet the plan is coded as 'mtb' discipline. If the discipline tag is correct, the guide should contain MTB-specific skills content (trail braking, switchback technique, technical climbing, etc.). If the race is actually a road gran fondo, the discipline tag is wrong and Road Skills/Road Race Strategy sections should be retained — but then the Cat 5–Cat 1 pathway is still wrong for a gran-fondo finisher. Either way, the discipline/content alignment needs resolving before sending.

### 17. [major] ×1  (mtb/ambitious_first_timer)
> The 'Road Skills' section in the table of contents is listed as generic content but is never contextualised for MTB or gravel. If this is truly an MTB plan, it must cover trail-specific technical skills, not road cornering or peloton positioning.

### 18. [major] ×1  (mtb/ambitious_first_timer)
> Zone Distribution preview check is marked FAIL and is never addressed or explained in the guide. A paying customer receiving a plan with a known failed check and no explanation is unacceptable.

### 19. [major] ×1  (mtb/ambitious_first_timer)
> FTP Test Frequency is flagged WARN but the guide text gives no indication of the warning or any mitigation (e.g., only one test scheduled in 8 weeks). This should be acknowledged and justified to the athlete.

### 20. [major] ×1  (road/masters_returner)
> TSS Progression is flagged WARN. While a warn is not a hard stop, the guide contains no acknowledgment or coaching rationale for the irregular TSS ramp — a paying masters athlete should be told why a week looks different, not left to wonder if the plan is broken.

### 21. [major] ×1  (road/masters_returner)
> The guide lists 'Road Skills' and 'Road Race Strategy' as dedicated sections (visible in the table of contents). Strategy content for a mass-participation gran fondo with a finish goal is marginal at best; a 'road race strategy' section implies criterium/peloton tactics that are actively misleading for an L'Étape-style event. Content must be confirmed as fondo-appropriate (pacing, climbing, fueling on course) rather than generic road-race tactics.

### 22. [major] ×1  (gravel/veteran_podium_chaser)
> The table of contents lists 'Road Skills' as a standalone section. For a gravel event this should cover gravel-specific skills (loose surface cornering, tire pressure management, technical descending) — not generic road skills. The section heading signals wrong-discipline content.

### 23. [major] ×1  (gravel/veteran_podium_chaser)
> TSS Progression is WARN and Taper Intensity is WARN. Neither is addressed or acknowledged anywhere in the visible guide text. A coach-authored document should at minimum note how these are handled (e.g., taper intensity strategy) so the athlete isn't left wondering.

### 24. [major] ×1  (gravel/veteran_podium_chaser)
> The long-ride duration range stated in the guide ('2.8–4.7 hours') should be cross-checked against the race's estimated finish time (~4.06 h from the fueling data). A peak long ride of only 2.8 h would be well short of race duration; even 4.7 h is barely adequate. No context or reassurance is given to the athlete about this range.

### 25. [major] ×1  (road/veteran_podium_chaser)
> A 'Category 5 to Category 1 Pathway' section is included in the table of contents and apparently in the guide body. This is a USA Cycling road-racing licence category ladder — it is completely irrelevant to a gran fondo athlete whose goal is a podium finish at a mass-participation event, not upgrading through a racing category system. It will confuse the athlete and undermine credibility.
