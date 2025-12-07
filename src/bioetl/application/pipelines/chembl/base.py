"""Base pipeline implementation for ChEMBL data extraction."""

from __future__ import annotations

from types import SimpleNamespace
from typing import cast

from bioetl.application.pipelines.base import (
    PipelineBase,
    _create_default_metadata_builder,
)
from bioetl.application.pipelines.chembl.extractor import ChemblExtractorImpl
from bioetl.application.pipelines.chembl.transformer import ChemblTransformerImpl
from bioetl.domain.clients.base.output.contracts import (
    OutputWriterABC,
    RunMetadataBuilderProtocol,
)
from bioetl.domain.clients.ports import ChemblExtractionPortABC
from bioetl.domain.configs import PipelineConfig
from bioetl.domain.models import RunContext
from bioetl.domain.observability import LoggingPortABC
from bioetl.domain.pipelines.contracts import ErrorPolicyABC, PipelineHookABC
from bioetl.domain.record_source import (
    FileRecordSourceFactoryABC,
    InMemoryRecordSource,
    RecordSource,
)
from bioetl.domain.schemas.pipeline_contracts import get_pipeline_contract
from bioetl.domain.transform.contracts import HashServiceABC, NormalizationServiceABC
from bioetl.domain.transform.transformers import TransformerABC
from bioetl.domain.validation.service import ValidationService


class ChemblPipelineBase(PipelineBase):
    """Базовый класс для ChEMBL-пайплайнов."""

    def __init__(
        self,
        config: PipelineConfig,
        logger: LoggingPortABC,
        validation_service: ValidationService,
        output_writer: OutputWriterABC,
        extraction_service: ChemblExtractionPortABC,
        hash_service: HashServiceABC,
        metadata_builder: RunMetadataBuilderProtocol | None = None,
        file_record_source_factory: FileRecordSourceFactoryABC | None = None,
        record_source: RecordSource | None = None,
        normalization_service: NormalizationServiceABC | None = None,
        hooks: list[PipelineHookABC] | None = None,
        error_policy: ErrorPolicyABC | None = None,
        post_transformer: TransformerABC | None = None,
    ) -> None:
        self._extraction_service = extraction_service
        self._chembl_release: str | None = None

        self.ID_COLUMN, self.API_FILTER_KEY = self._resolve_primary_key(config)

        if normalization_service is None:
            raise ValueError(
                "Normalization service is required. "
                "Inject NormalizationServiceABC from container."
            )
        norm_service = normalization_service

        # Create Extractor
        record_source_factory = (
            file_record_source_factory or _create_default_record_source_factory()
        )

        extractor = ChemblExtractorImpl(
            config=config,
            extraction_service=extraction_service,
            normalization_service=norm_service,
            logger=logger,
            record_source=record_source,
            file_record_source_factory=record_source_factory,
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
            metadata_builder=metadata_builder or _create_default_metadata_builder(),
            extractor=extractor,
            hooks=hooks,
            error_policy=error_policy,
            transformer=transformer,
            post_transformer=post_transformer,
        )

    @staticmethod
    def _resolve_primary_key(config: PipelineConfig) -> tuple[str, str]:
        """Resolve entity primary key and API filter key based on config."""

        pk = config.primary_key

        if not pk and config.pipeline and "primary_key" in config.pipeline:
            pk = config.pipeline["primary_key"]

        if not pk:
            pk = f"{config.entity_name}_id"

        if not pk:
            raise ValueError(
                (
                    "Could not resolve ID_COLUMN for entity "
                    f"'{config.entity_name}'. Please set 'primary_key' "
                    "in config or pipeline options."
                )
            )

        return pk, f"{pk}__in"

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


def _create_default_record_source_factory() -> FileRecordSourceFactoryABC:
    """Return record source factory that yields empty in-memory sources."""

    return cast(
        FileRecordSourceFactoryABC,
        SimpleNamespace(
            create_csv_source=lambda **kwargs: InMemoryRecordSource(
                [], chunk_size=kwargs.get("chunk_size")
            ),
            create_id_list_source=lambda **kwargs: InMemoryRecordSource(
                [], chunk_size=kwargs.get("chunk_size")
            ),
        ),
    )
