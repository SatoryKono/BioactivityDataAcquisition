"""Restore checkpoint observations from checksum-verified local evidence."""

from __future__ import annotations

import math
from datetime import datetime
from pathlib import Path

from bioetl.domain.ports import MetricsPort
from bioetl.domain.types import JsonDict
from bioetl.infrastructure.checkpoint._local_checkpoint_integrity import (
    compute_checkpoint_payload_sha256,
)
from bioetl.infrastructure.checkpoint._local_checkpoint_io import (
    latest_history_checkpoint_path,
    read_json_file,
)


def _newest_verified_payload(base_path: Path, pipeline: str) -> JsonDict | None:
    """Return the newest checksum-verified payload for a pipeline, if any."""
    candidates = [base_path / f"{pipeline}.json"]
    historical = latest_history_checkpoint_path(base_path, pipeline)
    if historical is not None:
        candidates.append(historical)
    existing = [path for path in candidates if path.is_file()]
    if not existing:
        return None
    newest = max(existing, key=lambda p: (p.stat().st_mtime_ns, p.name))
    payload = read_json_file(newest)
    metadata = payload.get("metadata")
    if (
        payload.get("pipeline") == pipeline
        and isinstance(metadata, dict)
        and payload.get("payload_sha256") == compute_checkpoint_payload_sha256(payload)
    ):
        return payload
    return None


def _restored_pipeline_value(base_path: Path, pipeline: str, *, now: datetime) -> float:
    """Return the verified saved timestamp for a pipeline, or zero."""
    payload = _newest_verified_payload(base_path, pipeline)
    if payload is None:
        return 0.0
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        return 0.0
    raw = metadata.get("checkpoint_saved_at_epoch_seconds")
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        return 0.0
    timestamp = float(raw)
    if math.isfinite(timestamp) and 0 < timestamp <= now.timestamp():
        return timestamp
    return 0.0


def rehydrate_checkpoint_metrics(
    metrics: MetricsPort, base_path: Path, *, now: datetime
) -> int:
    """Restore original save times, including history after resume-pointer cleanup.

    Invalid newest evidence is never replaced with an older successful sample.
    Zero invalidates a previously restored observation without fabricating a time.
    """
    history = base_path / ".history" / "by_pipeline"
    pipelines = {p.stem for p in base_path.glob("*.json")}
    if history.is_dir():
        pipelines.update(p.name for p in history.iterdir() if p.is_dir())
    restored = 0
    for pipeline in sorted(pipelines):
        try:
            value = _restored_pipeline_value(base_path, pipeline, now=now)
        except (OSError, ValueError, TypeError, KeyError):
            value = 0.0
        metrics.set_gauge(
            "bioetl_checkpoint_saved_at_seconds", value, {"pipeline": pipeline}
        )
        restored += int(value > 0)
    return restored
