# Open Questions: Jesse Couch
*Everything below is either unresolved in the live coaching relationship, or a
field the house profile.yaml schema wants that no email evidence supplies.
Nothing here has been invented — see profile.yaml for the null/UNKNOWN fields
this list explains.*

## Top priority — blocks correct zone-setting

1. **The actual mid-August FTP retest wattage is not in the archive.**
   Athlete's 2026-08-21 email states his "Functional Threshold Test this past
   Monday [~08-17] was up a fair amount since June," but no TP threshold-
   notification email exists for it. The likely reason: he was disconnected
   from the coach's TP account at the time (he reconnects and confirms
   "The account is connected" in the same email). The last CONFIRMED number
   in the archive is 270W from 2026-06-23 — known to be stale. **Action:**
   pull the actual mid-August value directly from TrainingPeaks (not
   recoverable from Gmail) before using FTP for anything.

## Unresolved threads (no coach reply as of 2026-08-29)

2. **Sodium/ingredients screenshot (08-27, "Re: Check In").** Athlete sent a
   product-label screenshot with corrected sodium math (394mg/bottle from the
   product itself). Coach's 08-24 "measurement before adjustment" plan
   implied a next-step analysis once real numbers came in — this is that
   data, and it hasn't been closed out.
3. **"Weight/Food Update" (08-29).** Same-day fueling/weight log from a
   4-hour ride. No response yet — plausibly just recent, not dropped.
4. **"What Went Well + Race Plan" (08-29).** Athlete explicitly asked "If the
   Race Plan does not work for you, please let me know" about his enduro-race
   pacing plan for the Czech doubleheader. No response yet.

## Schema fields the house profile.yaml wants but no evidence supplies

5. **sex** — never stated by either party anywhere in the archive.
6. **height_cm** — never stated.
7. **Age (60) is coach-asserted, not athlete-confirmed.** Coach's 2026-06-12
   email says "Since you're 60" while discussing strength periodization. The
   athlete never confirms this in any reply, and its original source
   (presumably an intake questionnaire) isn't in the Gmail archive. Treat as
   unverified provenance until confirmed against the actual intake record or
   TP profile.
8. **target_race.distance_miles / elevation_ft** for both Borderlands AZ
   State Championships and El Tour de Tucson — not stated in any email.
9. **target_race.goal_type / goal_description** for Borderlands — no email
   frames an explicit finish/top-N/podium goal for this specific race. His
   general competitive context (races well against European ex-pro fields)
   is documented but not translated into a stated goal for Borderlands
   itself.
10. **generic_demands** — not computed; this profile was assembled by hand
    from Gmail, not run through `generate_full_package.py`. If this athlete
    is ever run through the live pipeline, expect `race_match: none` (checked
    `known_races.py` — neither "Borderlands" nor "El Tour"/"Tucson" has an
    entry) and a generic-profile build.
11. **Exact Czech-race names and 09-05/09-06 dates.** These come from the
    task's own supplied anchors, not independently confirmed word-for-word in
    the Gmail archive. Best corroboration: his 2026-08-29 recap describes an
    enduro-format race, 75km with 4 unmarked timed sections, 11.5 total
    pedaling hours across what reads as two days, and his 08-27 email
    confirms a Sept 8 return flight to Italy (bounding the trip). Exact race
    names never appear.
12. **weeks_purchased / generation_revision / effective_date /
    planning_horizon_end / athlete_timezone** — none of the fulfillment
    metadata fields the house schema expects are stated anywhere in the
    archive.
13. **Whether the plan that ultimately landed on his TP calendar (by
    2026-06-11) came from a delayed successful pipeline run or was hand-built
    by the coach.** Both 2026-06-09 pipeline attempts are logged as FAILED;
    the PDF guide was manually attached 2026-06-12; no email confirms how the
    calendar itself got populated.
14. **El Tour de Tucson's full name is never spelled out in the archive.**
    The coach's emails only ever say "El Tour" (08-26, 08-27). The full race
    name is a task-supplied anchor, used in profile.yaml with that caveat
    flagged.
15. **Exact date the athlete swapped lower-body gym work for Zone 2 riding.**
    His 08-21 email says he did this "a few weeks ago" relative to that date
    — sometime in roughly late June to July, never pinned down exactly.
16. **strength.sessions_per_week** — TP notification cadence shows roughly
    weekly "Upper" entries (observed Jun 12, 17; Aug 26) but no explicit
    statement of frequency from either party.
17. **communication_frequency / accountability_need / autonomy_preference**
    — no explicit statement from either party; only inferable from behavior
    (detailed, itemized, high-engagement replies), which is noted in
    profile.yaml but not asserted as a fact.

## Added during schema-parity pass (coordinator-directed, 2026-08-29)

18. ~~`plan-builds/jesse-couch/calendar_baseline_v3.json` does not exist on
    this filesystem.~~ **RESOLVED 2026-08-29.** The file exists outside the
    repo, at `~/Library/Application Support/GravelGod/TrainingPeaksPublisher/
    plan-builds/jesse-couch/calendar_baseline_v3.json` (308542 bytes, written
    2026-08-29 08:40) — under `~/Library`, which Spotlight does not index by
    default, which is why my repo/worktree/Downloads/home-directory/`mdfind`
    search missed it. Once the coordinator supplied the exact path I read it
    directly: `{ws: [...106 workouts], ns: [...35 calendar notes]}`,
    `athleteId 1177325` on every entry (matches this profile's
    `tp_athlete_id`). All 9 travel-date entries in `profile.yaml` now carry
    `verified: true` with the specific `ns[]` note id cited per entry —
    re-read directly by me, not taken on the coordinator's word.
19. **"Danielle" and "Pia" (Nov 3 travel note) — source confirmed, relationship
    still unstated.** Verified directly in `calendar_baseline_v3.json`: `ns[]`
    note id 93518174, title "FLY TO LA to pick up Danielle and Pia" — this is
    Jesse's own calendar-note text (`ownerId` differs from `athleteId` in the
    file, consistent with coach-authored notes elsewhere, but the title text
    itself reads as the athlete's own phrasing/intent, matching the
    coordinator's account that it is not invented). Neither name appears
    anywhere in the 47-message Gmail archive, and the note carries no
    relationship context (no "wife," "daughter," etc.) — who they are to Jesse
    remains genuinely unstated. Treat as confirmed-source, unconfirmed-context
    personal data.
20. ~~"Old Man Shootout" weekly group ride — coordinator-supplied, unverified.~~
    **RESOLVED 2026-08-29.** Directly confirmed in `calendar_baseline_v3.json`'s
    `ws[]` array as a titled workout, not just a calendar note: 5 occurrences,
    every one a Saturday (2026-10-03, 10-10, 10-24, 10-31, 11-07), explicitly
    called "your protected long day" (2026-10-05 note) and "anchor long ride
    for the week" (multiple workout descriptions). Skips 2026-10-17 (High
    School Reunion) and does not appear before Oct 3 or after Nov 7 in this
    snapshot — cadence and date range are source-confirmed real facts now, not
    an asserted claim. See `recurring_sessions` / `calendar_protection` in
    profile.yaml for full citations.
21. **`availability_roles`** — left `null`. Unlike Steve Wagner, this athlete's
    archive contains no questionnaire-style day-by-day availability
    submission (no equivalent of preferred_days/long_ride_days/interval_days/
    off_days grid). If one exists in TrainingPeaks or an original intake
    record outside Gmail, it was not in the sources I had access to.
22. **13 additional steve-wagner top-level keys remain absent from this
    profile** (not requested in this pass, flagging for completeness): `bike`,
    `coaching`, `health_factors`, `life_balance`, `lifestyle`, `mental_game`,
    `methodology_preferences`, `motivation`, `movement_limitations`, `social`,
    `strength_preferences`, `work`, `workout_preferences`. None of these have
    supporting evidence in the Gmail archive I reviewed. Scoped out of this
    pass per the coordinator's explicit 8-key list; revisit if full schema
    parity is required.
