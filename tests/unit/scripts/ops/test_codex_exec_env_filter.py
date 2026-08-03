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
"""Coverage for Codex launcher env allow-list filtering."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest


pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[4]
CODEX_EXEC = ROOT / "scripts" / "ops" / "launchers" / "codex" / "codex-exec.sh"
RUN_CODEX_IMPL = ROOT / "scripts" / "ai" / "codex" / "helper" / "run-codex-impl.sh"

# Only REF is injected into the Codex parent process (remote HTTP MCP header).
CODEX_PARENT_ALLOWLIST = frozenset({"REF_TOOL_API_KEY"})


def _filter_codex_parent_env(env: dict[str, str]) -> dict[str, str]:
    """Mirror shell allow-list: non-empty allow-listed keys only."""
    return {
        key: value
        for key, value in env.items()
        if key in CODEX_PARENT_ALLOWLIST and value != ""
    }


def test_codex_parent_allowlist_is_ref_only_in_launchers() -> None:
    for path in (CODEX_EXEC, RUN_CODEX_IMPL):
        text = path.read_text(encoding="utf-8")
        assert "REF_TOOL_API_KEY" in text
        # Wrapper-scoped secrets must not be exported into the Codex process.
        for banned in (
            "BRAVE_API_KEY",
            "GITHUB_PERSONAL_ACCESS_TOKEN",
            "GITHUB_TOKEN",
            "HUB_PAT_TOKEN",
            "DOCKERHUB_USERNAME",
            "NEO4J_PASSWORD",
            "GRAFANA_SERVICE_ACCOUNT_TOKEN",
            "GRAFANA_USERNAME",
            "GRAFANA_PASSWORD",
        ):
            assert banned not in text, f"{path}: unexpected parent export of {banned}"


def test_codex_parent_env_filter_keeps_only_nonempty_allowlisted() -> None:
    filtered = _filter_codex_parent_env(
        {
            "REF_TOOL_API_KEY": "ref-secret",
            "BRAVE_API_KEY": "brave-secret",
            "GITHUB_TOKEN": "",
            "UNRELATED": "nope",
        }
    )
    assert filtered == {"REF_TOOL_API_KEY": "ref-secret"}


def test_codex_parent_env_filter_drops_empty_allowlisted() -> None:
    filtered = _filter_codex_parent_env(
        {
            "REF_TOOL_API_KEY": "",
            "UNRELATED": "value",
        }
    )
    assert filtered == {}


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="child-process env probe uses POSIX env; launchers covered by allow-list source test",
)
def test_child_process_receives_only_filtered_env(tmp_path: Path) -> None:
    """Launch a child and assert it sees only non-empty allow-listed keys."""
    seed = {
        "REF_TOOL_API_KEY": "ref-secret",
        "BRAVE_API_KEY": "brave-secret",
        "UNRELATED": "nope",
        "PATH": os.environ.get("PATH", "/usr/bin"),
    }
    filtered = _filter_codex_parent_env(seed)
    # Child inherits only the filtered map (plus PATH for python).
    child_env = {**filtered, "PATH": seed["PATH"]}
    script = (
        "import os, json; "
        "print(json.dumps({k: os.environ.get(k) for k in "
        "['REF_TOOL_API_KEY','BRAVE_API_KEY','UNRELATED']}))"
    )
    proc = subprocess.run(
        [sys.executable, "-c", script],
        env=child_env,
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )
    payload = __import__("json").loads(proc.stdout)
    assert payload["REF_TOOL_API_KEY"] == "ref-secret"
    assert payload["BRAVE_API_KEY"] is None
    assert payload["UNRELATED"] is None
