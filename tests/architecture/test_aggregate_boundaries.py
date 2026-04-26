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


FORBIDDEN_AGGREGATE_TYPES = {"Batch", "PipelineRun", "QuarantineEntry"}
ALLOWED_AGGREGATE_ID_TYPES = {"BatchID", "RunID", "EntityID", "ContentHash"}


def _read_aggregate_content(aggregates_dir: Path, filename: str) -> str:
    """Read aggregate content including sub-module facades.

    If a file is a re-export facade (e.g., batch.py), also reads the
    corresponding private sub-modules (_batch_*.py) and concatenates
    their content for architecture checks.
    """
    file_path = aggregates_dir / filename
    if not file_path.exists():
        return ""
    content = file_path.read_text(encoding="utf-8")
    # If the file is a facade (contains 'Re-export facade'), also read sub-modules
    if "Re-export facade" in content:
        stem = file_path.stem  # e.g., "batch" or "quarantine_entry"
        for sub_module in sorted(aggregates_dir.glob(f"_{stem}*.py")):
            content += "\n" + sub_module.read_text(encoding="utf-8")
        # Also check for alternate naming pattern (e.g., _quarantine_value_objects)
        alt_stem = stem.split("_")[0] if "_" in stem else stem
        if alt_stem != stem:
            for sub_module in sorted(aggregates_dir.glob(f"_{alt_stem}*.py")):
                sub_content = sub_module.read_text(encoding="utf-8")
                if sub_content not in content:
                    content += "\n" + sub_content
    return content


def _iter_aggregate_files(aggregates_dir: Path) -> list[Path]:
    return [
        py_file
        for py_file in aggregates_dir.glob("*.py")
        if py_file.name not in ("__init__.py", "events.py")
        and not py_file.name.startswith("_")
    ]


def _aggregate_tree(aggregates_dir: Path, py_file: Path) -> ast.AST | None:
    full_content = _read_aggregate_content(aggregates_dir, py_file.name)
    try:
        return ast.parse(full_content, filename=str(py_file))
    except SyntaxError:
        return None


def _current_aggregate_class(py_file: Path) -> str | None:
    if py_file.name == "batch.py":
        return "Batch"
    if py_file.name == "pipeline_run.py":
        return "PipelineRun"
    if py_file.name == "quarantine_entry.py":
        return "QuarantineEntry"
    return None


def _annotation_mentions_forbidden_type(annotation: str, forbidden: str) -> bool:
    import re

    if not re.search(rf"\b{forbidden}\b", annotation):
        return False
    for allowed in ALLOWED_AGGREGATE_ID_TYPES:
        if allowed in annotation and re.search(rf"{forbidden}ID\b", annotation):
            return False
    return True


def _aggregate_reference_violations(
    aggregates_dir: Path,
) -> list[str]:
    """Check for violations of aggregate references."""
    violations: list[str] = []
    for py_file in _iter_aggregate_files(aggregates_dir):
        tree = _aggregate_tree(aggregates_dir, py_file)
        if tree is None:
            continue
        current_file_class = _current_aggregate_class(py_file)
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            _check_class_body(node, py_file, current_file_class, violations)
    return violations


def _check_class_body(
    node: ast.ClassDef,
    py_file: Path,
    current_file_class: str | None,
    violations: list[str],
) -> None:
    """Check the body of a class for violations."""
    for item in node.body:
        if isinstance(item, ast.FunctionDef) and item.name == "__init__":
            _check_init_args(item, py_file, current_file_class, violations)
        if isinstance(item, ast.AnnAssign) and item.target:
            _check_ann_assign(item, py_file, current_file_class, violations)


def _check_init_args(
    item: ast.FunctionDef,
    py_file: Path,
    current_file_class: str | None,
    violations: list[str],
) -> None:
    """Check the arguments of __init__ for violations."""
    for arg in item.args.args:
        if not arg.annotation:
            continue
        ann_str = ast.unparse(arg.annotation)
        for forbidden in FORBIDDEN_AGGREGATE_TYPES:
            if (
                _annotation_mentions_forbidden_type(ann_str, forbidden)
                and forbidden != current_file_class
            ):
                violations.append(
                    f"{py_file.name}:{item.lineno} - "
                    f"Parameter '{arg.arg}' has type "
                    f"'{ann_str}' (should use ID type)"
                )


def _check_ann_assign(
    item: ast.AnnAssign,
    py_file: Path,
    current_file_class: str | None,
    violations: list[str],
) -> None:
    """Check annotated assignments for violations."""
    ann_str = ast.unparse(item.annotation)
    target_name = getattr(item.target, "id", "unknown")
    for forbidden in FORBIDDEN_AGGREGATE_TYPES:
        if (
            _annotation_mentions_forbidden_type(ann_str, forbidden)
            and forbidden != current_file_class
        ):
            violations.append(
                f"{py_file.name}:{item.lineno} - "
                f"Attribute '{target_name}' has type "
                f"'{ann_str}' (should use ID type)"
            )


def _immutable_property_violations(aggregates_dir: Path) -> list[str]:
    """Check for violations of immutable properties."""
    violations: list[str] = []
    for py_file in _iter_aggregate_files(aggregates_dir):
        tree = _aggregate_tree(aggregates_dir, py_file)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            _check_class_properties(node, py_file, violations)
    return violations


def _check_class_properties(
    node: ast.ClassDef,
    py_file: Path,
    violations: list[str],
) -> None:
    """Check the properties of a class for violations."""
    for item in node.body:
        if not isinstance(item, ast.FunctionDef):
            continue
        if not _is_property(item):
            continue
        if not item.returns:
            continue
        _check_property_return_type(item, py_file, violations)


def _is_property(item: ast.FunctionDef) -> bool:
    """Check if the function is a property."""
    return any(
        isinstance(decorator, ast.Name) and decorator.id == "property"
        for decorator in item.decorator_list
    )


def _check_property_return_type(
    item: ast.FunctionDef,
    py_file: Path,
    violations: list[str],
) -> None:
    """Check the return type of a property for violations."""
    ret_str = ast.unparse(item.returns)
    if "list[" in ret_str.lower() and "tuple(" not in ast.unparse(item):
        violations.append(
            f"{py_file.name}:{item.lineno} - "
            f"Property {item.name} returns "
            f"{ret_str}, should return tuple"
        )


def _other_aggregate_classes(
    *,
    aggregate_classes: dict[str, set[str]],
    current_filename: str,
) -> set[str]:
    return {
        class_name
        for other_file, classes in aggregate_classes.items()
        if other_file != current_filename
        for class_name in classes
    }


def _cross_aggregate_import_patterns(py_file: Path, class_name: str) -> tuple[str, ...]:
    return (
        f"from bioetl.domain.aggregates.{py_file.stem} import {class_name}",
        f"from bioetl.domain.aggregates import {class_name}",
        f"aggregates.{class_name}",
    )


def _cross_aggregate_import_violations(
    *,
    py_file: Path,
    content: str,
    aggregate_classes: dict[str, set[str]],
) -> list[str]:
    violations: list[str] = []
    for class_name in _other_aggregate_classes(
        aggregate_classes=aggregate_classes,
        current_filename=py_file.name,
    ):
        patterns = _cross_aggregate_import_patterns(py_file, class_name)
        if any(pattern in content for pattern in patterns):
            violations.append(f"{py_file.name} imports aggregate class {class_name}")
    return violations


def _aggregate_file_contents(aggregates_dir: Path) -> list[tuple[Path, str]]:
    return [
        (py_file, py_file.read_text(encoding="utf-8"))
        for py_file in aggregates_dir.glob("*.py")
        if py_file.name not in ("__init__.py", "events.py")
        and not py_file.name.startswith("_")
    ]


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
                "PipelineRunState",
            },
            "quarantine_entry.py": {
                "QuarantineEntry",
                "QuarantineStatus",
                "ResolutionInfo",
            },
        }

        violations = [
            violation
            for py_file, content in _aggregate_file_contents(aggregates_dir)
            for violation in _cross_aggregate_import_violations(
                py_file=py_file,
                content=content,
                aggregate_classes=aggregate_classes,
            )
        ]

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
        if not aggregates_dir.exists():
            pytest.skip("Aggregates directory not found")
        violations = _aggregate_reference_violations(aggregates_dir)

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
        for filename in expected_validators:
            content = _read_aggregate_content(aggregates_dir, filename)
            if not content:
                continue

            # Check for __post_init__ in value objects
            for class_name in expected_validators[filename]:
                if class_name in content:
                    assert "__post_init__" in content or "def _validate" in content, (
                        f"{filename}: {class_name} should validate "
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
        violations = _immutable_property_violations(aggregates_dir)

        assert not violations, (
            "Aggregate properties returning collections should return immutable types.\n"
            + "\n".join(f"  - {v}" for v in violations)
        )


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
            content = _read_aggregate_content(aggregates_dir, py_file)
            if not content:
                continue

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
            content = _read_aggregate_content(aggregates_dir, filename)
            if not content:
                continue

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
            content = _read_aggregate_content(aggregates_dir, filename)
            if not content:
                continue

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
            content = _read_aggregate_content(aggregates_dir, filename)
            if not content:
                continue

            for prop in properties:
                # Should have @property but not setter
                assert f"def {prop}(self)" in content, (
                    f"{filename}: {prop} should be a property"
                )
                assert f"@{prop}.setter" not in content, (
                    f"{filename}: {prop} should not have a setter (immutable)"
                )
