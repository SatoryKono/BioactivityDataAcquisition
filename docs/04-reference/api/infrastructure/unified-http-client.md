______________________________________________________________________

# Infrastructure Unified HTTP Client API Leaf

This package leaf points to maintained Infrastructure HTTP client guidance and
the live unified HTTP stack.

- Layer reference: [Infrastructure API](../infrastructure.md)
- Architecture context: [Infrastructure Layer](../../../02-architecture/03-infrastructure-layer.md)
- Source package: `src/bioetl/infrastructure/adapters/http/`
- Import guidance: `UnifiedHTTPClient` is the sanctioned runtime HTTP client
  abstraction; do not document `UnifiedAPIClient` as a new public client.

Request admission and network time are separate. `get_once(request_timeout=...)`
applies its transport deadline after rate-limit admission; ChEMBL health probes
use this deadline without counting local queue time as an upstream timeout.
Semantic Scholar health latency uses the measured transport duration when available.

`http_attempt_completed` records admission and transport seconds, attempt number,
HTTP status, exception type, circuit state, and remaining provider cooldown. It
omits URLs, headers, and bodies. `http_retry_wait` records the planned wait before
sleeping, so cancellation during backoff remains diagnosable.

A 429/503 `Retry-After` applies to subsequent requests on the same client, including
health-to-data transitions. A retry delay exceeding the configured wait budget
terminates the request; the cap must not cause an early retry. The limiter and
cooldown are client-scoped, not a cross-process quota. Run provider diagnostics
serially and account for other active clients before interpreting upstream limits.

This page is intentionally compact. Use source modules for exact signatures.

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-09-25'

______________________________________________________________________
