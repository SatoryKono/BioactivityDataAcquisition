"""Picomatch local backport: archive integrity and GHSA-fc5q ReDoS guards."""

from __future__ import annotations

import subprocess
import tarfile
from pathlib import Path

import pytest

from tests.architecture.backport_tarball import (
    ROOT,
    assert_archive_matches_provenance,
    assert_consumers_pin_archive,
)

pytestmark = pytest.mark.architecture
BACKPORT = ROOT / ".github/tooling/picomatch-backport"
CONSUMERS = (
    ".github/tooling/jscpd",
    "grafana/plugins/bioetl-scenes-app",
    "grafana/plugins/bioetl-selectorshell-panel",
)
ARCHIVE = BACKPORT / "picomatch-4.0.8-bioetl.3.tgz"


def test_picomatch_surface_is_tarball_only() -> None:
    names = {path.name for path in BACKPORT.iterdir() if path.is_file()}
    assert names == {
        "BACKPORT.md",
        "LICENSE",
        "package.json",
        ARCHIVE.name,
        "provenance.json",
        "test.cjs",
    }
    assert not (BACKPORT / "lib").exists()
    assert not (BACKPORT / "single-branch-wildcard.patch").exists()


def test_picomatch_archive_matches_reviewed_source() -> None:
    assert_archive_matches_provenance(
        BACKPORT,
        archive_name=ARCHIVE.name,
        expected={
            "upstream_commit": "7be3276fb8bd215a8c73fa066bcaf696c244ad88",
            "advisory": "GHSA-fc5q-39xc-vjpf",
            "local_version": "4.0.8-bioetl.3",
        },
    )


@pytest.mark.parametrize("consumer", CONSUMERS)
def test_picomatch_consumers_install_verified_archive(consumer: str) -> None:
    assert_consumers_pin_archive(
        [consumer],
        package_name="picomatch",
        version="4.0.8-bioetl.3",
        archive=ARCHIVE,
        forbidden_versions=("2.3.2", "4.0.7", "4.0.8-bioetl.1", "4.0.8-bioetl.2"),
    )


@pytest.mark.parametrize(
    "pattern",
    ["+(*)", "+(*a)", "*(*)", "*(*a)", "+(@(*a))", "*(@(*a))", "+(@(*))"],
)
def test_repeated_and_nested_extglob_wildcards_finish_with_bounded_input(
    pattern: str,
    tmp_path: Path,
) -> None:
    with tarfile.open(ARCHIVE) as packed:
        for member in packed.getmembers():
            assert member.isfile() and member.name.startswith("package/")
            relative = Path(member.name)
            assert ".." not in relative.parts
            content = packed.extractfile(member)
            assert content is not None
            destination = tmp_path / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content.read())
    code = (
        "const p=require(process.argv[1]);"
        "console.log(p.makeRe(process.argv[2]).test('a'.repeat(32)+'!'));"
    )
    result = subprocess.run(
        ["node", "-e", code, str(tmp_path / "package"), pattern],
        capture_output=True,
        text=True,
        timeout=3,
        check=True,
    )
    assert result.stdout.strip() == "false"
