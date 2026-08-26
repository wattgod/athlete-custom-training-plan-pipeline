# Public training-plan preview contract

Status: wired boundary on `codex/public-plan-preview-20260825`, rebased onto
Motoren's finalized canonical interface at `e231103`.

## Boundary

The three marketing sites send `training-plan-preview-request/v1` to a
server-side preview endpoint. They never call `/engine/block`, carry an engine
secret, reproduce workout-selection logic, or receive raw PlanIR/library data.

The server maps the finalized canonical engine result into
`training-plan-preview/v1` through `webhook/preview_contract.py`. Projection is
allowlist-only: unknown source fields are discarded. Common internal tokens in
athlete-visible text fail closed.

### Full-plan simulator (v2)

`training-plan-preview-request/v2` preserves v1 and adds the inputs required
for a truthful interactive delivery preview: plan length, race date and
expected duration, goal type, control method and applicable tested markers,
strength equipment, and optional per-preferred-day minute caps.
An optional `sample_week_number` asks Motoren to include that exact calendar
week, allowing every full-plan volume bar to be inspected without shipping
all workout copy in one response.

The response is `training-plan-preview/v2`. `planned_volume` contains every
week in the generated plan. `sample_weeks` contains two to four complete,
dated TrainingPeaks-style calendar samples and `plan.sample_week_numbers`
links them to the full curve. For every sample, phase, week type, dates,
minutes, and TSS must equal its corresponding `planned_volume` entry exactly.
The race week and its emitted race duration/TSS are mandatory.

The v2 projection also consumes private provenance assertions. Bike, ski, and
strength sessions must have passed the real coach-library rendering path;
race sessions must be engine overlays and cannot contain synthetic power
structure. Those assertions are not exposed publicly. Any mismatch fails the
whole response closed—partial and fallback plans are never public output.

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

## Motoren provider

`webhook/engine_preview_provider.py` lazily calls
`athletes/scripts/motoren_preview.py::generate_preview_source`. It also uses
Motoren's `engine_version()` and `voice_version()` callables for the public
envelope and cache key. Motoren runs the real block-builder, Nate renderer,
canonical TrainingPeaks projection, fueling policy, and voice pipeline in
memory; the adapter never rebuilds structures from names or calls the frozen
Endure `/engine/block` endpoint.

The endpoint remains independently kill-switched with
`PUBLIC_PLAN_PREVIEW_ENABLED`, so preview import/generation failures cannot
prevent the paid-order service from booting or fulfilling orders.

Motoren currently has native cycling disciplines only. Requests from
`xc_ski_labs` fail closed at the provider boundary rather than silently
returning the engine's gravel fallback as ski training. XC Ski exposure stays
off until a canonical ski provider passes this same contract and quality gate.

## Endpoint requirements before exposure

- same-origin or explicit allowlisted CORS for the three production domains;
- public rate limit and bounded request body;
- server-side cache keyed by the normalized request plus engine/voice version;
- no browser-visible secret;
- generic 400/422/429/503 errors with no stack traces or private paths;
- response validation through `project_response()` on every cache miss;
- analytics only after a person changes a control or selects a preset.
