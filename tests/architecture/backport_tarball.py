"""Shared assertions for hash-bound local npm security backports."""

from __future__ import annotations

import base64
import hashlib
import json
import tarfile
from collections.abc import Mapping, Sequence
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def assert_archive_matches_provenance(
    backport: Path,
    *,
    archive_name: str,
    expected: Mapping[str, str],
) -> None:
    provenance = json.loads((backport / "provenance.json").read_text(encoding="utf-8"))
    for key, value in expected.items():
        assert provenance[key] == value
    archive = backport / archive_name
    with tarfile.open(archive) as packed:
        assert set(packed.getnames()) == {
            *(f"package/{name}" for name in provenance["files"]),
            "package/package.json",
        }
        for relative, digest in provenance["files"].items():
            member = packed.extractfile(f"package/{relative}")
            assert member is not None
            assert hashlib.sha256(member.read()).hexdigest() == digest
        metadata = packed.extractfile("package/package.json")
        assert metadata is not None
        assert json.loads(metadata.read()) == json.loads(
            (backport / "package.json").read_text(encoding="utf-8")
        )


def assert_consumers_pin_archive(
    consumers: Sequence[str],
    *,
    package_name: str,
    version: str,
    archive: Path,
    forbidden_versions: Sequence[str] = (),
) -> None:
    integrity = (
        "sha512-"
        + base64.b64encode(hashlib.sha512(archive.read_bytes()).digest()).decode()
    )
    for consumer in consumers:
        folder = ROOT / consumer
        package = json.loads((folder / "package.json").read_text(encoding="utf-8"))
        lock = json.loads((folder / "package-lock.json").read_text(encoding="utf-8"))
        assert package["overrides"][package_name] == f"${package_name}"
        entries = [
            row
            for name, row in lock["packages"].items()
            if name.endswith(f"node_modules/{package_name}")
        ]
        assert entries
        for entry in entries:
            assert entry["version"] == version
            assert entry["integrity"] == integrity
            assert entry["resolved"].startswith("file:")
            assert (folder / entry["resolved"][5:]).resolve() == archive.resolve()
        if forbidden_versions:
            assert not any(
                row.get("version") in set(forbidden_versions)
                for name, row in lock["packages"].items()
                if name.endswith(f"node_modules/{package_name}")
            )
