#!/usr/bin/env python3
"""Canonical Grafana context URLs for the seven ADR-053 dashboard UIDs.

Production twin of the navigation-links contract. Builds `/d/` handoffs that:

- trim `run_id` and reject internal whitespace
- always pass `var-run_id` so a destination cannot keep a foreign UUID
- preserve `${__url_time_range}` (or `from=`/`to=`)
- emit a stable query order: workflow, pipeline, run_type, run_id, extras, time
"""

from __future__ import annotations

from dataclasses import dataclass, field
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
RUN_ID_TEMPLATE = "$run_id"
HTML_AMPERSAND = "&amp;"
# Grafana query-variable regex: capture trimmed non-empty token.
RUN_ID_GRAFANA_REGEX = r"/^\s*(\S(?:.*\S)?)\s*$/"
_RUN_ID_TEMPLATE_VALUES = frozenset(
    {
        RUN_ID_TEMPLATE,
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


def _pipeline_value(
    *, source_uid: str, template: bool, context: DashboardContext | None
) -> str:
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
        run_id = RUN_ID_TEMPLATE
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


@dataclass(slots=True)
class _HandoffQuery:
    """Mutable query normalization state kept out of the public API."""

    has_time_token: bool
    has_from: bool = False
    has_to: bool = False
    extras: list[tuple[str, str]] = field(default_factory=list)
    var_values: dict[str, str] = field(default_factory=dict)

    def add(self, key: str, value: str) -> None:
        if key == TIME_TOKEN or key.startswith("${__url_time_range"):
            self.has_time_token = True
            return
        if key == "from":
            self.has_from = True
            self.extras.append((key, value))
            return
        if key == "to":
            self.has_to = True
            self.extras.append((key, value))
            return
        if not key.startswith("var-"):
            self.extras.append((key, value))
            return
        name = key[4:]
        self.var_values[name] = _normalize_query_variable(name, value)

    def ensure_run_id(self) -> None:
        is_panel_link = any(key == "viewPanel" for key, _ in self.extras)
        if "run_id" not in self.var_values and not is_panel_link:
            self.var_values["run_id"] = RUN_ID_TEMPLATE

    def ordered_pairs(self) -> list[tuple[str, str]]:
        ordered: list[tuple[str, str]] = []
        for name in CORE_VAR_ORDER:
            if name in self.var_values:
                ordered.append((f"var-{name}", self.var_values.pop(name)))
        ordered.extend(
            (f"var-{name}", value) for name, value in self.var_values.items()
        )
        ordered.extend(self.extras)
        return ordered

    def append_time_token(self, query: str) -> str:
        if not self.has_time_token and self.has_from and self.has_to:
            return query
        return f"{query}&{TIME_TOKEN}" if query else TIME_TOKEN


def _normalize_query_variable(name: str, value: str) -> str:
    if name != "run_id" or value in _RUN_ID_TEMPLATE_VALUES:
        return value
    try:
        return normalize_run_id(value)
    except RunIdError:
        return str(value).strip()


def rewrite_dashboard_handoff_url(url: str) -> str:
    """Normalize a shipped `/d/` URL: require run_id + time, stable var order.

    Template values (`$run_id`, `${__value.raw}`, …) are preserved. Concrete
    `run_id` query values are trimmed. Missing `var-run_id` is filled with
    `$run_id` so Grafana cannot silently keep a foreign UUID.
    """
    raw = url.replace(HTML_AMPERSAND, "&")
    if not raw.startswith("/d/"):
        return url
    split = urlsplit(raw)
    path = split.path
    query_pairs = parse_qsl(split.query, keep_blank_values=True)
    state = _HandoffQuery(has_time_token=TIME_TOKEN in raw)
    for key, value in query_pairs:
        state.add(key, value)
    # Full-dashboard handoffs must carry run_id so Grafana cannot keep a foreign
    # UUID. Same-dashboard viewPanel deep-links keep authored vars (CURRENT
    # fleet CTAs must not leak run_id).
    state.ensure_run_id()
    query = urlencode(state.ordered_pairs(), safe="${}:._-")
    query = state.append_time_token(query)
    rewritten = urlunsplit((split.scheme, split.netloc, path, query, split.fragment))
    if HTML_AMPERSAND in url:
        rewritten = rewritten.replace("&", HTML_AMPERSAND)
    return rewritten


def preserves_time_window(url: str) -> bool:
    """Return whether a `/d/` URL carries Grafana time-range handoff."""
    decoded = url.replace(HTML_AMPERSAND, "&")
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
