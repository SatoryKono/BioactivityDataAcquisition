"""Canonical request assembly helpers for pipeline-runner creation seams."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from bioetl.composition.factories.pipeline.control_plane_artifacts import (
    ControlPlaneArtifacts,
    build_control_plane_artifacts,
)
from bioetl.domain.config import RuntimeConfig
from bioetl.domain.context import CachedBronzeContext
from bioetl.domain.filtering import InputFilterConfig
from bioetl.domain.ports import PipelineCreateRunnerRequest
from bioetl.domain.ports.config import SettingsPort
from bioetl.domain.ports.runtime.runner import ExecutionObservabilityPort
from bioetl.domain.types import RunID
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

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
    runtime: RuntimeConfig
    started_at: datetime
    settings: SettingsPort
    observability: ExecutionObservabilityPort


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


def _require_run_id(value: object) -> RunID:
    """Accept a UUID, a RunID NewType, or a UUID string (legacy callers)."""
    if isinstance(value, UUID):
        return RunID(value)
    if isinstance(value, str):
        try:
            return RunID(UUID(value))
        except ValueError as exc:
            raise TypeError(
                f"run_id must be UUID/RunID, got {type(value).__name__}"
            ) from exc
    raise TypeError(f"run_id must be UUID/RunID, got {type(value).__name__}")


def _require_runtime(value: object) -> RuntimeConfig:
    if isinstance(value, RuntimeConfig):
        return value
    raise TypeError(f"runtime must be RuntimeConfig, got {type(value).__name__}")


def _require_datetime(value: object) -> datetime:
    if isinstance(value, datetime):
        return value
    raise TypeError(f"started_at must be datetime, got {type(value).__name__}")


def _require_settings(value: object) -> SettingsPort:
    if isinstance(value, SettingsPort):
        return value
    raise TypeError(f"settings must be SettingsPort, got {type(value).__name__}")


def _require_observability(value: object) -> ExecutionObservabilityPort:
    if isinstance(value, ExecutionObservabilityPort):
        return value
    raise TypeError(
        f"observability must be ExecutionObservabilityPort, got {type(value).__name__}"
    )


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    raise TypeError(f"expected str | None, got {type(value).__name__}")


def _optional_str_tuple(
    value: object,
    *,
    size: int,
) -> tuple[str | None, ...]:
    if not isinstance(value, tuple) or len(value) != size:
        raise TypeError(f"expected tuple[{size} x str | None], got {type(value).__name__}")
    return tuple(_optional_str(item) for item in value)


def _optional_control_plane(value: object) -> ControlPlaneArtifacts | None:
    if value is None:
        return None
    if isinstance(value, ControlPlaneArtifacts):
        return value
    raise TypeError(
        f"control_plane must be ControlPlaneArtifacts | None, got {type(value).__name__}"
    )


def _optional_filter_config(value: object) -> InputFilterConfig | None:
    if value is None:
        return None
    if isinstance(value, InputFilterConfig):
        return value
    raise TypeError(
        f"filter_config must be InputFilterConfig | None, got {type(value).__name__}"
    )


def _optional_pipeline_config(value: object) -> PipelineYamlConfig | None:
    if value is None:
        return None
    if isinstance(value, PipelineYamlConfig):
        return value
    raise TypeError(
        f"config must be PipelineYamlConfig | None, got {type(value).__name__}"
    )


def _optional_cached_bronze(value: object) -> CachedBronzeContext | None:
    if value is None:
        return None
    if isinstance(value, CachedBronzeContext):
        return value
    raise TypeError(
        f"cached_bronze must be CachedBronzeContext | None, got {type(value).__name__}"
    )


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
        runtime=core.runtime,
        started_at=core.started_at,
        settings=core.settings,
        observability=core.observability,
        control_plane=resolved_control_plane,
        filter_config=options.filter_config,
        config=options.config,
        cached_bronze=options.cached_bronze,
    )


def build_pipeline_create_runner_request_from_kwargs(
    **kwargs: object,
) -> PipelineCreateRunnerRequest:
    """Compat wrapper for keyword-based runner request assembly."""
    config_hashes = kwargs.get(
        "config_hashes",
        (
            kwargs.get("config_hash"),
            kwargs.get("resolved_config_hash"),
            kwargs.get("effective_config_hash"),
        ),
    )
    replay_parentage = kwargs.get(
        "replay_parentage",
        (
            kwargs.get("replay_of_run_id"),
            kwargs.get("replay_of_manifest_id"),
        ),
    )
    hashed = _optional_str_tuple(config_hashes, size=3)
    replayed = _optional_str_tuple(replay_parentage, size=2)
    return build_pipeline_create_runner_request(
        core=PipelineCreateRunnerCore(
            run_id=_require_run_id(kwargs["run_id"]),
            runtime=_require_runtime(kwargs["runtime"]),
            started_at=_require_datetime(kwargs["started_at"]),
            settings=_require_settings(kwargs["settings"]),
            observability=_require_observability(kwargs["observability"]),
        ),
        extras=PipelineCreateRunnerExtras(
            control_plane=_optional_control_plane(kwargs.get("control_plane")),
            manifest_id=_optional_str(kwargs.get("manifest_id")),
            execution_fingerprint=_optional_str(kwargs.get("execution_fingerprint")),
            config_hashes=(hashed[0], hashed[1], hashed[2]),
            dq_contract_compatibility_hash=_optional_str(
                kwargs.get("dq_contract_compatibility_hash")
            ),
            effective_config_artifact_id=_optional_str(
                kwargs.get("effective_config_artifact_id")
            ),
            replay_parentage=(replayed[0], replayed[1]),
            input_snapshot_fingerprint=_optional_str(
                kwargs.get("input_snapshot_fingerprint")
            ),
            filter_config=_optional_filter_config(kwargs.get("filter_config")),
            config=_optional_pipeline_config(kwargs.get("config")),
            cached_bronze=_optional_cached_bronze(kwargs.get("cached_bronze")),
        ),
    )
