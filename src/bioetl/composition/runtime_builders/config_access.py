"""Composition-facing seam for runtime configuration access helpers."""

from __future__ import annotations

from functools import cache


from bioetl.domain.mapping.classification_data import ClassificationData
from bioetl.domain.mapping.protein_class_target_type import (
    ProteinClassTargetTypeMappingData,
)

from bioetl.domain.mapping import publication_type_classification
from bioetl.domain.mapping import protein_class_target_type
import bioetl.infrastructure.config.publication_type_classification_loader as publication_type_classification_loader
import bioetl.infrastructure.config.protein_class_target_type_loader as protein_class_target_type_loader


from pathlib import Path

from bioetl.composition.runtime_builders import _config_access_loaders
import bioetl.infrastructure.config.config_root as _config_root
import bioetl.infrastructure.config.dq_contract_config_loader as _dq_config_loader
import bioetl.infrastructure.config.pipeline_config_api as _pipeline_config_api
import bioetl.infrastructure.config.settings_api as _settings_api
import bioetl.infrastructure.config.source_config_loader as _source_config_loader
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

__all__ = [
    "create_dq_config_loader",
    "create_pipeline_config_loader",
    "create_source_config_loader",
    "get_settings",
    "load_dq_config_for_pipeline",
    "load_pipeline_config",
    "load_settings",
    "load_source_config",
    "resolve_configs_root",
]


create_pipeline_config_loader = _config_access_loaders.create_pipeline_config_loader
create_dq_config_loader = _config_access_loaders.create_dq_config_loader
create_source_config_loader = _config_access_loaders.create_source_config_loader
resolve_configs_root = _config_root.resolve_configs_root
_load_pipeline_config = _pipeline_config_api.load_pipeline_config
_load_dq_config_for_pipeline = _dq_config_loader.load_dq_config_for_pipeline


def get_settings() -> _settings_api.Settings:

    return _settings_api.get_settings()


def load_settings() -> _settings_api.Settings:
    return _settings_api.Settings()


def load_pipeline_config(pipeline_name: str) -> PipelineYamlConfig:
    """Load pipeline YAML through the canonical infrastructure entrypoint."""

    return _load_pipeline_config(pipeline_name)


def load_source_config(provider: str) -> object:

    return _source_config_loader.load_source_config(provider)


def load_dq_config_for_pipeline(
    pipeline_name: str,
    *,
    configs_root: Path | None = None,
) -> object:
    """Load DQ config through the canonical infrastructure entrypoint."""

    if configs_root is None:
        configs_root = resolve_configs_root(None)
    return _load_dq_config_for_pipeline(
        pipeline_name,
        configs_root=configs_root,
    )


@cache
def _load_publication_type_classification_data(
    configs_root_key: str,
) -> ClassificationData:
    """Load classification data once per configs root key."""

    return publication_type_classification_loader.PublicationTypeClassificationLoader(
        Path(configs_root_key)
    ).load()


def initialize_publication_type_classification(configs_root: Path) -> None:
    """Load publication type classification data into the domain module."""

    data = _load_publication_type_classification_data(str(configs_root))
    publication_type_classification.initialize_classification(data)


@cache
def _load_protein_class_target_type_mapping_data(
    configs_root_key: str,
) -> ProteinClassTargetTypeMappingData:
    """Load protein-class target type mapping once per configs root key."""

    return protein_class_target_type_loader.ProteinClassTargetTypeMappingLoader(
        Path(configs_root_key)
    ).load()


def initialize_protein_class_target_type_mapping(configs_root: Path) -> None:
    """Load protein-class L1 mapping and initialize the domain rule module."""

    data = _load_protein_class_target_type_mapping_data(str(configs_root))
    protein_class_target_type.initialize_protein_class_target_type_mapping(data)
