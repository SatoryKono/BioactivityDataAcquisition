"""RF-002 remainder: script/GHA/Docker sink regressions (#9062)."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.engineering.apply_s1_c2_fixes import replace_once
from scripts.engineering.common.repo_paths import ensure_safe_cli_argv
from scripts.ops.runtime.docker.check_network_preconditions import _run

pytestmark = pytest.mark.security


def test_ensure_safe_cli_argv_rejects_metacharacters() -> None:
    with pytest.raises(ValueError, match="shell metacharacters"):
        ensure_safe_cli_argv(["docker", "inspect", "a;rm"])


def test_check_network_run_rejects_injected_argv() -> None:
    with pytest.raises(ValueError, match="shell metacharacters"):
        _run(["docker", "network", "ls", "x|y"])


def test_apply_s1_c2_replace_once_rejects_escape(tmp_path: Path) -> None:
    victim = tmp_path / "outside.py"
    victim.write_text("keep\n", encoding="utf-8")
    with pytest.raises(ValueError, match="refusing path outside"):
        replace_once(victim, "keep", "gone", "escape")
