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
import re
import sys

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

    if WRITE_VERB_RE.search(code) and TP_HOST_RE.search(code):
        return _deny(
            "tp_write_guard: blocked a raw TP write (POST/PUT/PATCH/DELETE) against a "
            "TrainingPeaks endpoint without the GG_BLESSED_TP_WRITE marker. "
            "Ad-hoc TP writes need explicit, coach-visible justification -- see "
            ".claude/hooks/tp_write_guard.py for the escape hatches."
        )

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
