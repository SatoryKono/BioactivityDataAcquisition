"""Diff helpers for persisted pipeline run reports and repository env documents."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

MappingLike = dict[str, Any] | Any  # Any: decoded external JSON payload
ReportPayload = dict[str, Any]  # Any: decoded report JSON payload


def _as_mapping(value: MappingLike) -> ReportPayload:
    if isinstance(value, dict):
        return value
    raise TypeError("report payload must be a mapping")


def _int(value: object) -> int:
    if value is None:
        return 0
    if not isinstance(value, (str, bytes, bytearray, int, float)):
        return 0
    try:
        return int(value)
    except (TypeError, ValueError, OverflowError):
        return 0


def diff_pipeline_reports(left: MappingLike, right: MappingLike) -> ReportPayload:
    """Compute funnel and reason deltas between two pipeline report payloads."""
    left_payload = _as_mapping(left)
    right_payload = _as_mapping(right)
    return {
        "left_run_id": (left_payload.get("identity") or {}).get("run_id"),
        "right_run_id": (right_payload.get("identity") or {}).get("run_id"),
        "funnel_delta": _funnel_delta(left_payload, right_payload),
        "reasons_delta": _reasons_delta(left_payload, right_payload),
    }


def _funnel_rows(payload: ReportPayload) -> dict[str, ReportPayload]:
    return {
        str(row.get("stage_id")): row
        for row in payload.get("funnel") or []
        if isinstance(row, dict)
    }


def _funnel_delta(
    left: dict[str, Any],  # Any: decoded report payload
    right: dict[str, Any],  # Any: decoded report payload
) -> list[dict[str, Any]]:  # Any: dynamic funnel delta rows
    left_rows = _funnel_rows(left)
    right_rows = _funnel_rows(right)
    stages = sorted(set(left_rows) | set(right_rows))
    return [
        _stage_delta(stage, left_rows.get(stage, {}), right_rows.get(stage, {}))
        for stage in stages
    ]


def _stage_delta(
    stage: str,
    left: dict[str, Any],  # Any: dynamic funnel row
    right: dict[str, Any],  # Any: dynamic funnel row
) -> dict[str, Any]:  # Any: dynamic stage delta payload
    return {
        "stage_id": stage,
        "records_in_delta": _int(right.get("records_in"))
        - _int(left.get("records_in")),
        "records_out_delta": _int(right.get("records_out"))
        - _int(left.get("records_out")),
        "removed_total_delta": _int(right.get("removed_total"))
        - _int(left.get("removed_total")),
    }


def _reason_counts(payload: ReportPayload) -> dict[str, int]:
    items = payload.get("reasons_top_n") or []
    return {
        str(i.get("reason_code")): _int(i.get("count"))
        for i in items
        if isinstance(i, dict)
    }


def _reasons_delta(
    left: dict[str, Any],  # Any: decoded report payload
    right: dict[str, Any],  # Any: decoded report payload
) -> list[dict[str, Any]]:  # Any: dynamic reason delta rows
    left_counts = _reason_counts(left)
    right_counts = _reason_counts(right)
    return [
        {
            "reason_code": code,
            "count_delta": right_counts.get(code, 0) - left_counts.get(code, 0),
        }
        for code in sorted(set(left_counts) | set(right_counts))
    ]


def repository_env_candidate_paths(
    root: str | Path,
    process_environment: Mapping[str, object] | None = None,
) -> tuple[Path, ...]:
    """Return repository env candidates without reading them."""
    return _repository_env_paths(Path(root), process_environment or {})


def _repository_env_paths(
    root_path: Path, process: Mapping[str, object]
) -> tuple[Path, ...]:
    configured_env = str(process.get("BIOETL_ENV_FILE") or "").strip()
    if configured_env:
        env_path = Path(configured_env)
        if not env_path.is_absolute():
            env_path = root_path / env_path
    else:
        env_path = root_path / ".env"
    if str(process.get("BIOETL_SKIP_ENV_LOCAL") or "0").strip() == "1":
        return (env_path,)
    return env_path, root_path / ".env.local"


def _parse_repository_env_document(
    text: str | None, allowed: set[str]
) -> dict[str, str]:
    if not text:
        return {}
    values: dict[str, str] = {}
    for raw in text.splitlines():
        parsed = _parse_repository_env_line(raw, allowed)
        if parsed is not None:
            key, value = parsed
            values[key] = value
    return values


def _strip_repository_env_inline_comment(value: str) -> str:
    """Strip a shell-style inline comment outside quoted env text."""
    quote: str | None = None
    escaped = False
    for index, character in enumerate(value):
        if escaped:
            escaped = False
            continue
        if character == "\\" and quote is not None:
            escaped = True
            continue
        if character in {"'", '"'}:
            if quote is None:
                quote = character
            elif quote == character:
                quote = None
            continue
        if _is_repository_env_comment_start(value, index, character, quote):
            return value[:index].rstrip()
    return value.rstrip()


def _is_repository_env_comment_start(
    value: str, index: int, character: str, quote: str | None
) -> bool:
    return (
        character == "#" and quote is None and index > 0 and value[index - 1].isspace()
    )


def _parse_repository_env_line(raw: str, allowed: set[str]) -> tuple[str, str] | None:
    stripped = raw.strip()
    if not stripped or stripped.startswith("#") or "=" not in raw:
        return None
    key, value = raw.split("=", 1)
    key = key.strip()
    value = _strip_repository_env_inline_comment(value.strip())
    if key not in allowed:
        return None
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return key, value[1:-1]
    return key, value
