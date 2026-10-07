"""P02 F5: independent expected bytes for pre-existing canonical profiles."""

from __future__ import annotations

import math
from datetime import UTC, datetime
from uuid import UUID

import pytest

from bioetl.domain.aggregates import QuarantineEntry
from bioetl.domain.aggregates.events import QuarantineEntryCreated
from bioetl.domain.deterministic_identity import deterministic_id
from bioetl.domain.normalization import json as codec
from bioetl.domain.normalization.hash_identity import (
    serialize_hash_identity_canonical_json,
)
from bioetl.domain.normalization.json import (
    CanonicalJsonProfile,
    serialize_json_canonical,
)
from bioetl.domain.serialization import (
    serialize_to_canonical_json,
    serialize_to_json_canonical,
)
from bioetl.domain.types import BatchID, ContentHash, RunID
from bioetl.infrastructure.serialization.encoders import (
    OrjsonEncoder,
    StdLibJsonEncoder,
)

pytestmark = pytest.mark.unit
DOMAIN = CanonicalJsonProfile.DOMAIN_V1
PORT = CanonicalJsonProfile.PORT_V1
HISTORICAL = CanonicalJsonProfile.DOMAIN_STDLIB_V1
HISTORICAL_PORT = CanonicalJsonProfile.PORT_ORJSON_V1


@pytest.mark.parametrize("profile", [PORT, HISTORICAL])
def test_stdlib_profile_reader_preserves_historical_large_integer_bytes(
    profile: CanonicalJsonProfile,
) -> None:
    expected = '{"x":18446744073709551617}'
    reader = StdLibJsonEncoder()
    restored = reader.loads(expected)
    assert restored == {"x": 2**64 + 1}
    assert reader.dumps_canonical(restored, profile=profile) == expected
    assert OrjsonEncoder().dumps_canonical(restored, profile=profile) == expected


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_historical_orjson_port_admission_is_explicit(value: float) -> None:
    payload = {"x": value, "nested": [value]}
    expected = '{"nested":[null],"x":null}'
    assert serialize_json_canonical(payload, profile=HISTORICAL_PORT) == expected
    for encoder in (OrjsonEncoder(), StdLibJsonEncoder()):
        assert encoder.dumps_canonical(payload, profile=HISTORICAL_PORT) == expected
        with pytest.raises(ValueError, match="NaN or Infinity"):
            encoder.dumps_canonical(payload)


def test_historical_orjson_port_preserves_extended_types_and_integer_boundary() -> None:
    payload = {"x": datetime(2026, 10, 7, tzinfo=UTC), "id": UUID(int=1)}
    expected = (
        '{"id":"00000000-0000-0000-0000-000000000001","x":"2026-10-07T00:00:00+00:00"}'
    )
    for encoder in (OrjsonEncoder(), StdLibJsonEncoder()):
        assert encoder.dumps_canonical(payload, profile=HISTORICAL_PORT) == expected
        with pytest.raises(TypeError):
            encoder.dumps_canonical({"x": 2**64}, profile=HISTORICAL_PORT)


def test_historical_orjson_port_never_falls_back_without_codec(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(codec, "orjson", None)
    with pytest.raises(ImportError, match="port-orjson-v1"):
        serialize_json_canonical({"x": math.nan}, profile=HISTORICAL_PORT)


# Expected literals recorded/reviewed from clean d68fdc3a, not derived from either
# new implementation. Existing deterministic_identity_v1.json remains untouched.
CORPUS = [
    (0.0, '{"x":0.0}', '{"x":0.0}'),
    (-0.0, '{"x":-0.0}', '{"x":-0.0}'),
    (1e-7, '{"x":1e-7}', '{"x":1e-07}'),
    (1e-6, '{"x":1e-6}', '{"x":1e-06}'),
    (1e20, '{"x":1e+20}', '{"x":1e+20}'),
    (
        math.nextafter(1e-7, math.inf),
        '{"x":1.0000000000000001e-7}',
        '{"x":1.0000000000000001e-07}',
    ),
    (
        math.nextafter(1e-7, -math.inf),
        '{"x":9.999999999999998e-8}',
        '{"x":9.999999999999998e-08}',
    ),
    (5e-324, '{"x":5e-324}', '{"x":5e-324}'),
    (
        1.7976931348623157e308,
        '{"x":1.7976931348623157e+308}',
        '{"x":1.7976931348623157e+308}',
    ),
    (-(2**63), '{"x":-9223372036854775808}', '{"x":-9223372036854775808}'),
    (2**64 - 1, '{"x":18446744073709551615}', '{"x":18446744073709551615}'),
    (
        ["👋", {"β": [None, True, "é"]}],
        '{"x":["\\ud83d\\udc4b",{"\\u03b2":[null,true,"\\u00e9"]}]}',
        '{"x":["\\ud83d\\udc4b",{"\\u03b2":[null,true,"\\u00e9"]}]}',
    ),
]


@pytest.mark.parametrize("value,domain_bytes,port_bytes", CORPUS)
def test_expected_bytes_across_all_canonical_entrypoints(
    value: object,
    domain_bytes: str,
    port_bytes: str,
) -> None:
    payload = {"x": value}
    for serialize in (
        serialize_json_canonical,
        serialize_to_json_canonical,
        serialize_to_canonical_json,
        serialize_hash_identity_canonical_json,
    ):
        assert serialize(payload) == domain_bytes
        assert serialize(payload, profile=HISTORICAL) == port_bytes
        assert serialize(payload, profile=CanonicalJsonProfile.PORT_V1) == port_bytes
    for encoder in (OrjsonEncoder(), StdLibJsonEncoder()):
        assert encoder.dumps_canonical(payload) == port_bytes
        assert encoder.dumps_canonical(payload, profile=DOMAIN) == domain_bytes
        assert encoder.dumps_canonical(payload, profile=HISTORICAL) == port_bytes
        assert (
            encoder.dumps_canonical(payload, profile=CanonicalJsonProfile.PORT_V1)
            == port_bytes
        )


@pytest.mark.parametrize("integer", [2**64, -(2**63) - 1])
def test_integer_bounds_are_explicit_and_port_adapters_match(integer: int) -> None:
    expected = '{"x":' + str(integer) + "}"
    for encoder in (OrjsonEncoder(), StdLibJsonEncoder()):
        assert encoder.dumps_canonical({"x": integer}) == expected
        with pytest.raises(TypeError, match="64-bit"):
            encoder.dumps_canonical({"x": integer}, profile=DOMAIN)
    with pytest.raises(TypeError, match="64-bit"):
        serialize_json_canonical({"x": integer})
    assert serialize_json_canonical({"x": integer}, profile=HISTORICAL) == expected


@pytest.mark.parametrize(
    "payload",
    [{"x": math.nan}, {"x": math.inf}, {"x": -math.inf}, {1: "bad"}, {"x": object()}],
)
def test_unsupported_values_fail_identically_in_both_port_adapters(
    payload: dict,
) -> None:
    errors = []
    for encoder in (OrjsonEncoder(), StdLibJsonEncoder()):
        with pytest.raises((TypeError, ValueError)) as error:
            encoder.dumps_canonical(payload)
        errors.append((type(error.value), str(error.value)))
    assert errors[0] == errors[1]


def test_required_domain_codec_does_not_silently_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(codec, "orjson", None)
    monkeypatch.setattr(codec, "_orjson_available", False)
    with pytest.raises(ImportError, match="requires the locked orjson"):
        serialize_json_canonical({"x": 1e-7})
    assert serialize_json_canonical({"x": 1e-7}, profile=HISTORICAL) == '{"x":1e-07}'


@pytest.mark.parametrize("unknown", [None, "", "unknown", "latest"])
def test_unknown_historical_profile_is_not_replaced_with_default(
    unknown: object,
) -> None:
    with pytest.raises(ValueError):
        serialize_json_canonical({"x": 1e-7}, profile=unknown)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "metadata,expected",
    [
        (None, "df808d52-64c6-5fa3-9599-542d6d08c37c"),
        ({}, "901a129f-2b46-5d4b-abfa-5f02bd4409d7"),
        ({"nested": {"items": [1, 1e-7]}}, "49338572-8144-57a9-8933-74e6c209d5f6"),
    ],
)
def test_event_snapshot_keeps_baseline_ids(
    metadata: dict | None, expected: str
) -> None:
    event = QuarantineEntryCreated(
        occurred_at=datetime(2026, 10, 7, tzinfo=UTC),
        run_id=RunID(UUID(int=1)),
        batch_id=BatchID(UUID(int=2)),
        pipeline_name="p",
        error_code="E",
        payload_hash=ContentHash("a" * 64),
        metadata=metadata,
    )
    assert event.event_id == expected


def test_quarantine_default_identity_and_payload_bytes_remain_historical() -> None:
    entry = QuarantineEntry.create(
        "p",
        "E",
        {"value": 1e-7},
        RunID(UUID(int=1)),
        BatchID(UUID(int=2)),
        created_at=datetime(2026, 10, 7, tzinfo=UTC),
        metadata={"nested": [1]},
    )
    assert entry.entry_id == "efcc358c-0af9-5b69-97b6-bc27d5ad5492"
    assert (
        entry.payload_hash
        == "910750038eb30a40d06da88009b6259aabaf3751b3cb212c616d51abb6b008a4"
    )
    assert entry.collect_events()[0].event_id == "0652f667-5390-5674-b314-47b94c1a00ac"


def test_explicit_historical_factory_profile_reproduces_identity() -> None:
    args = ("p", "E", {"value": 1e-7}, RunID(UUID(int=1)), BatchID(UUID(int=2)))
    kwargs = {"created_at": datetime(2026, 10, 7, tzinfo=UTC)}
    current = QuarantineEntry.create(*args, **kwargs)
    historical = QuarantineEntry.create(*args, **kwargs, canonical_profile=HISTORICAL)
    assert current.payload == historical.payload
    assert current.payload_hash != historical.payload_hash
    assert current.entry_id != historical.entry_id
    event = historical.collect_events()[0]
    payload = {
        name: getattr(event, name)
        for name in (
            "occurred_at",
            "run_id",
            "batch_id",
            "pipeline_name",
            "error_code",
            "payload_hash",
            "metadata",
        )
    }
    assert event.event_id == deterministic_id(
        "QuarantineEntryCreated", payload, profile=HISTORICAL
    )
