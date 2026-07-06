# Torque / Low-Cadence Pack — 8 Distinctive Sessions

Researched from YouTube + coaching/science sources (Jun 2026). **Deliberately NOT**
the generic "5×5 @90% FTP @50-60rpm" — each session is a genuinely different force
stimulus. All TrainingPeaks/Zwift-safe `.zwo`. Set FTP in-app before importing.

> **Cadence is a prompt, not an ERG target.** Zwift/TP control *power*, not rpm.
> Shift into the gear that lets you hold the prescribed cadence. The per-segment
> cadence + cueing live in each file's description (and `Cadence=` attributes).

| File | Stimulus | What's distinctive | Structure | Source |
|------|----------|--------------------|-----------|--------|
| `T1_MuscleTension_Intervals_FasCat` | Strength-endurance (sub-thr) | Power-**agnostic** — limiter is torque/stroke, capped ~85% | 4×8min @50-55rpm, 4min off | FasCat |
| `T2_SFR_Salite-Forza-Resistenza` | Aerobic strength | Italian climb tradition; shorter/higher-rep, "don't pull the bars", never <40rpm | 6×4min @88% @45-50rpm | Sassi/Moser, Hero Dolomites |
| `T3_TorqueMax_SupraThreshold_EVOQ` | Supra-threshold VO2+torque | VO2 power AND max torque at once; ~1 Nm/kg target | 6→8×2.5min @108% @50-55rpm | EVOQ.bike |
| `T4_Ruegg_Torque-to-Power-Release_EF` | Torque→velocity transfer | Big-gear torque then **shift down + 1min max spin-up** within each rep | 4×(5min @115% @55rpm + 1min max) | EF Pro Cycling (Rüegg) |
| `T5_Pogacar-UAE_Torque-VO2-Sprint-Stack` | Torque+VO2+sprint, fatigued | Three demands stacked; **incomplete** high-Z2 recovery | 7×(2.5min @110% @50rpm + 15s sprint), 3min Z2 | UAE / Pogačar (Swart) |
| `T6_ForceReps_Stomps_Standing-Starts_CTS` | Neuromuscular force (alactic) | Max torque from **near-standstill** in a huge gear; long full rests | 8×12s max, 5min recovery | CTS / Pez |
| `T7_Sit-Stand-Efforts_Rouleur` | Posture/cadence contrast | Seated low-rpm ↔ standing higher-rpm at **constant watts** | 3×12min: 2min seat@50 / 1min stand@85 | Rouleur |
| `T8_Descending-Cadence_Torque-Ladder` | Cadence manipulation | Same watts, cadence steps **down** each rep so torque climbs | 4×5min @85%, 70→60→50→45rpm | Gear & Grit / CTS |

## Progressions (recommended) — `progressions/` (32 files, L1→L4 each)

Each session now has a 4-level ladder in `torque-pack/progressions/`. The 8 files
above are quick single sessions; the ladders are what you actually train through.

**Every progression file has a proper warm-up:** 15–20 min Z1→Z2 ramp **+ 1×10 min
high-cadence Z3 @100–120 rpm** (wakes up leg speed before the grind), plus 2–3×30s
spin-up openers before the supra-threshold/neuromuscular sessions (T3–T6).

**Progression principle (from the cadence ramp-in research):** as you adapt,
**cadence drops and volume/intensity rises** — L1 is the ~58–62 rpm entry, L4 the
~45 rpm peak.

| Session | L1 (entry) → L4 (peak) |
|---------|------------------------|
| T1 Muscle Tension | 3×7min @58-62rpm → 4×10min @48-52rpm (FasCat's 5-wk ramp) |
| T2 SFR | 4×3min @55-58rpm → 8×4min @45-48rpm |
| T3 TorqueMax | 5×2min @105%/60rpm → 8×3min @112%/50rpm |
| T4 Rüegg Torque→Power | 3×(4min@110%) → 5×(6min@115%), spin-up 135%→145% |
| T5 Pogačar Stack | 5 reps @105%/57rpm → 8 reps @112%/48rpm, sprint 160%→190% |
| T6 Force Reps/Stomps | 6×8s → 12×15s (count up, rests stay long) |
| T7 Sit-Stand | 3×9min @55/85rpm → 4×15min @48/90rpm |
| T8 Descending Ladder | 4 rungs 75→48rpm → 6 rungs 75→42rpm |

**Mini-block:** run one family L1→L4 over 4–5 weeks (one session/wk), repeating a
level if you miss the cadence/power target. Only advance when you completed the
current level on-target.

## How to use them
- **Base / off-season (Oct–Feb):** T1, T2, T8 — build the platform, 1–2×/week.
- **Late base → build:** T3, T4, T7 — once low-cadence tolerance is earned.
- **Build / advanced:** T5 — high stress, experienced riders only.
- **Pre-season neuromuscular primer:** T6 — separate day, fully warmed up.
- **Cadence ramp-in:** start ~65rpm for 2 weeks → 55-60 wks 3-4 → 50rpm once joints
  are happy → reserve 40-45rpm for advanced. Low cadence loads knees/connective tissue.

## The science (for honest copy)
- **PRO:** PLOS ONE Nov 2024 (Hebisz & Hebisz) — low cadence (50-70rpm) on hard
  intervals gave **8.7% VO2max vs 4.6%** at free cadence, same load. Strongest recent
  evidence that low cadence *amplifies aerobic adaptation* — when paired with intensity.
- **CON (cite for balance):** Nimmerichter et al., Front. Physiol. 2014 — low cadence
  (40rpm) at *moderate* intensity did NOT beat free cadence in trained veterans.
  **Takeaway: low cadence pays off with HIGH intensity, not moderate.**
- **Framing caveat (Dialed Health / Derek Teel):** on-bike low-cadence "strength" work
  is primarily a **metabolic** adaptation, not a muscular/skeletal one — it does **not
  replace gym strength training**. Don't oversell it as "strength."

## Sources
FasCat MTI · CTS High-Force/Stomps (trainright.com) · Catalyst Coaching & Hero Dolomites
SFR · EVOQ.bike TorqueMax · EF Pro Cycling (Rüegg) · Cycling Weekly / Cinch (UAE/Pogačar)
· PezCycling on-bike strength · Rouleur Sit-Stand · Gear & Grit "Big Gear Big Gains" ·
PLOS ONE 2024 (pone.0311833) · Frontiers 2014 (fphys.2014.00034). Full URLs in
`../RATIONALE.md` once merged.

## Not built as files (don't model cleanly in .zwo)
- **Single-leg / isolated-leg drills** (RoadBikeRider/Triathlete) — alternating legs
  + technique focus; better done off-script. Loaded version: 50-60rpm, 90s/leg, 5-10min/leg.
- **Science-to-Sport Nm-targeted over-gear VO2** — 4min @40-50rpm on 8-12% holding a
  Nm/kg target; same power zone as T3/T5 but metered by torque, not watts.

## Regenerate
```
python3 ../generate_torque.py
```
