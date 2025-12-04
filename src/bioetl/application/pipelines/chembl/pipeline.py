"""
Generic ChEMBL Entity Pipeline.

Replaces specific pipeline implementations (Activity, Assay, etc.)
with a configurable generic implementation.
"""
from bioetl.application.pipelines.chembl.base import ChemblPipelineBase
from bioetl.application.pipelines.hooks import ErrorPolicyABC, PipelineHookABC
from bioetl.domain.normalization_service import NormalizationService
from bioetl.domain.record_source import RecordSource
from bioetl.domain.contracts import ExtractionServiceABC
from bioetl.domain.transform.hash_service import HashService
from bioetl.domain.validation.service import ValidationService
from bioetl.infrastructure.config.models import PipelineConfig
from bioetl.infrastructure.logging.contracts import LoggerAdapterABC
from bioetl.infrastructure.output.unified_writer import UnifiedOutputWriter


class ChemblEntityPipeline(ChemblPipelineBase):
    """
    Универсальный пайплайн для сущностей ChEMBL.
    Конфигурируется через PipelineConfig.
    """

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
    ) -> None:
        super().__init__(
            config,
            logger,
            validation_service,
            output_writer,
            extraction_service,
            hash_service,
            record_source,
            normalization_service,
            hooks,
            error_policy,
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
