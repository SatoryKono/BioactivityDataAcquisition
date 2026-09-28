"""Composition facade. Implementation lives in `bioetl.domain.chembl.target_protein_classification` (#11241)."""

from __future__ import annotations

from bioetl.domain.chembl.target_protein_classification import (
    target_id_from_record,
    component_ids_from_target_record,
    build_target_component_indexes,
    resolve_target_ids,
    target_ids_from_component_record,
    leaf_ids_from_component_row,
    leaf_ids_from_classification_objects,
    leaf_ids_from_value,
    coerce_positive_int,
    coerce_text,
    canonical_json,
)

__all__ = ['build_target_component_indexes', 'canonical_json', 'coerce_positive_int', 'coerce_text', 'component_ids_from_target_record', 'leaf_ids_from_classification_objects', 'leaf_ids_from_component_row', 'leaf_ids_from_value', 'resolve_target_ids', 'target_id_from_record', 'target_ids_from_component_record']
