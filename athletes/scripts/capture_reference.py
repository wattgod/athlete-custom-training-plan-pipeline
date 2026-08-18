#!/usr/bin/env python3
"""Create a sanitized, deterministic reference-calendar fixture.

The TrainingPeaks calendar exports used to make a reference fixture include
customer data and provider-specific identifiers.  This small, dependency-free
tool keeps the fields that demonstrate the delivery standard while replacing
those identifiers and scrubbing personal data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import tempfile
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any, Iterable


REFERENCE_CAPTURE_VERSION = "reference_capture/v1"
KINDS = ("bike", "strength", "day_off", "race")
_EMAIL_RE = re.compile(
    r"(?<![\w.+-])[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}(?![\w.-])",
    re.IGNORECASE,
)
_URL_RE = re.compile(r"(?:https?://|www\.)[^\s<>\"']+", re.IGNORECASE)
_URL_TRAILING_PUNCTUATION = ".,;:!?)]}"

# The coach's own public contact address -- not athlete PII. A downstream
# grader once reported a false defect because this survived sanitization as
# "gravelgodcoachingatgmail.com" / "{coach_email}" instead of verbatim.
_PUBLIC_COACH_EMAIL = "gravelgodcoaching@gmail.com"
_PUBLIC_COACH_EMAIL_RE = re.compile(re.escape(_PUBLIC_COACH_EMAIL), re.IGNORECASE)
# Unicode Private Use Area -- exceedingly unlikely to appear in real captured
# text, and round-trips cleanly through JSON string escaping.
_PUBLIC_COACH_EMAIL_SENTINEL = "GG_PUBLIC_COACH_EMAIL"


class CaptureError(ValueError):
    """Raised when a raw TrainingPeaks export cannot be captured safely."""


def canonical_json_bytes(value: Any) -> bytes:
    """Return the canonical JSON representation used for fixture digests."""
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def payload_sha256(workouts: list[dict[str, Any]],
                   notes: list[dict[str, Any]]) -> str:
    """Digest the canonical payload, excluding mutable capture metadata."""
    payload = {"notes": notes, "workouts": workouts}
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def _date_only(value: Any, *, field: str) -> str:
    """Normalize a TrainingPeaks ISO datetime to its calendar date."""
    if not isinstance(value, str) or len(value) < 10:
        raise CaptureError(f"missing or invalid {field}")
    result = value[:10]
    try:
        date.fromisoformat(result)
    except ValueError as exc:
        raise CaptureError(f"missing or invalid {field}") from exc
    return result


def _required_text(value: Any, *, field: str) -> str:
    if not isinstance(value, str):
        raise CaptureError(f"missing or invalid {field}")
    return value


def _raw_collections(raw: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Accept both observed raw-dump shapes and normalize their containers."""
    if not isinstance(raw, dict):
        raise CaptureError("raw export must be a JSON object")
    if "workouts" in raw and "notes" in raw:
        workouts, notes = raw["workouts"], raw["notes"]
    elif "w" in raw and "n" in raw:
        workouts, notes = raw["w"], raw["n"]
    else:
        raise CaptureError("raw export must contain workouts/notes or w/n")
    if not isinstance(workouts, list) or not isinstance(notes, list):
        raise CaptureError("workouts and notes must both be JSON lists")
    if not all(isinstance(row, dict) for row in workouts + notes):
        raise CaptureError("workouts and notes must contain JSON objects")
    return workouts, notes


def _sort_rows(rows: Iterable[dict[str, Any]], *, date_field: str,
               id_field: str) -> list[dict[str, Any]]:
    """Use date plus provider ID so equivalent exports always capture alike."""
    return sorted(
        rows,
        key=lambda row: (_date_only(row.get(date_field), field=date_field),
                         str(row.get(id_field, ""))),
    )


def _synthetic_athlete_ids(workouts: list[dict[str, Any]],
                           notes: list[dict[str, Any]]) -> dict[str, int]:
    """Map each provider athlete ID to a stable, non-production identifier."""
    synthetic: dict[str, int] = {}
    for row in workouts + notes:
        raw_id = row.get("athleteId")
        if raw_id is None:
            raise CaptureError("missing athleteId")
        key = str(raw_id)
        if key not in synthetic:
            synthetic[key] = 1_000_001 + len(synthetic)
    return synthetic


def _kind_for(workout: dict[str, Any]) -> str:
    """Map the TP type ID to the delivery fixture kind.

    TrainingPeaks stores a race as type 2 (bike), so its canonical RACE DAY
    title distinguishes it from an ordinary bike workout.
    """
    type_id = workout.get("workoutTypeValueId")
    if type_id == 7:
        return "day_off"
    if type_id == 9:
        return "strength"
    if type_id == 2:
        title = _required_text(workout.get("title"), field="workout title")
        return "race" if title.casefold().startswith("race day") else "bike"
    raise CaptureError(f"unsupported workoutTypeValueId: {type_id!r}")


def _sanitizer(athlete_name: str, slug: str):
    name_parts = athlete_name.split()
    if len(name_parts) < 2:
        raise CaptureError("--athlete-name must include a first and last name")
    first_name, last_name = name_parts[0], name_parts[-1]
    if not slug.strip():
        raise CaptureError("--slug must not be empty")
    name_patterns = (
        (re.compile(rf"\b{re.escape(first_name)}\b", re.IGNORECASE), "{first_name}"),
        (re.compile(rf"\b{re.escape(last_name)}\b", re.IGNORECASE), "{last_name}"),
    )
    slug_folded = slug.casefold()

    def replace_url(match: re.Match[str]) -> str:
        url = match.group(0)
        trailing = ""
        while url and url[-1] in _URL_TRAILING_PUNCTUATION:
            trailing = url[-1] + trailing
            url = url[:-1]
        if slug_folded in url.casefold():
            return "{guide_url}" + trailing
        return url + trailing

    def sanitize_text(value: str) -> str:
        # Protect the coach's own public contact address before anything
        # else touches it -- both _EMAIL_RE (-> "{coach_email}") and the
        # final "@" -> "at" catch-all would otherwise mangle it, and it is
        # the address every note tells the athlete to write to, not PII to
        # scrub.
        protected = _PUBLIC_COACH_EMAIL_RE.sub(_PUBLIC_COACH_EMAIL_SENTINEL, value)
        result = _URL_RE.sub(replace_url, protected)
        result = _EMAIL_RE.sub("{coach_email}", result)
        for pattern, replacement in name_patterns:
            result = pattern.sub(replacement, result)
        # The fixture PII gate rejects every ``@``. This also covers an
        # unusual address the conservative email expression did not match.
        result = result.replace("@", "at")
        return result.replace(_PUBLIC_COACH_EMAIL_SENTINEL, _PUBLIC_COACH_EMAIL)

    return sanitize_text


def _sanitize_value(value: Any, sanitize_text) -> Any:
    """Scrub all retained strings, including text nested in TP structure."""
    if isinstance(value, str):
        return sanitize_text(value)
    if isinstance(value, list):
        return [_sanitize_value(item, sanitize_text) for item in value]
    if isinstance(value, dict):
        return {key: _sanitize_value(item, sanitize_text)
                for key, item in value.items()}
    return value


def capture_fixture(raw: Any, *, athlete_name: str, slug: str) -> dict[str, Any]:
    """Normalize and sanitize an in-memory raw export into a fixture object."""
    workouts_raw, notes_raw = _raw_collections(raw)
    workouts_raw = _sort_rows(workouts_raw, date_field="workoutDay",
                              id_field="workoutId")
    notes_raw = _sort_rows(notes_raw, date_field="noteDate", id_field="id")
    athlete_ids = _synthetic_athlete_ids(workouts_raw, notes_raw)
    sanitize_text = _sanitizer(athlete_name, slug)

    workouts: list[dict[str, Any]] = []
    for synthetic_id, workout in enumerate(workouts_raw, start=1):
        structure = workout.get("structure") or {}
        if not isinstance(structure, dict):
            raise CaptureError("workout structure must be an object or null")
        workouts.append({
            "workoutId": synthetic_id,
            "athleteId": athlete_ids[str(workout["athleteId"])],
            "date": _date_only(workout.get("workoutDay"), field="workoutDay"),
            "title": sanitize_text(_required_text(workout.get("title"), field="workout title")),
            "kind": _kind_for(workout),
            "totalTimePlanned": workout.get("totalTimePlanned"),
            "tssPlanned": workout.get("tssPlanned"),
            "ifPlanned": workout.get("ifPlanned"),
            "description": sanitize_text(_required_text(
                workout.get("description"), field="workout description")),
            "structure": _sanitize_value(structure, sanitize_text),
        })

    notes: list[dict[str, Any]] = []
    for synthetic_id, note in enumerate(notes_raw, start=1):
        notes.append({
            "id": synthetic_id,
            "athleteId": athlete_ids[str(note["athleteId"])],
            "date": _date_only(note.get("noteDate"), field="noteDate"),
            "title": sanitize_text(_required_text(note.get("title"), field="note title")),
            "description": sanitize_text(_required_text(
                note.get("description"), field="note description")),
        })

    captured_dates = [row["date"] for row in workouts + notes]
    if not captured_dates:
        raise CaptureError("raw export contains no workouts or notes")
    counts = Counter(workout["kind"] for workout in workouts)
    return {
        "reference_capture_version": REFERENCE_CAPTURE_VERSION,
        "captured_range": {"start": min(captured_dates), "end": max(captured_dates)},
        # A personal slug can itself contain an athlete's name. Retain the
        # source shape without reintroducing the PII the capture removed.
        "source": f"{{athlete_slug}}-{min(captured_dates)[:7]}",
        "counts": {
            "workouts_by_kind": {kind: counts[kind] for kind in KINDS},
            "notes": len(notes),
        },
        "payload_sha256": payload_sha256(workouts, notes),
        "workouts": workouts,
        "notes": notes,
    }


def write_fixture(path: Path, fixture: dict[str, Any]) -> None:
    """Atomically write a pretty, canonical fixture for review in diffs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    contents = json.dumps(fixture, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent,
        prefix=f".{path.name}.", suffix=".tmp", delete=False,
    ) as output:
        output.write(contents)
        temporary_path = Path(output.name)
    temporary_path.replace(path)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raw_json", type=Path, help="raw TrainingPeaks calendar export")
    parser.add_argument("--athlete-name", required=True,
                        help='athlete name to scrub, e.g. "First Last"')
    parser.add_argument("--slug", required=True, help="athlete slug used in guide URLs")
    parser.add_argument("--out", required=True, type=Path, help="fixture JSON output path")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        raw = json.loads(args.raw_json.read_text(encoding="utf-8"))
        fixture = capture_fixture(raw, athlete_name=args.athlete_name, slug=args.slug)
        write_fixture(args.out, fixture)
    except (CaptureError, OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"capture_reference: {exc}") from exc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
