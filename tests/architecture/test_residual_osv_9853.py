# pyright: reportArgumentType=false
"""Residual OSV exception #9853: mermaid/Grafana/PYSEC, Scorecard #1294 stays open."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

from bioetl.application.runtime_clock import current_utc_time

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "docs" / "00-project" / "governance" / "05-github-policy.md"
SECURITY_MD = ROOT / ".github" / "SECURITY.md"
SECURITY_WORKFLOW = ROOT / ".github" / "workflows" / "security.yml"
SCORECARD_WORKFLOW = ROOT / ".github" / "workflows" / "scorecard.yml"
MERMAID_PKG = ROOT / ".github" / "actions" / "setup-mermaid" / "package.json"
MERMAID_LOCK = ROOT / ".github" / "actions" / "setup-mermaid" / "package-lock.json"
MERMAID_ACTION = ROOT / ".github" / "actions" / "setup-mermaid" / "action.yml"
EXTRACT_ZIP = ROOT / ".github" / "actions" / "setup-mermaid" / "vendor" / "extract-zip"
SCENES_PKG = ROOT / "grafana" / "plugins" / "bioetl-scenes-app" / "package.json"
SCENES_LOCK = ROOT / "grafana" / "plugins" / "bioetl-scenes-app" / "package-lock.json"
SELECTOR_PKG = (
    ROOT / "grafana" / "plugins" / "bioetl-selectorshell-panel" / "package.json"
)
SELECTOR_LOCK = (
    ROOT / "grafana" / "plugins" / "bioetl-selectorshell-panel" / "package-lock.json"
)
EXPIRY = "2026-11-30"


def _json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return cast(dict[str, Any], payload)


def _lock_packages(path: Path) -> dict[str, Any]:
    packages = _json(path).get("packages")
    assert isinstance(packages, dict)
    return cast(dict[str, Any], packages)


def test_osv_scanner_toml_must_not_exist() -> None:
    """Scorecard Vulnerabilities #1294 must not be greened via osv-scanner.toml."""
    assert not (ROOT / "osv-scanner.toml").exists()
    assert not (ROOT / ".osv-scanner.toml").exists()
    assert not (ROOT / "osv-scanner.yml").exists()


def test_scorecard_workflow_does_not_ignore_vulnerabilities_check() -> None:
    text = SCORECARD_WORKFLOW.read_text(encoding="utf-8")
    workflow = yaml.safe_load(text)
    analysis = workflow["jobs"]["analysis"]
    scorecard_step = next(
        step
        for step in analysis["steps"]
        if str(step.get("uses", "")).startswith("ossf/scorecard-action@")
    )
    with_block = scorecard_step.get("with") or {}
    assert with_block.get("publish_results") is True
    assert "ignored_checks" not in with_block
    assert "checks" not in with_block
    lowered = text.lower()
    assert "ignored_checks" not in lowered
    assert "disable-vulnerabilities" not in lowered


def test_policy_documents_residual_osv_exception() -> None:
    text = POLICY.read_text(encoding="utf-8")
    assert "### 2.3.2 Residual OSV after RF-009 (#9853)" in text
    assert "Vulnerabilities" in text
    assert "#1294" in text
    assert "false green" in text
    assert EXPIRY in text
    assert "osv-scanner.toml" in text
    assert "PYSEC-2026-3721" in text
    assert "extract-zip" in text
    assert "grafana/plugins" in text
    assert "ADR-010" in text
    assert "#9859" in text


def test_residual_osv_exception_has_not_expired() -> None:
    """Keep the residual OSV exception pinned to the documented #9859 expiry."""
    deadline = date.fromisoformat(EXPIRY)
    assert deadline == date(2026, 11, 30)
    assert EXPIRY == "2026-11-30"
    assert current_utc_time().date() <= deadline, (
        f"residual OSV exception expired on {EXPIRY}; upgrade mermaid/Grafana "
        "or renew the exception with a new dated issue"
    )


def test_security_md_and_pip_audit_ignore_are_timeboxed() -> None:
    security_md = SECURITY_MD.read_text(encoding="utf-8")
    workflow = SECURITY_WORKFLOW.read_text(encoding="utf-8")
    pip_block = next(
        block
        for block in (ROOT / "uv.lock").read_text(encoding="utf-8").split("[[package]]")
        if 'name = "pip"' in block
    )
    assert "PYSEC-2026-3721" in security_md
    assert EXPIRY in security_md
    assert "#1294" in security_md
    assert "osv-scanner.toml" in security_md
    assert "26.2.1" in security_md
    assert "--ignore-vuln CVE-2026-3219" not in workflow
    assert "--ignore-vuln PYSEC-2026-3721" not in workflow
    assert EXPIRY in workflow
    assert "#9853" in workflow
    assert 'version = "26.2.1"' in pip_block


def test_mermaid_lockfile_keeps_patched_overrides() -> None:
    pkg = _json(MERMAID_PKG)
    overrides = pkg["overrides"]
    assert overrides["svgo"] == "3.3.5"
    assert overrides["tar-fs"] == "2.1.5"
    assert overrides["ws"] == "8.21.3"
    assert overrides["js-yaml"] == "4.3.2"
    assert overrides["extract-zip"] == "$extract-zip"

    packages = _lock_packages(MERMAID_LOCK)
    extract = packages["vendor/extract-zip"]
    assert extract["version"] == "2.0.2"
    assert packages["node_modules/svgo"]["version"] == "3.3.5"
    assert packages["node_modules/tar-fs"]["version"] == "2.1.5"
    assert packages["node_modules/ws"]["version"] == "8.21.3"
    assert packages["node_modules/js-yaml"]["version"] == "4.3.2"


def test_vendored_extract_zip_validates_symlink_targets() -> None:
    index = (EXTRACT_ZIP / "index.js").read_text(encoding="utf-8")
    action = MERMAID_ACTION.read_text(encoding="utf-8")
    assert "CVE-2026-56876" in index
    assert "assertPathInsideRoot" in index
    assert "symlink" in index
    assert 'cp -R "${ACTION_DIR}/vendor/." "${TOOL_DIR}/vendor/"' in action


def test_grafana_plugins_do_not_force_router_or_uuid_majors() -> None:
    """Only the explicit scenes bridge candidate may override the router seam."""
    selector_pkg = _json(SELECTOR_PKG)
    assert selector_pkg["overrides"] == {
        "react-router-dom-v5-compat": "$react-router-dom-v5-compat",
        "braces": "$braces",
        "@istanbuljs/load-nyc-config": {"js-yaml": "4.3.2"},
    }
    scenes_pkg = _json(SCENES_PKG)
    bridge_ref = (
        "file:../../tooling/router-v7-bridge/bioetl-grafana-router-v7-bridge-0.3.0.tgz"
    )
    assert scenes_pkg["dependencies"]["react-router-dom-v5-compat"] == bridge_ref
    assert selector_pkg["dependencies"]["react-router-dom-v5-compat"] == bridge_ref
    assert scenes_pkg["overrides"] == {
        "@grafana/scenes": {"react-router-dom": "7.18.4"},
        "braces": "$braces",
        "react-router-dom-v5-compat": "$react-router-dom-v5-compat",
        "@istanbuljs/load-nyc-config": {"js-yaml": "4.3.2"},
    }
    # This candidate has a real adapter for Grafana's legacy history contract;
    # a lockfile major alone is never host/runtime qualification evidence.
    bridge_root = ROOT / "grafana" / "tooling" / "router-v7-bridge"
    bridge = _json(bridge_root / "package.json")
    assert bridge["name"] == "@bioetl/grafana-router-v7-bridge"
    assert bridge["version"] == "0.3.0"
    assert bridge["dependencies"]["react-router-v7"] == "npm:react-router@7.18.4"
    assert bridge["dependencies"]["react-router-dom-v5"] == "npm:react-router-dom@5.3.4"
    assert (bridge_root / "bioetl-grafana-router-v7-bridge-0.3.0.tgz").is_file()
    scenes = _lock_packages(SCENES_LOCK)
    locked_bridge = scenes["node_modules/react-router-dom-v5-compat"]
    assert locked_bridge["name"] == bridge["name"]
    assert locked_bridge["version"] == bridge["version"]
    assert locked_bridge["resolved"] == bridge_ref
    assert scenes["node_modules/react-router"]["version"] == "7.18.4"
    assert scenes["node_modules/react-router-dom"]["version"] == "7.18.4"
    assert scenes["node_modules/react-router-v7"]["version"] == "7.18.4"
    # uuid comes from the declared Grafana dependency graph, without a forced
    # override or an invented security closeout.
    assert "uuid" not in scenes_pkg["overrides"]
    assert scenes["node_modules/uuid"]["version"] == "11.1.1"
    selector = _lock_packages(SELECTOR_LOCK)
    # NYC consumes only YAML's load API. Its compatibility/security fixtures
    # run in each installed plugin graph; the removed formatter must stay absent.
    for package, locked in ((scenes_pkg, scenes), (selector_pkg, selector)):
        assert "nyc-yaml-compat.test.cjs" in package["scripts"]["test:ci"]
        assert locked["node_modules/js-yaml"]["version"] == "4.3.2"
        assert not any(key.endswith("/sprintf-js") for key in locked)
        assert not any(
            key.endswith("/js-yaml") and row["version"].startswith("3.")
            for key, row in locked.items()
        )
    selector_bridge = selector["node_modules/react-router-dom-v5-compat"]
    assert selector_bridge["name"] == bridge["name"]
    assert selector_bridge["version"] == bridge["version"]
    assert selector_bridge["resolved"] == bridge_ref
    assert selector["node_modules/react-router"]["version"] == "5.3.4"
    assert selector["node_modules/react-router-dom"]["version"] == "5.3.4"
    assert selector["node_modules/react-router-v7"]["version"] == "7.18.4"


@pytest.mark.parametrize("lock_path", [SCENES_LOCK, SELECTOR_LOCK])
def test_grafana_locks_remove_vulnerable_legacy_yaml_chain(lock_path: Path) -> None:
    """Keep the audited YAML replacement and patched parser/source-map versions."""
    packages = _lock_packages(lock_path)
    expected = {
        "js-yaml": "4.3.2",
        "argparse": "2.0.1",
        "postcss-selector-parser": "7.1.6",
        "source-map-js": "1.2.2",
    }
    for name, version in expected.items():
        entries = [
            package
            for path, package in packages.items()
            if path.endswith(f"node_modules/{name}")
        ]
        assert entries, f"Missing audited dependency: {name}"
        assert all(package["version"] == version for package in entries), name
    assert not any(path.endswith("node_modules/sprintf-js") for path in packages)
