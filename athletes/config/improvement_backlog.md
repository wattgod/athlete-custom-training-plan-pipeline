# Improvement backlog — 2026-07-18

**Quality 1.13** · avg coach 5.38/10 · contract pass 100% · load 13.12/plan · 12 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×2  (gravel/masters_returner, road/veteran_podium_chaser)
> 'Category 5 to Category 1 Pathway' section appears in the table of contents and presumably in the body. This is a USA Cycling license-category progression framework for competitive road racers — it is completely irrelevant to a masters gran fondo participant and will confuse or mislead the athlete. It also implicitly contradicts the podium goal framing (gran fondo podiums are age-group/GC based, not cat-upgrade based).

### 2. [critical] ×1  (gravel/weekend_warrior)
> The table of contents and guide body include a 'Category 5 to Category 1 Pathway' section — this is road racing/USA Cycling category upgrade content that has zero relevance to a gravel event finisher. It is wrong-discipline content and would confuse or embarrass the business if a paying customer sees it.

### 3. [critical] ×1  (gravel/weekend_warrior)
> 'Road Race Strategy' section appears in the contents — this athlete is doing a gravel event (L'Etape Poland gravel format), not a road criterium or road race. Road race tactics (drafting strategy, sprint positioning, team tactics) are irrelevant and potentially misleading for a solo gravel finisher.

### 4. [critical] ×1  (mtb/ambitious_first_timer)
> Discipline mismatch: the athlete's discipline is MTB, but the plan is explicitly framed as a gravel plan throughout — the Table of Contents includes a 'Gravel Skills' section, and the overall guide voice treats this as a gravel event. MTB and gravel are different disciplines with different skills, bike setup, and terrain-specific demands. A 'Gravel Skills' section should not appear in an MTB plan, and any gravel-specific skill or equipment content will be wrong.

### 5. [critical] ×1  (mtb/ambitious_first_timer)
> Race discipline ambiguity unresolved: the race is named 'Gravelista' (confirmed in the verified DB as a gravel event in Victoria, Australia) yet the athlete's discipline is tagged 'mtb'. If the race is truly a gravel event, the athlete's discipline field is wrong and the plan should be a gravel plan — but then the athlete's MTB profile (skills, equipment, training focus) may be mismatched. If the athlete is an MTB rider doing a gravel race, the plan must acknowledge this explicitly and adjust accordingly. This contradiction was not resolved before generation.

### 6. [critical] ×1  (gravel/masters_returner)
> 'Road Race Strategy' section is listed in the table of contents. This athlete is doing a gravel granfondo, not a criterium or road race. Tactical road-race content (positioning, blocking, breakaway dynamics, etc.) does not apply and signals the plan was not properly customised for the discipline.

### 7. [critical] ×1  (road/veteran_podium_chaser)
> Section titled 'Category 5 to Category 1 Pathway' is entirely inappropriate for this athlete. The persona is 'veteran podium chaser' with 16 years of riding and a 320W FTP — this is not a beginner racer learning upgrade pathways. This section either belongs to a different template or was injected in error; it would embarrass the business and confuse the athlete.

### 8. [critical] ×1  (mtb/weekend_warrior)
> Discipline mismatch throughout: the athlete's discipline is MTB, yet the plan's table of contents and body text prominently feature a 'Gravel Skills' section and frame the entire event as a gravel-specific preparation. The race is named 'Trough Creek Gravel Grinder' but the athlete registered as an MTB rider — the plan should address MTB skills (technical descending, rock gardens, body position) not gravel cornering or gravel-specific content, or at minimum reconcile the discipline explicitly.

### 9. [critical] ×1  (mtb/weekend_warrior)
> Weekly session count contradiction: the 'Weekly Structure' section states 'Your week has 2 training days, 2 of which are key sessions,' which is internally nonsensical (2 total days cannot simultaneously include 2 key sessions plus easy rides and strength work). A 4 h/week Time-Crunched athlete should have more riding days than 2; this figure appears to be a template error.

### 10. [critical] ×1  (mtb/weekend_warrior)
> Off-day placement is athlete-hostile: the plan assigns the long ride to Monday and off days to Sunday AND Saturday, meaning the athlete's entire weekend — the only realistic time a weekend warrior can do a long ride — is blocked off. This directly contradicts the 'Weekend Warrior' persona and will make the plan unexecutable for this athlete.

### 11. [critical] ×1  (gravel/masters_returner)
> Section titled 'Road Race Strategy' and 'Category 5 to Category 1 Pathway' are listed in the Table of Contents and apparently present in the guide. These are road racing concepts with zero relevance to a gravel climbing event (Taiwan KOM Challenge). A Cat 5–Cat 1 upgrade pathway is UCI/USA Cycling road racing terminology and is actively wrong and embarrassing for a gravel athlete whose goal is simply to finish.

### 12. [critical] ×1  (gravel/masters_returner)
> 'Road Skills' section appears to include 'Road Race Strategy' content. The Taiwan KOM Challenge is a gravel/mountain climb event, not a criterium or road race. Any content covering road race tactics (attacking, covering breaks, pack positioning, etc.) is discipline-wrong and should be replaced with gravel-specific climbing strategy content.

### 13. [major] ×2  (road/veteran_podium_chaser)
> The guide states '16 years of cycling experience at Intermediate level' in the methodology justification. A rider with 16 years of riding history should be classified as Advanced or Experienced, not Intermediate. This directly contradicts the persona label 'Experienced racer chasing a podium' and undermines the athlete's confidence in the plan's personalisation.

### 14. [major] ×1  (gravel/weekend_warrior)
> The long ride peak duration mentioned in the Weekly Structure section is cited as only '1.5 hours' — for a 52.2-mile gravel race with an estimated finish time of ~3.7 hours, this is far too short and internally contradicts the plan's own 'biggest opportunity' callout urging the athlete toward 3-4 hour rides. The 1.5-hour figure reads like a placeholder or template artifact.

### 15. [major] ×1  (gravel/weekend_warrior)
> FTP Test Frequency check returned WARN in the preview — the guide text does not acknowledge or explain this warning. For a 10-week plan with a known FTP (174W), the frequency and placement of retests should be explicitly justified to the athlete so they are not left wondering why they are (or are not) retesting mid-plan.

### 16. [major] ×1  (mtb/ambitious_first_timer)
> Experience level contradiction: the guide text states '1 Years Riding' alongside 'Intermediate level' in the methodology justification. One year of riding is beginner, not intermediate. Calling a 1-year rider 'Intermediate level' is inaccurate and could lead the athlete to underestimate training risks or attempt intensity they are not ready for.

### 17. [major] ×1  (mtb/ambitious_first_timer)
> Long ride duration range stated as '2.7-4.5 hours' in the Weekly Structure section, but the race fueling JSON lists a race duration of 7.4 hours. Even accounting for taper and build-up, a peak long ride of 4.5 hours for a 7.4-hour goal event is a significant gap that is not explained or justified anywhere in the visible guide text.

### 18. [major] ×1  (road/veteran_podium_chaser)
> Long ride duration range cited as '3.4–5.8 hours' in the Weekly Structure section. For a 100-mile gran fondo with significant elevation, a peak long ride ceiling of 5.8 hours is plausible, but 3.4 hours as the floor description is oddly precise and unexplained — if this is a generated artefact it may be wrong for Week 1 of an athlete already doing 12 h/week, and the naked decimal figures read as machine output rather than coach language.

### 19. [major] ×1  (gravel/masters_returner)
> Fueling section states an estimated race duration of 4.1 hours (from plan JSON) but the guide text does not surface this figure or reconcile it with the long-ride duration cap of 2.1–3.5 hours. A 63-year-old finishing a 65-mile gravel ride may well take 4.5–5.5 hours; the fueling duration assumption should be stated explicitly so the athlete knows it is an estimate and can adjust carb targets accordingly.

### 20. [major] ×1  (mtb/weekend_warrior)
> Zone 1 lower bound and Zone 2 lower bound are missing from the zone chart (only wattage shown for Z1 as '0-97W' with no % FTP listed, and Z2 % FTP starts at 56% implying Z1 upper bound is 55% FTP = ~97 W which is correct, but the chart omits the % FTP column entry for Z1 entirely), creating an incomplete reference the athlete will notice.

### 21. [major] ×1  (mtb/weekend_warrior)
> TSS Progression and Taper Intensity both flagged WARN in the automated preview checks, yet the guide text contains no acknowledgment or mitigation of these warnings. A TSS jump or improper taper intensity for a 54-year-old masters athlete is a meaningful physiological risk that should be addressed, not silently ignored.

### 22. [major] ×1  (mtb/weekend_warrior)
> 'Gravel Skills' and 'Masters Training Considerations' appear in the table of contents but the truncated guide text does not show their content — if the Gravel Skills section contains gravel-specific technique advice (e.g., tire pressure for gravel, loose-over-hard cornering) sent to an MTB rider, that content is wrong for the discipline and potentially dangerous if the athlete is actually riding a mountain bike on singletrack.

### 23. [major] ×1  (gravel/masters_returner)
> The Zone table omits % FTP and % LTHR columns for Zone 1 (Active Recovery) — the lower bound is just listed as '0-68W' with no RPE-anchor percentage shown, while all other zones include % FTP. Minor inconsistency but looks sloppy and undermines coach credibility.

### 24. [major] ×1  (gravel/masters_returner)
> Recovery protocol states '24g protein + 61-73g carbs within 30 minutes' but the fueling section establishes 53g/hr carbs over 6.8h for race day. The post-ride carb window figure (61-73g) is not explained or sourced relative to the athlete's body weight formula — it appears to be pulled from a generic template and the math basis is opaque. For a paying customer this needs either a clear derivation or removal.

### 25. [minor] ×1  (gravel/weekend_warrior)
> 'Road Skills' section in the table of contents is ambiguous — if this covers gravel-specific skills (loose surface cornering, tire pressure management, rough terrain handling) it belongs; if it is generic road cycling content it does not. Given the other road-discipline contamination in this plan, this section needs verification before sending.
