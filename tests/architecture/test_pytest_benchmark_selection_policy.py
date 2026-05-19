from __future__ import annotations

from types import SimpleNamespace

from tests.benchmarks.conftest import (
    _DisabledBenchmarkFixturePlugin,
    _benchmark_plugin_active,
    pytest_configure as _benchmark_pytest_configure,
)
from tests.conftest import (
    _auto_enable_benchmark_selection_for_explicit_benchmark_runs,
    _selected_paths_are_benchmark_only,
    _selected_test_paths,
)


def _build_config(*args: str, markexpr: str = "not benchmark and not slow") -> object:
    return SimpleNamespace(
        args=list(args),
        option=SimpleNamespace(markexpr=markexpr),
    )


def test_selected_test_paths_normalize_explicit_nodeids() -> None:
    config = _build_config(
        r"tests\benchmarks\test_performance.py::TestHashBenchmarks::test_small_record"
    )

    assert _selected_test_paths(config) == ("tests/benchmarks/test_performance.py",)


def test_selected_paths_are_benchmark_only_for_benchmark_suite() -> None:
    config = _build_config("tests/benchmarks")

    assert _selected_paths_are_benchmark_only(config) is True


def test_selected_paths_are_not_benchmark_only_for_full_tests_root() -> None:
    config = _build_config("tests")

    assert _selected_paths_are_benchmark_only(config) is False


def test_auto_enable_benchmark_selection_for_explicit_benchmark_suite() -> None:
    config = _build_config("tests/benchmarks")

    _auto_enable_benchmark_selection_for_explicit_benchmark_runs(config)

    assert config.option.markexpr == "benchmark"


def test_auto_enable_benchmark_selection_does_not_override_explicit_markexpr() -> None:
    config = _build_config("tests/benchmarks", markexpr="benchmark and performance")

    _auto_enable_benchmark_selection_for_explicit_benchmark_runs(config)

    assert config.option.markexpr == "benchmark and performance"


def test_auto_enable_benchmark_selection_does_not_override_mixed_suite() -> None:
    config = _build_config("tests/benchmarks", "tests/unit")

    _auto_enable_benchmark_selection_for_explicit_benchmark_runs(config)

    assert config.option.markexpr == "not benchmark and not slow"


def test_benchmark_plugin_active_detects_registered_plugin_aliases() -> None:
    pluginmanager = SimpleNamespace(hasplugin=lambda name: name == "benchmark")
    config = SimpleNamespace(pluginmanager=pluginmanager)

    assert _benchmark_plugin_active(config) is True


def test_benchmark_plugin_active_is_false_when_plugin_is_disabled() -> None:
    pluginmanager = SimpleNamespace(hasplugin=lambda _name: False)
    config = SimpleNamespace(pluginmanager=pluginmanager)

    assert _benchmark_plugin_active(config) is False


def test_benchmark_pytest_configure_registers_skip_fixture_when_plugin_is_disabled() -> (
    None
):
    registrations: list[tuple[object, str]] = []

    class _PluginManager:
        def hasplugin(self, name: str) -> bool:
            return False

        def register(self, plugin: object, name: str) -> None:
            registrations.append((plugin, name))

    config = SimpleNamespace(pluginmanager=_PluginManager())

    _benchmark_pytest_configure(config)

    assert len(registrations) == 1
    plugin, name = registrations[0]
    assert name == "bioetl-disabled-benchmark-fixture"
    assert isinstance(plugin, _DisabledBenchmarkFixturePlugin)


def test_benchmark_pytest_configure_skips_registration_when_plugin_is_active() -> None:
    registrations: list[tuple[object, str]] = []

    class _PluginManager:
        def hasplugin(self, name: str) -> bool:
            return name == "benchmark"

        def register(self, plugin: object, name: str) -> None:
            registrations.append((plugin, name))

    config = SimpleNamespace(pluginmanager=_PluginManager())

    _benchmark_pytest_configure(config)

    assert registrations == []
