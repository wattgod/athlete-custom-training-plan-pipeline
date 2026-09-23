#!/usr/bin/env python3
"""Brand palette distinctness for the training-guide stylesheet.

`_css(brand)` emits one set of semantic token NAMES with brand-specific
VALUES. Two different token names resolving to the same value is a bug, not a
style choice: the components keyed to those tokens (training-phase
indicators, callout variants) then render pixel-identical and the distinction
the guide is drawing disappears. Guides also get printed, so a distinction
that survives only in hue is already lost on paper.
"""

from collections import defaultdict
from pathlib import Path
import re
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parent))

import training_guide_builder as guide_builder


# `_css` branches on road vs. everything else; `derive_discipline` can hand it
# any of these three.
BRANDS = ("gravel", "road", "mtb")

_TOKEN_RE = re.compile(r"^\s*(--gg-color-[a-z0-9-]+):\s*(#[0-9a-fA-F]{3,8});\s*$", re.M)
_VAR_RE = re.compile(r"var\((--gg-color-[a-z0-9-]+)\)")
_PHASE_RE = re.compile(r"\.phase-indicator--([a-z]+)\s*\{([^}]*)\}")
_CALLOUT_RE = re.compile(r"^\.(gg-[a-z]+)\s*\{([^}]*)\}", re.M)


def _color_tokens(brand):
    """Every --gg-color-* token in the :root block, resolved to its literal."""
    css = guide_builder._css(brand)
    root = css.split(":root {", 1)[1].split("\n}", 1)[0]
    tokens = {name: value.lower() for name, value in _TOKEN_RE.findall(root)}
    assert tokens, f"no --gg-color-* tokens parsed for brand {brand!r}"
    return tokens


def _accent_map(brand, rule_re, accent_property):
    """Variant -> accent token, read back out of the emitted CSS.

    Variants that repaint their own background are skipped: those carry a
    second, non-colour signal (the fill), so they stay legible even when the
    accent colour is shared. `.phase-indicator--race` is the solid-fill
    counterpart of `--peak` in every brand, and `.gg-blackpill` is the filled
    callout.
    """
    css = guide_builder._css(brand)
    accents = {}
    for variant, body in rule_re.findall(css):
        if "background" in body:
            continue
        declarations = dict(
            (part.split(":", 1)[0].strip(), part.split(":", 1)[1].strip())
            for part in body.split(";")
            if ":" in part
        )
        declared = declarations.get(accent_property)
        if not declared:
            continue
        found = _VAR_RE.search(declared)
        if found:
            accents[variant] = found.group(1)
    return accents


def _collisions(mapping, tokens):
    """value -> [names], for every value claimed by more than one name."""
    by_value = defaultdict(list)
    for name, token in mapping.items():
        label = name if name == token else f"{name} ({token})"
        by_value[tokens[token]].append(label)
    return {
        value: sorted(names) for value, names in by_value.items() if len(names) > 1
    }


def _report(subject, collisions):
    lines = [f"{subject}: {len(collisions)} colour value(s) claimed by more than one name"]
    for value, names in sorted(collisions.items()):
        lines.append(f"  {value} <- {', '.join(names)}")
    return "\n".join(lines)


@pytest.mark.parametrize("brand", BRANDS)
def test_semantic_color_tokens_resolve_to_distinct_values(brand):
    tokens = _color_tokens(brand)

    collisions = _collisions({name: name for name in tokens}, tokens)

    assert not collisions, _report(brand, collisions)


@pytest.mark.parametrize("brand", BRANDS)
def test_training_phase_indicators_are_distinguishable(brand):
    tokens = _color_tokens(brand)
    phases = _accent_map(brand, _PHASE_RE, "color")
    assert {"base", "build", "peak", "taper"} <= set(phases), phases

    collisions = _collisions(phases, tokens)

    assert not collisions, _report(f"{brand} phase indicators", collisions)


@pytest.mark.parametrize("brand", BRANDS)
def test_callout_variants_are_distinguishable(brand):
    tokens = _color_tokens(brand)
    callouts = _accent_map(brand, _CALLOUT_RE, "border-left-color")
    assert len(callouts) >= 3, callouts

    collisions = _collisions(callouts, tokens)

    assert not collisions, _report(f"{brand} callouts", collisions)
