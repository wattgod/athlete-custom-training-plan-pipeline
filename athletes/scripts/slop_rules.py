#!/usr/bin/env python3
"""
Slop detection rules for generated content.

Catches marketing fluff, AI-generated filler phrases, and lazy structural
patterns that weaken the brand voice. Import BANNED_PHRASES or call
check_text() from any generator.

Usage:
    from slop_rules import check_text, clean_text, BANNED_PHRASES

    violations = check_text(some_html_or_text)
    cleaned = clean_text(some_text)
"""

import re
from html.parser import HTMLParser


# ── Banned phrases ──────────────────────────────────────────
# Case-insensitive matching. Each entry is matched as a whole phrase.

BANNED_PHRASES = [
    # Hype words
    "revolutionary",
    "cutting-edge",
    "game-changing",
    "next-level",
    "best-in-class",
    "world-class",
    "state-of-the-art",
    "paradigm shift",
    # Empty escalation
    "take your cycling to the next level",
    "unlock your potential",
    "unlock your",
    "transform your",
    "leverage your",
    "elevate your",
    "supercharge your",
    "turbocharge",
    "synergy",
    "seamlessly",
    "holistic approach",
    # Filler openers
    "in today's fast-paced",
    "in today's world",
    "it's worth noting",
    "it goes without saying",
    "needless to say",
    "at the end of the day",
    # Fake depth
    "dive deep",
    "deep dive into",
]

# ── Banned structural patterns ──────────────────────────────
# Regex patterns that catch lazy AI sentence structures.

BANNED_STRUCTURES = [
    # "Whether you're a beginner or a seasoned pro"
    (r"whether you'?re a .{3,40} or a .{3,40}", "Whether you're a X or a Y"),
    # "From X to Y, we've got you covered"
    (r"from .{3,30} to .{3,30},?\s+we'?ve got you covered", "From X to Y, we've got you covered"),
    # "Look no further" / "Search no further"
    (r"(?:look|search) no further", "Look/search no further"),
    # "In the world of [noun]"
    (r"in the world of \w+", "In the world of X"),
    # "Are you ready to [verb]"
    (r"are you ready to \w+", "Are you ready to X"),
    # "Here's the thing" / "Here's what you need to know"
    (r"here'?s (?:the thing|what you need to know)", "Here's the thing / what you need to know"),
    # "Without further ado"
    (r"without further ado", "Without further ado"),
    # "It's no secret that"
    (r"it'?s no secret that", "It's no secret that"),
    # "Let's face it"
    (r"let'?s face it", "Let's face it"),
]


# ── Suggested replacements ──────────────────────────────────
# Maps banned phrase -> concrete replacement. Not exhaustive — some phrases
# should just be deleted rather than replaced.

_REPLACEMENTS = {
    "revolutionary": "new",
    "cutting-edge": "modern",
    "game-changing": "significant",
    "next-level": "",  # delete
    "best-in-class": "strong",
    "world-class": "top-tier",
    "state-of-the-art": "current",
    "paradigm shift": "change",
    "seamlessly": "",  # delete
    "holistic approach": "approach",
    "synergy": "combination",
    "turbocharge": "improve",
    "supercharge your": "improve your",
    "elevate your": "improve your",
    "transform your": "change your",
    "leverage your": "use your",
    "unlock your potential": "train effectively",
    "unlock your": "use your",
    "take your cycling to the next level": "get faster",
    "dive deep": "examine",
    "deep dive into": "detailed look at",
    "in today's fast-paced": "",  # delete the filler
    "in today's world": "",  # delete the filler
    "it's worth noting": "",  # just state the fact
    "it goes without saying": "",  # just state the fact
    "needless to say": "",  # just state the fact
    "at the end of the day": "ultimately",
}


# ── HTML text extractor ─────────────────────────────────────

class _TextExtractor(HTMLParser):
    """Extracts visible text from HTML, ignoring tags and attributes."""

    def __init__(self):
        super().__init__()
        self._parts = []
        self._skip = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self._skip = True

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript"):
            self._skip = False

    def handle_data(self, data):
        if not self._skip:
            self._parts.append(data)

    def get_text(self):
        return " ".join(self._parts)


def _extract_text(html):
    """Return visible text content from an HTML string."""
    extractor = _TextExtractor()
    extractor.feed(html)
    return extractor.get_text()


# ── Public API ──────────────────────────────────────────────

def check_text(text, is_html=False):
    """Check text for slop violations.

    Args:
        text: The text (or HTML) to check.
        is_html: If True, strip HTML tags before checking so that
                 tag attributes and script content are ignored.

    Returns:
        List of dicts: [{"phrase": str, "type": "banned_phrase"|"banned_structure"}]
    """
    if is_html:
        text = _extract_text(text)

    text_lower = text.lower()
    violations = []

    # Check banned phrases
    for phrase in BANNED_PHRASES:
        if phrase.lower() in text_lower:
            violations.append({"phrase": phrase, "type": "banned_phrase"})

    # Check banned structures
    for pattern, label in BANNED_STRUCTURES:
        if re.search(pattern, text_lower):
            violations.append({"phrase": label, "type": "banned_structure"})

    return violations


def clean_text(text):
    """Return text with common slop phrases replaced or removed.

    This is a best-effort helper. It handles exact phrase matches from
    _REPLACEMENTS. Structural patterns require manual rewriting.

    Args:
        text: Plain text to clean.

    Returns:
        Cleaned text string.
    """
    result = text
    for phrase, replacement in sorted(_REPLACEMENTS.items(), key=lambda x: -len(x[0])):
        # Case-insensitive replacement preserving sentence flow
        pattern = re.compile(re.escape(phrase), re.IGNORECASE)
        result = pattern.sub(replacement, result)

    # Clean up double spaces and leading spaces from deletions
    result = re.sub(r"  +", " ", result)
    result = re.sub(r"^ +", "", result, flags=re.MULTILINE)
    # Clean up orphaned punctuation from deletions (e.g., ", ," or ". .")
    result = re.sub(r",\s*,", ",", result)
    result = re.sub(r"\.\s*\.", ".", result)

    return result
