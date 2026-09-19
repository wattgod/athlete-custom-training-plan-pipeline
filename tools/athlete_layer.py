#!/usr/bin/env python3
"""Apply a per-athlete rules.yaml to plan_payload.json / notes_payload.json.

Replaces the bespoke `athlete_layer.py` scripts that used to live one per
athlete under the private build dir (`plan-builds/<athlete>/athlete_layer.py`,
each hand-editing a `plan_payload.json` + `notes_payload.json` pair into
`plan_payload_final.json` + `notes_payload_final.json`). Those scripts
encoded per-athlete rules as ad hoc Python; this module encodes them as data
(`rules.yaml`) and applies one fixed transform pipeline to it, per spec
`docs/specs/2026-09-18-variety-and-weekly-dynamic-plans.md` section B,
revision-2 decision 8.

Vocabulary (every key `rules.yaml` may set; all optional -- an absent key is
a no-op for that step). Two keys are engine-gap stop-gaps, noted below;
everything else is permanent athlete data (coaching rules that belong to the
athlete, not to a missing engine feature):

  title_format: "plain" | "duration_lead"
      duration_lead rewrites non-rest-day titles to "NN min -- Title" (NN =
      round(totalTimePlanned * 60)). Idempotent: an existing "OPTIONAL:"
      prefix is stripped before rebuilding and the OPTIONAL state is carried
      forward into the new title. Rest days (workoutTypeValueId == 7, or a
      title starting with "Rest Day") are never touched.

  title_allowlist_prefixes: [str]
      Title prefixes (after OPTIONAL: state is stripped) that are exempt
      from the optional_intensity detector below -- they always render as
      plain duration_lead titles. A title already matching "^\\d+ min --" is
      left exactly as-is (no double duration prefix).

  optional_intensity: {enabled: bool, text: str, intensity_detector: {...}}
      intensity_detector: {power_pct_gte: number, exclude_units: [str],
      type_ids: [int], title_regex: str}. A workout whose workoutTypeValueId
      is in type_ids and either (a) already carries an OPTIONAL title, (b)
      has a structure step target >= power_pct_gte on a unit not in
      exclude_units, or (c) has a title matching title_regex, gets an
      "OPTIONAL " title prefix; if enabled and its description does not
      already start with "OPTIONAL", `text` is prepended (blank line
      separated). The idempotency check is literal ("does the description
      already start with OPTIONAL"), not a check against `text` itself --
      write `text` to start with "OPTIONAL" (as every ported rules.yaml
      does) or reruns will double it. ENGINE GAP: this is `intensity_policy`
      from the athlete
      profile -- the renderer does not read it yet, so this key is the
      stop-gap until it does.

  force_optional_dates: [YYYY-MM-DD]
      Any workout on one of these dates whose workoutTypeValueId is in
      optional_intensity.intensity_detector.type_ids is forced OPTIONAL
      (title + description) even if the detector above would not have
      flagged it -- a travel/commitment override the engine's overlay missed
      on the coached path.

  strip_sentences: [regex]
      Each regex is removed (re.sub -> '') from every workout description,
      then the description is stripped. ENGINE GAP: this is `nutrition_policy`
      forbidden-language enforcement (no calorie/deficit/weight-loss
      language) plus any other per-athlete sentence ban -- the renderer's
      boilerplate does not consult either policy yet.

  replace_text: [{scope: "descriptions"|"notes"|"titles", from: str, to: str}]
      Plain str.replace, applied in list order. scope "descriptions" is
      workout descriptions, "notes" is note descriptions, "titles" is
      workout titles.

  title_strip_regex: [regex]
      Each regex is removed (re.sub -> '') from every workout title.

  guardrails: [{title_match_regex: str, text: str}]
      For every workout whose title matches title_match_regex, append `text`
      to its description unless `text.strip()` is already present
      (idempotent -- reruns do not double the guardrail).

  commitment_notes: [{date: YYYY-MM-DD, title: str, description: str}]
      Coach-authored notes appended verbatim (as {title, noteDate,
      description}) after every other note transform.

  drop_rest_on_multi_session_days: bool
      Drop Rest Day (workoutTypeValueId == 7) entries on any calendar day
      that also carries another workout.

  drop_notes: [{date: YYYY-MM-DD, title_contains: str}]
      Drop any note whose noteDate == date and whose title contains
      title_contains.

  drop_workouts: [{date: YYYY-MM-DD, title_contains: str}]
      Drop any workout whose day == date and whose title contains
      title_contains (e.g. the engine's Rest Day filler on a day a TP
      event already owns).

  note_prefix: {title_regex: str, exclude_title_contains: [str], text: str}
      For every note whose title matches title_regex and does not contain
      any of exclude_title_contains, prepend `text` (blank line separated)
      unless the description already starts with it.

  note_date_remap: [{title_prefix: str, to_date: YYYY-MM-DD}]
      Applied last, over every note (engine notes and commitment_notes
      alike): a note whose title starts with title_prefix gets its noteDate
      set to to_date.

  race_card: bool
      Always false today. Race-day description tailoring
      (plan-builds/<athlete>/race_card.py) is a separate, per-athlete script
      this layer does not reproduce -- an engine gap raised, not routed
      around. When false (the only supported value), the race-day
      description passes through unchanged.

CLI:
  python -m tools.athlete_layer --rules plan-builds/<athlete>/rules.yaml \\
      --in-dir plan-builds/<athlete>/<build> --out-dir plan-builds/<athlete>/<build>

  Reads plan_payload.json / notes_payload.json from --in-dir, applies
  --rules, writes plan_payload_final.json / notes_payload_final.json to
  --out-dir with json.dump(indent=1, ensure_ascii=False) -- the exact
  serialization the bespoke scripts used.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - pyyaml is a repo dependency
    yaml = None

Workout = dict[str, Any]
Note = dict[str, Any]
ChangeLog = list[tuple[str, str, str]]

REST_DAY_TYPE_ID = 7


def _day(w: dict) -> str:
    return (w.get("workoutDay") or "")[:10]


def _is_rest_day(w: Workout) -> bool:
    return w.get("workoutTypeValueId") == REST_DAY_TYPE_ID or str(w.get("title", "")).startswith("Rest Day")


def _is_optional(title: str) -> bool:
    return title.startswith("OPTIONAL")


def _strip_optional_colon(title: str) -> str:
    return re.sub(r"^OPTIONAL:\s*", "", title)


def _matches_intensity_detector(w: Workout, detector: dict) -> bool:
    power_pct_gte = detector.get("power_pct_gte")
    exclude_units = set(detector.get("exclude_units") or [])
    structure = w.get("structure")
    if power_pct_gte is not None and isinstance(structure, dict):
        for blk in structure.get("structure") or []:
            for step in blk.get("steps") or []:
                for t in step.get("targets") or []:
                    if t.get("unit") in exclude_units:
                        continue
                    value = t.get("maxValue") or t.get("minValue") or 0
                    if value >= power_pct_gte:
                        return True
    title_regex = detector.get("title_regex")
    if title_regex and re.search(title_regex, w.get("title", ""), re.I):
        return True
    return False


def _apply_title_format(plan: list[Workout], rules: dict, changed: ChangeLog) -> None:
    title_format = rules.get("title_format")
    if title_format != "duration_lead":
        return
    allowlist_prefixes = rules.get("title_allowlist_prefixes") or []
    optional_intensity = rules.get("optional_intensity") or {}
    detector = optional_intensity.get("intensity_detector") or {}
    type_ids = set(detector.get("type_ids") or [])
    optional_text = optional_intensity.get("text", "")
    enabled = bool(optional_intensity.get("enabled"))

    for w in plan:
        title = w["title"]
        kind = w.get("workoutTypeValueId")
        if _is_rest_day(w):
            continue
        mins = round((w.get("totalTimePlanned") or 0) * 60)
        base = _strip_optional_colon(title)
        already_optional = _is_optional(title)

        allowlisted = any(base.startswith(p) for p in allowlist_prefixes)
        if allowlisted:
            new_title = base if re.match(r"^\d+ min —", base) else f"{mins} min — {base}"
        elif kind in type_ids and (already_optional or _matches_intensity_detector(w, detector)):
            new_title = f"OPTIONAL {mins} min — {base}"
            if enabled:
                d = w.get("description") or ""
                if not d.startswith("OPTIONAL"):
                    w["description"] = optional_text + "\n\n" + d
        else:
            new_title = f"{mins} min — {base}"

        if new_title != title:
            changed.append((_day(w), title, new_title))
            w["title"] = new_title


def _apply_force_optional_dates(plan: list[Workout], rules: dict, changed: ChangeLog) -> None:
    dates = set(rules.get("force_optional_dates") or [])
    if not dates:
        return
    optional_intensity = rules.get("optional_intensity") or {}
    detector = optional_intensity.get("intensity_detector") or {}
    type_ids = set(detector.get("type_ids") or [])
    optional_text = optional_intensity.get("text", "")
    for w in plan:
        if _day(w) not in dates or w.get("workoutTypeValueId") not in type_ids:
            continue
        if _is_optional(w["title"]):
            continue
        old = w["title"]
        w["title"] = "OPTIONAL " + old
        w["description"] = optional_text + "\n\n" + (w.get("description") or "")
        changed.append((_day(w), "forced optional", w["title"]))


def _apply_strip_sentences(plan: list[Workout], rules: dict, changed: ChangeLog) -> None:
    patterns = rules.get("strip_sentences") or []
    if not patterns:
        return
    for w in plan:
        d = w.get("description") or ""
        d2 = d
        for pattern in patterns:
            d2 = re.sub(pattern, "", d2, flags=re.I)
        d2 = d2.strip()
        if d2 != d:
            w["description"] = d2
            changed.append((_day(w), "stripped sentence", w["title"]))


def _apply_replace_text(plan: list[Workout], notes: list[Note], rules: dict, changed: ChangeLog) -> None:
    entries = rules.get("replace_text") or []
    for entry in entries:
        scope = entry["scope"]
        frm, to = entry["from"], entry["to"]
        if scope == "descriptions":
            for w in plan:
                d = w.get("description") or ""
                if frm in d:
                    w["description"] = d.replace(frm, to)
                    changed.append((_day(w), "replace_text", w["title"]))
        elif scope == "titles":
            for w in plan:
                t = w["title"]
                if frm in t:
                    new_t = t.replace(frm, to)
                    changed.append((_day(w), t, new_t))
                    w["title"] = new_t
        elif scope == "notes":
            for n in notes:
                d = n.get("description") or ""
                if frm in d:
                    n["description"] = d.replace(frm, to)
                    changed.append((n.get("noteDate", ""), "replace_text note", n["title"]))
        else:
            raise ValueError(f"replace_text: unknown scope {scope!r}")


def _apply_title_strip_regex(plan: list[Workout], rules: dict, changed: ChangeLog) -> None:
    patterns = rules.get("title_strip_regex") or []
    if not patterns:
        return
    for w in plan:
        t = w["title"]
        t2 = t
        for pattern in patterns:
            t2 = re.sub(pattern, "", t2)
        if t2 != t:
            changed.append((_day(w), t, t2))
            w["title"] = t2


def _apply_guardrails(plan: list[Workout], rules: dict, changed: ChangeLog) -> None:
    guardrails = rules.get("guardrails") or []
    if not guardrails:
        return
    for w in plan:
        for g in guardrails:
            if not re.search(g["title_match_regex"], w["title"]):
                continue
            text = g["text"]
            d = w.get("description") or ""
            if text.strip() in d:
                continue
            w["description"] = d.rstrip() + text
            changed.append((_day(w), "guardrail", w["title"]))


def _apply_race_card(plan: list[Workout], rules: dict, changed: ChangeLog) -> None:
    if rules.get("race_card"):
        raise NotImplementedError(
            "race_card: true is not implemented in tools/athlete_layer.py -- "
            "race-day description tailoring is a per-athlete script "
            "(plan-builds/<athlete>/race_card.py), an engine gap, not a "
            "rules.yaml stop-gap. Set race_card: false."
        )


def _apply_drop_rest_on_multi_session_days(plan: list[Workout], rules: dict, changed: ChangeLog) -> list[Workout]:
    if not rules.get("drop_rest_on_multi_session_days"):
        return plan
    by_day: dict[str, list[Workout]] = defaultdict(list)
    for w in plan:
        by_day[_day(w)].append(w)
    kept = []
    for w in plan:
        if w.get("workoutTypeValueId") == REST_DAY_TYPE_ID and len(by_day[_day(w)]) > 1:
            changed.append((_day(w), "dropped rest day (multi-session)", w["title"]))
            continue
        kept.append(w)
    return kept


def _apply_drop_workouts(plan: list[Workout], rules: dict, changed: ChangeLog) -> list[Workout]:
    drops = rules.get("drop_workouts") or []
    if not drops:
        return plan
    kept = []
    for w in plan:
        drop = any(_day(w) == d["date"] and d["title_contains"] in (w.get("title") or "") for d in drops)
        if drop:
            changed.append((_day(w), "dropped workout", w.get("title", "")))
            continue
        kept.append(w)
    return kept


def _apply_drop_notes(notes: list[Note], rules: dict, changed: ChangeLog) -> list[Note]:
    drops = rules.get("drop_notes") or []
    if not drops:
        return notes
    kept = []
    for n in notes:
        drop = any(n.get("noteDate") == d["date"] and d["title_contains"] in n["title"] for d in drops)
        if drop:
            changed.append((n.get("noteDate", ""), "dropped note", n["title"]))
            continue
        kept.append(n)
    return kept


def _apply_note_prefix(notes: list[Note], rules: dict, changed: ChangeLog) -> None:
    note_prefix = rules.get("note_prefix")
    if not note_prefix:
        return
    title_regex = note_prefix["title_regex"]
    exclude = note_prefix.get("exclude_title_contains") or []
    text = note_prefix["text"]
    for n in notes:
        title = n["title"]
        if not re.search(title_regex, title):
            continue
        if any(x in title for x in exclude):
            continue
        d = n.get("description") or ""
        if d.startswith(text):
            continue
        n["description"] = text + d
        changed.append((n.get("noteDate", ""), "note_prefix", title))


def _build_commitment_notes(rules: dict) -> list[Note]:
    entries = rules.get("commitment_notes") or []
    return [{"title": e["title"], "noteDate": e["date"], "description": e["description"]} for e in entries]


def _apply_note_date_remap(notes: list[Note], rules: dict, changed: ChangeLog) -> None:
    remaps = rules.get("note_date_remap") or []
    if not remaps:
        return
    for n in notes:
        for r in remaps:
            if n["title"].startswith(r["title_prefix"]):
                if n.get("noteDate") != r["to_date"]:
                    changed.append((n.get("noteDate", ""), "note_date_remap", n["title"]))
                    n["noteDate"] = r["to_date"]
                break


def apply(plan: list[Workout], notes: list[Note], rules: dict) -> tuple[list[Workout], list[Note], ChangeLog]:
    """Apply `rules` (the parsed rules.yaml dict) to `plan` + `notes`.

    Mutates and returns new top-level lists (workout/note dicts inside are
    mutated in place, matching the bespoke scripts' behaviour); does not
    read or write any file. Returns (plan, notes, changed_log) where
    changed_log is a list of (date_or_key, before, after) tuples in
    application order, for the CLI's --verbose printout and for tests.
    """
    plan = list(plan)
    notes = list(notes)
    changed: ChangeLog = []

    _apply_title_format(plan, rules, changed)
    _apply_force_optional_dates(plan, rules, changed)
    _apply_strip_sentences(plan, rules, changed)
    _apply_replace_text(plan, notes, rules, changed)
    _apply_title_strip_regex(plan, rules, changed)
    _apply_guardrails(plan, rules, changed)
    _apply_race_card(plan, rules, changed)
    plan = _apply_drop_rest_on_multi_session_days(plan, rules, changed)
    plan = _apply_drop_workouts(plan, rules, changed)

    notes = _apply_drop_notes(notes, rules, changed)
    _apply_note_prefix(notes, rules, changed)
    notes = notes + _build_commitment_notes(rules)
    _apply_note_date_remap(notes, rules, changed)

    return plan, notes, changed


# --------------------------------------------------------------------- cli

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--rules", required=True, type=Path, help="path to rules.yaml")
    parser.add_argument("--in-dir", required=True, type=Path,
                         help="dir containing plan_payload.json + notes_payload.json")
    parser.add_argument("--out-dir", required=True, type=Path,
                         help="destination for plan_payload_final.json + notes_payload_final.json")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if yaml is None:  # pragma: no cover
        print("athlete_layer: pyyaml is required", file=sys.stderr)
        return 2

    rules = yaml.safe_load(args.rules.read_text()) or {}
    plan = json.loads((args.in_dir / "plan_payload.json").read_text())
    notes = json.loads((args.in_dir / "notes_payload.json").read_text())

    try:
        plan, notes, changed = apply(plan, notes, rules)
    except (KeyError, ValueError, NotImplementedError) as exc:
        print(f"athlete_layer: {exc}", file=sys.stderr)
        return 2

    args.out_dir.mkdir(parents=True, exist_ok=True)
    with open(args.out_dir / "plan_payload_final.json", "w") as f:
        json.dump(plan, f, indent=1, ensure_ascii=False)
    with open(args.out_dir / "notes_payload_final.json", "w") as f:
        json.dump(notes, f, indent=1, ensure_ascii=False)

    for c in changed:
        print(c)
    print(f"athlete_layer: {len(plan)} workouts, {len(notes)} notes, {len(changed)} changes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
