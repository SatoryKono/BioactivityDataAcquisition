"""Select and verify the exact child inputs of a completed composite."""

from __future__ import annotations

import shutil
from pathlib import Path
from tempfile import mkdtemp

from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
from bioetl.composition.runtime_builders.config_access import get_settings
from bioetl.composition.control_plane_paths import control_plane_root
from bioetl.composition.services.versioning import get_code_revision_provenance
from bioetl.composition.snapshot_serialization import to_serializable_mapping
from bioetl.domain.composite import CompositeConfig
from bioetl.domain.control_plane import RunManifest
from bioetl.domain.control_plane.composite_replay import has_composite_replay_bindings
from bioetl.domain.types import RunID
from bioetl.infrastructure.config.settings_api import Settings
from bioetl.infrastructure.control_plane import FileRunManifestStore
from bioetl.infrastructure.control_plane.replay_object_verifier import (
    ReplayObjectVerifier,
    verify_file,
)


class CompositeReplayInputs:
    """A replay reads only the selected, hash-verified Bronze batches."""

    def __init__(
        self,
        parent: RunManifest,
        children: dict[str, RunManifest],
        verifier: ReplayObjectVerifier,
        output_root: Path,
    ) -> None:
        self.parent = parent
        self.children = children
        self.verifier = verifier
        self.output_root = output_root

    def prepare_options(
        self, pipeline_name: str, options: dict[str, object]
    ) -> dict[str, object]:
        child = self.children.get(pipeline_name)
        if child is None:
            raise ValueError(f"Composite replay child is missing: {pipeline_name}")
        if (
            not pipeline_name
            or any(c in pipeline_name for c in "/\\:")
            or pipeline_name in (".", "..")
        ):
            raise ValueError("Invalid composite replay pipeline path")
        checks = self.verifier.verify(child)
        if not checks or not all(
            checks.get(key) is True
            for key in (
                "effective_config_hash",
                "dependency_lock_hash",
                "input_snapshot_fingerprint",
            )
        ):
            raise ValueError(
                f"Composite replay child objects are unavailable: {pipeline_name}"
            )
        root = self.output_root / pipeline_name
        root.mkdir(parents=True, exist_ok=False)
        index = 0
        for source in child.source_refs:
            for snapshot in source.input_snapshots:
                path = self.verifier._snapshot_path(
                    snapshot.immutable_uri or "", source.provider, source.entity
                )
                if path is None or verify_file(path, snapshot.content_hash) is not True:
                    raise ValueError("Composite replay input changed after validation")
                target = root / f"batch_{index:06d}.jsonl.zst"
                shutil.copyfile(path, target)
                if verify_file(target, snapshot.content_hash) is not True:
                    raise ValueError("Composite replay input copy failed verification")
                index += 1
        if index == 0:
            raise ValueError("Composite replay child has no immutable inputs")
        return {
            **options,
            "exact_replay": True,
            "replay_of_manifest_id": child.manifest_id,
            "use_cached_bronze": True,
            "cached_bronze_path": str(root),
            "cached_bronze_date": None,
        }

    def validate_runtime_manifest(self, pipeline_name: str, run_id: RunID) -> None:
        """Reject effective child config drift before its runner executes."""
        store = FileRunManifestStore(
            base_path=self.verifier.config_root.parent / "run_manifest"
        )
        current = store.get_by_run_id(run_id)
        captured = self.children[pipeline_name]
        if current is None or current.pipeline_name != pipeline_name:
            raise ValueError("Composite replay runtime manifest is missing")
        if to_serializable_mapping(current.resolved_config) != to_serializable_mapping(
            captured.resolved_config
        ):
            raise ValueError("Composite replay child configuration changed")
        original_runtime = to_serializable_mapping(captured.runtime_config)
        replay_runtime = to_serializable_mapping(current.runtime_config)
        original_runtime.pop("exact_replay", None)
        replay_runtime.pop("exact_replay", None)
        if original_runtime != replay_runtime:
            raise ValueError("Composite replay child runtime options changed")


def load_composite_replay_inputs(
    config: CompositeConfig,
    manifest_id: str,
    settings: Settings,
) -> CompositeReplayInputs:
    """Reject incomplete lineage and changed code/config before any execution."""
    control = control_plane_root(settings, "run_manifest").parent
    store = FileRunManifestStore(base_path=control / "run_manifest")
    parent = store.get(manifest_id)
    if (
        parent is None
        or parent.pipeline_name != config.name
        or parent.provider != "composite"
    ):
        raise ValueError("Composite replay parent identity mismatch")
    if to_serializable_mapping(parent.resolved_config) != to_serializable_mapping(
        config
    ):
        raise ValueError(
            "Composite replay configuration differs from the captured parent"
        )
    provenance = get_code_revision_provenance()
    if (
        parent.code_provenance.git_commit != provenance.git_commit
        or parent.code_provenance.dependency_lock_hash
        != provenance.dependency_lock_hash
        or provenance.source_revision_state != "clean"
        or parent.code_provenance.source_revision_state != "clean"
    ):
        raise ValueError(
            "Composite replay requires the captured clean code and dependency lock"
        )
    bindings = parent.launch_context.get("child_replay_manifests")
    if not isinstance(bindings, dict) or not has_composite_replay_bindings(parent):
        raise ValueError("Composite replay parent has no completed child bindings")
    allowed = {
        config.seed.pipeline,
        *(item.pipeline for item in config.dependencies),
        *(item.pipeline for item in config.enrichers),
    }
    if config.seed.pipeline not in bindings or set(bindings) - allowed:
        raise ValueError(
            "Composite replay child bindings do not match configured stages"
        )
    children: dict[str, RunManifest] = {}
    for pipeline, identity in sorted(bindings.items()):
        if not isinstance(pipeline, str) or not isinstance(identity, str):
            raise ValueError("Invalid composite replay child binding")
        child = store.get(identity)
        if child is None or child.pipeline_name != pipeline:
            raise ValueError("Composite replay child identity mismatch")
        if child.code_provenance.git_commit != parent.code_provenance.git_commit:
            raise ValueError("Composite replay child code revision mismatch")
        if child.code_provenance.source_revision_state != "clean":
            raise ValueError("Composite replay child requires captured clean code")
        if (
            child.code_provenance.dependency_lock_hash
            != parent.code_provenance.dependency_lock_hash
        ):
            raise ValueError("Composite replay child dependency lock mismatch")
        children[pipeline] = child
    verifier = ReplayObjectVerifier(
        config_root=control / "effective_config",
        lock_root=control / "dependency_locks",
        bronze_root=Path(settings.bronze_path),
    )
    if (
        tuple(ref for child in children.values() for ref in child.source_refs)
        != parent.source_refs
    ):
        raise ValueError("Composite replay source lineage differs from child bindings")
    for manifest in (parent, *children.values()):
        checks = verifier.verify(manifest)
        if not all(
            checks.get(key) is True
            for key in (
                "effective_config_hash",
                "dependency_lock_hash",
                "input_snapshot_fingerprint",
            )
        ):
            raise ValueError("Composite replay captured objects failed verification")
    workspace_root = control / "composite_replay_inputs"
    workspace_root.mkdir(parents=True, exist_ok=True)
    workspace = Path(mkdtemp(prefix="replay-", dir=workspace_root))
    return CompositeReplayInputs(parent, children, verifier, workspace / "inputs")


def load_runtime_composite_replay(
    config: CompositeConfig, runtime: CompositeRuntimeConfig
) -> CompositeReplayInputs | None:
    """Load captured children and enforce the parent seed limit for replay."""
    if not runtime.replay_of_manifest_id:
        return None
    replay = load_composite_replay_inputs(
        config, runtime.replay_of_manifest_id, get_settings()
    )
    if replay.parent.launch_context.get("seed_limit") != runtime.seed_limit:
        raise ValueError("Composite replay must preserve the captured seed limit")
    return replay
