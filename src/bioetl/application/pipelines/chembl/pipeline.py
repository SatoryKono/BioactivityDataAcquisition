"""
Generic ChEMBL Entity Pipeline.

Replaces specific pipeline implementations (Activity, Assay, etc.)
with a configurable generic implementation.
"""

from bioetl.application.pipelines.chembl.base import ChemblPipelineBase
from bioetl.domain.clients.base.output.contracts import (
    OutputWriterABC,
    RunMetadataBuilderProtocol,
)
from bioetl.domain.clients.ports.contracts import ChemblExtractionPortABC
from bioetl.domain.configs import PipelineConfig
from bioetl.domain.observability import LoggingPortABC
from bioetl.domain.pipelines.contracts import ErrorPolicyABC, PipelineHookABC
from bioetl.domain.record_source import (
    FileRecordSourceFactoryABC,
    RecordSource,
)
from bioetl.domain.transform.contracts import HashServiceABC, NormalizationServiceABC
from bioetl.domain.validation.service import ValidationService


class ChemblEntityPipeline(ChemblPipelineBase):
    """
    Универсальный пайплайн для сущностей ChEMBL.
    Конфигурируется через PipelineConfig.
    """

    def __init__(
        self,
        config: PipelineConfig,
        logger: LoggingPortABC,
        validation_service: ValidationService,
        output_writer: OutputWriterABC,
        extraction_service: ChemblExtractionPortABC,
        hash_service: HashServiceABC,
        metadata_builder: RunMetadataBuilderProtocol,
        file_record_source_factory: FileRecordSourceFactoryABC,
        record_source: RecordSource | None = None,
        normalization_service: NormalizationServiceABC | None = None,
        hooks: list[PipelineHookABC] | None = None,
        error_policy: ErrorPolicyABC | None = None,
    ) -> None:
        super().__init__(
            config=config,
            logger=logger,
            validation_service=validation_service,
            output_writer=output_writer,
            extraction_service=extraction_service,
            hash_service=hash_service,
            metadata_builder=metadata_builder,
            file_record_source_factory=file_record_source_factory,
            record_source=record_source,
            normalization_service=normalization_service,
            hooks=hooks,
            error_policy=error_policy,
        )

        # Configure entity-specific constants from config
        # pylint: disable=invalid-name

        # Priority 1: Explicit field in PipelineConfig
        pk = config.primary_key

        # Priority 2: Legacy location in pipeline dictionary
        if not pk and config.pipeline and "primary_key" in config.pipeline:
            pk = config.pipeline["primary_key"]

        # Priority 3: Default based on entity name
        if not pk:
            pk = f"{config.entity_name}_id"

        if not pk:
            raise ValueError(
                f"Could not resolve ID_COLUMN for entity "
                f"'{config.entity_name}'. Please set 'primary_key' "
                "in config or pipeline options."
            )

        self.ID_COLUMN = pk
        self.API_FILTER_KEY = f"{self.ID_COLUMN}__in"

    # No custom _do_transform needed - base class handles everything
