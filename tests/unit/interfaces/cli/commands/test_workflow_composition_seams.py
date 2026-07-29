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
"""Tests for lazy workflow CLI composition seams."""

from __future__ import annotations

import pytest

from bioetl.composition import control_plane_service_access
from bioetl.interfaces.cli.commands import _workflow_composition_seams as seams

pytestmark = pytest.mark.unit


def test_workflow_composition_seams_delegate_to_control_plane_service_access(
    monkeypatch,
) -> None:
    registry = object()
    calls: list[tuple[str, object]] = []

    monkeypatch.setattr(
        control_plane_service_access,
        "load_workflow_config",
        lambda name: calls.append(("load", name)) or "workflow-config",
    )
    monkeypatch.setattr(
        control_plane_service_access,
        "get_workflow_execution_service",
        lambda *, registry=None: (
            calls.append(("execute", registry)) or "execution-service"
        ),
    )
    monkeypatch.setattr(
        control_plane_service_access,
        "get_workflow_inspection_service",
        lambda: calls.append(("inspect", None)) or "inspection-service",
    )

    assert seams.load_workflow_config("daily") == "workflow-config"
    assert seams.get_workflow_execution_service(registry) == "execution-service"
    assert seams.get_workflow_inspection_service() == "inspection-service"
    assert calls == [
        ("load", "daily"),
        ("execute", registry),
        ("inspect", None),
    ]
