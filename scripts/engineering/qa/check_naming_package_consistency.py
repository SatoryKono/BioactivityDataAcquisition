#!/usr/bin/env python3
"""Pre-merge gate for naming/package consistency rules.

Rules:
1) strict suffix-policy: delegated to ``scripts/engineering/qa/naming_audit.py --check``.
2) layer-aware suffix/family policy: enforced from
   ``configs/quality/layered_suffix_policy.yaml``.
3) factory-only-in-composition: no ``Factory`` classes or ``*factory*.py`` modules
   outside ``src/bioetl/composition``.
4) canonical role subpackage names: ``contracts/mappers/services/facades`` only
   (singular forms are forbidden).
"""

from __future__ import annotations

import argparse
import ast
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import yaml

SRC_ROOT = Path("src/bioetl")
CANONICAL_NAMING_AUDIT_PATH = Path("scripts/engineering/qa/naming_audit.py")
LAYER_AWARE_SUFFIX_POLICY_PATH = Path("configs/quality/layered_suffix_policy.yaml")
CHECKPOINT_ASSEMBLY_PATH = "src/bioetl/composition/bootstrap/assembly/checkpoint.py"
OBSERVABILITY_RUNTIME_PATH = "src/bioetl/composition/bootstrap/runtime/observability.py"
ARCHITECTURE_TRACKER_ISSUE = "#3442"
ARCHITECTURE_OWNER = "@bioetl-architecture"
OBSERVABILITY_OWNER = "@bioetl-observability"
OBSERVABILITY_BOOTSTRAP_BEHIND_FACADE_REASON = (
    "Reviewed observability bootstrap implementation retained behind "
    "the runtime observability facade."
)
OBSERVABILITY_FACADE_REASON_TEMPLATE = (
    "Reviewed public runtime observability facade retained as the "
    "canonical bootstrap seam for {port} port wiring."
)
FORBIDDEN_FACTORY_LAYERS = (
    SRC_ROOT / "application",
    SRC_ROOT / "infrastructure",
    SRC_ROOT / "domain",
    SRC_ROOT / "interfaces",
)
SINGULAR_ROLE_TO_CANONICAL = {
    "contract": "contracts",
    "mapper": "mappers",
    "service": "services",
    "facade": "facades",
}
ALLOWED_FACTORY_FACADES = {
    "src/bioetl/application/core/wiring/factory.py",
}


@dataclass(frozen=True)
class Violation:
    """Single policy violation."""

    rule: str
    location: str
    details: str


@dataclass(frozen=True)
class AllowedSymbol:
    """Machine-readable exception or allowed legacy symbol."""

    symbol: str
    path: str
    issue: str
    reason: str
    owner: str
    expires_on: str
    removal_step: str


@dataclass(frozen=True)
class SuffixBoundaryRule:
    """Layer-aware suffix boundary rule."""

    rule_id: str
    description: str
    suffixes: tuple[str, ...]
    include_path_prefixes: tuple[str, ...]
    exclude_path_prefixes: tuple[str, ...]
    allowed_symbols: tuple[AllowedSymbol, ...]


@dataclass(frozen=True)
class FamilyFreezeRule:
    """Frozen name-family rule for reviewed ambiguity debt."""

    rule_id: str
    description: str
    include_path_prefixes: tuple[str, ...]
    match_regex: str
    allowed_symbols: tuple[AllowedSymbol, ...]


@dataclass(frozen=True)
class FunctionSuffixRule:
    """Reviewed function-level suffix rule."""

    rule_id: str
    description: str
    suffixes: tuple[str, ...]
    include_path_prefixes: tuple[str, ...]
    exclude_path_prefixes: tuple[str, ...]
    allowed_symbols: tuple[AllowedSymbol, ...]


@dataclass(frozen=True)
class LayerAwareNamingPolicy:
    """Structured layer-aware naming policy loaded from YAML."""

    version: int
    policy_scope: str
    function_suffix_rules: tuple[FunctionSuffixRule, ...]
    suffix_boundary_rules: tuple[SuffixBoundaryRule, ...]
    family_freeze_rules: tuple[FamilyFreezeRule, ...]


_CURATED_COMPOSITION_BOOTSTRAP_PORT_FACTORIES = (
    AllowedSymbol(
        symbol="bootstrap_checkpoint_port",
        path=CHECKPOINT_ASSEMBLY_PATH,
        issue=ARCHITECTURE_TRACKER_ISSUE,
        reason=(
            "Reviewed bootstrap factory that constructs the checkpoint port "
            "implementation for CLI/runtime wiring."
        ),
        owner=ARCHITECTURE_OWNER,
        expires_on="2026-12-31",
        removal_step="Remove after bootstrap port factories are consolidated to canonical runtime builders.",
    ),
    AllowedSymbol(
        symbol="bootstrap_composite_checkpoint_port",
        path=CHECKPOINT_ASSEMBLY_PATH,
        issue=ARCHITECTURE_TRACKER_ISSUE,
        reason=(
            "Reviewed bootstrap factory that constructs the composite checkpoint "
            "port for runtime resume and repair flows."
        ),
        owner=ARCHITECTURE_OWNER,
        expires_on="2026-12-31",
        removal_step=(
            "Remove after composite checkpoint wiring no longer requires "
            "compatibility factory seams."
        ),
    ),
    AllowedSymbol(
        symbol="bootstrap_quarantine_port",
        path=CHECKPOINT_ASSEMBLY_PATH,
        issue=ARCHITECTURE_TRACKER_ISSUE,
        reason=(
            "Reviewed bootstrap factory that constructs the quarantine port "
            "implementation for CLI/runtime wiring."
        ),
        owner=ARCHITECTURE_OWNER,
        expires_on="2026-12-31",
        removal_step="Remove after quarantine port wiring is fully collapsed to canonical bootstrap composition APIs.",
    ),
    AllowedSymbol(
        symbol="bootstrap_dq_monitor_port",
        path="src/bioetl/composition/bootstrap/runtime/dq_bootstrap.py",
        issue=ARCHITECTURE_TRACKER_ISSUE,
        reason=OBSERVABILITY_BOOTSTRAP_BEHIND_FACADE_REASON,
        owner=OBSERVABILITY_OWNER,
        expires_on="2026-12-31",
        removal_step=(
            "Remove when runtime observability bootstrap internals are merged "
            "and no longer need port-suffixed compatibility wrappers."
        ),
    ),
    AllowedSymbol(
        symbol="bootstrap_dq_monitor_port",
        path=OBSERVABILITY_RUNTIME_PATH,
        issue=ARCHITECTURE_TRACKER_ISSUE,
        reason=OBSERVABILITY_FACADE_REASON_TEMPLATE.format(port="DQ monitor"),
        owner=OBSERVABILITY_OWNER,
        expires_on="2026-12-31",
        removal_step=(
            "Remove after public observability bootstrap surface is stabilized "
            "without *_port compatibility factories."
        ),
    ),
    AllowedSymbol(
        symbol="bootstrap_logger_port",
        path="src/bioetl/composition/bootstrap/runtime/logger_bootstrap.py",
        issue=ARCHITECTURE_TRACKER_ISSUE,
        reason=OBSERVABILITY_BOOTSTRAP_BEHIND_FACADE_REASON,
        owner=OBSERVABILITY_OWNER,
        expires_on="2026-12-31",
        removal_step="Remove when logger port bootstrap path is canonicalized and compatibility wrappers are deleted.",
    ),
    AllowedSymbol(
        symbol="bootstrap_logger_port",
        path=OBSERVABILITY_RUNTIME_PATH,
        issue=ARCHITECTURE_TRACKER_ISSUE,
        reason=OBSERVABILITY_FACADE_REASON_TEMPLATE.format(port="logger"),
        owner=OBSERVABILITY_OWNER,
        expires_on="2026-12-31",
        removal_step="Remove after observability facade no longer exposes logger *_port bootstrap seam.",
    ),
    AllowedSymbol(
        symbol="bootstrap_metrics_port",
        path="src/bioetl/composition/bootstrap/runtime/metrics_bootstrap.py",
        issue=ARCHITECTURE_TRACKER_ISSUE,
        reason=OBSERVABILITY_BOOTSTRAP_BEHIND_FACADE_REASON,
        owner=OBSERVABILITY_OWNER,
        expires_on="2026-12-31",
        removal_step="Remove when metrics port bootstrap path is canonicalized and compatibility wrappers are deleted.",
    ),
    AllowedSymbol(
        symbol="bootstrap_metrics_port",
        path=OBSERVABILITY_RUNTIME_PATH,
        issue=ARCHITECTURE_TRACKER_ISSUE,
        reason=OBSERVABILITY_FACADE_REASON_TEMPLATE.format(port="metrics"),
        owner=OBSERVABILITY_OWNER,
        expires_on="2026-12-31",
        removal_step="Remove after observability facade no longer exposes metrics *_port bootstrap seam.",
    ),
    AllowedSymbol(
        symbol="bootstrap_tracer_port",
        path="src/bioetl/composition/bootstrap/runtime/tracing_bootstrap.py",
        issue=ARCHITECTURE_TRACKER_ISSUE,
        reason=OBSERVABILITY_BOOTSTRAP_BEHIND_FACADE_REASON,
        owner=OBSERVABILITY_OWNER,
        expires_on="2026-12-31",
        removal_step="Remove when tracer port bootstrap path is canonicalized and compatibility wrappers are deleted.",
    ),
    AllowedSymbol(
        symbol="bootstrap_tracer_port",
        path=OBSERVABILITY_RUNTIME_PATH,
        issue=ARCHITECTURE_TRACKER_ISSUE,
        reason=OBSERVABILITY_FACADE_REASON_TEMPLATE.format(port="tracer"),
        owner=OBSERVABILITY_OWNER,
        expires_on="2026-12-31",
        removal_step="Remove after observability facade no longer exposes tracer *_port bootstrap seam.",
    ),
)


def _run_suffix_policy_check(repo_root: Path) -> list[Violation]:
    script = repo_root / CANONICAL_NAMING_AUDIT_PATH
    docs_skip_path = repo_root / "docs" / "__naming_gate_skip__"
    if not script.exists():
        return [
            Violation(
                rule="suffix-policy",
                location=CANONICAL_NAMING_AUDIT_PATH.as_posix(),
                details=f"{CANONICAL_NAMING_AUDIT_PATH.as_posix()} not found",
            )
        ]
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--check",
            "--src",
            str(repo_root / SRC_ROOT),
            "--docs",
            str(docs_skip_path),
            "--configs",
            str(repo_root / "configs"),
        ],
        capture_output=True,
        text=True,
        cwd=repo_root,
    )
    if result.returncode == 0:
        return []
    output = (result.stdout + "\n" + result.stderr).strip()
    preview = "\n".join(output.splitlines()[:30])
    return [
        Violation(
            rule="suffix-policy",
            location="scripts/engineering/qa/naming_audit.py --check",
            details=preview or "naming_audit returned non-zero exit code",
        )
    ]


def _flatten_string_sequence(raw: object) -> tuple[str, ...]:
    if not isinstance(raw, list):
        return ()
    return tuple(
        value.strip()
        for value in raw
        if isinstance(value, str) and value.strip()
    )


def _load_allowed_symbols(raw: object) -> tuple[AllowedSymbol, ...]:
    if not isinstance(raw, list):
        return ()

    allowed: list[AllowedSymbol] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        symbol = str(item.get("symbol", "")).strip()
        path = str(item.get("path", "")).strip()
        issue = str(item.get("issue", "")).strip()
        reason = str(item.get("reason", "")).strip()
        owner = str(item.get("owner", "")).strip()
        expires_on = str(item.get("expires_on", "")).strip()
        removal_step = str(item.get("removal_step", "")).strip()
        if (
            symbol
            and path
            and issue
            and reason
            and owner
            and expires_on
            and removal_step
        ):
            try:
                date.fromisoformat(expires_on)
            except ValueError:
                continue
            allowed.append(
                AllowedSymbol(
                    symbol=symbol,
                    path=path,
                    issue=issue,
                    reason=reason,
                    owner=owner,
                    expires_on=expires_on,
                    removal_step=removal_step,
                )
            )
    return tuple(allowed)


def _merge_allowed_symbols(
    *groups: tuple[AllowedSymbol, ...],
) -> tuple[AllowedSymbol, ...]:
    """Return a stable deduplicated allowlist preserving first-seen order."""
    merged: list[AllowedSymbol] = []
    seen: set[tuple[str, str]] = set()
    for group in groups:
        for item in group:
            key = (item.symbol, item.path)
            if key in seen:
                continue
            merged.append(item)
            seen.add(key)
    return tuple(merged)


def _function_suffix_rule_from_config(item: object) -> FunctionSuffixRule | None:
    if not isinstance(item, dict):
        return None
    rule_id = str(item.get("rule_id", "")).strip()
    description = str(item.get("description", "")).strip()
    suffixes = _flatten_string_sequence(item.get("suffixes", []))
    include_path_prefixes = _flatten_string_sequence(item.get("include_path_prefixes", []))
    exclude_path_prefixes = _flatten_string_sequence(item.get("exclude_path_prefixes", []))
    allowed_symbols = _load_allowed_symbols(item.get("allowed_symbols", []))
    if rule_id == "composition_bootstrap_port_factories":
        allowed_symbols = _merge_allowed_symbols(
            allowed_symbols,
            _CURATED_COMPOSITION_BOOTSTRAP_PORT_FACTORIES,
        )
    if not (rule_id and description and suffixes and include_path_prefixes):
        return None
    return FunctionSuffixRule(
        rule_id=rule_id,
        description=description,
        suffixes=suffixes,
        include_path_prefixes=include_path_prefixes,
        exclude_path_prefixes=exclude_path_prefixes,
        allowed_symbols=allowed_symbols,
    )


def _suffix_boundary_rule_from_config(item: object) -> SuffixBoundaryRule | None:
    if not isinstance(item, dict):
        return None
    rule_id = str(item.get("rule_id", "")).strip()
    description = str(item.get("description", "")).strip()
    suffixes = _flatten_string_sequence(item.get("suffixes", []))
    include_path_prefixes = _flatten_string_sequence(item.get("include_path_prefixes", []))
    exclude_path_prefixes = _flatten_string_sequence(item.get("exclude_path_prefixes", []))
    allowed_symbols = _load_allowed_symbols(item.get("allowed_symbol_exceptions", []))
    if not (rule_id and description and suffixes and include_path_prefixes):
        return None
    return SuffixBoundaryRule(
        rule_id=rule_id,
        description=description,
        suffixes=suffixes,
        include_path_prefixes=include_path_prefixes,
        exclude_path_prefixes=exclude_path_prefixes,
        allowed_symbols=allowed_symbols,
    )


def _family_freeze_rule_from_config(item: object) -> FamilyFreezeRule | None:
    if not isinstance(item, dict):
        return None
    rule_id = str(item.get("rule_id", "")).strip()
    description = str(item.get("description", "")).strip()
    include_path_prefixes = _flatten_string_sequence(item.get("include_path_prefixes", []))
    match_regex = str(item.get("match_regex", "")).strip()
    allowed_symbols = _load_allowed_symbols(item.get("allowed_symbols", []))
    if not (rule_id and description and include_path_prefixes and match_regex):
        return None
    return FamilyFreezeRule(
        rule_id=rule_id,
        description=description,
        include_path_prefixes=include_path_prefixes,
        match_regex=match_regex,
        allowed_symbols=allowed_symbols,
    )


def _load_layer_aware_suffix_policy(repo_root: Path) -> LayerAwareNamingPolicy:
    path = repo_root / LAYER_AWARE_SUFFIX_POLICY_PATH
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError(
            "configs/quality/layered_suffix_policy.yaml must be a YAML mapping"
        )

    version = int(payload.get("version", 0))
    policy_scope = str(payload.get("policy_scope", "")).strip()

    function_rules = [
        rule
        for item in payload.get("function_suffix_rules", [])
        if (rule := _function_suffix_rule_from_config(item)) is not None
    ]
    suffix_rules = [
        rule
        for item in payload.get("suffix_boundary_rules", [])
        if (rule := _suffix_boundary_rule_from_config(item)) is not None
    ]
    family_rules = [
        rule
        for item in payload.get("family_freeze_rules", [])
        if (rule := _family_freeze_rule_from_config(item)) is not None
    ]

    return LayerAwareNamingPolicy(
        version=version,
        policy_scope=policy_scope,
        function_suffix_rules=tuple(function_rules),
        suffix_boundary_rules=tuple(suffix_rules),
        family_freeze_rules=tuple(family_rules),
    )


def _matches_any_prefix(path: str, prefixes: tuple[str, ...]) -> bool:
    return any(path.startswith(prefix) for prefix in prefixes)


def _is_public_facade_module(relative_path: str) -> bool:
    path = Path(relative_path)
    return path.name == "__init__.py" or path.name.endswith("_api.py")


def _is_allowed_symbol(
    *,
    symbol: str,
    relative_path: str,
    allowed_symbols: tuple[AllowedSymbol, ...],
) -> bool:
    return any(
        item.symbol == symbol and item.path == relative_path for item in allowed_symbols
    )


def _literal_assignment_names(
    tree: ast.Module,
    assignment_name: str,
) -> set[str]:
    """Extract string literal names from a top-level list/tuple/set assignment."""
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(target, ast.Name) and target.id == assignment_name
            for target in node.targets
        ):
            continue
        value = node.value
        if not isinstance(value, (ast.List, ast.Tuple, ast.Set)):
            return set()
        return {
            element.value
            for element in value.elts
            if isinstance(element, ast.Constant) and isinstance(element.value, str)
        }
    return set()


def _class_symbol(node: ast.AST) -> tuple[str, int, str] | None:
    if isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
        return node.name, node.lineno, "class"
    return None


def _reexport_symbols(
    node: ast.AST, exported_names: set[str]
) -> list[tuple[str, int, str]]:
    if not isinstance(node, (ast.ImportFrom, ast.Import)):
        return []

    symbols: list[tuple[str, int, str]] = []
    for alias in node.names:
        if alias.name == "*":
            continue
        public_name = alias.asname or alias.name.rsplit(".", 1)[-1]
        if public_name.startswith("_") or public_name not in exported_names:
            continue
        symbols.append((public_name, node.lineno, "re-export"))
    return symbols


def _alias_symbol(node: ast.AST) -> tuple[str, int, str] | None:
    if not isinstance(node, ast.Assign):
        return None
    if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
        return None
    if not isinstance(node.value, (ast.Name, ast.Attribute)):
        return None
    target_name = node.targets[0].id
    if target_name.startswith("_"):
        return None
    return target_name, node.lineno, "alias"


def _node_layer_aware_symbols(
    node: ast.AST, exported_names: set[str]
) -> list[tuple[str, int, str]]:
    class_symbol = _class_symbol(node)
    if class_symbol is not None:
        return [class_symbol]
    reexport_symbols = _reexport_symbols(node, exported_names)
    if reexport_symbols:
        return reexport_symbols
    alias_symbol = _alias_symbol(node)
    return [] if alias_symbol is None else [alias_symbol]


def _iter_layer_aware_symbols(tree: ast.Module) -> list[tuple[str, int, str]]:
    """Yield top-level class, alias, and public re-export symbols."""
    exported_names = _literal_assignment_names(tree, "__all__")
    symbols: list[tuple[str, int, str]] = []
    seen_symbols: set[str] = set()
    for node in tree.body:
        for name, lineno, kind in _node_layer_aware_symbols(node, exported_names):
            if name in seen_symbols:
                continue
            symbols.append((name, lineno, kind))
            seen_symbols.add(name)
    return symbols


def _iter_public_function_symbols(tree: ast.Module) -> list[tuple[str, int, str]]:
    """Yield top-level public function names for reviewed suffix checks."""
    symbols: list[tuple[str, int, str]] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("_"):
                continue
            symbols.append((node.name, node.lineno, "function"))
    return symbols


def _rule_matches_symbol_path(
    *,
    symbol_name: str,
    relative_path: str,
    rule: FunctionSuffixRule | SuffixBoundaryRule,
) -> bool:
    return (
        _matches_any_prefix(relative_path, rule.include_path_prefixes)
        and not _matches_any_prefix(relative_path, rule.exclude_path_prefixes)
        and any(symbol_name.endswith(suffix) for suffix in rule.suffixes)
        and not _is_allowed_symbol(
            symbol=symbol_name,
            relative_path=relative_path,
            allowed_symbols=rule.allowed_symbols,
        )
    )


def _function_suffix_rule_violation(
    *,
    relative_path: str,
    symbol_name: str,
    lineno: int,
    symbol_kind: str,
    rule: FunctionSuffixRule,
) -> Violation | None:
    if not _rule_matches_symbol_path(
        symbol_name=symbol_name, relative_path=relative_path, rule=rule
    ):
        return None
    return Violation(
        rule="layer-aware-suffix-policy",
        location=f"{relative_path}:{lineno}",
        details=(
            f"[{rule.rule_id}] {symbol_kind} {symbol_name} violates the "
            f"reviewed function suffix boundary for {', '.join(rule.suffixes)}"
        ),
    )


def _suffix_boundary_rule_violation(
    *,
    relative_path: str,
    symbol_name: str,
    lineno: int,
    symbol_kind: str,
    rule: SuffixBoundaryRule,
) -> Violation | None:
    if symbol_kind == "re-export" and not _is_public_facade_module(relative_path):
        return None
    if not _rule_matches_symbol_path(
        symbol_name=symbol_name, relative_path=relative_path, rule=rule
    ):
        return None
    return Violation(
        rule="layer-aware-suffix-policy",
        location=f"{relative_path}:{lineno}",
        details=(
            f"[{rule.rule_id}] {symbol_kind} {symbol_name} violates the "
            f"reviewed suffix boundary for {', '.join(rule.suffixes)}"
        ),
    )


def _family_freeze_rule_violation(
    *,
    relative_path: str,
    symbol_name: str,
    lineno: int,
    symbol_kind: str,
    rule: FamilyFreezeRule,
) -> Violation | None:
    if symbol_kind == "re-export":
        return None
    if not _matches_any_prefix(relative_path, rule.include_path_prefixes):
        return None
    if re.match(rule.match_regex, symbol_name) is None:
        return None
    if _is_allowed_symbol(
        symbol=symbol_name,
        relative_path=relative_path,
        allowed_symbols=rule.allowed_symbols,
    ):
        return None
    return Violation(
        rule="layer-aware-suffix-policy",
        location=f"{relative_path}:{lineno}",
        details=(
            f"[{rule.rule_id}] {symbol_kind} {symbol_name} is not registered "
            "in the frozen naming family"
        ),
    )


def _layer_aware_function_violations(
    *,
    relative_path: str,
    tree: ast.Module,
    policy: LayerAwareNamingPolicy,
) -> list[Violation]:
    return [
        violation
        for symbol_name, lineno, symbol_kind in _iter_public_function_symbols(tree)
        for rule in policy.function_suffix_rules
        if (
            violation := _function_suffix_rule_violation(
                relative_path=relative_path,
                symbol_name=symbol_name,
                lineno=lineno,
                symbol_kind=symbol_kind,
                rule=rule,
            )
        )
        is not None
    ]


def _layer_aware_public_symbol_violations(
    *,
    relative_path: str,
    tree: ast.Module,
    policy: LayerAwareNamingPolicy,
) -> list[Violation]:
    violations: list[Violation] = []
    for symbol_name, lineno, symbol_kind in _iter_layer_aware_symbols(tree):
        violations.extend(
            violation
            for rule in policy.suffix_boundary_rules
            if (
                violation := _suffix_boundary_rule_violation(
                    relative_path=relative_path,
                    symbol_name=symbol_name,
                    lineno=lineno,
                    symbol_kind=symbol_kind,
                    rule=rule,
                )
            )
            is not None
        )
        violations.extend(
            violation
            for rule in policy.family_freeze_rules
            if (
                violation := _family_freeze_rule_violation(
                    relative_path=relative_path,
                    symbol_name=symbol_name,
                    lineno=lineno,
                    symbol_kind=symbol_kind,
                    rule=rule,
                )
            )
            is not None
        )
    return violations


def _parse_python_file(path: Path) -> ast.Module | None:
    try:
        return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError:
        return None


def _layer_aware_suffix_violations(repo_root: Path) -> list[Violation]:
    policy = _load_layer_aware_suffix_policy(repo_root)
    src_root = repo_root / SRC_ROOT
    violations: list[Violation] = []

    for py_file in src_root.rglob("*.py"):
        if "__pycache__" in py_file.parts:
            continue
        tree = _parse_python_file(py_file)
        if tree is None:
            continue
        relative_path = py_file.relative_to(repo_root).as_posix()
        violations.extend(
            _layer_aware_function_violations(
                relative_path=relative_path, tree=tree, policy=policy
            )
        )
        violations.extend(
            _layer_aware_public_symbol_violations(
                relative_path=relative_path, tree=tree, policy=policy
            )
        )
    return violations


def _factory_module_violation(py_file: Path, *, repo_root: Path) -> Violation | None:
    if py_file.name not in {"factory.py"} and not py_file.name.endswith("_factory.py"):
        return None

    rel = py_file.relative_to(repo_root).as_posix()
    if rel in ALLOWED_FACTORY_FACADES:
        return None
    return Violation(
        rule="factory-only-in-composition",
        location=rel,
        details="Factory module is outside src/bioetl/composition",
    )


def _load_python_ast(py_file: Path) -> ast.AST | None:
    try:
        return ast.parse(py_file.read_text(encoding="utf-8"))
    except SyntaxError:
        return None


def _factory_class_violations(py_file: Path, *, repo_root: Path) -> list[Violation]:
    tree = _load_python_ast(py_file)
    if tree is None:
        return []

    rel = py_file.relative_to(repo_root).as_posix()
    return [
        Violation(
            rule="factory-only-in-composition",
            location=f"{rel}:{node.lineno}",
            details=f"class {node.name} must live in composition layer",
        )
        for node in ast.walk(tree)
        if (
            isinstance(node, ast.ClassDef)
            and node.name.endswith("Factory")
            and not node.name.startswith("_")
        )
    ]


def _violations_for_forbidden_factory_file(
    py_file: Path, *, repo_root: Path
) -> list[Violation]:
    violations: list[Violation] = []
    module_violation = _factory_module_violation(py_file, repo_root=repo_root)
    if module_violation is not None:
        violations.append(module_violation)
    violations.extend(_factory_class_violations(py_file, repo_root=repo_root))
    return violations


def _factory_violations(repo_root: Path) -> list[Violation]:
    violations: list[Violation] = []

    for layer in FORBIDDEN_FACTORY_LAYERS:
        layer_path = repo_root / layer
        if not layer_path.exists():
            continue
        for py_file in layer_path.rglob("*.py"):
            if "__pycache__" in py_file.parts:
                continue
            violations.extend(
                _violations_for_forbidden_factory_file(py_file, repo_root=repo_root)
            )
    return violations


def _package_template_violations(repo_root: Path) -> list[Violation]:
    violations: list[Violation] = []
    for directory in (repo_root / SRC_ROOT).rglob("*"):
        if not directory.is_dir() or "__pycache__" in directory.parts:
            continue
        singular_name = SINGULAR_ROLE_TO_CANONICAL.get(directory.name)
        if singular_name is None:
            continue
        rel = directory.relative_to(repo_root).as_posix()
        violations.append(
            Violation(
                rule="subpackage-template",
                location=rel,
                details=(
                    f"Use canonical subpackage name '{singular_name}' "
                    f"instead of '{directory.name}'"
                ),
            )
        )
    return violations


def run_checks(repo_root: Path) -> list[Violation]:
    """Run all consistency checks and return merged violations."""
    violations: list[Violation] = []
    violations.extend(_run_suffix_policy_check(repo_root))
    violations.extend(_layer_aware_suffix_violations(repo_root))
    violations.extend(_factory_violations(repo_root))
    violations.extend(_package_template_violations(repo_root))
    return violations


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check naming/package consistency pre-merge rules."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero when violations are found (CI mode).",
    )
    return parser.parse_args()


def main() -> int:
    """CLI entrypoint."""
    _ = _parse_args()
    repo_root = Path(__file__).resolve().parents[3]
    violations = run_checks(repo_root)

    if not violations:
        print(
            "Naming/package consistency: OK "
            "("
            "suffix-policy, layer-aware-suffix-policy, "
            "factory-only-in-composition, subpackage-template"
            ")"
        )
        return 0

    print(f"Naming/package consistency: {len(violations)} violation(s) found")
    for item in violations:
        print(f"  - [{item.rule}] {item.location}: {item.details}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
