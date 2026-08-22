/**
 * Execute one Phase 5 browser request through an existing Playwriter session.
 *
 * The atomic private invocation file supplies the three path values below.
 * This runner clears every browser and session global before returning.
 */

await (async () => {
  'use strict';

  const crypto = require('node:crypto');
  const fs = require('node:fs');
  const path = require('node:path');
  const receiptGlobal = '__GG_TP_PHASE5_RECEIPT__';
  const stateKeys = [
    'tpPhase5RequestPath', 'tpPhase5ReceiptPath', 'tpPhase5PayloadPath', 'page',
  ];

  try {
    const requestPath = path.resolve(String(state.tpPhase5RequestPath || ''));
    const receiptPath = path.resolve(String(state.tpPhase5ReceiptPath || ''));
    const payloadPath = path.resolve(String(state.tpPhase5PayloadPath || ''));
    if (!requestPath || !receiptPath || !payloadPath) {
      throw new Error('Phase 5 request, receipt, and payload paths are required');
    }
    if (!fs.existsSync(requestPath) || !fs.existsSync(payloadPath)) {
      throw new Error('Phase 5 request or browser payload is missing');
    }
    if (fs.existsSync(receiptPath)) {
      throw new Error('refusing to overwrite an existing Phase 5 receipt');
    }

    const request = JSON.parse(fs.readFileSync(requestPath, 'utf8'));
    const source = fs.readFileSync(payloadPath, 'utf8');
    const scriptSha256 = crypto.createHash('sha256').update(source).digest('hex');
    if (request.request_type !== 'trainingpeaks_playwright_request/v1') {
      throw new Error('unsupported Phase 5 Playwright request');
    }

    const targetUrl = `https://app.trainingpeaks.com/#calendar/athletes/${encodeURIComponent(
      String(request.tp_athlete_id),
    )}`;
    const current = new URL(page.url());
    if (current.origin !== 'https://app.trainingpeaks.com'
        || current.hash !== new URL(targetUrl).hash) {
      throw new Error('Playwriter page is not prebound to the exact athlete');
    }

    const bound = new URL(page.url());
    if (bound.origin !== 'https://app.trainingpeaks.com'
        || bound.hash !== new URL(targetUrl).hash) {
      throw new Error('Playwriter page binding changed before evaluation');
    }
    const receipt = await page.evaluate(
      async ({ sourceText, args, globalName }) => {
        delete window[globalName];
        window.__TP_SCRIPT_ARGS__ = args;
        try {
          const execution = (0, eval)(sourceText);
          if (execution && typeof execution.then === 'function') await execution;
          const deadline = Date.now() + 15 * 60 * 1000;
          while (!window[globalName]?.finished_at && Date.now() < deadline) {
            await new Promise(resolve => setTimeout(resolve, 100));
          }
          return window[globalName] || null;
        } finally {
          delete window.__TP_SCRIPT_ARGS__;
          delete window[globalName];
        }
      },
      {
        sourceText: source,
        args: { request, script_sha256: scriptSha256 },
        globalName: receiptGlobal,
      },
    );
    if (!receipt || !receipt.finished_at) {
      throw new Error('Phase 5 browser payload produced no finished receipt');
    }

    fs.mkdirSync(path.dirname(receiptPath), { recursive: true, mode: 0o700 });
    const temporary = `${receiptPath}.tmp-${Date.now()}-${process.pid}`;
    try {
      fs.writeFileSync(temporary, `${JSON.stringify(receipt)}\n`, {
        encoding: 'utf8', mode: 0o600, flag: 'wx',
      });
      fs.renameSync(temporary, receiptPath);
    } finally {
      if (fs.existsSync(temporary)) fs.rmSync(temporary, { force: true });
    }
  } finally {
    try {
      await page.evaluate(globalName => {
        delete window.__TP_SCRIPT_ARGS__;
        delete window[globalName];
      }, receiptGlobal);
    } catch (_error) {
      // The page may have closed. Persistent session state is still cleared.
    }
    for (const key of stateKeys) delete state[key];
  }
})();
