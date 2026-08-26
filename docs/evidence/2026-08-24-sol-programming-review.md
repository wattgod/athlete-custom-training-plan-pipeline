codex
I would not ship this plan as-is. Coach sign-off alone is insufficient; it needs material reprogramming.

I computed hard time as structured seconds at ≥92% FTP, VO₂ time at ≥106% FTP, and IF as `sqrt(TSS ÷ hours ÷ 100)`. Unstructured race cards have unknown hard time—they are not physiologically “zero,” but they cannot satisfy a computed compliance gate.

### Load ledger

| Week | JSON hours / TSS | Hours incl. 30-min strength | House hour budget | Structured ≥92% |
|---|---:|---:|---:|---:|
| W1 Aug 31–Sep 6 | 8.93 / 429.0 | 9.93 | 11.0 | 38.5 min |
| W2 Sep 7–13 | 10.35 / 473.4 | 10.85 | 11.0 | 46.5 min |
| W3 Sep 14–20 | 10.05 / 548.9 | 11.05 | 11.0 | 26.7 min |
| W4 Sep 21–27 | 7.50 / 292.6 | 7.50 | 6.2 recovery | 1.0 min |
| W5 Sep 28–Oct 4 | 6.13 / 277.5 | 6.63 | 7.0 taper | 10.0 min |
| W6 Oct 5–11 | 8.35 / 378.7 | 8.35 | 6.0 race | 12.5 min + unstructured race |

Strength TSS is excluded because the six rx StructuredStrength sessions are outside the live JSON.

## Findings

1. **BLOCKER — The FTP test cannot validly re-anchor the plan.**

   On Sep 1, the “FTP Test” prescribes 20 minutes at exactly 100% of the existing 261 W FTP, then instructs `average power × 0.95 = FTP`. Perfect execution at 261 W therefore returns **248 W**, a built-in 5% reduction. To reproduce 261 W, Steve would need to average roughly **275 W**, yet that is not the structured target.

   If the filed FTP is actually inflated 5–10%, true FTP could be approximately **235–248 W**. The locked 261 W test step would then demand roughly **105–111% of true FTP for 20 minutes**, making failure—not measurement—the likely outcome.

   Worse, [plan_summary.yaml](/Users/mattirowe/Documents/GravelGod/athlete-custom-training-plan-pipeline/.worktrees/tp-cadence-emission/athletes/steve-wagner/plan_summary.yaml) records `week_1_field_test: null` and `reanchor.required: false`. The program therefore depends on a test that is structurally invalid and does not carry an explicit re-anchor contract. I would refuse to prescribe the remaining %FTP work until this is fixed.

2. **BLOCKER — Testing and consecutive B-races create an excessive intensity re-entry for a masters athlete.**

   W1 has hard work on Sep 1, 3, 4 and 5:

   - Sep 1 FTP Test: **25.0 min ≥92%**
   - Sep 3 Anaerobic Test: **11.5 min**
   - Sep 4 Openers: **2.0 min**
   - Sep 5 Dirt Diggler: unstructured hard race

   W2 repeats four hard dates: Sep 8, 10, 11 and 12. That is **eight hard dates in 12 days**, counting the two races, immediately after months without progressive intensity.

   This breaches AE-2.1’s mature-athlete three-hard-day cap and the VO₂-block limit of five hard days per rolling two weeks. It is particularly indefensible under AE-8.1’s instruction to preserve masters VO₂ by providing *more spacing*.

3. **BLOCKER — Both B-race overlays violate AE-1.9.**

   AE-1.9 retains easy at −2 days and openers at −1. The actual −2 sessions are hard:

   - Dirt Diggler Sep 5: Sep 3 is the **Anaerobic Test**, not easy.
   - Fool’s Gold Sep 12: Sep 10 is **Accumulation**, containing **31.5 min ≥92%**, not easy.
   - Sep 4 and Sep 11 correctly contain openers.

   Keeping both weeks in base rather than creating taper phases is correct. The execution of the retained two-day logistics overlay is not. [AE-1.9](/Users/mattirowe/Documents/GravelGod/athlete-custom-training-plan-pipeline/.worktrees/tp-cadence-emission/docs/ALGORITHM_EVIDENCE.md:91)

4. **BLOCKER — The plan cannot substantiate AE-2.1’s 90–120 hard-minute floor.**

   The structured totals are **38.5, 46.5, 26.7, 1.0, 10.0 and 12.5 minutes** by week. W3 is the clearest failure: no unstructured race exists to hide behind, and it delivers only **26.7 minutes**, less than one-third of the 90-minute minimum.

   W1, W2 and W6 might accumulate additional hard time during races, but their race cards contain no structure, so compliance is unknowable rather than passed.

   There is also a canon contradiction that needs owner resolution: AE-1.12 permits only 2–3 taper reloads capped at 15 hard minutes each, making AE-2.1’s 90-minute weekly minimum impossible during taper. The plan still cannot claim unqualified compliance. [AE-2.1](/Users/mattirowe/Documents/GravelGod/athlete-custom-training-plan-pipeline/.worktrees/tp-cadence-emission/docs/ALGORITHM_EVIDENCE.md:123)

5. **MAJOR — VO₂ dosing is incoherent and twice fails AE-3.1.**

   Measured ≥106% FTP time:

   - Sep 8, VO₂max 30/30: **13 min — PASS**
   - Sep 15, Descending VO₂ Pyramid: **21 min — FAIL**, above 18-minute hard limit
   - Sep 17, Blended 30/30 + SFR: **3 min — FAIL**, below five-minute minimum
   - Sep 29, 30/30 VO₂: **10 min — PASS**

   The worst sequence is Sep 15’s overdosed 21 minutes, a full strength session the same day, then another VO₂-labelled workout only **48 hours later**. That second session is underdosed, followed 48 hours later by a 4.17-hour race simulation. This is neither a clean VO₂ progression nor masters spacing. [AE-3.1](/Users/mattirowe/Documents/GravelGod/athlete-custom-training-plan-pipeline/.worktrees/tp-cadence-emission/docs/ALGORITHM_EVIDENCE.md:196)

6. **MAJOR — The baseline battery violates AE-5.3’s one-max-effort-per-day rule.**

   The Sep 3 Anaerobic Test combines:

   - Three 10-second all-out sprints
   - One 60-second all-out effort
   - Twenty 30/30 repeats at 120% FTP

   AE-5.3 calls for a 4–6-day battery with one maximum duration per day. This session confounds peak sprint power, one-minute capacity and repeatability after prior maximal work. It will not produce clean classification data. [Testing canon](/Users/mattirowe/Documents/GravelGod/athlete-custom-training-plan-pipeline/.worktrees/tp-cadence-emission/docs/ALGORITHM_EVIDENCE.md:316)

7. **MAJOR — Six weeks could be a useful conversion block, but this plan spends the runway badly.**

   The calendar is two test/race weeks, one build week, one recovery week, taper, race. Steve gets only one nominal build week, Sep 14–20, before unloading.

   There is one controlled threshold-focused session on Sep 10, one oversized VO₂ session on Sep 15, one underdosed blend on Sep 17, and one race simulation on Sep 19. That is not a coherent progression out of “base-phase-no-exit”; it is a sudden intensity pile followed by withdrawal.

   Six weeks is not inherently too short for an experienced rider with substantial base. It is too short for this allocation, especially with consecutive B-races consuming the first two Saturdays.

8. **MAJOR — The taper caps pass, but the functional unload begins too early.**

   The formal AE-1.12 taper is good:

   - Taper starts Sep 28, **12 days out**
   - Sep 29: 10 hard minutes, maximum rep 30 seconds
   - Oct 6: 9 hard minutes, maximum rep 60 seconds
   - Oct 9: 3.5 hard minutes, maximum rep 120 seconds

   All three sessions stay under 15 hard minutes and contain no >120-second hard rep.

   The larger shape is poor: TSS falls from **548.9 in W3 to 292.6 in W4**, a 46.7% cut beginning Sep 21—**19 days before the race**—then remains at 277.5 in W5. Steve effectively unloads for almost three weeks after only one true build week. For an athlete already stuck in steady-state training, that risks preserving freshness without creating new race fitness. [AE-1.12](/Users/mattirowe/Documents/GravelGod/athlete-custom-training-plan-pipeline/.worktrees/tp-cadence-emission/docs/ALGORITHM_EVIDENCE.md:112)

9. **MAJOR — Strength is systematically stacked onto the hardest cycling dates.**

   The six additional strength sessions land on Sep 1, 3, 8, 15, 17 and 29—the same dates as the FTP test, Anaerobic Test, 13-minute VO₂, 21-minute VO₂, blended VO₂/SFR, and 10-minute VO₂ respectively.

   AE-8.4 allows morning-before strength only as a primer. Foundation A/B, Power Development and Cycling-Specific are full sessions, not primers. Even with several hours between sessions, this compromises test validity and makes recovery from every meaningful VO₂ workout harder. The Sep 1 and Sep 3 pair are unacceptable testing-day placements. [AE-8.4](/Users/mattirowe/Documents/GravelGod/athlete-custom-training-plan-pipeline/.worktrees/tp-cadence-emission/docs/ALGORITHM_EVIDENCE.md:436)

10. **MAJOR — Race-duration and durability modelling are not securely bound to the actual event.**

   The live race card plans **6.0 hours**, while the supplied event expectation is approximately **4.5–5 hours**. The coaching brief also admits SEG McCormick is unmatched and was built from neutral gravel assumptions.

   The only controlled ride approaching race duration is Sep 19’s **4.17-hour, 233-TSS** dress rehearsal, 21 days before the A-race. Later Saturdays shrink to **1.58 hours on Sep 26** and **2.0 hours on Oct 3**. The two 3-hour B-races add useful stochastic intensity, but they do not replace a second deliberate durability exposure or post-kJ power-decay check.

   Fueling practice is present—59 g/hr on Sep 19 and Sep 26—but **59 g/hr is just below AE-6.1’s 60–80 g/hr bracket for a 4–8-hour event**, and the 349 g race total is derived from the erroneous ~5.9-hour model.

11. **MINOR — Endurance compliance is mostly good, with one measurable miss.**

   The identifiable endurance/heat sessions mostly produce IF **0.632–0.658** and **40–43 TSS/hr**, inside AE-2.8.

   Sep 13’s 2.5-hour Aerobic Base calculates to **IF 0.685 and 47.0 TSS/hr**. Its load rate passes, but IF exceeds the 2–4-hour ceiling of **0.68**. That is a narrow numeric violation, made less defensible because it comes the morning after Fool’s Gold. [AE-2.8](/Users/mattirowe/Documents/GravelGod/athlete-custom-training-plan-pipeline/.worktrees/tp-cadence-emission/docs/ALGORITHM_EVIDENCE.md:174)

12. **MINOR — The two Mobility cards are not the hole.**

   Sep 10 and Sep 22 each provide a legitimate 30-minute mobility routine, and several Monday/race-week rest cards prescribe additional 8–10-minute mobility. Honest text mobility cards are appropriate; they do not need cycling power structure.

   The problem is the opposite: their 30-minute durations contribute to W4 reaching **7.50 hours against a 6.2-hour recovery budget**, while the real strength problem is six full sessions colliding with testing and VO₂ days.

## Verdict

**NO-GO. Do not ship after sign-off without revision.**

At minimum, the coach must replace the FTP test and explicitly re-anchor FTP, separate the baseline maxima, restore easy −2 days before both B-races, move or downgrade strength on testing/VO₂ days, redose the Sep 15/17 VO₂ pair, verify the A-race duration/course, and rebuild the recovery/taper transition. The [live TP payload](/Users/mattirowe/Documents/GravelGod/athlete-custom-training-plan-pipeline/.worktrees/tp-cadence-emission/athletes/steve-wagner/plan_672143_current.json) is not safe to approve as currently programmed.
tokens used
145,537
I would not ship this plan as-is. Coach sign-off alone is insufficient; it needs material reprogramming.

I computed hard time as structured seconds at ≥92% FTP, VO₂ time at ≥106% FTP, and IF as `sqrt(TSS ÷ hours ÷ 100)`. Unstructured race cards have unknown hard time—they are not physiologically “zero,” but they cannot satisfy a computed compliance gate.

### Load ledger

| Week | JSON hours / TSS | Hours incl. 30-min strength | House hour budget | Structured ≥92% |
|---|---:|---:|---:|---:|
| W1 Aug 31–Sep 6 | 8.93 / 429.0 | 9.93 | 11.0 | 38.5 min |
| W2 Sep 7–13 | 10.35 / 473.4 | 10.85 | 11.0 | 46.5 min |
| W3 Sep 14–20 | 10.05 / 548.9 | 11.05 | 11.0 | 26.7 min |
| W4 Sep 21–27 | 7.50 / 292.6 | 7.50 | 6.2 recovery | 1.0 min |
| W5 Sep 28–Oct 4 | 6.13 / 277.5 | 6.63 | 7.0 taper | 10.0 min |
| W6 Oct 5–11 | 8.35 / 378.7 | 8.35 | 6.0 race | 12.5 min + unstructured race |

Strength TSS is excluded because the six rx StructuredStrength sessions are outside the live JSON.

## Findings

1. **BLOCKER — The FTP test cannot validly re-anchor the plan.**

   On Sep 1, the “FTP Test” prescribes 20 minutes at exactly 100% of the existing 261 W FTP, then instructs `average power × 0.95 = FTP`. Perfect execution at 261 W therefore returns **248 W**, a built-in 5% reduction. To reproduce 261 W, Steve would need to average roughly **275 W**, yet that is not the structured target.

   If the filed FTP is actually inflated 5–10%, true FTP could be approximately **235–248 W**. The locked 261 W test step would then demand roughly **105–111% of true FTP for 20 minutes**, making failure—not measurement—the likely outcome.

   Worse, [plan_summary.yaml](/Users/mattirowe/Documents/GravelGod/athlete-custom-training-plan-pipeline/.worktrees/tp-cadence-emission/athletes/steve-wagner/plan_summary.yaml) records `week_1_field_test: null` and `reanchor.required: false`. The program therefore depends on a test that is structurally invalid and does not carry an explicit re-anchor contract. I would refuse to prescribe the remaining %FTP work until this is fixed.

2. **BLOCKER — Testing and consecutive B-races create an excessive intensity re-entry for a masters athlete.**

   W1 has hard work on Sep 1, 3, 4 and 5:

   - Sep 1 FTP Test: **25.0 min ≥92%**
   - Sep 3 Anaerobic Test: **11.5 min**
   - Sep 4 Openers: **2.0 min**
   - Sep 5 Dirt Diggler: unstructured hard race

   W2 repeats four hard dates: Sep 8, 10, 11 and 12. That is **eight hard dates in 12 days**, counting the two races, immediately after months without progressive intensity.

   This breaches AE-2.1’s mature-athlete three-hard-day cap and the VO₂-block limit of five hard days per rolling two weeks. It is particularly indefensible under AE-8.1’s instruction to preserve masters VO₂ by providing *more spacing*.

3. **BLOCKER — Both B-race overlays violate AE-1.9.**

   AE-1.9 retains easy at −2 days and openers at −1. The actual −2 sessions are hard:

   - Dirt Diggler Sep 5: Sep 3 is the **Anaerobic Test**, not easy.
   - Fool’s Gold Sep 12: Sep 10 is **Accumulation**, containing **31.5 min ≥92%**, not easy.
   - Sep 4 and Sep 11 correctly contain openers.

   Keeping both weeks in base rather than creating taper phases is correct. The execution of the retained two-day logistics overlay is not. [AE-1.9](/Users/mattirowe/Documents/GravelGod/athlete-custom-training-plan-pipeline/.worktrees/tp-cadence-emission/docs/ALGORITHM_EVIDENCE.md:91)

4. **BLOCKER — The plan cannot substantiate AE-2.1’s 90–120 hard-minute floor.**

   The structured totals are **38.5, 46.5, 26.7, 1.0, 10.0 and 12.5 minutes** by week. W3 is the clearest failure: no unstructured race exists to hide behind, and it delivers only **26.7 minutes**, less than one-third of the 90-minute minimum.

   W1, W2 and W6 might accumulate additional hard time during races, but their race cards contain no structure, so compliance is unknowable rather than passed.

   There is also a canon contradiction that needs owner resolution: AE-1.12 permits only 2–3 taper reloads capped at 15 hard minutes each, making AE-2.1’s 90-minute weekly minimum impossible during taper. The plan still cannot claim unqualified compliance. [AE-2.1](/Users/mattirowe/Documents/GravelGod/athlete-custom-training-plan-pipeline/.worktrees/tp-cadence-emission/docs/ALGORITHM_EVIDENCE.md:123)

5. **MAJOR — VO₂ dosing is incoherent and twice fails AE-3.1.**

   Measured ≥106% FTP time:

   - Sep 8, VO₂max 30/30: **13 min — PASS**
   - Sep 15, Descending VO₂ Pyramid: **21 min — FAIL**, above 18-minute hard limit
   - Sep 17, Blended 30/30 + SFR: **3 min — FAIL**, below five-minute minimum
   - Sep 29, 30/30 VO₂: **10 min — PASS**

   The worst sequence is Sep 15’s overdosed 21 minutes, a full strength session the same day, then another VO₂-labelled workout only **48 hours later**. That second session is underdosed, followed 48 hours later by a 4.17-hour race simulation. This is neither a clean VO₂ progression nor masters spacing. [AE-3.1](/Users/mattirowe/Documents/GravelGod/athlete-custom-training-plan-pipeline/.worktrees/tp-cadence-emission/docs/ALGORITHM_EVIDENCE.md:196)

6. **MAJOR — The baseline battery violates AE-5.3’s one-max-effort-per-day rule.**

   The Sep 3 Anaerobic Test combines:

   - Three 10-second all-out sprints
   - One 60-second all-out effort
   - Twenty 30/30 repeats at 120% FTP

   AE-5.3 calls for a 4–6-day battery with one maximum duration per day. This session confounds peak sprint power, one-minute capacity and repeatability after prior maximal work. It will not produce clean classification data. [Testing canon](/Users/mattirowe/Documents/GravelGod/athlete-custom-training-plan-pipeline/.worktrees/tp-cadence-emission/docs/ALGORITHM_EVIDENCE.md:316)

7. **MAJOR — Six weeks could be a useful conversion block, but this plan spends the runway badly.**

   The calendar is two test/race weeks, one build week, one recovery week, taper, race. Steve gets only one nominal build week, Sep 14–20, before unloading.

   There is one controlled threshold-focused session on Sep 10, one oversized VO₂ session on Sep 15, one underdosed blend on Sep 17, and one race simulation on Sep 19. That is not a coherent progression out of “base-phase-no-exit”; it is a sudden intensity pile followed by withdrawal.

   Six weeks is not inherently too short for an experienced rider with substantial base. It is too short for this allocation, especially with consecutive B-races consuming the first two Saturdays.

8. **MAJOR — The taper caps pass, but the functional unload begins too early.**

   The formal AE-1.12 taper is good:

   - Taper starts Sep 28, **12 days out**
   - Sep 29: 10 hard minutes, maximum rep 30 seconds
   - Oct 6: 9 hard minutes, maximum rep 60 seconds
   - Oct 9: 3.5 hard minutes, maximum rep 120 seconds

   All three sessions stay under 15 hard minutes and contain no >120-second hard rep.

   The larger shape is poor: TSS falls from **548.9 in W3 to 292.6 in W4**, a 46.7% cut beginning Sep 21—**19 days before the race**—then remains at 277.5 in W5. Steve effectively unloads for almost three weeks after only one true build week. For an athlete already stuck in steady-state training, that risks preserving freshness without creating new race fitness. [AE-1.12](/Users/mattirowe/Documents/GravelGod/athlete-custom-training-plan-pipeline/.worktrees/tp-cadence-emission/docs/ALGORITHM_EVIDENCE.md:112)

9. **MAJOR — Strength is systematically stacked onto the hardest cycling dates.**

   The six additional strength sessions land on Sep 1, 3, 8, 15, 17 and 29—the same dates as the FTP test, Anaerobic Test, 13-minute VO₂, 21-minute VO₂, blended VO₂/SFR, and 10-minute VO₂ respectively.

   AE-8.4 allows morning-before strength only as a primer. Foundation A/B, Power Development and Cycling-Specific are full sessions, not primers. Even with several hours between sessions, this compromises test validity and makes recovery from every meaningful VO₂ workout harder. The Sep 1 and Sep 3 pair are unacceptable testing-day placements. [AE-8.4](/Users/mattirowe/Documents/GravelGod/athlete-custom-training-plan-pipeline/.worktrees/tp-cadence-emission/docs/ALGORITHM_EVIDENCE.md:436)

10. **MAJOR — Race-duration and durability modelling are not securely bound to the actual event.**

   The live race card plans **6.0 hours**, while the supplied event expectation is approximately **4.5–5 hours**. The coaching brief also admits SEG McCormick is unmatched and was built from neutral gravel assumptions.

   The only controlled ride approaching race duration is Sep 19’s **4.17-hour, 233-TSS** dress rehearsal, 21 days before the A-race. Later Saturdays shrink to **1.58 hours on Sep 26** and **2.0 hours on Oct 3**. The two 3-hour B-races add useful stochastic intensity, but they do not replace a second deliberate durability exposure or post-kJ power-decay check.

   Fueling practice is present—59 g/hr on Sep 19 and Sep 26—but **59 g/hr is just below AE-6.1’s 60–80 g/hr bracket for a 4–8-hour event**, and the 349 g race total is derived from the erroneous ~5.9-hour model.

11. **MINOR — Endurance compliance is mostly good, with one measurable miss.**

   The identifiable endurance/heat sessions mostly produce IF **0.632–0.658** and **40–43 TSS/hr**, inside AE-2.8.

   Sep 13’s 2.5-hour Aerobic Base calculates to **IF 0.685 and 47.0 TSS/hr**. Its load rate passes, but IF exceeds the 2–4-hour ceiling of **0.68**. That is a narrow numeric violation, made less defensible because it comes the morning after Fool’s Gold. [AE-2.8](/Users/mattirowe/Documents/GravelGod/athlete-custom-training-plan-pipeline/.worktrees/tp-cadence-emission/docs/ALGORITHM_EVIDENCE.md:174)

12. **MINOR — The two Mobility cards are not the hole.**

   Sep 10 and Sep 22 each provide a legitimate 30-minute mobility routine, and several Monday/race-week rest cards prescribe additional 8–10-minute mobility. Honest text mobility cards are appropriate; they do not need cycling power structure.

   The problem is the opposite: their 30-minute durations contribute to W4 reaching **7.50 hours against a 6.2-hour recovery budget**, while the real strength problem is six full sessions colliding with testing and VO₂ days.

## Verdict

**NO-GO. Do not ship after sign-off without revision.**

At minimum, the coach must replace the FTP test and explicitly re-anchor FTP, separate the baseline maxima, restore easy −2 days before both B-races, move or downgrade strength on testing/VO₂ days, redose the Sep 15/17 VO₂ pair, verify the A-race duration/course, and rebuild the recovery/taper transition. The [live TP payload](/Users/mattirowe/Documents/GravelGod/athlete-custom-training-plan-pipeline/.worktrees/tp-cadence-emission/athletes/steve-wagner/plan_672143_current.json) is not safe to approve as currently programmed.
