#!/usr/bin/env python3
"""AST-анализатор дубликатов функций в выбранной области проекта."""

from __future__ import annotations

import argparse
import ast
import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

DEFAULT_PATTERNS = (
    "src/bioetl/application/**/utils.py",
    "src/bioetl/infrastructure/**/utils.py",
)
DEFAULT_EXCLUDE_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".venv",
    "__pycache__",
    "build",
    "data",
    "dist",
    "node_modules",
    "reports",
    "site",
}


@dataclass(frozen=True)
class FunctionRecord:
    name: str
    file_path: Path
    lineno: int
    body_hash: str
    body_source: str


def get_project_root() -> Path:
    """Вернуть путь к корню проекта."""
    return Path(__file__).resolve().parents[2]


def parse_args() -> argparse.Namespace:
    """Распарсить аргументы командной строки."""
    parser = argparse.ArgumentParser(
        description="AST-анализатор дубликатов функций в выбранной области.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  python src/tools/scripts/duplicate_function_analyzer.py
  python src/tools/scripts/duplicate_function_analyzer.py \\
    --pattern src/bioetl/application/**/utils.py \\
    --pattern src/bioetl/infrastructure/**/utils.py
        """,
    )
    parser.add_argument(
        "--pattern",
        action="append",
        default=list(DEFAULT_PATTERNS),
        help=(
            "Glob-паттерн для поиска файлов (можно указывать несколько раз). "
            f"По умолчанию: {', '.join(DEFAULT_PATTERNS)}"
        ),
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("reports/duplicate_function_report.md"),
        help="Путь для детального отчета (default: reports/duplicate_function_report.md).",
    )
    parser.add_argument(
        "--dry-run-report",
        type=Path,
        default=Path("reports/dry_run_report.md"),
        help="Путь для общего dry-run отчета (default: reports/dry_run_report.md).",
    )
    parser.add_argument(
        "--skip-dry-run-report",
        action="store_true",
        help="Не обновлять общий dry-run отчет.",
    )
    parser.add_argument(
        "--scan-root",
        type=Path,
        default=Path("."),
        help="Корень сканирования для подсчета вызовов по репозиторию.",
    )
    return parser.parse_args()


def should_skip(path: Path, exclude_dirs: set[str]) -> bool:
    """Проверить, нужно ли исключить путь из сканирования."""
    return any(parent.name in exclude_dirs for parent in path.parents)


def collect_target_files(patterns: list[str], project_root: Path) -> list[Path]:
    """Собрать файлы по заданным паттернам."""
    files: set[Path] = set()
    for pattern in patterns:
        files.update(project_root.glob(pattern))
    return sorted(files)


def load_source(path: Path) -> str:
    """Прочитать исходник файла."""
    return path.read_text(encoding="utf-8")


def extract_body_source(source_lines: list[str], node: ast.AST) -> str:
    """Извлечь текст тела функции без docstring."""
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return ""
    body_nodes = list(node.body)
    if body_nodes and isinstance(body_nodes[0], ast.Expr):
        value = getattr(body_nodes[0], "value", None)
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            body_nodes = body_nodes[1:]
    if not body_nodes:
        return ""
    start_line = body_nodes[0].lineno
    end_line = body_nodes[-1].end_lineno or body_nodes[-1].lineno
    return "".join(source_lines[start_line - 1 : end_line]).rstrip()


def hash_function_body(node: ast.AST) -> str:
    """Посчитать хеш тела функции на основе AST."""
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return ""
    body_nodes = list(node.body)
    if body_nodes and isinstance(body_nodes[0], ast.Expr):
        value = getattr(body_nodes[0], "value", None)
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            body_nodes = body_nodes[1:]
    module = ast.Module(body=body_nodes, type_ignores=[])
    normalized = ast.dump(module, include_attributes=False)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def collect_functions(files: list[Path]) -> list[FunctionRecord]:
    """Собрать функции из заданных файлов."""
    records: list[FunctionRecord] = []
    for path in files:
        source = load_source(path)
        source_lines = source.splitlines(keepends=True)
        tree = ast.parse(source, filename=str(path))
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                body_source = extract_body_source(source_lines, node)
                body_hash = hash_function_body(node)
                records.append(
                    FunctionRecord(
                        name=node.name,
                        file_path=path,
                        lineno=node.lineno,
                        body_hash=body_hash,
                        body_source=body_source,
                    )
                )
    return records


class CallCounter(ast.NodeVisitor):
    """Подсчет вызовов функций по имени."""

    def __init__(self, target_names: set[str]) -> None:
        self._target_names = target_names
        self.counts = dict.fromkeys(target_names, 0)

    def visit_Call(self, node: ast.Call) -> None:
        func_name = None
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr
        if func_name in self.counts:
            self.counts[func_name] += 1
        self.generic_visit(node)


def collect_call_counts(
    root: Path, target_names: set[str], exclude_dirs: set[str]
) -> dict[str, int]:
    """Подсчитать вызовы функций по репозиторию."""
    counter = CallCounter(target_names)
    for path in root.rglob("*.py"):
        if should_skip(path, exclude_dirs):
            continue
        source = load_source(path)
        tree = ast.parse(source, filename=str(path))
        counter.visit(tree)
    return counter.counts


def group_by_name(records: list[FunctionRecord]) -> dict[str, list[FunctionRecord]]:
    """Сгруппировать функции по имени."""
    grouped: dict[str, list[FunctionRecord]] = {}
    for record in records:
        grouped.setdefault(record.name, []).append(record)
    return grouped


def render_report(
    grouped: dict[str, list[FunctionRecord]],
    call_counts: dict[str, int],
    patterns: list[str],
    report_path: Path,
) -> None:
    """Сформировать детальный отчет."""
    timestamp = datetime.now(UTC).isoformat()
    lines: list[str] = [
        "# Duplicate Function Report",
        "",
        f"Generated: {timestamp} (UTC)",
        "",
        "## Scope",
        "",
        f"- Patterns: {', '.join(patterns)}",
        f"- Functions found: {sum(len(items) for items in grouped.values())}",
        f"- Duplicate names: {sum(1 for items in grouped.values() if len(items) > 1)}",
        "",
        "## Function Index",
        "",
    ]

    for name in sorted(grouped.keys()):
        records = sorted(grouped[name], key=lambda r: str(r.file_path))
        if len(records) == 1:
            continue
        call_count = call_counts.get(name, 0)
        lines.append(f"### {name}")
        lines.append("")
        lines.append(f"- Calls in repo: **{call_count}**")
        lines.append(f"- Occurrences: **{len(records)}**")
        lines.append("")
        lines.append("| File | Line | Body Hash |")
        lines.append("|------|------|-----------|")
        for record in records:
            lines.append(
                f"| `{record.file_path}` | {record.lineno} | `{record.body_hash[:12]}` |"
            )
        lines.append("")
        hash_groups: dict[str, list[FunctionRecord]] = {}
        for record in records:
            hash_groups.setdefault(record.body_hash, []).append(record)
        if len(hash_groups) > 1:
            lines.append("**Implementation differences:**")
            lines.append("")
            for body_hash, group in sorted(hash_groups.items()):
                files = ", ".join(f"`{rec.file_path}`" for rec in group)
                lines.append(f"- `{body_hash[:12]}` → {files}")
            lines.append("")

    candidates = [
        name
        for name, records in grouped.items()
        if len(records) > 1 and len({record.body_hash for record in records}) == 1
    ]
    lines.append("## Candidate Functions for Unification (Optional)")
    lines.append("")
    if candidates:
        for name in sorted(candidates):
            lines.append(f"- `{name}`")
    else:
        lines.append("- Нет очевидных кандидатов по идентичному body hash.")
    lines.append("")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def update_dry_run_report(
    report_path: Path,
    detail_report_path: Path,
    grouped: dict[str, list[FunctionRecord]],
    call_counts: dict[str, int],
) -> None:
    """Добавить секцию в общий dry-run отчет."""
    timestamp = datetime.now(UTC).isoformat()
    duplicates = {
        name: records for name, records in grouped.items() if len(records) > 1
    }
    lines = [
        "## Duplicate Function Analyzer",
        "",
        f"- Generated: {timestamp} (UTC)",
        f"- Duplicate names: {len(duplicates)}",
        f"- Detailed report: `{detail_report_path}`",
        "",
    ]
    for name in sorted(duplicates.keys()):
        call_count = call_counts.get(name, 0)
        lines.append(f"- `{name}`: {len(duplicates[name])} files, calls={call_count}")
    lines.append("")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    if report_path.exists():
        existing = report_path.read_text(encoding="utf-8").rstrip()
        content = "\n".join([existing, "", *lines])
    else:
        header = "# Dry-run Report\n"
        content = "\n".join([header, *lines])
    report_path.write_text(content, encoding="utf-8")


def main() -> None:
    args = parse_args()
    project_root = get_project_root()
    patterns = [p.strip() for p in args.pattern if p.strip()]
    files = collect_target_files(patterns, project_root)
    records = collect_functions(files)
    grouped = group_by_name(records)
    call_counts = collect_call_counts(
        project_root / args.scan_root, set(grouped.keys()), DEFAULT_EXCLUDE_DIRS
    )
    render_report(grouped, call_counts, patterns, args.report)
    if not args.skip_dry_run_report:
        update_dry_run_report(args.dry_run_report, args.report, grouped, call_counts)


if __name__ == "__main__":
    main()
