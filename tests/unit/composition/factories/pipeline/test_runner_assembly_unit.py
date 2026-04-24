"""Focused tests for pipeline runner assembly implementation seams."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock, patch

import pytest

from bioetl.composition.bootstrap_contexts import DQConfigsContext
from bioetl.composition.factories.pipeline.runner_assembly import (
    _build_checkpoint_manager,
    assemble_runner_impl,
)


def _make_pipeline() -> SimpleNamespace:
    run_context = SimpleNamespace(
        pipeline_version="1.0.0",
        config_hash="a" * 64,
        dq_contract_compatibility_hash="b" * 64,
        manifest_id="manifest-123",
        contract_ref="chembl.activity",
        contract_version="1.0.0",
        effective_config_artifact_id="artifact-123",
    )
    services = SimpleNamespace(
        checkpoint=MagicMock(),
        lock=MagicMock(),
        metrics=MagicMock(),
        storage=MagicMock(),
        dq_monitor=MagicMock(),
        dq_report_service=MagicMock(),
        metadata_coordinator=SimpleNamespace(run_context=run_context),
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
        exact_replay=False,
        effective_lock_ttl=60,
        wait_for_lock=False,
        lock_wait_timeout=10,
        heartbeat_interval=30,
        health_check_mode="strict",
    )
    context = SimpleNamespace(run_id="run-123")
    settings = SimpleNamespace(
        pipeline=SimpleNamespace(
            control_plane=SimpleNamespace(
                checkpoint_compatibility_policy="soft_fail",
                required_persistence_profile="degraded_observable",
            )
        )
    )
    return SimpleNamespace(
        services=services,
        config=config,
        runtime=runtime,
        context=context,
        settings=settings,
        run_id="run-123",
        shutdown_signal=MagicMock(),
    )


@pytest.mark.unit
def test_assemble_runner_impl_uses_injected_dq_configs_extractor() -> None:
    pipeline = cast(Any, _make_pipeline())
    observability = cast(
        Any,
        SimpleNamespace(tracer=MagicMock(), logger=MagicMock()),
    )
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


@pytest.mark.unit
def test_build_checkpoint_manager_uses_control_plane_policy() -> None:
    pipeline = cast(Any, _make_pipeline())
    logger = MagicMock()
    pipeline.settings.pipeline.control_plane.checkpoint_compatibility_policy = "observe"

    with (
        patch(
            "bioetl.composition.factories.pipeline.runner_assembly"
            ".CheckpointCompatibilityService",
            return_value=MagicMock(),
        ),
        patch(
            "bioetl.composition.factories.pipeline.runner_assembly"
            ".ServicesBuilder.create_checkpoint_manager",
            return_value=MagicMock(),
        ) as mock_create_manager,
    ):
        _build_checkpoint_manager(
            pipeline=pipeline,
            logger_port=logger,
        )

    assert mock_create_manager.call_args.kwargs["compatibility_policy"] == "observe"


@pytest.mark.unit
def test_build_checkpoint_manager_supports_legacy_observe_policy() -> None:
    pipeline = cast(Any, _make_pipeline())
    logger = MagicMock()
    pipeline.settings.pipeline.control_plane.checkpoint_compatibility_policy = (
        "legacy_observe"
    )

    with (
        patch(
            "bioetl.composition.factories.pipeline.runner_assembly"
            ".CheckpointCompatibilityService",
            return_value=MagicMock(),
        ),
        patch(
            "bioetl.composition.factories.pipeline.runner_assembly"
            ".ServicesBuilder.create_checkpoint_manager",
            return_value=MagicMock(),
        ) as mock_create_manager,
    ):
        _build_checkpoint_manager(
            pipeline=pipeline,
            logger_port=logger,
        )

    assert (
        mock_create_manager.call_args.kwargs["compatibility_policy"] == "legacy_observe"
    )


@pytest.mark.unit
def test_build_checkpoint_manager_supports_hard_fail_policy() -> None:
    pipeline = cast(Any, _make_pipeline())
    logger = MagicMock()
    pipeline.settings.pipeline.control_plane.checkpoint_compatibility_policy = (
        "hard_fail"
    )

    with (
        patch(
            "bioetl.composition.factories.pipeline.runner_assembly"
            ".CheckpointCompatibilityService",
            return_value=MagicMock(),
        ),
        patch(
            "bioetl.composition.factories.pipeline.runner_assembly"
            ".ServicesBuilder.create_checkpoint_manager",
            return_value=MagicMock(),
        ) as mock_create_manager,
    ):
        _build_checkpoint_manager(
            pipeline=pipeline,
            logger_port=logger,
        )

    assert mock_create_manager.call_args.kwargs["compatibility_policy"] == "hard_fail"


@pytest.mark.unit
def test_build_checkpoint_manager_fallbacks_to_soft_fail_on_invalid_policy() -> None:
    pipeline = cast(Any, _make_pipeline())
    logger = MagicMock()
    pipeline.settings.pipeline.control_plane.checkpoint_compatibility_policy = "invalid"

    with (
        patch(
            "bioetl.composition.factories.pipeline.runner_assembly"
            ".CheckpointCompatibilityService",
            return_value=MagicMock(),
        ),
        patch(
            "bioetl.composition.factories.pipeline.runner_assembly"
            ".ServicesBuilder.create_checkpoint_manager",
            return_value=MagicMock(),
        ) as mock_create_manager,
    ):
        _build_checkpoint_manager(
            pipeline=pipeline,
            logger_port=logger,
        )

    assert mock_create_manager.call_args.kwargs["compatibility_policy"] == "soft_fail"
    logger.warning.assert_called_once()


@pytest.mark.unit
def test_build_checkpoint_manager_coerces_observe_to_hard_fail_for_exact_replay() -> (
    None
):
    pipeline = cast(Any, _make_pipeline())
    logger = MagicMock()
    pipeline.runtime.exact_replay = True
    pipeline.settings.pipeline.control_plane.checkpoint_compatibility_policy = "observe"

    with (
        patch(
            "bioetl.composition.factories.pipeline.runner_assembly"
            ".CheckpointCompatibilityService",
            return_value=MagicMock(),
        ),
        patch(
            "bioetl.composition.factories.pipeline.runner_assembly"
            ".ServicesBuilder.create_checkpoint_manager",
            return_value=MagicMock(),
        ) as mock_create_manager,
    ):
        _build_checkpoint_manager(
            pipeline=pipeline,
            logger_port=logger,
        )

    assert mock_create_manager.call_args.kwargs["compatibility_policy"] == "hard_fail"
    logger.warning.assert_called_once()
    assert "Exact replay requires hard_fail" in logger.warning.call_args.args[0]


@pytest.mark.unit
def test_build_checkpoint_manager_coerces_soft_fail_to_hard_fail_for_exact_replay() -> (
    None
):
    pipeline = cast(Any, _make_pipeline())
    logger = MagicMock()
    pipeline.runtime.exact_replay = True
    pipeline.settings.pipeline.control_plane.checkpoint_compatibility_policy = (
        "soft_fail"
    )

    with (
        patch(
            "bioetl.composition.factories.pipeline.runner_assembly"
            ".CheckpointCompatibilityService",
            return_value=MagicMock(),
        ),
        patch(
            "bioetl.composition.factories.pipeline.runner_assembly"
            ".ServicesBuilder.create_checkpoint_manager",
            return_value=MagicMock(),
        ) as mock_create_manager,
    ):
        _build_checkpoint_manager(
            pipeline=pipeline,
            logger_port=logger,
        )

    assert mock_create_manager.call_args.kwargs["compatibility_policy"] == "hard_fail"
    logger.warning.assert_called_once()
    warning_kwargs = logger.warning.call_args.kwargs
    assert warning_kwargs["requested_policy"] == "soft_fail"
    assert warning_kwargs["applied_policy"] == "hard_fail"


@pytest.mark.unit
def test_build_checkpoint_manager_coerces_observe_to_soft_fail_for_replay_ready() -> (
    None
):
    pipeline = cast(Any, _make_pipeline())
    logger = MagicMock()
    pipeline.settings.pipeline.control_plane.required_persistence_profile = (
        "replay_ready"
    )
    pipeline.settings.pipeline.control_plane.checkpoint_compatibility_policy = "observe"

    with (
        patch(
            "bioetl.composition.factories.pipeline.runner_assembly"
            ".CheckpointCompatibilityService",
            return_value=MagicMock(),
        ),
        patch(
            "bioetl.composition.factories.pipeline.runner_assembly"
            ".ServicesBuilder.create_checkpoint_manager",
            return_value=MagicMock(),
        ) as mock_create_manager,
    ):
        _build_checkpoint_manager(
            pipeline=pipeline,
            logger_port=logger,
        )

    assert mock_create_manager.call_args.kwargs["compatibility_policy"] == "soft_fail"
    logger.warning.assert_called_once()
    warning_kwargs = logger.warning.call_args.kwargs
    assert warning_kwargs["required_persistence_profile"] == "replay_ready"
    assert warning_kwargs["requested_policy"] == "observe"
    assert warning_kwargs["applied_policy"] == "soft_fail"


@pytest.mark.unit
def test_build_checkpoint_manager_coerces_legacy_observe_to_soft_fail_for_forensic_grade() -> (
    None
):
    pipeline = cast(Any, _make_pipeline())
    logger = MagicMock()
    pipeline.settings.pipeline.control_plane.required_persistence_profile = (
        "forensic_grade"
    )
    pipeline.settings.pipeline.control_plane.checkpoint_compatibility_policy = (
        "legacy_observe"
    )

    with (
        patch(
            "bioetl.composition.factories.pipeline.runner_assembly"
            ".CheckpointCompatibilityService",
            return_value=MagicMock(),
        ),
        patch(
            "bioetl.composition.factories.pipeline.runner_assembly"
            ".ServicesBuilder.create_checkpoint_manager",
            return_value=MagicMock(),
        ) as mock_create_manager,
    ):
        _build_checkpoint_manager(
            pipeline=pipeline,
            logger_port=logger,
        )

    assert mock_create_manager.call_args.kwargs["compatibility_policy"] == "soft_fail"
    logger.warning.assert_called_once()
    warning_kwargs = logger.warning.call_args.kwargs
    assert warning_kwargs["required_persistence_profile"] == "forensic_grade"
    assert warning_kwargs["requested_policy"] == "legacy_observe"
    assert warning_kwargs["applied_policy"] == "soft_fail"
