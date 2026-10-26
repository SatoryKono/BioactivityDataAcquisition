#!/usr/bin/env python3
"""Generate a semantic Domain I/O taint inventory.

The operation norm lives in ``docs/02-architecture/01-domain-layer.md`` §3.
This module enforces that norm for CI. It does not define a second policy.

Pure ``urllib.parse`` calls and ``PurePath`` / path-value operations are not
domain I/O. Filesystem and network calls are. ``os``, ``pathlib``, and
``urllib`` are not banned as imports.

Static boundary (not interprocedural taint):

- Import bindings and their aliases are resolved inside one module.
- A direct assignment of a ``Path`` / ``PurePath`` constructor, class, or
  ``/`` join is visible for the whole enclosing function or module scope.
- Parameters, closures, star imports, tuple unpacking, and arbitrary
  ``name = forbidden_callable`` aliases are not resolved.
- ``loader.exec_module(...)`` is reported only when the receiver resolves
  through an ``importlib`` binding.
- A call is not I/O only because its attribute name matches a Path or
  network method.
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from collections.abc import Sequence
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
_REASON_NETWORK_READ = "network read"
_REASON_FILESYSTEM_DISCOVERY = "filesystem discovery"
_REASON_WALL_CLOCK = "wall-clock timestamp"
_MODULE_SCOPE = "<module>"
_REASON_FILESYSTEM_MODULE = "filesystem module load bypassing the import graph"
_KIND_LOCAL = "local"
_KIND_INSTANCE = "instance"

FORBIDDEN_IMPORT_PREFIXES = {
    "aiohttp": _REASON_NETWORK_CLIENT,
    "boto3": "external storage client",
    "botocore": "external storage client",
    "httpx": _REASON_NETWORK_CLIENT,
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
# Path methods already enforced by name. Applied only when the receiver
# resolves to pathlib.Path / PosixPath / WindowsPath, not to PurePath.
FORBIDDEN_ATTRIBUTE_CALLS = {
    "connect": "database/network connection",
    "exec_module": _REASON_FILESYSTEM_MODULE,
    "exists": "filesystem existence probe",
    "glob": _REASON_FILESYSTEM_DISCOVERY,
    "iterdir": _REASON_FILESYSTEM_DISCOVERY,
    "mkdir": "filesystem mutation",
    "module_from_spec": _REASON_FILESYSTEM_MODULE,
    "open": "filesystem read/write",
    "read_bytes": "filesystem read",
    "read_text": "filesystem read",
    "resolve": "filesystem resolution",
    "rglob": _REASON_FILESYSTEM_DISCOVERY,
    "spec_from_file_location": _REASON_FILESYSTEM_MODULE,
    "stat": "filesystem metadata read",
    "unlink": "filesystem mutation",
    "write_bytes": "filesystem write",
    "write_text": "filesystem write",
}
# Source-text keys kept for calls the binding resolver does not rename,
# including the bare ``uuid4()`` alias and ``datetime.now()``.
FORBIDDEN_QUALIFIED_CALLS = {
    "datetime.now": _REASON_WALL_CLOCK,
    "datetime.utcnow": _REASON_WALL_CLOCK,
    "importlib.util.module_from_spec": _REASON_FILESYSTEM_MODULE,
    "importlib.util.spec_from_file_location": _REASON_FILESYSTEM_MODULE,
    "os.getenv": "process environment read",
    "random.random": "randomness",
    "subprocess.run": "process execution",
    "time.time": _REASON_WALL_CLOCK,
    "uuid.uuid4": "random occurrence identity",
    "uuid4": "random occurrence identity",
}
# Canonical symbols after import resolution. ``os.*`` entries are the
# side-effect operations already named by the domain purity check and this
# scanner (read/write/mkdir/remove/rename, plus getenv/open/stat/unlink/exists).
_FORBIDDEN_RESOLVED_CALLS = {
    "datetime.datetime.now": _REASON_WALL_CLOCK,
    "datetime.datetime.utcnow": _REASON_WALL_CLOCK,
    "glob.glob": _REASON_FILESYSTEM_DISCOVERY,
    "importlib.util.module_from_spec": _REASON_FILESYSTEM_MODULE,
    "importlib.util.spec_from_file_location": _REASON_FILESYSTEM_MODULE,
    "os.getenv": "process environment read",
    "os.mkdir": "filesystem mutation",
    "os.open": "filesystem read/write",
    "os.path.exists": "filesystem existence probe",
    "os.read": "filesystem read",
    "os.remove": "filesystem mutation",
    "os.rename": "filesystem mutation",
    "os.stat": "filesystem metadata read",
    "os.unlink": "filesystem mutation",
    "os.write": "filesystem write",
    "random.random": "randomness",
    "sqlite3.connect": "database/network connection",
    "subprocess.run": "process execution",
    "time.time": _REASON_WALL_CLOCK,
    "urllib.request.urlopen": _REASON_NETWORK_READ,
    "uuid.uuid4": "random occurrence identity",
}
_PATH_IO_TYPES = frozenset(
    {
        "pathlib.Path",
        "pathlib.PosixPath",
        "pathlib.WindowsPath",
    }
)
_PURE_PATH_TYPES = frozenset(
    {
        "pathlib.PurePath",
        "pathlib.PurePosixPath",
        "pathlib.PureWindowsPath",
    }
)
_PATH_VALUE_TYPES = _PATH_IO_TYPES | _PURE_PATH_TYPES
_IMPORTLIB_RECEIVERS = frozenset({"importlib", "importlib.util"})
ALLOWED_CALL_EXCEPTIONS = {
    ("src/bioetl/domain/context.py", "current_utc_time", "datetime.now"): (
        "Canonical DomainContext clock seam; production injection must override "
        "it for replay-sensitive flows."
    ),
}


@dataclass(frozen=True, slots=True)
class TaintFinding:
    """One semantic taint finding or reviewed exception."""

    path: str
    line: int
    symbol: str
    kind: str
    reason: str


@dataclass(frozen=True, slots=True)
class _Binding:
    """One name bound to a module, symbol, instance type, or local."""

    kind: str
    target: str


@dataclass
class _Scope:
    names: dict[str, _Binding]
    parent: _Scope | None = None


@dataclass
class _Bindings:
    module: _Scope
    scopes: dict[int, _Scope]


def _module_scope(scope: _Scope) -> _Scope:
    current = scope
    while current.parent is not None:
        current = current.parent
    return current


def _lookup(scope: _Scope, name: str) -> _Binding | None:
    current: _Scope | None = scope
    while current is not None:
        found = current.names.get(name)
        if found is not None:
            return found
        current = current.parent
    return None


def _bind_import(scope: _Scope, node: ast.Import) -> None:
    for alias in node.names:
        if alias.asname:
            scope.names[alias.asname] = _Binding("module", alias.name)
            continue
        root = alias.name.split(".", maxsplit=1)[0]
        scope.names[root] = _Binding("module", root)


def _bind_import_from(scope: _Scope, node: ast.ImportFrom) -> None:
    module = node.module or ""
    for alias in node.names:
        if alias.name == "*":
            continue
        local = alias.asname or alias.name
        target = f"{module}.{alias.name}" if module else alias.name
        scope.names[local] = _Binding("symbol", target)


def _bind_assigned_name(scope: _Scope, name: str, expr: ast.AST | None) -> None:
    if expr is not None:
        symbol = _canonical_symbol(expr, scope)
        if symbol in _PATH_VALUE_TYPES:
            scope.names[name] = _Binding(_KIND_INSTANCE, symbol)
            return
    scope.names[name] = _Binding(_KIND_LOCAL, name)


def _bind_assign(scope: _Scope, node: ast.Assign) -> None:
    if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
        _bind_assigned_name(scope, node.targets[0].id, node.value)
        return
    for target in node.targets:
        elements = (
            target.elts if isinstance(target, ast.Tuple | ast.List) else (target,)
        )
        for element in elements:
            if isinstance(element, ast.Name):
                scope.names[element.id] = _Binding(_KIND_LOCAL, element.id)


def _bind_ann_assign(scope: _Scope, node: ast.AnnAssign) -> None:
    if isinstance(node.target, ast.Name):
        _bind_assigned_name(scope, node.target.id, node.value)


def _canonical_symbol(expr: ast.AST, scope: _Scope) -> str | None:
    if isinstance(expr, ast.Name):
        binding = _lookup(scope, expr.id)
        if binding is None or binding.kind == _KIND_LOCAL:
            return None
        return binding.target
    if isinstance(expr, ast.Attribute):
        base = _canonical_symbol(expr.value, scope)
        if base is None:
            return None
        return f"{base}.{expr.attr}"
    if isinstance(expr, ast.Call):
        callee = _canonical_symbol(expr.func, scope)
        if callee in _PATH_VALUE_TYPES:
            return callee
        return None
    if isinstance(expr, ast.BinOp):
        left = _canonical_symbol(expr.left, scope)
        if left in _PATH_VALUE_TYPES:
            return left
    return None


def _collect_body(scope: _Scope, bindings: _Bindings, body: Sequence[ast.stmt]) -> None:
    for stmt in body:
        _collect_stmt(scope, bindings, stmt)


def _collect_function(scope: _Scope, bindings: _Bindings, node: ast.stmt) -> None:
    if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
        return
    scope.names[node.name] = _Binding(_KIND_LOCAL, node.name)
    function_scope = _Scope(names={}, parent=_module_scope(scope))
    bindings.scopes[id(node)] = function_scope
    _collect_body(function_scope, bindings, node.body)


def _collect_class(scope: _Scope, bindings: _Bindings, node: ast.stmt) -> None:
    if not isinstance(node, ast.ClassDef):
        return
    scope.names[node.name] = _Binding(_KIND_LOCAL, node.name)
    class_scope = _Scope(names={}, parent=_module_scope(scope))
    bindings.scopes[id(node)] = class_scope
    _collect_body(class_scope, bindings, node.body)


def _collect_same_scope(
    scope: _Scope,
    bindings: _Bindings,
    bodies: Sequence[Sequence[ast.stmt]],
) -> None:
    for body in bodies:
        _collect_body(scope, bindings, body)


def _collect_import(scope: _Scope, bindings: _Bindings, node: ast.stmt) -> None:
    del bindings
    if isinstance(node, ast.Import):
        _bind_import(scope, node)


def _collect_import_from(scope: _Scope, bindings: _Bindings, node: ast.stmt) -> None:
    del bindings
    if isinstance(node, ast.ImportFrom):
        _bind_import_from(scope, node)


def _collect_assign(scope: _Scope, bindings: _Bindings, node: ast.stmt) -> None:
    del bindings
    if isinstance(node, ast.Assign):
        _bind_assign(scope, node)


def _collect_ann_assign(scope: _Scope, bindings: _Bindings, node: ast.stmt) -> None:
    del bindings
    if isinstance(node, ast.AnnAssign):
        _bind_ann_assign(scope, node)


def _collect_if(scope: _Scope, bindings: _Bindings, node: ast.stmt) -> None:
    if isinstance(node, ast.If):
        _collect_same_scope(scope, bindings, (node.body, node.orelse))


def _collect_loop(scope: _Scope, bindings: _Bindings, node: ast.stmt) -> None:
    if isinstance(node, ast.For | ast.AsyncFor | ast.While):
        _collect_same_scope(scope, bindings, (node.body, node.orelse))


def _collect_with(scope: _Scope, bindings: _Bindings, node: ast.stmt) -> None:
    if isinstance(node, ast.With | ast.AsyncWith):
        _collect_body(scope, bindings, node.body)


def _collect_try(scope: _Scope, bindings: _Bindings, node: ast.stmt) -> None:
    if not isinstance(node, ast.Try):
        return
    handler_bodies = tuple(handler.body for handler in node.handlers)
    _collect_same_scope(
        scope,
        bindings,
        (node.body, *handler_bodies, node.orelse, node.finalbody),
    )


def _collect_match(scope: _Scope, bindings: _Bindings, node: ast.stmt) -> None:
    if isinstance(node, ast.Match):
        _collect_same_scope(scope, bindings, tuple(case.body for case in node.cases))


_STMT_COLLECTORS = {
    ast.Import: _collect_import,
    ast.ImportFrom: _collect_import_from,
    ast.Assign: _collect_assign,
    ast.AnnAssign: _collect_ann_assign,
    ast.FunctionDef: _collect_function,
    ast.AsyncFunctionDef: _collect_function,
    ast.ClassDef: _collect_class,
    ast.If: _collect_if,
    ast.For: _collect_loop,
    ast.AsyncFor: _collect_loop,
    ast.While: _collect_loop,
    ast.With: _collect_with,
    ast.AsyncWith: _collect_with,
    ast.Try: _collect_try,
    ast.Match: _collect_match,
}


def _collect_stmt(scope: _Scope, bindings: _Bindings, stmt: ast.stmt) -> None:
    collector = _STMT_COLLECTORS.get(type(stmt))
    if collector is not None:
        collector(scope, bindings, stmt)


def _collect_bindings(tree: ast.AST) -> _Bindings:
    module = _Scope(names={})
    bindings = _Bindings(module=module, scopes={})
    body = tree.body if isinstance(tree, ast.Module) else ()
    _collect_body(module, bindings, body)
    return bindings


def _path_io_finding(symbol: str) -> tuple[str, str] | None:
    for prefix in _PATH_IO_TYPES:
        head = f"{prefix}."
        if not symbol.startswith(head):
            continue
        method = symbol[len(head) :]
        if "." in method:
            return None
        reason = FORBIDDEN_ATTRIBUTE_CALLS.get(method)
        if reason is None and method.startswith("read_"):
            reason = "filesystem read"
        elif reason is None and method.startswith("write_"):
            reason = "filesystem write"
        if reason is None:
            return None
        return f"attribute_call:{method}", reason
    return None


def _importlib_method_finding(symbol: str) -> tuple[str, str] | None:
    method = symbol.rsplit(".", maxsplit=1)[-1]
    receiver = symbol[: -(len(method) + 1)] if "." in symbol else ""
    if method not in {"exec_module", "module_from_spec", "spec_from_file_location"}:
        return None
    if receiver not in _IMPORTLIB_RECEIVERS and not receiver.startswith("importlib."):
        return None
    reason = FORBIDDEN_ATTRIBUTE_CALLS.get(method, _REASON_FILESYSTEM_MODULE)
    return f"attribute_call:{method}", reason


def _bare_name_finding(func: ast.Name, scope: _Scope) -> tuple[str, str] | None:
    binding = _lookup(scope, func.id)
    if binding is not None and binding.kind == _KIND_LOCAL:
        return None
    if binding is not None:
        return None
    reason = FORBIDDEN_CALL_NAMES.get(func.id)
    if reason is None:
        reason = FORBIDDEN_QUALIFIED_CALLS.get(func.id)
    if reason is None:
        return None
    return f"call:{func.id}", reason


def _call_match(func: ast.AST, scope: _Scope) -> tuple[str, str] | None:
    symbol = _canonical_symbol(func, scope)
    if symbol is not None:
        reason = _FORBIDDEN_RESOLVED_CALLS.get(symbol)
        if reason is not None:
            return f"call:{symbol}", reason
        path_finding = _path_io_finding(symbol)
        if path_finding is not None:
            return path_finding
        importlib_finding = _importlib_method_finding(symbol)
        if importlib_finding is not None:
            return importlib_finding
    if isinstance(func, ast.Name):
        return _bare_name_finding(func, scope)
    qualified = _qualified_name(func)
    reason = FORBIDDEN_QUALIFIED_CALLS.get(qualified)
    if reason is None:
        return None
    return f"call:{qualified}", reason


class _DomainIOTaintVisitor(ast.NodeVisitor):
    def __init__(self, relative_path: str, bindings: _Bindings) -> None:
        self.relative_path = relative_path
        self._bindings = bindings
        self._binding_scope = bindings.module
        self.scope: list[str] = []
        self.violations: list[TaintFinding] = []
        self.allowed_exceptions: list[TaintFinding] = []

    def _visit_scoped(self, node: ast.AST, name: str) -> None:
        self.scope.append(name)
        previous = self._binding_scope
        self._binding_scope = self._bindings.scopes.get(id(node), previous)
        self.generic_visit(node)
        self._binding_scope = previous
        self.scope.pop()

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._visit_scoped(node, node.name)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_scoped(node, node.name)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_scoped(node, node.name)

    def visit_Call(self, node: ast.Call) -> None:
        matched = _call_match(node.func, self._binding_scope)
        if matched is not None:
            self._record_call(node, matched[0], matched[1])
        self.generic_visit(node)

    def _record_call(self, node: ast.Call, kind: str, reason: str) -> None:
        owner = ".".join(self.scope) or _MODULE_SCOPE
        source_symbol = _qualified_name(node.func)
        finding = TaintFinding(
            path=self.relative_path,
            line=getattr(node, "lineno", 0),
            symbol=owner,
            kind=kind,
            reason=reason,
        )
        exception_key = (self.relative_path, owner, source_symbol)
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
            return
        self.violations.append(finding)


def _qualified_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _qualified_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""


def _iter_domain_python_files(domain_root: Path = DOMAIN_ROOT) -> tuple[Path, ...]:
    return tuple(sorted(path for path in domain_root.rglob("*.py") if path.is_file()))


def _relative(path: Path, *, root: Path) -> str:
    return path.relative_to(root).as_posix()


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


def _append_import_finding(
    finding: TaintFinding,
    *,
    allowed: bool,
    violations: list[TaintFinding],
    allowed_exceptions: list[TaintFinding],
) -> None:
    if allowed:
        allowed_exceptions.append(finding)
    else:
        violations.append(finding)


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
        _append_import_finding(
            finding,
            allowed=allowed,
            violations=violations,
            allowed_exceptions=allowed_exceptions,
        )
        return
    forbidden = _forbidden_import_finding(
        relative_path=relative_path,
        line=line,
        root_module=root_module,
    )
    if forbidden is not None:
        violations.append(forbidden)


def _scan_imports(
    relative_path: str,
    tree: ast.AST,
) -> tuple[list[TaintFinding], list[TaintFinding]]:
    violations: list[TaintFinding] = []
    allowed_exceptions: list[TaintFinding] = []
    for node in ast.walk(tree):
        modules = _import_modules_from_node(node)
        if modules is None:
            continue
        for module in modules:
            _classify_import_module(
                relative_path=relative_path,
                line=getattr(node, "lineno", 0),
                root_module=module.split(".", maxsplit=1)[0],
                violations=violations,
                allowed_exceptions=allowed_exceptions,
            )
    return violations, allowed_exceptions


def _finding_sort_key(finding: TaintFinding) -> tuple[str, int, str]:
    return (finding.path, finding.line, finding.kind)


def analyze_tree(
    tree: ast.AST,
    *,
    relative_path: str,
) -> tuple[list[TaintFinding], list[TaintFinding]]:
    """Return violations and reviewed exceptions for one parsed module."""
    violations, allowed_exceptions = _scan_imports(relative_path, tree)
    visitor = _DomainIOTaintVisitor(relative_path, _collect_bindings(tree))
    visitor.visit(tree)
    violations.extend(visitor.violations)
    allowed_exceptions.extend(visitor.allowed_exceptions)
    violations.sort(key=_finding_sort_key)
    allowed_exceptions.sort(key=_finding_sort_key)
    return violations, allowed_exceptions


def scan_domain_source(
    source: str,
    *,
    relative_path: str,
) -> tuple[tuple[TaintFinding, ...], tuple[TaintFinding, ...]]:
    """Parse synthetic source and return findings. Does not execute it."""
    tree = ast.parse(source)
    violations, allowed_exceptions = analyze_tree(tree, relative_path=relative_path)
    return tuple(violations), tuple(allowed_exceptions)


def build_payload(repo_root: Path = PROJECT_ROOT) -> dict[str, object]:
    domain_root = repo_root / "src" / "bioetl" / "domain"
    violations: list[TaintFinding] = []
    allowed_exceptions: list[TaintFinding] = []
    scanned_files = _iter_domain_python_files(domain_root)
    root = repo_root.resolve()
    for path in scanned_files:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        file_violations, file_exceptions = analyze_tree(
            tree,
            relative_path=_relative(path, root=root),
        )
        violations.extend(file_violations)
        allowed_exceptions.extend(file_exceptions)

    violations.sort(key=_finding_sort_key)
    allowed_exceptions.sort(key=_finding_sort_key)
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
