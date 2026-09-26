"""Stream A domain coverage for #10469 / #10519 (normalizer, pipeline, 4-line)."""

from __future__ import annotations

import math

import pytest

from bioetl.domain.behavior._dq_value_coercion import (
    _coerce_list_like,
    _coerce_numeric_value,
    _is_present,
    _violates_maximum,
    _violates_minimum,
)
from bioetl.domain.behavior.aggregation_validation_helpers import (
    build_group_key,
    canonical_group_value,
    collect_duplicate_groups,
    column_names,
    explicit_field_names,
    field_name_from_descriptor,
)
from bioetl.domain.behavior.normalization_config import NormalizationConfig
from bioetl.domain.behavior.normalization_service import BioactivityNormalizer
from bioetl.domain.behavior.value_validator import ValueValidator
from bioetl.domain.behavior.value_validator_rules import (
    is_percent_inhibition_type,
    normalize_unit_name,
    validate_percent_value,
)
from bioetl.domain.composite.field_groups_models import (
    FieldGroupDefinition,
    FieldGroupId,
    FieldMapping,
)
from bioetl.domain.composite.field_groups_registry import FieldGroupRegistry
from bioetl.domain.config.enum_loader import (
    get_chembl_enum,
    get_chembl_enum_set,
    get_enum_config,
    load_chembl_enums,
    load_provider_enums,
)
from bioetl.domain.config.validation import FieldValidation
from bioetl.domain.normalization._chembl_organisms import (
    _annotation_is_invalid,
    normalize_chembl_organism_name,
)
from bioetl.domain.run_reports.accounting import StageAccountingAccumulator
from bioetl.domain.run_reports.models import (
    BalanceStatus,
    LayerCounts,
    TrackingCoverage,
)
from bioetl.domain.run_reports.pipeline_builder import (
    PipelineRunReportOptionalBlocks,
    _derive_performance,
    _has_contract_activity,
    _is_contract_reason,
    _optional_mapping,
    _records_per_second,
    _resolve_catalog_version,
    _resolve_contract_summary,
    _resolve_performance,
    _resolve_top_reasons,
    _resolve_tracking,
    _status_from_layers,
    _with_rejection_details,
    build_pipeline_run_report,
)
from bioetl.domain.value_objects import ActivityType, Concentration, ConcentrationUnit

pytestmark = pytest.mark.unit


class _EnumLoader:
    def load_provider_enums(self, provider: str) -> dict[str, object]:
        del provider
        return {
            "activity": {"types": ["IC50", "Ki"], "broken": "not-a-list"},
            "bad": "not-a-mapping",
        }

    def load_chembl_enums(self) -> dict[str, object]:
        return self.load_provider_enums("chembl")


class _BoomConverter:
    def convert(self, value: float, from_unit: str, to_unit: str) -> float:
        del value, from_unit, to_unit
        raise ValueError("convert failed")

    def value_to_pchembl(self, value: float, unit: str) -> object:
        del value, unit
        raise ValueError("pchembl failed")

    def to_pchembl(self, concentration: Concentration) -> object:
        del concentration
        raise ValueError("pchembl failed")


def test_bioactivity_normalizer_invalid_convert_and_potency_buckets() -> None:
    normalizer = BioactivityNormalizer()
    invalid = normalizer.normalize_activity(0.0, "nM", "IC50")
    assert invalid.is_valid is False
    normalizer.converter = _BoomConverter()  # type: ignore[assignment]
    converted = normalizer.normalize_activity(10.0, "nM", "IC50", validate=False)
    assert converted.is_valid is False
    assert "convert failed" in str(converted.validation_message)
    assert normalizer.normalize_to_pchembl(1.0, "not-a-unit") is None
    host = BioactivityNormalizer()
    assert host.normalize_to_pchembl(1.0, "fM") is None
    host.converter = _BoomConverter()  # type: ignore[assignment]
    pchembl, potent = host._compute_pchembl_for_value(10.0)
    assert pchembl is None and potent is False
    assert host.classify_potency(3.0) == "inactive"
    assert host.classify_potency(4.5) == "weak"
    assert host.classify_potency(5.5) == "moderate"
    assert host.classify_potency(6.5) == "potent"
    assert host.classify_potency(8.0) == "highly_potent"
    assert host.is_potent(5.0) is True
    assert host.is_highly_potent(6.9) is False


def test_bioactivity_normalizer_batch_and_concentrations() -> None:
    normalizer = BioactivityNormalizer()
    listed = normalizer.normalize_multiple(
        [100.0, 200.0], "nM", "IC50", aggregate=False
    )
    assert isinstance(listed, list) and len(listed) == 2
    aggregated = normalizer.normalize_multiple([100.0, 200.0], "nM", "IC50")
    assert aggregated.is_valid is True
    empty = normalizer.normalize_multiple([-1.0], "nM", "IC50")
    assert empty.is_valid is False
    no_conc = normalizer.normalize_concentrations(())
    assert no_conc.is_valid is False
    concs = (
        Concentration(value=100.0, unit=ConcentrationUnit.NANOMOLAR),
        Concentration(value=200.0, unit=ConcentrationUnit.NANOMOLAR),
    )
    ok = normalizer.normalize_concentrations(concs)
    assert ok.is_valid is True and ok.pchembl is not None
    normalizer.converter = _BoomConverter()  # type: ignore[assignment]
    skipped = normalizer.normalize_concentrations(concs)
    assert skipped.is_valid is True and skipped.pchembl is None


def test_pipeline_builder_status_optional_and_performance() -> None:
    ok_layers = LayerCounts()
    silver, gold, silver_delta, gold_delta = _status_from_layers(ok_layers)
    assert silver is BalanceStatus.OK and gold is BalanceStatus.OK
    assert silver_delta == 0 and gold_delta == 0
    balanced = LayerCounts(bronze_records=100, silver_valid=100, gold_written=100)
    silver_ok, gold_ok, _, _ = _status_from_layers(balanced)
    assert silver_ok is BalanceStatus.OK and gold_ok is BalanceStatus.OK
    degraded = LayerCounts(bronze_records=100, silver_valid=99)
    silver_deg, gold_fail, _, _ = _status_from_layers(degraded)
    assert silver_deg is BalanceStatus.DEGRADED
    assert gold_fail is BalanceStatus.FAILING
    assert _optional_mapping(None) is None
    assert _optional_mapping({"k": 1}) == {"k": 1}
    assert _records_per_second(0, 1.0) is None
    assert _records_per_second(10, 2.0) == 5.0
    assert _derive_performance(identity={}, metrics_map={}, stage_timings=None) is None
    derived = _derive_performance(
        identity={"duration_seconds": 2},
        metrics_map={"records_fetched": 8},
        stage_timings={"extract": 1},
    )
    assert derived is not None and derived["stage_timings_present"] is True
    provided = _resolve_performance(
        performance={"custom": True},
        identity={},
        metrics_map={},
        stage_timings=None,
    )
    assert provided == {"custom": True}


def test_pipeline_builder_reasons_contract_tracking_and_build() -> None:
    acc = StageAccountingAccumulator()
    layers = LayerCounts(
        silver_filtered_out=2,
        silver_quarantined=1,
        gold_excluded_by_contract=3,
    )
    reasons = _resolve_top_reasons(acc, layers)
    assert {item["outcome"] for item in reasons} == {
        "filtered_out",
        "quarantined",
        "excluded_by_contract",
    }
    gold_fallback = next(
        item for item in reasons if item["outcome"] == "excluded_by_contract"
    )
    assert gold_fallback["reason_code"] == "gold_filter_exclusion"
    assert _is_contract_reason({"reason_family": "contract"}) is True
    assert _has_contract_activity(0, []) is False
    summary = _resolve_contract_summary(None, reasons, layers)
    assert summary is not None and summary["gold_excluded_by_contract"] == 3
    copied = _resolve_contract_summary({"given": 1}, reasons, layers)
    assert copied == {"given": 1}
    acc.record_gold_filter_rejection({"reason_code": "X", "field": "y"})
    attached = _with_rejection_details(None, acc)
    assert attached is not None and "rejection_details" in attached
    assert _with_rejection_details({"a": 1}, StageAccountingAccumulator()) == {"a": 1}
    assert _resolve_tracking(acc, (), None) is TrackingCoverage.PARTIAL
    assert _resolve_catalog_version(acc, None, "override") == "override"
    assert _resolve_catalog_version(acc, acc, None) == acc.reason_catalog_version
    report = build_pipeline_run_report(
        identity={"duration_seconds": 1},
        metrics={"records_bronze": 1, "records_silver": 1, "records_gold": 1},
        optional_blocks=PipelineRunReportOptionalBlocks(failure={"ok": True}),
    )
    assert report.failure == {"ok": True}
    none_acc = build_pipeline_run_report(identity={}, metrics={})
    assert none_acc.tracking_coverage is TrackingCoverage.PARTIAL


def test_dq_coercion_and_aggregation_group_helpers() -> None:
    rule = FieldValidation(
        field="x", validation_type="range", min_value=1.0, max_value=10.0
    )
    assert _is_present(0) is True
    assert _coerce_list_like([1]) == [1]
    assert _coerce_list_like({2}) == [2]
    assert _coerce_list_like("not-json") is None
    assert _coerce_list_like("  ") == []
    assert _coerce_list_like("[1, 2]") == [1, 2]
    assert _coerce_list_like("[") is None
    assert _coerce_list_like('{"a": 1}') is None
    assert _coerce_numeric_value(True) is None
    assert _coerce_numeric_value(object()) is None
    assert _coerce_numeric_value("x") is None
    assert _coerce_numeric_value(math.inf) is None
    assert _violates_minimum(0.0, rule) is True
    assert _violates_maximum(11.0, rule) is True
    dupes = collect_duplicate_groups(
        aggregation_results=[{"g": 1}, {"g": None}, {"g": 1}],
        group_by_fields=["g", "missing"],
    )
    assert len(dupes) == 1
    key = build_group_key({"g": None}, ["g", "absent"])
    assert key[0][1] == "NoneType"
    assert field_name_from_descriptor("col") == "col"
    assert field_name_from_descriptor({"name": "n"}) == "n"
    assert field_name_from_descriptor(1) is None
    assert column_names(["a", {"name": "b"}, 3]) == {"a", "b"}
    assert column_names("x") == set()
    assert explicit_field_names(["a", 1]) == {"a"}
    with pytest.raises(TypeError, match="JSON-serializable"):
        canonical_group_value({1, 2})


def test_value_validator_ranges_percent_and_unit_aliases() -> None:
    validator = ValueValidator(config=NormalizationConfig())
    assert validator.validate_concentration(math.inf, "nM")[0] is False
    assert validator.validate_concentration(1.0, "nope")[0] is False
    assert validator.validate_concentration(1e-20, "nM")[0] is False
    assert validator.validate_pchembl(math.nan)[0] is False
    assert validator.validate_pchembl(-0.1)[0] is False
    assert validator.validate_pchembl(15.0)[0] is False
    strict = ValueValidator(strict=True)
    assert strict.validate_pchembl(1.0)[0] is False
    assert strict.validate_pchembl(13.0)[0] is False
    assert validator.validate_activity_value(math.inf, "IC50")[0] is False
    assert validator.validate_activity_value(-1.0, "IC50")[0] is False
    percent_ok, _ = validator.validate_activity_value(
        50.0, ActivityType.PERCENT_INHIBITION
    )
    assert percent_ok is True
    unknown, _ = validator.validate_activity_value(1.0, "not-a-type")
    assert unknown is True
    validator._apply_molar_window("missing", 1.0, 2.0, 1.0)
    validator._concentration_ranges.pop("µM", None)
    assert validator._micromolar_key() in {"uM", None}
    with pytest.raises(ValueError, match="finite"):
        validator.set_concentration_range("nM", math.nan, 1.0)
    with pytest.raises(ValueError, match="less than"):
        validator.set_concentration_range("nM", 2.0, 1.0)
    assert normalize_unit_name("nanomolar") == "nM"
    assert is_percent_inhibition_type("% Inhibition") is False
    assert validate_percent_value(True)[0] is False  # type: ignore[arg-type]
    assert validate_percent_value(math.nan)[0] is False
    assert validate_percent_value(math.inf)[0] is False
    assert validate_percent_value(-1.0)[0] is False
    assert validate_percent_value(101.0)[0] is False


def test_field_group_registry_duplicate_keys_and_enum_loader() -> None:
    mapping = FieldMapping(
        base_name="title",
        provider_columns=("chembl.publication.title",),
        group=FieldGroupId.BIBLIOGRAPHY,
    )
    group = FieldGroupDefinition(
        group_id=FieldGroupId.BIBLIOGRAPHY,
        display_name="Biblio",
        fields=(mapping,),
    )
    registry = FieldGroupRegistry((group,))
    assert registry.get_group("chembl.publication.title") is FieldGroupId.BIBLIOGRAPHY
    assert registry.get_group("unknown") is FieldGroupId.TRASH
    dup_base = FieldGroupDefinition(
        group_id=FieldGroupId.TRASH,
        display_name="Trash",
        fields=(FieldMapping(base_name="title", provider_columns=("x.y.z",)),),
    )
    with pytest.raises(ValueError, match="Duplicate field-group base_name"):
        FieldGroupRegistry((group, dup_base))
    dup_col = FieldGroupDefinition(
        group_id=FieldGroupId.TRASH,
        display_name="Trash",
        fields=(
            FieldMapping(
                base_name="abstract",
                provider_columns=("chembl.publication.title",),
            ),
        ),
    )
    with pytest.raises(ValueError, match="Duplicate provider column"):
        FieldGroupRegistry((group, dup_col))
    loader = _EnumLoader()
    with pytest.raises(NotImplementedError, match="cannot perform direct I/O"):
        load_provider_enums("chembl")
    with pytest.raises(ValueError, match="cannot be blank"):
        load_provider_enums("  ", loader)
    assert get_chembl_enum("activity", "types", loader) == ["IC50", "Ki"]
    assert "Ki" in get_chembl_enum_set("activity", "types", loader)
    with pytest.raises(KeyError, match="not found"):
        get_enum_config("activity", "missing", loader)
    with pytest.raises(TypeError, match="Expected list"):
        get_enum_config("activity", "broken", loader)
    with pytest.raises(TypeError, match="Expected mapping"):
        get_enum_config("bad", "types", loader)
    assert load_chembl_enums(loader)["activity"]["types"] == ["IC50", "Ki"]


def test_chembl_organism_display_aliases_and_annotations() -> None:
    assert normalize_chembl_organism_name(None) is None
    assert normalize_chembl_organism_name("   ") is None
    assert normalize_chembl_organism_name("e. coli") == "Escherichia coli"
    assert normalize_chembl_organism_name("Homo sapiens (human)") == "Homo sapiens"
    assert normalize_chembl_organism_name("Unknown species") == "Unknown species"
    assert _annotation_is_invalid("") is True
    nested = normalize_chembl_organism_name("Name (outer (inner))")
    assert nested is not None and nested.startswith("Name")
