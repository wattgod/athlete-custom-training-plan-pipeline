"""Version-aware cache and provider boundary for public plan previews."""

from __future__ import annotations

import copy
import hashlib
import json
import threading
import time
from collections import OrderedDict
from typing import Any, Callable, Dict, Mapping, Tuple

from preview_contract import normalize_request, project_response, request_cache_key


class PreviewProviderUnavailable(RuntimeError):
    """The finalized canonical preview provider is not deployed."""


class PreviewCache:
    def __init__(self, *, ttl_seconds: int = 900, max_entries: int = 512,
                 clock: Callable[[], float] = time.monotonic):
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self.clock = clock
        self._items: "OrderedDict[str, Tuple[float, Dict[str, Any]]]" = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str) -> Dict[str, Any] | None:
        now = self.clock()
        with self._lock:
            item = self._items.get(key)
            if item is None:
                return None
            expires_at, value = item
            if expires_at <= now:
                del self._items[key]
                return None
            self._items.move_to_end(key)
            return copy.deepcopy(value)

    def put(self, key: str, value: Mapping[str, Any]) -> None:
        with self._lock:
            self._items[key] = (
                self.clock() + self.ttl_seconds, copy.deepcopy(dict(value)))
            self._items.move_to_end(key)
            while len(self._items) > self.max_entries:
                self._items.popitem(last=False)


PUBLIC_PREVIEW_CACHE = PreviewCache()


def versioned_cache_key(normalized_request: Mapping[str, Any], *,
                        engine_version: str, voice_version: str) -> str:
    material = {
        "request": request_cache_key(normalized_request),
        "engine_version": engine_version,
        "voice_version": voice_version,
    }
    wire = json.dumps(material, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(wire.encode("utf-8")).hexdigest()


def build_public_preview(
        payload: Mapping[str, Any], *,
        provider: Callable[[Mapping[str, Any]], Mapping[str, Any]],
        engine_version: str, voice_version: str,
        cache: PreviewCache = PUBLIC_PREVIEW_CACHE) -> Tuple[Dict[str, Any], bool]:
    """Return (validated public response, cache_hit)."""
    normalized = normalize_request(payload)
    key = versioned_cache_key(
        normalized, engine_version=engine_version, voice_version=voice_version)
    cached = cache.get(key)
    if cached is not None:
        return cached, True
    source = provider(normalized)
    if not isinstance(source, Mapping):
        raise PreviewProviderUnavailable(
            "canonical preview provider returned no source")
    response = project_response(
        normalized, source, engine_version=engine_version,
        voice_version=voice_version)
    cache.put(key, response)
    return response, False

