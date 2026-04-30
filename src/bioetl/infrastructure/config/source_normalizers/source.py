"""Source configuration normalization utilities.

Registered source-config compatibility shapes are normalized into the canonical
``source`` schema before pydantic validation. The accepted and retired shapes
are governed by ``configs/quality/config_compatibility_registry.yaml``.
"""

from __future__ import annotations

from bioetl.domain.types import JsonDict
from bioetl.infrastructure.config_merge import config_merge

_ENDPOINT_KEYS: tuple[str, ...] = ("base_url", "api_version")
_AUTH_KEYS: tuple[str, ...] = ("auth_type", "api_key")
_BATCH_KEYS: tuple[str, ...] = ("batch_size", "page_size", "max_url_length")
_RETIRED_PROVIDER_PAGINATION_KEYS: tuple[str, ...] = (
    "batch_size",
    "page_size",
    "max_url_length",
    "cursor_pagination",
)
_RETIRED_SOURCE_ROOT_KEYS: tuple[str, ...] = ("batch_size",)


def _deep_merge(
    base: JsonDict,  # Any: normalizer; input types vary
    override: JsonDict,  # Any: normalizer; input types vary
) -> JsonDict:  # Any: normalizer; input types vary
    """Deep merge two dictionaries with override precedence.

    Returns:
        Merged dictionary with override values taking precedence over base values.
    """
    return config_merge(base, override)


def _sync_timeout_aliases(
    data: JsonDict,  # Any: normalizer; input types vary
) -> JsonDict:  # Any: normalizer; input types vary
    """Ensure ``timeout`` and ``timeout_sec`` are kept in sync.

    Returns:
        Dictionary copy with both timeout aliases present and synchronized.
    """
    result = data.copy()
    if "timeout" in result and "timeout_sec" not in result:
        result["timeout_sec"] = result["timeout"]
    elif "timeout_sec" in result and "timeout" not in result:
        result["timeout"] = result["timeout_sec"]
    return result


def _normalize_rate_limit(
    source: JsonDict,  # Any: normalizer; input types vary
) -> None:
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


def _normalize_health_check(
    source: JsonDict,  # Any: normalizer; input types vary
) -> None:
    """Reconcile ``timeout`` ↔ ``timeout_sec`` in health_check in-place."""
    hc = source.get("health_check")
    if isinstance(hc, dict):
        source["health_check"] = _sync_timeout_aliases(hc)


def _get_dict_or_empty(
    container: JsonDict,  # Any: normalizer; input types vary
    key: str,
) -> JsonDict:  # Any: normalizer; input types vary
    """Return *container[key]* if it is a dict, otherwise an empty dict.

    Returns:
        Dictionary at container[key] if it is a dict, otherwise empty dict.
    """
    val = container.get(key)
    return val if isinstance(val, dict) else {}


def _copy_keys(
    src: JsonDict,  # Any: normalizer; input types vary
    dst: JsonDict,  # Any: normalizer; input types vary
    keys: tuple[str, ...],
) -> None:
    """Copy *keys* from *src* to *dst* via ``setdefault``."""
    for key in keys:
        if key in src:
            dst.setdefault(key, src[key])


def _normalize_source_rate_limits(
    source: JsonDict,  # Any: normalizer; input types vary
) -> None:
    """Normalize rate limiting aliases and health check timeouts."""
    _normalize_rate_limit(source)
    _normalize_health_check(source)


def _normalize_source_endpoints(
    source: JsonDict,  # Any: normalizer; input types vary
    provider_config: JsonDict,  # Any: normalizer; input types vary
    api: JsonDict,  # Any: normalizer; input types vary
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
    provider_config: JsonDict,  # Any: normalizer; input types vary
    api: JsonDict,  # Any: normalizer; input types vary
) -> None:
    """Normalize authentication configuration."""
    _copy_keys(api, provider_config, _AUTH_KEYS)


def _apply_batch_to_pagination(
    batch: JsonDict | int | None,  # Any: normalizer; input types vary
    pagination: JsonDict,  # Any: normalizer; input types vary
) -> None:
    """Extract batch_size, page_size, max_url_length from legacy batch config."""
    if isinstance(batch, dict):
        if "batch_size" in batch:
            pagination.setdefault("id_batch_size", batch["batch_size"])
        elif "size" in batch:
            pagination.setdefault("id_batch_size", batch["size"])
        elif "api_batch_size" in batch:
            pagination.setdefault("id_batch_size", batch["api_batch_size"])
        if "page_size" in batch:
            pagination.setdefault("page_size", batch["page_size"])
        if "max_url_length" in batch:
            pagination.setdefault("max_url_length", batch["max_url_length"])
    elif isinstance(batch, int):
        pagination.setdefault("id_batch_size", batch)


def _reject_retired_source_pagination_aliases(
    source: JsonDict,  # Any: normalizer; input types vary
    provider_config: JsonDict,  # Any: normalizer; input types vary
) -> None:
    """Reject retired source pagination aliases before normalization."""
    retired_root_keys = [key for key in _RETIRED_SOURCE_ROOT_KEYS if key in source]
    if retired_root_keys:
        raise ValueError(
            "Retired source root pagination aliases are not supported: "
            f"{', '.join(sorted(retired_root_keys))}. "
            "Use source.provider_config.pagination.id_batch_size instead."
        )

    retired_keys = [
        key for key in _RETIRED_PROVIDER_PAGINATION_KEYS if key in provider_config
    ]
    if retired_keys:
        raise ValueError(
            "Retired source provider pagination aliases are not supported: "
            f"{', '.join(sorted(retired_keys))}. "
            "Use source.provider_config.pagination.* instead."
        )


def _normalize_source_pagination(
    source: JsonDict,  # Any: normalizer; input types vary
    provider_config: JsonDict,  # Any: normalizer; input types vary
) -> None:
    """Normalize pagination and batch configuration."""
    _reject_retired_source_pagination_aliases(source, provider_config)

    pagination: JsonDict = _get_dict_or_empty(  # Any: values are heterogeneous
        provider_config, "pagination"
    )  # Any: normalizer; input types vary

    batch = source.pop("batch", None)
    _apply_batch_to_pagination(batch, pagination)

    if pagination:
        provider_config["pagination"] = pagination


def _prepare_source_transport_sections(
    source: JsonDict,  # Any: normalizer; input types vary
) -> tuple[
    JsonDict,  # Any: normalizer; input types vary
    JsonDict,  # Any: normalizer; input types vary
    JsonDict,  # Any: normalizer; input types vary
]:
    """Split source payload into mutable source, provider_config, and api sections."""
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

    return source_norm, provider_config, api


def _normalize_source_transport(
    source: JsonDict,  # Any: normalizer; input types vary
    provider_config: JsonDict,  # Any: normalizer; input types vary
    api: JsonDict,  # Any: normalizer; input types vary
) -> None:
    """Normalize accepted transport-facing source sections."""
    _normalize_source_rate_limits(source)
    _normalize_source_endpoints(source, provider_config, api)
    _normalize_source_auth(provider_config, api)
    _normalize_source_pagination(source, provider_config)


def _finalize_source_sections(
    config: JsonDict,  # Any: normalizer; input types vary
    source: JsonDict,  # Any: normalizer; input types vary
    provider_config: JsonDict,  # Any: normalizer; input types vary
) -> JsonDict:
    """Write normalized source sections back into the config payload."""
    if provider_config:
        source["provider_config"] = provider_config

    config["source"] = source
    return config


def normalize_source_config(
    raw: JsonDict,  # Any: normalizer; input types vary
) -> JsonDict:  # Any: normalizer; input types vary
    """Normalize registered source config aliases before validation.

    Returns:
        Normalized source configuration dictionary ready for Pydantic validation.
    """
    config = raw.copy()
    source = config.get("source")
    if not isinstance(source, dict):
        return config

    source_norm, provider_config, api = _prepare_source_transport_sections(source)
    _normalize_source_transport(source_norm, provider_config, api)
    return _finalize_source_sections(config, source_norm, provider_config)


__all__ = ["normalize_source_config"]
