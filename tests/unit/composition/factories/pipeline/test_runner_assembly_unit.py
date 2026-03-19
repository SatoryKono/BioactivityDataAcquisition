"""Focused tests for pipeline runner assembly implementation seams."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from bioetl.composition.bootstrap_contexts import DQConfigsContext
from bioetl.composition.factories.pipeline.runner_assembly import assemble_runner_impl


def _make_pipeline() -> SimpleNamespace:
    services = SimpleNamespace(
        checkpoint=MagicMock(),
        lock=MagicMock(),
        metrics=MagicMock(),
        storage=MagicMock(),
        dq_monitor=MagicMock(),
        dq_report_service=MagicMock(),
        metadata_coordinator=MagicMock(),
        metadata_writer=MagicMock(),
    )
    config = SimpleNamespace(
        pipeline_name="chembl_activity",
        provider="chembl",
        entity_type="activity",
        dq=MagicMock(),
        loading_strategy=None,
    )
    runtime = SimpleNamespace(
        resume=False,
        run_type="incremental",
        effective_lock_ttl=60,
        wait_for_lock=False,
        lock_wait_timeout=10,
        heartbeat_interval=30,
        health_check_mode="strict",
    )
    context = SimpleNamespace(run_id="run-123")
    return SimpleNamespace(
        services=services,
        config=config,
        runtime=runtime,
        context=context,
        run_id="run-123",
        shutdown_signal=MagicMock(),
    )


@pytest.mark.unit
def test_assemble_runner_impl_uses_injected_dq_configs_extractor() -> None:
    pipeline = _make_pipeline()
    observability = SimpleNamespace(tracer=MagicMock(), logger=MagicMock())
    dq_configs = DQConfigsContext(
        bronze=MagicMock(name="bronze_dq"),
        silver=MagicMock(name="silver_dq"),
        gold=MagicMock(name="gold_dq"),
    )

    with (
        patch(
            "bioetl.composition.factories.pipeline.runner_assembly._build_checkpoint_manager",
            return_value=MagicMock(),
        ),
        patch(
            "bioetl.composition.factories.pipeline.runner_assembly.MedallionLifecycleService",
            return_value=MagicMock(),
        ),
        patch(
            "bioetl.composition.factories.pipeline.runner_assembly._build_lock_manager",
            return_value=MagicMock(),
        ),
        patch(
            "bioetl.composition.factories.pipeline.runner_assembly._build_preflight_service",
            return_value=MagicMock(),
        ),
        patch(
            "bioetl.composition.factories.pipeline.runner_assembly.build_postrun_service",
        ) as mock_build_postrun_service,
        patch(
            "bioetl.composition.factories.pipeline.runner_assembly._build_observer",
            return_value=MagicMock(),
        ),
        patch(
            "bioetl.composition.factories.pipeline.runner_assembly._build_batch_executor",
            return_value=MagicMock(),
        ),
        patch(
            "bioetl.composition.factories.pipeline.runner_assembly._create_pipeline_runner",
            return_value=MagicMock(name="runner"),
        ) as mock_create_pipeline_runner,
    ):
        mock_build_postrun_service.return_value = MagicMock()

        result = assemble_runner_impl(
            pipeline=pipeline,
            observability=observability,
            silver_schema=None,
            gold_schema=MagicMock(),
            strict_gold_validation=True,
            yaml_config=MagicMock(),
            dq_configs_extractor=lambda _cfg: dq_configs,
        )

    assert result is mock_create_pipeline_runner.return_value
    assert mock_build_postrun_service.call_args.kwargs["dq_configs"] is dq_configs
