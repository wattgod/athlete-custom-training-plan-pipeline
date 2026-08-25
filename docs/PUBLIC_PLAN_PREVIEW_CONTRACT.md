# Public training-plan preview contract

Status: additive boundary on `codex/public-plan-preview-20260825`, forked from
the active Claude-polished branch at `e785ccb`. The browser integration remains
gated until the active branch's canonical engine interface is final.

## Boundary

The three marketing sites send `training-plan-preview-request/v1` to a
server-side preview endpoint. They never call `/engine/block`, carry an engine
secret, reproduce workout-selection logic, or receive raw PlanIR/library data.

The server maps the finalized canonical engine result into
`training-plan-preview/v1` through `webhook/preview_contract.py`. Projection is
allowlist-only: unknown source fields are discarded. Common internal tokens in
athlete-visible text fail closed.

## Request

```json
{
  "schema_version": "training-plan-preview-request/v1",
  "brand": "gravel_god",
  "preset_id": "committed-8",
  "race": {
    "slug": "unbound-200",
    "name": "Unbound Gravel 200",
    "discipline": "gravel",
    "demands": {"durability": 10, "heat": 8, "vo2_power": 6}
  },
  "rider": {
    "hours_per_week": 8,
    "preferred_days": ["tue", "thu", "sat", "sun"],
    "experience_level": "intermediate"
  }
}
```

Constraints: 4–18 hours; at least three preferred days; demand values 0–10;
known brand and experience enums; bounded strings and arrays.

## Response

The response includes:

- `schema_version`, `engine_version`, and `voice_version`;
- a deterministic `preview_id` and 15-minute cache TTL;
- normalized race and rider inputs;
- one complete seven-day week with target time/TSS;
- multiple sessions per day when applicable;
- distinct title, explicit purpose, duration, TSS, intensity, fuel tag, fueling
  guidance, and coach note;
- sanitized TrainingPeaks structure steps and normalized tile polyline;
- a complete strength block with focus, exercises, sets, reps, rest, and cues;
- the week-level coach note, weekly self-review, and workout-comment protocol.

## Consumer preview quality gate

The endpoint fails closed on a technically valid but unconvincing week. A
consumer preview must schedule work only on selected days, credibly use the
rider's available time, contain at least two race-discipline workouts and one
complete strength workout, and give every discipline workout structured steps,
a visible polyline, fueling guidance, purpose, and a coach note. Workout titles
must be distinct. This makes the preview a representative TrainingPeaks build
week rather than a sparse calendar-shaped teaser.

The marketing renderer presents the entire week at once, using TrainingPeaks'
marketplace sample-week conventions (day strip, sport/type, duration,
structured-workout profile, and expandable details) as a baseline. It adds a
first-class strength presentation and recomputes the full week when hours,
days, experience, or race change.

`voice_version` defaults to a digest of the checked-in voice renderers and
their contract tests. Production may override it with
`COACHING_VOICE_VERSION`, provided the value is a safe version token.

## Final-interface gate

The remaining engine-side adapter must consume the finalized canonical model
or PlanIR projection produced by the active Claude branch. It must not rebuild
structures from names, copy the frozen Endure `/engine/block` output, or
derive a second race-demand model. Until that interface lands, contract tests
use a production-shaped canonical fixture and no endpoint is exposed.

## Endpoint requirements before exposure

- same-origin or explicit allowlisted CORS for the three production domains;
- public rate limit and bounded request body;
- server-side cache keyed by the normalized request plus engine/voice version;
- no browser-visible secret;
- generic 400/422/429/503 errors with no stack traces or private paths;
- response validation through `project_response()` on every cache miss;
- analytics only after a person changes a control or selects a preset.
