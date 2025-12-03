"""
Generic ChEMBL Entity Pipeline.

Replaces specific pipeline implementations (Activity, Assay, etc.)
with a configurable generic implementation.
"""
from bioetl.application.pipelines.chembl.base import ChemblPipelineBase
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
        hash_service: HashService | None = None,
    ) -> None:
        super().__init__(
            config,
            logger,
            validation_service,
            output_writer,
            extraction_service,
            hash_service,
        )

        # Configure entity-specific constants from config
        # Pipeline config MUST provide 'primary_key'
        # pylint: disable=invalid-name
        pk = getattr(config, "primary_key", f"{config.entity_name}_id")
        self.ID_COLUMN = pk
        
        # Override ID_COLUMN for assay entity if defaulting to 'assay_id' but csv has 'assay_chembl_id'
        # Actually better to respect config. If config says assay_chembl_id, use it.
        # The issue is likely that config.primary_key IS assay_chembl_id, but the code below uses it as the column name to look for in CSV.
        # And CSV HAS assay_chembl_id.
        # Wait, the error said: "Input file ... must contain 'assay_id'"
        # This means self.ID_COLUMN was resolved to 'assay_id'.
        # Let's check why.
        # In assay.yaml: primary_key: assay_chembl_id
        # So config.primary_key should be 'assay_chembl_id'.
        # Unless config loading is failing to pick it up?
        # Or maybe I am looking at the wrong file?
        # Let's print debug info in __init__ temporarily or just fix logic.
        
        # Actually, let's look at ChemblEntityPipeline.__init__ again.
        # pk = getattr(config, "primary_key", f"{config.entity_name}_id")
        # PipelineConfig model does NOT have a 'primary_key' field at the top level!
        # It has provider, entity_name, etc.
        # primary_key might be in 'pipeline' dict or 'cli' dict or effectively lost if not modeled.
        # Let's check PipelineConfig in src/bioetl/infrastructure/config/models.py
        # It does NOT have primary_key field.
        # So getattr(config, "primary_key") fails (AttributeError) -> default value used?
        # No, getattr(obj, name, default) catches AttributeError.
        # So it defaults to f"{config.entity_name}_id" -> "assay_id".
        
        # FIX: We need to get primary_key from the loaded config dictionary which might be in 'pipeline' or just passed through if the loader supports it.
        # But config is a Pydantic model. Extra fields might be ignored or stored in __pydantic_extra__.
        # Better: Look in config.pipeline dict if we put it there, or add primary_key to PipelineConfig model.
        # Looking at assay.yaml, 'primary_key' is at top level.
        # If PipelineConfig doesn't define it, it's dropped by Pydantic unless extra='allow'.
        
        # Strategy 1: Check config.pipeline for it (if we move it there in yaml).
        # Strategy 2: Add it to PipelineConfig model.
        # Strategy 3: Check if it's available via model_dump or similar.
        
        # The YAML shows primary_key at top level.
        # Let's add it to PipelineConfig model to support it properly.
        
        self.API_FILTER_KEY = f"{self.ID_COLUMN}__in"

    # No custom _do_transform needed - base class handles everything
