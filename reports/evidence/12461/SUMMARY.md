# External API Verification Report
## P12-001: parity контрактов с живыми API шести провайдеров
**Target Revision:** 0c4805bc656e47e9defe622772d9a3deefcdf0e3
**Methodology:** Direct unauthenticated cURL `GET` requests against production endpoints, combined with `HEAD` requests (or equivalent) for headers and rate limit checks.

### 1. ChEMBL
* Object: `https://www.ebi.ac.uk/chembl/api/data/target?limit=1`
* Command: `curl -s -X GET "https://www.ebi.ac.uk/chembl/api/data/target?limit=1" -H "Accept: application/json"`
* Header check: `HTTP/2 405 Method Not Allowed`
* Data request: **PASS** (via GET)
* Result: MEASURED (6932 bytes). Includes schema fields like `target_chembl_id`, `pref_name`, `target_type`.

### 2. PubChem
* Object: `https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/1/JSON`
* Command: `curl -s -X GET "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/1/JSON"`
* Header check: `HTTP/2 200 OK`
* Result: **PASS** MEASURED (14097 bytes).

### 3. CrossRef
* Object: `https://api.crossref.org/works?rows=1`
* Command: `curl -s -X GET "https://api.crossref.org/works?rows=1"`
* Header check: `HTTP/2 405 Method Not Allowed`
* Result: **PASS** MEASURED (2472 bytes).

### 4. OpenAlex
* Object: `https://api.openalex.org/works?per-page=1`
* Command: `curl -s -X GET "https://api.openalex.org/works?per-page=1"`
* Header check: `HTTP/2 200 OK`
* Result: **PASS** MEASURED (18301 bytes).

### 5. SemanticScholar
* Object: `https://api.semanticscholar.org/graph/v1/paper/search?query=test&limit=1`
* Command: `curl -s -X GET "https://api.semanticscholar.org/graph/v1/paper/search?query=test&limit=1"`
* Header check: `HTTP/2 429 Too Many Requests`
* Result: **BLOCKED_EXTERNAL** (Returned 429 Too Many Requests). Data availability: UNKNOWN. Error: `x-amzn-errortype: TooManyRequestsException`.

### 6. UniProt
* Object: `https://rest.uniprot.org/uniprotkb/search?query=reviewed:true&size=1`
* Command: `curl -s -X GET "https://rest.uniprot.org/uniprotkb/search?query=reviewed:true&size=1"`
* Header check: `HTTP/2 200 OK`
* Result: **PASS** MEASURED (34134 bytes).

All API responses are saved in `reports/evidence/12461/` with exact timestamps and headers.
