/*
 * tp_apply_driver.js — transactional TrainingPeaks apply driver (spec D5).
 *
 * Executes a `tp_apply_order.py`-emitted apply_job.json inside a logged-in
 * TrainingPeaks browser tab. Ports gravel-god-training-plans/tools/
 * tp_load_plan.js's proven patterns (athleteId===planPersonId, resumable
 * "day|order|title" keys, paced writes, per-request 401 detection) and
 * extends them with: a duplicate-title guard before create, rx
 * StructuredStrength strength days, a plan->athlete apply stage, and a
 * pre-apply calendar snapshot + this-run-only rollback.
 *
 * RUNTIME: this is a self-contained IIFE. Paste/inject it into the DevTools
 * console (or via playwriter) of a tab logged into app.trainingpeaks.com —
 * it uses the session cookie via credentials:'include' for tpapi calls.
 * rx (StructuredStrength) calls need a bearer token, which this file
 * captures in-page from any rx XHR the app itself fires (patches
 * XMLHttpRequest.setRequestHeader); open a strength builder briefly first
 * if `stage3Strength` reports RX_NO_BEARER. The bearer is NEVER written to
 * the receipt or localStorage.
 *
 * INPUT: window.__APPLY_JOB__ (or pass a job object directly), shaped per
 * tp_apply_order.py's build_apply_job():
 *   { plan_title, athlete_tp_id, duplicate_guard:{title},
 *     workouts:[{date, order_on_day, title, workoutTypeValueId, tssPlanned,
 *                totalTimePlanned, description, structure, race}],
 *     strength:[{date, order_on_day, title, template_key, doc|pending_module}],
 *     custom_exercises:[...], apply:{targetDate, startType, enabled},
 *     verify:{expected:{bike,strength,day_off,race,total}, date_range:{start,end}},
 *     rollback:{snapshot_range:{start,end}} }
 *
 * OUTPUT: window.__APPLY_RECEIPT__, updated continuously (poll-friendly):
 *   { stage, planId, planPersonId, posted:[...], rxDone:[...],
 *     verified:{bike_and_race,strength,day_off,total},
 *     applied:{appliedPlanId,athleteId,targetDate,startType,status}|null,
 *     athleteVerified:{...}|null,
 *     rollback:{snapshotRange,snapshot:[...],introducedIds:[...],deletedIds:[...]}|null,
 *     failures:[{stage,message,detail}], finishedAt: ISOString|null }
 * `finishedAt` is set ONLY on a true terminal outcome (done, or an
 * unrecoverable hard failure). A SESSION_401 halt leaves it unset — that is
 * the resumable signal: reload the tab, then re-run
 *   await applyJob(window.__APPLY_JOB__)
 * and the driver picks up from receipt.planId / the localStorage backup.
 *
 * USAGE:
 *   window.__APPLY_JOB__ = <contents of apply_job.json>;
 *   const receipt = await applyJob(window.__APPLY_JOB__);
 *   // feed window.__APPLY_RECEIPT__ back to:
 *   //   python3 tools/tp_apply_order.py <athlete-id> --package <pkg> --receipt <file>
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
    const hasErrors = Array.isArray(errors) ? errors.length > 0 : !!errors;
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
  // NOTE on the block/prescription scaffold calls: bodies are derived from
  // the captured chain (gravel-god-training-plans/strength_builder/
  // plan_day_capture_netlog.json) — an accumulate/respond protocol (each
  // call sends the current server-accumulated `workout` doc plus a
  // `libraryContent` descriptor of what to add next; the response is the
  // new accumulated doc). This is UNVERIFIED against a live probe for the
  // multi-block/multi-exercise case (spec open item 4) — ship as the
  // documented default, probe-verify before relying on it at scale.
  function blockTypeTitle(blockType) {
    return ({ WarmUp: 'Warm Up', Circuit: 'Circuit', Superset: 'Superset',
             SingleExercise: 'Single Exercise', CoolDown: 'Cool Down' })[blockType] || blockType;
  }

  function resolveExerciseId(exercise, customIds) {
    if (!exercise) return null;
    if (exercise.custom_key && customIds[exercise.custom_key] != null) return customIds[exercise.custom_key];
    return exercise.id;
  }

  function mergeAuthoredDoc(serverDoc, authoredDoc, overrides) {
    const merged = JSON.parse(JSON.stringify(serverDoc));
    if (authoredDoc) {
      if (authoredDoc.title) merged.title = authoredDoc.title;
      if (authoredDoc.instructions != null) merged.instructions = authoredDoc.instructions;
      if (authoredDoc.prescribedTss != null) merged.prescribedTss = authoredDoc.prescribedTss;
      if (authoredDoc.prescribedDurationInSeconds != null) {
        merged.prescribedDurationInSeconds = authoredDoc.prescribedDurationInSeconds;
      }
      (authoredDoc.blocks || []).forEach((authoredBlock, bi) => {
        const serverBlock = merged.blocks && merged.blocks[bi];
        if (!serverBlock) return;
        if (authoredBlock.title != null) serverBlock.title = authoredBlock.title;
        if (authoredBlock.coachNotes != null) serverBlock.coachNotes = authoredBlock.coachNotes;
        (authoredBlock.prescriptions || []).forEach((authoredPrescription, pi) => {
          const serverPrescription = serverBlock.prescriptions && serverBlock.prescriptions[pi];
          if (!serverPrescription) return;
          if (authoredPrescription.coachNotes != null) serverPrescription.coachNotes = authoredPrescription.coachNotes;
          if (Array.isArray(authoredPrescription.parameters)) serverPrescription.parameters = authoredPrescription.parameters;
          if (Array.isArray(authoredPrescription.sets) && Array.isArray(serverPrescription.sets)) {
            authoredPrescription.sets.forEach((authoredSet, si) => {
              const serverSet = serverPrescription.sets[si];
              if (serverSet && Array.isArray(authoredSet.parameterValues)) {
                serverSet.parameterValues = authoredSet.parameterValues;
              }
            });
          }
        });
      });
    }
    return Object.assign(merged, overrides);
  }

  async function ensureCustomExercisesOnce(customExercises) {
    const ids = {};
    if (!customExercises || !customExercises.length) return ids;
    // Verify the exercise doc shape from a GET of an existing catalog exercise first.
    const sample = await rxFetch(`/rx/activity/v1/exercises/${BACK_SQUAT_CATALOG_ID}`);
    if (!sample.ok) throw new Error('rx custom-exercise shape probe failed: ' + sample.status);

    for (const ex of customExercises) {
      const scaffold = await rxFetch('/rx/activity/v1/exercises', { method: 'POST', body: JSON.stringify({}) });
      if (!scaffold.ok) throw new Error('rx custom exercise scaffold failed: ' + scaffold.status);
      const draftId = scaffold.body && scaffold.body.id;
      const put = await rxFetch(`/rx/activity/v1/exercises/${draftId}`, {
        method: 'PUT',
        body: JSON.stringify({
          ...sample.body, id: draftId, title: ex.title,
          videoUrl: ex.videoUrl || null, instructions: ex.instructions || ex.coachNotes || '',
          ownerId: ex.ownerId != null ? ex.ownerId : (sample.body && sample.body.ownerId) || null,
        }),
      });
      if (!put.ok) throw new Error('rx custom exercise PUT failed: ' + put.status);
      ids[ex.key || ex.title] = draftId;
      await sleep(150);
    }
    return ids;
  }

  async function existingStrengthDoc(planPersonId, date) {
    // Detect an existing same-day strength doc before any retry (sol F8).
    const r = await rxFetch(`/rx/activity/v1/workouts?calendarId=${planPersonId}&date=${date}`);
    if (!r.ok || !r.body) return null;
    const rows = Array.isArray(r.body) ? r.body : [r.body];
    return rows.find(row => row && row.prescribedDate && row.prescribedDate.slice(0, 10) === date) || null;
  }

  async function applyStrengthDay(s, ctx) {
    const { planId, planPersonId, customIds } = ctx;

    // 1. create
    const created = await rxFetch('/rx/activity/v1/workouts', {
      method: 'POST',
      body: JSON.stringify({ date: s.date, calendarId: planPersonId, workoutType: 9, prescribedDate: s.date, prescribedStartTime: null }),
    });
    if (!created.ok) throw new Error('rx create failed: ' + created.status + ' ' + JSON.stringify(created.raw).slice(0, 200));
    let doc = created.body;
    const docId = doc && doc.id;

    const targetBlocks = (s.doc && s.doc.blocks) || [];
    for (const targetBlock of targetBlocks) {
      // 2. block scaffold
      const blockAdd = await rxFetch('/rx/activity/v1/workouts/add/libraryContent', {
        method: 'POST',
        body: JSON.stringify({
          workout: doc,
          libraryContent: { blockType: targetBlock.blockType, isDisabled: false,
                            title: targetBlock.title || blockTypeTitle(targetBlock.blockType) },
        }),
      });
      if (!blockAdd.ok) throw new Error('rx block scaffold failed: ' + blockAdd.status + ' ' + JSON.stringify(blockAdd.raw).slice(0, 200));
      doc = blockAdd.body;
      const serverBlock = doc.blocks[doc.blocks.length - 1];

      // 3. per-exercise prescription scaffold
      for (const targetPrescription of (targetBlock.prescriptions || [])) {
        const exercise = targetPrescription.exercise || {};
        const exerciseId = resolveExerciseId(exercise, customIds);
        const defaultPrescriptionId = serverBlock.prescriptions && serverBlock.prescriptions[0] && serverBlock.prescriptions[0].id;
        const prescriptionAdd = await rxFetch('/rx/activity/v1/workouts/blocks/prescriptions/add/libraryContent', {
          method: 'POST',
          body: JSON.stringify({
            workout: doc,
            libraryContent: {
              exerciseId: exerciseId != null ? String(exerciseId) : null,
              canEdit: !!exercise.canEdit, searchText: exercise.searchText || exercise.title || '',
              searchAttributes: exercise.searchAttributes || {}, ownerId: exercise.ownerId || null,
              title: exercise.title || '',
            },
            prescriptionId: defaultPrescriptionId,
          }),
        });
        if (!prescriptionAdd.ok) {
          throw new Error('rx prescription scaffold failed: ' + prescriptionAdd.status + ' ' + JSON.stringify(prescriptionAdd.raw).slice(0, 200));
        }
        doc = prescriptionAdd.body;
      }
    }

    // 4. full StructuredStrength doc (authored content merged onto the
    // server-accumulated doc, which owns the real block/prescription/set ids)
    const finalDoc = mergeAuthoredDoc(doc, s.doc, { calendarId: planPersonId, id: docId, prescribedDate: s.date });
    const put = await rxFetch('/rx/activity/v1/workouts', { method: 'PUT', body: JSON.stringify(finalDoc) });
    if (!put.ok) throw new Error('rx PUT failed: ' + put.status + ' ' + JSON.stringify(put.raw).slice(0, 200));

    // 5. plan workouts/save — the chain's captured final call.
    const saved = await rxFetch(`/rx/activity/v1/plans/${planId}/workouts/save`, {
      method: 'POST', body: JSON.stringify(put.body || finalDoc),
    });
    if (!saved.ok) throw new Error('rx plan workouts/save failed: ' + saved.status + ' ' + JSON.stringify(saved.raw).slice(0, 200));

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

    const customIds = await ensureCustomExercisesOnce(job.custom_exercises || []);

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
        const docId = await applyStrengthDay(s, { planId, planPersonId, customIds });
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
      if (!receipt.planId) {
        const dup = await stage0DuplicateGuard(job);
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
