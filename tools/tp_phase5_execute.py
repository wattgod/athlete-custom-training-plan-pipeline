#!/usr/bin/env python3
"""Canonical Phase 5 TrainingPeaks Playwright entrypoint.

The caller supplies sealed artifacts and a short-lived capability by private
file. Secrets, browser session selection, and write/canary gates are read only
from server configuration. Output is deliberately redacted.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "webhook"))

from delivery.trainingpeaks.phase5_service import (  # noqa: E402
    CanaryPolicy,
    ExecutionGrantCodec,
    Phase5MutationService,
)
from delivery.trainingpeaks.playwright_transport import (  # noqa: E402
    PlaywrightTransport,
    PlaywrightTransportConfig,
)
from delivery.trainingpeaks.worker_service import CapabilityCodec  # noqa: E402


CAPABILITY_AUDIENCE = "gg-trainingpeaks-worker"
GRANT_AUDIENCE = "gg-tp-phase5-executor"


def _private_text(path: Path, label: str) -> str:
    resolved = path.resolve()
    if path.is_symlink() or not resolved.is_file():
        raise ValueError(f"{label} file is unavailable")
    mode = stat.S_IMODE(resolved.stat().st_mode)
    if mode & 0o077:
        raise ValueError(f"{label} file permissions are too broad")
    value = resolved.read_text(encoding="utf-8").strip()
    if not value:
        raise ValueError(f"{label} file is empty")
    return value


def _json_object(path: Path, label: str) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} is unavailable") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return value


def _secret(name: str) -> str:
    value = os.environ.get(name, "")
    if len(value.encode("utf-8")) < 32:
        raise ValueError(f"server configuration {name} is unavailable")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--capability-file", type=Path, required=True)
    parser.add_argument("--record-root", type=Path, required=True)
    parser.add_argument("--staging-root", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        contract = _json_object(args.contract, "apply contract")
        capability_token = _private_text(args.capability_file, "capability")
        cap_kid = os.environ.get("GG_WORKER_CAPABILITY_KID", "phase5-cap-k1")
        grant_kid = os.environ.get("GG_TP_EXECUTION_GRANT_KID", "phase5-grant-k1")
        capability_codec = CapabilityCodec(
            {cap_kid: _secret("GG_WORKER_CAPABILITY_SECRET")},
            audience=CAPABILITY_AUDIENCE)
        grant_codec = ExecutionGrantCodec(
            {grant_kid: _secret("GG_TP_EXECUTION_GRANT_SECRET")},
            audience=GRANT_AUDIENCE)
        service = Phase5MutationService(
            capability_codec, grant_codec, args.record_root,
            grant_kid=grant_kid,
            live_writes_enabled=os.environ.get("GG_TP_LIVE_WRITES_ENABLED") == "1",
            canary_policy=CanaryPolicy.from_environment(),
        )
        node = shutil.which("node")
        if not node:
            raise ValueError("Node.js is unavailable")
        runner = ROOT / "tools" / "tp_phase5_playwriter_cli.mjs"
        payload = ROOT / "tools" / "tp_phase5_browser_payload.js"
        transport = PlaywrightTransport(PlaywrightTransportConfig.create(
            [node, str(runner)], args.staging_root, payload))
        now = int(time.time())
        grant = service.exchange(
            capability_token, contract, args.state, now=now)
        receipt = service.execute(
            grant, contract, args.state, transport, now=now + 1)
        print(json.dumps({
            "status": receipt["status"],
            "operation_count": receipt["operation_count"],
            "receipt_digest": receipt["receipt_digest"],
        }, sort_keys=True))
        return 0
    except Exception as exc:
        print(json.dumps({
            "status": "failed", "error_type": type(exc).__name__,
        }, sort_keys=True), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
