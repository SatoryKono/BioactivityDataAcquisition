# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for bootstrap_logger module.

Tests the composition layer's bootstrap-phase structured logging utility.
"""

from __future__ import annotations

import pytest
import structlog


@pytest.mark.unit
class TestBootstrapLogger:
    """Tests for BootstrapLogger class."""

    def test_get_bootstrap_logger_returns_bound_logger(self):
        """Test that get_bootstrap_logger returns a structlog bound logger."""
        from bioetl.composition.bootstrap_logger import (
            get_bootstrap_logger,
            reset_bootstrap_logger,
        )

        reset_bootstrap_logger()  # Ensure clean state
        logger = get_bootstrap_logger()

        assert logger is not None
        assert isinstance(logger, structlog.stdlib.BoundLogger)

    def test_get_bootstrap_logger_is_cached(self):
        """Test that get_bootstrap_logger returns the same instance."""
        from bioetl.composition.bootstrap_logger import (
            get_bootstrap_logger,
            reset_bootstrap_logger,
        )

        reset_bootstrap_logger()
        logger1 = get_bootstrap_logger()
        logger2 = get_bootstrap_logger()

        assert logger1 is logger2

    def test_reset_bootstrap_logger_clears_cache(self):
        """Test that reset_bootstrap_logger clears the cached logger."""
        from bioetl.composition.bootstrap_logger import (
            get_bootstrap_logger,
            reset_bootstrap_logger,
        )

        reset_bootstrap_logger()
        logger1 = get_bootstrap_logger()
        reset_bootstrap_logger()
        logger2 = get_bootstrap_logger()

        # After reset, should be a different instance
        assert logger1 is not logger2

    def test_bootstrap_logger_class_has_all_methods(self):
        """Test that BootstrapLogger has debug, info, warning, error methods."""
        from bioetl.composition.bootstrap_logger import BootstrapLogger

        logger = BootstrapLogger()

        assert hasattr(logger, "debug")
        assert hasattr(logger, "info")
        assert hasattr(logger, "warning")
        assert hasattr(logger, "error")
        assert callable(logger.debug)
        assert callable(logger.info)
        assert callable(logger.warning)
        assert callable(logger.error)

    def test_bootstrap_logger_methods_accept_kwargs(self):
        """Test that BootstrapLogger methods accept keyword arguments."""
        from bioetl.composition.bootstrap_logger import BootstrapLogger

        logger = BootstrapLogger()

        # These should not raise
        logger.debug("test_event", key="value", provider="chembl")
        logger.info("test_event", key="value", provider="chembl")
        logger.warning("test_event", key="value", provider="chembl")
        logger.error("test_event", key="value", provider="chembl")

        assert callable(logger.debug)
        assert callable(logger.info)
        assert callable(logger.warning)
        assert callable(logger.error)

    def test_bootstrap_logger_bound_context(self):
        """Test that bootstrap logger has run_id and stage bound."""
        from bioetl.composition.bootstrap_logger import (
            get_bootstrap_logger,
            reset_bootstrap_logger,
        )

        reset_bootstrap_logger()
        logger = get_bootstrap_logger()

        # Access the bound values through the context vars
        # The logger should have 'bootstrap' run_id and 'bootstrap' stage
        # We can verify this by checking the logger's _context attribute
        assert hasattr(logger, "_context")
        # The bound values are in the context
        context = dict(logger._context)
        assert context.get("run_id") == "bootstrap"
        assert context.get("stage") == "bootstrap"
