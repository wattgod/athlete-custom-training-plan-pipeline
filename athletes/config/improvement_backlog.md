# Improvement backlog — 2026-08-25

**Quality -0.19** · avg coach 5.62/10 · contract pass 62% · load 15.12/plan · 11 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×2  (road/masters_returner, road/time_crunched_parent)
> 'Category 5 to Category 1 Pathway' section appears in the table of contents. This is a road-racing category progression concept (USA Cycling Cat 5→1 upgrade system) that is entirely irrelevant to a gran fondo athlete whose goal is a podium finish in a mass-participation event, not upgrading through a racing license system. It must be removed or replaced with gran-fondo-specific content before sending.

### 2. [critical] ×1  (mtb/ambitious_first_timer)
> "Gravel Skills" appears as a section heading in the Table of Contents (and presumably as a full section body, truncated here) for a mountain bike plan. This is a wrong-discipline content injection — MTB athletes need trail skills, technical descending, switchback cornering, and body position coaching, not gravel-specific content. This is the most embarrassing error in the document and must be corrected before sending.

### 3. [critical] ×1  (mtb/weekend_warrior)
> The Table of Contents and guide body include a 'Gravel Skills' section. This is an MTB event (discipline: mtb). Gravel-specific skills content is wrong-discipline material and would be embarrassing and potentially confusing to an MTB rider preparing for a singletrack/dirt 30-miler. It should be MTB Skills (e.g., technical cornering, braking, line choice, body position on descents).

### 4. [critical] ×1  (road/weekend_warrior)
> "Category 5 to Category 1 Pathway" section is listed in the table of contents. This is road-racing category upgrade content — completely irrelevant and potentially confusing for a gran fondo athlete whose only goal is 'Finish Strong.' Gran fondos are mass-participation events with no USA Cycling upgrade points; including a Cat 5→Cat 1 pathway is the wrong discipline/event context and will undermine credibility with the athlete.

### 5. [critical] ×1  (road/weekend_warrior)
> "Road Race Strategy" section is included in the table of contents. Tactical road-race content (breakaways, field positioning, sprint finishes, etc.) is inappropriate for a gran fondo finish-goal athlete. Gran fondo race strategy (pacing a long effort, managing climbs, fueling on the bike) is what belongs here. This is a content mismatch that a paying customer will notice immediately.

### 6. [critical] ×1  (gravel/veteran_podium_chaser)
> Per-Day Duration Cap check FAILED. The automated gate flagged at least one day exceeding the allowable duration ceiling for a 12 h/week athlete. This must be resolved before sending — an over-length session day is a direct injury/overtraining risk and embarrassing in a paid plan.

### 7. [critical] ×1  (gravel/veteran_podium_chaser)
> 'Road Race Strategy' and 'Category 5 to Category 1 Pathway' sections appear in the table of contents and presumably in the full document. These are road-racing constructs (USAC Cat system) with zero relevance to a gravel event like L'Étape Ciudad de México. Sending road-cat upgrade advice to a gravel racer is a discipline mismatch that destroys credibility.

### 8. [critical] ×1  (gravel/veteran_podium_chaser)
> Wrong-discipline content included: the table of contents lists 'Road Skills,' 'Road Race Strategy,' and 'Category 5 to Category 1 Pathway' — sections that belong in a road racing plan, not a gravel plan. Sending gravel-specific road-race category progression advice to a gravel podium chaser is a glaring discipline mismatch that undermines credibility.

### 9. [critical] ×1  (gravel/veteran_podium_chaser)
> Weight and height (121 lbs / 5'2") appear in the athlete profile but are not present in the plan facts JSON. These values were either fabricated by the generator or pulled from a wrong athlete record. Sending invented biometric data to a real athlete is unacceptable.

### 10. [critical] ×1  (mtb/weekend_warrior)
> Table of contents and guide body include 'Road Skills,' 'Road Race Strategy,' and 'Category 5 to Category 1 Pathway' sections — these are road racing constructs that are completely irrelevant and misleading for an MTB athlete. Cat 5–Cat 1 licensing pathways are a USA Cycling road/criterium concept; MTB uses a different category system entirely (Cat 3/2/1/Pro or XC/Enduro class structures). Sending this to an MTB rider is embarrassing and erodes trust.

### 11. [critical] ×1  (mtb/weekend_warrior)
> L'Étape Ciudad de México by Tour de France is a ROAD SPORTIVE (gran fondo), not an MTB event — yet the discipline field is 'mtb.' If the race is genuinely a road event (verified in the race DB), the plan should be built for road/gran fondo, not MTB. If the athlete truly rides MTB, the race classification is wrong. Either way, the discipline mismatch is unresolved and the guide contains no MTB-specific content (trail skills, technical descending, bike handling on singletrack) while simultaneously containing road race content — the worst of both worlds.

### 12. [major] ×2  (mtb/ambitious_first_timer, road/weekend_warrior)
> The long ride duration range cited in the Weekly Structure section is '3.4–5.8 hours.' The upper bound (5.8 h) slightly exceeds the fueling-derived race duration estimate of ~5.6 h, which is fine in isolation, but the lower bound of 3.4 h in Week 1 may be too aggressive for an athlete targeting a gradual base build — and more importantly, neither number is explained or sourced, making it feel like a data-merge artifact rather than coached guidance.

### 13. [major] ×1  (mtb/ambitious_first_timer)
> The FTP test frequency preview check returned WARN, yet the guide tells the athlete the test result 'sets ALL your training zones for the next 6 weeks' — an internally inconsistent statement in an 8-week plan where a retest may be scheduled. The 6-week figure appears to be boilerplate copy-paste that does not match this plan's actual retest cadence and will confuse the athlete.

### 14. [major] ×1  (mtb/ambitious_first_timer)
> The plan start date is 2026-08-31 and the race is 2026-10-24 (54 days / ~7.7 weeks away at plan start), yet the plan is described as 8 weeks. Given the plan_note clarification this is not a contradiction per se, but the guide itself never explains to the athlete why there is a one-week gap between 'today' and when they start — a first-timer will be confused and may start training immediately on the wrong week.

### 15. [major] ×1  (mtb/weekend_warrior)
> The Per-Day Duration Cap check is listed as FAIL in the preview checks, yet the guide text is sent without any acknowledgment, correction, or coach note explaining the violation. A FAIL-level automated flag must be resolved or explicitly justified before delivery.

### 16. [major] ×1  (mtb/weekend_warrior)
> The guide states the long ride peaks at 1.5 hours, but simultaneously tells the athlete 'a single 3-4 hour ride is worth more than two 1.5-hour rides.' For a 4 hrs/week athlete targeting a 30-mile MTB race with an estimated ~2.7 hr finish time, a 1.5 hr long ride ceiling is genuinely inadequate and the plan never resolves the contradiction — it just flags it as a 'blindspot' without a concrete corrective prescription.

### 17. [major] ×1  (mtb/weekend_warrior)
> The Taper Intensity check is WARN and the Zone Distribution check is WARN, but neither warning is addressed anywhere in the guide text. At minimum, a coaching note should explain why the taper intensity or zone split deviates from the norm and why it is appropriate for this athlete — otherwise the coach cannot put their name on it.

### 18. [major] ×1  (road/weekend_warrior)
> Weekly Volume check flagged WARN and Taper Intensity flagged WARN by the automated preview — neither is explained or resolved in the guide text provided. A WARN on weekly volume for a 7 h/week athlete is significant: if any week exceeds the cap or falls embarrassingly short, that is a concrete error the athlete will see in the calendar. These flags must be investigated and either corrected or explicitly acknowledged before sending.

### 19. [major] ×1  (road/time_crunched_parent)
> Off days listed as 'Tuesday, Wednesday, Monday' — three days off in a 7 h/week plan leaves only four riding days, which is fine, but listing Monday last when it is the first day of a standard week reads as a copy-paste artefact and could confuse the athlete about which days are actually off. The ordering should reflect the calendar week.

### 20. [major] ×1  (road/time_crunched_parent)
> Taper Intensity flagged WARN in the preview checks but the guide text does not address or explain the taper intensity concern to the athlete. If the automated gate already flagged it, the coach guide should reflect the resolution or caveat so the athlete (and any human reviewer) understands what to expect during taper.

### 21. [major] ×1  (road/masters_returner)
> Weekly Volume flagged WARN by the automated gate: 6 h/week produces long rides of roughly 1.5–2.5 h per the guide's own text, yet the race is 68 miles (~4.6 h per the fueling data). The guide acknowledges the gap with the 'Biggest Opportunity' callout but does not quantify the shortfall or give a concrete mitigation path (e.g., at least one 3-hour ride in Build/Peak). For a masters athlete returning from a layoff this is a meaningful durability risk that deserves a stronger, more specific coaching directive.

### 22. [major] ×1  (road/masters_returner)
> 'Road Race Strategy' appears as a table-of-contents section. Gran fondos are mass-participation events, not road races with tactical attacks and team dynamics. Tactical road-race content (wheel-sucking, attacking, field positioning) is wrong-discipline material for a finish-goal gran fondo athlete and could confuse or mislead her.

### 23. [major] ×1  (gravel/veteran_podium_chaser)
> Weekly Volume check returned WARN. For a podium-targeting athlete at 360 W FTP on 12 h/week, any week that falls materially outside the 10–13 h band (or spikes unexpectedly) needs explicit justification. The WARN is unresolved and the text provides no explanation.

### 24. [major] ×1  (gravel/veteran_podium_chaser)
> TSS Progression check returned WARN. A polarized plan for an experienced racer should show a clean 3:1 or 4:1 loading-to-recovery ramp. An unresolved TSS WARN suggests the ramp rate is either too aggressive or has an unexplained spike — both are problematic for a 14-week podium build.

### 25. [major] ×1  (gravel/veteran_podium_chaser)
> The long-ride duration range cited in the text ('2.3–3.8 hours') needs scrutiny against the Per-Day Duration Cap FAIL. If the upper end of 3.8 h is the capped day that triggered the FAIL, that value must be corrected before the guide text is consistent with the corrected calendar.
