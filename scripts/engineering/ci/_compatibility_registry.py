"""Shared compatibility-registry loader and measured-surface helpers."""

from __future__ import annotations

import ast
import re
import shutil
import subprocess
import tokenize
from dataclasses import dataclass
from functools import cache
from pathlib import Path

import yaml

ALLOWED_COMPATIBILITY_STATUSES = frozenset(
    {
        "deprecated-warn",
        "compat-shim",
        "mixed-module",
        "retained-entrypoint",
        "public-entrypoint",
    }
)

ALLOWED_MEASURED_ONLY_NEW_CODE_POLICIES = frozenset(
    {
        "no-new-first-party-imports",
    }
)

ALLOWED_MEASURED_ONLY_PROMOTION_TRIGGERS = frozenset(
    {
        "sanctioned-public-seam",
    }
)
ALLOWED_MEASURED_ONLY_REVIEW_CADENCES = frozenset(
    {
        "quarterly",
    }
)
ALLOWED_MEASURED_ONLY_REVIEW_OUTCOMES = frozenset(
    {
        "retain",
        "promote",
        "remove",
    }
)

_REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_REGISTRY_PATH = (
    _REPO_ROOT / "configs" / "quality" / "compatibility_facade_inventory.yaml"
)
DEFAULT_SRC_ROOT = _REPO_ROOT / "src" / "bioetl"


@dataclass(frozen=True)
class CompatibilityInventoryRow:
    """One curated compatibility ledger row."""

    path: str
    compatibility_role: str
    canonical_target: str
    status: str
    owner: str
    introduced_in: str
    review_date: str
    external_breaking_change_required: bool
    internal_callers_zero: bool
    allowed_call_sites: str
    migration_path: str
    exit_criteria: str


@dataclass(frozen=True)
class MeasuredOnlyModule:
    """One allowlisted measured-only compatibility module."""

    path: str
    owner: str
    reason: str
    review_date: str
    new_code_policy: str
    promotion_trigger: str


@dataclass(frozen=True)
class MeasuredOnlyRatchetScope:
    """One scoped ratchet budget for measured-only compatibility modules."""

    path_prefix: str
    max_modules: int


@dataclass(frozen=True)
class MeasuredOnlyRatchet:
    """Repo-level ratchet limits for measured-only compatibility surface growth."""

    max_total_modules: int
    scoped_limits: tuple[MeasuredOnlyRatchetScope, ...]


@dataclass(frozen=True)
class MeasuredOnlyReviewWorkflow:
    """Lifecycle review workflow for measured-only compatibility modules."""

    review_cadence: str
    required_checks: tuple[str, ...]
    allowed_outcomes: tuple[str, ...]
    promotion_requires_curated_row: bool


@dataclass(frozen=True)
class CompatibilityRegistry:
    """Machine-readable compatibility registry contract."""

    version: int
    policy_scope: str
    tracked_docstring_prefixes: tuple[str, ...]
    transition_debt: tuple[CompatibilityInventoryRow, ...]
    retained_entrypoints: tuple[CompatibilityInventoryRow, ...]
    measured_only_modules: tuple[MeasuredOnlyModule, ...]
    measured_only_ratchet: MeasuredOnlyRatchet
    measured_only_review_workflow: MeasuredOnlyReviewWorkflow

    @property
    def curated_rows(self) -> tuple[CompatibilityInventoryRow, ...]:
        return (*self.transition_debt, *self.retained_entrypoints)

    @property
    def curated_paths(self) -> set[str]:
        return {row.path for row in self.curated_rows}

    @property
    def measured_only_paths(self) -> set[str]:
        return {row.path for row in self.measured_only_modules}

    @property
    def measured_tracked_paths(self) -> set[str]:
        return self.curated_paths | self.measured_only_paths


def _load_yaml(path: Path) -> dict[str, object]:
    with path.open(encoding="utf-8") as stream:
        payload = yaml.safe_load(stream) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a mapping root")
    return payload


def _parse_inventory_rows(
    payload: object, *, section_name: str
) -> tuple[CompatibilityInventoryRow, ...]:
    if payload is None:
        return ()
    if not isinstance(payload, list):
        raise ValueError(f"{section_name} must be a list")

    rows: list[CompatibilityInventoryRow] = []
    for item in payload:
        if not isinstance(item, dict):
            raise ValueError(f"{section_name} rows must be mappings")
        row = CompatibilityInventoryRow(
            path=str(item["path"]),
            compatibility_role=str(item["compatibility_role"]),
            canonical_target=str(item["canonical_target"]),
            status=str(item["status"]),
            owner=str(item["owner"]),
            introduced_in=str(item["introduced_in"]),
            review_date=str(item["review_date"]),
            external_breaking_change_required=bool(
                item["external_breaking_change_required"]
            ),
            internal_callers_zero=bool(item["internal_callers_zero"]),
            allowed_call_sites=str(item["allowed_call_sites"]),
            migration_path=str(item["migration_path"]),
            exit_criteria=str(item["exit_criteria"]),
        )
        if row.status not in ALLOWED_COMPATIBILITY_STATUSES:
            raise ValueError(
                f"Unsupported compatibility status {row.status!r} for {row.path}"
            )
        rows.append(row)
    return tuple(rows)


def _parse_measured_only_rows(payload: object) -> tuple[MeasuredOnlyModule, ...]:
    if payload is None:
        return ()
    if not isinstance(payload, list):
        raise ValueError("measured_only_modules must be a list")

    rows: list[MeasuredOnlyModule] = []
    for item in payload:
        if not isinstance(item, dict):
            raise ValueError("measured_only_modules rows must be mappings")
        rows.append(
            MeasuredOnlyModule(
                path=str(item["path"]),
                owner=str(item["owner"]),
                reason=str(item["reason"]),
                review_date=str(item["review_date"]),
                new_code_policy=str(item["new_code_policy"]),
                promotion_trigger=str(item["promotion_trigger"]),
            )
        )
        if rows[-1].new_code_policy not in ALLOWED_MEASURED_ONLY_NEW_CODE_POLICIES:
            raise ValueError(
                "Unsupported measured-only new_code_policy "
                f"{rows[-1].new_code_policy!r} for {rows[-1].path}"
            )
        if rows[-1].promotion_trigger not in ALLOWED_MEASURED_ONLY_PROMOTION_TRIGGERS:
            raise ValueError(
                "Unsupported measured-only promotion_trigger "
                f"{rows[-1].promotion_trigger!r} for {rows[-1].path}"
            )
    return tuple(rows)


def _parse_measured_only_ratchet(payload: object) -> MeasuredOnlyRatchet:
    if not isinstance(payload, dict):
        raise ValueError("measured_only_ratchet must be a mapping")

    scoped_limits_payload = payload.get("scoped_limits")
    if not isinstance(scoped_limits_payload, list) or not scoped_limits_payload:
        raise ValueError("measured_only_ratchet.scoped_limits must be a non-empty list")

    scoped_limits: list[MeasuredOnlyRatchetScope] = []
    for item in scoped_limits_payload:
        if not isinstance(item, dict):
            raise ValueError(
                "measured_only_ratchet.scoped_limits rows must be mappings"
            )
        scope = MeasuredOnlyRatchetScope(
            path_prefix=str(item["path_prefix"]),
            max_modules=int(item["max_modules"]),
        )
        if scope.max_modules < 0:
            raise ValueError(
                "measured_only_ratchet scoped max_modules must be non-negative "
                f"for {scope.path_prefix}"
            )
        scoped_limits.append(scope)

    max_total_modules = int(payload["max_total_modules"])
    if max_total_modules < 0:
        raise ValueError("measured_only_ratchet.max_total_modules must be non-negative")

    return MeasuredOnlyRatchet(
        max_total_modules=max_total_modules,
        scoped_limits=tuple(scoped_limits),
    )


def _parse_measured_only_review_workflow(payload: object) -> MeasuredOnlyReviewWorkflow:
    if not isinstance(payload, dict):
        raise ValueError("measured_only_review_workflow must be a mapping")

    review_cadence = str(payload["review_cadence"])
    if review_cadence not in ALLOWED_MEASURED_ONLY_REVIEW_CADENCES:
        raise ValueError(
            "Unsupported measured_only_review_workflow.review_cadence "
            f"{review_cadence!r}"
        )

    required_checks_payload = payload.get("required_checks")
    if not isinstance(required_checks_payload, list) or not required_checks_payload:
        raise ValueError(
            "measured_only_review_workflow.required_checks must be a non-empty list"
        )
    required_checks = tuple(str(item) for item in required_checks_payload)

    allowed_outcomes_payload = payload.get("allowed_outcomes")
    if not isinstance(allowed_outcomes_payload, list) or not allowed_outcomes_payload:
        raise ValueError(
            "measured_only_review_workflow.allowed_outcomes must be a non-empty list"
        )
    allowed_outcomes = tuple(str(item) for item in allowed_outcomes_payload)
    invalid_outcomes = sorted(
        outcome
        for outcome in allowed_outcomes
        if outcome not in ALLOWED_MEASURED_ONLY_REVIEW_OUTCOMES
    )
    if invalid_outcomes:
        raise ValueError(
            "Unsupported measured_only_review_workflow.allowed_outcomes values: "
            + ", ".join(invalid_outcomes)
        )

    return MeasuredOnlyReviewWorkflow(
        review_cadence=review_cadence,
        required_checks=required_checks,
        allowed_outcomes=allowed_outcomes,
        promotion_requires_curated_row=bool(payload["promotion_requires_curated_row"]),
    )


def load_compatibility_registry(
    registry_path: Path = DEFAULT_REGISTRY_PATH,
) -> CompatibilityRegistry:
    """Load the canonical compatibility registry YAML."""
    payload = _load_yaml(registry_path)

    prefixes = payload.get("tracked_docstring_prefixes")
    if not isinstance(prefixes, list) or not prefixes:
        raise ValueError("tracked_docstring_prefixes must be a non-empty list")
    tracked_docstring_prefixes = tuple(str(item) for item in prefixes)

    registry = CompatibilityRegistry(
        version=int(payload["version"]),
        policy_scope=str(payload["policy_scope"]),
        tracked_docstring_prefixes=tracked_docstring_prefixes,
        transition_debt=_parse_inventory_rows(
            payload.get("transition_debt"), section_name="transition_debt"
        ),
        retained_entrypoints=_parse_inventory_rows(
            payload.get("retained_entrypoints"), section_name="retained_entrypoints"
        ),
        measured_only_modules=_parse_measured_only_rows(
            payload.get("measured_only_modules")
        ),
        measured_only_ratchet=_parse_measured_only_ratchet(
            payload.get("measured_only_ratchet")
        ),
        measured_only_review_workflow=_parse_measured_only_review_workflow(
            payload.get("measured_only_review_workflow")
        ),
    )
    if registry.policy_scope != "compatibility_facades":
        raise ValueError(
            "compatibility registry policy_scope must be compatibility_facades"
        )
    return registry


def scan_docstring_tracked_modules(
    *,
    src_root: Path = DEFAULT_SRC_ROOT,
    prefixes: tuple[str, ...],
) -> set[str]:
    """Return first-party modules whose first docstring line matches tracking prefixes."""
    return set(
        _scan_docstring_tracked_modules_cached(
            src_root=str(src_root.resolve()),
            prefixes=prefixes,
        )
    )


@cache
def _scan_docstring_tracked_modules_cached(
    *,
    src_root: str,
    prefixes: tuple[str, ...],
) -> tuple[str, ...]:
    repo_root = Path(src_root).resolve().parents[1]
    tracked_paths: list[str] = []

    for path in Path(src_root).rglob("*.py"):
        first_line = _module_docstring_first_line(path)
        if first_line is None:
            continue
        if first_line.startswith(prefixes):
            tracked_paths.append(path.resolve().relative_to(repo_root).as_posix())

    return tuple(sorted(tracked_paths))


def _module_docstring_first_line(path: Path) -> str | None:
    """Return the first module-docstring line without parsing the full file AST."""
    with tokenize.open(path) as handle:
        for token in tokenize.generate_tokens(handle.readline):
            if token.type in {
                tokenize.COMMENT,
                tokenize.ENCODING,
                tokenize.NL,
                tokenize.NEWLINE,
            }:
                continue
            if token.type != tokenize.STRING:
                return None
            value = ast.literal_eval(token.string)
            if not isinstance(value, str):
                return None
            return value.splitlines()[0].strip()
    return None


def find_first_party_imports_of_measured_only_modules(
    registry: CompatibilityRegistry,
    *,
    src_root: Path = DEFAULT_SRC_ROOT,
) -> dict[str, tuple[str, ...]]:
    """Return first-party src imports that still target measured-only modules."""
    repo_root = src_root.resolve().parents[1]
    measured_module_names = {
        path.removeprefix("src/").removesuffix(".py").replace("/", ".")
        for path in registry.measured_only_paths
    }
    violations: dict[str, set[str]] = {}

    for path in _candidate_import_paths(
        src_root=src_root,
        measured_module_names=measured_module_names,
    ):
        relative_path = path.resolve().relative_to(repo_root).as_posix()
        current_module = (
            relative_path.removeprefix("src/").removesuffix(".py").replace("/", ".")
        )
        for imported_module in _iter_imported_modules(path):
            if imported_module == current_module:
                continue
            if imported_module in measured_module_names:
                violations.setdefault(imported_module, set()).add(relative_path)

    return {
        module_name: tuple(sorted(importers))
        for module_name, importers in sorted(violations.items())
    }


def find_first_party_imports_of_internal_callers_zero_rows(
    registry: CompatibilityRegistry,
    *,
    src_root: Path = DEFAULT_SRC_ROOT,
) -> dict[str, tuple[str, ...]]:
    """Return first-party src imports of rows marked internal_callers_zero."""
    repo_root = src_root.resolve().parents[1]
    zero_caller_module_names = {
        _module_name_from_src_path(row.path)
        for row in registry.curated_rows
        if row.internal_callers_zero
    }
    if not zero_caller_module_names:
        return {}
    violations: dict[str, set[str]] = {}

    for path in _candidate_import_paths(
        src_root=src_root,
        measured_module_names=zero_caller_module_names,
    ):
        relative_path = path.resolve().relative_to(repo_root).as_posix()
        current_module = _module_name_from_src_path(relative_path)
        for imported_module in _iter_imported_modules(path):
            if imported_module == current_module:
                continue
            if imported_module in zero_caller_module_names:
                violations.setdefault(imported_module, set()).add(relative_path)

    return {
        module_name: tuple(sorted(importers))
        for module_name, importers in sorted(violations.items())
    }


def _module_name_from_src_path(path: str) -> str:
    return path.removeprefix("src/").removesuffix(".py").replace("/", ".")


def _candidate_import_paths(
    *,
    src_root: Path,
    measured_module_names: set[str],
) -> tuple[Path, ...]:
    """Return candidate files that textually reference any measured module."""
    rg_paths = _candidate_import_paths_via_rg(
        src_root=src_root,
        measured_module_names=measured_module_names,
    )
    if rg_paths is not None:
        return rg_paths
    return _candidate_import_paths_via_python(
        src_root=src_root,
        measured_module_names=measured_module_names,
    )


def _candidate_import_paths_via_rg(
    *,
    src_root: Path,
    measured_module_names: set[str],
) -> tuple[Path, ...] | None:
    """Use ripgrep when available to avoid opening every source file in Python."""
    if shutil.which("rg") is None or not measured_module_names:
        return None
    pattern = "|".join(re.escape(name) for name in sorted(measured_module_names))
    result = subprocess.run(
        ["rg", "-l", "-g", "*.py", "-e", pattern, str(src_root)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode not in {0, 1}:
        return None
    return tuple(
        sorted(
            Path(line.strip()) for line in result.stdout.splitlines() if line.strip()
        )
    )


def _candidate_import_paths_via_python(
    *,
    src_root: Path,
    measured_module_names: set[str],
) -> tuple[Path, ...]:
    """Fallback candidate scan when ripgrep is unavailable."""
    candidates: list[Path] = []
    for path in src_root.rglob("*.py"):
        source_text = path.read_text(encoding="utf-8")
        if any(module_name in source_text for module_name in measured_module_names):
            candidates.append(path)
    return tuple(candidates)


@cache
def _iter_imported_modules(path: Path) -> tuple[str, ...]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported_modules: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names if alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)

    return tuple(sorted(imported_modules))


def validate_measured_only_ratchet(
    registry: CompatibilityRegistry,
) -> tuple[tuple[str, ...], dict[str, int]]:
    """Return ratchet violations and current scoped counts."""
    violations: list[str] = []
    scoped_counts: dict[str, int] = {}

    total_modules = len(registry.measured_only_modules)
    if total_modules > registry.measured_only_ratchet.max_total_modules:
        violations.append(
            "measured-only total exceeds ratchet budget: "
            f"{total_modules} > {registry.measured_only_ratchet.max_total_modules}"
        )

    for scope in registry.measured_only_ratchet.scoped_limits:
        current_count = sum(
            1
            for row in registry.measured_only_modules
            if row.path.startswith(scope.path_prefix)
        )
        scoped_counts[scope.path_prefix] = current_count
        if current_count > scope.max_modules:
            violations.append(
                "measured-only scoped budget exceeded for "
                f"{scope.path_prefix}: {current_count} > {scope.max_modules}"
            )

    return tuple(violations), scoped_counts


def validate_measured_docstring_surface(
    registry: CompatibilityRegistry,
    *,
    src_root: Path = DEFAULT_SRC_ROOT,
) -> tuple[set[str], set[str]]:
    """Return unexpected and missing measured docstring-tracked modules."""
    discovered = scan_docstring_tracked_modules(
        src_root=src_root,
        prefixes=registry.tracked_docstring_prefixes,
    )
    allowed = registry.curated_paths | registry.measured_only_paths
    unexpected = discovered - allowed
    missing = registry.measured_only_paths - discovered
    return unexpected, missing
