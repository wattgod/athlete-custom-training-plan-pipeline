# TrainingPeaks API — reverse-engineering notes (custom-plan delivery)

Load-bearing, live-verified facts about the TrainingPeaks + rx (peakswaresb)
APIs that the custom-plan apply tooling (`tools/tp_apply_order.py`,
`tools/tp_apply_driver.js`) depends on. Captured while building TP-native
custom-plan delivery; kept in-repo so future work doesn't re-derive it.

Companion: `tools/rx_exercise_catalog_full.json` (690 exercises),
`tools/custom_movement_catalog_map.json`. Polyline computation lives in
`athletes/scripts/plan_ir.py::_compute_polyline`.

---

# rx StructuredStrength — definitive capture findings (2026-07-17, live probes on Example Client 2000302)

All verified live against `api.peakswaresb.com` with a captured bearer. Every probe cleaned up; Example Client's real calendar confirmed untouched at 65 workouts throughout.

## The model (corrects the driver's 405 and WS-C's placeholder approach)

1. **No separate custom-exercise endpoint exists.** The driver's `POST /rx/activity/v1/exercises` scaffold → PUT was the 405. Clicking "Create Custom Exercise" in the UI fires **zero network calls** — the exercise is added client-side and persists inline when the workout is saved.

2. **One-shot authoring works.** `POST /rx/activity/v1/workouts {date, calendarId, workoutType:9, prescribedDate}` → returns a doc shell with `id` + `calendarId`. Then a single `PUT /rx/activity/v1/workouts` with the FULL doc (all blocks, prescriptions, exercises, sets) → 200. **No per-exercise `add/libraryContent` scaffold calls are required** — build the whole doc client-side and PUT once. (VERIFIED: a doc with a catalog Back Squat block + an inline custom Suitcase Carry block returned 200, both blocks persisted.)

3. **Catalog exercise** = embed the real exercise object from `GET /rx/activity/v1/exercises/{id}` (`{id:"131", title, ownerId:2000301, videoUrl, instructions, parameters:[{category,parameter,id}...]}`). Its `id` is a STRING numeric; params carry real ids (Reps id "67", WeightLb id "193").

4. **Custom exercise** = embed inline, no catalog lineage:
   `{id: <client-uuid>, ownerId: 2000301, title, videoUrl, instructions, primaryMuscleGroups:null, secondaryMuscleGroups:null, canEdit:true, parameters:[{id:<uuid>, category:"Reps", parameter:"Reps", unit:{title:"Reps",abbreviation:"",unit:"Reps"}}]}`. VERIFIED accepted (custom "Suitcase Carry" persisted via the workout PUT). `ownerId 2000301` = the coach's exercise-owner id (same as catalog exercises).

## Rep / parameter rules (empirically bounded)

- **`Reps` accepts INTEGERS and RANGES.** `"8"`, `"6-8"`, `"10-12"` all → 200, zero field errors. **No low-end truncation needed** — keep the range string.
- **`"10/side"` as a Reps prescribedValue is REJECTED** (field error "not a valid value").
- **`RepsPerSide` / `Duration` / `RPE` parameters → 400 (structural reject)** when placed on an exercise whose definition only declares Reps+Weight (e.g. Back Squat). These params aren't universally valid; don't emit them speculatively.
- **CORRECTION (verified 2026-07-17, second probe): every prescription MUST include ≥1 parameter.** A `foundation_a` doc with param-less prescriptions returned 200 but with field errors `"A Prescription must include at least 1 Parameter"` on each. The earlier "param-less is valid" read was false — that first empty-doc probe never actually persisted (404 on delete). So EVERY prescription carries a Reps parameter:
  - **Per-side reps** ("10/side") → `Reps:"10"` (leading number/range) + full text in `coachNotes` ("Rx: 10/side").
  - **Timed holds** ("60 sec") → `Reps:"1"` + `coachNotes:"Rx: 60 sec hold"` (do NOT emit "60" as reps; Duration/RPE params structurally 400 on exercises that don't declare them).
  - **RPE / rest / tempo** → block/prescription `coachNotes`.

## Strength-doc validity: PROVEN LIVE (2026-07-17, final)
The corrected builder's `foundation_a` output (all prescriptions carrying a Reps param) was POSTed + PUT to the real rx API → **HTTP 200, ZERO field errors, all 5 blocks / 18 sets, snapshot echoed correctly**. Verified against both a raw-athlete `calendarId` and a plan's `planPersonId`. The one-shot inline model (catalog + custom exercises embedded, no scaffold calls) is confirmed end-to-end.

## SOLVED — rx plan-attach `save` call (2026-07-17, fresh session)
`POST /rx/activity/v1/plans/{planId}/workouts/save` is the step that attaches a strength workout to a PLAN (increments the plan's tpapi `workoutCount`). The earlier 500 was **field-shape**, not endpoint/sequence. Verified working on a fresh test plan: POST shell (`calendarId=planPersonId`) → POST the full merged doc to `/plans/{planId}/workouts/save` → 200, and `GET tpapi/plans/v1/plans/{id}` → workoutCount incremented (4 saved → count 4). **No intermediate PUT to `/workouts` and NO `add/libraryContent` scaffold calls are needed** — POST-shell then save is sufficient.

The shape the SAVE endpoint requires (stricter than the standalone PUT), matched field-for-field to the netlog:
- **`parameterValues[]`**: `{parameter:"Reps", inputFormat:"Integer", prescribedValue, executedValue:null, id:<uuid>}` — **`inputFormat:"Integer"` (NOT null)** and **NO `category` key** in parameterValues. `inputFormat:"Integer"` works for plain ints AND ranges ("6-8" → 200) AND per-side surrogates ("10" → 200). (`"Range"` also accepted, but "Integer" is uniform and sufficient.)
- **prescription**: must carry `compliancePercent:0, complianceState:"NoCompletion"`.
- **block**: must carry `compliancePercent:0, complianceState:"NoCompletion"`; for `SingleExercise` blocks `title` = the exercise title.
- The doc must be **merged onto the POST-shell response** (the shell carries all ~30 nullable fields: lastUpdatedAt, prescribedStartTime, isLocked, workoutSubTypeId, prescribedTss, etc.). Overlay blocks/title/snapshot/prescribedDate/prescribedDurationInSeconds/workoutType onto the shell.
- prescription-level `parameters[]` param def DOES keep `category` (`{parameter, title, unit, category, id:<uuid>}`); only the per-set `parameterValues[]` omit category. Exercise-object `parameters[]` for a catalog exercise carry the real numeric-string param ids.

**Driver change**: strength stage per day = POST shell (calendarId=planPersonId) → merge builder doc onto shell → POST `/plans/{planId}/workouts/save`. Drop the separate PUT-to-`/workouts` for the plan case.
**Builder change** (`rx_strength_docs.py`): parameterValues → drop `category`, add `inputFormat:"Integer"`; add `compliancePercent:0`/`complianceState:"NoCompletion"` to blocks + prescriptions; SingleExercise block title = exercise title.

## CRITICAL — inline custom exercises FAIL the plan `save` endpoint (2026-07-17)
The full-stage live run (all 7 templates → plan 661307) exposed this: **the `plans/{id}/workouts/save` endpoint returns 500 on any block containing an inline custom exercise** (client-UUID id + ownerId, no real library entry). Isolated by binary search: a Superset block with two CATALOG exercises (full live objects from `GET /exercises/{id}`) saves 200; the same-shaped block with two CUSTOM exercises (Dead Bug, Suitcase Carry) → 500 "internal server error". The save evidently resolves each exercise by id against the library and crashes on an id that doesn't exist. Custom-exercise creation via API is also blocked: `POST /rx/activity/v1/exercises` returns a BLANK scaffold (ignores the posted body, ownerId forced to the account), and `PUT /rx/activity/v1/exercises` → 403. So the earlier "custom exercises embed inline and persist on save" read (from the standalone athlete-calendar PUT) does NOT hold for the plan save path.

**Also required for catalog exercises on the save path:** embed the FULL live exercise object from `GET /rx/activity/v1/exercises/{id}` (real numeric-string param ids, muscleGroups, canEdit) — NOT a trimmed reconstruction with UUID param ids. The catalog DUMP (`rx_exercise_catalog.json`) only has title/video/owner, so the builder must fetch full objects (driver-side at save time) or the dump must be re-taken with full objects.

**Consequence / decision forced:** the approved "custom exercises for the truly-absent few" can't ship as inline. The 690-exercise catalog actually covers the 17 well (Dead Bug→"DeadBug", Med Ball Slam→"Medicine Ball Slam", Suitcase Carry→"Waiter's Carry", KB Swing to Goblet Catch→"Russian KB swing"; only MiniBand Marches + Ab Wheel lack a cousin). Recommended: map ALL movements to nearest catalog + real name in coachNotes ("nearest equivalent + notes"), which makes every doc all-catalog and saves 200. Awaiting Matti's call.

## Doc shape (top-level, from a real captured PUT)
`{id, workoutType:"StructuredStrength", calendarId, prescribedDate:"YYYY-MM-DD", title, instructions, prescribedDurationInSeconds, orderOnDay, blocks:[{id, blockType:"WarmUp"|"Superset"|"Circuit"|"SingleExercise"|"CoolDown", title, coachNotes, isComplete:false, parameters:[], prescriptions:[{id, coachNotes, exercise:<obj>, parameters:[<paramDef>], setSummaryTemplate:"{Reps}", sets:[{id, isComplete:false, setOrigin:"Prescribed", parameterValues:[{id, parameter:"Reps", category:"Reps", prescribedValue, executedValue:null, inputFormat:null}]}]}]}], files:[], snapshot:{totalBlocks, totalPrescriptions, totalSets, completedBlocks:0, completedPrescriptions:0, completedSets:0}}`. All ids except catalog exercise ids are client UUIDs.

## Required code changes
- **WS-C `rx_strength_docs.py`:** custom movements → inline exercise objects (uuid + ownerId 2000301 + title + video from template demo link), NOT `{custom:title}` placeholders. Rep ranges kept verbatim. Per-side/timed → a Reps parameter with a surrogate value (leading number, or "1" for a pure duration/no-count text) + full raw text in coachNotes — NEVER a param-less prescription (see the CORRECTION above: `parameters: []` is a field-error reject, not a valid shape). Catalog exercises → embed the real object (builder can carry a trimmed copy from the catalog dump: id/title/ownerId/videoUrl + a Reps param).
- **WS-D `tp_apply_driver.js`:** DELETE the `ensureCustomExercisesOnce` separate-endpoint logic (was the 405). Strength stage = POST-create shell → PUT full prebuilt doc → (if on a plan) `POST /plans/{planId}/workouts/save`. Keep the `{data,errors}` unwrap (errors is `{}` on success — already fixed, commit 2c5d0ee).
- Auth capture: install the XHR/fetch bearer grabber via `page.addInitScript` BEFORE app load (the app binds `setRequestHeader` early, so a post-load evaluate patch misses it unless a fresh rx call fires after patching — priming a builder works but addInitScript is cleaner).
