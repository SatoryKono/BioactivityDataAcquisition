"""TC-11 HTTP provider fixtures. The transport is mocked; smoke stays NOT_RUN."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

import pytest

from iuphar_target_class.http_provider import (
    HttpProvider,
    HttpTimeouts,
    TransportResponse,
    hit_status,
    http_adapter_config,
    publish_allowed,
    smoke_status,
)
from iuphar_target_class.snapshot import (
    VERSION_MATCHED,
    Completeness,
    assess_completeness,
)

pytestmark = pytest.mark.unit

_SECRET = "super-secret-value"
_TARGET = b'{"id":"1","type":"gpcr"}'


@dataclass
class ManualClock:
    now: float = 0.0
    sleeps: list[float] = field(default_factory=list)

    def time(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


@dataclass
class ScriptedTransport:
    script: list[TransportResponse | type[TimeoutError] | BaseException]
    calls: list[tuple[str, str, dict[str, str], HttpTimeouts]] = field(
        default_factory=list
    )

    def exchange(
        self,
        method: str,
        path: str,
        headers: Mapping[str, str],
        timeouts: HttpTimeouts,
    ) -> TransportResponse:
        self.calls.append((method, path, dict(headers), timeouts))
        item = self.script.pop(0)
        if item is TimeoutError:
            raise TimeoutError
        if isinstance(item, BaseException):
            raise item
        return item


def _completeness(*, approved: bool) -> Completeness:
    return assess_completeness(
        coverage_approved=approved,
        required_types_loaded=True,
        pagination_complete=True,
        transport_or_schema_errors=False,
        totals_match=True,
        provider_versions=VERSION_MATCHED,
        version_limitation_recorded=True,
    )


def _provider(
    script: list[TransportResponse | type[TimeoutError] | BaseException],
    *,
    approved: bool = True,
    api_key: str | None = None,
    clock: ManualClock | None = None,
) -> tuple[HttpProvider, ScriptedTransport, ManualClock]:
    transport = ScriptedTransport(script)
    used_clock = clock if clock is not None else ManualClock()
    provider = HttpProvider(
        transport,
        completeness=_completeness(approved=approved),
        clock=used_clock,
        api_key=api_key,
    )
    return provider, transport, used_clock


def _response(
    status: int,
    body: bytes = b"",
    retry_after: str | None = None,
) -> TransportResponse:
    headers = () if retry_after is None else (("Retry-After", retry_after),)
    return TransportResponse(status, body, headers)


def test_approved_adapter_numbers_and_timeout_split() -> None:
    config = http_adapter_config()
    assert config.timeout_sec == 15
    assert config.read_timeout_multiplier == 2
    assert config.max_retries == 3
    assert config.retry_base_delay == 1
    assert config.retry_max_delay == 30
    assert config.requests_per_second == 1
    assert config.burst == 1
    assert config.failure_threshold == 5
    assert config.recovery_timeout == 60
    assert config.operational_check == "NOT_RUN"
    assert config.timeouts == HttpTimeouts(15, 15, 15, 30)


def test_smoke_without_a_key_stays_not_run() -> None:
    check = smoke_status()
    assert check.status == "NOT_RUN"
    assert check.reason == (
        "параметры адаптера записаны; эксплуатационная проверка HTTP не запускалась"
    )


def test_404_on_a_complete_snapshot_is_not_found() -> None:
    provider, transport, _clock = _provider([_response(404)])
    hit = provider.get_target("1")
    assert hit_status(hit) == "not_found"
    assert hit.diagnostics == ()
    assert len(transport.calls) == 1


def test_empty_search_on_a_complete_snapshot_is_not_found() -> None:
    provider, _transport, _clock = _provider([_response(200, b'{"results":[]}')])
    hit = provider.find_by_uniprot("P12345")
    assert hit_status(hit) == "not_found"
    assert hit.records == ()


def test_401_is_source_unavailable_and_is_not_retried() -> None:
    provider, transport, _clock = _provider([_response(401)])
    hit = provider.get_target("1")
    assert hit_status(hit) == "source_unavailable"
    assert hit.diagnostics == ("source_unavailable:http_401",)
    assert len(transport.calls) == 1


def test_403_is_source_unavailable_and_is_not_retried() -> None:
    provider, transport, _clock = _provider([_response(403)])
    hit = provider.get_target("1")
    assert hit_status(hit) == "source_unavailable"
    assert hit.diagnostics == ("source_unavailable:http_403",)
    assert len(transport.calls) == 1


def test_429_exhausts_the_approved_retry_budget() -> None:
    script = [_response(429) for _index in range(4)]
    provider, transport, clock = _provider(script)
    hit = provider.get_target("1")
    assert hit_status(hit) == "source_unavailable"
    assert hit.diagnostics == ("source_unavailable:retries_exhausted",)
    assert len(transport.calls) == 4
    assert clock.sleeps == [1, 2, 4]


def test_timeout_exhausts_the_approved_retry_budget() -> None:
    provider, transport, _clock = _provider([TimeoutError] * 4)
    hit = provider.get_target("1")
    assert hit_status(hit) == "source_unavailable"
    assert hit.diagnostics == ("source_unavailable:timeout",)
    assert len(transport.calls) == 4


def test_bad_json_is_source_unavailable() -> None:
    provider, transport, _clock = _provider([_response(200, b"{")])
    hit = provider.get_target("1")
    assert hit_status(hit) == "source_unavailable"
    assert hit.diagnostics == ("source_unavailable:bad_json",)
    assert len(transport.calls) == 1


def test_schema_change_is_source_unavailable() -> None:
    provider, _transport, _clock = _provider([_response(200, b'{"name":"Receptor"}')])
    hit = provider.get_target("1")
    assert hit_status(hit) == "source_unavailable"
    assert hit.diagnostics == ("source_unavailable:schema",)
    assert hit.records == ()


def test_empty_body_is_source_unavailable() -> None:
    provider, _transport, _clock = _provider([_response(200, b"")])
    hit = provider.get_target("1")
    assert hit_status(hit) == "source_unavailable"
    assert hit.diagnostics == ("source_unavailable:empty_body",)


def test_incomplete_snapshot_does_not_publish_or_report_not_found() -> None:
    provider, _transport, _clock = _provider([_response(404)], approved=False)
    hit = provider.get_target("1")
    assert hit_status(hit) == "source_unavailable"
    assert hit.diagnostics == ("source_unavailable:incomplete",)
    assert publish_allowed(_completeness(approved=False)) is False
    assert publish_allowed(_completeness(approved=True)) is True


def test_retry_after_stays_inside_the_approved_max_delay() -> None:
    script = [
        _response(429, retry_after="2"),
        _response(429, retry_after="120"),
        _response(429, retry_after="2"),
        _response(429, retry_after="2"),
    ]
    provider, transport, clock = _provider(script)
    hit = provider.get_target("1")
    assert hit_status(hit) == "source_unavailable"
    assert hit.diagnostics == ("source_unavailable:retries_exhausted",)
    assert clock.sleeps == [2, 30, 2]
    assert len(transport.calls) == 4


def test_successful_payload_is_cached_and_errors_are_not() -> None:
    provider, transport, _clock = _provider([_response(200, _TARGET), _response(401)])
    first = provider.get_target("1")
    second = provider.get_target("1")
    denied = provider.get_target("2")
    assert hit_status(first) == "available"
    assert second.records == first.records
    assert hit_status(denied) == "source_unavailable"
    assert [call[1] for call in transport.calls] == ["/targets/1", "/targets/2"]


def test_rate_limit_uses_the_approved_one_request_per_second() -> None:
    provider, _transport, clock = _provider(
        [_response(200, _TARGET), _response(200, b'{"id":"2"}')]
    )
    provider.get_target("1")
    provider.get_target("2")
    assert clock.sleeps == [1]


def test_circuit_opens_after_five_failures_and_retries_after_recovery() -> None:
    clock = ManualClock()
    provider, transport, _clock = _provider([TimeoutError] * 24, clock=clock)
    for _index in range(5):
        assert hit_status(provider.get_target("1")) == "source_unavailable"
    blocked = provider.get_target("1")
    assert blocked.diagnostics == ("source_unavailable:circuit_open",)
    assert len(transport.calls) == 20
    clock.now += 60
    resumed = provider.get_target("1")
    assert hit_status(resumed) == "source_unavailable"
    assert len(transport.calls) == 24


def test_api_key_stays_out_of_the_url_and_the_result() -> None:
    provider, transport, _clock = _provider([_response(200, _TARGET)], api_key=_SECRET)
    hit = provider.get_target("1")
    rendered = " ".join(hit.diagnostics) + " " + transport.calls[0][1]
    assert _SECRET not in rendered
    assert "GTP-API-Key" not in rendered
    assert transport.calls[0][2] == {"GTP-API-Key": _SECRET}
    assert transport.calls[0][3] == HttpTimeouts(15, 15, 15, 30)


def test_zero_retry_after_still_waits_for_the_rate_limit() -> None:
    script = [_response(429, retry_after="0") for _index in range(4)]
    provider, transport, clock = _provider(script)
    hit = provider.get_target("1")
    assert hit_status(hit) == "source_unavailable"
    assert clock.sleeps == [1, 1, 1]
    assert len(transport.calls) == 4


def test_connection_reset_is_source_unavailable() -> None:
    script = [ConnectionResetError("connection reset") for _index in range(4)]
    provider, transport, _clock = _provider(script)
    hit = provider.get_target("1")
    assert hit_status(hit) == "source_unavailable"
    assert hit.diagnostics == ("source_unavailable:connection",)
    assert len(transport.calls) == 4


def test_mismatched_target_id_is_schema_and_is_not_cached() -> None:
    body = b'{"id":"2"}'
    provider, transport, _clock = _provider(
        [_response(200, body), _response(200, body)]
    )
    first = provider.get_target("1")
    second = provider.get_target("1")
    assert first.diagnostics == ("source_unavailable:schema",)
    assert second.diagnostics == ("source_unavailable:schema",)
    assert len(transport.calls) == 2


def test_unfinished_search_page_is_not_not_found() -> None:
    body = b'{"results":[],"next":"/targets?page=2"}'
    provider, transport, _clock = _provider([_response(200, body)])
    hit = provider.find_by_uniprot("P12345")
    assert hit_status(hit) == "source_unavailable"
    assert hit.diagnostics == ("source_unavailable:schema",)
    assert len(transport.calls) == 1
