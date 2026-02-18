"""Registry access helpers.

AUTO-GENERATED JSON payload is stored in ``registry.json``.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

REGISTRY_JSON_PATH = Path(__file__).with_name("registry.json")


@lru_cache(maxsize=1)
def load_registry() -> dict[str, Any]:
    """Load canonical registry JSON."""
    payload = json.loads(REGISTRY_JSON_PATH.read_text(encoding="utf-8"))
    return dict(payload)


ENTITY_REGISTRY = load_registry().get("entities", [])
