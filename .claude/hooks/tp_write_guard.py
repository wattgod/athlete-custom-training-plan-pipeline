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
2. (Removed 2026-09-19.) A ``*-publish/`` kernel-directory read used to
   switch the guard off for the whole call. Those directories hold JSON
   receipts, not scripts, so the hatch amounted to "read any existing
   receipt, then write anything" -- reachable by one ``ls``. Legacy
   kernel flows that write from the wrapper now use the marker above,
   which is the coach-visible audit trail they should have had.

Loaded scripts (security review, PR #260): a wrapper that reads a ``.js``
file from disk and evaluates it in the TP tab carries no write signal of
its own, so scanning only ``code`` missed the real write. The guard now
parses every ``readFileSync`` / ``readFile`` / ``require`` / ``import``
call, resolves the literal path, reads the file, applies the same
write-signal + TP-reference scan to its contents, and follows loads
inside loaded files transitively (cycle-safe, hard cap of 64 files).
Rules:
  - the path argument must be ONE string literal followed by ``,`` or
    ``)``. A variable, concatenation, ``path.join(...)``, template
    interpolation (other than ``${process.env.HOME}`` / ``${os.homedir()}``,
    which expand to ``~``) or ``fetch('file:...')`` is a DENY -- a script
    the guard cannot locate must not run against TrainingPeaks. Pass a
    literal path (absolute, ``~``, or relative to ``$CLAUDE_PROJECT_DIR``,
    falling back to the cwd only when that variable is unset).
  - the loader must be called directly. ``readFileSync`` / ``readFile`` /
    ``require`` referenced without an immediate ``(`` (aliased, passed
    around, ``require.resolve``), a computed member on ``fs`` (``fs[...]``)
    or ``createRequire`` is a DENY.
  - the scan runs on the raw ``code``: comments are NOT stripped, because
    a JS regex literal such as ``/[//]/`` makes any comment stripper lose
    real code. A load that sits in a comment or a string therefore still
    counts and fails closed (missing file -> DENY); delete the comment.
  - ``require``/``import`` literals that are package or builtin names
    (``'node:fs'``, ``'fs'``, ``'path'``: no ``/``, not starting with
    ``.`` or ``~``) are not files and are ignored; path-shaped literals
    are scripts whatever their extension (Node resolves ``.js``).
    ``readFileSync``/``readFile`` literals are scripts only when they end
    in ``.js``/``.mjs``/``.cjs`` -- ``.json`` payloads are ignored.
  - a ``readFileSync``/``readFile`` literal that is not a script is still
    read: ``.json`` must parse as JSON (data cannot be evaluated), every
    other extension is scanned exactly like a script -- a TP write in a
    ``.txt`` or extensionless file is the same write.
  - inside a loaded module, ``./`` and ``../`` ``require``/``import``
    literals resolve against THAT module's directory (Node semantics);
    static ``import x from '...'`` / ``export ... from '...'`` count as
    loads too.
  - a call that loads any file from disk must not also modify the
    filesystem or spawn a process (``writeFileSync``, ``copyFileSync``,
    ``rename``, ``symlink``, ``child_process``, ``execSync`` ...): the
    scan happens before the call runs, so a copy-then-load in one call
    would evaluate bytes the guard never saw. Split it into two calls.
  - a missing or unreadable script is a DENY.
  - Playwright's own injection calls are loads too: ``addScriptTag`` /
    ``addInitScript`` / ``addStyleTag`` are allowed only as
    ``({ path: '<literal>' })`` (the file is scanned like any script);
    ``url:``, ``content:`` and non-literal forms are a DENY.
  - the GG_BLESSED_TP_WRITE marker is only honored in ``code`` itself,
    never inside a loaded file (an agent could write it into a file).
  - ``trusted_script_paths()`` names the two reviewed weekly-drafts
    scripts by RESOLVED ABSOLUTE PATH, and ``TRUSTED_SCRIPT_HASHES`` pins
    their CONTENT (SHA-256): ``<publisher root>/plan-builds/_shared/
    upsert_draft_plan.js`` (plans/v1 writes only, refuses any plan not
    titled DRAFT) and ``<project dir>/tools/tp_weekly_packet.js``
    (read-only; its one ``POST`` is the TP PMC reporting query, which
    takes a body). Hashing normalises CRLF and the trailing newline so an
    editor save is not a false alarm. A trusted path whose content does
    not match its hash is a DENY that quotes the actual digest -- editing
    either script means re-reviewing it and updating the hash here
    (``python3 tp_write_guard.py --print-hashes`` prints both). The same
    content anywhere else is scanned and denied.

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

import hashlib
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
# SHA-256 of the two trusted scripts' contents. Editing a script = re-review + update here.
TRUSTED_SCRIPT_HASHES = {
    "upsert_draft_plan.js": "4507002ab7172530f67cdf29671217e6b7cc25b550974aab7b4817e8893f4078",
    "tp_weekly_packet.js": "e56fa9180a3e31a9d73f229730cadc0de2197ffa4fed9c1d5d790aed6940e6fe",
}
SCRIPT_SUFFIXES = (".js", ".mjs", ".cjs")
MAX_LOADED_FILES = 64
_MAX_SCRIPT_BYTES = 2_000_000

LOAD_CALL_RE = re.compile(
    r"""\b(readFileSync|readFile|require|import)\s*\(""",
    re.IGNORECASE,
)
_LITERAL_ARG_RE = re.compile(r"""\s*([`'"])((?:(?!\1).)*)\1\s*([,)])""")
FILE_URL_FETCH_RE = re.compile(r"""fetch\(\s*[`'"]file:""", re.IGNORECASE)
# A loader named but not called right there: aliased, destructured, passed.
# Token-shaped (must be followed by JS punctuation) so prose in a comment or
# string ("you require a token") does not trip it.
LOADER_ALIAS_RE = re.compile(
    r"""\b(readFileSync|readFile|require)\b\s*(?=[;,)\]}=.]|$)|\bcreateRequire\b|\bfs\s*\[""",
    re.IGNORECASE | re.MULTILINE,
)
# ES module static loads inside a loaded file.
STATIC_IMPORT_RE = re.compile(
    r"""\b(?:import\s+(?:[\w$*\s{},]+?\s+from\s+)?|export\s+[\w$*\s{},]+?\s+from\s+)([`'"])([^`'"]+)\1"""
)
# Filesystem mutation / process spawning. Forbidden in the same call as a load.
MUTATION_RE = re.compile(
    r"""\b(writeFileSync|writeFile|copyFileSync|copyFile|renameSync|rename|appendFileSync|appendFile"""
    r"""|symlinkSync|symlink|linkSync|truncateSync|truncate|createWriteStream|rmSync|rmdirSync|unlinkSync|unlink"""
    r"""|chmodSync|chmod|child_process|execSync|execFileSync|spawnSync|spawn|execFile|cpSync)\s*\(""",
)
# Playwright file injection: page.addScriptTag({ path }) etc. Only the
# ``{ path: '<literal>' }`` form is followable; everything else is denied.
INJECT_CALL_RE = re.compile(r"""\b(addScriptTag|addInitScript|addStyleTag)\s*\(""")
_INJECT_PATH_ARG_RE = re.compile(
    r"""\s*\{\s*path\s*:\s*([`'"])((?:(?!\1).)*)\1\s*,?\s*\}\s*\)""")
_HOME_INTERPOLATION_RE = re.compile(
    r"""\$\{\s*(?:process\.env\.HOME|os\.homedir\(\)|require\(['"]os['"]\)\.homedir\(\))\s*\}"""
)


def _publisher_root() -> Path:
    raw = os.environ.get(PUBLISHER_ROOT_ENV) or DEFAULT_PUBLISHER_ROOT
    return Path(os.path.expanduser(raw)).resolve()


def _project_dirs() -> list[Path]:
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR")
    return [Path(project_dir)] if project_dir else [Path.cwd()]


def trusted_script_paths() -> set[Path]:
    """The two reviewed weekly-drafts scripts, by resolved absolute path."""
    trusted = {(_publisher_root() / "plan-builds" / "_shared" / "upsert_draft_plan.js").resolve()}
    for base in _project_dirs():
        trusted.add((base / "tools" / "tp_weekly_packet.js").resolve())
    return trusted


def _is_bare_specifier(literal: str) -> bool:
    """``'fs'``, ``'node:fs'``, ``'lodash'``: a module name, not a file path."""
    if literal.startswith("node:"):
        return True
    return "/" not in literal and "\\" not in literal and not literal.startswith((".", "~"))


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


def _loads(code: str) -> tuple[list[tuple[str, str, bool]], list[str]]:
    """Parse the load calls in ``code``. Returns ``(loads, problems)``:
    ``loads`` is ``[(call, literal, is_script)]`` for every literal load
    (data files included, flagged ``is_script=False``); ``problems``
    explains every load shape the guard cannot follow."""
    loads: list[tuple[str, str, bool]] = []
    problems: list[str] = []
    if FILE_URL_FETCH_RE.search(code):
        problems.append("fetch('file:...') is not an inspectable script load")
    alias = LOADER_ALIAS_RE.search(code)
    if alias:
        problems.append(
            f"loader referenced without a direct call ({alias.group(0).strip()!r}) -- "
            "call readFileSync/readFile/require directly with one literal path")
    for match in INJECT_CALL_RE.finditer(code):
        call = match.group(1)
        arg = _INJECT_PATH_ARG_RE.match(code, match.end())
        if arg is None:
            problems.append(
                f"{call}(...) is only allowed as {{ path: '<literal>' }} -- url:, "
                "content: and non-literal forms cannot be scanned")
            continue
        loads.append((call, arg.group(2), True))
    for match in LOAD_CALL_RE.finditer(code):
        call = match.group(1)
        arg = _LITERAL_ARG_RE.match(code, match.end())
        if arg is None:
            problems.append(
                f"{call}(...) takes a non-literal path (variable, concatenation, "
                "path.join, ...) -- pass one literal path so the file can be scanned")
            continue
        literal = arg.group(2)
        if call.lower() in ("require", "import"):
            if _is_bare_specifier(literal):
                continue
            loads.append((call, literal, True))
        else:
            loads.append((call, literal, literal.lower().endswith(SCRIPT_SUFFIXES)))
    for match in STATIC_IMPORT_RE.finditer(code):
        literal = match.group(2)
        if not _is_bare_specifier(literal):
            loads.append(("import", literal, True))
    return loads, problems


def _resolve_load(call: str, literal: str, origin_dir: Path | None) -> Path | None:
    """``./``/``../`` module specifiers inside a loaded module resolve
    against that module's directory; everything else as a plain path."""
    if origin_dir is not None and call.lower() in ("require", "import") \
            and literal.startswith(("./", "../")):
        return (origin_dir / literal).resolve()
    return _resolve_script_path(literal)


def content_digest(content_bytes: bytes) -> str:
    """SHA-256 of a script with CRLF and the trailing newline normalised."""
    normalised = content_bytes.replace(b"\r\n", b"\n").rstrip(b"\n") + b"\n"
    return hashlib.sha256(normalised).hexdigest()


def scan_loaded_scripts(code: str) -> tuple[list[str], list[str]]:
    """Resolve every file loaded by ``code`` (scripts transitively) and scan
    each script the way ``code`` itself is scanned. Returns ``(denials,
    trusted)``: denial reasons (empty when clean) and the trusted scripts
    that were loaded."""
    denials: list[str] = []
    trusted: list[str] = []
    seen: set[Path] = set()
    trusted_set = trusted_script_paths()
    worklist: list[tuple[str, str, Path | None]] = [("code", code, None)]
    while worklist:
        origin, text, origin_dir = worklist.pop(0)
        loads, problems = _loads(text)
        denials.extend(f"{origin}: {problem}" for problem in problems)
        if loads:
            mutation = MUTATION_RE.search(text)
            if mutation:
                denials.append(
                    f"{origin}: loads a file and also calls {mutation.group(1)}(...) -- the "
                    "scan runs before the call, so a file changed in the same call would be "
                    "evaluated unscanned; split the write and the load into two calls")
        for call, literal, is_script in loads:
            path = _resolve_load(call, literal, origin_dir)
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
                denials.append(f"more than {MAX_LOADED_FILES} files loaded -- refusing to scan")
                return denials, trusted
            try:
                if path.stat().st_size > _MAX_SCRIPT_BYTES:
                    raise OSError("file too large to scan")
                content_bytes = path.read_bytes()
            except OSError as exc:
                denials.append(
                    f"{origin}: loaded file {literal!r} could not be read "
                    f"({exc.__class__.__name__}) -- a file the guard cannot inspect "
                    "must not run against TrainingPeaks")
                continue
            if path in trusted_set:
                expected = TRUSTED_SCRIPT_HASHES.get(path.name)
                actual = content_digest(content_bytes)
                if expected and actual == expected:
                    trusted.append(path.as_posix())
                else:
                    denials.append(
                        f"trusted script {path.as_posix()} does not match its reviewed "
                        f"SHA-256 (actual {actual}) -- re-review it and update "
                        "TRUSTED_SCRIPT_HASHES")
                continue
            content = content_bytes.decode("utf-8", errors="replace")
            if not is_script and path.suffix.lower() == ".json":
                try:
                    json.loads(content)
                except ValueError:
                    denials.append(
                        f"loaded file {path.as_posix()} is named .json but is not JSON")
                continue
            if WRITE_VERB_RE.search(content) and TP_HOST_RE.search(content):
                denials.append(
                    f"loaded file {path.as_posix()} contains a raw TP write "
                    "(POST/PUT/PATCH/DELETE against a TrainingPeaks endpoint)")
                continue
            worklist.append((path.as_posix(), content, path.parent))
    return denials, trusted


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

    denials, trusted = scan_loaded_scripts(code)
    if denials:
        return _deny(
            "tp_write_guard: blocked because " + "; ".join(denials) + ". "
            "Only the reviewed scripts named by trusted_script_paths() may be "
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


def print_hashes() -> int:
    for path in sorted(trusted_script_paths()):
        try:
            print(f"{content_digest(path.read_bytes())}  {path}")
        except OSError as exc:
            print(f"(unreadable: {exc.__class__.__name__})  {path}")
    return 0


if __name__ == "__main__":
    if "--print-hashes" in sys.argv[1:]:
        raise SystemExit(print_hashes())
    raise SystemExit(main())
