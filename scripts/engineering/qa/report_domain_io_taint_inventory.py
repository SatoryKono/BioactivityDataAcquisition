#!/usr/bin/env python3
"""Generate a semantic Domain I/O taint inventory."""

from __future__ import annotations

import argparse
import ast
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DOMAIN_ROOT = PROJECT_ROOT / "src" / "bioetl" / "domain"
DEFAULT_JSON_OUTPUT = (
    PROJECT_ROOT / "reports" / "quality" / "domain-io-taint-inventory.json"
)

SCHEMA_BOUNDARY_PREFIXES = (
    "src/bioetl/domain/contracts/",
    "src/bioetl/domain/schemas/",
)
PANDERA_IMPORT_PREFIXES = ("pandera", "pandas")
_REASON_NETWORK_CLIENT = "network client"
_REASON_FILESYSTEM_DISCOVERY = "filesystem discovery"
_REASON_WALL_CLOCK = "wall-clock timestamp"
_REASON_CATALOG_RESOLVE = (
    "Catalog lookup method named resolve (not filesystem Path.resolve)."
)
_REASON_CATALOG_PATH = "src/bioetl/domain/run_reports/reason_catalog.py"
_MODULE_SCOPE = "<module>"

FORBIDDEN_IMPORT_PREFIXES = {
    "aiohttp": _REASON_NETWORK_CLIENT,
    "boto3": "external storage client",
    "botocore": "external storage client",
    "httpx": _REASON_NETWORK_CLIENT,
    "os": "process environment/filesystem",
    "requests": _REASON_NETWORK_CLIENT,
    "socket": "network socket",
    "sqlalchemy": "database client",
    "sqlite3": "database client",
    "subprocess": "process execution",
}
FORBIDDEN_CALL_NAMES = {
    "input": "interactive input",
    "open": "filesystem read/write",
}
FORBIDDEN_ATTRIBUTE_CALLS = {
    "connect": "database/network connection",
    "exists": "filesystem existence probe",
    "glob": _REASON_FILESYSTEM_DISCOVERY,
    "iterdir": _REASON_FILESYSTEM_DISCOVERY,
    "mkdir": "filesystem mutation",
    "open": "filesystem read/write",
    "read_bytes": "filesystem read",
    "read_text": "filesystem read",
    "resolve": "filesystem resolution",
    "rglob": _REASON_FILESYSTEM_DISCOVERY,
    "stat": "filesystem metadata read",
    "unlink": "filesystem mutation",
    "write_bytes": "filesystem write",
    "write_text": "filesystem write",
}
FORBIDDEN_QUALIFIED_CALLS = {
    "datetime.now": _REASON_WALL_CLOCK,
    "datetime.utcnow": _REASON_WALL_CLOCK,
    "os.getenv": "process environment read",
    "random.random": "randomness",
    "subprocess.run": "process execution",
    "time.time": _REASON_WALL_CLOCK,
    "uuid.uuid4": "random occurrence identity",
    "uuid4": "random occurrence identity",
}
ALLOWED_CALL_EXCEPTIONS = {
    ("src/bioetl/domain/context.py", "current_utc_time", "datetime.now"): (
        "Canonical DomainContext clock seam; production injection must override "
        "it for replay-sensitive flows."
    ),
    # run_reports: catalog method name `resolve` is not Path.resolve; YAML load is
    # a package-local reason map (bounded shipped asset), not general Domain I/O.
    (
        _REASON_CATALOG_PATH,
        "ReasonCatalog.family_for",
        "self.resolve",
    ): _REASON_CATALOG_RESOLVE,
    (
        _REASON_CATALOG_PATH,
        "ReasonCatalog.default_outcome_for",
        "self.resolve",
    ): _REASON_CATALOG_RESOLVE,
    (
        _REASON_CATALOG_PATH,
        "_read_yaml_mapping",
        "path.read_text",
    ): "Loads package-local run-report reason catalog YAML from an explicit Path.",
    (
        _REASON_CATALOG_PATH,
        "default_reason_catalog",
        "resolve",
    ): "Locates package-root relative reason catalog path candidates.",
    (
        "src/bioetl/domain/run_reports/accounting_snapshots.py",
        "StageAccountingSnapshotsMixin._removals_for_bucket",
        "self._catalog.resolve",
    ): _REASON_CATALOG_RESOLVE,
}


@dataclass(frozen=True, slots=True)
class TaintFinding:
    """One semantic taint finding or reviewed exception."""

    path: str
    line: int
    symbol: str
    kind: str
    reason: str


class _DomainIOTaintVisitor(ast.NodeVisitor):
    def __init__(self, relative_path: str) -> None:
        self.relative_path = relative_path
        self.scope: list[str] = []
        self.violations: list[TaintFinding] = []
        self.allowed_exceptions: list[TaintFinding] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.scope.append(node.name)
        self.generic_visit(node)
        self.scope.pop()

    def visit_Call(self, node: ast.Call) -> None:
        symbol = _qualified_name(node.func)
        owner = ".".join(self.scope) or _MODULE_SCOPE
        reason: str | None = None
        kind: str | None = None
        if isinstance(node.func, ast.Name):
            reason = FORBIDDEN_CALL_NAMES.get(node.func.id)
            kind = f"call:{node.func.id}" if reason else None
        if reason is None and symbol in FORBIDDEN_QUALIFIED_CALLS:
            reason = FORBIDDEN_QUALIFIED_CALLS[symbol]
            kind = f"call:{symbol}"
        if reason is None and isinstance(node.func, ast.Attribute):
            reason = FORBIDDEN_ATTRIBUTE_CALLS.get(node.func.attr)
            kind = f"attribute_call:{node.func.attr}" if reason else None

        if reason is not None and kind is not None:
            finding = TaintFinding(
                path=self.relative_path,
                line=node.lineno,
                symbol=owner,
                kind=kind,
                reason=reason,
            )
            exception_key = (self.relative_path, owner, symbol)
            if exception_key in ALLOWED_CALL_EXCEPTIONS:
                self.allowed_exceptions.append(
                    TaintFinding(
                        path=finding.path,
                        line=finding.line,
                        symbol=finding.symbol,
                        kind=finding.kind,
                        reason=ALLOWED_CALL_EXCEPTIONS[exception_key],
                    )
                )
            else:
                self.violations.append(finding)

        self.generic_visit(node)


def _qualified_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _qualified_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""


def _iter_domain_python_files(domain_root: Path = DOMAIN_ROOT) -> tuple[Path, ...]:
    return tuple(sorted(path for path in domain_root.rglob("*.py") if path.is_file()))


def _relative(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def _import_modules_from_node(node: ast.AST) -> list[str] | None:
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    if isinstance(node, ast.ImportFrom):
        return [node.module or ""]
    return None


def _pandera_import_finding(
    *,
    relative_path: str,
    line: int,
    root_module: str,
) -> tuple[TaintFinding, bool]:
    """Return (finding, is_allowed_exception)."""
    if relative_path.startswith(SCHEMA_BOUNDARY_PREFIXES):
        return (
            TaintFinding(
                path=relative_path,
                line=line,
                symbol=_MODULE_SCOPE,
                kind=f"import:{root_module}",
                reason=(
                    "Pandera/Pandas are allowed only inside machine-checkable "
                    "Domain contract/schema boundary modules."
                ),
            ),
            True,
        )
    return (
        TaintFinding(
            path=relative_path,
            line=line,
            symbol=_MODULE_SCOPE,
            kind=f"import:{root_module}",
            reason=(
                "Pandera/Pandas imports outside domain contracts/schemas "
                "would couple domain behavior to dataframe infrastructure."
            ),
        ),
        False,
    )


def _forbidden_import_finding(
    *,
    relative_path: str,
    line: int,
    root_module: str,
) -> TaintFinding | None:
    reason = FORBIDDEN_IMPORT_PREFIXES.get(root_module)
    if reason is None:
        return None
    return TaintFinding(
        path=relative_path,
        line=line,
        symbol=_MODULE_SCOPE,
        kind=f"import:{root_module}",
        reason=reason,
    )


def _classify_import_module(
    *,
    relative_path: str,
    line: int,
    root_module: str,
    violations: list[TaintFinding],
    allowed_exceptions: list[TaintFinding],
) -> None:
    if root_module in PANDERA_IMPORT_PREFIXES:
        finding, allowed = _pandera_import_finding(
            relative_path=relative_path,
            line=line,
            root_module=root_module,
        )
        if allowed:
            allowed_exceptions.append(finding)
        else:
            violations.append(finding)
        return
    forbidden = _forbidden_import_finding(
        relative_path=relative_path,
        line=line,
        root_module=root_module,
    )
    if forbidden is not None:
        violations.append(forbidden)


def _scan_imports(
    path: Path, tree: ast.AST
) -> tuple[list[TaintFinding], list[TaintFinding]]:
    relative_path = _relative(path)
    violations: list[TaintFinding] = []
    allowed_exceptions: list[TaintFinding] = []
    for node in ast.walk(tree):
        modules = _import_modules_from_node(node)
        if modules is None:
            continue
        for module in modules:
            _classify_import_module(
                relative_path=relative_path,
                line=node.lineno,
                root_module=module.split(".", maxsplit=1)[0],
                violations=violations,
                allowed_exceptions=allowed_exceptions,
            )
    return violations, allowed_exceptions


def build_payload(repo_root: Path = PROJECT_ROOT) -> dict[str, object]:
    domain_root = repo_root / "src" / "bioetl" / "domain"
    violations: list[TaintFinding] = []
    allowed_exceptions: list[TaintFinding] = []
    scanned_files = _iter_domain_python_files(domain_root)
    for path in scanned_files:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        import_violations, import_exceptions = _scan_imports(path, tree)
        visitor = _DomainIOTaintVisitor(_relative(path))
        visitor.visit(tree)
        violations.extend(import_violations)
        violations.extend(visitor.violations)
        allowed_exceptions.extend(import_exceptions)
        allowed_exceptions.extend(visitor.allowed_exceptions)

    violations.sort(key=lambda finding: (finding.path, finding.line, finding.kind))
    allowed_exceptions.sort(
        key=lambda finding: (finding.path, finding.line, finding.kind)
    )
    return {
        "schema_version": 1,
        "generated_by": "scripts.engineering.qa.report_domain_io_taint_inventory",
        "domain_root": "src/bioetl/domain",
        "scanned_file_count": len(scanned_files),
        "violation_count": len(violations),
        "allowed_exception_count": len(allowed_exceptions),
        "violations": [asdict(finding) for finding in violations],
        "allowed_exceptions": [asdict(finding) for finding in allowed_exceptions],
    }


def _write_json(
    path: Path, payload: dict[str, object], *, root: Path | None = None
) -> None:
    from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_output_path

    path = resolve_output_path(path, root=root or REPO_ROOT)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    repo_root = args.repo_root.resolve()
    payload = build_payload(repo_root)
    output_path = args.json_out
    if not output_path.is_absolute():
        output_path = repo_root / output_path

    if args.check:
        expected = json.dumps(payload, indent=2, sort_keys=True) + "\n"
        if not output_path.exists():
            print(f"Missing Domain I/O taint inventory: {output_path}", file=sys.stderr)
            return 1
        actual = output_path.read_text(encoding="utf-8")
        if actual != expected:
            print(
                "Domain I/O taint inventory is stale. Regenerate with:\n"
                "  python -m scripts.engineering.qa report-domain-io-taint-inventory",
                file=sys.stderr,
            )
            return 1
        return 0

    _write_json(output_path, payload)
    print(f"Wrote Domain I/O taint inventory: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
