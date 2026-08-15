# Delivery reference fixtures

These fixtures are sanitized TrainingPeaks calendar captures used to show the
current house-standard delivery. They are examples for future delivery-lint
work; they do not define lint behavior by themselves.

## Schema

Each fixture has the `reference_capture/v1` header:

- `captured_range` is the inclusive date-only range covered by workouts and
  notes.
- `source` identifies the sanitized source-slug placeholder and capture
  month. The literal supplied slug is intentionally not retained because it
  commonly embeds the athlete's name.
- `counts` records the per-kind workout count and note count.
- `payload_sha256` is SHA-256 of canonical UTF-8 JSON for
  `{"notes": [...], "workouts": [...]}` (sorted keys, compact separators).

Workout records retain a synthetic `workoutId` and `athleteId`, plus `date`,
`title`, `kind`, `totalTimePlanned`, `tssPlanned`, `ifPlanned`,
`description`, and object-valued `structure`. Note records retain a synthetic
`id` and `athleteId`, plus `date`, `title`, and `description`. Athlete IDs
begin at `1000001`; workout and note IDs are sequential from `1` in their
respective collections. Dates are normalized to `YYYY-MM-DD`.

`kind` maps TP type 2 to `bike` (or `race` for a `RACE DAY` title), type 9 to
`strength`, and type 7 to `day_off`.

## Capture and governance

Engineering owns `athletes/scripts/capture_reference.py`. It accepts either
observed TP dump shape (`workouts`/`notes` or `w`/`n`), sanitizes athlete
names, guide URLs, email addresses, and provider identifiers, and writes a
deterministic fixture. Staged raw dumps remain outside version control.

Changing the house standard requires coaching approval. Regeneration is an
explicit, reviewed diff: run the capture tool against a fresh approved raw
dump, inspect the scrubbed output, and run the fixture tests before accepting
the new reference.

Lint rules are authored invariants; fixtures demonstrate them. A hand-built
calendar can propose a rule change, but it must not silently redefine what
the linter treats as correct.
