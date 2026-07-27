"""Unit tests for pytest last-failed empty-suite exit normalization."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from tests import conftest as root_conftest

pytestmark = pytest.mark.unit


@dataclass
class _FakeOptionNamespace:
    lf: bool = False
    tbstyle: str | None = None
    numprocesses: object | None = None
    timeout: object | None = None


@dataclass
class _FakeConfig:
    option: _FakeOptionNamespace
    _bioetl_last_failed_collected_count: int = 0

    def getoption(self, name: str) -> bool:
        if name == "lf":
            return self.option.lf
        raise ValueError(name)

    def getini(self, name: str) -> object:
        if name == "timeout":
            return "60"
        raise ValueError(name)


@dataclass
class _FakeSession:
    config: _FakeConfig
    testscollected: int
    exitstatus: int | pytest.ExitCode | None = None


class _FakePytestItem:
    def __init__(
        self,
        *,
        config: _FakeConfig | None = None,
        markers: dict[str, object] | None = None,
        nodeid: str = "test_item.py::test_func",
    ) -> None:
        self.config = config or _FakeConfig(option=_FakeOptionNamespace())
        self._markers = markers or {}
        self.added_markers: list[object] = []
        self.nodeid = nodeid

    def get_closest_marker(self, name: str) -> object | None:
        return self._markers.get(name)

    def add_marker(self, marker: object) -> None:
        self.added_markers.append(marker)


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

    item = _FakePytestItem(config=config)
    root_conftest.pytest_itemcollected(item)
    root_conftest.pytest_itemcollected(item)

    assert root_conftest._last_failed_collected_count(config) == 2


def test_windows_pycharm_traceback_policy_uses_line_style(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _FakeConfig(option=_FakeOptionNamespace(tbstyle="short"))
    monkeypatch.setattr(root_conftest.sys, "platform", "win32")
    monkeypatch.setenv("PYCHARM_HOSTED", "1")

    root_conftest._configure_windows_pycharm_traceback_style(config)

    assert config.option.tbstyle == "line"


def test_windows_pytest_bootstrap_overrides_disabled_test_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(root_conftest.sys, "platform", "win32")
    monkeypatch.setenv("BIOETL_TEST_MODE", "false")

    root_conftest._configure_windows_test_mode_for_control_plane_durability()

    assert root_conftest.os.environ["BIOETL_TEST_MODE"] == "true"


def test_windows_pycharm_traceback_policy_preserves_safe_style(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _FakeConfig(option=_FakeOptionNamespace(tbstyle="no"))
    monkeypatch.setattr(root_conftest.sys, "platform", "win32")
    monkeypatch.setenv("PYCHARM_HOSTED", "1")

    root_conftest._configure_windows_pycharm_traceback_style(config)

    assert config.option.tbstyle == "no"


def test_windows_traceback_policy_skips_non_pycharm_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _FakeConfig(option=_FakeOptionNamespace(tbstyle="short"))
    monkeypatch.setattr(root_conftest.sys, "platform", "win32")
    monkeypatch.delenv("PYCHARM_HOSTED", raising=False)
    monkeypatch.setattr(root_conftest.sys, "argv", ["pytest"])

    root_conftest._configure_windows_pycharm_traceback_style(config)

    assert config.option.tbstyle == "short"


def test_windows_pycharm_traceback_policy_detects_jetbrains_runner_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _FakeConfig(option=_FakeOptionNamespace(tbstyle="long"))
    monkeypatch.setattr(root_conftest.sys, "platform", "win32")
    monkeypatch.delenv("PYCHARM_HOSTED", raising=False)
    monkeypatch.setattr(
        root_conftest.sys,
        "argv",
        ["C:/Program Files/JetBrains/PyCharm/helpers/pycharm/_jb_pytest_runner.py"],
    )

    root_conftest._configure_windows_pycharm_traceback_style(config)

    assert config.option.tbstyle == "line"


def test_windows_pycharm_vcr_timeout_policy_extends_default_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    item = _FakePytestItem(markers={"vcr": pytest.mark.vcr.mark})
    monkeypatch.setattr(root_conftest.sys, "platform", "win32")
    monkeypatch.setenv("PYCHARM_HOSTED", "1")

    root_conftest._extend_windows_pycharm_vcr_timeout(item)

    assert len(item.added_markers) == 1
    timeout_marker = item.added_markers[0].mark
    assert timeout_marker.name == "timeout"
    assert timeout_marker.args == (180,)


def test_windows_pycharm_vcr_timeout_policy_preserves_explicit_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    item = _FakePytestItem(
        markers={
            "vcr": pytest.mark.vcr.mark,
            "timeout": pytest.mark.timeout(120).mark,
        }
    )
    monkeypatch.setattr(root_conftest.sys, "platform", "win32")
    monkeypatch.setenv("PYCHARM_HOSTED", "1")

    root_conftest._extend_windows_pycharm_vcr_timeout(item)

    assert item.added_markers == []


def test_windows_pycharm_vcr_timeout_policy_skips_non_vcr_tests(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    item = _FakePytestItem()
    monkeypatch.setattr(root_conftest.sys, "platform", "win32")
    monkeypatch.setenv("PYCHARM_HOSTED", "1")

    root_conftest._extend_windows_pycharm_vcr_timeout(item)

    assert item.added_markers == []


def test_windows_pycharm_vcr_timeout_policy_respects_larger_cli_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    item = _FakePytestItem(
        config=_FakeConfig(option=_FakeOptionNamespace(timeout=300)),
        markers={"vcr": pytest.mark.vcr.mark},
    )
    monkeypatch.setattr(root_conftest.sys, "platform", "win32")
    monkeypatch.setenv("PYCHARM_HOSTED", "1")

    root_conftest._extend_windows_pycharm_vcr_timeout(item)

    assert item.added_markers == []


def test_windows_xdist_policy_caps_auto_workers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _FakeConfig(option=_FakeOptionNamespace(numprocesses="auto"))
    monkeypatch.setattr(root_conftest.sys, "platform", "win32")
    monkeypatch.delenv("BIOETL_PYTEST_WINDOWS_XDIST_WORKERS", raising=False)

    root_conftest._configure_windows_xdist(config)

    assert config.option.numprocesses == 1


def test_windows_xdist_policy_caps_explicit_worker_count(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _FakeConfig(option=_FakeOptionNamespace(numprocesses=8))
    monkeypatch.setattr(root_conftest.sys, "platform", "win32")
    monkeypatch.delenv("BIOETL_PYTEST_WINDOWS_XDIST_WORKERS", raising=False)

    root_conftest._configure_windows_xdist(config)

    assert config.option.numprocesses == 1


def test_windows_xdist_policy_respects_env_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _FakeConfig(option=_FakeOptionNamespace(numprocesses="auto"))
    monkeypatch.setattr(root_conftest.sys, "platform", "win32")
    monkeypatch.setenv("BIOETL_PYTEST_WINDOWS_XDIST_WORKERS", "1")

    root_conftest._configure_windows_xdist(config)

    assert config.option.numprocesses == 1


def test_windows_xdist_policy_skips_non_windows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _FakeConfig(option=_FakeOptionNamespace(numprocesses="auto"))
    monkeypatch.setattr(root_conftest.sys, "platform", "linux")

    root_conftest._configure_windows_xdist(config)

    assert config.option.numprocesses == "auto"
