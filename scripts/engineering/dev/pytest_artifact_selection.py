"""Explicit scheduling partition for tests of committed generated evidence.

The manifest owns individual test functions (all parametrizations). Temporary
fixture generators and independent source contracts remain in ordinary CI.
"""

from __future__ import annotations

import ast
import json
import os
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[3]
MANIFEST = ROOT / "configs/quality/generated_artifact_tests.json"
STATE = pytest.StashKey[dict[str, Any]]()


def load_manifest(path: Path = MANIFEST) -> dict[str, Any]:
    """Read and validate the explicit scheduling inventory."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1:
        raise ValueError("Unsupported generated artifact test manifest")
    nodes = payload["tests"]
    if not nodes or len({row["node"] for row in nodes}) != len(nodes):
        raise ValueError("Artifact manifest must contain unique nonempty test nodes")
    for row in nodes:
        node = row["node"]
        if not node.startswith("tests/") or "::test_" not in node:
            raise ValueError(f"Expected individual test function: {node}")
        if any(token in node for token in ("*", "..", "[")):
            raise ValueError(f"Unsupported artifact node selector: {node}")
        if not row["artifacts"] or not row["reason"]:
            raise ValueError(f"Missing dependency evidence: {node}")
    return payload


def validate_selectors(payload: dict[str, Any], root: Path = ROOT) -> None:
    """Reject stale manifest functions before an ordinary CI subset can hide them."""
    trees: dict[str, ast.Module] = {}
    for row in payload["tests"]:
        path, *names = row["node"].split("::")
        if path not in trees:
            trees[path] = ast.parse((root / path).read_text(encoding="utf-8"))
        scope: ast.AST = trees[path]
        for name in names:
            matches = [
                node
                for node in getattr(scope, "body", [])
                if getattr(node, "name", None) == name
            ]
            if len(matches) != 1:
                raise ValueError(f"Stale artifact manifest selector: {row['node']}")
            scope = matches[0]
        if not isinstance(scope, (ast.FunctionDef, ast.AsyncFunctionDef)):
            raise ValueError(f"Artifact selector is not a function: {row['node']}")


def base_node(nodeid: str) -> str:
    """Return the function selector shared by its parametrizations."""
    return nodeid.split("[", 1)[0]


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("generated artifact scheduling")
    group.addoption(
        "--artifact-selection",
        choices=("all", "ci", "daily"),
        default=os.environ.get(
            "BIOETL_ARTIFACT_TEST_SELECTION",
            "ci"
            if os.environ.get("GITHUB_EVENT_NAME")
            in {"pull_request", "pull_request_target", "push"}
            else "all",
        ),
        help="ci defers committed generated evidence; daily selects all manifest nodes",
    )
    group.addoption("--artifact-selection-report", default=None)


@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]):
    """Mark before pytest -m, partition afterwards, and retain collection proof."""
    try:
        manifest = load_manifest()
        validate_selectors(manifest)
    except (OSError, ValueError, KeyError, TypeError, SyntaxError) as error:
        raise pytest.UsageError(
            f"Invalid generated-artifact selection manifest {MANIFEST}: {error}"
        ) from error
    selectors = {row["node"] for row in manifest["tests"]}
    original = [item.nodeid for item in items]
    for item in items:
        owned = base_node(item.nodeid) in selectors
        if item.get_closest_marker("generated_artifact") is not None and not owned:
            raise pytest.UsageError(
                f"Unmanifested generated_artifact test: {item.nodeid}"
            )
        if owned and item.get_closest_marker("generated_artifact") is None:
            raise pytest.UsageError(
                f"Manifest node lacks generated_artifact marker: {item.nodeid}"
            )
    yield
    mode = config.getoption("artifact_selection")
    before_partition = [item.nodeid for item in items]
    deferred = []
    selected = []
    for item in items:
        artifact = base_node(item.nodeid) in selectors
        if (mode == "ci" and artifact) or (mode == "daily" and not artifact):
            deferred.append(item)
        else:
            selected.append(item)
    if mode == "daily":
        missing = selectors - {base_node(item.nodeid) for item in selected}
        if missing:
            raise pytest.UsageError(
                "Daily artifact coverage is incomplete: " + ", ".join(sorted(missing))
            )
    items[:] = selected
    if deferred:
        config.hook.pytest_deselected(items=deferred)
    config.stash[STATE] = {
        "schema_version": 1,
        "selection": mode,
        "collected": original,
        "selected": [item.nodeid for item in selected],
        "deferred": [item.nodeid for item in deferred] if mode == "ci" else [],
        "other_deselected": sorted(set(original) - set(before_partition)),
        "daily_entrypoint": ".github/workflows/nightly.yml",
    }


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Record actual exit status; never turn pytest exit 5 into success."""
    destination = session.config.getoption("artifact_selection_report")
    if not destination:
        return
    payload = dict(session.config.stash.get(STATE, {}))
    payload["pytest_exit_code"] = int(exitstatus)
    payload["collection_errors"] = session.testsfailed
    payload["status"] = "executed" if exitstatus == 0 else "failed"
    if (
        exitstatus == pytest.ExitCode.NO_TESTS_COLLECTED
        and payload.get("selection") == "ci"
        and payload.get("collected")
        and not payload.get("selected")
        and not payload.get("other_deselected")
        and payload.get("collected") == payload.get("deferred")
        and session.testsfailed == 0
    ):
        payload["status"] = "deferred-to-daily"
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
