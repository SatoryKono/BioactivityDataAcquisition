"""Canonical Grafana QA scope for manual URLs and screenshot fixtures."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict

_QA_CONTEXT_PATH = Path("configs/quality/observability_qa_context.json")


class ObservabilityQaContext(TypedDict):
    """Bounded operator QA scope used by dashboard URLs and screenshots."""

    schema_version: str
    pipeline: str
    run_type: str
    provider: str
    run_id: str
    from_range: str
    to_range: str


def qa_context_path(repo_root: Path | None = None) -> Path:
    """Return the tracked QA context path."""
    root = repo_root if repo_root is not None else Path(".")
    return root / _QA_CONTEXT_PATH


def load_observability_qa_context(repo_root: Path | None = None) -> ObservabilityQaContext:
    """Load the single canonical QA context object."""
    payload = json.loads(qa_context_path(repo_root).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("observability QA context must be a JSON object")
    required = ("schema_version", "pipeline", "run_type", "provider", "run_id", "from", "to")
    missing = [key for key in required if not str(payload.get(key) or "").strip()]
    if missing:
        raise ValueError(f"observability QA context missing fields: {', '.join(missing)}")
    return {
        "schema_version": str(payload["schema_version"]),
        "pipeline": str(payload["pipeline"]),
        "run_type": str(payload["run_type"]),
        "provider": str(payload["provider"]),
        "run_id": str(payload["run_id"]),
        "from_range": str(payload["from"]),
        "to_range": str(payload["to"]),
    }


def grafana_qa_query_params(repo_root: Path | None = None) -> dict[str, str]:
    """Return Grafana query parameters derived from the canonical QA context."""
    context = load_observability_qa_context(repo_root)
    return {
        "var-pipeline": context["pipeline"],
        "var-run_type": context["run_type"],
        "var-provider": context["provider"],
        "var-run_id": context["run_id"],
        "from": context["from_range"],
        "to": context["to_range"],
    }
