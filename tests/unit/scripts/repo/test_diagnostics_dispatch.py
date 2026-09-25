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
"""Dispatch targets for scripts.engineering.diagnostics stay on disk."""

from __future__ import annotations

import pytest

from scripts.engineering.diagnostics.__main__ import COMMANDS, _DIR

pytestmark = pytest.mark.unit


def test_diagnostics_dispatch_targets_exist() -> None:
    """#11048: inspect-vcr pointed at a missing _tmp_inspect_vcr.py."""
    assert "inspect-vcr" not in COMMANDS
    missing = [
        name for name, script in COMMANDS.items() if not (_DIR / script).is_file()
    ]
    assert missing == []
