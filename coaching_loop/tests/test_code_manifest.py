"""C1 code_manifest: dirty-tree guard scoped to SOURCE paths only.

`is_source_path` is tested as a pure function. `build_code_manifest` is
tested both against a throwaway git repo built under `tmp_path` (so the
"runtime paths never count" and "non-source paths never count" cases can
be constructed precisely) and, as a smoke test, against this actual
worktree. All git calls are read-only (`git init`/`add`/`commit` only
inside `tmp_path`, `status`/`rev-parse` only against the real repo).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from coaching_loop.code_manifest import build_code_manifest, is_source_path

pytestmark = pytest.mark.skipif(
    subprocess.run(["git", "--version"], capture_output=True).returncode != 0,
    reason="git not available",
)


@pytest.mark.parametrize(
    "path",
    [
        "coaching_loop/hashing.py",
        "athletes/scripts/block_builder.py",
        "athletes/config/pipeline_settings.py",
        "coaching_loop/schemas/proposal_ir.schema.json",
        "athletes/config/nested/dir/file.py",
    ],
)
def test_source_paths_recognized(path):
    assert is_source_path(path) is True


@pytest.mark.parametrize(
    "path",
    [
        "athletes/roster/juan/journal.jsonl",
        "athletes/roster/juan/engine_state.yaml",
        "runs/2026-07-27/manifest.json",
        "approvals/wal/intent-0001.json",
        "README.md",
        "coaching_loop/fixtures/synthetic/tp_snapshot_900001.json",  # data fixture, not schema
    ],
)
def test_non_source_paths_excluded(path):
    assert is_source_path(path) is False


def test_runtime_prefix_wins_even_if_pattern_would_otherwise_match():
    # athletes/roster/**/*.py would match "*.py" by pattern alone -- the
    # runtime-prefix exclusion must win regardless.
    assert is_source_path("athletes/roster/juan/generated_helper.py") is False


def _init_repo(repo: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    (repo / "coaching_loop").mkdir(parents=True)
    (repo / "coaching_loop" / "hashing.py").write_text("# source\n")
    (repo / "athletes").mkdir()
    (repo / "athletes" / "roster").mkdir()
    (repo / "athletes" / "roster" / "journal.jsonl").write_text("{}\n")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "initial"], cwd=repo, check=True)


def test_clean_repo_reports_not_dirty(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    manifest = build_code_manifest(repo)
    assert manifest["dirty"] is False
    assert manifest["dirty_paths"] == []
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True, check=True
    ).stdout.strip()
    assert manifest["git_sha"] == sha


def test_dirty_source_file_flags_dirty(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    (repo / "coaching_loop" / "hashing.py").write_text("# changed\n")
    manifest = build_code_manifest(repo)
    assert manifest["dirty"] is True
    assert manifest["dirty_paths"] == ["coaching_loop/hashing.py"]


def test_dirty_runtime_only_file_does_not_flag_dirty(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    (repo / "athletes" / "roster" / "journal.jsonl").write_text('{"new": "line"}\n')
    manifest = build_code_manifest(repo)
    assert manifest["dirty"] is False
    assert manifest["dirty_paths"] == []


def test_dirty_non_source_file_does_not_flag_dirty(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    (repo / "README.md").write_text("# hi\n")
    manifest = build_code_manifest(repo)
    assert manifest["dirty"] is False
    assert manifest["dirty_paths"] == []


def test_new_untracked_source_file_flags_dirty(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    (repo / "coaching_loop" / "new_module.py").write_text("# new\n")
    manifest = build_code_manifest(repo)
    assert manifest["dirty"] is True
    assert "coaching_loop/new_module.py" in manifest["dirty_paths"]


def test_smoke_against_real_worktree_returns_full_sha_and_shape():
    manifest = build_code_manifest(Path(__file__).resolve().parents[2])
    assert len(manifest["git_sha"]) == 40
    assert all(c in "0123456789abcdef" for c in manifest["git_sha"])
    assert isinstance(manifest["dirty"], bool)
    assert isinstance(manifest["dirty_paths"], list)
