"""Common ChEMBL pipeline with record mapping support."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.mappers.chembl.record_mapper import ChemblRecordMapper
from bioetl.application.pipelines.chembl.base import ChemblPipelineBase
from bioetl.application.pipelines.stages.extract import ExtractStage

if TYPE_CHECKING:
    from bioetl.domain.ports.extraction import ExtractionServiceABC


class ChemblCommonPipeline(ChemblPipelineBase):
    """Common ChEMBL pipeline with record mapping.

    This pipeline extends ChemblPipelineBase by providing an ExtractStage
    configured with ChemblRecordMapper for domain model validation.

    The mapper validates raw records against domain models (ActivityRawModel,
    MoleculeRawModel, etc.) before converting to DataFrames, ensuring data
    quality at the application layer.

    Example:
        >>> pipeline = ChemblCommonPipeline(
        ...     config=config,
        ...     logger=logger,
        ...     extraction_service=extraction_service,
        ...     # ... other dependencies
        ... )
        >>> extract_stage = pipeline.create_extract_stage()
        >>> for df in extract_stage.extract("activity", target_chembl_id="CHEMBL25"):
        ...     transformed = pipeline.transform(df)
    """

    def create_extract_stage(self) -> ExtractStage:
        """Create an ExtractStage with ChEMBL record mapping.

        Returns:
            ExtractStage configured with:
            - The pipeline's extraction service
            - ChemblRecordMapper for domain model validation
        """
        return ExtractStage(
            extraction_service=self._extraction_service,
            record_mapper=ChemblRecordMapper(),
        )

    def create_raw_extract_stage(self) -> ExtractStage:
        """Create an ExtractStage without record mapping.

        Returns:
            ExtractStage configured with extraction service only.
            Records are converted directly to DataFrames without validation.
        """
        return ExtractStage(
            extraction_service=self._extraction_service,
            record_mapper=None,
        )

    @property
    def extraction_service(self) -> "ExtractionServiceABC":
        """Get the underlying extraction service."""
        return self._extraction_service


__all__ = ["ChemblCommonPipeline"]
