"""Composition wiring for the ChEMBL protein-classification snapshot source (#11250)."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import TYPE_CHECKING, Required, TypedDict, Unpack

from bioetl.application.services.protein.classification_resolution import (
    InvalidRecordPolicy,
    ProteinClassificationResolutionService,
)
from bioetl.domain.chembl.target_protein_classification import (
    _TARGET_PROTEIN_CLASSIFICATION_ENTITY_TYPE,
    build_target_component_indexes,
    resolve_target_ids,
)
from bioetl.infrastructure.adapters.chembl.protein_classification_graph import (
    ChEMBLProteinClassificationGraph,
)
from bioetl.infrastructure.adapters.chembl.target_protein_classification_data_source import (
    TargetProteinClassificationSnapshotDataSource as _SnapshotDataSource,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from bioetl.domain.mapping.protein_class_target_type import (
        ProteinClassTargetTypeMappingData,
    )
    from bioetl.domain.ports import DeltaReaderPort, LoggerPort
    from bioetl.infrastructure.adapters.chembl.target_protein_classification_loading_mixin import (
        IndexBuilder,
        TargetIdResolver,
    )


class _SnapshotSourceArgs(TypedDict, total=False):
    delta_reader: Required[DeltaReaderPort]
    logger: Required[LoggerPort]
    invalid_record_policy: str
    target_type_mapping_data: ProteinClassTargetTypeMappingData | None
    resolution_factory: Callable[..., object] | None
    entity_type: str
    index_builder: IndexBuilder
    target_id_resolver: TargetIdResolver


def _resolution_factory(
    *,
    protein_class_rows: Iterable[Mapping[str, object]],
    target_component_rows: Iterable[Mapping[str, object]],
    invalid_record_policy: InvalidRecordPolicy,
    target_type_mapping_data: ProteinClassTargetTypeMappingData | None,
) -> ProteinClassificationResolutionService:
    return ProteinClassificationResolutionService(
        ChEMBLProteinClassificationGraph.from_rows(
            protein_class_rows=protein_class_rows,
            target_component_rows=target_component_rows,
        ),
        invalid_record_policy=invalid_record_policy,
        target_type_mapping_data=target_type_mapping_data,
    )


class TargetProteinClassificationSnapshotDataSource(_SnapshotDataSource):
    """Inject the application resolution service into the infrastructure source."""

    def __init__(self, **kwargs: Unpack[_SnapshotSourceArgs]) -> None:
        kwargs.setdefault("resolution_factory", _resolution_factory)
        kwargs.setdefault("entity_type", _TARGET_PROTEIN_CLASSIFICATION_ENTITY_TYPE)
        kwargs.setdefault("index_builder", build_target_component_indexes)
        kwargs.setdefault("target_id_resolver", resolve_target_ids)
        super().__init__(**kwargs)


__all__ = ["TargetProteinClassificationSnapshotDataSource"]
