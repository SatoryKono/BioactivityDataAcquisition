"""Unexpected provider errors retain optional/required enrichment semantics."""

from __future__ import annotations

from unittest.mock import Mock

import polars as pl
import pytest

from bioetl.application.composite.coordinator import EnrichmentCoordinatorService
from bioetl.domain.composite import CompositeDQConfig, EnricherConfig
from tests.helpers.clock import fixed_test_clock

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
@pytest.mark.parametrize("required", [False, True])
async def test_unexpected_provider_exception_retains_failure_identity_and_reason(
    required,
):
    class ProviderUnexpectedError(Exception):
        pass

    error = ProviderUnexpectedError("upstream implementation failed")
    factory = Mock(side_effect=error)
    logger = Mock()
    coordinator = EnrichmentCoordinatorService(
        logger=logger, dq_config=CompositeDQConfig(), clock=fixed_test_clock()
    )
    enricher = EnricherConfig(
        pipeline="crossref_publication", join_keys=("doi",), required=required
    )
    keys = pl.DataFrame({"doi": ["10.1000/example"]})
    if required:
        with pytest.raises(ProviderUnexpectedError) as caught:
            await coordinator._run_single_enricher(enricher, keys, factory)
        assert caught.value is error
        log = logger.error
    else:
        result = await coordinator._run_single_enricher(enricher, keys, factory)
        assert result.status.value == "failed"
        assert result.error_message == str(error)
        log = logger.warning
    assert log.call_args.kwargs["reason_code"] == "unexpected_provider_error"
    factory.assert_called_once_with(enricher.pipeline, keys)
