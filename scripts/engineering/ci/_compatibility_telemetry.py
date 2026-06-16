"""Compatibility-surface telemetry helpers for CI quality reporting."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.engineering.qa.report_dead_code_inventory import build_dead_code_inventory
from scripts.engineering.qa.report_test_governance_audit import (
    collect_test_governance_report,
)

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _compatibility_registry import (  # type: ignore[import-not-found]
        DEFAULT_REGISTRY_PATH,
        load_compatibility_registry,
    )
else:
    from ._compatibility_registry import (
        DEFAULT_REGISTRY_PATH,
        load_compatibility_registry,
    )

DEFAULT_INVENTORY_DOC = (
    _REPO_ROOT / "docs" / "02-architecture" / "07-compatibility-facade-inventory.md"
)
DEFAULT_RUNTIME_UUID_SEAMS_PATH = (
    _REPO_ROOT / "configs" / "quality" / "runtime_uuid_seams.yaml"
)


@dataclass(frozen=True)
class CompatibilitySurfaceSnapshot:
    """Compact compatibility-surface counters used by CI reports."""

    curated_inventory_rows: int
    measured_tracked_modules: int
    measured_only_modules: int
    deprecated_warn_modules: int
    compat_shim_modules: int
    mixed_modules: int
    retained_entrypoints: int
    public_entrypoints: int

    def as_dict(self) -> dict[str, int]:
        """Return a stable JSON-serializable mapping."""
        return {
            "curated_inventory_rows": self.curated_inventory_rows,
            "measured_tracked_modules": self.measured_tracked_modules,
            "measured_only_modules": self.measured_only_modules,
            "deprecated_warn_modules": self.deprecated_warn_modules,
            "compat_shim_modules": self.compat_shim_modules,
            "mixed_modules": self.mixed_modules,
            "retained_entrypoints": self.retained_entrypoints,
            "public_entrypoints": self.public_entrypoints,
        }


@dataclass(frozen=True)
class RuntimeUuidGovernanceSnapshot:
    """Compact counters for runtime UUID governance review."""

    runtime_uuid_seam_count: int
    replay_critical_uuid_seam_count: int

    def as_dict(self) -> dict[str, int]:
        """Return a stable JSON-serializable mapping."""
        return {
            "runtime_uuid_seam_count": self.runtime_uuid_seam_count,
            "replay_critical_uuid_seam_count": self.replay_critical_uuid_seam_count,
        }


@dataclass(frozen=True)
class RetirementGovernanceSnapshot:
    """Compact counters for retirement/dead-code governance review."""

    triaged_entry_count: int
    repo_wide_zero_import_candidate_count: int
    repo_wide_classified_zero_import_candidate_count: int
    repo_wide_untriaged_zero_import_candidate_count: int
    repo_wide_owner_test_anchored_candidate_count: int
    repo_wide_candidates_without_owner_tests_count: int
    repo_wide_non_static_reachability_candidate_count: int
    triaged_retained_owner_test_anchored_count: int
    triaged_retained_without_owner_tests_count: int

    def as_dict(self) -> dict[str, int]:
        """Return a stable JSON-serializable mapping."""
        return {
            "triaged_entry_count": self.triaged_entry_count,
            "repo_wide_zero_import_candidate_count": (
                self.repo_wide_zero_import_candidate_count
            ),
            "repo_wide_classified_zero_import_candidate_count": (
                self.repo_wide_classified_zero_import_candidate_count
            ),
            "repo_wide_untriaged_zero_import_candidate_count": (
                self.repo_wide_untriaged_zero_import_candidate_count
            ),
            "repo_wide_owner_test_anchored_candidate_count": (
                self.repo_wide_owner_test_anchored_candidate_count
            ),
            "repo_wide_candidates_without_owner_tests_count": (
                self.repo_wide_candidates_without_owner_tests_count
            ),
            "repo_wide_non_static_reachability_candidate_count": (
                self.repo_wide_non_static_reachability_candidate_count
            ),
            "triaged_retained_owner_test_anchored_count": (
                self.triaged_retained_owner_test_anchored_count
            ),
            "triaged_retained_without_owner_tests_count": (
                self.triaged_retained_without_owner_tests_count
            ),
        }


@dataclass(frozen=True)
class TestGovernanceDebtSnapshot:
    """Compact counters for static test-governance debt review."""

    compatibility_test_files: int
    refined_assertless_tests: int
    markerless_test_functions: int
    duplicate_test_names: int
    duplicate_test_name_occurrences: int
    uuid4_call_sites: int
    date_today_call_sites: int

    def as_dict(self) -> dict[str, int]:
        """Return a stable JSON-serializable mapping."""
        return {
            "compatibility_test_files": self.compatibility_test_files,
            "refined_assertless_tests": self.refined_assertless_tests,
            "markerless_test_functions": self.markerless_test_functions,
            "duplicate_test_names": self.duplicate_test_names,
            "duplicate_test_name_occurrences": self.duplicate_test_name_occurrences,
            "uuid4_call_sites": self.uuid4_call_sites,
            "date_today_call_sites": self.date_today_call_sites,
        }


@dataclass(frozen=True)
class DebtGovernanceSnapshot:
    """Unified debt-governance counters for weekly reports and CI summaries."""

    compatibility_surface: CompatibilitySurfaceSnapshot
    runtime_uuid: RuntimeUuidGovernanceSnapshot
    retirement: RetirementGovernanceSnapshot
    test_governance: TestGovernanceDebtSnapshot

    def as_dict(self) -> dict[str, object]:
        """Return a stable JSON-serializable mapping."""
        return {
            "compatibility_surface": self.compatibility_surface.as_dict(),
            "runtime_uuid": self.runtime_uuid.as_dict(),
            "retirement": self.retirement.as_dict(),
            "test_governance": self.test_governance.as_dict(),
        }


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected mapping payload at {path}")
    return cast(dict[str, Any], payload)


def collect_compatibility_surface_snapshot(
    *,
    registry_path: Path = DEFAULT_REGISTRY_PATH,
) -> CompatibilitySurfaceSnapshot:
    """Collect compatibility-surface counters from the canonical YAML registry."""
    registry = load_compatibility_registry(registry_path)
    rows = registry.curated_rows

    status_counts = {
        "deprecated-warn": 0,
        "compat-shim": 0,
        "mixed-module": 0,
        "retained-entrypoint": 0,
        "public-entrypoint": 0,
    }
    for row in rows:
        status_counts[row.status] = status_counts.get(row.status, 0) + 1

    return CompatibilitySurfaceSnapshot(
        curated_inventory_rows=len(rows),
        measured_tracked_modules=len(registry.measured_tracked_paths),
        measured_only_modules=len(registry.measured_only_paths),
        deprecated_warn_modules=status_counts["deprecated-warn"],
        compat_shim_modules=status_counts["compat-shim"],
        mixed_modules=status_counts["mixed-module"],
        retained_entrypoints=status_counts["retained-entrypoint"],
        public_entrypoints=status_counts["public-entrypoint"],
    )


def collect_runtime_uuid_governance_snapshot(
    *,
    inventory_path: Path = DEFAULT_RUNTIME_UUID_SEAMS_PATH,
) -> RuntimeUuidGovernanceSnapshot:
    """Collect runtime UUID governance counters from the canonical seam inventory."""
    payload = _load_yaml_mapping(inventory_path)
    seams = payload.get("seams", [])
    if not isinstance(seams, list):
        raise ValueError(f"{inventory_path}: expected seams list")
    normalized = [entry for entry in seams if isinstance(entry, dict)]
    return RuntimeUuidGovernanceSnapshot(
        runtime_uuid_seam_count=len(normalized),
        replay_critical_uuid_seam_count=sum(
            1 for entry in normalized if entry.get("replay_critical")
        ),
    )


def collect_retirement_governance_snapshot(
    *,
    repo_root: Path = _REPO_ROOT,
) -> RetirementGovernanceSnapshot:
    """Collect retirement/dead-code governance counters from the live inventory."""
    inventory = build_dead_code_inventory(repo_root)
    summary = inventory.get("summary", {})
    if not isinstance(summary, dict):
        raise ValueError("Dead-code inventory summary must be a mapping")
    return RetirementGovernanceSnapshot(
        triaged_entry_count=int(summary["triaged_entry_count"]),
        repo_wide_zero_import_candidate_count=int(
            summary["repo_wide_zero_import_candidate_count"]
        ),
        repo_wide_classified_zero_import_candidate_count=int(
            summary["repo_wide_classified_zero_import_candidate_count"]
        ),
        repo_wide_untriaged_zero_import_candidate_count=int(
            summary["repo_wide_untriaged_zero_import_candidate_count"]
        ),
        repo_wide_owner_test_anchored_candidate_count=int(
            summary["repo_wide_owner_test_anchored_candidate_count"]
        ),
        repo_wide_candidates_without_owner_tests_count=int(
            summary["repo_wide_candidates_without_owner_tests_count"]
        ),
        repo_wide_non_static_reachability_candidate_count=int(
            summary["repo_wide_non_static_reachability_candidate_count"]
        ),
        triaged_retained_owner_test_anchored_count=int(
            summary["triaged_retained_owner_test_anchored_count"]
        ),
        triaged_retained_without_owner_tests_count=int(
            summary["triaged_retained_without_owner_tests_count"]
        ),
    )


def collect_test_governance_snapshot(
    *,
    repo_root: Path = _REPO_ROOT,
) -> TestGovernanceDebtSnapshot:
    """Collect static test-governance counters from the cached governance scanner."""
    report = collect_test_governance_report(repo_root)
    return TestGovernanceDebtSnapshot(
        compatibility_test_files=int(report["compatibility_test_files"]),
        refined_assertless_tests=int(report["refined_assertless_tests"]),
        markerless_test_functions=int(report["markerless_test_functions"]),
        duplicate_test_names=int(report["duplicate_test_names"]),
        duplicate_test_name_occurrences=int(report["duplicate_test_name_occurrences"]),
        uuid4_call_sites=int(report["uuid4_call_sites"]),
        date_today_call_sites=int(report["date_today_call_sites"]),
    )


def collect_debt_governance_snapshot(
    *,
    registry_path: Path = DEFAULT_REGISTRY_PATH,
    runtime_uuid_inventory_path: Path = DEFAULT_RUNTIME_UUID_SEAMS_PATH,
    repo_root: Path = _REPO_ROOT,
) -> DebtGovernanceSnapshot:
    """Collect the unified debt-governance snapshot used by CI reports."""
    compatibility_surface = collect_compatibility_surface_snapshot(
        registry_path=registry_path
    )
    return DebtGovernanceSnapshot(
        compatibility_surface=compatibility_surface,
        runtime_uuid=collect_runtime_uuid_governance_snapshot(
            inventory_path=runtime_uuid_inventory_path
        ),
        retirement=collect_retirement_governance_snapshot(repo_root=repo_root),
        test_governance=collect_test_governance_snapshot(repo_root=repo_root),
    )


def render_compatibility_surface_section(
    snapshot: CompatibilitySurfaceSnapshot, *, heading: str
) -> str:
    """Render a markdown section for CI summaries and weekly reports."""
    return "\n".join(
        [
            heading,
            f"- curated_inventory_rows: `{snapshot.curated_inventory_rows}`",
            f"- measured_tracked_modules: `{snapshot.measured_tracked_modules}`",
            f"- measured_only_modules: `{snapshot.measured_only_modules}`",
            f"- deprecated_warn_modules: `{snapshot.deprecated_warn_modules}`",
            f"- compat_shim_modules: `{snapshot.compat_shim_modules}`",
            f"- mixed_modules: `{snapshot.mixed_modules}`",
            f"- retained_entrypoints: `{snapshot.retained_entrypoints}`",
            f"- public_entrypoints: `{snapshot.public_entrypoints}`",
        ]
    )


def render_debt_governance_section(
    snapshot: DebtGovernanceSnapshot, *, heading: str
) -> str:
    """Render a markdown section for the unified debt-governance snapshot."""
    return "\n".join(
        [
            heading,
            "### Compatibility Surface",
            f"- curated_inventory_rows: `{snapshot.compatibility_surface.curated_inventory_rows}`",
            f"- measured_tracked_modules: `{snapshot.compatibility_surface.measured_tracked_modules}`",
            f"- measured_only_modules: `{snapshot.compatibility_surface.measured_only_modules}`",
            f"- deprecated_warn_modules: `{snapshot.compatibility_surface.deprecated_warn_modules}`",
            f"- compat_shim_modules: `{snapshot.compatibility_surface.compat_shim_modules}`",
            f"- mixed_modules: `{snapshot.compatibility_surface.mixed_modules}`",
            f"- retained_entrypoints: `{snapshot.compatibility_surface.retained_entrypoints}`",
            f"- public_entrypoints: `{snapshot.compatibility_surface.public_entrypoints}`",
            "### Runtime UUID Governance",
            f"- runtime_uuid_seam_count: `{snapshot.runtime_uuid.runtime_uuid_seam_count}`",
            f"- replay_critical_uuid_seam_count: `{snapshot.runtime_uuid.replay_critical_uuid_seam_count}`",
            "### Retirement Governance",
            f"- triaged_entry_count: `{snapshot.retirement.triaged_entry_count}`",
            f"- repo_wide_zero_import_candidate_count: `{snapshot.retirement.repo_wide_zero_import_candidate_count}`",
            (
                "- repo_wide_classified_zero_import_candidate_count: `"
                f"{snapshot.retirement.repo_wide_classified_zero_import_candidate_count}`"
            ),
            (
                "- repo_wide_untriaged_zero_import_candidate_count: `"
                f"{snapshot.retirement.repo_wide_untriaged_zero_import_candidate_count}`"
            ),
            (
                "- repo_wide_owner_test_anchored_candidate_count: `"
                f"{snapshot.retirement.repo_wide_owner_test_anchored_candidate_count}`"
            ),
            (
                "- repo_wide_candidates_without_owner_tests_count: `"
                f"{snapshot.retirement.repo_wide_candidates_without_owner_tests_count}`"
            ),
            (
                "- repo_wide_non_static_reachability_candidate_count: `"
                f"{snapshot.retirement.repo_wide_non_static_reachability_candidate_count}`"
            ),
            (
                "- triaged_retained_owner_test_anchored_count: `"
                f"{snapshot.retirement.triaged_retained_owner_test_anchored_count}`"
            ),
            (
                "- triaged_retained_without_owner_tests_count: `"
                f"{snapshot.retirement.triaged_retained_without_owner_tests_count}`"
            ),
            "### Test Governance",
            f"- compatibility_test_files: `{snapshot.test_governance.compatibility_test_files}`",
            f"- refined_assertless_tests: `{snapshot.test_governance.refined_assertless_tests}`",
            f"- markerless_test_functions: `{snapshot.test_governance.markerless_test_functions}`",
            f"- duplicate_test_names: `{snapshot.test_governance.duplicate_test_names}`",
            (
                "- duplicate_test_name_occurrences: `"
                f"{snapshot.test_governance.duplicate_test_name_occurrences}`"
            ),
            f"- uuid4_call_sites: `{snapshot.test_governance.uuid4_call_sites}`",
            f"- date_today_call_sites: `{snapshot.test_governance.date_today_call_sites}`",
        ]
    )
