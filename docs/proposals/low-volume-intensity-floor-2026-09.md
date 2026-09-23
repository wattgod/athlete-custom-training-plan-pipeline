# Proposal: the AE-2.1 hard-minutes floor for low-frequency athletes

Status: **PROPOSED, needs a ruling from Matti.** Nothing here is implemented.
Opened 2026-09-23 from the 2026-09-22 custom-plan order. Extends the open
contradiction §12 C2 in `docs/ALGORITHM_EVIDENCE.md`.

## What happened

A paying athlete, time-crunched, riding 2-3 days a week (~75 mi, about
5 h), lifting kettlebells three days a week, back from a crash and
concussion, asked for "a structured plan that will not leave me over trained
and blasted all the time." His 34-week plan came back from the review gate
with 26 `HARD_MINUTES_BELOW_FLOOR` warnings (5-44 hard minutes per load
week against 90) and an `R05` critical on every load week (1 intensity
session, gate wants 2).

The PR that carries this file fixes the two places where the gate applied a
rule more broadly than the rule is written:

- **AE-2.1 is scoped to athletes training at least 6 h/wk.** The gate
  applied it to everyone. It now skips athletes whose stated weekly hours
  are under 6.
- **R05's registry row allows one quality day when an athlete has 3 or
  fewer available cycling days.** The gate ignored that clause. It now
  honors it. See "The R05 judgment call" below.

What is left is a real conflict between ratified rules and what a
low-frequency calendar can hold.

## The rules involved

| Rule | Tier | What it says | Citations |
|---|---|---|---|
| AE-2.1 | Matti-authored | 90-120 min at >=92% FTP per load week for athletes at >=6 h/wk; below ~90, VO2max gains are "small and inconsistent"; day cap novices 2, mature 3 | "The 80/20 Trap"; R19; F3 |
| AE-2.2 | Matti-authored | Intensity share scales inversely with hours, ~70/30 at 7 h/wk, measured by time in zone ("hard" = everything above Z2) | WG "80/20 Trap", "Peter Attia" draft; D4 |
| AE-2.3 | E | Polarized is about 1-2 hard days; pyramidal 2-3 | R86; F4; J1 |
| AE-2.6 | H | VO2 maintenance every 14 days stands, even in base | R36, R54 |
| AE-3.1 | P, M | A VO2 session carries 5-18 min at >=106% FTP | WG FUNDAMENTALS + scorecard; R14, R93-R95 |
| R05 | registry, ACTIVE/CRITICAL | 2-3 intensity sessions per load week; training age <1 or <=3 available cycling days allows 1-3 | `docs/SPEC_EARNED_SELECTION.md` A3.6 |
| R01 | registry, ACTIVE/CRITICAL | No back-to-back intensity days | same |
| Long-ride buffer | house pattern, not an AE rule | Intensity days are never placed next to the long ride unless the athlete asked for that | `CLAUDE.md` ("Intensity days prefer Tue/Thu") |

## Why 90 minutes is out of reach for these calendars

The floor counts minutes at or above 92% FTP.

- A VO2 day is capped by AE-3.1 at 18 minutes at or above 106%. Counting
  the sub-106% reps, a VO2 day lands around 15-25 hard minutes.
- A threshold day at 95-100% can carry 40-45 minutes (2x20, 3x15).
- With two quality days the only way to 90 is two long threshold days
  every load week, which leaves no room for the VO2 touch AE-2.6 requires
  every 14 days.
- With one quality day the ceiling is roughly 45-60 minutes unless the long
  ride itself carries threshold blocks.

The generator's output bears this out. A synthetic athlete with three
riding days (Tue/Thu/Sat, so two quality days fit), 34-week plan, hard
minutes per load week as the gate measures them:

| Stated hours | Load weeks under 90 | Hard minutes (min / median / max) | Floor applies? |
|---|---|---|---|
| 5 h/wk | 26 of 26 | 6 / 24 / 77 | No: AE-2.1 starts at 6 h. The gate flagged these before this PR. |
| 7 h/wk | 26 of 26 | 6 / 20 / 54 | Yes, and every load week fails |

The 7 h row is the conflict. It is the same finding §12 C2 records for
Judd, Forest and Steve (10-24 hard minutes per load week): the floor is
not being met anywhere, and on a two- or three-ride week it cannot be met
without every ride being hard.

AE-2.2 does not settle it. Its 30% "hard" at 7 h is 126 minutes, but that
share counts tempo and sweet spot. AE-2.1 counts only work at 92% FTP and
up. The two rules use different rulers.

## Options

**A. Scale the floor by how many quality days the calendar can hold.** For
example, 45 minutes per quality day, capped at the current 90-120 band. The
floor bends with the schedule and still bites when the schedule has room.
Cost: 45 is a new number that needs evidence and a ruling. It also lets a
plan with one short quality day pass as compliant.

**B. For athletes with 3 or fewer riding days, replace the weekly warning
with one plan-level coach confirmation.** For example: "Low-frequency
athlete: the AE-2.1 floor is not reachable at N riding days. Confirm the
intensity dose." Measure everyone else over a rolling two-load-week window
(180 minutes) so one light week does not flag. Cost: the per-week signal
goes away for low-frequency athletes, and AE-2.1 would need the same
3-day line R05 already has. That is a ruling, not a code change.

**C. Keep the floor and make the generator reach it.** Put 92%-plus blocks
into the long ride and allow a second quality day next to the long ride.
Cost: it overrides the house long-ride buffer, goes against AE-2.3's 1-2
hard days for polarized weeks, and does the opposite of what this athlete
asked for. For someone coming back from a concussion that is hard to
defend.

**Recommendation: B.** The floor's evidence is about VO2 gains in athletes
who can absorb 90+ hard minutes. For a two- or three-ride week the useful
decision is the coach's, made once per plan, not 26 warnings that get
waived by reflex. The testing-week half of §12 C2 still needs its own
ruling. Option B does not settle it.

## The R05 judgment call in this PR

The PR's R05 change implements the "<=3 available cycling days allows 1-3"
clause from the registry row that AE-2.1 cites as the active R05. Two
things could make that the wrong call:

1. `SPEC_EARNED_SELECTION.md` is DRAFT r6. Its A3.0 table keeps the legacy
   verdict (`min(2, max_intensity)`) for R05 until the E3 cutover and
   labels the A3.6 row as the E3 target. AE-2.1 itself says any R05
   revision needs owner review and a version bump.
2. The residual case: four available days with a Saturday long ride (for
   example Wed/Thu/Fri/Sat). The long-ride buffer and R01 leave one quality
   slot, so the generator schedules one and R05 still wants two. The same
   reasoning as the three-day clause applies, but the registry row does not
   cover it. If R05's availability clause counted days where a quality
   session can go (available days not next to the long ride) instead of
   raw available days, this case would be covered.

If the registry row is not in force yet, revert the R05 commit and treat
R05 as part of this proposal.

## A related conflict from the same order

`UNRESOLVED_PAIN_MAX_PRESCRIPTION` treats any structured step at or above
105% FTP as "maximal". That covers every VO2 session, the race simulations
and the race-week openers. R02 (VO2 every 14 days, critical) and the
race-week opener and activation checks require exactly those sessions. The
intake also marks any non-"none" injury text as `status: active`, so "crash
last year, easing back in" reads as unresolved pain. This PR removes the
part the generator can honor (no field tests on such a plan). The rest
cannot be fixed in code without breaking R02. Options: ask a clearance
question at intake (cleared by a clinician? when?), and define "maximal" as
RPE 9+, all-out, sprints and tests rather than 105% FTP. Recommendation:
both.

**Blocked on:** Matti.
