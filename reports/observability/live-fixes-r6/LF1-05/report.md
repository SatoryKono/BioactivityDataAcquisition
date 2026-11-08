# LF1-05 Acceptance Artifacts and UUIDs

## 1. Context and Environment

* **Task**: GitHub issue #12801: [LF1-05] Подготовить UUID и ожидаемые артефакты приёмки.
* **Environment Status**: Live environment and Grafana are inaccessible (as noted in LF1-01 and confirmed by local testing restrictions). Because of this, diagnostic artifact checking from live deployment is marked `NOT_VERIFIABLE` / `BLOCKED`.
* **Methodology**: In accordance with the supervisor instructions, this report documents the requested UUID selections, expected pipeline stages, and the rationale for missing artifacts without hallucinating positive statuses for inaccessible live components.
* **Base SHA**: `6cf12d952f03836f996a4adbfb02da3a3df18029be6df0a69114186e24eb4b4e`
* **Time (UTC)**: `2026-11-08 13:31:59 UTC`
* **Parameters**: `pipeline=uniprot_protein,uniprot_idmapping`, `run_type=backfill`

### Verification provenance

* Deployment SHA: `NOT_VERIFIABLE`; the live deployment could not be queried.
* Local test checkout: `6374496d30c7111a3c0c535091ecbefd4797cf87`.
* Command: `python -m pytest -q -p no:cacheprovider -o addopts= tests/unit/interfaces/http/test_run_id_resolver.py tests/unit/interfaces/http/test_manifest_validation_catalog.py`.
* Local result: 13 passed. These unit tests cover resolver behavior with fixtures. They provide no live catalog or deployment evidence for the identifiers below.
* GitHub `pr-gate-complete` for the local test checkout: result unavailable at the time of this check.

## 2. UUID Selections and Expectations

| Category | UUID | Pipeline / Workflow | Manifest / Expected Artifacts | Expected Outcome / Rationale |
| :--- | :--- | :--- | :--- | :--- |
| **Positive 1 (Original)** | `ee3ce1ed-9487-572f-ae24-c98c6f6e3a37` | `uniprot_protein` / `uniprot_support_pack` | Manifest, reports, staging outputs | `NOT_VERIFIABLE` (Live API unreachable. Documented in unit tests: `test_run_id_resolver.py` & `test_manifest_validation_catalog.py`) |
| **Positive 2 (Additional)** | `d7cdb35b-e37a-5767-b30e-aa8dfb60d775` | `uniprot_idmapping` | Manifest, parsed TSV mappings | `NOT_VERIFIABLE` (Live environment blocked. Used as disambiguation case in `test_run_id_resolver.py`) |
| **Negative 1 (Historic without Manifest)** | `20261102T181217` | `uniprot_protein` | Report only, no manifest | `PASS` (Documented in `test_run_id_resolver.py` as a non-UUID compact stamp that acts as historic, lacking manifest) |
| **Negative 2 (Missing Manifest)** | `00000000-0000-0000-0000-000000000000` | N/A | None | `PASS` (Deliberately non-existent UUID to test absent manifest logic, expected resolution: `selected_run_id_not_found`) |

### Justification for the Negative Cases
* **Historic without Manifest (`20261102T181217`)**: As tested in `test_run_id_resolver.py`, compact historic stamps from reports catalogs that have no associated UUID manifest catalog entry fail to resolve in a live context (`test_non_uuid_token_does_not_raise_into_live_diagnostics`).
* **Completely Missing (`00000000-0000-0000-0000-000000000000`)**: A null UUID is selected to guarantee an absolute negative response from the catalog resolver. When queried, this UUID will be absent from both the manifest and report catalogs, triggering the fallback behavior which correctly reports `selected_run_id_not_found` rather than throwing a system exception, matching the logic detailed in `test_manifest_validation_catalog.py`.

## 3. Stages and Expected Responses

*For `ee3ce1ed-9487-572f-ae24-c98c6f6e3a37`:*
* **Stages**: Extract `uniprot_support_pack` -> Transform -> Validate -> Load.
* **Expected Answers**: Live endpoints for diagnostics (e.g. `selected_run_status`) would return successful parsing and loading metrics.
* **Verification Status**: `BLOCKED` (Live deployment unreachable).

*For `d7cdb35b-e37a-5767-b30e-aa8dfb60d775`:*
* **Stages**: Extract `uniprot_idmapping` -> Load.
* **Expected Answers**: Successful mapping load metrics.
* **Verification Status**: `BLOCKED` (Live deployment unreachable).

## 4. Backfill and Scope Decisions
Since the live systems are unreachable, no backfill execution can be practically triggered or verified from this environment. New recordings (when systems are online) should be initiated via standard launch contexts without hidden historical tree copying. All exceptions must be passed up to the owner gate.

## 5. Closure Passport Details (Issue #12801)
* **Owner**: Backend/API + Grafana/Observability
* **Deadline**: N/A (Standard SLA)
* **Scope**: Diagnostics and acceptance UUID planning
* **Outcome**: `PASS` for documentation/planning; `NOT_VERIFIABLE` for live metric extraction.
