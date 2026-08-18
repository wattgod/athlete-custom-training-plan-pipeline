# Improvement backlog — 2026-08-18

**Quality -1.97** · avg coach 5.38/10 · contract pass 25% · load 17.12/plan · 11 critical issue types

Ranked recurring issues (frequency × severity). Fix top-down; each fix must keep tests green AND raise the quality score.

### 1. [critical] ×3  (road/veteran_podium_chaser, road/weekend_warrior)
> 'Category 5 to Category 1 Pathway' section appears in the table of contents. This is a road-racing/category-upgrade framework that is completely irrelevant to a gran fondo finisher and actively misleading — it implies the athlete is pursuing USA Cycling upgrade points, which has nothing to do with a mass-participation gran fondo. Must be removed before sending.

### 2. [critical] ×1  (road/masters_returner)
> A 'Gravel Skills' chapter appears in the table of contents and presumably in the body of a plan written for a ROAD discipline athlete. Gravel cornering, surface-reading, and similar skills content is irrelevant and actively misleading for a road racer — this is a wrong-discipline content injection and is embarrassing.

### 3. [critical] ×1  (road/masters_returner)
> Equipment checklist says 'Bike — gravel or similar' for a road-discipline athlete. The Bowral Classic is a road sportive; prescribing a gravel bike contradicts the discipline flag and could influence an athlete's equipment decision incorrectly.

### 4. [critical] ×1  (gravel/masters_returner)
> Wrong discipline content: the guide includes a 'Road Race Strategy' section and a 'Category 5 to Category 1 Pathway' section. This athlete is training for a GRAVEL gran fondo, not a road criterium or road race. Cat 5-to-1 licensing pathway content is completely irrelevant and will confuse or embarrass the customer.

### 5. [critical] ×1  (gravel/masters_returner)
> Per-Day Duration Cap FAIL (flagged by automated check): with only 7 hours/week across 4 training days, at least one session in the plan apparently exceeds the per-day cap. A long-ride ceiling of 4.5 hours is cited in the guide, but 4.5h on a 7h week leaves only 2.5h for three other sessions — this is almost certainly the source of the flag and needs immediate review and correction before sending.

### 6. [critical] ×1  (road/veteran_podium_chaser)
> Plan length mismatch: the JSON states plan_weeks = 11 and plan_start_date = 2026-08-24, but the race date is 2026-11-08 — that span is only 11 weeks and 1 day, which is consistent. However, the guide's own countdown banner reads '82 days from today,' which would place 'today' around 2026-08-18. If the countdown is computed at generation time rather than from the plan start date, it will be stale and confusing the moment the email is opened even a few days later. The countdown banner should either be removed or replaced with a fixed 'Race date: November 8, 2026' statement.

### 7. [critical] ×1  (gravel/ambitious_first_timer)
> Wrong-discipline content: the table of contents and guide body include 'Road Race Strategy' and a 'Category 5 to Category 1 Pathway' section. This athlete is preparing for a gravel gran fondo, not a road criterium or road race. These sections belong to a road-racing template and are completely inappropriate here — they will confuse and embarrass.

### 8. [critical] ×1  (gravel/ambitious_first_timer)
> Per-Day Duration Cap check is a hard FAIL per the automated preview. The guide text references long rides of '2.7-4.5 hours' and an 8h weekly budget, but at least one day apparently violates the per-day cap. This is a concrete plan integrity error that must be resolved before sending.

### 9. [critical] ×1  (gravel/time_crunched_parent)
> 'Road Race Strategy' and 'Category 5 to Category 1 Pathway' sections appear in the table of contents for a gravel gran fondo plan. These are road-racing/criterium concepts that are completely wrong for this event and athlete, and will immediately undermine credibility with the customer.

### 10. [critical] ×1  (gravel/time_crunched_parent)
> Equipment checklist specifies a 'road bike' as the mandatory training bike. This athlete is preparing for a gravel event (Atlas Gran Fondo) — the checklist should reference a gravel bike, and road-bike-specific equipment assumptions (e.g., no mention of gravel-appropriate tires, tubeless setup, or wider tires) are potentially misleading and dangerous.

### 11. [critical] ×1  (road/veteran_podium_chaser)
> Weekly Volume preview check is flagged FAIL and was never resolved. Sending a plan with a known volume failure to a paying athlete — especially one targeting a podium — is unacceptable. The volume issue must be identified, corrected, and re-checked before release.

### 12. [major] ×1  (road/masters_returner)
> The automated preview check shows Per-Day Duration Caps as FAIL. The guide text references long rides of '2.1–3.5 hours' within a 6 h/week Time-Crunched plan — the upper end (3.5 h) may breach the per-day cap for this methodology and hours target, and the FAIL was not resolved before this draft was queued for delivery.

### 13. [major] ×1  (road/masters_returner)
> Zone Distribution and TSS Progression both show WARN status. Neither issue is addressed or explained in the guide text, meaning the plan may be delivered with a skewed zone split or an irregular TSS ramp that could lead to overtraining or undertraining in a masters returner who is already at elevated injury/fatigue risk.

### 14. [major] ×1  (road/weekend_warrior)
> Long-ride duration estimates in the Weekly Structure section cite '1.5–2.2 hours' as peak long-ride length and suggest 'a single 3–4 hour ride' as aspirational. For a race estimated at ~5.75 hours, this is a major undershoot — the athlete needs to know that their longest training ride should ideally approach 3–4 hours as a baseline, not as a stretch goal. The framing undersells the durability gap and may leave the athlete underprepared.

### 15. [major] ×1  (road/weekend_warrior)
> The guide repeatedly warns against Zone 3 ('gray zone — too hard to recover from, too easy to adapt'), but the Time-Crunched methodology explicitly prescribes Tempo/Sweet Spot (Z3–GS) as a core training tool for time-limited athletes. This creates a direct internal contradiction: the methodology section promotes intensity-dense sessions while the zones section tells the athlete to avoid Z3 except when prescribed. The framing will confuse athletes and undermine confidence in prescribed tempo work.

### 16. [major] ×1  (gravel/masters_returner)
> Three off-days per week (Sunday, Saturday, Friday) for a 7h/week athlete is an unusual and potentially problematic structure. Three consecutive weekend/Friday rest days means all 7 hours are compressed into Monday–Thursday, creating an aggressive mid-week block with no weekend long ride — the traditional and most practical day for gravel athletes. This needs to be confirmed as intentional athlete input, not a scheduling error.

### 17. [major] ×1  (gravel/masters_returner)
> TSS Progression WARN and Taper Intensity WARN are both flagged by the automated pre-checks but are not addressed or acknowledged anywhere in the guide. A progressive TSS issue could indicate a ramp rate that is too steep or an inconsistent taper — either could lead to overtraining or an underprepared race day for a 53-year-old masters athlete where recovery is especially critical.

### 18. [major] ×1  (road/veteran_podium_chaser)
> Zone Distribution check is FAIL in the preview, yet the guide contains no acknowledgment or correction of the zone distribution problem. Sending a plan with a known FAIL check without either fixing the underlying schedule or explicitly flagging it to the athlete is a quality-control gap that could result in weeks of wrongly distributed training.

### 19. [major] ×1  (road/veteran_podium_chaser)
> Weekly Volume check is WARN. The guide never addresses this. For an athlete targeting 11 h/week, volume distribution should be explicitly confirmed or the discrepancy explained. Shipping a plan with an unresolved volume warning is a coaching credibility risk.

### 20. [major] ×1  (road/veteran_podium_chaser)
> The fueling section references 67 g/h of carbohydrate and a projected race duration of ~4.4 hours (from JSON), but the truncated guide text does not visibly present these numbers in context. More importantly, 67 g/h is below the modern evidence-supported ceiling for trained athletes (90–120 g/h with multi-transportable carbs), and for a podium-chasing masters racer at a 4+ hour event this is a meaningful under-fueling risk. The number should be reviewed and, if kept, justified with a rationale (e.g., gut tolerance, conservative ramp-up).

### 21. [major] ×1  (gravel/ambitious_first_timer)
> TSS Progression check is WARN and Taper Intensity check is WARN — neither fatal alone, but combined they indicate the underlying calendar may have a ramp that is too steep early and/or insufficient intensity retention during taper. The guide text makes no acknowledgment or coaching note to the athlete about how to handle any unusual weeks, leaving them without guidance if they notice the anomaly.

### 22. [major] ×1  (gravel/ambitious_first_timer)
> 'Road Skills' section appears in the table of contents. For a gravel event, this should be gravel-specific skills (loose surface cornering, mud/sand riding, technical descents, tire pressure management) — not generic road skills. The content visible suggests a road-racing template was only partially adapted.

### 23. [major] ×1  (gravel/ambitious_first_timer)
> The guide states the G Spot zone LTHR as '92-96% LTHR' but the standard pyramidal literature places this zone at approximately 94-97% LTHR, overlapping with the lower threshold zone. The LTHR boundary as written conflicts with Zone 4's '95-105% LTHR' lower bound, creating a confusing 2-percentage-point overlap that a first-timer will not know how to resolve.

### 24. [major] ×1  (gravel/weekend_warrior)
> Per-Day Duration Caps check is flagged FAIL by the automated gate. The guide text mentions long-ride peaks of '1.9-3.2 hours' — the upper bound of 3.2 hours is plausible within a 7 hr/week budget, but the FAIL flag suggests at least one scheduled day exceeds the per-day cap. This must be resolved in the calendar before sending; if a single day is over-prescribed it contradicts the Time-Crunched promise and risks injury for a weekend warrior.

### 25. [major] ×1  (gravel/weekend_warrior)
> FTP Test Frequency is flagged WARN. For a 9-week plan with no known FTP, only one field test (Week 1) appears to be scheduled. Best practice for this plan length is a mid-plan re-test (around Week 5-6) so zones can be updated as fitness improves during Build. Skipping a second test means the athlete may be training to stale RPE anchors in Peak — weakening the plan's specificity claim.
