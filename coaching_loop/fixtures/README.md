# TP READ fixture capture recipe

This file tells you how to capture a real TP READ fixture and check it
against the schema. Write it in plain, short steps. Do not skip steps.

## What this fixture is

A TP READ fixture is a JSON file. It holds three things from
TrainingPeaks, for one athlete, for one week:

- the athlete's calendar for that week
- the workouts on that calendar
- comments on those workouts, in DERIVED FORM ONLY

Derived form means: no raw comment text. A comment record holds a
comment id, a workout id, a lexicon version, a list of lexicon hit term
ids, and a character length. It never holds the words the athlete wrote.

## Before you capture a fixture

1. Confirm the athlete id is not 418209. This id is excluded by code.
   Do not capture data for this athlete. Do not paste it into any
   fixture file.
2. Confirm you are logged in to TrainingPeaks as the coach. Use the
   coach's own browser session. Do not use any other account.
3. Confirm you will make READ calls only. Do not edit, add, or delete
   anything on the athlete's calendar during capture.

## Capture steps

1. Open the athlete's TrainingPeaks calendar. Go to the target week.
2. Read the week start date. Convert it to the athlete's own time zone.
   Confirm it falls on a Monday. Use this value as `calendar.week_start`.
3. Record the athlete's time zone as `calendar.athlete_tz` (IANA name,
   for example `America/Denver`).
4. For each of the 7 days in the week, record the date and the list of
   workout ids on that day. Use this to build `calendar.days`. Every
   week has exactly 7 day entries, Monday through Sunday. A rest day
   still gets a day entry, with an empty `workout_ids` list.
5. For each workout id, record these fields into `workouts`:
   - `workout_id`, `date`, `sport`, `title`, `status`
   - `slot`, if the loop already classifies this workout; otherwise use
     `null`
   - `structure`, if TrainingPeaks returns a structured workout; otherwise
     use `null`
   - `planned_duration_hours`, `completed_duration_hours`
   - `tss_planned`, `tss_completed`
   - `loop_owned`, true only if this workout id is in the engine's
     ownership registry
6. For each comment on a workout in this week, do this:
   a. Read the comment text.
   b. Run the comment text through the lexicon scanner (lexicon version
      pinned in `athletes/config/` per the loop's lexicon manifest).
   c. Record only the derived fields: `comment_id`, `workout_id`,
      `lexicon.version`, `lexicon.hits` (the list of matched term ids),
      and `length` (character count of the raw text).
   d. Discard the raw comment text. Do not write it to any file. Do not
      put it in `structure`, `title`, or any other free-text field.
7. Set `schema_version` to `"tp-fixture-v1"`.
8. Set `athlete_id` to the athlete's TrainingPeaks id, as an integer.
9. Set `fetched_at` to the current UTC timestamp.
10. Set `source` to `"real_capture"`. This marks the fixture as real
    data, not synthetic test data.
11. Save the file under a fixtures directory the parent session names.
    Use the pattern `tp_snapshot_<athlete_id>.json`.

## Validate the fixture

Run the validation script on the file you just saved:

```
python3 -m coaching_loop.validate_fixtures path/to/tp_snapshot_<athlete_id>.json
```

The script checks two things:

1. The athlete id is not 418209. If it is, the script fails and prints
   the reason. Delete the file. Do not use it.
2. The file matches `coaching_loop/schemas/tp_fixture.schema.json`. If a
   field is missing, wrong type, or extra, the script prints the exact
   field path and the problem.

Fix every problem the script reports. Run the script again. Do not use a
fixture that fails validation.

## What this recipe does not cover

- Comment text handling beyond derived form. The ONE sanctioned
  exception is an 8-word-max excerpt stored later in an exception
  ledger record, at proposal-generation time, not at capture time. Do
  not build that excerpt during capture.
- Readiness/wellness time series. TP READ fixtures cover calendar,
  workouts, and comments only. A2's readiness slope needs a different
  data source; that source and its fixture contract are not part of
  CL-T0a.
- Writing to TrainingPeaks. This recipe is read-only. If a step in this
  recipe ever asks you to save, edit, or delete something on the
  athlete's calendar, stop. That is out of scope for a fixture capture.
