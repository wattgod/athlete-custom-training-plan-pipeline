/*
 * Browser half of the canonical Phase 5 Playwright transport.
 *
 * The reviewed Playwright runner supplies window.__TP_SCRIPT_ARGS__ with:
 *   { request: trainingpeaks_playwright_request/v1, script_sha256: <hex> }
 *
 * This file has no credentials. It runs only in an already authenticated
 * app.trainingpeaks.com page, uses the exact contract operations supplied by
 * Phase 5, never retries POST, verifies every effect by provider readback, and
 * leaves a bounded receipt in window.__GG_TP_PHASE5_RECEIPT__ even on failure.
 */

(async () => {
  'use strict';

  const ARGS = window.__TP_SCRIPT_ARGS__ || {};
  const REQUEST = ARGS.request;
  const SCRIPT_SHA = String(ARGS.script_sha256 || '');
  const TP = 'https://tpapi.trainingpeaks.com';
  const RECEIPT_GLOBAL = '__GG_TP_PHASE5_RECEIPT__';
  const RETRY_DELAYS = [800, 2400, 7200];
  let lastWriteAt = 0;

  const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
  const dateOnly = value => String(value || '').slice(0, 10);
  const remoteId = (row, kind) => String(
    kind === 'workout_upsert'
      ? (row.workoutId ?? row.id ?? '')
      : (row.id ?? row.calendarNoteId ?? ''),
  );
  const canonicalJson = value => {
    if (value === null || typeof value !== 'object') return JSON.stringify(value);
    if (Array.isArray(value)) return `[${value.map(canonicalJson).join(',')}]`;
    return `{${Object.keys(value).sort().map(key => (
      `${JSON.stringify(key)}:${canonicalJson(value[key])}`
    )).join(',')}}`;
  };
  const sha256 = async value => {
    const bytes = new TextEncoder().encode(canonicalJson(value));
    const digest = await crypto.subtle.digest('SHA-256', bytes);
    return Array.from(new Uint8Array(digest), byte => (
      byte.toString(16).padStart(2, '0')
    )).join('');
  };

  function assertRequest() {
    if (!REQUEST || REQUEST.request_type !== 'trainingpeaks_playwright_request/v1') {
      throw new Error('REQUEST_SHAPE');
    }
    if (!/^[0-9a-f]{64}$/.test(REQUEST.contract_digest)
        || !/^[0-9a-f]{64}$/.test(SCRIPT_SHA)
        || SCRIPT_SHA !== REQUEST.script_sha256) {
      throw new Error('REQUEST_DIGEST');
    }
    if (!['apply', 'verify', 'rollback'].includes(REQUEST.action)
        || !Array.isArray(REQUEST.operations) || !REQUEST.operations.length
        || !Array.isArray(REQUEST.prior_receipts)) {
      throw new Error('REQUEST_ACTION');
    }
    if (location.origin !== 'https://app.trainingpeaks.com') {
      throw new Error('ORIGIN_BINDING');
    }
    if (String(REQUEST.tp_athlete_id) !== String(
      location.hash.match(/\/athletes\/(\d+)/)?.[1] || '',
    )) {
      throw new Error('ATHLETE_BINDING');
    }
    const ids = REQUEST.operations.map(operation => operation.op_id);
    if (ids.some(id => !id) || new Set(ids).size !== ids.length) {
      throw new Error('OPERATION_IDENTITY');
    }
  }

  async function api(path, opts = {}, expectJson = true) {
    const method = opts.method || 'GET';
    const delays = method === 'POST' ? [] : RETRY_DELAYS;
    let lastError = null;
    for (let attempt = 0; attempt <= delays.length; attempt += 1) {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 30_000);
      try {
        const response = await fetch(TP + path, {
          credentials: 'include',
          headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
          ...opts,
          signal: controller.signal,
        });
        const retryable = response.status === 401 || response.status === 429
          || response.status >= 500;
        if (retryable && attempt < delays.length) {
          await sleep(delays[attempt]);
          continue;
        }
        if (!response.ok) throw new Error(`HTTP_${response.status}`);
        const type = String(response.headers.get('content-type') || '').toLowerCase();
        if (!type.includes('application/json')) {
          if (expectJson) throw new Error('NON_JSON_RESPONSE');
          return null;
        }
        return await response.json();
      } catch (error) {
        lastError = error;
        const transient = error?.name === 'AbortError' || error instanceof TypeError;
        if (!transient || attempt >= delays.length) throw error;
        await sleep(delays[attempt]);
      } finally {
        clearTimeout(timer);
      }
    }
    throw lastError || new Error('REQUEST_FAILED');
  }

  async function mutate(method, path, body, expectJson = false) {
    if (REQUEST.dry_run) return null;
    const wait = Math.max(0, 150 - (Date.now() - lastWriteAt));
    if (wait) await sleep(wait);
    const result = await api(path, {
      method, body: body === undefined ? undefined : JSON.stringify(body),
    }, expectJson);
    lastWriteAt = Date.now();
    return result;
  }

  function rows(value, kind) {
    if (Array.isArray(value)) return value;
    if (value && Array.isArray(value.items)) return value.items;
    if (value && Array.isArray(value.workouts)) return value.workouts;
    if (value && Array.isArray(value.calendarNotes)) return value.calendarNotes;
    throw new Error(`${kind.toUpperCase()}_READ_SHAPE`);
  }

  function operationDate(operation) {
    const payload = operation.payload || operation.prior_payload || {};
    const explicit = dateOnly(payload.date);
    if (/^\d{4}-\d{2}-\d{2}$/.test(explicit)) return explicit;
    return operation.logical_id.match(/\d{4}-\d{2}-\d{2}/)?.[0] || null;
  }

  async function listOperation(operation) {
    const day = operationDate(operation);
    if (!day) throw new Error('OPERATION_DATE_MISSING');
    const athlete = encodeURIComponent(String(REQUEST.tp_athlete_id));
    if (operation.kind === 'workout_upsert') {
      return rows(await api(
        `/fitness/v6/athletes/${athlete}/workouts/${day}/${day}`,
      ), 'workout');
    }
    if (operation.kind === 'calendar_note_upsert') {
      return rows(await api(
        `/fitness/v3/athletes/${athlete}/calendarNote/${day}/${day}`,
      ), 'calendar_note');
    }
    throw new Error('UNSUPPORTED_KIND');
  }

  const marker = operation => `[GG:${operation.remote_marker}]`;
  const withMarker = (text, operation) => {
    const body = String(text || '').replace(/\s+$/u, '');
    return `${body}${body ? '\n\n' : ''}${marker(operation)}`;
  };
  const stripMarker = (text, operation) => String(text || '')
    .replace(new RegExp(`\\n?\\n?${marker(operation).replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}$`), '')
    .replace(/\s+$/u, '');

  function normalized(row, operation) {
    if (operation.kind === 'workout_upsert') {
      const hours = Number(row.totalTimePlanned ?? 0);
      return {
        date: dateOnly(row.workoutDay),
        title: String(row.title || ''),
        description: stripMarker(row.description, operation),
        tp_workout_type: row.workoutTypeValueId ?? null,
        total_seconds: Math.round(hours * 3600),
        tss_planned: row.tssPlanned ?? null,
        structure: row.structure ?? null,
      };
    }
    return {
      date: dateOnly(row.noteDate),
      title: String(row.title || ''),
      body: stripMarker(row.description, operation),
    };
  }

  function projectedBody(payload, operation, current = {}) {
    if (operation.kind === 'workout_upsert') {
      const durationHours = Number(payload.total_seconds || 0) / 3600;
      const tss = payload.tss_planned;
      const computedIf = durationHours > 0 && Number.isFinite(Number(tss))
        ? Math.sqrt(Number(tss) / (durationHours * 100)) : null;
      return {
        ...current,
        athleteId: Number(REQUEST.tp_athlete_id),
        title: payload.title,
        description: withMarker(payload.description, operation),
        workoutTypeValueId: payload.tp_workout_type,
        workoutDay: `${payload.date}T00:00:00`,
        totalTimePlanned: durationHours,
        tssPlanned: tss,
        structure: payload.structure,
        ...(payload.structure && computedIf !== null ? { ifPlanned: computedIf } : {}),
      };
    }
    return {
      ...current,
      athleteId: Number(REQUEST.tp_athlete_id),
      title: payload.title,
      description: withMarker(payload.body, operation),
      noteDate: `${payload.date}T00:00:00`,
    };
  }

  function collectionPath(operation) {
    const athlete = encodeURIComponent(String(REQUEST.tp_athlete_id));
    return operation.kind === 'workout_upsert'
      ? `/fitness/v6/athletes/${athlete}/workouts`
      : `/fitness/v1/athletes/${athlete}/calendarNote`;
  }

  function itemPath(operation, id) {
    return `${collectionPath(operation)}/${encodeURIComponent(String(id))}`;
  }

  function priorReceipt(operation) {
    return REQUEST.prior_receipts.find(row => row.op_id === operation.op_id) || null;
  }

  async function exactRow(operation, id = null) {
    const candidates = await listOperation(operation);
    const matches = id
      ? candidates.filter(row => remoteId(row, operation.kind) === String(id))
      : candidates.filter(row => String(row.description || '').includes(marker(operation)));
    if (matches.length > 1) throw new Error('MULTIPLE_REMOTE_MATCHES');
    return matches[0] || null;
  }

  async function observed(operation, row, payload) {
    const digest = await sha256(normalized(row, operation));
    const expected = await sha256(payload);
    if (digest !== expected) throw new Error('READBACK_DIGEST_MISMATCH');
    return digest;
  }

  async function applyOperation(operation) {
    const disposition = operation.disposition;
    const predecessorId = operation.predecessor?.remote_id || null;
    if (disposition === 'keep') {
      const row = await exactRow(operation, predecessorId);
      if (!row) throw new Error('PROTECTED_ITEM_MISSING');
      const digest = await sha256(normalized(row, operation));
      if (digest !== operation.expected_digest) throw new Error('PROTECTED_ITEM_DRIFT');
      return { op_id: operation.op_id, status: 'kept',
        remote_id: remoteId(row, operation.kind), observed_digest: digest,
        reconciled_after_error: false };
    }
    if (disposition === 'create') {
      const existing = await exactRow(operation);
      if (existing) {
        const digest = await observed(operation, existing, operation.payload);
        return { op_id: operation.op_id, status: 'landed',
          remote_id: remoteId(existing, operation.kind), observed_digest: digest,
          reconciled_after_error: true };
      }
      if (REQUEST.dry_run) return { op_id: operation.op_id, status: 'would_create',
        remote_id: null, observed_digest: operation.expected_digest,
        reconciled_after_error: false };
      let ambiguous = false;
      try {
        await mutate('POST', collectionPath(operation),
          projectedBody(operation.payload, operation), false);
      } catch (error) {
        ambiguous = error?.name === 'AbortError' || error instanceof TypeError;
        if (!ambiguous) throw error;
      }
      const row = await exactRow(operation);
      if (!row) throw new Error(ambiguous ? 'AMBIGUOUS_POST' : 'CREATE_NOT_FOUND');
      const digest = await observed(operation, row, operation.payload);
      return { op_id: operation.op_id, status: 'landed',
        remote_id: remoteId(row, operation.kind), observed_digest: digest,
        reconciled_after_error: ambiguous };
    }
    const targetId = predecessorId || priorReceipt(operation)?.remote_id;
    if (!targetId) throw new Error('PREDECESSOR_REMOTE_ID_MISSING');
    const current = await exactRow(operation, targetId);
    if (disposition === 'delete') {
      if (!current) return { op_id: operation.op_id, status: 'absent',
        remote_id: String(targetId), observed_digest: null,
        reconciled_after_error: true };
      await observed(operation, current, operation.prior_payload);
      if (!REQUEST.dry_run) await mutate('DELETE', itemPath(operation, targetId));
      if (!REQUEST.dry_run && await exactRow(operation, targetId)) {
        throw new Error('DELETE_READBACK_PRESENT');
      }
      return { op_id: operation.op_id,
        status: REQUEST.dry_run ? 'would_delete' : 'absent',
        remote_id: String(targetId), observed_digest: null,
        reconciled_after_error: false };
    }
    if (!current) throw new Error('UPDATE_TARGET_MISSING');
    await observed(operation, current, operation.prior_payload);
    if (!REQUEST.dry_run) {
      await mutate('PUT', itemPath(operation, targetId),
        projectedBody(operation.payload, operation, current));
    }
    const row = REQUEST.dry_run ? current : await exactRow(operation, targetId);
    const digest = REQUEST.dry_run
      ? operation.expected_digest : await observed(operation, row, operation.payload);
    return { op_id: operation.op_id,
      status: REQUEST.dry_run ? 'would_update' : 'landed',
      remote_id: String(targetId), observed_digest: digest,
      reconciled_after_error: false };
  }

  async function verifyOperation(operation) {
    const prior = priorReceipt(operation);
    const id = operation.predecessor?.remote_id || prior?.remote_id || null;
    if (operation.disposition === 'delete') {
      const row = id ? await exactRow(operation, id) : await exactRow(operation);
      if (row) throw new Error('VERIFY_DELETE_PRESENT');
      return { op_id: operation.op_id, status: 'absent', remote_id: id,
        observed_digest: null, reconciled_after_error: false };
    }
    const row = await exactRow(operation, id);
    if (!row) throw new Error('VERIFY_TARGET_MISSING');
    const payload = operation.payload || operation.prior_payload;
    const digest = payload
      ? await observed(operation, row, payload)
      : await sha256(normalized(row, operation));
    if (digest !== operation.expected_digest) throw new Error('VERIFY_DIGEST_MISMATCH');
    return { op_id: operation.op_id,
      status: operation.disposition === 'keep' ? 'kept' : 'landed',
      remote_id: remoteId(row, operation.kind), observed_digest: digest,
      reconciled_after_error: false };
  }

  async function rollbackOperation(operation) {
    const strategy = operation.rollback?.strategy;
    const prior = priorReceipt(operation);
    if (strategy === 'delete_by_remote_id') {
      const id = prior?.remote_id;
      if (!id) throw new Error('ROLLBACK_REMOTE_ID_MISSING');
      const current = await exactRow(operation, id);
      if (current && !REQUEST.dry_run) await mutate('DELETE', itemPath(operation, id));
      if (!REQUEST.dry_run && await exactRow(operation, id)) {
        throw new Error('ROLLBACK_DELETE_PRESENT');
      }
      return { op_id: operation.op_id,
        status: REQUEST.dry_run ? 'would_delete' : 'absent', remote_id: String(id),
        observed_digest: null, reconciled_after_error: !current };
    }
    const payload = operation.prior_payload || operation.before_image;
    if (!payload) throw new Error('ROLLBACK_BEFORE_IMAGE_MISSING');
    if (strategy === 'restore_prior_payload' || strategy === 'restore_before_image') {
      const id = prior?.remote_id || operation.predecessor?.remote_id;
      if (!id) throw new Error('ROLLBACK_REMOTE_ID_MISSING');
      const current = await exactRow(operation, id);
      if (!current) throw new Error('ROLLBACK_TARGET_MISSING');
      if (!REQUEST.dry_run) {
        await mutate('PUT', itemPath(operation, id),
          projectedBody(payload, operation, current));
      }
      const row = REQUEST.dry_run ? current : await exactRow(operation, id);
      const digest = REQUEST.dry_run ? await sha256(payload)
        : await observed(operation, row, payload);
      return { op_id: operation.op_id,
        status: REQUEST.dry_run ? 'would_restore' : 'restored', remote_id: String(id),
        observed_digest: digest, reconciled_after_error: false };
    }
    if (strategy === 'recreate_from_prior_payload') {
      let row = await exactRow(operation);
      if (!row && !REQUEST.dry_run) {
        await mutate('POST', collectionPath(operation),
          projectedBody(payload, operation), false);
        row = await exactRow(operation);
      }
      if (!row && !REQUEST.dry_run) throw new Error('ROLLBACK_RECREATE_MISSING');
      const digest = REQUEST.dry_run ? await sha256(payload)
        : await observed(operation, row, payload);
      return { op_id: operation.op_id,
        status: REQUEST.dry_run ? 'would_restore' : 'restored',
        remote_id: row ? remoteId(row, operation.kind) : prior?.remote_id || null,
        observed_digest: digest, reconciled_after_error: Boolean(row) };
    }
    throw new Error('ROLLBACK_STRATEGY_UNSUPPORTED');
  }

  const receipt = {
    receipt_type: 'trainingpeaks_playwright_receipt/v1',
    contract_digest: REQUEST?.contract_digest || null,
    action: REQUEST?.action || null,
    dry_run: Boolean(REQUEST?.dry_run),
    tp_athlete_id: REQUEST?.tp_athlete_id || null,
    script_sha256: SCRIPT_SHA,
    started_at: new Date().toISOString(), finished_at: null,
    readback_verified: false, rollback_verified: false,
    operations: [], failure: null,
  };

  try {
    assertRequest();
    const selected = REQUEST.action === 'rollback'
      ? REQUEST.operations.filter(operation => operation.disposition !== 'keep')
      : REQUEST.operations;
    for (const operation of selected) {
      try {
        const row = REQUEST.action === 'rollback'
          ? await rollbackOperation(operation)
          : REQUEST.action === 'verify'
            ? await verifyOperation(operation)
            : await applyOperation(operation);
        receipt.operations.push(row);
      } catch (error) {
        receipt.failure = {
          op_id: operation.op_id,
          code: String(error?.message || error).replace(/[^A-Z0-9_]/gi, '_').slice(0, 80),
        };
        break;
      }
    }
    const complete = receipt.operations.length === selected.length && receipt.failure === null;
    if (!REQUEST.dry_run && complete) {
      if (REQUEST.action === 'rollback') receipt.rollback_verified = true;
      else receipt.readback_verified = true;
    }
  } catch (error) {
    receipt.failure = {
      op_id: null,
      code: String(error?.message || error).replace(/[^A-Z0-9_]/gi, '_').slice(0, 80),
    };
  } finally {
    receipt.finished_at = new Date().toISOString();
    window[RECEIPT_GLOBAL] = receipt;
  }
})();
