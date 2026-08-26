"""Fail-closed adapter from Motoren to the public preview boundary."""

from functools import lru_cache
from pathlib import Path
import sys
from typing import Any, Mapping

from preview_service import PreviewProviderUnavailable


_ATHLETE_SCRIPTS = Path(__file__).resolve().parent.parent / "athletes" / "scripts"
if str(_ATHLETE_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_ATHLETE_SCRIPTS))


@lru_cache(maxsize=1)
def _load_motoren():
    """Import lazily so a preview failure cannot stop the order app booting."""
    try:
        import motoren_preview
    except Exception as exc:
        raise PreviewProviderUnavailable(
            "Motoren preview provider could not be loaded") from exc
    return motoren_preview


def generate_preview_source(
        normalized_request: Mapping[str, Any]) -> Mapping[str, Any]:
    if normalized_request.get("brand") == "xc_ski_labs":
        raise PreviewProviderUnavailable(
            "Motoren does not yet provide a native XC-ski preview")
    motoren = _load_motoren()
    try:
        return motoren.generate_preview_source(normalized_request)
    except motoren.MotorenPreviewError as exc:
        raise PreviewProviderUnavailable(
            "Motoren could not generate a complete public preview") from exc


def engine_version() -> str:
    return _load_motoren().engine_version()


def voice_version() -> str:
    return _load_motoren().voice_version()
