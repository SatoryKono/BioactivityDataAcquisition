# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Contract tests for provider adapter fetch orchestration surfaces."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.composition.factories.datasource.crossref import create_crossref_adapter
from bioetl.domain.ports import FallbackPolicyPort
from bioetl.infrastructure.adapters.crossref import CrossRefAdapter
from bioetl.infrastructure.adapters.openalex import OpenAlexAdapter
from bioetl.infrastructure.adapters.pubmed import PubMedAdapter
from bioetl.infrastructure.adapters.semanticscholar import SemanticScholarAdapter
from bioetl.infrastructure.adapters.uniprot import UniProtAdapter
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from tests.helpers.adapter_runtime import build_http_adapter_runtime_kwargs


@pytest.fixture
def mock_http_client() -> MagicMock:
    client = MagicMock()
    client.get = AsyncMock()
    client.get_once = AsyncMock()
    client.post = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    client.circuit_breaker = MagicMock()
    return client


@pytest.fixture
def openalex_adapter(mock_http_client: MagicMock) -> OpenAlexAdapter:
    logger = NoOpLogger()
    return OpenAlexAdapter(
        http_client=mock_http_client,
        logger=logger,
        mailto="test@example.com",
        batch_size=10,
        **build_http_adapter_runtime_kwargs(
            "openalex",
            logger=logger,
            include_fallback_service=True,
        ),
    )


@pytest.fixture
def crossref_adapter(mock_http_client: MagicMock) -> CrossRefAdapter:
    return create_crossref_adapter(
        http_client=mock_http_client,
        logger=NoOpLogger(),
        settings=None,
        mailto="test@example.com",
        batch_size=10,
    )


@pytest.fixture
def pubmed_adapter(mock_http_client: MagicMock) -> PubMedAdapter:
    logger = NoOpLogger()
    return PubMedAdapter(
        http_client=mock_http_client,
        logger=logger,
        email="test@example.com",
        **build_http_adapter_runtime_kwargs(
            "pubmed",
            logger=logger,
            include_fallback_service=True,
        ),
    )


@pytest.fixture
def semanticscholar_adapter(
    mock_http_client: MagicMock,
) -> SemanticScholarAdapter:
    logger = NoOpLogger()
    return SemanticScholarAdapter(
        http_client=mock_http_client,
        logger=logger,
        api_key="",
        batch_size=10,
        **build_http_adapter_runtime_kwargs(
            "semanticscholar",
            logger=logger,
            include_fallback_service=True,
        ),
    )


@pytest.fixture
def uniprot_adapter(mock_http_client: MagicMock) -> UniProtAdapter:
    logger = NoOpLogger()
    return UniProtAdapter(
        http_client=mock_http_client,
        logger=logger,
        **build_http_adapter_runtime_kwargs(
            "uniprot",
            logger=logger,
            include_fallback_service=True,
        ),
    )


@pytest.mark.asyncio
async def test_openalex_fetch_contract_routes_to_fetch_filtered(
    openalex_adapter: OpenAlexAdapter,
) -> None:
    async def fake_fetch_filtered(entity_type, filter_ids, filter_field, limit=None):
        assert entity_type == "publication"
        assert filter_ids == ["10.1038/test"]
        assert filter_field == "doi"
        assert limit == 1
        yield {"id": "W1"}

    openalex_adapter.fetch_filtered = fake_fetch_filtered  # type: ignore[assignment]
    rows = [
        row
        async for row in openalex_adapter.fetch(
            entity_type="publication",
            filter_ids=["10.1038/test"],
            filter_field="doi",
            limit=1,
        )
    ]
    assert rows == [{"id": "W1"}]


@pytest.mark.asyncio
async def test_openalex_fetch_filtered_contract_uses_doi_branch(
    openalex_adapter: OpenAlexAdapter,
) -> None:
    async def fake_fetch_filtered_by_doi(filter_ids, limit=None):
        assert filter_ids == ["10.1038/test"]
        assert limit == 2
        yield {"id": "W1"}

    openalex_adapter._fetch_filtered_by_doi = fake_fetch_filtered_by_doi  # type: ignore[method-assign]
    rows = [
        row
        async for row in openalex_adapter.fetch_filtered(
            entity_type="publication",
            filter_ids=["10.1038/test"],
            filter_field="doi",
            limit=2,
        )
    ]
    assert rows == [{"id": "W1"}]


@pytest.mark.asyncio
async def test_openalex_fetch_filtered_with_fallback_contract_uses_policy_port(
    openalex_adapter: OpenAlexAdapter,
) -> None:
    captured_request: dict[str, object] = {}

    async def fake_execute(request):
        captured_request["request"] = request
        yield {"id": "W2", "_lookup_method": "fallback"}

    openalex_adapter._fallback_fetch_service.execute = fake_execute  # type: ignore[method-assign]

    rows = [
        row
        async for row in openalex_adapter.fetch_filtered_with_fallback(
            entity_type="publication",
            filter_ids=["10.1038/test", "__title_only_0__"],
            filter_field="doi",
            fallback_mapping={"__title_only_0__": "Fallback title"},
            limit=3,
        )
    ]
    assert rows == [{"id": "W2", "_lookup_method": "fallback"}]
    request = captured_request["request"]
    assert isinstance(request.fallback_handler, FallbackPolicyPort)


@pytest.mark.asyncio
async def test_uniprot_fetch_contract_routes_to_fetch_filtered(
    uniprot_adapter: UniProtAdapter,
) -> None:
    async def fake_fetch_filtered(entity_type, filter_ids, filter_field, limit=None):
        assert entity_type == "protein"
        assert filter_ids == ["P12345"]
        assert filter_field == "accession"
        assert limit == 1
        yield {"accession": "P12345"}

    uniprot_adapter.fetch_filtered = fake_fetch_filtered  # type: ignore[assignment]
    rows = [
        row
        async for row in uniprot_adapter.fetch(
            entity_type="protein",
            filter_ids=["P12345"],
            filter_field="accession",
            limit=1,
        )
    ]
    assert rows == [{"accession": "P12345"}]


@pytest.mark.asyncio
async def test_uniprot_fetch_filtered_contract_supports_non_protein_strategy(
    uniprot_adapter: UniProtAdapter,
) -> None:
    async def feature_strategy(query=None, limit=None):
        yield {"feature_id": query, "limit": limit}

    uniprot_adapter._fetch_strategies["feature"] = feature_strategy
    rows = [
        row
        async for row in uniprot_adapter.fetch_filtered(
            entity_type="feature",
            filter_ids=["F1", "F2"],
            filter_field="accession",
            limit=2,
        )
    ]
    assert [row["feature_id"] for row in rows] == ["F1", "F2"]


@pytest.mark.asyncio
async def test_uniprot_fetch_filtered_with_fallback_contract_uses_policy_port(
    uniprot_adapter: UniProtAdapter,
) -> None:
    captured_request: dict[str, object] = {}

    async def fake_execute(request):
        captured_request["request"] = request
        yield {"accession": "P12345", "_lookup_method": "primary"}
        yield {"accession": "Q67890", "_lookup_method": "fallback"}

    uniprot_adapter._fallback_fetch_service.execute = fake_execute  # type: ignore[method-assign]

    rows = [
        row
        async for row in uniprot_adapter.fetch_filtered_with_fallback(
            entity_type="protein",
            filter_ids=["P12345", "Q67890"],
            filter_field="accession",
            fallback_mapping={"Q67890": "GENE2"},
            limit=5,
        )
    ]
    assert [row["accession"] for row in rows] == ["P12345", "Q67890"]
    request = captured_request["request"]
    assert isinstance(request.fallback_handler, FallbackPolicyPort)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("adapter_name", "call_kwargs", "expected_id_field"),
    [
        (
            "crossref_adapter",
            {
                "entity_type": "publication",
                "filter_ids": ["10.1038/test", "__title_only_0__"],
                "filter_field": "doi",
                "fallback_mapping": {"__title_only_0__": "Fallback title"},
                "limit": 3,
            },
            "DOI",
        ),
        (
            "pubmed_adapter",
            {
                "entity_type": "publication",
                "filter_ids": ["12345", "__title_only_0__"],
                "filter_field": "pmid",
                "fallback_mapping": {"__title_only_0__": "Fallback title"},
                "limit": 3,
            },
            "pmid",
        ),
        (
            "semanticscholar_adapter",
            {
                "entity_type": "publication",
                "filter_ids": ["10.1038/test", "__title_only_0__"],
                "filter_field": "doi",
                "fallback_mapping": {"__title_only_0__": "Fallback title"},
                "limit": 3,
            },
            "paperId",
        ),
    ],
)
async def test_provider_fetch_filtered_with_fallback_contract_uses_policy_port(
    request: pytest.FixtureRequest,
    adapter_name: str,
    call_kwargs: dict[str, object],
    expected_id_field: str,
) -> None:
    adapter = request.getfixturevalue(adapter_name)
    captured_request: dict[str, object] = {}

    async def fake_execute(fetch_request):
        captured_request["request"] = fetch_request
        yield {expected_id_field: "ID-1", "_lookup_method": "fallback"}

    adapter._fallback_fetch_service.execute = fake_execute  # type: ignore[method-assign]

    rows = [row async for row in adapter.fetch_filtered_with_fallback(**call_kwargs)]
    assert rows == [{expected_id_field: "ID-1", "_lookup_method": "fallback"}]
    fetch_request = captured_request["request"]
    assert isinstance(fetch_request.fallback_handler, FallbackPolicyPort)
