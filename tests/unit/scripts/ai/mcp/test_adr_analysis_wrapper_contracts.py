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
"""Source contracts for the ADR analysis MCP wrappers."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]
PS1 = ROOT / "scripts/ai/mcp/mcp_adr_analysis_wrapper.ps1"
SH = ROOT / "scripts/ai/mcp/mcp_adr_analysis_wrapper.sh"

pytestmark = pytest.mark.unit


def test_powershell_wrapper_respects_existing_npm_config_ignore_scripts() -> None:
    """#6429: do not force-overwrite an operator-set npm_config_ignore_scripts."""
    source = PS1.read_text(encoding="utf-8")
    assert "if (-not $env:npm_config_ignore_scripts)" in source
    assert '$env:npm_config_ignore_scripts = "true"' in source
    # Unconditional assignment must not appear outside the guard.
    unconditional = [
        line
        for line in source.splitlines()
        if line.strip() == '$env:npm_config_ignore_scripts = "true"'
    ]
    assert len(unconditional) == 1
    guarded_block = (
        "if (-not $env:npm_config_ignore_scripts) {\n"
        '    $env:npm_config_ignore_scripts = "true"\n'
        "}"
    )
    assert guarded_block in source.replace("\r\n", "\n")


def test_bash_wrapper_defaults_npm_config_ignore_scripts_without_overwrite() -> None:
    """Bash counterpart keeps the `${var:-true}` default form."""
    source = SH.read_text(encoding="utf-8")
    assert (
        'export npm_config_ignore_scripts="${npm_config_ignore_scripts:-true}"'
        in source
    )
