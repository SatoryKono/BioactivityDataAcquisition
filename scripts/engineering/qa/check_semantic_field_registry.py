#!/usr/bin/env python3
"""Validate canonical semantic field registry coverage."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(repo_root))
    sys.path.insert(0, str(repo_root / "src"))

from bioetl.domain.mapping.molecule_fields import MOLECULE_FIELD_MAPPING
from bioetl.domain.mapping.publication_fields import PUBLICATION_FIELD_MAPPING
from bioetl.domain.registry.field_aliases import MOLECULE_FIELD_ALIASES
from bioetl.domain.registry.semantic_fields import SemanticFieldRegistry
from bioetl.infrastructure.config.semantic_field_registry_loader import (
    SemanticFieldRegistryLoader,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
GENERIC_LEXICAL_COLLISIONS = frozenset(
    {"type", "value", "score", "description", "relation", "source"}
)


@dataclass(frozen=True, slots=True)
class RegistryFinding:
    """One semantic field registry validation finding."""

    kind: str
    field: str
    expected: str
    source: str
    message: str

    def as_dict(self) -> dict[str, str]:
        """Return a JSON-serializable finding payload."""
        return {
            "kind": self.kind,
            "field": self.field,
            "expected": self.expected,
            "source": self.source,
            "message": self.message,
        }


def _resolve_registry_cluster(
    registry: SemanticFieldRegistry,
    *,
    raw_name: str,
    canonical_name: str,
    source: str,
) -> RegistryFinding | None:
    canonical_cluster = registry.get_by_canonical_name(canonical_name)
    if canonical_cluster is None:
        return RegistryFinding(
            kind="missing_canonical_cluster",
            field=raw_name,
            expected=canonical_name,
            source=source,
            message=f"{source} maps {raw_name!r} to unregistered {canonical_name!r}",
        )

    if raw_name == canonical_name:
        return None

    alias_cluster = registry.get_by_legacy_name(raw_name)
    if alias_cluster is None:
        alias_cluster = registry.get_by_raw_provider_name(raw_name)
    if alias_cluster == canonical_cluster:
        return None

    return RegistryFinding(
        kind="missing_alias_binding",
        field=raw_name,
        expected=canonical_name,
        source=source,
        message=(
            f"{source} alias {raw_name!r} must resolve to canonical {canonical_name!r}"
        ),
    )


def _collect_publication_mapping_findings(
    registry: SemanticFieldRegistry,
) -> list[RegistryFinding]:
    findings: list[RegistryFinding] = []
    for provider, mapping in PUBLICATION_FIELD_MAPPING.items():
        for raw_name, canonical_name in mapping.items():
            finding = _resolve_registry_cluster(
                registry,
                raw_name=raw_name,
                canonical_name=canonical_name,
                source=f"PUBLICATION_FIELD_MAPPING[{provider}]",
            )
            if finding is not None:
                findings.append(finding)
    return findings


def _collect_molecule_mapping_findings(
    registry: SemanticFieldRegistry,
) -> list[RegistryFinding]:
    findings: list[RegistryFinding] = []
    for provider, mapping in MOLECULE_FIELD_MAPPING.items():
        for raw_name, canonical_name in mapping.items():
            finding = _resolve_registry_cluster(
                registry,
                raw_name=raw_name,
                canonical_name=canonical_name,
                source=f"MOLECULE_FIELD_MAPPING[{provider}]",
            )
            if finding is not None:
                findings.append(finding)
    return findings


def _collect_molecule_alias_findings(
    registry: SemanticFieldRegistry,
) -> list[RegistryFinding]:
    findings: list[RegistryFinding] = []
    for field_alias in MOLECULE_FIELD_ALIASES:
        for provider, raw_name in field_alias.provider_aliases.items():
            finding = _resolve_registry_cluster(
                registry,
                raw_name=raw_name,
                canonical_name=field_alias.canonical_name,
                source=f"MOLECULE_FIELD_ALIASES[{provider}]",
            )
            if finding is not None:
                findings.append(finding)
    return findings


def validate_registry(
    configs_root: Path = REPO_ROOT / "configs",
) -> tuple[RegistryFinding, ...]:
    """Return semantic field registry coverage findings."""
    registry = SemanticFieldRegistryLoader(configs_root).load()

    findings: list[RegistryFinding] = []
    findings.extend(_collect_publication_mapping_findings(registry))
    findings.extend(_collect_molecule_mapping_findings(registry))
    findings.extend(_collect_molecule_alias_findings(registry))

    for field_name in sorted(GENERIC_LEXICAL_COLLISIONS):
        if registry.get_by_canonical_name(field_name) is None:
            continue
        findings.append(
            RegistryFinding(
                kind="generic_collision_canonicalized",
                field=field_name,
                expected="<not registered>",
                source="GENERIC_LEXICAL_COLLISIONS",
                message=(
                    f"generic lexical collision {field_name!r} must not be "
                    "canonicalized without owner review"
                ),
            )
        )

    return tuple(findings)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate canonical semantic field registry coverage.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail with a non-zero exit code when findings are present",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit machine-readable validation output",
    )
    parser.add_argument(
        "--configs-root",
        type=Path,
        default=REPO_ROOT / "configs",
        help="configs root containing field_registry/canonical_registry.json",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    findings = validate_registry(args.configs_root)
    if args.json:
        payload = {
            "ok": not findings,
            "finding_count": len(findings),
            "findings": [finding.as_dict() for finding in findings],
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
    elif findings:
        print("[semantic-field-registry] validation failed")
        for finding in findings:
            print(f"- {finding.message}")
    else:
        print("[semantic-field-registry] ok")

    return 1 if args.check and findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
