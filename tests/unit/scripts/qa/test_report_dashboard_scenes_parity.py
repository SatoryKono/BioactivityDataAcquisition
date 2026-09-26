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
"""Tests for the deterministic Grafana Scenes parity ledger generator."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.engineering.qa.report_dashboard_scenes_parity import _sha256

pytestmark = pytest.mark.unit


def test_sha256_normalizes_json_line_endings(tmp_path: Path) -> None:
    lf_path = tmp_path / "lf.json"
    crlf_path = tmp_path / "crlf.json"
    lf_path.write_bytes(b'{\n  "status": "ok"\n}\n')
    crlf_path.write_bytes(b'{\r\n  "status": "ok"\r\n}\r\n')

    assert _sha256(lf_path) == _sha256(crlf_path)
