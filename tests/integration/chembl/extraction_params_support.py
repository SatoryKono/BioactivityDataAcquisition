"""Shared support for ChEMBL extraction-params integration tests."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from bioetl.domain.models.filter import ExtractionParams
from bioetl.domain.resilience import AdapterConfig
from bioetl.infrastructure.adapters.chembl import ChemblAdapter

CASSETTE_DIR = Path(__file__).parent.parent / "fixtures" / "vcr" / "chembl"


@dataclass(frozen=True, slots=True)
class ExtractionParamsCase:
    """Declarative test case for one ChEMBL entity extraction-params suite."""

    entity_type: str
    params: dict[str, object]
    expected_query_parts: tuple[str, ...]
    record_id_field: str
    input_filter_field: str | None = None
    cassette_names: tuple[str, ...] = ()
    cassette_hint: str = ""


def has_any_cassette(*cassette_names: str) -> bool:
    """Return whether any supported cassette filename exists."""
    return any(
        (CASSETTE_DIR / cassette_name).exists() for cassette_name in cassette_names
    )


def build_missing_cassette_reason(cassette_hint: str) -> str:
    """Build a stable skip reason for not-yet-recorded VCR cassettes."""
    return (
        "VCR cassette not yet recorded. "
        f"Record with: VCR_RECORD_MODE=new_episodes pytest -k {cassette_hint}"
    )


def _build_extraction_params(case: ExtractionParamsCase) -> ExtractionParams:
    return ExtractionParams(params=case.params)


def build_chembl_adapter(
    *,
    case: ExtractionParamsCase,
    http_client: Any,
    logger: MagicMock,
    page_size: int | None = None,
) -> ChemblAdapter:
    """Create one adapter configured with extraction params for the case."""
    adapter_config = None
    if page_size is not None:
        adapter_config = AdapterConfig(page_size=page_size)
    return ChemblAdapter(
        http_client=http_client,
        logger=logger,
        adapter_config=adapter_config,
        extraction_params=_build_extraction_params(case),
    )


def assert_build_params(
    *,
    case: ExtractionParamsCase,
    params: dict[str, object],
    page_size: int,
) -> None:
    """Assert common pagination params and all case-specific extraction params."""
    assert params["format"] == "json"
    assert params["limit"] == page_size
    assert params["offset"] == 0
    for key, expected_value in case.params.items():
        assert params[key] == expected_value


def assert_query_string_contains(
    *,
    case: ExtractionParamsCase,
    query_string: str,
) -> None:
    """Assert every expected query-string fragment is present."""
    for expected_part in case.expected_query_parts:
        assert expected_part in query_string


def assert_query_string_is_deterministic(
    extraction_params: ExtractionParams,
) -> None:
    """Assert stable sorted-key query-string generation across invocations."""
    qs1 = extraction_params.to_query_string()
    qs2 = extraction_params.to_query_string()
    assert qs1 == qs2
    keys = [part.split("=")[0] for part in qs1.split("&")]
    assert keys == sorted(keys)


def assert_metadata_records_extraction_params(
    *,
    case: ExtractionParamsCase,
    adapter: ChemblAdapter,
) -> None:
    """Assert adapter metadata serializes extraction params into query_string."""
    metadata = adapter.get_source_metadata()
    assert metadata.query_string is not None
    assert_query_string_contains(
        case=case,
        query_string=metadata.query_string,
    )


def assert_extraction_params_logged_at_init(
    *,
    case: ExtractionParamsCase,
    logger: MagicMock,
) -> None:
    """Assert adapter init emits one audit log for configured params."""
    info_calls = [
        call
        for call in logger.info.call_args_list
        if call.args and call.args[0] == "chembl_extraction_params_configured"
    ]
    assert len(info_calls) == 1
    kwargs = info_calls[0].kwargs
    assert kwargs["param_count"] == len(case.params)
    first_param_name = next(iter(case.params))
    assert first_param_name in kwargs["query_string"]


def assert_input_filter_field_not_overlapping(case: ExtractionParamsCase) -> None:
    """Assert entity input-filter field is not duplicated in extraction params."""
    assert case.input_filter_field is not None
    assert case.input_filter_field not in case.params


async def run_filtered_api_request_test(
    *,
    case: ExtractionParamsCase,
    token_bucket: Any,
    circuit_breaker: Any,
    logger: MagicMock,
) -> None:
    """Run the shared filtered-request integration flow against one entity."""
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient

    client = UnifiedHTTPClient(
        rate_limiter=token_bucket,
        circuit_breaker=circuit_breaker,
        timeout=30.0,
    )

    async with client:
        adapter = build_chembl_adapter(
            case=case,
            http_client=client,
            logger=logger,
            page_size=10,
        )

        records: list[dict[str, Any]] = []
        async for record in adapter.fetch(case.entity_type, limit=5):
            records.append(record)

        assert len(records) > 0
        for record in records:
            assert case.record_id_field in record

        assert_metadata_records_extraction_params(
            case=case,
            adapter=adapter,
        )


@pytest.fixture(scope="module")
def vcr_config() -> dict[str, Any]:
    """Configure VCR for shared ChEMBL extraction params tests."""
    return {
        "cassette_library_dir": str(CASSETTE_DIR),
        "record_mode": os.environ.get("VCR_RECORD_MODE", "none"),
        "match_on": ["method", "scheme", "host", "port", "path", "query"],
        "decode_compressed_response": True,
    }


@pytest.fixture
def extraction_params(extraction_case: ExtractionParamsCase) -> ExtractionParams:
    """Build entity-specific extraction params from one declarative case."""
    return _build_extraction_params(extraction_case)


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create a mock logger for testing."""
    return MagicMock()


@pytest.fixture
def mock_http_client() -> MagicMock:
    """Create a mock HTTP client."""
    from bioetl.domain.types import CircuitBreakerState

    client = MagicMock()
    client.circuit_breaker = MagicMock()
    client.circuit_breaker.get_state.return_value = CircuitBreakerState.CLOSED
    client.circuit_breaker.get_failure_count.return_value = 0
    return client
