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
"""Architecture gates for Docker stability contract issues #6291 and #6292."""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from collections import namedtuple
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
import yaml


pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = ROOT / "configs/quality/docker_runtime_contracts.yaml"
PREFLIGHT_PATH = ROOT / "scripts/ops/runtime/docker/docker_runtime_preflight.py"
BASELINE_PATH = ROOT / "reports/quality/docker-stability-baseline.json"
MIGRATION_RUNBOOK = (
    ROOT / "docs/05-operations/runbooks/docker-compose-project-migration.md"
)


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _load_preflight() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "docker_runtime_preflight", PREFLIGHT_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _ports(service: dict[str, Any]) -> list[tuple[str, int]]:
    result: list[tuple[str, int]] = []
    for entry in service.get("ports", []) or []:
        assert isinstance(entry, str), "Long-form ports must be handled explicitly"
        parts = entry.split("/", maxsplit=1)[0].split(":")
        assert len(parts) == 3, f"Published port must declare host IP: {entry}"
        result.append((parts[0], int(parts[1])))
    return result


def test_contract_preserves_adr010_and_stability_slo() -> None:
    contract = _load_yaml(CONTRACT_PATH)

    assert contract["schema_version"] == "docker-runtime-contract-v1"
    assert contract["policy"]["adr"] == "ADR-010"
    assert contract["policy"]["canonical_runtime"] is False
    assert contract["stability_slo"] == {
        "startup_cycles": 10,
        "soak_hours": 7.2,
        "unexpected_exits": 0,
        "restart_count_delta": 0,
        "oom_kills": 0,
        "unresolved_unhealthy": 0,
        "recovery_seconds_p99": 180,
        "recovery_trials": 10,
    }
    assert contract["hardening_targets"]["implementation_issue"] == 6293
    assert contract["hardening_targets"]["logging"]["allowed_drivers"] == [
        "local",
        "json-file",
    ]
    assert contract["hardening_targets"]["logging"]["max_size_required"] is True
    assert contract["hardening_targets"]["logging"]["max_files_required"] is True
    assert contract["path_policy"]["mixed_origin_for_same_project_forbidden"] is True
    assert (
        contract["path_policy"]["discouraged_origin_scope"]
        == "dashboard_data_plane_required_bind_mounts"
    )
    assert contract["path_policy"]["discouraged_compose_working_dir_prefixes"] == [
        "/tmp/bioetl-issues"
    ]
    source_identity = contract["dashboard_data_plane"]["source_identity"]
    assert source_identity["report_marker_name"] == ".bioetl-report-source.json"
    assert source_identity["report_marker_schema_version"] == "bioetl-report-source-v1"
    assert source_identity["resolution_precedence"] == [
        "runtime_root",
        "process_environment",
        "repository_environment",
        "container_environment",
        "container_label",
    ]
    assert source_identity["comparison_states"] == [
        "missing",
        "invalid",
        "foreign",
        "aligned",
    ]


def test_every_compose_stack_has_unique_project_and_single_service_owner() -> None:
    contract = _load_yaml(CONTRACT_PATH)
    project_names: set[str] = set()
    actual_owners: dict[str, str] = {}

    for stack_name, stack in contract["stacks"].items():
        compose = _load_yaml(ROOT / stack["compose_file"])
        assert compose["name"] == stack["project_name"]
        assert compose["name"] not in project_names
        project_names.add(compose["name"])

        expected_services = set(stack["required_services"]) | set(
            stack["optional_services"]
        )
        assert set(compose["services"]) == expected_services
        for service_name in compose["services"]:
            assert service_name not in actual_owners, (
                f"{service_name} is owned by {actual_owners[service_name]} and {stack_name}"
            )
            actual_owners[service_name] = stack_name

    assert actual_owners == contract["service_ownership"]
    assert "bioactivitydataacquisition2" not in project_names


def test_published_ports_are_localhost_bound_and_have_one_owner() -> None:
    contract = _load_yaml(CONTRACT_PATH)
    actual: dict[int, tuple[str, str]] = {}

    for stack_name, stack in contract["stacks"].items():
        compose = _load_yaml(ROOT / stack["compose_file"])
        for service_name, service in compose["services"].items():
            for host, published in _ports(service):
                assert host == "127.0.0.1"
                assert published not in actual
                actual[published] = (stack_name, service_name)

    expected = {
        int(port): (owner["stack"], owner["service"])
        for port, owner in contract["host_ports"].items()
    }
    assert actual == expected


def test_alertmanager_helper_binds_the_tracked_root_config_directory() -> None:
    compose_path = ROOT / "scripts/ops/runtime/docker/compose/alertmanager.yml"
    compose = _load_yaml(compose_path)
    service = compose["services"]["alertmanager"]
    mount = service["volumes"][0]
    source = mount.split(":", maxsplit=1)[0]

    resolved = (compose_path.parent / source).resolve()
    assert resolved == (ROOT / "grafana").resolve()
    assert resolved.is_dir()
    assert "--config.file=/etc/bioetl-grafana/alertmanager.yml" in service["command"]


def test_explicit_container_names_are_unique_and_justified() -> None:
    contract = _load_yaml(CONTRACT_PATH)
    retained = contract["retained_container_names"]
    actual: dict[str, str] = {}

    for stack_name, stack in contract["stacks"].items():
        compose = _load_yaml(ROOT / stack["compose_file"])
        for _service_name, service in compose["services"].items():
            container_name = service.get("container_name")
            if not container_name:
                continue
            assert container_name not in actual
            actual[container_name] = stack_name
            assert retained[container_name]["stack"] == stack_name
            assert retained[container_name]["reason"].strip()

    assert set(actual) == set(retained)


def test_required_environment_contract_lists_names_only() -> None:
    contract = _load_yaml(CONTRACT_PATH)
    preflight = _load_preflight()

    for stack in contract["stacks"].values():
        compose = _load_yaml(ROOT / stack["compose_file"])
        actual_names: set[str] = set()
        for service in compose["services"].values():
            actual_names.update(preflight._environment_names(service))
        assert set(stack["required_environment_names"]) <= actual_names
        assert all("=" not in name for name in stack["required_environment_names"])
        assert set(stack.get("required_secret_environment_names", [])) <= set(
            stack["required_environment_names"]
        )
        required_values = stack.get("required_non_secret_environment_values", {})
        assert set(required_values) <= set(stack["required_environment_names"])
        assert set(required_values).isdisjoint(
            stack.get("required_secret_environment_names", [])
        )


def test_neo4j_environment_avoids_image_owned_configuration_names() -> None:
    contract = _load_yaml(CONTRACT_PATH)
    preflight = _load_preflight()
    expected_safe_names = {
        "neo4j": {
            "BIOETL_NEO4J_USERNAME",
            "BIOETL_NEO4J_PASSWORD",
        },
        "neo4j-audit": {
            "BIOETL_NEO4J_AUDIT_USERNAME",
            "BIOETL_NEO4J_AUDIT_PASSWORD",
        },
    }

    for stack_name, safe_names in expected_safe_names.items():
        stack = contract["stacks"][stack_name]
        compose = _load_yaml(ROOT / stack["compose_file"])
        service = next(iter(compose["services"].values()))
        container_names = preflight._container_environment_names(service)
        forbidden = set(stack["forbidden_container_environment_names"])

        assert forbidden == {"NEO4J_USERNAME", "NEO4J_PASSWORD"}
        assert container_names.isdisjoint(forbidden)
        assert safe_names <= container_names
        assert service["environment"]["NEO4J_AUTH"].startswith("neo4j/")


def test_preflight_reports_image_environment_namespace_collision() -> None:
    contract = _load_yaml(CONTRACT_PATH)
    preflight = _load_preflight()
    contract["stacks"]["main"]["forbidden_container_environment_names"] = [
        "NEO4J_USERNAME"
    ]

    findings, _ = preflight._static_observations(ROOT, contract)
    collisions = [finding for finding in findings if finding.code == "F004"]

    assert [
        (
            finding.evidence["stack"],
            finding.evidence["service"],
            finding.evidence["name"],
        )
        for finding in collisions
    ] == [("main", "bioetl", "NEO4J_USERNAME")]


def test_preflight_rejects_unsupported_neo4j_bootstrap_username(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    contract = _load_yaml(CONTRACT_PATH)
    preflight = _load_preflight()
    monkeypatch.setenv("NEO4J_USERNAME", "unsupported-user")
    monkeypatch.setenv("NEO4J_AUDIT_USERNAME", "unsupported-audit-user")

    findings, _ = preflight._static_observations(ROOT, contract)
    unsupported = [
        finding
        for finding in findings
        if finding.code == "ENVIRONMENT_VALUE_UNSUPPORTED"
    ]

    assert [
        (finding.evidence["stack"], finding.evidence["name"]) for finding in unsupported
    ] == [
        ("neo4j", "NEO4J_USERNAME"),
        ("neo4j-audit", "NEO4J_AUDIT_USERNAME"),
    ]
    assert "unsupported-user" not in repr(unsupported)
    assert "unsupported-audit-user" not in repr(unsupported)


def test_required_secret_presence_is_checked_without_reading_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    contract = _load_yaml(CONTRACT_PATH)
    preflight = _load_preflight()
    secret_names = {
        name
        for stack in contract["stacks"].values()
        for name in stack.get("required_secret_environment_names", [])
    }
    for name in secret_names:
        monkeypatch.setenv(name, "sentinel-must-not-appear")
    monkeypatch.delenv("NEO4J_PASSWORD")

    findings, _ = preflight._static_observations(ROOT, contract)
    missing = [finding for finding in findings if finding.code == "SECRET_MISSING"]

    assert [
        (finding.evidence["stack"], finding.evidence["name"]) for finding in missing
    ] == [
        ("main", "NEO4J_PASSWORD"),
        ("neo4j", "NEO4J_PASSWORD"),
    ]
    assert "sentinel-must-not-appear" not in repr(missing)


def test_shared_networks_use_one_literal_name_for_all_consumers() -> None:
    """Shared nets use fixed name; auto-create (labels) or legacy external:true."""
    contract = _load_yaml(CONTRACT_PATH)
    expected_owner = "scripts/ops/runtime/docker/runtime_manager.py"

    for logical_name, expected in contract["shared_networks"].items():
        for stack_name in expected["consumers"]:
            stack = contract["stacks"][stack_name]
            compose = _load_yaml(ROOT / stack["compose_file"])
            actual = compose["networks"][logical_name]
            assert actual.get("name") == expected["name"]
            if actual.get("external") is True:
                continue
            labels = actual.get("labels") or {}
            assert labels.get("com.bioetl.owner") == expected_owner
            assert actual.get("driver", "bridge") == "bridge"


def test_live_project_origin_and_foreign_port_are_gate_errors(tmp_path: Path) -> None:
    preflight = _load_preflight()
    contract = {
        "stacks": {
            "main": {
                "compose_file": "docker-compose.yml",
                "project_name": "bioetl-main",
                "migration": {"legacy_project_name": "legacy-merged"},
            }
        },
        "host_ports": {8081: {"stack": "main", "service": "bioetl"}},
        "path_policy": {"discouraged_origins": ["/mnt/c", "/mnt/d", "/mnt/e"]},
    }
    rows = [
        {
            "Name": "bioetl-main",
            "ConfigFiles": "E:\\repo\\docker-compose.yml,/home/user/repo/extra.yml",
        },
        {"Name": "legacy-merged", "ConfigFiles": "/home/user/legacy.yml"},
    ]

    origin_findings = preflight._project_origin_findings(tmp_path, rows, contract)
    port_findings = preflight._host_port_findings({8081}, {}, contract)

    assert {finding.code for finding in origin_findings} == {"PROJECT_ORIGIN"}
    assert any("mixes Windows" in finding.message for finding in origin_findings)
    assert len(port_findings) == 1
    assert port_findings[0].code == "HOST_PORT_COLLISION"
    assert preflight._is_discouraged_bind_source("E:\\repo", ("/mnt/e",))
    assert preflight._is_discouraged_bind_source("/mnt/e/repo", ("/mnt/e",))
    assert preflight._is_discouraged_bind_source(
        "/run/desktop/mnt/host/e/repo", ("/mnt/e",)
    )
    assert preflight._is_discouraged_bind_source("/host_mnt/e/repo", ("/mnt/e",))
    assert not preflight._is_discouraged_bind_source("/home/user/repo", ("/mnt/e",))


def test_windows_and_wsl_spellings_of_same_compose_file_are_not_origin_drift() -> None:
    """Docker Desktop WSL config path of this checkout is not PROJECT_ORIGIN."""
    preflight = _load_preflight()
    root = Path(r"E:\github\BioactivityDataAcquisition")
    contract = {
        "stacks": {
            "neo4j": {
                "compose_file": "docker-compose.neo4j.yml",
                "project_name": "bioetl-neo4j",
            }
        },
        "path_policy": {},
    }
    rows = [
        {
            "Name": "bioetl-neo4j",
            "ConfigFiles": (
                r"E:\github\BioactivityDataAcquisition\docker-compose.neo4j.yml,"
                "/mnt/e/github/bioactivitydataacquisition/docker-compose.neo4j.yml"
            ),
        }
    ]

    findings = preflight._project_origin_findings(root, rows, contract)

    assert findings == []


def test_foreign_clone_compose_file_is_still_project_origin() -> None:
    preflight = _load_preflight()
    root = Path(r"E:\github\BioactivityDataAcquisition")
    contract = {
        "stacks": {
            "neo4j": {
                "compose_file": "docker-compose.neo4j.yml",
                "project_name": "bioetl-neo4j",
            }
        },
        "path_policy": {},
    }
    rows = [
        {
            "Name": "bioetl-neo4j",
            "ConfigFiles": (
                "/mnt/e/g-drive/05_ai/github/bioactivitydataacquisition2/"
                "docker-compose.neo4j.yml"
            ),
        }
    ]

    findings = preflight._project_origin_findings(root, rows, contract)

    assert any(finding.code == "PROJECT_ORIGIN" for finding in findings)
    unexpected = next(
        finding
        for finding in findings
        if finding.code == "PROJECT_ORIGIN"
        and "unexpected config path" in finding.message
    )
    assert unexpected.severity == "error"


def test_transient_issue_worktree_compose_is_gate_error(tmp_path: Path) -> None:
    preflight = _load_preflight()
    contract = {
        "stacks": {
            "main": {
                "compose_file": "docker-compose.yml",
                "project_name": "bioetl-main",
            }
        },
        "path_policy": {
            "discouraged_compose_working_dir_prefixes": ["/tmp/bioetl-issues"]
        },
    }
    rows = [
        {
            "Name": "bioetl-main",
            "ConfigFiles": "/tmp/bioetl-issues-8860-8861/docker-compose.yml",
        }
    ]

    findings = preflight._project_origin_findings(tmp_path, rows, contract)

    assert any(finding.code == "TRANSIENT_ORIGIN" for finding in findings)
    transient = next(
        finding for finding in findings if finding.code == "TRANSIENT_ORIGIN"
    )
    assert transient.evidence["stack"] == "main"
    assert transient.severity == "error"


def test_mount_origin_proxy_gate_is_scoped_to_dashboard_artifacts() -> None:
    preflight = _load_preflight()
    proxy = "/run/desktop/mnt/host/wsl/docker-desktop-bind-mounts/Ubuntu/" + "a" * 64
    contract = {
        "path_policy": {
            "discouraged_origin_scope": ("dashboard_data_plane_required_bind_mounts")
        },
        "dashboard_data_plane": {
            "producer_stack": "main",
            "required_bind_mounts": {
                "/app/data": {},
                "/app/reports": {},
            },
        },
    }
    project_to_stack = {
        "bioetl-main": "main",
        "bioetl-monitoring": "monitoring",
    }
    config_only = [
        {
            "project": "bioetl-monitoring",
            "mounts": [
                {
                    "Type": "bind",
                    "Source": proxy,
                    "Destination": "/var/lib/grafana/dashboards",
                }
            ],
        }
    ]

    assert (
        preflight._mount_origin_findings(
            config_only,
            contract=contract,
            project_to_stack=project_to_stack,
            discouraged=("/run/desktop/mnt/host/wsl/docker-desktop-bind-mounts",),
        )
        == []
    )

    producer_reports = [
        {
            "project": "bioetl-main",
            "mounts": [
                {
                    "Type": "bind",
                    "Source": proxy,
                    "Destination": "/app/reports",
                }
            ],
        }
    ]
    findings = preflight._mount_origin_findings(
        producer_reports,
        contract=contract,
        project_to_stack=project_to_stack,
        discouraged=("/run/desktop/mnt/host/wsl/docker-desktop-bind-mounts",),
    )

    assert len(findings) == 1
    assert findings[0].code == "MOUNT_ORIGIN"
    assert findings[0].evidence["stack"] == "main"


def test_dashboard_data_plane_rejects_healthy_producer_from_stale_checkout(
    tmp_path: Path,
) -> None:
    preflight = _load_preflight()
    contract = {
        "dashboard_data_plane": {
            "producer_stack": "main",
            "producer_service": "bioetl",
            "required_bind_mounts": {
                "/app/data": {
                    "relative_source": "data",
                    "environment_name": "BIOETL_DASHBOARD_DATA_ROOT",
                },
                "/app/reports": {
                    "relative_source": "reports",
                    "environment_name": "BIOETL_DASHBOARD_REPORT_ROOT",
                },
            },
            "source_identity": {
                "schema_version": "bioetl-dashboard-source-v1",
                "environment_name": "BIOETL_RUNTIME_SOURCE_ID",
                "label_name": "io.bioetl.dashboard-source-id",
                "unmanaged_value": "unmanaged",
            },
        }
    }
    expected_environment = preflight.dashboard_source_environment(tmp_path, contract)
    containers = [
        {
            "project": "bioetl-main",
            "service": "bioetl",
            "dashboard_source_id": "unmanaged",
            "mounts": [
                {
                    "Type": "bind",
                    "Source": "/external/bioetl/data",
                    "Destination": "/app/data",
                },
                {
                    "Type": "bind",
                    "Source": "/external/bioetl/reports",
                    "Destination": "/app/reports",
                },
            ],
        }
    ]

    findings = preflight._dashboard_source_findings(
        tmp_path,
        containers,
        contract=contract,
        project_to_stack={"bioetl-main": "main"},
    )

    assert {finding.code for finding in findings} == {
        "DASHBOARD_REPORT_SOURCE_IDENTITY",
        "DASHBOARD_SOURCE_IDENTITY",
        "DASHBOARD_SOURCE_MOUNT",
    }
    assert sum(finding.code == "DASHBOARD_SOURCE_MOUNT" for finding in findings) == 2
    assert len(expected_environment["BIOETL_RUNTIME_SOURCE_ID"]) == 64


def test_dashboard_data_plane_accepts_exact_managed_mounts(tmp_path: Path) -> None:
    preflight = _load_preflight()
    contract = _load_yaml(CONTRACT_PATH)
    environment = preflight.dashboard_source_environment(tmp_path, contract)
    from bioetl.application.services.run_reports.paths import (
        write_report_root_source_identity,
    )

    (tmp_path / "reports" / "run-reports").mkdir(parents=True)
    write_report_root_source_identity(
        report_root=tmp_path / "reports" / "run-reports",
        source_id=environment["BIOETL_RUNTIME_SOURCE_ID"],
    )
    containers = [
        {
            "project": "bioetl-main",
            "service": "bioetl",
            "dashboard_source_id": environment["BIOETL_RUNTIME_SOURCE_ID"],
            "mounts": [
                {
                    "Type": "bind",
                    "Source": str(tmp_path / "data"),
                    "Destination": "/app/data",
                },
                {
                    "Type": "bind",
                    "Source": str(tmp_path / "reports"),
                    "Destination": "/app/reports",
                },
            ],
        }
    ]

    assert (
        preflight._dashboard_source_findings(
            tmp_path,
            containers,
            contract=contract,
            project_to_stack={"bioetl-main": "main"},
        )
        == []
    )


def test_dashboard_data_plane_rejects_container_env_label_conflict(
    tmp_path: Path,
) -> None:
    preflight = _load_preflight()
    contract = _load_yaml(CONTRACT_PATH)
    environment = preflight.dashboard_source_environment(tmp_path, contract)
    expected = environment["BIOETL_RUNTIME_SOURCE_ID"]
    foreign = "f" * 64 if expected != "f" * 64 else "e" * 64
    from bioetl.application.services.run_reports.paths import (
        write_report_root_source_identity,
    )

    (tmp_path / "reports" / "run-reports").mkdir(parents=True)
    write_report_root_source_identity(
        report_root=tmp_path / "reports" / "run-reports",
        source_id=expected,
    )
    containers = [
        {
            "project": "bioetl-main",
            "service": "bioetl",
            "environment": [f"BIOETL_RUNTIME_SOURCE_ID={expected}"],
            "dashboard_source_id": foreign,
            "mounts": [
                {
                    "Type": "bind",
                    "Source": str(tmp_path / "data"),
                    "Destination": "/app/data",
                },
                {
                    "Type": "bind",
                    "Source": str(tmp_path / "reports"),
                    "Destination": "/app/reports",
                },
            ],
        }
    ]

    findings = preflight._dashboard_source_findings(
        tmp_path,
        containers,
        contract=contract,
        project_to_stack={"bioetl-main": "main"},
    )

    source_findings = [
        finding for finding in findings if finding.code == "DASHBOARD_SOURCE_IDENTITY"
    ]
    assert len(source_findings) == 1
    assert source_findings[0].evidence["source"] == "container_environment"
    assert source_findings[0].evidence["conflicts"] == ["container_label"]


def test_runtime_source_identity_is_not_a_prometheus_label() -> None:
    observability_root = ROOT / "src/bioetl/infrastructure/observability"
    metric_paths = [
        path
        for path in observability_root.rglob("*.py")
        if "metric" in path.stem or "prometheus" in path.stem
    ]
    assert metric_paths
    forbidden = (
        "BIOETL_RUNTIME_SOURCE_ID",
        "runtime_source_id",
        "source_identity",
    )
    for path in metric_paths:
        content = path.read_text(encoding="utf-8")
        for marker in forbidden:
            assert marker not in content, f"{path.relative_to(ROOT)}: {marker}"


def test_neo4j_helpers_delegate_to_the_single_compose_owner() -> None:
    helper_paths = [
        ROOT / "scripts/ops/runtime/neo4j/neo4j_quick_start.sh",
        ROOT / "scripts/ops/runtime/neo4j/neo4j-recovery-checklist.ps1",
        ROOT / "scripts/memory/setup/wsl_startup.sh",
    ]

    for path in helper_paths:
        content = path.read_text(encoding="utf-8")
        assert "docker compose -p bioetl-neo4j" in content
        assert "docker run" not in content
        assert "docker rm -f" not in content
        assert "bioetl_secure_password" not in content
        assert "-p 7474:7474" not in content


def test_operator_surfaces_do_not_advertise_legacy_neo4j_owners_or_credentials() -> (
    None
):
    operations_root = ROOT / "docs/05-operations"
    forbidden = (
        "docker run -d --name bioetl-neo4j",
        "docker start bioetl-neo4j",
        "docker stop bioetl-neo4j",
        "docker restart bioetl-neo4j",
        "docker kill bioetl-neo4j",
        "docker rm bioetl-neo4j",
        "docker rm -f bioetl-neo4j",
        "NEO4J_AUTH=neo4j/bioetl_secure_password",
        "bioetl_secure_password",
        "audit_secure_password",
    )

    paths = list(operations_root.rglob("*.md"))
    paths.extend((ROOT / "scripts").rglob("*.sh"))
    paths.extend((ROOT / "scripts").rglob("*.ps1"))
    for path in paths:
        content = path.read_text(encoding="utf-8")
        for marker in forbidden:
            assert marker not in content, f"{path.relative_to(ROOT)}: {marker}"
        for line in content.splitlines():
            assert not re.search(
                r"docker\s+(?:start|stop|restart|kill|rm)\s+(?:-[^\s]+\s+)*bioetl-neo4j\b",
                line,
            ), f"{path.relative_to(ROOT)}: {line}"
            if "docker compose" in line and (
                "docker-compose.neo4j" in line
                or re.search(r"\bneo4j(?:-audit)?\b", line)
            ):
                assert re.search(r"-p\s+bioetl-neo4j(?:-audit)?\b", line), (
                    f"{path.relative_to(ROOT)}: projectless Compose command: {line}"
                )


@pytest.mark.parametrize(
    ("total_gib", "free_gib", "minimum_gib", "expect_disk_error"),
    [(100, 49, 50, True), (400, 79, 80, True), (400, 81, 80, False)],
)
def test_capacity_uses_maximum_of_50_gib_and_20_percent(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    total_gib: int,
    free_gib: int,
    minimum_gib: int,
    expect_disk_error: bool,
) -> None:
    preflight = _load_preflight()
    usage = namedtuple("usage", "total used free")
    contract = {
        "capacity": {
            "minimum_free_disk_gib": 50,
            "minimum_free_disk_percent": 20,
            "minimum_free_memory_gib": 0,
            "minimum_cpus": 0,
        }
    }
    monkeypatch.setattr(
        preflight,
        "_run_read_only",
        lambda *_args, **_kwargs: preflight.CommandObservation(
            command=["docker", "info"],
            available=True,
            returncode=0,
            stdout='{"DockerRootDir":"/docker-data"}',
            stderr="",
        ),
    )
    gib = 1024**3
    monkeypatch.setattr(
        preflight.shutil,
        "disk_usage",
        lambda _path: usage(
            total_gib * gib,
            (total_gib - free_gib) * gib,
            free_gib * gib,
        ),
    )

    observation, findings = preflight._capacity_observation(tmp_path, contract)

    assert observation["required_free_disk_bytes"] == minimum_gib * gib
    assert (
        "CAPACITY_DISK" in {finding.code for finding in findings}
    ) is expect_disk_error


def test_capacity_fails_closed_when_docker_root_is_unknown(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    preflight = _load_preflight()
    monkeypatch.setattr(
        preflight,
        "_run_read_only",
        lambda *_args, **_kwargs: preflight.CommandObservation(
            command=["docker", "info"],
            available=False,
            returncode=None,
            stdout="",
            stderr="daemon unavailable",
        ),
    )
    contract = {
        "capacity": {
            "minimum_free_disk_gib": 50,
            "minimum_free_disk_percent": 20,
            "minimum_free_memory_gib": 0,
            "minimum_cpus": 0,
        }
    }

    _, findings = preflight._capacity_observation(tmp_path, contract)

    assert "CAPACITY_DOCKER_ROOT" in {finding.code for finding in findings}


def test_known_bad_fixture_reports_filesystem_warp_and_ownership(
    tmp_path: Path,
) -> None:
    preflight = _load_preflight()
    (tmp_path / "images/filesystem").mkdir(parents=True)
    (tmp_path / "images/warp").mkdir(parents=True)
    (tmp_path / "images/filesystem/Dockerfile").write_text(
        "FROM node:22-alpine\nWORKDIR /app\nRUN npm install package\n",
        encoding="utf-8",
    )
    (tmp_path / "images/warp/Dockerfile").write_text(
        'FROM debian:12\nCMD ["warp-cli", "connect"]\n',
        encoding="utf-8",
    )
    (tmp_path / "main.yml").write_text(
        """name: shared\nservices:\n  warp:\n    build:\n      dockerfile: images/warp/Dockerfile\n""",
        encoding="utf-8",
    )
    (tmp_path / "codex.yml").write_text(
        "name: shared\n"
        "services:\n"
        "  mcp-filesystem:\n"
        "    build:\n"
        "      dockerfile: images/filesystem/Dockerfile\n"
        "    volumes:\n"
        "      - ./:/app\n",
        encoding="utf-8",
    )
    contract = {
        "schema_version": "docker-runtime-contract-v1",
        "policy": {"canonical_runtime": False},
        "stacks": {
            "main": {
                "compose_file": "main.yml",
                "project_name": "bioetl-main",
                "required_services": ["warp"],
                "optional_services": [],
            },
            "codex": {
                "compose_file": "codex.yml",
                "project_name": "bioetl-codex",
                "required_services": ["mcp-filesystem"],
                "optional_services": [],
            },
        },
        "service_ownership": {"warp": "main", "mcp-filesystem": "codex"},
        "host_ports": {},
        "capacity": {
            "minimum_free_disk_gib": 0,
            "minimum_free_memory_gib": 0,
            "minimum_cpus": 0,
        },
    }
    contract_path = tmp_path / "contract.yml"
    contract_path.write_text(yaml.safe_dump(contract), encoding="utf-8")

    report = preflight.build_report(tmp_path, contract_path, static_only=True)
    finding_codes = {finding["code"] for finding in report["findings"]}

    assert report["summary"]["ok"] is False
    assert {"F001", "F002", "F003"} <= finding_codes


def test_preflight_command_surface_is_read_only_and_secret_safe() -> None:
    preflight = _load_preflight()
    allowed_verbs = {
        ("docker", "--version"),
        ("docker", "compose", "version"),
        ("docker", "compose", "ls"),
        ("docker", "image", "inspect"),
        ("docker", "info"),
        ("docker", "inspect"),
        ("docker", "ps"),
        ("wsl.exe", "--status"),
        ("wsl.exe", "--version"),
    }
    assert preflight.READ_ONLY_COMMANDS == allowed_verbs
    assert "docker compose up" not in PREFLIGHT_PATH.read_text(encoding="utf-8")
    assert "docker compose down" not in PREFLIGHT_PATH.read_text(encoding="utf-8")


def test_persistent_mcp_compose_is_retired_in_favor_of_on_demand_servers() -> None:
    contract = _load_yaml(CONTRACT_PATH)
    assert "codex" not in contract["stacks"]
    assert not (ROOT / "docker-compose.codex.yml").exists()
    assert not list(
        (ROOT / "scripts/ops/runtime/docker/images").glob("mcp-*/Dockerfile")
    )

    forbidden = ("docker-compose.codex.yml", "bioetl-codex", "Start-MCP", "start_mcp")
    for relative in tuple(
        ROOT / "scripts" / name
        for name in ("startup.sh", "startup.ps1", "shutdown.sh", "shutdown.ps1")
    ):
        text = relative.read_text(encoding="utf-8")
        assert all(marker not in text for marker in forbidden), relative

    smoke = ROOT / "scripts/ai/mcp/protocol_smoke.py"
    smoke_text = smoke.read_text(encoding="utf-8")
    assert '"method": "initialize"' in smoke_text
    assert '"method": "tools/list"' in smoke_text


def test_docker_cli_resolver_separates_engine_and_desktop_mcp_capabilities() -> None:
    shell = (ROOT / "scripts/ai/mcp/support/docker_cli_resolver.sh").read_text(
        encoding="utf-8"
    )
    powershell = (ROOT / "scripts/ai/mcp/support/docker_cli_resolver.ps1").read_text(
        encoding="utf-8"
    )

    assert "resolve_docker_engine_bin" in shell
    assert "resolve_docker_mcp_gateway_bin" in shell
    assert "Resolve-DockerEngineBin" in powershell
    assert "Resolve-DockerMcpGatewayBin" in powershell
    assert "no incompatible Linux CLI fallback" in shell
    assert '"${candidate}" version' in shell
    powershell_wrapper = (ROOT / "scripts/ai/mcp/mcp_docker_wrapper.ps1").read_text(
        encoding="utf-8"
    )
    assert "Resolve-DockerMcpGatewayBin" in powershell_wrapper


def test_retained_services_use_immutable_images_and_complete_envelopes() -> None:
    contract = _load_yaml(CONTRACT_PATH)
    required_fields = {
        "mem_limit",
        "mem_reservation",
        "cpus",
        "pids_limit",
        "init",
        "stop_grace_period",
        "logging",
        "healthcheck",
        "restart",
    }
    for stack_name, stack in contract["stacks"].items():
        compose = _load_yaml(ROOT / stack["compose_file"])
        for service_name, service in compose["services"].items():
            missing = required_fields - set(service)
            assert not missing, (
                f"{stack_name}/{service_name}: missing {sorted(missing)}"
            )
            # Neo4j official image already uses tini; compose init:true double-inits.
            if stack_name == "neo4j" or service_name == "neo4j":
                assert service["init"] is False
            else:
                assert service["init"] is True
            logging = service["logging"]
            assert logging["driver"] in {"local", "json-file"}
            assert logging["options"]["max-size"]
            assert logging["options"]["max-file"]
            if "image" in service:
                assert "@sha256:" in service["image"], (
                    f"{stack_name}/{service_name}: image is not immutable"
                )
            if "build" in service:
                dockerfile = ROOT / service["build"].get("dockerfile", "Dockerfile")
                from_lines = [
                    line
                    for line in dockerfile.read_text(encoding="utf-8").splitlines()
                    if line.startswith("FROM ")
                ]
                assert from_lines
                assert all("@sha256:" in line for line in from_lines), dockerfile


def test_readiness_and_build_tools_fail_closed() -> None:
    main = _load_yaml(ROOT / "docker-compose.yml")
    monitoring = _load_yaml(ROOT / "docker-compose.monitoring.yml")
    main_health = " ".join(map(str, main["services"]["bioetl"]["healthcheck"]["test"]))
    renderer_health = monitoring["services"]["renderer"]["healthcheck"]["test"]

    assert "/health/live" in main_health
    assert "/health/ready" not in main_health
    # Opt-in monitoring is Prom/Grafana/renderer only (Loki/Promtail/Tempo removed).
    assert "loki" not in monitoring["services"]
    assert "promtail" not in monitoring["services"]
    assert "tempo" not in monitoring["services"]
    # Renderer is optional (screenshots); must not health-gate Grafana UI.
    assert "renderer" not in monitoring["services"]["grafana"]["depends_on"]
    assert (
        monitoring["services"]["grafana"]["depends_on"]["prometheus"]["condition"]
        == "service_healthy"
    )
    assert renderer_health == [
        "CMD",
        "grafana-image-renderer",
        "healthcheck",
    ]
    assert monitoring["services"]["renderer"]["healthcheck"]["start_period"] == "45s"

    dockerfile = (ROOT / "Dockerfile.bioetl").read_text(encoding="utf-8")
    assert "PYTHONPATH=/app/src" not in dockerfile
    assert "COPY --chown=root:root src/ ./src/" not in dockerfile
    operations_dockerfile = (ROOT / "docs/05-operations/Dockerfile").read_text(
        encoding="utf-8"
    )
    assert "uv==0.11.26" in dockerfile
    assert dockerfile.count("apt-get upgrade -y") == 2
    assert dockerfile.count("pip==26.1.2") == 2
    assert (
        dockerfile.count(
            "python@sha256:a116514e19457bcb7af7efe9c3dd0b9b71e85b317694e7882a1c52aa15a78134"
        )
        == 2
    )
    assert "python:3.12-slim-bookworm" in dockerfile
    assert (
        "4fad23465a06cc5149a541fbec6f87e234a64dc0550f6bfdd2d290d8f03240df"
        not in dockerfile
    )
    assert "uv==0.11.26" in operations_dockerfile
    setup_uv = (ROOT / ".github/actions/setup-python-uv/action.yml").read_text(
        encoding="utf-8"
    )
    assert 'version: "0.11.26"' in setup_uv
    assert "sys.exit(0)" not in dockerfile
    assert "/health/live" in dockerfile
    healthcheck_blob = "\n".join(
        line
        for line in dockerfile.splitlines()
        if "HEALTHCHECK" in line or "health/" in line
    )
    assert "/health/live" in healthcheck_blob
    assert "/health/ready" not in healthcheck_blob
    assert (
        'CMD ["health", "server", "--host", "0.0.0.0", "--port", "8000"]' in dockerfile
    )
    assert dockerfile.count('SHELL ["/bin/bash", "-o", "pipefail", "-c"]') == 2
    assert "python -m pip install --only-binary=:all: --no-cache-dir" in dockerfile
    assert dockerfile.count("pip==26.1.2") == 2
    assert "uv==0.11.26" in dockerfile
    assert "useradd -r -u 999 -g bioetl bioetl" in dockerfile
    assert "USER 999:999" in dockerfile
    assert "USER bioetl" not in dockerfile
    assert (
        'CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('
        "'http://127.0.0.1:8000/health/live', timeout=3).read()\"]" in dockerfile
    )
    assert "CMD python -c" not in dockerfile
    # Default main surface is health/metrics only on :8000 (Quarantine Explorer UI removed).
    bioetl_service = main["services"]["bioetl"]
    assert bioetl_service["entrypoint"] == ["/bin/sh", "-c"]
    bioetl_command = " ".join(map(str, bioetl_service["command"]))
    assert "bioetl health server --host 0.0.0.0 --port 8000" in bioetl_command
    assert "quarantine serve" not in bioetl_command
    assert bioetl_service["ports"] == ["127.0.0.1:8000:8000"]
    bioetl_health = " ".join(map(str, bioetl_service["healthcheck"]["test"]))
    assert "127.0.0.1:8000/health/live" in bioetl_health
    assert "8081" not in bioetl_health


def test_warp_is_absent_from_default_and_optional_runtime_surfaces() -> None:
    contract = _load_yaml(CONTRACT_PATH)
    main = _load_yaml(ROOT / contract["stacks"]["main"]["compose_file"])

    assert "warp" not in main["services"]
    assert "warp" not in contract["service_ownership"]
    assert not (ROOT / "scripts/ops/runtime/docker/images/warp/Dockerfile").exists()
    assert contract["shared_networks"]["runtime"]["name"] == "bioetl-runtime"


def test_lifecycle_entrypoints_delegate_to_fail_closed_runtime_manager() -> None:
    manager = (ROOT / "scripts/ops/runtime/docker/runtime_manager.py").read_text(
        encoding="utf-8"
    )
    assert "choices=(" in manager
    for action in (
        "check",
        "start",
        "stop",
        "status",
        "logs",
        "diagnose",
        "recover",
        "clean",
    ):
        assert f'"{action}"' in manager
    assert "max_attempts=max(1, min(args.max_attempts, 3))" in manager
    assert "--confirm-destructive" in manager
    assert '"down", "--remove-orphans"' in manager

    for relative in ("scripts/ops/docker-setup.sh", "scripts/ops/docker-setup.ps1"):
        adapter = (ROOT / relative).read_text(encoding="utf-8")
        assert "runtime_manager.py" in adapter
        assert "--volumes" not in adapter
        assert "docker rmi" not in adapter
        assert "docker system prune" not in adapter
        assert "Start-Sleep" not in adapter
        assert "docker compose" not in adapter

    for relative in tuple(
        ROOT / "scripts" / name for name in ("startup.ps1", "shutdown.ps1")
    ):
        adapter = relative.read_text(encoding="utf-8")
        assert "$ProjectDir = Split-Path -Parent $PSScriptRoot" in adapter


def test_desktop_recovery_is_evidence_first_bounded_and_user_confirmed() -> None:
    recovery = (ROOT / "scripts/ops/runtime/docker/restart-docker.ps1").read_text(
        encoding="utf-8"
    )

    for capability in ("status", "restart", "start", "logs", "diagnose"):
        assert (
            f"Test-DesktopCapability '{capability}'" in recovery
            or capability in recovery
        )
    assert "ConfirmLastResort" in recovery
    assert "I_UNDERSTAND_FORCE_TERMINATION_IS_DESTRUCTIVE" in recovery
    assert "last_resort_confirmation_bypass_rejected" in recovery
    assert "TimeoutSeconds" in recovery
    assert "CommandTimeoutSeconds" in recovery
    assert "System.Diagnostics.ProcessStartInfo" in recovery
    assert "WaitForExit($WaitMilliseconds)" in recovery
    assert "docker-desktop-recovery-v2" in recovery
    for classification in (
        "daemon_identity",
        "wsl_integration",
        "engine_topology",
        "vhd_attachment",
        "project_origins",
        "port_owners",
        "bind_path_translation",
        "data_capacity",
    ):
        assert classification in recovery
    assert "ConfirmImpact = 'High'" in recovery
    assert "wsl --shutdown" not in recovery
    assert recovery.index("diagnose") < recovery.index("Stop-Process -Force")


def test_preflight_stack_scope_does_not_require_unselected_stack_secrets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    preflight = _load_preflight()
    contract = _load_yaml(CONTRACT_PATH)
    for name in {
        secret
        for stack in contract["stacks"].values()
        for secret in stack.get("required_secret_environment_names", [])
    }:
        monkeypatch.delenv(name, raising=False)

    findings, _ = preflight._static_observations(ROOT, contract, selected_stack="main")
    missing = {
        finding.evidence["name"]
        for finding in findings
        if finding.code == "SECRET_MISSING"
    }
    assert missing == {"NEO4J_PASSWORD"}


def test_host_probe_has_bounded_labels_and_no_container_socket_mount() -> None:
    contract = _load_yaml(CONTRACT_PATH)
    probe = (ROOT / "scripts/ops/runtime/docker/docker_runtime_probe.py").read_text(
        encoding="utf-8"
    )
    assert "bioetl_docker_runtime_primary_cause" in probe
    assert "primary_cause" in probe
    assert "--pushgateway-url" in probe
    assert "/var/run/docker.sock" not in probe
    assert contract["host_probe"]["metric_labels"][
        "bioetl_docker_runtime_primary_cause"
    ] == ["project", "stack"]
    for metric, labels in contract["host_probe"]["metric_labels"].items():
        assert metric in probe
        assert labels == sorted(labels)

    for stack in contract["stacks"].values():
        compose = _load_yaml(ROOT / stack["compose_file"])
        for service in compose["services"].values():
            mounts = "\n".join(map(str, service.get("volumes", [])))
            assert "/var/run/docker.sock" not in mounts


def test_structured_command_output_is_parsed_before_evidence_is_bounded(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    preflight = _load_preflight()
    rows = [
        {"Name": f"project-{index}", "ConfigFiles": f"/home/user/{index}/compose.yml"}
        for index in range(200)
    ]
    payload = json.dumps(rows)
    assert len(payload) > 4000

    monkeypatch.setattr(
        preflight.subprocess,
        "run",
        lambda *_args, **_kwargs: type(
            "Completed", (), {"returncode": 0, "stdout": payload, "stderr": ""}
        )(),
    )
    observation = preflight._run_read_only(
        ["docker", "compose", "ls", "--all", "--format", "json"], cwd=tmp_path
    )

    assert len(preflight._json_rows(observation.stdout)) == 200
    assert len(preflight._command_evidence(observation)["stdout"]) == 4000


def test_pre_change_baseline_captures_all_original_root_causes_without_secrets() -> (
    None
):
    baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    codes = {finding["code"] for finding in baseline["findings"]}
    rendered = BASELINE_PATH.read_text(encoding="utf-8").lower()

    assert baseline["schema_version"] == "docker-stability-baseline-v1"
    assert baseline["summary"]["ok"] is False
    assert {"F001", "F002", "F003"} <= codes
    assert "ghp_" not in rendered
    assert "bioetl_secure_password" not in rendered
    assert "environment_names" in rendered


def test_migration_map_and_runbook_protect_legacy_neo4j_volume() -> None:
    contract = _load_yaml(CONTRACT_PATH)
    migration = contract["stacks"]["neo4j"]["migration"]
    runbook = MIGRATION_RUNBOOK.read_text(encoding="utf-8")

    assert migration["requires_backup_restore_drill"] is True
    assert migration["volume_map"] == {
        "bioactivitydataacquisition2_neo4j_data": "bioetl-neo4j_neo4j_data",
        "bioactivitydataacquisition2_neo4j_logs": "bioetl-neo4j_neo4j_logs",
    }
    assert "MUST NOT use `--volumes`" in runbook
    assert "backup/restore drill" in runbook
    assert "not_applicable_no_legacy_volume" in runbook


def _workflow_needs(job: dict[str, Any]) -> list[str]:
    raw = job.get("needs")
    if raw is None:
        return []
    if isinstance(raw, str):
        return [raw]
    return list(raw)


def _workflow_ancestors(jobs: dict[str, Any], job_name: str) -> set[str]:
    seen: set[str] = set()
    stack = list(_workflow_needs(jobs[job_name]))
    while stack:
        current = stack.pop()
        if current in seen or current not in jobs:
            continue
        seen.add(current)
        stack.extend(_workflow_needs(jobs[current]))
    return seen


def test_docker_push_uses_environment_and_does_not_publish_latest_on_main() -> None:
    workflow = _load_yaml(ROOT / ".github/workflows/docker.yml")
    job = workflow["jobs"]["docker-push"]
    rendered = json.dumps(job)

    assert job.get("environment") == "ghcr-publish"
    assert ":latest" not in rendered
    assert "docker/build-push-action@" not in rendered
    assert "bioetl-scanned-image-${{ github.sha }}" in rendered
    assert "docker manifest inspect" in rendered


def test_docker_push_requires_all_validation_jobs() -> None:
    workflow = _load_yaml(ROOT / ".github/workflows/docker.yml")
    jobs = workflow["jobs"]
    ancestors = _workflow_ancestors(jobs, "docker-push")

    assert "docker-runtime-contracts" in ancestors
    assert "docker-lint" in ancestors
    assert "docker-compose-validate" in ancestors
    assert "docker-build" in ancestors


def test_docker_built_image_trivy_emits_full_evidence_and_blocks_fixable_medium_plus() -> (
    None
):
    workflow = _load_yaml(ROOT / ".github/workflows/docker.yml")
    steps = workflow["jobs"]["docker-build"]["steps"]
    built = {
        str(step.get("name")): step
        for step in steps
        if step.get("uses", "").startswith("aquasecurity/trivy-action@")
        and "bioetl:${{ github.sha }}" in str(step.get("with", {}).get("image-ref", ""))
    }
    evidence = [step for name, step in built.items() if "evidence scan" in name]
    assert {step["with"]["format"] for step in evidence} == {"json", "sarif"}
    assert all(str(step["with"].get("exit-code")) == "0" for step in evidence)
    assert all(
        step["with"]["severity"] == "CRITICAL,HIGH,MEDIUM,UNKNOWN" for step in evidence
    )
    enforcement = next(
        step
        for step in steps
        if step.get("name") == "Enforce fixable Trivy Critical High Medium policy"
    )
    enforcement_command = str(enforcement["run"])
    assert "trivy_baseline" in enforcement_command
    assert "--fail-on-fixable" in enforcement_command
    assert "reports/security/trivy-results.json" in enforcement_command
    assert "reports/security/trivy-fixability-audit.json" in enforcement_command
    assert all(step["with"].get("ignore-unfixed") is False for step in built.values())
    assert all(step["with"].get("version") == "v0.70.0" for step in built.values())


def test_docker_security_baseline_is_uploaded_with_bounded_retention() -> None:
    workflow = _load_yaml(ROOT / ".github/workflows/docker.yml")
    steps = workflow["jobs"]["docker-build"]["steps"]
    step_names = [str(step.get("name")) for step in steps]
    upload = next(
        step
        for step in steps
        if step.get("name") == "Upload reproducible security baseline"
    )
    assert "steps.validate-baseline.outcome == 'success'" in upload["if"]
    assert "reports/security/baseline.sha256" in upload["with"]["path"]
    assert "reports/security/trivy-fixability-audit.json" in upload["with"]["path"]
    assert upload["with"]["if-no-files-found"] == "error"
    assert upload["with"]["retention-days"] == 30
    assert any(
        step.get("name") == "Generate SBOM for the scanned local image"
        and step["with"]["output-file"] == "reports/security/bioetl.spdx.json"
        for step in steps
    )
    base_scan = next(
        step
        for step in steps
        if step.get("name") == "Run Trivy on pinned Debian bookworm base image"
    )
    assert base_scan["with"]["format"] == "json"
    assert base_scan["with"]["output"] == ("reports/security/trivy-base-results.json")
    assert step_names.index("Validate complete security baseline") < step_names.index(
        "Upload reproducible security baseline"
    )
    assert step_names.index("Generate Trivy fixability audit") < step_names.index(
        "Validate complete security baseline"
    )
    assert step_names.index("Enforce fixable Trivy Critical High Medium policy") < (
        step_names.index("Export exact scanned image for publication")
    )


def test_docker_security_gate_covers_dependency_build_inputs() -> None:
    workflow = _load_yaml(ROOT / ".github/workflows/docker.yml")
    trigger = workflow.get("on", workflow.get(True))
    assert isinstance(trigger, dict)
    for event in ("push", "pull_request"):
        paths = set(trigger[event]["paths"])
        assert {
            "Dockerfile.bioetl",
            "pyproject.toml",
            "uv.lock",
            "src/**",
            "configs/**",
            ".dockerignore",
        } <= paths
