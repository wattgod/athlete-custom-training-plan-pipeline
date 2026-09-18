#!/usr/bin/env node
/**
 * Tests for tools/tp_weekly_packet.js -- run via `node`.
 *
 * No network: buildWeeklyPacket() is exercised end-to-end against a mocked
 * `fetchJson`, and the pure helpers (window bucketing, note flattening,
 * PMC gap-filling) are also exercised directly. Plain assert-and-exit
 * script (no test framework), matching tools/test_tp_polyline.node.js.
 */
'use strict';

const assert = require('assert');
const {
  computeWindows,
  mapSettings,
  mapEvents,
  mapPmcDaily,
  mapWorkouts,
  mapComment,
  flattenNotes,
  buildSourceManifest,
  buildWeeklyPacket,
  addDays,
} = require('./tp_weekly_packet.js');

let passed = 0;
const pending = [];

function test(name, fn) {
  let result;
  try {
    result = fn();
  } catch (err) {
    console.error(`FAIL - ${name}`);
    console.error(err);
    process.exitCode = 1;
    return;
  }
  if (result && typeof result.then === 'function') {
    pending.push(result.then(
      () => { passed += 1; console.log(`ok - ${name}`); },
      (err) => { console.error(`FAIL - ${name}`); console.error(err); process.exitCode = 1; },
    ));
    return;
  }
  passed += 1;
  console.log(`ok - ${name}`);
}

// ------------------------------------------------------------ computeWindows

test('computeWindows derives all five windows from as_of and since', () => {
  const windows = computeWindows('2026-09-18', '2026-09-01');
  assert.deepStrictEqual(windows, {
    asOf: '2026-09-18',
    events: { start: '2026-09-18', end: '2027-03-17' },
    pmc: { start: '2026-08-07', end: '2026-09-17' },
    workouts: { start: '2026-08-07', end: '2026-10-02' },
    notes: { start: '2026-09-01', end: '2026-10-02' },
  });
});

test('addDays crosses month/year boundaries correctly (UTC, not local)', () => {
  assert.strictEqual(addDays('2026-12-31', 1), '2027-01-01');
  assert.strictEqual(addDays('2026-03-01', -1), '2026-02-28');
});

// ------------------------------------------------------------------ mapSettings

test('mapSettings pulls ftp/weight and passes thresholds through raw', () => {
  const raw = {
    powerZones: [{ threshold: 255 }, { threshold: 100 }],
    heartRateZones: [{ threshold: 148, maximumHeartRate: 200 }],
    weight: 68.5,
  };
  assert.deepStrictEqual(mapSettings(raw), {
    ftp_watts: 255,
    weight_kg: 68.5,
    thresholds: { powerZones: raw.powerZones, heartRateZones: raw.heartRateZones },
  });
});

test('mapSettings tolerates a missing/empty settings response', () => {
  assert.deepStrictEqual(mapSettings(null), {
    ftp_watts: null, weight_kg: null, thresholds: { powerZones: [], heartRateZones: [] },
  });
});

// --------------------------------------------------------------------- mapEvents

test('mapEvents maps fields and drops rows outside the window', () => {
  const raw = {
    events: [
      { id: 1, eventDate: '2026-09-20', name: 'Shawangunk Grit', atpPriority: 'A' },
      { eventId: 2, eventDate: '2027-06-01', name: 'Too far out' },
    ],
  };
  assert.deepStrictEqual(mapEvents(raw, '2026-09-18', '2026-12-01'), [
    { id: '1', date: '2026-09-20', name: 'Shawangunk Grit', priority: 'A' },
  ]);
});

test('mapEvents accepts a bare array payload', () => {
  const raw = [{ id: 5, eventDate: '2026-09-19', name: 'B race' }];
  assert.deepStrictEqual(mapEvents(raw, '2026-09-18', '2026-09-30'), [
    { id: '5', date: '2026-09-19', name: 'B race', priority: null },
  ]);
});

// ------------------------------------------------------------------- mapPmcDaily

test('mapPmcDaily fills every day in the window, gaps as null rows', () => {
  const raw = { data: [{ date: '2026-09-16', ctl: 55.1, atl: 60.2, tsb: -5.1, tssActual: 80, tssPlanned: 75 }] };
  const out = mapPmcDaily(raw, '2026-09-15', '2026-09-17');
  assert.strictEqual(out.length, 3);
  assert.deepStrictEqual(out[0], {
    date: '2026-09-15', ctl: null, atl: null, tsb: null, tss_actual: null, tss_planned: null,
  });
  assert.deepStrictEqual(out[1], {
    date: '2026-09-16', ctl: 55.1, atl: 60.2, tsb: -5.1, tss_actual: 80, tss_planned: 75,
  });
  assert.deepStrictEqual(out[2], {
    date: '2026-09-17', ctl: null, atl: null, tsb: null, tss_actual: null, tss_planned: null,
  });
});

// -------------------------------------------------------------------- mapWorkouts

test('mapWorkouts maps fields, sorts by date, drops rows outside the window', () => {
  const raw = {
    workouts: [
      { workoutId: 'w2', workoutDay: '2026-09-19T00:00:00', title: 'Threshold', workoutTypeValueId: 2, totalTimePlanned: 1.5, tssPlanned: 90 },
      { workoutId: 'w1', workoutDay: '2026-09-18T00:00:00', title: 'Endurance', workoutTypeValueId: 2, totalTimePlanned: 2, tssActual: 110, ifActual: 0.68 },
      { workoutId: 'w0', workoutDay: '2026-01-01T00:00:00', title: 'Too old' },
    ],
  };
  assert.deepStrictEqual(mapWorkouts(raw, '2026-09-18', '2026-09-30'), [
    {
      workout_id: 'w1', date: '2026-09-18', title: 'Endurance', type_id: 2,
      dur_planned_h: 2, dur_actual_h: null, tss_planned: null, tss_actual: 110,
      if_actual: 0.68, np: null,
    },
    {
      workout_id: 'w2', date: '2026-09-19', title: 'Threshold', type_id: 2,
      dur_planned_h: 1.5, dur_actual_h: null, tss_planned: 90, tss_actual: null,
      if_actual: null, np: null,
    },
  ]);
});

// ------------------------------------------------------------------ mapComment

test('mapComment maps id/date/author/text with fallback field names', () => {
  assert.deepStrictEqual(
    mapComment({ commentId: 'c1', createdDate: '2026-09-17T10:00:00', displayName: 'Matti', comment: 'Nice work.' }),
    { id: 'c1', date: '2026-09-17', author: 'Matti', text: 'Nice work.' },
  );
});

// ----------------------------------------------------------------- flattenNotes

test('flattenNotes merges per-note comments and drops notes outside the window', () => {
  const notesRaw = {
    calendarNotes: [
      { id: 'n1', noteDate: '2026-09-15', title: 'Week 1', description: 'Go easy.' },
      { id: 'n2', noteDate: '2026-01-01', title: 'Too old', description: 'x' },
    ],
  };
  const commentsByNoteId = {
    n1: { comments: [{ id: 'c1', date: '2026-09-16', author: 'Forest', text: 'Felt good.' }] },
  };
  assert.deepStrictEqual(flattenNotes(notesRaw, '2026-09-01', '2026-09-30', commentsByNoteId), [
    {
      note_id: 'n1', date: '2026-09-15', title: 'Week 1', description: 'Go easy.',
      comments: [{ id: 'c1', date: '2026-09-16', author: 'Forest', text: 'Felt good.' }],
    },
  ]);
});

test('flattenNotes defaults comments to [] when the comments fetch was empty/204', () => {
  const notesRaw = { calendarNotes: [{ id: 'n1', noteDate: '2026-09-15', title: 'Week 1', description: 'x' }] };
  assert.deepStrictEqual(flattenNotes(notesRaw, '2026-09-01', '2026-09-30', { n1: null }), [
    { note_id: 'n1', date: '2026-09-15', title: 'Week 1', description: 'x', comments: [] },
  ]);
});

// ------------------------------------------------------------- buildSourceManifest

test('buildSourceManifest carries captured_at and one entry per endpoint call', () => {
  assert.deepStrictEqual(
    buildSourceManifest('2026-09-18T12:00:00.000Z', [
      { path: '/a', status: 200 }, { path: '/b', status: 'error: timeout' },
    ]),
    {
      captured_at: '2026-09-18T12:00:00.000Z',
      endpoints: [{ path: '/a', status: 200 }, { path: '/b', status: 'error: timeout' }],
    },
  );
});

// ----------------------------------------------------------- buildWeeklyPacket

function mockFetchJson(routes) {
  const calls = [];
  return {
    calls,
    fetchJson(path) {
      calls.push(path);
      const match = Object.keys(routes).find((prefix) => path.indexOf(prefix) === 0);
      if (!match) return Promise.resolve({ ok: true, status: 200, body: null });
      const route = routes[match];
      if (route instanceof Error) return Promise.reject(route);
      return Promise.resolve(route);
    },
  };
}

test('buildWeeklyPacket assembles the full schema against a mocked fetch', () => {
  const athleteId = '999001';
  const routes = {
    [`/fitness/v1/athletes/${athleteId}/settings`]: {
      ok: true, status: 200,
      body: { powerZones: [{ threshold: 240 }], heartRateZones: [], weight: 70 },
    },
    [`/fitness/v6/athletes/${athleteId}/events/`]: {
      ok: true, status: 200,
      body: { events: [{ id: '1', eventDate: '2026-09-20', name: 'Race', atpPriority: 'A' }] },
    },
    [`/fitness/v1/athletes/${athleteId}/reporting/performancedata/`]: {
      ok: true, status: 200,
      body: { data: [{ date: '2026-09-17', ctl: 50, atl: 55, tsb: -5, tssActual: 60, tssPlanned: 60 }] },
    },
    [`/fitness/v6/athletes/${athleteId}/workouts/`]: {
      ok: true, status: 200,
      body: { workouts: [{ workoutId: 'w1', workoutDay: '2026-09-18', title: 'Endurance', totalTimePlanned: 2, tssPlanned: 60 }] },
    },
    [`/fitness/v3/athletes/${athleteId}/calendarNote/`]: {
      ok: true, status: 200,
      body: { calendarNotes: [{ id: 'n1', noteDate: '2026-09-15', title: 'Week', description: 'Go.' }] },
    },
    [`/fitness/v1/athletes/${athleteId}/calendarNote/n1/comments`]: { ok: true, status: 204, body: null },
  };
  const mock = mockFetchJson(routes);
  return buildWeeklyPacket(
    { athleteId, athleteKey: 'example', since: '2026-09-01', asOf: '2026-09-18' },
    { fetchJson: mock.fetchJson, nowIso: () => '2026-09-18T12:00:00.000Z' },
  ).then((packet) => {
    assert.strictEqual(packet.schema, 'weekly_packet/v1');
    assert.strictEqual(packet.athlete_key, 'example');
    assert.strictEqual(packet.tp_athlete_id, athleteId);
    assert.strictEqual(packet.as_of, '2026-09-18');
    assert.strictEqual(packet.settings.ftp_watts, 240);
    assert.strictEqual(packet.events.length, 1);
    assert.strictEqual(packet.pmc_daily.length, 42);
    assert.strictEqual(packet.workouts.length, 1);
    assert.strictEqual(packet.notes.length, 1);
    assert.deepStrictEqual(packet.notes[0].comments, []);
    assert.strictEqual(packet.source_manifest.captured_at, '2026-09-18T12:00:00.000Z');
    // 5 primary calls + 1 per-note comments call
    assert.strictEqual(packet.source_manifest.endpoints.length, 6);
    assert.ok(mock.calls.some((path) => path.indexOf('/calendarNote/n1/comments') !== -1));
  });
});

test('buildWeeklyPacket records a transport failure in source_manifest instead of throwing', () => {
  const athleteId = '999002';
  const routes = {
    [`/fitness/v1/athletes/${athleteId}/settings`]: new Error('network down'),
    [`/fitness/v6/athletes/${athleteId}/events/`]: { ok: true, status: 200, body: { events: [] } },
    [`/fitness/v1/athletes/${athleteId}/reporting/performancedata/`]: { ok: false, status: 500, body: null },
    [`/fitness/v6/athletes/${athleteId}/workouts/`]: { ok: true, status: 200, body: { workouts: [] } },
    [`/fitness/v3/athletes/${athleteId}/calendarNote/`]: { ok: true, status: 200, body: { calendarNotes: [] } },
  };
  const mock = mockFetchJson(routes);
  return buildWeeklyPacket(
    { athleteId, athleteKey: 'example', since: '2026-09-01', asOf: '2026-09-18' },
    { fetchJson: mock.fetchJson, nowIso: () => '2026-09-18T12:00:00.000Z' },
  ).then((packet) => {
    assert.deepStrictEqual(packet.settings, { ftp_watts: null, weight_kg: null, thresholds: { powerZones: [], heartRateZones: [] } });
    const settingsEntry = packet.source_manifest.endpoints.find(
      (entry) => entry.path.indexOf('/settings') !== -1,
    );
    assert.ok(String(settingsEntry.status).indexOf('error: network down') !== -1);
    const pmcEntry = packet.source_manifest.endpoints.find(
      (entry) => entry.path.indexOf('/reporting/performancedata/') !== -1,
    );
    assert.strictEqual(pmcEntry.status, 500);
    assert.strictEqual(packet.pmc_daily.length, 42);
    assert.strictEqual(packet.pmc_daily[0].ctl, null);
  });
});

Promise.all(pending).then(() => {
  console.log(`\n${passed} passed`);
  if (process.exitCode) {
    console.error('test_tp_weekly_packet.node.js: FAILURES ABOVE');
  } else {
    console.log('test_tp_weekly_packet.node.js: all green');
  }
});
