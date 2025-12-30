"""Backward compatibility module for deprecated pipeline classes.

This module provides deprecated aliases for provider-specific pipeline classes
that have been replaced by GenericPipeline.

All pipeline classes now use GenericPipeline directly. The old class names
are kept as type aliases with deprecation warnings.

Usage:
    # Old (deprecated):
    from bioetl.application.pipelines.chembl import ChEMBLActivityPipeline
    pipeline = ChEMBLActivityPipeline(...)  # Warning emitted

    # New (recommended):
    from bioetl.application.pipelines.generic import GenericPipeline
    pipeline = GenericPipeline(...)

The deprecated aliases will be removed in a future version.
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

from bioetl.application.pipelines.generic import GenericPipeline

if TYPE_CHECKING:
    from bioetl.application.core.base_transformer import BaseTransformer
    from bioetl.application.core.pipeline_services import PipelineServices
    from bioetl.domain.config import PipelineConfig, RuntimeConfig
    from bioetl.domain.types import RunID


def _create_deprecated_alias(
    class_name: str,
    provider: str,
    entity_type: str,
) -> type[GenericPipeline]:
    """Create a deprecated class alias for a pipeline.

    Args:
        class_name: Original class name (e.g., "ChEMBLActivityPipeline")
        provider: Provider name (e.g., "chembl")
        entity_type: Entity type (e.g., "activity")

    Returns:
        A class that behaves like GenericPipeline but emits a deprecation warning
    """

    class DeprecatedPipelineAlias(GenericPipeline):
        """Deprecated pipeline class - use GenericPipeline instead."""

        __doc__ = f"""Deprecated: {class_name} is deprecated.

        Use GenericPipeline directly instead. This class will be removed in a future version.

        Provider: {provider}
        Entity: {entity_type}
        """

        def __init__(
            self,
            config: PipelineConfig,
            runtime: RuntimeConfig,
            services: PipelineServices,
            run_id: RunID,
            transformer: BaseTransformer | None = None,
        ) -> None:
            warnings.warn(
                f"{class_name} is deprecated and will be removed in a future version. "
                "Use GenericPipeline directly instead. All pipeline-specific behavior "
                "is now configured via YAML configs and injected transformers.",
                DeprecationWarning,
                stacklevel=2,
            )
            super().__init__(config, runtime, services, run_id, transformer)

    # Set the class name for better error messages
    DeprecatedPipelineAlias.__name__ = class_name
    DeprecatedPipelineAlias.__qualname__ = class_name

    return DeprecatedPipelineAlias


# =============================================================================
# ChEMBL Pipeline Aliases
# =============================================================================

ChEMBLActivityPipeline: type[GenericPipeline] = _create_deprecated_alias(
    "ChEMBLActivityPipeline", "chembl", "activity"
)

ChEMBLAssayPipeline: type[GenericPipeline] = _create_deprecated_alias(
    "ChEMBLAssayPipeline", "chembl", "assay"
)

ChEMBLDocumentPipeline: type[GenericPipeline] = _create_deprecated_alias(
    "ChEMBLDocumentPipeline", "chembl", "document"
)

ChEMBLMoleculePipeline: type[GenericPipeline] = _create_deprecated_alias(
    "ChEMBLMoleculePipeline", "chembl", "molecule"
)

ChEMBLTargetPipeline: type[GenericPipeline] = _create_deprecated_alias(
    "ChEMBLTargetPipeline", "chembl", "target"
)

ChEMBLTargetComponentPipeline: type[GenericPipeline] = _create_deprecated_alias(
    "ChEMBLTargetComponentPipeline", "chembl", "target_component"
)

ChEMBLCompoundRecordPipeline: type[GenericPipeline] = _create_deprecated_alias(
    "ChEMBLCompoundRecordPipeline", "chembl", "compound_record"
)

ChEMBLCellLinePipeline: type[GenericPipeline] = _create_deprecated_alias(
    "ChEMBLCellLinePipeline", "chembl", "cell_line"
)


# =============================================================================
# PubChem Pipeline Aliases
# =============================================================================

PubChemCompoundPipeline: type[GenericPipeline] = _create_deprecated_alias(
    "PubChemCompoundPipeline", "pubchem", "compound"
)


# =============================================================================
# UniProt Pipeline Aliases
# =============================================================================

UniProtProteinPipeline: type[GenericPipeline] = _create_deprecated_alias(
    "UniProtProteinPipeline", "uniprot", "protein"
)


# =============================================================================
# PubMed Pipeline Aliases
# =============================================================================

PubMedPublicationsPipeline: type[GenericPipeline] = _create_deprecated_alias(
    "PubMedPublicationsPipeline", "pubmed", "publications"
)


__all__ = [
    "ChEMBLActivityPipeline",
    "ChEMBLAssayPipeline",
    "ChEMBLCellLinePipeline",
    "ChEMBLCompoundRecordPipeline",
    "ChEMBLDocumentPipeline",
    "ChEMBLMoleculePipeline",
    "ChEMBLTargetComponentPipeline",
    "ChEMBLTargetPipeline",
    "PubChemCompoundPipeline",
    "PubMedPublicationsPipeline",
    "UniProtProteinPipeline",
]
