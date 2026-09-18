# weekly_packet/v1

Single source of truth for the `weekly_packet/v1` field names. The producer
(`tools/tp_weekly_packet.js`, run by the session via playwriter, read-only)
and the consumer (`athletes/scripts/weekly_packet.py`, Executor A) both
conform to this document. If either side needs a field this doc does not
list, add it here first, then implement it.

Spec of record: `docs/specs/2026-09-18-variety-and-weekly-dynamic-plans.md`,
"B — revision 2 after adversarial review", decision 5.

## Top-level shape

```json
{
  "schema": "weekly_packet/v1",
  "athlete_key": "forest-hietpas",
  "tp_athlete_id": "123456",
  "as_of": "2026-09-18",
  "settings": { "...": "see below" },
  "events": [ "...": "see below" ],
  "pmc_daily": [ "...": "see below" ],
  "workouts": [ "...": "see below" ],
  "notes": [ "...": "see below" ],
  "source_manifest": { "...": "see below" }
}
```

| Field | Type | Notes |
|---|---|---|
| `schema` | string | Always `"weekly_packet/v1"`. |
| `athlete_key` | string | Passed in by the caller (`window.__PACKET_ARGS__.athleteKey`); never derived from TP. |
| `tp_athlete_id` | string | Passed in by the caller (`window.__PACKET_ARGS__.athleteId`), stringified. |
| `as_of` | string (`YYYY-MM-DD`) | Passed in via `window.__PACKET_ARGS__.asOf`, else the browser's local date at capture time. All windows below are computed from `as_of`. |
| `settings` | object | See "settings". |
| `events` | array | See "events". |
| `pmc_daily` | array | See "pmc_daily". |
| `workouts` | array | See "workouts". |
| `notes` | array | See "notes". |
| `source_manifest` | object | See "source_manifest". |

## Date windows (computed from `as_of`, inclusive both ends unless noted)

| Array | Window | Rationale |
|---|---|---|
| `events` | `[as_of, as_of + 180d]` | "next 180 days" per spec. |
| `pmc_daily` | `[as_of - 42d, as_of - 1d]` | "42 days ending yesterday" — `as_of` itself is excluded because TP's PMC report for the current day is usually incomplete. |
| `workouts` | `[as_of - 42d, as_of + 14d]` | "42 days back + 14 forward" per spec. |
| `notes` | `[since, as_of + 14d]` | `since` comes from `window.__PACKET_ARGS__.since` (required). End is pinned to the same forward edge as `workouts` so a note about next week's plan is captured alongside it — **this end-date choice is not in the spec text and is this executor's assumption; flag if wrong.** |

## `settings`

Verbatim (not renormalized) subset of `GET /fitness/v1/athletes/{id}/settings`:

| Field | Type | Source |
|---|---|---|
| `ftp_watts` | number\|null | `powerZones[0].threshold` |
| `weight_kg` | number\|null | `weight` when present. The live `/settings` response carries no weight field at all (verified 2026-09-18 on a coached athlete), so this is null in practice; the profile keeps its own weight. |
| `thresholds` | object | **Raw, unmodified** `{ powerZones, heartRateZones }` sub-objects from the settings response, exactly as returned. This is the "thresholds raw" field the spec calls for — never derive zone math from it in this script. |

## `events[]`

| Field | Type | Source |
|---|---|---|
| `id` | string | `row.id ?? row.eventId` |
| `date` | string (`YYYY-MM-DD`) | `row.eventDate` sliced to 10 chars |
| `name` | string | `row.name` |
| `priority` | string\|null | `row.atpPriority` |

## `pmc_daily[]`

One row per calendar day in the window (gaps filled with `null` metrics, never dropped).

| Field | Type | Source (unverified field names — see "Endpoint proof") |
|---|---|---|
| `date` | string (`YYYY-MM-DD`) | report row date |
| `ctl` | number\|null | |
| `atl` | number\|null | |
| `tsb` | number\|null | |
| `tss_actual` | number\|null | |
| `tss_planned` | number\|null | |

## `workouts[]`

| Field | Type | Source |
|---|---|---|
| `workout_id` | string | `row.workoutId ?? row.id` |
| `date` | string (`YYYY-MM-DD`) | `row.workoutDay` sliced to 10 chars |
| `title` | string | `row.title` |
| `type_id` | number\|null | `row.workoutTypeValueId` |
| `dur_planned_h` | number\|null | `row.totalTimePlanned` (TP reports this in hours already) |
| `dur_actual_h` | number\|null | `row.totalTime` (live v6 field, verified 2026-09-18; `totalTimeActual` accepted as a fallback) |
| `tss_planned` | number\|null | `row.tssPlanned` |
| `tss_actual` | number\|null | `row.tssActual` (unverified field name — see "Endpoint proof") |
| `if_actual` | number\|null | `row.if` (live v6 field, verified 2026-09-18) |
| `np` | number\|null | `row.normalizedPowerActual` (unverified field name) |

## `notes[]`

| Field | Type | Source |
|---|---|---|
| `note_id` | string | `row.id ?? row.calendarNoteId` |
| `date` | string (`YYYY-MM-DD`) | `row.noteDate` sliced to 10 chars |
| `title` | string | `row.title` |
| `description` | string | `row.description` |
| `comments` | array | See below. `[]` when the comments fetch 204s or is unavailable — never omit the key. |

`notes[].comments[]`:

| Field | Type | Source |
|---|---|---|
| `id` | string | comment row `id` |
| `date` | string (`YYYY-MM-DD`) | comment row date field, sliced to 10 chars |
| `author` | string | comment row author/display-name field |
| `text` | string | comment row text/body field |

## `source_manifest`

| Field | Type | Notes |
|---|---|---|
| `captured_at` | string (ISO 8601 UTC timestamp) | Set once, at the start of the run. |
| `endpoints` | array of `{path, status}` | One entry per HTTP call actually made (including calls that failed) — `path` is the request path (no query string beyond the `{start}/{end}` segments), `status` is the HTTP status code as a number, or the string `"error"` with the error message appended after a colon for a transport-level failure (no response). |

## Endpoint proof (checked against this repo and `~/plugins/endure-coaching-ops` before writing the producer)

| Endpoint used | Status | Evidence |
|---|---|---|
| `GET /fitness/v1/athletes/{id}/settings` | **Proven** | `athletes/monika-renk/implementation-notes.md` D6: live response fields quoted verbatim (`powerZones[0].threshold`, `heartRateZones[0]`). Also cited in `docs/CONSULT_ENGINE_SPEC.md`. |
| `GET /fitness/v6/athletes/{id}/workouts/{start}/{end}` | **Proven, but see conflict below** | `docs/CONSULT_ENGINE_SPEC.md`, `docs/PLAN_TRUTH_SPEC.md` I2, `docs/runbooks/CUSTOM_DELIVERY_RUNBOOK.md` all cite `fitness/v6/athletes/{id}/workouts` for reads/writes in this repo. **Conflict:** `~/plugins/endure-coaching-ops/skills/trainingpeaks-publisher/scripts/read_trainingpeaks_inventory.py` (a reviewed, tested transport) reads workouts from `fitness/v7`, not `v6`. This script uses **v6** because that is what the brief specified and what this repo's own docs consistently cite; v6/v7 is flagged as an open question below — confirm which is live-correct before the first real run. |
| `GET /fitness/v3/athletes/{id}/calendarNote/{start}/{end}` | **Proven** | `docs/runbooks/CUSTOM_DELIVERY_RUNBOOK.md`, `read_trainingpeaks_inventory.py` (tested substring assertion in `~/plugins/endure-coaching-ops/tests/test_trainingpeaks_publisher.py`). |
| `GET /fitness/v1/athletes/{id}/calendarNote/{noteId}/comments` | **Not independently proven** | Only source is this brief. No citation found in this repo or the plugin. Script calls it defensively (treats 204 and 404 alike as "no comments") and records the real status in `source_manifest`. |
| `POST /fitness/v1/athletes/{id}/reporting/performancedata/{start}/{end}` with `{"atlConstant":7,"atlStartValue":0,"ctlConstant":42,"ctlStartValue":0,"workoutTypes":[]}` | **Proven** | `docs/CONSULT_ENGINE_SPEC.md` §6: "PMC (`POST …/reporting/performancedata/{start}/{end}` with the constants body)". Response row field names (`ctl`/`atl`/`tsb`/`tssActual`/`tssPlanned` and equivalents) are **not** shown anywhere found — the mapper in `tools/tp_weekly_packet.js` tries several plausible casings defensively and this must be corrected against the first real response. |
| `GET /fitness/v6/athletes/{id}/events/{start}/{end}` | **Proven** | `read_trainingpeaks_inventory.py`, tested. This resolves the brief's "if you can cite one" fallback question — a real events endpoint exists and is used here instead of deriving events from race-flagged workouts. |
| `GET /users/v3/user` (roster) | **Not used** | Listed in the brief as a proven endpoint, but nothing in `weekly_packet/v1`'s schema needs roster data — `athlete_key`/`tp_athlete_id` are caller-supplied. Not called by this script. |
| Workout comment threads (`workoutComments` on the workouts response) | **Not independently proven** | Brief asserts the v6 workouts response "includes workoutComments threads". No citation found. The mapper reads `row.workoutComments` defensively (passes it through unmapped, only if present) but the schema above does not commit to a shape for it, since nothing confirms the response carries it.

## Non-goals

- No writes of any kind. Every call in `tools/tp_weekly_packet.js` is a GET,
  except the PMC report call, which is a POST that only reads a computed
  report (documented above) and never mutates athlete data.
- No athlete source text is committed to this repo. The example fixture at
  `tests/fixtures/weekly_packet_example.json` uses synthetic values only
  (`athlete_key: "example"`).
