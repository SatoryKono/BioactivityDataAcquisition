"""Stream A infrastructure residuals for #10469 / #10517 (control-plane, quality, schemas)."""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pandas as pd
import pytest
import yaml

from bioetl.domain.control_plane import (
    ControlPlaneArtifactLifecycleDecision,
    ControlPlaneArtifactLifecyclePlan,
    ControlPlaneArtifactRef,
    ControlPlaneArtifactResolutionIssue,
    ControlPlaneArtifactResolutionIssueCode,
    ControlPlaneArtifactSurface,
    RunCodeProvenance,
    RunManifest,
)
from bioetl.domain.types import RunID, RunType
from bioetl.infrastructure.config.chembl_policy_registry_loader import (
    ChemblPolicyRegistryLoader,
    _require_mapping,
    _require_sequence,
)
from bioetl.infrastructure.config.pipeline_normalizers import (
    _has_business_group,
    _is_empty_string_collection,
    _validate_contract_hash_policy_shims,
    _validate_schema_hash_policy_shims,
    apply_pipeline_schema_normalization,
)
from bioetl.infrastructure.control_plane import FileArtifactByteComparisonAdapter
from bioetl.infrastructure.control_plane import file_archive_store as archive_module
from bioetl.infrastructure.control_plane._raw_run_manifest_nested_validation import (
    raw_nested_schema_errors,
)
from bioetl.infrastructure.control_plane._run_manifest_scope_index import (
    LatestScopeIndexCatalog,
    LatestScopeIndexRecord,
    latest_scope_catalog_path,
    latest_scope_index_path,
    load_latest_scope_catalog,
    load_latest_scope_index,
    read_optional_text,
    restore_optional_text,
    write_latest_scope_catalog,
    write_latest_scope_index,
)
from bioetl.infrastructure.control_plane.file_archive_store import FileArchiveStore
from bioetl.infrastructure.control_plane.file_provider_health_evidence import (
    FileProviderHealthEvidenceStore,
    ProviderHealthEvidenceRecord,
)
from bioetl.infrastructure.control_plane.file_workflow_transform_artifact_store import (
    FileWorkflowTransformArtifactStore,
    _attr_tuple,
    _csv_value,
    _jsonable,
    _required_attr,
)
from bioetl.infrastructure.observability import observability_backend_process as backend
from bioetl.infrastructure.quality import architecture_debt_reduction as debt
from bioetl.infrastructure.quality import exemptions_registry_targets as targets
from bioetl.infrastructure.schemas.pipeline_config_common_schemas import (
    AuthoritativeContentHashPolicyConfig,
    AuthoritativeContentHashPolicyContractConfig,
    ScdConfigYamlConfig,
    SilverFiltersConfig,
    SinkLayerConfig,
    TransformConfig,
)
from bioetl.infrastructure.schemas.pipeline_contract_policy import (
    PipelineContractPolicy,
)
from bioetl.infrastructure.validation.pandera_validator import (
    BasePanderaValidator,
    NoOpValidator,
    PanderaGoldValidator,
    PanderaSilverValidator,
)

pytestmark = pytest.mark.unit


def _policy(**overrides: object) -> PipelineContractPolicy:
    payload: dict[str, object] = {
        "primary_key": ["id"],
        "merge_keys": ["id"],
        "contract_ref": "chembl.activity",
        "active_version": "v1",
        "rollout": {
            "mode": "single",
            "read_order": ["v1"],
            "write_versions": ["v1"],
        },
    }
    payload.update(overrides)
    return PipelineContractPolicy.model_validate(payload)


def test_artifact_comparison_overflow_yaml_dirs_and_semantic_mismatch(
    tmp_path: Path,
) -> None:
    extra = tmp_path / "extra.bin"
    extra.write_bytes(b"x")
    directory = tmp_path / "dir"
    directory.mkdir()
    left_yaml = tmp_path / "left.yaml"
    right_yaml = tmp_path / "right.yaml"
    left_yaml.write_text("rows:\n  - {id: 1}\n", encoding="utf-8")
    right_yaml.write_text("rows:\n  - {id: 2}\n", encoding="utf-8")
    left_txt = tmp_path / "left.txt"
    right_txt = tmp_path / "right.txt"
    left_txt.write_text("a", encoding="utf-8")
    right_txt.write_text("b", encoding="utf-8")
    left_json = tmp_path / "same.json"
    right_json = tmp_path / "same-ws.json"
    left_json.write_text('{"rows":[1],"run_id":"a"}', encoding="utf-8")
    right_json.write_text('{\n  "rows": [1],\n  "run_id": "b"\n}\n', encoding="utf-8")

    adapter = FileArtifactByteComparisonAdapter()
    overflow = adapter.compare_artifacts(
        [{"artifact_path": str(extra), "path": str(extra)}],
        [],
    )
    assert overflow["available"] is False
    assert overflow["missing_artifacts"]

    dirs = adapter.compare_artifacts(
        [{"artifact_path": str(directory)}],
        [{"artifact_path": str(directory)}],
    )
    assert dirs["equivalent"] is True

    yaml_mismatch = adapter.compare_artifacts(
        [{"metadata_path": str(left_yaml)}],
        [{"metadata_path": str(right_yaml)}],
    )
    assert yaml_mismatch["semantic_equivalent"] is False
    assert yaml_mismatch["semantic_difference_fields"]

    txt_mismatch = adapter.compare_artifacts(
        [{"metadata_path": str(left_txt)}],
        [{"metadata_path": str(right_txt)}],
    )
    assert txt_mismatch["equivalent"] is False

    occurrence = adapter.compare_artifacts(
        [{"metadata_path": str(left_json)}],
        [{"metadata_path": str(right_json)}],
    )
    assert occurrence["occurrence_only"] is True
    assert occurrence["raw_byte_equivalent"] is False


def test_artifact_comparison_list_length_and_empty_refs(tmp_path: Path) -> None:
    left = tmp_path / "left.json"
    right = tmp_path / "right.json"
    left.write_text(json.dumps({"items": [1, 2]}), encoding="utf-8")
    right.write_text(json.dumps({"items": [1]}), encoding="utf-8")
    result = FileArtifactByteComparisonAdapter().compare_artifacts(
        [{"metadata_path": str(left)}],
        [{"metadata_path": str(right)}],
    )
    assert result["equivalent"] is False
    empty = FileArtifactByteComparisonAdapter().compare_artifacts([], [])
    assert empty["available"] is False
    assert empty["equivalent"] is False


def test_raw_nested_schema_errors_cover_source_and_artifact_branches() -> None:
    errors = raw_nested_schema_errors(
        {
            "code_provenance": {"pipeline_version": 1, "git_commit": "abc"},
            "source_refs": [
                "not-an-object",
                {
                    "provider": " ",
                    "entity": 2,
                    "query": 3,
                },
                {
                    "provider": "chembl",
                    "entity": "activity",
                    "pipeline_name": "chembl_activity",
                    "input_snapshots": "bad",
                },
                {
                    "provider": "chembl",
                    "entity": "activity",
                    "pipeline_name": "chembl_activity",
                    "input_snapshots": [
                        "snap",
                        {
                            "snapshot_id": "",
                            "content_hash": 1,
                            "immutable_uri": 2,
                            "captured_at": 3,
                        },
                        {
                            "snapshot_id": "s1",
                            "content_hash": "abc",
                            "captured_at": "not-a-date",
                        },
                    ],
                },
            ],
            "planned_artifacts": ["bad", {"layer": "silver"}],
        }
    )
    assert "manifest_source_ref_not_object" in errors
    assert "manifest_source_ref_provider_empty" in errors
    assert "manifest_source_ref_entity_not_string" in errors
    assert "manifest_source_ref_pipeline_name_missing" in errors
    assert "manifest_source_ref_input_snapshots_missing" in errors
    assert "manifest_source_ref_input_snapshots_not_array" in errors
    assert "manifest_input_snapshot_not_object" in errors
    assert "manifest_input_snapshot_id_empty" in errors
    assert "manifest_input_content_hash_not_string" in errors
    assert "manifest_input_captured_at_not_string" in errors
    assert "manifest_input_captured_at_invalid" in errors
    assert "manifest_planned_artifact_not_object" in errors
    assert "manifest_planned_artifact_path_missing" in errors
    assert "manifest_code_provenance_pipeline_version_not_string" in errors
    skipped = raw_nested_schema_errors({"code_provenance": "x", "source_refs": {}})
    assert skipped == ()


def test_latest_scope_index_catalog_and_restore(tmp_path: Path) -> None:
    catalog_path = latest_scope_catalog_path(tmp_path)
    index_path = latest_scope_index_path(tmp_path, "chembl_activity", RunType.BACKFILL)
    assert load_latest_scope_catalog(catalog_path) is None
    assert load_latest_scope_index(
        index_path, pipeline_name="chembl_activity", run_type=RunType.BACKFILL
    ) is None

    catalog = LatestScopeIndexCatalog(
        complete=True,
        scopes=(("chembl_activity", RunType.BACKFILL),),
    )
    write_latest_scope_catalog(catalog_path, catalog)
    loaded = load_latest_scope_catalog(catalog_path)
    assert loaded == catalog

    record = LatestScopeIndexRecord(
        pipeline_name="chembl_activity",
        run_type=RunType.BACKFILL,
        manifest_id="m-1",
    )
    write_latest_scope_index(index_path, record)
    assert (
        load_latest_scope_index(
            index_path, pipeline_name="chembl_activity", run_type=RunType.BACKFILL
        )
        == record
    )

    catalog_path.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="JSON object"):
        load_latest_scope_catalog(catalog_path)
    catalog_path.write_text(json.dumps({"schema_version": 2}), encoding="utf-8")
    with pytest.raises(ValueError, match="schema_version"):
        load_latest_scope_catalog(catalog_path)
    catalog_path.write_text(
        json.dumps({"schema_version": 1, "complete": "yes", "scopes": []}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="malformed"):
        load_latest_scope_catalog(catalog_path)
    catalog_path.write_text(
        json.dumps({"schema_version": 1, "complete": True, "scopes": ["x"]}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="JSON object"):
        load_latest_scope_catalog(catalog_path)
    catalog_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "complete": True,
                "scopes": [{"pipeline_name": "", "run_type": "backfill"}],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="pipeline_name"):
        load_latest_scope_catalog(catalog_path)
    catalog_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "complete": True,
                "scopes": [{"pipeline_name": "p", "run_type": 1}],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="run_type"):
        load_latest_scope_catalog(catalog_path)
    catalog_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "complete": True,
                "scopes": [{"pipeline_name": "p", "run_type": "nope"}],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="run_type"):
        load_latest_scope_catalog(catalog_path)
    catalog_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "complete": True,
                "scopes": [
                    {"pipeline_name": "b", "run_type": "backfill"},
                    {"pipeline_name": "a", "run_type": "backfill"},
                ],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="deterministic"):
        load_latest_scope_catalog(catalog_path)
    catalog_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "complete": True,
                "scopes": [
                    {"pipeline_name": "a", "run_type": "backfill"},
                    {"pipeline_name": "a", "run_type": "backfill"},
                ],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate"):
        load_latest_scope_catalog(catalog_path)

    index_path.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="JSON object"):
        load_latest_scope_index(
            index_path, pipeline_name="chembl_activity", run_type=RunType.BACKFILL
        )
    index_path.write_text(json.dumps({"schema_version": 9}), encoding="utf-8")
    with pytest.raises(ValueError, match="schema_version"):
        load_latest_scope_index(
            index_path, pipeline_name="chembl_activity", run_type=RunType.BACKFILL
        )
    index_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "pipeline_name": "other",
                "run_type": "backfill",
                "manifest_id": "m",
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="requested scope"):
        load_latest_scope_index(
            index_path, pipeline_name="chembl_activity", run_type=RunType.BACKFILL
        )
    index_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "pipeline_name": "chembl_activity",
                "run_type": "backfill",
                "manifest_id": "  ",
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="manifest_id"):
        load_latest_scope_index(
            index_path, pipeline_name="chembl_activity", run_type=RunType.BACKFILL
        )

    missing = tmp_path / "missing.txt"
    assert read_optional_text(missing) is None
    existing = tmp_path / "keep.txt"
    existing.write_text("keep", encoding="utf-8")
    restore_optional_text(existing, None)
    assert not existing.exists()
    restore_optional_text(existing, "restored")
    assert existing.read_text(encoding="utf-8") == "restored"


def test_observability_backend_process_parse_drop_and_popen_kwargs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    netstat = (
        "  TCP    0.0.0.0:8000           0.0.0.0:0              LISTENING       12\n"
        "short\n"
        "  TCP    127.0.0.1:8000         0.0.0.0:0              LISTENING       bad\n"
        "  TCP    0.0.0.0:9000           0.0.0.0:0              ESTABLISHED     1\n"
    )
    assert backend._parse_windows_netstat_listener_pids(netstat, 8000) == (12,)
    ss = (
        "LISTEN 0 128 0.0.0.0:8000 0.0.0.0:* users:((python,pid=42,fd=3))\n"
        "short\n"
        "ESTAB 0 0 0.0.0.0:8000 0.0.0.0:*\n"
        "LISTEN 0 128 0.0.0.0:9000 0.0.0.0:* users:((python,pid=7,fd=1))\n"
        "LISTEN 0 128 0.0.0.0:8000 0.0.0.0:*\n"
    )
    assert backend._parse_posix_ss_listener_pids(ss, 8000) == (42,)
    assert backend._try_parse_pid("nope") is None
    assert backend.python_executable_to_tuple("python") == ("python",)
    assert backend.python_executable_to_tuple(["python", "-m"]) == ("python", "-m")

    monkeypatch.setattr(backend, "_resolve_system_executable", lambda _cmd: None)
    assert backend._find_windows_listener_pids_by_port(1) == ()
    assert backend._find_posix_listener_pids_by_port(1) == ()
    assert backend._run_taskkill(1).returncode == 1

    def _timeout(_command: list[str], **_kwargs: object) -> object:
        raise subprocess.TimeoutExpired(cmd="netstat", timeout=1)

    monkeypatch.setattr(backend.subprocess, "run", _timeout)
    monkeypatch.setattr(backend, "_resolve_system_executable", lambda _cmd: "netstat")
    assert backend._run_listener_probe(["netstat"]) == ""
    assert backend._run_taskkill(9).returncode == 1

    monkeypatch.setattr(backend, "_find_listening_backend_pids_by_port", lambda _p: ())
    assert backend.drop_listening_backend_on_port(8000, sleep_fn=lambda _s: None) is True
    monkeypatch.setattr(
        backend, "_find_listening_backend_pids_by_port", lambda _p: (11,)
    )
    monkeypatch.setattr(backend, "_drop_listener_pids", lambda _p, _ids: False)
    assert backend.drop_listening_backend_on_port(8000, sleep_fn=lambda _s: None) is False
    monkeypatch.setattr(backend, "_drop_listener_pids", lambda _p, _ids: True)
    monkeypatch.setattr(
        backend,
        "_find_listening_backend_pids_by_port",
        lambda _p: (),
    )
    assert backend.drop_listening_backend_on_port(8000, sleep_fn=lambda _s: None) is True

    monkeypatch.setattr(backend.os, "kill", lambda *_a, **_k: (_ for _ in ()).throw(OSError()))
    monkeypatch.setattr(backend, "_pid_still_listening", lambda *_a, **_k: False)
    assert backend._terminate_pid_with_sigterm(1, 2) is True
    assert backend._drop_posix_listener_pid(1, 2) is True

    posix_kwargs = backend._build_detached_backend_popen_kwargs(os_name="posix")
    assert posix_kwargs["start_new_session"] is True
    nt_kwargs = backend._build_detached_backend_popen_kwargs(
        os_name="nt",
        subprocess_module=SimpleNamespace(
            DEVNULL=subprocess.DEVNULL,
            DETACHED_PROCESS=1,
            CREATE_NEW_PROCESS_GROUP=2,
            CREATE_NO_WINDOW=4,
            STARTF_USESHOWWINDOW=8,
            SW_HIDE=0,
            STARTUPINFO=lambda: SimpleNamespace(dwFlags=0),
        ),
    )
    assert nt_kwargs["creationflags"] == 7
    env = backend._build_detached_backend_env(
        current_env={"PYTHONPATH": "existing"}
    )
    assert "existing" in env["PYTHONPATH"]

    launched: dict[str, object] = {}

    def _popen(command: list[str], **kwargs: object) -> SimpleNamespace:
        launched["command"] = command
        launched["kwargs"] = kwargs
        return SimpleNamespace(pid=1)

    monkeypatch.chdir(tmp_path)
    proc = backend.start_detached_quarantine_backend(
        bind_host="127.0.0.1",
        port=8011,
        python_executable="py",
        data_root=tmp_path,
        current_env={},
        popen_factory=_popen,
    )
    assert proc.pid == 1
    assert launched["command"][2] == "bioetl"
    assert backend.find_listening_backend_pid_by_port(8000) is None


def test_architecture_debt_reduction_classifies_remaining_categories(
    tmp_path: Path,
) -> None:
    reports = tmp_path / "reports" / "quality"
    reports.mkdir(parents=True)
    latest = reports / "tasks_architecture_metric_exemptions_2026-09-17-01.json"
    latest.write_text("{}", encoding="utf-8")
    assert debt.find_latest_architecture_debt_tasks_file(project_root=tmp_path) == latest
    empty = tmp_path / "empty"
    empty.mkdir()
    legacy = empty / "tasks_architecture_metric_exemptions_legacy.json"
    legacy.write_text("{}", encoding="utf-8")
    assert debt.find_latest_architecture_debt_tasks_file(project_root=empty) == legacy
    missing = tmp_path / "none"
    missing.mkdir()
    assert debt.find_latest_architecture_debt_tasks_file(project_root=missing) is None

    payload_path = tmp_path / "tasks.json"
    payload_path.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="mapping"):
        debt.load_architecture_debt_tasks(payload_path)
    payload_path.write_text(json.dumps({"tasks": []}), encoding="utf-8")
    assert debt.load_architecture_debt_tasks(payload_path)["tasks"] == []

    with pytest.raises(ValueError, match="generated_at"):
        debt.build_architecture_debt_execution_plan({}, generated_at=None)

    plan = debt.build_architecture_debt_execution_plan(
        {
            "tasks": [
                {
                    "id": "GOD-1",
                    "registry": "god_object",
                    "status": "needs_refactor",
                    "target_file": "src/bioetl/infrastructure/big.py",
                },
                {
                    "id": "NEAR-1",
                    "registry": "unknown_registry",
                    "status": "within_limit",
                    "current_value": 10,
                    "delta_to_limit": -2,
                    "target_file": "src/bioetl/application/x.py",
                },
                {
                    "id": "SAFE-1",
                    "registry": "file_size_limits",
                    "status": "within_limit",
                    "current_value": 700,
                    "delta_to_limit": -20,
                    "target_file": "src/bioetl/infrastructure/x.py",
                },
                {
                    "id": "LEN-1",
                    "registry": "function_length",
                    "status": "needs_refactor",
                    "current_value": 120,
                    "delta_to_limit": 20,
                    "target_file": "src/bioetl/application/x.py",
                },
                {
                    "id": "CLS-1",
                    "registry": "class_size",
                    "status": "needs_refactor",
                    "current_value": 400,
                    "target_file": "not/a/layer.py",
                },
                {
                    "id": "METH-1",
                    "registry": "class_method_count",
                    "status": "needs_refactor",
                    "current_value": 30,
                    "target_file": "src/bioetl/interfaces/x.py",
                },
                {
                    "id": "DEAD-1",
                    "task_family": "dead_code_review",
                    "registry": "artifact_governance",
                    "status": "needs_refactor",
                    "target_file": "src/bioetl/application/y.py",
                },
                {
                    "id": "HOT-1",
                    "task_family": "hotspot_family",
                    "registry": "artifact_governance",
                    "status": "needs_refactor",
                    "target_file": "src/bioetl/application/z.py",
                },
                {
                    "id": "CPLX-LAYER",
                    "registry": "domain_complexity",
                    "status": "needs_refactor",
                    "target_file": "src/bioetl/domain/x.py",
                },
            ]
        },
        generated_at=datetime(2026, 9, 17, tzinfo=UTC),
    )
    categories = {item["category"] for item in plan["tasks"]}
    assert "GOD_OBJECT" in categories
    assert "NEAR_LIMIT" in categories
    assert "SAFE_MARGIN" in categories
    assert "REDUCE_TO_LIMIT" in categories
    assert "DEAD_CODE_REVIEW_DEBT" in categories
    assert "HOTSPOT_SIZE_COUPLING_DEBT" in categories
    assert "COMPLEXITY" in categories
    output = debt._default_plan_output_path(
        project_root=tmp_path,
        generated_at=datetime(2026, 9, 17, 12, 0, tzinfo=UTC),
    )
    assert output.name.endswith("2026-09-17-12-00.json")


def test_pipeline_config_common_schemas_validators() -> None:
    with pytest.raises(ValueError, match="empty column"):
        SinkLayerConfig.model_validate({"sort_by": ["id", " "]})
    with pytest.raises(ValueError, match="duplicate"):
        SinkLayerConfig.model_validate({"sort_by": ["id", "id"]})
    layer = SinkLayerConfig.model_validate({"sort_by": ["id", "name"]})
    assert layer.sort_by == ["id", "name"]
    scd = ScdConfigYamlConfig.model_validate({"type": 2, "business_key": "id"})
    domain = scd.to_domain(primary_keys=("id",))
    assert domain.scd_type == 2
    with pytest.raises(ValueError, match="semver"):
        TransformConfig.model_validate({"version": "1"})
    assert TransformConfig.model_validate({"version": "v1.2.3-alpha+build"}).version
    with pytest.raises(ValueError, match="semver"):
        AuthoritativeContentHashPolicyContractConfig.model_validate(
            {"version": "1", "migration_note": "note"}
        )
    with pytest.raises(ValueError, match="non-empty"):
        AuthoritativeContentHashPolicyContractConfig.model_validate(
            {"version": "1.0.0", "migration_note": "  "}
        )
    with pytest.raises(ValueError, match="blank"):
        AuthoritativeContentHashPolicyConfig.model_validate(
            {
                "provider": "chembl",
                "entity": "activity",
                "contract": {"version": "1.0.0", "migration_note": "n"},
                "canonicalization": "json",
                "include_fields": ["id", " "],
            }
        )
    with pytest.raises(ValueError, match="duplicates"):
        AuthoritativeContentHashPolicyConfig.model_validate(
            {
                "provider": "chembl",
                "entity": "activity",
                "contract": {"version": "1.0.0", "migration_note": "n"},
                "canonicalization": "json",
                "include_fields": ["id", "id"],
            }
        )
    with pytest.raises(ValueError, match="field_ordering"):
        AuthoritativeContentHashPolicyConfig.model_validate(
            {
                "provider": "chembl",
                "entity": "activity",
                "contract": {"version": "1.0.0", "migration_note": "n"},
                "canonicalization": "json",
                "include_fields": ["id"],
                "field_ordering": {" ": "asc"},
            }
        )
    with pytest.raises(ValueError, match="Semantic filter keys"):
        SilverFiltersConfig.model_validate({"columns": {"id": ["x"]}})
    structural = SilverFiltersConfig.model_validate({"required_fields": ["id"]})
    assert structural.to_domain().required_fields == ("id",)


def test_pipeline_normalizers_hash_policy_and_chembl_ordering() -> None:
    assert _is_empty_string_collection(None) is True
    assert _is_empty_string_collection("x") is False
    assert _is_empty_string_collection([" ", ""]) is True
    assert _has_business_group({"system", "activity"}) is True
    config: dict[str, object] = {"provider": "chembl", "entity_type": "activity"}
    apply_pipeline_schema_normalization(
        config,
        entity_config={},
        config_path="unused",
        unified_hash_policy=None,
    )
    with pytest.raises(ValueError, match="hash_policy.provider"):
        apply_pipeline_schema_normalization(
            {"provider": "chembl", "entity_type": "activity"},
            entity_config={},
            config_path="x",
            unified_hash_policy={"provider": "pubchem", "entity": "activity"},
        )
    with pytest.raises(ValueError, match="hash_policy.entity"):
        apply_pipeline_schema_normalization(
            {"provider": "chembl", "entity_type": "activity"},
            entity_config={},
            config_path="x",
            unified_hash_policy={"provider": "chembl", "entity": "assay"},
        )
    with pytest.raises(ValueError, match="content_hash.include"):
        _validate_schema_hash_policy_shims({"content_hash": {"include": ["id"]}})
    with pytest.raises(ValueError, match="content_hash.exclude"):
        _validate_schema_hash_policy_shims({"content_hash": {"exclude": ["id"]}})
    with pytest.raises(ValueError, match="hash_include"):
        _validate_contract_hash_policy_shims({"hash_include": ["id"]})
    with pytest.raises(ValueError, match="hash_exclude"):
        _validate_contract_hash_policy_shims({"hash_exclude": ["id"]})
    with pytest.raises(ValueError, match="hash_policy.hash_policy must be a mapping"):
        apply_pipeline_schema_normalization(
            {"provider": "openalex", "entity_type": "work"},
            entity_config={},
            config_path="x",
            unified_hash_policy={
                "provider": "openalex",
                "entity": "work",
                "hash_policy": "bad",
            },
        )
    with pytest.raises(ValueError, match="field_ordering must be empty"):
        apply_pipeline_schema_normalization(
            {"provider": "chembl", "entity_type": "activity"},
            entity_config={},
            config_path="x",
            unified_hash_policy={
                "provider": "chembl",
                "entity": "activity",
                "hash_policy": {"field_ordering": {"id": "asc"}},
            },
        )
    projected: dict[str, object] = {"provider": "openalex", "entity_type": "work"}
    apply_pipeline_schema_normalization(
        projected,
        entity_config={},
        config_path="x",
        unified_hash_policy={
            "provider": "openalex",
            "entity": "work",
            "contract": {"version": "1"},
            "hash_policy": {"algorithm": "sha256"},
        },
    )
    assert projected["content_hash_policy"]["algorithm"] == "sha256"


def _archive_fixture(tmp_path: Path) -> tuple[FileArchiveStore, RunManifest, ControlPlaneArtifactLifecyclePlan]:
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
    (data / "manifest.json").write_text(json.dumps(manifest.to_dict()), encoding="utf-8")
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


def test_file_archive_store_rejects_incomplete_and_corrupt_index(tmp_path: Path) -> None:
    store, manifest, plan = _archive_fixture(tmp_path)
    blocked = ControlPlaneArtifactLifecyclePlan(
        generated_at=plan.generated_at,
        cutoff=plan.cutoff,
        dry_run=True,
        artifacts=plan.artifacts,
        resolution_issues=(
            ControlPlaneArtifactResolutionIssue(
                code=ControlPlaneArtifactResolutionIssueCode.LINEAGE_INDEX_MISSING,
                surface=ControlPlaneArtifactSurface.LINEAGE,
                detail="missing",
            ),
        ),
    )
    with pytest.raises(ValueError, match="archive_source_evidence_incomplete"):
        store.create(manifest=manifest, plan=blocked)
    with pytest.raises(ValueError, match="archive_path_outside_root"):
        archive_module._contained_file(tmp_path, str(tmp_path / "abs.txt"))
    pack = store.create(manifest=manifest, plan=plan)
    index = pack / "index.json"
    payload = json.loads(index.read_text(encoding="utf-8"))
    payload["schema"] = "wrong"
    index.write_text(json.dumps(payload), encoding="utf-8")
    assert store.verify(manifest=manifest, plan=plan) == (False, "archive_index_invalid")
    payload["schema"] = archive_module._SCHEMA
    payload["files"] = []
    index.write_text(json.dumps(payload), encoding="utf-8")
    assert store.verify(manifest=manifest, plan=plan) == (False, "archive_index_invalid")
    payload["files"] = {"path": "x"}
    index.write_text(json.dumps(payload), encoding="utf-8")
    assert store.verify(manifest=manifest, plan=plan)[0] is False
    (store.data_root / "manifest.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="archive_manifest_invalid"):
        store.create(manifest=manifest, plan=plan)


def test_provider_health_evidence_freshness_and_invalid_payloads(tmp_path: Path) -> None:
    store = FileProviderHealthEvidenceStore(tmp_path / "health")
    assert store.list_all() == ()
    now = datetime(2026, 9, 17, 12, 0, tzinfo=UTC)
    record = ProviderHealthEvidenceRecord(
        provider="chembl",
        status=1,
        observed_at=now.isoformat(),
        endpoint="/status",
        reason="  ok  ",
    )
    store.persist(record)
    loaded = store.load("chembl")
    assert loaded is not None
    assert loaded.is_fresh(now=now) is True
    stale = ProviderHealthEvidenceRecord(
        provider="chembl",
        status=1,
        observed_at="2020-01-01T00:00:00+00:00",
        endpoint="/status",
    )
    assert stale.is_fresh(now=now) is False
    assert ProviderHealthEvidenceRecord(
        provider="chembl",
        status=1,
        observed_at="not-a-date",
        endpoint="/status",
    ).observed_unix() is None
    bad = tmp_path / "health" / "bad.json"
    bad.write_text("{", encoding="utf-8")
    listed = tmp_path / "health" / "other.json"
    listed.write_text(json.dumps(["not-object"]), encoding="utf-8")
    status_bad = tmp_path / "health" / "status.json"
    status_bad.write_text(
        json.dumps(
            {
                "provider": "x",
                "status": 9,
                "observed_at": "t",
                "endpoint": 1,
                "reason": 2,
            }
        ),
        encoding="utf-8",
    )
    blank = tmp_path / "health" / "blank.json"
    blank.write_text(
        json.dumps({"provider": " ", "status": 1, "observed_at": "t", "endpoint": ""}),
        encoding="utf-8",
    )
    records = store.list_all()
    assert all(item.provider == "chembl" for item in records)


def test_pandera_validator_schema_gaps_and_gold_passthrough() -> None:
    import pandera.pandas as pa

    assert NoOpValidator().validate([{"id": 1}]).valid is True
    empty = PanderaSilverValidator(schema=None, strict=False)
    assert empty.validate([]).valid is True
    assert empty.validate([{"id": 1}]).valid is True
    strict = PanderaSilverValidator(schema=None, strict=True)
    failed = strict.validate([{"id": 1}])
    assert failed.valid is False
    rebound = empty.rebind_schema(pa.DataFrameSchema({"id": pa.Column(str)}))
    assert rebound.validate([{"id": "a"}]).valid is True

    class _NoColumns:
        pass

    host = BasePanderaValidator(schema=_NoColumns(), strict=False)  # type: ignore[arg-type]
    frame = pd.DataFrame({"id": ["a"]})
    assert host._reorder_to_schema(frame) is frame
    assert host._normalize_nullable_integer_columns(frame) is frame
    assert host._normalize_nullable_boolean_columns(frame) is frame

    nullable = pa.DataFrameSchema(
        {
            "n": pa.Column("Int64", nullable=True),
            "flag": pa.Column("boolean", nullable=True),
            "name": pa.Column(str, nullable=True),
        }
    )
    silver = PanderaSilverValidator(schema=nullable, strict=True)
    result = silver.validate([{"n": None, "flag": None}])
    assert result.valid is True
    mixed = silver.validate([{"n": "nope", "flag": "nope", "name": "ok"}])
    assert mixed.valid is False

    gold_schema = pa.DataFrameSchema({"id": pa.Column(str)}, strict=True)
    gold = PanderaGoldValidator(schema=gold_schema, strict=False)
    assert gold.validate([{"id": "a", "extra": 1}]).valid is True
    strict_gold = PanderaGoldValidator(schema=gold_schema, strict=True)
    assert strict_gold.validate([{"id": "a", "extra": 1}]).valid is False


def test_workflow_transform_artifact_store_debug_and_helpers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    clock = SimpleNamespace(now=lambda: datetime(2026, 9, 17, tzinfo=UTC))
    store = FileWorkflowTransformArtifactStore(base_path=tmp_path / "cp", clock=clock)
    context = SimpleNamespace(
        workflow_run_id="run-1",
        step_id="step-1",
        debug_export_enabled=False,
        created_at="not-dt",
    )
    assert store.write_reconcile_debug_artifacts(
        context=context,
        request=SimpleNamespace(),
        result=SimpleNamespace(),
        retained_rows=(),
        orphan_rows=(),
    ) == ()
    with pytest.raises(ValueError, match="requires"):
        _required_attr(SimpleNamespace(workflow_run_id=" "), "workflow_run_id")
    with pytest.raises(RuntimeError, match="clock"):
        FileWorkflowTransformArtifactStore(
            base_path=tmp_path / "cp",
            clock=SimpleNamespace(now=lambda: "now"),
        ).write_reconcile_result_artifact(
            context=SimpleNamespace(
                workflow_run_id="run-1",
                step_id="step-1",
                created_at="x",
            ),
            payload={"ok": True},
        )
    context.created_at = datetime(2026, 9, 17, tzinfo=UTC)
    context.debug_export_enabled = True
    context.workflow_name = "wf"
    context.debug_export_dir = "debug"
    request = SimpleNamespace(
        effective_source_keys=["src"],
        primary_keys=("id",),
        source_table="src",
        reference_table="ref",
    )
    result = SimpleNamespace(mutated=False, dry_run=True)
    refs = store.write_reconcile_debug_artifacts(
        context=context,
        request=request,
        result=result,
        retained_rows=({"id": 1, "nested": {"a": 1}},),
        orphan_rows=({"id": 2, "when": datetime(2026, 1, 1, tzinfo=UTC)},),
    )
    assert refs
    written = store.write_reconcile_result_artifact(
        context=context,
        payload={"status": "ok"},
    )
    assert written[-1]["type"] == "workflow_transform_result"
    assert _attr_tuple(SimpleNamespace(x=["a"]), "x") == ("a",)
    assert _attr_tuple(SimpleNamespace(x="nope"), "x") == ()
    assert json.loads(str(_csv_value({"a": 1}))) == {"a": 1}
    assert _csv_value(datetime(2026, 1, 1, tzinfo=UTC)).startswith("2026")
    assert _jsonable(object()).__class__ is str


def test_exemptions_registry_targets_symbol_and_registry_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(targets, "_project_root", lambda: tmp_path)
    monkeypatch.setattr(
        targets,
        "load_exemptions_registry",
        lambda _path=None: {"registries": []},
    )
    assert targets.validate_exemption_target_references() == ["registries: expected mapping"]
    monkeypatch.setattr(
        targets,
        "load_exemptions_registry",
        lambda _path=None: {"registries": {}},
    )
    assert targets.validate_exemption_target_references() == [
        "src/bioetl: source root not found"
    ]
    module = tmp_path / "src" / "bioetl" / "mod.py"
    module.parent.mkdir(parents=True)
    module.write_text("class Foo:\n    pass\n\ndef bar():\n    pass\n", encoding="utf-8")
    other = tmp_path / "src" / "bioetl" / "other.py"
    other.write_text("class Foo:\n    pass\n", encoding="utf-8")
    broken = tmp_path / "src" / "bioetl" / "broken.py"
    broken.write_text("def (", encoding="utf-8")
    monkeypatch.setattr(
        targets,
        "load_exemptions_registry",
        lambda _path=None: {
            "registries": {
                "file_size_limits": {"ignored.py": {}},
                "class_size": {
                    "src/bioetl/mod.py::": {},
                    "not-a-module::Foo": {},
                    "src/bioetl/missing.py::Foo": {},
                    "src/bioetl/mod.py::Missing": {},
                    "Unknown": {},
                    "Foo": {},
                },
                "function_length": {"src/bioetl/mod.py::bar": {}},
                "domain_complexity": {"bar": {}},
            }
        },
    )
    errors = targets.validate_exemption_target_references()
    assert any("must be non-empty" in item for item in errors)
    assert any("canonical module path" in item for item in errors)
    assert any("does not exist" in item for item in errors)
    assert any("not found in" in item for item in errors)
    assert any("not found" in item and "Unknown" in item for item in errors)
    assert any("ambiguous" in item for item in errors)


def test_chembl_policy_registry_loader_errors_and_unit_merge(tmp_path: Path) -> None:
    configs = tmp_path / "configs"
    vocab = configs / "vocab"
    vocab.mkdir(parents=True)
    loader = ChemblPolicyRegistryLoader(configs)
    with pytest.raises(FileNotFoundError):
        loader.load()
    (vocab / "chembl_controlled.yaml").write_text("[]", encoding="utf-8")
    with pytest.raises(TypeError, match="mapping"):
        loader.load()
    (vocab / "chembl_controlled.yaml").write_text(
        yaml.safe_dump(
            {
                "strict_boolean_families": "bad",
                "strict_flag_families": {},
                "controlled_vocabularies": {},
            }
        ),
        encoding="utf-8",
    )
    (vocab / "chembl_ontology.yaml").write_text(
        yaml.safe_dump({"families": {}}), encoding="utf-8"
    )
    with pytest.raises(TypeError, match="strict_boolean"):
        loader.load()
    (vocab / "chembl_controlled.yaml").write_text(
        yaml.safe_dump(
            {
                "strict_boolean_families": {
                    "flags": {
                        "invalid_value_mode": "reject",
                        "fields": ["activity.flag"],
                    }
                },
                "strict_flag_families": {},
                "controlled_vocabularies": {
                    "status": {
                        "invalid_value_mode": "reject",
                        "fields": ["activity.status"],
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    (vocab / "chembl_ontology.yaml").write_text("families: no", encoding="utf-8")
    with pytest.raises(TypeError, match="families"):
        loader.load()
    (vocab / "chembl_ontology.yaml").write_text(
        yaml.safe_dump(
            {
                "families": {
                    "units": {
                        "fields": ["activity.units"],
                        "companion_fields": "bad",
                    },
                    "skip": "not-dict",
                },
                "unit_companion_policies": {
                    "bad": "x",
                    "policy": {
                        "fields": ["activity.units_units", 1],
                        "ontology_families": "nope",
                    },
                    "ok": {
                        "fields": ["activity.units_units", "ignore.me"],
                        "ontology_families": ["units", "missing", 1],
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    data = loader.load()
    assert data.ontology_families[0].family_name == "units"
    with pytest.raises(TypeError):
        _require_sequence("x", field_name="fields")
    with pytest.raises(TypeError):
        _require_mapping("x", field_name="map")


def test_pipeline_contract_policy_rollout_and_merge_key_guards() -> None:
    policy = _policy()
    assert policy.rollout_mode == "single"
    assert policy.read_order == ["v1"]
    assert policy.write_versions == ["v1"]
    assert policy.affects_hash is False
    runtime = policy.to_contract_rollout_policy()
    assert runtime.active_version == "v1"
    with pytest.raises(ValueError, match="hash_datetime_policy"):
        _policy(hash_datetime_policy="bad")
    with pytest.raises(ValueError, match="overlap"):
        _policy(merge_keys=["other"])
    with pytest.raises(ValueError, match="rollout.mode"):
        _policy(rollout={"mode": "triple", "read_order": ["v1"], "write_versions": ["v1"]})
    with pytest.raises(ValueError, match="contract_ref"):
        _policy(contract_ref=" ")
    with pytest.raises(ValueError, match="active_version"):
        _policy(active_version=" ")
    with pytest.raises(ValueError, match="read_order"):
        _policy(
            rollout={"mode": "dual_read", "read_order": ["v2"], "write_versions": ["v1"]}
        )
    with pytest.raises(ValueError, match="write_versions"):
        _policy(
            rollout={"mode": "dual_write", "read_order": ["v1"], "write_versions": ["v2"]}
        )
    with pytest.raises(ValueError, match="duplicate"):
        _policy(
            rollout={
                "mode": "dual_read",
                "read_order": ["v1", "v1"],
                "write_versions": ["v1"],
            }
        )
    with pytest.raises(ValueError, match="duplicate"):
        _policy(
            rollout={
                "mode": "dual_write",
                "read_order": ["v1"],
                "write_versions": ["v1", "v1"],
            }
        )
    with pytest.raises(ValueError, match="read_order == \\[active_version\\]"):
        _policy(
            rollout={
                "mode": "single",
                "read_order": ["v1", "v2"],
                "write_versions": ["v1"],
            }
        )
    with pytest.raises(ValueError, match="write_versions == \\[active_version\\]"):
        _policy(
            rollout={
                "mode": "single",
                "read_order": ["v1"],
                "write_versions": ["v1", "v2"],
            }
        )
