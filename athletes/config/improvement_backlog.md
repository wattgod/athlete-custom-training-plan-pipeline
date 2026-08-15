# Improvement backlog — 2026-08-15

**Quality 0.27** · avg coach 5.62/10 · contract pass 100% · load 15.88/plan · 15 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×2  (gravel/time_crunched_parent, mtb/weekend_warrior)
> 'Category 5 to Category 1 Pathway' section is listed in the table of contents and presumably appears in the full guide. This is road-racing licence category language (USA Cycling / British Cycling cat system). It is completely irrelevant — and confusing — for a gravel gran fondo athlete. It should not exist in this plan.

### 2. [critical] ×2  (gravel/masters_returner, gravel/time_crunched_parent)
> 'Road Race Strategy' section appears in the table of contents. A UCI Gran Fondo Loutraki competitor needs gravel/gran-fondo race strategy, not road criterium or road-race tactics. Wrong-discipline content that will undermine athlete trust and coaching credibility.

### 3. [critical] ×1  (gravel/masters_returner)
> Road-race content included for a gravel athlete: the table of contents lists 'Road Race Strategy' and 'Category 5 to Category 1 Pathway' — these sections have no place in a gravel gran fondo plan and will confuse or embarrass the customer.

### 4. [critical] ×1  (gravel/masters_returner)
> 'Road Skills' section heading appears in the ToC instead of gravel-specific skills (e.g., loose-surface descending, gravel cornering, rough-terrain pacing). For a 99-mile gravel event in Morocco this is a meaningful omission AND a discipline mismatch.

### 5. [critical] ×1  (gravel/masters_returner)
> 'Road Race Strategy' and 'Category 5 to Category 1 Pathway' sections are listed in the Table of Contents and presumably appear in the full guide. This athlete is a gravel gran fondo finisher, not a criterium or road-race category racer. These sections are entirely wrong for the discipline and goal, and the Cat 5–Cat 1 pathway is embarrassing and potentially confusing to a masters gravel athlete.

### 6. [critical] ×1  (gravel/masters_returner)
> 'Road Skills' section appears in the Table of Contents. While some road-skills content overlaps with gravel (e.g., descending), a section by this name risks importing road-specific drills (pace-line etiquette, criterium cornering, echelon riding) that are irrelevant or misleading for a gravel event. This section must be replaced with gravel-specific skills content (loose-surface cornering, tire pressure management, technical descending on gravel, etc.).

### 7. [critical] ×1  (gravel/masters_returner)
> Section titled 'Road Race Strategy' is present in the table of contents (and presumably the body) for a GRAVEL discipline athlete. This is a flat-out discipline mismatch — gravel athletes do not race under road-race tactical conventions, and sending road-race strategy to a gravel rider is embarrassing and confusing.

### 8. [critical] ×1  (gravel/masters_returner)
> 'Category 5 to Category 1 Pathway' section is included. This is a USA Cycling road racing licensing pathway and is entirely irrelevant — even nonsensical — for a masters gravel athlete whose goal is simply to finish the Taiwan KOM Challenge. It should not exist in this plan.

### 9. [critical] ×1  (mtb/weekend_warrior)
> Discipline mismatch in content sections: the guide includes 'Road Skills,' 'Road Race Strategy,' and a 'Category 5 to Category 1 Pathway' section. This athlete is an MTB rider targeting a Gran Fondo, not a road criterium racer. These sections are wrong for the discipline and will confuse or mislead the athlete.

### 10. [critical] ×1  (mtb/weekend_warrior)
> Off-day and long-ride schedule is incoherent: the guide states 'Off days: Saturday, Sunday — Long rides: Monday.' Assigning the long ride to Monday (first day back after two consecutive off days) is an unusual and unexplained structure that contradicts normal training week logic and would strike any experienced athlete as a red flag. If intentional, it needs justification; if a generation error, it must be corrected.

### 11. [critical] ×1  (gravel/masters_returner)
> A 'Category 5 to Category 1 Pathway' section is included in the table of contents and presumably in the guide body. This is a USA Cycling road-racing licensing concept that is entirely irrelevant and misleading for a gravel athlete targeting a finisher event. It must be removed.

### 12. [critical] ×1  (gravel/veteran_podium_chaser)
> Discipline mismatch — the guide includes a 'Road Race Strategy' section and a 'Category 5 to Category 1 Pathway' section. This athlete is a gravel racer targeting the Tour de Tucson, not a road criterium or road circuit racer. These sections are copied from a road racing template and are wrong for this athlete.

### 13. [critical] ×1  (gravel/veteran_podium_chaser)
> 'Road Skills' section heading is visible in the table of contents. For gravel, skills content should cover gravel-specific cornering, loose-surface descending, and tire/pressure management — generic road skills copy is inappropriate and potentially embarrassing.

### 14. [critical] ×1  (road/weekend_warrior)
> Race day listed as 'Monday, November 30, 2026' — November 30, 2026 is a MONDAY, which is actually correct, but the guide header and race-day callout should double-check this is what the athlete expects; more critically the verified DB entry confirms this date, yet the day-of-week label should be verified programmatically — if the generation logic simply stamped 'Monday' without calculation this could silently be wrong for other plans. Flag for pipeline review.

### 15. [critical] ×1  (road/weekend_warrior)
> 'Category 5 to Category 1 Pathway' appears in the Table of Contents and presumably in the full guide body. This is a USA Cycling road racing licence progression section — completely irrelevant and potentially confusing for a weekend warrior whose sole goal is to finish a gran fondo. It implies a racing career pathway this athlete never asked for and did not profile into.

### 16. [major] ×1  (gravel/masters_returner)
> Weight (153 lbs / 69.4 kg) and height (5'10") appear in the profile but the athlete data JSON contains no weight or height fields — these values were fabricated by the generator and must not be presented as 'your profile' data to the customer.

### 17. [major] ×1  (gravel/masters_returner)
> Zone 1 power upper bound is listed as '0–101W' but with FTP = 185 W, Zone 1 should top out at roughly 55% FTP ≈ 102 W — the upper figure of 101 W is one watt low and the lower bound is 0 W with no %FTP anchor shown, making the chart internally inconsistent with the other zones that do show %FTP. Minor numerically but looks sloppy and erodes trust.

### 18. [major] ×1  (gravel/masters_returner)
> Off days are listed as 'Tuesday, Monday' in that order. Listing them out of calendar order (Monday should precede Tuesday) reads as a generation artifact and looks unprofessional to an attentive athlete.

### 19. [major] ×1  (gravel/masters_returner)
> Off-day list reads 'Tuesday, Friday, Wednesday' — three separate off days listed in a non-sequential, oddly ordered way for a 4-riding-day week. If correct, it should read 'Tuesday, Wednesday, Friday' (chronological); if the plan only has 2 off days it contradicts the 4-day riding structure stated in the same paragraph. Needs reconciliation with the actual calendar.

### 20. [major] ×1  (gravel/time_crunched_parent)
> Fueling: the plan states hourly_carbs = 60 g and duration = 3.3 h (i.e. ~198 g total carbs targeted). For a 47-year-old female going for a podium at 70 miles of gravel, 60 g/h is on the low end of current best practice (most performance-focused protocols now recommend 80–90 g/h for trained athletes with gut training). The guide should at minimum acknowledge this is a conservative starting point and flag gut-training progression — as written it presents 60 g/h as a fixed prescription without caveat.

### 21. [major] ×1  (gravel/time_crunched_parent)
> Zone Distribution flagged WARN by the automated gate and is never addressed or explained in the guide text. A paying athlete who reads 'Zone Distribution: WARN' in any context — or who notices the distribution is off — will have no coach rationale to fall back on. The guide should either correct the distribution or explicitly explain why the mix is intentional for this methodology.

### 22. [minor] ×2  (gravel/masters_returner, gravel/time_crunched_parent)
> 'Road Skills' section in the table of contents is ambiguous — for a gravel event this should be explicitly gravel-specific (loose surface cornering, descending on dirt, tire pressure management) not generic road skills. Minor but worth confirming the content matches the discipline.

### 23. [major] ×1  (mtb/weekend_warrior)
> No MTB-specific content anywhere in the visible guide: for an MTB discipline there should be references to technical trail skills, climbing/descending technique, tire pressure, tubeless setup, trail nutrition logistics, and riding position — none of these appear. The 'Equipment Checklist' and 'Skills' sections (referenced in the table of contents) presumably exist but the visible content shows only road-oriented skills context.

### 24. [major] ×1  (mtb/weekend_warrior)
> Race discipline label ambiguity: UCI Gran Fondo Loutraki is a road event (gran fondos are road races), yet the plan's discipline is tagged 'mtb.' If the athlete truly entered an MTB event, the race may be mis-identified; if the race is a road gran fondo, the discipline tag is wrong and the entire plan methodology and skills content should shift to road. Either way, this contradiction must be resolved before sending.

### 25. [minor] ×2  (gravel/veteran_podium_chaser, mtb/weekend_warrior)
> Long ride duration range cited as '2.2–3.8 hours' in the Weekly Structure section — the upper bound (3.8 h) is reasonable for a 70-mile race estimated at ~4.6 hours, but the lower bound description should clarify this is the Week 1 starting point, not a ceiling, to avoid the athlete under-preparing.
