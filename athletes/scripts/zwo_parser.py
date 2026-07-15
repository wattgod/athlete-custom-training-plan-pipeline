#!/usr/bin/env python3
"""Shared ZWO parsing for package inspection and PlanIR aggregation.

This module deliberately reads rendered ZWO files.  It does not participate in
workout generation; consumers can use the flattened power samples for metrics
or the preserved structural segments for a faithful representation of XML.
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Tuple


def parse_zwo_structure(zwo_path: Path) -> Dict[str, Any]:
    """Parse a ZWO file without unrolling its top-level XML structure.

    ``power_samples`` is intentionally expanded only for the existing TSS
    calculation.  ``segments`` retains one entry per ZWO element, including a
    single typed entry for each ``IntervalsT`` block.
    """
    tree = ET.parse(zwo_path)
    root = tree.getroot()
    name_el = root.find("name")
    desc_el = root.find("description")
    name = name_el.text if name_el is not None else zwo_path.stem
    description = desc_el.text if desc_el is not None else ""
    workout = root.find("workout")
    if workout is None:
        return {
            "name": name,
            "description": description,
            "segments": [],
            "power_samples": [],
            "intervals_summary": [],
        }

    segments: List[Dict[str, Any]] = []
    power_samples: List[Tuple[float, float]] = []
    intervals_summary: List[str] = []

    for element in workout:
        tag = element.tag
        if tag in ("Warmup", "Cooldown", "Ramp"):
            duration = float(element.get("Duration", 0))
            low = float(element.get("PowerLow", 0.5))
            high_default = 0.4 if tag == "Cooldown" else 0.7 if tag == "Warmup" else 0.8
            high = float(element.get("PowerHigh", high_default))
            segments.append({
                "name": tag,
                "kind": tag.lower(),
                "seconds": int(duration),
                "power_low": low,
                "power_high": high,
            })
            power_samples.append((duration, (low + high) / 2))
        elif tag == "SteadyState":
            duration = float(element.get("Duration", 0))
            power = float(element.get("Power", 0.6))
            segments.append({
                "name": "Steady State",
                "kind": "steady_state",
                "seconds": int(duration),
                "power_target": power,
            })
            power_samples.append((duration, power))
        elif tag == "IntervalsT":
            repeats = int(element.get("Repeat", 1))
            on_duration = float(element.get("OnDuration", 0))
            on_power = float(element.get("OnPower", 1.0))
            off_duration = float(element.get("OffDuration", 0))
            off_power = float(element.get("OffPower", 0.5))
            segments.append({
                "name": f"Intervals {repeats}x",
                "kind": "intervals",
                "seconds": int(repeats * (on_duration + off_duration)),
                "power_low": min(off_power, on_power),
                "power_high": max(off_power, on_power),
                "repeat": repeats,
                "on_seconds": int(on_duration),
                "on_power": on_power,
                "off_seconds": int(off_duration),
                "off_power": off_power,
            })
            for _ in range(repeats):
                power_samples.append((on_duration, on_power))
                power_samples.append((off_duration, off_power))
            intervals_summary.append(f"{repeats}x{int(on_duration / 60)}min @ {int(on_power * 100)}% FTP")
        elif tag == "FreeRide":
            duration = float(element.get("Duration", 0))
            # Keep the preview's established estimate for TSS only; PlanIR
            # correctly records that the XML has no target power.
            estimated_power = 0.65 if duration > 3600 else 0.55
            segments.append({
                "name": "Free Ride",
                "kind": "free_ride",
                "seconds": int(duration),
            })
            power_samples.append((duration, estimated_power))

    return {
        "name": name,
        "description": description,
        "segments": segments,
        "power_samples": power_samples,
        "intervals_summary": intervals_summary,
    }


def parse_zwo(zwo_path: Path, ftp: float) -> Dict[str, Any]:
    """Parse a ZWO file and calculate the preview's established metrics."""
    parsed = parse_zwo_structure(zwo_path)
    samples = parsed["power_samples"]
    if not samples:
        return _empty_workout(parsed["name"], parsed["description"])

    total_duration = sum(duration for duration, _ in samples)
    weighted_power_sum = sum(duration * (power ** 4) for duration, power in samples)
    np_ratio = (weighted_power_sum / total_duration) ** 0.25 if total_duration > 0 else 0
    normalized_power = np_ratio * ftp
    tss = (total_duration / 3600) * (np_ratio ** 2) * 100 if total_duration > 0 else 0

    return {
        "name": parsed["name"],
        "file": zwo_path.name,
        "duration_sec": total_duration,
        "duration_min": round(total_duration / 60, 1),
        "duration_hrs": round(total_duration / 3600, 2),
        "avg_power_ratio": round(np_ratio, 2),
        "normalized_power": round(normalized_power),
        "intensity_factor": round(np_ratio, 2),
        "tss": round(tss),
        "zone": _if_to_zone(np_ratio),
        "intervals_summary": ", ".join(parsed["intervals_summary"]),
        "description": parsed["description"],
        # Preserve the preview's historical flattened shape for callers.
        "segments": [(duration, round(power, 2)) for duration, power in samples],
    }


def _empty_workout(name: str, description: str) -> Dict[str, Any]:
    return {
        "name": name, "file": "", "duration_sec": 0, "duration_min": 0,
        "duration_hrs": 0, "avg_power_ratio": 0, "normalized_power": 0,
        "intensity_factor": 0, "tss": 0, "zone": "REST",
        "intervals_summary": "", "description": description, "segments": [],
    }


def _if_to_zone(if_val: float) -> str:
    if if_val < 0.55:
        return "Z1"
    if if_val < 0.75:
        return "Z2"
    if if_val < 0.87:
        return "Z3"
    if if_val < 0.95:
        return "Z4"
    if if_val < 1.06:
        return "Z5"
    return "Z5+"
