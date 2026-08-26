#!/usr/bin/env node

import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFile } from 'node:fs/promises';


const source = await readFile(new URL('./tp_phase5_browser_payload.js', import.meta.url), 'utf8');
const scriptSha = createHash('sha256').update(source).digest('hex');

function canonical(value) {
  if (value === null || typeof value !== 'object') return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(canonical).join(',')}]`;
  return `{${Object.keys(value).sort().map(key => (
    `${JSON.stringify(key)}:${canonical(value[key])}`
  )).join(',')}}`;
}

function digest(value) {
  return createHash('sha256').update(canonical(value)).digest('hex');
}

function singleStepStructure(metric, seconds, low, high) {
  return {
    primaryIntensityMetric: metric,
    primaryLengthMetric: 'duration',
    primaryIntensityTargetOrRange: 'range',
    importedFromZwo: false,
    polyline: [],
    structure: [{
      type: 'step',
      length: { value: 1, unit: 'repetition' },
      steps: [{
        name: 'Steady State',
        length: { value: seconds, unit: 'second' },
        targets: [{ minValue: low, maxValue: high }],
        intensityClass: 'active',
        openDuration: false,
      }],
      begin: 0,
      end: seconds,
    }],
  };
}

const rpeStructure = singleStepStructure('rpe', 600, 2, 3);
const hrStructure = singleStepStructure('percentOfThresholdHr', 900, 70, 80);

function workoutPayload(date, title, description, structure, seconds = 1800, tss = 20) {
  return {
    date, title, description, tp_workout_type: 2,
    total_seconds: seconds, tss_planned: tss, structure,
  };
}

function remoteWorkout(id, logicalId, payload) {
  return {
    workoutId: id,
    athleteId: 1522591,
    title: payload.title,
    description: payload.description,
    workoutTypeValueId: payload.tp_workout_type,
    workoutDay: `${payload.date}T00:00:00`,
    totalTimePlanned: payload.total_seconds / 3600,
    tssPlanned: payload.tss_planned,
    structure: payload.structure,
    ifPlanned: null,
    serverOwned: 'preserve-me',
  };
}

const order = 'canary_cheesehead';
const protectedLogical = `${order}:workout_upsert:2026-10-01#1`;
const createLogical = `${order}:workout_upsert:2026-10-05#1`;
const updateLogical = `${order}:workout_upsert:2026-10-06#1`;
const deleteLogical = `${order}:workout_upsert:2026-10-07#1`;
const protectedPayload = workoutPayload(
  '2026-10-01', 'Protected calendar item', 'Must not change', rpeStructure);
const createPayload = workoutPayload(
  '2026-10-05', 'Phase 5 RPE canary', 'RPE round trip', rpeStructure);
const updateBefore = workoutPayload(
  '2026-10-06', 'Phase 5 metric canary', 'Before update', rpeStructure);
const updateAfter = workoutPayload(
  '2026-10-06', 'Phase 5 metric canary', 'After update', hrStructure, 2400, 32);
const deleteBefore = workoutPayload(
  '2026-10-07', 'Phase 5 delete canary', 'Delete only this marker', rpeStructure);

const operations = [
  {
    op_id: `${protectedLogical}@r1`, logical_id: protectedLogical,
    kind: 'workout_upsert', disposition: 'keep', payload: null,
    expected_digest: digest(protectedPayload), prior_payload: null,
    remote_marker: protectedLogical,
    predecessor: { op_id: `${protectedLogical}@r0`, remote_id: 'protected-1' },
    rollback: { strategy: 'none' },
  },
  {
    op_id: `${createLogical}@r1`, logical_id: createLogical,
    kind: 'workout_upsert', disposition: 'create', payload: createPayload,
    expected_digest: digest(createPayload), prior_payload: null,
    remote_marker: createLogical, predecessor: null,
    rollback: { strategy: 'delete_by_remote_id' },
  },
  {
    op_id: `${updateLogical}@r1`, logical_id: updateLogical,
    kind: 'workout_upsert', disposition: 'update', payload: updateAfter,
    expected_digest: digest(updateAfter), prior_payload: updateBefore,
    remote_marker: updateLogical,
    predecessor: { op_id: `${updateLogical}@r0`, remote_id: 'update-1' },
    rollback: { strategy: 'restore_prior_payload' },
  },
  {
    op_id: `${deleteLogical}@r1`, logical_id: deleteLogical,
    kind: 'workout_upsert', disposition: 'delete', payload: null,
    expected_digest: null, prior_payload: deleteBefore,
    remote_marker: deleteLogical,
    predecessor: { op_id: `${deleteLogical}@r0`, remote_id: 'delete-1' },
    rollback: { strategy: 'recreate_from_prior_payload' },
  },
];

function request(action = 'apply', priorReceipts = []) {
  const selectedOperations = action === 'rollback'
    ? priorReceipts.map(row => operations.find(operation => operation.op_id === row.op_id))
    : operations;
  return {
    request_type: 'trainingpeaks_playwright_request/v1',
    contract_digest: 'a'.repeat(64), action, dry_run: false,
    order_id: order, tp_athlete_id: '1522591', generation_revision: 1,
    model_seal: 'b'.repeat(64), script_sha256: scriptSha,
    operations: selectedOperations, prior_receipts: priorReceipts,
  };
}

function jsonResponse(value, status = 200) {
  return new Response(JSON.stringify(value), {
    status, headers: { 'Content-Type': 'application/json' },
  });
}

async function runPayload(browserRequest, initialRows, {
  ambiguousCreate = false, nextCreatedId = 1,
} = {}) {
  const workouts = initialRows.map(row => structuredClone(row));
  const calls = [];
  let createdId = nextCreatedId;
  globalThis.window = globalThis;
  globalThis.location = {
    origin: 'https://app.trainingpeaks.com',
    hash: '#calendar/athletes/1522591',
  };
  globalThis.__TP_SCRIPT_ARGS__ = { request: browserRequest, script_sha256: scriptSha };
  delete globalThis.__GG_TP_PHASE5_RECEIPT__;
  globalThis.fetch = async (url, options = {}) => {
    const method = options.method || 'GET';
    const pathname = new URL(url).pathname;
    const requestBody = options.body === undefined ? undefined : JSON.parse(options.body);
    calls.push({ method, pathname, body: requestBody });
    const parts = pathname.split('/').filter(Boolean);
    if (method === 'GET') {
      const itemMatch = pathname.match(
        /^\/fitness\/v6\/athletes\/1522591\/workouts\/([^/]+)$/,
      );
      if (itemMatch) {
        const id = decodeURIComponent(itemMatch[1]);
        const row = workouts.find(candidate => String(candidate.workoutId) === id);
        return row ? jsonResponse(row) : jsonResponse({ error: 'not found' }, 404);
      }
      assert.match(pathname,
        /^\/fitness\/v7\/athletes\/1522591\/workouts\/\d{4}-\d{2}-\d{2}\/\d{4}-\d{2}-\d{2}$/);
      const start = parts.at(-2);
      const end = parts.at(-1);
      return jsonResponse(workouts.filter(row => {
        const day = String(row.workoutDay).slice(0, 10);
        return day >= start && day <= end;
      }));
    }
    if (method === 'POST') {
      assert.equal(pathname, '/fitness/v6/athletes/1522591/workouts');
      assert.equal(requestBody.workoutId, 0);
      assert.equal(typeof requestBody.structure, 'string');
      const row = {
        ...requestBody,
        workoutId: `created-${createdId++}`,
        structure: JSON.parse(requestBody.structure),
        serverOwned: 'preserve-me',
      };
      workouts.push(row);
      if (ambiguousCreate) throw new TypeError('simulated connection loss after commit');
      return jsonResponse(row, 201);
    }
    const id = decodeURIComponent(parts.at(-1));
    const index = workouts.findIndex(row => String(row.workoutId) === id);
    if (method === 'PUT') {
      assert.notEqual(index, -1);
      assert.equal(calls.some(call => (
        call.method === 'GET' && call.pathname === pathname
      )), true);
      assert.equal(requestBody.serverOwned, 'preserve-me');
      assert.equal(typeof requestBody.structure, 'string');
      workouts[index] = {
        ...requestBody,
        workoutId: id,
        structure: JSON.parse(requestBody.structure),
      };
      return jsonResponse(workouts[index]);
    }
    if (method === 'DELETE') {
      if (index !== -1) workouts.splice(index, 1);
      return jsonResponse({ ok: true });
    }
    throw new Error(`unexpected ${method} ${pathname}`);
  };

  const execution = (0, eval)(source);
  if (execution && typeof execution.then === 'function') await execution;
  return { receipt: globalThis.__GG_TP_PHASE5_RECEIPT__, workouts, calls };
}

const initial = [
  remoteWorkout('protected-1', protectedLogical, protectedPayload),
  remoteWorkout('update-1', updateLogical, updateBefore),
  remoteWorkout('delete-1', deleteLogical, deleteBefore),
];
const dryRequest = request();
dryRequest.dry_run = true;
const dryRun = await runPayload(dryRequest, initial);
assert.equal(dryRun.receipt.failure, null);
assert.equal(dryRun.receipt.dry_run, true);
assert.equal(dryRun.receipt.readback_verified, false);
assert.deepEqual(dryRun.receipt.operations.map(row => row.status), [
  'kept', 'would_create', 'would_update', 'would_delete',
]);
assert.equal(dryRun.calls.some(call => call.method !== 'GET'), false);
assert.deepEqual(dryRun.workouts, initial);

const applied = await runPayload(request(), initial, { ambiguousCreate: true });
assert.equal(applied.receipt.failure, null);
assert.equal(applied.receipt.readback_verified, true);
assert.equal(applied.receipt.rollback_verified, false);
assert.deepEqual(applied.receipt.operations.map(row => row.status), [
  'kept', 'landed', 'landed', 'absent',
]);
assert.equal(applied.receipt.operations[1].reconciled_after_error, true);
assert.equal(applied.workouts.find(row => row.workoutId === 'protected-1').title,
  protectedPayload.title);
assert.equal(applied.workouts.some(row => row.workoutId === 'delete-1'), false);
assert.equal(applied.workouts.find(row => row.workoutId === 'update-1')
  .structure.primaryIntensityMetric, 'percentOfThresholdHr');
assert.equal(applied.workouts.find(row => row.workoutId === 'update-1').ifPlanned, null);
assert.equal(applied.workouts.find(row => row.workoutId === 'update-1').serverOwned,
  'preserve-me');
assert.equal(applied.calls.filter(call => call.method === 'POST').length, 1);
assert.equal(applied.calls.filter(call => (
  call.method === 'GET' && call.pathname === '/fitness/v6/athletes/1522591/workouts/update-1'
)).length, 1);
assert.equal(applied.calls.filter(call => (
  call.method === 'GET' && call.pathname.includes('/workouts/2026-')
)).every(call => call.pathname.startsWith('/fitness/v7/')), true);
const createCall = applied.calls.find(call => call.method === 'POST');
assert.equal(createCall.body.workoutId, 0);
assert.equal(typeof createCall.body.structure, 'string');
assert.deepEqual(JSON.parse(createCall.body.structure), rpeStructure);
assert.equal('ifPlanned' in createCall.body, false);
assert.equal(createCall.body.description, createPayload.description);
assert.equal(applied.workouts.some(row => String(row.description).includes('[GG:')), false);

const resumedApply = await runPayload(request('apply', applied.receipt.operations), applied.workouts);
assert.equal(resumedApply.receipt.failure, null);
assert.equal(resumedApply.receipt.readback_verified, true);
assert.equal(resumedApply.calls.some(call => call.method !== 'GET'), false);

const priorReceipts = applied.receipt.operations.filter(row => (
  operations.find(operation => operation.op_id === row.op_id)?.disposition !== 'keep'
)).reverse();
const rolledBack = await runPayload(
  request('rollback', priorReceipts), applied.workouts, { nextCreatedId: 100 });
assert.equal(rolledBack.receipt.failure, null);
assert.equal(rolledBack.receipt.rollback_verified, true);
assert.deepEqual(rolledBack.receipt.operations.map(row => row.status), [
  'restored', 'restored', 'absent',
]);
assert.equal(rolledBack.workouts.some(row => (
  String(row.description).includes('[GG:')
)), false);
assert.equal(rolledBack.workouts.find(row => row.workoutId === 'update-1')
  .structure.primaryIntensityMetric, 'rpe');
assert.equal(rolledBack.workouts.find(row => row.workoutId === 'created-100').description,
  deleteBefore.description);
assert.equal(rolledBack.workouts.find(row => row.workoutId === 'protected-1').title,
  protectedPayload.title);
assert.equal(rolledBack.receipt.operations[0].remote_id, 'created-100');

const rollbackRetry = await runPayload(
  request('rollback', priorReceipts), rolledBack.workouts, { nextCreatedId: 200 });
assert.equal(rollbackRetry.receipt.failure, null);
assert.equal(rollbackRetry.receipt.rollback_verified, true);
assert.equal(rollbackRetry.calls.some(call => call.method !== 'GET'), false);
assert.equal(rollbackRetry.receipt.operations[0].remote_id, 'created-100');

const editedAfterApply = applied.workouts.map(row => (
  row.workoutId === applied.receipt.operations[1].remote_id
    ? { ...row, description: `${row.description}\nAthlete edit after apply` }
    : row
));
const createTarget = [applied.receipt.operations[1]];
const conflict = await runPayload(
  request('rollback', createTarget), editedAfterApply);
assert.equal(conflict.receipt.rollback_verified, false);
assert.equal(conflict.receipt.operations.length, 0);
assert.equal(conflict.receipt.failure.code, 'ROLLBACK_CONFLICT');
assert.equal(conflict.calls.some(call => call.method === 'DELETE'), false);
assert.equal(conflict.workouts.some(row => (
  String(row.description).includes('Athlete edit after apply')
)), true);

console.log('tp_phase5_browser_payload: ok');
