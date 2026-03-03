"""Legacy source configuration normalization utilities.

Transforms old source config variants into the canonical ``source`` schema
before pydantic validation.
"""

from __future__ import annotations

from typing import Any

from bioetl.infrastructure.config_merge import config_merge

_ENDPOINT_KEYS: tuple[str, ...] = ("base_url", "api_version")
_AUTH_KEYS: tuple[str, ...] = ("auth_type", "api_key")
_BATCH_KEYS: tuple[str, ...] = ("batch_size", "page_size", "max_url_length")


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Deep merge two dictionaries with override precedence."""
    return config_merge(base, override)


def _sync_timeout_aliases(d: dict[str, Any]) -> dict[str, Any]:
    """Ensure ``timeout`` and ``timeout_sec`` are kept in sync."""
    result = d.copy()
    if "timeout" in result and "timeout_sec" not in result:
        result["timeout_sec"] = result["timeout"]
    elif "timeout_sec" in result and "timeout" not in result:
        result["timeout"] = result["timeout_sec"]
    return result


def _normalize_rate_limit(source: dict[str, Any]) -> None:
    """Reconcile ``with_api_key`` ↔ ``authenticated`` aliases in-place."""
    rate_limit = source.get("rate_limit")
    if not isinstance(rate_limit, dict):
        return
    rl = rate_limit.copy()
    if isinstance(rl.get("with_api_key"), dict) and "authenticated" not in rl:
        rl["authenticated"] = rl["with_api_key"]
    if isinstance(rl.get("authenticated"), dict) and "with_api_key" not in rl:
        rl["with_api_key"] = rl["authenticated"]
    source["rate_limit"] = rl


def _normalize_health_check(source: dict[str, Any]) -> None:
    """Reconcile ``timeout`` ↔ ``timeout_sec`` in health_check in-place."""
    hc = source.get("health_check")
    if isinstance(hc, dict):
        source["health_check"] = _sync_timeout_aliases(hc)


def _get_dict_or_empty(container: dict[str, Any], key: str) -> dict[str, Any]:
    """Return *container[key]* if it is a dict, otherwise an empty dict."""
    val = container.get(key)
    return val if isinstance(val, dict) else {}


def _copy_keys(src: dict[str, Any], dst: dict[str, Any], keys: tuple[str, ...]) -> None:
    """Copy *keys* from *src* to *dst* via ``setdefault``."""
    for key in keys:
        if key in src:
            dst.setdefault(key, src[key])


def _normalize_source_rate_limits(source: dict[str, Any]) -> None:
    """Normalize rate limiting aliases and health check timeouts."""
    _normalize_rate_limit(source)
    _normalize_health_check(source)


def _normalize_source_endpoints(
    source: dict[str, Any],
    provider_config: dict[str, Any],
    api: dict[str, Any],
) -> None:
    """Normalize endpoint/URL and client configuration."""
    _copy_keys(api, provider_config, _ENDPOINT_KEYS)

    if isinstance(provider_config.get("client"), dict):
        client_norm = _get_dict_or_empty(source, "client")
        legacy_client = _sync_timeout_aliases(provider_config["client"])
        source["client"] = _deep_merge(legacy_client, client_norm)

    client = source.pop("client", None)
    if isinstance(client, dict):
        existing = _get_dict_or_empty(provider_config, "client")
        existing = _sync_timeout_aliases(existing) if existing else {}
        provider_config["client"] = _deep_merge(existing, _sync_timeout_aliases(client))


def _normalize_source_auth(
    provider_config: dict[str, Any],
    api: dict[str, Any],
) -> None:
    """Normalize authentication configuration."""
    _copy_keys(api, provider_config, _AUTH_KEYS)


def _normalize_source_pagination(
    source: dict[str, Any],
    provider_config: dict[str, Any],
) -> None:
    """Normalize pagination and batch configuration."""
    pagination: dict[str, Any] = _get_dict_or_empty(provider_config, "pagination")

    if provider_config.get("batch_size") is not None:
        pagination.setdefault("id_batch_size", provider_config["batch_size"])
    if provider_config.get("page_size") is not None:
        pagination.setdefault("page_size", provider_config["page_size"])
    if provider_config.get("max_url_length") is not None:
        pagination.setdefault("max_url_length", provider_config["max_url_length"])
    if provider_config.get("cursor_pagination"):
        pagination.setdefault("strategy", "cursor")

    batch_norm = _get_dict_or_empty(source, "batch")
    _copy_keys(provider_config, batch_norm, _BATCH_KEYS)
    if "batch_size" in provider_config:
        batch_norm.setdefault("size", provider_config["batch_size"])
    if batch_norm:
        source["batch"] = batch_norm

    batch = source.pop("batch", None)
    if isinstance(batch, dict):
        if "batch_size" in batch:
            provider_config.setdefault("batch_size", batch["batch_size"])
            pagination.setdefault("id_batch_size", batch["batch_size"])
        elif "size" in batch:
            provider_config.setdefault("batch_size", batch["size"])
            pagination.setdefault("id_batch_size", batch["size"])
        elif "api_batch_size" in batch:
            provider_config.setdefault("batch_size", batch["api_batch_size"])
            pagination.setdefault("id_batch_size", batch["api_batch_size"])
        if "page_size" in batch:
            _copy_keys(batch, provider_config, ("page_size", "max_url_length"))
            pagination.setdefault("page_size", batch["page_size"])
        if "max_url_length" in batch:
            pagination.setdefault("max_url_length", batch["max_url_length"])
    elif isinstance(batch, int):
        provider_config.setdefault("batch_size", batch)
        pagination.setdefault("id_batch_size", batch)

    if pagination:
        provider_config["pagination"] = pagination


def _promote_top_level_source_sections(raw: dict[str, Any]) -> dict[str, Any]:
    """Promote top-level source sections into ``source`` when missing."""
    if "source" in raw and isinstance(raw.get("source"), dict):
        return raw

    if not isinstance(raw.get("api"), dict):
        return raw

    source: dict[str, Any] = {
        "type": "api",
        "load_strategy": "full",
        "api": raw["api"],
    }
    for key in ("client", "batch", "rate_limit", "circuit_breaker", "health_check"):
        value = raw.get(key)
        if value is not None:
            source[key] = value

    promoted = raw.copy()
    promoted["source"] = source
    return promoted


def normalize_source_config(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize source config across legacy/new schemas before validation."""
    config = _promote_top_level_source_sections(raw).copy()
    source = config.get("source")
    if not isinstance(source, dict):
        return config

    source_norm = source.copy()

    provider_config = source_norm.get("provider_config")
    if not isinstance(provider_config, dict):
        provider_config = {}

    api_norm = _get_dict_or_empty(source_norm, "api")
    if provider_config:
        _copy_keys(provider_config, api_norm, (*_ENDPOINT_KEYS, *_AUTH_KEYS))
    if api_norm:
        source_norm["api"] = api_norm
    api = source_norm.pop("api", None)
    if not isinstance(api, dict):
        api = {}

    _normalize_source_rate_limits(source_norm)
    _normalize_source_endpoints(source_norm, provider_config, api)
    _normalize_source_auth(provider_config, api)
    _normalize_source_pagination(source_norm, provider_config)

    if provider_config:
        source_norm["provider_config"] = provider_config

    config["source"] = source_norm
    return config
