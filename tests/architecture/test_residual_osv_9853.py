# pyright: reportArgumentType=false
"""Residual OSV exception #9853: mermaid/Grafana/PYSEC, Scorecard #1294 stays open."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

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
    """Fail closed after 2026-11-30 so #9853 can close without losing the re-triage."""
    deadline = date.fromisoformat(EXPIRY)
    assert date.today() <= deadline, (
        f"Residual OSV exception expired on {EXPIRY}. "
        "Upgrade mermaid-cli/Grafana or renew §2.3.2 via #9859 with a new expiry."
    )


def test_security_md_and_pip_audit_ignore_are_timeboxed() -> None:
    security_md = SECURITY_MD.read_text(encoding="utf-8")
    workflow = SECURITY_WORKFLOW.read_text(encoding="utf-8")
    assert "PYSEC-2026-3721" in security_md
    assert EXPIRY in security_md
    assert "#1294" in security_md
    assert "osv-scanner.toml" in security_md
    assert "--ignore-vuln PYSEC-2026-3721" in workflow
    assert "--ignore-vuln CVE-2026-3219" in workflow
    assert EXPIRY in workflow
    assert "#9853" in workflow


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
    """Grafana 13 host still ships react-router 6; do not fake a 7.x/uuid 11 closeout."""
    for package_json in (SCENES_PKG, SELECTOR_PKG):
        payload = _json(package_json)
        assert "overrides" not in payload

    scenes = _lock_packages(SCENES_LOCK)
    selector = _lock_packages(SELECTOR_LOCK)
    assert scenes["node_modules/react-router"]["version"].startswith("6.")
    assert scenes["node_modules/uuid"]["version"].startswith("9.")
    assert "6.30.6" in {
        selector["node_modules/react-router-dom-v5-compat"]["version"],
        selector["node_modules/react-router-dom-v5-compat/node_modules/react-router"][
            "version"
        ],
    }
