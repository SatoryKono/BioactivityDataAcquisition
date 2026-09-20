"""Leftover quality/config/control_plane residuals not imported in three/four."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID

import pytest

from bioetl.domain.control_plane import ControlPlaneArtifactSurface
from bioetl.domain.control_plane.artifact_lifecycle import (
    ControlPlaneArtifactLifecycleDecision,
    ControlPlaneArtifactReplayImpact,
)
from bioetl.domain.types import RunID
from bioetl.infrastructure.config import pipeline_config_api as pipeline_api
from bioetl.infrastructure.control_plane._file_artifact_lifecycle_refs import (
    _append_effective_config_candidate,
    _append_lineage_candidates,
    resolve_replay_impact,
)
from bioetl.infrastructure.control_plane._file_lineage_queries import FileLineageQueriesMixin
from bioetl.infrastructure.control_plane._file_run_ledger_queries import FileRunLedgerQueriesMixin
from bioetl.infrastructure.control_plane.file_artifact_lifecycle_reasons import (
    _dedupe_reasons,
    _protected_by,
)
from bioetl.infrastructure.control_plane.file_artifact_lifecycle_types import _ProtectedRefs
from bioetl.infrastructure.control_plane.file_contract_registry_store import (
    FileContractRegistryStore,
    RegistryLoadError,
    create_contract_registry,
)
from bioetl.infrastructure.control_plane.file_effective_config_artifact_store import (
    FileEffectiveConfigArtifactStore,
)
from bioetl.infrastructure.control_plane.file_lineage_store import FileLineageStore
from bioetl.infrastructure.control_plane.file_workflow_execution_state_store import (
    FileWorkflowExecutionStateStore,
)
from bioetl.infrastructure.control_plane.file_workflow_ledger_store import FileWorkflowLedgerStore
from bioetl.infrastructure.control_plane.file_workflow_manifest_store import (
    FileWorkflowManifestStore,
)
from bioetl.infrastructure.schemas.pipeline_config import _serialize_schema_value
from bioetl.infrastructure.schemas.workflow_config import (
    _normalize_required_name,
    _normalize_required_names,
    validate_workflow_config_payload,
)

pytestmark = pytest.mark.unit


def _empty_protected() -> _ProtectedRefs:
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


class _LineageHost(FileLineageQueriesMixin):
    def __init__(self) -> None:
        self.base_path = Path(".")
        self.metrics = MagicMock()
        self._fragment = None
        self._ids: list[str] = []
        self._index_fragments: list[object] = []

    def _load_fragment(self, fragment_id: str):
        return self._fragment

    def _load_fragment_ids(self, index_path: Path, *, key: str) -> list[str]:
        return list(self._ids)

    def _semantic_fragment_index_path(self, fragment_id: str) -> Path:
        return Path(fragment_id)

    def _run_index_path(self, run_id: str) -> Path:
        return Path(run_id)

    def _manifest_index_path(self, manifest_id: str) -> Path:
        return Path(manifest_id)

    def _node_index_path(self, node_id: str) -> Path:
        return Path(node_id)

    def _load_from_index(self, index_path: Path, *, key: str):
        return list(self._index_fragments)


class _LedgerHost(FileRunLedgerQueriesMixin):
    def __init__(self, base_path: Path) -> None:
        self.base_path = base_path
        self.metrics = MagicMock()


class TestLifecycleReasonsAndRefs:
    def test_protected_by_all_surfaces(self, tmp_path: Path) -> None:
        path = tmp_path / "m.json"
        path.write_text("{}", encoding="utf-8")
        refs = _ProtectedRefs(
            manifest_ids=frozenset({"m1"}),
            run_ids=frozenset({"run-1"}),
            input_snapshot_ids=frozenset({"sha256:abc"}),
            effective_config_artifact_ids=frozenset({"cfg-1"}),
            lineage_fragment_ids=frozenset({"frag-1"}),
            evidence_floor_manifest_ids=frozenset({"m1"}),
            evidence_floor_run_ids=frozenset({"run-1"}),
            evidence_floor_input_snapshot_ids=frozenset({"sha256:abc"}),
            evidence_floor_effective_config_artifact_ids=frozenset({"cfg-1"}),
            evidence_floor_lineage_fragment_ids=frozenset({"frag-1"}),
        )
        manifest_reasons = _protected_by(
            surface=ControlPlaneArtifactSurface.RUN_MANIFEST,
            path=path,
            payload={"manifest_id": "m1", "run_id": "run-1"},
            protected_refs=refs,
        )
        assert "manifest:m1" in manifest_reasons
        config_reasons = _protected_by(
            surface=ControlPlaneArtifactSurface.EFFECTIVE_CONFIG,
            path=path,
            payload={"artifact_id": "cfg-1", "run_id": "run-1"},
            protected_refs=refs,
        )
        assert "effective_config:cfg-1" in config_reasons
        lineage_reasons = _protected_by(
            surface=ControlPlaneArtifactSurface.LINEAGE,
            path=path,
            payload={"fragment_id": "frag-1", "manifest_id": "m1", "run_id": "run-1"},
            protected_refs=refs,
        )
        assert any(reason.startswith("lineage:") for reason in lineage_reasons)
        checkpoint_reasons = _protected_by(
            surface=ControlPlaneArtifactSurface.CHECKPOINT,
            path=path,
            payload={
                "run_id": "run-1",
                "manifest_id": "m1",
                "effective_config_artifact_id": "cfg-1",
            },
            protected_refs=refs,
        )
        assert "run:run-1" in checkpoint_reasons
        bronze = tmp_path / "batch.jsonl"
        bronze.write_bytes(b"abc")
        empty_refs = _empty_protected()
        assert _protected_by(
            surface=ControlPlaneArtifactSurface.CACHED_BRONZE,
            path=bronze,
            payload={},
            protected_refs=empty_refs,
        ) == ()
        assert _dedupe_reasons(["a", "a", "b"]) == ("a", "b")
        assert resolve_replay_impact(
            surface=ControlPlaneArtifactSurface.RUN_MANIFEST,
            decision=ControlPlaneArtifactLifecycleDecision.RETAIN,
            protected_by=("evidence_floor:manifest:m1",),
        ) is ControlPlaneArtifactReplayImpact.STRICT_REPLAY_EVIDENCE_PROTECTED
        assert resolve_replay_impact(
            surface=ControlPlaneArtifactSurface.RUN_MANIFEST,
            decision=ControlPlaneArtifactLifecycleDecision.RETAIN,
            protected_by=("manifest:m1",),
        ) is ControlPlaneArtifactReplayImpact.RECOVERY_EVIDENCE_PROTECTED
        assert resolve_replay_impact(
            surface=ControlPlaneArtifactSurface.RUN_MANIFEST,
            decision=ControlPlaneArtifactLifecycleDecision.DELETE,
            protected_by=(),
        ) is ControlPlaneArtifactReplayImpact.UNPROTECTED_REPLAY_EVIDENCE_DELETE_CANDIDATE

    def test_manifest_candidate_helpers(self, tmp_path: Path) -> None:
        candidates: list[tuple[ControlPlaneArtifactSurface, Path]] = []
        manifest = SimpleNamespace(
            code_provenance=SimpleNamespace(effective_config_artifact_id="cfg-1"),
            manifest_id="m1",
        )
        _append_effective_config_candidate(candidates, tmp_path, manifest)
        assert candidates[-1][0] is ControlPlaneArtifactSurface.EFFECTIVE_CONFIG
        issues: list[object] = []
        _append_lineage_candidates(candidates, issues, tmp_path, manifest)
        assert issues


class TestControlPlaneStores:
    def test_workflow_manifest_miss_and_rollback(self, tmp_path: Path) -> None:
        store = FileWorkflowManifestStore(tmp_path)
        assert store.get("missing") is None
        assert store.get_by_run_id(RunID(UUID("00000000-0000-4000-8000-000000000001"))) is None
        assert store.list_all() == ()
        empty_index = tmp_path / "_by_run_id"
        empty_index.mkdir()
        (empty_index / "run.txt").write_text("  ", encoding="utf-8")
        assert store._load_manifest_id_for_run_id("run") is None
        stale = tmp_path / "m.json"
        stale.write_text("{}", encoding="utf-8")
        store._rollback_manifest_file(stale)
        assert not stale.exists()
        (tmp_path / "bad.json").write_text("[]", encoding="utf-8")
        with pytest.raises(ValueError, match="JSON object"):
            store._load_manifest("bad")

    def test_lineage_store_load_and_rollback(self, tmp_path: Path) -> None:
        store = FileLineageStore(tmp_path)
        assert store._load_fragment("missing") is None
        fragment_path = store._fragment_path("frag-1")
        fragment_path.parent.mkdir(parents=True)
        fragment_path.write_text("[]", encoding="utf-8")
        with pytest.raises(ValueError, match="JSON object"):
            store._load_fragment("frag-1")
        store._rollback_save(
            fragment_path=fragment_path,
            existing_fragment_payload=None,
            index_rollbacks=[],
        )
        assert not fragment_path.exists()
        host = _LineageHost()
        assert host.get_occurrence("x") is None
        host._ids = []
        assert host.get("missing") is None
        host._ids = ["a", "b"]
        with pytest.raises(ValueError, match="multiple stored"):
            host.get("semantic")
        host._ids = ["only"]
        host._fragment = None
        assert host.get("semantic") is None
        host._index_fragments = []
        assert host.list_by_run_id("run") == []

    def test_run_ledger_queries_miss(self, tmp_path: Path) -> None:
        host = _LedgerHost(tmp_path)
        assert host.list_entries("m1") == []
        assert host.list_entries_by_run_id(
            RunID(UUID("00000000-0000-4000-8000-000000000001"))
        ) == []
        assert host.list_entries_after("m1", None) == []

    def test_workflow_ledger_and_execution_miss(self, tmp_path: Path) -> None:
        ledger = FileWorkflowLedgerStore(tmp_path)
        assert ledger.list_entries("m1") == []
        assert ledger.list_entries_by_run_id(
            RunID(UUID("00000000-0000-4000-8000-000000000001"))
        ) == []
        state = FileWorkflowExecutionStateStore(tmp_path)
        assert state.get_by_run_id(
            RunID(UUID("00000000-0000-4000-8000-000000000001"))
        ) is None
        assert state.get_by_manifest_id("m1") is None
        assert state.get_latest("wf") is None
        (tmp_path / "_latest_by_workflow").mkdir()
        (tmp_path / "_latest_by_workflow" / "wf.txt").write_text("  ", encoding="utf-8")
        assert state.get_latest("wf") is None

    def test_effective_config_and_contract_registry(self, tmp_path: Path) -> None:
        store = FileEffectiveConfigArtifactStore(tmp_path)
        assert store.get("missing") is None
        assert store.get_by_run_id("run-1") is None
        assert store.get_occurrence_by_run_id("run-1") is None
        store.save(artifact_id="cfg-1", run_id="run-1", payload={"k": 1})
        store.save(artifact_id="cfg-1", run_id="run-1", payload={"k": 1})
        diff = store.diff_occurrences_by_run_id("run-1", "run-2")
        assert diff["left_artifact_present"] is True
        assert diff["right_artifact_present"] is False
        registry_store = FileContractRegistryStore(tmp_path / "missing.yaml")
        with pytest.raises(RegistryLoadError, match="Failed to read registry"):
            create_contract_registry(tmp_path / "missing.yaml")
        with pytest.raises(RegistryLoadError, match="Failed to read registry"):
            registry_store.load()
        with pytest.raises(RegistryLoadError, match="Failed to read registry"):
            FileContractRegistryStore(tmp_path / "also-missing.yaml").load()


class TestPipelineAndWorkflowConfig:
    def test_pipeline_config_api_guards(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        with pytest.raises(ValueError, match="provider>_<entity>"):
            pipeline_api.read_pipeline_config_payload("nounderscore")
        assert pipeline_api._get_unified_section({"pipeline": []}, "pipeline") is None
        assert pipeline_api._get_unified_section({"pipeline": {"x": 1}}, "pipeline") == {
            "x": 1
        }
        missing = tmp_path / "gone.yaml"
        assert pipeline_api._load_yaml_mapping(missing) is None
        not_mapping = tmp_path / "list.yaml"
        not_mapping.write_text("- a\n", encoding="utf-8")
        assert pipeline_api._load_yaml_mapping(not_mapping) is None
        pipelines = tmp_path / "pipelines"
        pipelines.mkdir()
        with pytest.raises(ValueError, match="Legacy pipeline config"):
            pipeline_api._assert_legacy_pipeline_config_surface_absent(tmp_path)
        pipeline_api._clear_pipeline_config_caches()
        mapped = pipeline_api.map_pipeline_config(SimpleNamespace())
        assert mapped is not None

    def test_schema_helpers(self) -> None:
        serialized = _serialize_schema_value({"a": ("x", {"b": 1})})
        assert serialized == {"a": ["x", {"b": 1}]}
        assert _serialize_schema_value("keep") == "keep"
        assert _normalize_required_name(" name ", "left_table") == "name"
        with pytest.raises(ValueError, match="cannot be empty"):
            _normalize_required_name("  ", "left_table")
        with pytest.raises(ValueError, match="cannot contain duplicates"):
            _normalize_required_names(["a", "a"], "left_columns")
        validated = validate_workflow_config_payload(
            {
                "workflow": {
                    "name": "wf",
                    "steps": [
                        {
                            "kind": "transform",
                            "step_id": "extract",
                            "transform_name": "passthrough",
                            "config": {},
                        }
                    ],
                }
            }
        )
        assert validated.workflow.name == "wf"
