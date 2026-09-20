"""Stream A remaining 1–4 line INF leftovers after unit XML 6fcff74a."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from bioetl.domain.control_plane import ControlPlaneArtifactSurface
from bioetl.infrastructure.adapters.base_metrics import AdapterMetricsRecorder
from bioetl.infrastructure.control_plane.file_artifact_lifecycle_payloads import (
    _artifact_id,
)
from bioetl.infrastructure.control_plane.file_artifact_lifecycle_reasons import (
    _protected_by,
)
from bioetl.infrastructure.control_plane.file_artifact_lifecycle_types import (
    _ProtectedRefs,
)
from bioetl.infrastructure.observability._metrics_gateway_publication import (
    _normalize_grouping_label_value,
)
from bioetl.infrastructure.quality.architecture_debt_reduction import (
    _within_limit_category,
)
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig
from bioetl.infrastructure.schemas.pipeline_config_common import DQYamlConfig
from bioetl.infrastructure.storage.delta_reader_helpers import (
    try_native_delta_row_count,
)
from bioetl.infrastructure.storage.gold.io_metrics import _split_gold_merged_table_label
from bioetl.infrastructure.storage.gold.writer_metrics import _split_gold_table_label
from bioetl.infrastructure.storage.workflow_foreign_key_reconciliation_support import (
    _is_current_flag_value,
)

pytestmark = pytest.mark.unit


def test_record_dropped_duplicates_without_metrics() -> None:
    recorder = AdapterMetricsRecorder(metrics=None, provider="chembl")
    recorder.record_dropped_duplicates("activity", 3)


def test_grouping_label_empty_and_unknown_key() -> None:
    assert _normalize_grouping_label_value("pipeline", "   ") == "unknown"
    assert _normalize_grouping_label_value("pipeline", "!!!") == "unknown"
    assert (
        _normalize_grouping_label_value("pipeline", "chembl_activity")
        == "chembl_activity"
    )
    assert (
        _normalize_grouping_label_value("other", "chembl_activity") == "chembl_activity"
    )


def test_cached_bronze_identity_and_reasons(tmp_path: Path) -> None:
    path = tmp_path / "bronze.jsonl"
    path.write_text("{}", encoding="utf-8")
    identity = _artifact_id(
        surface=ControlPlaneArtifactSurface.CACHED_BRONZE,
        path=path,
        payload={},
    )
    assert identity
    reasons = _protected_by(
        surface=ControlPlaneArtifactSurface.CACHED_BRONZE,
        path=path,
        payload={},
        protected_refs=_ProtectedRefs(
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
        ),
    )
    assert reasons == ()


def test_publication_entity_type_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "bioetl.domain.registry.publication.get_publication_entity_type_validation_error",
        lambda *_args, **_kwargs: "canonical name required",
    )
    host = PipelineYamlConfig.model_construct(
        entity_type="document",
        provider="chembl",
        business_primary_keys=("id",),
        technical_primary_key="hash",
    )
    with pytest.raises(ValueError, match="canonical name"):
        host.validate_entity_type_canonical()


def test_dq_yaml_domain_converters() -> None:
    field = SimpleNamespace(
        field="ic50",
        type="required",
        nullable=True,
        severity="error",
        severity_enricher=None,
        min=None,
        max=None,
        pattern=None,
        allowed=(),
        max_length=None,
        validator=None,
        error_message=None,
    )
    converted = DQYamlConfig._to_domain_field_validation(field)  # type: ignore[arg-type]
    assert converted.field == "ic50"
    cross = SimpleNamespace(
        name="pair",
        fields=("a", "b"),
        condition="all_present",
        severity="error",
        trigger_field=None,
        required_field=None,
        validator=None,
        error_message=None,
    )
    assert DQYamlConfig._to_domain_cross_field_validation(cross).name == "pair"  # type: ignore[arg-type]
    cond = SimpleNamespace(
        name="when",
        condition_field="status",
        condition_value=["ok"],
        condition_operator="in",
        then_validations=[field],
        else_validations=(),
        severity="error",
        error_message=None,
    )
    domain = DQYamlConfig._to_domain_conditional_validation(cond)  # type: ignore[arg-type]
    assert domain.name == "when"


def test_debt_reduction_mid_delta_returns_none() -> None:
    assert (
        _within_limit_category(
            status="within_limit",
            current_value=99,
            delta_to_limit=-10,
            default_limit=10,
        )
        is None
    )


def test_delta_row_count_error_and_gold_labels() -> None:
    class _Boom:
        def count(self) -> int:
            raise RuntimeError("nope")

    assert try_native_delta_row_count(_Boom()) is None  # type: ignore[arg-type]
    assert _split_gold_merged_table_label(".")[0]
    assert _split_gold_table_label("only")[0]


def test_current_flag_numeric_and_string() -> None:
    assert _is_current_flag_value(1) is True
    assert _is_current_flag_value("yes") is True
    assert _is_current_flag_value("no") is False
    assert _is_current_flag_value(object()) is False
