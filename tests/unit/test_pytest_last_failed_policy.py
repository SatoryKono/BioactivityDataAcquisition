"""Unit tests for pytest last-failed empty-suite exit normalization."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from tests import conftest as root_conftest


@dataclass
class _FakeOptionNamespace:
    lf: bool = False


@dataclass
class _FakeConfig:
    option: _FakeOptionNamespace
    _bioetl_last_failed_collected_count: int = 0

    def getoption(self, name: str) -> bool:
        if name == "lf":
            return self.option.lf
        raise ValueError(name)


@dataclass
class _FakeSession:
    config: _FakeConfig
    testscollected: int
    exitstatus: int | pytest.ExitCode | None = None


def test_should_treat_last_failed_empty_suite_as_success() -> None:
    assert root_conftest._should_treat_last_failed_empty_suite_as_success(
        config=_FakeConfig(option=_FakeOptionNamespace(lf=True)),
        collected_count=4,
        exitstatus=pytest.ExitCode.NO_TESTS_COLLECTED,
    )


def test_should_not_treat_real_empty_collection_as_success() -> None:
    assert not root_conftest._should_treat_last_failed_empty_suite_as_success(
        config=_FakeConfig(option=_FakeOptionNamespace(lf=True)),
        collected_count=0,
        exitstatus=pytest.ExitCode.NO_TESTS_COLLECTED,
    )


def test_should_not_treat_non_last_failed_run_as_success() -> None:
    assert not root_conftest._should_treat_last_failed_empty_suite_as_success(
        config=_FakeConfig(option=_FakeOptionNamespace(lf=False)),
        collected_count=4,
        exitstatus=pytest.ExitCode.NO_TESTS_COLLECTED,
    )


def test_pytest_sessionfinish_normalizes_last_failed_empty_suite() -> None:
    session = _FakeSession(
        config=_FakeConfig(
            option=_FakeOptionNamespace(lf=True),
            _bioetl_last_failed_collected_count=4,
        ),
        testscollected=4,
        exitstatus=pytest.ExitCode.NO_TESTS_COLLECTED,
    )

    root_conftest.pytest_sessionfinish(session, pytest.ExitCode.NO_TESTS_COLLECTED)

    assert session.exitstatus == 0


def test_pytest_sessionfinish_keeps_genuine_no_tests_failure() -> None:
    session = _FakeSession(
        config=_FakeConfig(option=_FakeOptionNamespace(lf=False)),
        testscollected=0,
        exitstatus=pytest.ExitCode.NO_TESTS_COLLECTED,
    )

    root_conftest.pytest_sessionfinish(session, pytest.ExitCode.NO_TESTS_COLLECTED)

    assert session.exitstatus == pytest.ExitCode.NO_TESTS_COLLECTED


def test_pytest_itemcollected_tracks_pre_deselection_count() -> None:
    config = _FakeConfig(option=_FakeOptionNamespace(lf=True))
    root_conftest._reset_last_failed_collection_state(config)

    item = type("Item", (), {"config": config})()
    root_conftest.pytest_itemcollected(item)
    root_conftest.pytest_itemcollected(item)

    assert root_conftest._last_failed_collected_count(config) == 2
