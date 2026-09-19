# RUNBOOK: capture a `weekly_packet/v1`

Run this from a Claude session with the playwriter transport and a Chrome
profile already logged into `app.trainingpeaks.com` as the coach. Read-only.
No write call is ever made to an athlete's calendar or plan. The one POST in
this recipe (`reporting/performancedata`) only reads a computed PMC report —
see `docs/WEEKLY_PACKET.md`, "Endpoint proof".

Schema: `docs/WEEKLY_PACKET.md`. Producer: `tools/tp_weekly_packet.js`.

## Preconditions

1. Chrome is open, logged into `app.trainingpeaks.com` as the coach account.
2. You have the athlete's numeric TP athlete id (`tp_athlete_id`) and the
   repo's `athlete_key` for them (`athletes/<athlete_key>/`).
3. Decide `since` (the earliest date notes should be pulled from — usually
   the date of the last weekly packet run for this athlete, or the start of
   the coached block if this is the first run).

## Steps

1. **Open a dedicated tab.** Do not reuse the coach's own tab — navigation in
   that tab mid-script destroys the execution context (hit in the
   `tp-dynamic-plan-builder` pilot). Use `context.newPage()` and navigate it
   to `https://app.trainingpeaks.com/`.

2. **Read the script source and stage the args**, in the SAME playwriter
   `execute` call (Node `fs` is available in that context):

   ```js
   const fs = require('node:fs');
   const src = fs.readFileSync('tools/tp_weekly_packet.js', 'utf8');
   const args = {
     athleteId: '<tp_athlete_id>',
     athleteKey: '<athlete_key>',
     since: '<YYYY-MM-DD>',
     // asOf is optional -- omit it to use the browser's current date.
   };
   await page.evaluate((a) => { window.__PACKET_ARGS__ = a; }, args);
   await page.evaluate(src).catch((err) => { throw err; });
   ```

3. **Poll for the result.** The script is async; it sets
   `window.__WEEKLY_PACKET__` when done (or an `{schema, error}` object on a
   hard failure inside the orchestrator itself — individual endpoint
   failures do NOT throw; they land in `source_manifest.endpoints` instead,
   see step 5). Poll every ~500ms, timeout after ~30s:

   ```js
   let packet = null;
   for (let i = 0; i < 60; i++) {
     packet = await page.evaluate(() => window.__WEEKLY_PACKET__);
     if (packet) break;
     await new Promise((r) => setTimeout(r, 500));
   }
   if (!packet) throw new Error('WEEKLY_PACKET_TIMEOUT');
   if (packet.error) throw new Error('WEEKLY_PACKET_FAILED: ' + packet.error);
   ```

4. **Reload on 401.** TP API auth tokens expire; a tab open for hours starts
   returning 401s with empty bodies. If `source_manifest.endpoints` shows
   401s across the board (not just one endpoint), `page.reload()` re-auths
   the SPA against the athlete-bound calendar view, then repeat steps 2–3.
   A single 401 on one endpoint (not all of them) is more likely a real
   permission gap for that athlete/endpoint — don't reload-and-retry blindly
   in that case; check the athlete id is a coached athlete on this account.

5. **Check `source_manifest.endpoints` before trusting the packet.** Every
   call this script makes is listed there with its status. Expect:
   - `settings`, `events`, `reporting/performancedata`, `workouts`,
     `calendarNote/{start}/{end}` — one entry each, should all be 200.
   - `calendarNote/{noteId}/comments` — one entry per note in the notes
     window; 200 or 204 are both fine (204 = no comments on that note). This
     endpoint is NOT independently proven (see `docs/WEEKLY_PACKET.md`) — a
     404 or other error here is not necessarily a bug in this script; it may
     mean the endpoint path is wrong and needs correcting against a real
     response the first time this runs.
   - Any non-2xx/204 status, or an `"error: ..."` string, means that section
     of the packet is empty/nulled, not fabricated. The packet is still
     written — a partial packet is more useful to the reviewer than none —
     but say so when handing it off.

6. **Save the JSON under the private builds dir**, never in this repo
   (athlete data is never committed — see `docs/WEEKLY_PACKET.md`,
   "Non-goals"):

   ```
   ~/Library/Application Support/GravelGod/TrainingPeaksPublisher/plan-builds/<athlete_key>/weekly-<as_of>/weekly_packet.json
   ```

   ```js
   const outDir = `${process.env.HOME}/Library/Application Support/GravelGod/TrainingPeaksPublisher/plan-builds/${args.athleteKey}/weekly-${packet.as_of}`;
   fs.mkdirSync(outDir, { recursive: true, mode: 0o700 });
   fs.writeFileSync(`${outDir}/weekly_packet.json`, JSON.stringify(packet, null, 2) + '\n', { mode: 0o600 });
   ```

7. **Hand off** the file path to `athletes/scripts/weekly_packet.py` (the
   normalizer/validator that `profile_refresh.py` consumes) — never the raw
   JSON pasted into a chat message or commit.

## Known-unverified field names (correct against the first real response)

`docs/WEEKLY_PACKET.md`'s "Endpoint proof" table lists which endpoints and
response field names are proven against this repo's history and which are
this executor's best guess. On the first real run, diff the raw responses
against `mapPmcDaily`/`mapWorkouts` in `tools/tp_weekly_packet.js` — the PMC
row field names (`ctl`/`atl`/`tsb`/`tssActual`/`tssPlanned`) and the workout
fields `ifActual`/`normalizedPowerActual` are not confirmed anywhere in this
repo or the `endure-coaching-ops` plugin. If they're wrong, those columns
will silently read `null` rather than error (by design — see "Non-goals" in
the schema doc for why partial-but-honest beats a thrown exception here) —
check for unexpected all-null columns in the first captured packet.

## What this script never does

- Never POSTs, PUTs, or DELETEs to any endpoint that mutates data.
- Never touches `plans/v1/*` (that's the `tp-dynamic-plan-builder` skill's
  job, a separate transport, on a separate DRAFT plan container).
- Never embeds an athlete id, name, or key as a literal in
  `tools/tp_weekly_packet.js` itself — every identifier comes in through
  `window.__PACKET_ARGS__` at run time.
