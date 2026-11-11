"""Single-attempt HTTP MCP probes with bounded reads and an absolute deadline."""

from collections.abc import Mapping
import http.client
import json
import re
import socket
import threading
import time
from urllib.parse import urlsplit

from scripts.ai.codex.mcp_probe_errors import ProbeError, rpc_result

MAX_RESPONSE_BYTES = 1024 * 1024


def _remaining(deadline: float) -> float:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise ProbeError("TIMEOUT", uncertain=True)
    return remaining


def _dial_address(address, source_address, deadline: float):
    family, kind, protocol, _, target = address
    stream = socket.socket(family, kind, protocol)
    try:
        stream.settimeout(_remaining(deadline))
        if source_address:
            stream.bind(source_address)
        stream.connect(target)
        return stream
    except BaseException:
        stream.close()
        raise


def _open_socket(address, source_address, deadline: float):
    host, port = address
    error = OSError("connection address unavailable")
    for item in socket.getaddrinfo(host, port, 0, socket.SOCK_STREAM):
        _remaining(deadline)
        try:
            return _dial_address(item, source_address, deadline)
        except OSError as exc:
            error = exc
    raise error


def _connect_before_deadline(connection, deadline: float) -> None:
    """Bound DNS, address attempts and TLS without a late protocol request."""
    finished = threading.Event()
    cancelled = threading.Event()
    errors = []
    connection._create_connection = lambda address, _timeout, source_address: (
        _open_socket(address, source_address, deadline)
    )

    def connect():
        try:
            connection.connect()
        except Exception as exc:
            errors.append(exc)
        finally:
            if cancelled.is_set():
                connection.close()
            finished.set()

    worker = threading.Thread(target=connect, daemon=True)
    worker.start()
    if not finished.wait(max(0.0, deadline - time.monotonic())):
        cancelled.set()
        connection.close()
        raise ProbeError("TIMEOUT", uncertain=True)
    if errors:
        raise errors[0]
    _remaining(deadline)


class _SocketDeadline:
    """Interrupt only this request's owned socket, including a partial line."""

    def __init__(self, stream_socket, deadline: float):
        self.socket = stream_socket
        self.deadline = deadline
        self.timer = threading.Timer(_remaining(deadline), self._interrupt)
        self.timer.daemon = True

    def _interrupt(self):
        try:
            self.socket.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass

    def __enter__(self):
        self.timer.start()
        return self

    def before_read(self):
        self.socket.settimeout(_remaining(self.deadline))

    def __exit__(self, *_):
        self.timer.cancel()


def _http_message(raw: bytes) -> dict:
    text = raw.decode("utf-8")
    if text.lstrip().startswith("{"):
        value = json.loads(text)
    else:
        value = json.loads(
            "\n".join(
                line[5:].strip()
                for line in text.splitlines()
                if line.startswith("data:")
            )
        )
    if not isinstance(value, dict):
        raise ProbeError("INVALID_RESPONSE")
    return value


def _sse_response(buffer: bytearray) -> bytes | None:
    while match := re.search(rb"\r?\n\r?\n", buffer):
        event = bytes(buffer[: match.start()])
        del buffer[: match.end()]
        if b"data:" in event and "id" in _http_message(event):
            return event
    return None


def _read_http_reply(response, timeout: float, *, guard=None) -> bytes:
    deadline = guard.deadline if guard else time.monotonic() + timeout
    event_stream = "text/event-stream" in response.headers.get("Content-Type", "")
    buffer = bytearray()
    total = 0
    while True:
        _remaining(deadline)
        if guard:
            guard.before_read()
        # read1 performs at most one underlying system call; the watchdog also
        # interrupts slow chunk headers and other buffered partial-line reads.
        chunk = response.read1(min(65536, MAX_RESPONSE_BYTES + 1 - total))
        _remaining(deadline)
        total += len(chunk)
        if total > MAX_RESPONSE_BYTES:
            raise ProbeError("RESPONSE_LIMIT", uncertain=True)
        buffer.extend(chunk)
        if event_stream:
            event = _sse_response(buffer)
            if event is not None:
                return event
        if not chunk or getattr(response, "isclosed", lambda: False)():
            return bytes(buffer)


class HttpProbeClient:
    """Own each HTTP connection; never redirect, replay, or DELETE a session."""

    def __init__(self, entry: Mapping, workspace, environment: Mapping[str, str]):
        del workspace
        self.url = urlsplit(str(entry["url"]))
        if self.url.scheme not in {"http", "https"} or not self.url.hostname:
            raise ProbeError("UNSUPPORTED_HTTP_URL")
        if self.url.username or self.url.password or entry.get("http_headers_helper"):
            raise ProbeError("AUTH_HELPER_NOT_TESTED")
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        self.headers.update(entry.get("http_headers") or {})
        for key, reference in (entry.get("env_http_headers") or {}).items():
            if not environment.get(reference):
                raise ProbeError("AUTH_REFERENCE_UNAVAILABLE")
            self.headers[key] = environment[reference]
        reference = entry.get("bearer_token_env_var")
        if reference:
            if not environment.get(reference):
                raise ProbeError("AUTH_REFERENCE_UNAVAILABLE")
            self.headers["Authorization"] = "Bearer " + environment[reference]
        self._identifier = 0
        self._last_deadline = 0.0
        self.transport_seen = False

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def _exchange(
        self, connection, payload: dict, deadline: float, notification: bool
    ) -> dict:
        _connect_before_deadline(connection, deadline)
        if connection.sock is None:
            raise ProbeError("CONNECTION_UNAVAILABLE", uncertain=True)
        with _SocketDeadline(connection.sock, deadline) as guard:
            guard.before_read()
            target = self.url.path or "/"
            if self.url.query:
                target += "?" + self.url.query
            connection.request(
                "POST", target, body=json.dumps(payload).encode(), headers=self.headers
            )
            guard.before_read()
            with connection.getresponse() as response:
                _remaining(deadline)
                if response.status in (401, 403):
                    raise ProbeError("AUTH_ERROR")
                if not 200 <= response.status < 300:
                    raise ProbeError("HTTP_ERROR")
                session = response.headers.get("Mcp-Session-Id")
                if session:
                    self.headers["Mcp-Session-Id"] = session
                if notification and response.status in (200, 202, 204):
                    return {}
                raw = _read_http_reply(response, _remaining(deadline), guard=guard)
        return _http_message(raw)

    def _post(
        self, payload: dict, timeout: float, *, notification: bool = False
    ) -> dict:
        deadline = time.monotonic() + timeout
        connection_type = (
            http.client.HTTPSConnection
            if self.url.scheme == "https"
            else http.client.HTTPConnection
        )
        connection = connection_type(
            self.url.hostname, self.url.port, timeout=_remaining(deadline)
        )
        try:
            result = self._exchange(connection, payload, deadline, notification)
            _remaining(deadline)
            return result
        except (TimeoutError, OSError, http.client.HTTPException):
            raise ProbeError("TIMEOUT_OR_CONNECTION", uncertain=True) from None
        except (ValueError, UnicodeError):
            raise ProbeError("INVALID_RESPONSE", uncertain=True) from None
        finally:
            connection.close()

    def request(self, method: str, params: dict, timeout: float) -> dict:
        # The initialized notification shares initialize's remaining budget.
        self._identifier += 1
        self._last_deadline = time.monotonic() + timeout
        value = self._post(
            {
                "jsonrpc": "2.0",
                "id": self._identifier,
                "method": method,
                "params": params,
            },
            _remaining(self._last_deadline),
        )
        self.transport_seen = True
        if value.get("id") != self._identifier:
            raise ProbeError("RESPONSE_ID_MISMATCH", uncertain=True)
        result = rpc_result(value)
        if method == "initialize" and isinstance(result.get("protocolVersion"), str):
            self.headers["MCP-Protocol-Version"] = result["protocolVersion"]
        return result

    def notify_initialized(self):
        self._post(
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            _remaining(self._last_deadline),
            notification=True,
        )
