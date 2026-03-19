"""Unit tests for source configuration normalizer functions."""

from __future__ import annotations

import pytest

from bioetl.infrastructure.config.source_normalizers.source import (
    _apply_batch_to_pagination,
    _copy_keys,
    _get_dict_or_empty,
    _normalize_health_check,
    _normalize_rate_limit,
    _sync_timeout_aliases,
    normalize_source_config,
)


class TestSyncTimeoutAliases:
    """Tests for _sync_timeout_aliases."""

    def test_timeout_to_timeout_sec(self) -> None:
        """Should copy timeout to timeout_sec."""
        result = _sync_timeout_aliases({"timeout": 30})
        assert result["timeout"] == 30
        assert result["timeout_sec"] == 30

    def test_timeout_sec_to_timeout(self) -> None:
        """Should copy timeout_sec to timeout."""
        result = _sync_timeout_aliases({"timeout_sec": 60})
        assert result["timeout"] == 60
        assert result["timeout_sec"] == 60

    def test_both_present_unchanged(self) -> None:
        """Should not overwrite when both are present."""
        result = _sync_timeout_aliases({"timeout": 30, "timeout_sec": 60})
        assert result["timeout"] == 30
        assert result["timeout_sec"] == 60

    def test_neither_present(self) -> None:
        """Should not add keys when neither is present."""
        result = _sync_timeout_aliases({"other": "val"})
        assert "timeout" not in result
        assert "timeout_sec" not in result


class TestNormalizeRateLimit:
    """Tests for _normalize_rate_limit."""

    def test_with_api_key_to_authenticated(self) -> None:
        """Should copy with_api_key to authenticated."""
        source: dict = {"rate_limit": {"with_api_key": {"rate": 10}}}
        _normalize_rate_limit(source)
        assert source["rate_limit"]["authenticated"] == {"rate": 10}

    def test_authenticated_to_with_api_key(self) -> None:
        """Should copy authenticated to with_api_key."""
        source: dict = {"rate_limit": {"authenticated": {"rate": 5}}}
        _normalize_rate_limit(source)
        assert source["rate_limit"]["with_api_key"] == {"rate": 5}

    def test_no_rate_limit_key(self) -> None:
        """Should be a no-op when rate_limit is absent."""
        source: dict = {"other": "val"}
        _normalize_rate_limit(source)
        assert "rate_limit" not in source

    def test_rate_limit_not_dict(self) -> None:
        """Should be a no-op when rate_limit is not a dict."""
        source: dict = {"rate_limit": "invalid"}
        _normalize_rate_limit(source)
        assert source["rate_limit"] == "invalid"


class TestNormalizeHealthCheck:
    """Tests for _normalize_health_check."""

    def test_syncs_timeout_in_health_check(self) -> None:
        """Should sync timeout aliases in health_check."""
        source: dict = {"health_check": {"timeout": 10}}
        _normalize_health_check(source)
        assert source["health_check"]["timeout_sec"] == 10

    def test_no_health_check(self) -> None:
        """Should be a no-op when health_check is absent."""
        source: dict = {"other": "val"}
        _normalize_health_check(source)

    def test_health_check_not_dict(self) -> None:
        """Should be a no-op when health_check is not a dict."""
        source: dict = {"health_check": "invalid"}
        _normalize_health_check(source)
        assert source["health_check"] == "invalid"


class TestGetDictOrEmpty:
    """Tests for _get_dict_or_empty."""

    def test_returns_dict(self) -> None:
        """Should return the dict when present."""
        assert _get_dict_or_empty({"key": {"a": 1}}, "key") == {"a": 1}

    def test_returns_empty_when_not_dict(self) -> None:
        """Should return empty dict when value is not a dict."""
        assert _get_dict_or_empty({"key": "string"}, "key") == {}

    def test_returns_empty_when_missing(self) -> None:
        """Should return empty dict when key is absent."""
        assert _get_dict_or_empty({}, "key") == {}


class TestCopyKeys:
    """Tests for _copy_keys."""

    def test_copies_existing_keys(self) -> None:
        """Should copy keys from src to dst via setdefault."""
        src = {"a": 1, "b": 2}
        dst: dict = {}
        _copy_keys(src, dst, ("a", "b"))
        assert dst == {"a": 1, "b": 2}

    def test_does_not_overwrite_existing(self) -> None:
        """Should not overwrite existing keys in dst."""
        src = {"a": 1}
        dst = {"a": 99}
        _copy_keys(src, dst, ("a",))
        assert dst["a"] == 99

    def test_skips_missing_keys(self) -> None:
        """Should skip keys not in src."""
        src = {"a": 1}
        dst: dict = {}
        _copy_keys(src, dst, ("a", "b"))
        assert dst == {"a": 1}


class TestApplyBatchToPagination:
    """Tests for _apply_batch_to_pagination."""

    def test_batch_dict_with_batch_size(self) -> None:
        """Should extract batch_size from dict."""
        pagination: dict = {}
        _apply_batch_to_pagination({"batch_size": 500}, pagination)
        assert pagination.get("id_batch_size") == 500

    def test_batch_dict_with_size_alias(self) -> None:
        """Should use 'size' as alias for batch_size."""
        pagination: dict = {}
        _apply_batch_to_pagination({"size": 200}, pagination)
        assert pagination.get("id_batch_size") == 200

    def test_batch_dict_with_api_batch_size(self) -> None:
        """Should use 'api_batch_size' as alias."""
        pagination: dict = {}
        _apply_batch_to_pagination({"api_batch_size": 100}, pagination)
        assert pagination.get("id_batch_size") == 100

    def test_batch_dict_with_page_size(self) -> None:
        """Should extract page_size."""
        pagination: dict = {}
        _apply_batch_to_pagination({"page_size": 50}, pagination)
        assert pagination.get("page_size") == 50

    def test_batch_dict_with_max_url_length(self) -> None:
        """Should extract max_url_length."""
        pagination: dict = {}
        _apply_batch_to_pagination({"max_url_length": 2000}, pagination)
        assert pagination.get("max_url_length") == 2000

    def test_batch_int(self) -> None:
        """Should use int batch as batch_size and id_batch_size."""
        pagination: dict = {}
        _apply_batch_to_pagination(300, pagination)
        assert pagination.get("id_batch_size") == 300

    def test_batch_none(self) -> None:
        """Should be a no-op when batch is None."""
        pagination: dict = {}
        _apply_batch_to_pagination(None, pagination)
        assert pagination == {}


class TestNormalizeSourceConfig:
    """Tests for normalize_source_config."""

    def test_no_source_section(self) -> None:
        """Should handle configs without source section."""
        raw = {"provider": "test"}
        result = normalize_source_config(raw)
        assert "provider" in result

    def test_source_not_dict(self) -> None:
        """Should handle non-dict source."""
        raw = {"source": "invalid"}
        result = normalize_source_config(raw)
        assert result["source"] == "invalid"

    def test_normalizes_complete_source(self) -> None:
        """Should normalize a complete source config."""
        raw = {
            "source": {
                "type": "api",
                "api": {"base_url": "https://api.example.com"},
                "client": {"timeout": 30},
                "rate_limit": {"with_api_key": {"rate": 10}},
                "health_check": {"timeout": 5},
                "provider_config": {
                    "pagination": {"id_batch_size": 100},
                },
            }
        }
        result = normalize_source_config(raw)
        source = result["source"]
        assert "rate_limit" in source
        assert source["rate_limit"].get("authenticated") == {"rate": 10}

    def test_normalizes_api_config(self) -> None:
        """Should normalize API endpoint config."""
        raw = {
            "source": {
                "type": "api",
                "api": {"base_url": "https://example.com", "api_version": "v1"},
                "provider_config": {},
            }
        }
        result = normalize_source_config(raw)
        source = result["source"]
        provider_config = source.get("provider_config", {})
        assert provider_config.get("base_url") == "https://example.com"

    def test_rejects_retired_provider_pagination_aliases(self) -> None:
        """Retired provider pagination aliases should fail fast."""
        raw = {
            "source": {
                "provider_config": {
                    "provider": "chembl",
                    "batch_size": 25,
                    "page_size": 250,
                    "cursor_pagination": True,
                }
            }
        }

        with pytest.raises(ValueError, match="Retired source provider pagination aliases"):
            normalize_source_config(raw)

    def test_canonical_provider_pagination_is_accepted(self) -> None:
        """Canonical pagination-only source config should stay valid."""
        raw = {
            "source": {
                "provider_config": {
                    "provider": "chembl",
                    "pagination": {
                        "id_batch_size": 25,
                        "page_size": 250,
                        "strategy": "offset",
                    },
                }
            }
        }

        result = normalize_source_config(raw)
        pagination = result["source"]["provider_config"]["pagination"]
        assert pagination["id_batch_size"] == 25
        assert pagination["page_size"] == 250
