"""Canonical pipeline registry manifest for composition-layer assembly."""

from __future__ import annotations

from bioetl.composition.factories.pipeline._registry_manifest_chembl import (
    CHEMBL_PIPELINE_CONFIGS,
)
from bioetl.composition.factories.pipeline._registry_manifest_non_chembl import (
    NON_CHEMBL_PIPELINE_CONFIGS,
)
from bioetl.composition.factories.pipeline.config_types import PipelineFactoryConfig

PIPELINE_CONFIGS: tuple[PipelineFactoryConfig, ...] = (
    *CHEMBL_PIPELINE_CONFIGS,
    *NON_CHEMBL_PIPELINE_CONFIGS,
)

__all__ = [
    "PIPELINE_CONFIGS",
    "PipelineFactoryConfig",
]
