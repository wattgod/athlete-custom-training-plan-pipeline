# Improvement backlog — 2026-09-09

**Quality -0.94** · avg coach 5.62/10 · contract pass 62% · load 17.0/plan · 11 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×3  (road/time_crunched_parent, road/veteran_podium_chaser, road/weekend_warrior)
> 'Category 5 to Category 1 Pathway' section appears in the table of contents for a 'podium-chasing veteran' persona — this content is for beginners learning racing categories, not an experienced racer chasing a podium. It is wrong-audience content and would embarrass the business if sent to this athlete.

### 2. [critical] ×1  (mtb/weekend_warrior)
> Discipline mismatch — the athlete's discipline is MTB, yet the guide contains sections titled 'Road Skills,' 'Road Race Strategy,' and 'Category 5 to Category 1 Pathway.' These are road-racing constructs that have no place in an MTB gran fondo plan and will confuse or mislead the athlete.

### 3. [critical] ×1  (mtb/weekend_warrior)
> Per-Day Duration Cap FAIL is unresolved — the automated gate flagged sessions that exceed the athlete's limits, meaning individual workouts are prescribed beyond what is coherent for a 4 h/week plan. This contradicts the Time-Crunched promise and must be corrected before sending.

### 4. [critical] ×1  (mtb/weekend_warrior)
> Long-ride ceiling of 1.5 hours is dangerously low for a 78-mile / ~5.75-hour race. The guide itself acknowledges this is shorter than ideal but then fails to rectify it anywhere in the visible plan logic. A weekend warrior targeting 'finish' on a nearly 6-hour event needs at least one 2.5–3-hour long ride in the Build/Peak phase; 1.5 hours is insufficient race-day preparation and risks the athlete bonking badly.

### 5. [critical] ×1  (mtb/weekend_warrior)
> Discipline mismatch — the Table of Contents explicitly lists a 'Gravel Skills' chapter for an athlete registered for an MTB (mountain bike) event. MTB skills (trail cornering, rock gardens, switchback climbing, technical descending, body position) are entirely different from gravel-specific skills. This is the most embarrassing error in the document.

### 6. [critical] ×1  (mtb/weekend_warrior)
> Long ride duration cap of 1.5 hours is dangerously low for a 30-mile MTB event. The fueling model computes race duration at ~2h 41min, and a fit 54-year-old weekend warrior on MTB terrain could easily take 3+ hours. The plan itself admits long rides top out at 1.5 hours yet only suggests 1-3 longer rides in Build/Peak. That is insufficient race-day durability preparation and contradicts the coach's own advice that 'a single 3-4 hour ride is worth more than two 1.5 hour rides.'

### 7. [critical] ×1  (road/time_crunched_parent)
> Table of contents and guide body include a 'Category 5 to Category 1 Pathway' section. This is road-racing/criterium category upgrade content and is completely irrelevant — and potentially confusing or embarrassing — for a gran fondo participant. Gran fondos are mass-participation events with no USA Cycling upgrade points; this section does not belong here at all.

### 8. [critical] ×1  (gravel/ambitious_first_timer)
> Automated gate flagged Zone Distribution as FAIL. The guide text claims 'roughly 75%' of riding stays easy (pyramidal target), but the preview check independently flagged this as failing. This is a methodology integrity issue: if the actual scheduled workouts don't reflect a pyramidal distribution, the plan contradicts its own stated approach and the athlete will be misled about what they're doing. This must be resolved before sending.

### 9. [critical] ×1  (road/masters_returner)
> Zone Distribution check FAILED (preview flag) and the guide provides no evidence of a fix. The stated distribution ('roughly 70% easy') is asserted in prose but the actual per-zone prescription that caused the failure is not visible or corrected. This must be resolved before sending — a wrong zone distribution undermines the entire Time-Crunched methodology claim.

### 10. [critical] ×1  (road/masters_returner)
> The guide text ends mid-sentence ('PRE-WORKOUT (2-3 HOURS BEFORE) If training') — the nutrition timing section, and presumably the remaining sections (Mental Preparation, Race Week, Race Day, Road Skills, etc.), are either missing or truncated. A paying customer must not receive an incomplete document.

### 11. [critical] ×1  (road/time_crunched_parent)
> 'Road Race Strategy' section is listed in the TOC. This is a gran fondo with a goal of 'finish,' not a criterium or road race with tactics, primes, or field dynamics. Including road race strategy content is wrong for the discipline context.

### 12. [major] ×1  (road/veteran_podium_chaser)
> Taper Intensity was flagged WARN in preview checks but there is no evidence in the guide text that the issue was resolved or annotated. Sending a plan with a known unresolved taper intensity warning to an athlete whose entire race outcome depends on arriving fresh is a coaching liability.

### 13. [major] ×1  (road/veteran_podium_chaser)
> The FTP test protocol states 'The test result sets ALL your training zones for the next 6 weeks' — but the total plan is only 10 weeks. Depending on when the test falls, this could imply zones are locked for more than the remaining plan duration, or the phrasing is simply boilerplate copy-paste that contradicts this specific plan's timeline and should say something like 'for the remainder of your plan'.

### 14. [major] ×1  (mtb/weekend_warrior)
> Gran Fondo Guadeloupe is a road/gravel gran fondo, not an MTB event — yet the plan JSON discipline is 'mtb.' Either the athlete's discipline field is wrong or the race assignment is wrong. This fundamental mismatch must be resolved before any plan content is finalised.

### 15. [major] ×1  (mtb/weekend_warrior)
> Taper Intensity WARN is unresolved — the automated gate flagged a potential issue with taper intensity but the guide shows no evidence of adjustment or coach note addressing it. Sending a plan with a known unreviewed taper problem to an A-priority race is unacceptable.

### 16. [major] ×1  (mtb/weekend_warrior)
> Weekly Volume WARN is unresolved — the gate flagged volume concerns but the guide does not address or explain the discrepancy, leaving the athlete with no clarity on whether prescribed volume is actually achievable within 4 h/week.

### 17. [major] ×1  (road/weekend_warrior)
> The guide states '7 Years Riding' and implicitly frames the athlete as 'Intermediate,' but the persona is 'weekend_warrior' with no questionnaire field for years of experience visible in the JSON. The plan text then uses '7 years of cycling experience at Intermediate level' as a methodology justification — if this was inferred or defaulted, it may be wrong and creates a trust problem if the athlete doesn't recognize themselves.

### 18. [major] ×1  (road/weekend_warrior)
> Three preview checks flagged WARN (TSS Progression, FTP Test Frequency, Taper Intensity) but the guide text contains no acknowledgment or mitigation of these known issues. A coach reviewing the plan should at minimum ensure the taper section and FTP test placement are defensible; sending without addressing them is a quality risk.

### 19. [major] ×1  (road/weekend_warrior)
> 'Road Race Strategy' and 'Road Skills' are listed as standalone sections in the table of contents. A gran fondo is a mass-participation timed event, not a criterium or road race. Tactical content written for competitive road racing (e.g., positioning, attacking, covering breaks) is inappropriate and potentially confusing for a rider whose goal is simply to finish.

### 20. [major] ×1  (mtb/weekend_warrior)
> Fueling section references a race duration of ~2h 41min (2.678… h) and 53 g carbs/hour, but this duration is suspiciously fast for a 30-mile MTB event in Texas with likely technical terrain. If the real expected finish time is 3-4 hours, the hourly carb target and total fueling strategy need to be recalculated and the athlete should be told her estimated finish window, not an implausibly fast number.

### 21. [major] ×1  (mtb/weekend_warrior)
> Off-day listing is internally inconsistent: the 'At a Glance' section lists off days as 'Wednesday, Monday' — an unusual ordering that implies Monday is the second off day, yet a 4-hour weekly plan with a Sunday long ride and mid-week intervals typically treats Monday as a primary recovery day. The awkward reversal of the conventional Mon/Wed order will confuse the athlete.

### 22. [major] ×1  (mtb/weekend_warrior)
> Zone 3 ('Gray Zone') warning is stated as policy throughout, yet the Time-Crunched methodology for a 4 h/week athlete legitimately prescribes Tempo (Z3) work during Build. The blanket 'avoid Z3' messaging conflicts with what the calendar will likely prescribe and needs nuance: 'only when prescribed' language exists but the repeated strong warnings will make athletes skip Z3 sessions that are intentional.

### 23. [major] ×1  (road/time_crunched_parent)
> Zone 1 (Active Recovery) row in the zone chart lists power as '0-110W' but shows no % FTP or % LTHR columns, while all other zones have them. This is an inconsistency that will confuse the athlete when they look at their head unit targets.

### 24. [major] ×1  (road/time_crunched_parent)
> The guide contains a 'Road Race Strategy' section (visible in the table of contents). Strategy content written for a road race (breakaways, peloton tactics, sprint finishes) is the wrong discipline framing for a gran fondo, which is a timed/participation event. If this section contains criterium or road-race tactical advice it must be replaced with gran fondo-specific pacing and climbing strategy.

### 25. [major] ×1  (road/time_crunched_parent)
> Three preview checks flagged WARN (Weekly Volume, Zone Distribution, Taper Intensity) but the guide text makes no acknowledgment of these. Specifically, the taper section in the guide simply says 'trust the training and rest' with no explanation of why taper intensity is atypical — if the automated gate flagged it, a human reader of the plan may notice the taper feels wrong and lose confidence in the plan.
