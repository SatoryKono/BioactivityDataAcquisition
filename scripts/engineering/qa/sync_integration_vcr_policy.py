#!/usr/bin/env python3
"""Synchronize tracked integration/e2e surfaces in integration_vcr_policy.yaml."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Callable, Iterable
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
POLICY_PATH = ROOT / "configs" / "quality" / "integration_vcr_policy.yaml"


def _atomic_write_text(path: Path, content: str) -> None:
    tmp_path = path.with_name(f"{path.name}.tmp")
    tmp_path.write_text(content, encoding="utf-8")
    os.replace(tmp_path, path)


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


def _append_governance_surface(
    governance: dict[str, object],
    bucket_name: str,
    relative_path: str,
) -> None:
    bucket = governance.setdefault(bucket_name, [])
    if not isinstance(bucket, list):
        raise TypeError(
            f"governance_and_runtime_surfaces.{bucket_name} must stay a list"
        )
    bucket.append(relative_path)


def _classify_adapter_surface(
    relative_path: str,
    integration: dict[str, object],
) -> bool:
    if not relative_path.startswith("tests/integration/adapters/"):
        return False
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
        if candidate in relative_path:
            provider_key = candidate
            break
    bucket = providers.setdefault(provider_key, [])
    if not isinstance(bucket, list):
        raise TypeError(f"adapter_provider_surfaces.{provider_key} must stay a list")
    bucket.append(relative_path)
    return True


def _classify_integration_path_prefix(
    relative_path: str,
    integration: dict[str, object],
) -> bool:
    path_buckets = (
        ("tests/integration/interfaces/", "interface_cli_surfaces"),
        ("tests/integration/composite/", "composite_config_and_merge"),
        ("tests/integration/validation/", "external_validation_surfaces"),
        (
            "tests/integration/chembl/",
            "chembl_parameter_extraction_surfaces",
        ),
        (
            "tests/integration/pipelines/",
            "normalization_and_pipeline_support",
        ),
    )
    for prefix, bucket_name in path_buckets:
        if relative_path.startswith(prefix):
            _ensure_list(integration, bucket_name).append(relative_path)
            return True
    if (
        relative_path.startswith("tests/integration/config/")
        or relative_path.startswith("tests/integration/infrastructure/")
        or relative_path.startswith("tests/integration/ci/test_config_")
    ):
        _ensure_list(integration, "config_and_storage_surfaces").append(relative_path)
        return True
    return _classify_adapter_surface(relative_path, integration)


def _classify_integration_governance_surface(
    relative_path: str,
    filename: str,
    governance: dict[str, object],
) -> bool:
    if "grafana" in filename:
        _append_governance_surface(governance, "grafana", relative_path)
        return True
    if "prometheus" in filename:
        _append_governance_surface(governance, "prometheus", relative_path)
        return True
    if "dq_" in filename:
        _append_governance_surface(governance, "data_quality", relative_path)
        return True
    if (
        "runner_lifecycle" in filename
        or "preflight_health_modes" in filename
        or relative_path.startswith("tests/integration/ci/")
    ):
        _append_governance_surface(governance, "control_plane", relative_path)
        return True
    return False


def _classify_integration(
    relative_path: str,
    integration: dict[str, object],
) -> None:
    normalized = relative_path.replace("\\", "/")
    filename = Path(normalized).name
    governance = _ensure_dict(integration, "governance_and_runtime_surfaces")
    if _classify_integration_path_prefix(normalized, integration):
        return
    if _classify_integration_governance_surface(normalized, filename, governance):
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


def _clean_inventory_bucket_values(bucket_value: object) -> object:
    if isinstance(bucket_value, list):
        return _sorted_unique(value for value in bucket_value if _path_exists(value))
    if isinstance(bucket_value, dict):
        cleaned: dict[str, object] = {}
        for key, value in bucket_value.items():
            if isinstance(value, list):
                cleaned[key] = _sorted_unique(
                    item for item in value if _path_exists(item)
                )
            elif isinstance(value, str) and _path_exists(value):
                cleaned[key] = value.replace("\\", "/")
        return cleaned
    return bucket_value


def _clean_e2e_bucket_values(bucket_value: object) -> object:
    if isinstance(bucket_value, list):
        return _sorted_unique(value for value in bucket_value if _path_exists(value))
    if isinstance(bucket_value, dict):
        cleaned = {
            key: value.replace("\\", "/")
            for key, value in bucket_value.items()
            if isinstance(value, str) and _path_exists(value)
        }
        return dict(sorted(cleaned.items()))
    return bucket_value


def _clean_tracked_inventory(
    integration: dict[str, object],
    e2e: dict[str, object],
) -> None:
    for bucket_name, bucket_value in integration.items():
        integration[bucket_name] = _clean_inventory_bucket_values(bucket_value)
    for bucket_name, bucket_value in e2e.items():
        e2e[bucket_name] = _clean_e2e_bucket_values(bucket_value)


def _repo_suite_paths(suite_name: str) -> list[str]:
    return sorted(
        str(path.relative_to(ROOT)).replace("\\", "/")
        for path in (ROOT / "tests" / suite_name).rglob("test_*.py")
    )


def _tracked_inventory_paths(tracked: dict[str, object]) -> set[str]:
    return {path.replace("\\", "/") for path in _iter_inventory_paths(tracked)}


def _add_missing_inventory_paths(
    repo_paths: Iterable[str],
    tracked_paths: set[str],
    classifier: Callable[[str, dict[str, object]], None],
    bucket: dict[str, object],
) -> None:
    for relative_path in repo_paths:
        if relative_path not in tracked_paths:
            classifier(relative_path, bucket)


def _sorted_bucket_values(bucket_value: object) -> object:
    if isinstance(bucket_value, list):
        return _sorted_unique(bucket_value)
    if isinstance(bucket_value, dict):
        cleaned: dict[str, object] = {}
        for key, value in bucket_value.items():
            if isinstance(value, list):
                cleaned[key] = _sorted_unique(value)
            elif isinstance(value, str):
                cleaned[key] = value.replace("\\", "/")
        return cleaned
    return bucket_value


def _sorted_e2e_bucket_values(bucket_value: object) -> object:
    if isinstance(bucket_value, list):
        return _sorted_unique(bucket_value)
    if isinstance(bucket_value, dict):
        return dict(
            sorted(
                (
                    key,
                    value.replace("\\", "/"),
                )
                for key, value in bucket_value.items()
                if isinstance(value, str)
            )
        )
    return bucket_value


def _sort_tracked_inventory(
    integration: dict[str, object],
    e2e: dict[str, object],
) -> None:
    for bucket_name, bucket_value in integration.items():
        integration[bucket_name] = _sorted_bucket_values(bucket_value)
    for bucket_name, bucket_value in e2e.items():
        e2e[bucket_name] = _sorted_e2e_bucket_values(bucket_value)


def _sorted_inventory(policy: dict[str, object]) -> dict[str, object]:
    tracked = policy["tracked_suite_inventory"]
    if not isinstance(tracked, dict):
        raise TypeError("tracked_suite_inventory must stay a mapping")

    integration = tracked["integration"]
    e2e = tracked["e2e"]
    if not isinstance(integration, dict) or not isinstance(e2e, dict):
        raise TypeError("tracked_suite_inventory sections must stay mappings")

    _clean_tracked_inventory(integration, e2e)
    tracked_paths = _tracked_inventory_paths(tracked)
    _add_missing_inventory_paths(
        _repo_suite_paths("integration"),
        tracked_paths,
        _classify_integration,
        integration,
    )
    _add_missing_inventory_paths(
        _repo_suite_paths("e2e"),
        tracked_paths,
        _classify_e2e,
        e2e,
    )
    _sort_tracked_inventory(integration, e2e)

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
        _atomic_write_text(POLICY_PATH, rendered)
        print(
            "[sync-integration-vcr-policy] rewrote configs/quality/integration_vcr_policy.yaml"
        )
        return 0

    print(
        "[sync-integration-vcr-policy] drift detected in configs/quality/integration_vcr_policy.yaml"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
