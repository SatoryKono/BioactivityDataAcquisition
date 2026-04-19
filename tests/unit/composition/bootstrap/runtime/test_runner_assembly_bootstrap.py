"""Unit tests for runner_assembly composite bootstrap helpers."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock

import pytest

_VALID_RUN_ID = "12345678-1234-5678-1234-567812345678"

from bioetl.composition.bootstrap.runtime.composite_support_services_factory import (
    CompositeSupportServices,
)
from bioetl.composition.bootstrap.runtime._runner_assembly_support import (
    CompositeRunnerServiceInputs,
)
from bioetl.composition.bootstrap.runtime.runner_assembly import (
    bootstrap_composite_runner,
    create_composite_runner,
    create_composite_runner_service,
)


@pytest.mark.unit
class TestCreateCompositeRunnerService:
    """Tests for create_composite_runner_service."""

    def test_returns_runner_service(self) -> None:
        """Creates CompositePipelineRunnerService with all provided deps."""
        config = MagicMock()
        runtime = MagicMock()
        logger = MagicMock()
        lock = MagicMock()
        fsm = MagicMock()

        result = create_composite_runner_service(
            CompositeRunnerServiceInputs(
                config=config,
                runtime=runtime,
                seed_runner_factory=MagicMock(),
                enricher_runner_factory=MagicMock(),
                key_extractor=MagicMock(),
                coordinator=MagicMock(),
                merger=MagicMock(),
                checkpoint_manager=MagicMock(),
                logger=logger,
                lock=lock,
                fsm_state_helper=fsm,
                run_id=_VALID_RUN_ID,
                dq_report_service=None,
                preflight_validator=None,
                dependencies_runner_factory=None,
                dependency_coordinator=None,
                quarantine_port=None,
                metrics=None,
                tracer=None,
                observer=None,
                manifest_id=None,
                run_ledger_service=None,
            )
        )

        assert result is not None

    def test_generates_run_id_when_none(self) -> None:
        """When run_id is None a UUID is generated."""
        result = create_composite_runner_service(
            CompositeRunnerServiceInputs(
                config=MagicMock(),
                runtime=MagicMock(),
                seed_runner_factory=MagicMock(),
                enricher_runner_factory=MagicMock(),
                key_extractor=MagicMock(),
                coordinator=MagicMock(),
                merger=MagicMock(),
                checkpoint_manager=MagicMock(),
                logger=MagicMock(),
                lock=MagicMock(),
                fsm_state_helper=MagicMock(),
                run_id=None,
                dq_report_service=None,
                preflight_validator=None,
                dependencies_runner_factory=None,
                dependency_coordinator=None,
                quarantine_port=None,
                metrics=None,
                tracer=None,
                observer=None,
                manifest_id=None,
                run_ledger_service=None,
            )
        )

        assert result is not None

    def test_requires_fsm_state_helper(self) -> None:
        """Implicit FSM helper construction is no longer supported."""
        with pytest.raises(
            AssertionError, match="Composite runner requires fsm_state_helper"
        ):
            create_composite_runner_service(
                CompositeRunnerServiceInputs(
                    config=MagicMock(),
                    runtime=MagicMock(),
                    seed_runner_factory=MagicMock(),
                    enricher_runner_factory=MagicMock(),
                    key_extractor=MagicMock(),
                    coordinator=MagicMock(),
                    merger=MagicMock(),
                    checkpoint_manager=MagicMock(),
                    logger=MagicMock(),
                    lock=MagicMock(),
                    fsm_state_helper=cast(Any, None),
                    run_id=_VALID_RUN_ID,
                    dq_report_service=None,
                    preflight_validator=None,
                    dependencies_runner_factory=None,
                    dependency_coordinator=None,
                    quarantine_port=None,
                    metrics=None,
                    tracer=None,
                    observer=None,
                    manifest_id=None,
                    run_ledger_service=None,
                )
            )


@pytest.mark.unit
class TestCreateCompositeRunner:
    """Tests for create_composite_runner."""

    def test_delegates_to_runner_factory(self) -> None:
        """create_composite_runner calls the provided runner_factory callable."""
        expected_runner = MagicMock()
        runner_factory = MagicMock(return_value=expected_runner)
        support_services = cast(
            CompositeSupportServices,
            SimpleNamespace(
                key_extractor=MagicMock(),
                dependency_coordinator=MagicMock(),
                coordinator=MagicMock(),
                merger=MagicMock(),
                checkpoint_manager=MagicMock(),
                fsm_state_helper=MagicMock(),
                dq_report_service=MagicMock(),
                quarantine_port=MagicMock(),
                manifest_id="manifest-123",
                run_ledger_service=MagicMock(),
            ),
        )

        result = create_composite_runner(
            config=MagicMock(),
            runtime=MagicMock(),
            run_id=_VALID_RUN_ID,
            logger=MagicMock(),
            metrics=MagicMock(),
            tracer=MagicMock(),
            lock=MagicMock(),
            seed_runner_factory=MagicMock(),
            dependencies_runner_factory=MagicMock(),
            enricher_runner_factory=MagicMock(),
            support_services=support_services,
            runner_factory=runner_factory,
        )

        assert result is expected_runner
        runner_factory.assert_called_once()

    def test_passes_support_services_fields(self) -> None:
        """Support service attributes are forwarded to the runner_factory."""
        runner_factory = MagicMock(return_value=MagicMock())
        key_extractor = MagicMock()
        dependency_coordinator = MagicMock()
        dq_report_service = MagicMock()
        quarantine_port = MagicMock()
        fsm_state_helper = MagicMock()
        support_services = cast(
            CompositeSupportServices,
            SimpleNamespace(
                key_extractor=key_extractor,
                dependency_coordinator=dependency_coordinator,
                coordinator=MagicMock(),
                merger=MagicMock(),
                checkpoint_manager=MagicMock(),
                fsm_state_helper=fsm_state_helper,
                dq_report_service=dq_report_service,
                quarantine_port=quarantine_port,
                manifest_id="manifest-123",
                run_ledger_service=MagicMock(name="run_ledger_service"),
            ),
        )

        create_composite_runner(
            config=MagicMock(),
            runtime=MagicMock(),
            run_id=_VALID_RUN_ID,
            logger=MagicMock(),
            metrics=MagicMock(),
            tracer=MagicMock(name="tracer"),
            lock=MagicMock(),
            seed_runner_factory=MagicMock(),
            dependencies_runner_factory=MagicMock(),
            enricher_runner_factory=MagicMock(),
            support_services=support_services,
            runner_factory=runner_factory,
        )

        call_args = runner_factory.call_args[0]
        assert len(call_args) == 1
        inputs = call_args[0]
        assert inputs.key_extractor is key_extractor
        assert inputs.dependency_coordinator is dependency_coordinator
        assert inputs.fsm_state_helper is fsm_state_helper
        assert inputs.dq_report_service is dq_report_service
        assert inputs.quarantine_port is quarantine_port
        assert inputs.tracer is not None
        assert inputs.manifest_id == "manifest-123"
        assert inputs.run_ledger_service is support_services.run_ledger_service


@pytest.mark.unit
class TestBootstrapCompositeRunner:
    """Tests for bootstrap_composite_runner."""

    def test_orchestrates_all_steps(self) -> None:
        """bootstrap_composite_runner chains basics -> factories -> services -> runner."""
        settings = SimpleNamespace()
        logger = MagicMock()
        metrics = MagicMock()
        storage = MagicMock()
        lock = MagicMock()

        bootstrap_basics = MagicMock(
            return_value=("rid", settings, logger, metrics, MagicMock(), storage, lock)
        )
        seed_f = MagicMock()
        dep_f = MagicMock()
        enr_f = MagicMock()
        build_factories = MagicMock(return_value=(seed_f, dep_f, enr_f))
        support = SimpleNamespace()
        build_support = MagicMock(return_value=support)
        expected = MagicMock()
        create_runner = MagicMock(return_value=expected)

        result = bootstrap_composite_runner(
            config=MagicMock(),
            runtime=MagicMock(),
            run_id=None,
            bootstrap_runtime_basics_fn=bootstrap_basics,
            build_runner_factories_fn=build_factories,
            build_support_services_fn=build_support,
            create_composite_runner_fn=create_runner,
        )

        assert result is expected
        bootstrap_basics.assert_called_once()
        build_factories.assert_called_once()
        build_support.assert_called_once()
        create_runner.assert_called_once()

    def test_passes_run_id_downstream(self) -> None:
        """Effective run_id from basics is forwarded to create_runner."""
        bootstrap_basics = MagicMock(
            return_value=(
                "effective-rid",
                SimpleNamespace(),
                MagicMock(),
                MagicMock(),
                MagicMock(),
                MagicMock(),
                MagicMock(),
            )
        )
        create_runner = MagicMock(return_value=MagicMock())

        bootstrap_composite_runner(
            config=MagicMock(),
            runtime=MagicMock(),
            run_id=None,
            bootstrap_runtime_basics_fn=bootstrap_basics,
            build_runner_factories_fn=MagicMock(
                return_value=(MagicMock(), MagicMock(), MagicMock())
            ),
            build_support_services_fn=MagicMock(return_value=SimpleNamespace()),
            create_composite_runner_fn=create_runner,
        )

        call_kwargs = create_runner.call_args[1]
        assert call_kwargs["run_id"] == "effective-rid"

    def test_passes_runtime_basics_into_support_services_builder(self) -> None:
        """bootstrap_composite_runner should forward basics to support builder."""
        settings = SimpleNamespace(name="settings")
        logger = MagicMock()
        metrics = MagicMock()
        storage = MagicMock()
        lock = MagicMock()
        bootstrap_basics = MagicMock(
            return_value=(
                "effective-rid",
                settings,
                logger,
                metrics,
                MagicMock(),
                storage,
                lock,
            )
        )
        build_support = MagicMock(return_value=SimpleNamespace())

        bootstrap_composite_runner(
            config=MagicMock(),
            runtime=MagicMock(),
            run_id=None,
            bootstrap_runtime_basics_fn=bootstrap_basics,
            build_runner_factories_fn=MagicMock(
                return_value=(MagicMock(), MagicMock(), MagicMock())
            ),
            build_support_services_fn=build_support,
            create_composite_runner_fn=MagicMock(return_value=MagicMock()),
        )

        call_kwargs = build_support.call_args[1]
        assert call_kwargs["settings"] is settings
        assert call_kwargs["logger"] is logger
        assert call_kwargs["storage"] is storage
        assert call_kwargs["run_id"] == "effective-rid"
