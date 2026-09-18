/**
 * Build a `weekly_packet/v1` object (schema: docs/WEEKLY_PACKET.md) from
 * TrainingPeaks read-only reads.
 *
 * READ-ONLY. Every call is a GET except the PMC report call, which is a POST
 * that only reads a computed report (see docs/WEEKLY_PACKET.md, "Endpoint
 * proof"). This file never writes to an athlete calendar, a plan, or a note.
 *
 * Two run modes, same file:
 *  - Browser (Playwriter): reads `window.__PACKET_ARGS__ =
 *    {athleteId, athleteKey, since, asOf?}`, runs `buildWeeklyPacket()`
 *    against the real `fetch` (with `credentials:'include'`, required for
 *    tpapi.trainingpeaks.com cross-origin cookies — see the
 *    tp-dynamic-plan-builder skill's transport gotchas), and writes the
 *    result to `window.__WEEKLY_PACKET__`. It never embeds athlete ids in
 *    this file.
 *  - Node (tests): `require('./tp_weekly_packet.js')` exposes the pure
 *    helpers and `buildWeeklyPacket(args, deps)` with an injectable
 *    `fetchJson`, so tools/test_tp_weekly_packet.node.js can run the whole
 *    orchestrator against a mocked fetch with no network.
 *
 * See docs/WEEKLY_PACKET.md for field-by-field provenance, including which
 * endpoints and response field names are proven vs. this executor's best
 * guess (PMC row fields and the workouts `workoutComments` shape are NOT
 * independently proven — see that doc before trusting them against a live
 * response).
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    root.tp_weekly_packet = factory(); // eslint-disable-line camelcase
  }
}(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  var TP_BASE = 'https://tpapi.trainingpeaks.com';
  var SCHEMA = 'weekly_packet/v1';
  var DAY_MS = 24 * 60 * 60 * 1000;

  // ------------------------------------------------------------- date math

  function parseIsoDate(value) {
    // Parse a YYYY-MM-DD string as a UTC midnight Date, never local time --
    // local-time parsing of a date-only string is a classic off-by-one-day
    // trap at DST boundaries.
    var parts = String(value).slice(0, 10).split('-').map(Number);
    return new Date(Date.UTC(parts[0], parts[1] - 1, parts[2]));
  }

  function formatIsoDate(date) {
    return date.toISOString().slice(0, 10);
  }

  function addDays(isoDate, days) {
    return formatIsoDate(new Date(parseIsoDate(isoDate).getTime() + days * DAY_MS));
  }

  function todayIsoUtc() {
    return formatIsoDate(new Date());
  }

  /**
   * Compute the five date windows the schema pins to `as_of`. Pure and
   * exported for direct unit testing -- see docs/WEEKLY_PACKET.md, "Date
   * windows" for the rationale of each boundary.
   */
  function computeWindows(asOf, since) {
    return {
      asOf: asOf,
      events: { start: asOf, end: addDays(asOf, 180) },
      pmc: { start: addDays(asOf, -42), end: addDays(asOf, -1) },
      workouts: { start: addDays(asOf, -42), end: addDays(asOf, 14) },
      notes: { start: since, end: addDays(asOf, 14) },
    };
  }

  // ------------------------------------------------------------ row mapping

  function dateOnly(value) {
    return String(value == null ? '' : value).slice(0, 10);
  }

  function firstDefined() {
    for (var i = 0; i < arguments.length; i++) {
      if (arguments[i] !== undefined && arguments[i] !== null) return arguments[i];
    }
    return null;
  }

  function inWindow(isoDate, start, end) {
    return isoDate >= start && isoDate <= end;
  }

  function rowsFrom(payload, names) {
    if (Array.isArray(payload)) return payload;
    for (var i = 0; i < names.length; i++) {
      if (payload && Array.isArray(payload[names[i]])) return payload[names[i]];
    }
    return [];
  }

  /** GET /fitness/v1/athletes/{id}/settings -> settings{ftp_watts, weight_kg, thresholds}. */
  function mapSettings(raw) {
    var powerZones = (raw && raw.powerZones) || [];
    var heartRateZones = (raw && raw.heartRateZones) || [];
    return {
      ftp_watts: firstDefined(powerZones[0] && powerZones[0].threshold),
      weight_kg: firstDefined(raw && raw.weight),
      thresholds: { powerZones: powerZones, heartRateZones: heartRateZones },
    };
  }

  /** GET /fitness/v6/athletes/{id}/events/{start}/{end} -> events[]. */
  function mapEvents(payload, start, end) {
    return rowsFrom(payload, ['items', 'events'])
      .map(function (row) {
        return {
          id: String(firstDefined(row.id, row.eventId, '')),
          date: dateOnly(row.eventDate),
          name: String(firstDefined(row.name, '')),
          priority: firstDefined(row.atpPriority),
        };
      })
      .filter(function (row) { return inWindow(row.date, start, end); })
      .sort(function (a, b) { return a.date.localeCompare(b.date) || a.id.localeCompare(b.id); });
  }

  /**
   * POST .../reporting/performancedata/{start}/{end} -> pmc_daily[].
   * One row per calendar day in [start, end], gaps filled with nulls rather
   * than dropped (a missing day is meaningful to a reviewer, not noise).
   * Field-name guesses are UNVERIFIED -- see docs/WEEKLY_PACKET.md.
   */
  function mapPmcDaily(payload, start, end) {
    var rows = rowsFrom(payload, ['items', 'performanceData', 'data']);
    var byDate = {};
    rows.forEach(function (row) {
      var date = dateOnly(firstDefined(row.date, row.workoutDay, row.day));
      if (!date) return;
      byDate[date] = {
        date: date,
        ctl: firstDefined(row.ctl, row.CTL),
        atl: firstDefined(row.atl, row.ATL),
        tsb: firstDefined(row.tsb, row.TSB),
        tss_actual: firstDefined(row.tssActual, row.tss_actual),
        tss_planned: firstDefined(row.tssPlanned, row.tss_planned),
      };
    });
    var out = [];
    var cursor = start;
    while (cursor <= end) {
      out.push(byDate[cursor] || {
        date: cursor, ctl: null, atl: null, tsb: null, tss_actual: null, tss_planned: null,
      });
      cursor = addDays(cursor, 1);
    }
    return out;
  }

  /** GET /fitness/v6/athletes/{id}/workouts/{start}/{end} -> workouts[]. */
  function mapWorkouts(payload, start, end) {
    return rowsFrom(payload, ['items', 'workouts'])
      .map(function (row) {
        return {
          workout_id: String(firstDefined(row.workoutId, row.id, '')),
          date: dateOnly(row.workoutDay),
          title: String(firstDefined(row.title, '')),
          type_id: firstDefined(row.workoutTypeValueId),
          dur_planned_h: firstDefined(row.totalTimePlanned),
          dur_actual_h: firstDefined(row.totalTimeActual),
          tss_planned: firstDefined(row.tssPlanned),
          tss_actual: firstDefined(row.tssActual),
          if_actual: firstDefined(row.ifActual, row.IF),
          np: firstDefined(row.normalizedPowerActual, row.np),
        };
      })
      .filter(function (row) { return inWindow(row.date, start, end); })
      .sort(function (a, b) { return a.date.localeCompare(b.date) || a.workout_id.localeCompare(b.workout_id); });
  }

  /** One comment row -> the schema's nested {id,date,author,text}. */
  function mapComment(row) {
    return {
      id: String(firstDefined(row.id, row.commentId, '')),
      date: dateOnly(firstDefined(row.date, row.commentDate, row.createdDate)),
      author: String(firstDefined(row.author, row.personName, row.displayName, '')),
      text: String(firstDefined(row.text, row.comment, row.content, '')),
    };
  }

  /**
   * GET /fitness/v3/athletes/{id}/calendarNote/{start}/{end} rows, plus a
   * per-note comments payload keyed by note id (204/missing -> []) ->
   * notes[]. `commentsByNoteId` values are raw comment-endpoint payloads or
   * null; this stays a pure mapper so it is unit-testable without a fetch.
   */
  function flattenNotes(payload, start, end, commentsByNoteId) {
    commentsByNoteId = commentsByNoteId || {};
    return rowsFrom(payload, ['items', 'calendarNotes'])
      .map(function (row) {
        var noteId = String(firstDefined(row.id, row.calendarNoteId, ''));
        var rawComments = commentsByNoteId[noteId];
        var comments = rawComments
          ? rowsFrom(rawComments, ['items', 'comments']).map(mapComment)
          : [];
        return {
          note_id: noteId,
          date: dateOnly(row.noteDate),
          title: String(firstDefined(row.title, '')),
          description: String(firstDefined(row.description, '')),
          comments: comments,
        };
      })
      .filter(function (row) { return inWindow(row.date, start, end); })
      .sort(function (a, b) { return a.date.localeCompare(b.date) || a.note_id.localeCompare(b.note_id); });
  }

  function buildSourceManifest(capturedAt, endpointResults) {
    return {
      captured_at: capturedAt,
      endpoints: endpointResults.map(function (entry) {
        return { path: entry.path, status: entry.status };
      }),
    };
  }

  // -------------------------------------------------------- orchestration

  /**
   * @param {Object} args {athleteId, athleteKey, since, asOf?}
   * @param {Object} deps {fetchJson(path, options?) -> Promise<any>,
   *   nowIso?: () => string} -- inject a mock in tests; the browser driver
   *   below supplies a real one bound to tpapi.trainingpeaks.com.
   * @returns {Promise<Object>} a weekly_packet/v1 object.
   */
  function buildWeeklyPacket(args, deps) {
    var athleteId = String(args.athleteId);
    var athleteKey = String(args.athleteKey);
    var since = String(args.since);
    var asOf = args.asOf ? String(args.asOf) : todayIsoUtc();
    var windows = computeWindows(asOf, since);
    var capturedAt = (deps.nowIso || function () { return new Date().toISOString(); })();
    var endpointResults = [];

    function call(path, options) {
      return deps.fetchJson(path, options).then(
        function (result) {
          endpointResults.push({ path: path, status: result.status });
          return result.ok ? result.body : null;
        },
        function (err) {
          endpointResults.push({ path: path, status: 'error: ' + (err && err.message ? err.message : String(err)) });
          return null;
        },
      );
    }

    var settingsPath = '/fitness/v1/athletes/' + athleteId + '/settings';
    var eventsPath = '/fitness/v6/athletes/' + athleteId + '/events/' + windows.events.start + '/' + windows.events.end;
    var pmcPath = '/fitness/v1/athletes/' + athleteId + '/reporting/performancedata/' + windows.pmc.start + '/' + windows.pmc.end;
    var workoutsPath = '/fitness/v6/athletes/' + athleteId + '/workouts/' + windows.workouts.start + '/' + windows.workouts.end;
    var notesPath = '/fitness/v3/athletes/' + athleteId + '/calendarNote/' + windows.notes.start + '/' + windows.notes.end;

    return Promise.all([
      call(settingsPath),
      call(eventsPath),
      call(pmcPath, {
        method: 'POST',
        body: { atlConstant: 7, atlStartValue: 0, ctlConstant: 42, ctlStartValue: 0, workoutTypes: [] },
      }),
      call(workoutsPath),
      call(notesPath),
    ]).then(function (results) {
      var settingsRaw = results[0];
      var eventsRaw = results[1];
      var pmcRaw = results[2];
      var workoutsRaw = results[3];
      var notesRaw = results[4];

      var noteRows = rowsFrom(notesRaw, ['items', 'calendarNotes']);
      return Promise.all(noteRows.map(function (row) {
        var noteId = String(firstDefined(row.id, row.calendarNoteId, ''));
        if (!noteId) return Promise.resolve([noteId, null]);
        var commentsPath = '/fitness/v1/athletes/' + athleteId + '/calendarNote/' + noteId + '/comments';
        return call(commentsPath).then(function (body) { return [noteId, body]; });
      })).then(function (pairs) {
        var commentsByNoteId = {};
        pairs.forEach(function (pair) { commentsByNoteId[pair[0]] = pair[1]; });

        return {
          schema: SCHEMA,
          athlete_key: athleteKey,
          tp_athlete_id: athleteId,
          as_of: asOf,
          settings: mapSettings(settingsRaw),
          events: mapEvents(eventsRaw, windows.events.start, windows.events.end),
          pmc_daily: mapPmcDaily(pmcRaw, windows.pmc.start, windows.pmc.end),
          workouts: mapWorkouts(workoutsRaw, windows.workouts.start, windows.workouts.end),
          notes: flattenNotes(notesRaw, windows.notes.start, windows.notes.end, commentsByNoteId),
          source_manifest: buildSourceManifest(capturedAt, endpointResults),
        };
      });
    });
  }

  var api = {
    computeWindows: computeWindows,
    mapSettings: mapSettings,
    mapEvents: mapEvents,
    mapPmcDaily: mapPmcDaily,
    mapWorkouts: mapWorkouts,
    mapComment: mapComment,
    flattenNotes: flattenNotes,
    buildSourceManifest: buildSourceManifest,
    buildWeeklyPacket: buildWeeklyPacket,
    addDays: addDays,
  };

  // ----------------------------------------------------------- browser driver
  // Only runs when injected into the logged-in app.trainingpeaks.com page by
  // playwriter -- see tools/RUNBOOK_weekly_packet.md. Never runs under Node
  // (require() never triggers this branch), so it is safe for this file to
  // reference `window`/`fetch` unconditionally here.
  if (typeof window !== 'undefined') {
    (function () {
      var ARGS = window.__PACKET_ARGS__ || {};

      function fetchJson(path, options) {
        options = options || {};
        var init = {
          method: options.method || 'GET',
          credentials: 'include', // required cross-origin cookie -- see tp-dynamic-plan-builder skill
          headers: { Accept: 'application/json' },
        };
        if (options.body !== undefined) {
          init.headers['Content-Type'] = 'application/json';
          init.body = JSON.stringify(options.body);
        }
        return fetch(TP_BASE + path, init).then(function (response) {
          return response.text().then(function (text) {
            var body = null;
            if (text) {
              try { body = JSON.parse(text); } catch (e) { body = null; }
            }
            return { ok: response.ok || response.status === 204, status: response.status, body: body };
          });
        });
      }

      buildWeeklyPacket(ARGS, { fetchJson: fetchJson })
        .then(function (packet) { window.__WEEKLY_PACKET__ = packet; })
        .catch(function (err) {
          window.__WEEKLY_PACKET__ = {
            schema: SCHEMA,
            error: String(err && err.message ? err.message : err),
          };
        });
    }());
  }

  return api;
}));
