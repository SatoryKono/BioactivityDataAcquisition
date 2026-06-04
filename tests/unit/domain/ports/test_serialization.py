"""Tests for JSON serialization port protocol."""

from __future__ import annotations

import pytest

from bioetl.domain.ports.serialization import JsonEncoderPort

pytestmark = pytest.mark.unit


class MockJsonEncoder:
    """Mock implementation of JsonEncoderPort for testing."""

    def dumps(
        self,
        obj: dict,
        *,
        sort_keys: bool = True,
        ensure_ascii: bool = False,
    ) -> str:
        return '{"key":"value"}'

    def dumps_canonical(self, obj: dict) -> str:
        return '{"key":"value"}'

    def loads(self, data: str | bytes) -> dict:
        return {"key": "value"}


def test_json_encoder_port_is_protocol() -> None:
    """Test that JsonEncoderPort is a runtime-checkable Protocol."""
    assert isinstance(MockJsonEncoder(), JsonEncoderPort)


def test_json_encoder_port_dumps_signature() -> None:
    """Test that JsonEncoderPort.dumps has correct signature."""
    encoder = MockJsonEncoder()
    result = encoder.dumps({"key": "value"})
    assert isinstance(result, str)


def test_json_encoder_port_dumps_canonical_signature() -> None:
    """Test that JsonEncoderPort.dumps_canonical has correct signature."""
    encoder = MockJsonEncoder()
    result = encoder.dumps_canonical({"key": "value"})
    assert isinstance(result, str)


def test_json_encoder_port_loads_signature() -> None:
    """Test that JsonEncoderPort.loads has correct signature."""
    encoder = MockJsonEncoder()
    result = encoder.loads('{"key":"value"}')
    assert isinstance(result, dict)


def test_json_encoder_port_loads_with_bytes() -> None:
    """Test that JsonEncoderPort.loads accepts bytes."""
    encoder = MockJsonEncoder()
    result = encoder.loads(b'{"key":"value"}')
    assert isinstance(result, dict)