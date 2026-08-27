# PMC / CTL / ATL / TSB — Knowledge-Base Mining (2026-08-26)

Coach brief: "underresearched on CTL, ATL, TSB planning and manipulation — tapering,
planning TSS to produce positive TSB with still high fitness on race day."
Scope: QMD graph (writing-graph, gravel-god, training-plans), repo evidence docs
(docs/evidence/2026-08-23-*.md), docs/ALGORITHM_EVIDENCE.md, athlete-facing copy.
NO code changes. Companion web-research track runs in parallel — §e is its shopping list.

---

## (a) Matti's own documented positions [E — he's the coach]

**1. Freshness beats fitness at the margin — enter A-races "very, very positive" TSB.**
> "you will go to the well. To go to the well, you need to be fresh. In technical
> terms, you want a very, very positive TSB. I'm willing to be[t] a lot of gravel
> racers put too much emphasis on getting their fitness high and less emphasis on
> entering the race in a low fatigue state at the expense of fitness. … It's WAY
> better to enter the race a little undertrained but fresh than it is a little
> fitter but buried."
— `writing-graph/inbox/gravel-god/i-screwed-up-sbt-grvl-so-you-dont-have-to.md`
(context: he raced SBT at "100+ CTL and LOTS and LOTS of intensity in my legs").

**2. Taper shape: last long hard ride 2 weeks out; drop volume, hold frequency + intensity.**
> "Ideally, you want your last long hard ride to happen two weeks out from RGG.
> And then leading into the event drop the volume and keep the frequency and
> intensity steady. … you also need to be fresher than you're probably comfortable
> with because going hard for 144 miles is just so hard on your body."
— `writing-graph/inbox/gravel-god/i-didnt-screw-up-red-granite-grinder-and-neither-do-you.md`

**3. Rest without load = detraining, not freshness** (same axis as corpus R101):
> "If you haven't gotten off the couch since October, you're definitely well-rested
> at this point, but … you're bleeding fitness and digging a gigantic fitness hole"
— `writing-graph/inbox/gravel-god/how-to-not-fk-up-your-holiday-training.md`

**4. Ratified in-repo rulings (Matti, already canonical):** AE-1.12 taper shape
(rest 10–14 d out → reload 2–3 hard efforts inside hard-content caps; manage ATL
as the active lever, CTL is a lagging result); AE-1.13 season close-out; AE-1.14
CTL trajectory gate (plan FAILs if modeled race-day CTL >10% below current);
AE-1.9c recovery-week denominator = demonstrated load. — `docs/ALGORITHM_EVIDENCE.md`

Note: Matti's written race-report positions (1, 2) and AE-1.12 agree in shape.
Nowhere in his own writing is a **numeric** race-day TSB target.

---

## (b) WKO / corpus claims table

Ratified = has a canonical AE rule in `docs/ALGORITHM_EVIDENCE.md`.
Sources: WKO = `docs/evidence/2026-08-23-wko-store-mining.md`, CZ = `…couzens-corpus-mining.md`,
WG = `…wider-graph-mining.md`, EC = `…empirical-cycling-mining.md`, FT = `…triathlon-fasttalk-mining.md`.

| Claim | Numbers | Source | Ratified? |
|---|---|---|---|
| Ramp cap, dual timescale | ≤8 CTL/wk in-block (2–4 wk max) AND ≤10 CTL/month net (gate at 10; 10–12 = WARN) | WKO R1; CZ B1 | **AE-1.4** ✓ |
| Ramp decelerates as intensity rises (TSS∝IF²) | multiplier shrinks with phase IF; TSS>300 lingers ~2 d | WKO R2; WG lever 10 | **AE-1.4** ✓ |
| Halve ramp above CTL 100; wall at 135–165 | GT ceiling 180–200 "not convertible to peak form" | WKO R3, R7 | **AE-1.4** ✓ |
| Run-dominant discount | −15–20% on all ramp ceilings | WKO R4 | **AE-1.4** ✓ |
| CTL bands by training age, hour-budget cap first | 1–2y <40/41–75/≥76 · 2–5y <60/61–95/≥96 · 5y+ <80/81–115/≥116; −10 over 50; 6–8 h/wk ⇒ CTL~75 ceiling | WKO R5, R6, R79 | **AE-1.5** ✓ |
| Peak CTL lands 8–12 wks BEFORE race; flat-line after (stabilization) | workout benefit ~50%@30d +25%@60d +12%@90d; fatigue steady-state ~21 d vs fitness ~126 d; constant-load sim ≈ +6% peak fitness on −4% work | CZ H2; WKO R10; WG stabilization | **AE-1.2** ✓ |
| CTL is not fitness; never target peak CTL on race day; never report CTL as fitness | WKO dropped Banister timing terms — CTL "knows nothing about you" | CZ H3 | folded into AE-1.2/AE-5.x framing, no standalone rule |
| Aerobic benchmark, not CTL, gates progression | Couzens case: aerobic numbers peaked ~CTL 150 while CTL climbed to ~190; CTL 200–210 = "horrible performances", racing at ~170 better | CZ D1/D2 | ✓ (AE-5.x benchmark rule; "CTL never the gate") |
| No monotonic CTL climbs; NFOR = ATL>CTL sustained | ATL>CTL ≥3 wks w/o recovery = fail | WKO R8 | **AE-2.4** ✓ |
| Expect 3–5 wk performance dip after aggressive ramp | don't re-prescribe on the dip | WKO R9 | **AE-4.5** ✓ |
| Taper = rest 10–14 d out, then reload 2–3 hard efforts | TSB rises during rest, "can leave the athlete too flat"; reload prevents flatness. **Anecdote tier — weakest in store** | WKO R57 | **AE-1.12** ✓ |
| Manage ATL as active lever in peak/race; CTL lags | ATL/TSB ~inverse, ~1-day offset. **Peak-performance TSB clusters near 0** in worked case (3-yr CTL ~110, top-10s at CTL ~105); 2nd case peaks ~15–40 pts below avg CTL — gap individual, not fixed | WKO R58 | **AE-1.12** ✓ shape only — **the TSB≈0 number was NOT ratified** |
| B/C races: no taper week/phase; 2-day overlay retained as logistics | binary, athlete buy-in | WKO R59 | **AE-1.9** ✓ |
| Keep one long easy "booster" ride weekly through peak; first thing cut | weekly, min every-other-week | WKO R60 | ✗ never ratified |
| Maintenance load < build load; minimum dose individual | "what it takes to get there ≠ what it takes to stay there" (Golich) | WKO R61 | ✗ never ratified |
| High positive TSB = detraining/reversibility risk, not freshness | qualitative bands: very negative = overload, very high = detraining, middle = train | WKO R101 | ✗ (only as reinforcement of 50–65% recovery band + AE-1.9c) |
| Plateaued-but-completing = NFOR, prescribe time off | — | WKO R102 | ✗ |
| ≥1 load channel trending up outside planned rest | both flat ⇒ peaks lost | WKO R104 | ✗ |
| Peak-readiness signal from top-performance cluster tightness | — | WKO R99 | ✗ |
| IM taper volume: 2 wks out = 60–75% of peak; race week ≤50%; intensity via short activations | one activation Rx: 5min@90% FTP + 3×5min @ IM pace | FT §F | ✗ never ratified |
| No "long aggressive taper" if specific-phase execution good; last major workout ≥10 d out | flat/lethargic race day named as the failure | FT §F (John Davis) | ✗ (consonant with AE-1.12) |
| Density blocks (4 consecutive hard days) deliberately break ramp caps | 29W/2wk cited | EC Rule 14 | ✗ — **pending ruling Q13** (flagged HIGH) |
| TSS/CTL invalid across disciplines/terrain; volume cross-check layer | — | AE §open Q18 | ✗ — **pending Q18** |
| CX exception: race-season CTL low-60s, taper 66→53, race-day **TSB +29** | FasCat CX Nationals case | `docs/evidence/2026-08-26-loading-benchmarks.md` §CX | ✗ (documented as event-class exception, no AE rule) |

**Also ratified nearby:** AE-1.1 (never fill the runway), AE-1.3 (residual stacking —
speed work IN race week, VO2 touch in final ~2 wks), AE-1.11 (camp lands 3–5 wks
pre-race), AE-1.14 (CTL trajectory gate — the only place the pipeline actually
*computes* CTL today).

---

## (c) What athletes are currently told

**Public gravel guide** — `/Users/mattirowe/Documents/GravelGod/gravel-race-automation/guide/gravel-guide-content.json`:
- L1370: "When CTL is climbing steadily and **TSB turns positive 10-14 days before
  race day, you are ready.**"
- L1384 (Base): "CTL rising steadily **(+3-5/wk)**. TSB slightly negative (-5 to -15)."
- L1388 (Build): "deliberately dig a fatigue hole (**TSB goes to -25**), recover just
  enough, then dig another hole."
- L1392 (Peak/Taper wks 11–12): "Volume drops 30-50%. Intensity stays high…
  Week 11: TSB rises to **+5 to +10**. Week 12: **TSB targets +15 to +25 for race day.**"
- L2854 (race week): "You're fit. **Your CTL is peaked.** Your TSB is climbing toward
  positive freshness."
- L2927–2933 (distance-scaled tapers): 7-day = −40% vol + 10-min race-pace effort 3 d
  out; 10-day = −50% vol + **two opener sessions of 3×5 min at threshold** (5 d and
  2 d out); 12–14-day = −40% wk1 / −60% wk2 + 20-min race-sim 5 d out + two full rest
  days before race day.
- L3122: "The heavy-leg feeling is not lost fitness—it's stored fitness waiting to
  be expressed… Trust the taper." (good, consistent)
- Infographic (`gravel-race-automation/wordpress/guide_infographics.py:867`):
  "PEAK / TAPER — Weeks 10-12: Reduce volume 40%, maintain intensity, rest up."

**Pipeline athlete guides** — `docs/guides/guillermo-romero/index.html`:
"Heavy legs mid-week are the taper working, not fitness leaving"; "The urge to
'check the legs' with one more hard effort spends race-day matches." Consistent
with AE-1.12. No TSB/CTL numbers surface in athlete guides — good.

**Generated taper workouts** — `athletes/scripts/generate_athlete_package.py:2296–2491`:
taper = 1 opener (4×15–30 s @ ~110%) + easy spins @ IF .58–.60; week budget ×0.70
(`CLAUDE.md:221`); openers/mini-taper overlay at B-races. Conservative, cap-compliant.

---

## (d) Contradictions found

1. **Race-day TSB target: three-way disagreement, nothing ratified.**
   Guide tells athletes **+15 to +25** (L1392). Corpus best worked case: peak
   performances **cluster near TSB 0** (R58), and R101 warns high positive TSB =
   detraining. Matti's own writing: "**very, very positive TSB**" (SBT, no number).
   The CX case in loading-benchmarks shows +29 working — for a 45-min event.
   No AE rule states any TSB band. The single most athlete-visible number in the
   whole PMC domain is unratified and mid-way contradicted by the corpus.

2. **Guide's 10-day taper prescribes 3×5 min AT THRESHOLD openers (L2930) —
   violates ratified AE-1.12 hard-content caps** (no ≥92%-FTP rep >120 s in
   taper/race weeks; ≤15 min ≥92% per session). 300-s threshold reps are more than
   double the ratified rep ceiling. The pipeline's own generated openers
   (4×15–30 s) comply; the public guide does not.

3. **Guide race-week copy: "Your CTL is peaked" (L2854) contradicts AE-1.2 /
   CZ H2-H3**: peak CTL should land **8–12 weeks before** race day and load
   flat-lines after; "never target peak CTL on race day." The guide's periodization
   chapter also draws CTL climbing through week 10–11 into the taper.

4. **Guide base-phase ramp "+3-5 CTL/wk" (L1384) = ~13–21 CTL/month — exceeds the
   ratified ≤10 CTL/month net cap (AE-1.4).** Within-week it's fine (≤8); the
   monthly net is the binding constraint the guide ignores.

5. **Guide taper = "maintain intensity" throughout vs AE-1.12 = rest-first, THEN
   reload.** Shape mismatch, mild: the ratified shape front-loads rest 10–14 d out
   with 2–3 reload efforts late; the guide (and infographic) describe uniformly
   reduced volume with intensity held high all the way through. Same macro effect,
   different microstructure — but AE-1.12 exists precisely because "all-intensity
   taper is a build week in disguise" (`CLAUDE.md` pitfall; WG §4).

6. Already-adjudicated but worth restating: sol found the B/C "no taper" wording vs
   the enforced 2-day B-race overlay (resolved in AE-1.9 as logistics-not-taper),
   and the 10 vs 10–12 CTL/month discrepancy (resolved: gate at 10). —
   `docs/evidence/2026-08-23-sol-review-findings.md` items 4, 6.

---

## (e) Gaps — covered by NEITHER corpus nor Matti's writing (web-research candidates)

1. **Numeric race-day TSB band, scaled by event duration/class** (5-h gravel vs
   10-h ultra vs 45-min CX). Corpus has one near-0 case + one CX +29 case; guide
   invented +15..+25; no evidence base.
2. **Taper dose-response literature** — Bosquet/Mujika-style meta findings
   (~40–60% volume reduction, 8–14 d, maintain intensity+frequency, progressive vs
   step taper, expected % performance gain). Entirely absent from the corpus; the
   guide's 40/50/60% numbers are uncited.
3. **Acceptable CTL bleed during taper** — how many CTL points (or %) may be lost
   between peak CTL and race day before it costs performance. AE-1.14 gates at
   >10% below *current* CTL but that number is a Matti heuristic from one athlete
   case, and it gates the whole plan, not the taper segment.
4. **TSB trajectory shaping** — how fast TSB should rise (ATL decay pacing), and
   whether an overload-then-taper (planned overreach 2–3 wks out) beats a plain
   taper; Banister/Thomas-Busso optimal-taper modeling. Nothing in corpus beyond
   R57's anecdote tier.
5. **Time-constant individualization** — CTL 42/ATL 7 defaults vs individual τ
   (corpus notes τ₁ varies ~30–60 d, one HRV note uses ATL 8–9 d for masters);
   no rule for when/how to deviate. Related: pending Q18 (TSS/CTL validity) and
   Q13 (density blocks vs ramp caps) are still open rulings.
6. **Positive-TSB detraining threshold** — R101 is purely qualitative; no number
   for when "fresh" tips into "reversibility."

**Questions for Matti (max 3):**
1. Ratify a race-day TSB band (by event class)? Options on the table: corpus ≈0,
   guide +15..+25, your own "very, very positive," CX case +29.
2. The public guide's 10-day taper (3×5 min @ threshold openers) breaks ratified
   AE-1.12 caps — fix the guide copy, or carve an exception for sub-threshold
   "activation" reps ≤5 min at ≤90%?
3. Guide says "your CTL is peaked" on race week and base ramps +3-5 CTL/wk — both
   contradict ratified AE rules (AE-1.2, AE-1.4). Rewrite the guide's PMC chapter
   to the ratified numbers?
