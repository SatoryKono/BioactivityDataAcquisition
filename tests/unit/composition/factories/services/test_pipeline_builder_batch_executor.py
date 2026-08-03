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
"""Unit tests for create_batch_executor_from_pipeline."""

from __future__ import annotations

from tests.helpers.synthetic_paths import synthetic_test_root
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from bioetl.application.core.batch_executor import BatchExecutor
from bioetl.composition.factories.services.pipeline_builder import (
    BatchExecutorBuildRequest,
    create_batch_executor_from_pipeline,
)

TEST_ROOT = synthetic_test_root("bioetl-pipeline-batch-executor")
BRONZE_ROOT = str(TEST_ROOT / "bronze")
SILVER_ROOT = str(TEST_ROOT / "silver")
GOLD_ROOT = str(TEST_ROOT / "gold")


def _make_pipeline(
    *,
    skip_gold: bool = False,
    checkpoint_interval: int | None = 123,
    batch_size: int = 50,
) -> SimpleNamespace:
    """Build a minimal pipeline stub for batch-executor assembly tests."""
    return SimpleNamespace(
        runtime=SimpleNamespace(skip_gold=skip_gold),
        services=MagicMock(name="services"),
        context=MagicMock(name="context"),
        config=SimpleNamespace(
            pipeline_name="chembl_activity",
            provider="chembl",
            entity_type="activity",
            dq=None,
            data_schema=None,
            table=SimpleNamespace(),
            column_groups=(),
            scd_config=None,
            checkpoint_interval=checkpoint_interval,
            batch_size=batch_size,
        ),
    )


def _make_callbacks() -> SimpleNamespace:
    """Build callback namespace used by pipeline builder."""
    return SimpleNamespace(
        transform=MagicMock(name="transform"),
        gold_filter=MagicMock(name="gold_filter"),
        gold_transform=MagicMock(name="gold_transform"),
    )


@pytest.mark.unit
class TestCreateBatchExecutorFromPipeline:
    """Tests for batch-executor assembly from pipeline context."""

    @patch(
        "bioetl.composition.factories.services.pipeline_batch_executor_builder.ContractAwareGoldValidator"
    )
    @patch(
        "bioetl.composition.factories.services.pipeline_batch_executor_builder.BatchExecutor"
    )
    @patch(
        "bioetl.composition.factories.services.pipeline_batch_executor_builder.BatchExtractionLoopService"
    )
    @patch(
        "bioetl.composition.factories.services.pipeline_batch_executor_builder.build_components_and_processing_service"
    )
    @patch(
        "bioetl.composition.factories.services.pipeline_batch_executor_builder.build_runtime_managers"
    )
    def test_uses_false_gold_filter_when_runtime_skip_gold(
        self,
        mock_build_runtime_managers: MagicMock,
        mock_build_components: MagicMock,
        mock_extraction_loop: MagicMock,
        mock_batch_executor: MagicMock,
        mock_gold_validator: MagicMock,
    ) -> None:
        pipeline = _make_pipeline(skip_gold=True)
        callbacks = _make_callbacks()
        mock_build_runtime_managers.return_value = (
            MagicMock(name="memory_manager"),
            MagicMock(name="tracing_manager"),
            MagicMock(name="batch_id_factory"),
            MagicMock(name="progress_service"),
            MagicMock(name="checkpoint_recovery_service"),
            MagicMock(name="execution_run_service"),
        )
        processing_service = MagicMock(name="processing_port")
        mock_build_components.return_value = (
            MagicMock(name="components"),
            processing_service,
        )
        expected = MagicMock(name="executor")
        mock_batch_executor.return_value = expected
        metric = MagicMock(name="gold_lifecycle_state_metric")

        with patch(
            "bioetl.composition.factories.services.pipeline_batch_executor_builder._gold_lifecycle_state_total",
            metric,
        ):
            result = create_batch_executor_from_pipeline(
                BatchExecutorBuildRequest(
                    pipeline=pipeline,
                    callbacks=callbacks,
                    silver_schema=None,
                    gold_schema=MagicMock(),
                    checkpoint_manager=MagicMock(),
                    shutdown_signal=MagicMock(),
                    create_batch_processing_components_fn=MagicMock(),
                )
            )

        gold_filter = mock_build_components.call_args.kwargs["gold_filter"]
        assert gold_filter(MagicMock(), {"id": "1"}) is False
        assert result is expected
        metric.return_value.labels.assert_called_once_with(
            pipeline="chembl_activity",
            table="chembl_activity",
            state="disabled",
        )
        metric.return_value.labels.return_value.inc.assert_called_once()
        mock_extraction_loop.assert_called_once()

    @patch(
        "bioetl.composition.factories.services.pipeline_batch_executor_builder.ContractAwareGoldValidator"
    )
    @patch(
        "bioetl.composition.factories.services.pipeline_batch_executor_builder.BatchExecutor"
    )
    @patch(
        "bioetl.composition.factories.services.pipeline_batch_executor_builder.BatchExtractionLoopService"
    )
    @patch(
        "bioetl.composition.factories.services.pipeline_batch_executor_builder.build_components_and_processing_service"
    )
    @patch(
        "bioetl.composition.factories.services.pipeline_batch_executor_builder.build_runtime_managers"
    )
    def test_forwards_runtime_manager_inputs(
        self,
        mock_build_runtime_managers: MagicMock,
        mock_build_components: MagicMock,
        mock_extraction_loop: MagicMock,
        mock_batch_executor: MagicMock,
        mock_gold_validator: MagicMock,
    ) -> None:
        pipeline = _make_pipeline()
        callbacks = _make_callbacks()
        memory_monitor = MagicMock(name="memory_monitor")
        memory_config = MagicMock(name="memory_config")
        tracer = MagicMock(name="tracer")
        batch_id_factory = MagicMock(name="batch_id_factory")
        checkpoint_manager = MagicMock(name="checkpoint_manager")
        mock_build_runtime_managers.return_value = (
            MagicMock(name="memory_manager"),
            MagicMock(name="tracing_manager"),
            MagicMock(name="effective_batch_id_factory"),
            MagicMock(name="progress_service"),
            MagicMock(name="checkpoint_recovery_service"),
            MagicMock(name="execution_run_service"),
        )
        mock_build_components.return_value = (
            MagicMock(name="components"),
            MagicMock(name="processing_port"),
        )

        create_batch_executor_from_pipeline(
            BatchExecutorBuildRequest(
                pipeline=pipeline,
                callbacks=callbacks,
                silver_schema=None,
                gold_schema=MagicMock(),
                checkpoint_manager=checkpoint_manager,
                shutdown_signal=MagicMock(),
                create_batch_processing_components_fn=MagicMock(),
                memory_monitor=memory_monitor,
                memory_config=memory_config,
                tracer=tracer,
                batch_id_factory=batch_id_factory,
            )
        )

        mock_build_runtime_managers.assert_called_once()
        call_kwargs = mock_build_runtime_managers.call_args.kwargs
        assert call_kwargs["pipeline"] is pipeline
        assert call_kwargs["checkpoint_manager"] is checkpoint_manager
        assert call_kwargs["memory_monitor"] is memory_monitor
        assert call_kwargs["memory_config"] is memory_config
        assert call_kwargs["tracer"] is tracer
        assert call_kwargs["batch_id_factory"] is batch_id_factory
        mock_extraction_loop.assert_called_once()
        mock_batch_executor.assert_called_once()

    @patch(
        "bioetl.composition.factories.services.pipeline_batch_executor_builder.ContractAwareGoldValidator"
    )
    @patch(
        "bioetl.composition.factories.services.pipeline_batch_executor_builder.BatchExecutor"
    )
    @patch(
        "bioetl.composition.factories.services.pipeline_batch_executor_builder.BatchExtractionLoopService"
    )
    @patch(
        "bioetl.composition.factories.services.pipeline_batch_executor_builder.build_components_and_processing_service"
    )
    @patch(
        "bioetl.composition.factories.services.pipeline_batch_executor_builder.build_runtime_managers"
    )
    def test_uses_default_checkpoint_interval_when_pipeline_config_missing(
        self,
        mock_build_runtime_managers: MagicMock,
        mock_build_components: MagicMock,
        mock_extraction_loop: MagicMock,
        mock_batch_executor: MagicMock,
        mock_gold_validator: MagicMock,
    ) -> None:
        pipeline = _make_pipeline(checkpoint_interval=None)
        mock_batch_executor.DEFAULT_CHECKPOINT_INTERVAL = 1000
        mock_build_runtime_managers.return_value = (
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
        )
        mock_build_components.return_value = (MagicMock(), MagicMock())

        create_batch_executor_from_pipeline(
            BatchExecutorBuildRequest(
                pipeline=pipeline,
                callbacks=_make_callbacks(),
                silver_schema=None,
                gold_schema=MagicMock(),
                checkpoint_manager=MagicMock(),
                shutdown_signal=MagicMock(),
                create_batch_processing_components_fn=MagicMock(),
            )
        )

        assert (
            mock_extraction_loop.call_args.kwargs["checkpoint_interval"]
            == BatchExecutor.DEFAULT_CHECKPOINT_INTERVAL
        )

    @patch(
        "bioetl.composition.factories.services.pipeline_batch_executor_builder.ContractAwareGoldValidator"
    )
    @patch(
        "bioetl.composition.factories.services.pipeline_batch_executor_builder.BatchExecutor"
    )
    @patch(
        "bioetl.composition.factories.services.pipeline_batch_executor_builder.BatchExtractionLoopService"
    )
    @patch(
        "bioetl.composition.factories.services.pipeline_batch_executor_builder.build_components_and_processing_service"
    )
    @patch(
        "bioetl.composition.factories.services.pipeline_batch_executor_builder.build_runtime_managers"
    )
    def test_propagates_output_paths_and_flat_structure_into_record_processor_config(
        self,
        mock_build_runtime_managers: MagicMock,
        mock_build_components: MagicMock,
        mock_extraction_loop: MagicMock,
        mock_batch_executor: MagicMock,
        mock_gold_validator: MagicMock,
    ) -> None:
        pipeline = _make_pipeline()
        mock_build_runtime_managers.return_value = (
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
        )
        mock_build_components.return_value = (MagicMock(), MagicMock())

        create_batch_executor_from_pipeline(
            BatchExecutorBuildRequest(
                pipeline=pipeline,
                callbacks=_make_callbacks(),
                silver_schema=None,
                gold_schema=MagicMock(),
                checkpoint_manager=MagicMock(),
                shutdown_signal=MagicMock(),
                create_batch_processing_components_fn=MagicMock(),
                bronze_output_path=BRONZE_ROOT,
                silver_output_path=SILVER_ROOT,
                gold_output_path=GOLD_ROOT,
                flat_structure=True,
            )
        )

        config = mock_batch_executor.call_args.kwargs["config"]
        assert config.bronze_output_path == BRONZE_ROOT
        assert config.silver_output_path == SILVER_ROOT
        assert config.gold_output_path == GOLD_ROOT
        assert config.flat_structure is True
        mock_extraction_loop.assert_called_once()

    @patch(
        "bioetl.composition.factories.services.pipeline_batch_executor_builder.ContractAwareGoldValidator"
    )
    @patch(
        "bioetl.composition.factories.services.pipeline_batch_executor_builder.BatchExecutor"
    )
    @patch(
        "bioetl.composition.factories.services.pipeline_batch_executor_builder.BatchExtractionLoopService"
    )
    @patch(
        "bioetl.composition.factories.services.pipeline_batch_executor_builder.build_components_and_processing_service"
    )
    @patch(
        "bioetl.composition.factories.services.pipeline_batch_executor_builder.build_runtime_managers"
    )
    def test_wires_batch_size_and_checkpoint_interval_from_pipeline_config(
        self,
        mock_build_runtime_managers: MagicMock,
        mock_build_components: MagicMock,
        mock_extraction_loop: MagicMock,
        mock_batch_executor: MagicMock,
        mock_gold_validator: MagicMock,
    ) -> None:
        pipeline = _make_pipeline(checkpoint_interval=321, batch_size=25)
        mock_build_runtime_managers.return_value = (
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
        )
        mock_build_components.return_value = (MagicMock(), MagicMock())

        create_batch_executor_from_pipeline(
            BatchExecutorBuildRequest(
                pipeline=pipeline,
                callbacks=_make_callbacks(),
                silver_schema=None,
                gold_schema=MagicMock(),
                checkpoint_manager=MagicMock(),
                shutdown_signal=MagicMock(),
                create_batch_processing_components_fn=MagicMock(),
            )
        )

        call_kwargs = mock_batch_executor.call_args.kwargs
        assert call_kwargs["batch_size"] == 25
        assert call_kwargs["checkpoint_interval"] == 321
