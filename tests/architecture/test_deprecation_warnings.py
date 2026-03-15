"""Guardrail: deprecated compatibility shims must emit ``DeprecationWarning``."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from bioetl.composition.bootstrap.runtime.runner_assembly import (
    create_composite_runner_with_legacy_fsm_adapter,
)
from bioetl.composition.factories.pipeline import facade as pipeline_factory


_FACADE_PATH = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "bioetl"
    / "composition"
    / "factories"
    / "pipeline"
    / "facade.py"
)

# Snapshot after wrapper extraction: facade stays a thin forwarder.
_FACADE_MAX_LINES = 180


@pytest.mark.architecture
def test_pipeline_factory_facade_does_not_grow() -> None:
    """Compatibility facade must not grow — migrate callers to canonical imports."""
    line_count = len(_FACADE_PATH.read_text(encoding="utf-8").splitlines())
    assert line_count <= _FACADE_MAX_LINES, (
        f"pipeline/facade.py grew to {line_count} lines (max {_FACADE_MAX_LINES}). "
        "Add new wiring to canonical modules, not the compat facade."
    )


def test_pipeline_factory_build_pipeline_services_warns() -> None:
    """Deprecated pipeline_factory facade must emit ``DeprecationWarning``."""
    with patch("bioetl.composition.factories.pipeline.facade._build_pipeline_services"):
        with pytest.warns(DeprecationWarning, match="pipeline_factory facade"):
            pipeline_factory.build_pipeline_services(
                "chembl_activity",
                object(),
                object(),
                object(),
            )


def test_pipeline_factory_create_pipeline_with_services_warns() -> None:
    """Deprecated pipeline_factory constructor facade must emit warning."""
    with patch(
        "bioetl.composition.factories.pipeline.facade._create_pipeline_with_services"
    ):
        with pytest.warns(DeprecationWarning, match="pipeline_factory facade"):
            pipeline_factory.create_pipeline_with_services(
                "chembl_activity",
                object(),  # pipeline_class
                "chembl",  # provider
                object(),  # create_data_source_fn
                None,  # transformer_class
                "run-id",
                object(),  # runtime
                object(),  # settings
                object(),  # logger
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
