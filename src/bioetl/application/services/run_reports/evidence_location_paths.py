"""Evidence-location catalog paths and DI alias registry (RF-002).

Application code receives absolute alias bases via composition/bootstrap —
never by reading process environment maps inside this module.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from bioetl.domain.control_plane.run_evidence_location import (
    DEFAULT_EVIDENCE_ROOT_ALIAS,
    EvidenceLocationInvalidError,
    EvidenceLocationKind,
    canonicalize_relative_data_root,
)

__all__ = [
    "EVIDENCE_LOCATIONS_DIRNAME",
    "EvidenceRootAliasRegistry",
    "default_evidence_root_alias_registry",
    "resolve_evidence_location_path",
    "resolve_evidence_locations_root",
]

# Additive catalog of data-root locators (RF-002). Lives beside pipeline/workflow
# report trees; does not rewrite immutable report snapshots.
EVIDENCE_LOCATIONS_DIRNAME = "_evidence-locations"


def _safe_location_segment(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in value)
    return cleaned[:120] or "unknown"


@dataclass(frozen=True, slots=True)
class EvidenceRootAliasRegistry:
    """Trusted absolute bases for evidence root aliases (DI-injected)."""

    aliases: Mapping[str, Path]

    def absolute_base(self, alias: str) -> Path:
        """Return the absolute base for ``alias`` or raise on unknown alias."""
        key = str(alias or "").strip()
        if key not in self.aliases:
            raise EvidenceLocationInvalidError(f"unknown evidence root alias: {key}")
        base = Path(self.aliases[key])
        if not base.is_absolute():
            raise EvidenceLocationInvalidError(
                f"evidence root alias base must be absolute: {key}"
            )
        return base

    def resolve_data_root(self, *, root_alias: str, relative_data_root: str) -> Path:
        """Join alias base with a validated relative data root."""
        relative = canonicalize_relative_data_root(relative_data_root)
        base = self.absolute_base(root_alias)
        if relative == ".":
            return base
        return base.joinpath(*relative.split("/"))


def default_evidence_root_alias_registry(
    *, dashboard_data_root: Path
) -> EvidenceRootAliasRegistry:
    """Build the v1 alias registry with the standard ``dashboard_data`` binding."""
    root = Path(dashboard_data_root)
    if not root.is_absolute():
        raise EvidenceLocationInvalidError(
            "dashboard_data alias base must be an absolute path"
        )
    return EvidenceRootAliasRegistry(aliases={DEFAULT_EVIDENCE_ROOT_ALIAS: root})


def resolve_evidence_locations_root(*, report_root: Path | None = None) -> Path:
    """Catalog root: ``reports/run-reports/_evidence-locations``."""
    # Keep the same default as ``paths.resolve_report_root`` without importing
    # that module (avoids an import cycle with the paths facade re-exports).
    base = (
        Path(report_root)
        if report_root is not None
        else Path("reports") / "run-reports"
    )
    return base / EVIDENCE_LOCATIONS_DIRNAME


def resolve_evidence_location_path(
    *,
    kind: EvidenceLocationKind | str,
    owner: str,
    run_id: str,
    report_root: Path | None = None,
) -> Path:
    """Path of one location record under the evidence-locations catalog."""
    kind_value = (
        kind.value if isinstance(kind, EvidenceLocationKind) else str(kind).strip()
    )
    if kind_value not in {
        EvidenceLocationKind.PIPELINE.value,
        EvidenceLocationKind.WORKFLOW.value,
    }:
        raise EvidenceLocationInvalidError(
            f"unsupported evidence location kind: {kind_value}"
        )
    return (
        resolve_evidence_locations_root(report_root=report_root)
        / kind_value
        / _safe_location_segment(owner)
        / f"{_safe_location_segment(run_id)}.json"
    )
