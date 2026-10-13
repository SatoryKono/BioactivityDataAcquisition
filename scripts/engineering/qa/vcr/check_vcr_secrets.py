#!/usr/bin/env python3
"""Fail closed on secret-bearing HTTP metadata in tracked VCR cassettes."""

from __future__ import annotations

import os
import re
import subprocess
import sys
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
        return [_location(path, interaction, f"{side}.headers", "invalid mapping")]
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
        for value_index, value in enumerate(values, start=1):
            if not isinstance(value, str):
                findings.append(
                    _location(
                        path, interaction, field, f"invalid value at {value_index}"
                    )
                )
            elif name in HEADER_KEYS and not _looks_redacted(value):
                findings.append(
                    _location(
                        path,
                        interaction,
                        field,
                        f"unredacted value at {value_index}",
                    )
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
                _location(path, interaction_index, "interaction", "invalid mapping")
            )
            continue
        for side in ("request", "response"):
            part = interaction.get(side)
            if not isinstance(part, dict):
                findings.append(
                    _location(
                        path, interaction_index, side, "missing or invalid mapping"
                    )
                )
                continue
            if side == "request":
                if not isinstance(part.get("method"), str):
                    findings.append(
                        _location(
                            path, interaction_index, "request.method", "invalid value"
                        )
                    )
                uri = part.get("uri")
                if isinstance(uri, str):
                    findings.extend(_scan_uri(path, interaction_index, uri))
                else:
                    findings.append(
                        _location(
                            path, interaction_index, "request.uri", "invalid value"
                        )
                    )
            elif not isinstance(part.get("status"), dict):
                findings.append(
                    _location(
                        path, interaction_index, "response.status", "invalid mapping"
                    )
                )
            findings.extend(
                _scan_headers(path, interaction_index, side, part.get("headers"))
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
    return (
        bool(re.search(rb"(?m)^interactions\s*:", raw))
        or "vcr" in name
        or "cassette" in name
    )


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

    findings: list[str] = []
    tracked_names = {path.resolve() for path in tracked_paths}
    for path in VCR_ROOT.rglob("*"):
        if (
            path.suffix.casefold() in {".yaml", ".yml"}
            and path.resolve() not in tracked_names
        ):
            findings.append(_location(path, "-", "inventory", "untracked VCR YAML"))
    read_count = 0
    excluded_count = 0
    cassette_count = 0
    canonical_cassette_count = 0
    unavailable_count = 0
    for path in tracked_paths:
        if not path.resolve().is_relative_to(ROOT.resolve()):
            findings.append(
                _location(path, "-", "inventory", "path escapes repository")
            )
            unavailable_count += 1
            continue
        try:
            raw = path.read_bytes()
        except OSError:
            findings.append(_location(path, "-", "yaml", "unreadable file"))
            unavailable_count += 1
            continue
        read_count += 1
        if raw.startswith(_LFS_POINTER_PREFIX):
            findings.append(_location(path, "-", "yaml", "LFS pointer is unavailable"))
            unavailable_count += 1
            continue
        if not _candidate(path, raw):
            excluded_count += 1
            continue
        document, parse_errors = _parse_document(path, raw)
        if parse_errors:
            findings.extend(parse_errors)
            unavailable_count += 1
            continue
        if not isinstance(document, dict) or "interactions" not in document:
            if path.is_relative_to(VCR_ROOT) and not path.stem.endswith("_meta"):
                findings.append(
                    _location(path, "-", "interactions", "missing from cassette")
                )
            else:
                excluded_count += 1
            continue
        cassette_count += 1
        if path.is_relative_to(VCR_ROOT):
            canonical_cassette_count += 1
        findings.extend(_scan_interactions(path, document))
    if not cassette_count or not canonical_cassette_count:
        findings.append(
            _location(VCR_ROOT, "-", "inventory", "empty cassette traversal")
        )

    summary = (
        f"tracked_yaml={len(tracked_paths)} read={read_count} "
        f"excluded={excluded_count} unavailable={unavailable_count} "
        f"cassettes={cassette_count} canonical_cassettes={canonical_cassette_count}"
    )
    if findings:
        sys.stderr.write(f"ERROR: VCR secret-safety check failed ({summary}).\n")
        for finding in findings:
            sys.stderr.write(f" - {finding}\n")
        return 1
    sys.stdout.write(f"OK: VCR HTTP metadata is sanitized ({summary}).\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
