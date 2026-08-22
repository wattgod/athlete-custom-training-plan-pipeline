"""Phase 5 bridge to a server-configured Playwright transport.

The browser runner is deliberately outside the fulfillment process because it
owns an interactive, cookie-authenticated browser.  This bridge remains the
authority boundary: it checkpoints every mutation intent before dispatch,
stages an exact contract-bound request with private permissions, accepts only
a strict receipt, and forwards verified per-operation evidence to the Phase 5
state machine.

No browser executable, session identifier, or command may come from an order.
Those values are server configuration supplied to :class:`PlaywrightTransport`.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from delivery.trainingpeaks.phase5_service import (
    MutationExecutionContext,
    Phase5AuthorizationError,
    Phase5ReadbackMismatch,
)


REQUEST_TYPE = "trainingpeaks_playwright_request/v1"
RECEIPT_TYPE = "trainingpeaks_playwright_receipt/v1"
_HEX_64 = re.compile(r"[0-9a-f]{64}\Z")
_SAFE_FILE_ID = re.compile(r"[A-Za-z0-9_-]{1,128}\Z")


class PlaywrightTransportError(RuntimeError):
    """The configured browser runner failed without proving remote state."""


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def compile_playwright_request(
    contract: Mapping[str, Any], *, action: str, dry_run: bool,
    script_sha256: str,
    prior_receipts: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Compile a credential-free, exact-contract browser request."""
    if action not in {"apply", "verify", "rollback"}:
        raise Phase5AuthorizationError("Playwright request action is invalid")
    required = {
        "contract_version", "order_id", "tp_athlete_id",
        "generation_revision", "model_seal", "operations",
    }
    if not required <= set(contract):
        raise Phase5AuthorizationError("Playwright request contract is incomplete")
    if contract.get("contract_version") != "apply_contract/v1":
        raise Phase5AuthorizationError("Playwright request contract version is unsupported")
    operations = contract.get("operations")
    if not isinstance(operations, list) or not operations:
        raise Phase5AuthorizationError("Playwright request operations are required")
    if not _HEX_64.fullmatch(str(script_sha256 or "")):
        raise Phase5AuthorizationError("Playwright browser payload digest is invalid")
    return {
        "request_type": REQUEST_TYPE,
        "contract_digest": _digest(contract),
        "action": action,
        "dry_run": bool(dry_run),
        "order_id": str(contract["order_id"]),
        "tp_athlete_id": str(contract["tp_athlete_id"]),
        "generation_revision": int(contract["generation_revision"]),
        "model_seal": str(contract["model_seal"]),
        "script_sha256": str(script_sha256),
        "operations": copy.deepcopy(operations),
        "prior_receipts": copy.deepcopy(list(prior_receipts)),
    }


@dataclass(frozen=True)
class PlaywrightTransportConfig:
    """Server-owned runner configuration; never populate from order data."""

    runner_argv: tuple[str, ...]
    staging_root: Path
    browser_payload_path: Path
    timeout_seconds: int = 15 * 60

    @classmethod
    def create(
        cls, runner_argv: Sequence[str], staging_root: Path | str,
        browser_payload_path: Path | str,
        *, timeout_seconds: int = 15 * 60,
    ) -> "PlaywrightTransportConfig":
        argv = tuple(str(item) for item in runner_argv)
        if not argv or any(not item.strip() for item in argv):
            raise ValueError("Playwright runner argv is required")
        timeout = int(timeout_seconds)
        if timeout < 30 or timeout > 30 * 60:
            raise ValueError("Playwright runner timeout is outside policy")
        payload = Path(browser_payload_path).resolve()
        if Path(browser_payload_path).is_symlink() or not payload.is_file():
            raise ValueError("Playwright browser payload is unavailable")
        return cls(argv, Path(staging_root).resolve(), payload, timeout)


ProcessRunner = Callable[..., subprocess.CompletedProcess[str]]


class PlaywrightTransport:
    """Callable Phase 5 executor backed by a configured Playwright runner."""

    def __init__(
        self, config: PlaywrightTransportConfig, *,
        process_runner: ProcessRunner = subprocess.run,
    ):
        self.config = config
        self._process_runner = process_runner

    @staticmethod
    def _write_private_json(path: Path, value: Mapping[str, Any]) -> None:
        fd, temporary = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(value, handle, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
            directory_fd = os.open(path.parent, os.O_DIRECTORY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def _stage_paths(self, context: MutationExecutionContext) -> tuple[Path, Path, Path]:
        claims = context.grant.claims
        order_id = str(claims.get("order_id") or "")
        grant_id = str(claims.get("grant_id") or "")
        if not _SAFE_FILE_ID.fullmatch(order_id) or not _SAFE_FILE_ID.fullmatch(grant_id):
            raise Phase5AuthorizationError("unsafe Playwright staging identity")
        root = self.config.staging_root
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        if root.is_symlink() or root.resolve() != root:
            raise Phase5AuthorizationError("unsafe Playwright staging root")
        attempt_dir = root / order_id / grant_id
        attempt_dir.mkdir(parents=True, exist_ok=False, mode=0o700)
        if attempt_dir.is_symlink() or attempt_dir.resolve().parent.parent != root:
            raise Phase5AuthorizationError("unsafe Playwright staging directory")
        return attempt_dir, attempt_dir / "request.json", attempt_dir / "receipt.json"

    @staticmethod
    def _load_receipt(path: Path) -> dict[str, Any]:
        if path.is_symlink():
            raise PlaywrightTransportError("Playwright receipt path is unsafe")
        try:
            raw = path.read_bytes()
        except OSError as exc:
            raise PlaywrightTransportError(
                "Playwright runner produced no receipt") from exc
        if len(raw) > 2 * 1024 * 1024:
            raise PlaywrightTransportError("Playwright receipt exceeds size policy")
        try:
            value = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PlaywrightTransportError("Playwright receipt is invalid JSON") from exc
        if not isinstance(value, dict):
            raise PlaywrightTransportError("Playwright receipt must be an object")
        return value

    @staticmethod
    def _validate_receipt(
        receipt: Mapping[str, Any], request: Mapping[str, Any],
    ) -> list[dict[str, Any]]:
        expected_keys = {
            "receipt_type", "contract_digest", "action", "dry_run",
            "tp_athlete_id", "script_sha256", "started_at", "finished_at",
            "readback_verified", "rollback_verified", "operations", "failure",
        }
        if set(receipt) != expected_keys or receipt.get("receipt_type") != RECEIPT_TYPE:
            raise PlaywrightTransportError("Playwright receipt shape is invalid")
        for field in ("contract_digest", "action", "tp_athlete_id"):
            if receipt.get(field) != request.get(field):
                raise PlaywrightTransportError(
                    f"Playwright receipt {field} binding mismatch")
        if receipt.get("dry_run") is not False:
            raise PlaywrightTransportError("live execution requires a non-dry-run receipt")
        if receipt.get("failure") is not None:
            raise PlaywrightTransportError("Playwright receipt reports a failed operation")
        if not _HEX_64.fullmatch(str(receipt.get("script_sha256") or "")):
            raise PlaywrightTransportError("Playwright receipt script digest is invalid")
        if receipt.get("script_sha256") != request.get("script_sha256"):
            raise PlaywrightTransportError("Playwright receipt script digest mismatch")
        if not all(isinstance(receipt.get(field), str) and receipt[field].strip()
                   for field in ("started_at", "finished_at")):
            raise PlaywrightTransportError("Playwright receipt timestamps are invalid")
        action = str(request["action"])
        if action == "rollback":
            if receipt.get("rollback_verified") is not True:
                raise Phase5ReadbackMismatch("Playwright rollback readback is incomplete")
        elif receipt.get("readback_verified") is not True:
            raise Phase5ReadbackMismatch("Playwright provider readback is incomplete")

        operations = receipt.get("operations")
        if not isinstance(operations, list):
            raise PlaywrightTransportError("Playwright receipt operations are invalid")
        expected_operations = [
            operation for operation in request["operations"]
            if not (action == "rollback" and operation["disposition"] == "keep")
        ]
        expected_by_id = {item["op_id"]: item for item in expected_operations}
        actual_by_id = {
            item.get("op_id"): item for item in operations if isinstance(item, dict)
        }
        if (len(actual_by_id) != len(operations)
                or set(actual_by_id) != set(expected_by_id)):
            raise Phase5ReadbackMismatch(
                "Playwright receipt operation set does not match the contract")
        strict_keys = {
            "op_id", "status", "remote_id", "observed_digest",
            "reconciled_after_error",
        }
        for op_id, operation in expected_by_id.items():
            row = actual_by_id[op_id]
            if set(row) != strict_keys or not isinstance(
                    row.get("reconciled_after_error"), bool):
                raise PlaywrightTransportError(
                    "Playwright operation receipt shape is invalid")
            disposition = operation["disposition"]
            if action == "rollback":
                strategy = (operation.get("rollback") or {}).get("strategy")
                if strategy == "delete_by_remote_id":
                    if row.get("status") != "absent" or row.get("observed_digest") is not None:
                        raise Phase5ReadbackMismatch(
                            "Playwright rollback delete remains ambiguous")
                elif strategy in {
                    "restore_prior_payload", "recreate_from_prior_payload",
                    "restore_before_image",
                }:
                    prior = operation.get("prior_payload") or operation.get("before_image")
                    if (row.get("status") != "restored"
                            or not str(row.get("remote_id") or "").strip()
                            or row.get("observed_digest") != _digest(prior)):
                        raise Phase5ReadbackMismatch(
                            "Playwright rollback restore mismatches the before-image")
                else:
                    raise Phase5ReadbackMismatch(
                        "Playwright rollback strategy is not verifiable")
            elif disposition == "keep":
                if (row.get("status") != "kept"
                        or not str(row.get("remote_id") or "").strip()
                        or row.get("observed_digest") != operation.get("expected_digest")):
                    raise Phase5ReadbackMismatch(
                        "Playwright protected-item readback mismatches the contract")
            elif disposition == "delete":
                if row.get("status") != "absent" or row.get("observed_digest") is not None:
                    raise Phase5ReadbackMismatch(
                        "Playwright delete readback remains ambiguous")
            else:
                if (row.get("status") not in {"landed", "restored"}
                        or not str(row.get("remote_id") or "").strip()
                        or row.get("observed_digest") != operation.get("expected_digest")):
                    raise Phase5ReadbackMismatch(
                        "Playwright write readback mismatches the contract")
        return [copy.deepcopy(actual_by_id[item["op_id"]])
                for item in expected_operations]

    def __call__(self, context: MutationExecutionContext) -> dict[str, Any]:
        action = str(context.grant.claims["action"])
        try:
            script_sha256 = hashlib.sha256(
                self.config.browser_payload_path.read_bytes()).hexdigest()
        except OSError as exc:
            raise PlaywrightTransportError(
                "Playwright browser payload is unavailable") from exc
        request = compile_playwright_request(
            context.contract, action=action, dry_run=False,
            script_sha256=script_sha256,
            prior_receipts=context.prior_receipts)
        if request["contract_digest"] != context.grant.claims["request_digest"]:
            raise Phase5AuthorizationError(
                "Playwright request digest does not match the execution grant")

        # Persist the entire intent set before starting the external process.
        # A runner crash can therefore never leave an unjournaled mutation.
        for operation in context.contract["operations"]:
            if action != "verify" and operation["disposition"] != "keep":
                context.persist_intent(operation)

        attempt_dir, request_path, receipt_path = self._stage_paths(context)
        try:
            self._write_private_json(request_path, request)
            argv = (*self.config.runner_argv,
                    "--request", str(request_path),
                    "--receipt", str(receipt_path))
            try:
                completed = self._process_runner(
                    argv, check=False, cwd=str(attempt_dir),
                    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL, text=True,
                    timeout=self.config.timeout_seconds,
                )
            except subprocess.TimeoutExpired as exc:
                raise PlaywrightTransportError(
                    "Playwright runner timed out; reconcile before retry") from exc
            except OSError as exc:
                raise PlaywrightTransportError(
                    "Playwright runner could not start") from exc
            if completed.returncode != 0:
                raise PlaywrightTransportError(
                    f"Playwright runner failed with exit code {completed.returncode}")
            receipt = self._load_receipt(receipt_path)
            rows = self._validate_receipt(receipt, request)
            operations_by_id = {
                operation["op_id"]: operation
                for operation in context.contract["operations"]
            }
            for row in rows:
                operation = operations_by_id[row["op_id"]]
                context.record_receipt(
                    operation, status=row["status"], remote_id=row["remote_id"],
                    observed_digest=row["observed_digest"],
                    reconciled_after_error=row["reconciled_after_error"],
                )
            return ({"rollback_verified": True} if action == "rollback"
                    else {"readback_verified": True})
        finally:
            # Raw payloads remain only in the authoritative sealed artifacts;
            # browser staging is ephemeral. The Phase 5 record retains the
            # redacted operation receipt and remote identities.
            for path in (receipt_path, request_path):
                try:
                    if path.exists() and not path.is_symlink():
                        path.unlink()
                except OSError:
                    pass
            try:
                attempt_dir.rmdir()
                attempt_dir.parent.rmdir()
            except OSError:
                pass
