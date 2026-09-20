"""Stream A domain coverage for #10469 / #10519 (4-line and 3-line leftovers)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from bioetl.domain.composite.aggregation_filters import (
    _try_comparison_operator,
    _validate_aggregation_filter_condition,
)
from bioetl.domain.composite.config_merge import ColumnGroupConfig, MergeConfig
from bioetl.domain.composite.strategy import ConflictResolution, MergeStrategy
from bioetl.domain.control_plane._run_ledger_runtime import (
    STAGE_STARTED_EVENT,
    RunLedgerEntry,
    canonicalize_run_ledger_stage_name,
    slice_ledger_entries_after,
)
from bioetl.domain.control_plane._run_manifest_deserialization import (
    _load_object_mapping,
    _load_replay_capability,
    _load_source_refs,
    _require_key,
)
from bioetl.domain.control_plane.contract_registry_service import ContractRegistry
from bioetl.domain.entities.chembl_structures_foundation import (
    _validate_target_protein_classification_resolution,
    _validate_target_protein_classification_status,
)
from bioetl.domain.error_classifier import ErrorClassifier
from bioetl.domain.exceptions.base import BioETLError, RecoverableError
from bioetl.domain.exceptions.bounded_context import (
    DomainExceptionContext,
    get_domain_exception_context,
)
from bioetl.domain.exceptions.storage._storage import StorageQuotaExceededError
from bioetl.domain.exceptions.validation import ValidationError
from bioetl.domain.mapping.publication_type_classification import is_initialized
from bioetl.domain.normalization._control_plane_payloads import (
    build_control_plane_idempotency_key,
    normalize_run_ledger_payload,
    normalize_run_manifest_spec,
)
from bioetl.domain.normalization._reference_id_ncbi_taxonomy import (
    normalize_ncbi_taxonomy_reference_id,
)
from bioetl.domain.normalization.dates import format_date_parts, parse_date_field
from bioetl.domain.normalization.profiles._normalization_helpers import (
    _identity,
    _normalizer_accepts_record_context,
    _normalizer_ref,
    _stable_value,
)
from bioetl.domain.normalization.profiles._profile_ontology_companion_normalizers import (
    _normalize_mapping_status,
    _record_string,
    build_obo_companion_iri_normalizer,
)
from bioetl.domain.normalization.profiles._profile_publication_normalizers import (
    normalize_profile_chembl_publication_classification_field,
    normalize_profile_publication_type_raw,
    normalize_profile_semantic_scholar_publication_type_raw,
)
from bioetl.domain.normalization.profiles._profile_textual_normalizers import (
    normalize_profile_canonical_smiles,
    normalize_profile_json_string,
    normalize_profile_json_string_strict,
    normalize_profile_json_string_unordered_collection,
    normalize_profile_smiles,
    normalize_profile_text,
)
from bioetl.domain.normalization.profiles.chembl_activity import create_case_normalizer
from bioetl.domain.normalization.reference_ids import (
    normalize_uniprot_mixed_mapping_reference_id,
)
from bioetl.domain.normalization.rules import (
    _apply_case_strategy,
    normalize_cross_pipeline_case,
)
from bioetl.domain.ports.export import ExportFileFingerprint
from bioetl.domain.ports.workflow_row_reconciliation import (
    RowReconciliationConfig,
    RowReconciliationConfigError,
    RowReconciliationLayer,
)
from bioetl.domain.registry.semantic_fields import (
    SemanticFieldCluster,
    SemanticFieldRegistry,
)
from bioetl.domain.run_reports.accounting import StageAccountingAccumulator
from bioetl.domain.run_reports.accounting_snapshots import (
    _is_degraded_balance,
    _is_unknown_balance,
    _prefer_mapped_count,
)
from bioetl.domain.run_reports.models import (
    BalanceStatus,
    StageFunnelRow,
    TrackingCoverage,
)
from bioetl.domain.types import RunID, RunType
from bioetl.domain.types.gold_schema_policy import (
    GoldSchemaPolicyByVersion,
    GoldSchemaVersionPolicy,
)
from bioetl.domain.value_objects._publication_field_group_config import FieldGroupConfig
from bioetl.domain.value_objects._run_context_create_support import (
    coerce_run_context_create_input,
)
from bioetl.domain.value_objects.activity_concentration import (
    Concentration,
    ConcentrationUnit,
)
from bioetl.domain.value_objects.compound_ids import AssayId, CompoundId
from bioetl.domain.value_objects.dq_report_enums import DQCheckStatus
from bioetl.domain.value_objects.dq_report_results_quality import CompletenessResult
from bioetl.domain.value_objects.identifiers import PubChemCid, UniProtId
from bioetl.domain.value_objects.publication_field_group_types import (
    PublicationFieldGroup,
)

pytestmark = pytest.mark.unit


def _cluster(
    cluster_id: str,
    canonical: str,
    *,
    legacy: tuple[str, ...] = (),
) -> SemanticFieldCluster:
    return SemanticFieldCluster(
        cluster_id=cluster_id,
        semantic_name=canonical,
        canonical_name=canonical,
        legacy_names=legacy,
        raw_provider_names=(),
        pipelines=("activity",),
        affected_paths=("p",),
        migration_status="done",
        notes="",
    )


def test_control_plane_payloads_and_normalization_helpers() -> None:
    spec = normalize_run_manifest_spec(
        {
            "code_provenance": {
                "config_hash": "abc",
                "contract_ref": "  c  ",
                "contract_version": " 1 ",
                "effective_config_artifact_id": "  ",
            },
            "source_refs": [
                {
                    "name": "chembl",
                    "input_snapshots": [{"snapshot_id": "b"}, {"snapshot_id": "a"}],
                }
            ],
            "planned_artifacts": ["gold", "silver"],
        }
    )
    assert spec["code_provenance"]["effective_config_artifact_id"] is None
    ledger = normalize_run_ledger_payload(
        {
            "run_id": str(uuid4()),
            "occurred_at": "2026-01-01T00:00:00+00:00",
            "metrics_snapshot": {"n": 1},
            "details": {"k": "v"},
        }
    )
    assert ledger["metrics_snapshot"]["n"] == 1
    key = build_control_plane_idempotency_key({"a": 1, "b": 2}, fields=("a", "b"))
    assert key.startswith("sha256:")
    assert _normalizer_accepts_record_context(_identity) is False
    assert _normalizer_accepts_record_context(len) is False

    def _with_record(value: object, *, record: object = None) -> object:
        del record
        return value

    assert _normalizer_accepts_record_context(_with_record) is True
    assert ":" in _normalizer_ref(_identity)
    with pytest.raises(TypeError, match="lambda"):
        _normalizer_ref(lambda value: value)
    assert _stable_value(b"ab") == "6162"
    assert _stable_value({2, 1}) == [1, 2]
    assert _stable_value({"b": 1, "a": 2}) == {"a": 2, "b": 1}
    assert _stable_value(_identity)["qualname"] == "_identity"


def test_textual_snapshots_schema_publication_compound_and_dq() -> None:
    assert normalize_profile_text(1) == 1
    assert normalize_profile_json_string("{") == "{"
    assert normalize_profile_json_string_strict("{") is None
    ordered = normalize_profile_json_string_unordered_collection(["b", "a"])
    assert ordered == '["a","b"]'
    assert normalize_profile_json_string_unordered_collection(1) == 1
    assert normalize_profile_smiles(None, is_canonical=True) is None
    assert normalize_profile_canonical_smiles(123) is None
    acc = StageAccountingAccumulator()
    assert acc.overall_tracking_coverage(()) is TrackingCoverage.NOT_TRACKED
    full = StageFunnelRow(
        stage_id="gold",
        records_in=1,
        records_out=1,
        removed_total=0,
        removals=(),
        balance_status=BalanceStatus.OK,
        tracking=TrackingCoverage.FULL,
    )
    mixed = StageFunnelRow(
        stage_id="silver",
        records_in=1,
        records_out=1,
        removed_total=0,
        removals=(),
        balance_status=BalanceStatus.OK,
        tracking=TrackingCoverage.PARTIAL,
    )
    assert acc.overall_tracking_coverage((full,)) is TrackingCoverage.FULL
    assert acc.overall_tracking_coverage((full, mixed)) is TrackingCoverage.PARTIAL
    assert _prefer_mapped_count(None, 7) == 7
    assert _prefer_mapped_count(0, 7) == 0
    assert _is_unknown_balance(0, TrackingCoverage.NOT_TRACKED) is True
    assert _is_degraded_balance(1, TrackingCoverage.PARTIAL) is True
    with pytest.raises(ValueError, match="cannot be empty"):
        GoldSchemaVersionPolicy(version=" ", schema={})
    with pytest.raises(ValueError, match="cannot be None"):
        GoldSchemaVersionPolicy(version="v1", schema=None)
    v1 = GoldSchemaVersionPolicy(version="v1", schema={"a": 1})
    v2 = GoldSchemaVersionPolicy(version="v2", schema={"a": 2})
    policy = GoldSchemaPolicyByVersion(active_version="v1", policies=(v1, v2))
    assert policy.active_schema == {"a": 1}
    assert policy.for_version("missing") is None
    assert policy.is_multi_version is True
    with pytest.raises(ValueError, match="duplicate"):
        GoldSchemaPolicyByVersion(active_version="v1", policies=(v1, v1))
    cfg = FieldGroupConfig()
    assert cfg.get_group("unknown") is PublicationFieldGroup.TRASH
    assert cfg.get_provider_rank("title") == -1
    assert cfg.get_provider_rank("other.publication.title") == 999
    ranked = cfg.sort_columns(["chembl.publication.title", "title"])
    assert "title" in ranked
    cid = CompoundId.from_raw("CHEMBL25", "chembl")
    assert cid.is_chembl is True and cid.numeric_id == 25
    pub = CompoundId.from_pubchem(2244)
    assert pub.is_pubchem is True and str(pub).startswith("pubchem:")
    object.__setattr__(cid, "_validated_id", None)
    with pytest.raises(ValueError, match="not properly validated"):
        _ = cid.numeric_id
    with pytest.raises(ValueError):
        AssayId("not-an-assay")
    frozen = CompletenessResult(
        required_fields={"a": 1.0},
        overall_completeness_score=1.0,
        minimum_threshold=0.5,
        status=DQCheckStatus.PASS,
        reject_reasons=[],  # type: ignore[arg-type]
    )
    assert frozen.reject_reasons == ()


def test_three_line_filters_merge_ledger_manifest_and_registry() -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        _validate_aggregation_filter_condition("  ")
    with pytest.raises(ValueError, match="invalid field"):
        _validate_aggregation_filter_condition("1field IS NULL")
    with pytest.raises(ValueError, match="trailing text"):
        _validate_aggregation_filter_condition("x IS NULL extra")
    with pytest.raises(ValueError, match="requires a value"):
        _try_comparison_operator("x == ", " == ")
    with pytest.raises(ValueError, match="additional operators"):
        _validate_aggregation_filter_condition("x == a OR b")
    _validate_aggregation_filter_condition("x == 'a OR b'")
    with pytest.raises(ValueError, match="unsupported syntax"):
        _validate_aggregation_filter_condition("x > 1")
    with pytest.raises(ValueError, match="fields or pattern"):
        ColumnGroupConfig(name="empty")
    with pytest.raises(ValueError, match="invalid pattern"):
        ColumnGroupConfig(name="bad", pattern="(")
    with pytest.raises(ValueError, match="cannot be empty"):
        MergeConfig(
            strategy=MergeStrategy.LEFT_OUTER,
            conflict_resolution=ConflictResolution.SEED_PRIORITY,
            output_silver_path="",
            output_gold_path="gold",
        )
    with pytest.raises(ValueError, match="field_priorities required"):
        MergeConfig(
            strategy=MergeStrategy.LEFT_OUTER,
            conflict_resolution=ConflictResolution.EXPLICIT_RULES,
            output_silver_path="silver",
            output_gold_path="gold",
        )
    with pytest.raises(ValueError, match="Unsupported run-ledger stage"):
        canonicalize_run_ledger_stage_name("not-a-stage")
    entry = RunLedgerEntry(
        entry_id="e1",
        manifest_id="m",
        run_id=RunID(uuid4()),
        event_type="  ",
        occurred_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert entry.event_type == "unknown_event"
    with pytest.raises(ValueError, match="was not found"):
        slice_ledger_entries_after([entry], "missing")
    assert slice_ledger_entries_after([entry], None) == (entry,)
    with pytest.raises(ValueError, match="expected one of"):
        RunLedgerEntry(
            entry_id="e2",
            manifest_id="m",
            run_id=RunID(uuid4()),
            event_type=STAGE_STARTED_EVENT,
            occurred_at=datetime(2026, 1, 1, tzinfo=UTC),
            stage="nope",
        )
    with pytest.raises(ValueError, match="Missing required field"):
        _require_key({}, "id", context="src")
    assert _load_source_refs("x", source_ref_type=dict, snapshot_ref_type=dict) == ()
    with pytest.raises(ValueError, match="must be an object"):
        _load_source_refs([1], source_ref_type=dict, snapshot_ref_type=dict)
    assert _load_object_mapping("x") == {}
    assert (
        _load_replay_capability(None, capability_type=str, rebuild_only="rebuild")
        == "rebuild"
    )
    with pytest.raises(ValueError, match="missing 'entries'"):
        ContractRegistry.from_dict({})
    with pytest.raises(ValueError, match="Invalid entry payload"):
        ContractRegistry.from_dict({"entries": {"c": 1}})
    with pytest.raises(ValueError, match="Invalid protein classification"):
        _validate_target_protein_classification_status("nope")
    with pytest.raises(ValueError, match="require component_id"):
        _validate_target_protein_classification_resolution(
            classification_status="resolved",
            component_id=None,
            leaf_id=1,
        )
    _validate_target_protein_classification_resolution(
        classification_status="quarantined",
        component_id=None,
        leaf_id=None,
    )


def test_three_line_errors_ids_dates_export_and_context() -> None:
    classifier = ErrorClassifier(strict_mode=True)
    assert (
        classifier.classify(type("RateLimitError", (Exception,), {})("x")) is not None
    )
    with pytest.raises(ValueError, match="Unknown exception type"):
        classifier.classify(RuntimeError("x"))
    classifier.reset_fallback_count()
    assert classifier.fallback_usage_count == 0
    assert classifier.classify(BioETLError("x")) is not None
    assert (
        get_domain_exception_context(RecoverableError("x"))
        is DomainExceptionContext.EXTERNAL_INTEGRATION
    )
    assert (
        get_domain_exception_context(ValidationError("x"))
        is DomainExceptionContext.VALIDATION
    )
    assert get_domain_exception_context(BioETLError) is DomainExceptionContext.PLATFORM
    quota = StorageQuotaExceededError(path="/tmp", quota_bytes=10, used_bytes=11)
    assert quota.quota_bytes == 10
    delta = StorageQuotaExceededError(table_path="t", reason="conflict", version=3)
    assert delta.reason == "conflict"
    legacy = StorageQuotaExceededError("t", "conflict", 4)
    assert legacy.reason == "conflict" and legacy.version == 4
    assert isinstance(is_initialized(), bool)
    assert normalize_ncbi_taxonomy_reference_id(0) == "0"
    assert normalize_ncbi_taxonomy_reference_id(9606.0) == 9606
    assert normalize_ncbi_taxonomy_reference_id(1.5) == 1.5
    assert format_date_parts(None) is None
    assert format_date_parts([[2020, 1, 2]]) == "2020-01-02"
    assert parse_date_field(None) is None
    assert parse_date_field("2020/01/02", "%Y/%m/%d") is not None
    assert parse_date_field("bad", "%Y/%m/%d") is None
    assert _record_string(None, "x") is None
    assert _record_string({"x": 1}, "x") is None
    assert _normalize_mapping_status(1) is None
    iri_fn = build_obo_companion_iri_normalizer(
        source_field="uo_id",
        canonical_prefix="UO",
        ontology_version="v1",
    )
    assert iri_fn("ignored") is None
    normalize_profile_chembl_publication_classification_field(
        None,
        field_name="unified_type",
        record={"publication_type_raw": "Journal"},
    )
    assert normalize_profile_publication_type_raw(1) is None
    assert normalize_profile_semantic_scholar_publication_type_raw("Review") == "Review"
    with pytest.raises(ValidationError, match="Unknown case strategy"):
        _apply_case_strategy("x", "weird")
    assert create_case_normalizer("lowercase")("Ab") == "ab"
    assert normalize_cross_pipeline_case(None) is None  # type: ignore[arg-type]
    mixed = normalize_uniprot_mixed_mapping_reference_id("chembl25")
    assert mixed == "CHEMBL25" or mixed == "chembl25"
    with pytest.raises(ValueError, match="size_bytes"):
        ExportFileFingerprint(path="p", size_bytes=-1, sha256="a" * 64)
    with pytest.raises(ValueError, match="64-character"):
        ExportFileFingerprint(path="p", size_bytes=1, sha256="zz")
    digest = ExportFileFingerprint(path="p", size_bytes=1, sha256=("A" * 64))
    assert digest.sha256 == "a" * 64
    with pytest.raises(RowReconciliationConfigError, match="cannot be empty"):
        RowReconciliationConfig(
            layer=RowReconciliationLayer.SILVER,
            left_table="l",
            right_table="r",
            left_columns=(),
            right_columns=(),
            left_primary_keys=("id",),
        )
    with pytest.raises(RowReconciliationConfigError, match="same length"):
        RowReconciliationConfig(
            layer="silver",
            left_table="l",
            right_table="r",
            left_columns=("a",),
            right_columns=("a", "b"),
            left_primary_keys=("id",),
        )
    with pytest.raises(ValueError, match="duplicate cluster_id"):
        SemanticFieldRegistry((_cluster("c1", "n1"), _cluster("c1", "n2")))
    with pytest.raises(ValueError, match="duplicate canonical_name"):
        SemanticFieldRegistry((_cluster("c1", "same"), _cluster("c2", "same")))
    with pytest.raises(ValueError, match="duplicate legacy_name"):
        SemanticFieldRegistry(
            (
                _cluster("c1", "n1", legacy=("old",)),
                _cluster("c2", "n2", legacy=("old",)),
            )
        )
    started = datetime(2026, 1, 1, tzinfo=UTC)
    created = coerce_run_context_create_input(
        None,
        {
            "run_id": UUID("00000000-0000-0000-0000-000000000001"),
            "run_type": RunType.INCREMENTAL,
            "started_at": started,
            "provider": "chembl",
            "entity": "activity",
            "transform_steps": ["a"],
        },
    )
    assert created.transform_steps == ("a",)
    with pytest.raises(TypeError, match="missing required"):
        coerce_run_context_create_input(None, {})
    with pytest.raises(ValueError, match="Unknown concentration unit"):
        ConcentrationUnit.from_string("kg")
    with pytest.raises(TypeError, match="must be numeric"):
        Concentration(value=True, unit=ConcentrationUnit.NANOMOLAR)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="Cannot parse"):
        Concentration.from_string("nope")
    with pytest.raises(ValueError, match="must be str"):
        UniProtId(123)  # type: ignore[arg-type]
    assert UniProtId.from_raw("bad") is None
    with pytest.raises(ValueError, match="must be int"):
        PubChemCid(True)  # type: ignore[arg-type]
    assert PubChemCid.from_raw(0) is None
