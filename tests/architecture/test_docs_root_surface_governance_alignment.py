from __future__ import annotations

import pytest

from pathlib import Path
import re
import subprocess
from typing import Any

import yaml


pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def _read_yaml(relative_path: str) -> dict[str, Any]:
    payload = yaml.safe_load(_read(relative_path))
    assert isinstance(payload, dict), f"{relative_path} must contain a YAML mapping"
    return payload


def _git_ls_files(*patterns: str) -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", *patterns],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return [line for line in result.stdout.splitlines() if line]

    # Windows / mixed-checkout git invocations occasionally fail even though the
    # governance invariant is simply "no tracked concepts/ surface remains".
    # Fall back to a filesystem scan so local empty/untracked directories do not
    # trip the test while still surfacing tracked-looking files if they exist.
    concepts_root = ROOT / "concepts"
    if not concepts_root.exists():
        return []

    tracked_like_paths: list[str] = []
    for path in concepts_root.rglob("*"):
        if any(part.startswith(".") for part in path.relative_to(concepts_root).parts):
            continue
        if path.is_file():
            tracked_like_paths.append(path.relative_to(ROOT).as_posix())
    return sorted(tracked_like_paths)


def test_adr_003_status_is_superseded_across_governance_surfaces() -> None:
    adr_text = _read(
        "docs/02-architecture/decisions/ADR-003-in-memory-locking-strategy.md"
    )
    adr_index_text = _read("docs/02-architecture/decisions/README.md")
    rules_text = _read("docs/00-project/RULES.md")

    assert "ADR-003" in adr_text
    assert "ADR-010" in adr_text
    assert re.search(r"status\s*:\s*superseded", adr_text, re.IGNORECASE)
    assert re.search(r"ADR-003.*\bSuperseded\b", adr_index_text, re.IGNORECASE)
    assert re.search(r"ADR-003.*\bSuperseded\b", rules_text, re.IGNORECASE)


def test_technical_debt_summary_tracks_live_exemption_baseline() -> None:
    summary_text = _read("docs/reports/evidence/technical-debt/SUMMARY.md")
    scorecard = _read_yaml("configs/quality/debt_scorecard.yaml")
    exemptions = _read_yaml("configs/quality/architecture_metric_exemptions.yaml")
    baseline = scorecard["baseline"]
    file_size_limits = baseline["by_registry"]["file_size_limits"]
    file_size_entries = exemptions["registries"]["file_size_limits"]

    assert len(file_size_entries) == file_size_limits
    assert f"`{file_size_limits}` active file-size-limit exemptions" in summary_text
    assert "не содержит active class/god-object" in summary_text
    assert "## Live File Size Exemption Inventory" in summary_text
    if not file_size_entries:
        assert "_No active file-size-limit exemptions_" in summary_text
    for path, metadata in file_size_entries.items():
        assert f"`{path}`" in summary_text
        assert metadata["owner"] in summary_text
        assert str(metadata["expires_on"]) in summary_text
        assert metadata["removal_step"] in summary_text


def _docker_helper_contract() -> dict[str, Any]:
    return _read_yaml("configs/quality/docker_helper_contracts.yaml")


def _environment_mapping(service: dict[str, Any]) -> dict[str, str]:
    environment = service.get("environment", {})
    if isinstance(environment, dict):
        return {str(key): str(value) for key, value in environment.items()}
    if isinstance(environment, list):
        result: dict[str, str] = {}
        for entry in environment:
            key, _, value = str(entry).partition("=")
            result[key] = value
        return result
    return {}


def test_docker_helper_contract_schema_is_explicit_and_fail_closed() -> None:
    contract = _docker_helper_contract()
    assert set(contract) == {"schema_version", "policy", "helpers"}
    assert contract["schema_version"] == 1

    policy = contract["policy"]
    assert set(policy) == {
        "adr",
        "canonical_runtime",
        "runtime_guardrail",
        "stable_anchor",
        "status",
    }
    assert policy["stable_anchor"] == "BIOETL_DOCKER_HELPER_ADR010_ADJUNCT"
    assert policy["adr"] == "ADR-010"
    assert policy["status"] == "optional_local_only_adjunct"
    assert policy["canonical_runtime"] is False
    assert "MUST NOT" in policy["runtime_guardrail"]

    allowed_helper_keys = {
        "credential_env",
        "forbidden_default_tokens",
        "forbidden_env_keys",
        "legacy_root_filename",
        "monitoring",
        "required_env_keys",
        "required_port_binds",
        "service",
        "status",
    }
    allowed_monitoring_keys = {
        "metrics_path",
        "posture",
        "prometheus_jobs",
        "reason",
    }
    for filename, helper in contract["helpers"].items():
        assert (ROOT / filename).is_file(), f"Missing helper compose file: {filename}"
        assert set(helper) <= allowed_helper_keys, (
            f"{filename} declares unsupported helper contract keys: "
            f"{sorted(set(helper) - allowed_helper_keys)}"
        )
        assert helper["status"] == "optional_local_only_adjunct"
        assert isinstance(helper["service"], str) and helper["service"]
        for key in (
            "credential_env",
            "forbidden_default_tokens",
            "forbidden_env_keys",
            "required_env_keys",
            "required_port_binds",
        ):
            if key in helper:
                assert isinstance(helper[key], list), f"{filename}.{key} must be a list"

        monitoring = helper["monitoring"]
        assert set(monitoring) <= allowed_monitoring_keys, (
            f"{filename} declares unsupported monitoring keys: "
            f"{sorted(set(monitoring) - allowed_monitoring_keys)}"
        )
        posture = monitoring["posture"]
        assert posture in {"healthcheck_only", "prometheus_scrape"}
        if posture == "prometheus_scrape":
            assert monitoring.get("prometheus_jobs")
            assert monitoring.get("metrics_path")
        else:
            assert monitoring.get("reason")


def test_root_governance_ratifies_reviewed_docker_helpers() -> None:
    contract = _docker_helper_contract()
    anchor = contract["policy"]["stable_anchor"]
    allowlist_text = _read(".github/root-allowlist.txt")
    file_policy_text = _read("docs/00-project/governance/03-file-policy.md")
    docker_quickstart_text = _read("docs/DOCKER_QUICKSTART.md")
    docker_setup_text = _read("docs/DOCKER_SETUP.md")

    assert contract["policy"]["adr"] == "ADR-010"
    assert contract["policy"]["canonical_runtime"] is False
    for text in (file_policy_text, docker_quickstart_text, docker_setup_text):
        assert anchor in text
        assert "configs/quality/docker_helper_contracts.yaml" in text

    for filename in contract["helpers"]:
        assert filename not in allowlist_text
        assert filename in docker_quickstart_text
        assert filename in docker_setup_text
        legacy_root_filename = contract["helpers"][filename]["legacy_root_filename"]
        assert legacy_root_filename not in allowlist_text
        assert legacy_root_filename in docker_quickstart_text
        assert legacy_root_filename in docker_setup_text

    assert "docker network create bioetl-monitoring" in docker_quickstart_text
    assert "docker network create bioetl-monitoring" in docker_setup_text


def test_docker_helper_compose_files_fail_closed_for_credentials_and_ports() -> None:
    contract = _docker_helper_contract()
    env_template_text = _read(".env.example")

    for filename, helper in contract["helpers"].items():
        compose_text = _read(filename)
        compose = _read_yaml(filename)
        all_ports = [
            str(port)
            for service in compose["services"].values()
            for port in service.get("ports", [])
        ]

        for env_name in helper.get("credential_env", []):
            assert f"${{{env_name}:?" in compose_text
            assert re.search(rf"^{re.escape(env_name)}=\s*$", env_template_text, re.M)

        for token in helper.get("forbidden_default_tokens", []):
            assert token not in compose_text
            assert token not in env_template_text

        for port in all_ports:
            assert port.startswith("127.0.0.1:"), (
                f"{filename} exposes helper port beyond localhost: {port}"
            )
        for required_port in helper.get("required_port_binds", []):
            assert required_port in all_ports


def test_sonarqube_helper_uses_canonical_environment_names() -> None:
    contract = _docker_helper_contract()
    helper = contract["helpers"]["scripts/ops/runtime/docker/compose/sonarqube.yml"]
    compose = _read_yaml("scripts/ops/runtime/docker/compose/sonarqube.yml")
    sonarqube_env = _environment_mapping(compose["services"]["sonarqube"])
    env_template_text = _read(".env.example")

    for key in helper["required_env_keys"]:
        assert key in sonarqube_env
    for key in helper["forbidden_env_keys"]:
        assert key not in sonarqube_env
        assert key not in env_template_text


def test_docker_helper_monitoring_contracts_match_prometheus_config() -> None:
    contract = _docker_helper_contract()
    prometheus = _read_yaml("grafana/prometheus.yml")
    jobs = {
        str(job["job_name"]): job
        for job in prometheus.get("scrape_configs", [])
        if isinstance(job, dict)
    }

    for filename, helper in contract["helpers"].items():
        compose = _read_yaml(filename)
        service = compose["services"][helper["service"]]
        monitoring = helper["monitoring"]
        posture = monitoring["posture"]
        if posture == "prometheus_scrape":
            expected_jobs = monitoring["prometheus_jobs"]
            expected_paths = monitoring["metrics_path"]
            if isinstance(expected_paths, str):
                expected_paths = [expected_paths]
            assert len(expected_jobs) == len(expected_paths)
            for expected_job, expected_path in zip(
                expected_jobs, expected_paths, strict=True
            ):
                assert expected_job in jobs
                assert jobs[expected_job]["metrics_path"] == expected_path
        elif posture == "healthcheck_only":
            assert "healthcheck" in service
            assert helper["service"] not in jobs
        else:
            raise AssertionError(f"Unknown helper monitoring posture: {posture}")


def test_canonical_docker_helpers_bootstrap_shared_external_networks() -> None:
    bash_helper = _read("scripts/ops/docker-setup.sh")
    powershell_helper = _read("scripts/ops/docker-setup.ps1")

    for helper_text in (bash_helper, powershell_helper):
        assert "bioetl-monitoring" in helper_text
        assert "warp-network" in helper_text
        assert "docker network inspect" in helper_text
        assert "docker network create" in helper_text


def test_concepts_root_surface_is_retired_from_repo_root() -> None:
    assert _git_ls_files("concepts", "concepts/**") == [], (
        "Root-level concepts/ surface must remain retired from the repository root"
    )
