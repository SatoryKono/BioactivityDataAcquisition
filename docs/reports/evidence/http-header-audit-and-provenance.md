# HTTP Header Audit & Provenance Note (Issue #12065, #12037)

## Provenance of VCR Cassettes (ChEMBL Replay Harness)
The existing ChEMBL replay seam (`_ReplayChemblHTTPClient`) is synthetic. It records request URLs and parameters, discards supplied headers, and creates synthetic deterministic responses for tests. The origin of the historical cassettes can only be established via real capture records; any cassettes without such verified origin are considered UNKNOWN provenance. We cannot attribute all legacy cassettes to a specific harness based on a single generic User-Agent.

## Consumer Audit
| Header | Consumer | Semantic Role | Action | Evidence |
|---|---|---|---|---|
| `Date` | None | None | keep/unknown | No direct code consumer found. |
| `Expires` | None | None | keep/unknown | No direct code consumer found. |
| `x-throttling-control` | None | None | keep/unknown | No direct code consumer found. |
| `x-chembl-retrieval-time` | None | None | keep/unknown | No direct code consumer found. |
| `Retry-After` | `_parse_float_header` in `api_request_collector.py`, `parse_retry_after` in `client_retry_policy.py` via `_client_retry_flow.py` and `request_timing.py` | Protocol-level pacing & delay telemetry | keep | Read from `response.headers.get("Retry-After")`. Used for backoff limits and retry scheduling. |
| `X-RateLimit-Reset` | `_parse_reset_header` in `api_request_collector.py` | Rate limit reset tracking | keep | Read from `response.headers.get("X-RateLimit-Reset")`. Used for API limits observability. |
| `ncbi-sid` | `CANONICAL_FILTER_HEADERS` in `vcr_config.py` | Secret/session ID | remove | Case-insensitive removal via `_build_before_record_response_filter`. |
| `ncbi-phid` | `CANONICAL_FILTER_HEADERS` in `vcr_config.py` | Secret/session ID | remove | Case-insensitive removal via `_build_before_record_response_filter`. |
| `set-cookie2` | `CANONICAL_RESPONSE_FILTER_HEADERS` in `vcr_config.py` | Auth token/session | remove | Case-insensitive removal via `_build_before_record_response_filter`. |

> Note: The absence of a remote search result does not prove absence of a consumer. Headers marked as `keep/unknown` are preserved safely.
