#!/usr/bin/env python3
"""Shared immutable version stamps for Motoren-generated artifacts.

Both the public preview and paid-plan projections import this module so a
delivery receipt can prove which engine revision and Git-tracked coaching
voice produced it.  Keep this module dependency-light: PlanIR and the preview
engine both depend on it.
"""

from __future__ import annotations

import hashlib
import os
import re
import subprocess
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[2]
_VOICE_SOURCE_FILES = (
    "athletes/config/voice_rules.yaml",
    "athletes/scripts/story_notes.py",
    "athletes/scripts/delivery_notes.py",
    "athletes/scripts/apply_contract.py",
    "athletes/scripts/voice_lint.py",
)


def _git_short_sha() -> str:
    """Return the deployed Git revision, preferring Railway metadata."""
    configured = (
        os.environ.get("RAILWAY_GIT_COMMIT_SHA")
        or os.environ.get("GIT_SHA")
        or ""
    ).strip().lower()
    if re.fullmatch(r"[0-9a-f]{7,40}", configured):
        return configured[:7]
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(_REPO_ROOT), capture_output=True, text=True,
            check=True, timeout=10,
        )
        sha = result.stdout.strip()
        if sha and re.fullmatch(r"[0-9a-f]{4,40}", sha):
            return sha
    except Exception:
        pass
    return "unknown"


def _voice_digest() -> str:
    """Hash every Git-tracked source that defines athlete-facing voice."""
    digest = hashlib.sha256()
    try:
        for relative in _VOICE_SOURCE_FILES:
            path = _REPO_ROOT / relative
            digest.update(relative.encode("utf-8"))
            digest.update(b"\0")
            digest.update(path.read_bytes())
            digest.update(b"\0")
    except OSError:
        return "unknown"
    return digest.hexdigest()[:12]


ENGINE_VERSION = f"motoren/{_git_short_sha()}+ae-2026-08-23"
VOICE_VERSION = f"voice/{_voice_digest()}"


def engine_version() -> str:
    return ENGINE_VERSION


def voice_version() -> str:
    return VOICE_VERSION
