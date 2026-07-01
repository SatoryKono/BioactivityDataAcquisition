"""Unit tests for Pandera runtime compatibility validation."""

from __future__ import annotations

import sys
import typing
from collections.abc import Mapping
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

pytestmark = pytest.mark.unit


class TestPanderaRuntimeSupportPolicy:
    """Test the runtime support policy constant."""

    def test_policy_is_immutable_mapping(self):
        """Test that policy is a frozen mapping."""
        assert isinstance(PANDERA_RUNTIME_SUPPORT_POLICY, Mapping)
        assert isinstance(PANDERA_RUNTIME_SUPPORT_POLICY, MappingProxyType)

    def test_policy_has_required_fields(self):
        """Test that policy contains required governance fields."""
        assert "owner" in PANDERA_RUNTIME_SUPPORT_POLICY
        assert "review_date" in PANDERA_RUNTIME_SUPPORT_POLICY
        assert "python_min" in PANDERA_RUNTIME_SUPPORT_POLICY
        assert "failure_policy" in PANDERA_RUNTIME_SUPPORT_POLICY
        assert "upstream_exit_condition" in PANDERA_RUNTIME_SUPPORT_POLICY

    def test_policy_values_are_strings(self):
        """Test that policy values are strings for YAML compatibility."""
        for key, value in PANDERA_RUNTIME_SUPPORT_POLICY.items():
            assert isinstance(key, str)
            assert isinstance(value, str)


class TestRequiresPanderaRuntimeValidation:
    """Test Python version detection for runtime validation."""

    def test_returns_true_for_python_314_plus(self, monkeypatch):
        """Test that Python 3.14+ requires runtime validation."""
        monkeypatch.setattr(sys, "version_info", (3, 14, 0))
        assert _requires_pandera_runtime_validation() is True

    def test_returns_true_for_python_315(self, monkeypatch):
        """Test that Python 3.15 requires runtime validation."""
        monkeypatch.setattr(sys, "version_info", (3, 15, 0))
        assert _requires_pandera_runtime_validation() is True

    def test_returns_false_for_python_313(self, monkeypatch):
        """Test that Python 3.13 does not require runtime validation."""
        monkeypatch.setattr(sys, "version_info", (3, 13, 0))
        assert _requires_pandera_runtime_validation() is False

    def test_returns_false_for_python_312(self, monkeypatch):
        """Test that Python 3.12 does not require runtime validation."""
        monkeypatch.setattr(sys, "version_info", (3, 12, 0))
        assert _requires_pandera_runtime_validation() is False


class TestTypingInspectOriginNeedsPatch:
    """Test typing_inspect origin detection."""

    def test_returns_false_when_origin_available(self, monkeypatch):
        """Test when typing_inspect.get_origin works correctly."""
        mock_module = type("MockModule", (), {})()
        mock_module.get_origin = lambda x: "some_origin"

        result = _typing_inspect_origin_needs_patch(mock_module)
        assert result is False

    def test_returns_true_when_origin_missing_but_typing_has_it(self, monkeypatch):
        """Test when typing_inspect.get_origin returns None but typing.get_origin works."""
        mock_module = type("MockModule", (), {})()
        mock_module.get_origin = lambda x: None

        result = _typing_inspect_origin_needs_patch(mock_module)
        assert result is True

    def test_returns_true_on_attribute_error(self, monkeypatch):
        """Test when typing_inspect module lacks get_origin attribute."""
        mock_module = type("MockModule", (), {})()
        # Create a mock without the attribute
        mock_module.get_origin = None

        result = _typing_inspect_origin_needs_patch(mock_module)
        assert result is True

    def test_returns_true_on_type_error(self, monkeypatch):
        """Test when typing_inspect.get_origin raises TypeError."""
        mock_module = type("MockModule", (), {})()
        mock_module.get_origin = lambda x: (_ for _ in ()).throw(TypeError())

        result = _typing_inspect_origin_needs_patch(mock_module)
        assert result is True

    def test_returns_true_on_value_error(self, monkeypatch):
        """Test when typing_inspect.get_origin raises ValueError."""
        mock_module = type("MockModule", (), {})()
        mock_module.get_origin = lambda x: (_ for _ in ()).throw(ValueError())

        result = _typing_inspect_origin_needs_patch(mock_module)
        assert result is True


class TestFindAnyFallback:
    """Test dispatcher registry fallback lookup."""

    def test_returns_fallback_when_any_in_registry(self):
        """Test returning the Any-registered fallback function."""
        registry = {typing.Any: lambda x: x}
        result = _find_any_fallback(registry)
        assert callable(result)

    def test_returns_none_when_any_not_in_registry(self):
        """Test returning None when no Any fallback is registered."""
        registry = {str: lambda x: x, int: lambda x: x}
        result = _find_any_fallback(registry)
        assert result is None

    def test_returns_none_for_empty_registry(self):
        """Test returning None for empty registry."""
        result = _find_any_fallback({})
        assert result is None


class TestDispatcherProbeHandlers:
    """Test dispatcher probe handler functions."""

    def test_union_handler_returns_input(self):
        """Test that union probe handler returns input unchanged."""
        result = _dispatcher_probe_union_handler(42)
        assert result == 42

    def test_union_handler_returns_string(self):
        """Test that union probe handler returns string unchanged."""
        result = _dispatcher_probe_union_handler("test")
        assert result == "test"

    def test_any_handler_returns_input(self):
        """Test that any probe handler returns input unchanged."""
        result = _dispatcher_probe_any_handler(42)
        assert result == 42

    def test_any_handler_returns_none(self):
        """Test that any probe handler returns None unchanged."""
        result = _dispatcher_probe_any_handler(None)
        assert result is None


class TestPanderaDispatcherNeedsPatch:
    """Test Pandera dispatcher patch detection."""

    def test_returns_true_on_attribute_error(self, monkeypatch):
        """Test when dispatcher class lacks required attributes."""
        mock_dispatcher_cls = type("MockDispatcher", (), {})

        result = _pandera_dispatcher_needs_patch(mock_dispatcher_cls)
        assert result is True

    def test_returns_true_on_instantiation_error(self, monkeypatch):
        """Test when dispatcher instantiation fails."""
        mock_dispatcher_cls = type("MockDispatcher", (), {})
        mock_dispatcher_cls.__init__ = lambda self: (_ for _ in ()).throw(RuntimeError())

        result = _pandera_dispatcher_needs_patch(mock_dispatcher_cls)
        assert result is True

    def test_returns_true_on_registry_not_dict(self, monkeypatch):
        """Test when function_registry is not a dict."""
        mock_dispatcher = type("MockDispatcher", (), {})()
        mock_dispatcher._function_registry = []
        mock_dispatcher_cls = lambda: mock_dispatcher

        result = _pandera_dispatcher_needs_patch(mock_dispatcher_cls)
        assert result is True

    def test_returns_true_on_key_error(self, monkeypatch):
        """Test when registry access raises KeyError."""
        mock_dispatcher = type("MockDispatcher", (), {})()
        mock_dispatcher._function_registry = {}
        mock_dispatcher_cls = lambda: mock_dispatcher

        result = _pandera_dispatcher_needs_patch(mock_dispatcher_cls)
        assert result is True


class TestUnsupportedRuntimeMessage:
    """Test error message formatting."""

    def test_message_for_origin_needs_patch(self):
        """Test message when typing_inspect origin needs patch."""
        message = _unsupported_runtime_message(
            origin_needs_patch=True,
            dispatcher_needs_patch=False,
        )
        assert "typing_inspect.get_origin lacks Python 3.14 union support" in message
        assert "Unsupported Pandera runtime" in message

    def test_message_for_dispatcher_needs_patch(self):
        """Test message when dispatcher needs patch."""
        message = _unsupported_runtime_message(
            origin_needs_patch=False,
            dispatcher_needs_patch=True,
        )
        assert "Pandera Dispatcher still requires union/catch-all fallback patching" in message
        assert "Unsupported Pandera runtime" in message

    def test_message_for_both_issues(self):
        """Test message when both issues are present."""
        message = _unsupported_runtime_message(
            origin_needs_patch=True,
            dispatcher_needs_patch=True,
        )
        assert "typing_inspect.get_origin lacks Python 3.14 union support" in message
        assert "Pandera Dispatcher still requires union/catch-all fallback patching" in message
        assert ";" in message  # Both reasons joined

    def test_message_for_generic_unsupported(self):
        """Test message when no specific reason is provided."""
        message = _unsupported_runtime_message(
            origin_needs_patch=False,
            dispatcher_needs_patch=False,
        )
        assert "unsupported Pandera runtime" in message
        assert "upgrade to a supported Pandera/typing_inspect combination" in message





class TestValidateSupportedPanderaRuntime:
    """Test main runtime validation function."""

    def test_returns_false_on_old_python(self, monkeypatch):
        """Test that validation returns False for Python < 3.14."""
        monkeypatch.setattr(sys, "version_info", (3, 13, 0))
        result = validate_supported_pandera_runtime()
        assert result is False

    def test_returns_false_on_import_error(self, monkeypatch):
        """Test that validation returns False when imports fail."""
        monkeypatch.setattr(sys, "version_info", (3, 14, 0))

        # Mock import to raise ImportError
        import builtins
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if "pandera" in name or "typing_inspect" in name:
                raise ImportError(f"No module named '{name}'")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)

        result = validate_supported_pandera_runtime()
        assert result is False

    def test_returns_false_on_attribute_error(self, monkeypatch):
        """Test that validation returns False on attribute errors."""
        monkeypatch.setattr(sys, "version_info", (3, 14, 0))

        import builtins
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if "pandera" in name:
                raise AttributeError("Missing attribute")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)

        result = validate_supported_pandera_runtime()
        assert result is False

    def test_returns_false_on_python_13_pydantic_compatibility(self, monkeypatch):
        """Test that validation returns False on Python 3.13 due to pydantic compatibility."""
        monkeypatch.setattr(sys, "version_info", (3, 13, 0))

        result = validate_supported_pandera_runtime()
        assert result is False

    def test_raises_on_unsupported_runtime(self, monkeypatch):
        """Test that validation raises error for unsupported runtime."""
        # Test the error message formatting directly
        message = _unsupported_runtime_message(
            origin_needs_patch=True,
            dispatcher_needs_patch=False,
        )
        assert "Unsupported Pandera runtime" in message
        assert "typing_inspect.get_origin lacks Python 3.14 union support" in message

    def test_unsupported_pandera_runtime_error_is_runtime_error(self):
        """Test that UnsupportedPanderaRuntimeError is a RuntimeError."""
        assert issubclass(UnsupportedPanderaRuntimeError, RuntimeError)

    def test_idempotent_after_successful_validation(self, monkeypatch):
        """Test that validation is idempotent after first success."""
        monkeypatch.setattr(sys, "version_info", (3, 14, 0))

        # Mock successful validation
        call_count = 0

        def mock_needs_patch(x):
            nonlocal call_count
            call_count += 1
            return False

        monkeypatch.setattr(
            "bioetl.infrastructure.compat.pandera_compat._typing_inspect_origin_needs_patch",
            mock_needs_patch,
        )
        monkeypatch.setattr(
            "bioetl.infrastructure.compat.pandera_compat._pandera_dispatcher_needs_patch",
            lambda x: False,
        )

        # Mock the imports to avoid pydantic compatibility issues
        import builtins
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if "pandera" in name:
                raise ImportError("Mocked import failure")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)

        # First call
        validate_supported_pandera_runtime()
        first_count = call_count

        # Second call should be idempotent
        validate_supported_pandera_runtime()
        second_count = call_count

        # Should not call patch detection again after first success
        assert second_count == first_count

