from __future__ import annotations

from types import SimpleNamespace

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
