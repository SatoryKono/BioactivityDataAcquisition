"""Vocabulary-specific helpers for DQ rule evaluators."""

from __future__ import annotations

import json
from collections.abc import Callable

from bioetl.domain.schemas.constants import (
    TARGET_COMPONENT_RELATIONSHIPS,
    TARGET_COMPONENT_TYPES,
)

TARGET_XREF_SOURCE_DB_VALUES = frozenset(
    {
        "AlphaFoldDB",
        "ChEBI",
        "DrugBank",
        "ExpressionAtlas",
        "Gene3D",
        "GoComponent",
        "GoFunction",
        "GoProcess",
        "HGNC",
        "IntAct",
        "InterPro",
        "OpenTargets",
        "PANTHER",
        "PDB",
        "PDBe",
        "Pfam",
        "PharmGKB",
        "Pharos",
        "Reactome",
        "SUPFAM",
        "TreeFam",
        "UniProt",
    }
)

_ValidationStrategy = Callable[[object, str | None], bool]


def _resolve_custom_validation_strategy(
    validator_name: str | None,
) -> _ValidationStrategy | None:
    """Resolve the validation strategy for a custom validator name."""
    if _target_json_vocabulary(validator_name) is not None:
        return _target_json_vocabulary_strategy
    if _target_xref_json_vocabulary(validator_name) is not None:
        return _target_xref_json_vocabulary_strategy
    if _publication_taxonomy_vocabulary(validator_name) is not None:
        return _publication_taxonomy_strategy
    return None


def _target_json_vocabulary_strategy(value: object, validator_name: str | None) -> bool:
    """Validate against target component JSON vocabulary."""
    vocab = _target_json_vocabulary(validator_name)
    return _target_json_vocabulary_rule_violated(value, allowed_values=vocab)


def _target_xref_json_vocabulary_strategy(
    value: object, validator_name: str | None
) -> bool:
    """Validate against target xref JSON vocabulary."""
    xref_vocab = _target_xref_json_vocabulary(validator_name)
    return _target_xref_json_vocabulary_rule_violated(value, allowed_values=xref_vocab)


def _publication_taxonomy_strategy(value: object, validator_name: str | None) -> bool:
    """Validate against publication taxonomy vocabulary."""
    pub_taxonomy = _publication_taxonomy_vocabulary(validator_name)
    return _publication_taxonomy_rule_violated(value, allowed_values=pub_taxonomy)


def _target_json_vocabulary(validator_name: str | None) -> frozenset[str] | None:
    if validator_name == "validate_target_component_types_json_vocab":
        return TARGET_COMPONENT_TYPES
    if validator_name == "validate_target_component_relationships_json_vocab":
        return TARGET_COMPONENT_RELATIONSHIPS
    return None


def _publication_taxonomy_vocabulary(
    validator_name: str | None,
) -> frozenset[str] | None:
    from bioetl.domain.mapping.publication_type_classification import (
        publication_classification_values,
    )

    mapping = {
        "validate_publication_type_unified_taxonomy": "publication_type_unified",
        "validate_publication_subclass_taxonomy": "publication_subclass",
        "validate_publication_class_taxonomy": "publication_class",
    }
    field_name = mapping.get(validator_name)
    if field_name is None:
        return None
    return publication_classification_values(field_name)


def _target_xref_json_vocabulary(
    validator_name: str | None,
) -> frozenset[str] | None:
    if validator_name in {
        "validate_target_xref_src_db_json_vocab",
        "validate_target_component_xref_src_db_json_vocab",
    }:
        return TARGET_XREF_SOURCE_DB_VALUES
    return None


def _target_json_vocabulary_rule_violated(
    value: object,
    *,
    allowed_values: frozenset[str],
) -> bool:
    list_like = _coerce_target_json_list(value)
    if list_like is None:
        return True
    return any(
        not isinstance(item, str) or item not in allowed_values for item in list_like
    )


def _publication_taxonomy_rule_violated(
    value: object,
    *,
    allowed_values: frozenset[str],
) -> bool:
    return not isinstance(value, str) or value not in allowed_values


def _target_xref_json_vocabulary_rule_violated(
    value: object,
    *,
    allowed_values: frozenset[str],
) -> bool:
    list_like = _coerce_target_json_list(value)
    if list_like is None:
        return True
    return any(_is_invalid_xref_item(item, allowed_values) for item in list_like)


def _is_invalid_xref_item(item: object, allowed_values: frozenset[str]) -> bool:
    if not isinstance(item, dict):
        return True
    source_value = item.get("xref_src_db")
    return not isinstance(source_value, str) or source_value not in allowed_values


def _coerce_target_json_list(value: object) -> list[object] | None:
    if isinstance(value, str):
        return _coerce_string_list_like(value)
    if isinstance(value, list):
        return value
    return None


def _coerce_string_list_like(value: str) -> list[object] | None:
    stripped = value.strip()
    if not stripped:
        return []
    if not _looks_like_json_list(stripped):
        return None
    return _decode_json_list_like(stripped)


def _looks_like_json_list(value: str) -> bool:
    return value.startswith("[") and value.endswith("]")


def _decode_json_list_like(value: str) -> list[object] | None:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, list) else None


__all__ = ["_resolve_custom_validation_strategy"]
