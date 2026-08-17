## Parent

#8859 (`CR-FULL-20260816`). Product stream split out of closed #8890 bulk confirms. Do **not** open one GitHub issue per raw finding. Do not reopen #8643 / #8644 / #8645 / #8652 without a fresh reproduction.

Campaign pin: `BASE_SHA=6a2c8abe8ac5501bae3fef69667c3ff09280e46c`.

## Outcome

Fix leftover adapter confirms from #8890 (untitled OpenAlex/PubMed fallback, Semantic Scholar placeholder key, PubChem CID batch/URL-encode).

## Confirmed majors (re-verify on current `origin/main` before implement)

- [ ] `CR-20260816-C-S06-infra-adapters-049` (unspecified) `src/bioetl/infrastructure/adapters/openalex/fallback.py` — Remove the untitled-candidate fallback in the candidate resolution logic: when a result lacks a title, do not return it from the loop over candidates. Return None instead so unresolved items are no...
- [ ] `CR-20260816-C-S06-infra-adapters-057` (unspecified) `src/bioetl/infrastructure/adapters/semanticscholar/fallback.py` — Update the fallback header construction in the relevant adapter method to pass skip_placeholder_api_key=True, matching the primary adapter so configured your_* placeholder keys are omitted. Add or ...
- [ ] `CR-20260816-C-S06-infra-adapters-103` (unspecified) `src/bioetl/infrastructure/adapters/pubchem/query_builder.py` — Update build_cid_batch_endpoint to construct the request path from every CID in batch using the complete joined list; do not use the truncated preview or append an ellipsis in the returned endpoint...
- [ ] `CR-20260816-C-S06-infra-adapters-110` (unspecified) `src/bioetl/infrastructure/adapters/pubchem/query_builder.py` — Update build_compound_name_endpoint, build_substance_name_endpoint, and build_assay_endpoint to URL-encode each query value with urllib.parse.quote(query, safe="") before interpolating it into the ...
- [ ] `CR-20260816-C-S06-infra-adapters-111` (unspecified) `src/bioetl/infrastructure/adapters/pubmed/fallback.py` — Remove the unconditional results[0] fallback in the result-selection logic so failed titles_match validation returns None, preserving publication matching only for validated candidates. Update the ...
- [ ] `CR-20260816-C-S08-infra-observability-005` (minor) `src/bioetl/infrastructure/observability/anomaly/detector.py` — Update the constructor validation for baseline configuration to reject any min_baseline_samples value greater than baseline_window, while preserving the existing lower-bound checks and assignments....

## Constraints

- Code/tests/contracts outrank CodeRabbit wording.
- One independent behavior change per task unless items share a helper.
- No `.env*` mutation.
- No tech-debt budget / exemption / threshold increase.
- Exact-cover retries stay on #8859.
