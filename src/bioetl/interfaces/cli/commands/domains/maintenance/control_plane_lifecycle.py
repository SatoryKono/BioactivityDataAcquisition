"""Control-plane lifecycle cleanup command."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Protocol, cast

import click

from bioetl.application.runtime_clock import current_utc_time
from bioetl.domain.control_plane import (
    ControlPlaneArtifactLifecyclePlan,
    ControlPlaneArtifactLifecyclePolicy,
)
from bioetl.interfaces.cli.formatters import echo_dry_run_prefix, echo_info

if TYPE_CHECKING:
    from bioetl.domain.control_plane import ControlPlaneArtifactLifecycleApplyResult

    class ControlPlaneArtifactLifecycleStoreProtocol(Protocol):
        def plan(
            self,
            policy: ControlPlaneArtifactLifecyclePolicy,
            *,
            dry_run: bool,
        ) -> ControlPlaneArtifactLifecyclePlan: ...

        def apply(
            self,
            plan: ControlPlaneArtifactLifecyclePlan,
        ) -> ControlPlaneArtifactLifecycleApplyResult: ...


__all__ = [
    "bootstrap_control_plane_lifecycle_store",
    "control_plane_lifecycle_command",
]


def bootstrap_control_plane_lifecycle_store() -> (
    ControlPlaneArtifactLifecycleStoreProtocol
):
    """Build the lifecycle store through the composition boundary."""
    from bioetl.composition.control_plane_service_access import (
        bootstrap_control_plane_lifecycle_store as _impl,
    )

    return cast("ControlPlaneArtifactLifecycleStoreProtocol", _impl())


@click.command("control-plane-lifecycle")
@click.option(
    "--retention-days",
    "-r",
    default=90,
    show_default=True,
    help="Minimum age of control-plane artifacts to delete.",
)
@click.option(
    "--apply",
    "apply_mode",
    is_flag=True,
    help="Delete selected candidates. Default is dry-run preview.",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json"]),
    default="text",
    show_default=True,
    help="Output format for the lifecycle plan.",
)
@click.option(
    "--protected-manifest-id",
    multiple=True,
    help="Manifest ID to retain regardless of age.",
)
@click.option(
    "--protected-run-id",
    multiple=True,
    help="Run ID to retain regardless of age.",
)
@click.option(
    "--protected-effective-config-artifact-id",
    multiple=True,
    help="Effective-config artifact ID to retain regardless of age.",
)
@click.option(
    "--protected-lineage-fragment-id",
    multiple=True,
    help="Lineage fragment ID to retain regardless of age.",
)
@click.option(
    "--protected-snapshot-id",
    multiple=True,
    help="Input snapshot ID to retain regardless of age.",
)
@click.option(
    "--allow-profile-floor-violation",
    is_flag=True,
    help=(
        "Allow deletion of stale artifacts required by replay_ready or "
        "forensic_grade evidence floors."
    ),
)
def control_plane_lifecycle_command(
    retention_days: int,
    apply_mode: bool,
    output_format: str,
    protected_manifest_id: tuple[str, ...],
    protected_run_id: tuple[str, ...],
    protected_effective_config_artifact_id: tuple[str, ...],
    protected_lineage_fragment_id: tuple[str, ...],
    protected_snapshot_id: tuple[str, ...],
    allow_profile_floor_violation: bool,
) -> None:
    """Plan or apply control-plane artifact lifecycle cleanup."""
    store = bootstrap_control_plane_lifecycle_store()
    dry_run = not apply_mode
    policy = ControlPlaneArtifactLifecyclePolicy(
        retention_days=retention_days,
        now=current_utc_time(),
        protected_manifest_ids=frozenset(protected_manifest_id),
        protected_run_ids=frozenset(protected_run_id),
        protected_effective_config_artifact_ids=frozenset(
            protected_effective_config_artifact_id
        ),
        protected_lineage_fragment_ids=frozenset(protected_lineage_fragment_id),
        protected_input_snapshot_ids=frozenset(protected_snapshot_id),
        allow_profile_floor_violation=allow_profile_floor_violation,
    )
    plan = store.plan(policy, dry_run=dry_run)
    result = store.apply(plan)

    if output_format == "json":
        click.echo(json.dumps(_plan_payload(plan, deleted_paths=result.deleted_paths)))
        return

    if dry_run:
        echo_dry_run_prefix(
            f"Control-plane lifecycle cleanup older than {retention_days} days"
        )
    echo_info(
        f"{'Would delete' if dry_run else 'Deleted'} {plan.delete_count} artifacts; "
        f"retained {plan.retain_count}."
    )
    for artifact in plan.artifacts:
        marker = "DELETE" if artifact.delete_selected else "RETAIN"
        protected_by = (
            f" protected_by={','.join(artifact.protected_by)}"
            if artifact.protected_by
            else ""
        )
        click.echo(
            f"{marker} {artifact.surface.value} {artifact.artifact_id} "
            f"{artifact.reason} replay_impact={artifact.replay_impact.value} "
            f"{artifact.path}{protected_by}"
        )


def _plan_payload(
    plan: ControlPlaneArtifactLifecyclePlan,
    *,
    deleted_paths: tuple[str, ...],
) -> dict[str, object]:
    return {
        "generated_at": plan.generated_at.isoformat(),
        "cutoff": plan.cutoff.isoformat(),
        "dry_run": plan.dry_run,
        "delete_count": plan.delete_count,
        "retain_count": plan.retain_count,
        "deleted_paths": list(deleted_paths),
        "artifacts": [
            {
                "surface": artifact.surface.value,
                "path": artifact.path,
                "artifact_id": artifact.artifact_id,
                "decision": artifact.decision.value,
                "reason": artifact.reason,
                "replay_impact": artifact.replay_impact.value,
                "created_at": (
                    artifact.created_at.isoformat() if artifact.created_at else None
                ),
                "protected_by": list(artifact.protected_by),
            }
            for artifact in plan.artifacts
        ],
    }
