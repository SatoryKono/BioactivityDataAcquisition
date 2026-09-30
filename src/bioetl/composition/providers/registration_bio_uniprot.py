"""UniProt ID Mapping config resolvers for bio provider registration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.domain.runtime.composition_boundary_policy import (
    resolve_uniprot_mapping_databases,
)
from bioetl.infrastructure.adapters.uniprot.constants import UNIPROT_API_BASE

if TYPE_CHECKING:
    from bioetl.domain.filtering import InputFilterConfig
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

__all__ = [
    "_extract_uniprot_mapping_seed_ids",
    "_resolve_uniprot_mapping_base_url",
    "_resolve_uniprot_mapping_databases",
    "_resolve_uniprot_mapping_input_path",
]


def _resolve_uniprot_mapping_base_url(pipeline_config: PipelineYamlConfig) -> str:
    """Resolve UniProt ID Mapping base URL from config with safe default."""
    if pipeline_config.source.api and pipeline_config.source.api.base_url:
        return str(pipeline_config.source.api.base_url)
    return str(UNIPROT_API_BASE)


def _resolve_uniprot_mapping_input_path(
    pipeline_config: PipelineYamlConfig,
    filter_config: InputFilterConfig | None = None,
) -> str:
    """Resolve input CSV path for UniProt ID Mapping seed IDs."""
    if filter_config and filter_config.enabled and filter_config.source_path:
        return filter_config.source_path
    configured = getattr(pipeline_config.source, "input_path", None)
    return configured or "data/input/target.csv"


def _resolve_uniprot_mapping_databases(
    pipeline_config: PipelineYamlConfig,
) -> tuple[str, str]:
    """Resolve source/target database names for UniProt mapping API."""

    configured_from = None
    configured_to = None
    if pipeline_config.source.api:
        configured_from = getattr(pipeline_config.source.api, "from_db", None)
        configured_to = getattr(pipeline_config.source.api, "to_db", None)
    return resolve_uniprot_mapping_databases(
        configured_from_db=configured_from,
        configured_to_db=configured_to,
    )


def _extract_uniprot_mapping_seed_ids(
    filter_config: InputFilterConfig | None,
) -> list[str] | None:
    """Extract optional seed IDs from input filter config."""
    if (
        filter_config is not None
        and filter_config.enabled
        and filter_config.direct_filter_ids
    ):
        return list(filter_config.direct_filter_ids)
    return None
