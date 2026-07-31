"""Isolation and concurrency contracts for file-backed MCP memory."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from memory.mcp_scope import initialize_memory_file, memory_scope_path

pytestmark = pytest.mark.unit


def test_scope_is_bound_to_worktree_branch_and_commit(tmp_path: Path) -> None:
    first = memory_scope_path(tmp_path / "a", branch="main", commit="a" * 40)
    same_scope = memory_scope_path(tmp_path / "a", branch="main", commit="a" * 40)
    other_worktree = memory_scope_path(
        tmp_path / "b", branch="main", commit="a" * 40
    )
    other_branch = memory_scope_path(
        tmp_path / "a", branch="feature/x", commit="a" * 40
    )
    other_commit = memory_scope_path(tmp_path / "a", branch="main", commit="b" * 40)

    assert same_scope == first
    assert len({first, other_worktree, other_branch, other_commit}) == 4
    assert "feature-x" in str(other_branch)


def test_concurrent_seed_is_atomic_and_shared_within_scope(tmp_path: Path) -> None:
    seed = tmp_path / "seed.json"
    seed.write_text('{"entities":[],"relations":[]}\n', encoding="utf-8")
    target = tmp_path / "scope" / "memory.json"

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda _: initialize_memory_file(target, seed), range(32)))

    assert json.loads(target.read_text(encoding="utf-8")) == {
        "entities": [],
        "relations": [],
    }
    assert not list(target.parent.glob("*.tmp"))
    assert not list(target.parent.glob("*.lock"))


def test_existing_same_scope_memory_is_shared_not_reseeded(tmp_path: Path) -> None:
    seed = tmp_path / "seed.json"
    seed.write_text('{"entities":[],"relations":[]}\n', encoding="utf-8")
    target = tmp_path / "scope" / "memory.json"
    initialize_memory_file(target, seed)
    target.write_text(
        '{"entities":[{"name":"shared"}],"relations":[]}\n',
        encoding="utf-8",
    )

    initialize_memory_file(target, seed)

    assert json.loads(target.read_text(encoding="utf-8"))["entities"] == [
        {"name": "shared"}
    ]
