"""PubChem Compound Pipeline Implementation.

Updated: Transformer injection via DI (Phase 1 refactoring).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.core.base import BasePipeline

if TYPE_CHECKING:
    from bioetl.application.core.base_transformer import BaseTransformer
    from bioetl.application.core.pipeline_services import PipelineServices
    from bioetl.domain.config import PipelineConfig, RuntimeConfig
    from bioetl.domain.types import RunID


class PubChemCompoundPipeline(BasePipeline):
    """Pipeline for processing PubChem compounds.

    Transformer is injected via DI from GenericPipelineFactory.
    Fallback to local creation for backward compatibility with tests.
    """

    def __init__(
        self,
        config: PipelineConfig,
        runtime: RuntimeConfig,
        services: PipelineServices,
        run_id: RunID,
        transformer: "BaseTransformer | None" = None,
    ) -> None:
        """Initialize PubChem compound pipeline.

        Args:
            config: Pipeline configuration.
            runtime: Runtime configuration.
            services: Injected services (ports).
            run_id: Unique identifier for this pipeline run.
            transformer: Injected transformer (DI). If None, creates fallback.

        """
        # Create fallback transformer if not injected (backward compatibility)
        if transformer is None:
            from bioetl.application.pipelines.pubchem.transformer import (
                PubChemCompoundTransformer,
            )

            transformer = PubChemCompoundTransformer(provider=config.provider)

        super().__init__(config, runtime, services, run_id, transformer=transformer)

    # transform_bronze_to_silver() is inherited from BasePipeline
