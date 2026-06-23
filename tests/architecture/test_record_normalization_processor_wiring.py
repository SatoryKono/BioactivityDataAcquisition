"""Architecture guardrails for RecordNormalizationProcessor wiring.

Normalization on shipped runtime paths must resolve through explicit
provider/entity coordinates unless the call site is a config-driven builder
that intentionally defers fallback policy to runtime configuration.
"""

from __future__ import annotations

import pytest

import ast
from pathlib import Path

pytestmark = pytest.mark.architecture

_CONFIG_DRIVEN_BUILDER_PATHS = {
    Path("bioetl/application/core/_batch_transformer_support.py"),
    Path(
        "bioetl/composition/factories/services/pipeline_processing_components_builder.py"
    ),
}


def _is_record_normalization_processor_call(node: ast.Call) -> bool:
    func = node.func
    return isinstance(func, ast.Name) and func.id == "RecordNormalizationProcessor"


def _keyword_value(node: ast.Call, name: str) -> ast.expr | None:
    for keyword in node.keywords:
        if keyword.arg == name:
            return keyword.value
    return None


def _has_entity_type_argument(node: ast.Call) -> bool:
    entity_type_value = _keyword_value(node, "entity_type")
    if entity_type_value is not None:
        return not (
            isinstance(entity_type_value, ast.Constant)
            and entity_type_value.value is None
        )
    return len(node.args) >= 2


def _has_hardcoded_true_fallback(node: ast.Call) -> bool:
    value = _keyword_value(node, "allow_compatibility_fallback")
    return isinstance(value, ast.Constant) and value.value is True


def test_record_normalization_processor_runtime_paths_keep_entity_coordinates(
    source_ast_cache: dict[Path, ast.Module],
    src_dir: Path,
) -> None:
    """Non-builder runtime paths must instantiate the processor with entity_type."""
    violations: list[str] = []

    for path, tree in sorted(source_ast_cache.items()):
        relative = path.relative_to(src_dir)
        if relative in _CONFIG_DRIVEN_BUILDER_PATHS:
            continue

        for node in ast.walk(tree):
            if not isinstance(
                node, ast.Call
            ) or not _is_record_normalization_processor_call(node):
                continue
            if not _has_entity_type_argument(node):
                violations.append(
                    f"{relative}:{node.lineno}: RecordNormalizationProcessor without entity_type"
                )

    assert not violations, (
        "RecordNormalizationProcessor must receive provider/entity coordinates on "
        "non-builder runtime paths so shipped profile resolution cannot silently "
        "fall back.\n" + "\n".join(f"  - {violation}" for violation in violations)
    )


def test_record_normalization_processor_never_enables_hardcoded_compatibility_fallback(
    source_ast_cache: dict[Path, ast.Module],
    src_dir: Path,
) -> None:
    """Production source must not opt into compatibility fallback inline."""
    violations: list[str] = []

    for path, tree in sorted(source_ast_cache.items()):
        relative = path.relative_to(src_dir)
        for node in ast.walk(tree):
            if not isinstance(
                node, ast.Call
            ) or not _is_record_normalization_processor_call(node):
                continue
            if _has_hardcoded_true_fallback(node):
                violations.append(
                    f"{relative}:{node.lineno}: allow_compatibility_fallback=True"
                )

    assert not violations, (
        "RecordNormalizationProcessor runtime wiring must not hardcode "
        "allow_compatibility_fallback=True in production source.\n"
        + "\n".join(f"  - {violation}" for violation in violations)
    )
