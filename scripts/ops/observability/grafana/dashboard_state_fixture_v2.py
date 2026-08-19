"""dashboard_state_fixture_v2 loader, digest, and fail-closed compare.

Used by the optional Grafana renderer --fixture-case path (#8984).
Does not change the default live render path.
"""
from __future__ import annotations

import hashlib
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from collections.abc import Mapping
from typing import Any, ClassVar

CONTRACT = "dashboard_state_fixture_v2"
REQUIRED_CASES = (
    "ok",
    "warn",
    "crit",
    "valid_empty",
    "telemetry_absent",
    "backend_error",
)


def canonical_json_sha256(payload: object) -> str:
    text = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_v2_index(index_path: Path) -> dict[str, Any]:
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("fixture v2 index must be a JSON object")
    if payload.get("contract") != CONTRACT:
        raise ValueError(f"fixture index must use {CONTRACT}")
    cases = payload.get("cases")
    if not isinstance(cases, dict) or not cases:
        raise ValueError("fixture v2 index requires a non-empty cases mapping")
    return payload


def load_v2_case(index_path: Path, case_id: str) -> dict[str, Any]:
    index = load_v2_index(index_path)
    meta = index["cases"].get(case_id)
    if not isinstance(meta, dict):
        raise ValueError(f"unknown fixture case {case_id!r}")
    rel = meta.get("path")
    if not isinstance(rel, str) or not rel:
        raise ValueError(f"fixture case {case_id!r} lacks path")
    payload = json.loads(_read_case_file(index_path, rel))
    return validate_v2_case(payload, expected_case_id=case_id)


def _read_case_file(index_path: Path, rel: str) -> str:
    candidates = [
        Path(rel),
        index_path.parent / Path(rel).name,
        Path(__file__).resolve().parents[4] / rel,
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate.read_text(encoding="utf-8")
    raise ValueError(f"fixture case file missing: {rel}")


def validate_v2_case(payload: Mapping[str, Any], *, expected_case_id: str) -> dict[str, Any]:
    if payload.get("contract") != CONTRACT:
        raise ValueError(f"case must use {CONTRACT}")
    case_id = str(payload.get("case_id") or "").strip()
    if case_id != expected_case_id:
        raise ValueError("case_id does not match --fixture-case")
    response = payload.get("datasource_response")
    if not isinstance(response, dict):
        raise ValueError("datasource_response must be a JSON object")
    expected_panels = payload.get("expected_panels")
    if not isinstance(expected_panels, list) or not expected_panels:
        raise ValueError("expected_panels must be a non-empty list")
    tokens = payload.get("expected_copy_tokens")
    if not isinstance(tokens, list) or not all(isinstance(item, str) for item in tokens):
        raise ValueError("expected_copy_tokens must be a list of strings")
    scope = str(payload.get("scope") or "").strip()
    if not scope:
        raise ValueError("scope is required")
    digest = str(payload.get("response_sha256") or "").strip()
    actual = canonical_json_sha256(response)
    if digest != actual:
        raise ValueError("response_sha256 does not match datasource_response")
    http_status = int(payload.get("http_status") or 0)
    if http_status < 100:
        raise ValueError("http_status is required")
    return dict(payload)


def compare_expected_actual(
    expected_panels: list[object],
    actual_panels: Mapping[str, str],
) -> None:
    """Fail closed when expected panel classifications differ from actual."""
    if not actual_panels:
        raise ValueError("actual panel classifications are missing")
    for item in expected_panels:
        if not isinstance(item, dict):
            raise ValueError("expected_panels entries must be objects")
        panel_id = str(item.get("id") or "").strip()
        expected = str(item.get("classification") or "").strip()
        if not panel_id or not expected:
            raise ValueError("expected_panels require id and classification")
        actual = str(actual_panels.get(panel_id) or "").strip()
        if actual != expected:
            raise ValueError(
                f"fixture case mismatch panel {panel_id}: expected {expected}, actual {actual or 'missing'}"
            )


def fixture_case_evidence(case: Mapping[str, Any]) -> dict[str, object]:
    return {
        "contract": CONTRACT,
        "case_id": case["case_id"],
        "http_status": case["http_status"],
        "scope": case["scope"],
        "response_sha256": case["response_sha256"],
        "expected_panels": case["expected_panels"],
        "expected_copy_tokens": case["expected_copy_tokens"],
    }


class _StubHandler(BaseHTTPRequestHandler):
    response_payload: ClassVar[dict[str, Any]] = {}
    status_code: ClassVar[int] = 200

    def log_message(self, _fmt: str, *_args: object) -> None:
        return

    def do_GET(self) -> None:
        body = json.dumps(self.response_payload).encode("utf-8")
        self.send_response(self.status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def start_stub_server(case: Mapping[str, Any], *, host: str = "127.0.0.1", port: int = 0) -> ThreadingHTTPServer:
    _StubHandler.response_payload = dict(case["datasource_response"])
    _StubHandler.status_code = int(case["http_status"])
    server = ThreadingHTTPServer((host, port), _StubHandler)
    return server
