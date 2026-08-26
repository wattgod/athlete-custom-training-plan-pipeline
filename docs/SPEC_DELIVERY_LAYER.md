# SPEC (DRAFT v2): The Delivery Layer — DeliveryIR + delivery_lint

**Goal:** an order becomes a finished, house-standard TrainingPeaks calendar
with zero LLM involvement per order. The coach's per-order work shrinks to
one review page and the judgment calls the machine surfaced. Everything
hand-done on the Guillermo Romero order (2026-08-14) becomes code.

v2 folds an adversarial review (gpt-5.6-sol, 2026-08-15) whose findings were
verified against the code before adoption. Where v1 assumed infrastructure,
v2 names what exists, what doesn't, and reuses the repo's settled designs:
`SPEC_TRUSTWORTHY_FULFILMENT.md` (apply lifecycle, seals, review catalog),
`apply_contract.py` (offline apply contract v1), `post_render_validator.py`,
`block_chain.derive_week_descriptors`, `block_notes.yaml`, `brands.yaml`,
`email_templates.py`. Companion tickets:
`docs/followups/CUSTOM_PLAN_QUALITY_TICKETS.md` (T1–T8).

## 0. Ground truth (verified, do not re-litigate)

- **There is no live TP apply path.** `delivery/trainingpeaks/adapter.py`
  `apply()` raises `TrainingPeaksAdapterDisabled`; the Phase-5 worker refuses
  apply/verify/rollback. What exists is the offline `apply_contract/v1`.
  Live apply is a deliverable of this spec, not a dependency.
- **PlanIR is not yet rich enough.** `Week = {number, phase, sessions}`;
  sessions lack emitted level, role, defining set, sim/dress-rehearsal
  flags; `RaceSnapshot` drops `courses[]`/`race_metadata`/climate.
  Enrichment precedes any blocker lint.
- **PlanIR already models rest days** (`_rest_session`, plan_ir.py) — the
  delivery layer decorates them; it does not invent a parallel `dayoffs[]`.
- **`apply_contract/v1` has no `if_planned`** and its note projection is
  generic-per-session — DeliveryIR requires a versioned `apply_contract/v2`
  projection.
- **`confirm_after_send` is not exactly-once** (send-then-write crash window
  duplicates email) and `APPLYING`/`APPLIED_ATTESTED` exist as constants but
  are absent from `VALID_STATUSES`.
- **The pipeline is multi-brand** (`athletes/config/brands.yaml`: Gravel God
  + Roadie Labs). Nothing in the delivery layer may hardcode Gravel God
  copy, names, URLs, or repos; unknown brand fails closed.

## 1. DeliveryIR

Versioned, sealed, provenance-carrying:

```
delivery_ir/v1
  delivery_ir_version, template_bundle_version, lint_ruleset_version,
  generator_revision, brand
  athlete: {id, first_name}
  events[]: {name, date, priority, course_resolution, drives_training?}
  guide: {staging_ref, publish_policy}            # §5
  sessions[]:                                     # one per PlanIR session,
    logical_id                                    # stable across revisions —
                                                  # (date,title) is NOT identity;
                                                  # titles change by design
    date, tp_kind, workout_type_value_id
    title            # §3 per-kind grammar
    if_planned       # power-structured bike only; else not_applicable_reason
    description_blocks[] (typed, slot-provenanced)
  notes[]: {logical_id, date, type, title, body}  # §4
  ladder:  {date -> g_per_hour, final_rehearsal_date}  # §4.3 algorithm
```

Slot values trace to source artifacts (profile / fueling.yaml / plan_dates /
race snapshot / static template). DeliveryIR digest joins the model seal and
review snapshot so the coach approves the athlete-experience, not just the
training content.

### 1.1 Delivery context (prerequisite enrichment)

Extend the canonical model/PlanIR with what templates and lint need:
`week_type` (via `derive_week_descriptors` — the single week-typing source),
emitted workout level + athlete training-age class, session role/purpose and
defining set, test protocol + post-test action, sim and dress-rehearsal
flags, event ledger, race characteristics/climate/altitude, course
resolution state, brand.

## 2. Metric and brand dispatch

Templates dispatch on `control_metric`/`control_basis` and test protocol:
"×0.95" copy is FTP-field-test-specific; LTHR/HRmax/RPE athletes get their
protocol's instruction (`canonical_training_model.py` already selects these).
RPE athletes have no TP structure by design — titles/notes must stand alone.
All copy, names ("GRAVEL GRIT" is a Gravel God asset), signatures, sender,
guide repo/URL come from the brand registry.

## 3. Title grammar (T5) — per kind

- keyed bike: `{Name} - {defining set} - {NNmin} - RPE{a[-b]}`
- plain bike: `Endurance - {NN}min - RPE3`
- strength: `{Template} - 30min` (no RPE)
- day off: `Day Off[ — {qualifier}]` (no duration/RPE)
- race: `RACE DAY — {Race Name}`

Name and set describe the EMITTED level's content, never the archetype's
terminal form. NN computed from structure.

## 4. Notes (T6–T8)

Inventory as v1 (start_here, weekly_briefing, after_test, fuel_ladder,
altitude_heat, grit_1..4, checkin, rehearsal_debrief, race_week,
after_nurture), with:

- **Scheduling is a collision-aware function, not fixed labels**: anchors +
  plan-fraction windows, minimum separation, same-day stacking order,
  merge/suppress precedence, and defined behavior when a plan lacks a
  build/peak/test/≥90-min ride/later event (a 4-week plan converges;
  a 16-week plan spreads). Weekly-briefing prose extends
  `block_notes.yaml` — no second week-type copy source.
- **Multi-course races render a decision rule from athlete-supplied facts
  only** until the `courses[]` schema ticket lands — never a sourced course
  table (S4). Multi-race athletes: the event ledger decides which later
  event drives `after_nurture`'s bridge offer and whether B-races alter
  calendar content.
- Unmet template preconditions degrade by rule (omit-with-record), never by
  emitting half-filled copy.
- **The note series is a block narrative, not a stack of reminders**:
  weekly briefings state the current intent, what the athlete is building,
  what to notice, and the handoff to the next phase or checkpoint. Athlete-
  facing copy directs; it does not defend or justify the prescription. Copy
  uses the registered brand plus an approved coach-voice
  source; absent a source, the renderer uses plain copy and records a voice-
  review item rather than inventing personal texture.
- **Autonomy is bounded**: a note may offer equivalent routes such as
  indoor/outdoor, safe terrain, duration within an approved range, or full
  rest/easy spin. Each menu preserves the training purpose, metric ceiling,
  load envelope, key-session order, and recovery. It states how to choose,
  when to stop or ask the coach, and what may not be stacked or made up.
  Health clearance, zones, event priority, and major load changes are never
  delegated.

### 4.3 Ladder algorithm (T7)

Inputs: fueling prescription (race target/range) + dated long rides
(≥90min) + sim flags. Rungs ascend monotonically THROUGH THE BUILD to the
race rate; the final pre-taper sim rung == race rate (dress rehearsal); the
taper rung is an explicit exception stepping back; race day == prescription.
Sessions <90min are off-ladder. Generated workout text defers to the ladder
until flat tags are retired.

## 5. Guide staging and publishing — OPEN COACH DECISION

Brand registry defines the guide repo/base URL. The trustworthy-fulfilment
design says guide publishing is gated/revocable with no public URL until
privacy is decided; current live practice (Monika, Guillermo) is a public
noindex URL on the brand Pages domain, linked from notes. Options:
(a) keep public+noindex (status quo), (b) tokenized unguessable paths,
(c) gated behind the course-access worker. **Coach picks; the spec encodes
the choice as `publish_policy` and notes embed the URL only after publish.**
Either way: publish is a release step bound to the approved revision, and
regeneration supersedes the published artifact.

## 6. delivery_lint

Runs in TWO modes: report-only over DeliveryIR (merged into the existing
review catalog via the `merge_generation_blockers` path — no competing
validation surface) and post-apply over a TP calendar read-back. Rules are
**authored invariants**; reference fixtures demonstrate them — a new
hand-build may PROPOSE a rule change, only coach approval ratchets the
ruleset (one flawed hand delivery must not redefine correctness).

Rules L01–L14 as v1, amended: L01 gets explicit span semantics (every
required date ≥1 entry; every otherwise-empty training date exactly one
day-off); L02 per-kind grammars; L05 encodes §4.3 including the taper
exception; L03 power-only; each rule ships report-only and is promoted to
blocker when its data dependency (§1.1) lands. L14 (PII) checks against a
forbidden-token set derived from the full profile at lint time.

## 7. Apply lifecycle (reuse, don't reinvent)

`APPROVED → APPLYING → APPLIED / APPLIED_ATTESTED → CONFIRMED` per
SPEC_TRUSTWORTHY_FULFILMENT §Phase-5: persisted intent before every remote
write, landed-operation journal with remote IDs keyed by `logical_id`,
per-athlete lease, resume/rollback/manual-completion, coach-visible failure
evidence. Add `APPLYING`/`APPLIED_ATTESTED` to `VALID_STATUSES`.

Re-apply after revision = three-way comparison (last-applied payload,
newly-approved payload, athlete's current TP object): athlete-created
entries untouched; owned objects updated only on unambiguous remote
identity; incompatible athlete edits stop for coach repair
(`apply_contract.py` semantics). Regeneration after anything landed
requires explicit supersede/abandon.

Confirmation: outbox + provider idempotency key (or provider-verified
message evidence) — the current send-then-write is not exactly-once.
Canonical state file:
`/data/deliveries/orders/<order>/fulfillment_status.json` (the
`order-work/.../athletes/` copy is generation scratch).

A failed deterministic render leaves the paid order in BLOCKED_REVIEW with
the artifact attached — never a hard order failure (order-safety).

## 8. Reference governance

Check sanitized captures (Monika 2947583, Guillermo 3032265 — currently only
in `~/Downloads`, which is unacceptable) into `references/` with schema
version, capture date-range, tool version, hashes, expected counts, PII
scrub. Ownership: capture tooling = engineering; standard changes =
coaching approval; regeneration = explicit reviewed diff.

## 9. Build order (revised per review)

1. Check in sanitized reference fixtures + capture CLI (§8).
2. Delivery-context enrichment of canonical model/PlanIR, versioned (§1.1).
3. Brand-aware templates: titles, day-off decoration, static notes, then
   computed notes, then race-derived; ladder + fuel/hydration blocks.
4. DeliveryIR → `apply_contract/v2` projection (notes, day-off decoration,
   if_planned policy, logical_ids, seals).
5. delivery_lint report-only, surfaced through the existing review catalog;
   post-apply read-back mode against fixtures.
6. Generator substance T1–T5 (separate PRs); promote lint rules to blockers
   as their data lands.
7. Guide staging + publish per the §5 decision.
8. Phase-5 worker auth, APPLYING lifecycle, three-way re-apply, rollback.
9. Post-apply lint in production, canary athlete, in-flight-order migration
   (no historical order auto-applies), permanent `APPLIED_ATTESTED` manual
   fallback.

Acceptance: a replayed Guillermo order produces — with no hand edits — a
calendar passing every lint rule, indistinguishable in kind from the
hand-built 2026-08-14 result; and a Roadie Labs order produces the same
with zero Gravel God copy.
