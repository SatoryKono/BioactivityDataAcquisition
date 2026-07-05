"""Local socket capability guard for HTTP interface unit tests."""

from __future__ import annotations

from functools import cache
from pathlib import Path
import socket

import pytest

_SOCKET_BACKED_TEST_MODULES = frozenset(
    {
        "test_health_server.py",
        "test_health_server_control_plane_checkpoint_freshness.py",
        "test_health_server_control_plane_identity.py",
        "test_processed_records_table.py",
    }
)


@cache
def _local_tcp_socket_available() -> bool:
    try:
        sock = socket.socket()
    except OSError:
        return False
    try:
        sock.bind(("127.0.0.1", 0))
    except OSError:
        return False
    finally:
        sock.close()
    return True


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    if _local_tcp_socket_available():
        return

    skip_local_socket = pytest.mark.skip(
        reason="Local TCP sockets are unavailable in this test environment."
    )
    for item in items:
        if Path(str(item.path)).name in _SOCKET_BACKED_TEST_MODULES:
            item.add_marker(skip_local_socket)
