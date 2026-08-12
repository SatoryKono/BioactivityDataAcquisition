# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.engineering.qa.report_module_coverage_inventory import (
    _SourceModuleSnapshot,
    _parse_coverage_xml,
    _module_is_declaration_only,
    _read_source_module_snapshots,
    _read_stable_source_module_snapshots,
    _refresh_existing_inventory_source_tree,
)

pytestmark = pytest.mark.unit


def test_read_source_module_snapshots_skips_vanished_path(
    tmp_path: Path,
) -> None:
    present = tmp_path / "present.py"
    vanished = tmp_path / "vanished.py"
    present.write_text("x = 1\n", encoding="utf-8")
    vanished.write_text("y = 2\n", encoding="utf-8")
    vanished.unlink()

    snapshots, digest = _read_source_module_snapshots(
        [present, vanished],
        tmp_path,
    )

    assert digest
    assert [snapshot.repo_path for snapshot in snapshots] == ["present.py"]


def test_read_stable_source_module_snapshots_retries_until_digest_stabilizes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    present = tmp_path / "present.py"
    present.write_text("x = 1\n", encoding="utf-8")

    calls = iter(
        [
            ([SimpleNamespace(repo_path="present.py")], "digest-a"),
            ([SimpleNamespace(repo_path="present.py")], "digest-b"),
            ([SimpleNamespace(repo_path="present.py")], "digest-b"),
        ]
    )

    monkeypatch.setattr(
        "scripts.engineering.qa.report_module_coverage_inventory._iter_source_modules",
        lambda repo_root: [present],
    )
    monkeypatch.setattr(
        "scripts.engineering.qa.report_module_coverage_inventory._read_source_module_snapshots",
        lambda source_paths, repo_root: next(calls),
    )

    snapshots, digest = _read_stable_source_module_snapshots(tmp_path, max_attempts=3)

    assert [snapshot.repo_path for snapshot in snapshots] == ["present.py"]
    assert digest == "digest-b"


def test_refresh_existing_inventory_reuses_stable_snapshot_digest(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "src" / "bioetl" / "present.py"
    source_path.parent.mkdir(parents=True)
    source_path.write_text("x = 1\n", encoding="utf-8")
    snapshot = _SourceModuleSnapshot(
        path=source_path,
        repo_path="src/bioetl/present.py",
        source_lines=1,
        declaration_only=False,
    )

    monkeypatch.setattr(
        "scripts.engineering.qa.report_module_coverage_inventory._read_stable_source_module_snapshots",
        lambda repo_root: ([snapshot], "stable-digest"),
    )
    monkeypatch.setattr(
        "scripts.engineering.qa.report_module_coverage_inventory._build_hotspot_family_coverage",
        lambda rows, *, repo_root: {},
    )
    monkeypatch.setattr(
        "scripts.engineering.qa.report_module_coverage_inventory.compute_source_tree_sha256",
        lambda *, repo_root: pytest.fail(
            "source hash should come from stable snapshot read"
        ),
    )

    refreshed = _refresh_existing_inventory_source_tree(
        {
            "modules": [
                {
                    "module": "bioetl.present",
                    "path": "src/bioetl/present.py",
                    "source_lines": 999,
                    "coverage_status": "fully_covered",
                    "coverage_percent": 100.0,
                    "executable_lines": 1,
                    "covered_lines": 1,
                    "missing_lines": 0,
                }
            ],
            "summary": {"source_tree_sha256": "stale-summary-digest"},
            "source_tree_sha256": "old-digest",
        },
        repo_root=tmp_path,
    )

    assert refreshed["source_tree_sha256"] == "stable-digest"
    assert refreshed["modules"][0]["source_lines"] == 999
    assert refreshed["summary"]["source_module_count"] == 1
    assert refreshed["summary"]["status_counts"]["fully_covered"] == 1
    assert refreshed["summary"]["unmeasured_module_count"] == 0
    assert refreshed["summary"]["uncovered_module_count"] == 0


def test_refresh_existing_inventory_prunes_removed_source_rows(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        "scripts.engineering.qa.report_module_coverage_inventory._read_stable_source_module_snapshots",
        lambda repo_root: ([], "stable-digest"),
    )
    monkeypatch.setattr(
        "scripts.engineering.qa.report_module_coverage_inventory._build_hotspot_family_coverage",
        lambda rows, *, repo_root: {},
    )

    refreshed = _refresh_existing_inventory_source_tree(
        {
            "modules": [
                {
                    "path": "src/bioetl/removed.py",
                    "coverage_status": "fully_covered",
                }
            ],
            "summary": {},
        },
        repo_root=tmp_path,
    )

    assert refreshed["modules"] == []
    assert refreshed["rows"] == []
    assert refreshed["summary"]["source_module_count"] == 0


def test_module_is_declaration_only_treats_private_attrs_surface_as_non_runtime() -> (
    None
):
    source = (
        '"""Typed attrs."""\n'
        "from __future__ import annotations\n"
        "from typing import TYPE_CHECKING\n"
        "if TYPE_CHECKING:\n"
        "    from x import Y\n"
        "class _Attrs:\n"
        "    __slots__ = ('a',)\n"
        "    a: int\n"
        "__all__ = ['_Attrs']\n"
    )

    assert _module_is_declaration_only(source) is True


def test_module_is_declaration_only_rejects_runtime_behavior() -> None:
    source = "def build() -> int:\n    return 1\n"

    assert _module_is_declaration_only(source) is False


def test_coverage_xml_prefers_bioetl_source_for_ambiguous_root_module(
    tmp_path: Path,
) -> None:
    scripts_init = tmp_path / "scripts" / "__init__.py"
    bioetl_init = tmp_path / "src" / "bioetl" / "__init__.py"
    coverage_xml = tmp_path / "reports" / "coverage" / "coverage.xml"
    scripts_init.parent.mkdir(parents=True)
    bioetl_init.parent.mkdir(parents=True)
    coverage_xml.parent.mkdir(parents=True)
    scripts_init.write_text("# package\n", encoding="utf-8")
    bioetl_init.write_text(
        '"""BioETL."""\n\n__version__ = "1.0"\n',
        encoding="utf-8",
    )
    coverage_xml.write_text(
        """<?xml version="1.0" ?>
<coverage>
  <sources>
    <source>scripts</source>
    <source>src/bioetl</source>
  </sources>
  <packages>
    <package name=".">
      <classes>
        <class name="__init__.py" filename="__init__.py">
          <lines><line number="3" hits="1"/></lines>
        </class>
      </classes>
    </package>
  </packages>
</coverage>
""",
        encoding="utf-8",
    )

    coverage_by_path = _parse_coverage_xml(coverage_xml, repo_root=tmp_path)

    assert coverage_by_path == {
        "src/bioetl/__init__.py": {
            "executable_lines": 1,
            "covered_lines": 1,
            "missing_lines": 0,
        }
    }
