"""Stream A remaining infrastructure residuals for #10469 / #10517."""

from __future__ import annotations

import json
from contextlib import AbstractContextManager
from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from urllib.error import URLError
from uuid import UUID

import pytest
import yaml
from pydantic import ValidationError

from bioetl.domain.ports import HealthCheckResult
from bioetl.domain.types import HealthStatus, RunID, RunType
from bioetl.infrastructure.config._composite_dq_externalization import (
    merge_external_dq_overrides,
)
from bioetl.infrastructure.config._composite_shared_policy_externalization import (
    merge_external_shared_policy,
)
from bioetl.infrastructure.config.dq_contract_config_loader import (
    _create_report_config,
    _parse_disposition_overrides,
    _parse_strictness_mode,
    _resolve_contract_strict_dq_validation,
    _resolve_identity_data,
    _resolve_threshold,
    _validate_identity_field,
)
from bioetl.infrastructure.config.enum_file_loader import (
    load_chembl_enums_from_file,
    load_provider_enums_from_file,
)
from bioetl.infrastructure.config.publication_controlled_vocabulary_loader import (
    PublicationControlledVocabularyLoader,
)
from bioetl.infrastructure.config.reason_catalog_loader import (
    load_default_reason_catalog,
    load_reason_catalog_from_path,
    load_reason_catalog_from_text,
)
from bioetl.infrastructure.control_plane._file_artifact_lifecycle_manifest_protections import (
    payload_execution_context,
    record_manifest_protections,
    required_persistence_profile,
    requires_evidence_floor,
    supports_historical_replay_floor,
)
from bioetl.infrastructure.control_plane._file_run_ledger_helpers import (
    RunLedgerCorruptionError,
    emit_ledger_append_duration_metric,
    emit_ledger_append_metric,
    emit_terminal_event_metric,
    ensure_entries_match_manifest_and_run_identity,
    ensure_entries_match_run_index,
    has_idempotent_duplicate,
    iter_jsonl_payloads_strict,
    resolve_ledger_pipeline,
)
from bioetl.infrastructure.control_plane._raw_run_manifest_inspection import (
    ContractEvidenceConflictError,
    RawRunManifestInspectionMixin,
    persist_contract_evidence,
)
from bioetl.infrastructure.control_plane._run_manifest_scope_index import (
    LatestScopeIndexCatalog,
)
from bioetl.infrastructure.control_plane._run_manifest_scope_rebuild import (
    plan_latest_scope_index_rebuild,
)
from bioetl.infrastructure.control_plane.file_artifact_lifecycle_payloads import (
    _artifact_id,
    _content_addressed_file_snapshot_id,
    _indexed_stem,
    _input_snapshot_ids,
    _is_payload_stale,
    _lineage_fragment_id_candidates,
    _manifest_or_run_is_protected,
    _optional_text,
    _parse_datetime,
    _read_json_object_or_empty,
    _resolve_lifecycle_reason,
)
from bioetl.infrastructure.control_plane.file_provider_health_evidence import (
    FileProviderHealthEvidenceStore,
    ProviderHealthEvidenceRecord,
)
from bioetl.infrastructure.control_plane.provider_health_evidence import (
    PersistingProviderHealthMonitor,
    rehydrate_provider_health_evidence,
)
from bioetl.infrastructure.observability._metrics_gateway_publication import (
    _sanitize_pushgateway_grouping_key,
    publish_metrics_to_gateway,
)
from bioetl.infrastructure.observability._prometheus_metric_label_normalizers import (
    normalize_adapter_endpoint_label,
    normalize_quarantine_reason,
    normalize_source_file_label,
)
from bioetl.infrastructure.observability.observability_backend_probes import (
    probe_observability_backend,
    probe_observability_backend_required_paths,
    wait_for_observability_backend_ready,
    wait_for_observability_backend_required_paths_ready,
)
from bioetl.infrastructure.quality._baseline_validation import (
    _validate_baseline_mapping,
    _validate_grouped_registry_coverage,
    _validate_registry_counts_mapping,
    _validate_registry_group_entry,
)
from bioetl.infrastructure.quality.architecture_debt_artifact_tasks import (
    _append_reviewed_metric_task,
    _count_value,
    _metric_policy,
    artifact_defaults,
)
from bioetl.infrastructure.quality.architecture_debt_task_support import (
    fallback_complexity,
    function_complexities,
    iter_source_modules,
    parse_limit_value,
    safe_text,
)
from bioetl.infrastructure.quality.architecture_quality_scorecard import (
    _as_float,
    _load_json,
    _load_yaml,
)
from bioetl.infrastructure.quality.budget_evaluator import (
    current_quarter_target,
    resolve_grace_allowances,
)
from bioetl.infrastructure.quality.exemptions_registry_policy import (
    validate_exemption_key_normalization,
    validate_exemptions_registry,
)
from bioetl.infrastructure.quality.exemptions_registry_validation import (
    get_policy_required_fields,
    validate_exemption_entry,
)
from bioetl.infrastructure.quality.report_formatter import (
    _extract_growth_violation_section,
    _is_active_grace_window,
    _is_rollout_cutoff_stale,
    split_growth_violations_by_severity,
)
from bioetl.infrastructure.schemas._composite_config_merge_schema import (
    ColumnGroupSchema,
    MergeSchema,
    MergeSortBySchema,
    TargetProteinClassificationProjectionSchema,
)
from bioetl.infrastructure.schemas.composite_config_base import (
    AggregationSchema,
    DependencySchema,
    EnricherSchema,
    SeedSchema,
)
from bioetl.infrastructure.schemas.pipeline_config_common import DQYamlConfig
from bioetl.infrastructure.schemas.workflow_config_fk import (
    _normalize_fk_optional_name,
    _normalize_fk_required_names,
    _require_fk_key_pairs_present,
    _require_fk_key_pairs_together,
    _validate_fk_composite_alignment,
)

pytestmark = pytest.mark.unit


class _InspectionHost(RawRunManifestInspectionMixin):
    def __init__(self, base_path: Path) -> None:
        self.base_path = base_path


class _ScopeStore:
    def __init__(self, base_path: Path, manifests: tuple[Any, ...]) -> None:
        self.base_path = base_path
        self._manifests = manifests
        self._current: dict[tuple[str, RunType], Any] = {}
        self._catalog: LatestScopeIndexCatalog | None = None
        self._raise = False

    def list_all(self) -> tuple[Any, ...]:
        return self._manifests

    def _latest_scope_index_path(self, pipeline_name: str, run_type: RunType) -> Path:
        return self.base_path / f"{pipeline_name}.{run_type.value}.json"

    def _load_latest_scope_catalog(self) -> LatestScopeIndexCatalog | None:
        if self._raise:
            raise ValueError("catalog corrupt")
        return self._catalog

    def _load_latest_scope_manifest(self, pipeline_name: str, run_type: RunType) -> Any:
        if self._raise:
            raise ValueError("index corrupt")
        return self._current.get((pipeline_name, run_type))


def test_scope_rebuild_create_update_noop_and_corrupt(tmp_path: Path) -> None:
    desired = SimpleNamespace(
        pipeline_name="chembl_activity",
        run_type=RunType.BACKFILL,
        manifest_id="m-new",
    )
    current = SimpleNamespace(
        pipeline_name="chembl_activity",
        run_type=RunType.BACKFILL,
        manifest_id="m-old",
    )
    store = _ScopeStore(tmp_path, (desired,))
    created = plan_latest_scope_index_rebuild(store)
    assert created["catalog"]["action"] == "create"
    assert created["entries"][0]["action"] == "create"
    store._current[(desired.pipeline_name, desired.run_type)] = current
    store._catalog = LatestScopeIndexCatalog(
        complete=False, scopes=((desired.pipeline_name, desired.run_type),)
    )
    updated = plan_latest_scope_index_rebuild(store)
    assert updated["entries"][0]["action"] == "update"
    assert updated["catalog"]["action"] == "update"
    store._current[(desired.pipeline_name, desired.run_type)] = desired
    store._catalog = LatestScopeIndexCatalog(
        complete=True, scopes=((desired.pipeline_name, desired.run_type),)
    )
    noop = plan_latest_scope_index_rebuild(store)
    assert noop["entries"][0]["action"] == "noop"
    assert noop["catalog"]["action"] == "noop"
    store._raise = True
    blocked = plan_latest_scope_index_rebuild(store)
    assert blocked["entries"][0]["action"] == "blocked_corrupt"
    assert blocked["catalog"]["action"] == "blocked_corrupt"


def test_raw_manifest_inspection_and_contract_evidence(tmp_path: Path) -> None:
    host = _InspectionHost(tmp_path)
    missing = host.inspect_raw_manifest("m-1")
    assert missing.parse_ok is False
    path = tmp_path / "m-1.json"
    path.write_text("{", encoding="utf-8")
    parsed = host.inspect_raw_manifest("m-1")
    assert "manifest_parse_error" in parsed.schema_errors
    path.write_text("[]", encoding="utf-8")
    not_object = host.inspect_raw_manifest("m-1")
    assert "manifest_payload_not_object" in not_object.schema_errors
    path.write_text(
        json.dumps(
            {
                "manifest_id": "other",
                "execution_fingerprint": "fp",
                "schema_version": "bad",
                "created_at": "nope",
                "run_id": "not-uuid",
                "run_type": "nope",
                "pipeline_name": "p",
                "provider": "chembl",
                "entity": "activity",
                "launch_context": [],
                "source_refs": {},
                "runtime_config": [],
                "planned_artifacts": {},
                "workflow_run_id": 1,
            }
        ),
        encoding="utf-8",
    )
    inspected = host.inspect_raw_manifest("m-1")
    assert inspected.parse_ok is True
    assert "manifest_id_mismatch" in inspected.schema_errors
    evidence = {
        "schema_version": "contract_evidence_v1",
        "contract_comparison_status": "ok",
        "lock_owner_id": "  owner  ",
    }
    persist_contract_evidence(tmp_path, "m-1", evidence)
    persist_contract_evidence(tmp_path, "m-1", evidence)
    with pytest.raises(ContractEvidenceConflictError):
        persist_contract_evidence(tmp_path, "m-1", {**evidence, "x": 1})


def test_provider_health_monitor_persist_and_rehydrate(tmp_path: Path) -> None:
    inner = SimpleNamespace(
        update_from_health_check_result=lambda result, logger=None: (
            HealthStatus.DEGRADED
        ),
        record_success=lambda provider: HealthStatus.HEALTHY,
        record_error=lambda provider: HealthStatus.UNHEALTHY,
        get_all_states=lambda: {"chembl": "state"},
    )
    store = FileProviderHealthEvidenceStore(tmp_path)
    clock = SimpleNamespace(now=lambda: datetime(2026, 9, 17, 12, 0))
    monitor = PersistingProviderHealthMonitor(
        inner=inner,  # type: ignore[arg-type]
        store=store,
        clock=clock,  # type: ignore[arg-type]
    )
    naive = HealthCheckResult(
        status=HealthStatus.DEGRADED,
        latency_ms=1.0,
        provider="chembl",
        endpoint="x" * 200,
        last_error="boom",
        checked_at=datetime(2026, 9, 17, 12, 0),
    )
    assert monitor.update_from_health_check_result(naive) is HealthStatus.DEGRADED
    loaded = store.load("chembl")
    assert loaded is not None
    assert loaded.reason == "probe_error"
    assert len(loaded.endpoint) == 128
    assert monitor.record_success("chembl") is HealthStatus.HEALTHY
    assert monitor.record_error("chembl") is HealthStatus.UNHEALTHY
    assert monitor.get_all_states() == {"chembl": "state"}
    metrics = SimpleNamespace(set_gauge=lambda *a, **k: None)
    published = rehydrate_provider_health_evidence(
        metrics,  # type: ignore[arg-type]
        store,
        now=datetime(2026, 9, 17, 12, 0, tzinfo=UTC),
    )
    assert published == 1
    store.persist(
        ProviderHealthEvidenceRecord(
            provider="pubchem",
            status=0,
            observed_at="not-a-date",
            endpoint="/",
        )
    )
    assert (
        rehydrate_provider_health_evidence(
            metrics,  # type: ignore[arg-type]
            store,
            now=datetime(2026, 9, 17, 12, 0, tzinfo=UTC),
        )
        == 2
    )


def test_artifact_lifecycle_payload_helpers(tmp_path: Path) -> None:
    jsonl = tmp_path / "rows.jsonl"
    jsonl.write_text("\n\n", encoding="utf-8")
    assert _read_json_object_or_empty(jsonl) == {}
    jsonl.write_text("[]\n", encoding="utf-8")
    assert _read_json_object_or_empty(jsonl) == {}
    jsonl.write_text("{not-json}\n", encoding="utf-8")
    assert _read_json_object_or_empty(jsonl) == {}
    payload_file = tmp_path / "row.json"
    payload_file.write_text(
        json.dumps({"created_at": "2020-01-01T00:00:00+00:00"}), encoding="utf-8"
    )
    payload = _read_json_object_or_empty(payload_file)
    cutoff = datetime(2026, 1, 1, tzinfo=UTC)
    assert _is_payload_stale(payload_file, payload, cutoff) is True
    assert _parse_datetime("not-a-date") is None
    naive = _parse_datetime("2026-01-01T00:00:00")
    assert naive is not None and naive.tzinfo is not None
    assert _optional_text("  ") is None
    from bioetl.domain.control_plane import ControlPlaneArtifactSurface

    assert (
        _artifact_id(
            surface=ControlPlaneArtifactSurface.RUN_MANIFEST,
            path=payload_file,
            payload={"manifest_id": "m"},
        )
        == "m"
    )
    assert (
        _artifact_id(
            surface=ControlPlaneArtifactSurface.LINEAGE,
            path=payload_file,
            payload={"fragment_id": "f"},
        )
        == "f"
    )
    assert (
        _artifact_id(
            surface=ControlPlaneArtifactSurface.CHECKPOINT,
            path=payload_file,
            payload={"metadata": {"run_id": "r1"}},
        )
        == "r1"
    )
    digest = _content_addressed_file_snapshot_id(payload_file)
    assert digest.startswith("sha256:")
    missing = tmp_path / "gone.bin"
    assert _content_addressed_file_snapshot_id(missing).startswith("unreadable:")
    indexed = tmp_path / "_by_run_id" / "abc.json"
    indexed.parent.mkdir()
    indexed.write_text("{}", encoding="utf-8")
    assert _indexed_stem(indexed) == "abc"
    assert _indexed_stem(payload_file) is None
    assert _input_snapshot_ids(
        {
            "source_refs": [
                "x",
                {"input_snapshots": "no"},
                {"input_snapshots": ["y", {"snapshot_id": " s1 "}]},
            ]
        }
    ) == ("s1",)
    assert _lineage_fragment_id_candidates({"fragment_id": "f"}) == ("f",)
    assert _manifest_or_run_is_protected(
        {"manifest_id": "m"}, manifest_ids=frozenset({"m"}), run_ids=frozenset()
    )
    assert _resolve_lifecycle_reason(
        stale=True, protected_by=("evidence_floor:x",)
    ) == ("reproducibility_evidence_floor")
    assert _resolve_lifecycle_reason(stale=True, protected_by=("ref",)) == (
        "protected_reference"
    )
    assert _resolve_lifecycle_reason(stale=True, protected_by=()) == "retention_expired"
    assert _resolve_lifecycle_reason(stale=False, protected_by=()) == (
        "within_retention_window"
    )


def test_manifest_protection_helpers() -> None:
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
    payload = {
        "manifest_id": "m1",
        "run_id": "r1",
        "replay_of_manifest_id": "m0",
        "code_provenance": {"effective_config_artifact_id": "cfg", "contract_ref": "c"},
        "source_refs": [{"input_snapshots": [{"snapshot_id": "s1"}]}],
        "launch_context": {
            "required_persistence_profile": "strict",
            "execution_context": "composite",
        },
        "provider": "composite",
        "entity": "activity",
    }
    record_manifest_protections(
        path=Path("m1.json"),
        payload=payload,
        refs=refs,
        evidence_floor=True,
    )
    assert "m1" in refs.manifest_ids
    assert "m0" in refs.manifest_ids
    assert "r1" in refs.evidence_floor_run_ids
    assert required_persistence_profile(payload) == "strict"
    assert payload_execution_context(payload) == "composite"
    assert payload_execution_context({"provider": "composite"}) == "composite"
    assert payload_execution_context(
        {"launch_context": {"execution_context": "source"}}
    ) == ("source")
    assert supports_historical_replay_floor({"provider": None}) is False
    assert supports_historical_replay_floor({"provider": "chembl"}) is False
    assert requires_evidence_floor({"required_persistence_profile": ""}) is False


def test_exemptions_policy_and_validation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from bioetl.infrastructure.quality import exemptions_registry_policy as policy

    monkeypatch.setattr(
        policy, "load_exemptions_registry", lambda _path=None: {"registries": []}
    )
    assert validate_exemption_key_normalization() == ["registries: expected mapping"]
    monkeypatch.setattr(
        policy,
        "load_exemptions_registry",
        lambda _path=None: {"registries": {"file_size_limits": []}},
    )
    assert "file_size_limits" in validate_exemption_key_normalization()[0]
    monkeypatch.setattr(policy, "_project_root", lambda: tmp_path)
    monkeypatch.setattr(
        policy,
        "load_exemptions_registry",
        lambda _path=None: {
            "registries": {
                "file_size_limits": {
                    "": {},
                    "not-a-path": {},
                    "src/bioetl/missing.py": {},
                }
            }
        },
    )
    errors = validate_exemption_key_normalization()
    assert any("non-empty" in item for item in errors)
    assert any("canonical path" in item for item in errors)
    assert any("does not exist" in item for item in errors)

    metadata: list[str] = []
    fields = get_policy_required_fields({"policy": "bad"}, metadata)
    assert "owner" in fields
    metadata_ok: list[str] = []
    get_policy_required_fields({"policy": {"required_fields": []}}, metadata_ok)
    assert metadata_ok
    metadata_blank: list[str] = []
    get_policy_required_fields(
        {"policy": {"required_fields": [" ", "owner"]}}, metadata_blank
    )
    entry_errors: list[str] = []
    expired: list[str] = []
    validate_exemption_entry(
        "class_size",
        "todo",
        "not-a-map",
        fields,
        date(2026, 9, 17),
        entry_errors,
        expired,
    )
    validate_exemption_entry(
        "class_size",
        "LiveClass",
        {
            "owner": "unassigned",
            "classification": "nope",
            "linked_rf": "bad",
            "expires_on": "2020-01-01",
            "reason": " ",
        },
        fields,
        date(2026, 9, 17),
        entry_errors,
        expired,
    )
    assert expired
    validate_exemption_entry(
        "class_size",
        "LiveClass",
        {
            "owner": "team-a",
            "classification": "technical_debt",
            "linked_rf": "RF-001",
            "expires_on": "not-date",
            "reason": "x",
            "value": 1,
            "removal_step": "split",
        },
        fields,
        date(2026, 9, 17),
        entry_errors,
        expired,
    )
    monkeypatch.setattr(
        policy,
        "load_exemptions_registry",
        lambda _path=None: {"registries": "bad"},
    )
    meta, _expired = validate_exemptions_registry()
    assert meta


def test_quality_helpers_and_report_formatter(tmp_path: Path) -> None:
    errors: list[str] = []
    assert (
        _validate_registry_counts_mapping(field_name="x", raw_mapping={}, errors=errors)
        is None
    )
    counts = _validate_registry_counts_mapping(
        field_name="x",
        raw_mapping={"": 1, "ok": -1, "good": 2},
        errors=errors,
    )
    assert counts == {"good": 2}
    assert (
        _validate_baseline_mapping(field_name="b", baseline=[], errors=errors) is None
    )
    _validate_baseline_mapping(
        field_name="b",
        baseline={"total_exemptions": 3, "by_registry": {"a": 1, "c": 1}},
        errors=errors,
    )
    assert (
        _validate_registry_group_entry(group_name="g", group_data=[], errors=errors)
        is None
    )
    assert (
        _validate_registry_group_entry(
            group_name="g", group_data={"registries": []}, errors=errors
        )
        is None
    )
    grouped = _validate_registry_group_entry(
        group_name="g",
        group_data={"registries": ["a", " ", "a"]},
        errors=errors,
    )
    assert grouped is not None
    _validate_grouped_registry_coverage(list(grouped), {"a", "b"}, errors)
    assert _count_value(True) == 0
    assert _count_value(4) == 4
    assert _metric_policy({"m": 1}, "m") == {}
    tasks: list[dict[str, object]] = []
    _append_reviewed_metric_task(
        tasks,
        task_id="t",
        registry_key="k",
        policy={"target_count": True},
        current_value=9,
        limit_field="target_count",
        goal="g",
        notes=[],
    )
    assert tasks == []
    _append_reviewed_metric_task(
        tasks,
        task_id="t",
        registry_key="k",
        policy={"target_count": 1, "owner": "@x"},
        current_value=9,
        limit_field="target_count",
        goal="g",
        notes=["n"],
    )
    assert tasks[0]["status"] == "needs_refactor"
    assert artifact_defaults(tmp_path)["debt_scorecard"].name == "debt_scorecard.yaml"
    assert parse_limit_value({"value": 1.2}) == 1
    assert parse_limit_value({"value": "12"}) == 12
    assert parse_limit_value({"value": "n/a"}) == "n/a"
    assert parse_limit_value({"value": None}) is None
    assert safe_text(tmp_path / "missing.py") is None
    assert iter_source_modules(tmp_path) == []
    tree_src = "def f(x):\n    if x and x:\n        return [y for y in x if y]\n"
    tree = __import__("ast").parse(tree_src)
    fn = next(node for node in tree.body if getattr(node, "name", None) == "f")
    assert fallback_complexity(fn) >= 2
    complexities = function_complexities(tree_src)
    assert "f" in complexities
    today = date(2026, 9, 17)
    assert _extract_growth_violation_section(
        "registry 'file_size_limits' count 2 exceeds budget 1"
    ) == ("registry:file_size_limits")
    assert (
        _extract_growth_violation_section("group 'hot' count 2 exceeds budget 1")
        == "group:hot"
    )
    assert _extract_growth_violation_section("total exemptions 3 exceeds budget 1") == (
        "total_exemptions"
    )
    assert (
        _extract_growth_violation_section("integral debt score 0.1 is below target 0.9")
        == "integral_score"
    )
    assert _extract_growth_violation_section("other") == "unknown"
    assert _is_rollout_cutoff_stale("2020-01-01", today=today) is True
    assert _is_active_grace_window({"approved": True}, today=today) is False
    blocking, warning = split_growth_violations_by_severity(
        violations=["registry 'file_size_limits' count 2 exceeds budget 1", "other"],
        scorecard={
            "governance": {
                "growth_section_gate_rollout": {
                    "default_mode": "block",
                    "warn_until_by_section": {
                        "registry:file_size_limits": "2099-01-01",
                    },
                }
            }
        },
        today=today,
        fallback_mode="nope",
    )
    assert warning
    assert blocking == ["other"]
    assert (
        current_quarter_target(
            {"quarterly_targets": [{"quarter": "2099Q1"}]}, today=today
        )
        is None
    )
    allowances = resolve_grace_allowances(
        {
            "grace_windows": [
                {
                    "approved": True,
                    "starts_on": "2026-01-01",
                    "ends_on": "2026-12-31",
                    "allowances": {
                        "total_exemptions": 2,
                        "registry_budgets": {"a": 1},
                        "group_budgets": "bad",
                    },
                }
            ]
        },
        today,
    )
    assert allowances[1] == 2
    payload = tmp_path / "obj.json"
    payload.write_text("[]", encoding="utf-8")
    with pytest.raises(TypeError):
        _load_json(tmp_path, payload.name)
    yaml_path = tmp_path / "x.yaml"
    yaml_path.write_text("- 1\n", encoding="utf-8")
    assert _load_yaml(tmp_path, yaml_path.name) == {}
    assert _as_float("1.5") == 1.5
    with pytest.raises(TypeError):
        _as_float(None)


def test_composite_and_fk_schema_validators() -> None:
    with pytest.raises(ValidationError, match="empty column"):
        AggregationSchema.model_validate(
            {
                "group_by": "id",
                "order_by": [" "],
                "fields": {"x": {"source": "s", "agg": "first"}},
            }
        )
    with pytest.raises(ValidationError, match="duplicate"):
        AggregationSchema.model_validate(
            {
                "group_by": "id",
                "order_by": ["id", "id"],
                "fields": {"x": {"source": "s", "agg": "first"}},
            }
        )
    agg = AggregationSchema.model_validate(
        {"group_by": "id", "fields": {"x": {"source": "s", "agg": "first"}}}
    )
    assert agg.to_domain().group_by == "id"
    with pytest.raises(ValidationError, match="empty strings"):
        SeedSchema.model_validate(
            {"pipeline": "p", "output_keys": [" "], "silver_table": "t"}
        )
    seed = SeedSchema.model_validate(
        {"pipeline": "p", "output_keys": ["id"], "silver_table": "t"}
    )
    assert seed.to_domain().pipeline == "p"
    with pytest.raises(ValidationError, match="mutually exclusive"):
        DependencySchema.model_validate(
            {
                "pipeline": "p",
                "join_keys": ["id"],
                "filter_field": "a",
                "filter_fields": ["b"],
            }
        )
    dep = DependencySchema.model_validate(
        {"pipeline": "p", "join_keys": ["id"], "filter_fields": ["id"]}
    )
    assert dep.to_domain().filter_fields == ("id",)
    with pytest.raises(ValidationError, match="requires aggregation"):
        EnricherSchema.model_validate(
            {"pipeline": "p", "join_keys": ["id"], "cardinality": "many_to_one"}
        )
    enricher = EnricherSchema.model_validate(
        {
            "pipeline": "p",
            "join_keys": ["id"],
            "cardinality": "many_to_one",
            "aggregation": {
                "group_by": "id",
                "fields": {"x": {"source": "s", "agg": "first"}},
            },
        }
    )
    assert enricher.to_domain().aggregation is not None
    with pytest.raises(ValidationError, match="empty column"):
        MergeSortBySchema.model_validate({"silver": [" "], "gold": ["id"]})
    with pytest.raises(ValidationError, match="fields or pattern"):
        ColumnGroupSchema.model_validate({"name": "g"})
    with pytest.raises(ValidationError, match="positive"):
        TargetProteinClassificationProjectionSchema.model_validate({"levels": [0]})
    projection = TargetProteinClassificationProjectionSchema()
    mappings = projection.expand_field_mappings()
    assert "protein_classifications" in mappings.values()
    with pytest.raises(ValidationError, match="field_priorities"):
        MergeSchema.model_validate(
            {
                "conflict_resolution": "explicit_rules",
                "output": {"silver": "s", "gold": "g"},
                "sort_by": {"silver": ["id"], "gold": ["id"]},
            }
        )
    merge = MergeSchema.model_validate(
        {
            "output": {"silver": "s", "gold": "g"},
            "sort_by": {"silver": ["id"], "gold": ["id"]},
            "target_protein_classification_projection": {},
            "column_groups": [{"name": "g", "fields": ["id"]}],
        }
    )
    domain = merge.to_domain()
    assert "protein_classifications" in domain.field_mappings.values()
    with pytest.raises(ValueError, match="cannot be empty"):
        _normalize_fk_required_names([], "source_keys")
    with pytest.raises(ValueError, match="duplicates"):
        _normalize_fk_required_names(["id", "id"], "source_keys")
    assert _normalize_fk_optional_name(None, "source_key") is None
    with pytest.raises(ValueError, match="requires source_key/reference_key"):
        _require_fk_key_pairs_present(
            source_key=None, reference_key=None, source_keys=None, reference_keys=None
        )
    with pytest.raises(ValueError, match="together"):
        _require_fk_key_pairs_together(
            source_key="id", reference_key=None, source_keys=None, reference_keys=None
        )
    with pytest.raises(ValueError, match="same length"):
        _validate_fk_composite_alignment(
            source_key="id",
            reference_key="id",
            source_keys=["id"],
            reference_keys=["a", "b"],
        )
    with pytest.raises(ValueError, match="must match first"):
        _validate_fk_composite_alignment(
            source_key="id",
            reference_key="ref",
            source_keys=["other"],
            reference_keys=["ref"],
        )
    with pytest.raises(ValidationError):
        DQYamlConfig.model_validate(
            {"soft_fail_threshold": 2, "hard_fail_threshold": 0.1}
        )


def test_dq_loader_helpers_and_externalization(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="identity must be a mapping"):
        _resolve_identity_data({"identity": []}, contract_ref="c")
    assert _resolve_identity_data({"identity": {"x": 1}}, contract_ref="c") == {"x": 1}
    assert _resolve_threshold({"soft_fail_threshold": 0.2}, "soft_fail", 0.05) == 0.2
    assert (
        _resolve_threshold({"thresholds": {"soft_fail": 0.3}}, "soft_fail", 0.05) == 0.3
    )
    assert _resolve_threshold({}, "soft_fail", 0.05) == 0.05
    assert _resolve_contract_strict_dq_validation({"strict_validation": True}) is True
    assert (
        _resolve_contract_strict_dq_validation({"strict_dq_validation": False}) is False
    )
    with pytest.raises(ValueError, match="strictness"):
        _parse_strictness_mode("nope")
    assert _parse_strictness_mode("strict") == "strict"
    assert _parse_disposition_overrides(None) == {}
    report = _create_report_config({"enabled": False, "format": "yaml"})
    assert report.enabled is False
    _validate_identity_field(
        merged={"contract_version": "1"}, field_name="contract_version", expected="1"
    )
    with pytest.raises(ValueError, match="mismatch"):
        _validate_identity_field(
            merged={"contract_version": "2"},
            field_name="contract_version",
            expected="1",
        )
    raw: dict[str, object] = {"composite": "no"}
    merge_external_dq_overrides(raw, tmp_path / "cfg.yaml")
    raw = {"composite": {"dq_overrides": "no"}}
    merge_external_dq_overrides(raw, tmp_path / "cfg.yaml")
    raw = {"composite": {"dq_overrides": {"dq_config_file": " "}}}
    merge_external_dq_overrides(raw, tmp_path / "cfg.yaml")
    cfg = tmp_path / "cfg.yaml"
    cfg.write_text("composite: {}\n", encoding="utf-8")
    with pytest.raises(FileNotFoundError):
        merge_external_dq_overrides(
            {"composite": {"dq_overrides": {"dq_config_file": "missing.yaml"}}},
            cfg,
        )
    dq = tmp_path / "dq.yaml"
    dq.write_text("- 1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="mapping"):
        merge_external_dq_overrides(
            {"composite": {"dq_overrides": {"dq_config_file": "dq.yaml"}}},
            cfg,
        )
    dq.write_text("dq_overrides: []\n", encoding="utf-8")
    with pytest.raises(ValueError, match="dq_overrides"):
        merge_external_dq_overrides(
            {"composite": {"dq_overrides": {"dq_config_file": "dq.yaml"}}},
            cfg,
        )
    dq.write_text("dq_overrides:\n  a: 1\n  nested:\n    x: 1\n", encoding="utf-8")
    payload = {
        "composite": {"dq_overrides": {"dq_config_file": "dq.yaml", "nested": {"y": 2}}}
    }
    merge_external_dq_overrides(payload, cfg)
    assert payload["composite"]["dq_overrides"]["nested"] == {"x": 1, "y": 2}
    merge_external_shared_policy({"composite": {}}, cfg)
    merge_external_shared_policy({"composite": {}, "maintenance": {}}, cfg)
    with pytest.raises(FileNotFoundError):
        merge_external_shared_policy(
            {
                "composite": {"keep": 1},
                "maintenance": {"composite_shared_policy_file": "missing.yaml"},
            },
            cfg,
        )
    policy = tmp_path / "policy.yaml"
    policy.write_text("- 1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="mapping"):
        merge_external_shared_policy(
            {
                "composite": {"keep": 1},
                "maintenance": {"composite_shared_policy_file": "policy.yaml"},
            },
            cfg,
        )
    policy.write_text("shared: 1\n", encoding="utf-8")
    shared = {
        "composite": {"keep": 1},
        "maintenance": {"composite_shared_policy_file": "policy.yaml"},
    }
    merge_external_shared_policy(shared, cfg)
    assert shared["composite"]["shared"] == 1


def test_reason_enum_and_publication_loaders(tmp_path: Path) -> None:
    assert load_reason_catalog_from_text("- 1") is None
    assert load_reason_catalog_from_text("{[") is None
    assert load_reason_catalog_from_path(tmp_path / "missing.yaml") is None
    catalog = load_default_reason_catalog()
    assert catalog is not None
    with pytest.raises(ValueError, match="blank"):
        load_provider_enums_from_file(" ")
    with pytest.raises(ValueError, match="path separators"):
        load_provider_enums_from_file("a/b")
    empty = tmp_path / "empty.yaml"
    empty.write_text("", encoding="utf-8")
    assert load_provider_enums_from_file("chembl", empty) == {}
    listed = tmp_path / "list.yaml"
    listed.write_text("- 1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="mapping"):
        load_provider_enums_from_file("chembl", listed)
    mapped = tmp_path / "map.yaml"
    mapped.write_text("flags:\n  - a\n  - b\n", encoding="utf-8")
    loaded = load_provider_enums_from_file("chembl", mapped)
    assert loaded["flags"] == ["a", "b"]
    frozen = load_chembl_enums_from_file(mapped)
    assert frozen["flags"] == ["a", "b"]
    loader = PublicationControlledVocabularyLoader(tmp_path)
    assert loader.load().allowed_values_by_field == {}
    vocab = tmp_path / "vocab"
    vocab.mkdir()
    (vocab / "publication_controlled.yaml").write_text(
        yaml.safe_dump(
            {
                "providers": {
                    1: {},
                    "chembl": {
                        1: {},
                        "ptype": {
                            "preserve_unknown": False,
                            "values": ["A"],
                        },
                        "status": {
                            "values": ["  Open  ", 1],
                            "inherits": "shared.status",
                        },
                    },
                },
                "shared": {"status": {"values": ["Closed", "  "]}},
            }
        ),
        encoding="utf-8",
    )
    registry = loader.load()
    assert ("chembl", "status") in registry.allowed_values_by_field
    (vocab / "publication_controlled.yaml").write_text("[]", encoding="utf-8")
    assert loader.load().allowed_values_by_field == {}


def test_observability_probes_and_label_normalizers() -> None:
    class _Resp(AbstractContextManager[Any]):
        def __init__(self, status: int) -> None:
            self.status = status

        def __exit__(self, *args: object) -> None:
            return None

    def ok(url: str, *, timeout: float) -> _Resp:
        del timeout
        return _Resp(200 if "live" in url or url.endswith("/ready") else 500)

    assert probe_observability_backend("http://x/health", urlopen_fn=ok) is True
    assert probe_observability_backend("http://x/other", urlopen_fn=ok) is False

    def boom(url: str, *, timeout: float) -> _Resp:
        del url, timeout
        raise URLError("down")

    assert probe_observability_backend("http://x/health", urlopen_fn=boom) is False
    assert probe_observability_backend_required_paths(
        "http://x/health", required_probe_paths=()
    )
    assert probe_observability_backend_required_paths(
        "http://x/health",
        required_probe_paths=("ready",),
        urlopen_fn=ok,
    )
    assert (
        probe_observability_backend_required_paths(
            "http://x/health",
            required_probe_paths=("/missing",),
            urlopen_fn=ok,
        )
        is False
    )
    assert (
        probe_observability_backend_required_paths(
            "http://x/health",
            required_probe_paths=("/ready",),
            urlopen_fn=boom,
        )
        is False
    )
    calls = {"n": 0}

    def later(url: str) -> bool:
        calls["n"] += 1
        return calls["n"] > 1

    assert (
        wait_for_observability_backend_ready(
            "http://x/health",
            timeout_seconds=1.0,
            poll_seconds=0.0,
            probe_fn=later,
            sleep_fn=lambda _s: None,
        )
        is True
    )
    assert wait_for_observability_backend_required_paths_ready(
        "http://x/health",
        required_probe_paths=(),
    )
    required_calls = {"n": 0}

    def later_required(url: str, **_kwargs: object) -> bool:
        required_calls["n"] += 1
        return required_calls["n"] > 1

    assert wait_for_observability_backend_required_paths_ready(
        "http://x/health",
        required_probe_paths=("/ready",),
        timeout_seconds=1.0,
        poll_seconds=0.0,
        required_probe_fn=later_required,
        sleep_fn=lambda _s: None,
    )
    assert normalize_adapter_endpoint_label("") == "/unknown"
    assert normalize_adapter_endpoint_label("/") == "/"
    deep = "/a/" + "/".join("seg" for _ in range(10))
    assert normalize_adapter_endpoint_label(deep).endswith("{param}")
    assert normalize_source_file_label("") == "unknown"
    assert normalize_source_file_label("C:\\tmp\\file.csv") == "csv_file"
    assert normalize_source_file_label("notes") == "extensionless_file"
    assert normalize_source_file_label("x.zzz") == "other_file"
    assert normalize_quarantine_reason("nope") == "other"
    sanitized = _sanitize_pushgateway_grouping_key(
        {"pipeline": " Chembl ", "run_type": "", "ignored": "x"}
    )
    assert sanitized == {"pipeline": "chembl"}
    assert _sanitize_pushgateway_grouping_key(None) == {}
    metric = SimpleNamespace(labels=lambda **_k: SimpleNamespace(inc=lambda: None))
    registry = SimpleNamespace(restricted_registry=lambda names: names)

    def push(*_a: object, **_k: object) -> None:
        return None

    assert publish_metrics_to_gateway(
        registry=registry,  # type: ignore[arg-type]
        push_gateway=push,
        publication_metric=metric,  # type: ignore[arg-type]
        grouping_key={"pipeline": "p", "run_type": "incremental"},
        metric_names=("m",),
    )


def test_run_ledger_helpers(tmp_path: Path) -> None:
    from bioetl.domain.control_plane.run_ledger import (
        RUN_FAILED_EVENT,
        RUN_FINISHED_EVENT,
        RUN_SHUTDOWN_EVENT,
    )

    assert resolve_ledger_pipeline(SimpleNamespace(details=None)) == "unknown"
    assert (
        resolve_ledger_pipeline(SimpleNamespace(details={"_diagnostic": []}))
        == "unknown"
    )
    assert (
        resolve_ledger_pipeline(
            SimpleNamespace(details={"_diagnostic": {"pipeline": "  "}})
        )
        == "unknown"
    )
    assert (
        resolve_ledger_pipeline(
            SimpleNamespace(details={"_diagnostic": {"pipeline": "chembl_activity"}})
        )
        == "chembl_activity"
    )
    emit_ledger_append_metric(None, pipeline="p", event_type="e", status="success")
    emit_ledger_append_duration_metric(
        None, pipeline="p", event_type="e", status="ok", duration_seconds=0.1
    )
    emit_terminal_event_metric(None, pipeline="p", event_type="other")
    metrics = SimpleNamespace(
        increment_counter=lambda *a, **k: None, observe_histogram=lambda *a, **k: None
    )
    emit_ledger_append_metric(metrics, pipeline="p", event_type="e", status="success")  # type: ignore[arg-type]
    emit_ledger_append_duration_metric(
        metrics,
        pipeline="p",
        event_type="e",
        status="ok",
        duration_seconds=0.1,  # type: ignore[arg-type]
    )
    emit_terminal_event_metric(metrics, pipeline="p", event_type=RUN_FINISHED_EVENT)  # type: ignore[arg-type]
    emit_terminal_event_metric(metrics, pipeline="p", event_type=RUN_FAILED_EVENT)  # type: ignore[arg-type]
    emit_terminal_event_metric(metrics, pipeline="p", event_type=RUN_SHUTDOWN_EVENT)  # type: ignore[arg-type]
    assert has_idempotent_duplicate([], idempotency_key=None) is False
    entry = SimpleNamespace(
        idempotency_key="k", manifest_id="m", run_id=RunID(UUID(int=1))
    )
    assert has_idempotent_duplicate([entry], idempotency_key="k") is True  # type: ignore[arg-type]
    ensure_entries_match_manifest_and_run_identity(entries=[], manifest_id="m")
    with pytest.raises(RunLedgerCorruptionError, match="different manifest_id"):
        ensure_entries_match_manifest_and_run_identity(
            entries=[SimpleNamespace(manifest_id="other", run_id=RunID(UUID(int=1)))],  # type: ignore[list-item]
            manifest_id="m",
        )
    with pytest.raises(RunLedgerCorruptionError, match="multiple run_id"):
        ensure_entries_match_manifest_and_run_identity(
            entries=[
                SimpleNamespace(manifest_id="m", run_id=RunID(UUID(int=1))),  # type: ignore[list-item]
                SimpleNamespace(manifest_id="m", run_id=RunID(UUID(int=2))),  # type: ignore[list-item]
            ],
            manifest_id="m",
        )
    run_id = RunID(UUID(int=1))
    with pytest.raises(RunLedgerCorruptionError, match="run-id index"):
        ensure_entries_match_run_index(
            entries=[SimpleNamespace(manifest_id="other", run_id=run_id)],  # type: ignore[list-item]
            manifest_id="m",
            run_id=run_id,
        )
    with pytest.raises(RunLedgerCorruptionError, match="different run_id"):
        ensure_entries_match_run_index(
            entries=[SimpleNamespace(manifest_id="m", run_id=RunID(UUID(int=2)))],  # type: ignore[list-item]
            manifest_id="m",
            run_id=run_id,
        )
    assert (
        iter_jsonl_payloads_strict(ledger_path=tmp_path / "l.jsonl", raw_text="  ")
        == []
    )
    with pytest.raises(RunLedgerCorruptionError, match="truncated"):
        iter_jsonl_payloads_strict(ledger_path=tmp_path / "l.jsonl", raw_text="{}\n{")
    with pytest.raises(RunLedgerCorruptionError, match="JSON object"):
        iter_jsonl_payloads_strict(ledger_path=tmp_path / "l.jsonl", raw_text="[]\n")
    with pytest.raises(RunLedgerCorruptionError, match="corrupted at line"):
        iter_jsonl_payloads_strict(ledger_path=tmp_path / "l.jsonl", raw_text="{no}\n")
    payloads = iter_jsonl_payloads_strict(
        ledger_path=tmp_path / "l.jsonl", raw_text='{}\n\n{"a": 1}\n'
    )
    assert payloads[-1]["a"] == 1
