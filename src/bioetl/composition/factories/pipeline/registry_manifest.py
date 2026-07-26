"""Canonical composition-layer assembly manifest for pipeline registration."""

from __future__ import annotations

from bioetl.composition.factories.pipeline._registry_manifest_chembl import (
    CHEMBL_PIPELINE_CONFIGS,
)
from bioetl.composition.factories.pipeline._registry_manifest_non_chembl import (
    NON_CHEMBL_PIPELINE_CONFIGS,
)

PIPELINE_CONFIGS = (
    *CHEMBL_PIPELINE_CONFIGS,
    *NON_CHEMBL_PIPELINE_CONFIGS,
)

__all__ = ["PIPELINE_CONFIGS"]
