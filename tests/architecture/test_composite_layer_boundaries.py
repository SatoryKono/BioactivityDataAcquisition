"""Tests for composite pipeline layer boundary enforcement.

These tests verify that the FSM implementation for composite pipelines
respects clean architecture layer boundaries:

- Domain layer (domain/composite): Contains FSM state enum and transition rules.
  MUST NOT import from application or infrastructure.

- Application layer (application/composite): Contains Runner, Coordinator, Merger.
  - Runner: MUST manage FSM state transitions
  - Coordinator: MUST NOT import FSM state or modify checkpoints
  - Merger: MUST NOT import FSM state or modify checkpoints

See ADR-026 §FSM Pattern for architectural decisions.
"""

from __future__ import annotations

import pytest

import ast
import re
from pathlib import Path


pytestmark = pytest.mark.architecture


def _module_import_violations(package_path: Path, import_root: str) -> list[str]:
    pattern_from = re.compile(rf"^\s*from\s+{re.escape(import_root)}\b", re.MULTILINE)
    pattern_import = re.compile(
        rf"^\s*import\s+{re.escape(import_root)}\b", re.MULTILINE
    )
    violations: list[str] = []
    for py_file in package_path.rglob("*.py"):
        content = py_file.read_text(encoding="utf-8")
        if pattern_from.search(content):
            violations.append(f"{py_file.name}: imports from {import_root}")
        if pattern_import.search(content):
            violations.append(f"{py_file.name}: imports {import_root}")
    return violations


def _type_checking_line_numbers(tree: ast.AST) -> set[int]:
    return {
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.If)
        and isinstance(node.test, ast.Name)
        and node.test.id == "TYPE_CHECKING"
    }


def _runtime_import_from_nodes(tree: ast.AST) -> list[ast.ImportFrom]:
    type_checking_lines = _type_checking_line_numbers(tree)
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.lineno not in type_checking_lines
    ]


def _module_level_checkpoint_imports(content: str) -> list[str]:
    tree = ast.parse(content)
    return [
        alias.name
        for node in _runtime_import_from_nodes(tree)
        if node.module and "checkpoint" in node.module.lower()
        for alias in node.names
    ]


def _checkpoint_module_content(src_dir: Path) -> str:
    checkpoint_pkg = src_dir / "bioetl" / "application" / "composite" / "checkpoint"
    checkpoint_file = src_dir / "bioetl" / "application" / "composite" / "checkpoint.py"
    if checkpoint_pkg.is_dir():
        return "\n".join(
            p.read_text(encoding="utf-8") for p in sorted(checkpoint_pkg.rglob("*.py"))
        )
    if checkpoint_file.exists():
        return checkpoint_file.read_text(encoding="utf-8")
    raise AssertionError("application/composite/checkpoint not found")


def _package_all_exports(content: str) -> list[str] | None:
    tree = ast.parse(content)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(target, ast.Name) and target.id == "__all__"
            for target in node.targets
        ):
            continue
        if not isinstance(node.value, ast.List):
            return []
        return [
            elt.value
            for elt in node.value.elts
            if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
        ]
    return None


def _get_composite_runner_file(src_dir: Path) -> Path:
    """Return the canonical CompositePipelineRunner module path."""
    return src_dir / "bioetl" / "application" / "composite" / "runner_pkg" / "runner.py"


def _is_allowed_fsm_import(module_name: str, *, allowed_modules: set[str]) -> bool:
    root_module = module_name.split(".")[0]
    return root_module in allowed_modules or module_name.startswith("bioetl.domain")


def _node_fsm_state_import_violations(
    node: ast.AST, *, allowed_modules: set[str]
) -> list[str]:
    if isinstance(node, ast.Import):
        return [
            f"import {alias.name}"
            for alias in node.names
            if not _is_allowed_fsm_import(alias.name, allowed_modules=allowed_modules)
        ]
    if isinstance(node, ast.ImportFrom) and node.module:
        if _is_allowed_fsm_import(node.module, allowed_modules=allowed_modules):
            return []
        return [f"from {node.module} import ..."]
    return []


def _fsm_state_import_violations(
    tree: ast.AST, *, allowed_modules: set[str]
) -> list[str]:
    return [
        violation
        for node in ast.walk(tree)
        for violation in _node_fsm_state_import_violations(
            node,
            allowed_modules=allowed_modules,
        )
    ]


class TestDomainCompositeLayerBoundaries:
    """Tests for domain/composite layer isolation."""

    def test_domain_composite_no_application_imports(self, src_dir: Path) -> None:
        """domain/composite MUST NOT import from bioetl.application.

        REQ-ARCH-FSM-001: FSM state enum and transition rules are pure domain logic.
        They must not depend on application layer orchestration.
        """
        domain_composite_path = src_dir / "bioetl" / "domain" / "composite"
        assert domain_composite_path.exists(), "domain/composite not found"

        violations = _module_import_violations(
            domain_composite_path, "bioetl.application"
        )

        assert not violations, (
            "domain/composite imports from application layer:\n"
            + "\n".join(f"  - {v}" for v in violations)
            + "\n\nFSM state must be pure domain logic."
        )

    def test_domain_composite_no_infrastructure_imports(self, src_dir: Path) -> None:
        """domain/composite MUST NOT import from bioetl.infrastructure.

        REQ-ARCH-FSM-002: FSM state enum must not depend on I/O implementations.
        """
        domain_composite_path = src_dir / "bioetl" / "domain" / "composite"
        assert domain_composite_path.exists(), "domain/composite not found"

        violations = _module_import_violations(
            domain_composite_path, "bioetl.infrastructure"
        )

        assert not violations, (
            "domain/composite imports from infrastructure layer:\n"
            + "\n".join(f"  - {v}" for v in violations)
        )

    def test_fsm_state_uses_only_standard_library(self, src_dir: Path) -> None:
        """FSM state module MUST use only standard library imports.

        REQ-ARCH-FSM-003: CompositePipelineState should be portable
        and not depend on external packages (except typing).
        """
        state_file = src_dir / "bioetl" / "domain" / "composite" / "state.py"
        assert state_file.exists(), "domain/composite/state.py not found"

        content = state_file.read_text(encoding="utf-8")
        tree = ast.parse(content)

        # Allowed standard library modules
        allowed_modules = {
            "__future__",
            "collections",
            "collections.abc",
            "enum",
            "typing",
            "dataclasses",
            "abc",
            # Allow domain exceptions import (lazy, inside method)
            "bioetl.domain.exceptions",
        }

        violations = _fsm_state_import_violations(tree, allowed_modules=allowed_modules)

        assert not violations, (
            "FSM state module has non-standard imports:\n"
            + "\n".join(f"  - {v}" for v in violations)
            + "\n\nFSM state should only use standard library and domain imports."
        )


class TestCoordinatorIsolation:
    """Tests for EnrichmentCoordinatorService FSM isolation."""

    def test_coordinator_no_fsm_state_import(self, src_dir: Path) -> None:
        """EnrichmentCoordinatorService MUST NOT import CompositePipelineState.

        REQ-ARCH-FSM-004: Coordinator is a delegated service that runs enrichers.
        It should not know about FSM states - that's Runner's responsibility.
        """
        coordinator_file = (
            src_dir / "bioetl" / "application" / "composite" / "coordinator.py"
        )
        assert coordinator_file.exists(), (
            "application/composite/coordinator.py not found"
        )

        content = coordinator_file.read_text(encoding="utf-8")

        # Check for CompositePipelineState import
        assert "CompositePipelineState" not in content, (
            "EnrichmentCoordinatorService imports CompositePipelineState.\n"
            "FSM state management is Runner's responsibility, not Coordinator's.\n"
            "See ADR-026 §FSM Pattern."
        )

    def test_coordinator_no_checkpoint_import(self, src_dir: Path) -> None:
        """EnrichmentCoordinatorService MUST NOT import checkpoint classes.

        REQ-ARCH-FSM-005: Coordinator should not directly manage checkpoints.
        Checkpoint management is Runner's responsibility.
        """
        coordinator_file = (
            src_dir / "bioetl" / "application" / "composite" / "coordinator.py"
        )
        assert coordinator_file.exists(), (
            "application/composite/coordinator.py not found"
        )

        content = coordinator_file.read_text(encoding="utf-8")
        checkpoint_imports = _module_level_checkpoint_imports(content)

        assert not checkpoint_imports, (
            f"EnrichmentCoordinatorService imports checkpoint classes at module level: "
            f"{checkpoint_imports}\n"
            "Checkpoint management is Runner's responsibility."
        )


class TestMergerIsolation:
    """Tests for MergeService FSM isolation."""

    def test_merger_no_fsm_state_import(self, src_dir: Path) -> None:
        """MergeService MUST NOT import CompositePipelineState.

        REQ-ARCH-FSM-006: Merger is a delegated service for joining data.
        It should not know about FSM states.
        """
        merger_file = src_dir / "bioetl" / "application" / "composite" / "merger.py"
        assert merger_file.exists(), "application/composite/merger.py not found"

        content = merger_file.read_text(encoding="utf-8")

        assert "CompositePipelineState" not in content, (
            "MergeService imports CompositePipelineState.\n"
            "FSM state management is Runner's responsibility."
        )

    def test_merger_no_checkpoint_import(self, src_dir: Path) -> None:
        """MergeService MUST NOT import checkpoint classes at module level.

        REQ-ARCH-FSM-007: Merger should not directly manage checkpoints.
        """
        merger_file = src_dir / "bioetl" / "application" / "composite" / "merger.py"
        assert merger_file.exists(), "application/composite/merger.py not found"

        content = merger_file.read_text(encoding="utf-8")
        checkpoint_imports = _module_level_checkpoint_imports(content)

        assert not checkpoint_imports, (
            f"MergeService imports checkpoint classes at module level: "
            f"{checkpoint_imports}"
        )


class TestKeyExtractorIsolation:
    """Tests for KeyExtractorService FSM isolation."""

    def test_key_extractor_no_fsm_state_import(self, src_dir: Path) -> None:
        """KeyExtractorService MUST NOT import CompositePipelineState.

        REQ-ARCH-FSM-008: KeyExtractor is a delegated service for extracting keys.
        It should not know about FSM states.
        """
        key_extractor_file = (
            src_dir / "bioetl" / "application" / "composite" / "key_extractor.py"
        )
        assert key_extractor_file.exists(), (
            "application/composite/key_extractor.py not found"
        )

        content = key_extractor_file.read_text(encoding="utf-8")

        assert "CompositePipelineState" not in content, (
            "KeyExtractorService imports CompositePipelineState.\n"
            "FSM state management is Runner's responsibility."
        )


class TestRunnerFSMOwnership:
    """Tests verifying Runner owns FSM state management."""

    def test_runner_imports_fsm_state(self, src_dir: Path) -> None:
        """CompositePipelineRunner MUST import CompositePipelineState.

        REQ-ARCH-FSM-009: Runner is responsible for FSM state transitions.
        It must import the state enum from domain layer.
        """
        runner_file = _get_composite_runner_file(src_dir)
        assert runner_file.exists(), (
            "application/composite/runner_pkg/runner.py not found"
        )

        content = runner_file.read_text(encoding="utf-8")

        # Must import from domain layer
        assert (
            "from bioetl.domain.composite.state import CompositePipelineState"
            in content
            or "from bioetl.domain.composite import CompositePipelineState" in content
        ), (
            "CompositePipelineRunner must import CompositePipelineState "
            "from domain layer for FSM management."
        )

    def test_runner_uses_fsm_transitions(self, src_dir: Path) -> None:
        """CompositePipelineRunner SHOULD use FSM state transitions.

        REQ-ARCH-FSM-010: Runner should have methods for state transitions.
        """
        runner_file = _get_composite_runner_file(src_dir)
        assert runner_file.exists(), (
            "application/composite/runner_pkg/runner.py not found"
        )

        content = runner_file.read_text(encoding="utf-8")

        # Check for FSM transition logging
        has_fsm_logging = "_log_fsm_transition" in content or "fsm" in content.lower()

        # Check for state changes
        has_state_changes = "with_state(" in content

        assert has_fsm_logging or has_state_changes, (
            "CompositePipelineRunner should manage FSM state transitions.\n"
            "Expected: _log_fsm_transition() calls or with_state() usage."
        )


class TestCheckpointFSMIntegration:
    """Tests for checkpoint FSM state integration."""

    def test_checkpoint_state_has_fsm_field(self, src_dir: Path) -> None:
        """CompositeCheckpointState MUST have FSM state field.

        REQ-ARCH-FSM-011: Checkpoint must persist FSM state for resume.
        """
        content = _checkpoint_module_content(src_dir)

        # Must import FSM state from domain
        has_fsm_import = (
            "CompositePipelineState" in content and "bioetl.domain.composite" in content
        )

        # Must have state field in CheckpointState
        has_state_field = (
            "state: CompositePipelineState" in content or "state:" in content
        )

        assert has_fsm_import and has_state_field, (
            "CompositeCheckpointState must have FSM state field.\n"
            "This enables resume functionality from any resumable state."
        )

    def test_checkpoint_imports_fsm_from_domain(self, src_dir: Path) -> None:
        """Checkpoint module MUST import FSM state from domain layer.

        REQ-ARCH-FSM-012: Application imports domain, not vice versa.
        """
        content = _checkpoint_module_content(src_dir)

        # Check for correct import direction
        correct_import = (
            "from bioetl.domain.composite.state import" in content
            or "from bioetl.domain.composite import" in content
        )

        assert correct_import, (
            "Checkpoint module must import CompositePipelineState from domain layer.\n"
            "Expected: from bioetl.domain.composite.state import CompositePipelineState"
        )


class TestFSMDomainExports:
    """Tests for FSM domain module exports."""

    def test_fsm_exported_from_domain_composite(self, src_dir: Path) -> None:
        """CompositePipelineState MUST be exported from domain/composite/__init__.py.

        REQ-ARCH-FSM-013: FSM state should be importable from package root.
        """
        init_file = src_dir / "bioetl" / "domain" / "composite" / "__init__.py"
        assert init_file.exists(), "domain/composite/__init__.py not found"

        content = init_file.read_text(encoding="utf-8")

        # Must export CompositePipelineState
        assert "CompositePipelineState" in content, (
            "domain/composite/__init__.py must export CompositePipelineState.\n"
            "Add to __all__ and import from state module."
        )

        # Must export transition functions
        assert "can_transition" in content, (
            "domain/composite/__init__.py must export can_transition function."
        )

        assert "validate_transition" in content, (
            "domain/composite/__init__.py must export validate_transition function."
        )

    def test_fsm_in_package_all(self, src_dir: Path) -> None:
        """FSM exports MUST be in __all__ list.

        REQ-ARCH-FSM-014: Public API should be explicit.
        """
        init_file = src_dir / "bioetl" / "domain" / "composite" / "__init__.py"
        assert init_file.exists(), "domain/composite/__init__.py not found"

        content = init_file.read_text(encoding="utf-8")
        all_list = _package_all_exports(content)

        assert all_list is not None, "__all__ not found in domain/composite/__init__.py"

        required_exports = {
            "CompositePipelineState",
            "can_transition",
            "validate_transition",
        }

        missing = required_exports - set(all_list)
        assert not missing, (
            f"FSM exports missing from __all__: {missing}\n"
            "Add these to __all__ list in domain/composite/__init__.py"
        )
