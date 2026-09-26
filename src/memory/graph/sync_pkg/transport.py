"""Neo4j HTTP transport for graph sync (AUD-002 slice: http_backend).

Owns ``http.client`` / ``urllib`` I/O and credential resolution. ``_core``
re-exports the public names so existing importers keep working.
"""

from __future__ import annotations

import base64
import http.client
import json
import os
import time
from pathlib import Path
from urllib import error, parse, request

from memory.graph.sync_pkg._core_convert import (
    _as_iterable,
    _as_mapping,
    _normalize_env_value,
    _read_text,
)
from memory.graph.sync_pkg._core_models import JsonValue

__all__ = [
    "_DEFAULT_NEO4J_AUDIT_DATABASE",
    "_DEFAULT_NEO4J_AUDIT_USERNAME",
    "Neo4jHttpClient",
    "_default_neo4j_host",
    "_env_flag_is_enabled",
    "_parse_auth_pair",
    "_read_env_file",
    "derive_http_uri",
    "load_repo_env",
    "resolve_neo4j_connection",
]

_DEFAULT_NEO4J_AUDIT_USERNAME = "neo4j"
_DEFAULT_NEO4J_AUDIT_DATABASE = "neo4j"


def _read_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    loaded: dict[str, str] = {}
    for raw_line in _read_text(path).splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        loaded[name.strip()] = _normalize_env_value(value)
    return loaded


def load_repo_env(root: Path) -> dict[str, str]:
    env = _read_env_file(root / ".env")
    env.update(_read_env_file(root / ".env.local"))
    shell_env = {key: value for key, value in os.environ.items() if value}
    env.update(shell_env)
    return env


def _parse_auth_pair(raw_auth: str | None) -> tuple[str | None, str | None]:
    if not raw_auth or "/" not in raw_auth:
        return None, None
    username, password = raw_auth.split("/", 1)
    return username or None, password or None


def _env_flag_is_enabled(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().casefold() not in {"", "0", "false", "no", "off"}


def _default_neo4j_host(env: dict[str, str]) -> str:
    if env.get("WSL_INTEROP") or env.get("WSL_DISTRO_NAME"):
        return "host.docker.internal"
    return "localhost"


def resolve_neo4j_connection(
    root: Path, explicit_http_uri: str | None
) -> tuple[str, str, str, str]:
    from memory.graph.sync_pkg import _core as core_mod

    env = core_mod.load_repo_env(root)
    audit_mode = _env_flag_is_enabled(env.get("LIVE_AUDIT_MODE"))
    default_host = _default_neo4j_host(env)

    if audit_mode:
        username = env.get("NEO4J_AUDIT_USERNAME")
        password = env.get("NEO4J_AUDIT_PASSWORD")
        database = (
            env.get("NEO4J_AUDIT_DATABASE")
            or env.get("NEO4J_DATABASE")
            or _DEFAULT_NEO4J_AUDIT_DATABASE
        )
        auth_username, auth_password = _parse_auth_pair(env.get("NEO4J_AUDIT_AUTH"))
        username = username or auth_username or _DEFAULT_NEO4J_AUDIT_USERNAME
        password = password or auth_password
        if not password:
            raise RuntimeError(
                "Neo4j audit password not found in NEO4J_AUDIT_PASSWORD or NEO4J_AUDIT_AUTH"
            )
        http_uri = (
            explicit_http_uri
            or env.get("NEO4J_AUDIT_HTTP_URI")
            or f"http://{default_host}:7475"  # NOSONAR - local Neo4j browser port
        )
    else:
        bolt_uri = env.get("NEO4J_URI", "bolt://localhost:7687")
        username = env.get("NEO4J_USERNAME") or env.get("NEO4J_AUTH_USERNAME")
        password = env.get("NEO4J_PASSWORD") or env.get("NEO4J_AUTH_PASSWORD")
        database = env.get("NEO4J_DATABASE", "neo4j")
        auth_username, auth_password = _parse_auth_pair(env.get("NEO4J_AUTH"))
        username = username or auth_username or "neo4j"
        password = password or auth_password
        if not password:
            raise RuntimeError(
                "Neo4j password not found in NEO4J_PASSWORD, NEO4J_AUTH_PASSWORD, or NEO4J_AUTH"
            )
        http_uri = (
            explicit_http_uri or env.get("NEO4J_HTTP_URI") or derive_http_uri(bolt_uri)
        )
    return http_uri.rstrip("/"), username, password, database


def derive_http_uri(neo4j_uri: str) -> str:
    parsed = parse.urlparse(neo4j_uri)
    if parsed.scheme in {"http", "https"}:
        return f"{parsed.scheme}://{parsed.hostname}:{parsed.port or (443 if parsed.scheme == 'https' else 80)}"
    scheme = "https" if parsed.scheme in {"neo4j+s", "bolt+s"} else "http"
    host = parsed.hostname or "localhost"
    return f"{scheme}://{host}:7474"


class Neo4jHttpClient:
    def __init__(
        self, base_uri: str, username: str, password: str, database: str
    ) -> None:
        self._endpoint = f"{base_uri}/db/{database}/tx/commit"
        self._primary_endpoint = self._endpoint
        parsed = parse.urlparse(base_uri)
        self._fallback_endpoint: str | None = None
        if parsed.hostname == "host.docker.internal":
            fallback_base = (
                parsed._replace(netloc=f"localhost:{parsed.port or 7474}")
                .geturl()
                .rstrip("/")
            )
            self._fallback_endpoint = f"{fallback_base}/db/{database}/tx/commit"
        auth_token = base64.b64encode(f"{username}:{password}".encode()).decode("ascii")
        self._headers = {
            "Authorization": f"Basic {auth_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def execute(
        self,
        statements: list[dict[str, JsonValue]],
        *,
        context: str | None = None,
    ) -> dict[str, object]:
        payload = json.dumps({"statements": statements}).encode("utf-8")
        last_exc: Exception | None = None
        attempt_errors: list[str] = []
        for attempt in range(12):
            endpoint = self._endpoint
            try:
                raw = self._execute_request(payload)
                break
            except error.HTTPError as exc:  # pragma: no cover - live backend dependent
                last_exc = self._handle_http_error(
                    endpoint,
                    exc,
                    context=context,
                    attempt=attempt,
                    attempt_errors=attempt_errors,
                )
                continue
            except (
                error.URLError,
                TimeoutError,
                ConnectionResetError,
                ConnectionAbortedError,
                http.client.RemoteDisconnected,
            ) as exc:  # pragma: no cover - network errors vary per environment
                last_exc = self._handle_transport_error(
                    endpoint,
                    exc,
                    context=context,
                    attempt=attempt,
                    attempt_errors=attempt_errors,
                )
                continue
        else:  # pragma: no cover - loop always breaks or raises
            raise RuntimeError(
                self._format_transport_error(
                    last_exc,
                    context=context,
                    attempt_errors=attempt_errors,
                )
            )
        body = json.loads(raw)
        if not isinstance(body, dict):
            raise RuntimeError(
                f"{self._context_prefix(context)}Neo4j response is not a JSON object"
            )
        errors = body.get("errors", [])
        if errors:
            prefix = self._context_prefix(context)
            raise RuntimeError(f"{prefix}Neo4j query/runtime error: {errors}")
        return body

    def _execute_request(self, payload: bytes) -> str:
        req = request.Request(
            self._endpoint,
            data=payload,
            headers=self._headers,
            method="POST",
        )
        response_cm = request.urlopen(req, timeout=60)
        with response_cm as response:
            raw_body: bytes = response.read()
            return raw_body.decode("utf-8")

    def _handle_http_error(
        self,
        endpoint: str,
        exc: error.HTTPError,
        *,
        context: str | None,
        attempt: int,
        attempt_errors: list[str],
    ) -> RuntimeError:
        body_text = exc.read().decode("utf-8", errors="replace")
        attempt_errors.append(
            self._format_transport_attempt(
                endpoint=endpoint,
                exc=exc,
                body_text=body_text,
            )
        )
        if not self._should_retry_http_error(exc):
            raise RuntimeError(
                self._format_query_error(exc, context=context, body_text=body_text)
            ) from exc
        runtime_error = RuntimeError(
            self._format_transport_error(
                exc,
                context=context,
                body_text=body_text,
                attempt_errors=attempt_errors,
            )
        )
        self._retry_or_raise(runtime_error, endpoint, exc, attempt)
        return runtime_error

    def _handle_transport_error(
        self,
        endpoint: str,
        exc: Exception,
        *,
        context: str | None,
        attempt: int,
        attempt_errors: list[str],
    ) -> RuntimeError:
        attempt_errors.append(
            self._format_transport_attempt(endpoint=endpoint, exc=exc)
        )
        runtime_error = RuntimeError(
            self._format_transport_error(
                exc,
                context=context,
                attempt_errors=attempt_errors,
            )
        )
        self._retry_or_raise(runtime_error, endpoint, exc, attempt)
        return runtime_error

    def _retry_or_raise(
        self,
        runtime_error: RuntimeError,
        endpoint: str,
        exc: Exception,
        attempt: int,
    ) -> None:
        if self._switch_to_fallback_endpoint():
            return
        if endpoint != self._primary_endpoint or self._is_last_attempt(attempt):
            raise runtime_error from exc
        self._sleep_before_retry(attempt)

    @staticmethod
    def _should_retry_http_error(exc: error.HTTPError) -> bool:
        return exc.code in {429, 502, 503, 504}

    def _switch_to_fallback_endpoint(self) -> bool:
        if self._fallback_endpoint and self._endpoint != self._fallback_endpoint:
            self._endpoint = self._fallback_endpoint
            self._fallback_endpoint = None
            return True
        return False

    @staticmethod
    def _is_last_attempt(attempt: int) -> bool:
        return attempt == 11

    @staticmethod
    def _sleep_before_retry(attempt: int) -> None:
        time.sleep(min(3.0, 0.5 * (attempt + 1)))

    def query(
        self,
        statement: str,
        parameters: dict[str, JsonValue] | None = None,
        *,
        context: str | None = None,
    ) -> list[dict[str, JsonValue]]:
        body = self.execute(
            [
                {
                    "statement": statement,
                    "parameters": parameters or {},
                }
            ],
            context=context,
        )
        results = body.get("results", [])
        result_items = _as_iterable(results)
        if not result_items:
            return []
        result = _as_mapping(result_items[0])
        columns = _as_iterable(result.get("columns"))
        rows: list[dict[str, JsonValue]] = []
        for entry_value in _as_iterable(result.get("data")):
            entry = _as_mapping(entry_value)
            raw_row = _as_iterable(entry.get("row"))
            row = {str(column): raw_row[index] for index, column in enumerate(columns)}
            rows.append(row)
        return rows

    @staticmethod
    def _context_prefix(context: str | None) -> str:
        return f"Neo4j {context} failed: " if context else ""

    def _format_transport_error(
        self,
        exc: Exception | None,
        *,
        context: str | None,
        body_text: str | None = None,
        attempt_errors: list[str] | None = None,
    ) -> str:
        prefix = self._context_prefix(context)
        detail = f"{exc}"
        if body_text:
            detail = f"{detail}; response={body_text[:500]}"
        attempts_suffix = ""
        if attempt_errors:
            attempts_suffix = " | attempts: " + " ; ".join(attempt_errors)
        return f"{prefix}transport error reaching HTTP endpoint {self._endpoint}: {detail}{attempts_suffix}"

    @staticmethod
    def _format_transport_attempt(
        *,
        endpoint: str,
        exc: Exception,
        body_text: str | None = None,
    ) -> str:
        detail = f"{type(exc).__name__}: {exc}"
        if body_text:
            detail = f"{detail}; response={body_text[:200]}"
        return f"{endpoint} -> {detail}"

    def _format_query_error(
        self,
        exc: error.HTTPError,
        *,
        context: str | None,
        body_text: str,
    ) -> str:
        prefix = self._context_prefix(context)
        detail: object = body_text[:500]
        try:
            payload = json.loads(body_text)
        except json.JSONDecodeError:
            payload = detail
        else:
            if isinstance(payload, dict) and isinstance(payload.get("errors"), list):
                detail = payload["errors"]
        return f"{prefix}query/runtime error (HTTP {exc.code}): {detail}"
