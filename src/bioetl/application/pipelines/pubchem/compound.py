"""PubChem Compound Pipeline Implementation.

Transformer is injected via DI from GenericPipelineFactory (REQ-ARCH-DI-007).
"""

from __future__ import annotations

from bioetl.application.core.base import BasePipeline


class PubChemCompoundPipeline(BasePipeline):
    """Pipeline for processing PubChem compounds.

    Transformer is injected via DI from GenericPipelineFactory.
    """

    # transform_bronze_to_silver() is inherited from BasePipeline
