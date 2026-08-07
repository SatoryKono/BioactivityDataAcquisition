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
"""Architecture tests for visual smoke manifest validation."""

from __future__ import annotations

import pytest

import importlib.util
import sys
from pathlib import Path
from types import ModuleType


pytestmark = pytest.mark.architecture


def _load_module() -> ModuleType:
    repo_root = Path(__file__).resolve().parents[2]
    module_path = repo_root / "scripts" / "diagrams" / "check" / "check_diagram_visual_smoke.py"
    spec = importlib.util.spec_from_file_location(
        "check_diagram_visual_smoke_module", module_path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_load_manifest_rejects_absolute_entries(tmp_path: Path) -> None:
    module = _load_module()
    manifest = tmp_path / "visual.manifest"
    absolute_entry = (tmp_path / "outside.svg").resolve().as_posix()
    manifest.write_text(f"{absolute_entry}\n", encoding="utf-8")

    try:
        module.load_manifest(manifest)
    except ValueError as exc:
        assert "must be relative" in str(exc)
    else:
        raise AssertionError("Expected absolute manifest validation to fail")


def test_load_manifest_rejects_parent_traversal_entries(tmp_path: Path) -> None:
    module = _load_module()
    manifest = tmp_path / "visual.manifest"
    manifest.write_text("../escape.svg\n", encoding="utf-8")

    try:
        module.load_manifest(manifest)
    except ValueError as exc:
        assert "must not escape the repository root" in str(exc)
    else:
        raise AssertionError("Expected traversal manifest validation to fail")


def test_build_report_payload_records_visual_smoke_summary() -> None:
    module = _load_module()

    payload = module.build_report_payload(
        manifest=Path("docs/manifest.txt"),
        rel_paths=["docs/diagram.svg", "docs/other.svg"],
        changed=["docs/other.svg"],
        status="failed",
    )

    assert payload["schema_version"] == "diagram-visual-smoke-report-v1"
    assert payload["status"] == "failed"
    assert payload["checked_count"] == 2
    assert payload["changed_count"] == 1
    assert payload["changed_paths"] == ["docs/other.svg"]
    assert payload["errors"] == []


def test_write_json_report_creates_parent_directory(tmp_path: Path) -> None:
    module = _load_module()
    report_path = tmp_path / "reports" / "diagrams" / "visual-smoke.json"

    module.write_json_report(
        report_path,
        {
            "schema_version": "diagram-visual-smoke-report-v1",
            "status": "passed",
        },
    )

    assert report_path.exists()
    assert '"status": "passed"' in report_path.read_text(encoding="utf-8")


def test_main_writes_failed_json_report_when_baseline_changed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _load_module()
    manifest = tmp_path / "visual-smoke.txt"
    svg_path = tmp_path / "diagram.svg"
    manifest.write_text("diagram.svg\n", encoding="utf-8")
    svg_path.write_text("<svg></svg>", encoding="utf-8")
    report_path = tmp_path / "visual-smoke.json"

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(module, "changed_paths", lambda rel_paths: rel_paths)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "check_diagram_visual_smoke.py",
            "--manifest",
            "visual-smoke.txt",
            "--json-out",
            "visual-smoke.json",
        ],
    )

    exit_code = module.main()

    assert exit_code == 1
    payload = module.json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["status"] == "failed"
    assert payload["changed_paths"] == ["diagram.svg"]
