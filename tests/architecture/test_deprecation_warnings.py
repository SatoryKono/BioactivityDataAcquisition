"""Guardrail: deprecated compatibility shims must emit ``DeprecationWarning``."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from bioetl.composition.bootstrap.runtime.runner_assembly import (
    create_composite_runner_with_legacy_fsm_adapter,
)


def test_legacy_composite_runner_factory_warns_without_fsm_helper() -> None:
    """Legacy runtime shim must emit warning on implicit FSM helper creation."""
    with (
        patch(
            "bioetl.application.composite.fsm_helper.FSMStateHelperService"
        ) as fsm_service_class,
        patch(
            "bioetl.composition.bootstrap.runtime.runner_assembly.CompositePipelineRunnerService"
        ),
    ):
        with pytest.warns(
            DeprecationWarning,
            match="Creating CompositePipelineRunner without fsm_state_helper is deprecated",
        ):
            create_composite_runner_with_legacy_fsm_adapter(
                config=object(),
                runtime=object(),
                seed_runner_factory=lambda: object(),
                enricher_runner_factory=lambda _provider, _frame: object(),
                key_extractor=object(),
                coordinator=object(),
                merger=object(),
                checkpoint_manager=object(),
                logger=object(),
                lock=object(),
                fsm_state_helper=None,
                run_id="run-id",
            )

    assert fsm_service_class.called
