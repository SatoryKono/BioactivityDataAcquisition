# Governance checks for runtime UUID generation seams.

from __future__ import annotations

import ast
import subprocess
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "configs/quality/runtime_uuid_seams.yaml"
SCAN_ROOTS = ("src/bioetl/application", "src/bioetl/composition")

pytestmark = pytest.mark.architecture


def _tracked_python_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", *SCAN_ROOTS],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [ROOT / line for line in result.stdout.splitlines() if line.endswith(".py")]


def _uuid4_seams() -> set[tuple[str, int, str]]:
    seams: set[tuple[str, int, str]] = set()
    for path in _tracked_python_files():
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

    assert replay_critical == []
    for entry in entries:
        assert str(entry["owner"]).strip()
        assert str(entry["classification"]).strip()
        assert str(entry["migration_policy"]).strip()
        assert entry["layer"] in {"application", "composition"}
