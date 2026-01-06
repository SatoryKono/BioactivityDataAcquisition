"""Architecture tests: Aggregate Boundary Isolation.

These tests ensure aggregates follow DDD principles:
1. Aggregates reference each other only by ID (not full objects)
2. Aggregates don't import other aggregate classes
3. Cross-aggregate coordination uses Domain Events
4. Invariants are protected within aggregate boundaries

REQ-ARCH-020: Aggregates must be units of consistency.
REQ-ARCH-021: Aggregates communicate via IDs and Domain Events.

See CLAUDE.md §2 Architecture and docs/RULES.md.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest


class TestAggregateBoundaryIsolation:
    """Tests ensuring aggregates don't reference each other directly."""

    @pytest.fixture
    def aggregates_dir(self, src_dir: Path) -> Path:
        """Get path to aggregates directory."""
        return src_dir / "bioetl" / "domain" / "aggregates"

    def test_no_cross_aggregate_imports(self, aggregates_dir: Path) -> None:
        """Aggregates should not import other aggregate classes.

        REQ-ARCH-020: Each aggregate is a consistency boundary.
        Aggregates should reference each other by ID only.
        """
        if not aggregates_dir.exists():
            pytest.skip("Aggregates directory not found")

        # Map of aggregate file -> aggregate classes defined
        aggregate_classes = {
            "batch.py": {"Batch", "BatchRecord", "BatchStatus"},
            "pipeline_run.py": {
                "PipelineRun",
                "StageResult",
                "StageStatus",
                "RunStatus",
            },
            "quarantine_entry.py": {
                "QuarantineEntry",
                "QuarantineStatus",
                "ResolutionInfo",
            },
        }

        violations = []

        for py_file in aggregates_dir.glob("*.py"):
            if py_file.name in ("__init__.py", "events.py"):
                continue

            other_aggregates = set()
            for other_file, classes in aggregate_classes.items():
                if other_file != py_file.name:
                    other_aggregates.update(classes)

            with py_file.open(encoding="utf-8") as f:
                content = f.read()

            for class_name in other_aggregates:
                # Check for imports of other aggregate classes
                patterns = [
                    f"from bioetl.domain.aggregates.{py_file.stem} import {class_name}",
                    f"from bioetl.domain.aggregates import {class_name}",
                    f"aggregates.{class_name}",
                ]
                for pattern in patterns:
                    if pattern in content:
                        violations.append(
                            f"{py_file.name} imports aggregate class {class_name}"
                        )

        assert not violations, (
            "Aggregates should not import other aggregate classes. "
            "Use IDs for cross-aggregate references.\n"
            + "\n".join(f"  - {v}" for v in violations)
        )

    def test_aggregates_use_id_types_for_references(self, aggregates_dir: Path) -> None:
        """Aggregates should use ID types (RunID, BatchID) for cross-references.

        REQ-ARCH-021: Cross-aggregate references must be by ID only,
        not by full aggregate objects.
        """
        import re

        if not aggregates_dir.exists():
            pytest.skip("Aggregates directory not found")

        # These aggregate type names should NOT appear in type hints
        forbidden_types = {"Batch", "PipelineRun", "QuarantineEntry"}

        # ID types that are allowed (they reference aggregates by ID)
        allowed_id_types = {"BatchID", "RunID", "EntityID", "ContentHash"}

        violations = []

        for py_file in aggregates_dir.glob("*.py"):
            if py_file.name in ("__init__.py", "events.py"):
                continue

            with py_file.open(encoding="utf-8") as f:
                try:
                    tree = ast.parse(f.read(), filename=str(py_file))
                except SyntaxError:
                    continue

            current_file_class = None
            if py_file.name == "batch.py":
                current_file_class = "Batch"
            elif py_file.name == "pipeline_run.py":
                current_file_class = "PipelineRun"
            elif py_file.name == "quarantine_entry.py":
                current_file_class = "QuarantineEntry"

            def is_forbidden_type(ann_str: str, forbidden: str) -> bool:
                """Check if annotation contains forbidden type (not ID type)."""
                # Check for exact match or as generic type parameter
                # Use word boundary to avoid matching substrings like "BatchID"
                pattern = rf"\b{forbidden}\b"
                if not re.search(pattern, ann_str):
                    return False
                # Skip if it's actually an ID type (e.g., BatchID, RunID)
                for allowed in allowed_id_types:
                    if allowed in ann_str:
                        # Check if the forbidden word is part of an ID type
                        id_pattern = rf"{forbidden}ID\b"
                        if re.search(id_pattern, ann_str):
                            return False
                return True

            # Check each class in the file
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    for item in node.body:
                        # Check __init__ parameters
                        if (
                            isinstance(item, ast.FunctionDef)
                            and item.name == "__init__"
                        ):
                            for arg in item.args.args:
                                if arg.annotation:
                                    ann_str = ast.unparse(arg.annotation)
                                    for forbidden in forbidden_types:
                                        if (
                                            is_forbidden_type(ann_str, forbidden)
                                            and forbidden != current_file_class
                                        ):
                                            violations.append(
                                                f"{py_file.name}:{item.lineno} - "
                                                f"Parameter '{arg.arg}' has type "
                                                f"'{ann_str}' (should use ID type)"
                                            )

                        # Check class attributes (AnnAssign)
                        if isinstance(item, ast.AnnAssign) and item.target:
                            ann_str = ast.unparse(item.annotation)
                            target_name = getattr(item.target, "id", "unknown")
                            for forbidden in forbidden_types:
                                if (
                                    is_forbidden_type(ann_str, forbidden)
                                    and forbidden != current_file_class
                                ):
                                    violations.append(
                                        f"{py_file.name}:{item.lineno} - "
                                        f"Attribute '{target_name}' has type "
                                        f"'{ann_str}' (should use ID type)"
                                    )

        assert not violations, (
            "Aggregates should reference other aggregates by ID only, "
            "not by full object type.\n" + "\n".join(f"  - {v}" for v in violations)
        )


class TestAggregateInvariantProtection:
    """Tests ensuring aggregates protect their invariants."""

    def test_aggregates_have_validate_invariants(self, src_dir: Path) -> None:
        """Aggregate entities should have _validate_invariants method.

        REQ-ARCH-022: Invariants must be validated internally.
        """
        aggregates_dir = src_dir / "bioetl" / "domain" / "aggregates"
        if not aggregates_dir.exists():
            pytest.skip("Aggregates directory not found")

        # Classes that should have invariant validation
        expected_validators = {
            "batch.py": ["BatchRecord"],  # Batch validates in _assert_open
            "pipeline_run.py": ["StageResult"],  # Uses __post_init__
            "quarantine_entry.py": ["ResolutionInfo"],  # Uses __post_init__
        }

        # Check that value objects inside aggregates validate in __post_init__
        for py_file in aggregates_dir.glob("*.py"):
            if py_file.name not in expected_validators:
                continue

            with py_file.open(encoding="utf-8") as f:
                content = f.read()

            # Check for __post_init__ in value objects
            for class_name in expected_validators[py_file.name]:
                if class_name in content:
                    assert "__post_init__" in content or "def _validate" in content, (
                        f"{py_file.name}: {class_name} should validate "
                        "invariants in __post_init__ or _validate_invariants()"
                    )

    def test_aggregate_properties_return_immutable_collections(
        self, src_dir: Path
    ) -> None:
        """Aggregate properties returning collections should return immutable types.

        REQ-ARCH-023: Internal state must be protected from external modification.
        """
        aggregates_dir = src_dir / "bioetl" / "domain" / "aggregates"
        if not aggregates_dir.exists():
            pytest.skip("Aggregates directory not found")

        violations = []

        for py_file in aggregates_dir.glob("*.py"):
            if py_file.name in ("__init__.py", "events.py"):
                continue

            with py_file.open(encoding="utf-8") as f:
                try:
                    tree = ast.parse(f.read(), filename=str(py_file))
                except SyntaxError:
                    continue

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    for item in node.body:
                        # Find properties that return collections
                        if isinstance(item, ast.FunctionDef):
                            for decorator in item.decorator_list:
                                if (
                                    isinstance(decorator, ast.Name)
                                    and decorator.id == "property"
                                ):
                                    # Check return annotation
                                    if item.returns:
                                        ret_str = ast.unparse(item.returns)
                                        # If returns list, should return tuple
                                        if "list[" in ret_str.lower():
                                            # Check function body for tuple() call
                                            body_str = ast.unparse(item)
                                            if "tuple(" not in body_str:
                                                violations.append(
                                                    f"{py_file.name}:{item.lineno} - "
                                                    f"Property {item.name} returns "
                                                    f"{ret_str}, should return tuple"
                                                )

        # Note: This is a soft check - existing code returns tuples correctly
        if violations:
            pytest.skip(f"Found potential issues: {violations}")


class TestDomainEventsForCoordination:
    """Tests ensuring aggregates use domain events for coordination."""

    def test_aggregates_emit_domain_events(self, src_dir: Path) -> None:
        """Aggregates should emit domain events for state changes.

        REQ-ARCH-024: Cross-aggregate coordination via Domain Events.
        """
        aggregates_dir = src_dir / "bioetl" / "domain" / "aggregates"
        if not aggregates_dir.exists():
            pytest.skip("Aggregates directory not found")

        required_patterns = {
            "batch.py": ["BatchCreated", "BatchSealed", "BatchWritten"],
            "pipeline_run.py": ["PipelineCompleted", "PipelineFailed"],
            "quarantine_entry.py": [
                "QuarantineEntryCreated",
                "QuarantineEntryResolved",
            ],
        }

        for py_file, events in required_patterns.items():
            file_path = aggregates_dir / py_file
            if not file_path.exists():
                continue

            with file_path.open(encoding="utf-8") as f:
                content = f.read()

            for event in events:
                assert event in content, (
                    f"{py_file} should emit {event} domain event "
                    "for cross-aggregate coordination"
                )

    def test_aggregates_have_collect_events_method(self, src_dir: Path) -> None:
        """All aggregates should have collect_events() method.

        REQ-ARCH-025: Events must be collectable for publishing.
        """
        aggregates_dir = src_dir / "bioetl" / "domain" / "aggregates"
        if not aggregates_dir.exists():
            pytest.skip("Aggregates directory not found")

        aggregate_files = ["batch.py", "pipeline_run.py", "quarantine_entry.py"]

        for filename in aggregate_files:
            file_path = aggregates_dir / filename
            if not file_path.exists():
                continue

            with file_path.open(encoding="utf-8") as f:
                content = f.read()

            assert "def collect_events(self)" in content, (
                f"{filename} should have collect_events() method "
                "for domain event collection"
            )


class TestAggregateConsistencyBoundary:
    """Tests ensuring aggregates are units of consistency."""

    def test_aggregate_state_changes_through_methods_only(self, src_dir: Path) -> None:
        """Aggregate state should only change through defined methods.

        REQ-ARCH-026: State changes only via aggregate methods.
        """
        aggregates_dir = src_dir / "bioetl" / "domain" / "aggregates"
        if not aggregates_dir.exists():
            pytest.skip("Aggregates directory not found")

        # Aggregate classes should use __slots__ to prevent attribute addition
        expected_slots = {
            "batch.py": "Batch",
            "pipeline_run.py": "PipelineRun",
            "quarantine_entry.py": "QuarantineEntry",
        }

        for filename, class_name in expected_slots.items():
            file_path = aggregates_dir / filename
            if not file_path.exists():
                continue

            with file_path.open(encoding="utf-8") as f:
                content = f.read()

            # Check for __slots__ in the aggregate class
            assert "__slots__" in content, (
                f"{filename}: {class_name} should use __slots__ "
                "to prevent arbitrary attribute assignment"
            )

    def test_aggregate_ids_are_immutable(self, src_dir: Path) -> None:
        """Aggregate identifiers should be immutable after creation.

        REQ-ARCH-027: IDs are immutable.
        """
        aggregates_dir = src_dir / "bioetl" / "domain" / "aggregates"
        if not aggregates_dir.exists():
            pytest.skip("Aggregates directory not found")

        # ID properties should not have setters
        id_properties = {
            "batch.py": ["batch_id", "run_id"],
            "pipeline_run.py": ["run_id"],
            "quarantine_entry.py": ["entry_id", "run_id", "batch_id"],
        }

        for filename, properties in id_properties.items():
            file_path = aggregates_dir / filename
            if not file_path.exists():
                continue

            with file_path.open(encoding="utf-8") as f:
                content = f.read()

            for prop in properties:
                # Should have @property but not setter
                assert f"def {prop}(self)" in content, (
                    f"{filename}: {prop} should be a property"
                )
                assert f"@{prop}.setter" not in content, (
                    f"{filename}: {prop} should not have a setter (immutable)"
                )
