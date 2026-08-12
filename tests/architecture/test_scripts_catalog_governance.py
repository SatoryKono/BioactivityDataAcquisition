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
"""Architecture tests for scripts catalog governance policy."""

from __future__ import annotations

import pytest

import contextlib
import importlib.util
import json
import io
import sys
from pathlib import Path

import yaml


pytestmark = pytest.mark.architecture


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_catalog_module():
    root = _project_root()
    module_path = root / "scripts" / "engineering" / "repo" / "check_scripts_catalog.py"
    spec = importlib.util.spec_from_file_location(
        "check_scripts_catalog_governance_test", module_path
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_scripts_catalog_governance_check_passes() -> None:
    """Scripts catalog policy must pass structural and lifecycle checks."""
    if sys.platform.startswith("win"):
        pytest.skip(
            "Scripts catalog governance check requires full repo walk which is prohibitively slow on Windows"
        )
    module = _load_catalog_module()
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        rc = module.main(["--catalog", "scripts/engineering/repo/catalog.yaml"])

    assert rc == 0, (
        "Scripts catalog governance validation failed.\n"
        f"stdout:\n{stdout.getvalue()}\n"
        f"stderr:\n{stderr.getvalue()}\n"
    )


def test_scripts_catalog_caps_active_script_surface() -> None:
    """Active script count must be governed by a no-growth lifecycle cap."""
    if sys.platform.startswith("win"):
        pytest.skip(
            "Scripts catalog governance check requires full repo walk which is prohibitively slow on Windows"
        )
    root = _project_root()
    catalog_path = root / "scripts" / "engineering" / "repo" / "catalog.yaml"
    manifest_path = root / "configs" / "quality" / "scripts_inventory_manifest.json"
    catalog = yaml.safe_load(catalog_path.read_text(encoding="utf-8"))

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    active_count = manifest["summary"]["status_counts"]["active"]

    lifecycle = catalog["lifecycle"]
    assert lifecycle["active_script_count_policy"] == "fail-fast-no-growth"
    assert lifecycle["active_script_count_max"] == active_count
    assert lifecycle["active_script_count_owner"]
    assert lifecycle["active_script_count_review_by"]


def test_temporary_scripts_require_all_governance_surfaces(tmp_path: Path) -> None:
    """A new scripts/temp executable must fail until every surface owns it."""
    module = _load_catalog_module()
    temp_root = tmp_path / "scripts" / "temp"
    temp_root.mkdir(parents=True)
    (temp_root / "README.md").write_text("# Temporary scripts\n", encoding="utf-8")
    (temp_root / "unregistered.py").write_text("pass\n", encoding="utf-8")
    violations: list[str] = []

    module._check_temporary_script_governance(
        root=tmp_path,
        scripts=[],
        entries={},
        violations=violations,
    )

    assert violations == [
        "temporary script missing from inventory manifest: "
        "scripts/temp/unregistered.py",
        "temporary script missing lifecycle registry entry: "
        "scripts/temp/unregistered.py",
        "temporary script missing from scripts/temp/README.md: "
        "scripts/temp/unregistered.py",
    ]


def test_temporary_scripts_reject_wrong_status_and_lifecycle(tmp_path: Path) -> None:
    """Temp entries must use the bounded temporary classification and review date."""
    module = _load_catalog_module()
    temp_root = tmp_path / "scripts" / "temp"
    temp_root.mkdir(parents=True)
    (temp_root / "README.md").write_text(
        "- `wrong.py` — diagnostic\n", encoding="utf-8"
    )
    (temp_root / "wrong.py").write_text("pass\n", encoding="utf-8")
    relative_path = "scripts/temp/wrong.py"
    violations: list[str] = []

    module._check_temporary_script_governance(
        root=tmp_path,
        scripts=[{"path": relative_path, "status": "active"}],
        entries={
            relative_path: {
                "decision": "legacy_manual_utility",
                "review_by": "later",
            }
        },
        violations=violations,
    )

    assert violations == [
        "temporary script must use status=temporary_diagnostic: "
        "scripts/temp/wrong.py (got 'active')",
        "temporary script must use decision=temporary_diagnostic: "
        "scripts/temp/wrong.py",
        "temporary script review_by must be YYYY-MM-DD: scripts/temp/wrong.py",
    ]


def test_scripts_catalog_declares_entrypoint_surfaces() -> None:
    """Entrypoint and router surfaces must be catalogued, not implicit."""
    root = _project_root()
    catalog_path = root / "scripts" / "engineering" / "repo" / "catalog.yaml"
    catalog = yaml.safe_load(catalog_path.read_text(encoding="utf-8"))

    entrypoints = catalog["entrypoints"]
    assert entrypoints["package_console_scripts"]["bioetl"] == (
        "src/bioetl/interfaces/cli/main.py"
    )
    for rel_path in entrypoints["script_routers"].values():
        assert (root / rel_path).is_file()
    for rel_path in entrypoints["workflow_surfaces"]:
        assert (root / rel_path).is_file()
