/**
 * Compute the TrainingPeaks calendar-tile power-profile polyline.
 *
 * Faithful JS port of tools/tp_polyline.py, which itself thin-wraps
 * athletes/scripts/tp_polyline.py::compute_polyline -- the vendored SINGLE
 * SOURCE OF TRUTH for TP's calendar-tile polyline (reverse-engineered from
 * Matti's working OG TrainingPeaks workouts, vendored byte-identically into
 * gravel-god-training-plans/tools/tp_polyline.py too).
 *
 * TP PEAK-NORMALIZES y: `y = intensity / workout's own peak intensity`, NOT
 * a flat `intensity / 100`. Confirmed 2026-08-26 against four live
 * TP-native ZWO-imported cards on athlete 33194 with max targets of
 * 58/60/64/65% FTP -- every one carries polyline maxY == 1.0.
 *
 * The core algorithm (unroll repetition blocks -> flatten to (duration,
 * intensity) leaves -> peak = max(intensities, 1) -> per-leaf
 * [t_begin,y],[t_end,y] point pairs, x/y rounded to 3 decimals) must
 * byte-match tools/tp_polyline.py's output on every golden case -- see
 * test_tp_polyline.node.js and test_tp_polyline.py (both draw on
 * athletes/scripts/tp_polyline_golden.json). It does NOT collapse adjacent
 * equal-y step boundaries -- redundant identical-coordinate points are
 * intentionally part of the single source of truth's golden-pinned output
 * (e.g. its vo2_intervals_unrolled case).
 *
 * Standalone (no dependencies) so it can be eval'd directly into a browser
 * page by tools/tp_polyline_repair.js (loaded as the
 * `window.__POLYLINE_LIB__` source), or required as a Node module for
 * test_tp_polyline.node.js. Exposes `polyline_from_structure` -- same
 * function name as the Python port -- as both a CommonJS export and a
 * browser global.
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    root.polyline_from_structure = factory().polyline_from_structure;
  }
}(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  var CADENCE_UNIT = 'roundOrStridePerMinute'; // unused by the core algorithm --
  // kept only as documentation: the core, like its Python/vendored
  // reference, reads targets[0] unconditionally (the established repo
  // convention: index 0 is always the primary %FTP target, index 1+ is
  // the secondary cadence target) and does not defensively filter it.
  var RPE_METRICS = { rpe: true, perceivedExertion: true };

  function round3(n) {
    return Math.round(n * 1000) / 1000;
  }

  // ---- core: byte-for-byte port of compute_polyline(structure_blocks) ----
  function computePolyline(blocks) {
    var flat = [];
    for (var b = 0; b < blocks.length; b++) {
      var block = blocks[b];
      var length = block.length || {};
      var inner = block.steps || [];
      if (length.unit === 'repetition') {
        var reps = parseInt(length.value != null ? length.value : 1, 10);
        for (var r = 0; r < reps; r++) {
          for (var s = 0; s < inner.length; s++) flat.push(inner[s]);
        }
      } else {
        for (var s2 = 0; s2 < inner.length; s2++) flat.push(inner[s2]);
      }
    }

    var durations = [];
    var intensities = [];
    for (var i = 0; i < flat.length; i++) {
      var step = flat[i];
      durations.push((step.length && step.length.value) || 0);
      var t0 = (step.targets && step.targets[0]) || {};
      var maxv = t0.maxValue;
      intensities.push(maxv != null ? maxv : (t0.minValue != null ? t0.minValue : 0));
    }

    var total = 0;
    for (var d = 0; d < durations.length; d++) total += durations[d];

    var peak = 1;
    for (var p = 0; p < intensities.length; p++) {
      if (intensities[p] > peak) peak = intensities[p];
    }

    var polyline = [[0, 0]];
    if (total > 0) {
      var cum = 0.0;
      var emittedX = 0.0;
      for (var k = 0; k < durations.length; k++) {
        var dur = durations[k];
        var intensity = intensities[k];
        var y = round3(intensity / peak);
        var tBegin = Math.max(emittedX, Math.min(1.0, round3(cum)));
        cum += dur / total;
        var tEnd = Math.max(tBegin, Math.min(1.0, round3(cum)));
        polyline.push([tBegin, y]);
        polyline.push([tEnd, y]);
        emittedX = tEnd;
      }
    }
    polyline.push([1, 0]);
    return polyline;
  }

  /**
   * @param {Object|null} structureObj - {"structure": [...blocks...],
   *   "primaryIntensityMetric": ...} -- the same shape carried on a
   *   session / plan-payload entry's `structure` field.
   * @returns {Array<[number, number]>}
   */
  function polyline_from_structure(structureObj) { // eslint-disable-line camelcase
    if (!structureObj) return [];

    var metric = structureObj.primaryIntensityMetric;
    if (RPE_METRICS[metric]) return [];

    var blocks = structureObj.structure || [];
    if (!blocks.length) return [];

    return computePolyline(blocks);
  }

  return { polyline_from_structure: polyline_from_structure }; // eslint-disable-line camelcase
}));
