# The Fundamentals of Interval Manipulation
### A named, cited taxonomy of the levers that change an interval's stimulus — the basis of `progression_engine.py`

Difficulty is not one knob. A structured workout is a set of **orthogonal levers**, each
mapping to a distinct physiological target. Progress (or regress) by turning *one* lever
and holding the rest — that's how you know what drove the adaptation, and it's how the
engine's `AXES` registry is built.

The canonical framework is **Buchheit & Laursen, "High-Intensity Interval Training:
Solutions to the Programming Puzzle" (Sports Medicine 2013, Parts I & II)** — the academic
backbone of their book *Science and Application of HIIT*. They define a HIIT session as the
**manipulation of at least 9 variables**, each shifting the session among **6 acute response
types**. Two accounting backbones make the taxonomy programmable:
- **Aerobic sessions** are scored on **T@VO₂max** — time spent ≥90% VO₂max — target **~10 min/session**.
- **Threshold/anaerobic sessions** are accounted by **W′bal** — the anaerobic battery that
  drains above Critical Power (CP) and refills, slowly, below it.

Both are now computed in the engine (`t_at_vo2max_proxy`, `wbal_nadir`).

---

## Master table — every lever as a tunable axis

| # | Lever (coaching term) | Engine axis | Physiological effect | How to PROGRESS | Caution |
|---|------------------------|-------------|----------------------|-----------------|---------|
| 1 | **Work intensity** (%FTP / %vVO₂max / vs CP) | `intensity` | Selects the system. 90–105% vVO₂max → the VO₂max stimulus (max O₂ transport + type-II + near-max cardiac output); just-sub-CP → MLSS/threshold; >CP → linear W′ drain; supramaximal → glycolytic + neuromuscular. | Hold duration, raise watts (SS 88→thr 100→VO₂ 110%). | Supramaximal **halves** T@VO₂max & spikes lactate. Prescribe L5–L7 in **watts only** — HR/RPE lag or fail. |
| 2 | **Work duration** (rep length) | `work_duration` | VO₂ takes **1:20–2:20** to reach max, so 1-min reps under-deliver (peak VO₂ ~82% vs ~92% at 2 min). Longer reps add glycolytic load / build TTE. | Hold intensity, extend reps (4→6→8 min). | Too long collapses intensity — Seiler 4×16 fell to 88% HRpeak, **half** the gain of 4×8. |
| 3 | **Relief duration** (time between reps) | `recovery_duration` | Short relief keeps VO₂ elevated (more T@VO₂max) & leaves W′ low → progressive depletion; long relief refills W′/PCr, sustains power. | Shorten relief (3→2→1.5 min). | **~2 min is the floor of benefit** for ~4-min bouts (Seiler & Hetlelid: gain plateaus past 2 min; athletes self-select ~118 s). Too short → power craters. |
| 4 | **Relief intensity** (active/passive float) | `recovery_intensity` | Master dial for W′ reconstitution. Recover deep below CP → small τ → fast refill; float near CP → large τ → slow refill (the over-under engine). | Raise the float (passive→50→67% vVO₂max), or raise the "under" toward CP. | BL optimum ≈ **70% vVO₂max** for short HIIT; for relief <2–3 min keep it **passive** (active washes out PCr). |
| 5 | **Reps & sets/series** (+ between-series rec) | `reps`, `sets` | Total accumulated T@VO₂max / W′ depletion / kJ. **Splitting into series *reduces* total T@VO₂max** but buys quality/repeatability. | Add reps (12→13×30/15) → add series (3→5) → add sessions/wk. | Series lower the T@VO₂max ratio; cap hard days at 2–3/wk. |
| 6 | **Work:rest ratio / density** | `density` | Ratio >1 maximizes the T@VO₂max-per-exercise-minute ratio; lower density preserves peak power. | Tighten ratio (2:1→3:1→4:1); 30/30→30/20→30/15. | Dense + supramaximal = glycolytic blowup; the float must stay genuinely easy. |
| 7 | **Cadence** (torque 40–60 vs spin 100–120 rpm) | `cadence` | At fixed power: low rpm → ↑force/stroke, ↑type-II recruitment, ↓CV strain; high rpm → ↑CV/metabolic load, spares legs. | Lower the floor (65→55→50→40 rpm); **best evidence = carry low cadence INTO the VO₂/HIIT reps.** | NOT a gym substitute (Kristoffersen 2014: 40-rpm tempo changed nothing). Patellofemoral load **+29%** at 70 vs 90 rpm → gate behind knee-history flag. |
| 8 | **Prefatigue / sequencing** (durability) | `prefatigue_kj` | Same effort after accumulated kJ trains fatigue resistance; CP holds but **W′ and sprint power decay first** (independent of fresh fitness). | Move the interval deeper: fresh → ~1000–1500 → ~2000 → ~2500–3000+ kJ (normalize kJ·kg⁻¹). | **De-rate VO₂/anaerobic targets 10–20% when fatigued**; fueling mandatory; not for novices. |
| 9 | **Interval shape** | `shape` | Over-unders → lactate shuttling (W′ saw-tooth toward zero); fast-start → accelerated VO₂ kinetics → more T@VO₂max; micro-burst 30/15 → bank T@VO₂max at low RPE; ramped → repeatability/pacing. | Over-unders: raise under-floor & over-ceiling, lengthen, add reps; fast-start: bigger opening surge. | Overs >~110% become VO₂ work & blow up the set; don't run fast-start in ERG; the "under" is never rest. |
| 10 | **Total dose** (TSS / kJ) | *(computed `dose()`)* | The *amount*, orthogonal to the *kind*. **TSS = IF²·hrs·100** (100 TSS = 1 hr @ FTP); scales with intensity². kJ ≈ kcal & is the durability substrate. | Raise session TSS / weekly kJ within a controlled CTL ramp. | TSS scales as IF² — doubling intensity >doubles stress. >300 lingers ~2 days, >450 multi-day. Under-weights neuromuscular/durability. |
| 11 | *Exercise modality* (BL's 9th) | *(gradient cue)* | Uphill/big-gear raises neuromuscular load without raising speed; mostly fixed for a bike-only engine. | Add gradient to load force without speed. | Mostly a constant here. |

> The engine computes **TSS** (`Σ (dur/3600)·IF²·100`, FTP-independent), **kJ**
> (`Σ power·FTP·dur/1000`), a **W′bal nadir** (Skiba differential), and a **T@VO₂max
> proxy** from the same segments it renders — so you can hold dose constant while changing
> *which* lever delivers it, and size prefatigue by *energy burned*.

---

## Summary by lever group

### The canonical frame: 9 variables, 6 responses, T@VO₂max
A HIIT session is the manipulation of *"at least nine variables"*: work intensity, work
duration, relief intensity, relief duration, modality, number of reps, number of series,
between-series recovery duration & intensity. *"The intensity and duration of work and
relief intervals are the key influencing factors."* Manipulating them shifts the session
among six acute responses (metabolic/aerobic → +neuromuscular → +glycolytic → … →
purely anaerobic-glycolytic+neuromuscular, the SIT-only zone), which map to four formats:
**long intervals (2–4 min), short intervals (<45 s), repeated-sprint (≤10 s), sprint-interval
(20–30 s all-out)**. The master aerobic outcome is **T@VO₂max ≥ ~10 min/session**.
*(Buchheit & Laursen, Sports Med 2013, Part I & II.)*

### Levers 1–2: intensity & duration (the two key factors)
Anchor aerobic HIIT to **power at VO₂max (vVO₂max/MAP)**; long intervals run 90–105% of it.
Below sits threshold/MLSS, above sits the **Anaerobic Speed Reserve**. Duration sets how much
of the system you load — VO₂ kinetics take 1:20–2:20 to arrive, so reps must be long enough to
reach max. Seiler's classic 4×4 / 4×8 / 4×16 gave 94 / 90 / 88% HRpeak and 13.2 / 9.6 / 4.9 mM
lactate — and **4×8 won** (~2× the gain) by maximizing accumulated time in a high-but-sustainable
zone. Progress duration before watts. *(Coggan levels; Billat vVO₂max/Tlim; Seiler 2013; Empirical Cycling TTE.)*

### Levers 3–4: relief duration & intensity (the recovery dials)
Velocity in 4-min bouts rises 1→2 min recovery but **not** 2→4 min — **~2 min is the optimum**;
for short HIIT keep relief <2–3 min **passive**. Relief intensity is the master dial for W′:
Skiba's model drains W′ linearly above CP and refills it exponentially below, with time constant
**τ = 546·e^(−0.01·D_CP) + 316** (D_CP = how far below CP you float). Recover deep → fast refill;
float near CP → slow refill (over-unders). Design sets so W′bal hits a **small positive nadir on
the final rep** (last rep = limiter). *(Seiler & Hetlelid 2005; Skiba et al. 2012.)*

### Levers 5–6: reps, series & density (accumulation)
To bank ~10 min T@VO₂max a 30/30 @110% format (T@VO₂max ratio ≈30%) implies ~30 min work as
**3 sets of 10–12 min** — but splitting into series *reduces* total T@VO₂max while buying quality.
Rønnestad's canonical block is **3 series × (13 × 30s @ ~MAP / 15s @ 50%), 3 min between** — progressed
by adding reps (12→13), series (3→5), then sessions/week — ~3× the VO₂max gain of effort-matched
4×5-min. Greatest T@VO₂max ratio comes from long intervals or short intervals with **work:rest > 1**.
*(Buchheit & Laursen Part I; Rønnestad 2015/2020.)*

### Lever 7: cadence (force ↔ metabolic)
At fixed power, low cadence trades flow for force (type-II recruitment, tendon tension, less CV strain).
Honest verdict for a generator: low cadence at *moderate* intensity builds little (Kristoffersen 2014
null); low cadence applied to *high-intensity* intervals improves VO₂max/Pmax (Hebisz 2024) and sprint
power (Paton 2009). Model two families — aerobic muscle-tension (50–60 rpm tempo/SS) and low-cadence
VO₂/HIIT — and treat the latter as the evidence-backed progression. Knee load **+29%** at 70 vs 90 rpm.
*(Buchheit & Laursen Part II; Kristoffersen 2014; Hebisz 2024; Paton 2009; Bini & Hume 2013.)*

### Lever 8: prefatigue / sequencing (durability)
Durability = the deterioration of your power profile over a long ride, *independent of fresh fitness*.
Two riders with equal fresh FTP can differ hugely after 3 h. Pros' 5/12-min power declines around
1000–3000 kJ (U23 collapse ~1500, elite ~2500 — van Erp); a 2025 review found **10–20% decline after
high-intensity prior work**, and it's the **intensity of the bridge work, not kJ total**, that drives it
(W′ and sprint fall while CP holds — Spragg). Ladder: fresh → ~1000–1500 → ~2000 → ~2500–3000+ kJ.
**De-rate VO₂/anaerobic 10–20% when fatigued; keep threshold near-normal.** *(Maunder 2021; Spragg 2024.)*

### Lever 9: interval shape
**Over-unders** alternate ~90–95% unders / ~105–110% overs (1–2 min each): overs drain W′ above CP, the
unders (just below CP, large τ) only partly refill it, so W′bal saw-tooths toward zero — training lactate
shuttling at threshold. **Fast-start** reps open ~30s @130% then settle 100–110%, exploiting accelerated
VO₂ on-kinetics (prior hard bout cut the VO₂ τ ~45%) to bank more T@VO₂max. **Micro-bursts (30/15, 40/20)**
accumulate the most time >90% VO₂max at the *lowest* RPE. Overs >110% become VO₂ work; don't run fast-start
in ERG; the "under" is never rest. *(Billat 30/30 & 15/15; Rønnestad 30/15; TrainerRoad/FasCat over-unders.)*

### Lever 10: total work / TSS / kJ (dose, orthogonal to all)
The other ten set the *kind*; this sets the *amount*. **TSS = (sec·NP·IF)/(FTP·3600)·100 = IF²·hrs·100**
(100 TSS = 1 hr @ FTP). Because it scales with IF², doubling intensity more than doubles stress — a generator
must check session TSS against the athlete's CTL ramp. kJ (≈ kcal) is the companion raw-energy axis and the
durability substrate. *(Coggan TSS/levels; Normalized Power.)*

---

## Engine-design synthesis (how the levers compose)
**A workout = base interval (intensity × duration × shape) × cadence overlay × prefatigue/kJ context ×
recovery configuration × accumulation (reps/sets/density), governed by a total-dose budget.** The levers are
orthogonal — progress one, hold the rest. Two backbones make it programmable:
- **Aerobic** → score on **T@VO₂max** (~10 min target), maximized by 30/30, 30/15, fast-start with work:rest >1 and ~70% vVO₂max floats.
- **Threshold/anaerobic** → account by **W′bal**: deplete above CP, reconstitute below; design so W′bal hits a small
  positive nadir on the final rep. Seed W′ ≈ 15–25 kJ; CP ≈ FTP/0.96 if only FTP known.

**Safety gates to encode:** knee-history flag → cadence floor; novice flag → cap prefatigue kJ; ≤2–3 hard
days/week; de-rate VO₂/anaerobic 10–20% under fatigue; prescribe L5–L7 in **watts only**.

> Implementation note: the W′bal τ constants (546 / 316 / 0.01) were fit to a 7-subject 2012 cohort —
> the engine exposes τ as tunable, not hard-coded.

---

## Primary sources
- **Buchheit & Laursen, Sports Med 2013 — Part I (Cardiopulmonary):** https://paulogentil.com/pdf/HIIT%201%202013.pdf
- **Part II (Anaerobic / Neuromuscular / Practical):** https://martin-buchheit.net/wp-content/uploads/2018/01/buchheit-laursen-hit-solutions-to-the-programming-puzzle-part-ii.pdf
- **Book:** *Science and Application of HIIT*, Laursen & Buchheit (Human Kinetics)

### Secondary (cited inline)
Seiler 2013 interval-duration: https://pubmed.ncbi.nlm.nih.gov/21812820/ · Seiler & Hetlelid 2005 recovery:
https://pubmed.ncbi.nlm.nih.gov/16177614/ · Skiba W′bal 2012: https://pubmed.ncbi.nlm.nih.gov/22382171/
(τ: http://markliversedge.blogspot.com/2014/07/wbal-its-implementation-and-optimisation.html) · Billat
vVO₂max: https://pubmed.ncbi.nlm.nih.gov/8857705/ · Billat 30/30: https://pubmed.ncbi.nlm.nih.gov/10638376/ ·
Rønnestad 2015: https://pubmed.ncbi.nlm.nih.gov/24382021/ · Rønnestad 2020:
https://onlinelibrary.wiley.com/doi/full/10.1111/sms.13627 · Coggan levels/TSS:
https://www.trainingpeaks.com/blog/power-training-levels/ · NP/IF/TSS:
https://www.trainingpeaks.com/learn/articles/normalized-power-intensity-factor-training-stress/ ·
Kristoffersen 2014 cadence: https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3907705/ · Hebisz 2024:
https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11559993/ · Paton 2009: https://pubmed.ncbi.nlm.nih.gov/19675486/ ·
Bini & Hume 2013 knee load: https://pubmed.ncbi.nlm.nih.gov/23898683/ · Maunder 2021 durability:
https://link.springer.com/article/10.1007/s40279-021-01459-0 · Spragg 2024:
https://pmc.ncbi.nlm.nih.gov/articles/PMC11235642/ · Empirical Cycling TTE:
https://www.empiricalcycling.com/podcast-episodes/watts-doc-39-why-you-probably-cant-hold-your-ftp-for-an-hour
