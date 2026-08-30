"""Security regressions for the local WSL proxy listener."""

from __future__ import annotations

import pytest

from scripts.ops.runtime.wsl import wsl_proxy

pytestmark = pytest.mark.unit


def test_parse_listen_settings_defaults_to_loopback() -> None:
    assert wsl_proxy._parse_listen_settings([]) == ("127.0.0.1", 3128)


def test_parse_listen_settings_allows_explicit_wsl_interface() -> None:
    assert wsl_proxy._parse_listen_settings(
        ["--listen-host", "172.30.96.1", "--listen-port", "3129"]
    ) == ("172.30.96.1", 3129)


@pytest.mark.parametrize("listener_host", ["0.0.0.0", "::", "localhost"])
def test_parse_listen_settings_rejects_non_concrete_addresses(
    listener_host: str,
) -> None:
    with pytest.raises(SystemExit, match="2"):
        wsl_proxy._parse_listen_settings(["--listen-host", listener_host])
