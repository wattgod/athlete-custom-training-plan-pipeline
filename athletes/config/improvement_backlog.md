# Improvement backlog — 2026-07-28

**Quality -1.8** · avg coach 4.75/10 · contract pass 75% · load 17.62/plan · 16 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×1  (mtb/ambitious_first_timer)
> Discipline mismatch: the athlete profile specifies 'mtb' yet the plan is titled 'Gravel Revival 75mi Training Guide,' the table of contents includes a 'Gravel Skills' chapter, and all discipline-specific language references gravel riding. If the athlete is truly an MTB rider entered in a gravel event, the plan must acknowledge that and swap gravel-specific skills/execution content for MTB-appropriate content (technical descending, singletrack cornering, etc.). If the race IS a gravel event and discipline should be gravel, the athlete record is wrong and must be reconciled before sending — either way this cannot go out as-is.

### 2. [critical] ×1  (mtb/ambitious_first_timer)
> Experience level contradiction: the guide states '1 years of cycling experience at Intermediate level' — 1 year of experience is beginner, not intermediate. Labeling a 1-year rider as Intermediate misstates their development stage and could lead to inappropriate training decisions or erode coach credibility.

### 3. [critical] ×1  (gravel/weekend_warrior)
> Table of contents and apparent plan content includes 'Road Race Strategy' and 'Category 5 to Category 1 Pathway' sections. This athlete is a gravel rider targeting a 43.5-mile gravel event with a goal of 'finish' — road racing categories and cat-upgrade strategy are completely irrelevant and will confuse or embarrass.

### 4. [critical] ×1  (gravel/weekend_warrior)
> The long ride is capped at 1.5 hours in the guide text. The fueling section stipulates a 2.8-hour estimated race duration, meaning the athlete will never train at or near race duration. For a 43.5-mile gravel event, this is a significant preparation gap that the guide itself quietly acknowledges but then fails to resolve structurally.

### 5. [critical] ×1  (gravel/time_crunched_parent)
> Road-racing content injected into a gravel plan: the Table of Contents lists 'Road Skills,' 'Road Race Strategy,' and 'Category 5 to Category 1 Pathway' sections. These are entirely wrong-discipline content for a gravel gran fondo athlete. A Cat 5–Cat 1 upgrade pathway is a USA Cycling road racing concept with zero relevance here, and road race tactics (peloton positioning, sprint lead-outs, etc.) differ materially from gravel race strategy. This would confuse and embarrass.

### 6. [critical] ×1  (gravel/time_crunched_parent)
> Fueling carb figure contradicts the plan's own data: the JSON specifies 64g carbs/hour, but the guide's 'Weekly Structure' long-ride note references a 1.9–3.2 hour duration window and the fueling JSON sets duration_h at 4.0h — implying a race-day target of ~256g total (64 × 4). Nowhere in the visible text is 64g/hr cited; instead the recovery protocol references '71–85g carbs' post-ride without tying it to the 64g/hr race fueling figure, creating a silent contradiction that will mislead the athlete about in-race nutrition.

### 7. [critical] ×1  (gravel/masters_returner)
> 'Category 5 to Category 1 Pathway' section appears in the table of contents and presumably in the guide body. This is a USA Cycling road-racing licensing concept that is entirely irrelevant to a gravel event (L'Étape Ciudad de México) and to this athlete's stated goal of 'finish.' It will confuse and undermine credibility.

### 8. [critical] ×1  (gravel/masters_returner)
> 'Road Race Strategy' section is listed in the ToC. This is a gravel event, not a road race. Tactics, pack dynamics, and strategy for a road race are incorrect for gravel and should be replaced with gravel-specific content (pacing on mixed terrain, self-sufficiency, aid station management, etc.).

### 9. [critical] ×1  (mtb/weekend_warrior)
> Wrong discipline content throughout: the guide includes a 'Road Skills', 'Road Race Strategy', and 'Category 5 to Category 1 Pathway' section (visible in the table of contents). This athlete is an MTB racer. Road racing categories, road cornering cues, and road-specific strategy are irrelevant and actively misleading for mountain biking.

### 10. [critical] ×1  (mtb/weekend_warrior)
> The Sparkassen Münsterland Giro is a road cycling gran fondo / race, not an MTB event. The verified race database confirms it takes place in Münster, North Rhine-Westphalia — a flat to gently rolling region of Germany famous for a road cycling event. The athlete's discipline is flagged as 'mtb' but the race is on-road. Either the discipline tag is wrong (athlete may have selected MTB in error) or the race assignment is wrong. This contradiction must be resolved before sending — coaching content, skills sections, and terrain cues are built for the wrong surface.

### 11. [critical] ×1  (mtb/weekend_warrior)
> Per-Day Duration Cap check is FAIL in the automated preview. The guide text was truncated so the specific offending session cannot be confirmed, but a flagged cap violation for a 4 h/week athlete whose long ride budget should be roughly 90–120 min means at least one day likely prescribes an unrealistic duration. This must be corrected before sending.

### 12. [critical] ×1  (gravel/veteran_podium_chaser)
> Wrong discipline content — the guide includes a 'Road Skills,' 'Road Race Strategy,' and 'Category 5 to Category 1 Pathway' section (visible in the Table of Contents). This athlete is a gravel racer. Road racing categories (Cat 5 to Cat 1) are entirely irrelevant and potentially insulting to an 18-year veteran. These sections must be replaced with gravel-specific content (e.g., loose-surface cornering, singletrack/doubletrack technique, gravel race strategy).

### 13. [critical] ×1  (gravel/veteran_podium_chaser)
> Off-day scheduling contradiction: the plan states 'Off days: Saturday, Sunday — Long rides: Tuesday.' For a 13h/week experienced racer targeting a Saturday gravel century, placing the long ride on Tuesday and both rest days on the weekend is highly atypical and functionally poor — it eliminates weekend outdoor long-ride opportunities and buries the hardest session mid-week when most athletes have work commitments. This needs explicit justification or correction.

### 14. [critical] ×1  (mtb/weekend_warrior)
> Discipline mismatch — the guide contains a 'Road Race Strategy' section and a 'Category 5 to Category 1 Pathway' section. This athlete is doing an MTB gran fondo (discipline: mtb). Road racing category progression and road criterium/pack-race tactics are completely irrelevant and embarrassing to send to an MTB rider.

### 15. [critical] ×1  (mtb/weekend_warrior)
> The long ride is capped at 1.5 hours in a plan for a 65-mile MTB gran fondo with an estimated ~4.1-hour finish time. The guide itself acknowledges the problem but then prescribes only 1.5 h as the peak long ride. A 1.5 h long ride is less than 37% of race duration — dangerously underprepared for a 'finish' goal. The Per-Day Duration Cap FAIL flag in the preview checks is unresolved and directly related to this.

### 16. [critical] ×1  (mtb/weekend_warrior)
> The preview check 'Per-Day Duration Caps: FAIL' is a known flagged issue that has not been corrected or even acknowledged in the guide text. Sending a plan with a known FAIL flag without resolution or explanation to the athlete is unacceptable.

### 17. [major] ×2  (gravel/time_crunched_parent, mtb/ambitious_first_timer)
> Long ride duration range cited as '2.7-4.5 hours' in the Weekly Structure section. At 8 hours/week over a 10-week pyramidal plan targeting a ~6.7-hour race, a 4.5-hour long ride cap is plausible only at peak, but 2.7 hours as a floor seems low for Week 1 of base at this volume. More importantly, no source or calculation is shown — if these numbers are auto-generated they should be spot-checked against the actual calendar, and the wide range without phase context may confuse a first-timer.

### 18. [major] ×1  (mtb/ambitious_first_timer)
> Plan start date mismatch: the JSON states plan_start_date = 2026-08-10 and weeks_until_race = 11, but the plan is only 10 weeks long. Per the plan_note the athlete simply starts one week later (2026-08-17). The guide never tells the athlete when to START the plan, which is a significant omission — a first-timer will not know to wait a week and may start immediately on receiving this guide, misaligning their taper with race day.

### 19. [major] ×1  (mtb/ambitious_first_timer)
> The 'Years Riding: 1' combined with 'Intermediate level' label is internally inconsistent within the guide itself (the profile box and the methodology rationale both appear in the same document with conflicting characterizations), which will undermine athlete trust.

### 20. [major] ×1  (gravel/masters_returner)
> The 'At a Glance' section lists THREE off days (Monday, Saturday, AND Friday), yet the Weekly Structure section states the athlete has 4 training days. Three off days on a 7-day week leaves only 4 days, which is arithmetically consistent — but then the plan also mentions 'strength training included,' implying a fifth session type. More critically, Friday AND Saturday as consecutive off days with Sunday as the long ride means the athlete has no easy ride buffer before the long ride if Saturday is also off. This needs to be verified against the actual calendar; as written it is confusing and potentially contradictory depending on how strength days are counted.

### 21. [major] ×1  (gravel/masters_returner)
> The Weekly Volume automated check returned WARN but no explanation or mitigation is provided anywhere in the guide text. For a masters returner at 8h/week, a volume warning could indicate weeks exceed the target or ramp rate is too steep — either way, a paying customer should not receive a plan with a flagged structural issue that the guide text neither addresses nor explains.

### 22. [major] ×1  (gravel/weekend_warrior)
> The fueling recommendation of 58g carbs/hour for a 2.8-hour effort is internally consistent, but the plan never reconciles how the athlete practices this in training when no ride reaches 2.8 hours. The race-simulation and dress-rehearsal fueling mentioned in the Peak phase description is hollow if ride length never approaches race duration.

### 23. [major] ×1  (gravel/weekend_warrior)
> 'Road Skills' section appears in the table of contents for a gravel athlete — if this covers road-specific cornering, drafting, or peloton skills rather than gravel-specific skills (loose surface cornering, bike handling on descents, gear selection on gravel), it is wrong-discipline content.

### 24. [major] ×1  (gravel/weekend_warrior)
> Off days are listed as 'Wednesday, Tuesday, Monday' — three consecutive days off in a 4-hour/week plan effectively compresses all riding into Thu–Sun. While not impossible, listing Monday–Wednesday as off days should be explicitly justified or the ordering clarified, as it reads oddly and may reflect a template error.

### 25. [major] ×1  (gravel/time_crunched_parent)
> Saturday is listed as an off day, but for a time-crunched parent whose long ride is Sunday, Saturday is the natural 'day-before' easy prep or second long outdoor ride opportunity. More importantly, the plan simultaneously states 'aim for at least 1–2 outdoor rides per week' yet locks off both weekend days except Sunday — making that goal structurally impossible to achieve within the stated 4 training days. The off-day logic needs re-examination for this persona.
