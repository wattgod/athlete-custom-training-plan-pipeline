import hashlib
import json
import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "tools" / "tp_phase5_playwriter_cli.mjs"


def _fake_playwriter(tmp_path: Path) -> tuple[Path, Path]:
    executable = tmp_path / "reviewed-playwriter"
    log = tmp_path / "commands.jsonl"
    executable.write_text(
        """#!/usr/bin/env python3
import json
import os
import re
import sys
from pathlib import Path

log = Path(os.environ['FAKE_PLAYWRITER_LOG'])
with log.open('a', encoding='utf-8') as handle:
    handle.write(json.dumps(sys.argv[1:]) + '\\n')
args = sys.argv[1:]
if args == ['--version']:
    print('playwriter/0.4.0 test-runtime')
elif args == ['session', 'list']:
    print('ID  BROWSER  PROFILE          EXT')
    print('4   Chrome   coach@example.com install:Chrome:fixture123')
elif len(args) == 4 and args[:3] == ['-s', '4', '-f']:
    source = Path(args[3]).read_text(encoding='utf-8')
    if ('state.tpPhase5PayloadPath=' in source
            or 'state.tpPhase5PayloadSource=' not in source
            or 'state.tpPhase5PayloadSha256=' not in source):
        raise SystemExit(10)
    match = re.search(r'state\\.tpPhase5ReceiptPath=(\"(?:[^\"\\\\]|\\\\.)*\")', source)
    if not match:
        raise SystemExit(9)
    receipt = Path(json.loads(match.group(1)))
    receipt.write_text('{}\\n', encoding='utf-8')
else:
    raise SystemExit(8)
""",
        encoding="utf-8",
    )
    executable.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
    return executable, log


def _environment(executable: Path, log: Path) -> dict[str, str]:
    env = os.environ.copy()
    env.update({
        "FAKE_PLAYWRITER_LOG": str(log),
        "GG_TP_PLAYWRITER_BIN": str(executable),
        "GG_TP_PLAYWRITER_BIN_SHA256": hashlib.sha256(
            executable.read_bytes()).hexdigest(),
        "GG_TP_PLAYWRITER_VERSION": "0.4.0",
        "GG_TP_PLAYWRITER_SESSION": "4",
        "GG_TP_PLAYWRITER_PROFILE": "coach@example.com",
        "GG_TP_PLAYWRITER_BROWSER_KEY": "install:Chrome:fixture123",
    })
    return env


def test_playwriter_adapter_uses_one_atomic_profile_bound_invocation(tmp_path):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js is required")
    executable, log = _fake_playwriter(tmp_path)
    request = tmp_path / "request.json"
    receipt = tmp_path / "receipt.json"
    request.write_text("{}\n", encoding="utf-8")

    completed = subprocess.run(
        [node, str(CLI), "--request", str(request), "--receipt", str(receipt)],
        env=_environment(executable, log), check=False,
        capture_output=True, text=True, timeout=30,
    )

    assert completed.returncode == 0, completed.stderr
    commands = [json.loads(line) for line in log.read_text().splitlines()]
    assert commands[:2] == [["--version"], ["session", "list"]]
    assert len(commands) == 3
    assert commands[2][:3] == ["-s", "4", "-f"]
    assert all("-e" not in command for command in commands)
    assert receipt.is_file()
    assert not list(tmp_path.glob(".tp-phase5-invocation-*.js"))


def test_playwriter_adapter_refuses_profile_substitution(tmp_path):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js is required")
    executable, log = _fake_playwriter(tmp_path)
    request = tmp_path / "request.json"
    receipt = tmp_path / "receipt.json"
    request.write_text("{}\n", encoding="utf-8")
    env = _environment(executable, log)
    env["GG_TP_PLAYWRITER_PROFILE"] = "wrong@example.com"

    completed = subprocess.run(
        [node, str(CLI), "--request", str(request), "--receipt", str(receipt)],
        env=env, check=False, capture_output=True, text=True, timeout=30,
    )

    assert completed.returncode != 0
    assert not receipt.exists()
    commands = [json.loads(line) for line in log.read_text().splitlines()]
    assert commands == [["--version"], ["session", "list"]]
