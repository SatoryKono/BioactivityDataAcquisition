"""Architecture checks for consolidated Copilot/Codex MCP setup wrappers."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_setup_backend_writes_expected_vscode_mcp_config(tmp_path: Path) -> None:
    """Canonical backend should generate .vscode/mcp.json with GitHub MCP server."""
    root = _project_root()
    result = subprocess.run(
        [
            sys.executable,
            "scripts/dev/setup_copilot_codex_mcp.py",
            "--root",
            str(tmp_path),
            "--skip-codex",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    mcp_path = tmp_path / ".vscode" / "mcp.json"
    assert mcp_path.exists()

    payload = json.loads(mcp_path.read_text(encoding="utf-8"))
    assert payload["servers"]["github"]["command"] == "npx"
    assert payload["servers"]["github"]["args"][0] == "-y"


def test_setup_sh_wrapper_delegates_to_backend() -> None:
    """Bash wrapper must stay a thin facade over the Python backend."""
    root = _project_root()
    content = (root / "scripts/dev/setup_copilot_codex_mcp.sh").read_text(
        encoding="utf-8"
    )
    assert "scripts/dev/setup_copilot_codex_mcp.py" in content


def test_setup_ps1_wrapper_delegates_to_backend() -> None:
    """PowerShell wrapper must stay a thin facade over the Python backend."""
    root = _project_root()
    content = (root / "scripts/dev/setup_copilot_codex_mcp.ps1").read_text(
        encoding="utf-8"
    )
    assert "scripts/dev/setup_copilot_codex_mcp.py" in content
