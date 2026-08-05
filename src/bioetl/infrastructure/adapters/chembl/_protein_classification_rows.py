"""Row parsers for ChEMBL protein classification graph construction."""

from __future__ import annotations

import json
from collections.abc import Mapping

from bioetl.domain.value_objects.protein_class_hierarchy import (
    ProteinClassificationResolutionError,
)
from bioetl.infrastructure.adapters.chembl._protein_classification_coerce import (
    coerce_int,
    coerce_int_tuple,
    coerce_positive_int,
    coerce_str,
    load_json_if_needed,
)
from bioetl.infrastructure.adapters.chembl._protein_classification_node import (
    ProteinClassificationNode,
)

__all__ = [
    "component_leaf_ids_from_row",
    "node_from_row",
]


def node_from_row(
    row: Mapping[str, object],
) -> ProteinClassificationNode | None:
    protein_class_id = coerce_int(row.get("protein_class_id"))
    if protein_class_id is None or protein_class_id < 1:
        return None
    return ProteinClassificationNode(
        protein_class_id=protein_class_id,
        parent_id=coerce_positive_int(row.get("parent_id")),
        class_level=coerce_int(row.get("class_level")),
        pref_name=coerce_str(row.get("pref_name")),
        protein_class_desc=coerce_str(row.get("protein_class_desc")),
        replaced_by=coerce_positive_int(row.get("replaced_by")),
    )


def component_leaf_ids_from_row(
    row: Mapping[str, object],
) -> tuple[int | None, tuple[int, ...]]:
    component_id = coerce_int(row.get("component_id"))
    if component_id is None or component_id < 1:
        return None, ()
    leaf_ids = leaf_ids_from_value(row.get("protein_classification_ids"))
    if not leaf_ids:
        leaf_ids = leaf_ids_from_forensic_value(row.get("protein_classifications"))
    return component_id, leaf_ids


def leaf_ids_from_value(value: object) -> tuple[int, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return ()
        try:
            loaded = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise ProteinClassificationResolutionError(
                "protein_classification_ids must be canonical JSON"
            ) from exc
        return coerce_int_tuple(loaded)
    return coerce_int_tuple(value)


def leaf_ids_from_forensic_value(value: object) -> tuple[int, ...]:
    if value is None:
        return ()
    loaded = load_json_if_needed(value)
    if not isinstance(loaded, list):
        return ()
    leaf_ids: list[int] = []
    for item in loaded:
        if isinstance(item, Mapping):
            leaf_id = coerce_int(item.get("protein_classification_id"))
            if leaf_id is not None and leaf_id > 0:
                leaf_ids.append(leaf_id)
    return tuple(dict.fromkeys(leaf_ids))
