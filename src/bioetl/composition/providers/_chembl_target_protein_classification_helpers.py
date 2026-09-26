"""Composition facade. Implementation lives in `bioetl.domain.chembl.target_protein_classification` (#11241)."""

from __future__ import annotations

from bioetl.domain.chembl.target_protein_classification import (
    _TARGET_PROTEIN_CLASSIFICATION_ENTITY_TYPE,
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

__all__ = ['target_id_from_record', 'component_ids_from_target_record', 'build_target_component_indexes', 'resolve_target_ids', 'target_ids_from_component_record', 'leaf_ids_from_component_row', 'leaf_ids_from_classification_objects', 'leaf_ids_from_value', 'coerce_positive_int', 'coerce_text', 'canonical_json']
