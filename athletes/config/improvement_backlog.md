# Improvement backlog — 2026-06-21

**Quality 2.76** · avg coach 5.75/10 · contract pass 38% · load 6.88/plan · 4 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×1  (mtb/weekend_warrior)
> Discipline mismatch: The table of contents explicitly lists a 'Gravel Skills' section. This is an MTB race plan. Gravel cornering, gravel-specific handling drills, or any gravel-framed skills content has no place here and will confuse or embarrass the athlete. Must be replaced with MTB-specific technical skills content (singletrack cornering, braking technique, body position on roots/rocks, etc.).

### 2. [critical] ×1  (gravel/weekend_warrior)
> Race database status contradiction: The plan facts explicitly state the race comes from a 'verified race database — treat as real' and the preview checks all passed, yet the guide displays 'Race not in database — please verify your date independently' with an alarming triple-check warning. This will destroy athlete confidence in the entire plan and is factually wrong given the source data.

### 3. [critical] ×1  (gravel/weekend_warrior)
> Fueling duration is 0.0 hours in the plan JSON, which means the nutrition strategy section and any race-day fueling guidance (70g/hr carbs) is being applied to a zero-length event. This is either a data pipeline bug or a misconfiguration — either way, race-day fueling advice anchored to a 0.0h duration is nonsensical and potentially harmful if the athlete acts on it.

### 4. [critical] ×1  (road/weekend_warrior)
> The plan states the peak long ride is 1.5 hours for a 78-mile event that will take the athlete approximately 4.5–5.5 hours. The guide itself admits this is 'shorter than ideal' and recommends 3–4 hour rides, yet the prescribed ceiling is 1.5 hours. This is a direct internal contradiction that a paying customer will catch immediately and that will destroy trust in the plan. The long-ride cap must reflect realistic weekend-warrior constraints honestly, or the plan must be restructured to push the long ride higher (e.g., 2.5–3h) in Build/Peak with explicit guidance on how to find that time.

### 5. [major] ×1  (mtb/weekend_warrior)
> Off-days listed as 'Tuesday, Friday, Thursday' — three days listed in a non-sequential, confusing order for a 5h/week athlete who should have exactly 3 off days. The ordering (Tue, Fri, Thu) reads like a data-rendering bug and will make the athlete question whether the plan was generated correctly.

### 6. [major] ×1  (mtb/weekend_warrior)
> Plan start date mismatch: The JSON sets plan_start_date as 2026-06-29, but the guide header references 'Avatar 202606210' suggesting a generation artifact around June 21. The countdown shown is '139 days from today' — which does not align with a June 29 start to a November 7 race (that gap is ~131 days). This inconsistency will erode athlete trust in the date math.

### 7. [major] ×1  (mtb/weekend_warrior)
> Zone 1 (Active Recovery) is missing its HR% and FTP% columns in the zone chart — every other zone has them. This looks like a rendering drop and leaves the athlete without complete zone anchors for their lowest-intensity work, which is the most-used zone in a polarized plan.

### 8. [major] ×1  (gravel/weekend_warrior)
> Race distance is 0 miles in the source data, yet the guide confidently references specific long-ride duration ranges ('2.1–3.5 hours') without any noted uncertainty about event length. If the distance is truly unknown, these numbers are fabricated and the plan should flag the gap rather than invent specifics.

### 9. [major] ×1  (gravel/weekend_warrior)
> Gravel-specific skills content is listed in the table of contents ('Gravel Skills' chapter) which is correct for the discipline, but the truncated text does not confirm the body contains gravel-appropriate content (e.g., loose surface cornering, tire pressure, loaded descending) rather than generic road or cross content. Given the discipline mismatch risk flagged in the QA brief, this chapter needs verification before sending.

### 10. [major] ×1  (road/weekend_warrior)
> The countdown reads '104 days from today' — this is a dynamic value that appears to have been calculated at generation time and hardcoded. If the email is delayed even a day or two, the number will be wrong. Either remove it or make clear it was calculated as of a specific date.

### 11. [major] ×1  (road/weekend_warrior)
> The 'G Spot' zone label (between Tempo and Threshold) is non-standard and informal to the point of being potentially off-putting or unprofessional for some customers, especially in a paid product. It needs either a more conventional label (e.g., 'Sweet Spot') or at minimum a note acknowledging the colloquial name.

### 12. [minor] ×1  (mtb/weekend_warrior)
> The guide references 'Strength training: Included (bodyweight)' in the at-a-glance block, but no strength content is visible in the truncated guide and it is not listed as a phase-specific element in the phase progression section. If strength work appears only in the calendar and not in the guide narrative, the athlete has no execution context for it.

### 13. [minor] ×1  (mtb/weekend_warrior)
> The 'GS G Spot' zone label (Zone 3.5 / 88-93% FTP) is unconventional jargon that may read as unprofessional or confusing to a mainstream weekend-warrior athlete. It is not a standard polarized zone designation and should either be renamed or given a brief explanatory note.

### 14. [minor] ×1  (gravel/weekend_warrior)
> The intensity distribution is described as '50% easy / 35% tempo / 15% hard' but then the zone chart labels the distribution as Sweet Spot/Threshold. For a gravel 'finish' goal athlete, 35% tempo is on the high side and may not match what the calendar actually prescribes — the prose and the methodology should align precisely.

### 15. [minor] ×1  (gravel/weekend_warrior)
> The athlete's weight (192 lbs / 87.1 kg) and height (5'6") are displayed in the profile section but were not present in the plan JSON athlete object — these figures appear to have come from somewhere (questionnaire presumably) but cannot be verified against the provided data, creating a potential for a mismatch embarrassment if wrong.

### 16. [minor] ×1  (road/weekend_warrior)
> The TSS Progression check returned WARN in the preview checks, but the guide text contains no acknowledgment of this or any compensating explanation. A coach reviewing the plan should understand why TSS progression is flagged and whether it represents a real concern for this athlete.

### 17. [minor] ×1  (road/weekend_warrior)
> The off-day schedule lists Saturday as an off day, but the 'YOUR BIGGEST OPPORTUNITY' callout specifically suggests 'clearing a Saturday morning' for longer rides — this directly conflicts with Saturday being a prescribed rest day and may confuse the athlete.
