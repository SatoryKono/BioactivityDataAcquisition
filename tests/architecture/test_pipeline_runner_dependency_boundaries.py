"""Architecture guardrails for PipelineRunner dependency assembly."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from tests.helpers.git_index_scan import git_tracked_files

ROOT = Path(__file__).resolve().parents[2]
LEGACY_RUNNER_KWARGS = frozenset(
    {
        "executor",
        "checkpoint_manager",
        "shutdown_signal",
        "lock_runtime_service",
        "lock_manager",
        "preflight",
        "postrun",
        "lifecycle_service",
        "observer",
    }
)


def _production_python_files() -> tuple[Path, ...]:
    return git_tracked_files(root=ROOT, paths=("src/bioetl",), suffixes=(".py",))


@pytest.mark.architecture
def test_first_party_runtime_uses_typed_pipeline_runner_dependencies() -> None:
    """Production callers must not bypass typed PipelineRunnerDependencies."""
    violations: list[str] = []
    for path in _production_python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Name) or node.func.id != "PipelineRunner":
                continue
            legacy_kwargs = sorted(
                keyword.arg
                for keyword in node.keywords
                if keyword.arg in LEGACY_RUNNER_KWARGS
            )
            if legacy_kwargs:
                rel_path = path.relative_to(ROOT).as_posix()
                violations.append(
                    f"{rel_path}:{node.lineno} uses legacy kwargs {legacy_kwargs}"
                )

    assert not violations, (
        "Production PipelineRunner construction must use PipelineRunnerDependencies "
        "or a composition factory, not legacy direct kwargs:\n" + "\n".join(violations)
    )
