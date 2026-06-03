"""Security-oriented snapshot helpers for effective-config builders."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.infrastructure.config.settings_api import Settings


_EXECUTION_SECRET_SETTING_SURFACES: tuple[tuple[str, str], ...] = (
    ("settings.pii_salt_current", "pii_salt_current"),
    ("settings.pii_salt_next", "pii_salt_next"),
    ("settings.pubmed_api_key", "pubmed_api_key"),
    ("settings.uniprot_api_key", "uniprot_api_key"),
    ("settings.openalex_api_key", "openalex_api_key"),
    ("settings.semanticscholar_api_key", "semanticscholar_api_key"),
)


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
    """Build redaction policy block for execution settings snapshot."""
    secret_surfaces: dict[str, object] = {}
    for surface, attribute_name in _EXECUTION_SECRET_SETTING_SURFACES:
        value = getattr(settings, attribute_name, None)
        hashed_value = _secret_value_hash(value, value_hash)
        secret_surfaces[surface] = {
            "present": hashed_value is not None,
            "value_hash": hashed_value,
        }
    return {
        "policy": "secret_values_redacted_hash_anchored",
        "hash_algorithm": "sha256",
        "secret_surfaces": secret_surfaces,
    }
