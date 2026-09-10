# Improvement backlog — 2026-09-10

**Quality 1.55** · avg coach 5.75/10 · contract pass 100% · load 13.0/plan · 9 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×2  (gravel/ambitious_first_timer, road/masters_returner)
> Table of Contents and guide body include a 'Category 5 to Category 1 Pathway' section — this is a USA Cycling road-racing licence category system that is entirely irrelevant to a gravel event. It should not exist in this guide and will confuse or embarrass the athlete.

### 2. [critical] ×1  (gravel/veteran_podium_chaser)
> Table of contents lists 'Road Race Strategy' and 'Category 5 to Category 1 Pathway' sections — this is a GRAVEL race plan. Road-racing category progression (Cat 5 to Cat 1) is USA Cycling road racing nomenclature with zero relevance to GFNY Miami gravel. This is a direct discipline mismatch that would embarrass the business and confuse the athlete.

### 3. [critical] ×1  (gravel/veteran_podium_chaser)
> 'Road Skills' appears as a standalone section in the table of contents. Gravel-specific skills (loose surface cornering, technical descending, gravel handling) should replace generic road skills content for a gravel race plan.

### 4. [critical] ×1  (gravel/ambitious_first_timer)
> 'Road Race Strategy' section is listed in the contents and present in the guide. This athlete is racing a gravel event (L'Étape Ciudad de México), not a road criterium or road race. Discipline-specific strategy content is wrong for the event.

### 5. [critical] ×1  (gravel/ambitious_first_timer)
> 'Category 5 to Category 1 Pathway' section is listed in the table of contents and presumably elaborated later in the guide. This is a road racing categorization framework (USA Cycling license categories) that is entirely irrelevant to a gravel gran fondo. A paying first-timer preparing for Gran Fondo Guadeloupe will be confused or misled by this content.

### 6. [critical] ×1  (gravel/masters_returner)
> Table of contents and apparent body content include 'Road Race Strategy' and a 'Category 5 to Category 1 Pathway' section — both are entirely wrong for a gravel gran fondo athlete with a goal of 'finish.' This content belongs to a road criterium/road-race plan and is embarrassing boilerplate bleed-through that will confuse and undermine trust with this customer.

### 7. [critical] ×1  (gravel/masters_returner)
> 'Road Skills' section (TOC) may be acceptable generically, but combined with 'Road Race Strategy' and 'Cat 5–1 Pathway,' the entire skills/strategy block appears to be road-racing template copy. A gravel gran fondo plan should address gravel-specific skills: loose-surface cornering, descent technique on dirt, tyre pressure management, self-sufficiency/navigation — none of which are visible in the truncated text.

### 8. [critical] ×1  (gravel/time_crunched_parent)
> Road racing content included for a gravel athlete: the table of contents lists 'Road Race Strategy' and 'Category 5 to Category 1 Pathway' sections. These are discipline-wrong and undermine credibility with a gravel gran fondo participant — a paying customer will immediately notice this.

### 9. [critical] ×1  (gravel/time_crunched_parent)
> Athlete's stated goal is 'podium' but the guide renders it as only 'Compete' under Goals & Blindspots. This is the most personally motivating part of the plan; getting it wrong signals the plan is generic and not built for this athlete.

### 10. [minor] ×4  (gravel/ambitious_first_timer, gravel/time_crunched_parent, gravel/veteran_podium_chaser, road/veteran_podium_chaser)
> Long ride duration range cited as '2.3-3.8 hours' in the Weekly Structure section. For a 3.29h projected race duration, the upper end of 3.8h is reasonable, but the lower end of 2.3h in early base weeks should be explicitly flagged as a base-phase figure to avoid confusion about whether this range applies across all weeks.

### 11. [major] ×2  (road/masters_returner, road/veteran_podium_chaser)
> The automated preview flagged 'Taper Intensity: WARN' and this was not resolved or explained anywhere in the guide. A taper section that carries an unresolved warning should not be sent to a paying customer without a coach reviewing and either fixing the intensity prescription or adding an explicit rationale for why the taper deviates from the norm.

### 12. [major] ×1  (gravel/veteran_podium_chaser)
> Weekly Volume check flagged WARN and TSS Progression flagged WARN in the preview checks — neither issue is addressed or explained anywhere in the visible guide text. For a 14h/week athlete these are significant structural signals that should be resolved before sending.

### 13. [major] ×1  (gravel/veteran_podium_chaser)
> FTP Test Frequency flagged WARN. The plan establishes RPE-only zones with a single Week 1 field test for an 8-week block targeting a podium. For an experienced racer at this volume, no follow-up re-test or anchor update is mentioned, leaving the athlete potentially training on a stale anchor for 7 weeks.

### 14. [major] ×1  (gravel/veteran_podium_chaser)
> The methodology rationale states '15 years of cycling experience at Intermediate level' — a 15-year veteran should be classified as advanced/experienced, not intermediate. This contradicts the 'veteran_podium_chaser' persona and could undermine athlete confidence in the plan's calibration.

### 15. [major] ×1  (gravel/ambitious_first_timer)
> Weekly Volume and TSS Progression both flagged WARN in preview checks, yet the guide body contains no acknowledgement or explanation of this. A paying athlete receiving a plan with known volume/TSS issues deserves a coach note explaining the trade-off or the cap that was applied.

### 16. [major] ×1  (gravel/ambitious_first_timer)
> The guide references 'Road Skills' as a standalone section in the contents. While gravel does require skills, the section title is ambiguous and — given the other road-racing content present — risks containing road-specific (e.g. criterium cornering, peloton positioning) rather than gravel-specific skills content. Needs verification and likely renaming to 'Gravel Skills'.

### 17. [major] ×1  (gravel/veteran_podium_chaser)
> Experience level mislabeled: the JSON persona is 'veteran_podium_chaser' (9 years, experienced racer) but the guide text calls her 'Intermediate level' in the methodology rationale. This is directly contradicted by the athlete data and will undermine trust with an experienced racer.

### 18. [major] ×1  (gravel/veteran_podium_chaser)
> FTP test validity window is wrong: the guide states 'The test result sets ALL your training zones for the next 6 weeks,' but the plan is only 9 weeks long and schedules at least one test. A 6-week window claim doesn't align with the plan length or any standard retest cadence flagged by the FTP Test Frequency WARN — this should say something like 'until your next retest' or cite the actual retesting schedule.

### 19. [major] ×1  (gravel/veteran_podium_chaser)
> Fueling recommendation appears low for the expected race duration: the plan calculates ~5.3 h race duration but specifies only 62 g carbs/hour. Current sports-science guidance for efforts of this intensity and duration in a podium-chasing athlete supports 80–100 g/h (with trained gut). For a competitive female masters athlete targeting a podium, 62 g/h is a meaningful under-fueling risk that could cost the race result — this should at minimum be flagged as a floor, not a ceiling.

### 20. [major] ×1  (gravel/veteran_podium_chaser)
> Three automated pre-flight checks are flagged WARN (Weekly Volume, FTP Test Frequency, Taper Intensity) but the guide text never addresses or explains these deviations. A paying athlete receiving a plan where automated checks fired warnings deserves either a corrected plan or explicit coach commentary acknowledging and justifying the deviation.

### 21. [major] ×1  (gravel/ambitious_first_timer)
> 'Road Race Strategy' appears as a section heading in the table of contents. This athlete is doing a gravel gran fondo, not a road race. The correct framing should be gravel/gran fondo pacing and race strategy. Sending road-race tactical content to a gravel athlete is discipline-wrong and undermines credibility.

### 22. [major] ×1  (gravel/masters_returner)
> Off days listed as 'Wednesday, Sunday, Thursday' — that is three off days in a 7-day week, leaving only four training days, which is consistent with the '4 training days' statement. However, listing Sunday as an off day when Saturday is the designated long-ride day is fine, but calling out three named rest days in the at-a-glance summary will read oddly to athletes expecting a typical Mon–Fri structure. More importantly, the order (Wed, Sun, Thu) is non-chronological and will cause confusion — should be listed in day order.

### 23. [major] ×1  (gravel/masters_returner)
> Fueling section references an estimated race duration of ~6.69 hours (from plan JSON: duration_h ≈ 6.69) and 57 g carbs/hour, but the guide text does not surface these numbers in the Nutrition Strategy section visible in the truncated text. For a masters athlete whose #1 goal is 'finish,' race-day fueling specifics (total carb target, on-bike eating schedule, product suggestions) are a key deliverable and appear absent or buried.

### 24. [major] ×1  (road/masters_returner)
> The Zone chart omits % FTP values for Zone 1 (shown only as '0–126 W' with no percentage column entry) and is also missing % LTHR for Zone 1, breaking the parallel structure of the table. Minor in isolation, but for a paying masters athlete who may train by HR, missing reference ranges in Zone 1 look like a production error.

### 25. [major] ×1  (road/veteran_podium_chaser)
> 'Category 5 to Category 1 Pathway' section appears in the table of contents and presumably in the body. This is a USA Cycling domestic racing category ladder concept that is irrelevant and potentially confusing for a New Zealand sportive/gran fondo (Lake Taupo Cycle Challenge is a mass-participation event, not a licensed road race with cat upgrades). It signals the plan was not properly filtered for event type and geography, and will undermine athlete trust.
