"""Regression tests for the dashboard stack cutover helper."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scripts.ops.runtime.docker import recreate_cutover_stacks as cutover

pytestmark = [pytest.mark.unit, pytest.mark.repo_backed]


def test_container_env_falls_back_to_current_container_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def fake_container_env(container: str) -> dict[str, str]:
        calls.append(container)
        if container == "missing":
            raise RuntimeError("not found")
        return {"NEO4J_PASSWORD": "managed"}

    monkeypatch.setattr(cutover, "_container_env", fake_container_env)

    result = cutover._container_env_from_candidates(("missing", "bioetl"))

    assert result == {"NEO4J_PASSWORD": "managed"}
    assert calls == ["missing", "bioetl"]


def test_recreate_main_forces_image_rebuild(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    compose_file = tmp_path / "docker-compose.yml"
    compose_file.write_text("services: {}\n", encoding="utf-8")
    commands: list[list[str]] = []

    def fake_run(
        command: list[str],
        *,
        cwd: Path | None = None,
        env: dict[str, str] | None = None,
        timeout: float = 600.0,
    ) -> subprocess.CompletedProcess[str]:
        del cwd, env, timeout
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(cutover, "_run", fake_run)

    cutover.recreate_stack(
        runtime=tmp_path,
        project="bioetl-main",
        compose_file=compose_file,
        env_overrides={},
        build=True,
    )

    assert commands[0][-2:] == ["down", "--remove-orphans"]
    assert commands[1][-3:] == ["-d", "--remove-orphans", "--build"]
