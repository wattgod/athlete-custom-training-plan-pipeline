#!/usr/bin/env python3
"""PreToolUse guard for mcp__playwriter__execute: blocks unblessed TP writes.

This repo's playwright transport (mcp__playwriter__execute) can run
arbitrary browser-context JS. A hand-rolled POST/PUT/DELETE against a live
TrainingPeaks endpoint from an ad-hoc session is exactly the failure mode
the tp-dynamic-plan-builder skill's hard rails exist to prevent (see
plugins/endure-coaching-ops/skills/tp-dynamic-plan-builder/SKILL.md --
"Plan library only", "NO EXCEPTIONS FOR TEST ATHLETES") -- a wrong write
against an athlete's live calendar or plan container is not reversible by
just re-running something.

This hook denies any mcp__playwriter__execute call whose ``code`` contains
BOTH a write signal AND a reference to TrainingPeaks (a host, or a
host-less TP API path -- page-context code often builds a relative URL
against whatever origin it's already running on):

  Write signals (any quoting/spacing, verbs POST/PUT/PATCH/DELETE):
    - a ``method`` key: ``method: "POST"``, ``"method":'PUT'``, etc.
    - ``.post(``/``.put(``/``.patch(``/``.delete(``
    - ``XMLHttpRequest``-style ``.open("POST", ...)`` (any quote)
    - ``.sendBeacon(`` (always a fire-and-forget POST)

  TrainingPeaks references:
    - any ``trainingpeaks.com`` or ``peakswaresb.com`` substring (matches
      every subdomain, e.g. tpapi.trainingpeaks.com)
    - a host-less TP API path: ``/plans/v1``..``/fitness/v1``-``/fitness/v6``,
      ``/rx/activity``, ``/exerciselibrary``, ``/calendarNote``

Escape hatches (both intentionally narrow, and only honored once the input
has parsed successfully -- see "Fail closed" below):

1. **The GG_BLESSED_TP_WRITE marker.** A code string containing the literal
   comment ``/* GG_BLESSED_TP_WRITE */`` bypasses the guard. This exists for
   a human who has read the write, confirmed it targets the right plan/
   athlete, and is deliberately running it in a coach-supervised session --
   NOT for an agent to add to its own code to self-authorize. Ad-hoc TP
   writes that reach for this marker still need explicit, coach-visible
   justification (say so in the session transcript) -- the marker is an
   audit trail, not a rubber stamp.
2. **Kernel-driven flows.** Code that reads a script out of a
   ``TrainingPeaksPublisher/*-publish/`` directory (the proven kernel
   scripts referenced by the coaching-ops skills, e.g. ``sonja-publish/``,
   ``steve-publish/``, ``cheesehead-publish/``) is trusted -- those scripts
   are the reviewed, proven transport this repo's skills already delegate
   real writes to.

Loaded scripts (security review, PR #260): a wrapper that reads a ``.js``
file from disk and evaluates it in the TP tab carries no write signal of
its own, so scanning only ``code`` missed the real write. The guard now
also resolves every literal script path handed to ``readFileSync`` /
``readFile`` / ``require`` / ``import`` (``*.js``, ``*.mjs``, ``*.cjs``;
``.json`` and other data files are ignored), reads the file, and applies
the same write-signal + TP-reference scan to its contents, following one
further level of loads inside it. Rules:
  - a path that cannot be resolved (template literal, variable, missing
    file, unreadable) is a DENY -- a script the guard cannot inspect must
    not run against TrainingPeaks; pass a literal path (absolute, ``~``,
    or relative to ``$CLAUDE_PROJECT_DIR`` / the cwd).
  - the GG_BLESSED_TP_WRITE marker is only honored in ``code`` itself,
    never inside a loaded file (an agent could write it into a file).
  - ``TRUSTED_LOADED_SCRIPTS`` names the two reviewed weekly-drafts
    scripts by path suffix: ``plan-builds/_shared/upsert_draft_plan.js``
    (plans/v1 writes only, refuses any plan not titled DRAFT) and
    ``tools/tp_weekly_packet.js`` (read-only; its one ``POST`` is the TP
    PMC reporting query, which takes a body). They are allowed as-is.
    Adding a path here is a reviewed change, not a session-time edit.

Fail CLOSED, not open: any exception while parsing stdin, malformed JSON,
a non-object payload, or a missing/non-string ``code`` on a call this hook
must evaluate (i.e. not already known to be some OTHER tool) emits a DENY
decision, not ``{}``. Hooks communicate their decision via the JSON on
stdout, not the process exit code -- ``main()`` always exits 0 and lets the
JSON payload carry the verdict. The ONLY unconditional-allow shortcut is a
successfully parsed payload whose ``tool_name`` is present and is some tool
other than ``mcp__playwriter__execute`` -- everything else (including a
missing/empty ``tool_name``) is evaluated defensively rather than assumed
safe, since the guard must not rely on settings.json's matcher alone to
scope invocation.

This hook only ever intervenes to DENY; it never grants a blanket allow
that would override any other permission control.

NOTE: this guards THIS repo's Claude Code sessions only. It has no effect
on writes made outside this tool (e.g. a human driving the TP web UI
directly, or a script run outside of mcp__playwriter__execute).
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

WRITE_VERB_RE = re.compile(
    r"""("""
    r"""['"]?method['"]?\s*:\s*['"](POST|PUT|PATCH|DELETE)['"]"""  # method: "POST" / 'method':'PUT' / "method":"PATCH"
    r"""|\.(post|put|patch|delete)\("""                              # .post( / .put( / .patch( / .delete(
    r"""|\.open\(\s*['"](POST|PUT|PATCH|DELETE)['"]"""               # XHR-style .open("POST", ...)
    r"""|\.sendBeacon\("""                                           # sendBeacon( -- always a write
    r""")""",
    re.IGNORECASE,
)
TP_HOST_RE = re.compile(
    r"""("""
    r"""trainingpeaks\.com"""       # any subdomain, e.g. tpapi.trainingpeaks.com
    r"""|peakswaresb\.com"""
    r"""|/plans/v1"""               # host-less TP API paths (page-context relative URLs)
    r"""|/fitness/v[1-6]"""
    r"""|/rx/activity"""
    r"""|/exerciselibrary"""
    r"""|/calendarNote"""
    r""")""",
    re.IGNORECASE,
)
BLESSED_MARKER = "/* GG_BLESSED_TP_WRITE */"
KERNEL_READ_RE = re.compile(
    r"""readFileSync\(\s*[`'"][^`'"]*TrainingPeaksPublisher/[^`'"/]+-publish/""",
    re.IGNORECASE,
)

LOADED_SCRIPT_RE = re.compile(
    r"""(?:readFileSync|readFile|require|import)\(\s*([`'"])([^`'"]+?\.[cm]?js)\1""",
    re.IGNORECASE,
)
# Path SUFFIXES of the reviewed weekly-drafts transport scripts. Matched
# against the resolved, normalised path, so an absolute or relative spelling
# of the same file both qualify. Keep this list short and reviewed.
TRUSTED_LOADED_SCRIPTS = (
    "TrainingPeaksPublisher/plan-builds/_shared/upsert_draft_plan.js",
    "tools/tp_weekly_packet.js",
)
MAX_LOAD_DEPTH = 2
_MAX_SCRIPT_BYTES = 2_000_000

GUARDED_TOOL = "mcp__playwriter__execute"


def _allow(message: str | None = None) -> dict:
    """No opinion / explicit bypass -- normal permission flow proceeds."""
    return {"systemMessage": message} if message else {}


def _deny(reason: str) -> dict:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        },
        "systemMessage": reason,
    }


def _resolve_script_path(raw: str) -> Path | None:
    """Turn a literal path from a load call into a Path. ``None`` when the
    literal is not resolvable without running JS (template interpolation)."""
    if "${" in raw:
        return None
    raw = os.path.expanduser(raw)
    candidate = Path(raw)
    if candidate.is_absolute():
        return candidate
    bases = []
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR")
    if project_dir:
        bases.append(Path(project_dir))
    bases.append(Path.cwd())
    for base in bases:
        joined = base / candidate
        if joined.exists():
            return joined
    return bases[0] / candidate


def _is_trusted_script(path: Path) -> bool:
    normalised = path.as_posix()
    return any(normalised.endswith(suffix) for suffix in TRUSTED_LOADED_SCRIPTS)


def scan_loaded_scripts(code: str, depth: int = 1,
                        seen: set[str] | None = None) -> tuple[list[str], list[str]]:
    """Resolve every literal ``*.js`` path loaded by ``code`` and scan the
    file the way ``code`` itself is scanned. Returns ``(denials, trusted)``:
    denial reasons (empty when clean) and the trusted scripts that were
    loaded (for the audit message)."""
    seen = set() if seen is None else seen
    denials: list[str] = []
    trusted: list[str] = []
    for match in LOADED_SCRIPT_RE.finditer(code):
        raw = match.group(2)
        path = _resolve_script_path(raw)
        if path is None:
            denials.append(
                f"loaded script path {raw!r} is a template literal the guard cannot "
                "resolve -- pass a literal path so the file can be scanned")
            continue
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        if _is_trusted_script(path):
            trusted.append(path.as_posix())
            continue
        try:
            if path.stat().st_size > _MAX_SCRIPT_BYTES:
                raise OSError("file too large to scan")
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            denials.append(
                f"loaded script {raw!r} could not be read ({exc.__class__.__name__}) "
                "-- a script the guard cannot inspect must not run against TrainingPeaks")
            continue
        if WRITE_VERB_RE.search(content) and TP_HOST_RE.search(content):
            denials.append(
                f"loaded script {path.as_posix()} contains a raw TP write "
                "(POST/PUT/PATCH/DELETE against a TrainingPeaks endpoint)")
            continue
        if depth < MAX_LOAD_DEPTH:
            nested_denials, nested_trusted = scan_loaded_scripts(
                content, depth + 1, seen)
            denials.extend(nested_denials)
            trusted.extend(nested_trusted)
    return denials, trusted


def evaluate(tool_name: str, tool_input: dict) -> dict:
    if tool_name and tool_name != GUARDED_TOOL:
        return _allow()

    code = tool_input.get("code") or ""

    if BLESSED_MARKER in code:
        return _allow(
            "tp_write_guard: GG_BLESSED_TP_WRITE marker present -- guard bypassed.")

    if KERNEL_READ_RE.search(code):
        return _allow(
            "tp_write_guard: kernel-script read (*-publish/) detected -- guard bypassed.")

    denials, trusted = scan_loaded_scripts(code)
    if denials:
        return _deny(
            "tp_write_guard: blocked because " + "; ".join(denials) + ". "
            "Only the reviewed scripts named in TRUSTED_LOADED_SCRIPTS may be "
            "evaluated in the TP tab -- see .claude/hooks/tp_write_guard.py."
        )

    if WRITE_VERB_RE.search(code) and TP_HOST_RE.search(code):
        return _deny(
            "tp_write_guard: blocked a raw TP write (POST/PUT/PATCH/DELETE) against a "
            "TrainingPeaks endpoint without the GG_BLESSED_TP_WRITE marker. "
            "Ad-hoc TP writes need explicit, coach-visible justification -- see "
            ".claude/hooks/tp_write_guard.py for the escape hatches."
        )

    if trusted:
        return _allow(
            "tp_write_guard: trusted loaded script(s) allowed: " + ", ".join(trusted))
    return _allow()


def main() -> int:
    """Always exits 0 -- the JSON on stdout carries the decision. Any
    failure to cleanly parse stdin into {tool_name: str?, tool_input: dict?,
    tool_input.code: str} on a call this hook must evaluate is a DENY
    (fail closed), never a silent ``{}`` (fail open)."""
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
        if not isinstance(payload, dict):
            raise ValueError("hook payload must be a JSON object")

        tool_name = payload.get("tool_name")
        if tool_name is not None and not isinstance(tool_name, str):
            raise ValueError("tool_name must be a string")

        if tool_name and tool_name != GUARDED_TOOL:
            # The ONLY unconditional-allow shortcut: a cleanly parsed
            # payload that is definitely some OTHER tool.
            print(json.dumps(_allow()))
            return 0

        tool_input = payload.get("tool_input")
        if tool_input is None:
            tool_input = {}
        if not isinstance(tool_input, dict):
            raise ValueError("tool_input must be an object")

        code = tool_input.get("code")
        if code is not None and not isinstance(code, str):
            raise ValueError("tool_input.code must be a string")
        if not code:
            raise ValueError("tool_input.code is missing or empty")

    except Exception:
        print(json.dumps(_deny(
            "tp_write_guard could not parse input — failing closed")))
        return 0

    result = evaluate(tool_name or GUARDED_TOOL, tool_input)
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
