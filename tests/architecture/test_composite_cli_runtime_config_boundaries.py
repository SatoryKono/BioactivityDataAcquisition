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
"""Architecture checks for composite runtime-config import boundaries."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest


@pytest.mark.architecture
@pytest.mark.parametrize(
    "relative_path",
    [
        Path("bioetl/interfaces/cli/commands/run_composite.py"),
        Path("bioetl/interfaces/cli/commands/domains/composite/execution.py"),
        Path("bioetl/interfaces/cli/commands/domains/composite/runtime.py"),
        Path("bioetl/interfaces/cli/commands/domains/composite/support.py"),
        Path("bioetl/composition/bootstrap/runtime/composite.py"),
        Path("bioetl/composition/bootstrap/runtime/runtime_basics.py"),
        Path("bioetl/composition/bootstrap/runtime/runner_factory_builder_service.py"),
        Path(
            "bioetl/composition/bootstrap/runtime/composite_support_service_builders.py"
        ),
        Path(
            "bioetl/composition/bootstrap/runtime/composite_support_services_factory.py"
        ),
        Path("bioetl/composition/bootstrap/runtime/composite_bootstrap_builders.py"),
        Path("bioetl/composition/bootstrap/runtime/runner_assembly.py"),
    ],
)
def test_composite_runtime_modules_import_runtime_config_from_stable_facade(
    src_dir: Path,
    relative_path: Path,
) -> None:
    """Runtime-facing modules should import CompositeRuntimeConfig via stable facade."""
    file_path = src_dir / relative_path
    content = file_path.read_text(encoding="utf-8")
    canonical_import = (
        "from bioetl.application.composite.runtime_models import CompositeRuntimeConfig"
    )

    assert canonical_import in content, (
        f"{relative_path} must import CompositeRuntimeConfig from runtime_models."
    )
    assert (
        "from bioetl.application.composite.runner_pkg import CompositeRuntimeConfig"
        not in content
    ), f"{relative_path} must not import CompositeRuntimeConfig from runner_pkg facade."
    assert (
        "from bioetl.application.composite.runner_pkg.runner_models import "
        "CompositeRuntimeConfig" not in content
    ), f"{relative_path} must not import CompositeRuntimeConfig from runner_models."


def _parse_tree(path: Path) -> ast.AST:
    return ast.parse(path.read_text(encoding="utf-8"))


@pytest.mark.architecture
def test_composite_support_service_builders_stays_facade_only(src_dir: Path) -> None:
    """The composite support builders module should remain a thin re-export facade."""
    file_path = (
        src_dir
        / "bioetl"
        / "composition"
        / "bootstrap"
        / "runtime"
        / "composite_support_service_builders.py"
    )
    content = file_path.read_text(encoding="utf-8")
    tree = _parse_tree(file_path)

    function_defs = [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    class_defs = [
        node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)
    ]

    assert not function_defs, (
        "composite_support_service_builders.py must stay a facade-only module. "
        f"Found local function definitions: {function_defs}"
    )
    assert not class_defs, (
        "composite_support_service_builders.py must stay a facade-only module. "
        f"Found local class definitions: {class_defs}"
    )

    allowed_import_modules = {
        "bioetl.application.composite.runtime_models",
        "bioetl.composition.bootstrap.runtime.composite_execution_support_builder",
        "bioetl.composition.bootstrap.runtime.composite_merge_dependency_builder",
        "bioetl.composition.bootstrap.runtime.composite_runtime_management_builder",
        "bioetl.composition.bootstrap.runtime.composite_support_service_bundles",
        "__future__",
        "typing",
    }
    import_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    unexpected_imports = import_modules - allowed_import_modules
    assert not unexpected_imports, (
        "composite_support_service_builders.py imported unexpected modules:\n"
        + "\n".join(sorted(unexpected_imports))
    )

    line_count = len(content.splitlines())
    assert line_count <= 40, (
        "composite_support_service_builders.py must remain a thin facade "
        f"(current lines: {line_count}, max: 40)."
    )
