#!/usr/bin/env python3
"""Pre-merge gate for naming/package consistency rules.

Rules:
1) strict suffix-policy: delegated to ``scripts/engineering/qa/naming_audit.py --check``.
2) layer-aware suffix/family policy: enforced from
   ``configs/quality/layered_suffix_policy.yaml``.
3) factory-only-in-composition: no ``Factory`` classes or ``*factory*.py`` modules
   outside ``src/bioetl/composition``.
4) builder-only-in-composition: no public ``Builder`` classes or unregistered
   ``*builder*.py`` modules outside ``src/bioetl/composition``.
5) canonical role subpackage names: ``contracts/mappers/services/facades`` only
   (singular forms are forbidden).
"""

from __future__ import annotations

import argparse
import ast
import importlib.util
import os
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import yaml

SRC_ROOT = Path("src/bioetl")
CANONICAL_NAMING_AUDIT_PATH = Path("scripts/engineering/qa/naming_audit.py")
LAYER_AWARE_SUFFIX_POLICY_PATH = Path("configs/quality/layered_suffix_policy.yaml")
FORBIDDEN_FACTORY_LAYERS = (
    SRC_ROOT / "application",
    SRC_ROOT / "infrastructure",
    SRC_ROOT / "domain",
    SRC_ROOT / "interfaces",
)
FORBIDDEN_BUILDER_LAYERS = FORBIDDEN_FACTORY_LAYERS
SINGULAR_ROLE_TO_CANONICAL = {
    "contract": "contracts",
    "mapper": "mappers",
    "service": "services",
    "facade": "facades",
}
ALLOWED_FACTORY_FACADES = {
    "src/bioetl/application/core/wiring/factory.py",
}
ALLOWED_BUILDER_FACADES: frozenset[str] = frozenset()


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
class AllowedModule:
    """Machine-readable exception for a reviewed module path."""

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
    allowed_modules: tuple[AllowedModule, ...]


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
class LayerSuffixMatrixEntry:
    """Allowed/forbidden suffix contract for one architectural layer."""

    layer: str
    allowed_suffixes: tuple[str, ...]
    forbidden_suffixes: tuple[str, ...]


@dataclass(frozen=True)
class CanonicalFamilySymbol:
    """Published canonical or compatibility symbol owner."""

    symbol: str
    path: str
    reason: str = ""


@dataclass(frozen=True)
class CanonicalFamilyRegistryEntry:
    """Canonical naming family with explicit owners and compatibility seams."""

    family_id: str
    canonical_symbols: tuple[CanonicalFamilySymbol, ...]
    compatibility_symbols: tuple[CanonicalFamilySymbol, ...]


@dataclass(frozen=True)
class LayerAwareNamingPolicy:
    """Structured layer-aware naming policy loaded from YAML."""

    version: int
    policy_scope: str
    layer_suffix_matrix: tuple[LayerSuffixMatrixEntry, ...]
    canonical_family_registry: tuple[CanonicalFamilyRegistryEntry, ...]
    function_suffix_rules: tuple[FunctionSuffixRule, ...]
    suffix_boundary_rules: tuple[SuffixBoundaryRule, ...]
    family_freeze_rules: tuple[FamilyFreezeRule, ...]


def _load_naming_audit_module(repo_root: Path):
    script = repo_root / CANONICAL_NAMING_AUDIT_PATH
    spec = importlib.util.spec_from_file_location(
        "bioetl_naming_audit_runtime",
        script,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {CANONICAL_NAMING_AUDIT_PATH.as_posix()}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["bioetl_naming_audit_runtime"] = module
    spec.loader.exec_module(module)
    return module


def _suffix_policy_preview(
    results: dict[str, list[object]],
) -> str:
    lines: list[str] = []
    for category, violations in results.items():
        if not violations:
            continue
        lines.append(f"{category}: {len(violations)} violation(s)")
        for item in violations[:5]:
            path = getattr(item, "path", "<unknown>")
            line = getattr(item, "line", None) or "-"
            current_name = getattr(item, "current_name", "<unknown>")
            issue = getattr(getattr(item, "issue", None), "value", "violation")
            lines.append(f"  - {path}:{line}: {current_name}: {issue}")
    return "\n".join(lines[:30])


def _run_suffix_policy_check(repo_root: Path) -> list[Violation]:
    script = repo_root / CANONICAL_NAMING_AUDIT_PATH
    if not script.exists():
        return [
            Violation(
                rule="suffix-policy",
                location=CANONICAL_NAMING_AUDIT_PATH.as_posix(),
                details=f"{CANONICAL_NAMING_AUDIT_PATH.as_posix()} not found",
            )
        ]
    if os.environ.get("BIOETL_FULL_NAMING_AUDIT", "0") != "1":
        return []

    docs_skip_path = repo_root / "docs" / "__naming_gate_skip__"
    try:
        naming_audit = _load_naming_audit_module(repo_root)
        registry = naming_audit.load_naming_registry(
            repo_root / "configs" / "naming_exceptions.yaml"
        )
        registry_errors = naming_audit.validate_naming_registry(registry)
        if registry_errors:
            return [
                Violation(
                    rule="suffix-policy",
                    location="configs/naming_exceptions.yaml",
                    details="\n".join(registry_errors[:30]),
                )
            ]
        module_trees = naming_audit._build_python_module_tree_cache(
            repo_root / SRC_ROOT
        )
        results = naming_audit.run_audit(
            repo_root / SRC_ROOT,
            docs_skip_path,
            repo_root / "configs",
            registry,
            module_trees=module_trees,
        )
    except Exception as exc:  # pragma: no cover - defensive CLI failure path
        return [
            Violation(
                rule="suffix-policy",
                location=CANONICAL_NAMING_AUDIT_PATH.as_posix(),
                details=f"failed to run naming audit: {exc}",
            )
        ]

    total_violations = sum(len(violations) for violations in results.values())
    if total_violations == 0:
        return []
    return [
        Violation(
            rule="suffix-policy",
            location="scripts/engineering/qa/naming_audit.py --check",
            details=_suffix_policy_preview(results),
        )
    ]


def _flatten_string_sequence(raw: object) -> tuple[str, ...]:
    if not isinstance(raw, list):
        return ()
    return tuple(
        value.strip() for value in raw if isinstance(value, str) and value.strip()
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


def _load_allowed_modules(raw: object) -> tuple[AllowedModule, ...]:
    if not isinstance(raw, list):
        return ()

    allowed: list[AllowedModule] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        path = str(item.get("path", "")).strip()
        issue = str(item.get("issue", "")).strip()
        reason = str(item.get("reason", "")).strip()
        owner = str(item.get("owner", "")).strip()
        expires_on = str(item.get("expires_on", "")).strip()
        removal_step = str(item.get("removal_step", "")).strip()
        if path and issue and reason and owner and expires_on and removal_step:
            try:
                date.fromisoformat(expires_on)
            except ValueError:
                continue
            allowed.append(
                AllowedModule(
                    path=path,
                    issue=issue,
                    reason=reason,
                    owner=owner,
                    expires_on=expires_on,
                    removal_step=removal_step,
                )
            )
    return tuple(allowed)


def _validate_allowed_metadata(
    *,
    issue: str,
    owner: str,
    expires_on: str,
    location: str,
) -> None:
    if not issue.startswith("#"):
        raise ValueError(f"{location} must use an issue reference like #1234")
    if not owner.startswith("@"):
        raise ValueError(f"{location} must use an owner handle like @bioetl-team")
    try:
        expiry = date.fromisoformat(expires_on)
    except ValueError as exc:
        raise ValueError(f"{location} must use ISO expires_on metadata") from exc
    if expiry < date.today():
        raise ValueError(f"{location} has stale expires_on={expires_on}")


def _load_canonical_family_symbols(raw: object) -> tuple[CanonicalFamilySymbol, ...]:
    if not isinstance(raw, list):
        return ()

    symbols: list[CanonicalFamilySymbol] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        symbol = str(item.get("symbol", "")).strip()
        path = str(item.get("path", "")).strip()
        reason = str(item.get("reason", "")).strip()
        if symbol and path:
            symbols.append(
                CanonicalFamilySymbol(
                    symbol=symbol,
                    path=path,
                    reason=reason,
                )
            )
    return tuple(symbols)


def _load_layer_suffix_matrix(raw: object) -> tuple[LayerSuffixMatrixEntry, ...]:
    if not isinstance(raw, list):
        return ()

    entries: list[LayerSuffixMatrixEntry] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        layer = str(item.get("layer", "")).strip()
        allowed_suffixes = _flatten_string_sequence(item.get("allowed_suffixes", []))
        forbidden_suffixes = _flatten_string_sequence(
            item.get("forbidden_suffixes", [])
        )
        if layer and allowed_suffixes and forbidden_suffixes:
            entries.append(
                LayerSuffixMatrixEntry(
                    layer=layer,
                    allowed_suffixes=allowed_suffixes,
                    forbidden_suffixes=forbidden_suffixes,
                )
            )
    return tuple(entries)


def _load_canonical_family_registry(
    raw: object,
) -> tuple[CanonicalFamilyRegistryEntry, ...]:
    if not isinstance(raw, list):
        return ()

    entries: list[CanonicalFamilyRegistryEntry] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        family_id = str(item.get("family_id", "")).strip()
        canonical_symbols = _load_canonical_family_symbols(
            item.get("canonical_symbols", [])
        )
        compatibility_symbols = _load_canonical_family_symbols(
            item.get("compatibility_symbols", [])
        )
        if family_id and canonical_symbols:
            entries.append(
                CanonicalFamilyRegistryEntry(
                    family_id=family_id,
                    canonical_symbols=canonical_symbols,
                    compatibility_symbols=compatibility_symbols,
                )
            )
    return tuple(entries)


def _validate_layer_suffix_matrix(
    entries: tuple[LayerSuffixMatrixEntry, ...],
) -> None:
    if not entries:
        raise ValueError("layer_suffix_matrix must not be empty")

    expected_layers = {
        "domain",
        "application",
        "infrastructure",
        "composition",
        "interfaces",
    }
    actual_layers = {entry.layer for entry in entries}
    if actual_layers != expected_layers:
        raise ValueError(
            "layer_suffix_matrix must define exactly the canonical layers: "
            + ", ".join(sorted(expected_layers))
        )
    for entry in entries:
        overlap = set(entry.allowed_suffixes) & set(entry.forbidden_suffixes)
        if overlap:
            raise ValueError(
                f"layer_suffix_matrix[{entry.layer}] overlaps allowed/forbidden "
                f"suffixes: {sorted(overlap)}"
            )


def _canonical_symbol_names(repo_root: Path, relative_path: str) -> set[str]:
    path = repo_root / relative_path
    if not path.exists():
        raise ValueError(
            f"canonical_family_registry references missing file: {relative_path}"
        )

    tree = _parse_python_file(path)
    if tree is None:
        raise ValueError(
            "canonical_family_registry references unparsable Python file: "
            f"{relative_path}"
        )
    return {symbol for symbol, _, _ in _iter_layer_aware_symbols(tree)}


def _validate_canonical_family_symbol_locations(
    entries: tuple[CanonicalFamilyRegistryEntry, ...],
    *,
    repo_root: Path,
) -> None:
    for entry in entries:
        for symbol in entry.canonical_symbols:
            module_symbols = _canonical_symbol_names(repo_root, symbol.path)
            if symbol.symbol not in module_symbols:
                raise ValueError(
                    "canonical_family_registry symbol/path drift: "
                    f"{entry.family_id}:{symbol.symbol} not found in {symbol.path}"
                )


def _validate_canonical_family_registry(
    entries: tuple[CanonicalFamilyRegistryEntry, ...],
) -> None:
    if not entries:
        raise ValueError("canonical_family_registry must not be empty")
    seen_family_ids: set[str] = set()
    for entry in entries:
        if entry.family_id in seen_family_ids:
            raise ValueError(
                f"canonical_family_registry duplicates family_id={entry.family_id}"
            )
        seen_family_ids.add(entry.family_id)
        for symbol in entry.canonical_symbols:
            if not symbol.symbol.endswith(
                ("Runner", "Service", "Port", "Adapter", "Client")
            ):
                raise ValueError(
                    "canonical_family_registry canonical symbol must publish an "
                    f"explicit role suffix: {entry.family_id}:{symbol.symbol}"
                )


def _base_suffix_rule_parts(
    item: dict[str, object], *, allowed_key: str
) -> tuple[
    str,
    str,
    tuple[str, ...],
    tuple[str, ...],
    tuple[str, ...],
    tuple[AllowedSymbol, ...],
]:
    return (
        str(item.get("rule_id", "")).strip(),
        str(item.get("description", "")).strip(),
        _flatten_string_sequence(item.get("suffixes", [])),
        _flatten_string_sequence(item.get("include_path_prefixes", [])),
        _flatten_string_sequence(item.get("exclude_path_prefixes", [])),
        _load_allowed_symbols(item.get(allowed_key, [])),
    )


def _rule_has_required_suffix_parts(
    rule_id: str,
    description: str,
    suffixes: tuple[str, ...],
    include_path_prefixes: tuple[str, ...],
) -> bool:
    return bool(rule_id and description and suffixes and include_path_prefixes)


def _function_suffix_rule_from_config(item: object) -> FunctionSuffixRule | None:
    if not isinstance(item, dict):
        return None
    (
        rule_id,
        description,
        suffixes,
        include_path_prefixes,
        exclude_path_prefixes,
        allowed_symbols,
    ) = _base_suffix_rule_parts(item, allowed_key="allowed_symbols")
    if not _rule_has_required_suffix_parts(
        rule_id, description, suffixes, include_path_prefixes
    ):
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
    (
        rule_id,
        description,
        suffixes,
        include_path_prefixes,
        exclude_path_prefixes,
        allowed_symbols,
    ) = _base_suffix_rule_parts(item, allowed_key="allowed_symbol_exceptions")
    if not _rule_has_required_suffix_parts(
        rule_id, description, suffixes, include_path_prefixes
    ):
        return None
    return SuffixBoundaryRule(
        rule_id=rule_id,
        description=description,
        suffixes=suffixes,
        include_path_prefixes=include_path_prefixes,
        exclude_path_prefixes=exclude_path_prefixes,
        allowed_symbols=allowed_symbols,
        allowed_modules=_load_allowed_modules(
            item.get("allowed_module_exceptions", [])
        ),
    )


def _family_freeze_rule_from_config(item: object) -> FamilyFreezeRule | None:
    if not isinstance(item, dict):
        return None
    rule_id = str(item.get("rule_id", "")).strip()
    description = str(item.get("description", "")).strip()
    include_path_prefixes = _flatten_string_sequence(
        item.get("include_path_prefixes", [])
    )
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
    layer_suffix_matrix = _load_layer_suffix_matrix(
        payload.get("layer_suffix_matrix", [])
    )
    canonical_family_registry = _load_canonical_family_registry(
        payload.get("canonical_family_registry", [])
    )

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

    _validate_layer_suffix_matrix(layer_suffix_matrix)
    _validate_canonical_family_registry(canonical_family_registry)

    for rule in function_rules:
        for item in rule.allowed_symbols:
            _validate_allowed_metadata(
                issue=item.issue,
                owner=item.owner,
                expires_on=item.expires_on,
                location=f"{rule.rule_id}:{item.symbol}",
            )
    for rule in suffix_rules:
        for item in rule.allowed_symbols:
            _validate_allowed_metadata(
                issue=item.issue,
                owner=item.owner,
                expires_on=item.expires_on,
                location=f"{rule.rule_id}:{item.symbol}",
            )
        for item in rule.allowed_modules:
            _validate_allowed_metadata(
                issue=item.issue,
                owner=item.owner,
                expires_on=item.expires_on,
                location=f"{rule.rule_id}:{item.path}",
            )
    for rule in family_rules:
        for item in rule.allowed_symbols:
            _validate_allowed_metadata(
                issue=item.issue,
                owner=item.owner,
                expires_on=item.expires_on,
                location=f"{rule.rule_id}:{item.symbol}",
            )

    return LayerAwareNamingPolicy(
        version=version,
        policy_scope=policy_scope,
        layer_suffix_matrix=layer_suffix_matrix,
        canonical_family_registry=canonical_family_registry,
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


def _is_allowed_module(
    *,
    relative_path: str,
    allowed_modules: tuple[AllowedModule, ...],
) -> bool:
    return any(item.path == relative_path for item in allowed_modules)


def _literal_assignment_names(
    tree: ast.Module,
    assignment_name: str,
) -> set[str]:
    """Extract string literal names from a top-level list/tuple/set assignment."""
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not _is_named_assignment(node, assignment_name):
            continue
        return _string_literals_from_sequence(node.value)
    return set()


def _is_named_assignment(node: ast.Assign, assignment_name: str) -> bool:
    return any(
        isinstance(target, ast.Name) and target.id == assignment_name
        for target in node.targets
    )


def _string_literals_from_sequence(value: ast.expr) -> set[str]:
    if not isinstance(value, (ast.List, ast.Tuple, ast.Set)):
        return set()
    return {
        element.value
        for element in value.elts
        if isinstance(element, ast.Constant) and isinstance(element.value, str)
    }


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


def _module_name_matches_suffix(stem: str, suffixes: tuple[str, ...]) -> bool:
    stem_lower = stem.lower()
    return any(
        stem_lower.endswith(f"_{suffix.lower()}")
        or stem_lower.endswith(f"_{suffix.lower()}s")
        for suffix in suffixes
    )


def _suffix_boundary_module_violation(
    *,
    relative_path: str,
    rule: SuffixBoundaryRule,
) -> Violation | None:
    if rule.rule_id != "non_composition_builder_suffix":
        return None
    path = Path(relative_path)
    if path.stem.startswith("_") or path.name == "__init__.py":
        return None
    if not (
        _matches_any_prefix(relative_path, rule.include_path_prefixes)
        and not _matches_any_prefix(relative_path, rule.exclude_path_prefixes)
        and _module_name_matches_suffix(path.stem, rule.suffixes)
    ):
        return None
    if _is_allowed_module(
        relative_path=relative_path, allowed_modules=rule.allowed_modules
    ):
        return None
    return Violation(
        rule="layer-aware-suffix-policy",
        location=relative_path,
        details=(
            f"[{rule.rule_id}] module {path.name} violates the reviewed "
            f"suffix boundary for {', '.join(rule.suffixes)}"
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


def _layer_aware_module_violations(
    *,
    relative_path: str,
    policy: LayerAwareNamingPolicy,
) -> list[Violation]:
    return [
        violation
        for rule in policy.suffix_boundary_rules
        if (
            violation := _suffix_boundary_module_violation(
                relative_path=relative_path,
                rule=rule,
            )
        )
        is not None
    ]


def _parse_python_file(path: Path) -> ast.Module | None:
    try:
        return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError:
        return None


def _build_python_ast_cache(py_files: tuple[Path, ...]) -> dict[Path, ast.Module]:
    """Parse repository Python files once for all consistency checks."""
    ast_cache: dict[Path, ast.Module] = {}
    for py_file in py_files:
        tree = _parse_python_file(py_file)
        if tree is not None:
            ast_cache[py_file] = tree
    return ast_cache


def _layer_aware_suffix_violations(repo_root: Path) -> list[Violation]:
    policy = _load_layer_aware_suffix_policy(repo_root)
    py_files, _ = _collect_src_tree(repo_root)
    return _layer_aware_suffix_violations_for_files(
        repo_root=repo_root,
        policy=policy,
        py_files=py_files,
    )


def _layer_aware_suffix_violations_for_files(
    *,
    repo_root: Path,
    policy: LayerAwareNamingPolicy,
    py_files: tuple[Path, ...],
    ast_cache: dict[Path, ast.Module] | None = None,
) -> list[Violation]:
    violations: list[Violation] = []

    for py_file in py_files:
        relative_path = py_file.relative_to(repo_root).as_posix()
        violations.extend(
            _layer_aware_module_violations(relative_path=relative_path, policy=policy)
        )
        tree = (
            ast_cache.get(py_file)
            if ast_cache is not None
            else _parse_python_file(py_file)
        )
        if tree is None:
            continue
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


def _collect_src_tree(repo_root: Path) -> tuple[tuple[Path, ...], tuple[Path, ...]]:
    py_files: list[Path] = []
    directories: list[Path] = []
    src_root = repo_root / SRC_ROOT
    for dirpath, dirnames, filenames in os.walk(src_root):
        if "__pycache__" in Path(dirpath).parts:
            dirnames[:] = []
            continue
        current_dir = Path(dirpath)
        directories.append(current_dir)
        py_files.extend(
            current_dir / filename for filename in filenames if filename.endswith(".py")
        )
    return tuple(py_files), tuple(directories)


def _is_under_layer(relative_path: str, layer: Path) -> bool:
    layer_prefix = layer.as_posix().rstrip("/") + "/"
    return relative_path.startswith(layer_prefix)


def _is_under_any_layer(relative_path: str, layers: tuple[Path, ...]) -> bool:
    return any(_is_under_layer(relative_path, layer) for layer in layers)


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


def _builder_allowed_modules(repo_root: Path) -> frozenset[str]:
    policy = _load_layer_aware_suffix_policy(repo_root)
    return _builder_allowed_modules_for_policy(policy)


def _builder_allowed_modules_for_policy(
    policy: LayerAwareNamingPolicy,
) -> frozenset[str]:
    for rule in policy.suffix_boundary_rules:
        if rule.rule_id == "non_composition_builder_suffix":
            return frozenset(item.path for item in rule.allowed_modules)
    return frozenset()


def _builder_module_violation(py_file: Path, *, repo_root: Path) -> Violation | None:
    return _builder_module_violation_for_allowed_modules(
        py_file,
        repo_root=repo_root,
        allowed_modules=_builder_allowed_modules(repo_root),
    )


def _builder_module_violation_for_allowed_modules(
    py_file: Path,
    *,
    repo_root: Path,
    allowed_modules: frozenset[str],
) -> Violation | None:
    stem_lower = py_file.stem.lower()
    if not (
        stem_lower == "builder"
        or stem_lower.endswith("_builder")
        or stem_lower.endswith("_builders")
    ):
        return None
    if py_file.stem.startswith("_"):
        return None

    rel = py_file.relative_to(repo_root).as_posix()
    if rel in ALLOWED_BUILDER_FACADES or rel in allowed_modules:
        return None
    return Violation(
        rule="builder-only-in-composition",
        location=rel,
        details="Builder module is outside src/bioetl/composition",
    )


def _factory_class_violations_from_tree(
    *,
    tree: ast.AST | None,
    py_file: Path,
    repo_root: Path,
) -> list[Violation]:
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


def _builder_class_violations_from_tree(
    *,
    tree: ast.AST | None,
    py_file: Path,
    repo_root: Path,
) -> list[Violation]:
    if tree is None:
        return []

    rel = py_file.relative_to(repo_root).as_posix()
    return [
        Violation(
            rule="builder-only-in-composition",
            location=f"{rel}:{node.lineno}",
            details=f"class {node.name} must live in composition layer",
        )
        for node in ast.walk(tree)
        if (
            isinstance(node, ast.ClassDef)
            and node.name.endswith("Builder")
            and not node.name.startswith("_")
        )
    ]


def _violations_for_forbidden_factory_file(
    py_file: Path,
    *,
    repo_root: Path,
    tree: ast.AST | None = None,
) -> list[Violation]:
    violations: list[Violation] = []
    module_violation = _factory_module_violation(py_file, repo_root=repo_root)
    if module_violation is not None:
        violations.append(module_violation)
    violations.extend(
        _factory_class_violations_from_tree(
            tree=tree,
            py_file=py_file,
            repo_root=repo_root,
        )
    )
    return violations


def _factory_violations(repo_root: Path) -> list[Violation]:
    py_files, _ = _collect_src_tree(repo_root)
    return _factory_violations_for_files(repo_root=repo_root, py_files=py_files)


def _factory_violations_for_files(
    *,
    repo_root: Path,
    py_files: tuple[Path, ...],
    ast_cache: dict[Path, ast.Module] | None = None,
) -> list[Violation]:
    violations: list[Violation] = []

    for py_file in py_files:
        relative_path = py_file.relative_to(repo_root).as_posix()
        if not _is_under_any_layer(relative_path, FORBIDDEN_FACTORY_LAYERS):
            continue
        violations.extend(
            _violations_for_forbidden_factory_file(
                py_file,
                repo_root=repo_root,
                tree=(
                    ast_cache.get(py_file)
                    if ast_cache is not None
                    else _parse_python_file(py_file)
                ),
            )
        )
    return violations


def _violations_for_forbidden_builder_file(
    py_file: Path,
    *,
    repo_root: Path,
    tree: ast.AST | None = None,
) -> list[Violation]:
    violations: list[Violation] = []
    module_violation = _builder_module_violation(py_file, repo_root=repo_root)
    if module_violation is not None:
        violations.append(module_violation)
    violations.extend(
        _builder_class_violations_from_tree(
            tree=tree,
            py_file=py_file,
            repo_root=repo_root,
        )
    )
    return violations


def _builder_violations(repo_root: Path) -> list[Violation]:
    policy = _load_layer_aware_suffix_policy(repo_root)
    py_files, _ = _collect_src_tree(repo_root)
    return _builder_violations_for_files(
        repo_root=repo_root,
        py_files=py_files,
        allowed_modules=_builder_allowed_modules_for_policy(policy),
    )


def _builder_violations_for_files(
    *,
    repo_root: Path,
    py_files: tuple[Path, ...],
    allowed_modules: frozenset[str],
    ast_cache: dict[Path, ast.Module] | None = None,
) -> list[Violation]:
    violations: list[Violation] = []

    for py_file in py_files:
        relative_path = py_file.relative_to(repo_root).as_posix()
        if not _is_under_any_layer(relative_path, FORBIDDEN_BUILDER_LAYERS):
            continue
        module_violation = _builder_module_violation_for_allowed_modules(
            py_file,
            repo_root=repo_root,
            allowed_modules=allowed_modules,
        )
        if module_violation is not None:
            violations.append(module_violation)
        violations.extend(
            _builder_class_violations_from_tree(
                tree=(
                    ast_cache.get(py_file)
                    if ast_cache is not None
                    else _parse_python_file(py_file)
                ),
                py_file=py_file,
                repo_root=repo_root,
            )
        )
    return violations


def _package_template_violations(repo_root: Path) -> list[Violation]:
    _, directories = _collect_src_tree(repo_root)
    return _package_template_violations_for_dirs(
        repo_root=repo_root,
        directories=directories,
    )


def _package_template_violations_for_dirs(
    *,
    repo_root: Path,
    directories: tuple[Path, ...],
) -> list[Violation]:
    violations: list[Violation] = []
    for directory in directories:
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
    policy = _load_layer_aware_suffix_policy(repo_root)
    _validate_canonical_family_symbol_locations(
        policy.canonical_family_registry,
        repo_root=repo_root,
    )
    py_files, directories = _collect_src_tree(repo_root)
    ast_cache = _build_python_ast_cache(py_files)
    violations: list[Violation] = []
    violations.extend(_run_suffix_policy_check(repo_root))
    violations.extend(
        _layer_aware_suffix_violations_for_files(
            repo_root=repo_root,
            policy=policy,
            py_files=py_files,
            ast_cache=ast_cache,
        )
    )
    violations.extend(
        _factory_violations_for_files(
            repo_root=repo_root,
            py_files=py_files,
            ast_cache=ast_cache,
        )
    )
    violations.extend(
        _builder_violations_for_files(
            repo_root=repo_root,
            py_files=py_files,
            allowed_modules=_builder_allowed_modules_for_policy(policy),
            ast_cache=ast_cache,
        )
    )
    violations.extend(
        _package_template_violations_for_dirs(
            repo_root=repo_root,
            directories=directories,
        )
    )
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
            "factory-only-in-composition, builder-only-in-composition, "
            "subpackage-template"
            ")"
        )
        return 0

    print(f"Naming/package consistency: {len(violations)} violation(s) found")
    for item in violations:
        print(f"  - [{item.rule}] {item.location}: {item.details}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
