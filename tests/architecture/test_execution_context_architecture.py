"""Architecture guardrails for execution context responsibilities."""

from __future__ import annotations

import pytest

import ast
from pathlib import Path


pytestmark = pytest.mark.architecture

CONTEXT_MODULE = Path("src/bioetl/domain/context.py")
CONTROL_PLANE_MANIFEST_MODULE = Path("src/bioetl/domain/control_plane/run_manifest.py")
VALUE_OBJECT_MANIFEST_MODULE = Path("src/bioetl/domain/value_objects/run_manifest.py")


def _module_docstring(path: Path) -> str:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return ast.get_docstring(tree) or ""


def _class_docstring(path: Path, class_name: str) -> str:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return ast.get_docstring(node) or ""
    raise AssertionError(f"{class_name} not found in {path}")


def test_context_module_documents_split_runtime_model() -> None:
    docstring = _module_docstring(CONTEXT_MODULE)
    assert "PipelineRunContext" in docstring
    assert "PipelineContext" in docstring
    assert "control-plane" in docstring.lower()
    assert "run_manifest.RunManifest" in docstring
    assert "universal runtime manifest object" in docstring


def test_pipeline_context_roles_are_explicit() -> None:
    pipeline_context_doc = _class_docstring(CONTEXT_MODULE, "PipelineContext")
    pipeline_run_context_doc = _class_docstring(CONTEXT_MODULE, "PipelineRunContext")

    assert "In-run processing context" in pipeline_context_doc
    assert "Launch/execution descriptor" in pipeline_run_context_doc


def test_control_plane_run_manifest_is_documented_as_provenance_artifact() -> None:
    module_docstring = _module_docstring(CONTROL_PLANE_MANIFEST_MODULE)
    class_docstring = _class_docstring(CONTROL_PLANE_MANIFEST_MODULE, "RunManifest")

    assert "provenance" in module_docstring.lower()
    assert "replace ``PipelineRunContext`` or ``PipelineContext``" in module_docstring
    assert "control-plane artifact" in class_docstring
    assert "not the universal runtime" in class_docstring


def test_value_object_run_manifest_module_is_not_reintroduced() -> None:
    assert not VALUE_OBJECT_MANIFEST_MODULE.exists(), (
        "The deprecated value-object RunManifest module must stay removed. "
        "Use PipelineRunContext/PipelineContext for runtime execution and "
        "domain.control_plane.RunManifest for provenance."
    )
