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
"""Closeout guardrails for technical-debt issues #5507-#5509."""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
CLOSEOUT = ROOT / "reports" / "quality" / "tech-debt-issues-5507-5509-closeout.json"
CLI_CONFIG_BOOTSTRAP = (
    ROOT / "src" / "bioetl" / "composition" / "bootstrap" / "cli" / "config.py"
)
MAINTENANCE_SERVICE_ACCESS = (
    ROOT
    / "src"
    / "bioetl"
    / "interfaces"
    / "cli"
    / "commands"
    / "domains"
    / "maintenance"
    / "service_access.py"
)
CONTRACT_POLICY_LOADER = (
    ROOT / "src" / "bioetl" / "infrastructure" / "config" / "contract_policy_loader.py"
)
ENTITY_CONFIGS_ROOT = ROOT / "configs" / "entities"


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict), path
    return payload


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.add(node.module)
    return imported


def _collect_exact_importers(target_module: str) -> set[str]:
    importers: set[str] = set()
    for path in sorted((ROOT / "src" / "bioetl").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            modules: list[str] = []
            if isinstance(node, ast.Import):
                modules.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                modules.append(node.module or "")
            if any(module_name == target_module for module_name in modules):
                importers.add(path.relative_to(ROOT).as_posix())
                break
    return importers


def test_closeout_artifact_covers_requested_issues__5507_5509() -> None:
    payload = _load_json(CLOSEOUT)
    issues = payload["issues"]
    assert payload["schema_version"] == "tech-debt-issues-5507-5509-closeout-v1"
    assert payload["debt_budget_outcome"] == "reduced_or_unchanged"
    assert {issue["number"] for issue in issues} == {5507, 5508, 5509}
    assert all(issue["status"] == "closed-ready" for issue in issues)


def test_issue_5507_cli_config_bootstrap_uses_owner_config_access_seam() -> None:
    imported_modules = _imports(CLI_CONFIG_BOOTSTRAP)
    assert "bioetl.composition.runtime_builders.config_access" in imported_modules
    assert "bioetl.infrastructure.config.config_root" not in imported_modules
    assert "bioetl.infrastructure.config.pipeline_config_api" not in imported_modules


def test_issue_5508_maintenance_cli_chain_no_longer_imports_retained_facade() -> None:
    imported_modules = _imports(MAINTENANCE_SERVICE_ACCESS)
    assert "bioetl.composition.maintenance_service_access" in imported_modules
    assert "bioetl.composition.maintenance_api" not in imported_modules
    assert _collect_exact_importers("bioetl.composition.maintenance_api") == set()


def test_issue_5509_contract_policy_loader_no_longer_contains_compat_backfills() -> (
    None
):
    source = CONTRACT_POLICY_LOADER.read_text(encoding="utf-8")
    assert "_apply_root_hash_policy_contract_overrides" not in source
    assert "_apply_rollout_defaults" not in source
    assert "_default_contract_identity" not in source
    assert "_validate_root_hash_policy_compatibility" not in source


def test_issue_5509_entity_contract_identity_stays_explicit() -> None:
    for path in sorted(ENTITY_CONFIGS_ROOT.rglob("*.yaml")):
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict):
            continue
        contracts = payload.get("contracts")
        if not isinstance(contracts, dict):
            continue

        provider = str(payload.get("provider", "")).strip()
        entity = str(payload.get("entity", "")).strip()
        root_hash_policy = payload.get("hash_policy")
        assert isinstance(root_hash_policy, dict), path
        contract_metadata = root_hash_policy.get("contract")
        assert isinstance(contract_metadata, dict), path
        active_version = str(contract_metadata.get("version", "")).strip()

        assert contracts.get("contract_ref") == f"{provider}.{entity}", path
        assert contracts.get("active_version") == active_version, path
        assert contracts.get("hash_include") == [], path
        assert contracts.get("hash_exclude") == [], path

        rollout = contracts.get("rollout")
        assert rollout == {
            "mode": "single",
            "read_order": [active_version],
            "write_versions": [active_version],
            "affects_hash": False,
        }, path
