#!/usr/bin/env python3
"""Synchronize tracked integration/e2e surfaces in integration_vcr_policy.yaml."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Iterable
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "configs" / "quality" / "integration_vcr_policy.yaml"


def _iter_inventory_paths(node: object) -> list[str]:
    if isinstance(node, str):
        return [node]
    if isinstance(node, list):
        paths: list[str] = []
        for item in node:
            paths.extend(_iter_inventory_paths(item))
        return paths
    if isinstance(node, dict):
        paths: list[str] = []
        for item in node.values():
            paths.extend(_iter_inventory_paths(item))
        return paths
    return []


def _sorted_unique(values: Iterable[str]) -> list[str]:
    return sorted({value.replace("\\", "/") for value in values})


def _ensure_list(node: dict[str, object], key: str) -> list[str]:
    value = node.setdefault(key, [])
    if isinstance(value, list):
        return value
    raise TypeError(f"{key} must stay a list")


def _ensure_dict(node: dict[str, object], key: str) -> dict[str, object]:
    value = node.setdefault(key, {})
    if isinstance(value, dict):
        return value
    raise TypeError(f"{key} must stay a dict")


def _path_exists(relative_path: str) -> bool:
    return (ROOT / relative_path).exists()


def _classify_integration(
    relative_path: str,
    integration: dict[str, object],
) -> None:
    normalized = relative_path.replace("\\", "/")
    parts = Path(normalized).parts
    filename = Path(normalized).name
    governance = _ensure_dict(integration, "governance_and_runtime_surfaces")

    if normalized.startswith("tests/integration/interfaces/"):
        _ensure_list(integration, "interface_cli_surfaces").append(normalized)
        return
    if normalized.startswith("tests/integration/composite/"):
        _ensure_list(integration, "composite_config_and_merge").append(normalized)
        return
    if normalized.startswith("tests/integration/config/") or normalized.startswith(
        "tests/integration/infrastructure/"
    ) or normalized.startswith("tests/integration/ci/test_config_"):
        _ensure_list(integration, "config_and_storage_surfaces").append(normalized)
        return
    if normalized.startswith("tests/integration/validation/"):
        _ensure_list(integration, "external_validation_surfaces").append(normalized)
        return
    if normalized.startswith("tests/integration/chembl/"):
        _ensure_list(integration, "chembl_parameter_extraction_surfaces").append(
            normalized
        )
        return
    if normalized.startswith("tests/integration/adapters/"):
        providers = _ensure_dict(integration, "adapter_provider_surfaces")
        provider_key = "shared_http_behavior"
        for candidate in (
            "chembl",
            "crossref",
            "openalex",
            "pubchem",
            "pubmed",
            "semanticscholar",
            "uniprot",
        ):
            if candidate in normalized:
                provider_key = candidate
                break
        bucket = providers.setdefault(provider_key, [])
        if not isinstance(bucket, list):
            raise TypeError(f"adapter_provider_surfaces.{provider_key} must stay a list")
        bucket.append(normalized)
        return
    if normalized.startswith("tests/integration/pipelines/"):
        _ensure_list(integration, "normalization_and_pipeline_support").append(normalized)
        return

    if "grafana" in filename:
        bucket = governance.setdefault("grafana", [])
        if not isinstance(bucket, list):
            raise TypeError("governance_and_runtime_surfaces.grafana must stay a list")
        bucket.append(normalized)
        return
    if "prometheus" in filename:
        bucket = governance.setdefault("prometheus", [])
        if not isinstance(bucket, list):
            raise TypeError(
                "governance_and_runtime_surfaces.prometheus must stay a list"
            )
        bucket.append(normalized)
        return
    if "dq_" in filename:
        bucket = governance.setdefault("data_quality", [])
        if not isinstance(bucket, list):
            raise TypeError(
                "governance_and_runtime_surfaces.data_quality must stay a list"
            )
        bucket.append(normalized)
        return
    if (
        "runner_lifecycle" in filename
        or "preflight_health_modes" in filename
        or normalized.startswith("tests/integration/ci/")
    ):
        bucket = governance.setdefault("control_plane", [])
        if not isinstance(bucket, list):
            raise TypeError(
                "governance_and_runtime_surfaces.control_plane must stay a list"
            )
        bucket.append(normalized)
        return

    _ensure_list(integration, "normalization_and_pipeline_support").append(normalized)


def _classify_e2e(relative_path: str, e2e: dict[str, object]) -> None:
    normalized = relative_path.replace("\\", "/")
    filename = Path(normalized).name
    provider_runs = _ensure_dict(e2e, "provider_runs")
    scenario_runs = _ensure_dict(e2e, "scenario_runs")
    operational = _ensure_list(e2e, "operational_and_governance_surfaces")
    resilience = _ensure_list(e2e, "resilience_and_failure_surfaces")

    provider_map = {
        value.replace("\\", "/"): key
        for key, value in provider_runs.items()
        if isinstance(value, str)
    }
    scenario_map = {
        value.replace("\\", "/"): key
        for key, value in scenario_runs.items()
        if isinstance(value, str)
    }
    if normalized in provider_map or normalized in scenario_map:
        return

    resilience_hints = (
        "network_failure",
        "circuit_breaker",
        "graceful_shutdown",
        "with_dq_errors",
        "with_schema_drift",
        "resilience",
    )
    if any(hint in filename for hint in resilience_hints):
        resilience.append(normalized)
        return
    operational.append(normalized)


def _sorted_inventory(policy: dict[str, object]) -> dict[str, object]:
    tracked = policy["tracked_suite_inventory"]
    if not isinstance(tracked, dict):
        raise TypeError("tracked_suite_inventory must stay a mapping")

    integration = tracked["integration"]
    e2e = tracked["e2e"]
    if not isinstance(integration, dict) or not isinstance(e2e, dict):
        raise TypeError("tracked_suite_inventory sections must stay mappings")

    # Drop stale paths while preserving the current bucket topology.
    for bucket_name, bucket_value in list(integration.items()):
        if isinstance(bucket_value, list):
            integration[bucket_name] = _sorted_unique(
                value for value in bucket_value if _path_exists(value)
            )
        elif isinstance(bucket_value, dict):
            cleaned: dict[str, object] = {}
            for key, value in bucket_value.items():
                if isinstance(value, list):
                    cleaned[key] = _sorted_unique(
                        item for item in value if _path_exists(item)
                    )
                elif isinstance(value, str) and _path_exists(value):
                    cleaned[key] = value.replace("\\", "/")
            integration[bucket_name] = cleaned

    for bucket_name, bucket_value in list(e2e.items()):
        if isinstance(bucket_value, list):
            e2e[bucket_name] = _sorted_unique(
                value for value in bucket_value if _path_exists(value)
            )
        elif isinstance(bucket_value, dict):
            cleaned = {
                key: value.replace("\\", "/")
                for key, value in bucket_value.items()
                if isinstance(value, str) and _path_exists(value)
            }
            e2e[bucket_name] = dict(sorted(cleaned.items()))

    tracked_paths = {
        path.replace("\\", "/") for path in _iter_inventory_paths(tracked)
    }
    repo_integration_paths = sorted(
        str(path.relative_to(ROOT)).replace("\\", "/")
        for path in (ROOT / "tests" / "integration").rglob("test_*.py")
    )
    repo_e2e_paths = sorted(
        str(path.relative_to(ROOT)).replace("\\", "/")
        for path in (ROOT / "tests" / "e2e").rglob("test_*.py")
    )

    for relative_path in repo_integration_paths:
        if relative_path not in tracked_paths:
            _classify_integration(relative_path, integration)

    for relative_path in repo_e2e_paths:
        if relative_path not in tracked_paths:
            _classify_e2e(relative_path, e2e)

    for bucket_name, bucket_value in list(integration.items()):
        if isinstance(bucket_value, list):
            integration[bucket_name] = _sorted_unique(bucket_value)
        elif isinstance(bucket_value, dict):
            cleaned = {}
            for key, value in bucket_value.items():
                if isinstance(value, list):
                    cleaned[key] = _sorted_unique(value)
                elif isinstance(value, str):
                    cleaned[key] = value.replace("\\", "/")
            integration[bucket_name] = cleaned

    for bucket_name, bucket_value in list(e2e.items()):
        if isinstance(bucket_value, list):
            e2e[bucket_name] = _sorted_unique(bucket_value)
        elif isinstance(bucket_value, dict):
            e2e[bucket_name] = dict(
                sorted(
                    (
                        key,
                        value.replace("\\", "/"),
                    )
                    for key, value in bucket_value.items()
                    if isinstance(value, str)
                )
            )

    return policy


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Sync or validate tracked integration/e2e surfaces in integration_vcr_policy.yaml."
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true", help="Rewrite the policy file.")
    mode.add_argument("--check", action="store_true", help="Fail if drift is detected.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    write_mode = args.write or not args.check
    original = POLICY_PATH.read_text(encoding="utf-8")
    policy = yaml.safe_load(original)
    if not isinstance(policy, dict):
        raise TypeError("integration_vcr_policy.yaml must stay a mapping")

    updated = _sorted_inventory(policy)
    rendered = yaml.safe_dump(updated, sort_keys=False, allow_unicode=True)
    if rendered == original:
        print("[sync-integration-vcr-policy] inventory is already synchronized")
        return 0

    if write_mode:
        POLICY_PATH.write_text(rendered, encoding="utf-8")
        print("[sync-integration-vcr-policy] rewrote configs/quality/integration_vcr_policy.yaml")
        return 0

    print("[sync-integration-vcr-policy] drift detected in configs/quality/integration_vcr_policy.yaml")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
