"""Shared BAO label normalizers for ChEMBL profile contexts."""

from __future__ import annotations

from bioetl.domain.normalization.chembl import normalize_bao_label

from .profile_normalizers import normalize_profile_bao_identifier

__all__ = ["normalize_profile_bao_label_from_bao_format"]


def normalize_profile_bao_label_from_bao_format(
    value: object,
    record: dict[str, object] | None = None,
) -> str | None:
    """Resolve canonical BAO labels from sibling ``bao_format`` when possible."""
    if value is not None and not isinstance(value, str):
        return None

    normalized_bao_identifier = (
        None
        if record is None
        else normalize_profile_bao_identifier(record.get("bao_format"))
    )
    bao_identifier = (
        normalized_bao_identifier
        if isinstance(normalized_bao_identifier, str)
        else None
    )
    return normalize_bao_label(value, bao_identifier=bao_identifier)
