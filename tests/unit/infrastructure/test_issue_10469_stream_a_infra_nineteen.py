"""Stream A leftover INF: snapshots, schema edges, unknown surfaces."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from bioetl.domain.models.metadata import InputSnapshotRef, SourceMetadata
from bioetl.infrastructure.control_plane.file_artifact_lifecycle_payloads import (
    _artifact_id,
)
from bioetl.infrastructure.control_plane.file_artifact_lifecycle_reasons import (
    _protected_by,
)
from bioetl.infrastructure.control_plane.file_artifact_lifecycle_types import (
    _ProtectedRefs,
)
from bioetl.infrastructure.quality.architecture_debt_reduction import _layer_for_target
from bioetl.infrastructure.schemas.composite_config_base import EnricherSchema
from bioetl.infrastructure.schemas.pipeline_config_common_schemas import (
    AuthoritativeContentHashPolicyConfig,
    TransformConfig,
)
from bioetl.infrastructure.schemas.workflow_config import WorkflowConfigSchema
from bioetl.infrastructure.storage.bronze.metadata_snapshot_refs import (
    attach_live_snapshot_to_source_metadata,
    build_bronze_source_metadata_with_live_snapshot,
)
from bioetl.infrastructure.storage.delta_reader_helpers import (
    try_native_delta_row_count,
)
from bioetl.infrastructure.storage.silver.operations.validation_operations import (
    _resolve_payload_runtime_host,
)

pytestmark = pytest.mark.unit


def _empty_refs() -> _ProtectedRefs:
    return _ProtectedRefs(
        manifest_ids=frozenset(),
        run_ids=frozenset(),
        input_snapshot_ids=frozenset(),
        effective_config_artifact_ids=frozenset(),
        lineage_fragment_ids=frozenset(),
        evidence_floor_manifest_ids=frozenset(),
        evidence_floor_run_ids=frozenset(),
        evidence_floor_input_snapshot_ids=frozenset(),
        evidence_floor_effective_config_artifact_ids=frozenset(),
        evidence_floor_lineage_fragment_ids=frozenset(),
    )


def test_unknown_artifact_surface_defaults() -> None:
    path = Path("artifact.bin")
    unknown = object()
    with pytest.raises(AssertionError, match="unreachable"):
        _artifact_id(surface=unknown, path=path, payload={})  # type: ignore[arg-type]
    with pytest.raises(AssertionError, match="unreachable"):
        _protected_by(
            surface=unknown,  # type: ignore[arg-type]
            path=path,
            payload={},
            protected_refs=_empty_refs(),
        )


def test_snapshot_attach_existing_and_new() -> None:
    snap = InputSnapshotRef(
        snapshot_id="s1", content_hash="h1", immutable_uri="file://a"
    )
    source = SourceMetadata(type="api", input_snapshots=[])
    built = build_bronze_source_metadata_with_live_snapshot(
        source_metadata=source,
        snapshot=snap,
    )
    assert built is source
    same = attach_live_snapshot_to_source_metadata(
        source_metadata=source, snapshot=snap
    )
    assert same is source
    other = InputSnapshotRef(
        snapshot_id="s2", content_hash="h2", immutable_uri="file://b"
    )
    attached = attach_live_snapshot_to_source_metadata(
        source_metadata=source, snapshot=other
    )
    assert attached is source
    assert len(source.input_snapshots) >= 2


def test_semver_none_and_blank_field_ordering() -> None:
    assert TransformConfig.validate_semver(None) is None
    with pytest.raises(ValueError, match="non-empty"):
        AuthoritativeContentHashPolicyConfig.validate_field_ordering({" ": "asc"})


def test_enricher_empty_join_keys() -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        EnricherSchema.validate_join_keys_not_empty([])
    with pytest.raises(ValueError, match="empty strings"):
        EnricherSchema(pipeline="p", join_keys=[""])


def test_runtime_host_without_nested_host() -> None:
    host = SimpleNamespace(marker=True)
    assert _resolve_payload_runtime_host(host) is host  # type: ignore[arg-type]


def test_layer_for_empty_target() -> None:
    assert _layer_for_target(None) is None
    assert _layer_for_target("src/only.py") is None


def test_delta_count_reraises_keyboardinterrupt() -> None:
    class _Boom:
        def count(self) -> int:
            raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        try_native_delta_row_count(_Boom())  # type: ignore[arg-type]


def test_workflow_config_wraps_domain_valueerror(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _boom(self: WorkflowConfigSchema) -> object:
        raise ValueError("cycle")

    monkeypatch.setattr(WorkflowConfigSchema, "to_domain", _boom)
    with pytest.raises(ValueError, match="cycle"):
        WorkflowConfigSchema(name="wf", steps=[]).validate_domain_invariants()
