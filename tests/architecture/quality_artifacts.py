"""Shared loader for committed reports/quality artifacts (S6 / #9602)."""

from __future__ import annotations

import ast
import json
from pathlib import Path
import shlex
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
QUALITY_ROOT = PROJECT_ROOT / "reports" / "quality"
MANIFEST_NAME = "source-tree-manifest.json"


def quality_artifact_path(*parts: str) -> Path:
    """Return a path under ``reports/quality``."""
    return QUALITY_ROOT.joinpath(*parts)


def load_source_tree_manifest() -> dict[str, Any]:
    """Load the unified source-tree manifest."""
    payload = json.loads(
        quality_artifact_path(MANIFEST_NAME).read_text(encoding="utf-8")
    )
    if not isinstance(payload, dict):
        raise TypeError("source-tree-manifest.json must be an object")
    return payload


def assert_retained_entrypoint_src_importers(entry: dict[str, Any]) -> None:
    """Keep every retained compatibility facade at zero first-party importers."""
    assert int(entry["src_importer_count"]) == 0
    assert list(entry.get("src_importers") or []) == []


def assert_memory_test_has_required_lane(test_path: Path) -> None:
    """Require the current canonical memory owner rather than historical unit labels."""
    markers: set[str] = set()
    for statement in ast.parse(test_path.read_text(encoding="utf-8")).body:
        if isinstance(statement, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "pytestmark"
            for target in statement.targets
        ):
            value = statement.value
            values = value.elts if isinstance(value, (ast.List, ast.Tuple)) else [value]
            markers.update(ast.unparse(marker) for marker in values)
    assert "pytest.mark.memory" in markers
    relative = test_path.relative_to(PROJECT_ROOT).as_posix()
    matrix = yaml.safe_load(
        (PROJECT_ROOT / "configs/quality/test_matrix.yaml").read_text(encoding="utf-8")
    )
    lane = matrix["test_lanes"]["lanes"]["memory"]
    assert relative in lane["paths"]
    assert relative in lane["pytest_args"]
    assert lane["marker_expression"] == "memory and not benchmark"
    workflow = yaml.safe_load(
        (PROJECT_ROOT / ".github/workflows/tests.yml").read_text(encoding="utf-8")
    )
    job = workflow["jobs"]["memory-tests"]
    assert "if" not in job
    assert not job.get("continue-on-error", False)
    step = next(
        step
        for step in job["steps"]
        if step.get("name") == "Run dedicated Neo4j memory test lane"
    )
    assert "if" not in step
    assert not step.get("continue-on-error", False)
    commands: list[list[str]] = []
    for command in step["run"].replace("\\\n", " ").splitlines():
        lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|()<>")
        lexer.whitespace_split = True
        parsed = list(lexer)
        if parsed:
            commands.append(parsed)
    assert commands
    argv = commands[-1]
    assert argv[:5] == ["uv", "run", "--frozen", "--no-build", "pytest"]
    assert not any(token and set(token) <= set(";&|()<>") for token in argv)
    assert relative in argv
    assert argv[argv.index("-m") + 1] == "memory"


def load_quality_json(*parts: str) -> Any:
    """Load a committed quality JSON artifact.

    When the payload pins ``source_tree_sha256``, it must match the manifest.
    """
    path = quality_artifact_path(*parts)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and "source_tree_sha256" in payload:
        manifest = load_source_tree_manifest()
        pinned = payload.get("source_tree_sha256")
        canonical = manifest.get("source_tree_sha256")
        if pinned != canonical and path.name != MANIFEST_NAME:
            raise AssertionError(
                f"{path.as_posix()} source_tree_sha256={pinned!r} "
                f"does not match manifest {canonical!r}"
            )
    return payload
