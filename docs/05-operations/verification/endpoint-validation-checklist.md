______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-08-09'

______________________________________________________________________

# Manual Endpoint Validation Checklists

> **Status:** Historical verification artifact (non-normative).
> Use this report as dated evidence only; current policy source of truth is `docs/00-project/RULES.md` and active ADRs.

*Generated: 2026-02-17 | Prompt 6 (manual-EP) sync workflow*

Quick-reference validation checklists for all 7 BioETL data providers.
Each section covers base configuration, health check, pagination, retry,
and sample curl commands extracted from `configs/providers/{provider}.yaml`
and `src/bioetl/infrastructure/adapters/{provider}/` source code.

______________________________________________________________________

## Table of Contents

1. [ChEMBL](#1-chembl)
1. [CrossRef](#2-crossref)
1. [OpenAlex](#3-openalex)
1. [PubChem](#4-pubchem)
1. [PubMed](#5-pubmed)
1. [Semantic Scholar](#6-semantic-scholar)
1. [UniProt](#7-uniprot)

______________________________________________________________________

## 1. ChEMBL

**Source config:** `configs/providers/chembl.yaml`
**Adapter code:** `src/bioetl/infrastructure/adapters/chembl/client.py`
**API Docs:** https://www.ebi.ac.uk/chembl/ws

### Base Configuration

| Parameter         | Value                                   |
| ----------------- | --------------------------------------- |
| Base URL          | `https://www.ebi.ac.uk/chembl/api/data` |
| Auth Type         | `public` (no authentication required)   |
| Rate Limit        | 3 req/sec, burst 10                     |
| Page Size         | 1000 records/page (paginated queries)   |
| Filter Batch Size | 20 IDs per filtered API request         |
| Timeout           | 60.0 sec                                |
| Max Retries       | 3                                       |
| Max URL Length    | 2000 chars                              |
| API Version       | None (unversioned)                      |
| Data License      | CC BY-SA 3.0                            |

### Health Check

- [ ] `curl -s -o /dev/null -w "%{http-code}" "https://www.ebi.ac.uk/chembl/api/data/status"` returns 200
- [ ] Response JSON contains `{"status": "UP"}` (adapter returns HEALTHY)
- [ ] Response time < 5 sec (otherwise DEGRADED)

```bash
# Full health check with response body inspection
curl -s "https://www.ebi.ac.uk/chembl/api/data/status?format=json" | python3 -m json.tool
```

### Pagination

| Type                                     | Next Indicator                 | Last Page Signal           |
| ---------------------------------------- | ------------------------------ | -------------------------- |
| Offset-based (`limit` + `offset` params) | `page-meta.next` is not `null` | `page-meta.next` is `null` |

**Response envelope:**

```
{
  "page-meta": {
    "limit": 1000,
    "offset": 0,
    "total-count": 20000000,
    "next": "/chembl/api/data/activity?limit=1000&offset=1000",
    "previous": null
  },
  "<entity-plural-key>": [ ... records ... ]
}
```

**Non-paginated entities:** `target`, `target-component`, `protein-class` (all records returned in single response).

### Retry & Circuit Breaker

| Parameter                         | Value                                                |
| --------------------------------- | ---------------------------------------------------- |
| `use-retry-after`                 | `false` (ChEMBL does not return Retry-After headers) |
| Circuit Breaker Failure Threshold | 5                                                    |
| Circuit Breaker Recovery Timeout  | 300 sec                                              |

### Validation Commands

```bash
# 1. Health check
curl -s "https://www.ebi.ac.uk/chembl/api/data/status?format=json"

# 2. Fetch first page of activities (limit=5 for validation)
curl -s "https://www.ebi.ac.uk/chembl/api/data/activity?format=json&limit=5&offset=0" | python3 -c "
import json, sys; d=json.load(sys.stdin)
print('Records:', len(d.get('activities',[])))
print('Total:', d.get('page-meta',{}).get('total-count'))
print('Has next:', d.get('page-meta',{}).get('next') is not None)
"

# 3. Entity count check
curl -s "https://www.ebi.ac.uk/chembl/api/data/molecule?format=json&limit=1" | python3 -c "
import json, sys; d=json.load(sys.stdin)
print('molecule total-count:', d.get('page-meta',{}).get('total-count'))
"

# 4. Filtered query (by ChEMBL ID)
curl -s "https://www.ebi.ac.uk/chembl/api/data/molecule?format=json&molecule-chembl-id--in=CHEMBL25,CHEMBL59" | python3 -c "
import json, sys; d=json.load(sys.stdin)
print('Records:', len(d.get('molecules',[])))
"
```

### Checklist

- [ ] Health endpoint returns 200 with `status: UP`
- [ ] Paginated fetch returns `page-meta` with `total-count`
- [ ] `page-meta.next` is populated when more pages exist
- [ ] `format=json` parameter is respected
- [ ] Filter `--in` operator works for batch ID lookups
- [ ] Non-paginated entities (target, protein-class) return all records without limit/offset

______________________________________________________________________

## 2. CrossRef

**Source config:** `configs/providers/crossref.yaml`
**Adapter code:** `src/bioetl/infrastructure/adapters/crossref/client.py`
**API Docs:** https://api.crossref.org/swagger-ui/

### Base Configuration

| Parameter         | Value                                             |
| ----------------- | ------------------------------------------------- |
| Base URL          | `https://api.crossref.org`                        |
| Auth Type         | `email` (polite pool via `mailto` parameter)      |
| Rate Limit        | 50 req/sec (polite pool), burst 100               |
| Polite Pool       | `true` (requires `BIOETL_CROSSREF_EMAIL` env var) |
| Batch Size        | 50 DOIs per batch                                 |
| Cursor Pagination | `true`                                            |
| Timeout           | 30.0 sec                                          |
| Max Retries       | 3                                                 |
| Data License      | CC0 metadata                                      |

### Health Check

- [ ] `curl -s -o /dev/null -w "%{http-code}" "https://api.crossref.org/works?rows=1"` returns 200
- [ ] Response time < 5 sec (>5 sec triggers DEGRADED in adapter)

```bash
# Health check with polite pool identification
curl -s -H "User-Agent: BioETL/1.0 (mailto:your@email.com)" \
  "https://api.crossref.org/works?rows=1&mailto=your@email.com" | python3 -c "
import json, sys; d=json.load(sys.stdin)
print('Status:', d.get('status'))
print('Total results:', d.get('message',{}).get('total-results'))
"
```

### Pagination

| Type                          | Next Indicator                | Last Page Signal         |
| ----------------------------- | ----------------------------- | ------------------------ |
| Cursor-based (`cursor` param) | `message.next-cursor` present | `message.items` is empty |

**Response envelope:**

```
{
  "status": "ok",
  "message": {
    "total-results": 150000000,
    "items": [ ... records ... ],
    "next-cursor": "AoJ..."
  }
}
```

**DOI resolution:** Individual works are fetched via `GET /works/{doi}` returning the record directly under `message`.

### Retry & Circuit Breaker

| Parameter                         | Value                                        |
| --------------------------------- | -------------------------------------------- |
| `use-retry-after`                 | `true` (CrossRef returns Retry-After on 429) |
| Circuit Breaker Failure Threshold | 5                                            |
| Circuit Breaker Recovery Timeout  | 300 sec                                      |

### Validation Commands

```bash
# 1. Health check (polite pool)
curl -s "https://api.crossref.org/works?rows=1&mailto=your@email.com" \
  -H "User-Agent: BioETL/1.0 (mailto:your@email.com)" | python3 -c "
import json, sys; d=json.load(sys.stdin)
print('Status:', d.get('status'))
"

# 2. Single DOI resolution
curl -s "https://api.crossref.org/works/10.1038/nature12373" | python3 -c "
import json, sys; d=json.load(sys.stdin)
msg = d.get('message', {})
print('Title:', msg.get('title', ['N/A'])[0])
print('DOI:', msg.get('DOI'))
"

# 3. Cursor-based search
curl -s "https://api.crossref.org/works?query=pharmacogenomics&rows=5&cursor=*&mailto=your@email.com" | python3 -c "
import json, sys; d=json.load(sys.stdin)
msg = d.get('message', {})
print('Items:', len(msg.get('items', [])))
print('Next cursor:', msg.get('next-cursor', 'N/A')[:20], '...')
"
```

### Checklist

- [ ] Health endpoint `/works?rows=1` returns 200 with `status: ok`
- [ ] DOI resolution via `/works/{doi}` returns the correct publication
- [ ] Cursor pagination returns `next-cursor` in `message`
- [ ] Polite pool is activated (check `User-Agent` header with `mailto:`)
- [ ] Retry-After header is respected on 429 responses

______________________________________________________________________

## 3. OpenAlex

**Source config:** `configs/providers/openalex.yaml`
**Adapter code:** `src/bioetl/infrastructure/adapters/openalex/client.py`
**API Docs:** https://developers.openalex.org

### Base Configuration

| Parameter         | Value                                             |
| ----------------- | ------------------------------------------------- |
| Base URL          | `https://api.openalex.org`                        |
| Auth Type         | API key via `BIOETL_OPENALEX_API_KEY`             |
| Rate Limit        | 10 req/sec with credit-model headers, burst 20    |
| Attribution       | `BIOETL_OPENALEX_EMAIL` optional contact metadata |
| Batch Size        | 50 DOIs per batch                                 |
| Cursor Pagination | `true`                                            |
| Timeout           | 30.0 sec                                          |
| Max Retries       | 3                                                 |
| Data License      | CC0 (Public Domain)                               |

### Health Check

- [ ] `curl -s -o /dev/null -w "%{http-code}" "https://api.openalex.org/works?per-page=1"` returns 200
- [ ] Response time < 5 sec (>5 sec triggers DEGRADED)

```bash
# Health check with API key; optional mailto is attribution only
curl -s "https://api.openalex.org/works?per-page=1&api_key=${BIOETL_OPENALEX_API_KEY}&mailto=${BIOETL_OPENALEX_EMAIL:-}" | python3 -c "
import json, sys; d=json.load(sys.stdin)
print('Count:', d.get('meta',{}).get('count'))
print('Results:', len(d.get('results', [])))
"
```

### Pagination

| Type                                       | Next Indicator                   | Last Page Signal             |
| ------------------------------------------ | -------------------------------- | ---------------------------- |
| Cursor-based (`cursor` param, initial `*`) | `meta.next-cursor` is not `null` | `meta.next-cursor` is `null` |

**Response envelope:**

```
{
  "meta": {
    "count": 250000000,
    "db-response-time-ms": 50,
    "page": 1,
    "per-page": 50,
    "next-cursor": "IlsxNjk..."
  },
  "results": [ ... records ... ]
}
```

**DOI batch lookup:** Uses `filter=doi:doi1|doi2|doi3` (pipe-separated) with `per-page=N`.

### Retry & Circuit Breaker

| Parameter                         | Value   |
| --------------------------------- | ------- |
| `use-retry-after`                 | `true`  |
| Circuit Breaker Failure Threshold | 5       |
| Circuit Breaker Recovery Timeout  | 300 sec |

### Validation Commands

```bash
# 1. Health check
curl -s "https://api.openalex.org/works?per-page=1&api_key=${BIOETL_OPENALEX_API_KEY}&mailto=${BIOETL_OPENALEX_EMAIL:-}" | python3 -c "
import json, sys; d=json.load(sys.stdin)
print('Status OK:', d.get('meta') is not None)
"

# 2. Batch DOI lookup (pipe-separated)
curl -s "https://api.openalex.org/works?filter=doi:10.1038/nature12373|10.1126/science.1247005&per-page=10&api_key=${BIOETL_OPENALEX_API_KEY}&mailto=${BIOETL_OPENALEX_EMAIL:-}" | python3 -c "
import json, sys; d=json.load(sys.stdin)
for r in d.get('results', []):
    print(r.get('doi'), '-', r.get('title','N/A')[:60])
"

# 3. Cursor pagination
curl -s "https://api.openalex.org/works?search=pharmacogenomics&cursor=*&per-page=5&api_key=${BIOETL_OPENALEX_API_KEY}&mailto=${BIOETL_OPENALEX_EMAIL:-}" | python3 -c "
import json, sys; d=json.load(sys.stdin)
meta = d.get('meta', {})
print('Results:', len(d.get('results', [])))
print('Next cursor:', meta.get('next-cursor', 'N/A')[:20], '...')
"

# 4. Title search
curl -s "https://api.openalex.org/works?filter=title.search:aspirin+anti+inflammatory&per-page=3&api_key=${BIOETL_OPENALEX_API_KEY}&mailto=${BIOETL_OPENALEX_EMAIL:-}" | python3 -c "
import json, sys; d=json.load(sys.stdin)
for r in d.get('results', []):
    print(r.get('title','N/A')[:80])
"
```

### Checklist

- [ ] Health endpoint `/works?per-page=1` returns 200 with `meta` block
- [ ] Batch DOI filter `filter=doi:id1|id2` returns matched results
- [ ] Cursor pagination returns `meta.next-cursor` for continuation
- [ ] Title search via `filter=title.search:...` returns results
- [ ] API key is sent via `api_key`; optional `mailto` remains attribution-only
- [ ] Retry-After header is respected on 429 responses

______________________________________________________________________

## 4. PubChem

**Source config:** `configs/providers/pubchem.yaml`
**Adapter code:** `src/bioetl/infrastructure/adapters/pubchem/client.py`
**API Docs:** https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest

### Base Configuration

| Parameter    | Value                                       |
| ------------ | ------------------------------------------- |
| Base URL     | `https://pubchem.ncbi.nlm.nih.gov/rest/pug` |
| Auth Type    | `public` (no authentication required)       |
| Rate Limit   | 5.0 req/sec, burst 10                       |
| Batch Size   | 50                                          |
| Timeout      | 30.0 sec                                    |
| Max Retries  | 3                                           |
| Data License | Public Domain                               |

### Health Check

- [ ] Lightweight compound query for water (CID 962) returns valid data
- [ ] Health check timeout: 10 sec (from YAML)

```bash
# Health check: fetch water compound (CID 962)
curl -s "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/962/property/MolecularFormula/JSON" | python3 -c "
import json, sys; d=json.load(sys.stdin)
props = d.get('PropertyTable',{}).get('Properties',[])
print('CID:', props[0].get('CID') if props else 'N/A')
print('Formula:', props[0].get('MolecularFormula') if props else 'N/A')
"
```

### Pagination

| Type                                     | Next Indicator | Last Page Signal |
| ---------------------------------------- | -------------- | ---------------- |
| No pagination (uses `pubchempy` library) | N/A            | N/A              |

**Note:** PubChem adapter uses the `pubchempy` Python library (synchronous), which wraps
PUG REST API calls. Responses are returned as compound objects, not paginated JSON.
Fetch strategies include SMILES-based search, CID-based lookup, and InChIKey lookup.

### Retry & Circuit Breaker

| Parameter                         | Value                                       |
| --------------------------------- | ------------------------------------------- |
| `use-retry-after`                 | `true` (PubChem returns Retry-After on 429) |
| Circuit Breaker Failure Threshold | 5                                           |
| Circuit Breaker Recovery Timeout  | 300 sec                                     |

### Validation Commands

```bash
# 1. Health check (CID 962 = water)
curl -s "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/962/property/MolecularFormula,MolecularWeight,CanonicalSMILES/JSON"

# 2. Search by compound name
curl -s "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/aspirin/property/MolecularFormula,CanonicalSMILES/JSON" | python3 -c "
import json, sys; d=json.load(sys.stdin)
props = d.get('PropertyTable',{}).get('Properties',[])
for p in props[:3]:
    print(f\"CID: {p.get('CID')}, SMILES: {p.get('CanonicalSMILES')}\")
"

# 3. Batch CID lookup
curl -s "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/2244,3672/property/MolecularFormula,CanonicalSMILES/JSON"

# 4. SMILES-based search
curl -s "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/smiles/CC(%3DO)OC1%3DCC%3DCC%3DC1C(%3DO)O/property/MolecularFormula/JSON"

# 5. Rate limit test (should return 429 if exceeded)
for i in $(seq 1 10); do
  curl -s -o /dev/null -w "%{http-code}\n" "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/962/property/MolecularFormula/JSON"
done
```

### Checklist

- [ ] Health endpoint (CID 962 lookup) returns valid compound data
- [ ] Name-based search returns expected compounds
- [ ] CID batch lookup returns matching records
- [ ] SMILES-based search returns compound properties
- [ ] Rate limit (5 req/sec) is enforced, 429 returned on excess
- [ ] Retry-After header is present in 429 responses

______________________________________________________________________

## 5. PubMed

**Source config:** `configs/providers/pubmed.yaml`
**Adapter code:** `src/bioetl/infrastructure/adapters/pubmed/adapter.py`
**API Docs:** https://www.ncbi.nlm.nih.gov/books/NBK25500/

### Base Configuration

| Parameter             | Value                                                                       |
| --------------------- | --------------------------------------------------------------------------- |
| Base URL              | `https://eutils.ncbi.nlm.nih.gov/entrez/eutils`                             |
| Auth Type             | `api-key` (optional, via `BIOETL_PUBMED_API_KEY` env var)                   |
| Email                 | Optional (`BIOETL_PUBMED_EMAIL`; empty unless set, adapter returns `None`) |
| Rate Limit (no key)   | 3.0 req/sec, burst 5                                                        |
| Rate Limit (with key) | 10 req/sec, burst 20                                                        |
| Batch Size            | 200 PMIDs per efetch request                                                |
| Timeout               | 60.0 sec                                                                    |
| Max Retries           | 3                                                                           |
| Data License          | Public Domain (US Government)                                               |

### Health Check

- [ ] `curl -s -o /dev/null -w "%{http-code}" "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/einfo.fcgi?db=pubmed&retmode=json&email=test@example.com"` returns 200
- [ ] Health check timeout: 10 sec (from YAML)
- [ ] Response time < 5 sec (>5 sec triggers DEGRADED)

```bash
# Health check: einfo endpoint (lightweight, no search)
curl -s "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/einfo.fcgi?db=pubmed&retmode=json&email=test@example.com" | python3 -c "
import json, sys; d=json.load(sys.stdin)
result = d.get('einforesult',{}).get('dbinfo',{})
if isinstance(d, dict) and 'einforesult' in d:
    print('DB info available: OK')
else:
    print('Response:', list(d.keys()))
"
```

### Pagination

| Type                                                  | Next Indicator                 | Last Page Signal    |
| ----------------------------------------------------- | ------------------------------ | ------------------- |
| Two-phase: esearch (get PMIDs) + efetch (get records) | esearch returns full PMID list | All PMIDs processed |

**Search phase (`esearch.fcgi`):**

```
Response: { "esearchresult": { "idlist": ["12345", "67890", ...], "count": "500" } }
```

**Fetch phase (`efetch.fcgi`):**

```
Params: db=pubmed, id=PMID1,PMID2,..., retmode=xml, rettype=abstract
Response: XML (PubmedArticleSet) parsed by PubMedXmlProcessor
```

Records are fetched in batches of 200 PMIDs per efetch request.

### Retry & Circuit Breaker

| Parameter                         | Value   |
| --------------------------------- | ------- |
| `use-retry-after`                 | `true`  |
| Circuit Breaker Failure Threshold | 5       |
| Circuit Breaker Recovery Timeout  | 300 sec |

### Validation Commands

```bash
# 1. Health check (einfo)
curl -s "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/einfo.fcgi?db=pubmed&retmode=json&email=test@example.com"

# 2. Search for PMIDs
curl -s "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=pharmacogenomics&retmax=5&retmode=json&email=test@example.com" | python3 -c "
import json, sys; d=json.load(sys.stdin)
result = d.get('esearchresult', {})
print('Count:', result.get('count'))
print('IDs:', result.get('idlist', []))
"

# 3. Fetch article by PMID (XML)
curl -s "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=33826699&retmode=xml&rettype=abstract&email=test@example.com" | head -20

# 4. Rate limit validation (with API key)
curl -s -o /dev/null -w "%{http-code}" \
  "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=test&retmax=1&retmode=json&email=test@example.com&api-key=YOUR-KEY"
```

### Checklist

- [ ] Health endpoint `einfo.fcgi?db=pubmed` returns 200
- [ ] esearch returns `idlist` with valid PMIDs for known queries
- [ ] efetch returns well-formed XML (`PubmedArticleSet`)
- [ ] Email parameter is included in all requests
- [ ] API key (when provided) increases rate limit to 10 req/sec
- [ ] Retry-After header is respected on 429 responses

______________________________________________________________________

## 6. Semantic Scholar

**Source config:** `configs/providers/semanticscholar.yaml`
**Adapter code:** `src/bioetl/infrastructure/adapters/semanticscholar/adapter.py`
**API Docs:** https://api.semanticscholar.org/api-docs/

### Base Configuration

| Parameter             | Value                                                    |
| --------------------- | -------------------------------------------------------- |
| Base URL              | `https://api.semanticscholar.org/graph/v1`               |
| Auth Type             | `api-key` (via `BIOETL_SEMANTICSCHOLAR_API_KEY` env var) |
| Rate Limit (no key)   | 0.1 req/sec (1 per 10 sec), burst 1                      |
| Rate Limit (with key) | 1.0 req/sec, burst 5                                     |
| Sliding Window        | 300 sec (5-minute window)                                |
| Batch Size            | 100 (adapter default, 50 in config for safety)           |
| Page Size             | 100                                                      |
| Timeout               | 60.0 sec                                                 |
| Max Retries           | 5                                                        |
| Retry Base Delay      | 30.0 sec                                                 |
| Retry Max Delay       | 300.0 sec (5 min)                                        |
| Data License          | Semantic Scholar Dataset License                         |

### Health Check

- [ ] `curl -s -o /dev/null -w "%{http-code}" "https://api.semanticscholar.org/graph/v1/paper/search?query=test&limit=1&fields=paperId"` returns 200
- [ ] Health check timeout: 30 sec
- [ ] Response 429 returns DEGRADED (not UNHEALTHY) -- rate limiting is expected without API key
- [ ] `skip-on-429: true` in YAML config

```bash
# Health check (may return 429 without API key)
curl -s -w "\nHTTP Code: %{http-code}\n" \
  "https://api.semanticscholar.org/graph/v1/paper/search?query=test&limit=1&fields=paperId"

# Health check with API key
curl -s -w "\nHTTP Code: %{http-code}\n" \
  -H "x-api-key: YOUR-API-KEY" \
  "https://api.semanticscholar.org/graph/v1/paper/search?query=test&limit=1&fields=paperId"
```

### Pagination

| Type                                           | Next Indicator                            | Last Page Signal |
| ---------------------------------------------- | ----------------------------------------- | ---------------- |
| Offset-based (`offset` + `limit` for search)   | `next` field in response (integer offset) | `next` is `null` |
| Batch POST (`/paper/batch` for DOI resolution) | N/A (single response)                     | N/A              |

**Search response envelope:**

```
{
  "total": 10000,
  "offset": 0,
  "next": 100,
  "data": [ ... paper records ... ]
}
```

**Batch DOI resolution (`POST /paper/batch`):**

```
Request: { "ids": ["DOI:10.1038/...", "DOI:10.1126/..."] }
Response: [ {paper1}, null, {paper3}, ... ]  // null for not-found DOIs
```

The batch response preserves order and returns `null` for unresolved DOIs.

### Retry & Circuit Breaker

| Parameter                         | Value              |
| --------------------------------- | ------------------ |
| `use-retry-after`                 | `true`             |
| Circuit Breaker Failure Threshold | 10 (more tolerant) |
| Circuit Breaker Recovery Timeout  | 600 sec (10 min)   |

### Validation Commands

```bash
# 1. Health check (search endpoint)
curl -s "https://api.semanticscholar.org/graph/v1/paper/search?query=test&limit=1&fields=paperId" | python3 -c "
import json, sys; d=json.load(sys.stdin)
print('Total:', d.get('total'))
print('Data count:', len(d.get('data', [])))
"

# 2. Batch DOI resolution (POST)
curl -s -X POST "https://api.semanticscholar.org/graph/v1/paper/batch?fields=paperId,externalIds,title,year" \
  -H "Content-Type: application/json" \
  -d '{"ids": ["DOI:10.1038/nature12373", "DOI:10.1126/science.1247005"]}' | python3 -c "
import json, sys; d=json.load(sys.stdin)
for r in d:
    if r: print(f\"paperId: {r.get('paperId')}, title: {r.get('title','N/A')[:60]}\")
    else: print('NOT FOUND (null)')
"

# 3. Search with offset pagination
curl -s "https://api.semanticscholar.org/graph/v1/paper/search?query=pharmacogenomics&limit=5&offset=0&fields=paperId,title" | python3 -c "
import json, sys; d=json.load(sys.stdin)
print('Total:', d.get('total'))
print('Next offset:', d.get('next'))
for r in d.get('data', []):
    print(f\"  {r.get('title','N/A')[:70]}\")
"

# 4. Rate limit test (expect 429 without API key)
curl -s -o /dev/null -w "%{http-code}\n" "https://api.semanticscholar.org/graph/v1/paper/search?query=test&limit=1&fields=paperId"
```

### Checklist

- [ ] Health endpoint `/paper/search?query=test&limit=1` returns 200 (or 429 without API key)
- [ ] Batch DOI resolution via `POST /paper/batch` returns array with null for not-found
- [ ] API key header `x-api-key` is accepted and enables stable rate limit
- [ ] Offset pagination returns `next` field for continuation
- [ ] 429 responses include Retry-After header
- [ ] Rate limit without API key is extremely restrictive (1 req / 10 sec)

______________________________________________________________________

## 7. UniProt

**Source config:** `configs/providers/uniprot.yaml`
**Adapter code:** `src/bioetl/infrastructure/adapters/uniprot/client.py`
**API Docs:** https://www.uniprot.org/help/api

### Base Configuration

| Parameter               | Value                                                                           |
| ----------------------- | ------------------------------------------------------------------------------- |
| Base URL                | `https://rest.uniprot.org`                                                      |
| Auth Type               | `api-key` (optional, via `BIOETL_UNIPROT_API_KEY` env var)                      |
| Rate Limit (no key)     | 10.0 req/sec, burst 20                                                          |
| Rate Limit (with key)   | 100 req/sec, burst 200                                                          |
| Batch Size              | 200 (source YAML), 100 IDs per OR-query (adapter constant `UNIPROT-BATCH-SIZE`) |
| Protein Fetch Page Size | 500 (hardcoded in adapter)                                                      |
| Timeout                 | 30.0 sec                                                                        |
| Max Retries             | 3                                                                               |
| Data License            | CC BY 4.0                                                                       |

### Health Check

- [ ] Ubiquitin probe query `accession:P62988` returns valid protein record
- [ ] Health check timeout: 10 sec (from YAML)

```bash
# Health check: search for Ubiquitin (P62988)
curl -s "https://rest.uniprot.org/uniprotkb/search?query=accession:P62988&size=1&format=json" | python3 -c "
import json, sys; d=json.load(sys.stdin)
results = d.get('results', [])
print('Found:', len(results), 'records')
if results:
    print('Accession:', results[0].get('primaryAccession'))
    print('Protein:', results[0].get('proteinDescription',{}).get('recommendedName',{}).get('fullName',{}).get('value','N/A'))
"
```

### Pagination

| Type                                           | Next Indicator                 | Last Page Signal                 |
| ---------------------------------------------- | ------------------------------ | -------------------------------- |
| Cursor-based (`cursor` param in response JSON) | `nextCursor` field in response | `nextCursor` is absent or `null` |

**Response envelope (protein search):**

```
{
  "results": [ ... protein records ... ],
  "nextCursor": "1mbl5u6gbs0lq"
}
```

**Filtered fetch:** Uses OR-query syntax `accession:P12345 OR accession:Q67890` in batches of 100.

**Other entity types:**

- `feature`: Fetched via `GET /uniprotkb/{accession}.json`, extracts `features` array
- `sequence`: Fetched via `GET /uniprotkb/stream?query=...&format=fasta`, parsed by `FastaParser`

### Retry & Circuit Breaker

| Parameter                         | Value   |
| --------------------------------- | ------- |
| `use-retry-after`                 | `true`  |
| Circuit Breaker Failure Threshold | 5       |
| Circuit Breaker Recovery Timeout  | 300 sec |

### Validation Commands

```bash
# 1. Health check (Ubiquitin probe)
curl -s "https://rest.uniprot.org/uniprotkb/search?query=accession:P62988&size=1&format=json" | python3 -c "
import json, sys; d=json.load(sys.stdin)
print('Results:', len(d.get('results', [])))
"

# 2. Protein search with fields
curl -s "https://rest.uniprot.org/uniprotkb/search?query=accession:P62988&size=1&format=json&fields=accession,protein-name,organism-name,sequence,length" | python3 -c "
import json, sys; d=json.load(sys.stdin)
for r in d.get('results', []):
    print(f\"Accession: {r.get('primaryAccession')}\")
    print(f\"Length: {r.get('sequence',{}).get('length')}\")
"

# 3. Batch OR-query (multiple accessions)
curl -s "https://rest.uniprot.org/uniprotkb/search?query=(accession:P62988 OR accession:P04637)&size=10&format=json" | python3 -c "
import json, sys; d=json.load(sys.stdin)
for r in d.get('results', []):
    print(f\"Accession: {r.get('primaryAccession')}\")
"

# 4. Cursor pagination
curl -s "https://rest.uniprot.org/uniprotkb/search?query=organism-id:9606+AND+reviewed:true&size=5&format=json" | python3 -c "
import json, sys; d=json.load(sys.stdin)
print('Results:', len(d.get('results', [])))
print('Next cursor:', d.get('nextCursor', 'N/A')[:20] if d.get('nextCursor') else 'None')
"

# 5. Feature fetch (individual accession)
curl -s "https://rest.uniprot.org/uniprotkb/P62988.json" | python3 -c "
import json, sys; d=json.load(sys.stdin)
features = d.get('features', [])
print(f'Features: {len(features)}')
for f in features[:3]:
    print(f\"  {f.get('type')}: {f.get('description','')[:50]}\")
"

# 6. FASTA sequence fetch
curl -s "https://rest.uniprot.org/uniprotkb/stream?query=accession:P62988&format=fasta" | head -5
```

### Checklist

- [ ] Health endpoint (Ubiquitin P62988 query) returns 200 with results
- [ ] Protein search with `fields` parameter returns requested fields
- [ ] OR-query syntax works for batch accession lookups
- [ ] Cursor pagination returns `nextCursor` for continuation
- [ ] Feature endpoint `/{accession}.json` returns `features` array
- [ ] FASTA stream endpoint returns valid FASTA format
- [ ] API key (when provided) enables higher rate limits (100 req/sec)
- [ ] Retry-After header is respected on 429 responses

______________________________________________________________________

## Cross-Provider Summary

### Authentication Matrix

| Provider         | Auth Type             | Env Variable                                   | Polite Pool      |
| ---------------- | --------------------- | ---------------------------------------------- | ---------------- |
| ChEMBL           | Public                | N/A                                            | N/A              |
| CrossRef         | Email                 | `BIOETL_CROSSREF_EMAIL`                        | Yes (50 req/sec) |
| OpenAlex         | API Key               | `BIOETL_OPENALEX_API_KEY` (`BIOETL_OPENALEX_EMAIL` attribution optional) | N/A              |
| PubChem          | Public                | N/A                                            | N/A              |
| PubMed           | API Key (optional)    | `BIOETL_PUBMED_API_KEY`, `BIOETL_PUBMED_EMAIL` | N/A              |
| Semantic Scholar | API Key (recommended) | `BIOETL_SEMANTICSCHOLAR_API_KEY`               | N/A              |
| UniProt          | API Key (optional)    | `BIOETL_UNIPROT_API_KEY`                       | N/A              |

### Rate Limit Comparison

| Provider         | Without Key/Email                 | With Key/Email           |
| ---------------- | --------------------------------- | ------------------------ |
| ChEMBL           | 0.1 req/sec (`chembl.yaml`)       | N/A                      |
| CrossRef         | Shared pool (aggressive limiting) | 50 req/sec (polite pool) |
| OpenAlex         | Not a production support boundary | 10 req/sec with API key / credit model |
| PubChem          | 5 req/sec                         | N/A                      |
| PubMed           | 3 req/sec                         | 10 req/sec               |
| Semantic Scholar | 0.1 req/sec (1 per 10s)           | 1 req/sec                |
| UniProt          | 10 req/sec                        | 100 req/sec              |

### Pagination Type Comparison

| Provider         | Pagination Type                     | Key Response Fields                       |
| ---------------- | ----------------------------------- | ----------------------------------------- |
| ChEMBL           | Offset (`limit`/`offset`)           | `page-meta.next`, `page-meta.total-count` |
| CrossRef         | Cursor (`cursor`)                   | `message.next-cursor`                     |
| OpenAlex         | Cursor (`cursor`, initial `*`)      | `meta.next-cursor`                        |
| PubChem          | None (via pubchempy library)        | N/A                                       |
| PubMed           | Two-phase (esearch + efetch)        | `esearchresult.idlist`                    |
| Semantic Scholar | Offset (search) / Batch POST (DOIs) | `next` (offset integer)                   |
| UniProt          | Cursor (`nextCursor` in JSON)       | `nextCursor`                              |

### Circuit Breaker Settings

| Provider         | Failure Threshold | Recovery Timeout |
| ---------------- | ----------------- | ---------------- |
| ChEMBL           | 5                 | 300 sec (5 min)  |
| CrossRef         | 5                 | 300 sec (5 min)  |
| OpenAlex         | 5                 | 300 sec (5 min)  |
| PubChem          | 5                 | 300 sec (5 min)  |
| PubMed           | 5                 | 300 sec (5 min)  |
| Semantic Scholar | 10                | 600 sec (10 min) |
| UniProt          | 5                 | 300 sec (5 min)  |
