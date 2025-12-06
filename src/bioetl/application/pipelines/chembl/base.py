"""Base pipeline implementation for ChEMBL data extraction."""

from __future__ import annotations

from bioetl.application.config.pipeline_config_schema import PipelineConfig
from bioetl.application.pipelines.base import PipelineBase
from bioetl.application.pipelines.chembl.extractor import ChemblExtractorImpl
from bioetl.application.pipelines.chembl.transformer import ChemblTransformerImpl
from bioetl.application.pipelines.hooks import ErrorPolicyABC, PipelineHookABC
from bioetl.domain.contracts import ExtractionServiceABC
from bioetl.domain.models import RunContext
from bioetl.domain.normalization_service import (
    ChemblNormalizationService,
    NormalizationService,
)
from bioetl.domain.record_source import RecordSource
from bioetl.domain.schemas.pipeline_contracts import get_pipeline_contract
from bioetl.domain.transform.hash_service import HashService
from bioetl.domain.transform.transformers import TransformerABC
from bioetl.domain.validation.service import ValidationService
from bioetl.infrastructure.logging.contracts import LoggerAdapterABC
from bioetl.infrastructure.output.unified_writer import UnifiedOutputWriter


class ChemblPipelineBase(PipelineBase):
    """Базовый класс для ChEMBL-пайплайнов."""

    def __init__(
        self,
        config: PipelineConfig,
        logger: LoggerAdapterABC,
        validation_service: ValidationService,
        output_writer: UnifiedOutputWriter,
        extraction_service: ExtractionServiceABC,
        hash_service: HashService,
        record_source: RecordSource | None = None,
        normalization_service: NormalizationService | None = None,
        hooks: list[PipelineHookABC] | None = None,
        error_policy: ErrorPolicyABC | None = None,
        post_transformer: TransformerABC | None = None,
    ) -> None:
        self._extraction_service = extraction_service
        self._chembl_release: str | None = None

        norm_service = normalization_service or ChemblNormalizationService(config)

        # Create Extractor
        extractor = ChemblExtractorImpl(
            config=config,
            extraction_service=extraction_service,
            normalization_service=norm_service,
            logger=logger,
            record_source=record_source,
        )

        # Create Transformer
        # Need schema contract
        contract = get_pipeline_contract(config.id, default_entity=config.entity_name)
        transformer = ChemblTransformerImpl(
            validation_service=validation_service,
            schema_contract=contract,
            normalization_service=norm_service,
            logger=logger,
        )

        super().__init__(
            config=config,
            logger=logger,
            validation_service=validation_service,
            output_writer=output_writer,
            hash_service=hash_service,
            extractor=extractor,
            hooks=hooks,
            error_policy=error_policy,
            transformer=transformer,
            post_transformer=post_transformer,
        )

    def get_version(self) -> str:
        """Возвращает версию релиза ChEMBL (например, 'chembl_34')."""
        if self._chembl_release is None:
            self._chembl_release = self._extraction_service.get_release_version()
        return self._chembl_release

    def get_chembl_release(self) -> str:
        """Alias for get_version for backward compatibility."""
        return self.get_version()

    def _enrich_context(self, context: RunContext) -> None:
        """Adds ChEMBL release version to metadata."""
        context.metadata["chembl_release"] = self.get_version()

    # Removed extract, iter_chunks, transform, validate, write as they are in Base or Components.
    # pre_transform and _do_transform hooks?
    # They were called by ChemblPipelineBase.transform.
    # Now ChemblTransformerImpl.apply calls its own hooks.
    # If subclasses override pre_transform/_do_transform on THIS class,
    # they won't be called by ChemblTransformerImpl.

    # To support inheritance overriding, ChemblTransformerImpl should call back
    # or we should subclass ChemblTransformerImpl for specific pipelines.
    # Or we pass 'self' to transformer? No.

    # Most ChEMBL pipelines (Activity, Assay) didn't override them.
    # If they did, I'd need to check.
    # ChemblEntityPipeline might override?
