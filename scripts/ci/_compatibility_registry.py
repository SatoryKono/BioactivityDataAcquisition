"""Shared compatibility-registry loader and measured-surface helpers."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

import yaml

ALLOWED_COMPATIBILITY_STATUSES = frozenset(
    {
        "deprecated-warn",
        "compat-shim",
        "mixed-module",
        "retained-entrypoint",
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

_REPO_ROOT = Path(__file__).resolve().parents[2]
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
class CompatibilityRegistry:
    """Machine-readable compatibility registry contract."""

    version: int
    policy_scope: str
    tracked_docstring_prefixes: tuple[str, ...]
    transition_debt: tuple[CompatibilityInventoryRow, ...]
    retained_entrypoints: tuple[CompatibilityInventoryRow, ...]
    measured_only_modules: tuple[MeasuredOnlyModule, ...]

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
    repo_root = src_root.resolve().parents[1]
    tracked_paths: set[str] = set()

    for path in src_root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        module_docstring = ast.get_docstring(tree)
        if module_docstring is None:
            continue
        first_line = module_docstring.splitlines()[0].strip()
        if first_line.startswith(prefixes):
            tracked_paths.add(path.resolve().relative_to(repo_root).as_posix())

    return tracked_paths


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
