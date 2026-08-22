#!/usr/bin/env node

/**
 * Atomic process adapter between Phase 5 and the reviewed Playwriter CLI.
 *
 * Browser identity is server configuration. The adapter verifies the exact
 * executable bytes, version, session, profile, and extension connection, then
 * executes one private generated runner file. It never uses persistent
 * Playwriter state as a handoff between separate CLI invocations.
 */

import { spawnSync } from 'node:child_process';
import { createHash, randomBytes } from 'node:crypto';
import {
  chmodSync, existsSync, readFileSync, rmSync, writeFileSync,
} from 'node:fs';
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

function configured(name, pattern) {
  const value = String(process.env[name] || '').trim();
  if (!pattern.test(value)) throw new Error(`${name} is required`);
  return value;
}

function run(executable, commandArgs, options = {}) {
  const result = spawnSync(executable, commandArgs, {
    encoding: 'utf8', timeout: 60_000, ...options,
  });
  if (result.error) throw result.error;
  if (result.status !== 0) throw new Error('reviewed Playwriter preflight failed');
  return result;
}

const args = parseArgs(process.argv.slice(2));
if (!existsSync(args.request)) throw new Error('Phase 5 request file is missing');
if (existsSync(args.receipt)) throw new Error('refusing to overwrite Phase 5 receipt');

const session = configured('GG_TP_PLAYWRITER_SESSION', /^[A-Za-z0-9_-]{1,128}$/);
const expectedVersion = configured('GG_TP_PLAYWRITER_VERSION', /^\d+\.\d+\.\d+$/);
const expectedProfile = configured('GG_TP_PLAYWRITER_PROFILE', /^[^\s]{1,256}$/);
const expectedBrowserKey = configured(
  'GG_TP_PLAYWRITER_BROWSER_KEY', /^[A-Za-z0-9:_-]{1,256}$/,
);
const expectedExecutableSha = configured(
  'GG_TP_PLAYWRITER_BIN_SHA256', /^[0-9a-f]{64}$/,
);
const executable = String(process.env.GG_TP_PLAYWRITER_BIN || '').trim();
if (!path.isAbsolute(executable) || !existsSync(executable)) {
  throw new Error('GG_TP_PLAYWRITER_BIN must be an absolute reviewed executable');
}
const actualExecutableSha = createHash('sha256').update(readFileSync(executable)).digest('hex');
if (actualExecutableSha !== expectedExecutableSha) {
  throw new Error('reviewed Playwriter executable digest mismatch');
}

const version = run(executable, ['--version']).stdout;
if (!version.includes(`playwriter/${expectedVersion}`)) {
  throw new Error('reviewed Playwriter version mismatch');
}
const sessions = run(executable, ['session', 'list']).stdout.split(/\r?\n/);
const selected = sessions.map(line => line.trim().split(/\s+/)).find(parts => (
  parts.length >= 4 && parts[0] === session
));
if (!selected || selected[2] !== expectedProfile || selected[3] !== expectedBrowserKey) {
  throw new Error('reviewed Playwriter session/profile binding mismatch');
}

const here = path.dirname(fileURLToPath(import.meta.url));
const runnerPath = path.join(here, 'tp_phase5_playwriter_run.js');
const payloadPath = path.join(here, 'tp_phase5_browser_payload.js');
const invocationPath = path.join(
  path.dirname(args.request),
  `.tp-phase5-invocation-${process.pid}-${randomBytes(8).toString('hex')}.js`,
);
const preamble = [
  `state.tpPhase5RequestPath=${JSON.stringify(args.request)};`,
  `state.tpPhase5ReceiptPath=${JSON.stringify(args.receipt)};`,
  `state.tpPhase5PayloadPath=${JSON.stringify(payloadPath)};`,
].join('\n');

try {
  writeFileSync(
    invocationPath,
    `${preamble}\n${readFileSync(runnerPath, 'utf8')}`,
    { encoding: 'utf8', mode: 0o600, flag: 'wx' },
  );
  chmodSync(invocationPath, 0o600);
  const result = spawnSync(executable, ['-s', session, '-f', invocationPath], {
    stdio: 'ignore', timeout: 15 * 60 * 1000,
  });
  if (result.error) throw result.error;
  if (result.status !== 0) process.exitCode = result.status || 1;
} finally {
  rmSync(invocationPath, { force: true });
}
if (process.exitCode) process.exit(process.exitCode);
if (!existsSync(args.receipt)) throw new Error('Playwriter produced no Phase 5 receipt');
