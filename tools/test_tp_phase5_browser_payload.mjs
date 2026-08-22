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

function marker(logicalId) {
  return `[GG:${logicalId}]`;
}

const rpeStructure = {
  primaryIntensityMetric: 'rpe',
  primaryLengthMetric: 'duration',
  structure: [{ type: 'step', length: { value: 600, unit: 'second' },
    targets: [{ minValue: 2, maxValue: 3 }] }],
};
const hrStructure = {
  primaryIntensityMetric: 'percentOfThresholdHr',
  primaryLengthMetric: 'duration',
  structure: [{ type: 'step', length: { value: 900, unit: 'second' },
    targets: [{ minValue: 70, maxValue: 80 }] }],
};

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
    description: `${payload.description}\n\n${marker(logicalId)}`,
    workoutTypeValueId: payload.tp_workout_type,
    workoutDay: `${payload.date}T00:00:00`,
    totalTimePlanned: payload.total_seconds / 3600,
    tssPlanned: payload.tss_planned,
    structure: payload.structure,
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
  return {
    request_type: 'trainingpeaks_playwright_request/v1',
    contract_digest: 'a'.repeat(64), action, dry_run: false,
    order_id: order, tp_athlete_id: '1522591', generation_revision: 1,
    model_seal: 'b'.repeat(64), script_sha256: scriptSha,
    operations, prior_receipts: priorReceipts,
  };
}

function jsonResponse(value, status = 200) {
  return new Response(JSON.stringify(value), {
    status, headers: { 'Content-Type': 'application/json' },
  });
}

async function runPayload(browserRequest, initialRows, { ambiguousCreate = false } = {}) {
  const workouts = initialRows.map(row => structuredClone(row));
  const calls = [];
  let createdId = 1;
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
    calls.push({ method, pathname });
    const parts = pathname.split('/').filter(Boolean);
    if (method === 'GET') {
      const start = parts.at(-2);
      const end = parts.at(-1);
      return jsonResponse(workouts.filter(row => {
        const day = String(row.workoutDay).slice(0, 10);
        return day >= start && day <= end;
      }));
    }
    if (method === 'POST') {
      const body = JSON.parse(options.body);
      const row = { ...body, workoutId: `created-${createdId++}` };
      workouts.push(row);
      if (ambiguousCreate) throw new TypeError('simulated connection loss after commit');
      return jsonResponse(row, 201);
    }
    const id = decodeURIComponent(parts.at(-1));
    const index = workouts.findIndex(row => String(row.workoutId) === id);
    if (method === 'PUT') {
      assert.notEqual(index, -1);
      workouts[index] = { ...JSON.parse(options.body), workoutId: id };
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
assert.equal(applied.calls.filter(call => call.method === 'POST').length, 1);

const priorReceipts = applied.receipt.operations;
const rolledBack = await runPayload(
  request('rollback', priorReceipts), applied.workouts);
assert.equal(rolledBack.receipt.failure, null);
assert.equal(rolledBack.receipt.rollback_verified, true);
assert.deepEqual(rolledBack.receipt.operations.map(row => row.status), [
  'absent', 'restored', 'restored',
]);
assert.equal(rolledBack.workouts.some(row => (
  String(row.description).includes(marker(createLogical))
)), false);
assert.equal(rolledBack.workouts.find(row => row.workoutId === 'update-1')
  .structure.primaryIntensityMetric, 'rpe');
assert.equal(rolledBack.workouts.some(row => (
  String(row.description).includes(marker(deleteLogical))
)), true);
assert.equal(rolledBack.workouts.find(row => row.workoutId === 'protected-1').title,
  protectedPayload.title);

console.log('tp_phase5_browser_payload: ok');
