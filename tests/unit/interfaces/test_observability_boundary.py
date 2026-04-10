from __future__ import annotations

from unittest import mock

import pytest


@pytest.mark.unit
def test_start_metrics_server_delegates_to_composition_observability_api() -> None:
    import bioetl.interfaces.observability as observability_module

    logger = mock.Mock()

    with mock.patch(
        "bioetl.composition.observability_api.start_metrics_server",
        return_value=True,
    ) as mock_start_metrics_server:
        result = observability_module.start_metrics_server(
            port=9200,
            addr="127.0.0.1",
            fail_fast=False,
            retry_count=2,
            retry_delay=0.25,
            logger=logger,
        )

    assert result is True
    mock_start_metrics_server.assert_called_once_with(
        port=9200,
        addr="127.0.0.1",
        fail_fast=False,
        retry_count=2,
        retry_delay=0.25,
        logger=logger,
    )


@pytest.mark.unit
def test_push_metrics_to_gateway_delegates_to_composition_observability_api() -> None:
    import bioetl.interfaces.observability as observability_module

    logger = mock.Mock()

    with mock.patch(
        "bioetl.composition.observability_api.push_metrics_to_gateway",
        return_value=True,
    ) as mock_push_metrics:
        result = observability_module.push_metrics_to_gateway(
            run_label="bioetl",
            pipeline_name="chembl_activity",
            run_type="incremental",
            logger=logger,
        )

    assert result is True
    mock_push_metrics.assert_called_once_with(
        run_label="bioetl",
        pipeline_name="chembl_activity",
        run_type="incremental",
        logger=logger,
    )
