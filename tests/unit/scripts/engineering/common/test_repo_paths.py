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
"""Unit tests for shared script path confinement helpers."""

from __future__ import annotations

from pathlib import Path

import pytest
from scripts.engineering.common.repo_paths import (
    REPO_ROOT,
    argparse_repo_path,
    confined_io_path,
    ensure_path_within_root,
    ensure_repo_path,
    open_confined,
    read_text_confined,
    read_text_confined_or_none,
    rebuild_confined_path,
    resolve_cli_path,
    write_text_confined,
)

pytestmark = pytest.mark.unit


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
    assert (
        resolved
        == (
            REPO_ROOT / "scripts" / "engineering" / "common" / "repo_paths.py"
        ).resolve()
    )


def test_ensure_local_http_url_accepts_loopback() -> None:
    from scripts.engineering.common.repo_paths import ensure_local_http_url

    assert ensure_local_http_url("http://localhost:9090/") == "http://localhost:9090"
    assert ensure_local_http_url("http://prometheus:9090") == "http://prometheus:9090"
    assert ensure_local_http_url("http://pushgateway:9091") == "http://pushgateway:9091"


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

    root = r"E:\workspace\example\BioactivityDataAcquisition2"
    assert ensure_safe_cli_argv(["git", "-C", root, "ls-files"]) == [
        "git",
        "-C",
        root,
        "ls-files",
    ]


def test_ensure_safe_cli_argv_rejects_command_chaining_metacharacters() -> None:
    from scripts.engineering.common.repo_paths import ensure_safe_cli_argv

    with pytest.raises(ValueError, match="shell metacharacters"):
        ensure_safe_cli_argv(["python", "-c", "print(1); rm -rf /"])


def test_rebuild_confined_path_joins_relative_parts(tmp_path: Path) -> None:
    target = tmp_path / "reports" / "quality" / "x.json"
    target.parent.mkdir(parents=True)
    target.write_text("{}", encoding="utf-8")
    rebuilt = rebuild_confined_path(target, root=tmp_path)
    assert rebuilt == target.resolve()
    assert rebuilt.is_relative_to(tmp_path.resolve())


def test_confined_io_path_rejects_escape(tmp_path: Path) -> None:
    outside = tmp_path / "escape.txt"
    outside.write_text("x", encoding="utf-8")
    with pytest.raises(ValueError, match="refusing path outside"):
        confined_io_path(outside, root=REPO_ROOT)


def test_confined_io_path_allows_external_absolute_under_custom_root(
    tmp_path: Path,
) -> None:
    target = tmp_path / "out.json"
    target.write_text("{}", encoding="utf-8")
    resolved = confined_io_path(target, root=tmp_path, allow_external_absolute=True)
    assert resolved == target.resolve()


def test_read_text_confined_reads_file_under_root(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "input.txt"
    target.parent.mkdir(parents=True)
    target.write_text("payload", encoding="utf-8")
    assert read_text_confined(target, root=tmp_path) == "payload"


def test_read_text_confined_rejects_traversal(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside.txt"
    outside.write_text("x", encoding="utf-8")
    with pytest.raises(ValueError, match="refusing path outside"):
        read_text_confined(tmp_path / ".." / "outside.txt", root=tmp_path)


def test_read_text_confined_or_none_returns_none_for_missing(
    tmp_path: Path,
) -> None:
    missing = tmp_path / "missing.txt"
    assert read_text_confined_or_none(missing, root=tmp_path) is None


def test_read_text_confined_or_none_reads_existing(tmp_path: Path) -> None:
    target = tmp_path / "present.txt"
    target.write_text("{}", encoding="utf-8")
    assert read_text_confined_or_none(target, root=tmp_path) == "{}"


def test_write_text_confined_writes_under_root(tmp_path: Path) -> None:
    target = tmp_path / "deep" / "dir" / "out.txt"
    written = write_text_confined(target, "content", root=tmp_path)
    assert written == target.resolve()
    assert target.read_text(encoding="utf-8") == "content"


def test_write_text_confined_rejects_escape_without_writing(tmp_path: Path) -> None:
    outside = tmp_path.parent / "escape-write.txt"
    with pytest.raises(ValueError, match="refusing path outside"):
        write_text_confined(tmp_path / ".." / "escape-write.txt", "x", root=tmp_path)
    assert not outside.exists()


def test_write_text_confined_allows_external_absolute(tmp_path: Path) -> None:
    target = tmp_path / "external-out.txt"
    written = write_text_confined(
        target, "ok", root=REPO_ROOT, allow_external_absolute=True
    )
    assert written.read_text(encoding="utf-8") == "ok"


def test_open_confined_reads_csv_rows(tmp_path: Path) -> None:
    import csv

    target = tmp_path / "rows.csv"
    target.write_text("a,b\n1,2\n", encoding="utf-8")
    with open_confined(
        target, "r", root=tmp_path, encoding="utf-8", newline=""
    ) as handle:
        assert list(csv.DictReader(handle)) == [{"a": "1", "b": "2"}]


def test_open_confined_rejects_traversal(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="refusing path outside"):
        open_confined(
            tmp_path / ".." / "nope.txt", "r", root=tmp_path, encoding="utf-8"
        )
