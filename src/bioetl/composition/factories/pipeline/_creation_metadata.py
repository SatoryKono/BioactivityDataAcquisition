"""Metadata and Silver validation helpers for pipeline creation."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, cast

import pyarrow as pa

from bioetl.application.services.lineage.metadata_coordinator import (
    MetadataCoordinator,
)
from bioetl.composition.factories.pipeline.construction_types import (
    _SchemaBuilder,
)
from bioetl.composition.factories.pipeline.run_context_factory import (
    RunContextFactory,
)
from bioetl.domain.config import DQConfig
from bioetl.domain.ports import SilverValidatorPort
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig
from bioetl.infrastructure.validation import ContractAwareSilverValidator

if TYPE_CHECKING:
    from bioetl.composition.contracts.factories import ServiceBundleDeps
    from bioetl.composition.factories.pipeline._creation_wiring import (
        _PipelineCreationInputs,
    )


def _build_metadata_coordinator(
    *,
    inputs: _PipelineCreationInputs,
    yaml_config: PipelineYamlConfig,
    deps: ServiceBundleDeps,
    extract_entity_type: Callable[[str], str | None],
) -> MetadataCoordinator:
    """Build the metadata coordinator from the canonical run context factory."""
    from bioetl.composition.services.versioning import (
        get_git_commit,
        get_pipeline_version,
    )

    request = inputs.request
    run_context_factory = RunContextFactory(
        pipeline_name=inputs.pipeline_name,
        provider=inputs.provider,
        entity_type_extractor=extract_entity_type,
        pipeline_version_getter=get_pipeline_version,
        git_commit_getter=get_git_commit,
        config_hash_getter=deps.compute_config_hash,
    )
    return MetadataCoordinator(
        run_context_factory.create(
            run_id=request.run_id,
            runtime=request.runtime,
            started_at=request.started_at,
            yaml_config=yaml_config,
            manifest_id=request.manifest_id,
            execution_fingerprint=request.execution_fingerprint,
            config_hashes=(
                request.config_hash,
                request.resolved_config_hash,
                request.effective_config_hash,
            ),
            dq_contract_compatibility_hash=request.dq_contract_compatibility_hash,
            effective_config_artifact_id=request.effective_config_artifact_id,
            exact_replay=bool(request.runtime.exact_replay),
            replay_of_run_id=request.replay_of_run_id,
            replay_of_manifest_id=request.replay_of_manifest_id,
            input_snapshot_fingerprint=request.input_snapshot_fingerprint,
        )
    )


def _create_silver_validator(
    pandera_silver_schema: object | None,
    dq_config: DQConfig | None = None,
) -> SilverValidatorPort | None:
    """Create a contract-aware Silver validator when a schema is configured."""
    if pandera_silver_schema is None:
        return None

    schema_builder = cast(_SchemaBuilder, pandera_silver_schema)
    typed_schema = cast("pa.DataFrameSchema | None", schema_builder.to_schema())
    return ContractAwareSilverValidator(typed_schema, dq_config=dq_config)
