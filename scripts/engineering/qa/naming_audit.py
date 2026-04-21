#!/usr/bin/env python3
"""
Naming Convention Audit Tool for BioETL.

Validates naming conventions according to RULES.md v5.24 §2:
- Classes: PascalCase with role-appropriate suffixes
- Modules: snake_case
- Functions: snake_case with semantic prefixes
- Documentation: kebab-case (or NN- prefixed for ordered docs)
- YAML Configs: snake_case
- Constants: UPPER_SNAKE_CASE

Usage:
    python src/tools/naming_audit.py                  # Full audit
    python src/tools/naming_audit.py --check          # CI mode (exit 1 on violations)
    python src/tools/naming_audit.py --output reports/quality/naming-audit.md  # Save report to file
"""

from __future__ import annotations

import argparse
import ast
import logging
import re
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import yaml

# Configure logging for CLI output
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)
REPO_ROOT = Path(__file__).resolve().parents[3]
NAMING_EXCEPTIONS_PATH = REPO_ROOT / "configs" / "naming_exceptions.yaml"


class ViolationType(StrEnum):
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


@dataclass(frozen=True)
class StablePublicName:
    """Registry entry for an intentionally stable public identifier."""

    name: str
    location: str
    reason: str


@dataclass(frozen=True)
class ForbiddenAlias:
    """Registry entry for a forbidden legacy alias."""

    legacy_name: str
    canonical_name: str
    export_surface: str
    reason: str


@dataclass(frozen=True)
class NamingRegistry:
    """Parsed naming exception registry."""

    documentation_exceptions: frozenset[str]
    root_file_exceptions: frozenset[str]
    class_suffix_exceptions: frozenset[str]
    function_prefix_exceptions: frozenset[str]
    stable_pipeline_ids: tuple[StablePublicName, ...]
    stable_pipeline_classes: tuple[StablePublicName, ...]
    stable_transformers: tuple[StablePublicName, ...]
    stable_gold_schemas: tuple[StablePublicName, ...]
    forbidden_domain_entity_aliases: tuple[ForbiddenAlias, ...]


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
    "Assembler": ["Assembler"],
}

# Directories excluded from doc naming audit (archives, plans, AI content)
_DOC_EXCLUDED_DIRS = {
    "99-archive",
    "plans",
}

# Sub-paths excluded from doc naming audit (relative to docs root)
_DOC_EXCLUDED_SUBPATHS = {
    "00-project/ai",
    "repor",
    "reports",
    "docs/reports",
    "reports/evidence",
}


def _normalize_doc_excluded_subpath(subpath: str) -> str:
    """Normalize configured docs exclusion prefixes to docs-root-relative paths."""
    normalized = subpath.replace("\\", "/").strip("/")
    if normalized.startswith("docs/"):
        normalized = normalized.removeprefix("docs/")
    return normalized


def _flatten_string_values(raw: object) -> list[str]:
    """Flatten nested YAML lists/dicts to strings only."""
    values: list[str] = []
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, str):
                values.append(item)
    elif isinstance(raw, dict):
        for value in raw.values():
            values.extend(_flatten_string_values(value))
    return values


def _load_stable_names(raw: object) -> tuple[StablePublicName, ...]:
    """Parse stable public surface entries from YAML."""
    if not isinstance(raw, list):
        return ()
    entries: list[StablePublicName] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        location = str(item.get("location", "")).strip()
        reason = str(item.get("reason", "")).strip()
        if name and location and reason:
            entries.append(
                StablePublicName(name=name, location=location, reason=reason)
            )
    return tuple(entries)


def _load_forbidden_aliases(raw: object) -> tuple[ForbiddenAlias, ...]:
    """Parse forbidden legacy alias entries from YAML."""
    if not isinstance(raw, list):
        return ()
    entries: list[ForbiddenAlias] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        legacy_name = str(item.get("legacy_name", "")).strip()
        canonical_name = str(item.get("canonical_name", "")).strip()
        export_surface = str(item.get("export_surface", "")).strip()
        reason = str(item.get("reason", "")).strip()
        if legacy_name and canonical_name and export_surface and reason:
            entries.append(
                ForbiddenAlias(
                    legacy_name=legacy_name,
                    canonical_name=canonical_name,
                    export_surface=export_surface,
                    reason=reason,
                )
            )
    return tuple(entries)


def load_naming_registry(
    registry_path: Path = NAMING_EXCEPTIONS_PATH,
) -> NamingRegistry:
    """Load the naming exception registry from configs/."""
    if not registry_path.exists():
        raise FileNotFoundError(f"Naming exception registry missing: {registry_path}")

    payload = yaml.safe_load(registry_path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError(
            "Naming exception registry must be a YAML mapping at top level"
        )

    stable_public_surface = payload.get("stable_public_surface", {})
    if not isinstance(stable_public_surface, dict):
        raise ValueError("stable_public_surface must be a mapping")

    return NamingRegistry(
        documentation_exceptions=frozenset(
            _flatten_string_values(payload.get("documentation_exceptions", []))
        ),
        root_file_exceptions=frozenset(
            _flatten_string_values(payload.get("root_file_exceptions", []))
        ),
        class_suffix_exceptions=frozenset(
            _flatten_string_values(payload.get("class_suffix_exceptions", {}))
        ),
        function_prefix_exceptions=frozenset(
            _flatten_string_values(payload.get("function_prefix_exceptions", []))
        ),
        stable_pipeline_ids=_load_stable_names(
            stable_public_surface.get("pipeline_ids", [])
        ),
        stable_pipeline_classes=_load_stable_names(
            stable_public_surface.get("pipeline_classes", [])
        ),
        stable_transformers=_load_stable_names(
            stable_public_surface.get("transformers", [])
        ),
        stable_gold_schemas=_load_stable_names(
            stable_public_surface.get("gold_schemas", [])
        ),
        forbidden_domain_entity_aliases=_load_forbidden_aliases(
            payload.get("forbidden_domain_entity_aliases", [])
        ),
    )


def validate_naming_registry(registry: NamingRegistry) -> list[str]:
    """Return consistency errors for the loaded naming registry."""
    errors: list[str] = []

    overlap = {
        alias.legacy_name for alias in registry.forbidden_domain_entity_aliases
    } & set(registry.class_suffix_exceptions)
    if overlap:
        joined = ", ".join(sorted(overlap))
        errors.append(
            "Forbidden legacy aliases are still declared as class suffix exceptions: "
            f"{joined}"
        )

    stable_id_names = {entry.name for entry in registry.stable_pipeline_ids}
    if not stable_id_names:
        errors.append(
            "stable_public_surface.pipeline_ids must declare at least one entry"
        )

    for required in ("pubchem_compound", "uniprot_protein"):
        if required not in stable_id_names:
            errors.append(
                f"stable_public_surface.pipeline_ids is missing required entry: {required}"
            )

    return errors


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


def has_valid_suffix(class_name: str, allowed_no_suffix: frozenset[str]) -> bool:
    """Check whether a class name has a valid suffix or registry-backed exception."""
    if class_name in allowed_no_suffix:
        return True

    for suffixes in ROLE_SUFFIXES.values():
        for suffix in suffixes:
            if class_name.endswith(suffix):
                return True

    return False


def _iter_python_files(base_path: Path) -> Iterator[Path]:
    for py_file in base_path.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue
        yield py_file


def _class_naming_violation(py_file: Path, node: ast.ClassDef) -> Violation | None:
    class_name = node.name

    if class_name.startswith("_") and not class_name.startswith("__"):
        return None

    if is_pascal_case(class_name) or class_name.startswith("_"):
        return None

    return Violation(
        category="class",
        path=str(py_file),
        line=node.lineno,
        current_name=class_name,
        issue=ViolationType.CAMELCASE,
        recommendation=class_name[0].upper() + class_name[1:],
    )


def _doc_relative_parts(docs_path: Path, md_file: Path) -> tuple[Path | None, tuple[str, ...]]:
    try:
        rel = md_file.relative_to(docs_path)
        return rel, rel.parts
    except ValueError:
        return None, ()


def _is_excluded_doc_path(docs_path: Path, md_file: Path) -> bool:
    rel, rel_parts = _doc_relative_parts(docs_path, md_file)
    if rel_parts and rel_parts[0] in _DOC_EXCLUDED_DIRS:
        return True
    if rel is None:
        return False
    normalized_rel = str(rel).replace("\\", "/")
    return any(
        normalized_rel.startswith(_normalize_doc_excluded_subpath(subpath))
        for subpath in _DOC_EXCLUDED_SUBPATHS
    )


def check_python_modules(base_path: Path) -> Iterator[Violation]:
    """Проверяет naming conventions для Python-модулей."""
    for py_file in _iter_python_files(base_path):
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
    for py_file in _iter_python_files(base_path):
        try:
            with open(py_file, encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=str(py_file))
        except (SyntaxError, UnicodeDecodeError):
            continue

        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            if violation := _class_naming_violation(py_file, node):
                yield violation


def check_documentation(
    docs_path: Path, documentation_exceptions: frozenset[str]
) -> Iterator[Violation]:
    """Проверяет naming conventions для файлов документации."""
    for md_file in docs_path.rglob("*.md"):
        filename = md_file.name

        # Исключения для конвенционных файлов
        if filename in documentation_exceptions:
            continue

        if _is_excluded_doc_path(docs_path, md_file):
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
    src_path: Path,
    docs_path: Path,
    configs_path: Path,
    registry: NamingRegistry,
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
        results["docs"].extend(
            check_documentation(docs_path, registry.documentation_exceptions)
        )

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
                    f"| `{v.path}` | {line} | `{v.current_name}` | "
                    f"{v.issue.value} | `{v.recommendation}` |"
                )
            lines.append("")

    if total_violations == 0:
        lines.append(
            "OK: **No violations found. All naming conventions are followed.**"
        )

    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
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
    return parser.parse_args()


def _audit_paths(args: argparse.Namespace) -> tuple[Path, Path, Path]:
    base_dir = REPO_ROOT
    return base_dir / args.src, base_dir / args.docs, base_dir / args.configs


def _load_validated_registry() -> NamingRegistry | None:
    try:
        registry = load_naming_registry()
    except (FileNotFoundError, OSError, ValueError, yaml.YAMLError) as exc:
        logger.error("Failed to load naming exception registry: %s", exc)
        return None

    registry_errors = validate_naming_registry(registry)
    if registry_errors:
        for error in registry_errors:
            logger.error("Naming exception registry error: %s", error)
        return None

    return registry


def _emit_report(report: str, output: str | None) -> None:
    if output:
        output_path = Path(output)
        output_path.write_text(report, encoding="utf-8")
        logger.info("Report saved to %s", output_path)
        return
    logger.info("%s", report)


def main() -> int:
    """Точка входа."""
    args = parse_args()
    src_path, docs_path, configs_path = _audit_paths(args)

    registry = _load_validated_registry()
    if registry is None:
        return 1

    results = run_audit(src_path, docs_path, configs_path, registry)
    report = format_report(results)
    _emit_report(report, args.output)

    # CI mode
    total_violations = sum(len(v) for v in results.values())
    if args.check and total_violations > 0:
        logger.error("Found %d naming violations", total_violations)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
