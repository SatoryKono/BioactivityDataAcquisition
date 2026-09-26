"""Focused infrastructure tests for small coverage residuals in #10469."""

from __future__ import annotations

from contextlib import nullcontext
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.chembl._entity_mapping_lookup import (
    has_entity_composite_key,
)
from bioetl.infrastructure.adapters.chembl.entity_mapper import ChemblEntityMapper
from bioetl.infrastructure.adapters.common.adapter_defaults import (
    create_default_fallback_service,
)
from bioetl.infrastructure.adapters.crossref.client_runtime_helpers import (
    _require_runtime_service,
)
from bioetl.infrastructure.adapters.health_status_policy import (
    classify_health_probe_status,
)
from bioetl.infrastructure.adapters.decorators._data_source_delegation import (
    DataSourceFetchRequest,
)
from bioetl.infrastructure.adapters.http.health import (
    assess_health_from_circuit_breaker,
)
from bioetl.infrastructure.adapters.http._client_retry_policy import (
    _record_request_metrics,
)
from bioetl.infrastructure.adapters.openalex.query_execution import (
    OpenAlexQueryExecutor,
)
from bioetl.infrastructure.adapters.pubchem._fetch_strategy_transport import (
    resolve_transport_bag,
)
from bioetl.infrastructure.adr._adr_file_utils import parse_adr_filename
from bioetl.infrastructure.config._dq_config_layers import _load_unified_quality_layer
from bioetl.infrastructure.config._dq_config_normalization import (
    normalize_to_file_format,
)
from bioetl.infrastructure.config._dq_config_validation_merge import (
    merge_validation_lists_for_key,
)
from bioetl.infrastructure.control_plane.archive_run_reports import _identity_matches
from bioetl.infrastructure.control_plane.file_historical_replay_universe_store import (
    FileHistoricalReplayUniverseStore,
)
from bioetl.infrastructure.observability.required_publication_series import (
    _child_exists,
)
from bioetl.infrastructure.quality.architecture_debt_task_policy import (
    load_yaml_if_present,
)
from bioetl.infrastructure.quality.architecture_quality_scoring import _lazy_import_util
from bioetl.infrastructure.quality.exemptions_registry_paths import (
    build_module_path_key,
)
from bioetl.infrastructure.storage.audit_normalization import require_audit_timestamp

pytestmark = pytest.mark.unit


def test_chembl_composite_key_helpers_delegate_registry_answer() -> None:
    assert has_entity_composite_key("publication_term") is True
    assert ChemblEntityMapper.has_composite_key("publication_term") is True


def test_default_fallback_service_preserves_metrics_dependency() -> None:
    metrics = MagicMock()
    service = create_default_fallback_service(adapter_metrics=metrics)
    assert service._adapter_metrics is metrics


def test_crossref_runtime_service_rejects_missing_dependency() -> None:
    with pytest.raises(ValueError, match="requires injected logger"):
        _require_runtime_service(None, name="logger")


def test_unknown_health_status_code_is_unhealthy() -> None:
    assert classify_health_probe_status(418) is HealthStatus.UNHEALTHY


def test_http_metrics_noop_when_metrics_are_disabled() -> None:
    assert _record_request_metrics(None, "chembl", "get", 0.1, 200, 0, None) is None


@pytest.mark.asyncio
async def test_openalex_query_executor_maps_non_object_json_to_empty_mapping() -> None:
    response = MagicMock()
    response.json.return_value = ["not", "an", "object"]
    http_client = MagicMock()
    http_client.get = MagicMock(return_value=None)

    async def get(*args: object, **kwargs: object) -> object:
        return response

    http_client.get = get
    executor = OpenAlexQueryExecutor(
        http_client=http_client,
        adapter_metrics=SimpleNamespace(measure_request=lambda _: nullcontext()),
        request_collector=MagicMock(),
        headers_provider=lambda: {},
        api_base="https://api.openalex.org",
    )
    assert await executor.request_works_payload({"filter": "x"}) == {}


def test_pubchem_transport_bag_rejects_unknown_legacy_keyword() -> None:
    with pytest.raises(TypeError, match="unexpected keyword.*unknown"):
        resolve_transport_bag(None, {"unknown": 1})


def test_adr_filename_parser_rejects_noncanonical_name() -> None:
    assert parse_adr_filename(Path("README.md")) is None


def test_unified_quality_layer_returns_flat_legacy_payload(tmp_path: Path) -> None:
    path = tmp_path / "provider.yaml"
    path.write_text("placeholder", encoding="utf-8")
    payload = {"thresholds": {"soft_fail": 0.1}}
    assert (
        _load_unified_quality_layer(
            layer_path=path,
            fallback_keys=("thresholds",),
            load_yaml=lambda _: payload,
        )
        is payload
    )


def test_dq_threshold_normalization_replaces_non_mapping_container() -> None:
    assert normalize_to_file_format(
        {"thresholds": "invalid", "soft_fail_threshold": 0.1}
    ) == {"thresholds": {"soft_fail": 0.1}}


def test_validation_list_merge_replaces_heterogeneous_override() -> None:
    override = ["replacement"]
    result = merge_validation_lists_for_key(
        [{"type": "range"}], override, "validations"
    )
    assert result == override
    assert result is not override


def test_data_source_fetch_request_exposes_all_port_arguments() -> None:
    request = DataSourceFetchRequest(
        entity_type="publication",
        limit=10,
        query="kinase",
        filter_ids=["1"],
        filter_field="pmid",
        offset=2,
    )

    assert request.as_kwargs() == {
        "entity_type": "publication",
        "limit": 10,
        "query": "kinase",
        "filter_ids": ["1"],
        "filter_field": "pmid",
        "offset": 2,
    }


def test_half_open_circuit_breaker_is_degraded() -> None:
    circuit_breaker = MagicMock()
    circuit_breaker.get_state.return_value = SimpleNamespace(value="HALF_OPEN")
    circuit_breaker.get_failure_count.return_value = 1

    assert assess_health_from_circuit_breaker(circuit_breaker) is HealthStatus.DEGRADED


def test_archive_identity_rejects_non_mapping_payload() -> None:
    assert _identity_matches("invalid", MagicMock()) is False


def test_historical_universe_store_returns_none_when_directory_is_absent(
    tmp_path: Path,
) -> None:
    store = FileHistoricalReplayUniverseStore(tmp_path / "missing")

    assert store.load_latest_report() is None


def test_prometheus_child_lookup_rejects_non_mapping_registry() -> None:
    metric = SimpleNamespace(_metrics=None, _labelnames=("pipeline",))

    assert _child_exists(metric, {"pipeline": "chembl_assay"}) is False


def test_missing_architecture_task_yaml_loads_as_empty_mapping(tmp_path: Path) -> None:
    assert load_yaml_if_present(tmp_path / "missing.yaml") == {}


def test_lazy_import_utilization_reports_bounded_ratio() -> None:
    assert _lazy_import_util(observed=7, cap=10) == 0.7


def test_module_path_key_resolves_relative_source_root() -> None:
    assert (
        build_module_path_key(
            Path.cwd() / "src/bioetl/domain/example.py",
            src_root="src",
        )
        == "src/bioetl/domain/example.py"
    )


def test_audit_timestamp_rejects_naive_datetime() -> None:
    with pytest.raises(ValueError, match="must be timezone-aware"):
        require_audit_timestamp(
            logger=MagicMock(),
            timestamp=datetime(2026, 1, 1),
            table_name="assay",
            mode="append",
        )


def test_infrastructure_export_facade_rejects_unknown_attribute() -> None:
    import bioetl.infrastructure.export as export_facade

    with pytest.raises(AttributeError, match="has no attribute 'unknown_export'"):
        export_facade.__getattr__("unknown_export")
