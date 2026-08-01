# Improvement backlog — 2026-08-01

**Quality -1.06** · avg coach 5.5/10 · contract pass 62% · load 17.0/plan · 14 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [major] ×3  (road/masters_returner, road/weekend_warrior)
> 'Road Race Strategy' section is listed in the table of contents. The athlete is riding a gran fondo (finish goal, not a race with tactical competition). Road race strategy content — attacks, positioning for a finish sprint, team tactics — is inappropriate and could actively mislead the athlete about what race day looks like.

### 2. [critical] ×1  (gravel/ambitious_first_timer)
> FTP listed as body weight in the athlete profile box: '132 lbs Weight (59.9 kg)' AND '132W FTP' — these are numerically identical by coincidence, so the template has almost certainly swapped or duplicated the FTP value into the weight field. The athlete's actual weight was never collected in the questionnaire data provided; publishing '132 lbs' as her weight is fabricated data that will be immediately obvious to the athlete.

### 3. [critical] ×1  (gravel/ambitious_first_timer)
> The Table of Contents and guide body include a 'Road Race Strategy — Category 5 to Category 1 Pathway' section. This athlete is a gravel racer targeting a finish at L'Etape Brasil, not a road criterium/circuit racer chasing USA Cycling upgrade points. This content is for the wrong discipline entirely and is deeply confusing.

### 4. [critical] ×1  (road/masters_returner)
> 'Category 5 to Category 1 Pathway' section appears in the table of contents and presumably in the body. This athlete's goal is simply to FINISH a gran fondo (Lake Taupo Cycle Challenge). Cat 5–1 is a USA Cycling racing licence pathway with zero relevance to this event, this goal, or this discipline context. It will confuse and undermine trust.

### 5. [critical] ×1  (road/masters_returner)
> Per-Day Duration Caps check FAILED in the preview gate and the text was still sent. At least one workout exceeds the per-day cap for a 6 h/week masters athlete — this is an unresolved data error that could prescribe an unsafe or nonsensical single-session duration.

### 6. [critical] ×1  (mtb/weekend_warrior)
> Discipline mismatch throughout: the athlete's discipline is 'mtb' but the plan is titled 'Grassroots Gravel 60mi Training Guide,' the race is called 'Grassroots Gravel,' there is a dedicated 'Gravel Skills' section in the table of contents, and the indoor/outdoor section references 'gravel'-specific language. The race database confirms the event name is Grassroots Gravel and it is located in Pueblo, Colorado — however the athlete's discipline flag is MTB, not gravel. Either the athlete is doing a gravel event on a mountain bike (common) and the plan should address MTB-on-gravel specifics, or the discipline field is wrong. Either way, a 'Gravel Skills' section is the wrong content for an MTB rider, and the plan never addresses MTB-specific execution (suspension setup, body position on technical terrain, etc.). This must be resolved before sending.

### 7. [critical] ×1  (mtb/weekend_warrior)
> Zone 2 power band is missing the lower bound in the zone chart — it shows '106-144W' but the % FTP column for Zone 2 shows '56-75% FTP' while Zone 1 shows '0-105W' with no % FTP range listed. More importantly, Zone 1 has no % FTP or % LTHR populated at all, making the chart incomplete and inconsistent. A paying athlete cannot use an incomplete zone chart.

### 8. [critical] ×1  (road/masters_returner)
> The guide includes a 'Category 5 to Category 1 Pathway' section (visible in the Table of Contents). This athlete is a masters gran fondo participant whose goal is simply to finish — not a USA Cycling licensed road racer pursuing upgrade points. This section is wrong-persona content that will confuse and potentially embarrass the athlete, and signals the guide was not properly filtered for this persona.

### 9. [critical] ×1  (road/masters_returner)
> Zone Distribution check is listed as FAIL in the preview checks, yet the plan is being prepared for delivery. A failed zone distribution means the prescribed time-in-zone across the 13 weeks does not conform to the stated Time-Crunched methodology (≈70% easy), which is the methodological promise made explicitly in the guide text. Sending a plan whose own QA gate flagged this as broken is not acceptable.

### 10. [critical] ×1  (road/weekend_warrior)
> Fueling recommendation is dangerously low and internally inconsistent. Plan JSON specifies 58 g carbs/hour for a ~5.7-hour effort, yet the guide text does not surface this number at all in the visible excerpt. More critically, 58 g/hr is well below the current evidence base (80-100+ g/hr for a trained athlete using mixed transporters over 5+ hours) and is likely to cause a bonk on race day. The guide must state the correct number prominently and it must be defensible.

### 11. [critical] ×1  (road/weekend_warrior)
> Weekly schedule contradiction: Saturday is listed as an OFF day AND the guide states 'Long rides: Sunday.' However, the standard expectation for a weekend warrior is a Sunday long ride — listing Saturday as off is fine — but elsewhere the guide's 'YOUR WEEK AT A GLANCE' block lists 'Off days: Saturday, Monday' while also implying the long ride falls on Sunday. This is internally consistent on the surface, but the long-ride peak duration cited in the text is '1.5 hours,' which for a 78-mile (~5.7-hour) granfondo is woefully short and directly contradicts the 'biggest opportunity' callout. A 1.5-hour ceiling on long rides is a plan-design failure for this event, not just a caveat.

### 12. [critical] ×1  (mtb/weekend_warrior)
> DISCIPLINE MISMATCH — The guide includes a 'Gravel Skills' chapter (visible in the Table of Contents). This is an MTB event (Dunoon Dirt Dash). Gravel-specific skills content has no place here and would immediately undermine the athlete's confidence in the plan. Must be replaced with MTB-specific trail skills content (body position, technical descending, braking, line choice).

### 13. [critical] ×1  (mtb/weekend_warrior)
> FACTUAL CONTRADICTION — The zone chart rows for Zone 1 and Zone 2 are missing their '% FTP' column values (Zone 1 shows only '0-112W' and no percentage label; Zone 2 shows '56-75% FTP' but Zone 1 is blank). More importantly, the lower bound of Zone 2 is stated as 113W. At FTP 205W, 56% = 115W, not 113W — a minor rounding error, but the missing Zone 1 % FTP label is a visible production defect that reads as sloppy.

### 14. [critical] ×1  (road/weekend_warrior)
> "Category 5 to Category 1 Pathway" section is listed in the table of contents and appears to be included in the guide. This is entirely wrong for a weekend warrior whose goal is simply to finish a 43.5-mile gran fondo-style event. It implies a USA Cycling racing license upgrade pathway that is irrelevant, confusing, and potentially embarrassing to send to this customer.

### 15. [critical] ×1  (road/weekend_warrior)
> The automated preview check explicitly flagged 'Per-Day Duration Caps: FAIL' and this issue is unresolved. The guide has not been corrected before reaching QA. At least one workout day likely exceeds the per-session cap appropriate for a 4 h/week athlete — sending a plan with a known flagged failure is not acceptable.

### 16. [major] ×1  (gravel/ambitious_first_timer)
> Off days are listed as 'Tuesday, Monday' — days are named out of calendar order (Monday comes before Tuesday). This reads as a template rendering bug and looks unprofessional; it may also indicate the underlying schedule data is mis-ordered.

### 17. [major] ×1  (gravel/ambitious_first_timer)
> The guide includes a 'Road Skills' section in the Table of Contents. While some road-skills content (descending, cornering) is relevant to gravel, a standalone 'Road Skills' heading without gravel-specific framing (loose surface cornering, technical descents, mud/gravel handling) is mismatched to the discipline and persona.

### 18. [major] ×1  (gravel/ambitious_first_timer)
> Height ('5'8"') appears in the athlete profile box but height was not a field in the questionnaire data provided — this value is fabricated or pulled from a wrong athlete's profile, which is a data-integrity failure.

### 19. [major] ×1  (road/masters_returner)
> Long-ride duration targets stated in the guide (1.5–2.5 hours peak) are far too short for a ~7-hour race. Even the coach's own 'biggest opportunity' callout acknowledges the rides are short and recommends 3–4 hours, but the plan's prescribed long-ride ceiling of 2.5 hours is never reconciled with that advice — the athlete is left with contradictory guidance.

### 20. [major] ×1  (road/masters_returner)
> TSS Progression flagged WARN in the preview gate but is never acknowledged or mitigated in the guide text. A masters returner is at elevated overtraining risk; a non-standard TSS ramp deserves an explicit note to the athlete or a plan correction.

### 21. [major] ×1  (gravel/time_crunched_parent)
> Countdown says '84 days from today' but the plan start date is 2026-08-10 and race date is 2026-10-24 — that is 75 days from plan start, not 84. The '84 days' figure appears to be calculated from a generation date earlier than the plan start, which is fine, but presenting it to the athlete as a countdown without clarifying the reference date is confusing and could undermine trust in the plan's arithmetic.

### 22. [major] ×1  (gravel/time_crunched_parent)
> The Zone 2 power row is missing its '% FTP' column entry in the zone table (shown as blank in the truncated text: '133-180W 56-75% FTP' — this is actually present, but the Zone 1 row shows no % FTP or % LTHR values at all). Zone 1 only lists '0-132W' with no percentage anchors, which is inconsistent with every other zone row and may confuse athletes using a different FTP after a retest.

### 23. [major] ×1  (mtb/weekend_warrior)
> The avatar/file header reads 'Avatar 202608013' — this internal ID is exposed in the document title and should be replaced with the athlete's name or redacted before sending to a customer.

### 24. [major] ×1  (mtb/weekend_warrior)
> Zone Distribution and FTP Test Frequency both carry WARN flags from the automated preview but there is no acknowledgement or mitigation in the guide text. If zone distribution is skewed (likely too much Zone 3 for a Time-Crunched plan that claims 70% easy), the methodology claim of '~70% easy' may contradict the actual calendar, which is embarrassing if the athlete checks the numbers.

### 25. [major] ×1  (mtb/weekend_warrior)
> The off-days listed ('Sunday, Thursday, Tuesday') include three days — but the plan says 4 training days per week from a 5 h/week budget. Three off-days in a 7-day week leaves only 4 training days, which is consistent, but listing off-days in the order Sunday, Thursday, Tuesday (non-chronological) is confusing and looks like a data-rendering bug.
