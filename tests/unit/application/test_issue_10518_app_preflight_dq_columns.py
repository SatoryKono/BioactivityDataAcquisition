"""Stream B APP: leftover preflight, DQ, evidence, metrics, and column helpers."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from bioetl.application.composite.column_service import ColumnOrderService
from bioetl.application.composite.column_service_support import (
    collect_pattern_columns,
    extract_field_from_qualified_name,
)
from bioetl.application.composite.helpers.preflight_schema_field_extraction import (
    extract_fields_from_schema,
    simplify_dtype,
)
from bioetl.application.core.batch_executor_dq_helpers import (
    build_dataframe_from_records,
    dataframe_error_types,
    normalize_records_for_polars,
    stringify_value,
)
from bioetl.application.observability.control_plane_evidence.checks import (
    EvidenceCheckResult,
)
from bioetl.application.observability.control_plane_evidence.models import (
    _overall_status,
    _processing_status,
    _scope_kind,
)
from bioetl.application.pipelines.openalex import _extractors_authors as oa
from bioetl.application.services.ops._metrics_service_gateway_support import (
    _MetricsGatewayMixin,
)
from bioetl.domain.composite import ColumnGroupConfig
from bioetl.domain.control_plane.run_ledger import (
    RUN_FAILED_EVENT,
    RUN_FINISHED_EVENT,
    RUN_SHUTDOWN_EVENT,
)
from bioetl.domain.exceptions import BioETLError, DataQualityError

pytestmark = pytest.mark.unit


def test_preflight_dtype_and_schema_extraction_fallbacks() -> None:
    assert simplify_dtype("pandas.Int64") == "int"
    assert simplify_dtype("pandera.float64") == "float"

    class _Broken:
        @classmethod
        def to_schema(cls) -> object:
            raise ValueError("bad schema")

    host = SimpleNamespace(_logger=MagicMock())
    fields = extract_fields_from_schema(host, _Broken, "silver")  # type: ignore[arg-type]
    assert fields == {}
    host._logger.warning.assert_called()

    class _BioBroken:
        x: int

        @classmethod
        def to_schema(cls) -> object:
            raise BioETLError("bio")

    bio_fields = extract_fields_from_schema(host, _BioBroken, "gold")  # type: ignore[arg-type]
    assert "x" in bio_fields

    class _DqBroken:
        @classmethod
        def to_schema(cls) -> object:
            raise DataQualityError("dq")

    extract_fields_from_schema(host, _DqBroken, "bronze")  # type: ignore[arg-type]


def test_dq_helpers_stringify_and_empty_dataframe() -> None:
    assert "PolarsError" in {cls.__name__ for cls in dataframe_error_types()}
    assert stringify_value({"a": 1}, {"payload"}, "payload") == '{"a": 1}'
    assert stringify_value(None, {"payload"}, "payload") is None
    mixed = normalize_records_for_polars(
        [{"payload": {"a": 1}}, {"payload": "already"}]
    )
    assert mixed is not None
    assert (
        build_dataframe_from_records(
            records=[],
            logger=MagicMock(),
        )
        is None
    )


def test_evidence_models_status_and_scope() -> None:
    assert _overall_status(()) == "UNKNOWN"
    finished = SimpleNamespace(event_type=RUN_FINISHED_EVENT)
    failed = SimpleNamespace(event_type=RUN_FAILED_EVENT)
    shutdown = SimpleNamespace(event_type=RUN_SHUTDOWN_EVENT)
    manifest = SimpleNamespace(launch_context={})
    assert _processing_status(manifest, (finished,)) == "success"  # type: ignore[arg-type]
    assert _processing_status(manifest, (failed,)) == "failed"  # type: ignore[arg-type]
    assert _processing_status(manifest, (shutdown,)) == "shutdown"  # type: ignore[arg-type]
    assert (
        _scope_kind(resolved_via="selected_run_id_not_found", manifest=manifest)
        == "unresolved"
    )
    assert (
        _scope_kind(resolved_via="pipeline_scope", manifest=manifest)
        == "pipeline_current"
    )
    assert (
        _overall_status(
            (
                EvidenceCheckResult("a", "OK", "ok", "d"),
                EvidenceCheckResult("b", "ERROR", "err", "d"),
            )
        )
        == "ERROR"
    )


def test_metrics_gateway_delete_error_and_unsuccessful() -> None:
    class _Host(_MetricsGatewayMixin):
        logger = MagicMock()
        tracer = None
        _publisher = SimpleNamespace(
            delete_from_gateway=lambda **_k: (_ for _ in ()).throw(RuntimeError("down"))
        )

    host = _Host()
    failed = host._delete_from_gateway_impl(
        gateway="https://prom", run_label="r1", labels={"job": "bioetl"}
    )
    assert failed.success is False
    host._publisher = SimpleNamespace(delete_from_gateway=lambda **_k: False)
    unsuccessful = host._delete_from_gateway_impl(
        gateway="http://prom", run_label="r1", labels={"job": "bioetl"}
    )
    assert unsuccessful.success is False
    host._publisher = SimpleNamespace(delete_from_gateway=lambda **_k: True)
    ok = host._delete_from_gateway_impl(
        gateway="https://prom", run_label="r1", labels={"job": "bioetl"}
    )
    assert ok.success is True


def test_column_service_empty_and_static_delegates() -> None:
    service = ColumnOrderService(logger=MagicMock())
    assert service.order_column_names([]) == []
    assert isinstance(service.order_column_names(["id", "name"]), list)
    assert ColumnOrderService._apply_renames_stage(["a"], {"a": "b"}) == ["b"]
    assert ColumnOrderService.get_enricher_prefix("chembl_activity").endswith(".")
    assert ColumnOrderService._parse_pipeline_name("chembl_activity") == (
        "chembl",
        "activity",
    )
    assert extract_field_from_qualified_name("a.b") == "b"
    group = ColumnGroupConfig(name="g", pattern="id")
    object.__setattr__(group, "pattern", "[")
    assert (
        collect_pattern_columns(
            {"id"}, set(), group, lambda cols, _o: cols, MagicMock()
        )
        == []
    )
    empty_group = ColumnGroupConfig(name="g", fields=("id",))
    object.__setattr__(empty_group, "pattern", None)
    assert (
        collect_pattern_columns(
            {"id"}, set(), empty_group, lambda cols, _o: cols, MagicMock()
        )
        == []
    )


def test_openalex_author_helpers_skip_non_list_institutions() -> None:
    payload = [
        {"institutions": "bad"},
        {"institutions": [None, {"id": "https://openalex.org/I1"}]},
    ]
    assert oa.extract_affiliations(payload) == []
    ids = oa.extract_institution_ids(payload)
    assert ids in ([], ["I1"])
    assert oa.extract_institution_ror_ids(payload) == []
