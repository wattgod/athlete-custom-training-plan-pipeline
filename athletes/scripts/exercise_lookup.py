#!/usr/bin/env python3
"""
Exercise Video Library Lookup Module
Provides fuzzy matching and query functions for exercise video URLs
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from difflib import SequenceMatcher

# Load library on import
_LIBRARY = None
_LIBRARY_PATH = Path(__file__).parent / "exercise_video_library.json"

def _load_library():
    """Load exercise library (lazy loading)"""
    global _LIBRARY
    if _LIBRARY is None:
        if not _LIBRARY_PATH.exists():
            raise FileNotFoundError(f"Exercise library not found: {_LIBRARY_PATH}")
        with open(_LIBRARY_PATH, 'r', encoding='utf-8') as f:
            _LIBRARY = json.load(f)
    return _LIBRARY

def normalize_exercise_name(name: str) -> str:
    """Normalize exercise name for matching"""
    # Convert to lowercase
    normalized = name.lower().strip()
    # Remove set markers (A1, B2, etc.)
    normalized = re.sub(r'^[a-z]\d+\s+', '', normalized)
    # Remove parenthetical notes
    normalized = re.sub(r'\s*\([^)]+\)', '', normalized)
    # Normalize common variations
    normalized = normalized.replace('push-up', 'pushup').replace('push up', 'pushup')
    normalized = normalized.replace('dumbbell', 'db').replace('dumbell', 'db')
    normalized = normalized.replace('kettlebell', 'kb').replace('kettle bell', 'kb')
    normalized = normalized.replace('single-leg', 'sl').replace('single leg', 'sl')
    normalized = normalized.replace('romanian deadlift', 'rdl')
    normalized = normalized.replace('rdl', 'romanian deadlift')  # For matching
    # Handle compound variations
    normalized = normalized.replace('+ shoulder tap', 'to single-arm support')
    normalized = normalized.replace('shoulder tap', 'single-arm support')
    # Clean whitespace
    normalized = ' '.join(normalized.split())
    return normalized

def similarity_score(str1: str, str2: str) -> float:
    """Calculate similarity score between two strings"""
    return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()

def get_video_url(exercise_name: str, fuzzy_threshold: float = 0.6) -> Optional[str]:
    """
    Fuzzy match exercise name, return video URL
    
    Args:
        exercise_name: Exercise name to look up
        fuzzy_threshold: Minimum similarity score (0-1) for fuzzy match
    
    Returns:
        Video URL if found, None otherwise
    """
    library = _load_library()
    normalized_search = normalize_exercise_name(exercise_name)
    
    best_match = None
    best_score = 0.0
    
    # Handle compound names (e.g., "Box Jump or Squat Jump")
    # Try matching each part separately
    if ' or ' in exercise_name.lower() or ' / ' in exercise_name.lower():
        parts = re.split(r'\s+or\s+|\s+/\s+', exercise_name, flags=re.IGNORECASE)
        for part in parts:
            part_url = get_video_url(part.strip(), fuzzy_threshold)
            if part_url:
                return part_url
    
    # Priority 1: Exact match (normalized)
    for exercise in library["exercises"]:
        ex_normalized = normalize_exercise_name(exercise["name"])
        
        # Exact match
        if ex_normalized == normalized_search:
            return exercise["video_url"]
        
        # Partial match (search term contains exercise name or vice versa)
        if normalized_search in ex_normalized or ex_normalized in normalized_search:
            if len(ex_normalized) > 5:  # Avoid very short matches
                return exercise["video_url"]
        
        # Alias match
        for alias in exercise.get("aliases", []):
            alias_normalized = normalize_exercise_name(alias)
            if alias_normalized == normalized_search:
                return exercise["video_url"]
    
    # Priority 2: Fuzzy match
    for exercise in library["exercises"]:
        ex_normalized = normalize_exercise_name(exercise["name"])
        score = similarity_score(ex_normalized, normalized_search)
        
        # Also check aliases
        for alias in exercise.get("aliases", []):
            alias_normalized = normalize_exercise_name(alias)
            alias_score = similarity_score(alias_normalized, normalized_search)
            score = max(score, alias_score)
        
        # Check if key words match (for compound names)
        search_words = set(normalized_search.split())
        ex_words = set(ex_normalized.split())
        word_overlap = len(search_words & ex_words)
        if word_overlap >= 2:  # At least 2 words match
            score = max(score, 0.7)  # Boost score for word overlap
        
        if score > best_score:
            best_score = score
            best_match = exercise
    
    # Return if above threshold
    if best_match and best_score >= fuzzy_threshold:
        return best_match["video_url"]
    
    return None

def get_exercises_by_category(category: str) -> List[Dict]:
    """
    Return all exercises in a category
    
    Args:
        category: Category name (squat, hinge, push, pull, core, carry, glute, mobility, plyometric, power)
    
    Returns:
        List of exercise dictionaries
    """
    library = _load_library()
    category_lower = category.lower()
    
    return [
        ex for ex in library["exercises"]
        if ex["category"].lower() == category_lower
    ]

def get_exercises_by_equipment(equipment: List[str]) -> List[Dict]:
    """
    Return exercises matching available equipment
    
    Args:
        equipment: List of available equipment (e.g., ['bodyweight', 'dumbbell', 'band'])
    
    Returns:
        List of exercises that can be performed with the equipment
    """
    library = _load_library()
    equipment_set = set(e.lower() for e in equipment)
    
    matching = []
    for exercise in library["exercises"]:
        ex_equipment = set(e.lower() for e in exercise.get("equipment", []))
        # Exercise can be done if all required equipment is available
        if ex_equipment.issubset(equipment_set) or 'bodyweight' in ex_equipment:
            matching.append(exercise)
    
    return matching

def get_substitutes(exercise_name: str, reason: str = None) -> List[Dict]:
    """
    Return substitute exercises (same pattern, different variation)
    
    Args:
        exercise_name: Exercise to find substitutes for
        reason: Why substitute needed ('no_equipment', 'easier', 'harder', 'injury_knee', 'injury_shoulder')
    
    Returns:
        List of substitute exercise dictionaries
    """
    library = _load_library()
    
    # Find the exercise first
    target_exercise = None
    normalized_search = normalize_exercise_name(exercise_name)
    
    for exercise in library["exercises"]:
        ex_normalized = normalize_exercise_name(exercise["name"])
        if ex_normalized == normalized_search:
            target_exercise = exercise
            break
    
    if not target_exercise:
        return []
    
    # Find exercises with same category/subcategory
    category = target_exercise["category"]
    subcategory = target_exercise["subcategory"]
    
    substitutes = []
    for exercise in library["exercises"]:
        if exercise["id"] == target_exercise["id"]:
            continue  # Skip self
        
        # Same movement pattern
        if exercise["category"] == category and exercise["subcategory"] == subcategory:
            # Apply reason filters
            if reason == 'no_equipment':
                if 'bodyweight' in exercise.get("equipment", []):
                    substitutes.append(exercise)
            elif reason == 'easier':
                if exercise["difficulty"] == 'beginner' and target_exercise["difficulty"] != 'beginner':
                    substitutes.append(exercise)
            elif reason == 'harder':
                if exercise["difficulty"] == 'advanced' and target_exercise["difficulty"] != 'advanced':
                    substitutes.append(exercise)
            elif reason == 'injury_knee':
                # Avoid deep knee flexion
                if 'squat' not in exercise["name"].lower() or 'assisted' in exercise["name"].lower():
                    substitutes.append(exercise)
            elif reason == 'injury_shoulder':
                # Avoid overhead or heavy pressing
                if 'overhead' not in exercise["name"].lower() and 'press' not in exercise["name"].lower():
                    substitutes.append(exercise)
            else:
                substitutes.append(exercise)
    
    return substitutes

def validate_exercise_urls(exercises: List[str]) -> Dict:
    """
    Check if all exercise URLs are valid, return report
    
    Args:
        exercises: List of exercise names to validate
    
    Returns:
        Dictionary with validation results
    """
    library = _load_library()
    
    results = {
        "total": len(exercises),
        "found": 0,
        "missing": [],
        "details": {}
    }
    
    for exercise_name in exercises:
        url = get_video_url(exercise_name)
        if url:
            results["found"] += 1
            results["details"][exercise_name] = {
                "status": "found",
                "url": url
            }
        else:
            results["missing"].append(exercise_name)
            results["details"][exercise_name] = {
                "status": "missing",
                "url": None
            }
    
    results["coverage"] = results["found"] / results["total"] if results["total"] > 0 else 0
    
    return results

def get_exercise_by_id(exercise_id: str) -> Optional[Dict]:
    """Get exercise by ID"""
    library = _load_library()
    for exercise in library["exercises"]:
        if exercise["id"] == exercise_id:
            return exercise
    return None

def search_exercises(query: str, limit: int = 10) -> List[Dict]:
    """
    Search exercises by name (fuzzy search)
    
    Args:
        query: Search query
        limit: Maximum number of results
    
    Returns:
        List of matching exercises sorted by relevance
    """
    library = _load_library()
    normalized_query = normalize_exercise_name(query)
    
    matches = []
    for exercise in library["exercises"]:
        ex_normalized = normalize_exercise_name(exercise["name"])
        score = similarity_score(ex_normalized, normalized_query)
        
        # Also check aliases
        for alias in exercise.get("aliases", []):
            alias_normalized = normalize_exercise_name(alias)
            alias_score = similarity_score(alias_normalized, normalized_query)
            score = max(score, alias_score)
        
        if score > 0.3:  # Low threshold for search
            matches.append((exercise, score))
    
    # Sort by score (descending)
    matches.sort(key=lambda x: x[1], reverse=True)
    
    return [ex for ex, score in matches[:limit]]

def get_library_stats() -> Dict:
    """Get statistics about the exercise library"""
    library = _load_library()
    
    stats = {
        "total_exercises": len(library["exercises"]),
        "by_category": {},
        "by_source": {
            "precision_nutrition": 0,
            "youtube": 0
        },
        "by_difficulty": {
            "beginner": 0,
            "intermediate": 0,
            "advanced": 0
        },
        "by_equipment": {}
    }
    
    for exercise in library["exercises"]:
        # Category counts
        cat = exercise["category"]
        stats["by_category"][cat] = stats["by_category"].get(cat, 0) + 1
        
        # Source counts
        source = exercise["video_source"]
        stats["by_source"][source] = stats["by_source"].get(source, 0) + 1
        
        # Difficulty counts
        diff = exercise["difficulty"]
        stats["by_difficulty"][diff] = stats["by_difficulty"].get(diff, 0) + 1
        
        # Equipment counts
        for eq in exercise.get("equipment", []):
            stats["by_equipment"][eq] = stats["by_equipment"].get(eq, 0) + 1
    
    return stats

if __name__ == "__main__":
    # Test the module
    print("Exercise Library Lookup Module - Test")
    print("=" * 70)
    
    # Test fuzzy matching
    test_exercises = [
        "Push-Up",
        "Pushup",
        "DB Bench Press",
        "Dumbbell Bench Press",
        "KB Swing",
        "Single-Leg RDL",
        "Dead Bug",
        "Farmer Carry"
    ]
    
    print("\nTesting fuzzy matching:")
    for ex in test_exercises:
        url = get_video_url(ex)
        status = "✓" if url else "✗"
        print(f"  {status} {ex:30s} -> {url[:50] if url else 'NOT FOUND'}")
    
    # Test category lookup
    print("\n\nTesting category lookup:")
    for category in ["squat", "hinge", "push", "pull", "core"]:
        exercises = get_exercises_by_category(category)
        print(f"  {category:10s}: {len(exercises)} exercises")
    
    # Test stats
    print("\n\nLibrary Statistics:")
    stats = get_library_stats()
    print(f"  Total exercises: {stats['total_exercises']}")
    print(f"  By source: {stats['by_source']}")
    print(f"  By category: {stats['by_category']}")

