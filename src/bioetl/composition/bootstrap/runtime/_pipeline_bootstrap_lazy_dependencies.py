"""Lazy policy and registry dependencies for pipeline bootstrap phases."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.composition.factories.pipeline.registry import (
        PipelineFactoryRegistrationState,
        PipelineRegistryProtocol,
    )


def initialize_chembl_policy_registry(configs_root: Path) -> None:
    """Initialize the ChEMBL normalization-policy registry lazily."""
    from bioetl.composition.bootstrap.runtime.normalization_policy_init import (
        initialize_chembl_policy_registry as _initialize,
    )

    _initialize(configs_root)


def initialize_publication_controlled_vocabulary(configs_root: Path) -> None:
    """Initialize publication controlled vocabularies lazily."""
    from bioetl.composition.bootstrap.runtime.publication_vocab_init import (
        initialize_publication_controlled_vocabulary as _initialize,
    )

    _initialize(configs_root)


def initialize_publication_type_classification(configs_root: Path) -> None:
    """Initialize publication-type classification lazily."""
    from bioetl.composition.bootstrap.runtime.classification_init import (
        initialize_publication_type_classification as _initialize,
    )

    _initialize(configs_root)


def initialize_protein_class_target_type_mapping(configs_root: Path) -> None:
    """Initialize protein-class target-type mappings lazily."""
    from bioetl.composition.bootstrap.runtime.classification_init import (
        initialize_protein_class_target_type_mapping as _initialize,
    )

    _initialize(configs_root)


def register_all_pipelines(
    registry: PipelineRegistryProtocol | None = None,
    *,
    registration_state: PipelineFactoryRegistrationState | None = None,
) -> None:
    """Register all pipeline factories without importing them at module load."""
    from bioetl.composition.factories.pipeline.registry import (
        register_all_pipelines as _register_all_pipelines,
    )

    _register_all_pipelines(
        registry=registry,
        registration_state=registration_state,
    )
