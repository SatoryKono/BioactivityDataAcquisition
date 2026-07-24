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
FORBIDDEN_IMPORT_PREFIXES = {
    "aiohttp": "network client",
    "boto3": "external storage client",
    "botocore": "external storage client",
    "httpx": "network client",
    "os": "process environment/filesystem",
    "requests": "network client",
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
    "glob": "filesystem discovery",
    "iterdir": "filesystem discovery",
    "mkdir": "filesystem mutation",
    "open": "filesystem read/write",
    "read_bytes": "filesystem read",
    "read_text": "filesystem read",
    "resolve": "filesystem resolution",
    "rglob": "filesystem discovery",
    "stat": "filesystem metadata read",
    "unlink": "filesystem mutation",
    "write_bytes": "filesystem write",
    "write_text": "filesystem write",
}
FORBIDDEN_QUALIFIED_CALLS = {
    "datetime.now": "wall-clock timestamp",
    "datetime.utcnow": "wall-clock timestamp",
    "os.getenv": "process environment read",
    "random.random": "randomness",
    "subprocess.run": "process execution",
    "time.time": "wall-clock timestamp",
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
        "src/bioetl/domain/run_reports/reason_catalog.py",
        "ReasonCatalog.family_for",
        "self.resolve",
    ): "Catalog lookup method named resolve (not filesystem Path.resolve).",
    (
        "src/bioetl/domain/run_reports/reason_catalog.py",
        "ReasonCatalog.default_outcome_for",
        "self.resolve",
    ): "Catalog lookup method named resolve (not filesystem Path.resolve).",
    (
        "src/bioetl/domain/run_reports/reason_catalog.py",
        "_read_yaml_mapping",
        "path.read_text",
    ): "Loads package-local run-report reason catalog YAML from an explicit Path.",
    (
        "src/bioetl/domain/run_reports/reason_catalog.py",
        "default_reason_catalog",
        "resolve",
    ): "Locates package-root relative reason catalog path candidates.",
    (
        "src/bioetl/domain/run_reports/accounting_snapshots.py",
        "StageAccountingSnapshotsMixin._removals_for_bucket",
        "self._catalog.resolve",
    ): "Catalog lookup method named resolve (not filesystem Path.resolve).",
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
        owner = ".".join(self.scope) or "<module>"
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


def _scan_imports(
    path: Path, tree: ast.AST
) -> tuple[list[TaintFinding], list[TaintFinding]]:
    relative_path = _relative(path)
    violations: list[TaintFinding] = []
    allowed_exceptions: list[TaintFinding] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            modules = [node.module or ""]
        else:
            continue

        for module in modules:
            root_module = module.split(".", maxsplit=1)[0]
            if root_module in PANDERA_IMPORT_PREFIXES:
                if relative_path.startswith(SCHEMA_BOUNDARY_PREFIXES):
                    allowed_exceptions.append(
                        TaintFinding(
                            path=relative_path,
                            line=node.lineno,
                            symbol="<module>",
                            kind=f"import:{root_module}",
                            reason=(
                                "Pandera/Pandas are allowed only inside machine-checkable "
                                "Domain contract/schema boundary modules."
                            ),
                        )
                    )
                else:
                    violations.append(
                        TaintFinding(
                            path=relative_path,
                            line=node.lineno,
                            symbol="<module>",
                            kind=f"import:{root_module}",
                            reason=(
                                "Pandera/Pandas imports outside domain contracts/schemas "
                                "would couple domain behavior to dataframe infrastructure."
                            ),
                        )
                    )
                continue

            for forbidden_prefix, reason in FORBIDDEN_IMPORT_PREFIXES.items():
                if root_module == forbidden_prefix:
                    violations.append(
                        TaintFinding(
                            path=relative_path,
                            line=node.lineno,
                            symbol="<module>",
                            kind=f"import:{root_module}",
                            reason=reason,
                        )
                    )
                    break
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
