"""Focused infrastructure tests for small coverage residuals in #10469."""

from __future__ import annotations

from contextlib import nullcontext
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
