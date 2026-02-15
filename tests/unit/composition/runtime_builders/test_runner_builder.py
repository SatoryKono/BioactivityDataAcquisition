"""Unit tests for runtime runner builder leaf module."""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from bioetl.composition.runtime_builders import runner_builder


class _FakeFactory:
    def __init__(self) -> None:
        self.kwargs: dict[str, object] | None = None

    def create_runner(self, **kwargs: object) -> object:
        self.kwargs = kwargs
        return "runner-instance"


class _FakeRegistry:
    def __init__(self, factory: _FakeFactory) -> None:
        self._factory = factory

    def get(self, pipeline_name: str) -> SimpleNamespace:
        return SimpleNamespace(factory=self._factory, pipeline_name=pipeline_name)


def test_build_pipeline_runner_wires_dependencies(monkeypatch) -> None:
    """Builder should assemble dependencies and pass them to pipeline factory."""
    fake_factory = _FakeFactory()
    fake_registry = _FakeRegistry(factory=fake_factory)

    calls: dict[str, object] = {}

    monkeypatch.setattr(
        runner_builder,
        "register_all_providers",
        lambda: calls.setdefault("providers", True),
    )
    monkeypatch.setattr(
        runner_builder,
        "register_all_pipelines",
        lambda registry=None: calls.setdefault("pipelines_registry", registry),
    )
    monkeypatch.setattr(
        runner_builder,
        "get_settings",
        lambda: SimpleNamespace(
            pipeline=SimpleNamespace(heartbeat_interval=30), test_mode=False
        ),
    )
    monkeypatch.setattr(
        runner_builder,
        "load_pipeline_config",
        lambda _: SimpleNamespace(
            maintenance={"retain_days": 7}, input_filter=SimpleNamespace()
        ),
    )

    logger_calls: list[tuple[str, dict[str, object]]] = []
    logger = SimpleNamespace(
        info=lambda event, **kwargs: logger_calls.append((event, kwargs)),
    )
    monkeypatch.setattr(
        runner_builder,
        "_build_observability_bundle",
        lambda **_: SimpleNamespace(logger=logger),
    )
    monkeypatch.setattr(
        runner_builder, "_assemble_vacuum_settings", lambda **_: "vacuum"
    )
    monkeypatch.setattr(
        runner_builder, "_assemble_runtime_config", lambda **_: "runtime"
    )
    monkeypatch.setattr(
        runner_builder,
        "_assemble_filter_config",
        lambda **_: SimpleNamespace(
            source_path="ids.csv",
            column_name="molecule_id",
            filter_field="molecule_id",
        ),
    )
    monkeypatch.setattr(
        runner_builder,
        "_assemble_cached_bronze_context",
        lambda _: SimpleNamespace(
            enabled=True, bronze_path="/tmp/bronze", bronze_date="2026-01-01"
        ),
    )

    context = SimpleNamespace(
        pipeline_name="chembl_activity",
        run_id=uuid4(),
        log_level="INFO",
        vacuum=None,
        run_type="incremental",
        resume=False,
        limit=100,
        query=None,
        dry_run=False,
        skip_gold=False,
        input_filter=SimpleNamespace(enabled=False),
    )

    result = runner_builder.build_pipeline_runner(context, registry=fake_registry)

    assert result == "runner-instance"
    assert calls["providers"] is True
    assert calls["pipelines_registry"] is fake_registry
    assert fake_factory.kwargs is not None
    assert fake_factory.kwargs["runtime"] == "runtime"
    assert fake_factory.kwargs["cached_bronze"].enabled is True
    assert [event for event, _ in logger_calls] == [
        "input_filter_enabled",
        "cached_bronze_mode_enabled",
    ]


def test_build_pipeline_runner_uses_default_registry(monkeypatch) -> None:
    """Builder should use default registry when no explicit registry is provided."""
    fake_factory = _FakeFactory()
    default_registry = _FakeRegistry(factory=fake_factory)

    monkeypatch.setattr(runner_builder, "register_all_providers", lambda: None)
    monkeypatch.setattr(
        runner_builder, "register_all_pipelines", lambda registry=None: None
    )
    monkeypatch.setattr(
        runner_builder, "get_default_registry", lambda: default_registry
    )
    monkeypatch.setattr(
        runner_builder,
        "get_settings",
        lambda: SimpleNamespace(
            pipeline=SimpleNamespace(heartbeat_interval=15), test_mode=True
        ),
    )
    monkeypatch.setattr(
        runner_builder,
        "load_pipeline_config",
        lambda _: SimpleNamespace(maintenance=None, input_filter=None),
    )
    monkeypatch.setattr(
        runner_builder,
        "_build_observability_bundle",
        lambda **_: SimpleNamespace(logger=SimpleNamespace(info=lambda *_, **__: None)),
    )
    monkeypatch.setattr(runner_builder, "_assemble_vacuum_settings", lambda **_: None)
    monkeypatch.setattr(
        runner_builder, "_assemble_runtime_config", lambda **_: "runtime"
    )
    monkeypatch.setattr(runner_builder, "_assemble_filter_config", lambda **_: None)
    monkeypatch.setattr(
        runner_builder,
        "_assemble_cached_bronze_context",
        lambda _: SimpleNamespace(enabled=False),
    )

    context = SimpleNamespace(
        pipeline_name="chembl_activity",
        run_id=uuid4(),
        log_level="INFO",
        vacuum=None,
        run_type="incremental",
        resume=False,
        limit=None,
        query=None,
        dry_run=False,
        skip_gold=False,
        input_filter=SimpleNamespace(enabled=False),
    )

    result = runner_builder.build_pipeline_runner(context)

    assert result == "runner-instance"
    assert fake_factory.kwargs is not None
    assert fake_factory.kwargs["runtime"] == "runtime"
