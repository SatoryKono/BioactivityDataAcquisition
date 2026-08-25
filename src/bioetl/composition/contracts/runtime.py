"""Runtime-builder structural contracts (ADR-058)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    CachedBronzeContext = object
    PipelineRunContext = object
    RunSourceRef = object
    Settings = object


class ManifestSourceRefBuilder(Protocol):
    def build_run_source_refs(
        self,
        *,
        ctx: PipelineRunContext,
        cached_bronze: CachedBronzeContext | None,
        settings: Settings,
        provider: str,
        entity: str,
        required_persistence_profile: object,
    ) -> tuple[RunSourceRef, ...]: ...


class ManifestLaunchContextBuilder(Protocol):
    def build_launch_context_snapshot(
        self,
        ctx: PipelineRunContext,
        *,
        run_type_value: str,
        execution_context_value: str,
        configured_required_persistence_profile: str | None,
        required_persistence_profile: str,
        required_persistence_profile_opt_down: bool,
        strict_exact_replay_supported: bool,
        reproducibility_family: str,
        replay_family_contract: str,
        strict_replay_runtime_verdict: str,
        replay_support_scope: str,
        replay_support_reason: str,
    ) -> dict[str, object]: ...
