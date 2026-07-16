"""Canonical, versioned personalized fueling policy and render helpers."""
from dataclasses import asdict, dataclass
import re
from typing import Any, Dict, List, Optional

POLICY_VERSION = "2026-07-14.2"
_DEFAULT_IF = {"survival": .62, "finish": .68, "compete": .75, "podium": .80}


def _duration_ceiling(hours: float) -> float:
    """Hourly-carb ceiling that steps DOWN for very long events (fat oxidation
    rises, GI risk climbs). Never raises a shorter-race target. Sub-8h races (the
    common gravel band) are uncapped here and governed by the work-rate model."""
    if hours <= 8:
        return 90.0
    if hours <= 12:
        return 70.0
    if hours <= 16:
        return 60.0
    return 50.0


@dataclass
class FuelingPrescription:
    race_target_g_per_hour: int
    race_range_g_per_hour: List[int]
    total_g: int
    training_tiers: Dict[str, Dict[str, Any]]
    hydration: Dict[str, Any]
    assumptions: List[str]
    inputs: Dict[str, Any]
    policy_version: str = POLICY_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _number(value: Any) -> Optional[float]:
    try:
        if value in (None, ""):
            return None
        if isinstance(value, str):
            match = re.search(r"\d+(?:\.\d+)?", value)
            return float(match.group()) if match else None
        return float(value)
    except (TypeError, ValueError):
        return None


def _plausible_g_per_hour(value: Any, *, units_implied: bool) -> Optional[float]:
    """Parse an explicit, physiologically plausible carbohydrate rate.

    Free text such as ``2 gels per hour`` must not become ``2 g/hr``. Numeric
    values are accepted only for fields whose key already declares g/hr;
    otherwise the value itself must include grams-per-hour units.
    """
    if isinstance(value, (int, float)):
        parsed = float(value) if units_implied else None
    else:
        text = str(value or "").strip().lower()
        if units_implied and re.fullmatch(r"\d+(?:\.\d+)?", text):
            parsed = float(text)
        else:
            match = re.search(
                r"(\d+(?:\.\d+)?)\s*(?:g|grams?)\s*(?:/|per)\s*(?:h|hr|hrs|hour|hours)\b",
                text,
            )
            parsed = float(match.group(1)) if match else None
    return parsed if parsed is not None and 15 <= parsed <= 150 else None


def tolerated_intake_from_profile(profile: Dict[str, Any]) -> Optional[float]:
    """Read demonstrated g/hr tolerance from current and future profile aliases."""
    sources = (
        profile.get("fueling", {}), profile.get("nutrition", {}),
        profile.get("workout_preferences", {}), profile.get("fitness_markers", {}),
    )
    for source in sources:
        for key in ("tolerated_carbs_g_per_hour", "current_carbs_g_per_hour",
                    "training_fuel_g_per_hour"):
            value = _plausible_g_per_hour(source.get(key), units_implied=True)
            if value is not None:
                return value
        value = _plausible_g_per_hour(source.get("training_fuel"), units_implied=False)
        if value is not None:
            return value
    return None


def build_fueling_prescription(*, duration_hours: float, weight_kg: float,
                               ftp_watts: Optional[float], goal_type: str,
                               gut_phase: str = "build", tolerated_g_per_hour: Optional[float] = None,
                               sex: Optional[str] = None) -> FuelingPrescription:
    """Make one race prescription from body mass, absolute work and tolerance.

    Sex is intentionally not a carbohydrate-rate multiplier. It only adds an
    energy-availability reminder where useful.
    """
    goal = goal_type if goal_type in _DEFAULT_IF else "finish"
    assumptions: List[str] = []
    intensity_factor = _DEFAULT_IF[goal]
    if not ftp_watts or ftp_watts <= 0:
        ftp_watts = weight_kg * 2.4
        assumptions.append("FTP unavailable; estimated absolute work rate from body mass.")
    absolute_work = float(ftp_watts) * intensity_factor
    # Work-rate first, with a deliberately modest goal effect. Goal cannot turn a
    # small athlete into a 90 g/hr prescription by itself.
    goal_adjustment = {"survival": -5, "finish": 0, "compete": 3, "podium": 5}[goal]
    target = 48 + .055 * absolute_work + .10 * (weight_kg - 60) + goal_adjustment
    target = max(45, min(90, target))
    modeled_target = target
    tolerated = _plausible_g_per_hour(tolerated_g_per_hour, units_implied=True)
    if tolerated is None:
        assumptions.append("Current carbohydrate tolerance was not captured; conservative ceiling applied.")
        target = min(target, 70 if weight_kg < 65 else 80)
    else:
        # Do not prescribe a large untrained jump above demonstrated tolerance.
        target = min(target, tolerated + 10)
        if target < modeled_target:
            assumptions.append(
                "Race requirement exceeds demonstrated tolerance; progress gut training and review with the coach."
            )
    if gut_phase in ("base", "early"):
        target = min(target, 65)
        assumptions.append("Early gut-training phase: race-rate practice should progress gradually.")
    duration_cap = _duration_ceiling(duration_hours)
    if target > duration_cap:
        target = duration_cap
        assumptions.append(
            f"Long-duration event (~{duration_hours:.0f}h): hourly carbs capped at "
            f"{int(duration_cap)} g/hr — fuel scales DOWN with race length, not up."
        )
    if str(sex).lower() == "female":
        assumptions.append("Energy-availability check: avoid chronic under-fueling; sex does not reduce carbohydrate target.")

    target_i = int(round(target))
    race_range = [max(20, target_i - 7), min(90, target_i + 7)]
    race_range[0] = min(race_range[0], target_i)
    race_range[1] = max(race_range[1], target_i)
    # Training tiers are projections of this prescription, not separate policy.
    tiers = {
        "quality": {"target_g_per_hour": max(30, target_i - 10), "range_g_per_hour": [max(25, target_i - 17), max(35, target_i - 3)]},
        "long_ride": {"target_g_per_hour": max(35, target_i - 5), "range_g_per_hour": [max(30, target_i - 12), target_i]},
        "race_sim": {"target_g_per_hour": target_i, "range_g_per_hour": race_range},
    }
    hydration = {"target_ml_per_hour": 600 if duration_hours > 6 else 500,
                 "electrolytes": "500-1000mg sodium per hour depending on sweat rate"}
    return FuelingPrescription(
        race_target_g_per_hour=target_i, race_range_g_per_hour=race_range,
        total_g=round(target_i * duration_hours), training_tiers=tiers,
        hydration=hydration, assumptions=assumptions,
        inputs={"duration_hours": round(duration_hours, 1), "weight_kg": round(weight_kg, 1),
                "ftp_watts": round(float(ftp_watts)), "intensity_factor": intensity_factor,
                "absolute_work_watts": round(absolute_work), "goal_type": goal,
                "gut_training_phase": gut_phase, "tolerated_g_per_hour": tolerated},
    )


def prescription_from_fueling(fueling: Dict[str, Any]) -> Dict[str, Any]:
    """Return the canonical prescription, adapting pre-policy fueling files."""
    if fueling.get("prescription"):
        return fueling["prescription"]
    carbs = fueling.get("carbohydrates", {})
    target = _number(carbs.get("hourly_target"))
    if not target:
        return fueling
    target_i = int(round(target))
    race_range = carbs.get("hourly_range") or [max(20, target_i - 7), min(90, target_i + 7)]
    hydration = fueling.get("recommendations", {}).get("hydration") or {}
    return {
        "race_target_g_per_hour": target_i,
        "race_range_g_per_hour": list(race_range),
        "total_g": carbs.get("total_grams"),
        "training_tiers": {
            "quality": {"target_g_per_hour": max(30, target_i - 10),
                        "range_g_per_hour": [max(25, target_i - 17), max(35, target_i - 3)]},
            "long_ride": {"target_g_per_hour": max(35, target_i - 5),
                          "range_g_per_hour": [max(30, target_i - 12), target_i]},
            "race_sim": {"target_g_per_hour": target_i,
                         "range_g_per_hour": list(race_range)},
        },
        "hydration": hydration,
        "assumptions": ["Adapted from legacy carbohydrates fields."],
        "inputs": {"source": "legacy_carbohydrates"},
        "policy_version": "legacy-adapter",
    }


def render_workout_fueling(prescription: Dict[str, Any], tier: str, phase_ceiling=None) -> str:
    """The only personalized per-workout fuel renderer.

    phase_ceiling (from the week's gut-training target range) clamps the target
    DOWN so early-plan workouts don't prescribe more than the athlete's gut is
    trained for that week — the guide teaches a week-by-week gut progression, so
    a base-phase long ride must not tag 62 g/hr while the athlete is told 40-50.
    """
    tier_data = prescription.get("training_tiers", {}).get(tier, {})
    target = tier_data.get("target_g_per_hour", prescription.get("race_target_g_per_hour"))
    if not target:
        return ""
    if phase_ceiling:
        target = min(target, phase_ceiling)
    label = {"quality": "HIGH FUEL", "long_ride": "LONG-RIDE FUEL", "race_sim": "RACE FUEL"}.get(tier, "FUEL")
    return f"{label}: Target {target}g carbs/hr. Practice this prescription."
