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
# Governance checks for runtime UUID generation seams.

from __future__ import annotations

import ast
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "configs/quality/runtime_uuid_seams.yaml"
SCAN_ROOTS = ("src/bioetl",)
UUID4_SCAN_TIMEOUT_SECONDS = 10

pytestmark = pytest.mark.architecture


def _run_bounded_scan(command: list[str]) -> tuple[int, tuple[str, ...]] | None:
    """Run a scanner without PIPE reader threads that can hang on Windows."""
    try:
        with (
            tempfile.TemporaryFile(mode="w+", encoding="utf-8") as stdout_file,
            tempfile.TemporaryFile(mode="w+", encoding="utf-8") as stderr_file,
        ):
            result = subprocess.run(
                command,
                cwd=ROOT,
                check=False,
                stdout=stdout_file,
                stderr=stderr_file,
                text=True,
                timeout=UUID4_SCAN_TIMEOUT_SECONDS,
            )
            stdout_file.seek(0)
            return result.returncode, tuple(stdout_file.read().splitlines())
    except (OSError, subprocess.TimeoutExpired):
        return None


def _uuid4_candidate_files() -> tuple[Path, ...]:
    """Prefilter candidate files so Windows/WSL runs do not parse every module."""
    commands = (
        ["rg", "--files-with-matches", "-F", "uuid4", *SCAN_ROOTS],
        [shutil.which("git") or "git", "grep", "-l", "uuid4", "--", *SCAN_ROOTS],
    )
    for command in commands:
        result = _run_bounded_scan(command)
        if result is None:
            continue
        returncode, output_lines = result
        if returncode == 0:
            return tuple(ROOT / line for line in output_lines if line.endswith(".py"))
        if returncode == 1:
            return ()
    raise AssertionError("Runtime UUID seam scanners failed or timed out")


def _uuid4_seams() -> set[tuple[str, int, str]]:
    seams: set[tuple[str, int, str]] = set()
    for path in _uuid4_candidate_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        rel_path = path.relative_to(ROOT).as_posix()
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "uuid4"
            ):
                seams.add((rel_path, node.lineno, "call"))
            if (
                isinstance(node, ast.keyword)
                and node.arg is not None
                and "uuid" in node.arg
                and isinstance(node.value, ast.Name)
                and node.value.id == "uuid4"
            ):
                seams.add((rel_path, node.value.lineno, "factory"))
    return seams


def _load_inventory() -> dict[str, Any]:
    return cast(dict[str, Any], yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")))


def test_runtime_uuid4_generation_seams_are_classified() -> None:
    inventory = _load_inventory()
    entries = cast(list[dict[str, Any]], inventory["seams"])
    expected = {
        (str(entry["path"]), int(entry["line"]), str(entry["kind"]))
        for entry in entries
    }

    assert _uuid4_seams() == expected


def test_runtime_uuid4_inventory_forbids_replay_critical_random_identity() -> None:
    inventory = _load_inventory()
    entries = cast(list[dict[str, Any]], inventory["seams"])
    replay_critical = [entry for entry in entries if entry.get("replay_critical")]

    assert entries == []
    assert replay_critical == []
    for entry in entries:
        assert str(entry["owner"]).strip()
        assert str(entry["classification"]).strip()
        assert str(entry["migration_policy"]).strip()
        assert entry["layer"] in {"application", "composition", "infrastructure"}


def test_runtime_uuid4_inventory_enforces_zero_production_budget() -> None:
    inventory = _load_inventory()
    policy = cast(dict[str, Any], inventory["policy"])
    entries = cast(list[dict[str, Any]], inventory["seams"])

    assert policy["production_uuid4_budget"] == 0
    assert policy["scan_scope"] == "src/bioetl"
    assert entries == []


def test_runtime_uuid4_inventory_links_deterministic_factory_evidence() -> None:
    inventory = _load_inventory()
    history = cast(list[dict[str, Any]], inventory["review_history"])
    current_review = [entry for entry in history if entry.get("issue") == "#5044"]
    assert current_review, "Runtime UUID seam inventory must record #5044 review"
    assert current_review[0]["outcome"] == "production_random_uuid_zero_budget_enforced"

    evidence = cast(dict[str, Any], inventory["deterministic_factory_evidence"])
    guard_tests = cast(list[str], evidence["guard_tests"])
    assert evidence["issue"] == "#4968"
    assert guard_tests
    missing = [path for path in guard_tests if not (ROOT / path).exists()]
    assert not missing, (
        "Runtime UUID deterministic factory evidence points at missing tests:\n"
        + "\n".join(missing)
    )
