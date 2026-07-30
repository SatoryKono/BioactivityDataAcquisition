"""Tests for repository-scoped memory namespaces."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from memory.scope import RepositoryScope, safe_component

pytestmark = pytest.mark.unit


def test_namespace_path_isolated_by_worktree_and_task(tmp_path: Path) -> None:
    first = RepositoryScope("repo", "a" * 40, "main", "tree-a", "task")
    second = RepositoryScope("repo", "a" * 40, "main", "tree-b", "task")
    third = RepositoryScope("repo", "a" * 40, "main", "tree-a", "other")
    fourth = RepositoryScope("repo", "a" * 40, "feature", "tree-a", "task")

    assert first.namespace_path(tmp_path) != second.namespace_path(tmp_path)
    assert first.namespace_path(tmp_path) != third.namespace_path(tmp_path)
    assert first.namespace_path(tmp_path) != fourth.namespace_path(tmp_path)
    assert first.namespace_path(tmp_path).is_relative_to(tmp_path)


@pytest.mark.parametrize("value", ["", "  ", ".", "..", "///"])
def test_safe_component_rejects_empty_or_relative_values(value: str) -> None:
    with pytest.raises(ValueError):
        safe_component(value)


def test_safe_component_removes_path_traversal() -> None:
    assert safe_component("../../Task Name") == "task-name"


def test_repository_scope_discovers_local_git_identity(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.email", "test@example.invalid"],
        check=True,
    )
    (repo / "README.md").write_text("test\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "README.md"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "initial"], check=True)

    scope = RepositoryScope.discover(repo, task_id="Task 123")

    assert scope.repo_id == "repo"
    assert len(scope.git_commit) == 40
    assert scope.task_id == "Task 123"
    assert scope.namespace_path(tmp_path / "state").name == "task-123"
