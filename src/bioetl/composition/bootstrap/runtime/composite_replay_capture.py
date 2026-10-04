"""Bind completed composite provenance to the actual participating children."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from bioetl.application.services.execution.pipeline_runner_models import RunResult
from bioetl.domain.control_plane import ReplayCapability, RunSourceRef
from bioetl.infrastructure.config.settings_api import Settings
from bioetl.infrastructure.control_plane import FileRunManifestStore
from bioetl.infrastructure.control_plane.replay_object_verifier import (
    ReplayObjectVerifier,
)


def bind_composite_replay_children(
    manifest_id: str | None,
    children: list[RunResult],
    settings: Settings,
) -> None:
    """Persist complete, verified child bindings; a partial run cannot be promoted."""
    root = Path(settings.data_dir) / "output" / "control"
    store = FileRunManifestStore(base_path=root / "run_manifest")
    parent = store.get(manifest_id) if manifest_id else None
    if parent is None or parent.provider != "composite":
        raise ValueError("Composite replay parent manifest is missing")
    verifier = ReplayObjectVerifier(
        config_root=root / "effective_config",
        lock_root=root / "dependency_locks",
        bronze_root=Path(settings.bronze_path),
    )
    bindings: dict[str, str] = {}
    sources: list[RunSourceRef] = []
    for result in sorted(children, key=lambda item: item.pipeline_name):
        child = store.get(result.manifest_id) if result.manifest_id else None
        if (
            not result.is_success
            or child is None
            or str(child.run_id) != result.run_id
            or child.pipeline_name != result.pipeline_name
            or child.pipeline_name in bindings
            or child.code_provenance.git_commit != parent.code_provenance.git_commit
            or child.code_provenance.dependency_lock_hash
            != parent.code_provenance.dependency_lock_hash
        ):
            raise ValueError("Composite replay child identity or completion mismatch")
        checks = verifier.verify(child)
        if not all(
            checks.get(key) is True
            for key in (
                "effective_config_hash",
                "dependency_lock_hash",
                "input_snapshot_fingerprint",
            )
        ):
            raise ValueError(
                f"Composite replay child is not verified: {child.pipeline_name}"
            )
        bindings[child.pipeline_name] = child.manifest_id
        sources.extend(child.source_refs)
    if not bindings:
        raise ValueError("Composite replay requires completed source children")
    captured = replace(
        parent,
        source_refs=tuple(sources),
        launch_context={
            **parent.launch_context,
            "child_replay_manifests": bindings,
            "strict_exact_replay_supported": True,
            "exact_replay_support_boundary": "verified_composite_child_snapshot_bindings",
            "composite_replay_semantics": "verified_child_snapshots",
            "replay_boundary_reason": "complete_child_lineage_verified",
        },
        replay_capability=ReplayCapability.EXACT_REPLAY_SUPPORTED,
    )
    checks = verifier.verify(captured)
    if not all(
        checks.get(key) is True
        for key in (
            "effective_config_hash",
            "dependency_lock_hash",
            "input_snapshot_fingerprint",
        )
    ):
        raise ValueError(
            "Composite replay parent objects or complete lineage are not verified"
        )
    store.save(captured)
