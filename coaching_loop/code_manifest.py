"""C1 code_manifest: git SHA + dirty-tree guard scoped to SOURCE paths only.

docs/COACHING_LOOP_SPEC.md, C1: "code_manifest (sol r2 f6, luna r2 f1):
git SHA + dirty-tree guard scoped to SOURCE paths only (*.py,
athletes/config/**, schema files). Machine-owned runtime paths --
athletes/roster/*/journal.jsonl, engine_state.yaml, runs/**,
approvals/WAL files -- are .gitignore'd working data, excluded from both
the dirty check and code_manifest, so the loop's own writes never block
the next run or shift the manifest."

Read-only: `git status` + `git rev-parse HEAD` against the given repo
root. No git writes, no network, no mutation of any kind.
"""

from __future__ import annotations

import fnmatch
import subprocess
from pathlib import Path

# fnmatch's "*" already matches "/" (it compiles to regex ".*"), so
# "athletes/config/**" and "athletes/config/*" behave identically here --
# written with "**" to mirror the spec text literally.
SOURCE_GLOBS = ("*.py", "athletes/config/**", "*.schema.json")

# Machine-owned runtime paths, excluded from the dirty check regardless
# of whether they happen to match a SOURCE_GLOBS pattern.
RUNTIME_PATH_PREFIXES = (
    "athletes/roster/",  # journal.jsonl, engine_state.yaml live under here
    "runs/",
    "approvals/",
)


def is_source_path(path: str) -> bool:
    """True if `path` (repo-relative, forward slashes) is a SOURCE path
    per C1's dirty-tree guard scope."""
    if any(path.startswith(prefix) for prefix in RUNTIME_PATH_PREFIXES):
        return False
    return any(fnmatch.fnmatch(path, pattern) for pattern in SOURCE_GLOBS)


def _git(args: list[str], repo_root: Path) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def build_code_manifest(repo_root: str | Path) -> dict:
    """{git_sha, dirty, dirty_paths} for the worktree at `repo_root`,
    scoped to SOURCE paths only. `git status --porcelain
    --untracked-files=all` (one line per file, not per directory) +
    `git rev-parse HEAD`. Read-only.
    """
    repo_root = Path(repo_root)
    git_sha = _git(["rev-parse", "HEAD"], repo_root).strip()
    status_output = _git(["status", "--porcelain", "--untracked-files=all"], repo_root)

    dirty_paths: list[str] = []
    for line in status_output.splitlines():
        if not line.strip():
            continue
        # Porcelain v1 format: "XY <path>" or "XY <old> -> <new>" for renames.
        path = line[3:].split(" -> ")[-1].strip()
        if is_source_path(path):
            dirty_paths.append(path)

    return {
        "git_sha": git_sha,
        "dirty": bool(dirty_paths),
        "dirty_paths": sorted(dirty_paths),
    }
