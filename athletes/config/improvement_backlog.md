# Improvement backlog — baseline-v1

**Quality -1.4** · avg coach 4.0/10 · contract pass 40% · load 13.0/plan · 8 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×1  (gravel/veteran_podium_chaser)
> Week-count contradiction: The JSON specifies a 17-week plan but the guide title, intro, and Phase Progression section all state '15 weeks.' This is a direct factual conflict visible to the athlete on the first page and will destroy trust immediately.

### 2. [critical] ×1  (gravel/veteran_podium_chaser)
> FTP test protocol is broken and dangerous: The protocol lists a '5-minute ALL OUT' effort followed by a '20-minute ALL OUT' effort with only a 5-minute recovery between them. A proper 20-minute FTP test requires a full 5-minute maximal blowout effort BEFORE the 20-minute test (to deplete anaerobic reserves), not a second surprise all-out effort after an already maximal 5-minute bout. As written, the athlete will produce a meaningless, artificially low 20-minute power number and set wrong zones for 6 weeks — the guide's own stated consequence of a bad test.

### 3. [critical] ×1  (gravel/veteran_podium_chaser)
> Methodology description is inaccurate: The guide states '12 years of cycling experience at Intermediate level' for a persona labeled 'Experienced racer chasing a podium' (veteran_podium_chaser). A veteran podium chaser is not an intermediate-level rider. This misrepresents the athlete's experience tier in a document personalized to them.

### 4. [critical] ×1  (road/time_crunched_parent)
> Plan duration mismatch: the JSON says 10 weeks out but the document repeatedly states '8-week plan' and '8 weeks.' The athlete will be confused about when their plan actually starts and the taper timing will be wrong.

### 5. [critical] ×1  (road/time_crunched_parent)
> Gravel Skills section included for a road discipline athlete. This is the wrong content entirely — gravel cornering, loose-surface braking, and similar skills drills do not belong in a road racing plan and will undermine coaching credibility.

### 6. [critical] ×1  (road/time_crunched_parent)
> Long ride peak duration stated as '1.5-1.5 hours' — this is clearly a template rendering error (likely a variable substitution failure). For an 81-mile / ~6.8-hour event, this number is also dangerously low and contradicts the guide's own advice to do 3-4 hour rides.

### 7. [critical] ×1  (road/time_crunched_parent)
> Off Days Respected check is FAIL: the plan promises specific off days (Tuesday, Friday) but the automated check confirms these are violated somewhere in the calendar. Sending a plan with known scheduling conflicts is unacceptable.

### 8. [critical] ×1  (road/time_crunched_parent)
> Zone Distribution check is FAIL: the stated 50/35/15 distribution does not match what is actually scheduled. The methodology claim is contradicted by the actual workouts — athlete will be training in the wrong zones relative to what is promised.

### 9. [major] ×1  (gravel/veteran_podium_chaser)
> Fueling duration mismatch: The JSON specifies fueling.duration_h = 9.4 hours, but a 150-mile gravel race with 2800 ft of climbing for a 305W FTP athlete targeting a podium would realistically finish in roughly 7.5–9 hours. 9.4 hours is on the outer edge but plausible only for mid-pack; for a podium goal it is likely too conservative and should be flagged. More importantly, the guide text does not surface the 9.4-hour race duration or the 88 g/hr carb target anywhere in the truncated nutrition section — a critical omission for a 150-mile event where fueling is a primary limiter.

### 10. [major] ×1  (gravel/veteran_podium_chaser)
> Zone Distribution check is WARN (not PASS): The preview flag indicates a zone distribution warning, yet the guide text makes no mention of this deviation, offers no explanation to the athlete, and presents the pyramidal distribution as if it were cleanly achieved. A coach would at minimum acknowledge and contextualize any flagged deviation.

### 11. [major] ×1  (road/time_crunched_parent)
> TSS Progression is WARN and Taper Intensity is WARN — neither is addressed or explained anywhere in the guide text, leaving potential under-taper or spike-load issues unacknowledged for a 47-year-old masters athlete.

### 12. [major] ×1  (road/time_crunched_parent)
> The FTP test protocol describes a '5 minutes ALL OUT' effort followed by a '20 minutes ALL OUT' effort with no explanation of the relationship between them. A standard Coggan 20-min test does not include a preceding 5-min all-out as described here — this will skew the result and confuse the athlete.

### 13. [major] ×1  (road/time_crunched_parent)
> Zone 1 power range is listed as '0-64W' but Zone 2 starts at '66-88W,' leaving a 65W gap that is undefined. This is a display/calculation error that will cause athlete confusion when following prescribed zones.

### 14. [major] ×1  (road/time_crunched_parent)
> The 'YOUR BIGGEST OPPORTUNITY' callout advises single rides of 3-4 hours, yet the Per-Day Duration Cap check PASSed — these two pieces of information are potentially contradictory and need to be reconciled explicitly for a 5 hr/week athlete.

### 15. [minor] ×1  (gravel/veteran_podium_chaser)
> Long ride duration range cited as '4.6–7.8 hours' in the Weekly Structure section but the plan is only 15 (or 17) weeks and the race is 9.4 hours — the upper long-ride ceiling of 7.8 hours may be under-explained relative to the race duration, especially since Long Ride vs Race Duration passed its check (implying the calendar handles it), but the guide text number could alarm the athlete that they never ride close to race length.

### 16. [minor] ×1  (road/time_crunched_parent)
> The guide refers to 'Eroica Germania' as implicitly a gravel/vintage event (it is a gravel-style gran fondo on historic roads) yet the discipline is tagged as 'road' — the cadence drill advice to 'grind up climbs' for 'gravel racing' leaks through from a gravel template, reinforcing the discipline mismatch.

### 17. [minor] ×1  (road/time_crunched_parent)
> Post-ride recovery nutrition references '56kg body weight' but the athlete profile states 123 lbs (55.8 kg) — while numerically close, the rounding inconsistency and unit mixing within the same section looks sloppy and uncoached.

### 18. [minor] ×1  (road/time_crunched_parent)
> The guide text is truncated mid-sentence in the Recovery Protocol section ('weigh'), meaning critical hydration guidance is missing from the delivered document.
