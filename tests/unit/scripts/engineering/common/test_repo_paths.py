"""Unit tests for shared script path confinement helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.engineering.common.repo_paths import (
    REPO_ROOT,
    argparse_repo_path,
    ensure_path_within_root,
    ensure_repo_path,
    resolve_cli_path,
)


def test_ensure_repo_path_accepts_in_tree_path() -> None:
    target = REPO_ROOT / "scripts" / "engineering" / "common" / "repo_paths.py"
    assert ensure_repo_path(target) == target.resolve()


def test_ensure_repo_path_rejects_escape(tmp_path: Path) -> None:
    outside = tmp_path / "outside.txt"
    outside.write_text("x", encoding="utf-8")
    with pytest.raises(ValueError, match="refusing path outside"):
        ensure_repo_path(outside)


def test_ensure_path_within_root_allows_root_itself(tmp_path: Path) -> None:
    assert ensure_path_within_root(tmp_path, tmp_path) == tmp_path.resolve()


def test_resolve_cli_path_joins_relative_under_root() -> None:
    relative = "reports/quality/example.json"
    resolved = resolve_cli_path(relative)
    assert resolved == (REPO_ROOT / relative).resolve()
    assert resolved.is_relative_to(REPO_ROOT.resolve())


def test_resolve_cli_path_rejects_escape(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="refusing path outside"):
        resolve_cli_path(tmp_path / "escape.txt")


def test_argparse_repo_path_accepts_repo_relative() -> None:
    resolved = argparse_repo_path("scripts/engineering/common/repo_paths.py")
    assert resolved == (
        REPO_ROOT / "scripts" / "engineering" / "common" / "repo_paths.py"
    ).resolve()


def test_ensure_local_http_url_accepts_loopback() -> None:
    from scripts.engineering.common.repo_paths import ensure_local_http_url

    assert ensure_local_http_url("http://localhost:9090/") == "http://localhost:9090"
    assert ensure_local_http_url("http://prometheus:9090") == "http://prometheus:9090"


def test_ensure_local_http_url_rejects_remote() -> None:
    from scripts.engineering.common.repo_paths import ensure_local_http_url

    with pytest.raises(ValueError, match="refusing non-local URL host"):
        ensure_local_http_url("http://evil.example/metrics")


def test_ensure_safe_cli_argv_accepts_clean_tokens() -> None:
    from scripts.engineering.common.repo_paths import ensure_safe_cli_argv

    assert ensure_safe_cli_argv(["python", "-m", "pytest"]) == [
        "python",
        "-m",
        "pytest",
    ]


def test_ensure_safe_cli_argv_accepts_windows_paths() -> None:
    from scripts.engineering.common.repo_paths import ensure_safe_cli_argv

    root = r"E:\g-drive\05_AI\github\BioactivityDataAcquisition2"
    assert ensure_safe_cli_argv(["git", "-C", root, "ls-files"]) == [
        "git",
        "-C",
        root,
        "ls-files",
    ]


def test_ensure_safe_cli_argv_rejects_metacharacters() -> None:
    from scripts.engineering.common.repo_paths import ensure_safe_cli_argv

    with pytest.raises(ValueError, match="shell metacharacters"):
        ensure_safe_cli_argv(["python", "-c", "print(1); rm -rf /"])
