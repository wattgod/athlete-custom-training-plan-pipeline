/*
 * tp_polyline_repair.js -- browser-context repair pass for wrong "bar-style"
 * TP calendar-tile polylines (see tools/tp_polyline.py's module docstring
 * for the bug and the peak-normalized fix, confirmed against live TP
 * cards on 2026-08-26).
 *
 * Run via Playwriter (or equivalent) inside an already-authenticated
 * app.trainingpeaks.com tab. Requires two globals set BEFORE this script
 * runs:
 *
 *   window.__POLYLINE_LIB__   -- the full SOURCE TEXT of tools/tp_polyline.js
 *                                (read the file, assign its contents as a
 *                                string). This script `eval`s it once to
 *                                define `polyline_from_structure` (the JS
 *                                port defines it as a page/global -- see
 *                                tp_polyline.js's UMD wrapper -- this only
 *                                works in a plain browser tab with no
 *                                CommonJS `module` global shadowing it).
 *
 *   window.__REPAIR_SCOPE__   -- {
 *     layer: "athlete" | "plan",
 *     id:    <athleteId | planId>,
 *     start: "YYYY-MM-DD",
 *     end:   "YYYY-MM-DD",
 *   }
 *
 * Behavior by layer:
 *   athlete -- GET /fitness/v6/athletes/{id}/workouts/{start}/{end}, for
 *     every row with a parseable, non-null structure.structure: recompute
 *     the polyline; if it differs from stored (including stored
 *     empty/bar-style), PUT the FULL row back to
 *     /fitness/v6/athletes/{id}/workouts/{workoutId} with `structure`
 *     JSON.stringify'd (proven shape -- see tools/tp_phase5_browser_payload.js
 *     wireBody()/applyOperation()'s PUT path).
 *
 *   plan -- GET /plans/v1/plans/{id}/workouts/{start}/{end}. There is NO
 *     proven single-item PUT for the plan/container layer (no
 *     `plans/v1/.../workouts/{id}` PUT appears in any captured
 *     apply_plan.js build script). What IS proven there (see each
 *     plan-builds/<athlete>/apply_plan.js, all TP-native July 2026 SKU
 *     builds):
 *       DELETE /plans/v1/plans/{planId}/workouts/{workoutId}   (120ms spacing)
 *       POST   /plans/v1/plans/{planId}/workouts                (120ms spacing)
 *         body = {...workoutContentFields, planId, athleteId: planPersonId}
 *         -- `structure` in this POST body is a plain OBJECT, NOT
 *         JSON.stringify'd (unlike the athlete-layer PUT above; confirmed
 *         against apply_plan.js's own `window.__PLAN_PAYLOAD__` workout
 *         bodies, which are POSTed with `structure` as a nested object).
 *     So for every row whose recomputed polyline differs, this script
 *     DELETEs the old workout, then POSTs a recreation carrying every
 *     other field from the old row verbatim (title, workoutDay,
 *     description, totalTimePlanned, tssPlanned, workoutTypeValueId,
 *     coachComments, etc. -- everything except the old `workoutId`/`id`,
 *     which cannot be reused for a create) plus the corrected structure.
 *     If the DELETE succeeds but the POST fails, that is recorded as a
 *     DATA-LOSS-RISK failure (the workout is gone from TP and NOT
 *     recreated) -- these need a human to reconcile, not a retry.
 *
 * RPE-metric structures (primaryIntensityMetric rpe/perceivedExertion) are
 * skipped -- there is no live-verified RPE polyline convention (see
 * tp_polyline.py's module docstring); they are counted in
 * receipt.skippedRpe, never written.
 *
 * 120ms spacing between writes. Every item is wrapped in its own try/catch
 * -- one bad row never aborts the scan. Final receipt lives in
 * window.__POLYLINE_REPAIR_RECEIPT__:
 *   { scanned, changed, skippedRpe, failed: [{context, message}],
 *     recreated: [{oldId, newId, title, date}] }  // plan layer only
 */
(async () => {
  'use strict';

  const TP = 'https://tpapi.trainingpeaks.com';
  const RECEIPT_GLOBAL = '__POLYLINE_REPAIR_RECEIPT__';
  const WRITE_SPACING_MS = 120;

  const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

  const receipt = (window[RECEIPT_GLOBAL] = {
    scanned: 0, changed: 0, skippedRpe: 0, failed: [], recreated: [],
  });

  function fail(context, message) {
    receipt.failed.push({ context, message: String(message?.message || message) });
  }

  // ---- load the polyline lib ---------------------------------------------
  const LIB_SRC = window.__POLYLINE_LIB__;
  if (typeof LIB_SRC !== 'string' || !LIB_SRC.trim()) {
    throw new Error(
      'POLYLINE_LIB_MISSING -- set window.__POLYLINE_LIB__ to the tools/tp_polyline.js '
      + 'source text before running this script');
  }
  // Indirect eval runs in global scope, so tp_polyline.js's UMD wrapper sees
  // no CommonJS `module` and falls through to defining window.polyline_from_structure.
  (0, eval)(LIB_SRC); // eslint-disable-line no-eval
  const computePolyline = window.polyline_from_structure;
  if (typeof computePolyline !== 'function') {
    throw new Error('POLYLINE_LIB_SHAPE -- eval of __POLYLINE_LIB__ did not define '
      + 'window.polyline_from_structure');
  }

  // ---- scope --------------------------------------------------------------
  const SCOPE = window.__REPAIR_SCOPE__;
  if (!SCOPE || !['athlete', 'plan'].includes(SCOPE.layer)
      || !SCOPE.id || !SCOPE.start || !SCOPE.end) {
    throw new Error(
      'REPAIR_SCOPE_MISSING -- set window.__REPAIR_SCOPE__ = '
      + '{layer: "athlete"|"plan", id, start: "YYYY-MM-DD", end: "YYYY-MM-DD"}');
  }

  // ---- fetch helpers --------------------------------------------------------
  let lastWriteAt = 0;

  async function api(path, opts = {}) {
    const response = await fetch(TP + path, {
      credentials: 'include',
      headers: { 'Content-Type': 'application/json', ...(opts.headers || {}) },
      ...opts,
    });
    if (response.status === 401) throw new Error('TP_SESSION_401');
    let body = null;
    try { body = await response.json(); } catch (_) { /* some 200s/DELETEs are empty */ }
    return { status: response.status, ok: response.status >= 200 && response.status < 300, body };
  }

  async function write(method, path, body) {
    const wait = Math.max(0, WRITE_SPACING_MS - (Date.now() - lastWriteAt));
    if (wait) await sleep(wait);
    const result = await api(path, {
      method, body: body === undefined ? undefined : JSON.stringify(body),
    });
    lastWriteAt = Date.now();
    return result;
  }

  function rowsFrom(value) {
    if (Array.isArray(value)) return value;
    if (value && Array.isArray(value.items)) return value.items;
    if (value && Array.isArray(value.workouts)) return value.workouts;
    return [];
  }

  // structure comes back as either a JSON string (athlete-layer GET) or
  // already-parsed object -- handle both. Returns undefined (distinct from
  // null) when the field is a string that fails to parse.
  function parseStructure(raw) {
    if (raw == null) return null;
    if (typeof raw === 'object') return raw;
    if (typeof raw !== 'string' || !raw.trim()) return null;
    try {
      return JSON.parse(raw);
    } catch (_) {
      return undefined;
    }
  }

  function polylinesEqual(a, b) {
    const pa = Array.isArray(a) ? a : [];
    const pb = Array.isArray(b) ? b : [];
    if (pa.length !== pb.length) return false;
    for (let i = 0; i < pa.length; i += 1) {
      if (pa[i][0] !== pb[i][0] || pa[i][1] !== pb[i][1]) return false;
    }
    return true;
  }

  function isRpeMetric(structureObj) {
    return structureObj.primaryIntensityMetric === 'rpe'
      || structureObj.primaryIntensityMetric === 'perceivedExertion';
  }

  // ---- athlete layer: proven single-item PUT --------------------------------
  async function repairAthleteRow(athleteId, row) {
    receipt.scanned += 1;
    const id = row.workoutId ?? row.id;
    const structureObj = parseStructure(row.structure);
    if (structureObj === undefined) { fail(id ?? row.title, 'STRUCTURE_UNPARSEABLE'); return; }
    if (!structureObj || !structureObj.structure) return; // nothing to repair
    if (isRpeMetric(structureObj)) { receipt.skippedRpe += 1; return; }

    const computed = computePolyline(structureObj);
    if (polylinesEqual(structureObj.polyline, computed)) return;
    if (!id) { fail(row.title || '(untitled)', 'WORKOUT_ID_MISSING'); return; }

    try {
      const corrected = { ...structureObj, polyline: computed };
      const body = { ...row, structure: JSON.stringify(corrected) };
      const result = await write(
        'PUT',
        `/fitness/v6/athletes/${encodeURIComponent(athleteId)}/workouts/${encodeURIComponent(id)}`,
        body,
      );
      if (!result.ok) throw new Error(`PUT_${result.status}`);
      receipt.changed += 1;
    } catch (error) {
      fail(id, error);
    }
  }

  async function repairAthleteScope() {
    const value = await api(
      `/fitness/v6/athletes/${encodeURIComponent(SCOPE.id)}/workouts/${SCOPE.start}/${SCOPE.end}`,
    );
    if (!value.ok) throw new Error(`ATHLETE_WORKOUTS_FETCH_${value.status}`);
    for (const row of rowsFrom(value.body)) {
      // eslint-disable-next-line no-await-in-loop
      await repairAthleteRow(SCOPE.id, row);
    }
  }

  // ---- plan layer: no proven PUT -- DELETE + POST recreate -------------------
  async function repairPlanRow(planId, planPersonId, row) {
    receipt.scanned += 1;
    const oldId = row.workoutId ?? row.id ?? null;
    const structureObj = parseStructure(row.structure);
    if (structureObj === undefined) { fail(oldId ?? row.title, 'STRUCTURE_UNPARSEABLE'); return; }
    if (!structureObj || !structureObj.structure) return; // nothing to repair
    if (isRpeMetric(structureObj)) { receipt.skippedRpe += 1; return; }

    let computed;
    try {
      computed = computePolyline(structureObj);
    } catch (error) { fail(oldId ?? row.title, error); return; }
    if (polylinesEqual(structureObj.polyline, computed)) return;
    if (oldId == null) { fail(row.title || '(untitled)', 'WORKOUT_ID_MISSING'); return; }

    let deleted = false;
    try {
      const del = await write(
        'DELETE', `/plans/v1/plans/${encodeURIComponent(planId)}/workouts/${encodeURIComponent(oldId)}`,
      );
      // 404/405 on the sweep-delete means it's already gone -- treat as
      // success (matches apply_plan.js's sweep-delete convention), anything
      // else non-2xx is a real failure and we must NOT proceed to POST.
      if (!del.ok && del.status !== 404 && del.status !== 405) {
        throw new Error(`DELETE_${del.status}`);
      }
      deleted = true;

      // Preserve every other field from the old row -- only the
      // server-identity fields (workoutId/id) are dropped, since a POST
      // creates a NEW workout and cannot reuse the old id.
      const { workoutId: _wid, id: _id, ...contentFields } = row;
      const corrected = { ...structureObj, polyline: computed };
      const body = {
        ...contentFields,
        structure: corrected, // plan-layer POST expects an object, not a JSON string
        planId: Number(planId),
        athleteId: planPersonId,
      };
      const created = await write(
        'POST', `/plans/v1/plans/${encodeURIComponent(planId)}/workouts`, body,
      );
      if (!created.ok) throw new Error(`POST_${created.status}`);
      const newId = created.body && (created.body.workoutId ?? created.body.id ?? null);
      receipt.changed += 1;
      receipt.recreated.push({
        oldId, newId: newId ?? null, title: row.title || null,
        date: (row.workoutDay || '').slice(0, 10) || null,
      });
    } catch (error) {
      if (deleted) {
        // DATA-LOSS RISK: the old (wrong-polyline) workout is already
        // gone from TP and the recreate did not land. Do not retry --
        // leave this for a human to reconcile from the receipt.
        fail(oldId, `DELETED_BUT_RECREATE_FAILED: ${error?.message || error}`);
      } else {
        fail(oldId, error);
      }
    }
  }

  async function repairPlanScope() {
    const plan = await api(`/plans/v1/plans/${encodeURIComponent(SCOPE.id)}`);
    if (!plan.ok) throw new Error(`PLAN_FETCH_${plan.status}`);
    const planPersonId = plan.body && plan.body.planPersonId;
    if (!planPersonId) throw new Error('PLAN_READ_NO_PERSON_ID');

    const value = await api(
      `/plans/v1/plans/${encodeURIComponent(SCOPE.id)}/workouts/${SCOPE.start}/${SCOPE.end}`,
    );
    if (!value.ok) throw new Error(`PLAN_WORKOUTS_FETCH_${value.status}`);
    for (const row of rowsFrom(value.body)) {
      // eslint-disable-next-line no-await-in-loop
      await repairPlanRow(SCOPE.id, planPersonId, row);
    }
  }

  // ---- run ------------------------------------------------------------------
  try {
    if (SCOPE.layer === 'athlete') {
      await repairAthleteScope();
    } else {
      await repairPlanScope();
    }
  } catch (error) {
    fail('SCOPE', error);
  }

  return receipt;
})();
