#!/usr/bin/env node

/**
 * Process adapter between Phase 5 and the reviewed Playwriter CLI.
 *
 * The session and executable are server configuration. Only private request
 * and receipt paths are accepted from Phase 5; no order can select a browser,
 * profile, command, or executable.
 */

import { spawnSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';


function parseArgs(argv) {
  const parsed = {};
  for (let index = 0; index < argv.length; index += 2) {
    const key = argv[index];
    const value = argv[index + 1];
    if (!['--request', '--receipt'].includes(key) || !value) {
      throw new Error('usage: tp_phase5_playwriter_cli.mjs --request PATH --receipt PATH');
    }
    parsed[key.slice(2)] = path.resolve(value);
  }
  if (!parsed.request || !parsed.receipt) throw new Error('request and receipt are required');
  return parsed;
}

const args = parseArgs(process.argv.slice(2));
if (!existsSync(args.request)) throw new Error('Phase 5 request file is missing');
if (existsSync(args.receipt)) throw new Error('refusing to overwrite Phase 5 receipt');

const session = String(process.env.GG_TP_PLAYWRITER_SESSION || '');
if (!/^[A-Za-z0-9_-]{1,128}$/.test(session)) {
  throw new Error('GG_TP_PLAYWRITER_SESSION is required');
}
const executable = String(process.env.GG_TP_PLAYWRITER_BIN || 'playwriter');
if (!/^[A-Za-z0-9_./-]+$/.test(executable)) {
  throw new Error('GG_TP_PLAYWRITER_BIN is unsafe');
}

const here = path.dirname(fileURLToPath(import.meta.url));
const runnerPath = path.join(here, 'tp_phase5_playwriter_run.js');
const payloadPath = path.join(here, 'tp_phase5_browser_payload.js');
const expression = [
  `state.tpPhase5RequestPath=${JSON.stringify(args.request)}`,
  `state.tpPhase5ReceiptPath=${JSON.stringify(args.receipt)}`,
  `state.tpPhase5PayloadPath=${JSON.stringify(payloadPath)}`,
].join(';');

for (const commandArgs of [
  ['-s', session, '-e', expression],
  ['-s', session, '-f', runnerPath],
]) {
  const result = spawnSync(executable, commandArgs, {
    stdio: 'ignore', timeout: 15 * 60 * 1000,
  });
  if (result.error) throw result.error;
  if (result.status !== 0) process.exit(result.status || 1);
}
if (!existsSync(args.receipt)) throw new Error('Playwriter produced no Phase 5 receipt');
