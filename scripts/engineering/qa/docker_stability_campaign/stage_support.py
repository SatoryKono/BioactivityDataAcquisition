"""Shared state and evidence helpers for campaign stages."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .commands import manager_command, restart_baseline
from .model import (
    atomic_json,
    load_json,
    remember_evidence_tree,
    updated_now,
)


def save_state(path: Path, state: dict[str, Any]) -> None:
    updated_now(state)
    atomic_json(path, state)


def index_and_save(state: dict[str, Any], state_path: Path, evidence_dir: Path) -> None:
    remember_evidence_tree(state, evidence_dir, evidence_dir)
    save_state(state_path, state)


def probe_services(path: Path) -> dict[str, str]:
    return {
        str(row["service"]): str(row["container_id"])
        for row in load_json(path).get("services", [])
        if isinstance(row, Mapping) and row.get("service") and row.get("container_id")
    }


def clean_baseline(path: Path, baseline_path: Path) -> dict[str, str]:
    counts, containers = restart_baseline(load_json(path))
    atomic_json(
        baseline_path,
        {"restart_counts": counts, "container_ids": containers},
        replace=False,
    )
    return containers


def manager_step(
    runtime_origin: Path,
    contract: Path,
    spec: Any,
    action: str,
    report_dir: Path,
    timeout: float,
) -> dict[str, Any]:
    return manager_command(
        runtime_origin,
        action,
        spec,
        timeout,
        report_dir,
        contract=contract,
    )
