"""Runtime policy boundaries preserve structural validation and original errors."""

from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from bioetl.infrastructure.adapters.decorators.circuit_breaker import (
    CircuitBreakerDataSourceDecorator,
)
from bioetl.infrastructure.adapters.uniprot import _idmapping_transport as mapping
from bioetl.infrastructure.quality import architecture_debt_task_support as debt
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

pytestmark = pytest.mark.unit


def test_fallback_complexity_still_counts_branching_when_radon_is_unavailable(
    monkeypatch,
):
    monkeypatch.setattr(
        debt, "import_module", Mock(side_effect=ImportError("optional radon absent"))
    )
    metrics = debt.function_complexities(
        "def choose(value):\n    if value:\n        return 1\n    return 0\n"
    )
    assert metrics == {"choose": 2}


def test_exported_pipeline_schema_keeps_layer_specific_write_modes():
    sink = PipelineYamlConfig.model_json_schema()["properties"]["sink"]
    assert sink["additionalProperties"] is False
    assert sink["properties"]["bronze"]["properties"]["mode"]["enum"] == [
        "append",
        None,
    ]
    assert sink["properties"]["silver"]["properties"]["mode"]["enum"] == [
        "append",
        "merge",
        None,
    ]
    assert "scd2" in sink["properties"]["gold"]["properties"]["mode"]["enum"]


@pytest.mark.asyncio
async def test_circuit_breaker_records_failure_without_changing_original_exception():
    from bioetl.domain.exceptions import BioETLError

    error = BioETLError("source failed")

    async def fetch(**kwargs):
        raise error
        yield  # pragma: no cover - async iterator shape

    async def call(operation):
        return await operation()

    from bioetl.domain.types import CircuitBreakerState

    breaker = SimpleNamespace(
        call=AsyncMock(side_effect=call),
        get_state=lambda: CircuitBreakerState.CLOSED,
        get_failure_count=lambda: 1,
        recovery_timeout=60.0,
    )
    source = SimpleNamespace(provider_name="chembl", fetch=fetch)
    decorator = CircuitBreakerDataSourceDecorator(source, breaker, Mock())
    from bioetl.infrastructure.adapters.decorators._data_source_delegation import (
        DataSourceFetchRequest,
    )

    with pytest.raises(BioETLError) as caught:
        _ = [
            row
            async for row in decorator._iterate_with_error_recording(
                DataSourceFetchRequest(entity_type="assay")
            )
        ]
    assert caught.value is error
    breaker.call.assert_awaited_once()


@pytest.mark.asyncio
async def test_idmapping_repeated_next_page_is_bounded(monkeypatch):
    monkeypatch.setattr(mapping, "_MAX_RESULT_PAGES", 1)
    client = mapping.IDMappingTransportMixin()
    response = SimpleNamespace(
        status_code=200, json=lambda: {"results": []}, headers={}
    )
    deps = SimpleNamespace(
        base_url="https://rest.uniprot.org",
        http_client=SimpleNamespace(get=AsyncMock(return_value=response)),
        _adapter_metrics=SimpleNamespace(
            measure_request=lambda endpoint: nullcontext()
        ),
        _append_mapping_results=lambda *args: True,
        _get_next_page_url=lambda headers: (
            "https://rest.uniprot.org/idmapping/results/job"
        ),
    )
    monkeypatch.setattr(client, "_transport_deps", lambda: deps)
    monkeypatch.setattr(client, "_results_redirect", lambda *args, **kwargs: None)
    with pytest.raises(mapping.IDMappingJobError, match="page limit exceeded"):
        await client._fetch_results_pages(
            "job", {}, "https://rest.uniprot.org/idmapping/results/job"
        )
    deps.http_client.get.assert_awaited_once()
