"""Governed normalization for open-access status surfaces."""

from __future__ import annotations

from bioetl.domain.normalization.text import normalize_oa_status as _normalize_oa_text
from bioetl.domain.schemas.common.publication_base import OA_STATUS_VALUES

__all__ = ["OA_STATUS_REGISTRY", "normalize_governed_oa_status"]

OA_STATUS_REGISTRY = frozenset(OA_STATUS_VALUES)


def normalize_governed_oa_status(value: object) -> str | None:
    """Normalize OA status against the shared publication OA-status registry."""
    if value is None or isinstance(value, str):
        normalized = _normalize_oa_text(value)
        return normalized if normalized in OA_STATUS_REGISTRY else None
    return None
