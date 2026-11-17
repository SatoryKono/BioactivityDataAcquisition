"""Bind the picomatch security backport archive to reviewed source bytes."""

from __future__ import annotations

import base64
import hashlib
import json
import tarfile
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture
ROOT = Path(__file__).resolve().parents[2]
BACKPORT = ROOT / ".github/tooling/picomatch-backport"
CONSUMERS = (
    ".github/tooling/jscpd",
    "grafana/plugins/bioetl-scenes-app",
    "grafana/plugins/bioetl-selectorshell-panel",
)


def test_backport_archive_matches_reviewed_source() -> None:
    provenance = json.loads((BACKPORT / "provenance.json").read_text())
    assert provenance["upstream_commit"] == "7be3276fb8bd215a8c73fa066bcaf696c244ad88"
    assert provenance["advisory"] == "GHSA-fc5q-39xc-vjpf"
    assert provenance["local_version"] == "4.0.8-bioetl.2"
    archive = BACKPORT / "picomatch-4.0.8-bioetl.2.tgz"
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
    assert package["overrides"]["picomatch"] == "$picomatch"
    entries = [
        row
        for name, row in lock["packages"].items()
        if name.endswith("node_modules/picomatch")
    ]
    assert entries
    archive = BACKPORT / "picomatch-4.0.8-bioetl.2.tgz"
    integrity = (
        "sha512-"
        + base64.b64encode(hashlib.sha512(archive.read_bytes()).digest()).decode()
    )
    for entry in entries:
        assert entry["version"] == "4.0.8-bioetl.2"
        assert entry["integrity"] == integrity
        assert entry["resolved"].startswith("file:")
        assert (folder / entry["resolved"][5:]).resolve() == archive.resolve()
    # No vulnerable registry picomatch remains in the lockfile graph.
    assert not any(
        row.get("version") in {"2.3.2", "4.0.7"}
        for name, row in lock["packages"].items()
        if name.endswith("node_modules/picomatch")
    )


@pytest.mark.parametrize("pattern", ["+(*)", "+(*a)", "*(*)", "*(*a)"])
def test_repeated_single_branch_wildcards_finish_with_bounded_input(
    pattern: str,
) -> None:
    code = (
        "const p=require(process.argv[1]);"
        "console.log(p.makeRe(process.argv[2]).test('a'.repeat(32)+'!'));"
    )
    result = subprocess.run(
        ["node", "-e", code, str(BACKPORT), pattern],
        capture_output=True,
        text=True,
        timeout=3,
        check=True,
    )
    assert result.stdout.strip() == "false"
