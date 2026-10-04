"""Bind the security backport's installed archive to reviewed source bytes."""

from __future__ import annotations

import base64
import hashlib
import json
import tarfile
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture
ROOT = Path(__file__).resolve().parents[2]
BACKPORT = ROOT / ".github/tooling/braces-backport"
CONSUMERS = (
    ".github/tooling/jscpd",
    "grafana/plugins/bioetl-scenes-app",
    "grafana/plugins/bioetl-selectorshell-panel",
)


def test_backport_archive_matches_reviewed_source() -> None:
    provenance = json.loads((BACKPORT / "provenance.json").read_text())
    assert provenance["upstream_commit"] == "28d440b5dd449dbf1fe6f3506cf94ecca4d02660"
    archive = BACKPORT / "braces-3.0.4-bioetl.1.tgz"
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
            (BACKPORT / "package.json").read_text(encoding="utf-8")
        )


@pytest.mark.parametrize("consumer", CONSUMERS)
def test_consumers_install_the_verified_backport(consumer: str) -> None:
    folder = ROOT / consumer
    package = json.loads((folder / "package.json").read_text())
    lock = json.loads((folder / "package-lock.json").read_text())
    assert package["overrides"]["braces"] == "$braces"
    entries = [
        row
        for name, row in lock["packages"].items()
        if name.endswith("node_modules/braces")
    ]
    assert entries
    archive = BACKPORT / "braces-3.0.4-bioetl.1.tgz"
    integrity = (
        "sha512-"
        + base64.b64encode(hashlib.sha512(archive.read_bytes()).digest()).decode()
    )
    for entry in entries:
        assert entry["version"] == "3.0.4-bioetl.1"
        assert entry["integrity"] == integrity
        assert entry["resolved"].startswith("file:")
        assert (folder / entry["resolved"][5:]).resolve() == archive.resolve()
