# Empirical Cycling (Kolie Moore) Mining — 2026-08-23

Miner: web-research agent over empiricalcycling.com + Moore's TrainingPeaks/CTS articles. Podcast audio inaccessible; claims marked UNVERIFIED must not drive algorithm design until re-verified. Rule IDs EC-1..17.

STATUS: PENDING — awaiting Matti rulings (see ALGORITHM_EVIDENCE.md §11).

---

# Empirical Cycling / Kolie Moore — Quantified Methodology Mining Report

**Scope note on access limits:** empiricalcycling.com podcast-episode pages are landing pages (title + 1-2 sentence description) with no embedded transcripts — audio content itself is inaccessible to web fetch. All quantified rules below come from Kolie Moore's own **written articles** (mainly TrainingPeaks/CTS-hosted, which do have full text) plus secondary paraphrase from podcast interview show-notes and TrainerRoad community threads. Where a claim rests only on secondary paraphrase (not a primary Moore quote), it is marked accordingly. Two fetches failed outright (TLS cert error on x3training.com, 403 on capovelo.com) — those claims are flagged UNVERIFIED.

---

## Extracted Rules

### 1. FTP is NOT a fixed 95% of 20-min power
**RULE:** Do not derive FTP as a fixed ratio of 20-minute best power; the ratio varies by athlete phenotype (anaerobic contribution to short efforts).
**NUMBERS:** FTP/20-min-power ratio ranges 86% (track sprinter) to 96% (time trialist). Case studies: elite female road cyclist 268W FTP / 279W 20-min = 96.1%; elite male track racer 238W FTP / 262W 20-min = 90.8% (anaerobic contribution 11W and 24W respectively).
**SOURCE:** [The FTP Test: Physiology and New Protocols](https://www.trainingpeaks.com/blog/the-physiology-of-ftp-and-new-testing-protocols/) (Kolie Moore, TrainingPeaks) — this is the article referenced by [Watts Doc #26](https://www.empiricalcycling.com/podcast-episodes/watts-doc-26-ftp-testing-revisited) and [Ten Minute Tips #63](https://www.empiricalcycling.com/podcast-episodes/ten-minute-tips-63-the-best-and-worst-ways-to-test-ftp).
**CONFIDENCE:** Coach opinion grounded in critical-power physiology; not itself peer-reviewed but consistent with CP/W′ literature.
**HOOK:** testing, athlete classification.
**CONTRADICTION:** None named in ratified list, but flags a hidden assumption risk if the pipeline ever estimates FTP as 20min×0.95.

### 2. TTE at FTP is individual and ranges 30–70 minutes, not a fixed 60
**RULE:** Treat "60-minute power" as a population average, not a per-athlete constant; test/track individual TTE.
**NUMBERS:** TTE at MLSS/FTP ranges 30–70 min; blood lactate at MLSS 2–8 mmol/L; example athletes: 40-min TTE (female road cyclist), 75-min TTE (male track racer).
**SOURCE:** Same TrainingPeaks article as above.
**CONFIDENCE:** Coach opinion built on established MLSS/TTE physiology.
**HOOK:** testing, athlete classification, block_chain (TIZ dosing).
**CONTRADICTION:** Undermines any hardcoded "FTP = 60-min power" definition baked into a pipeline; doesn't directly conflict with the ratified T@VO2max 8–14min band (different metric domain).

### 3. Progressive baseline→3-stage FTP test protocol (TTE-anchored)
**RULE:** Use a 4-test progression, each stage held at ~95–100%+ of target FTP for longer or until TTE, rather than a single 20-min or ramp test.
**NUMBERS:**
- Baseline (35–45min or TTE): 10min@92-95% → 15min@100% → 10-15min ramp to exhaustion.
- Progression 1 (40–50min or TTE+10min): 10min@95% → 20-30min@100% → 10min ramp.
- Progression 2 (35–60min or TTE+10min): 10min@97% → 20-45min@100% → 5min all-out.
- Progression 3 (40–75min or TTE+5min): 5min@97% → up to 70min@100%.
- Corroborating structured workout (matches Baseline stage): 5min@60% → 10min@96%/90rpm → 15min@102%/95rpm → 15min@103-115%/95rpm (74-min total).
**SOURCE:** [TrainingPeaks FTP physiology article](https://www.trainingpeaks.com/blog/the-physiology-of-ftp-and-new-testing-protocols/); corroborating workout file: [TrainerDay — Kolie Moore Baseline TTE FTP Test](https://app.trainerday.com/workouts/kolie-moore-baseline-tte-ftp-test-3) (third-party mirror, not empiricalcycling.com itself, so treat as secondary confirmation).
**CONFIDENCE:** Coach-proprietary protocol; widely discussed/replicated in the community (e.g., [TrainerRoad forum thread](https://www.trainerroad.com/forum/t/kolie-moore-test-some-help-please-on-how-to-structure/56433)), not peer-reviewed.
**HOOK:** testing, calculate_plan_dates (test cadence), series progression.
**CONTRADICTION:** New territory — no ratified rule currently governs test-protocol design.

### 4. 20-min ramp/TT tests distrusted as FTP determinants
**RULE:** Avoid short ramp/20-min tests as the sole FTP source; prefer longer submaximal/TTE-anchored protocols.
**NUMBERS:** UNVERIFIED — a "~50-60% of the population gets an accurate FTP from a 20-min test" figure surfaced during research but could not be verified verbatim against the source text; treat as unconfirmed.
**SOURCE:** [TrainingPeaks FTP article](https://www.trainingpeaks.com/blog/the-physiology-of-ftp-and-new-testing-protocols/); community corroboration (paraphrase only, no verbatim Moore quote recovered) in [TrainerRoad "Kolie Moore on the ramp test" thread](https://www.trainerroad.com/forum/t/kolie-moore-on-the-ramp-test/68796) (235+ replies — forum users report "Kolie had the ramp test as a bad workout/test," "really dislikes the ramp test for FTP," but no verbatim Moore quote or physiological rationale was recoverable through this thread).
**CONFIDENCE:** Coach opinion; the specific accuracy percentage is UNVERIFIED.
**HOOK:** testing.
**CONTRADICTION:** None ratified.

### 5. Endurance/LT1 zone is individualized and can sit below 60% FTP
**RULE:** Do not treat 60–70% FTP as a universal endurance floor; test/observe individual LT1, which can be materially lower.
**NUMBERS:** Typical endurance range cited as 60–75% FTP, but Moore explicitly notes some athletes' LT1 sits at 50–55% FTP. RPE 4-5/10 typical endurance, RPE 3/10 permissible, RPE 2-4 for fatigued athletes. Session-end freshness check: should be able to do a 5-min max effort and lose only ~10W.
**SOURCE:** [A Practical Guide To Base Training With Kolie Moore (CTS/TrainingPeaks)](https://trainright.com/practical-guide-base-training-kolie-moore/).
**CONFIDENCE:** Coach opinion / practitioner heuristic, individualized-RPE based.
**HOOK:** workout_selector, block_chain, athlete classification.
**CONTRADICTION — FLAGGED:** Direct tension with the ratified "endurance IF .60–.70 scaled down with duration" floor. Moore's stated 50-55% FTP LT1 for some athletes would fall below that floor, meaning a hard .60 floor could push a genuinely low-LT1 athlete into tempo-intensity territory during nominal "endurance" rides.

### 6. Weekly volume ceiling / diminishing returns
**RULE:** Even at the pro level, hours beyond ~25-30/week show fast diminishing returns; typical pro range 15-20 to 25-30 hrs/week.
**SOURCE:** Same [trainright.com article](https://trainright.com/practical-guide-base-training-kolie-moore/).
**CONFIDENCE:** Coach opinion/observational.
**HOOK:** calculate_plan_dates, block_chain, athlete classification (volume tier).
**CONTRADICTION:** None ratified (complementary to, not conflicting with, the hard-min/week floor).

### 7. Sweet-spot/tempo dosing capped at 2-3 sessions/week; progress duration before power
**RULE:** Cap sweet-spot/tempo-type sessions at 2-3/week due to fatigue cost; when progressing, extend time-in-zone before raising power.
**SOURCE:** [Training Talk with Kolie Moore | EP#271 — That Triathlon Show](https://scientifictriathlon.com/tts271/).
**CONFIDENCE:** Coach opinion (interview paraphrase from show notes, not a verbatim transcript quote).
**HOOK:** block_chain, workout_selector, series progression.
**CONTRADICTION — FLAGGED:** Compare to ratified "2-3 intensity days + 90-120 hard-min/week floor." Ambiguous whether Moore's 2-3/week cap is meant as a total-hard-day ceiling or specific to the sweet-spot modality alone — if the pipeline stacks sweet-spot AND separate threshold/VO2 sessions in the same week without reconciling against this cap, it risks double-counting "hard days." Needs adjudication on definitional scope.

### 8. Sweet-spot-vs-polarized framed as a false dichotomy ("kayfabe")
**RULE:** Don't pre-decide an athlete's intensity distribution using a fixed model (polarized 80/20, sweet-spot-base, etc.) ahead of time.
**SOURCE:** [Ten Minute Tips #17: Sweetspot vs Polarized Is Kayfabe](https://www.empiricalcycling.com/podcast-episodes/ten-minute-tips-17-sweetspot-vs-polarized-is-kayfabe) — landing-page description only (episode audio inaccessible): *"we discuss where the sweetspot vs polarized dichotomy may have come from as a stepping off point to consider if you should use such rules to decide your training intensity distribution ahead of time."*
**CONFIDENCE:** Coach opinion; the word "kayfabe" (pro-wrestling term for a staged storyline presented as real) signals Moore's stance strongly, but the full argument is UNVERIFIED beyond this one-sentence description — could not access transcript.
**HOOK:** block_chain, workout_selector (intensity-distribution model choice).
**CONTRADICTION — FLAGGED (philosophical):** This is Moore's central methodological objection and cuts against ANY fixed-ratio/fixed-cap rule in the ratified list (the .60-.70 IF band, 50 TSS/hr cap, 2-3 intensity-day floor, etc.) *to the extent they are applied as universal population rules rather than individually tested targets*. This is the throughline behind Rules 5, 7, 9, 14, 15 below — flag as a single adjudication point: "fixed % rules vs individualized/TTE-tested thresholds."

### 9. VO2max intervals: 2-6 min TT-style work, governed by cadence/breathing not real-time power
**RULE:** Prescribe VO2max work as longer (2-6 min), TT-paced intervals; govern intensity in real time by cadence and breathing rate, not power/HR (those are used only in post-analysis); avoid intermediate-duration formats like 30/30s.
**NUMBERS:** 2-6 min work intervals; example rest manipulation "45s on/15s off" (vs. 30s off) to bias toward the aerobic system; periodic training done fully "blinded to power."
**SOURCE:** [Training Talk with Kolie Moore | EP#271](https://scientifictriathlon.com/tts271/) (interview show-notes synthesis, not verbatim transcript).
**CONFIDENCE:** Coach opinion / practitioner heuristic layered on stroke-volume/diastolic-filling physiology.
**HOOK:** workout_selector, block_compliance.
**CONTRADICTION — FLAGGED:** Compatible on its face with the ratified "T@VO2max 8-14 min pass band" (e.g., 3×4min or 4×3min reaches that band), but Moore's compliance mechanism (cadence/breathing-governed, graded post-hoc) is philosophically at odds with any block_compliance gate that grades a session purely on power-in-zone — a session Moore would call "on target" by RPE/breathing could fail a power-based compliance check, and vice versa.

### 10. Hard-start VO2max intervals — UNVERIFIED at primary source
**RULE (reported, not independently confirmed):** Starting a VO2max interval above target/sustainable pace increases time at ≥90% HRpeak / time-near-VO2max despite power decay across the interval.
**SOURCE:** Attempted fetch of [x3training.com — Endurance Innovation 103](https://x3training.com/endurance-innovation-103-kolie-moore-on-vo2max/) failed (TLS certificate error, twice, both https and http); [CapoVelo.com](https://capovelo.com/youre-training-too-hard-for-criteriums-heres-why/) returned HTTP 403. Only WebSearch snippet summaries were recoverable, not primary text.
**CONFIDENCE:** UNVERIFIED against a primary or directly-quoted source in this pass. Flag explicitly — do not treat as citable until a primary transcript/text is obtained.
**HOOK:** workout_selector.

### 11. Base-period anaerobic capacity work — "mixed results"; address neuromuscular weakness off-bike instead
**RULE (reported, not independently confirmed):** On-bike anaerobic-capacity intervals during the base period produce mixed results; if neuromuscular power is a limiter, prefer off-bike strength work to build force capacity during base.
**SOURCE:** CapoVelo.com article (403 Forbidden — could not verify verbatim).
**CONFIDENCE:** UNVERIFIED (blocked fetch; secondary WebSearch synthesis only).
**HOOK:** block_chain, athlete classification.

### 12. Sprint maintenance dosing (~22s sprints)
**RULE (reported, not independently confirmed):** Short (~22-second) sprints used to maintain high-end/neuromuscular capacity and sprint form.
**SOURCE:** WebSearch synthesis only; no URL fetch confirmed this number verbatim against primary text.
**CONFIDENCE:** UNVERIFIED.
**HOOK:** workout_selector.

### 13. Concurrent-training (strength + endurance) sequencing rules
**RULE:** Sequence same-day strength and hard endurance with endurance first and ≥3hr gap; otherwise separate strength from hard endurance by 24-48hr; flag endurance rides >2-3hr or interval work >~80% FTP on a strength day as risking the hypertrophy signal.
**NUMBERS:** 24-48hr separation (general); ≥3hr same-day gap (endurance first); >2-3hr ride or >80%FTP intervals flagged; mTOR "significantly activated for 18 hours" post-strength (longer in untrained); heavy leg session (4×5 squat, 4×5 deadlift, 4×12 split squat) depleted muscle glycogen by 38% on average, requiring days (not hours) to replenish; cites Hickson (1980) 10-week concurrent-training study where strength gains plateaued/reversed after week 7.
**SOURCE:** [Risks of Concurrent Training (Kolie Moore, TrainingPeaks)](https://trainingpeaks.com/blog/risks-of-concurrent-training/).
**CONFIDENCE:** Mixed — physiology (mTOR timing, glycogen depletion, Hickson 1980) is cited from real literature (moderate-high confidence); the specific dosing thresholds (3hr gap, 24-48hr, 80%FTP/2-3hr flags) read as Moore's practical synthesis (coach-opinion confidence).
**HOOK:** block_chain (day-level sequencing), workout_selector, block_compliance.
**CONTRADICTION:** No ratified rule currently governs same-day strength/endurance sequencing — clean addition, recommend for adjudication/inclusion rather than conflict resolution.

### 14. Training-density block clustering (strongest documented CTL/ramp-rate disagreement)
**RULE:** Cluster hard days into consecutive blocks (e.g., 4 days of threshold work) followed by a longer easy/recovery block, rather than smoothing load evenly across the week — this drives larger short-term threshold gains than an even distribution.
**NUMBERS:** Example week structure: 4 consecutive days threshold work → 3 days easy/recovery/rest → 3 days sweet-spot work. Cited real-athlete result: 29W FTP gain (252W→281W) over 2 weeks using this density approach. Supporting literature cited: training-frequency studies at 2/3/4/5×/week for 60/120/180/240/300 total weekly minutes; adding two extra 1-hr sessions/week eliminated training "non-responders"; a block-periodization HIT protocol used 5 HIT sessions in week 1 followed by 1 HIT session/week for weeks 2-4.
**SOURCE:** [Break Through Your Performance Plateau By Increasing Training Density (Kolie Moore, TrainingPeaks)](https://www.trainingpeaks.com/blog/break-through-your-performance-plateau-by-increasing-training-density/).
**CONFIDENCE:** Coach-authored, cites peer-reviewed training-frequency/block-periodization literature; moderate-high confidence on underlying research, coach-opinion on the specific day-counts and the 29W anecdote (single-athlete case study, not a study result).
**HOOK:** block_chain, calculate_plan_dates, series progression.
**CONTRADICTION — STRONGEST FLAG IN THIS REPORT:** This is a direct, well-sourced conflict with the ratified rule "ramp ≤8 CTL/wk within-block and ≤10-12 CTL/month net." Moore's density-block method deliberately produces a spiky, concentrated load (4 consecutive hard days) specifically to drive the short-term gain he documents — a strict ≤8 CTL/wk-within-block ceiling could mechanically forbid the exact structure behind his cited 29W/2-week result. Recommend this article be the primary reference when the ramp-rate rule comes up for head-coach review.

### 15. RPE as a first-class signal, with periodic power-blinded training
**RULE:** Weight RPE equally with power; periodically train "blinded to power" so athletes stay calibrated to internal effort — some athletes lose the ability to read RPE independent of a power meter.
**SOURCE:** [Training Talk with Kolie Moore | EP#271](https://scientifictriathlon.com/tts271/); corroborating landing page (description only, no verbatim quote recoverable): [RPE Matters Just As Much as Power — Campfire Endurance](https://www.campfireendurance.com/the-infirmary/why-rpe-matters-just-as-much-as-power-kolie-moore-from-empirical-cycling-on-training-smarter).
**CONFIDENCE:** Coach opinion / practitioner heuristic.
**HOOK:** workout_selector, athlete classification, block_compliance.
**CONTRADICTION:** Same philosophical tension as Rule 9 — power/TSS-centric compliance and gating logic (W'bal nadir gate, TSS/hr cap) is fundamentally metric-based, while Moore treats the power meter as an occasionally-unreliable signal needing periodic RPE recalibration.

### 16. "Plans written in sand, not stone"
**RULE:** Training plans should flex around accumulated fatigue/life-stress signals a power meter can't capture, rather than being followed rigidly.
**SOURCE:** [Campfire Endurance summary](https://www.campfireendurance.com/the-infirmary/why-rpe-matters-just-as-much-as-power-kolie-moore-from-empirical-cycling-on-training-smarter) — paraphrase, not a verbatim Moore quote (author's summary phrasing).
**CONFIDENCE:** Coach opinion; UNVERIFIED verbatim.
**HOOK:** block_compliance (adaptive override logic), block_chain.
**CONTRADICTION:** Consonant with (not contradictory to) this org's existing "dampened adaptation reacts to trends not events" doctrine; in tension only with any *rigid, non-overridable* ramp/taper rule.

### 17. Strength training: framed mainly for bone density + interference management, not direct performance transfer
**RULE:** No strong on-bike performance-transfer claims found for strength training in this source set; primary stated benefit is bone density (via varied-impact work: jogging, plyometrics, skipping rope), with dosing governed by the concurrent-training interference rules in Rule 13.
**SOURCE:** [Training Talk with Kolie Moore | EP#271](https://scientifictriathlon.com/tts271/); [Risks of Concurrent Training](https://trainingpeaks.com/blog/risks-of-concurrent-training/).
**CONFIDENCE:** Coach opinion.
**HOOK:** block_chain, athlete classification.
**CONTRADICTION:** None ratified.

---

## Top 10 (ranked by algorithmic usefulness × source strength)

| # | Rule | Hook | Confidence |
|---|------|------|------------|
| 1 | 4-stage progressive TTE-anchored FTP test protocol (Rule 3) | testing | Coach protocol, well-documented |
| 2 | TTE at FTP is individual, 30-70min not fixed 60 (Rule 2) | testing, athlete classification | Coach opinion + physiology |
| 3 | Training-density block clustering vs smooth ramp (Rule 14) | block_chain, ramp-rate policy | Coach article + cited literature |
| 4 | FTP ≠ fixed 95% of 20-min power (Rule 1) | testing | Coach opinion + physiology |
| 5 | Concurrent-training sequencing rules, 3hr/24-48hr (Rule 13) | block_chain, workout_selector | Coach article + cited studies |
| 6 | Endurance/LT1 individualized, can be <60% FTP (Rule 5) | workout_selector, block_chain | Coach opinion |
| 7 | Sweet-spot capped 2-3x/week, progress duration not power (Rule 7) | block_chain, series progression | Coach opinion (interview) |
| 8 | VO2max: 2-6min TT intervals, cadence/breathing-governed (Rule 9) | workout_selector, block_compliance | Coach opinion (interview) |
| 9 | Sweet-spot-vs-polarized = false dichotomy ("kayfabe") (Rule 8) | block_chain philosophy | Title-level, content UNVERIFIED |
| 10 | RPE first-class + periodic power-blinded training (Rule 15) | workout_selector, block_compliance | Coach opinion |

---

## Contradictions Table (vs. ratified standards)

| Ratified Standard | Moore's Position | Severity | Rule # |
|---|---|---|---|
| Endurance IF .60–.70 scaled down with duration | LT1 individually tested; some athletes sit at 50–55% FTP, below the .60 floor | Medium — direct numeric overlap gap | 5 |
| 2–3 intensity days + 90–120 hard-min/week floor | Sweet-spot alone capped 2-3x/week; unclear if this is additive to or inclusive of threshold/VO2 days | Medium — definitional ambiguity, needs scope clarification | 7 |
| Ramp ≤8 CTL/wk within-block, ≤10-12 CTL/month net | Deliberately clusters 4 consecutive hard days into short dense blocks to drive short-term FTP gains (29W/2wk cited) | **High — most direct, best-sourced conflict found** | 14 |
| T@VO2max 8-14 min pass band | Broadly compatible (2-6min reps can sum to 8-14min), but compliance is governed by cadence/breathing, not power-in-zone | Low-Medium — mechanism mismatch, not a numeric conflict | 9 |
| W'bal nadir 0-6 kJ gate for threshold/anaerobic work | **Could not verify.** Despite targeted searching, no primary Moore quote or reliably-sourced paraphrase of a W'bal critique was found in this research pass. | **Not confirmed — see Gaps below** | — |
| Fixed % / TSS-based rules generally (implicit across the ratified set) | Explicitly rejects pre-deciding intensity distribution via fixed models ("sweetspot vs polarized is kayfabe") | Philosophical, cuts across multiple rules | 8, 15 |
| 45-min floor, VO2 every 14 days, recovery week 50-65% TSS, taper hard-content caps | **No corresponding Moore statement found** in this research pass | Gap, not contradiction | — |

---

## Gaps / Explicitly Not Found

- **W'bal skepticism** — the brief specifically expected this; I could not locate it. No primary empiricalcycling.com text, TrainingPeaks article, or reliable secondary paraphrase surfaced a specific Moore critique of W'bal for interval prescription in this pass. This likely lives in podcast audio only (episode pages have no transcripts). Recommend a follow-up pass pulling YouTube auto-captions for Watts Doc episodes, or a transcript service, specifically targeting episodes tagged "critical power" / "W'bal."
- **TSS/CTL direct critique** — no verbatim Moore quote found; Rule 14 (training density) is the strongest *indirect* evidence of his practical stance but is not itself a stated TSS/CTL critique.
- **Ramp-test critique rationale** — only community paraphrase (235-reply TrainerRoad thread) recovered; no verbatim quote or physiological reasoning captured, and the source episode/number is unconfirmed.
- **Recovery-week and taper percentage guidance** — nothing found attributable to Moore specifically.
- **Hard-start VO2max interval mechanism and base-period anaerobic-work claims (Rules 10-12)** — blocked by TLS/403 errors on x3training.com and CapoVelo.com; only WebSearch-snippet-level synthesis available, explicitly marked UNVERIFIED.

**Recommend for the head coach:** treat Rule 14 (training density vs. ramp-rate cap) as the one confirmed, well-sourced, high-priority adjudication item from this pass; everything else marked UNVERIFIED should not be relied on for algorithm design until re-verified against primary text or transcript.
