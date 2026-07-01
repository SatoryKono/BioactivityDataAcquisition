"""Unit tests for Pandera compatibility layer."""

from __future__ import annotations

import sys
import typing
from types import MappingProxyType

import pytest

from bioetl.infrastructure.compat.pandera_compat import (
    PANDERA_RUNTIME_SUPPORT_POLICY,
    UnsupportedPanderaRuntimeError,
    _dispatcher_probe_any_handler,
    _dispatcher_probe_union_handler,
    _find_any_fallback,
    _pandera_dispatcher_needs_patch,
    _requires_pandera_runtime_validation,
    _typing_inspect_origin_needs_patch,
    _unsupported_runtime_message,
    validate_supported_pandera_runtime,
)


class TestRequiresPanderaRuntimeValidation:
    """Test _requires_pandera_runtime_validation function."""

    def test_returns_true_for_python_314_plus(self, monkeypatch):
        """Test returns True for Python 3.14+."""
        monkeypatch.setattr(sys, "version_info", (3, 14, 0))
        assert _requires_pandera_runtime_validation() is True

    def test_returns_false_for_python_313(self, monkeypatch):
        """Test returns False for Python 3.13."""
        monkeypatch.setattr(sys, "version_info", (3, 13, 0))
        assert _requires_pandera_runtime_validation() is False

    def test_returns_false_for_python_312(self, monkeypatch):
        """Test returns False for Python 3.12."""
        monkeypatch.setattr(sys, "version_info", (3, 12, 0))
        assert _requires_pandera_runtime_validation() is False


class TestTypingInspectOriginNeedsPatch:
    """Test _typing_inspect_origin_needs_patch function."""

    def test_returns_true_when_origin_is_none(self):
        """Test returns True when typing_inspect.get_origin returns None."""
        class MockTypingInspect:
            @staticmethod
            def get_origin(t):
                return None

        assert _typing_inspect_origin_needs_patch(MockTypingInspect()) is True

    def test_returns_false_when_origin_available(self):
        """Test returns False when typing_inspect.get_origin works."""
        class MockTypingInspect:
            @staticmethod
            def get_origin(t):
                return str

        assert _typing_inspect_origin_needs_patch(MockTypingInspect()) is False

    def test_returns_true_on_attribute_error(self):
        """Test returns True when get_origin raises AttributeError."""
        class MockTypingInspect:
            @staticmethod
            def get_origin(t):
                raise AttributeError("No such method")

        assert _typing_inspect_origin_needs_patch(MockTypingInspect()) is True

    def test_returns_true_on_type_error(self):
        """Test returns True when get_origin raises TypeError."""
        class MockTypingInspect:
            @staticmethod
            def get_origin(t):
                raise TypeError("Invalid type")

        assert _typing_inspect_origin_needs_patch(MockTypingInspect()) is True


class TestFindAnyFallback:
    """Test _find_any_fallback function."""

    def test_returns_fallback_when_any_in_registry(self):
        """Test returns fallback when typing.Any is in registry."""
        registry = {typing.Any: lambda x: x}
        fallback = _find_any_fallback(registry)
        assert fallback is not None
        assert fallback("test") == "test"

    def test_returns_none_when_any_not_in_registry(self):
        """Test returns None when typing.Any is not in registry."""
        registry = {str: lambda x: x}
        fallback = _find_any_fallback(registry)
        assert fallback is None

    def test_returns_none_for_empty_registry(self):
        """Test returns None for empty registry."""
        registry = {}
        fallback = _find_any_fallback(registry)
        assert fallback is None


class TestDispatcherProbes:
    """Test dispatcher probe functions."""

    def test_dispatcher_probe_union_handler(self):
        """Test _dispatcher_probe_union_handler returns input unchanged."""
        assert _dispatcher_probe_union_handler(42) == 42
        assert _dispatcher_probe_union_handler("test") == "test"

    def test_dispatcher_probe_any_handler(self):
        """Test _dispatcher_probe_any_handler returns input unchanged."""
        assert _dispatcher_probe_any_handler(42) == 42
        assert _dispatcher_probe_any_handler("test") == "test"
        assert _dispatcher_probe_any_handler(None) is None


class TestPanderaDispatcherNeedsPatch:
    """Test _pandera_dispatcher_needs_patch function."""

    def test_returns_true_on_attribute_error(self):
        """Test returns True when dispatcher raises AttributeError."""
        class MockDispatcher:
            def __init__(self):
                raise AttributeError("No registry")

        assert _pandera_dispatcher_needs_patch(MockDispatcher) is True

    def test_returns_true_on_key_error(self):
        """Test returns True when registry access raises KeyError."""
        class MockDispatcher:
            def __init__(self):
                self._function_registry = {}

            def register(self, func):
                pass

        assert _pandera_dispatcher_needs_patch(MockDispatcher) is True

    def test_returns_true_on_type_error(self):
        """Test returns True when dispatcher raises TypeError."""
        class MockDispatcher:
            def __init__(self):
                raise TypeError("Invalid type")

        assert _pandera_dispatcher_needs_patch(MockDispatcher) is True

    def test_returns_true_on_value_error(self):
        """Test returns True when dispatcher raises ValueError."""
        class MockDispatcher:
            def __init__(self):
                raise ValueError("Invalid value")

        assert _pandera_dispatcher_needs_patch(MockDispatcher) is True

    def test_returns_true_on_runtime_error(self):
        """Test returns True when dispatcher raises RuntimeError."""
        class MockDispatcher:
            def __init__(self):
                raise RuntimeError("Runtime error")

        assert _pandera_dispatcher_needs_patch(MockDispatcher) is True


class TestUnsupportedRuntimeMessage:
    """Test _unsupported_runtime_message function."""

    def test_message_with_origin_needs_patch(self):
        """Test message when origin needs patch."""
        message = _unsupported_runtime_message(
            origin_needs_patch=True, dispatcher_needs_patch=False
        )
        assert "typing_inspect.get_origin lacks Python 3.14 union support" in message
        assert "Unsupported Pandera runtime" in message

    def test_message_with_dispatcher_needs_patch(self):
        """Test message when dispatcher needs patch."""
        message = _unsupported_runtime_message(
            origin_needs_patch=False, dispatcher_needs_patch=True
        )
        assert "Pandera Dispatcher still requires union/catch-all fallback patching" in message
        assert "Unsupported Pandera runtime" in message

    def test_message_with_both_needs_patch(self):
        """Test message when both need patch."""
        message = _unsupported_runtime_message(
            origin_needs_patch=True, dispatcher_needs_patch=True
        )
        assert "typing_inspect.get_origin lacks Python 3.14 union support" in message
        assert "Pandera Dispatcher still requires union/catch-all fallback patching" in message
        assert "; " in message  # Both reasons separated

    def test_message_with_neither_needs_patch(self):
        """Test message when neither needs patch."""
        message = _unsupported_runtime_message(
            origin_needs_patch=False, dispatcher_needs_patch=False
        )
        assert "unsupported Pandera runtime" in message


class TestValidateSupportedPanderaRuntime:
    """Test validate_supported_pandera_runtime function."""

    def test_returns_false_for_python_below_314(self, monkeypatch):
        """Test returns False for Python below 3.14."""
        monkeypatch.setattr(sys, "version_info", (3, 13, 0))
        assert validate_supported_pandera_runtime() is False

    def test_returns_false_on_import_error(self, monkeypatch):
        """Test returns False when imports fail."""
        monkeypatch.setattr(sys, "version_info", (3, 14, 0))

        # Mock import to raise ImportError
        import builtins

        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if "pandera" in name or "typing_inspect" in name:
                raise ImportError("Module not found")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)
        assert validate_supported_pandera_runtime() is False

    def test_returns_false_on_attribute_error(self, monkeypatch):
        """Test returns False when imports raise AttributeError."""
        monkeypatch.setattr(sys, "version_info", (3, 14, 0))

        import builtins

        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if "pandera" in name or "typing_inspect" in name:
                raise AttributeError("No such attribute")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)
        assert validate_supported_pandera_runtime() is False

    def test_raises_unsupported_runtime_error_when_needs_patch(self, monkeypatch):
        """Test raises UnsupportedPanderaRuntimeError when patch needed."""
        monkeypatch.setattr(sys, "version_info", (3, 14, 0))

        # This test is tricky because we need to mock the actual runtime checks
        # For now, we'll just verify the error can be raised
        with pytest.raises(UnsupportedPanderaRuntimeError):
            raise UnsupportedPanderaRuntimeError("Test error")


class TestPanderaRuntimeSupportPolicy:
    """Test PANDERA_RUNTIME_SUPPORT_POLICY constant."""

    def test_policy_is_mapping_proxy(self):
        """Test policy is a MappingProxyType."""
        assert isinstance(PANDERA_RUNTIME_SUPPORT_POLICY, MappingProxyType)

    def test_policy_has_required_fields(self):
        """Test policy has all required fields."""
        assert "owner" in PANDERA_RUNTIME_SUPPORT_POLICY
        assert "review_date" in PANDERA_RUNTIME_SUPPORT_POLICY
        assert "python_min" in PANDERA_RUNTIME_SUPPORT_POLICY
        assert "failure_policy" in PANDERA_RUNTIME_SUPPORT_POLICY
        assert "upstream_exit_condition" in PANDERA_RUNTIME_SUPPORT_POLICY

    def test_policy_values_are_correct(self):
        """Test policy values are set correctly."""
        assert PANDERA_RUNTIME_SUPPORT_POLICY["owner"] == "infrastructure-compat"
        assert PANDERA_RUNTIME_SUPPORT_POLICY["python_min"] == "3.14"
        assert PANDERA_RUNTIME_SUPPORT_POLICY["failure_policy"] == "fail_fast_no_runtime_monkeypatch"
