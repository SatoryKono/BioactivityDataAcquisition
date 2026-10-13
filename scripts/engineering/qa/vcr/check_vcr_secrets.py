#!/usr/bin/env python3
"""Fail closed on secret-bearing HTTP metadata in tracked VCR cassettes."""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlsplit

import yaml

ROOT = Path(__file__).resolve().parents[4]
VCR_ROOT = ROOT / "tests" / "fixtures" / "vcr"

QUERY_KEYS = {
    "api_key",
    "apikey",
    "token",
    "key",
    "access_token",
    "refresh_token",
    "ncbi_sid",
    "ncbi_phid",
    "ncbi-sid",
    "ncbi-phid",
    "session_id",
    "sessionid",
    "session_token",
}
HEADER_KEYS = {
    "authorization",
    "x-api-key",
    "api-key",
    "x-auth-token",
    "proxy-authorization",
    "cookie",
    "set-cookie",
    "set-cookie2",
    "ncbi-sid",
    "ncbi-phid",
}
REDACTED_MARKERS = ("redacted", "<redacted>", "***", "example", "dummy", "test")
_INVALID_MAPPING = "invalid mapping"
_LFS_POINTER_PREFIX = b"version https://git-lfs.github.com/spec/v1"


class _DuplicateKeyError(yaml.YAMLError):
    """A YAML mapping has more than one value for the same key."""


class _StrictCassetteLoader(yaml.SafeLoader):
    """Load safe YAML while rejecting duplicate mapping keys."""

    def construct_mapping(
        self, node: yaml.MappingNode, deep: bool = False
    ) -> dict[Any, Any]:
        self.flatten_mapping(node)
        result: dict[Any, Any] = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in result:
                raise _DuplicateKeyError
            result[key] = self.construct_object(value_node, deep=deep)
        return result


def _location(path: Path, interaction: int | str, field: str, issue: str) -> str:
    try:
        relative = path.relative_to(ROOT).as_posix()
    except ValueError:
        relative = path.as_posix()
    return f"{relative}:interaction {interaction}:{field}: {issue}"


def _looks_redacted(value: str) -> bool:
    lowered = value.strip().strip("'\"").lower()
    if not lowered:
        return True
    exact_markers = {marker.lower() for marker in REDACTED_MARKERS}
    if lowered in exact_markers:
        return True
    return lowered in {"[redacted]", "bearer [redacted]", "bearer <redacted>"}


def _reject_alias_cycles(value: object, active: set[int], visited: set[int]) -> None:
    if not isinstance(value, (dict, list)):
        return
    identity = id(value)
    if identity in active:
        raise ValueError("cyclic_alias")
    if identity in visited:
        return
    active.add(identity)
    children = (
        (item for pair in value.items() for item in pair)
        if isinstance(value, dict)
        else iter(value)
    )
    for child in children:
        _reject_alias_cycles(child, active, visited)
    active.remove(identity)
    visited.add(identity)


def _parse_document(path: Path, raw: bytes) -> tuple[object | None, list[str]]:
    if raw.startswith(_LFS_POINTER_PREFIX):
        return None, [_location(path, "-", "yaml", "LFS pointer is unavailable")]
    try:
        document = yaml.load(raw, Loader=_StrictCassetteLoader)
        _reject_alias_cycles(document, set(), set())
    except _DuplicateKeyError:
        return None, [_location(path, "-", "yaml", "duplicate mapping key")]
    except (yaml.YAMLError, UnicodeError, ValueError, TypeError, RecursionError):
        return None, [_location(path, "-", "yaml", "malformed or cyclic document")]
    return document, []


def _scan_uri(path: Path, interaction: int, uri_value: str) -> list[str]:
    try:
        query_items = parse_qsl(
            urlsplit(uri_value).query,
            keep_blank_values=True,
            encoding="utf-8",
            errors="strict",
        )
    except (UnicodeError, ValueError):
        return [_location(path, interaction, "request.uri", "invalid URI")]
    findings: list[str] = []
    for key, value in query_items:
        normalized_key = key.casefold()
        if normalized_key in QUERY_KEYS and not _looks_redacted(value):
            findings.append(
                _location(
                    path,
                    interaction,
                    f"request.uri.query.{normalized_key}",
                    "unredacted credential",
                )
            )
    return findings


def _scan_headers(
    path: Path, interaction: int, side: str, headers: object
) -> list[str]:
    if not isinstance(headers, dict):
        return [_location(path, interaction, f"{side}.headers", _INVALID_MAPPING)]
    findings: list[str] = []
    for raw_name, raw_values in headers.items():
        if not isinstance(raw_name, str):
            findings.append(
                _location(path, interaction, f"{side}.headers", "invalid field name")
            )
            continue
        name = raw_name.casefold()
        field = f"{side}.headers.{name}" if name in HEADER_KEYS else f"{side}.headers"
        if isinstance(raw_values, str):
            values: list[object] = [raw_values]
        elif isinstance(raw_values, list) and raw_values:
            values = raw_values
        else:
            findings.append(_location(path, interaction, field, "invalid values"))
            continue
        findings.extend(_scan_header_values(path, interaction, field, name, values))
    return findings


def _scan_header_values(
    path: Path, interaction: int, field: str, name: str, values: list[object]
) -> list[str]:
    findings: list[str] = []
    for value_index, value in enumerate(values, start=1):
        if not isinstance(value, str):
            findings.append(
                _location(path, interaction, field, f"invalid value at {value_index}")
            )
        elif name in HEADER_KEYS and not _looks_redacted(value):
            findings.append(
                _location(
                    path, interaction, field, f"unredacted value at {value_index}"
                )
            )
    return findings


def _scan_request(path: Path, interaction: int, request: dict[Any, Any]) -> list[str]:
    findings: list[str] = []
    if not isinstance(request.get("method"), str):
        findings.append(_location(path, interaction, "request.method", "invalid value"))
    uri = request.get("uri")
    if isinstance(uri, str):
        findings.extend(_scan_uri(path, interaction, uri))
    else:
        findings.append(_location(path, interaction, "request.uri", "invalid value"))
    return findings


def _scan_part(path: Path, interaction: int, side: str, part: object) -> list[str]:
    if not isinstance(part, dict):
        return [_location(path, interaction, side, "missing or invalid mapping")]
    findings = _scan_headers(path, interaction, side, part.get("headers"))
    if side == "request":
        findings.extend(_scan_request(path, interaction, part))
    elif not isinstance(part.get("status"), dict):
        findings.append(
            _location(path, interaction, "response.status", _INVALID_MAPPING)
        )
    return findings


def _scan_interactions(path: Path, document: object) -> list[str]:
    if not isinstance(document, dict):
        return [_location(path, "-", "interactions", "invalid document mapping")]
    interactions = document.get("interactions")
    if not isinstance(interactions, list) or not interactions:
        return [_location(path, "-", "interactions", "missing or empty list")]
    findings: list[str] = []
    for interaction_index, interaction in enumerate(interactions, start=1):
        if not isinstance(interaction, dict):
            findings.append(
                _location(path, interaction_index, "interaction", _INVALID_MAPPING)
            )
            continue
        for side in ("request", "response"):
            findings.extend(
                _scan_part(path, interaction_index, side, interaction.get(side))
            )
    return findings


def _scan_file(path: Path, *, raw: bytes | None = None) -> list[str]:
    try:
        content = path.read_bytes() if raw is None else raw
    except OSError:
        return [_location(path, "-", "yaml", "unreadable file")]
    document, errors = _parse_document(path, content)
    if errors:
        return errors
    return _scan_interactions(path, document)


def _tracked_yaml_paths() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "-z", "--", "*.yaml", "*.yml"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return [ROOT / os.fsdecode(item) for item in result.stdout.split(b"\0") if item]


def _candidate(path: Path, raw: bytes) -> bool:
    if path.is_relative_to(VCR_ROOT):
        return True
    name = path.relative_to(ROOT).as_posix().casefold()
    if "vcr" in name or "cassette" in name:
        return True
    try:
        for document in yaml.compose_all(raw, Loader=yaml.SafeLoader):
            if isinstance(document, yaml.MappingNode) and any(
                isinstance(key, yaml.ScalarNode) and key.value == "interactions"
                for key, _ in document.value
            ):
                return True
    except (yaml.YAMLError, UnicodeError, ValueError, TypeError, RecursionError):
        # An unreadable YAML structure cannot prove that the file is unrelated.
        # Route it to the strict parser instead of silently excluding it.
        return True
    return False


@dataclass
class _Inventory:
    findings: list[str] = field(default_factory=list)
    read: int = 0
    excluded: int = 0
    cassettes: int = 0
    canonical_cassettes: int = 0
    unavailable: int = 0

    def reject(self, path: Path, field_name: str, reason: str) -> None:
        self.findings.append(_location(path, "-", field_name, reason))
        self.unavailable += 1


def _inspect_document(path: Path, raw: bytes, inventory: _Inventory) -> None:
    if not _candidate(path, raw):
        inventory.excluded += 1
        return
    document, parse_errors = _parse_document(path, raw)
    if parse_errors:
        inventory.findings.extend(parse_errors)
        inventory.unavailable += 1
        return
    if not isinstance(document, dict) or "interactions" not in document:
        if path.is_relative_to(VCR_ROOT) and not path.stem.endswith("_meta"):
            inventory.findings.append(
                _location(path, "-", "interactions", "missing from cassette")
            )
        else:
            inventory.excluded += 1
        return
    inventory.cassettes += 1
    if path.is_relative_to(VCR_ROOT):
        inventory.canonical_cassettes += 1
    inventory.findings.extend(_scan_interactions(path, document))


def _inspect_path(path: Path, inventory: _Inventory) -> None:
    if not path.resolve().is_relative_to(ROOT.resolve()):
        inventory.reject(path, "inventory", "path escapes repository")
        return
    try:
        raw = path.read_bytes()
    except OSError:
        inventory.reject(path, "yaml", "unreadable file")
        return
    inventory.read += 1
    if raw.startswith(_LFS_POINTER_PREFIX):
        inventory.reject(path, "yaml", "LFS pointer is unavailable")
        return
    _inspect_document(path, raw, inventory)


def _untracked_findings(tracked_paths: list[Path]) -> list[str]:
    tracked_names = {path.resolve() for path in tracked_paths}
    return [
        _location(path, "-", "inventory", "untracked VCR YAML")
        for path in VCR_ROOT.rglob("*")
        if path.suffix.casefold() in {".yaml", ".yml"}
        and path.resolve() not in tracked_names
    ]


def _report_inventory(tracked_count: int, inventory: _Inventory) -> int:
    if not inventory.cassettes or not inventory.canonical_cassettes:
        inventory.findings.append(
            _location(VCR_ROOT, "-", "inventory", "empty cassette traversal")
        )
    summary = (
        f"tracked_yaml={tracked_count} read={inventory.read} "
        f"excluded={inventory.excluded} unavailable={inventory.unavailable} "
        f"cassettes={inventory.cassettes} canonical_cassettes={inventory.canonical_cassettes}"
    )
    if inventory.findings:
        sys.stderr.write(f"ERROR: VCR secret-safety check failed ({summary}).\n")
        for finding in inventory.findings:
            sys.stderr.write(f" - {finding}\n")
        return 1
    sys.stdout.write(f"OK: VCR HTTP metadata is sanitized ({summary}).\n")
    return 0


def main() -> int:
    if not VCR_ROOT.is_dir():
        sys.stderr.write(
            _location(VCR_ROOT, "-", "root", "missing VCR directory") + "\n"
        )
        return 1
    try:
        tracked_paths = _tracked_yaml_paths()
    except (OSError, subprocess.CalledProcessError):
        sys.stderr.write(
            _location(ROOT, "-", "inventory", "git ls-files failed") + "\n"
        )
        return 1
    if not tracked_paths:
        sys.stderr.write(
            _location(ROOT, "-", "inventory", "empty tracked YAML traversal") + "\n"
        )
        return 1
    inventory = _Inventory(findings=_untracked_findings(tracked_paths))
    for path in tracked_paths:
        _inspect_path(path, inventory)
    return _report_inventory(len(tracked_paths), inventory)


if __name__ == "__main__":
    raise SystemExit(main())
