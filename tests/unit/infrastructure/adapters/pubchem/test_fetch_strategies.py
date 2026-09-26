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
"""Unit tests for infrastructure/adapters/pubchem/fetch_strategies.py.

Tests PubChemFetchStrategies helper class for different fetch modes.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.infrastructure.adapters.pubchem.fetch_strategies import (
    PubChemFetchStrategies,
)


@pytest.fixture
def mock_logger():
    """Create a mock LoggerPort."""
    logger = MagicMock()
    logger.warning = MagicMock()
    logger.info = MagicMock()
    logger.debug = MagicMock()
    return logger


@pytest.fixture
def mock_rate_limiter():
    """Create a mock TokenBucketRateLimiter rate limiter."""
    limiter = MagicMock()
    limiter.acquire = AsyncMock()
    return limiter


@pytest.fixture
def mock_circuit_breaker():
    """Create a mock CircuitBreakerGuard."""
    breaker = MagicMock()
    breaker.call = AsyncMock()
    return breaker


@pytest.fixture
def mock_entity_mapper():
    """Create a mock PubChemEntityMapper."""
    mapper = MagicMock()
    mapper.compound_to_dict = MagicMock(
        side_effect=lambda c: {
            "molecule_id": getattr(c, "molecule_id", 1),
            "name": "test_compound",
        }
    )
    mapper.substance_to_dict = MagicMock(
        side_effect=lambda s: {"sid": getattr(s, "sid", 1), "name": "test_substance"}
    )
    mapper.assay_to_dict = MagicMock(
        side_effect=lambda a: {"aid": getattr(a, "aid", 1), "name": "test_assay"}
    )
    return mapper


@pytest.fixture
def mock_run_in_executor():
    """Create a mock run_in_executor function."""
    return AsyncMock()


@pytest.fixture
def fetch_strategies(
    mock_logger,
    mock_rate_limiter,
    mock_circuit_breaker,
    mock_entity_mapper,
    mock_run_in_executor,
):
    """Create a PubChemFetchStrategies instance with mocked dependencies."""
    return PubChemFetchStrategies(
        logger=mock_logger,
        rate_limiter=mock_rate_limiter,
        circuit_breaker=mock_circuit_breaker,
        mapper=mock_entity_mapper,
        run_in_executor=mock_run_in_executor,
        provider_name="pubchem",
    )


async def collect_async_iterator(
    async_iter: AsyncIterator[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Helper to collect all items from an async iterator."""
    result = []
    async for item in async_iter:
        result.append(item)
    return result


async def drain_async_iterator(async_iter: AsyncIterator[Any]) -> None:
    """Consume an async iterator until completion."""
    async for _ in async_iter:
        continue


@pytest.mark.unit
class TestPubChemFetchStrategiesInit:
    """Tests for PubChemFetchStrategies initialization."""

    def test_init_stores_dependencies(
        self,
        mock_logger,
        mock_rate_limiter,
        mock_circuit_breaker,
        mock_entity_mapper,
        mock_run_in_executor,
    ):
        """Test that __init__ stores all dependencies correctly."""
        strategies = PubChemFetchStrategies(
            logger=mock_logger,
            rate_limiter=mock_rate_limiter,
            circuit_breaker=mock_circuit_breaker,
            mapper=mock_entity_mapper,
            run_in_executor=mock_run_in_executor,
            provider_name="test_provider",
        )

        assert strategies._logger is mock_logger
        assert strategies._rate_limiter is mock_rate_limiter
        assert strategies._circuit_breaker is mock_circuit_breaker
        assert strategies._mapper is mock_entity_mapper
        assert strategies._run_in_executor is mock_run_in_executor
        assert strategies._provider_name == "test_provider"

    def test_init_preserves_injected_collaborators(
        self,
        mock_logger,
        mock_rate_limiter,
        mock_circuit_breaker,
        mock_entity_mapper,
        mock_run_in_executor,
    ):
        """Injected mapper collaborators should bypass inline construction."""
        response_mapper = MagicMock()
        fetch_flow = MagicMock()

        strategies = PubChemFetchStrategies(
            logger=mock_logger,
            rate_limiter=mock_rate_limiter,
            circuit_breaker=mock_circuit_breaker,
            mapper=mock_entity_mapper,
            run_in_executor=mock_run_in_executor,
            response_mapper=response_mapper,
            fetch_flow=fetch_flow,
        )

        assert strategies._response_mapper is response_mapper
        assert strategies._fetch_flow is fetch_flow

    def test_init_default_provider_name(
        self,
        mock_logger,
        mock_rate_limiter,
        mock_circuit_breaker,
        mock_entity_mapper,
        mock_run_in_executor,
    ):
        """Test that default provider_name is 'pubchem'."""
        strategies = PubChemFetchStrategies(
            logger=mock_logger,
            rate_limiter=mock_rate_limiter,
            circuit_breaker=mock_circuit_breaker,
            mapper=mock_entity_mapper,
            run_in_executor=mock_run_in_executor,
        )

        assert strategies._provider_name == "pubchem"

    def test_record_request_uses_collector_when_available(
        self,
        mock_logger,
        mock_rate_limiter,
        mock_circuit_breaker,
        mock_entity_mapper,
        mock_run_in_executor,
    ):
        """Request collector receives canonical PubChem URL and estimated size."""
        collector = MagicMock()
        strategies = PubChemFetchStrategies(
            logger=mock_logger,
            rate_limiter=mock_rate_limiter,
            circuit_breaker=mock_circuit_breaker,
            mapper=mock_entity_mapper,
            run_in_executor=mock_run_in_executor,
            request_collector=collector,
        )

        strategies._record_request("/compound/name/water/json", 12.5, result_count=3)

        collector.record_request.assert_called_once_with(
            url="https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/water/json",
            method="GET",
            response_size=6000,
            duration_ms=12.5,
            status_code=200,
        )


@pytest.mark.unit
class TestFetchByQuery:
    """Tests for fetch_by_query method."""

    @pytest.mark.asyncio
    async def test_fetch_by_query_acquires_rate_limit(
        self, fetch_strategies, mock_rate_limiter, mock_circuit_breaker
    ):
        """Test that fetch_by_query acquires rate limit."""
        mock_circuit_breaker.call.return_value = []

        await drain_async_iterator(fetch_strategies.fetch_by_query("aspirin", limit=10))

        mock_rate_limiter.acquire.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_by_query_uses_circuit_breaker(
        self, fetch_strategies, mock_circuit_breaker
    ):
        """Test that fetch_by_query uses circuit breaker."""
        mock_circuit_breaker.call.return_value = []

        await drain_async_iterator(fetch_strategies.fetch_by_query("aspirin", limit=10))

        mock_circuit_breaker.call.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_by_query_yields_compounds(
        self, fetch_strategies, mock_circuit_breaker, mock_entity_mapper
    ):
        """Test that fetch_by_query yields compound dictionaries."""
        mock_compound1 = MagicMock(molecule_id=2244)
        mock_compound2 = MagicMock(molecule_id=3672)
        mock_circuit_breaker.call.return_value = [mock_compound1, mock_compound2]

        results = await collect_async_iterator(
            fetch_strategies.fetch_by_query("aspirin", limit=None)
        )

        assert len(results) == 2
        assert mock_entity_mapper.compound_to_dict.call_count == 2

    @pytest.mark.asyncio
    async def test_fetch_by_query_respects_limit(
        self, fetch_strategies, mock_circuit_breaker
    ):
        """Test that fetch_by_query respects limit parameter."""
        mock_compounds = [MagicMock(molecule_id=i) for i in range(10)]
        mock_circuit_breaker.call.return_value = mock_compounds

        results = await collect_async_iterator(
            fetch_strategies.fetch_by_query("aspirin", limit=3)
        )

        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_fetch_by_query_handles_empty_result(
        self, fetch_strategies, mock_circuit_breaker
    ):
        """Test that fetch_by_query handles empty results."""
        mock_circuit_breaker.call.return_value = []

        results = await collect_async_iterator(
            fetch_strategies.fetch_by_query("nonexistent", limit=None)
        )

        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_fetch_by_query_handles_none_result(
        self, fetch_strategies, mock_circuit_breaker
    ):
        """Test that fetch_by_query handles None result from API."""
        mock_circuit_breaker.call.return_value = None

        results = await collect_async_iterator(
            fetch_strategies.fetch_by_query("nonexistent", limit=None)
        )

        assert len(results) == 0


@pytest.mark.unit
class TestFetchBySmiles:
    """Tests for fetch_by_smiles method."""

    @pytest.mark.asyncio
    async def test_fetch_by_smiles_yields_compounds(
        self, fetch_strategies, mock_circuit_breaker, mock_entity_mapper
    ):
        """Test that fetch_by_smiles yields compound dictionaries."""
        mock_compound = MagicMock(molecule_id=2244)
        mock_circuit_breaker.call.return_value = [mock_compound]

        smiles_list = ["CC(=O)OC1=CC=CC=C1C(=O)O"]
        results = await collect_async_iterator(
            fetch_strategies.fetch_by_smiles(smiles_list, limit=None)
        )

        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_fetch_by_smiles_skips_empty_smiles(
        self, fetch_strategies, mock_circuit_breaker
    ):
        """Test that fetch_by_smiles skips empty SMILES strings."""
        mock_compound = MagicMock(molecule_id=2244)
        mock_circuit_breaker.call.return_value = [mock_compound]

        smiles_list = ["", "  ", "CC(=O)OC1=CC=CC=C1C(=O)O", None]
        results = await collect_async_iterator(
            fetch_strategies.fetch_by_smiles(smiles_list, limit=None)
        )

        # Should only process non-empty SMILES
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_fetch_by_smiles_respects_limit(
        self, fetch_strategies, mock_circuit_breaker
    ):
        """Test that fetch_by_smiles respects limit parameter."""
        mock_compound = MagicMock(molecule_id=1)
        mock_circuit_breaker.call.return_value = [mock_compound]

        smiles_list = ["CC", "CCC", "CCCC", "CCCCC"]
        results = await collect_async_iterator(
            fetch_strategies.fetch_by_smiles(smiles_list, limit=2)
        )

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_fetch_by_smiles_limit_zero_skips_api_calls(
        self, fetch_strategies, mock_circuit_breaker
    ):
        """A zero limit should stop before scheduling the first chunk."""
        results = await collect_async_iterator(
            fetch_strategies.fetch_by_smiles(["CC", "CCC"], limit=0)
        )

        assert results == []
        mock_circuit_breaker.call.assert_not_called()

    @pytest.mark.asyncio
    async def test_fetch_by_smiles_stops_mid_chunk_when_limit_is_reached(
        self, fetch_strategies
    ):
        """The async chunk iterator can yield more records than the requested limit."""

        async def fake_iter_chunk_records(
            chunk: list[str],
        ) -> AsyncIterator[dict[str, int]]:
            assert chunk == ["CC", "CCC"]
            for molecule_id in (1, 2, 3):
                yield {"molecule_id": molecule_id}

        fetch_strategies._iter_smiles_chunk_records = fake_iter_chunk_records

        results = await collect_async_iterator(
            fetch_strategies.fetch_by_smiles(["CC", "CCC"], limit=2, batch_size=2)
        )

        assert results == [{"molecule_id": 1}, {"molecule_id": 2}]

    @pytest.mark.asyncio
    async def test_fetch_by_smiles_logs_warning_on_error(
        self, fetch_strategies, mock_circuit_breaker, mock_logger
    ):
        """Test that fetch_by_smiles logs warning when SMILES fetch fails."""
        mock_circuit_breaker.call.side_effect = RuntimeError("API error")

        smiles_list = ["invalid_smiles"]
        results = await collect_async_iterator(
            fetch_strategies.fetch_by_smiles(smiles_list, limit=None)
        )

        assert len(results) == 0
        mock_logger.warning.assert_called()
        call_args = mock_logger.warning.call_args
        assert call_args[0][0] == "smiles_fetch_failed"


@pytest.mark.unit
class TestParseValidCids:
    """Tests for _parse_valid_cids method."""

    def test_parse_valid_molecule_ids_converts_strings_to_ints(self, fetch_strategies):
        """Test that _parse_valid_cids converts string CIDs to integers."""
        molecule_id_list = ["2244", "3672", "5988"]

        result = fetch_strategies._parse_valid_cids(molecule_id_list)

        assert result == [2244, 3672, 5988]

    def test_parse_valid_molecule_ids_skips_invalid_molecule_ids(
        self, fetch_strategies, mock_logger
    ):
        """Test that _parse_valid_cids skips invalid CIDs and logs warning."""
        molecule_id_list = ["2244", "invalid", "3672", ""]

        result = fetch_strategies._parse_valid_cids(molecule_id_list)

        assert result == [2244, 3672]
        # Should log warnings for invalid CIDs
        assert mock_logger.warning.call_count >= 2


@pytest.mark.unit
class TestFetchByCids:
    """Tests for fetch_by_cids method."""

    @pytest.mark.asyncio
    async def test_fetch_by_cids_yields_compounds(
        self, fetch_strategies, mock_circuit_breaker
    ):
        """Test that fetch_by_cids yields compound dictionaries."""
        mock_compound = MagicMock(molecule_id=2244)
        mock_circuit_breaker.call.return_value = [mock_compound]

        molecule_id_list = ["2244"]
        results = await collect_async_iterator(
            fetch_strategies.fetch_by_cids(molecule_id_list, limit=None)
        )

        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_fetch_by_cids_batches_requests(
        self, fetch_strategies, mock_circuit_breaker
    ):
        """Test that fetch_by_cids batches requests."""
        mock_compound = MagicMock(molecule_id=1)
        mock_circuit_breaker.call.return_value = [mock_compound]

        # Create list with more CIDs than batch size
        molecule_id_list = [str(i) for i in range(120)]
        await collect_async_iterator(
            fetch_strategies.fetch_by_cids(molecule_id_list, limit=None, batch_size=50)
        )

        # Should have made 3 batches (50 + 50 + 20)
        assert mock_circuit_breaker.call.call_count == 3

    @pytest.mark.asyncio
    async def test_fetch_by_cids_respects_limit(
        self, fetch_strategies, mock_circuit_breaker
    ):
        """Test that fetch_by_cids respects limit parameter."""
        mock_compounds = [MagicMock(molecule_id=i) for i in range(10)]
        mock_circuit_breaker.call.return_value = mock_compounds

        molecule_id_list = [str(i) for i in range(100)]
        results = await collect_async_iterator(
            fetch_strategies.fetch_by_cids(molecule_id_list, limit=5, batch_size=50)
        )

        assert len(results) == 5

    @pytest.mark.asyncio
    async def test_fetch_by_cids_limit_zero_skips_first_batch(
        self, fetch_strategies, mock_circuit_breaker
    ):
        """A zero CID limit should return before issuing a batch request."""
        results = await collect_async_iterator(
            fetch_strategies.fetch_by_cids(["2244", "3672"], limit=0)
        )

        assert results == []
        mock_circuit_breaker.call.assert_not_called()

    @pytest.mark.asyncio
    async def test_fetch_by_cids_logs_warning_on_batch_error(
        self, fetch_strategies, mock_circuit_breaker, mock_logger
    ):
        """Test that fetch_by_cids logs warning when batch fetch fails."""
        mock_circuit_breaker.call.side_effect = RuntimeError("API error")

        molecule_id_list = ["2244", "3672"]
        results = await collect_async_iterator(
            fetch_strategies.fetch_by_cids(molecule_id_list, limit=None)
        )

        assert len(results) == 0
        mock_logger.warning.assert_called()
        call_args = mock_logger.warning.call_args
        assert call_args[0][0] == "molecule_id_batch_fetch_failed"


@pytest.mark.unit
class TestFetchByInchiKey:
    """Tests for fetch_by_inchikey method."""

    @pytest.mark.asyncio
    async def test_fetch_by_inchikey_yields_compounds(
        self, fetch_strategies, mock_circuit_breaker, mock_entity_mapper
    ):
        """Valid InChIKey values are routed through the PubChem compound mapper."""
        mock_compound = MagicMock(molecule_id=702)
        mock_circuit_breaker.call.return_value = [mock_compound]

        results = await collect_async_iterator(
            fetch_strategies.fetch_by_inchikey(
                ["BSYNRYMUTXBXSQ-UHFFFAOYSA-N"], limit=None
            )
        )

        assert len(results) == 1
        mock_entity_mapper.compound_to_dict.assert_called_once_with(mock_compound)

    @pytest.mark.asyncio
    async def test_fetch_by_inchikey_skips_blank_and_invalid_values(
        self, fetch_strategies, mock_circuit_breaker, mock_logger
    ):
        """Invalid InChIKey selectors should be skipped without network calls."""
        results = await collect_async_iterator(
            fetch_strategies.fetch_by_inchikey(["", "bad-key"], limit=None)
        )

        assert results == []
        mock_circuit_breaker.call.assert_not_called()
        mock_logger.warning.assert_called_once()
        assert mock_logger.warning.call_args[0][0] == "invalid_inchikey_skipped"

    @pytest.mark.asyncio
    async def test_fetch_by_inchikey_logs_fetch_errors(
        self, fetch_strategies, mock_circuit_breaker, mock_logger
    ):
        """Fetch strategy errors are logged and do not stop later chunk processing."""
        mock_circuit_breaker.call.side_effect = RuntimeError("API error")

        results = await collect_async_iterator(
            fetch_strategies.fetch_by_inchikey(
                ["BSYNRYMUTXBXSQ-UHFFFAOYSA-N"], limit=None
            )
        )

        assert results == []
        mock_logger.warning.assert_called()
        assert mock_logger.warning.call_args[0][0] == "inchikey_fetch_failed"

    @pytest.mark.asyncio
    async def test_fetch_by_inchikey_stops_mid_chunk_when_limit_is_reached(
        self, fetch_strategies
    ):
        """The InChIKey iterator enforces limits after records are yielded."""

        async def fake_iter_chunk_records(
            chunk: list[str],
        ) -> AsyncIterator[dict[str, int]]:
            assert chunk == [
                "BSYNRYMUTXBXSQ-UHFFFAOYSA-N",
                "LFQSCWFLJHTTHZ-UHFFFAOYSA-N",
            ]
            for molecule_id in (1, 2, 3):
                yield {"molecule_id": molecule_id}

        fetch_strategies._iter_inchikey_chunk_records = fake_iter_chunk_records

        results = await collect_async_iterator(
            fetch_strategies.fetch_by_inchikey(
                [
                    "BSYNRYMUTXBXSQ-UHFFFAOYSA-N",
                    "LFQSCWFLJHTTHZ-UHFFFAOYSA-N",
                ],
                limit=2,
                batch_size=2,
            )
        )

        assert results == [{"molecule_id": 1}, {"molecule_id": 2}]


@pytest.mark.unit
class TestFetchSubstances:
    """Tests for fetch_substances method."""

    @pytest.mark.asyncio
    async def test_fetch_substances_raises_on_empty_query(self, fetch_strategies):
        """Test that fetch_substances raises ValueError for empty query."""
        with pytest.raises(ValueError, match="Query is required"):
            await drain_async_iterator(
                fetch_strategies.fetch_substances(None, limit=10)
            )

    @pytest.mark.asyncio
    async def test_fetch_substances_yields_substances(
        self, fetch_strategies, mock_circuit_breaker, mock_entity_mapper
    ):
        """Test that fetch_substances yields substance dictionaries."""
        mock_substance = MagicMock(sid=12345)
        mock_circuit_breaker.call.return_value = [mock_substance]

        results = await collect_async_iterator(
            fetch_strategies.fetch_substances("aspirin", limit=None)
        )

        assert len(results) == 1
        mock_entity_mapper.substance_to_dict.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_substances_respects_limit(
        self, fetch_strategies, mock_circuit_breaker
    ):
        """Test that fetch_substances respects limit parameter."""
        mock_substances = [MagicMock(sid=i) for i in range(10)]
        mock_circuit_breaker.call.return_value = mock_substances

        results = await collect_async_iterator(
            fetch_strategies.fetch_substances("test", limit=3)
        )

        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_fetch_substances_handles_empty_result(
        self, fetch_strategies, mock_circuit_breaker
    ):
        """Test that fetch_substances handles empty results."""
        mock_circuit_breaker.call.return_value = []

        results = await collect_async_iterator(
            fetch_strategies.fetch_substances("nonexistent", limit=None)
        )

        assert len(results) == 0


@pytest.mark.unit
class TestFetchAssays:
    """Tests for fetch_assays method."""

    @pytest.mark.asyncio
    async def test_fetch_assays_raises_on_empty_query(self, fetch_strategies):
        """Test that fetch_assays raises ValueError for empty query."""
        with pytest.raises(ValueError, match="Query is required"):
            await drain_async_iterator(fetch_strategies.fetch_assays(None, limit=10))

    @pytest.mark.asyncio
    async def test_fetch_assays_yields_assays(
        self, fetch_strategies, mock_circuit_breaker, mock_entity_mapper
    ):
        """Test that fetch_assays yields assay dictionaries."""
        mock_assay = MagicMock(aid=67890)
        mock_circuit_breaker.call.return_value = [mock_assay]

        results = await collect_async_iterator(
            fetch_strategies.fetch_assays("kinase", limit=None)
        )

        assert len(results) == 1
        mock_entity_mapper.assay_to_dict.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_assays_respects_limit(
        self, fetch_strategies, mock_circuit_breaker
    ):
        """Test that fetch_assays respects limit parameter."""
        mock_assays = [MagicMock(aid=i) for i in range(10)]
        mock_circuit_breaker.call.return_value = mock_assays

        results = await collect_async_iterator(
            fetch_strategies.fetch_assays("test", limit=3)
        )

        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_fetch_assays_handles_empty_result(
        self, fetch_strategies, mock_circuit_breaker
    ):
        """Test that fetch_assays handles empty results."""
        mock_circuit_breaker.call.return_value = []

        results = await collect_async_iterator(
            fetch_strategies.fetch_assays("nonexistent", limit=None)
        )

        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_fetch_assays_handles_none_result(
        self, fetch_strategies, mock_circuit_breaker
    ):
        """Test that fetch_assays handles None result from API."""
        mock_circuit_breaker.call.return_value = None

        results = await collect_async_iterator(
            fetch_strategies.fetch_assays("nonexistent", limit=None)
        )

        assert len(results) == 0
