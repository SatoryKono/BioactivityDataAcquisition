"""Bootstrap classification mapping data."""

from __future__ import annotations

from functools import cache
from pathlib import Path

from bioetl.domain.mapping.classification_data import ClassificationData


@cache
def _load_publication_type_classification_data(configs_root_key: str) -> ClassificationData:
    """Load classification data once per configs root key."""
    from bioetl.infrastructure.config import (
        publication_type_classification_loader as loader_module,
    )

    return loader_module.PublicationTypeClassificationLoader(
        Path(configs_root_key)
    ).load()


def initialize_publication_type_classification(configs_root: Path) -> None:
    """Load publication type classification data into the domain module."""
    from bioetl.domain.mapping import publication_type_classification

    data = _load_publication_type_classification_data(str(configs_root))
    publication_type_classification.initialize_classification(data)


@cache
def _load_protein_class_target_type_mapping_data(configs_root_key: str) -> object:
    """Load protein-class target type mapping once per configs root key."""
    from bioetl.infrastructure.config import protein_class_target_type_loader

    return protein_class_target_type_loader.ProteinClassTargetTypeMappingLoader(
        Path(configs_root_key)
    ).load()


def initialize_protein_class_target_type_mapping(configs_root: Path) -> None:
    """Load protein-class L1 mapping and initialize the domain rule module."""
    from bioetl.domain.mapping import protein_class_target_type

    data = _load_protein_class_target_type_mapping_data(str(configs_root))
    protein_class_target_type.initialize_protein_class_target_type_mapping(data)
