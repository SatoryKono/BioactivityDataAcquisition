"""Canonical request assembly helpers for pipeline-runner creation seams."""

from __future__ import annotations

from dataclasses import dataclass
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
    from bioetl.infrastructure.config.settings_api import Settings

__all__ = [
    "PipelineCreateRunnerCore",
    "PipelineCreateRunnerExtras",
    "build_pipeline_create_runner_request",
    "build_pipeline_create_runner_request_from_kwargs",
]


@dataclass(frozen=True, slots=True)
class PipelineCreateRunnerCore:
    """Required runtime handles for runner creation (S107 pack)."""

    run_id: RunID
    runtime: object
    started_at: datetime
    settings: object
    observability: object


@dataclass(frozen=True, slots=True)
class PipelineCreateRunnerExtras:
    """Optional control-plane / config inputs for runner creation (S107 pack)."""

    control_plane: ControlPlaneArtifacts | None = None
    manifest_id: str | None = None
    execution_fingerprint: str | None = None
    config_hashes: tuple[str | None, str | None, str | None] = (None, None, None)
    dq_contract_compatibility_hash: str | None = None
    effective_config_artifact_id: str | None = None
    replay_parentage: tuple[str | None, str | None] = (None, None)
    input_snapshot_fingerprint: str | None = None
    filter_config: InputFilterConfig | None = None
    config: PipelineYamlConfig | None = None
    cached_bronze: CachedBronzeContext | None = None


def build_pipeline_create_runner_request(
    *,
    core: PipelineCreateRunnerCore,
    extras: PipelineCreateRunnerExtras | None = None,
) -> PipelineCreateRunnerRequest:
    """Build the canonical public runner request from packed runtime inputs.

    ``core`` holds required runtime handles; ``extras`` packs optional
    control-plane identities and pipeline config seams (python:S107).
    """
    options = extras or PipelineCreateRunnerExtras()
    config_hash, resolved_config_hash, effective_config_hash = options.config_hashes
    replay_of_run_id, replay_of_manifest_id = options.replay_parentage
    resolved_control_plane = options.control_plane or build_control_plane_artifacts(
        manifest_id=options.manifest_id,
        execution_fingerprint=options.execution_fingerprint,
        config_hash=config_hash,
        resolved_config_hash=resolved_config_hash,
        effective_config_hash=effective_config_hash,
        dq_contract_compatibility_hash=options.dq_contract_compatibility_hash,
        effective_config_artifact_id=options.effective_config_artifact_id,
        replay_of_run_id=replay_of_run_id,
        replay_of_manifest_id=replay_of_manifest_id,
        input_snapshot_fingerprint=options.input_snapshot_fingerprint,
    )
    return PipelineCreateRunnerRequest(
        run_id=core.run_id,
        runtime=cast("RuntimeConfig", core.runtime),
        started_at=core.started_at,
        settings=cast("Settings", core.settings),
        observability=cast("ObservabilityBundle", core.observability),
        control_plane=resolved_control_plane,
        filter_config=options.filter_config,
        config=options.config,
        cached_bronze=options.cached_bronze,
    )


def build_pipeline_create_runner_request_from_kwargs(
    **kwargs: object,
) -> PipelineCreateRunnerRequest:
    """Compat wrapper for keyword-based runner request assembly."""
    return build_pipeline_create_runner_request(
        core=PipelineCreateRunnerCore(
            run_id=cast("RunID", kwargs["run_id"]),
            runtime=kwargs["runtime"],
            started_at=cast("datetime", kwargs["started_at"]),
            settings=cast("Settings", kwargs["settings"]),
            observability=cast("ObservabilityBundle", kwargs["observability"]),
        ),
        extras=PipelineCreateRunnerExtras(
            control_plane=cast(
                "ControlPlaneArtifacts | None",
                kwargs.get("control_plane"),
            ),
            manifest_id=cast(str | None, kwargs.get("manifest_id")),
            execution_fingerprint=cast(str | None, kwargs.get("execution_fingerprint")),
            config_hashes=cast(
                "tuple[str | None, str | None, str | None]",
                kwargs.get(
                    "config_hashes",
                    (
                        kwargs.get("config_hash"),
                        kwargs.get("resolved_config_hash"),
                        kwargs.get("effective_config_hash"),
                    ),
                ),
            ),
            dq_contract_compatibility_hash=cast(
                str | None,
                kwargs.get("dq_contract_compatibility_hash"),
            ),
            effective_config_artifact_id=cast(
                str | None,
                kwargs.get("effective_config_artifact_id"),
            ),
            replay_parentage=cast(
                "tuple[str | None, str | None]",
                kwargs.get(
                    "replay_parentage",
                    (
                        kwargs.get("replay_of_run_id"),
                        kwargs.get("replay_of_manifest_id"),
                    ),
                ),
            ),
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
        ),
    )
