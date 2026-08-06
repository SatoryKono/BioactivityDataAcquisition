"""Security-oriented snapshot helpers for effective-config builders."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.infrastructure.config.settings_api import Settings

# Surfaces whose raw values must never be hash-anchored (low-entropy / salt).
_PRESENCE_ONLY_SECRET_SURFACES: frozenset[str] = frozenset(
    {
        "settings.pii_salt_current",
        "settings.pii_salt_next",
    }
)

_EXECUTION_SECRET_SETTING_SURFACES: tuple[tuple[str, str], ...] = (
    ("settings.pii_salt_current", "pii_salt_current"),
    ("settings.pii_salt_next", "pii_salt_next"),
    ("settings.pubmed_api_key", "pubmed_api_key"),
    ("settings.uniprot_api_key", "uniprot_api_key"),
    ("settings.openalex_api_key", "openalex_api_key"),
    ("settings.semanticscholar_api_key", "semanticscholar_api_key"),
)


def _secret_is_present(value: object) -> bool:
    if value is None:
        return False
    get_secret_value = getattr(value, "get_secret_value", None)
    raw_value = get_secret_value() if callable(get_secret_value) else value
    return raw_value not in (None, "")


def _secret_value_hash(
    value: object,
    value_hash: Callable[[str], str],
) -> str | None:
    if value is None:
        return None
    get_secret_value = getattr(value, "get_secret_value", None)
    raw_value = get_secret_value() if callable(get_secret_value) else value
    if raw_value in (None, ""):
        return None
    return value_hash(str(raw_value))


def build_secret_surface_inventory(
    *,
    settings: Settings,
    value_hash: Callable[[str], str],
) -> dict[str, object]:
    """Build redaction policy block for execution settings snapshot.

    Low-entropy salt surfaces are presence-only (no reversible-by-guessing
    digests). API keys remain hash-anchored for drift detection.
    """
    secret_surfaces: dict[str, object] = {}
    for surface, attribute_name in _EXECUTION_SECRET_SETTING_SURFACES:
        value = getattr(settings, attribute_name, None)
        present = _secret_is_present(value)
        if surface in _PRESENCE_ONLY_SECRET_SURFACES:
            secret_surfaces[surface] = {
                "present": present,
                "value_hash": None,
                "hash_policy": "presence_only",
            }
            continue
        hashed_value = _secret_value_hash(value, value_hash) if present else None
        secret_surfaces[surface] = {
            "present": present,
            "value_hash": hashed_value,
            "hash_policy": "sha256_anchored",
        }
    return {
        "policy": "secret_values_redacted_hash_anchored",
        "hash_algorithm": "sha256",
        "secret_surfaces": secret_surfaces,
    }
