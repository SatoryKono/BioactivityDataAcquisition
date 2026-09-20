"""Stream A leftover domain coverage (#10469): normalization through value objects."""

from __future__ import annotations

import builtins
import importlib
import math
import sys
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

import bioetl.domain.normalization.json as json_normalization
import bioetl.domain.serialization as serialization_mod
from bioetl.domain.medallion import Layer
from bioetl.domain.normalization._chembl_organisms import (
    _strip_trailing_parenthetical_annotation,
    normalize_chembl_organism_name,
)
from bioetl.domain.normalization._control_plane_identity import (
    _normalize_bool_text_token,
)
from bioetl.domain.normalization._control_plane_payloads import (
    _manifest_snapshot_sort_key,
    _normalize_manifest_source_ref,
    _normalize_manifest_source_refs_field,
    _normalize_optional_text,
)
from bioetl.domain.normalization._reference_id_ncbi_taxonomy import (
    _normalize_ncbi_taxonomy_text,
    _normalize_ncbi_taxonomy_textual,
)
from bioetl.domain.normalization._reference_id_support import (
    _json_fallback,
    _normalize_openalex_candidate,
)
from bioetl.domain.normalization.dates import (
    _normalize_partial_month,
    _parse_year_month,
)
from bioetl.domain.normalization.profiles._normalization_helpers import (
    _normalizer_accepts_record_context,
    _require_stable_normalizer_identity,
    _stable_primitive,
)
from bioetl.domain.normalization.profiles._profile_ontology_companion_normalizers import (
    _normalize_mapping_status,
)
from bioetl.domain.normalization.profiles._profile_publication_normalizers import (
    normalize_profile_publication_type,
    normalize_profile_semantic_scholar_publication_type_raw,
)
from bioetl.domain.normalization.profiles._profile_textual_normalizers import (
    _parse_unordered_json_string,
    _serialize_unordered_json_collection,
    normalize_profile_json_string,
    normalize_profile_json_string_strict,
)
from bioetl.domain.normalization.profiles._profile_value_normalizers import (
    _UNHANDLED,
    _coerce_profile_float,
    _coerce_profile_int_text,
    _finalize_profile_float,
    _parse_json_string_list,
)
from bioetl.domain.normalization.profiles._standard_profile_rule_components import (
    _bound_case_normalizer,
)
from bioetl.domain.normalization.reference_ids import (
    normalize_doi_reference_id,
    normalize_pmid_reference_id,
    normalize_uniprot_mixed_mapping_reference_id,
)
from bioetl.domain.normalization.rules import normalize_boolean, normalize_operator
from bioetl.domain.ports.workflow_row_reconciliation import (
    RowReconciliationConfig,
    RowReconciliationConfigError,
    RowReconciliationLayer,
    _normalize_workflow_name,
    _required_name,
)
from bioetl.domain.registry.semantic_fields import (
    SemanticFieldCluster,
    SemanticFieldRegistry,
)
from bioetl.domain.run_reports._stage_bucket import _StageBucket
from bioetl.domain.run_reports.accounting import StageAccountingAccumulator
from bioetl.domain.run_reports.models import TrackingCoverage, WorkflowExecutionRow
from bioetl.domain.run_reports.reason_catalog import ReasonCatalog
from bioetl.domain.run_reports.workflow_builder import _payload_mapping
from bioetl.domain.run_reports.workflow_totals import _measured_current
from bioetl.domain.types._gold_contracts_support import (
    normalize_column_name,
    normalize_optional_text,
)
from bioetl.domain.types.gold_contracts_rejects import (
    _extract_version_from_standard_attributes,
    _known_contract_version_or_none,
    _resolve_version_from_schema,
    normalize_reason_code,
)
from bioetl.domain.types.gold_schema_policy import (
    GoldSchemaPolicyByVersion,
    GoldSchemaVersionPolicy,
)
from bioetl.domain.value_objects._publication_field_group_config import FieldGroupConfig
from bioetl.domain.value_objects._run_context_create_support import (
    _optional_str_value,
    _require_value,
    _run_id_value,
)
from bioetl.domain.value_objects.activity_concentration import (
    Concentration,
    ConcentrationUnit,
)
from bioetl.domain.value_objects.bronze_result import (
    _has_provider_entity,
    _normalized_path_parts,
    _strip_v1_prefix,
)
from bioetl.domain.value_objects.compound_ids import AssayId, CompoundId
from bioetl.domain.value_objects.dq_report_builder import (
    DQReportSummary,
    DQThresholds,
    GoldDQReport,
    SilverDQReport,
)
from bioetl.domain.value_objects.dq_report_enums import DQCheckStatus, DQReportStatus
from bioetl.domain.value_objects.dq_report_results_quality import (
    AnomalyDetectionResult,
    AnomalyMetric,
    BusinessRuleResult,
    BusinessRulesResult,
)
from bioetl.domain.value_objects.identifiers import PubChemCid
from bioetl.domain.value_objects.protein_class_hierarchy import (
    ProteinClassHierarchy,
    ProteinClassLevel,
    _require_level_id,
)

pytestmark = pytest.mark.unit

_NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _reload_without_orjson(module: object) -> object:
    real_import = builtins.__import__

    def _blocked(
        name: str,
        globals: object = None,
        locals: object = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ) -> object:
        if name == "orjson":
            raise ImportError("forced missing orjson")
        return real_import(name, globals, locals, fromlist, level)

    builtins.__import__ = _blocked  # type: ignore[method-assign]
    sys.modules.pop("orjson", None)
    try:
        return importlib.reload(module)  # type: ignore[arg-type]
    finally:
        builtins.__import__ = real_import  # type: ignore[method-assign]


def test_chembl_organism_empty_after_strip_and_unmapped_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert _strip_trailing_parenthetical_annotation("Name)") == "Name)"
    monkeypatch.setattr(
        "bioetl.domain.normalization._chembl_organisms._strip_trailing_parenthetical_annotation",
        lambda _value: "",
    )
    assert normalize_chembl_organism_name("Homo sapiens") is None
    monkeypatch.setattr(
        "bioetl.domain.normalization._chembl_organisms.normalize_organism_name",
        lambda _value: None,
    )
    monkeypatch.setattr(
        "bioetl.domain.normalization._chembl_organisms._strip_trailing_parenthetical_annotation",
        lambda value: value,
    )
    assert normalize_chembl_organism_name("Unmapped species") == "Unmapped species"


def test_control_plane_identity_and_payload_private_fallbacks() -> None:
    assert _normalize_bool_text_token(None) is None
    assert _normalize_bool_text_token("true") == "true"
    normalized: dict[str, object] = {}
    _normalize_manifest_source_refs_field({"source_refs": "plain"}, normalized)
    assert "source_refs" not in normalized
    assert _normalize_manifest_source_ref("plain-ref") == "plain-ref"
    assert _manifest_snapshot_sort_key("snap") == ("", "snap")
    assert _normalize_optional_text(None) is None


def test_reference_id_taxonomy_support_dates_and_json_import_fallback() -> None:
    assert _normalize_ncbi_taxonomy_text("not-a-tax") is None
    marker = object()
    assert _normalize_ncbi_taxonomy_textual(marker) is marker
    assert _normalize_openalex_candidate("W123", prefix="A") is None
    assert _json_fallback("  token  ") == "token"
    assert _parse_year_month("2024-ab") is None
    assert _normalize_partial_month("2024-00") is None
    assert _normalize_partial_month("2024-13") is None
    reloaded_json = _reload_without_orjson(json_normalization)
    reloaded_ser = _reload_without_orjson(serialization_mod)
    try:
        assert reloaded_json._orjson_available is False
        assert reloaded_ser._orjson_available is False
    finally:
        importlib.reload(json_normalization)
        importlib.reload(serialization_mod)


def test_normalization_helpers_signature_identity_and_primitive(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _no_signature(_obj: object) -> object:
        raise TypeError("no signature")

    monkeypatch.setattr(
        "bioetl.domain.normalization.profiles._normalization_helpers.inspect.signature",
        _no_signature,
    )
    assert _normalizer_accepts_record_context(str) is False

    class _Callable:
        def __call__(self, value: object) -> object:
            return value

    with pytest.raises(TypeError, match="deterministic"):
        _require_stable_normalizer_identity(_Callable())
    assert _stable_primitive(object()) is not None


def test_profile_normalizers_whitespace_unknown_and_bound_case() -> None:
    assert _normalize_mapping_status("   ") is None
    assert (
        normalize_profile_publication_type(
            "not-a-known-publication-type",
            allowed_values=frozenset({"Journal"}),
        )
        is None
    )
    assert normalize_profile_semantic_scholar_publication_type_raw(1) is None
    assert normalize_profile_semantic_scholar_publication_type_raw("   ") is None
    assert normalize_profile_json_string("   ") is None
    assert normalize_profile_json_string_strict("   ") is None
    assert _parse_unordered_json_string("   ") is None
    serialized = _serialize_unordered_json_collection({"b": 1, "a": 2}, original="{}")
    assert '"a"' in str(serialized)
    assert _parse_json_string_list("   ") is None
    assert _coerce_profile_int_text("   ") is None
    assert _coerce_profile_float("   ") is None
    assert _finalize_profile_float(_UNHANDLED, fallback="kept") == "kept"
    bound = _bound_case_normalizer(frozenset({"IC50"}))
    assert bound("ic50") == "IC50"


def test_reference_ids_rules_workflow_and_semantic_registry() -> None:
    assert normalize_uniprot_mixed_mapping_reference_id(None) is None
    assert normalize_uniprot_mixed_mapping_reference_id(1) == 1
    assert normalize_doi_reference_id(1) == 1
    assert normalize_pmid_reference_id(1.5) == 1.5
    assert normalize_boolean(2) is None
    assert normalize_boolean(0.5) is None
    assert normalize_boolean("   ") is None
    assert normalize_operator("   ") is None
    with pytest.raises(RowReconciliationConfigError, match="cannot be empty"):
        _required_name("  ", "left_table")
    with pytest.raises(RowReconciliationConfigError, match="workflow_name"):
        _normalize_workflow_name("  ")
    with pytest.raises(RowReconciliationConfigError, match="cannot be empty"):
        RowReconciliationConfig(
            layer=RowReconciliationLayer.SILVER,
            left_table="  ",
            right_table="r",
            left_columns=("id",),
            right_columns=("id",),
            left_primary_keys=("id",),
        )
    with pytest.raises(RowReconciliationConfigError, match="workflow_name"):
        RowReconciliationConfig(
            layer=RowReconciliationLayer.SILVER,
            left_table="l",
            right_table="r",
            left_columns=("id",),
            right_columns=("id",),
            left_primary_keys=("id",),
            workflow_name="  ",
        )
    cluster = SemanticFieldCluster(
        cluster_id="c1",
        semantic_name="name",
        canonical_name="name",
        legacy_names=(),
        raw_provider_names=(),
        pipelines=("activity",),
        affected_paths=("p",),
        migration_status="done",
        notes="",
    )
    registry = SemanticFieldRegistry((cluster,))
    assert registry.clusters == (cluster,)


def test_run_reports_tracking_unknown_catalog_payload_and_mutation() -> None:
    acc = StageAccountingAccumulator()
    assert acc._tracking_for("custom", _StageBucket()) is TrackingCoverage.NOT_TRACKED
    assert (
        acc._balance_status(
            records_in=0,
            records_out=1,
            removed_total=0,
            unaccounted=1,
            tracking=TrackingCoverage.NOT_TRACKED,
        ).name
        == "UNKNOWN"
    )
    catalog = ReasonCatalog(version="v", entries={}, unknown_code="MISSING")
    fallback = catalog.resolve("nope")
    assert fallback.code == "MISSING"
    assert _payload_mapping(None) == {}
    row = WorkflowExecutionRow(step_id="a", status="success", records_extracted=1)
    assert (
        _measured_current(
            row,
            {"source_scope": "all_current", "mutation_mode": "unexpected"},
        )
        is None
    )


def test_gold_support_rejects_schema_policy_and_field_providers() -> None:
    with pytest.raises(ValueError, match="non-empty string"):
        normalize_column_name(1, field_name="column")
    with pytest.raises(ValueError, match="non-empty string"):
        normalize_column_name("  ", field_name="column")
    with pytest.raises(ValueError, match="must be strings"):
        normalize_optional_text(1)
    with pytest.raises(ValueError, match="GoldRejectReasonCode"):
        normalize_reason_code(1)
    schema = SimpleNamespace(active_version="1.2.3")
    assert _extract_version_from_standard_attributes(schema) == "1.2.3"
    assert _known_contract_version_or_none("1.2.3") == "1.2.3"
    assert _resolve_version_from_schema(schema) == "1.2.3"
    v1 = GoldSchemaVersionPolicy(version="v1", schema={"a": 1})
    with pytest.raises(ValueError, match="active_version must be present"):
        GoldSchemaPolicyByVersion(active_version="v9", policies=(v1,))
    cfg = FieldGroupConfig()
    mapped = next(iter(cfg.field_groups))
    assert cfg.get_field_providers(mapped) == list(cfg.provider_priority)
    assert cfg.get_field_providers("not-a-mapped-field") == []


def test_run_context_concentration_bronze_compound_and_identifiers() -> None:
    with pytest.raises(TypeError, match="must be"):
        _require_value({"provider": 1}, "provider", str)
    with pytest.raises(TypeError, match="str or None"):
        _optional_str_value({"pipeline_version": 1}, "pipeline_version")
    with pytest.raises(TypeError, match="UUID or a legacy string"):
        _run_id_value({"run_id": 1})
    with pytest.raises(TypeError, match="must be numeric"):
        Concentration(value="1.0", unit=ConcentrationUnit.NANOMOLAR)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="must be finite"):
        Concentration(value=math.inf, unit=ConcentrationUnit.NANOMOLAR)
    with pytest.raises(ValueError, match="provider/entity"):
        _normalized_path_parts("")
    assert _strip_v1_prefix([]) == []
    assert _has_provider_entity([" ", "activity"]) is False
    with pytest.raises(ValueError, match="Unsupported compound source"):
        CompoundId(value="x", source="other")  # type: ignore[arg-type]
    cid = CompoundId.from_chembl("CHEMBL25")
    assert cid.__eq__("not-a-compound-id") is NotImplemented
    assert AssayId("CHEMBL1")._validate("CHEMBL1") == "CHEMBL1"
    with pytest.raises(ValueError, match="Invalid PubChem CID"):
        PubChemCid("not-a-cid")
    with pytest.raises(ValueError, match="must be int"):
        PubChemCid(1.5)  # type: ignore[arg-type]


def test_dq_reports_wrong_layer_list_coercion_and_protein_path() -> None:
    summary = DQReportSummary(1, 1, 0, 0, DQReportStatus.PASS)
    thresholds = DQThresholds(0.1, 0.2, 0.0, DQCheckStatus.PASS)
    with pytest.raises(ValueError, match="must be SILVER"):
        SilverDQReport(
            layer=Layer.GOLD,
            timestamp=_NOW,
            run_id="r",
            pipeline="p",
            source_batch_ids=("b1",),
            target_table="t",
            checks={},
            thresholds=thresholds,
            summary=summary,
        )
    with pytest.raises(ValueError, match="must be GOLD"):
        GoldDQReport(
            layer=Layer.SILVER,
            timestamp=_NOW,
            run_id="r",
            pipeline="p",
            target_table="t",
            checks={},
            data_freshness=None,
            summary=summary,
        )
    rules = BusinessRulesResult(
        rules_evaluated=1,
        rules_passed=1,
        rules_failed=0,
        rules=[  # type: ignore[arg-type]
            BusinessRuleResult(
                rule_id="r1",
                name="n",
                description="d",
                passed=True,
                violations=0,
            )
        ],
    )
    assert isinstance(rules.rules, tuple)
    anomaly = AnomalyDetectionResult(
        cold_start_days=1,
        current_day=1,
        cold_start_mode=True,
        anomalies_detected=["spike"],  # type: ignore[arg-type]
        metrics_monitored=[AnomalyMetric(metric="m", current_value=1.0)],  # type: ignore[arg-type]
    )
    assert anomaly.anomalies_detected == ("spike",)
    assert isinstance(anomaly.metrics_monitored, tuple)
    empty = ProteinClassLevel.empty()
    hierarchy = ProteinClassHierarchy.__new__(ProteinClassHierarchy)
    object.__setattr__(hierarchy, "l1", empty)
    object.__setattr__(hierarchy, "l2", empty)
    object.__setattr__(hierarchy, "l3", empty)
    object.__setattr__(hierarchy, "l4", empty)
    object.__setattr__(hierarchy, "l5", empty)
    object.__setattr__(hierarchy, "leaf_id", 1)
    object.__setattr__(hierarchy, "path", ())
    assert hierarchy.is_leaf is False
    with pytest.raises(ValueError, match="must carry identifiers"):
        _require_level_id(None)
