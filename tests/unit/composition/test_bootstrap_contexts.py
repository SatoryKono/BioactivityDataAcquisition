"""Tests for composition/bootstrap_contexts.py module exports."""

from __future__ import annotations


class TestBootstrapContextsModuleExports:
    """Tests for bootstrap context naming and module exports."""

    def test_rate_limit_context_importable(self) -> None:
        """RateLimitContext is importable from bootstrap_contexts."""
        from bioetl.composition.bootstrap_contexts import RateLimitContext

        assert RateLimitContext.__name__ == "RateLimitContext"

    def test_legacy_rate_limit_config_not_exported(self) -> None:
        """Legacy RateLimitConfig is not exported from bootstrap_contexts."""
        from bioetl.composition import bootstrap_contexts

        assert "RateLimitContext" in bootstrap_contexts.__all__
        assert "RateLimitConfig" not in bootstrap_contexts.__all__
        assert not hasattr(bootstrap_contexts, "RateLimitConfig")
