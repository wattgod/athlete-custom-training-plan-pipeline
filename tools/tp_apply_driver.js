throw new Error(
  'AUTOMATED TRAININGPEAKS APPLY IS DISABLED FOR PHASE 1. '
  + 'Automated apply returns in Phase 4/5 via the worker. Until then, the coach '
  + 'must apply manually in the TrainingPeaks UI and record APPLIED through the '
  + 'authenticated fulfillment transition with evidence.',
);

/*
 * tp_apply_driver.js — retired Phase 1 TrainingPeaks apply driver (spec D5).
 *
 * Historical implementation retained for Phase 4/5 worker migration evidence.
 * The top-of-file hard exit is the Phase 1 release boundary: this file cannot
 * install applyJob, inspect browser credentials, call a gate, or contact TP.
 */

(function () {
  const TP = 'https://tpapi.trainingpeaks.com';
  const RX = 'https://api.peakswaresb.com';
  const BACK_SQUAT_CATALOG_ID = 131; // known-good id (V2_BUILD_SPEC.md) — used only to probe rx auth
  const sleep = ms => new Promise(r => setTimeout(r, ms));

  // ---- rx bearer capture (in-page XHR intercept; never persisted) --------
  let _rxBearer = null;
  if (!window.__applyDriverXhrPatched) {
    window.__applyDriverXhrPatched = true;
    const origSetHeader = XMLHttpRequest.prototype.setRequestHeader;
    XMLHttpRequest.prototype.setRequestHeader = function (name, value) {
      if (String(name).toLowerCase() === 'authorization' && /^bearer /i.test(String(value))) {
        _rxBearer = value; // in-memory only — never logged, never written to the receipt
      }
      return origSetHeader.apply(this, arguments);
    };
  }

  // ---- receipt -------------------------------------------------------------
  const receipt = (window.__APPLY_RECEIPT__ = window.__APPLY_RECEIPT__ || {
    stage: 'idle', planId: null, planPersonId: null,
    posted: [], rxDone: [], verified: null, applied: null,
    athleteVerified: null, rollback: null, failures: [], finishedAt: null,
  });

  function setStage(stage) { receipt.stage = stage; _backup(); }
  function fail(stage, message, detail) {
    receipt.failures.push({ stage, message: String(message), detail: detail != null ? String(detail).slice(0, 300) : undefined });
  }
  function _backup() {
    try { localStorage.setItem('tp_apply_driver_receipt', JSON.stringify(receipt)); } catch (_) { /* best effort */ }
  }

  function validateJobBinding(job) {
    const required = [
      'order_id', 'athlete_id', 'generation_revision', 'model_seal',
      'release_manifest_digest', 'tp_manifest_sha256',
    ];
    const missing = required.filter(k => job[k] === undefined || job[k] === null || job[k] === '');
    if (missing.length) throw new Error(`APPLY_JOB_BINDING_MISSING: ${missing.join(', ')}`);
    if (job.delivery_platform !== 'trainingpeaks') {
      throw new Error('APPLY_JOB_PLATFORM_MISMATCH: delivery_platform must be trainingpeaks');
    }
    if (!job.gate || !job.gate.url || !job.gate.token) {
      throw new Error('APPLY_JOB_GATE_MISSING: short-lived live gate is required');
    }
  }

  async function checkLiveGate(job) {
    const separator = job.gate.url.includes('?') ? '&' : '?';
    const response = await fetch(
      `${job.gate.url}${separator}token=${encodeURIComponent(job.gate.token)}`,
      { method: 'GET', credentials: 'omit', cache: 'no-store' },
    );
    let body = {};
    try { body = await response.json(); } catch (_) { /* handled below */ }
    if (!response.ok) {
      throw new Error(`APPLY_GATE_REFUSED: ${body.error || `HTTP ${response.status}`}`);
    }
    const required = [
      'order_id', 'athlete_id', 'delivery_platform', 'generation_revision',
      'model_seal', 'release_manifest_digest', 'tp_manifest_sha256',
    ];
    const drift = required.filter(k => body[k] !== job[k]);
    if (drift.length || body.status !== 'APPROVED' || body.legacy
        || !body.seal_verified || !body.release_authorized) {
      throw new Error(`APPLY_GATE_BINDING_MISMATCH: ${drift.join(', ') || 'authority'}`);
    }
  }

  // ---- fetch wrappers --------------------------------------------------
  async function tpFetch(path, opts = {}) {
    const r = await fetch(TP + path, {
      credentials: 'include',
      headers: { 'Content-Type': 'application/json', ...(opts.headers || {}) },
      ...opts,
    });
    if (r.status === 401) { const e = new Error('TP_SESSION_401'); e.is401 = true; throw e; }
    let body = null; try { body = await r.json(); } catch (_) { /* some 200s are empty */ }
    return { status: r.status, ok: r.status === 200 || r.status === 201, body };
  }

  async function rxFetch(path, opts = {}) {
    if (!_rxBearer) {
      throw new Error('RX_NO_BEARER — open a strength builder once in this tab to trigger capture, then retry');
    }
    const r = await fetch(RX + path, {
      headers: { 'Content-Type': 'application/json', Authorization: _rxBearer, ...(opts.headers || {}) },
      ...opts,
    });
    if (r.status === 401) { const e = new Error('RX_SESSION_401'); e.is401 = true; throw e; }
    let body = null; try { body = await r.json(); } catch (_) { /* some 200s are empty */ }
    // Live rx responses are wrapped {data, errors} — unwrap; non-empty errors are a failure.
    const errors = body && body.errors;
    // errors can be [], {}, or a populated array/object — only non-empty means failure
    const hasErrors = !!errors && (Array.isArray(errors) ? errors.length > 0 : Object.keys(errors).length > 0);
    const ok = (r.status === 200 || r.status === 201) && !hasErrors;
    const data = body && typeof body === 'object' && 'data' in body ? body.data : body;
    return { status: r.status, ok, body: data, raw: body };
  }

  // ---- date helpers ------------------------------------------------------
  function addDays(dateStr, n) {
    const d = new Date(dateStr + 'T00:00:00Z');
    d.setUTCDate(d.getUTCDate() + n);
    return d.toISOString().slice(0, 10);
  }
  function addDaysClamped(dateStr, n, maxStr) {
    const candidate = addDays(dateStr, n);
    return candidate < maxStr ? candidate : maxStr;
  }
  function resumeKey(workoutDay, orderOnDay, title) {
    return (workoutDay || '').slice(0, 10) + '|' + (orderOnDay || 0) + '|' + title;
  }

  // ---- Stage 0: duplicate guard ------------------------------------------
  async function stage0DuplicateGuard(job) {
    setStage('duplicate_guard');
    const list = await tpFetch('/plans/v1/plans'); // raw array
    if (!list.ok) throw new Error('duplicate guard: could not list plans: ' + list.status);
    const title = job.duplicate_guard.title;
    const matches = (list.body || []).filter(p => p.title === title);
    if (matches.length > 1) {
      fail('duplicate_guard', `${matches.length} plans already titled ${JSON.stringify(title)} — stop and ask`,
           JSON.stringify(matches.map(m => m.planId)));
      throw new Error('DUPLICATE_GUARD_MULTIPLE');
    }
    if (matches.length === 1) {
      receipt.planId = matches[0].planId;
      receipt.planPersonId = matches[0].planPersonId;
      _backup();
      return { adopted: true };
    }
    return { adopted: false };
  }

  // ---- Stage 1: create or adopt -------------------------------------------
  async function stage1CreateOrAdopt(job, duplicateResult) {
    setStage('create');
    if (duplicateResult.adopted) return;
    const c = await tpFetch('/plans/v1/plans', {
      method: 'POST', body: JSON.stringify({ title: job.plan_title, planType: 0 }),
    });
    if (!c.ok) { fail('create', 'create plan failed', JSON.stringify(c.body)); throw new Error('CREATE_FAILED'); }
    // Record planId/planPersonId BEFORE any workout POST — covers the crash
    // window between TP create and a durable receipt write (sol r2 F2).
    receipt.planId = c.body.planId;
    receipt.planPersonId = c.body.planPersonId;
    _backup();
  }

  // ---- ranged plan-workout reads (chunked; responses are RAW ARRAYS) -----
  async function rangedPlanWorkouts(planId, start, end) {
    const out = []; let cursor = start;
    while (cursor <= end) {
      const chunkEnd = addDaysClamped(cursor, 120, end);
      const r = await tpFetch(`/plans/v1/plans/${planId}/workouts/${cursor}/${chunkEnd}`);
      if (r.ok && Array.isArray(r.body)) out.push(...r.body);
      if (chunkEnd === end) break;
      cursor = addDays(chunkEnd, 1);
    }
    return out;
  }

  function tallyByKind(rows) {
    const counts = { workoutType2: 0, strength: 0, dayOff: 0, total: 0 };
    for (const r of rows) {
      counts.total++;
      if (r.workoutTypeValueId === 9) counts.strength++;
      else if (r.workoutTypeValueId === 7) counts.dayOff++;
      else counts.workoutType2++; // bike + race share workoutTypeValueId 2
    }
    return counts;
  }

  // ---- Stage 2: bike / day-off / race workouts ---------------------------
  async function stage2Workouts(job, { paceMs = 150 } = {}) {
    if (!job.workouts.length) return;
    setStage('workouts');
    const { planId, planPersonId } = receipt;
    const dates = job.workouts.map(w => w.date).sort();
    const start = dates[0], end = dates[dates.length - 1];

    const existingRows = await rangedPlanWorkouts(planId, start, end);
    const have = new Set(existingRows.map(w => resumeKey(w.workoutDay, w.orderOnDay, w.title)));
    const alreadyDone = new Set(
      receipt.posted.filter(p => p.status === 'ok' || p.status === 'skipped' || p.status === 'ok_readback')
                    .map(p => resumeKey(p.date + 'T00:00:00', p.order_on_day, p.title))
    );

    for (const w of job.workouts) {
      const key = resumeKey(w.date + 'T00:00:00', w.order_on_day, w.title);
      if (have.has(key) || alreadyDone.has(key)) {
        receipt.posted.push({ date: w.date, order_on_day: w.order_on_day, title: w.title, status: 'skipped' });
        continue;
      }
      const body = {
        athleteId: planPersonId, planId, title: w.title,
        workoutTypeValueId: w.workoutTypeValueId, workoutDay: w.date + 'T00:00:00',
        totalTimePlanned: w.totalTimePlanned, tssPlanned: w.tssPlanned,
        description: w.description || '',
      };
      if (w.structure) body.structure = w.structure;

      try {
        const r = await tpFetch(`/plans/v1/plans/${planId}/workouts`, { method: 'POST', body: JSON.stringify(body) });
        if (r.ok) {
          receipt.posted.push({ date: w.date, order_on_day: w.order_on_day, title: w.title, status: 'ok' });
        } else {
          // NO blind retry of a non-idempotent POST — classify remote state via readback first.
          const landed = (await rangedPlanWorkouts(planId, w.date, w.date))
            .some(row => resumeKey(row.workoutDay, row.orderOnDay, row.title) === key);
          receipt.posted.push({
            date: w.date, order_on_day: w.order_on_day, title: w.title,
            status: landed ? 'ok_readback' : 'error', detail: JSON.stringify(r.body).slice(0, 200),
          });
          if (!landed) fail('workouts', `post failed and readback did not find it: ${w.date} ${w.title}`, r.status);
        }
      } catch (e) {
        if (e.is401) throw e; // propagate — applyJob() decides resumable-halt policy
        const landed = await rangedPlanWorkouts(planId, w.date, w.date)
          .then(rows => rows.some(row => resumeKey(row.workoutDay, row.orderOnDay, row.title) === key))
          .catch(() => false);
        receipt.posted.push({
          date: w.date, order_on_day: w.order_on_day, title: w.title,
          status: landed ? 'ok_readback' : 'error', detail: e.message,
        });
        if (!landed) fail('workouts', `post errored and readback did not find it: ${w.date} ${w.title}`, e.message);
      }
      await sleep(paceMs);
    }
  }

  // ---- Stage 3: strength via rx -------------------------------------------
  // One-shot authoring (findings doc, 2026-07-17 live probes, ALL-CATALOG
  // final decision): every movement resolves to a real catalog exercise --
  // there is no more inline-custom-exercise concept, and no exercise-
  // fetching call is needed here either (job.strength[i].doc already embeds
  // each exercise's FULL live object, verbatim from
  // tools/rx_exercise_catalog_full.json, built by tools/rx_strength_docs.py).
  // No per-block/per-exercise scaffold calls are required: POST creates a
  // doc shell, then a single PUT/save with the FULL prebuilt doc persists
  // everything in one call.
  async function existingStrengthDoc(planPersonId, date) {
    // Detect an existing same-day strength doc before any retry (sol F8).
    const r = await rxFetch(`/rx/activity/v1/workouts?calendarId=${planPersonId}&date=${date}`);
    if (!r.ok || !r.body) return null;
    const rows = Array.isArray(r.body) ? r.body : [r.body];
    return rows.find(row => row && row.prescribedDate && row.prescribedDate.slice(0, 10) === date) || null;
  }

  // SOLVED 2026-07-17 ("rx plan-attach save call"): POST
  // /rx/activity/v1/plans/{planId}/workouts/save is stricter than the
  // standalone PUT to /workouts -- the shell response from the create POST
  // carries ~30 nullable fields the save needs (lastUpdatedAt,
  // prescribedStartTime, isLocked, workoutSubTypeId, prescribedTss, etc.).
  // Only overlay the authored content onto the shell; the shell owns
  // everything else.
  const STRENGTH_DOC_OVERLAY_KEYS = [
    'blocks', 'title', 'snapshot', 'prescribedDate', 'prescribedDurationInSeconds',
    'workoutType', 'instructions',
  ];
  function mergeDocOntoShell(shell, doc, overrides) {
    const merged = Object.assign({}, shell);
    for (const key of STRENGTH_DOC_OVERLAY_KEYS) {
      if (doc && Object.prototype.hasOwnProperty.call(doc, key)) merged[key] = doc[key];
    }
    return Object.assign(merged, overrides);
  }

  async function applyStrengthDay(s, ctx) {
    const { planId, planPersonId } = ctx;

    // 1. create the doc shell.
    const created = await rxFetch('/rx/activity/v1/workouts', {
      method: 'POST',
      body: JSON.stringify({ date: s.date, calendarId: planPersonId, workoutType: 9, prescribedDate: s.date }),
    });
    if (!created.ok) throw new Error('rx create failed: ' + created.status + ' ' + JSON.stringify(created.raw).slice(0, 200));
    const shell = created.body;
    const docId = shell && shell.id;
    if (docId == null) throw new Error('rx create returned no shell id: ' + JSON.stringify(created.raw).slice(0, 200));

    if (planId) {
      // Plan flow: overlay the authored doc onto the shell, then POST
      // straight to save -- it persists AND attaches to the plan in one
      // call. No intermediate PUT to /workouts for this case.
      const mergedDoc = mergeDocOntoShell(shell, s.doc, {
        id: docId, calendarId: planPersonId, prescribedDate: s.date,
      });
      const saved = await rxFetch(`/rx/activity/v1/plans/${planId}/workouts/save`, {
        method: 'POST', body: JSON.stringify(mergedDoc),
      });
      if (!saved.ok) throw new Error('rx plan workouts/save failed: ' + saved.status + ' ' + JSON.stringify(saved.raw).slice(0, 200));
      return (saved.body && saved.body.id) || docId;
    }

    // Raw-athlete flow (no plan context): the standalone PUT persists
    // directly -- verified live (findings doc, "Strength-doc validity:
    // PROVEN LIVE").
    const finalDoc = Object.assign({}, s.doc, { id: docId, calendarId: planPersonId, prescribedDate: s.date });
    const put = await rxFetch('/rx/activity/v1/workouts', { method: 'PUT', body: JSON.stringify(finalDoc) });
    if (!put.ok) throw new Error('rx PUT failed: ' + put.status + ' ' + JSON.stringify(put.raw).slice(0, 200));
    return (put.body && put.body.id) || docId;
  }

  async function stage3Strength(job, { paceMs = 200 } = {}) {
    if (!job.strength.length) return;
    setStage('strength');
    const { planId, planPersonId } = receipt;

    // Validate rx auth with a GET before any write.
    let probe;
    try {
      probe = await rxFetch(`/rx/activity/v1/exercises/${BACK_SQUAT_CATALOG_ID}`);
    } catch (e) {
      if (e.is401) throw e;
      throw new Error('rx auth validation GET errored: ' + e.message);
    }
    if (!probe.ok) throw new Error('rx auth validation GET failed: ' + probe.status);

    for (const s of job.strength) {
      const dayKey = s.date + '|' + (s.order_on_day || 0);
      if (receipt.rxDone.some(d => d.key === dayKey && (d.status === 'ok' || d.status === 'ok_existing'))) continue;

      if (s.pending_module || !s.doc) {
        receipt.rxDone.push({ key: dayKey, date: s.date, template_key: s.template_key, status: 'skipped_pending_module' });
        continue;
      }
      try {
        const already = await existingStrengthDoc(planPersonId, s.date);
        if (already) {
          receipt.rxDone.push({ key: dayKey, date: s.date, template_key: s.template_key, status: 'ok_existing', docId: already.id });
          continue;
        }
        const docId = await applyStrengthDay(s, { planId, planPersonId });
        receipt.rxDone.push({ key: dayKey, date: s.date, template_key: s.template_key, status: 'ok', docId });
      } catch (e) {
        if (e.is401) throw e; // propagate — applyJob() decides resumable-halt policy
        receipt.rxDone.push({ key: dayKey, date: s.date, template_key: s.template_key, status: 'error', detail: e.message });
        fail('strength', `strength day failed: ${s.date} (${s.template_key})`, e.message);
      }
      await sleep(paceMs);
    }
  }

  // ---- Stage 4: verify plan ------------------------------------------------
  async function stage4VerifyPlan(job) {
    setStage('verify');
    const { planId } = receipt;
    const range = job.verify.date_range;
    const rows = await rangedPlanWorkouts(planId, range.start, range.end);
    const actual = tallyByKind(rows);
    receipt.verified = {
      bike_and_race: actual.workoutType2, strength: actual.strength,
      day_off: actual.dayOff, total: actual.total,
    };
    const expected = job.verify.expected;
    const expectedCombined = {
      bike_and_race: expected.bike + expected.race, strength: expected.strength,
      day_off: expected.day_off, total: expected.total,
    };
    const ok = Object.keys(expectedCombined).every(k => receipt.verified[k] === expectedCombined[k]);
    if (!ok) {
      fail('verify', 'plan verification count mismatch',
          JSON.stringify({ expected: expectedCombined, actual: receipt.verified }));
      throw new Error('VERIFY_MISMATCH');
    }
  }

  // ---- Stage 5: apply plan -> athlete (only if job.apply.enabled) --------
  async function athleteWorkoutsRange(athleteId, start, end) {
    const out = []; let cursor = start;
    while (cursor <= end) {
      const chunkEnd = addDaysClamped(cursor, 120, end);
      const r = await tpFetch(`/fitness/v6/athletes/${athleteId}/workouts/${cursor}/${chunkEnd}`);
      if (r.ok && Array.isArray(r.body)) out.push(...r.body);
      if (chunkEnd === end) break;
      cursor = addDays(chunkEnd, 1);
    }
    return out;
  }

  async function pollApplyPlanStatus(appliedPlanId, { intervalMs = 1500, maxAttempts = 40 } = {}) {
    if (!appliedPlanId) return 'unknown';
    for (let i = 0; i < maxAttempts; i++) {
      const r = await tpFetch('/plans/v1/appliedplans/applyPlanStatus', {
        method: 'POST', body: JSON.stringify([appliedPlanId]),
      });
      const row = r.body && (Array.isArray(r.body) ? r.body[0] : r.body);
      const status = row && (row.status || row.state);
      if (status && /complete|ok|done/i.test(status)) return status;
      if (status && /fail|error/i.test(status)) return status;
      await sleep(intervalMs);
    }
    return 'timeout';
  }

  async function rollbackThisRun(athleteId) {
    // Delete ONLY the workout ids introduced by THIS run — never a range-wipe.
    const ids = (receipt.rollback && receipt.rollback.introducedIds) || [];
    for (const id of ids) {
      try {
        await tpFetch(`/fitness/v6/athletes/${athleteId}/workouts/${id}`, { method: 'DELETE' });
        receipt.rollback.deletedIds.push(id);
      } catch (e) {
        fail('rollback', `failed to delete introduced workout ${id}`, e.message);
      }
      await sleep(120);
    }
    _backup();
  }

  async function stage5ApplyToAthlete(job) {
    if (!job.apply || !job.apply.enabled) return;
    setStage('apply');
    const { planId } = receipt;
    const athleteId = String(job.athlete_tp_id);
    const range = job.rollback.snapshot_range;

    // Snapshot BEFORE applying — old + new coexist briefly, calendar is never empty.
    const before = await athleteWorkoutsRange(athleteId, range.start, range.end);
    receipt.rollback = {
      snapshotRange: range,
      snapshot: before.map(w => ({ id: w.workoutId || w.id, title: w.title, day: (w.workoutDay || '').slice(0, 10) })),
      introducedIds: [], deletedIds: [],
    };
    _backup();

    const applyBody = [{
      athleteId, planId, planTitle: job.plan_title,
      targetDate: job.apply.targetDate, startType: job.apply.startType || 1,
    }];
    const applied = await tpFetch('/plans/v1/commands/applyplan', { method: 'POST', body: JSON.stringify(applyBody) });
    if (!applied.ok) {
      fail('apply', 'applyplan POST failed', JSON.stringify(applied.body).slice(0, 200));
      throw new Error('APPLY_FAILED');
    }
    const row = Array.isArray(applied.body) ? applied.body[0] : applied.body;
    const appliedPlanId = row && row.appliedPlanId;

    const status = await pollApplyPlanStatus(appliedPlanId);
    receipt.applied = { appliedPlanId, athleteId, targetDate: job.apply.targetDate,
                        startType: job.apply.startType || 1, status };
    _backup();
    if (!/complete|ok|done/i.test(String(status))) {
      fail('apply', 'applyPlanStatus did not reach a completed state', status);
      await rollbackThisRun(athleteId);
      throw new Error('APPLY_STATUS_NOT_OK');
    }

    setStage('apply_verify');
    const after = await athleteWorkoutsRange(athleteId, range.start, range.end);
    const beforeIds = new Set(before.map(w => w.workoutId || w.id));
    const introduced = after.filter(w => !beforeIds.has(w.workoutId || w.id));
    receipt.rollback.introducedIds = introduced.map(w => w.workoutId || w.id);
    _backup();

    const actual = tallyByKind(introduced);
    receipt.athleteVerified = {
      bike_and_race: actual.workoutType2, strength: actual.strength,
      day_off: actual.dayOff, total: actual.total,
    };
    const expected = job.verify.expected;
    const expectedCombined = {
      bike_and_race: expected.bike + expected.race, strength: expected.strength,
      day_off: expected.day_off, total: expected.total,
    };
    const ok = Object.keys(expectedCombined).every(k => receipt.athleteVerified[k] === expectedCombined[k]);
    if (!ok) {
      fail('apply_verify', 'athlete calendar verification mismatch',
          JSON.stringify({ expected: expectedCombined, actual: receipt.athleteVerified }));
      await rollbackThisRun(athleteId);
      throw new Error('APPLY_VERIFY_MISMATCH');
    }
  }

  // ---- entrypoint ----------------------------------------------------------
  async function applyJob(job) {
    job = job || window.__APPLY_JOB__;
    if (!job) throw new Error('no job — set window.__APPLY_JOB__ or pass one to applyJob()');
    try {
      validateJobBinding(job);
      setStage('gate');
      await checkLiveGate(job);
      if (!receipt.planId) {
        const dup = await stage0DuplicateGuard(job);
        // Duplicate inspection is read-only and may take time. Re-check at
        // the final boundary immediately before stage 1's first POST.
        setStage('gate');
        await checkLiveGate(job);
        await stage1CreateOrAdopt(job, dup);
      }
      await stage2Workouts(job);
      await stage3Strength(job);
      await stage4VerifyPlan(job);
      await stage5ApplyToAthlete(job);
      setStage('done');
      receipt.finishedAt = new Date().toISOString();
    } catch (e) {
      if (e && e.is401) {
        fail(receipt.stage, 'SESSION_401 — reload the tab, then re-run applyJob(window.__APPLY_JOB__); '
                            + 'resumes from receipt.planId / the localStorage backup.', e.message);
        // finishedAt intentionally left unset: this halt is resumable, not terminal.
      } else {
        setStage('failed');
        receipt.finishedAt = new Date().toISOString();
      }
      _backup();
      throw e;
    }
    _backup();
    return receipt;
  }

  if (typeof window !== 'undefined') {
    window.applyJob = applyJob;
  }
})();
