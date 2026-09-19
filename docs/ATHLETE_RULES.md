# Athlete rules (`rules.yaml` + `tools/athlete_layer.py`)

Spec of record: `docs/specs/2026-09-18-variety-and-weekly-dynamic-plans.md`,
section B, revision-2 decision 8.

Per-athlete post-processing used to be a bespoke Python script per athlete:
`plan-builds/<athlete>/<build>/athlete_layer.py`, hand-editing
`plan_payload.json` + `notes_payload.json` into `plan_payload_final.json` +
`notes_payload_final.json`. Three of those scripts existed (Forest Hietpas,
Edward Shapiro, Ari Shapiro). Each encoded the same handful of operations —
retitle, strip a sentence, append a guardrail, drop a note — as one-off code.

`tools/athlete_layer.py` replaces the code with one fixed pipeline and moves
the per-athlete part into data: `plan-builds/<athlete>/rules.yaml` (private
dir, outside this repo — never commit athlete source text). Ported rules
files: `forest-hietpas/rules.yaml`, `edward-shapiro/rules.yaml`,
`ari-shapiro/rules.yaml`, plus a minimal `judd-pulley/rules.yaml` for the
athlete with no bespoke script.

## Usage

```
python -m tools.athlete_layer \
  --rules plan-builds/<athlete>/rules.yaml \
  --in-dir plan-builds/<athlete>/<build> \
  --out-dir plan-builds/<athlete>/<build>
```

Reads `plan_payload.json` + `notes_payload.json` from `--in-dir`. Writes
`plan_payload_final.json` + `notes_payload_final.json` to `--out-dir` with
`json.dump(indent=1, ensure_ascii=False)` — the same serialization the
bespoke scripts used, so a diff against a committed `*_final.json` stays
clean.

From Python: `tools.athlete_layer.apply(plan, notes, rules) -> (plan, notes,
changed_log)`, where `plan`/`notes` are the parsed JSON lists and `rules` is
the parsed `rules.yaml` dict. Pure function: no file I/O, no network. The
CLI is a thin wrapper around it.

## Vocabulary

Every key is optional. An absent key is a no-op for that step. The
pipeline runs the steps below in this fixed order, regardless of the order
keys appear in `rules.yaml`.

### Permanent athlete data

These describe the athlete, not a missing engine feature. They stay even
after the engine reads `intensity_policy` / `nutrition_policy` directly
(see the engine-gap section below) — a guardrail on a flared achilles, a
teen sleep target, or a commitment note about a work shift is never going
to be an engine concern.

- **`title_format`**: `"plain"` or `"duration_lead"`. `duration_lead`
  rewrites every non-rest-day title to `"NN min — Title"` (`NN` =
  `round(totalTimePlanned * 60)`). Idempotent: an existing `"OPTIONAL:"`
  prefix is stripped before rebuilding, and the OPTIONAL state carries
  forward into the new title. Rest days (`workoutTypeValueId == 7`, or a
  title starting with `"Rest Day"`) are never touched. `"plain"` (or
  omitting the key) leaves titles alone.
- **`title_allowlist_prefixes`**: `[str]`. Title prefixes (checked after
  stripping any `"OPTIONAL:"` state) that are exempt from the
  `optional_intensity` detector below — they always render as plain
  `duration_lead` titles, never OPTIONAL. A title already matching
  `"^\d+ min —"` is left exactly as-is (no double duration prefix).
- **`force_optional_dates`**: `[YYYY-MM-DD]`. Any workout on one of these
  dates whose `workoutTypeValueId` is in
  `optional_intensity.intensity_detector.type_ids` is forced OPTIONAL
  (title + description), even if the detector below would not have
  flagged it — a travel/commitment override the engine's overlay missed on
  the coached path.
- **`replace_text`**: `[{scope: "descriptions"|"notes"|"titles", from,
  to}]`. Plain `str.replace`, applied in list order. `scope` picks the
  field: `"descriptions"` = workout descriptions, `"notes"` = note
  descriptions, `"titles"` = workout titles.
- **`title_strip_regex`**: `[regex]`. Each regex is removed
  (`re.sub(pattern, "", title)`) from every workout title.
- **`guardrails`**: `[{title_match_regex, text}]`. For every workout whose
  title matches `title_match_regex`, append `text` to its description
  unless `text.strip()` is already present — idempotent, so a rerun does
  not double the guardrail.
- **`commitment_notes`**: `[{date, title, description}]`. Coach-authored
  notes appended verbatim (as `{title, noteDate: date, description}`)
  after every other note transform.
- **`drop_rest_on_multi_session_days`**: `bool`. Drop `Rest Day`
  (`workoutTypeValueId == 7`) entries on any calendar day that also
  carries another workout (e.g. a lift plus a spin already covers the
  day; a synthetic Rest Day card is noise).
- **`drop_notes`**: `[{date, title_contains}]`. Drop any note whose
  `noteDate == date` and whose title contains `title_contains`.
- **`drop_workouts`**: `[{date, title_contains}]`. Drop any workout whose
  day is `date` and whose title contains `title_contains` -- for a day a
  TP event already owns (the engine does not consume C events and fills
  the day with a Rest Day card). Applied after
  `drop_rest_on_multi_session_days`.
- **`note_prefix`**: `{title_regex, exclude_title_contains: [str], text}`.
  For every note whose title matches `title_regex` and does not contain
  any string in `exclude_title_contains`, prepend `text` unless the
  description already starts with it.
- **`note_date_remap`**: `[{title_prefix, to_date}]`. Applied last, over
  every note (engine notes and `commitment_notes` alike): a note whose
  title starts with `title_prefix` gets its `noteDate` set to `to_date`.
- **`race_card`**: `bool`. Always `false` today (see engine gaps below).

### Engine-gap stop-gaps

These two keys stand in for a profile field the renderer does not read
yet. They belong in `rules.yaml` only until the renderer does; the fix
belongs in the renderer, not in more `rules.yaml` growth.

- **`optional_intensity`**: `{enabled, text, intensity_detector: {
  power_pct_gte, exclude_units: [str], type_ids: [int], title_regex}}`.
  Stop-gap for the athlete profile's `intensity_policy`. A workout whose
  `workoutTypeValueId` is in `intensity_detector.type_ids` and either (a)
  already carries an OPTIONAL title, (b) has a structure step target
  `>= power_pct_gte` on a unit not in `exclude_units`, or (c) has a title
  matching `title_regex`, gets an `"OPTIONAL "` title prefix; if `enabled`
  and its description does not already start with `"OPTIONAL"`, `text` is
  prepended (blank-line separated). That check is literal — it tests
  whether the description starts with the string `"OPTIONAL"`, not
  whether it already starts with `text`. Write `text` to start with
  `"OPTIONAL"` (every ported rules.yaml does) or a rerun will double it.
- **`strip_sentences`**: `[regex]`. Stop-gap for the athlete profile's
  `nutrition_policy` (forbidden calorie/deficit/weight-loss language) and
  any other per-athlete sentence ban. Each regex is removed
  (`re.sub(pattern, "", description)`) from every workout description,
  then the description is stripped.

### `race_card` — out of scope, not a rules.yaml key to grow

Race-day description tailoring (`plan-builds/<athlete>/race_card.py`) stays
a separate, per-athlete script this layer does not reproduce. `rules.yaml`
always sets `race_card: false`; `tools/athlete_layer.py` raises if it ever
sees `race_card: true`, so a future athlete cannot silently ship without
their race card. This is an engine gap raised, not routed around — see the
spec's "Engine gaps raised" list.

## Golden tests

`tools/test_athlete_layer.py` runs `apply()` against the three real
`plan_payload.json` / `notes_payload.json` pairs under the private build
dir (`~/Library/Application Support/GravelGod/TrainingPeaksPublisher/
plan-builds/<athlete>/<build>/`) and compares the result to the shipped
`*_final.json` files. Skipped (not failed) when that directory is absent —
CI and other machines never see it.

Forest's build is byte-identical (`race_card: false`, and Forest never used
`race_card.py`). Ed's and Ari's builds are byte-identical **except** the
`2026-11-07` Race Day description, which the golden test excludes from
comparison — that field is `race_card.py`'s output, opaque to this layer
per the carve-out above.
