# Contract Parity Matrix (EXTERNAL_VERIFY)
**Target Revision (SHA):** 0c4805bc656e47e9defe622772d9a3deefcdf0e3

## ChEMBL
* Endpoint: `https://www.ebi.ac.uk/chembl/api/data/target`
* Data Verification: MEASURED (6932 bytes). Includes schema fields like `target_chembl_id`, `pref_name`, `target_type`.
* Fallback Error: None for GET. (HEAD returns 405).
* Status: **PASS**

## PubChem
* Endpoint: `https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/1/JSON`
* Data Verification: MEASURED (14097 bytes).
* Status: **PASS**

## CrossRef
* Endpoint: `https://api.crossref.org/works`
* Data Verification: MEASURED (2472 bytes).
* Status: **PASS**

## OpenAlex
* Endpoint: `https://api.openalex.org/works`
* Data Verification: MEASURED (18301 bytes).
* Status: **PASS**

## SemanticScholar
* Endpoint: `https://api.semanticscholar.org/graph/v1/paper/search`
* Data Verification: UNKNOWN.
* Fallback Error: `HTTP/2 429 Too Many Requests`, `x-amzn-errortype: TooManyRequestsException`.
* Status: **BLOCKED_EXTERNAL**

## UniProt
* Endpoint: `https://rest.uniprot.org/uniprotkb/search`
* Data Verification: MEASURED (34134 bytes).
* Status: **PASS**

All raw data and headers are stored in `reports/evidence/12461/`.
