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
UUID4_SCAN_TIMEOUT_SECONDS = 10

pytestmark = pytest.mark.architecture


def _uuid4_candidate_files() -> tuple[Path, ...]:
    """Prefilter candidate files so Windows/WSL runs do not parse every module."""
    try:
        result = subprocess.run(
            [
                "rg",
                "--files-with-matches",
                "-F",
                "uuid4",
                *SCAN_ROOTS,
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=UUID4_SCAN_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        pass
    else:
        if result.returncode == 0:
            return tuple(
                ROOT / line
                for line in result.stdout.splitlines()
                if line.endswith(".py")
            )
        if result.returncode == 1:
            return ()

    try:
        import shutil

        git_cmd = shutil.which("git") or "git"
        result = subprocess.run(
            [git_cmd, "grep", "-l", "uuid4", "--", *SCAN_ROOTS],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=UUID4_SCAN_TIMEOUT_SECONDS,
        )
        if result.returncode == 0:
            return tuple(
                ROOT / line
                for line in result.stdout.splitlines()
                if line.endswith(".py")
            )
        if result.returncode == 1:
            return ()
    except (OSError, subprocess.TimeoutExpired):
        pass

    files: list[Path] = []
    for scan_root in SCAN_ROOTS:
        files.extend((ROOT / scan_root).rglob("*.py"))
    return tuple(sorted(path for path in files if path.is_file()))


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

    assert replay_critical == []
    for entry in entries:
        assert str(entry["owner"]).strip()
        assert str(entry["classification"]).strip()
        assert str(entry["migration_policy"]).strip()
        assert entry["layer"] in {"application", "composition"}


def test_runtime_uuid4_inventory_documents_exact_replay_injection_seams() -> None:
    inventory = _load_inventory()
    entries = cast(list[dict[str, Any]], inventory["seams"])
    by_path = {
        str(entry["path"]): str(entry["migration_policy"])
        for entry in entries
        if isinstance(entry, dict)
    }
    expected_requirements = {
        "src/bioetl/application/services/execution/pipeline_runner_service.py": (
            "exact replay requires explicit run_id"
        ),
        "src/bioetl/application/services/control_plane/manifest/service_scaffold.py": (
            "manifest_id_factory"
        ),
        "src/bioetl/application/services/control_plane/ledger/service.py": (
            "event_id_factory"
        ),
        "src/bioetl/application/services/control_plane/workflow/execution_service.py": (
            "run_id_factory"
        ),
        "src/bioetl/composition/bootstrap/runtime/_runner_assembly_support.py": (
            "control-plane-attached"
        ),
        "src/bioetl/composition/bootstrap/runtime/pipeline_context_builder.py": (
            "run_id_factory"
        ),
    }

    missing: list[str] = []
    for path, required_token in expected_requirements.items():
        policy = by_path.get(path, "")
        if required_token not in policy:
            missing.append(f"{path} -> {required_token}")

    assert not missing, (
        "Exact replay/runtime UUID seams must document their explicit injection "
        "migration path:\n" + "\n".join(missing)
    )


def test_runtime_uuid4_inventory_links_deterministic_factory_evidence() -> None:
    inventory = _load_inventory()
    history = cast(list[dict[str, Any]], inventory["review_history"])
    current_review = [entry for entry in history if entry.get("issue") == "#4968"]
    assert current_review, "Runtime UUID seam inventory must record #4968 review"
    assert current_review[0]["outcome"] == "deterministic_factory_evidence_confirmed"

    evidence = cast(dict[str, Any], inventory["deterministic_factory_evidence"])
    guard_tests = cast(list[str], evidence["guard_tests"])
    assert evidence["issue"] == "#4968"
    assert guard_tests
    missing = [path for path in guard_tests if not (ROOT / path).exists()]
    assert not missing, (
        "Runtime UUID deterministic factory evidence points at missing tests:\n"
        + "\n".join(missing)
    )
