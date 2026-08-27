#!/usr/bin/env node
/**
 * Golden-reproduction test for tools/tp_polyline.js -- run via `node`.
 *
 * Mirrors tools/test_tp_polyline.py: tools/tp_polyline.js must byte-match
 * tools/tp_polyline.py's output, which itself thin-wraps
 * athletes/scripts/tp_polyline.py::compute_polyline (the single source of
 * truth, PEAK-normalized -- see tp_polyline.js's module docstring for the
 * 2026-08-26 live-evidence correction). Draws on the same
 * athletes/scripts/tp_polyline_golden.json vectors the Python test uses.
 * Plain assert-and-exit script (no test framework) so it runs anywhere
 * `node` runs.
 */
'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const { polyline_from_structure } = require('./tp_polyline.js');

const ROOT = path.resolve(__dirname, '..');
const UNDERLYING_GOLDEN = JSON.parse(fs.readFileSync(
  path.join(ROOT, 'athletes', 'scripts', 'tp_polyline_golden.json'), 'utf8'));

function asStructureObj(blocks) {
  return { primaryIntensityMetric: 'percentOfFtp', structure: blocks };
}

let passed = 0;

function test(name, fn) {
  try {
    fn();
    passed += 1;
    console.log(`ok - ${name}`);
  } catch (err) {
    console.error(`FAIL - ${name}`);
    console.error(err);
    process.exitCode = 1;
  }
}

// ------------------------------------------------------------- golden case
// 100-peak reference: peak intensity here IS 100, so flat-/100 and
// peak-normalization agree -- this is why it "still passes" across the
// algorithm correction.
const GOLDEN_STRUCTURE = {
  primaryIntensityMetric: 'percentOfFtp',
  structure: [
    { type: 'step', length: { value: 1, unit: 'repetition' },
      steps: [{ name: 'Warm up', length: { value: 1200, unit: 'second' },
                targets: [{ minValue: 50, maxValue: 70 }], intensityClass: 'warmUp' }] },
    { type: 'step', length: { value: 1, unit: 'repetition' },
      steps: [{ name: 'Active', length: { value: 360, unit: 'second' },
                targets: [{ minValue: 100 }], intensityClass: 'active' }] },
    { type: 'step', length: { value: 1, unit: 'repetition' },
      steps: [{ name: 'Rest', length: { value: 240, unit: 'second' },
                targets: [{ minValue: 55 }], intensityClass: 'rest' }] },
    { type: 'step', length: { value: 1, unit: 'repetition' },
      steps: [{ name: 'Active', length: { value: 360, unit: 'second' },
                targets: [{ minValue: 100 }], intensityClass: 'active' }] },
    { type: 'step', length: { value: 1, unit: 'repetition' },
      steps: [{ name: 'Rest', length: { value: 240, unit: 'second' },
                targets: [{ minValue: 55 }], intensityClass: 'rest' }] },
    { type: 'step', length: { value: 1, unit: 'repetition' },
      steps: [{ name: 'Cool down', length: { value: 600, unit: 'second' },
                targets: [{ minValue: 50 }], intensityClass: 'coolDown' }] },
  ],
};
const GOLDEN_POLYLINE = [
  [0, 0], [0, 0.7], [0.4, 0.7], [0.4, 1], [0.52, 1], [0.52, 0.55],
  [0.6, 0.55], [0.6, 1], [0.72, 1], [0.72, 0.55], [0.8, 0.55],
  [0.8, 0.5], [1, 0.5], [1, 0],
];

test('100-peak reference reproduces exactly', () => {
  assert.deepStrictEqual(polyline_from_structure(GOLDEN_STRUCTURE), GOLDEN_POLYLINE);
});

// ---------------------------------------------------------- sub-100 peak
// The correction this course-change exists to fix: TP normalizes to the
// workout's own peak, not a flat /100. warmup 50-60% (600s), steady 65%
// (900s), cooldown 50% (300s) -- peak is 65, so the steady step must
// normalize to y == 1.0.
test('sub-100 peak normalizes to 1.0, not raw percent', () => {
  const structure = asStructureObj([
    { length: { value: 1, unit: 'repetition' },
      steps: [{ length: { value: 600, unit: 'second' }, targets: [{ minValue: 50, maxValue: 60 }] }] },
    { length: { value: 1, unit: 'repetition' },
      steps: [{ length: { value: 900, unit: 'second' }, targets: [{ minValue: 65 }] }] },
    { length: { value: 1, unit: 'repetition' },
      steps: [{ length: { value: 300, unit: 'second' }, targets: [{ minValue: 50 }] }] },
  ]);
  const computed = polyline_from_structure(structure);
  assert.strictEqual(Math.max(...computed.map((p) => p[1])), 1);
  assert.deepStrictEqual(computed, [
    [0, 0], [0, 0.923], [0.333, 0.923], [0.333, 1],
    [0.833, 1], [0.833, 0.769], [1, 0.769], [1, 0],
  ]);
});

// ------------------------------------------- underlying-module golden cases
test('every underlying golden case reproduces through the wrapper', () => {
  Object.keys(UNDERLYING_GOLDEN.inputs).forEach((name) => {
    const expected = UNDERLYING_GOLDEN.expected[name];
    const got = polyline_from_structure(asStructureObj(UNDERLYING_GOLDEN.inputs[name]));
    assert.deepStrictEqual(got, expected, `drift on ${name}`);
  });
});

test('repetition block unrolls via vo2_intervals_unrolled case', () => {
  const blocks = UNDERLYING_GOLDEN.inputs.vo2_intervals_unrolled;
  const computed = polyline_from_structure(asStructureObj(blocks));
  assert.deepStrictEqual(computed[0], [0, 0]);
  assert.deepStrictEqual(computed[computed.length - 1], [1, 0]);
  assert.strictEqual(Math.max(...computed.map((p) => p[1])), 1.0);
});

test('adjacent equal-y boundaries are not collapsed', () => {
  const blocks = UNDERLYING_GOLDEN.inputs.vo2_intervals_unrolled;
  const computed = polyline_from_structure(asStructureObj(blocks));
  const dupCount = computed.filter((p) => p[0] === 0.667 && p[1] === 0.4).length;
  assert.strictEqual(dupCount, 2);
});

// --------------------------------------------------------------------- RPE
test('rpe metric returns empty polyline', () => {
  const structure = Object.assign({}, GOLDEN_STRUCTURE, { primaryIntensityMetric: 'rpe' });
  assert.deepStrictEqual(polyline_from_structure(structure), []);
});

test('perceivedExertion metric returns empty polyline', () => {
  const structure = Object.assign({}, GOLDEN_STRUCTURE, { primaryIntensityMetric: 'perceivedExertion' });
  assert.deepStrictEqual(polyline_from_structure(structure), []);
});

// --------------------------------------------------------------- degenerate
test('degenerate inputs return empty', () => {
  assert.deepStrictEqual(polyline_from_structure(null), []);
  assert.deepStrictEqual(polyline_from_structure(undefined), []);
  assert.deepStrictEqual(polyline_from_structure({}), []);
  assert.deepStrictEqual(polyline_from_structure({ primaryIntensityMetric: 'percentOfFtp' }), []);
  assert.deepStrictEqual(
    polyline_from_structure({ primaryIntensityMetric: 'percentOfFtp', structure: [] }), []);
});

test('zero total duration delegates to underlying flat line, not []', () => {
  const structure = asStructureObj([
    { length: { value: 1, unit: 'repetition' },
      steps: [{ length: { value: 0, unit: 'second' }, targets: [{ minValue: 50 }] }] },
  ]);
  assert.deepStrictEqual(polyline_from_structure(structure), [[0, 0], [1, 0]]);
});

console.log(`\n${passed} passed`);
if (process.exitCode) {
  console.error('test_tp_polyline.node.js: FAILURES ABOVE');
} else {
  console.log('test_tp_polyline.node.js: all green');
}
