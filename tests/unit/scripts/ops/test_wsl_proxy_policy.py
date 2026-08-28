"""Unit contracts for the Windows-side WSL proxy bind policy."""

from __future__ import annotations

import ipaddress

import pytest

from scripts.ops.runtime.wsl import wsl_proxy


pytestmark = pytest.mark.unit


def test_loopback_is_the_safe_default() -> None:
    host, networks = wsl_proxy.build_bind_policy(
        "127.0.0.1", allow_wildcard=False, allow_cidrs=[]
    )

    assert host == "127.0.0.1"
    assert networks == (ipaddress.ip_network("127.0.0.0/8"),)
    assert wsl_proxy.is_client_allowed("127.0.0.2", networks)
    assert not wsl_proxy.is_client_allowed("172.30.32.2", networks)


def test_wildcard_requires_opt_in_and_nonempty_allowlist() -> None:
    with pytest.raises(ValueError, match="allow-wildcard"):
        wsl_proxy.build_bind_policy(
            "0.0.0.0", allow_wildcard=False, allow_cidrs=["172.30.32.0/20"]
        )
    with pytest.raises(ValueError, match="allow-cidr"):
        wsl_proxy.build_bind_policy("0.0.0.0", allow_wildcard=True, allow_cidrs=[])
    with pytest.raises(ValueError, match="unrestricted"):
        wsl_proxy.build_bind_policy(
            "0.0.0.0", allow_wildcard=True, allow_cidrs=["0.0.0.0/0"]
        )


def test_public_interface_bind_is_rejected() -> None:
    with pytest.raises(ValueError, match="private WSL adapter"):
        wsl_proxy.build_bind_policy(
            "203.0.113.1", allow_wildcard=False, allow_cidrs=["172.30.32.0/20"]
        )


def test_explicit_wsl_bind_enforces_client_subnet() -> None:
    host, networks = wsl_proxy.build_bind_policy(
        "172.30.32.1",
        allow_wildcard=False,
        allow_cidrs=["172.30.32.0/20"],
    )

    assert host == "172.30.32.1"
    assert wsl_proxy.is_client_allowed("172.30.47.254", networks)
    assert not wsl_proxy.is_client_allowed("172.30.48.1", networks)
    assert not wsl_proxy.is_client_allowed("not-an-ip", networks)


@pytest.mark.parametrize("value", ["not-a-cidr", "::1/128"])
def test_allowlist_rejects_invalid_or_ipv6_cidrs(value: str) -> None:
    with pytest.raises(ValueError):
        wsl_proxy.parse_allow_cidrs([value])
