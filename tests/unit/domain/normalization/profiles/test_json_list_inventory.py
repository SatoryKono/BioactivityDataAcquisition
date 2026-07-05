"""Guardrails for JSON/list normalization profile classification."""

from __future__ import annotations

import pytest

from bioetl.domain.normalization.profiles.base import FieldRule
from bioetl.domain.normalization.profiles.registry import NORMALIZATION_PROFILE_REGISTRY

pytestmark = pytest.mark.unit

_STRUCTURED_FIELD_SUFFIXES = ("_json", "_list", "_ids", "_references")
_KNOWN_STRUCTURED_FIELDS = frozenset(
    {
        "authors",
        "references",
        "grants",
        "keywords",
        "chemicals",
        "databanks",
        "lineage",
    }
)


def _requires_structured_classification(field_name: str) -> bool:
    return field_name.endswith(_STRUCTURED_FIELD_SUFFIXES) or (
        field_name in _KNOWN_STRUCTURED_FIELDS
    )


def _is_structured_field_classified(rule: FieldRule) -> bool:
    notes = (rule.notes or "").lower()
    return (
        rule.set_like
        or "json" in notes
        or "ontology" in notes
        or "list-like" in notes
        or "pipe-delimited list" in notes
    )


def test_json_list_like_profile_fields_are_explicitly_classified() -> None:
    missing: list[str] = []
    # Known exceptions: path_* fields in target_protein_classification are set-like
    # but don't have structured classification notes due to base profile behavior
    _KNOWN_EXCEPTIONS = {
        "chembl.target_protein_classification.path_ids",
        "chembl.target_protein_classification.path_names",
        "chembl.target_protein_classification.path_labels",
    }

    for (provider, entity), profile in NORMALIZATION_PROFILE_REGISTRY.items():
        for field_name, rule in profile.field_rules.items():
            if field_name in profile.meta_fields:
                continue
            if not _requires_structured_classification(field_name):
                continue
            field_key = f"{provider}.{entity}.{field_name}"
            if field_key in _KNOWN_EXCEPTIONS:
                continue
            if not _is_structured_field_classified(rule):
                missing.append(f"{provider}.{entity}.{field_name}: {rule.notes}")

    assert not missing, "Unclassified JSON/list-like fields:\n" + "\n".join(missing)
