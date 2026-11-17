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
ARCHIVE = BACKPORT / "picomatch-4.0.8-bioetl.9.tgz"


@pytest.fixture
def packed_picomatch(tmp_path: Path) -> Path:
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
    return tmp_path / "package"


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
            "local_version": "4.0.8-bioetl.9",
        },
    )


@pytest.mark.parametrize("consumer", CONSUMERS)
def test_picomatch_consumers_install_verified_archive(consumer: str) -> None:
    assert_consumers_pin_archive(
        [consumer],
        package_name="picomatch",
        version="4.0.8-bioetl.9",
        archive=ARCHIVE,
        forbidden_versions=(
            "2.3.2",
            "4.0.7",
            "4.0.8-bioetl.1",
            "4.0.8-bioetl.2",
            "4.0.8-bioetl.3",
            "4.0.8-bioetl.4",
            "4.0.8-bioetl.5",
            "4.0.8-bioetl.6",
            "4.0.8-bioetl.7",
            "4.0.8-bioetl.8",
        ),
    )


@pytest.mark.parametrize(
    ("pattern", "unit", "repeat"),
    [
        ("+(*)", "a", 32),
        ("+(*a)", "a", 32),
        ("*(*)", "a", 32),
        ("*(*a)", "a", 32),
        ("+(@(*a))", "a", 32),
        ("*(@(*a))", "a", 32),
        ("+(@(*))", "a", 32),
        ("+(@(*))b", "a", 32),
        ("+(*)b", "a", 32),
        ("+(@(a|aa))", "a", 48),
        ("*(@(a|aa))", "a", 48),
        # General literal prefix-overlap (not single-char only).
        ("+(ab|abab)", "ab", 48),
        ("+(@(ab|abab))", "ab", 48),
        ("*(@(ab|abab))", "ab", 48),
        # Nested unbounded +(...) without wildcard (not only *).
        ("+(@(+(a)))", "a", 40),
        ("*(@(+(a)))", "a", 40),
        ("+(?(+(a)))", "a", 40),
        ("+(@(*(a)))", "a", 40),
        ("+(a|[a]a)", "a", 40),
        ("+((a|aa))", "a", 40),
        ("+(a?(a))", "a", 40),
        ("@(+(a))+", "a", 40),
        ("(+(a))+", "a", 40),
    ],
)
def test_repeated_and_nested_extglob_wildcards_finish_with_bounded_input(
    pattern: str,
    unit: str,
    repeat: int,
    packed_picomatch: Path,
) -> None:
    code = (
        "const p=require(process.argv[1]);"
        "const unit=process.argv[3];"
        "const n=Number(process.argv[4]);"
        "console.log(p.makeRe(process.argv[2]).test(unit.repeat(n)+'!'));"
    )
    result = subprocess.run(
        [
            "node",
            "-e",
            code,
            str(packed_picomatch),
            pattern,
            unit,
            str(repeat),
        ],
        capture_output=True,
        text=True,
        timeout=3,
        check=True,
    )
    assert result.stdout.strip() == "false"


def test_fail_closed_ignores_max_extglob_recursion_bypass(
    packed_picomatch: Path,
) -> None:
    code = (
        "const p=require(process.argv[1]);"
        "const re=p.makeRe('+((a|aa))',{maxExtglobRecursion:false});"
        "console.log(re.test('a'.repeat(40)+'!'));"
    )
    result = subprocess.run(
        ["node", "-e", code, str(packed_picomatch)],
        capture_output=True,
        text=True,
        timeout=3,
        check=True,
    )
    assert result.stdout.strip() == "false"


def test_fail_closed_preserves_ascii_word_and_glob_smoke(
    packed_picomatch: Path,
) -> None:
    code = (
        "const p=require(process.argv[1]);"
        "console.log(["
        "p.makeRe('*.js').test('a.js'),"
        "p.makeRe('*.js').test('a.md'),"
        "p.makeRe('+(ab)').test('ababab'),"
        "p.makeRe('+(a)').test('aaa')"
        "].join(','));"
    )
    result = subprocess.run(
        ["node", "-e", code, str(packed_picomatch)],
        capture_output=True,
        text=True,
        timeout=3,
        check=True,
    )
    assert result.stdout.strip() == "true,false,true,true"


def test_deep_optional_extglob_compiles_without_recursive_rescanning(
    packed_picomatch: Path,
) -> None:
    code = (
        "const p=require(process.argv[1]);"
        "p.makeRe('?(a'.repeat(800)+'b'+')'.repeat(800));"
        "console.log('compiled');"
    )
    result = subprocess.run(
        ["node", "-e", code, str(packed_picomatch)],
        capture_output=True,
        text=True,
        timeout=3,
        check=True,
    )
    assert result.stdout.strip() == "compiled"
