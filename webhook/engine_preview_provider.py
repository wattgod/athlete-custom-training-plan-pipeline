"""Finalized engine to public preview source adapter.

The implementation intentionally remains closed until the active
Claude-polished branch publishes its final canonical in-memory interface.
Wiring this module to the frozen Endure ``/engine/block`` response would lose
native structures, polylines, current coach copy, and the authoritative race
demand vector, so fail closed instead.
"""

from typing import Any, Mapping

from preview_service import PreviewProviderUnavailable


def generate_preview_source(
        _normalized_request: Mapping[str, Any]) -> Mapping[str, Any]:
    raise PreviewProviderUnavailable(
        "final canonical engine preview interface is not available")

