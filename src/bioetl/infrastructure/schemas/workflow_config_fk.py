"""Foreign-key reconcile config normalization helpers."""

from __future__ import annotations


def _normalize_fk_required_name(value: str, field_name: str) -> str:
    normalized = str(value).strip()
    if not normalized:
        raise ValueError(f"reconcile_foreign_keys {field_name} cannot be empty")
    return normalized


def _normalize_fk_optional_name(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    return _normalize_fk_required_name(value, field_name)


def _normalize_fk_required_names(values: list[str], field_name: str) -> list[str]:
    normalized = [_normalize_fk_required_name(value, field_name) for value in values]
    if len(set(normalized)) != len(normalized):
        raise ValueError(
            f"reconcile_foreign_keys {field_name} cannot contain duplicates"
        )
    return normalized


def _normalize_fk_optional_names(
    values: list[str] | None,
    field_name: str,
) -> list[str] | None:
    if values is None:
        return None
    return _normalize_fk_required_names(values, field_name)


def _require_fk_key_pairs_present(
    *,
    source_key: str | None,
    reference_key: str | None,
    source_keys: list[str] | None,
    reference_keys: list[str] | None,
) -> None:
    single_pair_present = source_key is not None or reference_key is not None
    composite_pair_present = source_keys is not None or reference_keys is not None
    if not single_pair_present and not composite_pair_present:
        raise ValueError(
            "reconcile_foreign_keys requires source_key/reference_key or "
            "source_keys/reference_keys"
        )


def _require_fk_key_pairs_together(
    *,
    source_key: str | None,
    reference_key: str | None,
    source_keys: list[str] | None,
    reference_keys: list[str] | None,
) -> None:
    if (source_key is None) != (reference_key is None):
        raise ValueError(
            "reconcile_foreign_keys requires source_key and reference_key together"
        )
    if (source_keys is None) != (reference_keys is None):
        raise ValueError(
            "reconcile_foreign_keys requires source_keys and reference_keys together"
        )


def _require_matching_key_prefix(
    single_key: str | None,
    composite_keys: list[str],
    *,
    field_label: str,
) -> None:
    if single_key is not None and composite_keys[0] != single_key:
        raise ValueError(
            f"reconcile_foreign_keys {field_label} must match first {field_label}s"
        )


def _validate_fk_composite_alignment(
    *,
    source_key: str | None,
    reference_key: str | None,
    source_keys: list[str] | None,
    reference_keys: list[str] | None,
) -> None:
    if source_keys is None or reference_keys is None:
        return
    if len(source_keys) != len(reference_keys):
        raise ValueError(
            "reconcile_foreign_keys source_keys and reference_keys must have "
            "the same length"
        )
    _require_matching_key_prefix(source_key, source_keys, field_label="source_key")
    _require_matching_key_prefix(
        reference_key,
        reference_keys,
        field_label="reference_key",
    )
