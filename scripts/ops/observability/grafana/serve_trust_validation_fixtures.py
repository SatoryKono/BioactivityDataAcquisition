"""Serve Trust validation fixtures over HTTP for Grafana Infinity close-ups.

Maps:
  GET /ops/control-plane/{endpoint}?pipeline=...&run_type=...&run_id=...
to fixtures under tests/fixtures/grafana/control_plane_validation/{endpoint}/{state}.json

State selection (first match):
  1. query param ``fixture_state``
  2. env BIOETL_TRUST_FIXTURE_STATE
  3. default ``populated``

HTTP status:
  - service_unavailable → 503
  - others → 200 (backend_error is ERROR in body, not transport failure)

Example:
  python scripts/ops/observability/grafana/serve_trust_validation_fixtures.py --port 18080
  # Point temporary Infinity URL override or local proxy at http://127.0.0.1:18080
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import ClassVar
from urllib.parse import parse_qs, urlparse

DEFAULT_ROOT = Path("tests/fixtures/grafana/control_plane_validation")
ENDPOINTS = {
    "checkpoint-validation",
    "manifest-validation",
    "lineage-validation",
    "retention-compliance",
    "failure-reasons",
}
ALLOWED_STATES = {
    "populated",
    "valid_empty_or_unknown",
    "backend_error",
    "service_unavailable",
    "empty_rows",
}


def _preload_fixtures(root: Path) -> dict[tuple[str, str], dict[str, object]]:
    """Load allowlisted fixture JSON from constant endpoint/state names."""
    loaded: dict[tuple[str, str], dict[str, object]] = {}
    for endpoint in ENDPOINTS:
        for state in ALLOWED_STATES:
            path = root / endpoint / f"{state}.json"
            if not path.is_file():
                continue
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                loaded[(endpoint, state)] = payload
    return loaded


def _validated_loopback_host(value: str) -> str:
    """Permit this HTTP fixture server only on loopback interfaces."""
    host = value.strip().lower()
    if host == "localhost":
        return host
    try:
        address = ipaddress.ip_address(host)
    except ValueError as error:
        raise ValueError(f"fixture host must be loopback: {value!r}") from error
    if not address.is_loopback:
        raise ValueError(f"fixture host must be loopback: {value!r}")
    return host


class FixtureHandler(BaseHTTPRequestHandler):
    fixture_root: Path = DEFAULT_ROOT
    default_state: str = "populated"
    fixtures: ClassVar[dict[tuple[str, str], dict[str, object]]] = {}

    def log_message(self, _fmt: str, *_args: object) -> None:
        # Keep stdout free of secrets; only method + path.
        import sys

        print(f"[fixture] {self.command} {self.path}", file=sys.stderr)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        prefix = "/ops/control-plane/"
        if not path.startswith(prefix):
            self._send(404, {"error": "not_found"})
            return
        endpoint = path[len(prefix) :]
        if endpoint not in ENDPOINTS:
            self._send(404, {"error": "unknown_endpoint"})
            return
        qs = parse_qs(parsed.query)
        active_from_file = ""
        active_file = self.fixture_root / ".active_state"
        if active_file.is_file():
            active_from_file = active_file.read_text(encoding="utf-8").strip()
        raw_state = (
            (qs.get("fixture_state") or [None])[0]
            or os.environ.get("BIOETL_TRUST_FIXTURE_STATE")
            or active_from_file
            or self.default_state
        )
        if raw_state not in ALLOWED_STATES:
            self._send(404, {"error": "unknown_state"})
            return
        fixtures = self.fixtures or _preload_fixtures(self.fixture_root)
        if not self.fixtures:
            FixtureHandler.fixtures = fixtures
        payload = fixtures.get((endpoint, raw_state))
        if payload is None:
            self._send(404, {"error": "fixture_missing"})
            return
        http_status = 503 if raw_state == "service_unavailable" else 200
        stored_status = payload.get("http_status")
        if isinstance(stored_status, int):
            http_status = stored_status
        self._send(http_status, payload)

    def _send(self, status: int, payload: dict[str, object]) -> None:
        body = json.dumps(payload, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18080)
    parser.add_argument("--fixture-root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument(
        "--default-state",
        default=os.environ.get("BIOETL_TRUST_FIXTURE_STATE", "populated"),
        help="Default fixture state when fixture_state query is omitted",
    )
    args = parser.parse_args()
    from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_cli_path

    args.host = _validated_loopback_host(args.host)
    args.fixture_root = resolve_cli_path(args.fixture_root, root=REPO_ROOT)
    if not args.fixture_root.is_dir():
        raise SystemExit(f"fixture root missing: {args.fixture_root}")
    FixtureHandler.fixture_root = args.fixture_root
    FixtureHandler.default_state = args.default_state
    FixtureHandler.fixtures = _preload_fixtures(args.fixture_root)
    server = ThreadingHTTPServer((args.host, args.port), FixtureHandler)
    print(
        f"serving {args.fixture_root} on http://{args.host}:{args.port} "  # NOSONAR -- loopback-only fixture contract
        f"(default_state={args.default_state})",
        flush=True,
    )
    print(
        "example: "
        f"http://{args.host}:{args.port}/ops/control-plane/checkpoint-validation"  # NOSONAR -- loopback-only fixture contract
        f"?pipeline=chembl_activity&run_type=incremental"
        f"&run_id=00000000-0000-0000-0000-000000008576&fixture_state=backend_error",
        flush=True,
    )
    try:
        server.serve_forever()  # NOSONAR -- host is validated as loopback-only above
    except KeyboardInterrupt:
        print("stopped", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
