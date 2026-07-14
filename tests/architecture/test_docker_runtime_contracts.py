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
        "startup_cycles": 100,
        "soak_hours": 72,
        "unexpected_exits": 0,
        "restart_count_delta": 0,
        "oom_kills": 0,
        "unresolved_unhealthy": 0,
        "recovery_seconds_p99": 180,
        "recovery_trials": 100,
    }
    assert contract["hardening_targets"]["implementation_issue"] == 6293
    assert contract["path_policy"]["mixed_origin_for_same_project_forbidden"] is True


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


def test_shared_networks_use_one_external_literal_name_for_all_consumers() -> None:
    contract = _load_yaml(CONTRACT_PATH)

    for logical_name, expected in contract["shared_networks"].items():
        for stack_name in expected["consumers"]:
            stack = contract["stacks"][stack_name]
            compose = _load_yaml(ROOT / stack["compose_file"])
            actual = compose["networks"][logical_name]
            assert actual == {"external": True, "name": expected["name"]}


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
