# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
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
        "test_health_server_control_plane_validation_evidence.py",
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
