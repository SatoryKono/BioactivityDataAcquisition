"""UniProt Protein Pipeline Implementation.

Transformer is injected via DI from GenericPipelineFactory (REQ-ARCH-DI-007).
"""

from __future__ import annotations

from bioetl.application.core.base import BasePipeline


class UniProtProteinPipeline(BasePipeline):
    """Pipeline for processing UniProt proteins.

    Transformer is injected via DI from GenericPipelineFactory.
    """

    # transform_bronze_to_silver() is inherited from BasePipeline
