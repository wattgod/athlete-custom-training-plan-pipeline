import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from archetype_registry import get_archetype
from nate_workout_generator import (
    generate_blocks_from_archetype,
    generate_nate_zwo,
    validate_steady_workout_invariants,
)


@pytest.mark.parametrize("workout_type", ["endurance", "recovery"])
@pytest.mark.parametrize("level", range(1, 7))
def test_steady_workout_warmup_never_finishes_above_main_set(workout_type, level):
    zwo = generate_nate_zwo(workout_type, level=level)
    assert zwo is not None
    warmup = re.search(r'<Warmup\b[^>]*PowerHigh="([0-9.]+)"', zwo)
    steady = re.search(r'<SteadyState\b[^>]*Duration="([1-9]\d*)"[^>]*Power="([0-9.]+)"', zwo)
    if warmup and steady:
        assert float(warmup.group(1)) <= float(steady.group(2))
    cooldown = re.search(r'<Cooldown\b[^>]*PowerLow="([0-9.]+)"\s+PowerHigh="([0-9.]+)"', zwo)
    if cooldown and steady:
        assert float(cooldown.group(2)) <= float(cooldown.group(1)) <= float(steady.group(2))
    assert validate_steady_workout_invariants(zwo)


def test_malformed_steady_workout_fails_invariant_validation():
    malformed = ('<Warmup Duration="600" PowerLow="0.45" PowerHigh="0.70"/>'
                 '<SteadyState Duration="1200" Power="0.60"/>'
                 '<Cooldown Duration="300" PowerLow="0.65" PowerHigh="0.45"/>')
    assert not validate_steady_workout_invariants(malformed)


@pytest.mark.parametrize("name", [
    "Endurance with Surges",
    "HVLI Terrain Simulation",
    "FatMax VLamax Suppression",
    "Blended Endurance/Threshold/Sprints",
])
def test_variable_endurance_sessions_are_not_rewritten_as_pure_steady(name):
    _, archetype = get_archetype(name)
    blocks = generate_blocks_from_archetype(archetype, 1)
    warmup = re.search(r'<Warmup\b[^>]*PowerHigh="([0-9.]+)"', blocks)
    steady_powers = re.findall(r'<SteadyState\b[^>]*Power="([0-9.]+)"', blocks)
    assert len(set(steady_powers)) > 1
    if warmup:
        assert float(warmup.group(1)) > float(steady_powers[0])
