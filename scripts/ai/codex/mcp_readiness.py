"""Effective-route MCP readiness with explicit untested and uncertain outcomes."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
import json
import math
import datetime
import time

from scripts.ai.codex.mcp_probe_client import ProbeError, client_for, probe_environment
from scripts.ai.codex.mcp_routes import changed_routes, route_snapshot
from scripts.ai.codex.native_mcp_config import ConfigCapture

SUPPORTED_PROTOCOLS = frozenset({"2024-11-05", "2025-03-26"})

READ_TOOLS_BY_SERVER = {
    "filesystem": frozenset(
        {"read_file", "read_text_file", "list_directory", "list_allowed_directories"}
    ),
    "ast-grep": frozenset({"find_code", "find_code_by_rule", "find_code_by_pattern"}),
    "code-analyzer": frozenset({"count_tokens", "count_code_tokens"}),
    "adr-analysis": frozenset({"list_roots"}),
    "github": frozenset({"get_me", "search_repositories", "get_file_contents"}),
    "context7": frozenset({"resolve-library-id", "query-docs", "get-library-docs"}),
    "ref": frozenset({"ref_search_documentation", "ref_read_url"}),
    "fetch": frozenset({"fetch"}),
    "memory": frozenset({"search_nodes", "open_nodes"}),
    "deja": frozenset({"recall", "recall_context", "blame", "how", "fix"}),
}
SERVICE_EFFECTS = [
    "network requests",
    "ordinary adapter/backend cache and logs",
    "launch of the selected approved adapter and its approved backend",
    "own diagnostic adapter shutdown; no shared-owner restart",
]


def _limit(entry: Mapping, key: str) -> float:
    value = entry.get(key)
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise ProbeError("ROUTE_LIMIT_NOT_RESOLVED")
    if not math.isfinite(value) or value <= 0:
        raise ProbeError("INVALID_ROUTE_LIMIT")
    return float(value)


def _control(value: object, server: str) -> dict:
    if not isinstance(value, dict):
        raise ProbeError("CONTROL_NOT_DECLARED")
    tool = value.get("tool")
    if tool not in READ_TOOLS_BY_SERVER.get(server, ()) or not isinstance(
        value.get("arguments"), dict
    ):
        raise ProbeError("READ_CONTROL_NOT_APPROVED")
    expected = value.get("contains_all")
    denial = value.get("expected_policy_reason")
    if denial == "WORKSPACE_POLICY_DENIED":
        return value
    if (
        not isinstance(expected, list)
        or not expected
        or not all(isinstance(x, str) and x.strip() for x in expected)
    ):
        raise ProbeError("CONTROL_EXPECTATION_MISSING")
    return value


def _initialize(client, timeout: float) -> None:
    result = client.request(
        "initialize",
        {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "bioetl-mcp-doctor", "version": "1"},
        },
        timeout,
    )
    version = result.get("protocolVersion")
    if version not in SUPPORTED_PROTOCOLS:
        try:
            datetime.date.fromisoformat(version)
        except (ValueError, TypeError):
            raise ProbeError("INITIALIZE_CONTRACT") from None
        raise ProbeError("PROTOCOL_VERSION_NOT_SUPPORTED")
    if not isinstance(result.get("capabilities"), dict):
        raise ProbeError("INITIALIZE_CONTRACT")
    info = result.get("serverInfo")
    if (
        not isinstance(info, dict)
        or not isinstance(info.get("name"), str)
        or not info["name"]
    ):
        raise ProbeError("INITIALIZE_IDENTITY_MISSING")
    client.notify_initialized()


def _listed_tools(result: Mapping) -> list[str]:
    tools = result.get("tools")
    if not isinstance(tools, list):
        raise ProbeError("CATALOG_INVALID")
    names = []
    for item in tools:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            raise ProbeError("CATALOG_INVALID")
        names.append(item["name"])
    return names


def _catalog(client, timeout: float) -> list[str]:
    cursor = None
    seen = set()
    names = []
    deadline = time.monotonic() + timeout
    for _ in range(64):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ProbeError("CATALOG_TIMEOUT", uncertain=True)
        result = client.request(
            "tools/list", {"cursor": cursor} if cursor else {}, remaining
        )
        tools = _listed_tools(result)
        names.extend(tools)
        if len(names) > 4096:
            raise ProbeError("CATALOG_LIMIT")
        cursor = result.get("nextCursor")
        if cursor is None:
            return names
        if not isinstance(cursor, str) or not cursor or cursor in seen:
            raise ProbeError("CATALOG_CURSOR_INVALID")
        seen.add(cursor)
    raise ProbeError("CATALOG_PAGE_LIMIT")


def _semantic_call(client, control: Mapping, timeout: float) -> None:
    result = client.request(
        "tools/call",
        {
            "name": control["tool"],
            "arguments": control["arguments"],
        },
        timeout,
    )
    if result.get("isError"):
        raise ProbeError("TOOL_REPORTED_ERROR")
    if control.get("expected_policy_reason"):
        raise ProbeError("EXPECTED_POLICY_DENIAL_NOT_OBSERVED")
    rendered = _render_tool_result(result)
    if not rendered.strip():
        raise ProbeError("EMPTY_TOOL_RESULT")
    if len(rendered.encode("utf-8")) > 1024 * 1024:
        raise ProbeError("RESPONSE_LIMIT", uncertain=True)
    if not all(token in rendered for token in control["contains_all"]):
        raise ProbeError("CONTROL_RESULT_MISMATCH")


def _render_tool_result(result: Mapping) -> str:
    content = result.get("content") or []
    if not isinstance(content, list):
        raise ProbeError("INVALID_TOOL_RESULT")
    rendered = "\n".join(
        block["text"]
        for block in content
        if isinstance(block, dict) and isinstance(block.get("text"), str)
    )
    structured = result.get("structuredContent")
    if isinstance(structured, dict) and structured:
        rendered += json.dumps(structured, ensure_ascii=False)
    return rendered


def _phase(row: dict, name: str, operation: Callable):
    started = time.monotonic()
    try:
        result = operation()
    except BaseException:
        row["phases"][name] = {
            "status": "FAIL",
            "elapsed_ms": round((time.monotonic() - started) * 1000),
        }
        raise
    row["phases"][name] = {
        "status": "PASS",
        "elapsed_ms": round((time.monotonic() - started) * 1000),
    }
    return result


def _run_session(
    row: dict, entry: Mapping, control: Mapping, workspace, environment, factory
):
    startup = _limit(entry, "startup_timeout_sec")
    tool_limit = _limit(entry, "tool_timeout_sec")
    row["limits"] = {
        "startup_and_initialize_sec": startup,
        "catalog_sec": tool_limit,
        "tool_call_sec": tool_limit,
        "source": "native effective MCP configuration",
    }
    began = time.monotonic()
    with factory(entry, workspace, environment) as client:
        row["phases"]["client_start"] = {
            "status": "PASS",
            "elapsed_ms": round((time.monotonic() - began) * 1000),
        }
        remaining = startup - (time.monotonic() - began)
        if remaining <= 0:
            raise ProbeError("STARTUP_OBSERVATION_TIMEOUT", uncertain=True)
        try:
            _phase(row, "initialize", lambda: _initialize(client, remaining))
        finally:
            row["phases"]["transport"] = {
                "status": "PASS" if client.transport_seen else "NOT_TESTED"
            }
        names = _phase(row, "catalog", lambda: _catalog(client, tool_limit))
        row["tool_count_raw"] = len(names)
        effective_names = _effective_tools(entry, names)
        row["tool_count"] = len(effective_names)
        row["native_tool_filters_applied"] = True
        row["memory_write_tools_advertised"] = bool(
            {
                "create_entities",
                "delete_entities",
                "add_observations",
                "delete_observations",
                "create_relations",
                "delete_relations",
            }
            & set(names)
        )
        if control["tool"] not in effective_names:
            raise ProbeError("CONTROL_TOOL_MISSING")
        _phase(row, "tool", lambda: _semantic_call(client, control, tool_limit))
        row["control_status"] = "PASS"
    row["detail"] = (
        "tool control passed; independent backend/access identity NOT_TESTED"
    )


def _effective_tools(entry: Mapping, names: Sequence[str]) -> list[str]:
    """Apply native allow/deny lists without changing the backend catalogue."""
    enabled = entry.get("enabled_tools")
    disabled = set(entry.get("disabled_tools") or [])
    return [
        name
        for name in names
        if (enabled is None or name in enabled) and name not in disabled
    ]


def _control_enabled(entry: Mapping, tool: str) -> bool:
    allowed = entry.get("enabled_tools")
    return tool not in (entry.get("disabled_tools") or []) and (
        allowed is None or tool in allowed
    )


def _probe_row(name, entry, control_value, capture, *, environment, factory, required):
    row = {
        "server": name,
        "required": required,
        "status": "NOT_TESTED",
        "ready": False,
        "uncertain_outcome": False,
        "phases": {},
        "backend_identity_status": "NOT_TESTED",
        "technical_write_prohibition_status": "NOT_TESTED",
        "control_status": "NOT_TESTED",
    }
    if entry is None:
        return {
            **row,
            "status": "FAIL",
            "detail": "expected route absent from native resolution",
        }
    if entry.get("enabled", True) is False:
        return {
            **row,
            "status": "DISABLED",
            "detail": "disabled by native effective configuration",
        }
    try:
        control = _control(control_value, name)
        if not _control_enabled(entry, control["tool"]):
            return {
                **row,
                "control_status": "DISABLED",
                "detail": "CONTROL_TOOL_DISABLED_BY_CONFIG",
            }
        _run_session(
            row,
            entry,
            control,
            capture.workspace,
            probe_environment(entry, environment),
            factory,
        )
    except ProbeError as exc:
        _apply_probe_failure(row, control_value, exc)
    except Exception:
        row["status"] = "FAIL"
        row["detail"] = "diagnostic failed; raw exception and payload omitted"
        row["uncertain_outcome"] = True
    return row


def _apply_probe_failure(row: dict, control_value, exc: ProbeError) -> None:
    expected = (
        isinstance(control_value, dict)
        and control_value.get("expected_policy_reason") == "WORKSPACE_POLICY_DENIED"
    )
    row["status"] = (
        "DENIED_AS_EXPECTED"
        if expected
        and exc.category == "WORKSPACE_POLICY_DENIED"
        and row["phases"].get("tool", {}).get("status") == "FAIL"
        else "FAIL"
    )
    if exc.category in {
        "CONTROL_NOT_DECLARED",
        "READ_CONTROL_NOT_APPROVED",
        "PROTOCOL_VERSION_NOT_SUPPORTED",
        "INSTALL_OR_UNREVIEWED_LAUNCHER_NOT_TESTED",
        "ADAPTER_PREFIX_NOT_TESTED",
        "EXISTING_ADAPTER_REQUIRED",
        "NONBLOCKING_STDIO_NOT_SUPPORTED",
        "WRAPPER_BACKEND_NO_INSTALL_NOT_VERIFIED",
        "ROUTE_LIMIT_NOT_RESOLVED",
        "AUTH_REFERENCE_UNAVAILABLE",
        "AUTH_HELPER_NOT_TESTED",
    }:
        row["status"] = "NOT_TESTED"
    if exc.category == "ADAPTER_DISABLED_BY_POLICY":
        row["status"] = "DISABLED"
    if "tool" in row["phases"]:
        row["control_status"] = row["status"]
        if row["status"] == "DENIED_AS_EXPECTED":
            row["phases"]["tool"]["status"] = "DENIED_AS_EXPECTED"
    row["detail"] = exc.category
    row["uncertain_outcome"] = exc.uncertain


def _aggregate_status(rows: Sequence[Mapping]) -> str:
    mandatory = [row for row in rows if row["required"]]
    for status in ("STALE", "FAIL", "DISABLED"):
        if any(row["status"] == status for row in mandatory):
            return status
    return "NOT_TESTED"


def readiness_report(
    capture: ConfigCapture,
    *,
    expected: Sequence[str],
    required: Sequence[str],
    profile: str,
    controls: Mapping,
    environment: Mapping[str, str],
    after: ConfigCapture | Callable[[], ConfigCapture] | None = None,
    factory=client_for,
) -> dict:
    report = route_snapshot(capture, expected=expected, project_profile=profile)
    entries = capture.payload["config"].get("mcp_servers", {})
    rows = [
        _probe_row(
            name,
            entries.get(name),
            controls.get(name),
            capture,
            environment=environment,
            factory=factory,
            required=name in required,
        )
        for name in sorted(set(expected) | set(entries))
    ]
    if callable(after):
        try:
            after = after()
        except Exception:
            after = None
            for row in rows:
                row["status"] = "STALE"
                row["detail"] = "final native configuration unavailable"
    changed = set(changed_routes(capture, after)) if after else set()
    for row in rows:
        if row["server"] in changed:
            row["status"] = "STALE"
            row["ready"] = False
            row["detail"] = "native selection inputs changed during observation"
    report.update(
        readiness_level="tool_and_identity",
        results=rows,
        ready=False,
        status=_aggregate_status(rows),
        service_effects=SERVICE_EFFECTS,
        ordinary_user_session="NOT_TESTED",
    )
    return report
