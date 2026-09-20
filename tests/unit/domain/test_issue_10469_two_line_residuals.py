"""Behavior tests for two-line domain coverage residuals in #10469."""

from __future__ import annotations

from enum import Enum

import pytest

from bioetl.domain.behavior._dq_serializer_html._renderers import _format_dict_detail
from bioetl.domain.behavior.activity_aggregator._methods import (
    _geometric_mean,
    _median_absolute_deviation,
)
from bioetl.domain.behavior.merged_metadata_helpers import (
    _normalize_record_id_key,
    _normalize_record_id_value,
)
from bioetl.domain.config._converters import require_literal
from bioetl.domain.config.pipeline import FieldPolicyConfig
from bioetl.domain.entities.bioactivity._converters import (
    _safe_str_from_float,
    _safe_str_from_text,
)
from bioetl.domain.lineage._shared import _plain_float, _plain_identifier
from bioetl.domain.lineage.graph import _load_edges, _load_node_refs
from bioetl.domain.locking import LockContext, LockContextHolder
from bioetl.domain.normalization._reference_id_normalizers import (
    _normalize_issn_text,
    normalize_ror_reference_id,
)
from bioetl.domain.normalization.chembl import (
    _normalize_prefixed_identifier,
    normalize_cellosaurus_id,
)
from bioetl.domain.normalization.profiles._profile_activity_ontology_normalizers import (
    _normalize_mapping_status,
)
from bioetl.domain.normalization.profiles._standard_profile_rule_context import (
    _coerce_rule_component,
)
from bioetl.domain.ports.health_check import HealthCheckResult
from bioetl.domain.transformations.coercion import safe_str
from bioetl.domain.types import HealthStatus, RunID
from bioetl.domain.value_objects._chemical_identifiers import (
    SMILES,
    _validate_smiles_normalization_mode,
)
from bioetl.domain.value_objects._publication_year import PublicationYear
from bioetl.domain.value_objects.activity_confidence import ConfidenceScore
from bioetl.domain.value_objects.pchembl_value import PChemblValue
from bioetl.domain.workflow.dag import (
    WorkflowDagValidationError,
    _assert_workflow_has_steps,
    validate_workflow_dag,
)


pytestmark = pytest.mark.unit


def test_html_dict_detail_falls_back_for_non_json_value() -> None:
    rendered = _format_dict_detail({"value": object()})
    assert rendered.startswith("<pre>")
    assert "object" in rendered


def test_activity_aggregation_edge_cases_are_explicit() -> None:
    with pytest.raises(ValueError, match="empty sequence"):
        _geometric_mean([])
    assert _median_absolute_deviation([1.0]) == 0.0


def test_record_id_helpers_normalize_sequences_and_reject_object_keys() -> None:
    assert _normalize_record_id_value(("a", 1)) == ["a", 1]
    with pytest.raises(TypeError, match="Unsupported mapping key"):
        _normalize_record_id_key(object())


def test_require_literal_reports_allowed_choices() -> None:
    with pytest.raises(ValueError, match="must be one of"):
        require_literal("invalid", field_name="mode", allowed=frozenset({"a", "b"}))


def test_field_policy_rejects_overlapping_boolean_tokens() -> None:
    with pytest.raises(ValueError, match="must not overlap"):
        FieldPolicyConfig(
            field="active",
            boolean_true_values=("yes",),
            boolean_false_values=("yes",),
        )


def test_bioactivity_string_helpers_preserve_fallback_values() -> None:
    assert _safe_str_from_float(1.5) == "1.5"
    assert _safe_str_from_text("   ") is None


class _PlainEnum(Enum):
    VALUE = "plain"


def test_lineage_plain_value_helpers_validate_float_and_enum() -> None:
    assert _plain_float(1.5) == 1.5
    with pytest.raises(ValueError, match="NaN or Infinity"):
        _plain_float(float("nan"))
    assert _plain_identifier(_PlainEnum.VALUE) == "plain"


def test_lineage_graph_loaders_default_invalid_collections_to_empty() -> None:
    assert _load_node_refs({}) == ()
    assert _load_edges({}) == ()


def test_lock_context_without_timestamp_is_valid_and_holder_returns_context() -> None:
    context = LockContext(key="lock:test", owner_id=RunID("owner"))
    holder = LockContextHolder()
    holder.set(context)
    assert context.is_valid()
    assert holder.get() is context


def test_reference_id_normalizers_reject_invalid_or_absent_values() -> None:
    assert _normalize_issn_text("invalid") is None
    marker = object()
    assert normalize_ror_reference_id(marker) is marker


def test_chembl_identifier_normalizers_cover_prefix_and_absent_cellosaurus() -> None:
    import re

    assert (
        _normalize_prefixed_identifier(
            "chembl123",
            prefix="CHEMBL",
            pattern=re.compile(r"CHEMBL_(\d+)", re.IGNORECASE),
        )
        == "CHEMBL123"
    )
    assert normalize_cellosaurus_id(None) is None


def test_mapping_status_normalizer_rejects_non_text_and_blank_text() -> None:
    assert _normalize_mapping_status(1) is None
    assert _normalize_mapping_status("   ") is None


def test_rule_component_accepts_callable_and_rejects_invalid_shape() -> None:
    def normalizer(value: object) -> object:
        return value

    resolved, _notes = _coerce_rule_component(field_name="field", component=normalizer)
    assert resolved is normalizer
    with pytest.raises(ValueError, match="invalid component"):
        _coerce_rule_component(field_name="field", component=object())


@pytest.mark.parametrize(
    "kwargs",
    [
        {"latency_ms": -1.0, "consecutive_failures": 0},
        {"latency_ms": 1.0, "consecutive_failures": -1},
    ],
)
def test_health_check_result_rejects_invalid_numbers(kwargs: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        HealthCheckResult(
            status=HealthStatus.HEALTHY,
            provider="provider",
            **kwargs,
        )


class _BrokenString:
    def __str__(self) -> str:
        raise ValueError("cannot stringify")


def test_safe_str_returns_default_when_conversion_fails() -> None:
    assert safe_str(_BrokenString(), default="fallback") == "fallback"


def test_smiles_comparison_and_mode_validation() -> None:
    smiles = SMILES("CC")
    assert (smiles == object()) is False
    with pytest.raises(ValueError, match="Unsupported SMILES"):
        _validate_smiles_normalization_mode("unsupported")


def test_publication_year_rejects_float_and_compares_other_type() -> None:
    with pytest.raises(ValueError, match="must be int"):
        PublicationYear(2024.5)
    assert (PublicationYear(2024) == object()) is False


def test_numeric_value_objects_return_not_implemented_for_other_types() -> None:
    confidence = ConfidenceScore(5)
    pchembl = PChemblValue(7.0)
    assert (confidence == object()) is False
    assert (pchembl == object()) is False
    with pytest.raises(TypeError):
        _ = confidence < object()
    with pytest.raises(TypeError):
        _ = pchembl < object()


def test_workflow_dag_validates_and_rejects_empty_workflow() -> None:
    from types import SimpleNamespace

    validate_workflow_dag((SimpleNamespace(step_id="step", depends_on=()),))
    with pytest.raises(WorkflowDagValidationError, match="at least one step"):
        _assert_workflow_has_steps(())
