# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Architecture tests: No transformer fallback in BasePipeline.

REQ-ARCH-001: BasePipeline MUST NOT create transformers internally.
Transformers MUST be injected via DI from GenericPipelineFactory.

This ensures all dependency creation is centralized in the composition root.

See CLAUDE.md §2.2 Dependency Injection.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

# Paths relative to project root
APPLICATION_DIR = Path("src/bioetl/application")
PIPELINES_DIR = Path("src/bioetl/application/pipelines")


def _get_base_path(relative_path: Path) -> Path:
    """Resolve path - works from project root or tests directory."""
    if relative_path.exists():
        return relative_path
    # Try from tests directory context
    return Path(__file__).parent.parent.parent / relative_path


class TestNoTransformerFallback:
    """Tests ensuring transformer fallback is not used in pipelines."""

    def test_no_default_transformer_class_in_basepipeline(self) -> None:
        """BasePipeline must not have default_transformer_class attribute.

        REQ-ARCH-001: Transformers must be injected via DI.
        BasePipeline should not have fallback transformer creation.
        """
        base_file = _get_base_path(APPLICATION_DIR) / "core" / "base.py"
        if not base_file.exists():
            pytest.skip("BasePipeline file not found")

        content = base_file.read_text(encoding="utf-8")

        # Check for class variable definition
        pattern = r"default_transformer_class\s*[=:]"
        matches = list(re.finditer(pattern, content))

        assert not matches, (
            "BasePipeline must not define default_transformer_class.\n"
            "Transformers must be injected via DI from GenericPipelineFactory.\n"
            f"Found: {len(matches)} occurrences in base.py\n"
            "See REQ-ARCH-001 and CLAUDE.md §2.2"
        )

    def test_basepipeline_init_does_not_create_transformer(self) -> None:
        """BasePipeline.__init__ must not create transformers internally.

        REQ-ARCH-001: All transformers must be injected via constructor,
        not created inside __init__.
        """
        base_file = _get_base_path(APPLICATION_DIR) / "core" / "base.py"
        if not base_file.exists():
            pytest.skip("BasePipeline file not found")

        content = base_file.read_text(encoding="utf-8")

        try:
            tree = ast.parse(content)
        except SyntaxError:
            pytest.fail("Failed to parse base.py")

        init_method = _find_basepipeline_init(tree)
        if init_method is None:
            pytest.fail("Could not find BasePipeline.__init__ method")

        forbidden_pattern = _find_forbidden_transformer_pattern(content, init_method)
        if forbidden_pattern is not None:
            pytest.fail(
                f"BasePipeline.__init__ contains forbidden pattern: {forbidden_pattern}\n"
                "Transformers must be injected via DI, not created internally.\n"
                "See REQ-ARCH-001"
            )

    def test_no_default_transformer_class_in_pipeline_subclasses(self) -> None:
        """Pipeline subclasses must not define default_transformer_class.

        REQ-ARCH-001: All transformers are provided via GenericPipelineFactory.
        Pipeline classes should be simple containers without transformer fallbacks.
        """
        pipelines_path = _get_base_path(PIPELINES_DIR)
        if not pipelines_path.exists():
            pytest.skip("Pipelines directory not found")

        violations = _find_pipeline_subclass_default_transformer_violations(
            pipelines_path
        )

        assert not violations, (
            "Pipeline subclasses must not define default_transformer_class.\n"
            "Transformers are injected via GenericPipelineFactory.\n\n"
            "Violations found:\n"
            + "\n".join(f"  - {v}" for v in violations)
            + "\n\nSee REQ-ARCH-001 and CLAUDE.md §2.2"
        )

    def test_all_factories_have_transformer_class(self) -> None:
        """All pipeline factories must have transformer_class configured.

        REQ-ARCH-001: Since BasePipeline has no fallback, factories
        must provide transformer_class for proper DI.
        """
        factories_file = (
            _get_base_path(Path("src/bioetl/composition/factories"))
            / "pipeline"
            / "registry.py"
        )
        if not factories_file.exists():
            pytest.skip("pipeline/registry.py not found")

        content = factories_file.read_text(encoding="utf-8")
        factory_without_transformer = _find_factory_missing_transformer_class(content)
        if factory_without_transformer is not None:
            pytest.fail(
                f"Factory missing transformer_class:\n{factory_without_transformer[:200]}...\n"
                "All factories must specify transformer_class for DI.\n"
                "See REQ-ARCH-001"
            )


class TestTransformerInjectionPath:
    """Tests verifying the transformer injection path through factories."""

    def test_generic_factory_creates_transformer(self) -> None:
        """GenericPipelineFactory must delegate transformer creation properly.

        Verify that:
        1. Factory has create_transformer() method (public API)
        2. create_with_services() passes transformer_class to pipeline creation
        3. construction helpers build transformer and injection reaches pipeline
        """
        assembler_file = (
            _get_base_path(Path("src/bioetl/composition/factories"))
            / "pipeline"
            / "assembler.py"
        )
        service_bundle_file = (
            _get_base_path(Path("src/bioetl/composition/factories"))
            / "services"
            / "bundle.py"
        )
        construction_file = (
            _get_base_path(Path("src/bioetl/composition/factories"))
            / "pipeline"
            / "construction.py"
        )
        if not construction_file.exists():
            pytest.skip("pipeline/construction.py not found")
        if not assembler_file.exists():
            pytest.skip("pipeline/assembler.py not found")
        if not service_bundle_file.exists():
            pytest.skip("services/bundle.py not found")

        assembler_content = assembler_file.read_text(encoding="utf-8")
        service_bundle_content = service_bundle_file.read_text(encoding="utf-8")
        construction_content = construction_file.read_text(encoding="utf-8")
        combined_content = (
            f"{assembler_content}\n{service_bundle_content}\n{construction_content}"
        )

        # Check for create_transformer method (public API for direct usage)
        assert "def create_transformer" in combined_content, (
            "GenericPipelineFactory must have create_transformer() method"
        )

        # Check that create_with_services passes transformer_class
        assert "transformer_class=self.transformer_class" in combined_content, (
            "GenericPipelineFactory.create_with_services must pass "
            "transformer_class to create_pipeline_with_services()"
        )

        # Verify builder path creates transformer and pipeline receives it.
        assert "transformer_class(" in combined_content, (
            "pipeline factory construction path must create transformer "
            "from transformer_class"
        )
        assert "transformer=transformer" in combined_content, (
            "pipeline_factory must pass transformer to pipeline constructor"
        )


def _find_basepipeline_init(tree: ast.AST) -> ast.FunctionDef | None:
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef) or node.name != "BasePipeline":
            continue
        for item in node.body:
            if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                return item
    return None


def _find_forbidden_transformer_pattern(
    content: str,
    init_method: ast.FunctionDef,
) -> str | None:
    init_source = ast.get_source_segment(content, init_method)
    if not init_source:
        return None
    forbidden_patterns = [
        r"self\.default_transformer_class\(",
        r"Transformer\(\)",
        r"transformer_class\(",
    ]
    for pattern in forbidden_patterns:
        if re.search(pattern, init_source):
            return pattern
    return None


def _find_pipeline_subclass_default_transformer_violations(
    pipelines_path: Path,
) -> list[str]:
    pattern = r"default_transformer_class\s*="
    base_path = _get_base_path(PIPELINES_DIR)
    violations: list[str] = []
    for py_file in pipelines_path.rglob("*.py"):
        if _is_skipped_pipeline_file(py_file):
            continue
        content = py_file.read_text(encoding="utf-8")
        if re.search(pattern, content):
            violations.append(str(py_file.relative_to(base_path)))
    return violations


def _is_skipped_pipeline_file(py_file: Path) -> bool:
    return "transformer" in py_file.name.lower() or py_file.name.startswith("_")


def _find_factory_missing_transformer_class(content: str) -> str | None:
    factory_pattern = r"GenericPipelineFactory\([^)]+\)"
    for match in re.finditer(factory_pattern, content, re.DOTALL):
        factory_def = match.group(0)
        if "transformer_class=" not in factory_def:
            return factory_def
    return None
