#!/usr/bin/env python3
"""Analyze lightweight code-quality heuristics for manual Sonar triage."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def _empty_issues(total_files: int) -> dict[str, int]:
    return {
        "complex_functions": 0,
        "long_functions": 0,
        "unused_imports": 0,
        "missing_docstrings": 0,
        "total_files": total_files,
        "total_lines": 0,
    }


def _read_file_content(file_path: Path) -> tuple[str, list[str]]:
    with file_path.open("r", encoding="utf-8") as handle:
        content = handle.read()
    return content, content.split("\n")


def _handle_file_read_error(file_path: Path, error: Exception) -> None:
    if isinstance(error, UnicodeDecodeError):
        print(f"⚠️  Skipping {file_path} due to encoding issues")
    elif isinstance(error, PermissionError):
        print(f"⚠️  Skipping {file_path} due to permission issues")
    else:
        print(f"⚠️  Skipping {file_path} due to file access error: {error}")


def _check_function_complexity(content: str, file_issues: dict[str, int]) -> None:
    if "if " in content or "for " in content or "while " in content:
        indicators = content.count("if") + content.count("for") + content.count("while")
        if indicators > 5:
            file_issues["complex_functions"] += 1


def _check_function_length(lines: list[str], file_issues: dict[str, int]) -> None:
    function_lines = [line for line in lines if line.strip() and not line.strip().startswith("#")]
    if len(function_lines) > 50:
        file_issues["long_functions"] += 1


def _check_docstring_presence(content: str, file_issues: dict[str, int]) -> None:
    if '"""' not in content and "'''" not in content:
        file_issues["missing_docstrings"] += 1


def _check_function_quality(content: str, lines: list[str], file_issues: dict[str, int]) -> None:
    _check_function_complexity(content, file_issues)
    _check_function_length(lines, file_issues)
    _check_docstring_presence(content, file_issues)


def _merge_file_issues(target: dict[str, int], source: dict[str, int]) -> None:
    for key in ("complex_functions", "long_functions", "missing_docstrings", "total_lines"):
        target[key] += source[key]


def _analyze_single_file(file_path: Path) -> dict[str, int]:
    file_issues = _empty_issues(1)
    try:
        content, lines = _read_file_content(file_path)
        file_issues["total_lines"] = len(lines)
        if "def " in content:
            _check_function_quality(content, lines, file_issues)
    except (UnicodeDecodeError, PermissionError, OSError) as exc:
        _handle_file_read_error(file_path, exc)
    return file_issues


def _analyze_file_batch(python_files: list[Path]) -> dict[str, int]:
    issues_found = _empty_issues(len(python_files))
    for file_path in python_files:
        _merge_file_issues(issues_found, _analyze_single_file(file_path))
    return issues_found


def analyze_python_code() -> dict[str, int]:
    python_files = list(Path("./src").rglob("*.py"))
    if not python_files:
        print("❌ No Python files found in ./src")
        return _empty_issues(0)

    print(f"📊 Analyzing {len(python_files)} Python files...")
    return _analyze_file_batch(python_files[:50])


def _is_test_file(file_name: str) -> bool:
    return file_name.startswith("test_") or file_name.endswith("_test.py")


def _add_module_name(file_name: str, structure: dict[str, set[str]]) -> None:
    module_name = file_name.removesuffix(".py")
    if not module_name.startswith("_"):
        structure["modules"].add(module_name)


def _process_directories(dirs: list[str], structure: dict[str, set[str]]) -> None:
    for dir_name in dirs:
        if not dir_name.startswith("_"):
            structure["packages"].add(dir_name)


def _process_files(files: list[str], structure: dict[str, set[str]]) -> None:
    for file_name in files:
        if not file_name.endswith(".py"):
            continue
        if _is_test_file(file_name):
            structure["test_files"].add(file_name)
        else:
            _add_module_name(file_name, structure)


def analyze_code_structure() -> dict[str, set[str]]:
    structure = {"packages": set(), "modules": set(), "test_files": set()}
    for _root, dirs, files in os.walk("./src"):
        _process_directories(dirs, structure)
        _process_files(files, structure)
    return structure


def _render_quality_relevance(quality_score: float, quality_issues: dict[str, int]) -> None:
    print("\n🎯 Sonar Remediation Issues Relevance:")

    if quality_score >= 90:
        print("   ✅ EXCELLENT - Code quality is very high")
        print("   📋 Sonar issues may be proactive/preventive")
        print("   🔮 Focus on maintaining quality rather than fixing issues")
    elif quality_score >= 75:
        print("   ✅ GOOD - Code quality is solid")
        print("   📋 Sonar issues are likely relevant for continuous improvement")
        print("   🔮 Wave-based approach makes sense for systematic improvement")
    elif quality_score >= 50:
        print("   ⚠️  FAIR - Code quality needs attention")
        print("   📋 Sonar issues are highly relevant and necessary")
        print("   🔮 Remediation waves should be prioritized")
    else:
        print("   ❌ POOR - Code quality needs significant improvement")
        print("   📋 Sonar issues are critical and urgent")
        print("   🔮 Immediate action required on remediation")

    print("\n💡 Specific Recommendations:")
    if quality_issues["complex_functions"] > 5:
        print("   • Refactor complex functions (Wave 3: complexity refactors)")
    if quality_issues["long_functions"] > 3:
        print("   • Split long functions into smaller, focused methods")
    if quality_issues["missing_docstrings"] > 10:
        print("   • Add docstrings for better documentation (Wave 4: hygiene)")


def main() -> None:
    print("🔍 Comprehensive Code Quality Analysis")
    print("=" * 50)

    print("\n🏗️  Code Structure Analysis:")
    structure = analyze_code_structure()
    print(f"   Packages: {len(structure['packages'])}")
    print(f"   Modules: {len(structure['modules'])}")
    print(f"   Test files: {len(structure['test_files'])}")

    print("\n🔬 Code Quality Analysis:")
    quality_issues = analyze_python_code()
    print(f"   Files analyzed: {quality_issues['total_files']}")
    print(f"   Total lines: {quality_issues['total_lines']}")
    print(f"   Complex functions: {quality_issues['complex_functions']}")
    print(f"   Long functions: {quality_issues['long_functions']}")
    print(f"   Missing docstrings: {quality_issues['missing_docstrings']}")

    total_issues = (
        quality_issues["complex_functions"]
        + quality_issues["long_functions"]
        + quality_issues["missing_docstrings"]
    )
    if quality_issues["total_files"] > 0:
        issues_per_file = total_issues / quality_issues["total_files"]
        quality_score = max(0.0, 100 - (issues_per_file * 10))
    else:
        quality_score = 100.0

    print(f"\n📊 Quality Score: {quality_score:.1f}/100")
    _render_quality_relevance(quality_score, quality_issues)
    print("\n✅ Analysis complete!")


if __name__ == "__main__":
    main()
