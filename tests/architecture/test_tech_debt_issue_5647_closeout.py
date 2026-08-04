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
"""Closeout guards for technical-debt issue #5647."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest


pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
CLOSEOUT = ROOT / "reports" / "quality" / "tech-debt-issue-5647-closeout.json"
WIRING_HELPER = (
    ROOT
    / "src"
    / "bioetl"
    / "application"
    / "core"
    / "wiring"
    / "_lazy_export_facade.py"
)
APPLICATION_SHARED_HELPER = (
    ROOT / "src" / "bioetl" / "application" / "core" / "wiring" / "lazy_export_hooks.py"
)
CONTROL_PLANE_HELPER = (
    ROOT
    / "src"
    / "bioetl"
    / "application"
    / "services"
    / "control_plane"
    / "_lazy_export_facade.py"
)
SHARED_HELPER = ROOT / "src" / "bioetl" / "composition" / "lazy_exports.py"


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_issue_5647_lazy_export_helper_implementations_are_unified() -> None:
    wiring_text = WIRING_HELPER.read_text(encoding="utf-8")
    application_shared_text = APPLICATION_SHARED_HELPER.read_text(encoding="utf-8")
    control_plane_text = CONTROL_PLANE_HELPER.read_text(encoding="utf-8")
    shared_text = SHARED_HELPER.read_text(encoding="utf-8")

    assert "def install_lazy_exports(" in shared_text
    assert "from importlib import import_module" in shared_text
    assert "from importlib import import_module" in application_shared_text
    assert "from importlib import import_module" not in wiring_text
    assert "from importlib import import_module" not in control_plane_text
    assert "from bioetl.composition.lazy_exports import" not in wiring_text
    assert "from bioetl.composition.lazy_exports import" not in control_plane_text
    assert "from bioetl.application.core.wiring.lazy_export_hooks import" in (
        wiring_text
    )
    assert "from bioetl.application.core.wiring.lazy_export_hooks import" in (
        control_plane_text
    )
    assert (
        "bioetl.application.core.wiring._lazy_export_facade" not in control_plane_text
    )
    assert "install_lazy_export_facade(" in wiring_text
    assert "_install_lazy_export_facade(" in control_plane_text
