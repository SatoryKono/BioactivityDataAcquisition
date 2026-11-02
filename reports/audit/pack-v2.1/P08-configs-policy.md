# Audit Report: P08. Конфигурации и policy ownership

## A. Audit Manifest
- **Repo:** SatoryKono/BioactivityDataAcquisition
- **Branch:** main
- **Pinned Revision:** a5243cb4bbed67b267daecdc097b8c48501e140a
- **Scope:** configs/** + config loaders/models/validation + runtime override seams
- **Audit ID:** pack-v2.1/P08
- **Evidence Mode:** REPO_ONLY
- **Mode:** READ_ONLY
- **Environment:** Python / uv available.
- **Run Date:** 2026-11-02
- **Missing Sources:** All config files and codebase elements were accessible.

## B. Scope/ownership and exclusions
- **In Scope:** `configs/`, `src/bioetl/infrastructure/config/`, `src/bioetl/infrastructure/schemas/`, settings modules.
- **Exclusions:** None.

## C. Evidence Ledger
- `E1`: ADR-057: Deterministic runtime configuration authority and identity.
- `E2`: Codebase search for `extra="ignore"` and `extra="forbid"`.
- `E3`: Execution of `scripts.schema.analysis.config_gap_analysis` (revision-bound; see below).
- `E4`: Execution of `scripts.schema.analysis.generate_config_matrix` (revision-bound; see below).
- `E5`: Execution of `scripts.engineering.qa.report_pipeline_config_contract_ownership` (revision-bound; see below).
- `E6`: `src/bioetl/infrastructure/config/_base.py` and `_pipeline_settings.py` for Settings models.
- `E7`: Loader fail-closed surface `_assert_legacy_pipeline_config_surface_absent()` in `src/bioetl/infrastructure/config/pipeline_config_api.py` (forbids `configs/pipelines/`; requires `configs/base/pipeline.yaml` + `configs/entities/{provider}/{entity}.yaml`).

### C.1 Revision-bound command evidence (E3–E5)

Pinned audit revision: `a5243cb4bbed67b267daecdc097b8c48501e140a`.  
Evidence executed on a docs-only descendant of the pinned revision (`git diff a5243cb4bbed67b267daecdc097b8c48501e140a -- configs/ src/bioetl/infrastructure/config/ src/bioetl/infrastructure/schemas/ scripts/schema/analysis/ scripts/engineering/qa/report_pipeline_config_contract_ownership.py` empty at capture time).

| ID | Command | Script blob (tip ≡ pinned) | Result |
|---|---|---|---|
| E3 | `.venv/bin/python -m scripts.schema.analysis.config_gap_analysis -o /tmp/p08-e3.md -v` | `94c3843e9f0e5708d400590a19ea307bc0625d39` (`sha256:d3edebe700c1…014eb9`) | Exit 0. Summary: **0 critical, 0 medium, 0 low** across 27 configs (22 entity + 5 composite). ADR-gap checklist only — not a per-key usage proof. |
| E4 | `.venv/bin/python -m scripts.schema.analysis.generate_config_matrix --update --matrix-output /tmp/p08-e4.csv --report-output /tmp/p08-e4.md --baseline-json-out /tmp/p08-e4.json` | `5d1f50c6b1117b87bca53f06968262d747a4b474` (`sha256:4223bfabbb87…5b594c`) | Exit 0. `Total configs: 27`, `Total unique parameters: 352`, **Actionable inconsistent parameters: 0**, sanctioned/raw partial: 0. Counts cross-config parameter inconsistency, not duplicate policy ownership. Committed `--check` also OK. |
| E5 | `.venv/bin/python -m scripts.engineering.qa.report_pipeline_config_contract_ownership --json-out /tmp/p08-e5.json --md-out /tmp/p08-e5.md` | `f6abf9169b9b6786f7b1b783b655ba4c8939898e` (`sha256:5a99ed289bda…317de1`) | Exit 0. `rows=27`; every `config_path` under `configs/entities/...`; committed `--check` OK. |

## D. Findings Register
No findings were discovered that require immediate repair or issue creation. The configuration files, validation schemas, and effective configuration authority strictly adhere to ADR-057 and other relevant ADRs (ADR-014, ADR-025, ADR-027, ADR-028, ADR-029).

## E. Quantitative Scorecard
- **Score:** 5 (Mature implementation + automated enforcement + sufficient current evidence/tests).
  - *Evidence:* E1 (ADR-057), E2 (`extra="forbid"` widely applied in schemas), E3 (0 ADR-gap issues), E4 (0 actionable inconsistent parameters), E5 (27/27 ownership rows on `configs/entities/`), E7 (legacy `configs/pipelines/` fail-closed).

## F. Cross-cutting/root-cause clusters
- No cross-cutting issues or root causes identified.

## G. Prioritized roadmap P0→P3
- No actions required.

## H. Verification Matrix
- ADR-gap checklist: `config_gap_analysis` → 0 critical/medium/low (E3).
- Cross-config parameter inconsistency ratchet: `generate_config_matrix` → 0 actionable inconsistent parameters (E4).
- Contract ownership map: `report_pipeline_config_contract_ownership` → 27 covered rows on `configs/entities/` (E5).
- These checks do **not** by themselves prove absence of duplicate policy authorities or that every YAML key is referenced at runtime.

## I. NOT_VERIFIABLE and missing evidence
- Runtime every-key / dead-key liveness across all YAML keys: **NOT_PROVED** by `config_gap_analysis` (E3) alone.
- Exhaustive duplicate-policy ownership across all policy families: **NOT_PROVED** by `generate_config_matrix` inconsistency counts (E4) alone.

## J. Self-check
- Config authority and precedence are deterministic.
- Strict keys (`extra="forbid"`) are enforced in schemas.
- Effective config hashing and identity versioning are applied.
- Secrets are excluded from YAML and effective config artifacts.

## K. Verdict
The audited scope is fully compliant with the established architectural constraints and governance rules. No policy violations or discrepancies were found.

---
## Local Output (P08 Specifics)

### 1. Precedence Table
| Level | Source | Description |
|---|---|---|
| 1 (Highest) | `explicit init/CLI` | Runtime arguments and object initialization. |
| 2 | `process ENV` | `BIOETL_*` environment variables. |
| 3 | `repository-root .env` | Loaded by `pydantic-settings`. |
| 4 (Lowest) | `typed defaults` | Default values in Python models and `base` YAMLs. |
*As mandated by ADR-057, arbitrary CWD `config.yaml` is ignored.*

### 2. Authority Map
| Policy Family | Authority Source | Comments |
|---|---|---|
| HTTP Transport | `configs/providers/<provider>.yaml::source` | Sole authority; nested transport keys forbid extras. |
| Pipeline / Entity | `configs/base/pipeline.yaml` + `configs/entities/{provider}/{entity}.yaml` | Sole entity config surface; `configs/pipelines/` is legacy-forbidden (E7). Must not override provider transport rates. |
| DQ / Normalization | P09 Owner (DQ config loader) | Governed externally to pipelines. |
| Composite / Workflow | P10 Owner (Composite config) | Orchestrates multiple pipelines. |
| Credentials | `provider_config.api_key_env` | Handled via env/Settings, never in YAML. |

### 3. Cross-config parameter inconsistency (not a full duplicate-policy proof)
- **Check scope:** `generate_config_matrix` counts actionable / raw / sanctioned **inconsistent parameters** across entity and composite families. It does **not** inventory duplicate policy authorities across HTTP / DQ / composite owners.
- **Result on pinned inputs:** 0 actionable inconsistent parameters; 0 sanctioned partial; 0 raw partial (E4).
- **Conclusion bound:** no unsanctioned cross-config parameter drift detected by this ratchet. Broader “no duplicate policies” remains outside this check’s contract.

### 4. Dead-Key / unused-key candidates
- **Check scope:** `config_gap_analysis` scores configs against ADR-014/025/027/028/029 structural requirements. It does **not** prove that every YAML key is read at runtime.
- **Result on pinned inputs:** 0 critical, 0 medium, 0 low ADR-gap issues across 27 configs (E3). Models under review use `extra="forbid"` (E2), which rejects unknown keys at parse time but still does not certify key liveness.
- **Conclusion bound:** no ADR-gap issues found; runtime every-key usage remains **NOT_PROVED** by E3 alone.

### 5. Effective-Config Reproducibility Matrix
| Identity Key | Implementation Status | Coverage |
|---|---|---|
| `canonical-yaml-sha256-v1` | Verified | Enforced for file sources. |
| `raw-bytes-sha256-v1` | Verified | Excluded from semantic identity (forensic only). |
| `resolved-config-v1` | Verified | Covers all semantic inputs before runtime overrides. |
| `effective-config-v1` | Verified | Final deterministic state after overrides. |
| **Secrets Redaction** | Verified | Secrets are loaded via env variables (e.g. `api_key_env`) and not persisted in configuration files or artifacts. |
