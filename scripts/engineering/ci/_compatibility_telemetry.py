"""Compatibility-surface telemetry helpers for CI quality reporting."""

from __future__ import annotations

import json
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, cast

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
    from scripts.engineering.ci._compatibility_registry import (  # type: ignore[import-not-found]
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

GovernanceArtifactSource = Literal["live", "committed"]


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


def _load_json_mapping(path: Path) -> dict[str, Any]:
    """Load a committed JSON object or fail closed."""
    if not path.is_file():
        raise FileNotFoundError(f"missing committed governance artifact: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected JSON object")
    return cast(dict[str, Any], payload)


def _require_int_field(mapping: Mapping[str, Any], key: str) -> int:
    """Return a required integer field or fail closed."""
    if key not in mapping:
        raise ValueError(f"missing required integer field {key!r}")
    value = mapping[key]
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{key} must be int, got {type(value)!r}")
    return value


def _retirement_from_summary(summary: object) -> RetirementGovernanceSnapshot:
    """Map a dead-code inventory summary into the compact CI snapshot."""
    if not isinstance(summary, dict):
        raise ValueError("Dead-code inventory summary must be a mapping")
    return RetirementGovernanceSnapshot(
        triaged_entry_count=_require_int_field(summary, "triaged_entry_count"),
        repo_wide_zero_import_candidate_count=_require_int_field(
            summary, "repo_wide_zero_import_candidate_count"
        ),
        repo_wide_classified_zero_import_candidate_count=_require_int_field(
            summary, "repo_wide_classified_zero_import_candidate_count"
        ),
        repo_wide_untriaged_zero_import_candidate_count=_require_int_field(
            summary, "repo_wide_untriaged_zero_import_candidate_count"
        ),
        repo_wide_owner_test_anchored_candidate_count=_require_int_field(
            summary, "repo_wide_owner_test_anchored_candidate_count"
        ),
        repo_wide_candidates_without_owner_tests_count=_require_int_field(
            summary, "repo_wide_candidates_without_owner_tests_count"
        ),
        repo_wide_non_static_reachability_candidate_count=_require_int_field(
            summary, "repo_wide_non_static_reachability_candidate_count"
        ),
        triaged_retained_owner_test_anchored_count=_require_int_field(
            summary, "triaged_retained_owner_test_anchored_count"
        ),
        triaged_retained_without_owner_tests_count=_require_int_field(
            summary, "triaged_retained_without_owner_tests_count"
        ),
    )


def _test_governance_from_report(report: object) -> TestGovernanceDebtSnapshot:
    """Map a test-governance report object into the compact CI snapshot."""
    if not isinstance(report, dict):
        raise ValueError("Test-governance report must be a mapping")
    return TestGovernanceDebtSnapshot(
        compatibility_test_files=_require_int_field(report, "compatibility_test_files"),
        refined_assertless_tests=_require_int_field(report, "refined_assertless_tests"),
        markerless_test_functions=_require_int_field(
            report, "markerless_test_functions"
        ),
        duplicate_test_names=_require_int_field(report, "duplicate_test_names"),
        duplicate_test_name_occurrences=_require_int_field(
            report, "duplicate_test_name_occurrences"
        ),
        uuid4_call_sites=_require_int_field(report, "uuid4_call_sites"),
        date_today_call_sites=_require_int_field(report, "date_today_call_sites"),
    )


def _validate_artifact_source(artifact_source: str) -> GovernanceArtifactSource:
    if artifact_source in {"live", "committed"}:
        return artifact_source
    raise ValueError(
        f"artifact_source must be 'live' or 'committed', got {artifact_source!r}"
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
    artifact_source: str = "live",
) -> RetirementGovernanceSnapshot:
    """Collect retirement/dead-code governance counters.

    ``live`` rebuilds the inventory. ``committed`` reads
    ``reports/quality/dead-code-inventory.json`` and fails closed when the
    artifact is missing or incomplete. Architecture tests remain the live
    drift owner for that file.
    """
    source = _validate_artifact_source(artifact_source)
    if source == "committed":
        payload = _load_json_mapping(
            repo_root / "reports" / "quality" / "dead-code-inventory.json"
        )
        return _retirement_from_summary(payload.get("summary"))
    inventory = build_dead_code_inventory(repo_root)
    return _retirement_from_summary(inventory.get("summary"))


def collect_test_governance_snapshot(
    *,
    repo_root: Path = _REPO_ROOT,
    artifact_source: str = "live",
) -> TestGovernanceDebtSnapshot:
    """Collect static test-governance counters.

    ``live`` uses the governance scanner (which may reuse a fresh committed
    artifact after hashing the source tree). ``committed`` reads
    ``reports/quality/test-governance-current.json`` without a live rescan
    and fails closed when the artifact is missing or incomplete.
    """
    source = _validate_artifact_source(artifact_source)
    if source == "committed":
        payload = _load_json_mapping(
            repo_root / "reports" / "quality" / "test-governance-current.json"
        )
        return _test_governance_from_report(payload.get("report"))
    payload = collect_test_governance_report(repo_root)
    return _test_governance_from_report(payload["report"])


def collect_debt_governance_snapshot(
    *,
    registry_path: Path = DEFAULT_REGISTRY_PATH,
    runtime_uuid_inventory_path: Path = DEFAULT_RUNTIME_UUID_SEAMS_PATH,
    repo_root: Path = _REPO_ROOT,
    artifact_source: str = "live",
) -> DebtGovernanceSnapshot:
    """Collect the unified debt-governance snapshot used by CI reports."""
    source = _validate_artifact_source(artifact_source)
    compatibility_surface = collect_compatibility_surface_snapshot(
        registry_path=registry_path
    )
    return DebtGovernanceSnapshot(
        compatibility_surface=compatibility_surface,
        runtime_uuid=collect_runtime_uuid_governance_snapshot(
            inventory_path=runtime_uuid_inventory_path
        ),
        retirement=collect_retirement_governance_snapshot(
            repo_root=repo_root, artifact_source=source
        ),
        test_governance=collect_test_governance_snapshot(
            repo_root=repo_root, artifact_source=source
        ),
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
