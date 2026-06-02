"""Split runtime-mode and collaborator attachment tests for runtime runner builder."""

from __future__ import annotations

import pytest

from bioetl.composition.runtime_builders import (
    inputs_runtime_assembly,
)
from bioetl.composition.runtime_builders import inputs_resolver
from bioetl.composition.runtime_builders._runner_builder_orchestration import (
    attach_runner_control_plane_collaborators,
)

# ruff: noqa: F403,F405
from tests.unit.composition.runtime_builders.runner_builder_test_support import *


pytestmark = pytest.mark.unit


def test_strict_runner_collaborator_attachment_requires_run_ledger_service() -> None:
    with pytest.raises(RuntimeError, match="requires artifact publication closure"):
        attach_runner_control_plane_collaborators(
            runner=_FakeRunner(),
            required_profile="replay_ready",
            run_ledger_service=None,
        )


def test_build_pipeline_runner_forces_probe_mode_in_test_mode(tmp_path: Path) -> None:
    _, fake_registry = _build_factory_registry()
    captured: dict[str, object] = {}

    def assemble_runtime_config_fn(**kwargs: object) -> dict[str, object]:
        captured.update(kwargs)
        return _runtime_config_stub()

    _call_build_pipeline_runner(
        _build_context(vacuum=SimpleNamespace(enabled=None, retention_days=7)),
        registry=fake_registry,
        settings=_build_settings(
            data_dir=str(tmp_path),
            health_check_mode="strict",
            test_mode=True,
        ),
        pipeline_config=_build_pipeline_config(
            maintenance=SimpleNamespace(auto_vacuum=False, vacuum_retention_days=7),
            batch_size=100,
        ),
        assemble_vacuum_settings_fn=lambda **_: SimpleNamespace(
            enabled=False,
            retention_days=7,
        ),
        assemble_runtime_config_fn=assemble_runtime_config_fn,
    )

    assert captured["health_check_mode"] == "probe"


def test_build_pipeline_runner_uses_configured_mode_outside_test_mode(
    tmp_path: Path,
) -> None:
    _, fake_registry = _build_factory_registry()
    captured: dict[str, object] = {}

    def assemble_runtime_config_fn(**kwargs: object) -> dict[str, object]:
        captured.update(kwargs)
        return _runtime_config_stub()

    _call_build_pipeline_runner(
        _build_context(vacuum=SimpleNamespace(enabled=None, retention_days=7)),
        registry=fake_registry,
        settings=_build_settings(
            data_dir=str(tmp_path),
            health_check_mode="probe",
            test_mode=False,
        ),
        pipeline_config=_build_pipeline_config(
            maintenance=SimpleNamespace(auto_vacuum=False, vacuum_retention_days=7),
            batch_size=100,
        ),
        assemble_vacuum_settings_fn=lambda **_: SimpleNamespace(
            enabled=False,
            retention_days=7,
        ),
        assemble_runtime_config_fn=assemble_runtime_config_fn,
    )

    assert captured["health_check_mode"] == "probe"


def test_build_pipeline_runner_forces_skip_gold_when_sink_disabled(
    tmp_path: Path,
) -> None:
    """Builder should disable Gold writes when pipeline YAML disables Gold sink."""
    fake_factory, fake_registry = _build_factory_registry()

    _call_build_pipeline_runner(
        _build_context(vacuum=SimpleNamespace(enabled=None, retention_days=7)),
        registry=fake_registry,
        settings=_build_settings(
            data_dir=str(tmp_path),
            health_check_mode="strict",
        ),
        pipeline_config=_build_pipeline_config(
            pipeline_name="chembl_activity",
            maintenance=SimpleNamespace(auto_vacuum=False, vacuum_retention_days=7),
            batch_size=100,
            sink={"gold": SimpleNamespace(enabled=False)},
        ),
        assemble_vacuum_settings_fn=lambda **_: SimpleNamespace(
            enabled=False,
            retention_days=7,
        ),
        assemble_runtime_config_fn=inputs_resolver.assemble_runtime_config,
    )

    assert fake_factory.kwargs is not None
    runtime = fake_factory.kwargs["runtime"]
    assert runtime.skip_gold is True


def test_assemble_filter_config_passes_cli_overrides_when_enabled() -> None:
    ctx = SimpleNamespace(
        ignore_yaml_filter=False,
        input_filter=SimpleNamespace(
            enabled=True,
            source_path="ids.csv",
            column_name="compound_id",
            filter_field="compound_id",
            fallback_column="legacy_id",
            filter_ids=["1", "2"],
            fallback_mapping={"1": "A"},
            multi_filter_ids={"compound_id": ["1"]},
            valid_combinations=[{"compound_id": "1"}],
        ),
    )
    sentinel = object()

    with patch.object(
        inputs_runtime_assembly.FilterConfigBuilder, "build", return_value=sentinel
    ) as mock_build:
        result = inputs_resolver.assemble_filter_config(
            yaml_filter=SimpleNamespace(),
            ctx=ctx,
            test_mode=False,
        )

    assert result is sentinel
    assert mock_build.call_args.kwargs["cli_csv"] == "ids.csv"
    assert mock_build.call_args.kwargs["test_mode"] is False
