# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
from __future__ import annotations

import pytest

from scripts.ops.observability.archive_control_plane import main

pytestmark = pytest.mark.unit


def test_archive_control_plane_requires_manifest_argument() -> None:
    raised = False
    try:
        main([])
    except SystemExit:
        raised = True
    assert raised is True
