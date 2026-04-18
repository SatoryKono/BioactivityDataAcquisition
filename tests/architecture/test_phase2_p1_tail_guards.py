"""Phase 2 guards for architecture P1 tails."""

from __future__ import annotations

import ast
from pathlib import Path


CRITICAL_MODULES = ("src/bioetl/infrastructure/adapters/uniprot/idmapping_client.py",)
ALLOWED_BROAD_EXCEPTION_POLICIES: dict[str, frozenset[str]] = {
    # Legacy/runtime utility seams that still centralize broad exception handling.
    # Empty reason-code sets mean "tracked exception site" rather than
    # "CLI fallback handler that must carry reason_code markers".
    "src/bioetl/application/services/error_handler.py": frozenset(),
    "src/bioetl/infrastructure/storage/silver_writer.py": frozenset(),
    "src/bioetl/infrastructure/storage/silver/support.py": frozenset(),
    "src/bioetl/infrastructure/storage/silver/operations/maintenance_operations.py": frozenset(),
    "src/bioetl/interfaces/cli/commands/domains/run/command.py": frozenset(),
}
P0_2_CRITICAL_ERROR_MODULES = (
    "src/bioetl/application/core/batch_executor.py",
    "src/bioetl/application/core/postrun/cleanup_orchestrator.py",
    "src/bioetl/application/core/postrun/dq_report_orchestrator.py",
    "src/bioetl/application/core/postrun/metadata_version_resolver.py",
    "src/bioetl/application/composite/runner_pkg/runner.py",
    "src/bioetl/interfaces/http/health_server.py",
    "src/bioetl/interfaces/http/health_server_http_mixin.py",
)
P0_2_REASON_CODE_MIN_COVERAGE = 0.95


def _load_tree(path: str) -> ast.AST:
    """Load Python AST for a file path."""
    source = Path(path).read_text(encoding="utf-8")
    return ast.parse(source, filename=path)


def _has_exception_name(node: ast.expr) -> bool:
    """Return True when expression includes Exception type."""
    if isinstance(node, ast.Name):
        return node.id == "Exception"
    if isinstance(node, ast.Tuple):
        return any(_has_exception_name(element) for element in node.elts)
    return False


def _has_bioetl_error_name(node: ast.expr) -> bool:
    """Return True when expression includes BioETLError type."""
    if isinstance(node, ast.Name):
        return node.id == "BioETLError"
    if isinstance(node, ast.Tuple):
        return any(_has_bioetl_error_name(element) for element in node.elts)
    return False


def test_critical_modules_have_no_broad_exception_handlers() -> None:
    """Critical modules should not use except Exception or bare except."""
    violations: list[str] = []
    for path in CRITICAL_MODULES:
        tree = _load_tree(path)
        for node in ast.walk(tree):
            if not isinstance(node, ast.ExceptHandler):
                continue
            if node.type is None:
                violations.append(f"{path}:{node.lineno} uses bare except")
                continue
            if _has_exception_name(node.type):
                violations.append(f"{path}:{node.lineno} catches Exception")

    assert not violations, "Broad exception handlers found:\n" + "\n".join(violations)


def test_broad_exception_handlers_are_limited_to_cli_entrypoints() -> None:
    """Allow `except Exception` only in top-level CLI entrypoints with guard rails."""
    violations: list[str] = []
    seen_reason_codes: dict[str, set[str]] = {
        file_path: set() for file_path in ALLOWED_BROAD_EXCEPTION_POLICIES
    }

    for file_path in Path("src/bioetl").rglob("*.py"):
        rel_path = str(file_path).replace("\\", "/")
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=rel_path)

        for node in ast.walk(tree):
            if not isinstance(node, ast.Try):
                continue

            for index, handler in enumerate(node.handlers):
                if handler.type is None:
                    violations.append(f"{rel_path}:{handler.lineno} uses bare except")
                    continue
                if not _has_exception_name(handler.type):
                    continue

                allowed_reason_codes = ALLOWED_BROAD_EXCEPTION_POLICIES.get(rel_path)
                if allowed_reason_codes is None:
                    violations.append(
                        f"{rel_path}:{handler.lineno} catches Exception outside CLI allowlist"
                    )
                    continue

                if allowed_reason_codes:
                    has_bioetl_before = any(
                        h.type is not None and _has_bioetl_error_name(h.type)
                        for h in node.handlers[:index]
                    )
                    if not has_bioetl_before:
                        violations.append(
                            f"{rel_path}:{handler.lineno} missing preceding except BioETLError"
                        )

                    handler_source = ast.get_source_segment(source, handler) or ""
                    if "reason_code=" not in handler_source:
                        violations.append(
                            f"{rel_path}:{handler.lineno} missing reason_code in fallback handler"
                        )
                        continue

                    matched_reason_codes = {
                        code for code in allowed_reason_codes if code in handler_source
                    }
                    if not matched_reason_codes:
                        violations.append(
                            f"{rel_path}:{handler.lineno} reason_code not in allowlist "
                            f"{sorted(allowed_reason_codes)}"
                        )
                        continue

                    seen_reason_codes[rel_path].update(matched_reason_codes)

    for rel_path, allowed_reason_codes in ALLOWED_BROAD_EXCEPTION_POLICIES.items():
        missing = allowed_reason_codes - seen_reason_codes[rel_path]
        if missing:
            violations.append(
                f"{rel_path} missing broad-exception handlers for {sorted(missing)}"
            )
        unexpected = seen_reason_codes[rel_path] - allowed_reason_codes
        if unexpected:
            violations.append(
                f"{rel_path} has unexpected broad-exception reason_code values "
                f"{sorted(unexpected)}"
            )

    assert not violations, "Broad exception policy violations:\n" + "\n".join(
        violations
    )


_BIOETL_ERROR_NAMES = frozenset(
    {"BioETLError", "CriticalError", "RecoverableError", "DataQualityError"}
)


def _is_bioetl_error_handler(handler: ast.ExceptHandler) -> bool:
    """Return True when handler catches BioETLError or a known subclass."""
    if handler.type is None:
        return False
    if isinstance(handler.type, ast.Name):
        return handler.type.id in _BIOETL_ERROR_NAMES
    if isinstance(handler.type, ast.Tuple):
        return any(
            isinstance(elt, ast.Name) and elt.id in _BIOETL_ERROR_NAMES
            for elt in handler.type.elts
        )
    return False


def _handler_has_logger_call(handler: ast.ExceptHandler) -> bool:
    """Return True when handler body contains self._logger.* calls."""
    for node in ast.walk(handler):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            value = node.func.value
            if (
                isinstance(value, ast.Attribute)
                and isinstance(value.value, ast.Name)
                and value.value.id == "self"
                and value.attr == "_logger"
            ):
                return True
    return False


def _handler_has_reason_code(handler: ast.ExceptHandler) -> bool:
    """Return True when handler body contains reason_code= keyword arg."""
    for node in ast.walk(handler):
        if isinstance(node, ast.keyword) and node.arg == "reason_code":
            return True
    return False


def _is_structured_error_call(call: ast.Call) -> bool:
    """Return True when call is a structured error sink in handler body."""
    if isinstance(call.func, ast.Name):
        return call.func.id in {"handle_cli_failure", "render_exception"}
    if isinstance(call.func, ast.Attribute):
        method_name = call.func.attr
        if method_name in {"error", "warning", "exception", "critical"}:
            receiver = call.func.value
            if (
                isinstance(receiver, ast.Attribute)
                and isinstance(receiver.value, ast.Name)
                and receiver.value.id == "self"
                and receiver.attr == "_logger"
            ):
                return True
            if isinstance(receiver, ast.Name) and receiver.id in {
                "logger",
                "_logger",
            }:
                return True
    return False


def _handler_has_structured_error_call(handler: ast.ExceptHandler) -> bool:
    """Return True when handler emits structured error/warning output."""
    for node in ast.walk(handler):
        if isinstance(node, ast.Call) and _is_structured_error_call(node):
            return True
    return False


def test_application_bioetl_error_handlers_have_reason_code() -> None:
    """All except BioETLError handlers that log must include reason_code."""
    violations: list[str] = []

    for file_path in Path("src/bioetl/application").rglob("*.py"):
        rel_path = str(file_path).replace("\\", "/")
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=rel_path)

        for node in ast.walk(tree):
            if not isinstance(node, ast.ExceptHandler):
                continue
            if not _is_bioetl_error_handler(node):
                continue
            if not _handler_has_logger_call(node):
                continue
            if not _handler_has_reason_code(node):
                violations.append(
                    f"{rel_path}:{node.lineno} except BioETLError with logging "
                    f"but no reason_code="
                )

    assert not violations, (
        "Application-layer BioETLError handlers missing reason_code:\n"
        + "\n".join(violations)
    )


def test_p0_2_critical_modules_have_no_broad_exception_handlers() -> None:
    """P0-2 critical paths must avoid broad catch in non-entrypoint layers."""
    violations: list[str] = []
    for path in P0_2_CRITICAL_ERROR_MODULES:
        tree = _load_tree(path)
        for node in ast.walk(tree):
            if not isinstance(node, ast.ExceptHandler):
                continue
            if node.type is None:
                violations.append(f"{path}:{node.lineno} uses bare except")
                continue
            if _has_exception_name(node.type):
                violations.append(f"{path}:{node.lineno} catches Exception")

    assert not violations, (
        "Broad exception handlers found in P0-2 critical modules:\n"
        + "\n".join(violations)
    )


def test_p0_2_reason_code_coverage_on_critical_paths() -> None:
    """P0-2: structured handlers in critical paths must carry reason_code >=95%."""
    covered = 0
    total = 0
    missing: list[str] = []

    for path in P0_2_CRITICAL_ERROR_MODULES:
        tree = _load_tree(path)
        for node in ast.walk(tree):
            if not isinstance(node, ast.ExceptHandler):
                continue
            if not _handler_has_structured_error_call(node):
                continue
            total += 1
            if _handler_has_reason_code(node):
                covered += 1
            else:
                missing.append(f"{path}:{node.lineno}")

    assert total > 0, "No structured exception handlers found in critical modules"

    coverage = covered / total
    assert coverage >= P0_2_REASON_CODE_MIN_COVERAGE, (
        f"reason_code coverage in critical modules is {coverage:.2%}, "
        f"required >= {P0_2_REASON_CODE_MIN_COVERAGE:.0%}. "
        f"Missing handlers: {missing}"
    )
