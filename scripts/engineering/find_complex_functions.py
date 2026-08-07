#!/usr/bin/env python3
"""Find functions with high cognitive complexity in scripts directory."""

import ast
from pathlib import Path


def calculate_cognitive_complexity(node: ast.AST) -> int:
    """Calculate cognitive complexity of an AST node."""
    complexity = 0
    nesting_level = 0

    for child in ast.walk(node):
        if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
            complexity += 1 + nesting_level
            nesting_level += 1
        elif isinstance(child, ast.ExceptHandler):
            complexity += 1 + nesting_level
            nesting_level += 1
        elif isinstance(child, (ast.BoolOp, ast.Compare)):
            complexity += 1
        elif isinstance(child, (ast.Lambda, ast.ListComp, ast.DictComp, ast.SetComp, ast.GeneratorExp)):
            complexity += 1 + nesting_level
        elif isinstance(child, ast.IfExp):
            complexity += 1 + nesting_level
        elif isinstance(child, (ast.And, ast.Or)):
            complexity += 1

        # Decrease nesting after compound statements
        if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor, ast.ExceptHandler)):
            # This is a simplification - proper nesting tracking would need more context
            pass

    return complexity


def find_complex_functions(file_path: Path, threshold: int = 15) -> list[tuple[str, int, int]]:
    """Find functions with cognitive complexity above threshold."""
    try:
        source = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []

    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError:
        return []

    results = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            complexity = calculate_cognitive_complexity(node)
            if complexity > threshold:
                results.append((node.name, node.lineno, complexity))
    return results


def main() -> None:
    scripts_dir = Path(__file__).parent.parent.parent
    threshold = 15

    all_results = []
    for py_file in scripts_dir.rglob("*.py"):
        if "__pycache__" in py_file.parts:
            continue
        results = find_complex_functions(py_file, threshold)
        if results:
            for func_name, line_no, complexity in results:
                rel_path = py_file.relative_to(scripts_dir)
                all_results.append((str(rel_path), func_name, line_no, complexity))

    # Sort by complexity descending
    all_results.sort(key=lambda x: x[3], reverse=True)

    print(f"Functions with cognitive complexity > {threshold}:")
    print("=" * 80)
    for rel_path, func_name, line_no, complexity in all_results:
        print(f"{complexity:3d} {rel_path}:{line_no} - {func_name}()")

    print(f"\nTotal: {len(all_results)} functions")


if __name__ == "__main__":
    main()
