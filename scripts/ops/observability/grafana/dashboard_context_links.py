#!/usr/bin/env python3
"""Canonical Grafana context URLs for the seven ADR-053 dashboard UIDs.

Production twin of the navigation-links contract. Builds `/d/` handoffs that:

- trim `run_id` and reject internal whitespace
- always pass `var-run_id` so a destination cannot keep a foreign UUID
- preserve `${__url_time_range}` (or `from=`/`to=`)
- emit a stable query order: workflow, pipeline, run_type, run_id, extras, time
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import parse_qsl, unquote, urlencode, urlsplit, urlunsplit

SEVEN_UIDS: tuple[str, ...] = (
    "bioetl-control-plane-v1",
    "bioetl-overview-v2",
    "bioetl-runtime",
    "bioetl-provider-health-v2",
    "bioetl-dq-v2",
    "bioetl-incident-v1",
    "bioetl-run-explorer-v1",
)

PATH_BY_UID: dict[str, str] = {uid: uid for uid in SEVEN_UIDS}

CORE_VAR_ORDER: tuple[str, ...] = ("workflow", "pipeline", "run_type", "run_id")
TIME_TOKEN = "${__url_time_range}"
# Grafana query-variable regex: capture trimmed non-empty token.
RUN_ID_GRAFANA_REGEX = r"/^\s*(\S(?:.*\S)?)\s*$/"
_RUN_ID_TEMPLATE_VALUES = frozenset(
    {
        "$run_id",
        "${run_id}",
        "${__value.raw}",
        "${__data.fields.run_id}",
        "${__data.fields.Run ID}",
    }
)


class RunIdError(ValueError):
    """Raised when a concrete run_id is missing, blank, or internally spaced."""


def normalize_run_id(value: object) -> str:
    """Trim leading/trailing whitespace; reject empty or internally spaced ids."""
    if value is None:
        raise RunIdError("run_id is required")
    trimmed = unquote(str(value)).replace("\u00a0", " ").strip()
    if not trimmed:
        raise RunIdError("run_id is empty after trim")
    if any(char.isspace() for char in trimmed):
        raise RunIdError("run_id contains internal whitespace")
    return trimmed


@dataclass(frozen=True, slots=True)
class DashboardContext:
    """One operator selection applied to all seven UIDs."""

    workflow: str
    pipeline: str
    run_type: str
    run_id: str
    provider: str = "unknown"
    pipeline_context: str | None = None
    stage: str = "$__all"

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", normalize_run_id(self.run_id))


def _pipeline_value(*, source_uid: str, template: bool, context: DashboardContext | None) -> str:
    if template:
        if source_uid == "bioetl-provider-health-v2":
            return "$pipeline_context"
        return "$pipeline"
    assert context is not None
    if source_uid == "bioetl-provider-health-v2":
        return context.pipeline_context or context.pipeline
    return context.pipeline


def build_handoff_url(
    target_uid: str,
    *,
    source_uid: str = "bioetl-overview-v2",
    context: DashboardContext | None = None,
    template: bool = True,
    extras: dict[str, str] | None = None,
) -> str:
    """Return a `/d/{uid}/{path}` URL with canonical var order and time range."""
    if target_uid not in PATH_BY_UID:
        raise ValueError(f"unknown dashboard uid: {target_uid}")
    if not template and context is None:
        raise ValueError("concrete context is required when template=False")
    pipe = _pipeline_value(source_uid=source_uid, template=template, context=context)
    if template:
        workflow = "$workflow"
        run_type = "$run_type"
        run_id = "$run_id"
        provider = (
            "$provider"
            if source_uid in {"bioetl-provider-health-v2", "bioetl-incident-v1"}
            else "unknown"
        )
        stage = "$__all"
        pipeline_context = pipe
    else:
        assert context is not None
        workflow = context.workflow
        run_type = context.run_type
        run_id = context.run_id
        provider = context.provider
        stage = context.stage
        pipeline_context = context.pipeline_context or context.pipeline
    values: dict[str, str] = {
        "workflow": workflow,
        "pipeline": pipe,
        "run_type": run_type,
        "run_id": run_id,
    }
    extra_values: dict[str, str] = dict(extras or {})
    if target_uid in {"bioetl-runtime", "bioetl-dq-v2"}:
        extra_values.setdefault("stage", stage)
    if target_uid == "bioetl-provider-health-v2":
        extra_values.setdefault("provider", provider)
        extra_values.setdefault("pipeline_context", pipeline_context)
    return _assemble_url(target_uid, values=values, extras=extra_values)


def urls_for_context(context: DashboardContext) -> dict[str, str]:
    """Build the seven UID URLs from one trimmed context object."""
    return {
        uid: build_handoff_url(uid, context=context, template=False)
        for uid in SEVEN_UIDS
    }


def _assemble_url(
    target_uid: str,
    *,
    values: dict[str, str],
    extras: dict[str, str],
) -> str:
    parts: list[str] = []
    for name in CORE_VAR_ORDER:
        parts.append(f"var-{name}={values[name]}")
    for name, value in extras.items():
        if name in CORE_VAR_ORDER:
            continue
        parts.append(f"var-{name}={value}")
    parts.append(TIME_TOKEN)
    query = "&".join(parts)
    return f"/d/{target_uid}/{PATH_BY_UID[target_uid]}?{query}"


def rewrite_dashboard_handoff_url(url: str) -> str:
    """Normalize a shipped `/d/` URL: require run_id + time, stable var order.

    Template values (`$run_id`, `${__value.raw}`, …) are preserved. Concrete
    `run_id` query values are trimmed. Missing `var-run_id` is filled with
    `$run_id` so Grafana cannot silently keep a foreign UUID.
    """
    raw = url.replace("&amp;", "&")
    if not raw.startswith("/d/"):
        return url
    split = urlsplit(raw)
    path = split.path
    query_pairs = parse_qsl(split.query, keep_blank_values=True)
    extras: list[tuple[str, str]] = []
    var_values: dict[str, str] = {}
    has_time_token = TIME_TOKEN in raw
    has_from = False
    has_to = False
    for key, value in query_pairs:
        if key == TIME_TOKEN or key.startswith("${__url_time_range"):
            has_time_token = True
            continue
        if key == "from":
            has_from = True
            extras.append((key, value))
            continue
        if key == "to":
            has_to = True
            extras.append((key, value))
            continue
        if key.startswith("var-"):
            name = key[4:]
            if name == "run_id" and value not in _RUN_ID_TEMPLATE_VALUES:
                try:
                    value = normalize_run_id(value)
                except RunIdError:
                    value = str(value).strip()
            var_values[name] = value
            continue
        extras.append((key, value))
    # Full-dashboard handoffs must carry run_id so Grafana cannot keep a foreign
    # UUID. Same-dashboard viewPanel deep-links keep authored vars (CURRENT
    # fleet CTAs must not leak run_id).
    if "run_id" not in var_values and "viewPanel" not in {key for key, _ in extras}:
        var_values["run_id"] = "$run_id"
    ordered: list[tuple[str, str]] = []
    for name in CORE_VAR_ORDER:
        if name in var_values:
            ordered.append((f"var-{name}", var_values.pop(name)))
    for name, value in var_values.items():
        ordered.append((f"var-{name}", value))
    ordered.extend(extras)
    query = urlencode(ordered, safe="${}:._-")
    needs_time_token = has_time_token or not (has_from and has_to)
    if needs_time_token:
        query = f"{query}&{TIME_TOKEN}" if query else TIME_TOKEN
    rewritten = urlunsplit((split.scheme, split.netloc, path, query, split.fragment))
    if "&amp;" in url:
        rewritten = rewritten.replace("&", "&amp;")
    return rewritten


def preserves_time_window(url: str) -> bool:
    """Return whether a `/d/` URL carries Grafana time-range handoff."""
    decoded = url.replace("&amp;", "&")
    return TIME_TOKEN in decoded or ("from=" in decoded and "to=" in decoded)


__all__ = [
    "CORE_VAR_ORDER",
    "PATH_BY_UID",
    "RUN_ID_GRAFANA_REGEX",
    "SEVEN_UIDS",
    "TIME_TOKEN",
    "DashboardContext",
    "RunIdError",
    "build_handoff_url",
    "normalize_run_id",
    "preserves_time_window",
    "rewrite_dashboard_handoff_url",
    "urls_for_context",
]
