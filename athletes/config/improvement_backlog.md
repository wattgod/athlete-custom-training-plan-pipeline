# Improvement backlog — 2026-09-20

**Quality -1.13** · avg coach 5.62/10 · contract pass 50% · load 16.88/plan · 13 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×2  (gravel/ambitious_first_timer, road/masters_returner)
> "Category 5 to Category 1 Pathway" section is listed in the table of contents. This is a road-racing licensing/upgrade pathway that is completely irrelevant to a gran fondo finisher goal. It belongs in a criterium or road-race plan for a racer seeking upgrades, not here. Sending this to a 56-year-old masters gran fondo rider is confusing and embarrassing.

### 2. [critical] ×1  (road/masters_returner)
> Zone Distribution preview check is flagged FAIL, yet the guide text never acknowledges or corrects the failure. The coach narrative says '70% easy' but the actual week-by-week zone distribution is apparently wrong. An unresolved FAIL on a core training-quality gate means zones may be systematically misconfigured for this athlete.

### 3. [critical] ×1  (gravel/ambitious_first_timer)
> 'Road Race Strategy' section is listed in the Table of Contents and appears to be present in the guide — this athlete is doing a gravel gran fondo, not a criterium or road race. Road race tactics (positioning, drafting echelons, attacking fields, etc.) are irrelevant and potentially confusing or embarrassing.

### 4. [critical] ×1  (road/veteran_podium_chaser)
> Weekly Volume check FAILED and Per-Day Duration Cap check FAILED — neither failure is explained or corrected in the guide text. Sending a plan with known automated failures to a paying athlete without resolution is unacceptable regardless of what the failures are.

### 5. [critical] ×1  (road/veteran_podium_chaser)
> 'Category 5 to Category 1 Pathway' is listed in the Table of Contents and appears to be included as a section. This is a USA Cycling licensing/categorization pathway concept that is irrelevant and potentially confusing for an athlete whose stated goal is a podium at a single Gran Fondo-style event. It implies she is racing criteriums/road races on a USA Cycling license — there is no evidence of that — and it distracts from the actual race goal.

### 6. [critical] ×1  (gravel/time_crunched_parent)
> Wrong-discipline content included: 'Road Race Strategy' and 'Category 5 to Category 1 Pathway' sections appear in the table of contents (and presumably in the full guide) for a GRAVEL athlete. These are road-racing constructs that have no place in a gravel plan and will confuse or embarrass the customer.

### 7. [critical] ×1  (gravel/time_crunched_parent)
> 'Road Skills' section is listed generically — if it contains road-racing cornering or criterium tactics rather than gravel-specific skills (loose surface descending, creek crossings, gravel cornering, navigation), it is wrong-discipline content.

### 8. [critical] ×1  (road/weekend_warrior)
> Zone Distribution FAIL from automated pre-check is unresolved. The guide claims '~70% easy riding' for a Time-Crunched methodology, but Time-Crunched training is specifically defined by a polarized/intensity-heavy distribution (typically 80/20 or even more intensity-dense than traditional plans). Claiming 70% Z1-Z2 for a Time-Crunched plan contradicts the methodology's core principle and will confuse an experienced athlete.

### 9. [critical] ×1  (road/weekend_warrior)
> Peak long-ride duration stated as 1.5 hours for a 68-mile race that will take roughly 4.5-5 hours. Even accounting for the 'weekly hours limit' caveat, the plan acknowledges this in a sidebar note but then normalizes a 1.5-hour long ride as acceptable. A 1.5-hour peak long ride for a 68-mile A-race is a fundamental mismatch that should trigger a stronger override or escalation, not just a soft 'biggest opportunity' callout.

### 10. [critical] ×1  (gravel/time_crunched_parent)
> Discipline mismatch — the table of contents lists 'Road Race Strategy' and 'Category 5 to Category 1 Pathway' sections. This is a gravel gran fondo plan; road racing categories and road race tactics are wrong-discipline content and would be embarrassing to send to a gravel athlete.

### 11. [critical] ×1  (road/weekend_warrior)
> Zone Distribution automated check is marked FAIL and the guide provides no explanation or remediation. Sending a plan with a known failing zone distribution check is indefensible — the athlete will accumulate time in the wrong zones.

### 12. [critical] ×1  (road/weekend_warrior)
> plan_weeks (11) is longer than weeks_until_race (10), yet the guide never mentions the delayed start or that the athlete should begin in Week 2. The plan_note clarifies this is intentional, but the guide text is completely silent on it — the athlete will be confused about when to start.

### 13. [critical] ×1  (road/weekend_warrior)
> 'Category 5 to Category 1 Pathway' appears in the table of contents. This is racing-licence pathway content for competitive road racers, not a weekend warrior with a 'finish' goal. It is wrong content for this persona and could actively mislead the athlete.

### 14. [major] ×1  (road/masters_returner)
> The recovery section is visibly truncated mid-sentence ('Cool room (') — the guide is being sent with incomplete content. A paying customer will receive a guide that cuts off abruptly, which is unprofessional and may omit critical recovery and race-week information.

### 15. [major] ×1  (road/masters_returner)
> TSS Progression is flagged WARN in preview checks, but the guide contains no coach note acknowledging an uneven TSS ramp or advising the athlete how to handle it. A WARN on progression should either be resolved or surfaced with explicit guidance.

### 16. [major] ×1  (road/masters_returner)
> The '"Road Race Strategy" section in the TOC is discipline-correct, but pairing it with a 'Category 5 to Category 1 Pathway' strongly suggests boilerplate road-race template content was injected. Both sections need auditing to confirm they are gran fondo / sportive specific, not criterium/road-race-specific.

### 17. [major] ×1  (gravel/ambitious_first_timer)
> Three preview checks flagged WARN (TSS Progression, FTP Test Frequency, Taper Intensity) with no explanation or mitigation in the guide text. A paying athlete receiving a guide with unresolved system warnings — even if invisible to them — means the plan may have a ramp rate, taper sharpness, or test-scheduling issue that a human coach has not signed off on.

### 18. [major] ×1  (gravel/ambitious_first_timer)
> 'Road Skills' section is listed in the ToC — the truncated text prevents full review, but if this section contains road-specific cornering or pack-riding drills rather than gravel-specific skills (loose surface descending, technical terrain, self-sufficiency), it is wrong for this discipline.

### 19. [major] ×1  (road/veteran_podium_chaser)
> The guide repeatedly describes the athlete's experience as 'Intermediate level' (e.g., 'calibrated to your available time and experience level'), yet she has 10 years of riding and is classified as a 'veteran podium chaser.' 'Intermediate' undersells her experience, may undermine her confidence in the plan, and could reflect wrong-persona content being injected.

### 20. [major] ×1  (road/veteran_podium_chaser)
> Taper Intensity check returned WARN and is unresolved. For a podium-goal athlete at an A-priority race, taper intensity management is critical; the warning must be investigated and either corrected or explicitly acknowledged before sending.

### 21. [major] ×1  (road/veteran_podium_chaser)
> The Long Ride duration range cited in the Weekly Structure section is '2.3–3.8 hours,' but the race is estimated at ~3.3 hours. A peak long ride of only 3.8 hours provides very little buffer above race duration for an experienced athlete targeting a podium — this should be closer to 4–5 hours at peak. Combined with the Per-Day Duration Cap failure this figure is suspect and potentially too low.

### 22. [major] ×1  (gravel/time_crunched_parent)
> Zone 1 power range is listed as '0-96W' but Zone 2 starts at '97W' — the zone chart omits the upper bound label for Z1 explicitly matching 55% FTP (96W at 175W FTP = 54.9% FTP). More critically, the %FTP column for Zone 1 is blank/missing in the rendered text, making the chart internally inconsistent and unprofessional.

### 23. [major] ×1  (gravel/time_crunched_parent)
> Taper Intensity flagged WARN by the automated preview gate. The guide text instructs 'short, sharp efforts keep the engine awake' during taper but the zone distribution and taper intensity checks both warn — the written taper guidance may not match the calendar's actual intensity prescription. This contradiction must be resolved before sending.

### 24. [major] ×1  (gravel/time_crunched_parent)
> Zone Distribution flagged WARN by the automated preview gate. The guide claims 'roughly 65%' of riding stays easy (Z1-Z2), but the preview check warns the distribution may not match. The written claim and the actual calendar distribution are potentially misaligned — a coaching embarrassment if the athlete checks.

### 25. [major] ×1  (gravel/time_crunched_parent)
> Fueling section references an estimated race duration of ~4.79 hours (288 min). At 175W FTP for a 37-year-old male targeting a podium at a 102-mile gravel event with 3,500 ft of climbing, a sub-5-hour finish is plausible but on the aggressive end. However, the guide should state this duration explicitly as an estimate so the athlete can adjust carb totals — leaving it as a raw decimal in the JSON without surfacing it clearly in the guide is a transparency gap.
