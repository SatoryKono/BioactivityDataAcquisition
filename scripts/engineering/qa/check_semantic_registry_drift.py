#!/usr/bin/env python3
"""Validate generated semantic registry drift candidates."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]

if __package__ in {None, ""}:
    sys.path.insert(0, str(REPO_ROOT))
    sys.path.insert(0, str(REPO_ROOT / "src"))

from bioetl.domain.mapping.molecule_fields import MOLECULE_FIELD_MAPPING
from bioetl.domain.mapping.publication_fields import (
    PUBLICATION_FIELD_MAPPING,
)
from bioetl.domain.registry.field_aliases import MOLECULE_FIELD_ALIASES
from bioetl.domain.registry.semantic_fields import (
    SemanticFieldRegistry,
)
from bioetl.infrastructure.config.semantic_field_registry_loader import (
    SemanticFieldRegistryLoader,
)

DEFAULT_AUDIT_CLUSTER_REGISTRY = (
    REPO_ROOT
    / "reports"
    / "semantic_pipeline_audit"
    / "semantic_cluster_registry_2026-07-01.json"
)
DEFAULT_REVIEW_REGISTRY = (
    REPO_ROOT / "configs" / "field_registry" / "semantic_audit_review_registry.yaml"
)
NON_BLOCKING_AUDIT_STATUSES = frozenset({"PARTIAL", "WEAK", "CONFLICTING"})
MAX_WARNING_LINES = 20


@dataclass(frozen=True, slots=True)
class DriftCandidate:
    """One generated semantic registry coverage candidate."""

    canonical_name: str
    raw_name: str
    source: str
    relation: str

    def as_dict(self) -> dict[str, str]:
        """Return a JSON-serializable candidate payload."""
        return {
            "canonical_name": self.canonical_name,
            "raw_name": self.raw_name,
            "source": self.source,
            "relation": self.relation,
        }


@dataclass(frozen=True, slots=True)
class DriftFinding:
    """One blocking semantic registry drift finding."""

    kind: str
    canonical_name: str
    raw_name: str
    source: str
    message: str

    def as_dict(self) -> dict[str, str]:
        """Return a JSON-serializable finding payload."""
        return {
            "kind": self.kind,
            "canonical_name": self.canonical_name,
            "raw_name": self.raw_name,
            "source": self.source,
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class DriftWarning:
    """One non-blocking semantic registry drift warning."""

    kind: str
    cluster_id: str
    canonical_name: str
    status: str
    source: str
    message: str

    def as_dict(self) -> dict[str, str]:
        """Return a JSON-serializable warning payload."""
        return {
            "kind": self.kind,
            "cluster_id": self.cluster_id,
            "canonical_name": self.canonical_name,
            "status": self.status,
            "source": self.source,
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class DriftValidationResult:
    """Semantic registry drift validation result."""

    candidates: tuple[DriftCandidate, ...]
    findings: tuple[DriftFinding, ...]
    warnings: tuple[DriftWarning, ...]

    @property
    def ok(self) -> bool:
        """Return whether no blocking drift findings were found."""
        return not self.findings


def _load_yaml(path: Path, *, root: Path | None = None) -> dict[str, Any]:
    from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_output_path

    path = resolve_output_path(path, root=root or REPO_ROOT)
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        return payload
    raise ValueError(f"Expected YAML mapping in {path}")


def _load_json(path: Path, *, root: Path | None = None) -> dict[str, Any]:
    from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_output_path

    path = resolve_output_path(path, root=root or REPO_ROOT)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        return payload
    raise ValueError(f"Expected JSON mapping in {path}")


def _candidate(
    *,
    canonical_name: str,
    raw_name: str,
    source: str,
) -> DriftCandidate:
    relation = "identity" if raw_name == canonical_name else "alias"
    return DriftCandidate(
        canonical_name=canonical_name,
        raw_name=raw_name,
        source=source,
        relation=relation,
    )


def _iter_publication_mapping_candidates() -> tuple[DriftCandidate, ...]:
    candidates: list[DriftCandidate] = []
    for provider, mapping in PUBLICATION_FIELD_MAPPING.items():
        for raw_name, canonical_name in mapping.items():
            candidates.append(
                _candidate(
                    canonical_name=canonical_name,
                    raw_name=raw_name,
                    source=f"PUBLICATION_FIELD_MAPPING[{provider}]",
                )
            )
    return tuple(candidates)


def _iter_molecule_mapping_candidates() -> tuple[DriftCandidate, ...]:
    candidates: list[DriftCandidate] = []
    for provider, mapping in MOLECULE_FIELD_MAPPING.items():
        for raw_name, canonical_name in mapping.items():
            candidates.append(
                _candidate(
                    canonical_name=canonical_name,
                    raw_name=raw_name,
                    source=f"MOLECULE_FIELD_MAPPING[{provider}]",
                )
            )
    return tuple(candidates)


def _iter_molecule_alias_candidates() -> tuple[DriftCandidate, ...]:
    candidates: list[DriftCandidate] = []
    for field_alias in MOLECULE_FIELD_ALIASES:
        for provider, raw_name in field_alias.provider_aliases.items():
            candidates.append(
                _candidate(
                    canonical_name=field_alias.canonical_name,
                    raw_name=raw_name,
                    source=f"MOLECULE_FIELD_ALIASES[{provider}]",
                )
            )
    return tuple(candidates)


def discover_exact_registry_candidates(
    repo_root: Path = REPO_ROOT,
) -> tuple[DriftCandidate, ...]:
    """Return exact candidates from runtime mappings and the domain alias registry."""
    _ = repo_root  # Kept for CLI/test API compatibility.
    candidates: list[DriftCandidate] = []
    candidates.extend(_iter_publication_mapping_candidates())
    candidates.extend(_iter_molecule_mapping_candidates())
    candidates.extend(_iter_molecule_alias_candidates())
    return tuple(candidates)


def _resolve_candidate(
    registry: SemanticFieldRegistry,
    candidate: DriftCandidate,
) -> DriftFinding | None:
    canonical_cluster = registry.get_by_canonical_name(candidate.canonical_name)
    if canonical_cluster is None:
        return DriftFinding(
            kind="missing_canonical_cluster",
            canonical_name=candidate.canonical_name,
            raw_name=candidate.raw_name,
            source=candidate.source,
            message=(
                f"{candidate.source} maps {candidate.raw_name!r} to unregistered "
                f"canonical field {candidate.canonical_name!r}"
            ),
        )

    if candidate.raw_name == candidate.canonical_name:
        return None

    alias_cluster = registry.get_by_legacy_name(candidate.raw_name)
    if alias_cluster is None:
        alias_cluster = registry.get_by_raw_provider_name(candidate.raw_name)
    if alias_cluster == canonical_cluster:
        return None

    return DriftFinding(
        kind="missing_alias_binding",
        canonical_name=candidate.canonical_name,
        raw_name=candidate.raw_name,
        source=candidate.source,
        message=(
            f"{candidate.source} alias {candidate.raw_name!r} must resolve to "
            f"canonical field {candidate.canonical_name!r}"
        ),
    )


def _iter_non_blocking_audit_warnings(
    repo_root: Path,
    audit_cluster_registry: Path,
    review_registry: Path,
) -> tuple[DriftWarning, ...]:
    path = audit_cluster_registry
    if not path.is_absolute():
        path = repo_root / path
    if not path.exists():
        return ()

    payload = _load_json(path)
    review_payload = _load_yaml(
        review_registry
        if review_registry.is_absolute()
        else repo_root / review_registry
    )
    clusters = payload.get("clusters", [])
    if not isinstance(clusters, list):
        return ()

    warnings: list[DriftWarning] = []
    source = (
        path.relative_to(repo_root).as_posix()
        if path.is_relative_to(repo_root)
        else path.as_posix()
    )
    for cluster in clusters:
        if not isinstance(cluster, dict):
            continue
        status = cluster.get("semantic_default") or cluster.get("semantic_status")
        if not isinstance(status, str):
            continue
        status = status.upper()
        if status not in NON_BLOCKING_AUDIT_STATUSES:
            continue

        cluster_id = str(cluster.get("cluster_id") or "<unknown>")
        if _warning_reviewed(
            review_payload,
            cluster_id=cluster_id,
            status=status,
        ):
            continue
        canonical_name = str(
            cluster.get("canonical_field")
            or cluster.get("canonical_name")
            or "<unknown>"
        )
        kind_by_status = {
            "CONFLICTING": "conflicting_cluster_requires_owner_review",
            "PARTIAL": "partial_identity_cluster_requires_owner_review",
            "WEAK": "weak_same_name_cluster",
        }
        warnings.append(
            DriftWarning(
                kind=kind_by_status.get(status, "non_blocking_audit_cluster"),
                cluster_id=cluster_id,
                canonical_name=canonical_name,
                status=status,
                source=source,
                message=(
                    f"{status} audit cluster {cluster_id!r} for {canonical_name!r} "
                    "is intentionally non-blocking until owner review classifies it"
                ),
            )
        )
    return tuple(warnings)


def _warning_reviewed(
    review_payload: dict[str, Any],
    *,
    cluster_id: str,
    status: str,
) -> bool:
    for section in ("semantic_reviews", "warning_reviews"):
        reviews = review_payload.get(section, [])
        if not isinstance(reviews, list):
            continue
        for review in reviews:
            if not isinstance(review, dict):
                continue
            statuses = review.get("semantic_statuses", [])
            if not isinstance(statuses, list) or status not in {
                str(item).upper() for item in statuses
            }:
                continue
            clusters = review.get("clusters")
            if clusters is None:
                return True
            if isinstance(clusters, list) and cluster_id in {
                str(item) for item in clusters
            }:
                return True
    return False


def validate_semantic_registry_drift(
    repo_root: Path = REPO_ROOT,
    *,
    audit_cluster_registry: Path = DEFAULT_AUDIT_CLUSTER_REGISTRY,
    review_registry: Path = DEFAULT_REVIEW_REGISTRY,
) -> DriftValidationResult:
    """Return blocking findings and non-blocking warnings for registry drift."""
    registry = SemanticFieldRegistryLoader(repo_root / "configs").load()
    candidates = discover_exact_registry_candidates(repo_root)
    findings = tuple(
        finding
        for candidate in candidates
        if (finding := _resolve_candidate(registry, candidate)) is not None
    )
    warnings = _iter_non_blocking_audit_warnings(
        repo_root,
        audit_cluster_registry,
        review_registry,
    )
    return DriftValidationResult(
        candidates=candidates,
        findings=findings,
        warnings=warnings,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate generated semantic registry drift candidates.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail with a non-zero exit code when blocking findings are present",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit machine-readable validation output",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=REPO_ROOT,
        help="repository root containing configs, src and reports",
    )
    parser.add_argument(
        "--audit-cluster-registry",
        type=Path,
        default=DEFAULT_AUDIT_CLUSTER_REGISTRY,
        help="semantic audit cluster registry used for non-blocking warnings",
    )
    parser.add_argument(
        "--review-registry",
        type=Path,
        default=DEFAULT_REVIEW_REGISTRY,
        help="semantic audit review registry used to suppress reviewed warnings",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    result = validate_semantic_registry_drift(
        args.repo_root,
        audit_cluster_registry=args.audit_cluster_registry,
        review_registry=args.review_registry,
    )
    if args.json:
        payload = {
            "ok": result.ok,
            "candidate_count": len(result.candidates),
            "blocking_finding_count": len(result.findings),
            "warning_count": len(result.warnings),
            "findings": [finding.as_dict() for finding in result.findings],
            "warnings": [warning.as_dict() for warning in result.warnings],
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
    elif result.findings:
        print("[semantic-registry-drift] blocking drift detected")
        for finding in result.findings:
            print(f"- {finding.message}")
        if result.warnings:
            print(
                "[semantic-registry-drift] "
                f"{len(result.warnings)} non-blocking audit warnings suppressed"
            )
    else:
        print(
            "[semantic-registry-drift] ok "
            f"({len(result.candidates)} exact candidates checked)"
        )
        if result.warnings:
            print(
                "[semantic-registry-drift] "
                f"{len(result.warnings)} non-blocking audit warnings"
            )
            for warning in result.warnings[:MAX_WARNING_LINES]:
                print(f"- {warning.message}")
            remaining = len(result.warnings) - MAX_WARNING_LINES
            if remaining > 0:
                print(f"- ... {remaining} more warnings")

    return 1 if args.check and result.findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
