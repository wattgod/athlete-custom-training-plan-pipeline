# Sheet Additions — Forest Hietpas

Prepared 2026-09-01. Target workbook: **Forest Hietpas — Historical Coaching
Trends & Communications**, Drive file `1e_p-lSHifduWWk37WAJZdRPNXreE1_5gf0w8Mmw_Zbo`
(owned by stormspandies@gmail.com).

Headers and first-empty-row below were read from a freshly downloaded copy of
the live workbook, not assumed. Rows are tab-separated — paste into the named
cell and Sheets will split the columns.

Source for everything here: Forest's email 2026-08-31 21:44 UTC, Gmail message
`1a059c84fb079225`, thread `1a04f95a7162fab1` ("Re: Welcome Back").

---

## 1. Messages 2025-26 — paste at `A771`

Header (A1:L1): `Message ID · Athlete · Date · Direction · Sender · Service ·
Chat · Body · Attachments · Unread · Coaching Signal · Source`
First empty row: **771** (770 populated).

```
gmail:1a059c84fb079225	Forest Hietpas	2026-08-31 21:44:43	Athlete → Coach	Forest Hietpas	Email	Re: Welcome Back	Thanks for getting everything up. Sadly I got sick last night and had to start by taking day 1 off. I don't work Fridays so I don't do 20min rides on Fridays. I'll just do longer workouts. Runs on m-th will never be more than 40min. I don't have the time. If I have a rest day I'd rather take it on a m-th so that I don't impact my opportunities to do bigger things on the weekend. Unless you really want me to chill out on a weekend. Which I'm also down to do. Just clarifying where my mind goes.	0		Availability constraints + illness (day 1 missed)	Gmail thread 1a04f95a7162fab1
```

---

## 2. Action & Decision Log — paste at `A19`

Header (A1:J1): `Timestamp · Action · System · Result · Source ID · Actor ·
Status · Risk / Note · Next Step · Link`
First empty row: **19** (18 populated).

```
2026-09-01	Rebuilt block from athlete feedback	Motoren (athlete-custom-training-plan-pipeline)	Friday 20-min ride removed; Friday is now the long day (95/95/110/100 min across W1-W4); rest days moved to Mon+Tue; cycling budget raised 2.0 → 4.0 h/wk; total volume 3.4 → 5.3 h/wk	gmail:1a059c84fb079225	Claude	Complete — NOT yet applied to TP	Plan is bike + strength only. No runs generated, and Beat the Blerch (2026-09-12) sits on the calendar as a Rest Day. Cause: profile discipline=gravel routes past dual_sport_dispatch, the only sanctioned run path.	Coach ruling: cycling block or dual-sport block. Then publish to TP.	https://app.trainingpeaks.com/#calendar/729185
```

---

## 3. Re-Onboarding 2026 — no paste row

That tab is a key/value brief, not an append-style table. Two cells are now
stale and should be edited in place rather than appended:

- **Status** (currently "Draft follow-up ready") → athlete has replied; block
  rebuilt 2026-09-01, awaiting coach ruling on runs.
- Add Friday to the weekly shape: **no 20-min ride, long day, 110 min
  available, athlete does not work Fridays** (his ruling, 2026-08-31).

---

## Profile changes made (source of the rebuild)

`athletes/forest-hietpas/profile.yaml`:
1. Removed the Friday entry from `recurring_sessions` (the 20-min 4am ride).
2. `schedule_constraints.preferred_off_days`: `[tuesday, saturday]` →
   `[tuesday, monday]` — he wants rest Mon–Thu so weekends stay open.
3. `availability_roles.long_ride_days` and `preferred_long_day`: `saturday` →
   `friday`. Saturday was the designated long day while also being
   `availability: unavailable, max_duration_min: 0` — a standing contradiction
   caused by encoding this block's specific Saturday commitments (Time w Finn
   09-05, Beat the Blerch 09-12) as permanent weekly unavailability.
4. `weekly_availability.cycling_hours_target`: `2.0` → `4.0`. Without this the
   Friday slot stayed empty — the four 4am rides plus one real session consumed
   the entire old budget. Still under his 7 h available and inside the "build
   to 6–7 h" note.
5. `daily_shape.friday` updated from "not specified in the 08-21 call" to his
   2026-08-31 ruling.

**NOT made:** the 40-minute Mon–Thu run cap. `dual_sport_week.yaml` is a single
global config with a fixed weekly template and no per-athlete override, and no
Thursday run slot. Encoding it would change policy for every dual-sport
athlete. Raised as an engine gap rather than routed around.
