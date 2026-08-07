#!/usr/bin/env python3
"""Generate domain ports inventory under ``src/bioetl/domain/ports/``.

Definitions (authoritative for RULES.md / architecture gates):

* **port_protocol_classes** — ``ast.ClassDef`` nodes named ``*Port`` whose
  bases include ``Protocol`` (direct name or attribute), scanned under
  ``src/bioetl/domain/ports/**/*.py``.
* **runtime_checkable_port_count** — subset of those classes decorated with
  ``@runtime_checkable`` (name or attribute; bare or call form).
* **runtime_checkable_decorator_count** — raw ``@runtime_checkable`` token
  occurrences in scanned module bodies (includes non-``*Port`` Protocols).
* **port_module_files** — ``*.py`` files under the ports tree excluding any
  ``__init__.py`` (implementation modules only).
* **scanned_python_files** — all ``*.py`` files including ``__init__.py``.

Usage::

    python -m scripts.engineering.qa report-domain-ports-inventory
    python -m scripts.engineering.qa report-domain-ports-inventory --check
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]
PORTS_ROOT = PROJECT_ROOT / "src" / "bioetl" / "domain" / "ports"
DEFAULT_JSON_OUTPUT = (
    PROJECT_ROOT / "reports" / "quality" / "domain-ports-inventory.json"
)
DEFAULT_MD_OUTPUT = PROJECT_ROOT / "reports" / "quality" / "domain-ports-inventory.md"
SCHEMA_VERSION = 1
GENERATED_BY = "scripts.engineering.qa.report_domain_ports_inventory"


@dataclass(frozen=True, slots=True)
class PortClassRecord:
    """One Protocol class ending with Port."""

    path: str
    name: str
    line: int
    runtime_checkable: bool


def _relative(path: Path, *, root: Path = PROJECT_ROOT) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _base_names(bases: list[ast.expr]) -> set[str]:
    names: set[str] = set()
    for base in bases:
        if isinstance(base, ast.Name):
            names.add(base.id)
        elif isinstance(base, ast.Attribute):
            names.add(base.attr)
    return names


def _is_runtime_checkable(decorators: list[ast.expr]) -> bool:
    for decorator in decorators:
        node = decorator
        if isinstance(node, ast.Call):
            node = node.func
        if isinstance(node, ast.Name) and node.id == "runtime_checkable":
            return True
        if isinstance(node, ast.Attribute) and node.attr == "runtime_checkable":
            return True
    return False


def _count_runtime_checkable_tokens(source: str) -> int:
    return source.count("@runtime_checkable")


def _iter_port_python_files(ports_root: Path) -> list[Path]:
    return sorted(path for path in ports_root.rglob("*.py") if path.is_file())


def collect_ports_inventory(
    *,
    repo_root: Path = PROJECT_ROOT,
    ports_root: Path | None = None,
) -> dict[str, Any]:
    """Scan domain ports and return a deterministic inventory payload."""
    root = repo_root.resolve()
    ports = (ports_root or (root / "src" / "bioetl" / "domain" / "ports")).resolve()
    if not ports.is_dir():
        raise FileNotFoundError(f"ports root missing: {ports}")

    all_py = _iter_port_python_files(ports)
    module_files = [path for path in all_py if path.name != "__init__.py"]
    records: list[PortClassRecord] = []
    decorator_total = 0

    for path in all_py:
        source = path.read_text(encoding="utf-8")
        decorator_total += _count_runtime_checkable_tokens(source)
        tree = ast.parse(source, filename=str(path))
        relative = _relative(path, root=root)
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            if not node.name.endswith("Port"):
                continue
            if "Protocol" not in _base_names(node.bases):
                continue
            records.append(
                PortClassRecord(
                    path=relative,
                    name=node.name,
                    line=node.lineno,
                    runtime_checkable=_is_runtime_checkable(node.decorator_list),
                )
            )

    records.sort(key=lambda item: (item.path, item.line, item.name))
    protocol_count = len(records)
    runtime_port_count = sum(1 for item in records if item.runtime_checkable)
    coverage_pct = (
        round(100.0 * runtime_port_count / protocol_count, 2) if protocol_count else 0.0
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "ports_root": "src/bioetl/domain/ports",
        "definitions": {
            "port_protocol_classes": (
                "Protocol classes named *Port under domain/ports/**/*.py"
            ),
            "runtime_checkable_port_count": (
                "port_protocol_classes decorated with @runtime_checkable"
            ),
            "runtime_checkable_decorator_count": (
                "raw @runtime_checkable occurrences in scanned *.py bodies "
                "(may include non-*Port Protocols)"
            ),
            "port_module_files": ("*.py under domain/ports excluding __init__.py"),
            "scanned_python_files": (
                "all *.py under domain/ports including __init__.py"
            ),
        },
        "summary": {
            "scanned_python_files": len(all_py),
            "port_module_files": len(module_files),
            "port_protocol_classes": protocol_count,
            "runtime_checkable_port_count": runtime_port_count,
            "runtime_checkable_decorator_count": decorator_total,
            "runtime_checkable_coverage_pct": coverage_pct,
        },
        "ports": [asdict(item) for item in records],
    }


def render_markdown(payload: dict[str, Any]) -> str:
    """Render a short markdown inventory report."""
    summary = payload["summary"]
    assert isinstance(summary, dict)
    lines = [
        "# Domain Ports Inventory",
        "",
        f"Generated by `{payload['generated_by']}`.",
        "",
        "## Definitions",
        "",
        "| Metric | Definition |",
        "| --- | --- |",
    ]
    definitions = payload.get("definitions", {})
    assert isinstance(definitions, dict)
    for key, text in definitions.items():
        lines.append(f"| `{key}` | {text} |")
    lines.extend(
        [
            "",
            "## Summary",
            "",
            "| Metric | Count |",
            "| --- | ---: |",
            f"| scanned_python_files | {summary['scanned_python_files']} |",
            f"| port_module_files (excl. `__init__`) | {summary['port_module_files']} |",
            f"| port_protocol_classes (`*Port` + Protocol) | {summary['port_protocol_classes']} |",
            f"| runtime_checkable_port_count | {summary['runtime_checkable_port_count']} |",
            f"| runtime_checkable_decorator_count | {summary['runtime_checkable_decorator_count']} |",
            f"| runtime_checkable_coverage_pct | {summary['runtime_checkable_coverage_pct']} |",
            "",
            "## Port classes",
            "",
            "| Path | Class | Line | `@runtime_checkable` |",
            "| --- | --- | ---: | --- |",
        ]
    )
    ports = payload.get("ports", [])
    assert isinstance(ports, list)
    for item in ports:
        assert isinstance(item, dict)
        lines.append(
            f"| `{item['path']}` | `{item['name']}` | {item['line']} | "
            f"{'yes' if item['runtime_checkable'] else 'no'} |"
        )
    lines.append("")
    return "\n".join(lines)


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_OUTPUT)
    parser.add_argument("--md-out", type=Path, default=DEFAULT_MD_OUTPUT)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail when JSON/MD artifacts drift from a live scan",
    )
    args = parser.parse_args(argv)

    repo_root = args.repo_root.resolve()
    payload = collect_ports_inventory(repo_root=repo_root)
    json_out = (
        args.json_out if args.json_out.is_absolute() else repo_root / args.json_out
    )
    md_out = args.md_out if args.md_out.is_absolute() else repo_root / args.md_out
    expected_json = _canonical_json(payload)
    expected_md = render_markdown(payload)

    if args.check:
        errors: list[str] = []
        if not json_out.exists():
            errors.append(f"missing domain ports inventory JSON: {json_out}")
        elif json_out.read_text(encoding="utf-8") != expected_json:
            errors.append(f"stale domain ports inventory JSON: {json_out}")
        if not md_out.exists():
            errors.append(f"missing domain ports inventory MD: {md_out}")
        elif md_out.read_text(encoding="utf-8") != expected_md:
            errors.append(f"stale domain ports inventory MD: {md_out}")
        if errors:
            for message in errors:
                print(message, file=sys.stderr)
            print(
                "Regenerate with:\n"
                "  python -m scripts.engineering.qa report-domain-ports-inventory",
                file=sys.stderr,
            )
            return 1
        summary = payload["summary"]
        assert isinstance(summary, dict)
        print(
            "[ok] domain ports inventory: "
            f"port_protocol_classes={summary['port_protocol_classes']} "
            f"runtime_checkable_port_count={summary['runtime_checkable_port_count']} "
            f"port_module_files={summary['port_module_files']}"
        )
        return 0

    _write_text(json_out, expected_json)
    _write_text(md_out, expected_md)
    summary = payload["summary"]
    assert isinstance(summary, dict)
    print(f"Wrote domain ports inventory JSON: {json_out}")
    print(f"Wrote domain ports inventory MD: {md_out}")
    print(
        "summary: "
        f"port_protocol_classes={summary['port_protocol_classes']} "
        f"runtime_checkable_port_count={summary['runtime_checkable_port_count']} "
        f"port_module_files={summary['port_module_files']} "
        f"scanned_python_files={summary['scanned_python_files']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
