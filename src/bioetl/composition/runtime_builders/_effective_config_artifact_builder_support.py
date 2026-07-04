"""Support helpers for effective-config artifact runtime builders."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.composition.runtime_builders._effective_config_graph_support import (
    build_effective_config_candidate_paths,
)
from bioetl.composition.runtime_builders._effective_config_source_refs_support import (
    build_effective_config_source_refs as _build_effective_config_source_refs,
    resolve_effective_config_entity,
)
from bioetl.composition.runtime_builders._effective_config_runtime_snapshot_support import (
    add_silver_filter_compatibility_defaults,
    build_execution_environment_snapshot,
    build_execution_settings_snapshot,
    current_silver_filter_compatibility_mode,
    current_silver_filter_compatibility_snapshot,
)
from bioetl.composition.runtime_builders._runtime_launch_context_fields import (
    build_runtime_launch_field_snapshot,
)
from bioetl.composition.runtime_builders._run_manifest_snapshot_support import (
    to_serializable_mapping as _to_serializable_mapping,
)
from bioetl.composition.runtime_builders.run_manifest_support import (
    resolve_run_context_values,
)
from bioetl.infrastructure.config.config_root import resolve_configs_root

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineRunContext
    from bioetl.infrastructure.config.settings_api import Settings
    from bioetl.domain.control_plane.effective_config_artifact import ConfigSourceRef


def build_runtime_overrides_snapshot(
    ctx: PipelineRunContext,
    settings: Settings,
) -> dict[str, object]:
    """Convert launch context options into runtime-override snapshot shape."""
    run_type_value, execution_context_value = resolve_run_context_values(ctx)
    cli_overrides = build_runtime_launch_field_snapshot(
        ctx,
        run_type_value=run_type_value,
    )
    cli_overrides.update(
        {
            "required_persistence_profile": getattr(
                ctx, "required_persistence_profile", None
            ),
            "input_filter": _to_serializable_mapping(
                getattr(ctx, "input_filter", None)
            ),
            "cached_bronze": _to_serializable_mapping(
                getattr(ctx, "cached_bronze", None)
            ),
            "vacuum": _to_serializable_mapping(getattr(ctx, "vacuum", None)),
            "replay_of_run_id": getattr(ctx, "replay_of_run_id", None),
            "replay_of_manifest_id": getattr(ctx, "replay_of_manifest_id", None),
            "silver_filter_compatibility_mode": (
                current_silver_filter_compatibility_mode()
            ),
        }
    )
    silver_filter_compatibility = current_silver_filter_compatibility_snapshot()
    runtime_fields = build_runtime_launch_field_snapshot(
        ctx,
        run_type_value=run_type_value,
        execution_context_value=execution_context_value,
    )
    runtime_fields.update(
        {
            "required_persistence_profile": getattr(
                ctx, "required_persistence_profile", None
            ),
            "vacuum": _to_serializable_mapping(getattr(ctx, "vacuum", None)),
            "input_filter": _to_serializable_mapping(
                getattr(ctx, "input_filter", None)
            ),
            "cached_bronze": _to_serializable_mapping(
                getattr(ctx, "cached_bronze", None)
            ),
            "settings_snapshot": build_execution_settings_snapshot(settings),
            "silver_filter_compatibility": silver_filter_compatibility,
            "silver_filter_compatibility_mode": silver_filter_compatibility["mode"],
        }
    )
    return {
        "cli": cli_overrides,
        "env": {
            "execution_environment": build_execution_environment_snapshot(settings)
        },
        "runtime": runtime_fields,
    }


def build_composite_runtime_overrides_snapshot(
    *,
    pipeline_name: str,
    runtime_config: object,
    required_persistence_profile: str,
    settings: Settings,
) -> dict[str, object]:
    """Convert composite runtime config into effective-config override shape."""
    runtime_payload = _to_serializable_mapping(runtime_config)
    runtime_payload.setdefault("pipeline_name", pipeline_name)
    runtime_payload.setdefault("execution_context", "composite")
    runtime_payload.setdefault(
        "required_persistence_profile", required_persistence_profile
    )
    runtime_payload.setdefault(
        "settings_snapshot", build_execution_settings_snapshot(settings)
    )
    add_silver_filter_compatibility_defaults(runtime_payload)
    return {
        "cli": dict(runtime_payload),
        "env": {
            "execution_environment": build_execution_environment_snapshot(settings)
        },
        "runtime": runtime_payload,
    }


def build_effective_config_source_refs(
    *,
    provider: str,
    entity: str,
    repo_root: Path | None = None,
) -> list[ConfigSourceRef]:
    """Build source references used to materialize effective config artifacts."""
    resolved_repo_root = repo_root or resolve_configs_root().parent
    return _build_effective_config_source_refs(
        provider=provider,
        entity=resolve_effective_config_entity(provider, entity),
        candidate_paths_factory=build_effective_config_candidate_paths,
        repo_root=resolved_repo_root,
    )
