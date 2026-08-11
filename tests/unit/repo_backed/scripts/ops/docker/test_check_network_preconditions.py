"""Unit tests for network precondition checker (no live Docker required)."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.ops.runtime.docker import check_network_preconditions as mod

pytestmark = [pytest.mark.unit, pytest.mark.repo_backed]


def test_contract_lists_shared_networks() -> None:
    contract = mod._load_contract(Path("configs/quality/docker_runtime_contracts.yaml"))
    shared = contract["shared_networks"]
    assert shared["monitoring"]["name"] == "bioetl-monitoring"
    assert "main" in shared["monitoring"]["consumers"]
    assert "monitoring" in shared["monitoring"]["consumers"]
    assert shared["runtime"]["name"] == "bioetl-runtime"


def test_missing_network_is_hard_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(args: list[str], *, timeout: float = 15.0) -> tuple[int, str, str]:
        del timeout
        if args[:3] == ["docker", "network", "inspect"]:
            return 1, "", "Error: network not found"
        return 0, "", ""

    monkeypatch.setattr(mod, "_run", fake_run)
    results = mod.check_shared_network(
        "bioetl-monitoring", expected_owner=mod.EXPECTED_OWNER
    )
    assert len(results) == 1
    assert results[0].ok is False
    assert results[0].code == "NETWORK_MISSING"


def test_owner_drift_is_hard_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(args: list[str], *, timeout: float = 15.0) -> tuple[int, str, str]:
        del timeout
        if args[:3] == ["docker", "network", "inspect"]:
            return (
                0,
                '{"Labels":{"com.bioetl.owner":"foreign-owner"}}',
                "",
            )
        return 0, "", ""

    monkeypatch.setattr(mod, "_run", fake_run)
    results = mod.check_shared_network(
        "bioetl-monitoring", expected_owner=mod.EXPECTED_OWNER
    )
    assert results[0].ok is False
    assert results[0].code == "NETWORK_OWNER_DRIFT"


def test_bioetl_not_on_monitoring_is_hard_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(args: list[str], *, timeout: float = 15.0) -> tuple[int, str, str]:
        del timeout
        if args[:2] == ["docker", "inspect"] and "bioetl" in args:
            return 0, '{"bioetl-runtime":{}}', ""
        return 0, "", ""

    monkeypatch.setattr(mod, "_run", fake_run)
    results = mod.check_bioetl_on_monitoring()
    assert results[0].ok is False
    assert results[0].code == "BIOETL_NOT_ON_MONITORING_NETWORK"


def test_bioetl_not_running_is_warning_not_hard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(args: list[str], *, timeout: float = 15.0) -> tuple[int, str, str]:
        del timeout
        if args[:2] == ["docker", "inspect"] and "bioetl" in args:
            return 1, "", "No such object"
        return 0, "", ""

    monkeypatch.setattr(mod, "_run", fake_run)
    results = mod.check_bioetl_on_monitoring()
    assert results[0].code == "BIOETL_NOT_RUNNING"
    # Treated as warning in main() — ok flag true so monitoring can still start.
    assert results[0].ok is True


def test_monitoring_stack_networks_do_not_include_runtime() -> None:
    contract = mod._load_contract(Path("configs/quality/docker_runtime_contracts.yaml"))
    names = [n for n, _o in mod._networks_for_stack(contract, "monitoring")]
    assert names == ["bioetl-monitoring"]
    main_names = [n for n, _o in mod._networks_for_stack(contract, "main")]
    assert set(main_names) == {"bioetl-monitoring", "bioetl-runtime"}


def test_ensure_creates_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_run(args: list[str], *, timeout: float = 15.0) -> tuple[int, str, str]:
        del timeout
        calls.append(list(args))
        if args[:3] == ["docker", "network", "inspect"]:
            return 1, "", "missing"
        if args[:3] == ["docker", "network", "create"]:
            return 0, "id", ""
        return 0, "", ""

    monkeypatch.setattr(mod, "_run", fake_run)
    result = mod.ensure_shared_network(
        "bioetl-monitoring", expected_owner=mod.EXPECTED_OWNER
    )
    assert result.ok is True
    assert result.code == "NETWORK_CREATED"
    create = [c for c in calls if c[:3] == ["docker", "network", "create"]][0]
    assert f"{mod.OWNER_LABEL}={mod.EXPECTED_OWNER}" in create


def test_run_checks_ensure_creates_all_for_stack_all(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Full reinstall: --stack all --ensure must create both shared nets."""
    contract = tmp_path / "contract.yml"
    contract.write_text(
        """
shared_networks:
  monitoring:
    name: bioetl-monitoring
    owner: scripts/ops/runtime/docker/runtime_manager.py
    consumers: [main, monitoring]
  runtime:
    name: bioetl-runtime
    owner: scripts/ops/runtime/docker/runtime_manager.py
    consumers: [main, neo4j]
""",
        encoding="utf-8",
    )
    created: list[str] = []
    state: dict[str, bool] = {}

    def fake_run(args: list[str], *, timeout: float = 15.0) -> tuple[int, str, str]:
        del timeout
        if args[:3] == ["docker", "network", "create"]:
            name = args[-1]
            created.append(name)
            state[name] = True
            return 0, "id", ""
        if args[:3] == ["docker", "network", "inspect"]:
            name = args[-1]
            # ensure path uses format owner; check path uses json
            if name not in state:
                return 1, "", "missing"
            if "--format" in args and "json" in " ".join(args):
                owner = mod.EXPECTED_OWNER
                return 0, f'{{"Labels":{{"com.bioetl.owner":"{owner}"}}}}', ""
            return 0, mod.EXPECTED_OWNER, ""
        if args[:2] == ["docker", "inspect"] and "bioetl" in args:
            return 1, "", "No such object"
        return 0, "", ""

    monkeypatch.setattr(mod, "_run", fake_run)
    results = mod.run_checks(stack="all", contract_path=contract, ensure=True)
    assert set(created) == {"bioetl-monitoring", "bioetl-runtime"}
    assert any(r.code == "NETWORK_CREATED" for r in results)
    assert all(
        r.ok
        for r in results
        if r.code
        not in {
            "BIOETL_NOT_RUNNING",
            "NETWORK_CREATED",
            "NETWORK_ALREADY_EXISTS",
            "NETWORK_OK",
            "BIOETL_ON_MONITORING_NETWORK",
        }
        or r.ok
    )
    hard = [r for r in results if not r.ok and r.evidence.get("severity") != "warning"]
    assert hard == []
