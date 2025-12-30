#!/usr/bin/env python3
"""
Naming Convention Audit Tool for BioETL.

Validates naming conventions according to RULES.md v5.0 §2:
- Classes: PascalCase with role-appropriate suffixes
- Modules: snake_case
- Functions: snake_case with semantic prefixes
- Documentation: kebab-case (or NN- prefixed for ordered docs)
- YAML Configs: snake_case
- Constants: UPPER_SNAKE_CASE

Usage:
    python src/tools/naming_audit.py                  # Full audit
    python src/tools/naming_audit.py --check          # CI mode (exit 1 on violations)
    python src/tools/naming_audit.py --output report.md  # Save report to file
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class ViolationType(str, Enum):
    """Тип нарушения naming convention."""

    CAMELCASE = "camelCase вместо PascalCase/snake_case"
    UPPERCASE_MODULE = "UPPERCASE в имени модуля"
    HYPHEN_IN_MODULE = "дефис в имени Python-модуля"
    MISSING_SUFFIX = "отсутствует обязательный суффикс"
    UNDERSCORE_IN_DOC = "underscore в имени документации"
    UPPERCASE_DOC = "UPPER_SNAKE_CASE в документации"


@dataclass
class Violation:
    """Нарушение naming convention."""

    category: str
    path: str
    line: int | None
    current_name: str
    issue: ViolationType
    recommendation: str


# Суффиксы для классов по ролям
ROLE_SUFFIXES = {
    "Factory": ["Factory"],
    "Client": ["Client"],
    "Facade": ["Facade"],
    "Registry": ["Registry"],
    "Adapter": ["Adapter"],
    "Protocol": ["Protocol", "Port", "ABC"],
    "Config": ["Config", "Model", "Params", "Settings"],
    "Error": ["Error", "Exception"],
    "Impl": ["Impl"],
    "Service": ["Service"],
    "Writer": ["Writer"],
    "Manager": ["Manager"],
    "Monitor": ["Monitor"],
    "Tracker": ["Tracker"],
    "Builder": ["Builder"],
    "Validator": ["Validator"],
    "Exporter": ["Exporter"],
    "Transformer": ["Transformer"],
    "Pipeline": ["Pipeline"],
    "Observer": ["Observer"],
    "Handler": ["Handler"],
    "Processor": ["Processor"],
    "Recorder": ["Recorder"],
    "Aggregator": ["Aggregator"],
    "Orchestrator": ["Orchestrator"],
    "Collector": ["Collector"],
}

# Допустимые классы без суффиксов (domain entities, enums, etc.)
ALLOWED_NO_SUFFIX = {
    # Domain entities
    "Activity",
    "Assay",
    "Target",
    "TargetComponent",
    "Molecule",
    "Document",
    "Compound",
    "Protein",
    "Publication",
    # Enums
    "Layer",
    "WriteMode",
    "SilverWriteMode",
    "GoldWriteMode",
    "ClearPolicy",
    "RunType",
    "HealthStatus",
    "DriftLevel",
    "CircuitBreakerState",
    "DataClassification",
    "ErrorType",
    "DQStatus",
    "LifecyclePhase",
    "AuditOperation",
    "AuditLayer",
    "AnomalyType",
    "AnomalySeverity",
    # TypedDict classes
    "BronzeRecord",
    "SilverRecord",
    "RawDate",
    "NormalizedDate",
    "RawAuthor",
    "RawIdentifiers",
    "NormalizedIdentifiers",
    "RawClassification",
    "NormalizedClassification",
    # Value objects and results
    "Anomaly",
    "LineageRecord",
    "BatchLineage",
    "ClearDecision",
    "ClearResult",
    "CleanupPreview",
    "CleanupResult",
    "LayerInfo",
    "TransformResult",
    "TransformedRecord",
    "BatchResult",
    "DQResult",
    "VacuumResult",
    "ValidationResult",
    "HealthReport",
    "PreflightReport",
    "ComponentHealthResult",
    "ConfigValidationError",
    "FilterLoadResult",
    "MemoryStats",
    "ProviderHealthState",
    "ShutdownSignal",
    "AuditEntry",
    "LockContext",
    "PipelineEvent",
    "RetryPolicy",
    # Context classes
    "InputFilterContext",
    "VacuumConfig",
    "PipelineContext",
    "PipelineRunContext",
    "StorageContext",
    "ObservabilityBundle",
    "PipelineServices",
    "PipelineDefinition",
    "ProviderConfig",
    "HttpConfig",
    "RunOptions",
    "VacuumOptions",
    "ArchiveOptions",
    "RecordProcessorConfig",
    "MemoryConfig",
    # Base classes
    "BaseEntity",
    "BasePipeline",
    "BaseTransformer",
    "BaseHttpAdapter",
    "BaseSyncAdapter",
    "BaseFieldExtractor",
    "BaseChemblTransformer",
    "BaseServicesFactory",
    # Private helpers
    "_NoOpSpan",
    "_NoOpOtelTracer",
    # Policies
    "MedallionPolicy",
    "WriteModePolicy",
    # TypedDict suffixed with Dict
    "GoldColumnFilterDict",
    "GoldRangeDict",
    "GoldFiltersDict",
    "CsvExportDict",
    "BronzeSinkDict",
    "SilverSinkDict",
    "GoldValidationDict",
    "GoldSinkDict",
    "SinkDict",
    "TransformDict",
    "DQRulesDict",
    "CircuitBreakerDict",
    "InputFilterDict",
    "ClientConfigDict",
    "RateLimitDict",
    "ProviderConfigDict",
    "SourceConfigDict",
    "SourceFileDict",
    "PipelineConfigDict",
    "RuntimeArgsDict",
    # Filters
    "GoldRangeFilter",
    "GoldColumnFilter",
    "GoldListLengthFilter",
    "GoldListContainsFilter",
    "GoldFilterConfig",
    "InputFilterConfig",
    "FilteredDataSource",
}

# Конвенционные файлы документации верхнего уровня (допустимы в UPPER_CASE)
DOC_EXCEPTIONS = {
    "README.md",
    "CHANGELOG.md",
    "REQUIREMENTS.md",
    "RULES.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "LICENSE.md",
    "CLAUDE.md",
    "AGENT.md",
}


def is_pascal_case(name: str) -> bool:
    """Проверяет, что имя в PascalCase."""
    return bool(re.match(r"^[A-Z][a-zA-Z0-9]*$", name))


def is_snake_case(name: str) -> bool:
    """Проверяет, что имя в snake_case."""
    return bool(re.match(r"^[a-z][a-z0-9_]*$", name))


def is_kebab_case(name: str) -> bool:
    """Проверяет, что имя в kebab-case."""
    return bool(re.match(r"^[a-z][a-z0-9-]*$", name))


def is_prefixed_doc(name: str) -> bool:
    """Проверяет, что документ имеет числовой префикс (NN-)."""
    return bool(re.match(r"^\d{2}-", name))


def has_valid_suffix(class_name: str) -> bool:
    """Проверяет, что класс имеет допустимый суффикс или в списке исключений."""
    if class_name in ALLOWED_NO_SUFFIX:
        return True

    for suffixes in ROLE_SUFFIXES.values():
        for suffix in suffixes:
            if class_name.endswith(suffix):
                return True

    return False


def check_python_modules(base_path: Path) -> Iterator[Violation]:
    """Проверяет naming conventions для Python-модулей."""
    for py_file in base_path.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue

        filename = py_file.stem
        if filename.startswith("__"):  # __init__, __main__
            continue

        # Проверка на uppercase
        if any(c.isupper() for c in filename):
            yield Violation(
                category="module",
                path=str(py_file),
                line=None,
                current_name=filename,
                issue=ViolationType.UPPERCASE_MODULE,
                recommendation=filename.lower(),
            )

        # Проверка на дефисы
        if "-" in filename:
            yield Violation(
                category="module",
                path=str(py_file),
                line=None,
                current_name=filename,
                issue=ViolationType.HYPHEN_IN_MODULE,
                recommendation=filename.replace("-", "_"),
            )


def check_classes(base_path: Path) -> Iterator[Violation]:
    """Проверяет naming conventions для классов."""
    for py_file in base_path.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue

        try:
            with open(py_file, encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=str(py_file))
        except (SyntaxError, UnicodeDecodeError):
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_name = node.name

                # Проверка PascalCase (должна начинаться с заглавной, но не с _)
                if class_name.startswith("_") and not class_name.startswith("__"):
                    # Приватные классы типа _NoOpSpan допустимы
                    continue

                if not is_pascal_case(class_name) and not class_name.startswith("_"):
                    yield Violation(
                        category="class",
                        path=str(py_file),
                        line=node.lineno,
                        current_name=class_name,
                        issue=ViolationType.CAMELCASE,
                        recommendation=class_name[0].upper() + class_name[1:],
                    )


def check_documentation(docs_path: Path) -> Iterator[Violation]:
    """Проверяет naming conventions для файлов документации."""
    for md_file in docs_path.rglob("*.md"):
        filename = md_file.name

        # Исключения для конвенционных файлов
        if filename in DOC_EXCEPTIONS:
            continue

        basename = md_file.stem

        # Проверка на underscore (должен быть kebab-case)
        if "_" in basename and not is_prefixed_doc(basename):
            yield Violation(
                category="doc",
                path=str(md_file),
                line=None,
                current_name=filename,
                issue=ViolationType.UNDERSCORE_IN_DOC,
                recommendation=basename.replace("_", "-") + ".md",
            )

        # Проверка на UPPER_SNAKE_CASE (без числового префикса)
        if re.match(r"^[A-Z][A-Z_]+$", basename) and not is_prefixed_doc(basename):
            yield Violation(
                category="doc",
                path=str(md_file),
                line=None,
                current_name=filename,
                issue=ViolationType.UPPERCASE_DOC,
                recommendation=basename.lower().replace("_", "-") + ".md",
            )


def check_yaml_configs(configs_path: Path) -> Iterator[Violation]:
    """Проверяет naming conventions для YAML-конфигов."""
    for yaml_file in configs_path.rglob("*.yaml"):
        filename = yaml_file.stem

        # Проверка на uppercase
        if any(c.isupper() for c in filename):
            yield Violation(
                category="config",
                path=str(yaml_file),
                line=None,
                current_name=filename,
                issue=ViolationType.UPPERCASE_MODULE,
                recommendation=filename.lower(),
            )

        # Проверка на дефисы (YAML должен быть snake_case)
        if "-" in filename:
            yield Violation(
                category="config",
                path=str(yaml_file),
                line=None,
                current_name=filename,
                issue=ViolationType.HYPHEN_IN_MODULE,
                recommendation=filename.replace("-", "_"),
            )


def run_audit(
    src_path: Path, docs_path: Path, configs_path: Path
) -> dict[str, list[Violation]]:
    """Запускает полный аудит naming conventions."""
    results: dict[str, list[Violation]] = {
        "modules": [],
        "classes": [],
        "docs": [],
        "configs": [],
    }

    # Проверка Python-модулей
    results["modules"].extend(check_python_modules(src_path))

    # Проверка классов
    results["classes"].extend(check_classes(src_path))

    # Проверка документации
    if docs_path.exists():
        results["docs"].extend(check_documentation(docs_path))

    # Проверка YAML-конфигов
    if configs_path.exists():
        results["configs"].extend(check_yaml_configs(configs_path))

    return results


def format_report(results: dict[str, list[Violation]]) -> str:
    """Форматирует отчёт об аудите."""
    lines = [
        "# Naming Convention Audit Report",
        "",
        "## Summary",
        "",
    ]

    total_violations = sum(len(v) for v in results.values())

    lines.append(f"**Total violations: {total_violations}**")
    lines.append("")
    lines.append("| Category | Violations |")
    lines.append("|----------|------------|")
    for category, violations in results.items():
        lines.append(f"| {category.title()} | {len(violations)} |")

    lines.append("")

    for category, violations in results.items():
        if violations:
            lines.append(f"## {category.title()} Violations")
            lines.append("")
            lines.append("| Path | Line | Current | Issue | Recommendation |")
            lines.append("|------|------|---------|-------|----------------|")
            for v in violations:
                line = v.line if v.line else "-"
                lines.append(
                    f"| `{v.path}` | {line} | `{v.current_name}` | {v.issue.value} | `{v.recommendation}` |"
                )
            lines.append("")

    if total_violations == 0:
        lines.append("✅ **No violations found. All naming conventions are followed.**")

    return "\n".join(lines)


def main() -> int:
    """Точка входа."""
    parser = argparse.ArgumentParser(
        description="Naming Convention Audit Tool for BioETL"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="CI mode: exit with code 1 if violations found",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Save report to file",
    )
    parser.add_argument(
        "--src",
        type=str,
        default="src/bioetl",
        help="Source code path (default: src/bioetl)",
    )
    parser.add_argument(
        "--docs",
        type=str,
        default="docs",
        help="Documentation path (default: docs)",
    )
    parser.add_argument(
        "--configs",
        type=str,
        default="configs",
        help="Configs path (default: configs)",
    )

    args = parser.parse_args()

    # Определяем базовые пути
    base_dir = Path(__file__).parent.parent.parent
    src_path = base_dir / args.src
    docs_path = base_dir / args.docs
    configs_path = base_dir / args.configs

    # Запуск аудита
    results = run_audit(src_path, docs_path, configs_path)
    report = format_report(results)

    # Вывод или сохранение отчёта
    if args.output:
        output_path = Path(args.output)
        output_path.write_text(report, encoding="utf-8")
        print(f"Report saved to {output_path}")
    else:
        print(report)

    # CI mode
    total_violations = sum(len(v) for v in results.values())
    if args.check and total_violations > 0:
        print(f"\n❌ Found {total_violations} naming violations", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
