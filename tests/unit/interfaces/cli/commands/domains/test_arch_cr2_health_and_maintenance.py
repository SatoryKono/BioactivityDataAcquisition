"""ARCH-CR2-03/04: health lifecycle order + maintenance command non-mutation."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import click
import pytest

from bioetl.interfaces.cli.commands.domains.maintenance import command_group as maint
from bioetl.interfaces.cli.commands.domains.health import (
    server_integration_lifecycle as lifecycle,
)


@pytest.mark.asyncio
async def test_run_health_server_resolves_quarantine_before_build(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    order: list[str] = []
    deps = MagicMock(name="deps")
    quarantine = MagicMock(name="quarantine")
    server = MagicMock()
    server.start = AsyncMock()
    server.stop = AsyncMock()

    def get_deps(**kwargs):  # type: ignore[no-untyped-def]
        order.append("get_deps")
        return deps

    def get_quarantine(**kwargs):  # type: ignore[no-untyped-def]
        order.append("get_quarantine")
        return quarantine

    def build_server(**kwargs):  # type: ignore[no-untyped-def]
        order.append("build_server")
        assert kwargs.get("quarantine_service") is quarantine
        assert kwargs.get("deps") is deps
        return server

    async def close_resources(**kwargs):  # type: ignore[no-untyped-def]
        order.append("close")

    monkeypatch.setattr(
        lifecycle._deps, "get_health_server_dependencies", get_deps
    )
    monkeypatch.setattr(
        lifecycle._deps,
        "_get_optional_health_server_quarantine_service",
        get_quarantine,
    )
    monkeypatch.setattr(lifecycle._deps, "build_health_server", build_server)
    monkeypatch.setattr(
        lifecycle._deps, "close_health_server_resources", close_resources
    )
    monkeypatch.setattr(
        lifecycle._deps, "build_health_server_pycache_prefix", lambda: Path("/tmp/p")
    )
    monkeypatch.setattr(
        lifecycle._observability, "_start_health_observability", lambda: None
    )

    # Interrupt the keep-alive loop immediately after start.
    async def _sleep(_seconds: float) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(lifecycle.asyncio, "sleep", _sleep)

    with pytest.raises(KeyboardInterrupt):
        await lifecycle._run_health_server("127.0.0.1", 9, start_metrics=False)

    assert order.index("get_quarantine") < order.index("build_server")
    assert order.index("get_deps") < order.index("build_server")


def test_load_maintenance_command_does_not_mutate_shared_name() -> None:
    @click.command("original")
    def sample() -> None:
        """noop"""

    maint._EAGER_MAINTENANCE_COMMANDS["sample-alias"] = (sample, "help")
    try:
        first = maint._load_maintenance_command("sample-alias")
        second = maint._load_maintenance_command("sample-alias")
        assert first is not None and second is not None
        assert first.name == "sample-alias"
        assert second.name == "sample-alias"
        # Registry singleton keeps original name.
        assert sample.name == "original"
    finally:
        maint._EAGER_MAINTENANCE_COMMANDS.pop("sample-alias", None)
