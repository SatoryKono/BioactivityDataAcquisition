"""ChEMBL Subcellular Fraction Pipeline.

Extracts unique subcellular fraction values from ChEMBL Assay records
and processes through Bronze → Silver → Gold layers.

Entity: Subcellular Fraction (derived from Assay)
Provider: ChEMBL (https://www.ebi.ac.uk/chembl/)

This is a derived entity pipeline - it extracts unique assay_subcellular_fraction
values from Assay API responses. ChEMBL does NOT have a dedicated
/subcellular_fraction endpoint.

Transformer is injected via DI from GenericPipelineFactory (REQ-ARCH-DI-007).

.. versionadded:: 2.1.0
    Added as derived entity pipeline (ADR-030).
"""

from __future__ import annotations

from bioetl.application.core.base import BasePipeline


class ChEMBLSubcellularFractionPipeline(BasePipeline):
    """Pipeline for ChEMBL subcellular fraction data.

    This pipeline extracts unique subcellular fraction values from Assay records:
    - Cellular compartments used in bioassays (e.g., "Microsomes", "Cytosol")
    - Preparation types (e.g., "Mitochondria", "Membrane fraction")

    Subcellular fractions describe the biological context of biochemical assays.

    Uses SubcellularFractionDataSource wrapper to extract and deduplicate
    unique values from /assay endpoint responses.

    Transformer is injected via DI from GenericPipelineFactory.

    .. versionadded:: 2.1.0
        Added for derived entity support with force_full_scan (ADR-030).
    """

    # transform_bronze_to_silver() is inherited from BasePipeline
    # should_write_gold() is inherited from BasePipeline (uses config.gold_filters)
