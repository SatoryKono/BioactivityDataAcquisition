"""Same-path owner tests for JSON encoder module."""

from __future__ import annotations

import pytest

from bioetl.infrastructure.serialization.encoders import StdLibJsonEncoder, __all__


pytestmark = pytest.mark.unit


def test_stdlib_json_encoder_round_trips_compact_json() -> None:
    encoder = StdLibJsonEncoder()
    payload = {"b": 2, "a": 1}

    dumped = encoder.dumps(payload)

    assert dumped == '{"a":1,"b":2}'
    assert encoder.loads(dumped) == {"a": 1, "b": 2}


def test_stdlib_json_encoder_canonical_output_is_stable() -> None:
    encoder = StdLibJsonEncoder()

    assert encoder.dumps_canonical({"b": "beta", "a": "alpha"}) == (
        '{"a":"alpha","b":"beta"}'
    )
    assert "get_json_encoder" in __all__
