"""Composition wiring for the ChEMBL protein-classification snapshot source (#11250)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.services.protein.classification_resolution import (
    ProteinClassificationResolutionService,
)
from bioetl.infrastructure.adapters.chembl.protein_classification_graph import (
    ChEMBLProteinClassificationGraph,
)
from bioetl.infrastructure.adapters.chembl.target_protein_classification_data_source import (
    TargetProteinClassificationSnapshotDataSource as _SnapshotDataSource,
)

if TYPE_CHECKING:
    from bioetl.domain.mapping.protein_class_target_type import (
        ProteinClassTargetTypeMappingData,
    )


def _resolution_factory(
    *,
    protein_class_rows: object,
    target_component_rows: object,
    invalid_record_policy: str,
    target_type_mapping_data: ProteinClassTargetTypeMappingData | None,
) -> ProteinClassificationResolutionService:
    return ProteinClassificationResolutionService(
        ChEMBLProteinClassificationGraph.from_rows(
            protein_class_rows=protein_class_rows,  # type: ignore[arg-type]
            target_component_rows=target_component_rows,  # type: ignore[arg-type]
        ),
        invalid_record_policy=invalid_record_policy,  # type: ignore[arg-type]
        target_type_mapping_data=target_type_mapping_data,
    )


class TargetProteinClassificationSnapshotDataSource(_SnapshotDataSource):
    """Inject the application resolution service into the infrastructure source."""

    def __init__(self, **kwargs: object) -> None:
        kwargs.setdefault("resolution_factory", _resolution_factory)
        super().__init__(**kwargs)  # type: ignore[arg-type]


__all__ = ["TargetProteinClassificationSnapshotDataSource"]
