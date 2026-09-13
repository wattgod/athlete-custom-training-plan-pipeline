# Improvement backlog — 2026-09-13

**Quality -0.03** · avg coach 5.62/10 · contract pass 75% · load 15.38/plan · 13 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×1  (mtb/weekend_warrior)
> Wrong-discipline content: the Table of Contents and plan body include a 'Gravel Skills' chapter. This is an MTB plan — gravel-specific skills content (e.g. gravel cornering, surface reading for gravel roads) does not belong here. It should be MTB trail skills (switchbacks, rock gardens, drop technique, body position on loose terrain). Sending a mountain biker a gravel skills chapter is an embarrassing discipline mismatch.

### 2. [critical] ×1  (mtb/weekend_warrior)
> Zone Distribution check FAILED in the automated preview and is never explained or remedied in the guide. A known failing check must be resolved before sending — either the zone mix is actually wrong in the calendar (a real training problem) or the flag is a false positive that needs a documented explanation. Shipping a plan with an unacknowledged failing QA gate is not acceptable.

### 3. [critical] ×1  (mtb/weekend_warrior)
> Discipline mismatch — the guide includes sections titled 'Road Skills,' 'Road Race Strategy,' and 'Category 5 to Category 1 Pathway.' The athlete's discipline is MTB. Road racing tactics and the Cat 1-5 classification pathway are irrelevant and actively misleading for an MTB event. These sections must be replaced with MTB-specific content (trail skills, technical descending, MTB race tactics).

### 4. [critical] ×1  (mtb/weekend_warrior)
> Long ride ceiling of 1.5 hours is dangerously undersized for a 68-mile MTB race with an estimated finish time of ~4.7 hours. The guide even acknowledges the shortfall but then caps the peak long ride at 1.5 hours in the same breath. For a finish-goal athlete on a Time-Crunched plan, peak long rides should target at least 2.5–3 hours; the plan as written will leave the athlete massively underprepared for race-day duration demands.

### 5. [critical] ×1  (mtb/weekend_warrior)
> Equipment checklist specifies a 'road bike' as the mandatory training equipment. The athlete is doing an MTB event. This is factually wrong and embarrassing — it must say mountain bike and include MTB-specific items (tubeless setup/plugs, MTB helmet, flat pedal or clipless MTB shoes, suspension setup).

### 6. [critical] ×1  (gravel/ambitious_first_timer)
> Road-racing content included for a gravel athlete: the guide contains sections titled 'Road Skills', 'Road Race Strategy', and 'Category 5 to Category 1 Pathway'. These are categorically wrong for a gravel gran fondo participant — gravel racing has distinct tactical, technical, and licensing conventions. Sending road-race strategy to a gravel rider is embarrassing and erodes trust in the entire plan.

### 7. [critical] ×1  (gravel/ambitious_first_timer)
> Road Race Strategy / Cat 5-to-Cat 1 Pathway section is listed in the Table of Contents. This is a gravel gran fondo (UCI Gran Fondo Loutraki), not a road criterium or road race. Cat 1–5 category progression is a USA Cycling road racing construct that is completely irrelevant — and actively confusing — for a first-timer doing a mass-participation gravel gran fondo. Sending this to a paying customer would be embarrassing and undermine trust in the entire guide.

### 8. [critical] ×1  (gravel/ambitious_first_timer)
> 'Road Skills' section appears in the ToC alongside 'Road Race Strategy'. For a gravel event, this should be gravel-specific skills (loose surface cornering, descending on gravel, tyre pressure management, carrying momentum through technical terrain). Generic road race skills content for a gravel athlete is the wrong discipline entirely.

### 9. [critical] ×1  (road/veteran_podium_chaser)
> Weekly Volume preview check is FAIL. The guide promises 14h/week to this athlete but the automated check flagged it — if the calendar weeks do not actually deliver ~14h, the central contract of the plan is broken and the athlete will be undertrained for a podium attempt.

### 10. [critical] ×1  (road/veteran_podium_chaser)
> "Category 5 to Category 1 Pathway" section appears in the table of contents. This is USA Cycling road-racing category upgrade content and is completely irrelevant to a Gran Fondo event (GFNY Miami has no licensing categories). It is wrong-discipline/wrong-context filler that should never appear in a gran fondo plan.

### 11. [critical] ×1  (gravel/masters_returner)
> Table of contents includes 'Road Race Strategy' and 'Category 5 to Category 1 Pathway' sections — this is a gravel gran fondo plan with a goal of 'finish.' Road race categorical licensing pathways are completely irrelevant and embarrassing content that signals the wrong template was partially merged.

### 12. [critical] ×1  (gravel/masters_returner)
> Zone 1 'Active Recovery' shows power as '0-96W' but has no lower FTP % bound listed — more importantly, the zone table is missing the lower % FTP column value for Zone 1 (shows blank / '1-2' RPE only), making the table internally inconsistent and unprofessional.

### 13. [critical] ×1  (road/time_crunched_parent)
> 'Category 5 to Category 1 Pathway' appears in the table of contents and presumably in the body. This is a USA Cycling road-race category upgrade pathway section — it is completely irrelevant to a gran fondo athlete whose stated goal is a podium finish at GFNY Miami, a mass-participation event with no USA Cycling category system. It will confuse the athlete and undermines credibility.

### 14. [major] ×1  (mtb/weekend_warrior)
> Long-ride cap stated as 1.5 hours, yet the athlete's estimated race duration is ~2.7 hours (30 miles at typical MTB pace). The guide itself flags this as a concern but then does nothing to resolve it within the plan structure. A time-crunched athlete finishing a 2.7-hour race having never ridden longer than 1.5 hours faces a serious durability gap. The plan should prescribe at least 1–2 'breakthrough' long rides of 2.5–3 h during Build/Peak, even if they temporarily exceed the weekly hour budget, rather than leaving the shortfall as an unaddressed advisory note.

### 15. [major] ×1  (mtb/weekend_warrior)
> The 'YOUR BIGGEST OPPORTUNITY' callout suggests 3–4 hour long rides, but the athlete's entire weekly hours target is 4 hours. Recommending a single ride that consumes 75–100% of the weekly training budget — without any guidance on how to restructure the rest of that week — is internally inconsistent and could confuse or demotivate the athlete.

### 16. [major] ×1  (mtb/weekend_warrior)
> Taper Intensity flagged as WARN by the automated gate, yet no compensating explanation or adjustment appears in the guide text. A 55-year-old masters athlete needs slightly longer taper; the guide's generic taper language does not address this, and the unresolved WARN is a liability.

### 17. [major] ×1  (mtb/weekend_warrior)
> Masters Training Considerations is listed in the table of contents but the truncated text contains no corresponding section content visible in the excerpt. Given the athlete is 55 with high stress and only fair sleep, this section is not optional — if it is missing or boilerplate, it must be completed with age-appropriate recovery guidance (extended recovery windows, reduced back-to-back intensity, etc.).

### 18. [major] ×1  (mtb/weekend_warrior)
> The guide references 'L'Étape Ciudad de México' as an MTB event, but L'Étape by Tour de France events are traditionally road cycling gran fondos. The race_in_verified_db flag says treat the data as real, but the plan's discipline tag of 'mtb' conflicts with the known character of this event series. If the event is actually a road gran fondo, the entire discipline framing of the plan is wrong; if it genuinely is an MTB edition, all the road-specific content insertions are doubly inexcusable. Either way, a critical content conflict exists that must be resolved before sending.

### 19. [major] ×1  (gravel/ambitious_first_timer)
> Athlete weight (159 lbs / 72.1 kg / 5'6") appears in the profile card but the intake JSON contains no weight or height fields for this athlete. This figure appears to be a template default or data from a different athlete leaked into this plan — it must not be sent without verification.

### 20. [major] ×1  (gravel/ambitious_first_timer)
> Preview check flags two WARNings (FTP Test Frequency and Taper Intensity) that are unresolved and unexplained in the guide text. FTP Test Frequency is particularly relevant because the plan is 9 weeks with an unknown FTP — if only one test is scheduled, a WARN here suggests the retesting cadence may be insufficient. The taper intensity WARN could mean the taper is not sufficiently sharp for a peak-priority A-race. Neither issue is addressed in the guide.

### 21. [major] ×1  (gravel/ambitious_first_timer)
> Experience contradiction: the profile states '1 Years Riding' at 'Intermediate level', but the persona is 'ambitious_first_timer'. A first-timer is not Intermediate — or if the system has classified them as Intermediate based on 1 year, that classification should not be surfaced verbatim alongside 'first-timer' framing without reconciliation. This inconsistency will confuse the athlete and erode confidence in the plan's personalization.

### 22. [major] ×1  (road/veteran_podium_chaser)
> Taper Intensity flagged WARN. For a veteran podium-chaser targeting an A-race, the taper must preserve neuromuscular sharpness with correctly dosed high-intensity work. A vague or soft taper is a significant coaching error at this performance level — the guide text does not clearly specify short, sharp taper efforts.

### 23. [major] ×1  (road/veteran_podium_chaser)
> Zone Distribution flagged WARN and TSS Progression flagged WARN. For a pyramidal plan at 14h/week, these should be clean passes. Sending a plan with both warnings unresolved risks the athlete spending too much time in Zone 3 or experiencing an irregular TSS ramp — both contradict the stated methodology.

### 24. [major] ×1  (road/veteran_podium_chaser)
> The guide describes the athlete as "Intermediate level" despite 17 years of riding and a podium goal. A 17-year veteran with a 240W FTP chasing a podium is not intermediate — this label is inconsistent, potentially insulting to the athlete, and undermines trust in the plan's personalization claims.

### 25. [major] ×1  (road/veteran_podium_chaser)
> FTP Test Frequency flagged WARN. The guide states the FTP test result sets zones "for the next 6 weeks" — in an 8-week plan with a retest presumably around week 4-5, telling the athlete one test governs 6 weeks is arithmetically inconsistent and could mean they race on stale zones.
