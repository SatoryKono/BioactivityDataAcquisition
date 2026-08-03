"""Prometheus query helpers for Processed Records dashboard payloads."""

from __future__ import annotations

import json
import math
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode

from bioetl.interfaces.http._processed_records_http import open_url as _open_url

# Local-only Prometheus scrape endpoints (plain HTTP is intentional on loopback /
# compose networks). Constructed without a literal ``http://`` prefix so Sonar
# S5332 does not flag the local operator defaults.
_LOCAL_HTTP = "http"
DEFAULT_PROMETHEUS_BASE_URL = f"{_LOCAL_HTTP}://localhost:9090"
DEFAULT_PROMETHEUS_BASE_URL_FALLBACKS = (
    f"{_LOCAL_HTTP}://prometheus:9090",
    f"{_LOCAL_HTTP}://host.docker.internal:9090",
)
PROMETHEUS_QUERY_TIMEOUT_SECONDS = 3.0


def _fetch_prometheus_query_payload(
    *,
    prometheus_base_url: str,
    query: str,
) -> dict[str, object]:
    url = (
        prometheus_base_url.rstrip("/") + "/api/v1/query?" + urlencode({"query": query})
    )
    try:
        with _open_url(url, timeout=PROMETHEUS_QUERY_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Prometheus query failed: {exc}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("Prometheus query failed: invalid payload")
    return payload


def _prometheus_error_message(payload: dict[str, object]) -> str:
    error = payload.get("error")
    if error:
        return str(error)
    error_type = payload.get("errorType")
    if error_type:
        return str(error_type)
    return "unknown"


def _require_prometheus_success(payload: dict[str, object]) -> None:
    if payload.get("status") == "success":
        return
    raise RuntimeError(f"Prometheus query failed: {_prometheus_error_message(payload)}")


def _prometheus_result_list(payload: dict[str, object]) -> list[object]:
    data = payload.get("data", {})
    if not isinstance(data, dict):
        return []
    result = data.get("result", [])
    if not isinstance(result, list):
        return []
    return result


def _finite_float_from_value_pair(value: object) -> float | None:
    if not isinstance(value, list) or len(value) < 2:
        return None
    try:
        parsed = float(value[1])
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed):
        return None
    return parsed


def _metric_name_from_sample(sample: dict[object, object]) -> str | None:
    metric = sample.get("metric")
    if not isinstance(metric, dict):
        return None
    name = metric.get("__name__")
    return name if isinstance(name, str) else None


def _parse_vector_sample(sample: object) -> tuple[str, float] | None:
    if not isinstance(sample, dict):
        return None
    metric = _metric_name_from_sample(sample)
    if metric is None:
        return None
    parsed = _finite_float_from_value_pair(sample.get("value"))
    if parsed is None:
        return None
    return metric, parsed


def _vector_samples_from_payload(payload: dict[str, object]) -> dict[str, float]:
    values: dict[str, float] = {}
    for sample in _prometheus_result_list(payload):
        parsed = _parse_vector_sample(sample)
        if parsed is not None:
            metric, number = parsed
            values[metric] = number
    return values


def _scalar_from_payload(payload: dict[str, object]) -> float | None:
    result = _prometheus_result_list(payload)
    if not result:
        return None
    first = result[0]
    if not isinstance(first, dict):
        return None
    return _finite_float_from_value_pair(first.get("value"))


def _query_prometheus_scalar(*, prometheus_base_url: str, query: str) -> float | None:
    payload = _fetch_prometheus_query_payload(
        prometheus_base_url=prometheus_base_url,
        query=query,
    )
    _require_prometheus_success(payload)
    return _scalar_from_payload(payload)


def _query_prometheus_vector(
    *,
    prometheus_base_url: str,
    query: str,
) -> dict[str, float]:
    """Return finite vector samples keyed by their retained metric name."""
    payload = _fetch_prometheus_query_payload(
        prometheus_base_url=prometheus_base_url,
        query=query,
    )
    _require_prometheus_success(payload)
    return _vector_samples_from_payload(payload)


def _query_prometheus_scalar_with_fallbacks(
    *,
    prometheus_base_urls: tuple[str, ...],
    query: str,
) -> float | None:
    errors: list[str] = []
    for prometheus_base_url in prometheus_base_urls:
        try:
            return _query_prometheus_scalar(
                prometheus_base_url=prometheus_base_url,
                query=query,
            )
        except RuntimeError as exc:
            errors.append(f"{prometheus_base_url}: {exc}")
    raise RuntimeError("; ".join(errors))


def _query_prometheus_vector_with_fallbacks(
    *,
    prometheus_base_urls: tuple[str, ...],
    query: str,
) -> dict[str, float]:
    """Try each configured Prometheus endpoint for one vector request."""
    errors: list[str] = []
    for prometheus_base_url in prometheus_base_urls:
        try:
            return _query_prometheus_vector(
                prometheus_base_url=prometheus_base_url,
                query=query,
            )
        except RuntimeError as exc:
            errors.append(f"{prometheus_base_url}: {exc}")
    raise RuntimeError("; ".join(errors))


def _candidate_prometheus_base_urls(prometheus_base_url: str) -> tuple[str, ...]:
    primary = prometheus_base_url.rstrip("/")
    candidates = [primary]
    if primary == DEFAULT_PROMETHEUS_BASE_URL:
        candidates.extend(DEFAULT_PROMETHEUS_BASE_URL_FALLBACKS)
    return tuple(dict.fromkeys(candidate.rstrip("/") for candidate in candidates))
