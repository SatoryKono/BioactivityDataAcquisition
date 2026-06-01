"""Tests for BasePipeline purity and contract adherence.

Ensures that BasePipeline remains a thin container and does not re-implement
logic that belongs in Transformers or Ports.
"""

from __future__ import annotations

import pytest

import ast
from pathlib import Path


pytestmark = pytest.mark.architecture

def test_base_pipeline_does_not_have_gold_methods(src_dir: Path) -> None:
    """BasePipeline MUST NOT implement Gold transformation logic.

    REQ-ARCH-REF-001: should_write_gold and transform_for_gold have been moved
    to BaseTransformer. BasePipeline should not re-implement them.
    """
    base_pipeline_file = src_dir / "bioetl/application/core/base.py"

    with open(base_pipeline_file, encoding="utf-8") as f:
        tree = ast.parse(f.read())

    methods = {
        node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
    }

    forbidden = {"should_write_gold", "transform_for_gold"}
    found = methods.intersection(forbidden)

    assert not found, (
        f"BasePipeline contains forbidden methods: {found}. Logic belongs in BaseTransformer."
    )


def test_base_pipeline_does_not_have_gold_constants(src_dir: Path) -> None:
    """BasePipeline MUST NOT have GOLD_EXCLUDE_FIELDS constant."""
    base_pipeline_file = src_dir / "bioetl/application/core/base.py"

    with open(base_pipeline_file, encoding="utf-8") as f:
        tree = ast.parse(f.read())

    assigns = {
        target.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name)
    }

    # Check for Annotated assignment (class vars)
    ann_assigns = {
        node.target.id
        for node in ast.walk(tree)
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
    }

    all_vars = assigns.union(ann_assigns)

    assert "GOLD_EXCLUDE_FIELDS" not in all_vars, (
        "BasePipeline must not define GOLD_EXCLUDE_FIELDS"
    )
