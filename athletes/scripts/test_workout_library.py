#!/usr/bin/env python3
"""
Unit tests for WorkoutLibrary and workout generation.

Tests workout progressions, strength workout rotation, and ZWO generation.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from workout_library import (
    WorkoutLibrary,
    generate_progressive_interval_blocks,
    generate_progressive_endurance_blocks,
    generate_strength_workout_text,
    generate_strength_zwo,
)


def test_interval_progressions():
    """Test that interval workouts progress through phases correctly."""
    print("\n=== Testing Interval Progressions ===")

    # Build phase should have progressively harder workouts
    build_workouts = []
    for week in range(1, 7):
        workout = WorkoutLibrary.get_interval_workout('build', week)
        build_workouts.append(workout)
        print(f"Week {week}: {workout['name']} - {workout['intervals']}x{workout['on_duration']//60}min @ {int(workout['on_power']*100)}%")

    # Verify we get different workouts (variety)
    names = [w['name'] for w in build_workouts]
    unique_names = set(names)
    assert len(unique_names) >= 3, f"Expected at least 3 unique workouts, got {len(unique_names)}"
    print(f"✓ Found {len(unique_names)} unique interval workouts")

    # Peak phase should have higher intensity
    peak_workout = WorkoutLibrary.get_interval_workout('peak', 1)
    assert peak_workout['on_power'] >= 1.08, f"Peak VO2max should be >= 108%, got {peak_workout['on_power']*100}%"
    print(f"✓ Peak phase has high intensity: {int(peak_workout['on_power']*100)}%")


def test_endurance_progressions():
    """Test that endurance workouts have variety."""
    print("\n=== Testing Endurance Progressions ===")

    endurance_workouts = []
    for week in range(1, 7):
        workout = WorkoutLibrary.get_endurance_workout(week)
        endurance_workouts.append(workout)
        print(f"Week {week}: {workout['name']} - {workout['structure']}")

    # Verify variety
    structures = [w['structure'] for w in endurance_workouts]
    unique_structures = set(structures)
    assert len(unique_structures) >= 3, f"Expected at least 3 unique structures, got {len(unique_structures)}"
    print(f"✓ Found {len(unique_structures)} unique endurance structures")


def test_long_ride_progressions():
    """Test long ride workouts by phase."""
    print("\n=== Testing Long Ride Progressions ===")

    phases = ['base', 'build', 'peak']
    for phase in phases:
        workout = WorkoutLibrary.get_long_ride_workout(phase, 1)
        print(f"{phase.title()}: {workout['name']} - Z2 @ {int(workout['z2_power']*100)}%, Tempo @ {int(workout['tempo_power']*100)}%")

    # Build/peak should have tempo component
    build_ride = WorkoutLibrary.get_long_ride_workout('build', 1)
    assert build_ride['tempo_power'] > 0, "Build long rides should include tempo"
    print(f"✓ Build long rides include tempo at {int(build_ride['tempo_power']*100)}%")


def test_strength_workout_rotation():
    """Test that strength workouts rotate properly."""
    print("\n=== Testing Strength Workout Rotation ===")

    session1_workouts = []
    session2_workouts = []

    for week in range(1, 5):
        s1 = WorkoutLibrary.get_strength_workout(week, 1)
        s2 = WorkoutLibrary.get_strength_workout(week, 2)
        session1_workouts.append(s1['name'])
        session2_workouts.append(s2['name'])
        print(f"Week {week}: Session 1 = {s1['name']}, Session 2 = {s2['name']}")

    # Session 1 should rotate through Foundation A, Power, Cycling-Specific
    # Session 2 should rotate through Foundation B, Mobility
    assert len(set(session1_workouts)) >= 2, "Session 1 should rotate through workouts"
    assert len(set(session2_workouts)) >= 2, "Session 2 should rotate through workouts"
    print(f"✓ Session 1 rotates through: {set(session1_workouts)}")
    print(f"✓ Session 2 rotates through: {set(session2_workouts)}")


def test_zwo_generation():
    """Test ZWO XML generation."""
    print("\n=== Testing ZWO Generation ===")

    # Test interval ZWO
    blocks, name = generate_progressive_interval_blocks('build', 1, 1, 60)
    assert '<Warmup' in blocks, "Interval workout should have warmup"
    assert '<IntervalsT' in blocks, "Interval workout should have intervals"
    assert '<Cooldown' in blocks, "Interval workout should have cooldown"
    print(f"✓ Generated interval workout: {name}")

    # Test endurance ZWO
    blocks, name = generate_progressive_endurance_blocks(1, 60)
    assert '<Warmup' in blocks, "Endurance workout should have warmup"
    assert '<SteadyState' in blocks, "Endurance workout should have steady state"
    print(f"✓ Generated endurance workout: {name}")

    # Test strength ZWO
    blocks, name = generate_strength_zwo(1, 1)
    assert '<Warmup' in blocks or '<SteadyState' in blocks, "Strength workout should have content"
    assert 'Exercise' in blocks, "Strength workout should have exercise prompts"
    print(f"✓ Generated strength workout: {name}")


def test_strength_workout_text():
    """Test strength workout text generation."""
    print("\n=== Testing Strength Workout Text ===")

    text = generate_strength_workout_text(1, 1)
    assert '# ' in text, "Should have markdown header"
    assert 'Warmup' in text, "Should have warmup section"
    assert 'Cooldown' in text, "Should have cooldown section"
    assert 'Main Workout' in text, "Should have main workout section"
    print(f"✓ Generated strength text with all sections")


def run_all_tests():
    """Run all tests and report results."""
    print("=" * 60)
    print("WORKOUT LIBRARY UNIT TESTS")
    print("=" * 60)

    tests = [
        test_interval_progressions,
        test_endurance_progressions,
        test_long_ride_progressions,
        test_strength_workout_rotation,
        test_zwo_generation,
        test_strength_workout_text,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"\n❌ FAILED: {test.__name__}")
            print(f"   {e}")
            failed += 1
        except Exception as e:
            print(f"\n❌ ERROR: {test.__name__}")
            print(f"   {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
