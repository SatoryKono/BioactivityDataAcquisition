"""Stream A control-plane leftovers: archive, stores, lineage, ledger, comparison."""

from __future__ import annotations

import json
import os
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock
from uuid import UUID

import pytest

from bioetl.domain.control_plane import (
    ControlPlaneArtifactLifecycleDecision,
    ControlPlaneArtifactLifecyclePlan,
    ControlPlaneArtifactRef,
    ControlPlaneArtifactSurface,
    RunCodeProvenance,
    RunManifest,
)
from bioetl.domain.control_plane.workflow_ledger import WORKFLOW_STARTED_EVENT
from bioetl.domain.types import RunID, RunType
from bioetl.infrastructure.control_plane import file_archive_store as archive_module
from bioetl.infrastructure.control_plane._file_artifact_lifecycle_manifest_protections import (
    collect_manifest_protections,
    payload_contract_ref,
    payload_execution_context,
    supports_historical_replay_floor,
)
from bioetl.infrastructure.control_plane._file_artifact_lifecycle_refs import (
    _append_lineage_candidates,
)
from bioetl.infrastructure.control_plane._file_lineage_queries import (
    FileLineageQueriesMixin,
)
from bioetl.infrastructure.control_plane._file_run_ledger_helpers import (
    append_jsonl_payload,
    truncate_ledger_to_offset,
)
from bioetl.infrastructure.control_plane._file_run_ledger_queries import (
    FileRunLedgerQueriesMixin,
)
from bioetl.infrastructure.control_plane._raw_run_manifest_inspection import (
    ContractEvidenceConflictError,
    RawRunManifestInspectionMixin,
    _load_contract_evidence,
    _optional_evidence_text,
    persist_contract_evidence,
)
from bioetl.infrastructure.control_plane.artifact_byte_comparison import (
    _ArtifactComparisonState,
    _compare_semantic_sidecar_pair,
    _mapping_difference_paths,
    _record_semantic_raw_difference,
)
from bioetl.infrastructure.control_plane.file_archive_store import FileArchiveStore
from bioetl.infrastructure.control_plane.file_artifact_lifecycle_payloads import (
    _artifact_id,
    _effective_config_artifact_id,
    _input_snapshot_ids,
    _is_payload_stale,
)
from bioetl.infrastructure.control_plane.file_artifact_lifecycle_reasons import (
    _protected_by,
)
from bioetl.infrastructure.control_plane.file_artifact_lifecycle_types import (
    _ProtectedRefs,
)
from bioetl.infrastructure.control_plane.file_contract_registry_store import (
    FileContractRegistryStore,
    RegistryLoadError,
)
from bioetl.infrastructure.control_plane.file_effective_config_artifact_store import (
    FileEffectiveConfigArtifactStore,
    _build_semantic_payload,
    _normalize_semantic_payload_for_conflict_check,
)
from bioetl.infrastructure.control_plane.file_lineage_store import FileLineageStore
from bioetl.infrastructure.control_plane.file_provider_health_evidence import (
    _record_from_path,
)
from bioetl.infrastructure.control_plane.file_workflow_ledger_store import (
    FileWorkflowLedgerStore,
    _append_jsonl_payload,
)
from bioetl.infrastructure.control_plane.file_workflow_manifest_store import (
    FileWorkflowManifestStore,
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


def _archive_case(
    tmp_path: Path,
) -> tuple[FileArchiveStore, RunManifest, ControlPlaneArtifactLifecyclePlan]:
    data = tmp_path / "data"
    data.mkdir()
    manifest = RunManifest(
        manifest_id="manifest-archive",
        execution_fingerprint="fingerprint",
        schema_version="1.0",
        created_at=datetime(2026, 9, 15, tzinfo=UTC),
        run_id=RunID(UUID(int=14)),
        run_type=RunType.BACKFILL,
        pipeline_name="chembl_assay",
        provider="chembl",
        entity="assay",
        launch_context={"archive_policy": {"required": True, "policy_ref": "local-v1"}},
        code_provenance=RunCodeProvenance(),
    )
    (data / "manifest.json").write_text(
        json.dumps(manifest.to_dict()), encoding="utf-8"
    )
    (data / "ledger.jsonl").write_text("ledger evidence\n", encoding="utf-8")
    artifacts = tuple(
        ControlPlaneArtifactRef(
            surface=surface,
            path=str(data / name),
            artifact_id=manifest.manifest_id,
            decision=ControlPlaneArtifactLifecycleDecision.RETAIN,
            reason="selected",
        )
        for name, surface in (
            ("manifest.json", ControlPlaneArtifactSurface.RUN_MANIFEST),
            ("ledger.jsonl", ControlPlaneArtifactSurface.RUN_LEDGER),
        )
    )
    plan = ControlPlaneArtifactLifecyclePlan(
        generated_at=manifest.created_at,
        cutoff=manifest.created_at,
        dry_run=True,
        artifacts=artifacts,
    )
    return FileArchiveStore(data, tmp_path / "archive"), manifest, plan


class _InspectHost(RawRunManifestInspectionMixin):
    def __init__(self, base_path: Path) -> None:
        self.base_path = base_path


class _LineageHost(FileLineageQueriesMixin):
    def __init__(self) -> None:
        self.base_path = Path(".")
        self.metrics = MagicMock()

    def _load_fragment(self, fragment_id: str) -> object:
        raise ValueError("corrupt fragment")

    def _load_fragment_ids(self, index_path: Path, *, key: str) -> list[str]:
        del index_path, key
        return []

    def _semantic_fragment_index_path(self, fragment_id: str) -> Path:
        return Path(fragment_id)


class _LedgerHost(FileRunLedgerQueriesMixin):
    def __init__(self, base_path: Path) -> None:
        self.base_path = base_path
        self.metrics = MagicMock()


class TestFileArchiveStoreLeftovers:
    def test_inventory_and_entry_helpers_reject_invalid_shapes(
        self, tmp_path: Path
    ) -> None:
        sources = {"a.txt": tmp_path / "a.txt"}
        sources["a.txt"].write_text("ok", encoding="utf-8")
        assert (
            archive_module._inventory_error("not-list", sources)
            == "archive_index_invalid"
        )
        assert (
            archive_module._inventory_error(["not-dict"], sources)
            == "archive_index_invalid"
        )
        assert (
            archive_module._entry_error(
                "not-dict", sources=sources, seen=set(), pack=tmp_path
            )
            == "archive_index_invalid"
        )
        assert (
            archive_module._entry_error(
                {"path": "missing.txt"},
                sources=sources,
                seen=set(),
                pack=tmp_path,
            )
            == "archive_inventory_mismatch"
        )
        nested = tmp_path / "dir"
        nested.mkdir()
        with pytest.raises(ValueError, match="archive_path_outside_root"):
            archive_module._contained_file(tmp_path, "dir")

    def test_create_rejects_copy_checksum_mismatch(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        store, manifest, plan = _archive_case(tmp_path)
        original = archive_module._digest

        def flaky(path: Path) -> str:
            digest = original(path)
            if "files" in path.parts or "restored" in path.parts:
                return "0" * 64
            return digest

        monkeypatch.setattr(archive_module, "_digest", flaky)
        with pytest.raises(ValueError, match="archive_copy_checksum_mismatch"):
            store.create(manifest=manifest, plan=plan)

    def test_create_rejects_source_changed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        store, manifest, plan = _archive_case(tmp_path)
        original = archive_module._digest
        seen: dict[str, int] = {}

        def flaky(path: Path) -> str:
            key = str(path)
            seen[key] = seen.get(key, 0) + 1
            digest = original(path)
            if path.parent == store.data_root and seen[key] > 1:
                return "00" * 32
            return digest

        monkeypatch.setattr(archive_module, "_digest", flaky)
        with pytest.raises(ValueError, match="archive_source_changed"):
            store.create(manifest=manifest, plan=plan)

    def test_create_raises_when_verify_fails(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        store, manifest, plan = _archive_case(tmp_path)
        monkeypatch.setattr(
            FileArchiveStore,
            "verify",
            lambda self, **_kwargs: (False, "forced_verify_failure"),
        )
        with pytest.raises(ValueError, match="forced_verify_failure"):
            store.create(manifest=manifest, plan=plan)


class TestManifestProtectionsAndInspection:
    def test_collect_skips_index_dirs_and_empty_payloads(self, tmp_path: Path) -> None:
        base = tmp_path / "cp"
        manifest_root = base / "run_manifest"
        indexed = manifest_root / "_by_run_id"
        indexed.mkdir(parents=True)
        (indexed / "skip.json").write_text('{"manifest_id": "idx"}', encoding="utf-8")
        (manifest_root / "empty.json").write_text("{}", encoding="utf-8")
        (manifest_root / "live.json").write_text(
            json.dumps(
                {
                    "manifest_id": "live",
                    "created_at": "2026-06-01T00:00:00+00:00",
                    "run_id": "r-live",
                }
            ),
            encoding="utf-8",
        )
        (manifest_root / "stale.json").write_text(
            json.dumps(
                {
                    "manifest_id": "stale",
                    "created_at": "2020-01-01T00:00:00+00:00",
                    "required_persistence_profile": "replay_ready",
                    "run_id": "r-stale",
                }
            ),
            encoding="utf-8",
        )
        refs = SimpleNamespace(
            manifest_ids=set(),
            evidence_floor_manifest_ids=set(),
            run_ids=set(),
            evidence_floor_run_ids=set(),
            effective_config_artifact_ids=set(),
            evidence_floor_effective_config_artifact_ids=set(),
            input_snapshot_ids=set(),
            evidence_floor_input_snapshot_ids=set(),
        )
        collect_manifest_protections(
            base_path=base,
            cutoff=datetime(2026, 1, 1, tzinfo=UTC),
            refs=refs,
            allow_profile_floor_violation=False,
        )
        assert "live" in refs.manifest_ids
        assert "stale" in refs.evidence_floor_manifest_ids
        assert "idx" not in refs.manifest_ids

    def test_historical_replay_floor_valueerror_and_contract_ref(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from bioetl.infrastructure.control_plane import (
            _file_artifact_lifecycle_manifest_protections as protections,
        )

        monkeypatch.setattr(
            protections,
            "resolve_reproducibility_family_profile",
            lambda **_kwargs: (_ for _ in ()).throw(ValueError("unknown family")),
        )
        assert (
            supports_historical_replay_floor(
                {"provider": "chembl", "entity": "activity"}
            )
            is False
        )
        assert payload_contract_ref({"code_provenance": "bad"}) is None
        assert payload_execution_context({"provider": "composite"}) == "composite"

    def test_raw_manifest_unicode_and_contract_evidence(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        host = _InspectHost(tmp_path)
        broken = tmp_path / "bad.json"
        broken.write_bytes(b"\xff\xfe")
        inspection = host.inspect_raw_manifest("bad")
        assert inspection.parse_ok is False
        assert inspection.schema_errors == ("manifest_read_error",)

        sidecar = tmp_path / "m1.contract-evidence.json"
        sidecar.write_text("{not-json", encoding="utf-8")
        assert _load_contract_evidence(tmp_path, "m1") is None
        assert _optional_evidence_text({"k": "  "}, "k") is None
        assert _optional_evidence_text(None, "k") is None

        existing = tmp_path / "m2.contract-evidence.json"
        existing.write_text("payload", encoding="utf-8")
        original = Path.read_text

        def wrapped(self: Path, *args: object, **kwargs: object) -> str:
            if self.name == existing.name:
                raise UnicodeError("cannot compare")
            return original(self, *args, **kwargs)  # type: ignore[arg-type]

        monkeypatch.setattr(Path, "read_text", wrapped)
        with pytest.raises(ContractEvidenceConflictError, match="cannot be compared"):
            persist_contract_evidence(
                tmp_path, "m2", {"schema_version": "contract_evidence_v1"}
            )


class TestArtifactComparisonAndPayloads:
    def test_mapping_and_semantic_raw_difference_branches(self, tmp_path: Path) -> None:
        missing = _mapping_difference_paths({"a": 1}, {"b": 2}, prefix="")
        assert "a" in missing and "b" in missing
        state = _ArtifactComparisonState()
        _record_semantic_raw_difference(
            state,
            label="pair",
            raw_difference_fields=("payload.value",),
            raw_byte_equivalent=False,
        )
        assert state.raw_byte_only_artifacts == ["pair"]
        left = tmp_path / "left.json"
        right = tmp_path / "right.json"
        left.write_text('{"a": 1}', encoding="utf-8")
        right.write_text('{"a":1}', encoding="utf-8")
        sidecar_state = _ArtifactComparisonState()
        _compare_semantic_sidecar_pair(
            sidecar_state,
            left=("path", left),
            right=("path", right),
            label="json-pair",
            raw_byte_equivalent=False,
        )
        assert "json-pair" in sidecar_state.raw_byte_only_artifacts

    def test_payload_helpers_oserror_bronze_and_default_surface(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        payload_file = tmp_path / "row.json"
        payload_file.write_text("{}", encoding="utf-8")
        cutoff = datetime(2026, 1, 1, tzinfo=UTC)

        def boom(_self: Path) -> os.stat_result:
            raise OSError("stat failed")

        monkeypatch.setattr(Path, "stat", boom)
        assert _is_payload_stale(payload_file, {}, cutoff) is False
        bronze = tmp_path / "cached.bin"
        bronze.write_bytes(b"abc")
        digest = _artifact_id(
            surface=ControlPlaneArtifactSurface.CACHED_BRONZE,
            path=bronze,
            payload={},
        )
        assert digest.startswith("sha256:")
        assert (
            _artifact_id(
                surface=ControlPlaneArtifactSurface.CHECKPOINT,
                path=payload_file,
                payload={},
            )
            == payload_file.stem
        )
        assert _effective_config_artifact_id({"code_provenance": "bad"}) is None
        assert _input_snapshot_ids({"source_refs": "nope"}) == ()


class TestLineageLedgerManifestStores:
    def test_lineage_rollback_restore_and_stored_id_mismatch(
        self, tmp_path: Path
    ) -> None:
        store = FileLineageStore(tmp_path)
        fragment_path = store._fragment_path("frag-1")
        fragment_path.parent.mkdir(parents=True)
        index_dir = tmp_path / "index_dir"
        index_dir.mkdir()
        store._rollback_save(
            fragment_path=fragment_path,
            existing_fragment_payload='{"fragment_id": "frag-1"}',
            index_rollbacks=[(index_dir, 0)],
        )
        assert (
            json.loads(fragment_path.read_text(encoding="utf-8"))["fragment_id"]
            == "frag-1"
        )
        fragment_path.write_text(
            json.dumps(
                {
                    "fragment_id": "frag-1",
                    "nodes": [],
                    "edges": [],
                    "stored_fragment_id": "other-id",
                }
            ),
            encoding="utf-8",
        )
        assert store._load_fragment("frag-1") is None
        host = _LineageHost()
        with pytest.raises(ValueError, match="corrupt fragment"):
            host.get_occurrence("x")

    def test_workflow_ledger_empty_write_blank_lines_and_failed_read(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        target = tmp_path / "ledger.jsonl"
        monkeypatch.setattr(os, "write", lambda *_args: 0)
        with pytest.raises(OSError, match="empty write"):
            _append_jsonl_payload(target, b"abc\n")

        writes = {"n": 0}

        def partial_write(_fd: int, payload: bytes) -> int:
            writes["n"] += 1
            if writes["n"] == 1:
                return 1
            raise OSError("write failed")

        monkeypatch.setattr(os, "write", partial_write)
        monkeypatch.setattr(
            os, "ftruncate", lambda *_args: (_ for _ in ()).throw(OSError("trunc"))
        )
        with pytest.raises(OSError, match="write failed"):
            _append_jsonl_payload(target, b"abcdef\n")

        store = FileWorkflowLedgerStore(tmp_path)
        run_id = RunID(UUID("00000000-0000-4000-8000-000000000011"))
        index_dir = tmp_path / "_by_run_id"
        index_dir.mkdir()
        (index_dir / f"{run_id}.txt").write_text("m-bad", encoding="utf-8")
        (tmp_path / "m-bad.jsonl").write_text("[]\n", encoding="utf-8")
        with pytest.raises(ValueError, match="JSON object"):
            store.list_entries_by_run_id(run_id)
        (tmp_path / "m-blank.jsonl").write_text(
            "\n\n"
            + json.dumps(
                {
                    "entry_id": "e1",
                    "manifest_id": "m-blank",
                    "workflow_run_id": str(run_id),
                    "event_type": WORKFLOW_STARTED_EVENT,
                    "occurred_at": "2026-01-01T00:00:00+00:00",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        entries = store._load_entries("m-blank")
        assert len(entries) == 1

    def test_workflow_manifest_get_and_list_failures(self, tmp_path: Path) -> None:
        store = FileWorkflowManifestStore(tmp_path)
        (tmp_path / "bad.json").write_text("[]", encoding="utf-8")
        with pytest.raises(ValueError, match="JSON object"):
            store.get("bad")
        with pytest.raises(ValueError, match="JSON object"):
            store.list_all()

    def test_run_ledger_queries_miss_and_error_paths(self, tmp_path: Path) -> None:
        host = _LedgerHost(tmp_path)
        run_id = RunID(UUID("00000000-0000-4000-8000-000000000021"))
        index_dir = tmp_path / "_by_run_id"
        index_dir.mkdir()
        (index_dir / f"{run_id}.txt").write_text("m1\n", encoding="utf-8")
        assert host.list_entries_by_run_id(run_id) == []

        def raise_value(_manifest_id: str) -> list[object]:
            raise ValueError("bad watermark")

        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.setattr(host, "_load_entries", raise_value)
        try:
            with pytest.raises(ValueError, match="bad watermark"):
                host.list_entries_after("m1", None)
        finally:
            monkeypatch.undo()

        def raise_type(_manifest_id: str) -> list[object]:
            raise TypeError("bad type")

        monkeypatch.setattr(host, "_load_entries", raise_type)
        try:
            with pytest.raises(Exception, match="list_entries_after"):
                host.list_entries_after("m1", None)
        finally:
            monkeypatch.undo()

    def test_run_ledger_helpers_truncate_and_empty_write(self, tmp_path: Path) -> None:
        missing = tmp_path / "gone.jsonl"
        truncate_ledger_to_offset(
            missing,
            offset=0,
            flush_file_descriptor=lambda _fd: None,
        )
        os_module = SimpleNamespace(
            O_RDWR=os.O_RDWR,
            open=lambda *_a, **_k: 7,
            fstat=lambda _fd: SimpleNamespace(st_size=3),
            write=lambda *_a, **_k: 0,
            ftruncate=lambda *_a, **_k: (_ for _ in ()).throw(OSError("trunc")),
            close=lambda _fd: None,
        )
        with pytest.raises(OSError, match="empty write"):
            append_jsonl_payload(
                tmp_path / "out.jsonl",
                b"abc\n",
                open_flags=os.O_APPEND | os.O_CREAT | os.O_WRONLY,
                os_module=os_module,  # type: ignore[arg-type]
                flush_file_descriptor=lambda _fd: None,
            )


class TestContractRegistryHealthConfigAndRefs:
    def test_contract_registry_save_validate_and_read_errors(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        store = FileContractRegistryStore(tmp_path / "reg.yaml")
        registry = SimpleNamespace(to_dict=lambda: {"entries": {}})
        monkeypatch.setattr(
            "bioetl.infrastructure.control_plane.file_contract_registry_store.atomic_write_text",
            lambda *_a, **_k: (_ for _ in ()).throw(OSError("disk")),
        )
        with pytest.raises(RegistryLoadError, match="Failed to save"):
            store.save(registry)  # type: ignore[arg-type]
        source = tmp_path / "src.yaml"
        source.write_text("ok", encoding="utf-8")
        entry = SimpleNamespace(
            source_path=str(source), published_artifacts=["missing.art"]
        )
        result = store.validate_filesystem_consistency(
            SimpleNamespace(entries={"c.e": entry})  # type: ignore[arg-type]
        )
        assert result.valid is False
        monkeypatch.setattr(
            "bioetl.infrastructure.control_plane.file_contract_registry_store.load_contract_registry_payload",
            lambda _path: (_ for _ in ()).throw(OSError("io")),
        )
        with pytest.raises(RegistryLoadError, match="Failed to read"):
            store._read_registry_data(tmp_path / "reg.yaml")
        monkeypatch.setattr(
            "bioetl.infrastructure.control_plane.file_contract_registry_store.load_contract_registry_payload",
            lambda _path: (_ for _ in ()).throw(ValueError("bad yaml")),
        )
        with pytest.raises(RegistryLoadError, match="bad yaml"):
            store._read_registry_data(tmp_path / "reg.yaml")

    def test_provider_health_record_guards(self, tmp_path: Path) -> None:
        directory = tmp_path / "dir"
        directory.mkdir()
        assert _record_from_path(directory) is None
        payload = tmp_path / "obs.json"
        payload.write_text(
            json.dumps(
                {
                    "provider": "chembl",
                    "status": 1,
                    "observed_at": "2026-01-01T00:00:00+00:00",
                    "endpoint": 12,
                    "reason": 9,
                }
            ),
            encoding="utf-8",
        )
        record = _record_from_path(payload)
        assert record is not None
        assert record.endpoint == ""
        assert record.reason is None
        payload.write_text(
            json.dumps(
                {
                    "provider": "chembl",
                    "status": 1,
                    "observed_at": 1,
                    "endpoint": "/",
                }
            ),
            encoding="utf-8",
        )
        assert _record_from_path(payload) is None

    def test_effective_config_empty_index_and_semantic_normalize(
        self, tmp_path: Path
    ) -> None:
        store = FileEffectiveConfigArtifactStore(tmp_path)
        index_dir = tmp_path / "_by_run_id"
        index_dir.mkdir()
        (index_dir / "run-1.txt").write_text("   ", encoding="utf-8")
        assert store.get_by_run_id("run-1") is None
        semantic = _build_semantic_payload(
            artifact_id="cfg-1",
            payload={"semantic_artifact": {"schema_version": "v2", "body": 1}},
        )
        assert semantic["schema_version"] == "v2"
        normalized = _normalize_semantic_payload_for_conflict_check(
            {
                "semantic_artifact": {
                    "source_refs": ["uri", {"raw_source_hash": "x", "uri": "y"}],
                }
            }
        )
        refs = normalized["semantic_artifact"]["source_refs"]  # type: ignore[index]
        assert refs[0] == "uri"
        assert refs[1] == {"uri": "y"}

    def test_lineage_index_corrupt_and_cached_bronze_reasons(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from bioetl.infrastructure.control_plane import (
            _file_artifact_lifecycle_refs as refs_mod,
        )
        from bioetl.infrastructure.control_plane._file_lineage_index import (
            stable_key_filename,
        )

        index_dir = tmp_path / "lineage" / "_by_manifest_id"
        index_dir.mkdir(parents=True)
        (index_dir / f"{stable_key_filename('m1')}.jsonl").write_text(
            "x\n", encoding="utf-8"
        )
        monkeypatch.setattr(
            refs_mod,
            "load_fragment_ids",
            lambda *_a, **_k: (_ for _ in ()).throw(ValueError("corrupt")),
        )
        candidates: list[tuple[ControlPlaneArtifactSurface, Path]] = []
        issues: list[Any] = []
        _append_lineage_candidates(
            candidates,
            issues,
            tmp_path,
            SimpleNamespace(manifest_id="m1"),  # type: ignore[arg-type]
        )
        assert issues
        assert issues[0].code.value == "lineage_index_corrupt"
        bronze = tmp_path / "cached.bin"
        bronze.write_bytes(b"abc")
        digest = _artifact_id(
            surface=ControlPlaneArtifactSurface.CACHED_BRONZE,
            path=bronze,
            payload={},
        )
        refs = replace(
            _empty_protected(),
            input_snapshot_ids=frozenset({digest}),
            evidence_floor_input_snapshot_ids=frozenset({digest}),
        )
        reasons = _protected_by(
            surface=ControlPlaneArtifactSurface.CACHED_BRONZE,
            path=bronze,
            payload={},
            protected_refs=refs,
        )
        assert any(item.startswith("snapshot:") for item in reasons)
        ledger = tmp_path / "_by_run_id" / "run-1.jsonl"
        ledger.parent.mkdir()
        ledger.write_text("{}\n", encoding="utf-8")
        ledger_refs = replace(
            _empty_protected(),
            run_ids=frozenset({"run-1"}),
            evidence_floor_run_ids=frozenset({"run-1"}),
        )
        indexed = _protected_by(
            surface=ControlPlaneArtifactSurface.RUN_LEDGER,
            path=ledger,
            payload={},
            protected_refs=ledger_refs,
        )
        assert "run:run-1" in indexed
        assert "evidence_floor:run:run-1" in indexed
