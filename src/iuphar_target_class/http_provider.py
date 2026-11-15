"""HTTP provider with the same read interface as the offline snapshot.

Numbers come from the approved ``http_adapter`` block. This module does not
run the operational smoke check and does not read ``.env``.
"""

from __future__ import annotations

import json
import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import quote

from .acceptance import NOT_RUN_REASONS
from .policy import policy_document
from .snapshot import Completeness, FrozenRecord, ProviderHit, freeze_record

API_KEY_HEADER = "GTP-API-Key"
RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})
AUTH_STATUS = frozenset({401, 403})


@dataclass(frozen=True, slots=True)
class HttpTimeouts:
    """Approved split: connect, write and pool share ``timeout_sec``."""

    connect: int
    write: int
    pool: int
    read: int


@dataclass(frozen=True, slots=True)
class HttpAdapterConfig:
    """Recorded adapter configuration. Callers do not supply other numbers."""

    timeout_sec: int
    read_timeout_multiplier: int
    max_retries: int
    retry_base_delay: int
    retry_max_delay: int
    requests_per_second: int
    burst: int
    failure_threshold: int
    recovery_timeout: int
    version: str
    operational_check: str

    @property
    def timeouts(self) -> HttpTimeouts:
        read = self.timeout_sec * self.read_timeout_multiplier
        return HttpTimeouts(self.timeout_sec, self.timeout_sec, self.timeout_sec, read)


@dataclass(frozen=True, slots=True)
class TransportResponse:
    """One mock or live HTTP response. The body is raw bytes."""

    status_code: int
    body: bytes = b""
    headers: tuple[tuple[str, str], ...] = ()

    def header(self, name: str) -> str | None:
        folded = name.casefold()
        for key, value in self.headers:
            if key.casefold() == folded:
                return value
        return None


@dataclass(frozen=True, slots=True)
class SmokeCheck:
    """Operational smoke. Without a live run this stays ``NOT_RUN``."""

    status: str
    reason: str


@dataclass(frozen=True, slots=True)
class _Step:
    hit: ProviderHit
    retry: bool
    failure: bool
    cacheable: bool
    code: str
    retry_after: str | None = None


class Clock(Protocol):
    """Monotonic clock. Tests supply a manual implementation."""

    def time(self) -> float:
        """Return the current monotonic time in seconds."""

    def sleep(self, seconds: float) -> None:
        """Advance or block for ``seconds``."""


class Transport(Protocol):
    """One HTTP exchange. The provider never opens a socket itself."""

    def exchange(
        self,
        method: str,
        path: str,
        headers: Mapping[str, str],
        timeouts: HttpTimeouts,
    ) -> TransportResponse:
        """Perform one request."""


class _SystemClock:
    def time(self) -> float:
        return time.monotonic()

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)


class _RateGate:
    def __init__(self, config: HttpAdapterConfig, clock: Clock) -> None:
        self._rate = config.requests_per_second
        self._burst = config.burst
        self._clock = clock
        self._tokens = float(config.burst)
        self._updated = clock.time()

    def acquire(self) -> None:
        self._refill()
        if self._tokens < 1:
            deficit = (1 - self._tokens) / self._rate
            self._clock.sleep(deficit)
            self._refill()
        self._tokens -= 1

    def _refill(self) -> None:
        now = self._clock.time()
        elapsed = now - self._updated
        self._updated = now
        refilled = self._tokens + elapsed * self._rate
        self._tokens = min(float(self._burst), refilled)


class _Breaker:
    def __init__(self, config: HttpAdapterConfig) -> None:
        self._threshold = config.failure_threshold
        self._recovery = config.recovery_timeout
        self._failures = 0
        self._open_until: float | None = None

    def allow(self, now: float) -> bool:
        if self._open_until is None:
            return True
        if now < self._open_until:
            return False
        self._open_until = None
        return True

    def fail(self, now: float) -> None:
        self._failures += 1
        if self._failures >= self._threshold:
            self._open_until = now + self._recovery

    def ok(self) -> None:
        self._failures = 0
        self._open_until = None


class HttpProvider:
    """Snapshot-shaped reads over an injected transport."""

    def __init__(
        self,
        transport: Transport,
        *,
        completeness: Completeness,
        clock: Clock | None = None,
        api_key: str | None = None,
    ) -> None:
        self.config = http_adapter_config()
        self.adapter_version = self.config.version
        self._transport = transport
        self._completeness = completeness
        self._clock = clock if clock is not None else _SystemClock()
        self._api_key = api_key
        self._cache: dict[str, ProviderHit] = {}
        self._rate = _RateGate(self.config, self._clock)
        self._breaker = _Breaker(self.config)

    def get_target(self, target_id: str) -> ProviderHit:
        """Return one target payload, or an empty hit when it is absent."""
        path = f"/targets/{quote(target_id, safe='')}"
        return self._get(path, "target", target_id)

    def find_by_uniprot(self, accession: str) -> ProviderHit:
        """Return targets for one accession. An empty list is an empty search."""
        path = "/targets?uniprot=" + quote(accession, safe="")
        return self._get(path, "search")

    def find_by_gene(self, symbol: str, species: str) -> ProviderHit:
        """Return targets for one gene symbol in one species."""
        path = "/targets?gene=" + quote(symbol, safe="")
        path += "&species=" + quote(species, safe="")
        return self._get(path, "search")

    def get_families(self, family_ids: tuple[str, ...]) -> ProviderHit:
        """Return stored families. A transport failure drops every record."""
        records: list[FrozenRecord] = []
        missing: list[str] = []
        for family_id in family_ids:
            path = f"/families/{quote(family_id, safe='')}"
            hit = self._get(path, "family", family_id)
            if _is_unavailable(hit):
                return hit
            if hit.records:
                records.extend(hit.records)
            else:
                missing.append(family_id)
        diagnostics = tuple(f"missing family {family_id}" for family_id in missing)
        digest = records[0].payload_sha256 if len(records) == 1 else None
        return _seal(ProviderHit(tuple(records), digest, diagnostics), self._api_key)

    def _get(self, path: str, expect: str, record_id: str | None = None) -> ProviderHit:
        cached = self._cache.get(path)
        if cached is not None:
            return cached
        now = self._clock.time()
        if not self._breaker.allow(now):
            return _seal(_unavailable("circuit_open"), self._api_key)
        step = self._attempt(path, expect, record_id)
        self._observe(step)
        sealed = _seal(step.hit, self._api_key)
        if step.cacheable and sealed is step.hit:
            self._cache[path] = sealed
        return sealed

    def _attempt(self, path: str, expect: str, record_id: str | None) -> _Step:
        index = 0
        remaining = self.config.max_retries
        while True:
            step = self._exchange(path, expect, record_id)
            if not step.retry:
                return step
            if remaining == 0:
                return _exhausted(step)
            delay = self._delay(index, step.retry_after)
            if delay > 0:
                self._clock.sleep(delay)
            index += 1
            remaining -= 1

    def _exchange(self, path: str, expect: str, record_id: str | None) -> _Step:
        self._rate.acquire()
        try:
            response = self._transport.exchange(
                "GET",
                path,
                _headers(self._api_key),
                self.config.timeouts,
            )
        except TimeoutError:
            return _Step(_unavailable("timeout"), True, True, False, "timeout")
        except OSError:
            return _Step(_unavailable("connection"), True, True, False, "connection")
        return _from_response(response, expect, self._completeness, record_id)

    def _observe(self, step: _Step) -> None:
        if step.failure:
            self._breaker.fail(self._clock.time())
            return
        self._breaker.ok()

    def _delay(self, index: int, retry_after: str | None) -> float:
        parsed = _retry_after_seconds(retry_after)
        if parsed is None:
            parsed = self.config.retry_base_delay * (2**index)
        return float(min(parsed, self.config.retry_max_delay))


def http_adapter_config() -> HttpAdapterConfig:
    """Read the approved adapter block. Missing keys stay an error."""
    block = policy_document()["http_adapter"]
    if not isinstance(block, dict):
        raise ValueError("http_adapter is missing")
    return HttpAdapterConfig(
        timeout_sec=_number(block, "timeout_sec"),
        read_timeout_multiplier=_number(block, "read_timeout_multiplier"),
        max_retries=_number(block, "max_retries"),
        retry_base_delay=_number(block, "retry_base_delay", minimum=0),
        retry_max_delay=_number(block, "retry_max_delay", minimum=0),
        requests_per_second=_number(block, "requests_per_second"),
        burst=_number(block, "burst"),
        failure_threshold=_number(block, "failure_threshold"),
        recovery_timeout=_number(block, "recovery_timeout"),
        version=_text(block, "version"),
        operational_check=_text(block, "operational_check"),
    )


def smoke_status() -> SmokeCheck:
    """Keep the operational check ``NOT_RUN`` until a live run is recorded."""
    config = http_adapter_config()
    return SmokeCheck(config.operational_check, NOT_RUN_REASONS["http_transport"])


def publish_allowed(completeness: Completeness) -> bool:
    """An incomplete snapshot is not published as an updated release."""
    return completeness.complete and completeness.publishable


def hit_status(hit: ProviderHit) -> str:
    """Map one hit to available, not_found, or source_unavailable."""
    if _is_unavailable(hit):
        return "source_unavailable"
    if hit.records:
        return "available"
    return "not_found"


def _headers(api_key: str | None) -> dict[str, str]:
    if not api_key:
        return {}
    return {API_KEY_HEADER: api_key}


def _number(block: Mapping[str, object], name: str, *, minimum: int = 1) -> int:
    value = block.get(name)
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{name} is not approved")
    return value


def _text(block: Mapping[str, object], name: str) -> str:
    value = block.get(name)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} is not approved")
    return value


def _unavailable(code: str) -> ProviderHit:
    return ProviderHit((), None, (f"source_unavailable:{code}",))


def _is_unavailable(hit: ProviderHit) -> bool:
    return any(item.startswith("source_unavailable:") for item in hit.diagnostics)


def _exhausted(step: _Step) -> _Step:
    kept = step.code in {"timeout", "connection"}
    code = step.code if kept else "retries_exhausted"
    return _Step(_unavailable(code), False, True, False, code)


def _from_response(
    response: TransportResponse,
    expect: str,
    completeness: Completeness,
    record_id: str | None,
) -> _Step:
    if response.status_code in RETRYABLE_STATUS:
        return _Step(
            _unavailable(f"http_{response.status_code}"),
            True,
            True,
            False,
            f"http_{response.status_code}",
            response.header("Retry-After"),
        )
    if response.status_code in AUTH_STATUS:
        return _Step(
            _unavailable(f"http_{response.status_code}"),
            False,
            False,
            False,
            f"http_{response.status_code}",
        )
    if response.status_code == 404:
        return _absence(completeness)
    if response.status_code != 200:
        return _Step(
            _unavailable(f"http_{response.status_code}"),
            False,
            False,
            False,
            f"http_{response.status_code}",
        )
    return _parsed(response.body, expect, completeness, record_id)


def _absence(completeness: Completeness) -> _Step:
    if completeness.allows_not_found:
        return _Step(ProviderHit((), None, ()), False, False, False, "not_found")
    return _Step(_unavailable("incomplete"), False, False, False, "incomplete")


def _parsed(
    body: bytes,
    expect: str,
    completeness: Completeness,
    record_id: str | None,
) -> _Step:
    loaded = _load_json(body)
    if isinstance(loaded, str):
        return _Step(_unavailable(loaded), False, False, False, loaded)
    if expect == "search":
        return _parsed_search(loaded, completeness)
    kind = "family" if expect == "family" else "target"
    record = _one_record(loaded, kind, record_id)
    if isinstance(record, str):
        return _Step(_unavailable(record), False, False, False, record)
    hit = ProviderHit((record,), record.payload_sha256, ())
    return _Step(hit, False, False, True, "available")


def _parsed_search(payload: object, completeness: Completeness) -> _Step:
    items = _search_items(payload)
    if isinstance(items, str):
        return _Step(_unavailable(items), False, False, False, items)
    if not items:
        return _absence(completeness)
    records: list[FrozenRecord] = []
    for item in items:
        record = _one_record(item, "target")
        if isinstance(record, str):
            return _Step(_unavailable(record), False, False, False, record)
        records.append(record)
    digest = records[0].payload_sha256 if len(records) == 1 else None
    hit = ProviderHit(tuple(records), digest, ())
    return _Step(hit, False, False, True, "available")


def _load_json(body: bytes) -> object | str:
    if not body.strip():
        return "empty_body"
    try:
        return json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return "bad_json"


def _search_items(payload: object) -> list[object] | str:
    if isinstance(payload, list):
        return list(payload)
    if isinstance(payload, dict) and set(payload) == {"results"}:
        results = payload["results"]
        if isinstance(results, list):
            return list(results)
    return "schema"


def _one_record(
    payload: object,
    kind: str,
    expected_id: str | None = None,
) -> FrozenRecord | str:
    if not isinstance(payload, dict):
        return "schema"
    record_id = payload.get("id")
    if not isinstance(record_id, str) or not record_id:
        return "schema"
    if expected_id is not None and record_id != expected_id:
        return "schema"
    return freeze_record(kind, record_id, payload)


def _retry_after_seconds(value: str | None) -> int | None:
    if value is None:
        return None
    text = value.strip()
    if not text.isdecimal():
        return None
    return int(text)


def _seal(hit: ProviderHit, api_key: str | None) -> ProviderHit:
    if _secret_leaked(hit, api_key):
        return _unavailable("secret")
    return hit


def _secret_leaked(hit: ProviderHit, api_key: str | None) -> bool:
    chunks = list(hit.diagnostics)
    for record in hit.records:
        chunks.append(record.record_id)
        chunks.append(record.payload.decode("utf-8", "replace"))
    rendered = "\n".join(chunks)
    if API_KEY_HEADER in rendered:
        return True
    return bool(api_key) and api_key in rendered
