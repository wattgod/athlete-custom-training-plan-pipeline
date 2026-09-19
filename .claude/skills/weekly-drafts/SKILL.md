---
name: weekly-drafts
description: "Run the weekly Motoren DRAFT-plan loop for coached athletes: capture a weekly_packet/v1 per athlete from TrainingPeaks (read-only, playwriter), refresh each profile, build the plan, render the review page, upsert one standing DRAFT dynamic plan per athlete into the coach's plan library. Use on Matti's weekly review (Monday) or when he asks for the drafts. Never writes an athlete's live calendar."
---

# Weekly drafts

Spec of record: `athlete-custom-training-plan-pipeline/docs/specs/2026-09-18-variety-and-weekly-dynamic-plans.md`
(section B, revision 2). Packet schema: `docs/WEEKLY_PACKET.md`. Rules vocabulary: `docs/ATHLETE_RULES.md`.

## Roster

Athletes with `athletes/<id>/profile.yaml` AND `plan-builds/<id>/rules.yaml` in the private dir
`~/Library/Application Support/GravelGod/TrainingPeaksPublisher/plan-builds/`. TP ids live in the roster
memory (`roster-fall-close-out`). Run 1 (2026-09-18): forest-hietpas 729185, edward-shapiro 544668,
ari-shapiro 4439069, judd-pulley 4032686.

## Procedure

1. Export the pipeline branch. The loop rebuilds `athletes/<id>/` in whatever tree it runs in, so never run
   it in a working tree:
   ```
   cd <pipeline worktree>; E=<scratch>/weekly-$(date +%F); git checkout-index -a --prefix="$E/"
   cd "$E" && git init -q && git add -A && git -c user.email=x@x -c user.name=x commit -qm snapshot
   ```
2. Capture packets. Reset playwriter, open a dedicated tab on app.trainingpeaks.com, then per athlete inject
   `tools/tp_weekly_packet.js` with `window.__PACKET_ARGS__ = {athleteId, athleteKey, since, asOf}` and poll
   `window.__WEEKLY_PACKET__` (recipe: `tools/RUNBOOK_weekly_packet.md`). Save with playwriter `fs` under
   `/tmp/gg-weekly-packets-<date>/<id>.json` (its fs allows only /Users and /tmp), then copy to a packets dir.
   Every `source_manifest.endpoints` status must be 200 or 204.
3. Run the loop:
   ```
   python3 tools/weekly_draft_plan.py --athlete <id> [--athlete ...] --packets-dir <dir> --run-date <YYYY-MM-DD> --builds-root <builds> [--force]
   ```
   `<builds>/<id>/rules.yaml` must exist (copy from the private dir). Outputs per athlete:
   `refresh_diff.json`, `coaching_history.md`, `weekly_draft_state.json`, `weekly-<date>/{plan_payload_final,
   notes_payload_final,draft_manifest}.json`. Status is built, skipped or held. A hold is a decision for Matti
   (FTP mismatch, race date mismatch, under 2 weeks to race, excluded athlete, profile fails validation,
   missing profile section). Do not work around a hold.
4. Render and publish the page:
   ```
   python3 tools/weekly_review_page.py --builds-root <builds> --run-date <date> --out <html> [--run-1]
   ```
   Publish it to the standing artifact "Motoren Weekly Drafts" (`url` https://claude.ai/artifact/5URyMcXRMp8GL5hLrKdcSa)
   after stripping the html/head/body wrapper and adding the `data-theme` token blocks.
5. Upsert every BUILT athlete. Copy `plan_payload_final.json`, `notes_payload_final.json`, `draft_manifest.json`
   to `/tmp/gg-drafts-<date>/<id>/`. In the dedicated tab: reload, set `window.__DRAFT_TITLE__` (manifest
   title), `window.__PLAN_ID__` (from `weekly_draft_state.json`, null on the first run), `__PLAN_PAYLOAD__`,
   `__NOTES_PAYLOAD__`, evaluate `plan-builds/_shared/upsert_draft_plan.js`, poll `window.__TP_RECEIPT__`.
   Accept only: `failed` empty, `partial` false, `isDynamicConfirmed` true, readback found == expected with no
   mismatches and no `unmatched` rows. Save the receipt beside the payloads and write `plan_id` /
   `plan_person_id` into `weekly_draft_state.json`.
   Before the FIRST run that updates an existing draft (`__PLAN_ID__` set), verify the note-delete endpoint on a
   disposable plan per `_shared/RUNBOOK.md`.
6. Persist. Copy each athlete's `weekly-<date>/` directory, `weekly_draft_state.json`, `refresh_diff.json` and
   `coaching_history.md` into the private `plan-builds/<id>/` (playwriter `fs` when Bash is refused).
   Profile changes in `refresh_diff.json` are applied to the repo profile separately
   (`athletes/scripts/profile_refresh.py <id> --packet ... --history ... --today ... --write` in the worktree),
   then committed.
7. Tell Matti: per athlete the status, the holds with both sources, plan ids, and the artifact link. Live
   calendars are never touched by this loop; he copies with the dual calendar.

## Rules

- Never write to `fitness/*` endpoints. `plans/v1` only, keyed on the recorded `plan_id`.
- A hold is reported, not resolved. FTP is Matti's number.
- No athlete source text in the repo. History and receipts stay in the private dir.
- Adversarial review before any change to the engine or the transport.

## Guard (security review, PR #260)

`.claude/hooks/tp_write_guard.py` scans the `code` string passed to `mcp__playwriter__execute` AND every script that
code loads (`readFileSync` / `readFile` / `require` / `import` / `page.addScriptTag({ path })`, followed
transitively). A loaded script with a POST/PUT/PATCH/DELETE against a TrainingPeaks endpoint is denied unless it IS
one of the two reviewed files, matched by resolved absolute path AND SHA-256 of its content: `~/Library/Application
Support/GravelGod/TrainingPeaksPublisher/plan-builds/_shared/upsert_draft_plan.js` (plans/v1 writes only, refuses any
plan not titled DRAFT) and `<repo>/tools/tp_weekly_packet.js` (read-only; its one POST is TP's PMC reporting query).
Rules:
- Evaluate only those two scripts in the TP tab. Never evaluate ad-hoc JS there. The same content at any other path is
  scanned and denied; either file edited in-session fails its hash and is denied until re-reviewed and re-pinned
  (`python3 .claude/hooks/tp_write_guard.py --print-hashes`; CRLF and trailing-newline differences are tolerated).
- Load them by ONE literal path (absolute, `~`, `${process.env.HOME}`, or relative to the repo) with the loader called
  directly. A variable, concatenation, `path.join`, aliased or destructured loader, `createRequire`, other template
  interpolation, `addScriptTag` with `url:`/`content:`, or a missing file is denied. Builtin requires (`'node:fs'`,
  `'fs'`, `'path'`) are fine.
- Comments are not stripped (a JS regex literal defeats any stripper), so a load inside a comment still counts and
  fails closed. Delete the comment rather than leaving a dead load in the wrapper.
- There is no kernel-directory escape hatch any more. A legacy flow that writes from the wrapper needs the
  `/* GG_BLESSED_TP_WRITE */` marker, which is the coach-visible audit trail for a hand-run write.
- The guard is a regex tripwire for straightforward and accidental writes, not a defence against deliberate
  obfuscation. The "only the named scripts" rule above is the real control.
