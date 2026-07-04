#!/usr/bin/env python3
"""Validate ownership for generic lexical fields in semantic surfaces."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OWNERSHIP_PATH = (
    REPO_ROOT / "configs" / "field_registry" / "generic_field_ownership.yaml"
)
DEFAULT_REGISTRY_PATH = (
    REPO_ROOT / "configs" / "field_registry" / "canonical_registry.json"
)
GOLD_CONTRACT_DIR = REPO_ROOT / "docs" / "04-reference" / "contracts" / "gold"
COMPOSITE_CONFIG_DIR = REPO_ROOT / "configs" / "composites"
COMPOSITE_FIELD_GROUP_DIR = COMPOSITE_CONFIG_DIR / "field_groups"
SYSTEM_SCOPED_GENERIC_FIELDS = frozenset({"_source"})


@dataclass(frozen=True, slots=True)
class GenericFieldOccurrence:
    """One generic lexical field occurrence in a governed surface."""

    surface: str
    path: str
    field: str
    context: str


@dataclass(frozen=True, slots=True)
class GenericFieldFinding:
    """One generic field ownership validation finding."""

    kind: str
    surface: str
    path: str
    field: str
    context: str
    message: str

    def as_dict(self) -> dict[str, str]:
        """Return a JSON-serializable finding payload."""
        return {
            "kind": self.kind,
            "surface": self.surface,
            "path": self.path,
            "field": self.field,
            "context": self.context,
            "message": self.message,
        }


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        return payload
    raise ValueError(f"Expected YAML mapping in {path}")


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        return payload
    raise ValueError(f"Expected JSON mapping in {path}")


def _repo_rel(path: Path, repo_root: Path) -> str:
    return path.relative_to(repo_root).as_posix()


def _is_denied_field(field: str, denied_terms: frozenset[str]) -> bool:
    if field in SYSTEM_SCOPED_GENERIC_FIELDS:
        return False
    return field in denied_terms


def _iter_gold_json_occurrences(
    *,
    repo_root: Path,
    denied_terms: frozenset[str],
) -> tuple[GenericFieldOccurrence, ...]:
    occurrences: list[GenericFieldOccurrence] = []
    for contract_path in sorted(
        (repo_root / GOLD_CONTRACT_DIR.relative_to(REPO_ROOT)).glob("*.json")
    ):
        payload = _load_json(contract_path)
        properties = payload.get("properties", {})
        if not isinstance(properties, dict):
            continue
        for field in sorted(properties):
            if isinstance(field, str) and _is_denied_field(field, denied_terms):
                occurrences.append(
                    GenericFieldOccurrence(
                        surface="gold_json_property",
                        path=_repo_rel(contract_path, repo_root),
                        field=field,
                        context="properties",
                    )
                )
    return tuple(occurrences)


def _iter_composite_column_group_occurrences(
    *,
    repo_root: Path,
    denied_terms: frozenset[str],
) -> tuple[GenericFieldOccurrence, ...]:
    occurrences: list[GenericFieldOccurrence] = []
    composite_dir = repo_root / COMPOSITE_CONFIG_DIR.relative_to(REPO_ROOT)
    for config_path in sorted(composite_dir.glob("*.yaml")):
        payload = _load_yaml(config_path)
        composite = payload.get("composite", {})
        merge = composite.get("merge", {}) if isinstance(composite, dict) else {}
        groups = merge.get("column_groups", []) if isinstance(merge, dict) else []
        if not isinstance(groups, list):
            continue
        for group in groups:
            if not isinstance(group, dict):
                continue
            context = str(group.get("name") or "<unnamed>")
            fields = group.get("fields", [])
            if not isinstance(fields, list):
                continue
            for field in fields:
                if isinstance(field, str) and _is_denied_field(field, denied_terms):
                    occurrences.append(
                        GenericFieldOccurrence(
                            surface="composite_column_group_field",
                            path=_repo_rel(config_path, repo_root),
                            field=field,
                            context=context,
                        )
                    )
    return tuple(occurrences)


def _iter_composite_field_group_occurrences(
    *,
    repo_root: Path,
    denied_terms: frozenset[str],
) -> tuple[GenericFieldOccurrence, ...]:
    occurrences: list[GenericFieldOccurrence] = []
    field_group_dir = repo_root / COMPOSITE_FIELD_GROUP_DIR.relative_to(REPO_ROOT)
    if not field_group_dir.exists():
        return tuple(occurrences)
    for config_path in sorted(field_group_dir.glob("*.yaml")):
        payload = _load_yaml(config_path)
        groups = payload.get("groups", [])
        if not isinstance(groups, list):
            continue
        for group in groups:
            if not isinstance(group, dict):
                continue
            context = str(group.get("id") or "<unnamed>")
            fields = group.get("fields", [])
            if not isinstance(fields, list):
                continue
            for field_entry in fields:
                if not isinstance(field_entry, dict):
                    continue
                base_name = field_entry.get("base_name")
                if isinstance(base_name, str) and _is_denied_field(
                    base_name,
                    denied_terms,
                ):
                    occurrences.append(
                        GenericFieldOccurrence(
                            surface="composite_field_group_base_name",
                            path=_repo_rel(config_path, repo_root),
                            field=base_name,
                            context=context,
                        )
                    )
    return tuple(occurrences)


def _iter_canonical_registry_occurrences(
    *,
    repo_root: Path,
    registry_path: Path,
    denied_terms: frozenset[str],
) -> tuple[GenericFieldOccurrence, ...]:
    payload = _load_json(registry_path)
    clusters = payload.get("clusters", [])
    if not isinstance(clusters, list):
        return ()
    occurrences: list[GenericFieldOccurrence] = []
    for cluster in clusters:
        if not isinstance(cluster, dict):
            continue
        canonical_name = cluster.get("canonical_name")
        cluster_id = str(cluster.get("cluster_id") or "<unknown>")
        if isinstance(canonical_name, str) and _is_denied_field(
            canonical_name,
            denied_terms,
        ):
            occurrences.append(
                GenericFieldOccurrence(
                    surface="canonical_registry_cluster",
                    path=_repo_rel(registry_path, repo_root),
                    field=canonical_name,
                    context=cluster_id,
                )
            )
    return tuple(occurrences)


def _ownership_entries(payload: dict[str, Any]) -> tuple[GenericFieldOccurrence, ...]:
    entries = payload.get("entries", [])
    if not isinstance(entries, list):
        return ()
    occurrences: list[GenericFieldOccurrence] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        surface = entry.get("surface")
        path = entry.get("path")
        context = entry.get("context")
        fields = entry.get("fields", [])
        if not (
            isinstance(surface, str)
            and isinstance(path, str)
            and isinstance(context, str)
            and isinstance(fields, list)
        ):
            continue
        for field in fields:
            if isinstance(field, str):
                occurrences.append(
                    GenericFieldOccurrence(
                        surface=surface,
                        path=path,
                        field=field,
                        context=context,
                    )
                )
    return tuple(occurrences)


def _entry_metadata_findings(
    payload: dict[str, Any],
    *,
    ownership_path: Path,
) -> list[GenericFieldFinding]:
    entries = payload.get("entries", [])
    if not isinstance(entries, list):
        return [
            GenericFieldFinding(
                kind="invalid_ownership_entries",
                surface="ownership_registry",
                path=ownership_path.as_posix(),
                field="entries",
                context="<root>",
                message="generic field ownership registry must define entries list",
            )
        ]
    findings: list[GenericFieldFinding] = []
    required = ("owner", "semantic_role", "rationale")
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            findings.append(
                GenericFieldFinding(
                    kind="invalid_ownership_entry",
                    surface="ownership_registry",
                    path=ownership_path.as_posix(),
                    field=str(index),
                    context="<entry>",
                    message=f"ownership entry {index} must be a mapping",
                )
            )
            continue
        for key in required:
            value = entry.get(key)
            if isinstance(value, str) and value.strip():
                continue
            findings.append(
                GenericFieldFinding(
                    kind="missing_ownership_metadata",
                    surface=str(entry.get("surface") or "ownership_registry"),
                    path=str(entry.get("path") or ownership_path.as_posix()),
                    field=str(entry.get("fields") or index),
                    context=str(entry.get("context") or "<entry>"),
                    message=f"ownership entry {index} is missing non-empty {key!r}",
                )
            )
    return findings


def _finding_for_unowned(
    occurrence: GenericFieldOccurrence,
) -> GenericFieldFinding:
    return GenericFieldFinding(
        kind="unowned_generic_field",
        surface=occurrence.surface,
        path=occurrence.path,
        field=occurrence.field,
        context=occurrence.context,
        message=(
            f"{occurrence.surface} {occurrence.path}:{occurrence.context} uses "
            f"generic field {occurrence.field!r} without owner-approved semantics"
        ),
    )


def _finding_for_stale_ownership(
    occurrence: GenericFieldOccurrence,
) -> GenericFieldFinding:
    return GenericFieldFinding(
        kind="stale_generic_field_ownership",
        surface=occurrence.surface,
        path=occurrence.path,
        field=occurrence.field,
        context=occurrence.context,
        message=(
            f"ownership entry for {occurrence.surface} "
            f"{occurrence.path}:{occurrence.context}:{occurrence.field} "
            "does not match a current generic field occurrence"
        ),
    )


def validate_generic_field_ownership(
    *,
    repo_root: Path = REPO_ROOT,
    ownership_path: Path = DEFAULT_OWNERSHIP_PATH,
    registry_path: Path = DEFAULT_REGISTRY_PATH,
) -> tuple[GenericFieldFinding, ...]:
    """Return generic field ownership findings for governed semantic surfaces."""
    ownership_payload = _load_yaml(ownership_path)
    denied_terms = frozenset(
        term
        for term in ownership_payload.get("denied_terms", [])
        if isinstance(term, str)
    )
    if not denied_terms:
        raise ValueError(f"{ownership_path} must define denied_terms")

    actual_occurrences = set(
        _iter_canonical_registry_occurrences(
            repo_root=repo_root,
            registry_path=registry_path,
            denied_terms=denied_terms,
        )
        + _iter_gold_json_occurrences(repo_root=repo_root, denied_terms=denied_terms)
        + _iter_composite_column_group_occurrences(
            repo_root=repo_root,
            denied_terms=denied_terms,
        )
        + _iter_composite_field_group_occurrences(
            repo_root=repo_root,
            denied_terms=denied_terms,
        )
    )
    owned_occurrences = set(_ownership_entries(ownership_payload))

    findings = _entry_metadata_findings(
        ownership_payload,
        ownership_path=ownership_path,
    )
    findings.extend(
        _finding_for_unowned(occurrence)
        for occurrence in sorted(
            actual_occurrences - owned_occurrences,
            key=lambda item: (item.path, item.surface, item.context, item.field),
        )
    )
    findings.extend(
        _finding_for_stale_ownership(occurrence)
        for occurrence in sorted(
            owned_occurrences - actual_occurrences,
            key=lambda item: (item.path, item.surface, item.context, item.field),
        )
    )
    return tuple(findings)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate ownership for generic lexical fields.",
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
        "--repo-root",
        type=Path,
        default=REPO_ROOT,
        help="repository root containing configs, docs, and contracts",
    )
    parser.add_argument(
        "--ownership-path",
        type=Path,
        default=DEFAULT_OWNERSHIP_PATH,
        help="generic field ownership YAML registry",
    )
    parser.add_argument(
        "--registry-path",
        type=Path,
        default=DEFAULT_REGISTRY_PATH,
        help="canonical semantic field registry JSON",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    findings = validate_generic_field_ownership(
        repo_root=args.repo_root,
        ownership_path=args.ownership_path,
        registry_path=args.registry_path,
    )
    if args.json:
        payload = {
            "ok": not findings,
            "finding_count": len(findings),
            "findings": [finding.as_dict() for finding in findings],
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
    elif findings:
        print("[generic-field-ownership] validation failed")
        for finding in findings:
            print(f"- {finding.message}")
    else:
        print("[generic-field-ownership] ok")

    return 1 if args.check and findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
