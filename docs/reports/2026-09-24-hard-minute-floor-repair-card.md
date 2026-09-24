# Motoren hard-minute floor: generator repair card (2026-09-24)

## Rehearsal finding

The ten-order offline replay produced 47 `HARD_MINUTES_BELOW_FLOOR` findings across seven orders: long runway 13; unknown FTP 5; HR/RPE 5; full gym 6; no strength 6; joint A races 6; repeat buyer first 6. The other three orders had none. These are load-week findings only. The current counter in `post_render_validator.py` credits structured bike time at or above 92% FTP and expands repetition blocks; it does not credit lower-target tempo, sweet spot, or endurance work.

Two representative sealed plans expose distinct constraints:

- `cohort-05`, 12 cycling hours/week, four structured years: Saturday is the long ride, Thursday is unavailable, and Tuesday is the sole generated intensity day in weeks 1–3. Tuesday's hard-minute dose is 5.3, 25.0, then 30.0 minutes; the other riding contributes only 0.5, 0.7, then 3.4 minutes. Moving intensity to Friday would adjoin Saturday's long ride; adding VO2 repetitions is constrained by AE-3.1. This order also has separate VO2-dose findings in the replay.
- `cohort-06`, six cycling hours/week, three structured years: the schedule permits Monday and Friday intensity around a Wednesday long ride. The existing library selection gives 5.0 VO2 + 30.0 threshold minutes in week 1, 10.0 + 33.5 in week 2, and 14.0 + 41.5 in week 3: 35.0, 43.5, and 55.5 total, still below 90. More hard days would conflict with the athlete's available days and AE-2.1 day cap.

The first three failing orders with zero structured years (`cohort-02`, `cohort-03`, `cohort-04`) reveal a separate AE-1.10 precedence issue. The current generator gives them VO2 work without modeling the six-week frequency, six-week duration, and conversational-ride graduation sequence. Exempting them from the floor solely because `years_structured == 0` would hide that programming defect. `plan_ir.training_age_class()` also labels some of these athletes `experienced` based on years cycling, which is not evidence of passing AE-1.10's intensity gate.

## Why this needs a bounded design ruling before a code change

AE-2.1 ratifies 90–120 genuinely hard minutes for graduated athletes training at least six hours/week, capped at two or three hard days. AE-2.2 defines its high-zone distribution as all time above Z2, while the implemented floor counts only time at or above 92% FTP. Those are different accounting rulers; changing the counter to credit tempo/sweet spot would materially change pass/fail behavior. AE-3.1 caps a VO2 session at 18 minutes above 106% FTP. Given the actual schedules and library workouts above, adding repetitions or a day until the 90-minute gate passes would silently override athlete availability, workout dose, or both. No ratified rule authorizes that trade.

## Smallest safe implementation sequence

1. Ratify a single hard-minute accounting definition for AE-2.1 (zone boundary, whether open-effort tests and lower-zone race simulations count, and whether the 90-minute number is an absolute floor for a six-hour week with two hard days). Record it beside AE-2.1/AE-2.2 and use the same ruler in planning, post-render validation, and coach review. Keep the present finding visible until then.
2. Implement AE-1.10 onboarding as an explicit, persisted athlete state with a recorded graduation signal. The generator should produce its frequency/duration phases and the validator should exempt only athletes demonstrably still inside that state. Add an order-level review finding when the required graduation evidence is missing.
3. For graduated athletes, calculate the attainable hard-minute budget from the athlete's available intensity days, daily caps, long-ride spacing, and AE-3.1 VO2 ceiling before selecting workouts. Choose only existing library items whose measured structures meet the target; reject candidates that overshoot VO2 or exceed caps. If the feasible set is empty, surface a specific schedule/dose conflict to the coach rather than fabricate or stretch workouts.
4. Regression fixtures: the sealed `cohort-05`/`cohort-06` schedules and a novice with zero structured years. Assert exact day placement, planned and rendered hard minutes under the ratified ruler, VO2 ceiling, weekly hour fit, taper exemptions, and no athlete-calendar writes. Rerun the fixed ten-order replay and compare every finding by ID; a lower warning count alone is not acceptance.

No generator or gate code was changed in this investigation. The 47 findings remain blockers for review readiness, alongside the rehearsal's independent voice, RPE/structure, VO2-dose, stale-race, and unresolved-pain findings. This card does not certify Motoren for ten orders/day.
