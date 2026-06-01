"""Canonical ChEMBL pipeline marker class definitions.

All ChEMBL entity pipelines inherit 100% of their logic from BasePipeline.
Transformers are injected via DI from GenericPipelineFactory (REQ-ARCH-DI-007).
Individual classes exist for type identity and IDE discoverability.
"""

from __future__ import annotations

__all__ = [
    "ChEMBLActivityPipeline",
    "ChEMBLAssayParametersPipeline",
    "ChEMBLAssayPipeline",
    "ChEMBLCellLinePipeline",
    "ChEMBLCompoundRecordPipeline",
    "ChEMBLMoleculePipeline",
    "ChEMBLProteinClassPipeline",
    "ChEMBLPublicationPipeline",
    "ChEMBLPublicationSimilarityPipeline",
    "ChEMBLPublicationTermPipeline",
    "ChEMBLSubcellularFractionPipeline",
    "ChEMBLTargetComponentPipeline",
    "ChEMBLTargetPipeline",
    "ChEMBLTargetProteinClassificationPipeline",
    "ChEMBLTissuePipeline",
]

from bioetl.application.core.base import BasePipeline


class ChEMBLActivityPipeline(BasePipeline):
    """Pipeline for ChEMBL bioactivity data (IC50, Ki, EC50, etc.)."""


class ChEMBLAssayPipeline(BasePipeline):
    """Pipeline for ChEMBL assay definitions (binding, functional, ADMET)."""


class ChEMBLAssayParametersPipeline(BasePipeline):
    """Pipeline for ChEMBL assay parameters."""


class ChEMBLCellLinePipeline(BasePipeline):
    """Pipeline for ChEMBL cell line data (in vitro experiment objects)."""


class ChEMBLCompoundRecordPipeline(BasePipeline):
    """Pipeline for ChEMBL compound records (molecule-document links)."""


class ChEMBLMoleculePipeline(BasePipeline):
    """Pipeline for ChEMBL molecule data (small molecules, antibodies)."""


class ChEMBLProteinClassPipeline(BasePipeline):
    """Pipeline for ChEMBL protein classification hierarchy."""


class ChEMBLPublicationPipeline(BasePipeline):
    """Pipeline for ChEMBL publication data."""


class ChEMBLPublicationSimilarityPipeline(BasePipeline):
    """Pipeline for ChEMBL publication similarity (Tanimoto coefficients).

    .. versionchanged:: 2.0.0
        Renamed from ChEMBLDocumentSimilarityPipeline (ADR-024).
    """


class ChEMBLPublicationTermPipeline(BasePipeline):
    """Pipeline for ChEMBL publication terms (MeSH headings, keywords).

    .. versionchanged:: 2.0.0
        Renamed from ChEMBLDocumentTermPipeline (ADR-024).
    """


class ChEMBLSubcellularFractionPipeline(BasePipeline):
    """Pipeline for ChEMBL subcellular fraction data (derived from Assay).

    .. versionadded:: 2.1.0
        Added as derived entity pipeline (ADR-030).
    """


class ChEMBLTargetPipeline(BasePipeline):
    """Pipeline for ChEMBL biological targets (proteins, complexes)."""


class ChEMBLTargetComponentPipeline(BasePipeline):
    """Pipeline for ChEMBL target component data (protein sequences)."""


class ChEMBLTargetProteinClassificationPipeline(BasePipeline):
    """Pipeline for derived ChEMBL target-to-protein-classification relations."""


class ChEMBLTissuePipeline(BasePipeline):
    """Pipeline for ChEMBL tissue data (anatomical structures)."""
