"""One explicitly anonymous, bounded VCR capture; never replace a fixture."""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx
import vcr
import yaml

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
from tests.helpers.vcr_config import build_base_vcr_config
from bioetl.infrastructure.adapters.semanticscholar.request_headers import build_semanticscholar_headers

OUT = Path(__file__).parent
fixture = ROOT / "tests/fixtures/vcr/semanticscholar/TestSemanticScholarAdapterIntegration.test_fetch_with_query.yaml"
meta = fixture.with_name(fixture.stem + "_meta.yaml")
old = yaml.safe_load(fixture.read_text(encoding="utf-8"))
request = old["interactions"][0]["request"]
now = datetime.now(timezone.utc)
previous = datetime.fromisoformat("2026-10-06T11:41:23.954386+00:00")
assert (now - previous).total_seconds() >= 3600, "Owner cooldown not expired"
assert request["method"] == "GET"
assert request["uri"].startswith("https://api.semanticscholar.org/graph/v1/paper/search?")
assert not (OUT / "capture.yaml").exists(), "Refusing duplicate attempt"
sensitive = {"authorization", "proxy-authorization", "x-api-key", "api-key", "x-auth-token", "cookie", "set-cookie"}
config = build_base_vcr_config(record_mode="all", decode_compressed_response=True, filter_headers=sorted(sensitive), filter_query_parameters=["api_key", "apikey", "key", "token"])
response_filter = config["before_record_response"]
def sanitize_response(response):
    response["headers"] = {k: v for k, v in response["headers"].items() if k.lower() not in sensitive}
    return response_filter(response)
config["before_record_response"] = sanitize_response
headers = build_semanticscholar_headers("", include_content_type=True, skip_placeholder_api_key=True)
receipt = {
    "source_sha": "a36c17b3fb1aace4bd45c666f3b79b05f49da449",
    "requested_at": now.isoformat(),
    "method": request["method"], "uri": request["uri"],
    "previous_requested_at": previous.isoformat(),
    "previous_status": 429, "previous_retry_after": None,
    "elapsed_seconds": (now - previous).total_seconds(),
    "authenticated": False, "secrets_read": False,
    "record_mode": "all", "timeout_seconds": 5, "retries": 0,
    "follow_redirects": False, "user_agent": headers["User-Agent"],
    "fixture_sha256_before": hashlib.sha256(fixture.read_bytes()).hexdigest(),
    "sidecar_sha256_before": hashlib.sha256(meta.read_bytes()).hexdigest(),
}
try:
    with httpx.Client(timeout=5, follow_redirects=False) as client:
        with vcr.VCR(**config).use_cassette(str(OUT / "capture.yaml")):
            response = client.request(request["method"], request["uri"], headers=headers, content=request["body"])
    receipt.update(status_code=response.status_code, retry_after=response.headers.get("retry-after"), response_date=response.headers.get("date"))
    (OUT / "response.bin").write_bytes(response.content)
    receipt["response_sha256"] = hashlib.sha256(response.content).hexdigest()
    recorded = yaml.safe_load((OUT / "capture.yaml").read_text(encoding="utf-8"))
    item = recorded["interactions"][0]
    body = item["response"]["body"]["string"]
    body_bytes = body.encode("utf-8") if isinstance(body, str) else body
    assert body_bytes == response.content, "Captured response body differs"
    assert len(recorded["interactions"]) == 1
    assert not any(k.lower() in sensitive for side in ("request", "response") for k in item[side]["headers"])
    receipt["sensitive_headers_absent"] = True
    receipt["capture_body_matches_response"] = True
    receipt["capture_sha256"] = hashlib.sha256((OUT / "capture.yaml").read_bytes()).hexdigest()
    receipt["result"] = "candidate_needs_validation" if response.status_code == 200 else "blocked_http_status"
except Exception as exc:
    receipt["error_type"] = type(exc).__name__
    receipt["result"] = "blocked_capture_error"
receipt["completed_at"] = datetime.now(timezone.utc).isoformat()
receipt["fixture_unchanged"] = hashlib.sha256(fixture.read_bytes()).hexdigest() == receipt["fixture_sha256_before"]
receipt["sidecar_unchanged"] = hashlib.sha256(meta.read_bytes()).hexdigest() == receipt["sidecar_sha256_before"]
(OUT / "summary.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
print(json.dumps(receipt, indent=2))
