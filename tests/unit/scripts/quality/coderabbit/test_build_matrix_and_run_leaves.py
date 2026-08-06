# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface.
"""Nominal-path coverage for CodeRabbit matrix builders and leaf runner."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.unit


def _import_build_matrix():
    import scripts.quality.coderabbit.build_matrix as build_matrix

    return build_matrix


def _import_run_leaves():
    import scripts.quality.coderabbit.run_leaves as run_leaves

    return run_leaves


def test_write_list_persists_non_empty_file_list_atomically(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """write_list must create a durable newline-terminated artifact under OUT."""
    build_matrix = _import_build_matrix()
    out = tmp_path / "artifacts"
    out.mkdir()
    monkeypatch.setattr(build_matrix, "OUT", out)

    files = [
        "src/bioetl/domain/types/__init__.py",
        "src/bioetl/domain/ports/runtime.py",
    ]
    path = build_matrix.write_list("_S-test-leaf.txt", files)

    assert path == out / "_S-test-leaf.txt"
    assert path.is_file()
    assert path.read_text(encoding="utf-8") == chr(10).join(files) + chr(10)


def test_matrix_generation_writes_leaf_file_list_and_matrix_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Nominal matrix generation with a non-empty leaf must emit consumable artifacts."""
    build_matrix = _import_build_matrix()
    out = tmp_path / "matrix-out"
    out.mkdir()
    monkeypatch.setattr(build_matrix, "OUT", out)
    monkeypatch.setattr(build_matrix, "CAP", 10)

    tracked = [f"src/bioetl/domain/pkg/file_{i:02d}.py" for i in range(4)]
    leaves: list[dict[str, object]] = []
    for i in range(0, len(tracked), build_matrix.CAP):
        chunk = tracked[i : i + build_matrix.CAP]
        lid = "S01-domain-pkg"
        lp = build_matrix.write_list(f"_{lid}.txt", chunk)
        leaves.append(
            {
                "id": lid,
                "wave": "A",
                "globs": ["domain pkg selection"],
                "files": len(chunk),
                "under_cap": True,
                "dir": None,
                "use_file_list": str(lp),
                "note": "domain pkg selection",
            }
        )

    assert len(leaves) == 1
    list_path = Path(str(leaves[0]["use_file_list"]))
    assert list_path.is_file()
    assert list_path.read_text(encoding="utf-8").splitlines() == tracked

    matrix = {
        "campaign": "CR-FULL-test",
        "base_sha": "deadbeefcafebabe",
        "cap": build_matrix.CAP,
        "leaf_count": len(leaves),
        "total_files_assigned": sum(
            build_matrix._leaf_file_count(item) for item in leaves
        ),
        "leaves": leaves,
    }
    matrix_path = out / "01-scope-matrix.json"
    build_matrix.atomic_write(
        matrix_path,
        json.dumps(matrix, indent=2, ensure_ascii=False, sort_keys=True),
    )
    loaded = json.loads(matrix_path.read_text(encoding="utf-8"))
    assert loaded["leaf_count"] == 1
    assert loaded["total_files_assigned"] == 4
    assert loaded["leaves"][0]["id"] == "S01-domain-pkg"
    assert Path(loaded["leaves"][0]["use_file_list"]).read_text(
        encoding="utf-8"
    ).splitlines() == tracked


def test_run_leaf_dir_path_invokes_coderabbit_with_prefaced_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """run_leaf must resolve the coderabbit executable and prefix PATH for WSL installs."""
    run_leaves = _import_run_leaves()
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    monkeypatch.setattr(run_leaves, "LOG_DIR", log_dir)
    monkeypatch.setattr(run_leaves, "CODERABBIT", "coderabbit")
    monkeypatch.setenv("PATH", "/usr/bin")

    captured: dict[str, Any] = {}

    def fake_run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        captured["cmd"] = list(cmd)
        captured["env"] = dict(kwargs.get("env") or {})
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="review ok" + chr(10),
            stderr="",
        )

    monkeypatch.setattr(run_leaves.subprocess, "run", fake_run)

    result = run_leaves.run_leaf(
        {"id": "S02-app-core", "wave": "A", "dir": "src/bioetl/application/core"},
        base="main",
    )

    assert result["status"] == "ok"
    assert captured["cmd"] == [
        "coderabbit",
        "review",
        "--base",
        "main",
        "--dir",
        "src/bioetl/application/core",
        "--plain",
    ]
    path_env = str(captured["env"].get("PATH", ""))
    assert path_env.startswith("/home/fedor/.local/bin:")
    assert "/usr/bin" in path_env
    assert captured["env"].get("NO_COLOR") == "1"
    assert captured["env"].get("TERM") == "dumb"
    assert result["cmd"] == captured["cmd"]
    log_path = Path(str(result["log"]))
    assert log_path.is_file()
    assert "review ok" in log_path.read_text(encoding="utf-8")


def test_run_leaf_consumes_file_list_artifact_from_write_list(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """File-list leaves must read write_list artifacts and review the common prefix dir."""
    build_matrix = _import_build_matrix()
    run_leaves = _import_run_leaves()

    out = tmp_path / "artifacts"
    out.mkdir()
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    monkeypatch.setattr(build_matrix, "OUT", out)
    monkeypatch.setattr(run_leaves, "LOG_DIR", log_dir)
    monkeypatch.setattr(run_leaves, "CODERABBIT", "coderabbit")

    files = [
        "src/bioetl/domain/types/a.py",
        "src/bioetl/domain/types/b.py",
    ]
    list_path = build_matrix.write_list("_S01-domain-types.txt", files)

    captured: dict[str, Any] = {}

    def fake_run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        if cmd and cmd[0] == "git":
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=0,
                stdout=chr(10).join(files) + chr(10),
                stderr="",
            )
        captured["cmd"] = list(cmd)
        captured["env"] = dict(kwargs.get("env") or {})
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="ok" + chr(10),
            stderr="",
        )

    monkeypatch.setattr(run_leaves.subprocess, "run", fake_run)

    result = run_leaves.run_leaf(
        {
            "id": "S01-domain-types",
            "wave": "A",
            "use_file_list": str(list_path),
            "files": str(len(files)),
        },
        base="origin/main",
    )

    assert result["status"] == "ok"
    assert captured["cmd"] == [
        "coderabbit",
        "review",
        "--base",
        "origin/main",
        "--dir",
        "src/bioetl/domain/types",
        "--plain",
    ]
    assert str(captured["env"].get("PATH", "")).startswith("/home/fedor/.local/bin:")
