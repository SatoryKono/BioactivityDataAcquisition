"""DQ rule evaluator dictionaries and helper functions.

Extracted from dq_rule_evaluator.py to meet file size limits.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from bioetl.domain.behavior._dq_condition_matchers import (
    _CONDITIONAL_MATCHERS,
)
from bioetl.domain.behavior._dq_rule_evaluators_cross import (
    _all_present_rule_violated,
    _any_present_rule_violated,
    _conditional_required_rule_violated,
    _custom_cross_field_rule_violated,
    _mutually_exclusive_rule_violated,
)
from bioetl.domain.behavior._dq_rule_evaluators_cross import (
    _custom_cross_rule_violated as _custom_cross_rule_violated_impl,
)
from bioetl.domain.behavior._dq_value_coercion import (
    _coerce_list_like,
    _coerce_numeric_value,
    _is_present,
    _violates_maximum,
    _violates_minimum,
)
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

if TYPE_CHECKING:
    from bioetl.domain.config.validation import (
        CrossFieldValidation,
        FieldValidation,
    )
    from bioetl.domain.types import JsonDict


def _field_rule_violated(record: JsonDict, rule: FieldValidation) -> bool:
    value = record.get(rule.field)
    evaluator = _FIELD_RULE_EVALUATORS.get(rule.validation_type)
    if evaluator is None:
        return False
    return evaluator(record, rule, value)


def _cross_rule_violated(record: JsonDict, rule: CrossFieldValidation) -> bool:
    values = [record.get(field) for field in rule.fields]
    present_count = sum(1 for value in values if _is_present(value))
    evaluator = _CROSS_RULE_EVALUATORS.get(rule.condition)
    if evaluator is None:
        return False
    return evaluator(record, rule, present_count)


def _conditional_matches(record: JsonDict, rule: CrossFieldValidation) -> bool:
    value = record.get(rule.condition_field)
    evaluator = _CONDITIONAL_MATCHERS.get(rule.condition_operator)
    if evaluator is None:
        return False
    return evaluator(value, rule.condition_value)


def _range_rule_violated(value: object, rule: FieldValidation) -> bool:
    numeric_value = _coerce_numeric_value(value)
    if numeric_value is None:
        return True
    return _violates_minimum(numeric_value, rule) or _violates_maximum(
        numeric_value, rule
    )


def _pattern_rule_violated(value: object, rule: FieldValidation) -> bool:
    import re

    if not isinstance(value, str) or rule.pattern is None:
        return True
    return re.search(rule.pattern, value) is None


def _max_length_rule_violated(value: object, rule: FieldValidation) -> bool:
    if not isinstance(value, str) or rule.max_length is None:
        return True
    return len(value) > rule.max_length


def _not_empty_list_rule_violated(value: object) -> bool:
    list_like = _coerce_list_like(value)
    if list_like is None:
        return True
    return len(list_like) == 0


def _custom_rule_violated(
    record: JsonDict,
    value: object,
    validator_name: str | None,
) -> bool:
    from bioetl.domain.validation.chemical import validate_smiles

    if validator_name == "smiles_validator":
        return value is not None and not validate_smiles(str(value))
    target_vocabulary = _target_json_vocabulary(validator_name)
    if target_vocabulary is not None:
        return _target_json_vocabulary_rule_violated(
            value,
            allowed_values=target_vocabulary,
        )
    target_xref_vocabulary = _target_xref_json_vocabulary(validator_name)
    if target_xref_vocabulary is not None:
        return _target_xref_json_vocabulary_rule_violated(
            value,
            allowed_values=target_xref_vocabulary,
        )
    publication_taxonomy = _publication_taxonomy_vocabulary(validator_name)
    if publication_taxonomy is not None:
        return _publication_taxonomy_rule_violated(
            value,
            allowed_values=publication_taxonomy,
        )
    if validator_name == "validate_hierarchy_no_self_reference":
        return _custom_cross_rule_violated(
            record,
            validator_name,
        )
    return False


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


def _custom_cross_rule_violated(
    record: JsonDict,
    validator_name: str | None,
) -> bool:
    return _custom_cross_rule_violated_impl(record, validator_name)


def _required_rule_violated(
    record: JsonDict,
    rule: FieldValidation,
    value: object,
) -> bool:
    return rule.field not in record or value is None


def _not_null_rule_violated(
    record: JsonDict,
    rule: FieldValidation,
    value: object,
) -> bool:
    del record, rule
    return value is None


def _range_field_rule_violated(
    record: JsonDict,
    rule: FieldValidation,
    value: object,
) -> bool:
    del record
    return False if value is None else _range_rule_violated(value, rule)


def _pattern_field_rule_violated(
    record: JsonDict,
    rule: FieldValidation,
    value: object,
) -> bool:
    del record
    return False if value is None else _pattern_rule_violated(value, rule)


def _enum_field_rule_violated(
    record: JsonDict,
    rule: FieldValidation,
    value: object,
) -> bool:
    del record
    return False if value is None else value not in set(rule.allowed)


def _max_length_field_rule_violated(
    record: JsonDict,
    rule: FieldValidation,
    value: object,
) -> bool:
    del record
    return False if value is None else _max_length_rule_violated(value, rule)


def _not_empty_list_field_rule_violated(
    record: JsonDict,
    rule: FieldValidation,
    value: object,
) -> bool:
    del record, rule
    return False if value is None else _not_empty_list_rule_violated(value)


def _custom_field_rule_violated(
    record: JsonDict,
    rule: FieldValidation,
    value: object,
) -> bool:
    if value is None:
        return False
    return _custom_rule_violated(record, value, rule.validator)


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
    for item in list_like:
        if not isinstance(item, dict):
            return True
        source_value = item.get("xref_src_db")
        if not isinstance(source_value, str) or source_value not in allowed_values:
            return True
    return False


def _coerce_target_json_list(value: object) -> list[object] | None:
    if isinstance(value, str):
        return _coerce_string_list_like(value)
    if isinstance(value, list):
        return value
    return None


_FIELD_RULE_EVALUATORS = {
    "required": _required_rule_violated,
    "not_null": _not_null_rule_violated,
    "range": _range_field_rule_violated,
    "pattern": _pattern_field_rule_violated,
    "enum": _enum_field_rule_violated,
    "max_length": _max_length_field_rule_violated,
    "not_empty_list": _not_empty_list_field_rule_violated,
    "custom": _custom_field_rule_violated,
}


_CROSS_RULE_EVALUATORS = {
    "all_present": _all_present_rule_violated,
    "any_present": _any_present_rule_violated,
    "mutually_exclusive": _mutually_exclusive_rule_violated,
    "conditional_required": _conditional_required_rule_violated,
    "custom": _custom_cross_field_rule_violated,
}


__all__ = [
    "_conditional_matches",
    "_cross_rule_violated",
    "_field_rule_violated",
]
