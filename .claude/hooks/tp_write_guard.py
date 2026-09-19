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
2. **Kernel-driven flows.** Code that loads an EXISTING script from a
   ``<publisher root>/*-publish/`` directory (the proven kernel scripts the
   coaching-ops skills delegate real writes to, e.g. ``sonja-publish/``,
   ``steve-publish/``, ``cheesehead-publish/``) is trusted. The publisher
   root is ``~/Library/Application Support/GravelGod/TrainingPeaksPublisher``
   (override with ``$GG_TP_PUBLISHER_ROOT`` for tests). A ``-publish/``
   string that does not resolve to a real file under that root is NOT a
   kernel read -- it was once a bare substring match, which a comment
   could satisfy.

Loaded scripts (security review, PR #260): a wrapper that reads a ``.js``
file from disk and evaluates it in the TP tab carries no write signal of
its own, so scanning only ``code`` missed the real write. The guard now
parses every ``readFileSync`` / ``readFile`` / ``require`` / ``import`` /
``createRequire`` call (comments stripped first), resolves the literal
path, reads the file, applies the same write-signal + TP-reference scan
to its contents, and follows loads inside loaded files transitively
(cycle-safe, hard cap of 64 files). Rules:
  - the path argument must be ONE string literal followed by ``,`` or
    ``)``. A variable, concatenation, ``path.join(...)``, template
    interpolation (other than ``${process.env.HOME}`` / ``${os.homedir()}``,
    which expand to ``~``) or ``fetch('file:...')`` is a DENY -- a script
    the guard cannot locate must not run against TrainingPeaks. Pass a
    literal path (absolute, ``~``, or relative to ``$CLAUDE_PROJECT_DIR`` /
    the cwd).
  - ``require``/``import`` literals are scripts whatever their extension
    (Node resolves ``.js``); ``readFileSync``/``readFile`` literals are
    scripts only when they end in ``.js``/``.mjs``/``.cjs`` -- ``.json``
    payloads and other data files are ignored.
  - a missing or unreadable script is a DENY.
  - the GG_BLESSED_TP_WRITE marker is only honored in ``code`` itself,
    never inside a loaded file (an agent could write it into a file).
  - ``trusted_script_paths()`` names the two reviewed weekly-drafts
    scripts by RESOLVED ABSOLUTE PATH, not by name: ``<publisher root>/
    plan-builds/_shared/upsert_draft_plan.js`` (plans/v1 writes only,
    refuses any plan not titled DRAFT) and ``<project dir>/tools/
    tp_weekly_packet.js`` (read-only; its one ``POST`` is the TP PMC
    reporting query, which takes a body). Those two files are allowed
    as-is; the same content anywhere else is scanned and denied. Adding a
    path is a reviewed change to this file, not a session-time edit.

What this guard is: a tripwire against straightforward and accidental
raw TP writes from an agent session. It is regex-based; an author who
deliberately obfuscates (``eval(atob(...))``, ``data:`` imports, string-
built verbs and hosts) can get past it. The skills' "only the named
scripts, never ad-hoc JS in the TP tab" rule is the real control; this
hook catches the honest mistakes.

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
GUARDED_TOOL = "mcp__playwriter__execute"

PUBLISHER_ROOT_ENV = "GG_TP_PUBLISHER_ROOT"
DEFAULT_PUBLISHER_ROOT = "~/Library/Application Support/GravelGod/TrainingPeaksPublisher"
SCRIPT_SUFFIXES = (".js", ".mjs", ".cjs")
MAX_LOADED_FILES = 64
_MAX_SCRIPT_BYTES = 2_000_000

# JS string literals (kept) vs. line/block comments (dropped) -- used so a
# commented-out load does not count, while a URL inside a string survives.
_STRING_OR_COMMENT_RE = re.compile(
    r"""("(?:\\.|[^"\\\n])*"|'(?:\\.|[^'\\\n])*'|`(?:\\.|[^`\\])*`)"""
    r"""|//[^\n]*|/\*[\s\S]*?\*/"""
)
LOAD_CALL_RE = re.compile(
    r"""\b(readFileSync|readFile|require|import|createRequire)\s*\(""",
    re.IGNORECASE,
)
_LITERAL_ARG_RE = re.compile(r"""\s*([`'"])((?:(?!\1).)*)\1\s*([,)])""")
FILE_URL_FETCH_RE = re.compile(r"""fetch\(\s*[`'"]file:""", re.IGNORECASE)
_HOME_INTERPOLATION_RE = re.compile(
    r"""\$\{\s*(?:process\.env\.HOME|os\.homedir\(\)|require\(['"]os['"]\)\.homedir\(\))\s*\}"""
)


def _strip_comments(code: str) -> str:
    return _STRING_OR_COMMENT_RE.sub(lambda m: m.group(1) or " ", code)


def _publisher_root() -> Path:
    raw = os.environ.get(PUBLISHER_ROOT_ENV) or DEFAULT_PUBLISHER_ROOT
    return Path(os.path.expanduser(raw)).resolve()


def _project_dirs() -> list[Path]:
    dirs = []
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR")
    if project_dir:
        dirs.append(Path(project_dir))
    dirs.append(Path.cwd())
    return dirs


def trusted_script_paths() -> set[Path]:
    """The two reviewed weekly-drafts scripts, by resolved absolute path."""
    trusted = {_publisher_root() / "plan-builds" / "_shared" / "upsert_draft_plan.js"}
    for base in _project_dirs():
        trusted.add((base / "tools" / "tp_weekly_packet.js").resolve())
    return trusted


def _is_kernel_script(path: Path) -> bool:
    root = _publisher_root()
    try:
        rel = path.relative_to(root)
    except ValueError:
        return False
    return bool(rel.parts) and rel.parts[0].endswith("-publish") and path.is_file()


def _resolve_script_path(raw: str) -> Path | None:
    """Turn a literal path into a resolved Path; ``None`` when the literal
    still needs JS evaluation (template interpolation)."""
    raw = _HOME_INTERPOLATION_RE.sub("~", raw)
    if "${" in raw:
        return None
    candidate = Path(os.path.expanduser(raw))
    if candidate.is_absolute():
        return candidate.resolve()
    bases = _project_dirs()
    for base in bases:
        joined = base / candidate
        if joined.exists():
            return joined.resolve()
    return (bases[0] / candidate).resolve()


def _script_loads(code: str) -> tuple[list[tuple[str, str]], list[str]]:
    """Parse the load calls in ``code``. Returns ``(loads, problems)`` where
    ``loads`` is ``[(call, literal)]`` for loads that name a script and
    ``problems`` explains every call whose argument is not one literal."""
    stripped = _strip_comments(code)
    loads: list[tuple[str, str]] = []
    problems: list[str] = []
    if FILE_URL_FETCH_RE.search(stripped):
        problems.append("fetch('file:...') is not an inspectable script load")
    for match in LOAD_CALL_RE.finditer(stripped):
        call = match.group(1)
        arg = _LITERAL_ARG_RE.match(stripped, match.end())
        if arg is None:
            problems.append(
                f"{call}(...) takes a non-literal path (variable, concatenation, "
                "path.join, ...) -- pass one literal path so the file can be scanned")
            continue
        literal = arg.group(2)
        if call.lower() == "createrequire":
            continue  # its argument is a base URL, not a script
        if call.lower() in ("require", "import"):
            loads.append((call, literal))
        elif literal.lower().endswith(SCRIPT_SUFFIXES):
            loads.append((call, literal))
    return loads, problems


def scan_loaded_scripts(code: str) -> tuple[list[str], list[str], list[str]]:
    """Resolve every script loaded by ``code`` (transitively) and scan each
    the way ``code`` itself is scanned. Returns ``(denials, trusted, kernel)``:
    denial reasons (empty when clean), trusted scripts that were loaded, and
    kernel (*-publish/) scripts that were loaded."""
    denials: list[str] = []
    trusted: list[str] = []
    kernel: list[str] = []
    seen: set[Path] = set()
    trusted_set = trusted_script_paths()
    worklist = [("code", code)]
    while worklist:
        origin, text = worklist.pop(0)
        loads, problems = _script_loads(text)
        denials.extend(f"{origin}: {problem}" for problem in problems)
        for call, literal in loads:
            path = _resolve_script_path(literal)
            if path is None:
                denials.append(
                    f"{origin}: {call}({literal!r}) is a template literal the guard "
                    "cannot resolve -- pass a literal path so the file can be scanned")
                continue
            if call.lower() in ("require", "import") and not path.exists():
                with_js = path.with_name(path.name + ".js")
                if with_js.exists():
                    path = with_js
            if path in seen:
                continue
            seen.add(path)
            if len(seen) > MAX_LOADED_FILES:
                denials.append(f"more than {MAX_LOADED_FILES} scripts loaded -- refusing to scan")
                return denials, trusted, kernel
            if path in trusted_set:
                trusted.append(path.as_posix())
                continue
            if _is_kernel_script(path):
                kernel.append(path.as_posix())
                continue
            try:
                if path.stat().st_size > _MAX_SCRIPT_BYTES:
                    raise OSError("file too large to scan")
                content = path.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                denials.append(
                    f"{origin}: loaded script {literal!r} could not be read "
                    f"({exc.__class__.__name__}) -- a script the guard cannot inspect "
                    "must not run against TrainingPeaks")
                continue
            if WRITE_VERB_RE.search(content) and TP_HOST_RE.search(content):
                denials.append(
                    f"loaded script {path.as_posix()} contains a raw TP write "
                    "(POST/PUT/PATCH/DELETE against a TrainingPeaks endpoint)")
                continue
            worklist.append((path.as_posix(), content))
    return denials, trusted, kernel


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

    denials, trusted, kernel = scan_loaded_scripts(code)
    if denials:
        return _deny(
            "tp_write_guard: blocked because " + "; ".join(denials) + ". "
            "Only the reviewed scripts named by trusted_script_paths() may be "
            "evaluated in the TP tab -- see .claude/hooks/tp_write_guard.py."
        )

    if kernel:
        return _allow(
            "tp_write_guard: kernel-script read (*-publish/) detected -- guard bypassed: "
            + ", ".join(kernel))

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
