"""Support helpers for composition runtime runner control-plane policy."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.composition.runtime_builders._runner_control_plane_artifact_policy import (
    requires_artifact_publication_closure as _requires_artifact_publication_closure,
    validate_artifact_recorder_attachment as _validate_artifact_recorder_attachment,
)
from bioetl.composition.runtime_builders._runner_control_plane_data_root_policy import (
    validate_strict_data_root_policy as _validate_strict_data_root_policy,
)
from bioetl.domain.control_plane.reproducibility_policy import (
    validate_required_persistence_profile as domain_validate_required_persistence_profile,
)

if TYPE_CHECKING:
    from bioetl.infrastructure.config.settings_api import Settings


def resolve_required_artifact_lineage_layers(
    *,
    yaml_config: object | None,
    skip_gold: bool = False,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Return active sink layers and layers missing metadata sidecars."""
    from bioetl.domain.control_plane.artifact_lineage_layers import (
        resolve_required_artifact_lineage_layers as resolve_layers,
    )

    return resolve_layers(yaml_config=yaml_config, skip_gold=skip_gold)


def validate_required_persistence_profile(
    *,
    manifest_enabled: bool,
    ledger_enabled: bool,
    required_profile: object,
    execution_label: str,
    exact_replay_execution_context_supported: bool = True,
    composite_resume_rich_replay_supported: bool = True,
    missing_artifact_lineage_layers: tuple[str, ...] = (),
) -> None:
    """Fail closed when static control-plane flags cannot satisfy required profile."""
    domain_validate_required_persistence_profile(
        manifest_enabled=manifest_enabled,
        ledger_enabled=ledger_enabled,
        required_profile=required_profile,
        execution_label=execution_label,
        exact_replay_execution_context_supported=(
            exact_replay_execution_context_supported
        ),
        composite_resume_rich_replay_supported=(
            composite_resume_rich_replay_supported
        ),
        missing_artifact_lineage_layers=missing_artifact_lineage_layers,
    )


def validate_strict_data_root_policy(
    *,
    settings: Settings,
    required_profile: object,
    exact_replay: bool = False,
) -> None:
    """Fail closed when strict reproducibility relies on fallback data roots."""
    _validate_strict_data_root_policy(
        settings=settings,
        required_profile=required_profile,
        exact_replay=exact_replay,
    )


requires_artifact_publication_closure = _requires_artifact_publication_closure
validate_artifact_recorder_attachment = _validate_artifact_recorder_attachment


def validate_manifest_persistence_requirements(
    *,
    yaml_config: object,
    skip_gold: bool,
    ledger_enabled: bool,
    required_profile: str,
    strict_exact_replay_supported: bool,
) -> None:
    """Validate manifest persistence requirements before manifest creation."""
    _active_layers, missing_artifact_lineage_layers = (
        resolve_required_artifact_lineage_layers(
            yaml_config=yaml_config,
            skip_gold=skip_gold,
        )
    )
    validate_required_persistence_profile(
        manifest_enabled=True,
        ledger_enabled=ledger_enabled,
        required_profile=required_profile,
        execution_label="Pipeline execution",
        exact_replay_execution_context_supported=strict_exact_replay_supported,
        composite_resume_rich_replay_supported=True,
        missing_artifact_lineage_layers=missing_artifact_lineage_layers,
    )
