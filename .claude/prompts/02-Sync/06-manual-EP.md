# manual-EP — Manual Endpoint Validation Checklist

*Priority: low | Version: 1.0 | Aligned with RULES.md v5.19*

---

## Goal

Generate a manual validation checklist for API endpoints used by a `{{source}}` adapter, covering URL correctness, pagination behavior, response envelope structure, and rate limiting.

---

## Input

| Parameter | Source | Example |
|-----------|--------|---------|
| `{{source}}` | User argument | `chembl`, `uniprot`, `pubmed` |
| docs API | `docs/04-reference/pipelines/{{provider}}/` or `docs/04-reference/providers/{{provider}}/` | API reference |
| adapter | `src/bioetl/infrastructure/adapters/{{provider}}/client.py` | HTTP adapter code |
| source config | `configs/sources/{{provider}}.yaml` | Source configuration |

---

## Output

Markdown checklist for manual verification.

---

## Algorithm

### 1. Extract endpoint info from adapter code

Parse the adapter client to find:
- Base URL from source config
- Entity-specific URL patterns (path construction)
- Pagination implementation (offset, cursor, page token)
- Response envelope parsing (where data records live in JSON)
- Rate limit handling (headers, backoff)
- Health check endpoint

### 2. Extract from source config

From `configs/sources/{{provider}}.yaml`:
```yaml
source.provider_config.base_url
source.provider_config.page_size
source.rate_limit.requests_per_second
source.rate_limit.burst
source.health_check.endpoint
source.circuit_breaker.*
source.retry.*
```

### 3. Generate checklist

```markdown
## Manual Endpoint Validation: {{source}}

### 1. Base Configuration

| Parameter | Config Value | Verified |
|-----------|-------------|----------|
| Base URL | `{{base_url}}` | [ ] |
| Auth Type | `{{auth_type}}` | [ ] |
| Page Size | `{{page_size}}` | [ ] |
| Rate Limit | `{{rps}} req/s, burst {{burst}}` | [ ] |
| Timeout | `{{timeout}}s` | [ ] |
| Max Retries | `{{max_retries}}` | [ ] |

### 2. Health Check

| Check | Expected | Command | Result |
|-------|----------|---------|--------|
| Endpoint accessible | HTTP 200 | `curl -s -o /dev/null -w "%{http_code}" {{health_url}}` | [ ] |
| Response time | < {{timeout}}s | `curl -s -w "%{time_total}" {{health_url}}` | [ ] |
| Response format | JSON | `curl -s {{health_url}} | python -m json.tool` | [ ] |

### 3. Entity Endpoints

For each entity in `configs/sources/{{provider}}.yaml`:

#### {{entity}}

| Check | Expected | Command | Result |
|-------|----------|---------|--------|
| URL valid | HTTP 200 | `curl -s -o /dev/null -w "%{http_code}" "{{entity_url}}?limit=1"` | [ ] |
| Returns data | Non-empty array | `curl -s "{{entity_url}}?limit=1" | python -c "import json,sys; d=json.load(sys.stdin); print(len(d.get('{{data_key}}', d.get('results', []))))"` | [ ] |
| PK present | `{{primary_key}}` in response | `curl -s "{{entity_url}}?limit=1" | python -c "import json,sys; d=json.load(sys.stdin); print('{{primary_key}}' in d['{{data_key}}'][0])"` | [ ] |

### 4. Pagination

| Check | Expected | Adapter Implementation | Result |
|-------|----------|----------------------|--------|
| Type | `{{pagination_type}}` (offset/cursor/link) | `{{adapter_file}}:{{line}}` | [ ] |
| Next page indicator | `{{next_field}}` | Response field | [ ] |
| Page size respected | Returns ≤ `{{page_size}}` records | Verified with `?limit={{page_size}}` | [ ] |
| Last page detection | `{{last_page_signal}}` | Empty results / null next | [ ] |
| Total count available | `{{total_field}}` if any | Optional | [ ] |

### 5. Response Envelope

| Check | Expected | Adapter Parsing | Result |
|-------|----------|----------------|--------|
| Data path | `{{envelope_path}}` (e.g., `response.results`) | `{{adapter_file}}:{{line}}` | [ ] |
| Record count field | `{{count_field}}` | Optional | [ ] |
| Error format | `{{error_format}}` | Handled in adapter | [ ] |

### 6. Rate Limiting

| Check | Expected | Result |
|-------|----------|--------|
| Retry-After header | `{{retry_after}}` (yes/no) | [ ] |
| Rate limit headers | `{{rate_headers}}` | [ ] |
| Burst handling | `{{burst}}` requests OK | [ ] |
| 429 response | Graceful backoff | [ ] |

### 7. Edge Cases

- [ ] Empty result set (no records match filter)
- [ ] Single record response
- [ ] Maximum page size response
- [ ] Invalid entity/endpoint (expected 404)
- [ ] Malformed query parameter (expected 400)
- [ ] Server error simulation (if testable)
```

---

## Commit & PR Convention (`{{C}}`)

- **Branch:** `qa/{{source}}-ep`
- **PR title:** `qa({{source}}): endpoint validation checklist`
- **Labels:** `qa`

---

## Example

For `chembl`:

```markdown
### 2. Health Check

| Check | Expected | Command | Result |
|-------|----------|---------|--------|
| Endpoint | HTTP 200 | `curl -s -o /dev/null -w "%{http_code}" https://www.ebi.ac.uk/chembl/api/data/status.json` | [ ] |

### 4. Pagination

| Check | Expected | Result |
|-------|----------|--------|
| Type | offset-based | [ ] |
| Next page | `page_meta.next` in response | [ ] |
| Page size | 1000 (config) | [ ] |
| Last page | `page_meta.next = null` | [ ] |
```

---

## Constraints

- Do NOT execute curl commands. This prompt generates the checklist only.
- All URLs must be constructed from source config, not hardcoded.
- If adapter uses a client library (e.g., `chembl_webresource_client`) instead of direct HTTP, note this and adjust verification commands accordingly.
- Rate limit tests should be non-destructive (observe, don't flood).
- Include `[LIBRARY CLIENT]` note if the provider uses a wrapped client rather than raw HTTP.
