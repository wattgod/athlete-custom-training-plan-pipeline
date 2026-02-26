#!/usr/bin/env python3
"""Race intel enhancer -- adds rider intel citations and generates coaching brief.

Sprint 4 of the race-to-archetype mapping system.

Given a workout pack and race data (with rider_intel), this module:
1. Scans rider intel for relevant keywords matching each workout's category
2. Adds up to 2 rider_intel_citations per workout
3. Generates a Markdown coaching brief summarizing the race, demands, and pack

Usage:
    from race_intel_enhancer import enhance_with_rider_intel, generate_race_brief

    enhanced = enhance_with_rider_intel(pack, race_data)
    brief = generate_race_brief(race_data, enhanced, demands)
"""

import re
from typing import List, Optional


# =============================================================================
# CATEGORY-TO-KEYWORD MAPPING
# =============================================================================
# Keywords that connect archetype categories to rider intel content.
# When a rider says "the heat was brutal", that matches Durability/Endurance.
# =============================================================================

CATEGORY_KEYWORDS = {
    # Endurance / durability categories
    'Durability': ['pace', 'endurance', 'fatigue', 'bonk', 'miles', 'survival', 'long', 'duration', 'suffer', 'exhaustion'],
    'HVLI_Extended': ['pace', 'endurance', 'fatigue', 'bonk', 'miles', 'survival', 'long', 'duration', 'steady'],
    'Endurance': ['pace', 'endurance', 'fatigue', 'bonk', 'miles', 'survival', 'long', 'duration', 'base'],

    # Climbing categories
    'Mixed_Climbing': ['climb', 'elevation', 'hill', 'steep', 'gradient', 'ascent', 'grade', 'mountain', 'summit'],
    'Over_Under': ['climb', 'elevation', 'hill', 'steep', 'gradient', 'ascent', 'threshold', 'power'],
    'SFR_Muscle_Force': ['climb', 'elevation', 'hill', 'steep', 'gradient', 'ascent', 'force', 'grind'],

    # Heat / environment
    'Tempo': ['heat', 'hot', 'hydration', 'sun', 'cooling', 'temperature', 'weather'],

    # Technical / gravel
    'Gravel_Specific': ['rocky', 'technical', 'sand', 'mud', 'loose', 'ruts', 'gravel', 'rough', 'surface', 'chunky'],
    'Cadence_Work': ['rocky', 'technical', 'sand', 'mud', 'loose', 'ruts', 'cadence', 'spin'],
    'Critical_Power': ['rocky', 'technical', 'power', 'surge', 'effort'],

    # VO2 / race intensity
    'VO2max': ['attack', 'surge', 'sprint', 'break', 'selection', 'fast', 'intensity', 'hard', 'explosive'],
    'Anaerobic_Capacity': ['attack', 'surge', 'sprint', 'break', 'selection', 'fast', 'anaerobic', 'punch'],
    'Race_Simulation': ['attack', 'surge', 'sprint', 'break', 'selection', 'fast', 'race', 'peloton', 'tactics'],

    # Threshold
    'TT_Threshold': ['threshold', 'steady', 'power', 'sustained', 'time trial', 'effort'],
    'G_Spot': ['threshold', 'steady', 'sustained', 'sweet spot', 'tempo'],
    'Norwegian_Double': ['threshold', 'sustained', 'interval', 'volume'],

    # Other
    'Blended': ['mixed', 'varied', 'unpredictable', 'changing', 'terrain'],
    'Sprint_Neuromuscular': ['sprint', 'attack', 'explosive', 'power', 'acceleration'],
    'LT1_MAF': ['aerobic', 'base', 'easy', 'zone 2', 'heart rate', 'maf'],
    'INSCYD': ['metabolic', 'lactate', 'fat', 'carb', 'fuel'],
    'Recovery': ['recovery', 'rest', 'easy'],
}

# Max citations per workout
MAX_CITATIONS_PER_WORKOUT = 2


def enhance_with_rider_intel(pack: list, race_data: dict) -> list:
    """Add rider intel citations to each workout in the pack.

    For each workout, scans rider intel for keywords matching its category.
    Adds a 'rider_intel_citations' list (max 2) to each pack item.

    Args:
        pack: List of pack items from select_workout_pack().
        race_data: Full race JSON (race_data['race']['youtube_data']['rider_intel']).

    Returns:
        The same pack list, mutated with rider_intel_citations added.
    """
    # Extract rider intel
    rider_intel = _extract_rider_intel(race_data)
    if not rider_intel:
        # No intel available -- add empty citations
        for item in pack:
            item['rider_intel_citations'] = []
        return pack

    # Build searchable text pool
    text_pool = _build_text_pool(rider_intel)

    for item in pack:
        category = item.get('category', '')
        keywords = CATEGORY_KEYWORDS.get(category, [])
        citations = _find_citations(text_pool, keywords)
        item['rider_intel_citations'] = citations[:MAX_CITATIONS_PER_WORKOUT]

    return pack


def _extract_rider_intel(race_data: dict) -> Optional[dict]:
    """Extract rider_intel from nested race data structure."""
    try:
        return race_data['race']['youtube_data']['rider_intel']
    except (KeyError, TypeError):
        return None


def _build_text_pool(rider_intel: dict) -> list:
    """Build a flat list of searchable text items from rider intel.

    Each item: {'text': str, 'source': str}

    Sources:
      - search_text (single blob)
      - race_day_tips[].text
      - terrain_notes[].text
      - key_challenges[].description
      - additional_quotes[].text
    """
    pool = []

    # search_text is a single string
    st = rider_intel.get('search_text', '')
    if st:
        pool.append({'text': st, 'source': 'search_text'})

    # race_day_tips
    for tip in rider_intel.get('race_day_tips', []):
        text = tip.get('text', '')
        if text:
            pool.append({'text': text, 'source': 'race_day_tip'})

    # terrain_notes
    for note in rider_intel.get('terrain_notes', []):
        text = note.get('text', '')
        if text:
            pool.append({'text': text, 'source': 'terrain_note'})

    # key_challenges
    for challenge in rider_intel.get('key_challenges', []):
        text = challenge.get('description', '')
        if text:
            pool.append({'text': text, 'source': 'key_challenge'})

    # additional_quotes
    for quote in rider_intel.get('additional_quotes', []):
        text = quote.get('text', '')
        if text:
            pool.append({'text': text, 'source': 'additional_quote'})

    return pool


def _find_citations(text_pool: list, keywords: list) -> list:
    """Find text items that match any of the keywords.

    Returns list of {'text': str, 'source': str, 'matched_keyword': str}.
    Prioritizes shorter, more specific citations (not search_text blobs).
    """
    if not keywords or not text_pool:
        return []

    matches = []
    seen_texts = set()

    for item in text_pool:
        text_lower = item['text'].lower()
        for kw in keywords:
            if kw.lower() in text_lower:
                # Avoid duplicates
                text_key = item['text'][:100]
                if text_key in seen_texts:
                    continue
                seen_texts.add(text_key)
                matches.append({
                    'text': item['text'],
                    'source': item['source'],
                    'matched_keyword': kw,
                })
                break  # one match per text item is enough

    # Sort: prefer specific citations over search_text blobs
    SOURCE_PRIORITY = {
        'key_challenge': 0,
        'terrain_note': 1,
        'race_day_tip': 2,
        'additional_quote': 3,
        'search_text': 4,
    }
    matches.sort(key=lambda x: (SOURCE_PRIORITY.get(x['source'], 5), len(x['text'])))

    return matches


# =============================================================================
# COACHING BRIEF GENERATION
# =============================================================================

def generate_race_brief(race_data: dict, pack: list, demands: dict) -> str:
    """Generate a Markdown coaching brief for the race training pack.

    Structure:
      # Train for {race_name}
      ## Race Profile
      ## Training Demands
      ## Your {N}-Workout Pack
      ## How to Use This Pack

    Args:
        race_data: Full race JSON dict.
        pack: Enhanced pack list (with rider_intel_citations).
        demands: Demand vector dict (8 dimensions).

    Returns:
        Markdown string.
    """
    race = race_data.get('race', {})
    name = race.get('display_name') or race.get('name', 'Unknown Race')
    vitals = race.get('vitals', {})
    rating = race.get('gravel_god_rating', {})

    lines = []

    # Title
    lines.append(f"# Train for {name}")
    lines.append("")

    # Race Profile
    lines.append("## Race Profile")
    lines.append("")
    distance = vitals.get('distance_mi', '?')
    elevation = vitals.get('elevation_ft', '?')
    tier = rating.get('tier_label', f"TIER {rating.get('tier', '?')}")
    discipline = rating.get('discipline', 'gravel')
    location = vitals.get('location', '?')
    date_str = vitals.get('date_specific', vitals.get('date', '?'))

    lines.append(f"- **Distance**: {distance} miles")
    lines.append(f"- **Elevation**: {elevation} ft")
    lines.append(f"- **Location**: {location}")
    lines.append(f"- **Date**: {date_str}")
    lines.append(f"- **Tier**: {tier}")
    lines.append(f"- **Discipline**: {discipline}")
    lines.append("")

    # Training Demands
    lines.append("## Training Demands")
    lines.append("")
    lines.append("| Dimension | Score | Bar |")
    lines.append("|-----------|-------|-----|")
    for dim in ['durability', 'climbing', 'vo2_power', 'threshold',
                'technical', 'heat_resilience', 'altitude', 'race_specificity']:
        score = demands.get(dim, 0)
        bar = _demand_bar(score)
        dim_label = dim.replace('_', ' ').title()
        lines.append(f"| {dim_label} | {score}/10 | {bar} |")
    lines.append("")

    # Workout Pack
    lines.append(f"## Your {len(pack)}-Workout Pack")
    lines.append("")
    for i, item in enumerate(pack, 1):
        arch_name = item.get('archetype_name', '?')
        cat = item.get('category', '?')
        score = item.get('relevance_score', 0)
        level = item.get('level', 3)

        lines.append(f"### {i}. {arch_name}")
        lines.append(f"- **Category**: {cat}")
        lines.append(f"- **Relevance**: {score}/100")
        lines.append(f"- **Level**: {level}/6")

        # Why this workout
        why = _why_this_workout(cat, demands)
        if why:
            lines.append(f"- **Why**: {why}")

        # Rider intel citation
        citations = item.get('rider_intel_citations', [])
        if citations:
            lines.append(f"- **Riders say**: \"{_truncate(citations[0]['text'], 200)}\"")
        lines.append("")

    # How to Use
    lines.append("## How to Use This Pack")
    lines.append("")
    lines.append("1. **Schedule 2-3 workouts per week** from this pack alongside your base training")
    lines.append("2. **Progress through levels** -- start at your current level, advance every 2-3 weeks")
    lines.append("3. **Prioritize top-relevance workouts** -- the higher the score, the more race-specific")
    lines.append("4. **Listen to your body** -- skip or substitute if fatigued")
    lines.append("5. **Race week**: Drop to level 1 for openers only")
    lines.append("")

    return "\n".join(lines)


def _demand_bar(score: int) -> str:
    """Generate a visual bar for demand score."""
    filled = min(10, max(0, score))
    return "`" + "#" * filled + "." * (10 - filled) + "`"


def _truncate(text: str, max_len: int = 200) -> str:
    """Truncate text with ellipsis."""
    if len(text) <= max_len:
        return text
    return text[:max_len - 3] + "..."


def _why_this_workout(category: str, demands: dict) -> str:
    """Generate a one-sentence explanation of why this category was selected."""
    reasons = {
        'Durability': 'High durability demand ({d}/10) -- this race requires sustained effort over many hours',
        'HVLI_Extended': 'High durability demand ({d}/10) -- extended time in zone builds the engine you need',
        'Endurance': 'Endurance foundation -- base aerobic capacity is critical for this distance',
        'Mixed_Climbing': 'Climbing demand ({d}/10) -- this race includes sustained climbing that requires specific preparation',
        'Over_Under': 'Climbing + threshold demand -- over/under intervals build the ability to surge on climbs',
        'SFR_Muscle_Force': 'Climbing demand ({d}/10) -- low-cadence force work builds climbing-specific strength',
        'VO2max': 'VO2 power demand ({d}/10) -- top-end aerobic power for race-pace efforts',
        'Anaerobic_Capacity': 'VO2 power demand ({d}/10) -- anaerobic capacity for surges and attacks',
        'TT_Threshold': 'Threshold demand ({d}/10) -- sustained power at race pace',
        'G_Spot': 'Threshold demand ({d}/10) -- G-Spot (87-92% FTP) builds race-pace durability',
        'Norwegian_Double': 'Threshold demand ({d}/10) -- Norwegian method for aerobic threshold development',
        'Gravel_Specific': 'Technical demand ({d}/10) -- gravel-specific skills and power patterns',
        'Race_Simulation': 'Race specificity demand ({d}/10) -- simulate race-day intensity patterns',
        'Cadence_Work': 'Technical demand ({d}/10) -- cadence variability for changing terrain',
        'Critical_Power': 'Technical + VO2 demand -- critical power work for repeated efforts',
        'Blended': 'Race specificity demand ({d}/10) -- mixed-system workouts that simulate real racing',
        'Tempo': 'Threshold demand ({d}/10) -- tempo work builds the aerobic base for sustained effort',
        'Sprint_Neuromuscular': 'VO2 power demand ({d}/10) -- neuromuscular power for explosive efforts',
        'LT1_MAF': 'Altitude demand ({d}/10) -- aerobic base development for altitude performance',
        'INSCYD': 'Metabolic optimization for race-specific fuel utilization',
    }

    template = reasons.get(category, '')
    if not template:
        return ''

    # Find the relevant demand dimension for this category
    dim_map = {
        'Durability': 'durability', 'HVLI_Extended': 'durability', 'Endurance': 'durability',
        'Mixed_Climbing': 'climbing', 'Over_Under': 'climbing', 'SFR_Muscle_Force': 'climbing',
        'VO2max': 'vo2_power', 'Anaerobic_Capacity': 'vo2_power', 'Sprint_Neuromuscular': 'vo2_power',
        'TT_Threshold': 'threshold', 'G_Spot': 'threshold', 'Norwegian_Double': 'threshold', 'Tempo': 'threshold',
        'Gravel_Specific': 'technical', 'Cadence_Work': 'technical', 'Critical_Power': 'technical',
        'Race_Simulation': 'race_specificity', 'Blended': 'race_specificity',
        'LT1_MAF': 'altitude',
    }
    dim = dim_map.get(category, '')
    d = demands.get(dim, 0)

    return template.format(d=d)


if __name__ == '__main__':
    import json

    # Demo: generate a brief with mock data
    mock_demands = {
        'durability': 9, 'climbing': 4, 'vo2_power': 6, 'threshold': 5,
        'technical': 5, 'heat_resilience': 8, 'altitude': 2, 'race_specificity': 7,
    }
    mock_race = {
        'race': {
            'name': 'Unbound 200',
            'display_name': 'Unbound Gravel 200',
            'vitals': {
                'distance_mi': 200,
                'elevation_ft': 11000,
                'location': 'Emporia, Kansas',
                'date_specific': '2026: June 6',
            },
            'gravel_god_rating': {
                'tier': 1,
                'tier_label': 'TIER 1',
                'discipline': 'gravel',
            },
        }
    }
    mock_pack = [
        {'category': 'Durability', 'archetype_name': 'Tired VO2max', 'relevance_score': 100, 'level': 3, 'rider_intel_citations': []},
        {'category': 'VO2max', 'archetype_name': '5x3 VO2 Classic', 'relevance_score': 80, 'level': 3, 'rider_intel_citations': []},
    ]
    print(generate_race_brief(mock_race, mock_pack, mock_demands))
