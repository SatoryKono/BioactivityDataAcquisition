"""Canonical request assembly helpers for pipeline-runner creation seams."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, cast

from bioetl.composition.factories.pipeline.control_plane_artifacts import (
    ControlPlaneArtifacts,
    build_control_plane_artifacts,
)
from bioetl.domain.context import CachedBronzeContext
from bioetl.domain.filtering import InputFilterConfig
from bioetl.domain.ports import PipelineCreateRunnerRequest
from bioetl.domain.types import RunID
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

if TYPE_CHECKING:
    from bioetl.composition.observability import ObservabilityBundle
    from bioetl.domain.config import RuntimeConfig
    from bioetl.infrastructure.config import Settings

__all__ = [
    "build_pipeline_create_runner_request",
    "build_pipeline_create_runner_request_from_kwargs",
]


def build_pipeline_create_runner_request(
    *,
    run_id: RunID,
    runtime: object,
    started_at: datetime,
    settings: object,
    observability: object,
    control_plane: ControlPlaneArtifacts | None = None,
    manifest_id: str | None = None,
    execution_fingerprint: str | None = None,
    config_hash: str | None = None,
    resolved_config_hash: str | None = None,
    effective_config_hash: str | None = None,
    dq_contract_compatibility_hash: str | None = None,
    effective_config_artifact_id: str | None = None,
    replay_of_run_id: str | None = None,
    replay_of_manifest_id: str | None = None,
    input_snapshot_fingerprint: str | None = None,
    filter_config: InputFilterConfig | None = None,
    config: PipelineYamlConfig | None = None,
    cached_bronze: CachedBronzeContext | None = None,
) -> PipelineCreateRunnerRequest:
    """Build the canonical public runner request from explicit runtime inputs."""
    resolved_control_plane = control_plane or build_control_plane_artifacts(
        manifest_id=manifest_id,
        execution_fingerprint=execution_fingerprint,
        config_hash=config_hash,
        resolved_config_hash=resolved_config_hash,
        effective_config_hash=effective_config_hash,
        dq_contract_compatibility_hash=dq_contract_compatibility_hash,
        effective_config_artifact_id=effective_config_artifact_id,
        replay_of_run_id=replay_of_run_id,
        replay_of_manifest_id=replay_of_manifest_id,
        input_snapshot_fingerprint=input_snapshot_fingerprint,
    )
    return PipelineCreateRunnerRequest(
        run_id=run_id,
        runtime=cast("RuntimeConfig", runtime),
        started_at=started_at,
        settings=cast("Settings", settings),
        observability=cast("ObservabilityBundle", observability),
        control_plane=resolved_control_plane,
        filter_config=filter_config,
        config=config,
        cached_bronze=cached_bronze,
    )


def build_pipeline_create_runner_request_from_kwargs(
    **kwargs: object,
) -> PipelineCreateRunnerRequest:
    """Compat wrapper for keyword-based runner request assembly."""
    return build_pipeline_create_runner_request(
        run_id=cast("RunID", kwargs["run_id"]),
        runtime=kwargs["runtime"],
        started_at=cast("datetime", kwargs["started_at"]),
        settings=cast("Settings", kwargs["settings"]),
        observability=cast("ObservabilityBundle", kwargs["observability"]),
        control_plane=cast(
            "ControlPlaneArtifacts | None",
            kwargs.get("control_plane"),
        ),
        manifest_id=cast(str | None, kwargs.get("manifest_id")),
        execution_fingerprint=cast(str | None, kwargs.get("execution_fingerprint")),
        config_hash=cast(str | None, kwargs.get("config_hash")),
        resolved_config_hash=cast(str | None, kwargs.get("resolved_config_hash")),
        effective_config_hash=cast(str | None, kwargs.get("effective_config_hash")),
        dq_contract_compatibility_hash=cast(
            str | None,
            kwargs.get("dq_contract_compatibility_hash"),
        ),
        effective_config_artifact_id=cast(
            str | None,
            kwargs.get("effective_config_artifact_id"),
        ),
        replay_of_run_id=cast(str | None, kwargs.get("replay_of_run_id")),
        replay_of_manifest_id=cast(str | None, kwargs.get("replay_of_manifest_id")),
        input_snapshot_fingerprint=cast(
            str | None,
            kwargs.get("input_snapshot_fingerprint"),
        ),
        filter_config=cast("InputFilterConfig | None", kwargs.get("filter_config")),
        config=cast("PipelineYamlConfig | None", kwargs.get("config")),
        cached_bronze=cast(
            "CachedBronzeContext | None",
            kwargs.get("cached_bronze"),
        ),
    )
