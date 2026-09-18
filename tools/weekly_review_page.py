#!/usr/bin/env python3
"""One HTML review page for a weekly-draft-plan run (Motoren spec Part B).

Spec: docs/specs/2026-09-18-variety-and-weekly-dynamic-plans.md, "B --
implementation plan": "one page, per athlete: profile diff, block shape
(weekly hours/TSS vs 6-wk demonstrated and CTL), variety block, lint
verdict, 'the 3 lines Matti would tell the athlete'." Read-only: this
tool never writes to the repo, ``builds_root``, or TrainingPeaks -- it
only reads ``draft_manifest.json`` (and, for the "three lines" section,
the run's notes payload) and writes the single ``--out`` HTML file.

Athlete discovery: every ``<builds_root>/<athlete_id>/weekly-<run_date>/``
directory that has a ``draft_manifest.json`` is one card on the page (in
that sense ``tools/weekly_draft_plan.py`` IS the roster for a run -- it
wrote one manifest per athlete it processed, "skipped"/"held"/"built"
alike).

Data sources per athlete, all under
``builds_root/<athlete_id>/weekly-<run_date>/``:
  - ``draft_manifest.json`` -- status, title, plan_day_one, per_week
    (week/hours/tss), notes_count, lint, variety, fallbacks, and the
    whole ``refresh_diff`` dict (see weekly_draft_plan.py's docstring for
    its assumed shape): ``holds``, ``writes`` (profile changes, each
    ``{path, old, new, source}``), ``standing_contradictions``,
    ``demonstrated`` (``{hours_6wk, tss_6wk, ctl}``).
  - ``notes_payload_final.json`` (falling back to ``notes_payload.json``)
    -- only read for the "Three lines to <First>" section, and only when
    present (a "skipped"/"held" run has no fresh notes payload for this
    run date; that section is simply empty).

"Three lines to <First name>" -- the spec's "3 lines Matti would tell the
athlete": the first sentence of the description of each of the first
three Monday-dated notes (the weekly story notes; mid-week notes are not
Mondays), in date order, prefixed DRAFT.

Run-1 banner (``--run-1``): the exact text from the spec's "Run 1 note"
for the review page, for the pilot's very first run only -- distinguishes
the DRAFT plan from the athlete's already-published live calendar so it
does not read as a second copy to reconcile. Off by default; the spec
ties this text to "Run 1" specifically, not every run.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any, Mapping, Sequence

MANIFEST_FILENAME = "draft_manifest.json"

RUN_1_NOTE = (
    "Run 1 note: Forest/Ed/Ari live calendars already carry the same "
    "blocks (published Sep 17); the drafts are the “what Motoren "
    "would do from next Monday” view Matti copies from, not a "
    "second copy to reconcile."
)

STATUS_LABELS = {"built": "BUILT", "skipped": "SKIPPED", "held": "HELD"}


# --------------------------------------------------------------------------
# data loading
# --------------------------------------------------------------------------

def _read_json(path: Path) -> Any:
    if not path.exists():
        return None
    return json.loads(path.read_text())


def discover_athletes(builds_root: Path, run_date: str) -> list[tuple[str, Path]]:
    """Every ``<athlete_id>`` directory under ``builds_root`` that has a
    ``draft_manifest.json`` for this ``run_date``, sorted by id."""
    found: list[tuple[str, Path]] = []
    if not builds_root.exists():
        return found
    for child in sorted(builds_root.iterdir()):
        if not child.is_dir():
            continue
        manifest_path = child / f"weekly-{run_date}" / MANIFEST_FILENAME
        if manifest_path.exists():
            found.append((child.name, manifest_path))
    return found


def _load_notes(run_dir: Path) -> list[dict]:
    for name in ("notes_payload_final.json", "notes_payload.json"):
        data = _read_json(run_dir / name)
        if isinstance(data, list):
            return data
    return []


_SENTENCE_RE = re.compile(r"(.+?[.!?])(\s|$)")


_SKIP_OPENER_RE = re.compile(r"^(week\s+\d+\s+of\s+\d+|\d+[.)]|[-*])\s*[.:]?\s*$", re.I)


def _first_sentence(text: str) -> str:
    """First sentence that says something: "Week 1 of 7." style openers
    and bare list markers are skipped."""
    text = (text or "").strip()
    if not text:
        return ""
    for raw in re.split(r"(?<=[.!?])\s+|\n+", text):
        cand = raw.strip().lstrip("-*• ").strip()
        if not cand or _SKIP_OPENER_RE.match(cand):
            continue
        match = _SENTENCE_RE.search(cand)
        return (match.group(1).strip() if match else cand)
    return ""


def _monday_notes(notes: list[dict]) -> list[dict]:
    dated: list[tuple[date, dict]] = []
    for note in notes:
        try:
            d = date.fromisoformat(str(note.get("noteDate"))[:10])
        except (ValueError, TypeError):
            continue
        if d.weekday() == 0:  # Monday
            dated.append((d, note))
    dated.sort(key=lambda pair: pair[0])
    # Prefer the weekly story notes ("Week 3: Build"); the Day-1 comment
    # protocol shares the Monday and is not the message of the week. Fall
    # back to every Monday note when no note is titled that way.
    weekly = [n for _, n in dated if re.match(r"^\s*week\s+\d+\b", str(n.get("title") or ""), re.I)]
    return weekly or [note for _, note in dated]


def _first_name(name: str | None) -> str:
    name = (name or "").strip()
    return name.split()[0] if name else "the athlete"


# --------------------------------------------------------------------------
# HTML rendering (no external assets; system fonts; dense; readable at
# 400px -- tables get their own horizontal scroller rather than the page
# body scrolling)
# --------------------------------------------------------------------------

def _e(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def _table(headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> str:
    if not rows:
        return "<p class=\"empty\">none</p>"
    head = "".join(f"<th>{_e(h)}</th>" for h in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{_e(cell)}</td>" for cell in row) + "</tr>"
        for row in rows
    )
    return f"<div class=\"twrap\"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>"


def _render_athlete(athlete_id: str, manifest: Mapping[str, Any], run_dir: Path) -> str:
    status = str(manifest.get("status", "?"))
    status_label = STATUS_LABELS.get(status, status.upper())
    name = manifest.get("name") or athlete_id
    title = manifest.get("title") or ""
    refresh_diff = manifest.get("refresh_diff") or {}
    holds = refresh_diff.get("holds") or []
    writes = refresh_diff.get("writes") or []
    demonstrated = refresh_diff.get("demonstrated") or {}
    per_week = manifest.get("per_week") or []
    lint = manifest.get("lint") or {}
    variety = manifest.get("variety") or {}
    fallbacks = manifest.get("fallbacks", 0)
    notes_list = manifest.get("notes") or []

    sections = []

    sections.append(
        f"<div class=\"hdr\"><span class=\"status s-{status}\">{_e(status_label)}</span>"
        f"<h2>{_e(name)}</h2><span class=\"title\">{_e(title)}</span></div>"
    )

    if writes:
        rows = [
            (w.get("path", ""), f"{w.get('old', '')} → {w.get('new', '')}", w.get("source", ""))
            for w in writes
        ]
        sections.append("<h3>Profile changes</h3>" + _table(["field", "old → new", "source"], rows))

    if holds:
        rows = []
        for h in holds:
            sources = ", ".join(str(s) for s in (h.get("sources") or []))
            rows.append((h.get("type", ""), h.get("message", ""), sources))
        sections.append("<h3>Holds</h3>" + _table(["type", "message", "sources"], rows))

    if status == "built":
        demo_hours = demonstrated.get("hours_6wk")
        demo_tss = demonstrated.get("tss_6wk")
        ctl = demonstrated.get("ctl")
        if isinstance(ctl, (int, float)):
            ctl = round(ctl)
        rows = [(w.get("week"), w.get("hours"), w.get("tss")) for w in per_week]
        block_table = _table(["week", "hours", "TSS"], rows)
        demo_line = (
            f"<p class=\"meta\">6-wk demonstrated: {_e(demo_hours)}h / {_e(demo_tss)} TSS "
            f"&middot; CTL {_e(ctl)}</p>"
            if demonstrated else ""
        )
        sections.append(f"<h3>Block shape</h3>{block_table}{demo_line}")

        pool = variety.get("pool_utilisation") or {}
        pool_line = ", ".join(f"{k}: {v.get('used')}/{v.get('pool')}" for k, v in pool.items())
        sections.append(
            "<h3>Variety</h3><p class=\"meta\">"
            f"distinct items {_e(variety.get('distinct_items'))} &middot; "
            f"families {_e(variety.get('distinct_families'))} &middot; "
            f"series {_e(len(variety.get('series') or []))}"
            + (f" &middot; pool {_e(pool_line)}" if pool_line else "")
            + "</p>"
        )

        sections.append(
            "<h3>Lint</h3><p class=\"meta\">"
            f"fail {_e(lint.get('fail', 0))} &middot; warn {_e(lint.get('warn', 0))} "
            f"&middot; allow-listed {_e(lint.get('allow_listed', 0))}</p>"
        )
        sections.append(f"<h3>Fallbacks</h3><p class=\"meta\">{_e(fallbacks)}</p>")

        notes_payload = _load_notes(run_dir)
        monday_notes = _monday_notes(notes_payload)[:3]
        if monday_notes:
            lines = "".join(
                f"<li>{_e(_first_sentence(n.get('description')))}</li>" for n in monday_notes
            )
            sections.append(
                f"<h3>Three lines to {_e(_first_name(manifest.get('name')))} (DRAFT)</h3>"
                f"<ol class=\"lines\">{lines}</ol>"
            )

    if notes_list:
        sections.append(
            "<h3>Run notes</h3><ul class=\"lines\">"
            + "".join(f"<li>{_e(n)}</li>" for n in notes_list)
            + "</ul>"
        )

    return f"<section class=\"athlete\">{''.join(sections)}</section>"


CSS = """
:root{color-scheme:light dark;--bg:#fff;--fg:#111;--muted:#666;--line:#ddd;
--built:#0a7a2f;--skipped:#8a6d00;--held:#a4001d;--card:#fafafa}
@media(prefers-color-scheme:dark){:root{--bg:#111;--fg:#eee;--muted:#aaa;
--line:#333;--built:#4fd67a;--skipped:#e0c34a;--held:#ff6b7a;--card:#1a1a1a}}
*{box-sizing:border-box}
body{margin:0;padding:12px;background:var(--bg);color:var(--fg);
font-family:-apple-system,system-ui,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
font-size:14px;line-height:1.4}
h1{font-size:18px;margin:0 0 8px}
h2{font-size:16px;margin:0 8px 0 0;display:inline}
h3{font-size:12px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);
margin:10px 0 4px}
.banner{background:var(--card);border:1px solid var(--line);border-radius:4px;
padding:8px 10px;margin-bottom:10px;font-size:13px}
.athlete{border:1px solid var(--line);border-radius:6px;background:var(--card);
padding:10px;margin-bottom:10px}
.hdr{display:flex;align-items:baseline;gap:8px;flex-wrap:wrap}
.status{font-size:11px;font-weight:700;letter-spacing:.05em;border-radius:3px;
padding:2px 6px;color:#fff}
.status.s-built{background:var(--built)}
.status.s-skipped{background:var(--skipped)}
.status.s-held{background:var(--held)}
.title{color:var(--muted);font-size:13px}
.meta{margin:2px 0;color:var(--muted)}
.empty{margin:2px 0;color:var(--muted)}
.twrap{overflow-x:auto}
table{border-collapse:collapse;width:100%;font-size:13px}
th,td{border:1px solid var(--line);padding:3px 6px;text-align:left;
white-space:nowrap}
td:nth-child(2){white-space:normal}
.lines{margin:2px 0;padding-left:18px}
"""


def render(athletes: Sequence[tuple[str, Mapping[str, Any], Path]], run_date: str, run_1: bool) -> str:
    body = [f"<h1>Weekly drafts &mdash; {_e(run_date)}</h1>"]
    if run_1:
        body.append(f"<div class=\"banner\">{_e(RUN_1_NOTE)}</div>")
    if not athletes:
        body.append("<p class=\"empty\">no athlete manifests found for this run date</p>")
    for athlete_id, manifest, run_dir in athletes:
        body.append(_render_athlete(athlete_id, manifest, run_dir))
    return (
        "<!doctype html><html><head><meta charset=\"utf-8\">"
        f"<title>Weekly drafts {_e(run_date)}</title><style>{CSS}</style>"
        f"</head><body>{''.join(body)}</body></html>\n"
    )


def build_page(builds_root: Path, run_date: str, run_1: bool = False) -> str:
    athletes = []
    for athlete_id, manifest_path in discover_athletes(builds_root, run_date):
        manifest = _read_json(manifest_path) or {}
        athletes.append((athlete_id, manifest, manifest_path.parent))
    return render(athletes, run_date, run_1)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--builds-root", required=True)
    parser.add_argument("--run-date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--out", required=True)
    parser.add_argument("--run-1", action="store_true",
                         help="include the spec's Run 1 disclaimer banner")
    args = parser.parse_args(argv)

    html_out = build_page(Path(args.builds_root), args.run_date, run_1=args.run_1)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html_out)
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
