from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import yaml


@dataclass
class DocsCheckResult:
    missing_abc_entries: set[str]
    extra_abc_entries: set[str]
    schema_mismatches: dict[str, str]

    def is_ok(self) -> bool:
        return not (self.missing_abc_entries or self.extra_abc_entries or self.schema_mismatches)

    def format_errors(self) -> str:
        lines: list[str] = []
        if self.missing_abc_entries:
            missing = ", ".join(sorted(self.missing_abc_entries))
            lines.append(f"Missing ABC entries in docs/01-ABC/INDEX.md: {missing}")
        if self.extra_abc_entries:
            extra = ", ".join(sorted(self.extra_abc_entries))
            lines.append(f"Unexpected ABC entries in docs/01-ABC/INDEX.md: {extra}")
        for schema, message in sorted(self.schema_mismatches.items()):
            lines.append(f"Schema '{schema}': {message}")
        return "\n".join(lines)


def _find_project_root(start: Path) -> Path:
    for path in [start, *start.parents]:
        if (path / "pyproject.toml").exists() or (path / ".git").exists():
            return path
    return start


def _load_yaml(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        msg = f"Expected mapping in {path}"
        raise ValueError(msg)
    return data


def _load_abc_sources(root: Path) -> tuple[set[str], Path]:
    registry_path = root / "src" / "bioetl" / "infrastructure" / "clients" / "base" / "abc_registry.yaml"
    impl_path = root / "src" / "bioetl" / "infrastructure" / "clients" / "base" / "abc_impls.yaml"
    app_impl_path = root / "src" / "bioetl" / "interfaces" / "abc_impls_application.yaml"

    registry = set(_load_yaml(registry_path))
    impls = set(_load_yaml(impl_path))
    app_impls = set(_load_yaml(app_impl_path))

    expected_abcs = registry | impls | app_impls
    docs_path = root / "docs" / "01-ABC" / "INDEX.md"
    return expected_abcs, docs_path


def _parse_abc_index(text: str) -> set[str]:
    pattern = re.compile(r"^- `([^`]+)`", flags=re.MULTILINE)
    return set(pattern.findall(text))


def _extract_schema_columns(lines: Iterable[str]) -> list[str]:
    text = " ".join(lines)
    return re.findall(r"`([^`]+)`", text)


def _load_schema_docs(schema_doc_path: Path) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current: str | None = None
    buffer: list[str] = []
    for line in schema_doc_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            if current is not None:
                sections[current] = _extract_schema_columns(buffer)
            current = line[3:].strip()
            buffer = []
        elif current is not None:
            if not line.strip() and buffer:
                sections[current] = _extract_schema_columns(buffer)
                current = None
                buffer = []
            elif line.strip():
                buffer.append(line.strip())
    if current is not None:
        sections[current] = _extract_schema_columns(buffer)
    return sections


def _load_schema_expectations(root: Path) -> dict[str, list[str]]:
    sys.path.insert(0, str(root / "src"))
    from bioetl.domain.schemas.chembl import output_views  # noqa: WPS433

    expected: dict[str, list[str]] = {}
    for name in dir(output_views):
        if not name.endswith("_OUTPUT_COLUMNS"):
            continue
        heading = name.removesuffix("_OUTPUT_COLUMNS").title()
        expected[heading] = list(getattr(output_views, name))
    return expected


def run_checks() -> DocsCheckResult:
    root = _find_project_root(Path(__file__).resolve())
    expected_abcs, docs_path = _load_abc_sources(root)
    doc_text = docs_path.read_text(encoding="utf-8")
    documented_abcs = _parse_abc_index(doc_text)

    missing_abc_entries = expected_abcs - documented_abcs
    extra_abc_entries = documented_abcs - expected_abcs

    schema_doc_path = root / "docs" / "schemas" / "01-chembl-schema-columns.md"
    documented_schemas = _load_schema_docs(schema_doc_path)
    expected_schemas = _load_schema_expectations(root)

    schema_mismatches: dict[str, str] = {}
    for name, expected_columns in expected_schemas.items():
        if name not in documented_schemas:
            schema_mismatches[name] = "Section missing in documentation"
            continue
        documented_columns = documented_schemas[name]
        if documented_columns != expected_columns:
            schema_mismatches[name] = (
                "Column order mismatch between docs and output_views constants"
            )

    for name in documented_schemas:
        if name not in expected_schemas:
            schema_mismatches[name] = "Unexpected schema documented"

    return DocsCheckResult(
        missing_abc_entries=missing_abc_entries,
        extra_abc_entries=extra_abc_entries,
        schema_mismatches=schema_mismatches,
    )


def main() -> None:
    result = run_checks()
    if not result.is_ok():
        print(result.format_errors())
        raise SystemExit(os.EX_SOFTWARE)


if __name__ == "__main__":
    main()
