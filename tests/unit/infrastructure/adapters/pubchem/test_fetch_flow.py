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
"""Tests for PubChem fetch flow.

Covers:
- PubChemFetchFlow.execute: happy path, error propagation, request recording
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.infrastructure.adapters.pubchem.fetch_flow import PubChemFetchFlow


@pytest.fixture
def mock_rate_limiter() -> AsyncMock:
    rl = AsyncMock()
    rl.acquire = AsyncMock()
    return rl


@pytest.fixture
def mock_circuit_breaker() -> AsyncMock:
    cb = AsyncMock()
    return cb


@pytest.fixture
def mock_run_in_executor() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_record_request() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_normalize_results() -> MagicMock:
    return MagicMock(side_effect=lambda x: x if isinstance(x, list) else [])


@pytest.fixture
def fetch_flow(
    mock_rate_limiter: AsyncMock,
    mock_circuit_breaker: AsyncMock,
    mock_run_in_executor: AsyncMock,
    mock_record_request: MagicMock,
    mock_normalize_results: MagicMock,
) -> PubChemFetchFlow:
    return PubChemFetchFlow(
        rate_limiter=mock_rate_limiter,
        circuit_breaker=mock_circuit_breaker,
        run_in_executor=mock_run_in_executor,
        record_request=mock_record_request,
        normalize_results=mock_normalize_results,
    )


@pytest.mark.unit
class TestFetchFlowExecute:
    async def test_happy_path(
        self,
        fetch_flow: PubChemFetchFlow,
        mock_rate_limiter: AsyncMock,
        mock_circuit_breaker: AsyncMock,
        mock_record_request: MagicMock,
        mock_normalize_results: MagicMock,
    ) -> None:
        """Execute acquires rate limiter, calls circuit breaker, normalizes, records."""
        raw_data = [{"cid": 1}, {"cid": 2}]
        mock_circuit_breaker.call.return_value = raw_data
        mock_normalize_results.side_effect = lambda x: x if isinstance(x, list) else []

        result = await fetch_flow.execute(
            endpoint="/compound/name/aspirin/JSON",
            pubchem_callable=MagicMock(),
            pubchem_args=("aspirin", "name"),
        )

        assert result == raw_data
        mock_rate_limiter.acquire.assert_awaited_once()
        mock_circuit_breaker.call.assert_awaited_once()
        mock_record_request.assert_called_once()
        # Check record_request received endpoint and result_count
        call_kwargs = mock_record_request.call_args
        assert call_kwargs[0][0] == "/compound/name/aspirin/JSON"
        assert call_kwargs[1]["result_count"] == 2

    async def test_records_duration_ms(
        self,
        fetch_flow: PubChemFetchFlow,
        mock_circuit_breaker: AsyncMock,
        mock_record_request: MagicMock,
    ) -> None:
        """Duration is passed as a positive float."""
        mock_circuit_breaker.call.return_value = [{"cid": 1}]
        fetch_flow.normalize_results = lambda x: x if isinstance(x, list) else []

        await fetch_flow.execute(
            endpoint="/test",
            pubchem_callable=MagicMock(),
            pubchem_args=(),
        )

        duration_ms = mock_record_request.call_args[0][1]
        assert isinstance(duration_ms, float)
        assert duration_ms >= 0

    async def test_error_propagation_from_circuit_breaker(
        self,
        fetch_flow: PubChemFetchFlow,
        mock_circuit_breaker: AsyncMock,
    ) -> None:
        """Errors from circuit_breaker.call propagate up."""
        mock_circuit_breaker.call.side_effect = RuntimeError("API down")

        with pytest.raises(RuntimeError, match="API down"):
            await fetch_flow.execute(
                endpoint="/compound/name/fail/JSON",
                pubchem_callable=MagicMock(),
                pubchem_args=(),
            )

    async def test_rate_limiter_called_before_circuit_breaker(
        self,
        fetch_flow: PubChemFetchFlow,
        mock_rate_limiter: AsyncMock,
        mock_circuit_breaker: AsyncMock,
    ) -> None:
        """Rate limiter acquire happens before circuit breaker call."""
        call_order: list[str] = []

        async def track_acquire() -> None:
            await asyncio.sleep(0)
            call_order.append("acquire")

        async def track_cb_call(*args: object, **kwargs: object) -> list[object]:
            await asyncio.sleep(0)
            call_order.append("cb_call")
            return []

        mock_rate_limiter.acquire = track_acquire
        mock_circuit_breaker.call = track_cb_call
        fetch_flow.normalize_results = lambda x: x if isinstance(x, list) else []

        await fetch_flow.execute(
            endpoint="/test",
            pubchem_callable=MagicMock(),
            pubchem_args=(),
        )

        assert call_order == ["acquire", "cb_call"]

    async def test_normalize_called_with_raw_results(
        self,
        fetch_flow: PubChemFetchFlow,
        mock_circuit_breaker: AsyncMock,
        mock_normalize_results: MagicMock,
    ) -> None:
        """normalize_results receives the raw output from circuit_breaker."""
        raw = ("tuple_result",)
        mock_circuit_breaker.call.return_value = raw
        mock_normalize_results.side_effect = lambda x: (
            list(x) if isinstance(x, tuple) else []
        )

        result = await fetch_flow.execute(
            endpoint="/test",
            pubchem_callable=MagicMock(),
            pubchem_args=(),
        )

        mock_normalize_results.assert_called_once_with(raw)
        assert result == ["tuple_result"]
