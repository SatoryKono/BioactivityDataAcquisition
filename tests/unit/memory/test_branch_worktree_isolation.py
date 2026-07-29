"""Branch, worktree, repository, and task namespace isolation tests."""

from __future__ import annotations

from pathlib import Path

from memory.scope import RepositoryScope


def _scope(
    *,
    repo_id: str = "bioetl",
    worktree_id: str = "worktree-a",
    branch: str = "main",
    task_id: str = "task-a",
) -> RepositoryScope:
    return RepositoryScope(
        repo_id=repo_id,
        git_commit="a" * 40,
        branch=branch,
        worktree_id=worktree_id,
        task_id=task_id,
    )


def test_each_identity_dimension_produces_a_distinct_namespace(tmp_path: Path) -> None:
    baseline = _scope().namespace_path(tmp_path)
    variants = (
        _scope(repo_id="fork").namespace_path(tmp_path),
        _scope(worktree_id="worktree-b").namespace_path(tmp_path),
        _scope(branch="feature-memory").namespace_path(tmp_path),
        _scope(task_id="task-b").namespace_path(tmp_path),
    )

    assert len({baseline, *variants}) == 5
    assert all(path.is_relative_to(tmp_path) for path in (baseline, *variants))


def test_untrusted_branch_component_cannot_escape_storage_root(tmp_path: Path) -> None:
    namespace = _scope(branch="../../outside").namespace_path(tmp_path)

    assert namespace.is_relative_to(tmp_path)
    assert ".." not in namespace.parts


def test_normalization_collisions_keep_distinct_namespaces(tmp_path: Path) -> None:
    slash_branch = _scope(branch="feature/a").namespace_path(tmp_path)
    hyphen_branch = _scope(branch="feature-a").namespace_path(tmp_path)

    assert slash_branch != hyphen_branch
