# Improvement backlog — 2026-08-07

**Quality -0.01** · avg coach 5.75/10 · contract pass 62% · load 15.0/plan · 11 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×1  (road/veteran_podium_chaser)
> Table of contents lists a 'Category 5 to Category 1 Pathway' section — a USA Cycling road-racing category upgrade pathway that is entirely irrelevant to a gran fondo competitor. Gran fondos are non-licensed mass-participation events with no upgrade categories. This section must be removed; leaving it in signals the plan was not written for this athlete and will destroy credibility instantly.

### 2. [critical] ×1  (road/time_crunched_parent)
> 'Gravel Skills' appears as a titled section in the table of contents and presumably in the body of a plan for a ROAD athlete targeting a road gran fondo. This is the wrong discipline content and is deeply embarrassing — it signals the template was not correctly filtered for discipline.

### 3. [critical] ×1  (road/time_crunched_parent)
> The preview check flags Zone Distribution as FAIL, yet the guide text never acknowledges, explains, or corrects this. Sending a plan with a known failing check — especially one that directly affects training stimulus — is unacceptable.

### 4. [critical] ×1  (gravel/masters_returner)
> The table of contents includes a 'Road Race Strategy — Category 5 to Category 1 Pathway' section. This athlete is doing a gravel event (Taiwan KOM Challenge). Road-race category progression content is flatly wrong for the discipline and would embarrass the business if sent.

### 5. [critical] ×1  (gravel/masters_returner)
> Zone Distribution check FAILED in the preview but the guide text never addresses or corrects it. Sending a plan with a known failed check — without at least acknowledging the deviation — is a quality-control failure. The guide claims '~70% easy' distribution but the calendar (which we cannot see) apparently contradicts that.

### 6. [critical] ×1  (road/weekend_warrior)
> 'Category 5 to Category 1 Pathway' section is present in the table of contents and presumably in the full guide. This is a USA Cycling road-racing category upgrade pathway — entirely irrelevant and potentially confusing for a weekend warrior whose stated goal is simply to finish a gran fondo. It signals to the athlete that the plan was not built for them.

### 7. [critical] ×1  (road/weekend_warrior)
> Weekly Volume check flagged FAIL in the preview checks. The guide text describes long rides of only '1.5–2 hours' as the peak within a 4h/week budget, which is grossly insufficient for a 78.3-mile (~5.8h) gran fondo. The guide acknowledges the gap but does not resolve it structurally — a failing automated check plus an admitted volume shortfall should block sending.

### 8. [critical] ×1  (road/veteran_podium_chaser)
> Section titled 'Category 5 to Category 1 Pathway' appears in the table of contents (and presumably in the full document). This is a USA Cycling road racing licence upgrade pathway — it is completely irrelevant to a Gran Fondo athlete. Gran Fondos are not mass-start licensed races; there are no categories, no upgrade points, and no Cat 1-5 progression. Including this section is factually wrong for the event and discipline context, and will confuse or mislead the athlete.

### 9. [critical] ×1  (gravel/ambitious_first_timer)
> Table of contents and guide body include 'Road Race Strategy' and 'Category 5 to Category 1 Pathway' sections — this is a GRAVEL event. Cat 5–1 is a USA Cycling road-racing licence classification that is irrelevant and confusing for a gravel finisher; sending it will look amateurish and erode trust in the whole plan.

### 10. [critical] ×1  (gravel/ambitious_first_timer)
> Zone chart omits the absolute power ranges for Zone 1 (Active Recovery) and Zone 2 (Endurance) — it shows '0-100W' for Z1 but leaves the watt range blank for Z2 (only shows '101-136W' in the truncated text; needs verification), and the LTHR columns for Z1 and Z2 appear missing entirely. An athlete without a heart-rate background relies on these numbers to set their head unit; gaps here break the core training tool.

### 11. [critical] ×1  (road/time_crunched_parent)
> Three off-days listed (Thursday, Tuesday, Wednesday) — that is 3 rest days in a single week, leaving only 4 training days. Combined with a long ride on Saturday and intervals mid-week, this implies only 1 mid-week interval day, which is inconsistent with '4 training days, 2 of which are key sessions' stated two pages later. If the off-days are correct the weekly structure copy is wrong; if the weekly structure is correct the off-days list is wrong. Either way this contradiction will confuse the athlete and must be resolved before sending.

### 12. [major] ×2  (road/veteran_podium_chaser)
> The plan describes the athlete's experience level as 'Intermediate' ('17 years of cycling experience at Intermediate level') — an obvious internal contradiction. Someone with 17 years of riding who is chasing a podium at an A-priority race is by any reasonable definition an advanced or expert-level rider, not intermediate. This mislabel may have downstream effects on prescribed volume and intensity ceilings.

### 13. [major] ×2  (gravel/masters_returner, road/veteran_podium_chaser)
> Long ride duration range cited as '2.7–4.5 hours' for a target race duration of ~6.8+ hours. No explanation is given for why the peak long ride falls so far short of race duration — even acknowledging the Time-Crunched constraint, this gap deserves a coaching note to manage athlete expectations.

### 14. [major] ×1  (road/veteran_podium_chaser)
> The Weekly Volume automated check flagged a WARN and this was never resolved or explained to the athlete. A 15 h/week target for a 38-year-old with 17 years' experience is high but defensible — however, if the generated weeks deviate materially from 15 h, the athlete deserves to know, and the guide must not silently paper over a QA warning.

### 15. [major] ×1  (road/veteran_podium_chaser)
> Weekly Volume check flagged WARN and the guide never addresses or explains it. A 14h/week athlete is on the high end for a generated plan, and the guide text references a long-ride range of '3.3–5.5 hours' which, combined with 5 training days, seems light for 14h total — the math implies roughly 2.1h average for remaining sessions, which is plausible but tight. Without seeing the calendar it cannot be confirmed correct, but the unresolved WARN is a red flag that must be reconciled before sending.

### 16. [major] ×1  (road/veteran_podium_chaser)
> The 'Category 5 to Category 1 Pathway' section appears in the Table of Contents. This content is entirely inappropriate for a veteran podium-chaser (persona: experienced racer). Cat 5→1 pathway guidance is beginner/progression content that has no place in a plan for someone described as having 6 years of experience chasing a podium at an A-priority race. This smells like a content block inserted from a beginner template.

### 17. [major] ×1  (road/time_crunched_parent)
> Long-ride duration ceiling stated as '1.5–2.5 hours' for a 109-mile (~9.5 h) event. Even for a time-crunched athlete this upper cap is far too low and directly contradicts the 'biggest opportunity' callout a few lines later that urges 3–4 hour rides. The two passages give conflicting guidance.

### 18. [major] ×1  (road/time_crunched_parent)
> FTP Test Frequency is flagged WARN in preview checks but is never surfaced or discussed in the guide. With only a 9-week plan, the athlete needs clarity on whether/when a retest is scheduled; the zone chart says 'sets zones for the next 6 weeks' which implies a retest but none is explicitly addressed for this short plan.

### 19. [major] ×1  (road/time_crunched_parent)
> The athlete identifier 'Avatar 202608072' appears in the document title and header. This is a raw system ID — a paying customer should see their name or a clean label, not an internal avatar hash. This is embarrassing and undermines trust.

### 20. [major] ×1  (gravel/masters_returner)
> Fueling section states a 6.8-hour duration target (from plan JSON) but the guide nowhere reconciles this with the race profile: 93 miles of climbing to Wuling Pass at 125W FTP for a 53-year-old masters woman will almost certainly take longer than 6.8 hours. The 53 g/hr carb figure may be calibrated to the wrong duration, risking under-fueling on race day.

### 21. [major] ×1  (gravel/masters_returner)
> Off days listed in the 'At a Glance' box are Thursday, Monday, AND Friday — three consecutive or near-consecutive off days in a 7 h/week Time-Crunched plan is an unusual and unexplained structure that compresses all training into a very tight window (Tue/Wed/Sat/Sun), which conflicts with the methodology's intent of spreading intensity-dense sessions across the week.

### 22. [major] ×1  (gravel/masters_returner)
> 'Road Skills' section appears in the table of contents without gravel-specific content signals (e.g., loose surface cornering, trail braking, tire pressure for gravel). For a technical mountain climb like Taiwan KOM this is a missed opportunity at best and generic filler at worst.

### 23. [major] ×1  (road/weekend_warrior)
> 'Road Race Strategy' section appears in the table of contents. Gran Fondo Guadeloupe is a granfondo/sportive, not a mass-start road race with tactics, team dynamics, or points finishes. Strategy content oriented around road racing (positioning, attacks, leadouts) is wrong-discipline content for this athlete and event.

### 24. [major] ×1  (road/weekend_warrior)
> Taper Intensity flagged WARN. The guide states 'short, sharp efforts keep the engine awake' in the taper but gives no prescription guidance for what 'sharp' means in terms of zone, duration, or frequency. For a masters athlete (age 50) whose top priority is arriving fresh, an unresolved taper intensity warning is a meaningful coaching gap.

### 25. [major] ×1  (road/weekend_warrior)
> 'Masters Training Considerations' appears in the table of contents but the truncated guide text does not show its content being applied in the body sections visible (e.g., no mention of extended recovery windows, reduced high-intensity frequency, or age-appropriate load caps in the Weekly Structure or Phase Progression sections). Listing it without integrating it is cosmetic.
