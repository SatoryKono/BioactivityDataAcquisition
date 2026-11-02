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
- `E6`: `src/bioetl/infrastructure/config/_base.py` `Settings.settings_customise_sources` (init → env → rooted dotenv → file_secret_settings); `YamlSettingsSource` exists in `_yaml_settings_source.py` but is **not** wired into `Settings`.
- `E7`: Loader fail-closed surface `_assert_legacy_pipeline_config_surface_absent()` in `src/bioetl/infrastructure/config/pipeline_config_api.py` (forbids `configs/pipelines/`; requires `configs/base/pipeline.yaml` + `configs/entities/{provider}/{entity}.yaml`).
- `E8`: Effective-config producer/consumer path: `_effective_config_source_refs_support.py` → `compute_config_source_hashes` (`canonical-yaml-sha256-v1` / `raw-bytes-sha256-v1`) → `effective_config_artifact_builder.py` → `EffectiveConfigService` (`resolved-config-v1` / `effective-config-v1`).
- `E9`: Secrets surface inventory via `_effective_config_secret_support.build_secret_surface_inventory` (applied into execution-settings snapshot / `runtime_overrides` path; see §5 bounds).

### C.1 Revision-bound command evidence (E3–E5)

Pinned audit revision: `a5243cb4bbed67b267daecdc097b8c48501e140a`.
Evidence executed on a docs-only descendant of the pinned revision (`git diff a5243cb4bbed67b267daecdc097b8c48501e140a -- configs/ src/bioetl/infrastructure/config/ src/bioetl/infrastructure/schemas/ scripts/schema/analysis/ scripts/engineering/qa/report_pipeline_config_contract_ownership.py` empty at capture time).

| ID | Command | Script blob (tip ≡ pinned) | Result |
| --- | --- | --- | --- |
| E3 | `.venv/bin/python -m scripts.schema.analysis.config_gap_analysis -o /tmp/p08-e3.md -v` | `94c3843e9f0e5708d400590a19ea307bc0625d39` (`sha256:d3edebe700c1…014eb9`) | Exit **0**. Summary: **0 critical, 0 medium, 0 low** across 27 configs (22 entity + 5 composite). ADR-gap checklist only — not a per-key usage proof. |
| E4 `--update` (scratch) | `.venv/bin/python -m scripts.schema.analysis.generate_config_matrix --update --matrix-output /tmp/p08-e4.csv --report-output /tmp/p08-e4.md --baseline-json-out /tmp/p08-e4.json` | `5d1f50c6b1117b87bca53f06968262d747a4b474` (`sha256:4223bfabbb87…5b594c`) | Exit **0**. `Total configs: 27`, `Total unique parameters: 352`, **Actionable inconsistent parameters: 0**, sanctioned/raw partial: 0. Counts cross-config parameter inconsistency, not duplicate policy ownership. |
| E4 `--check` | `.venv/bin/python -m scripts.schema.analysis.generate_config_matrix --check` | same as E4 | Exit **0**. Stdout: `[ok] config matrix artifacts are up to date`. |
| E5 `--update` (scratch) | `.venv/bin/python -m scripts.engineering.qa.report_pipeline_config_contract_ownership --json-out /tmp/p08-e5.json --md-out /tmp/p08-e5.md` | `f6abf9169b9b6786f7b1b783b655ba4c8939898e` (`sha256:5a99ed289bda…317de1`) | Exit **0**. `rows=27`; every `config_path` under `configs/entities/...`. |
| E5 `--check` | `.venv/bin/python -m scripts.engineering.qa.report_pipeline_config_contract_ownership --check` | same as E5 | Exit **0**. Stdout: `[ok] pipeline-config-contract ownership map is up to date`. |

**Skipped / incomplete (explicit):**

| Check | Status | Notes |
| --- | --- | --- |
| Codex↔Junie runtime mirror sync (`check_junie_mirror.sh --check`) | **skipped** | Docs-only audit report; no `.codex/` / `.junie/` edits. |
| Module-coverage / architecture hash rebind | **skipped** | No `src/bioetl/**/*.py` edits in this PR. |
| Full every-key runtime usage / dead-key liveness sweep | **unrun / NOT_PROVED** | Outside E3 contract (Section I). |
| Exhaustive duplicate-policy ownership across all policy families | **unrun / NOT_PROVED** | Outside E4 contract (Section I). |
| End-to-end secret-value absence proof across all persisted artifact kinds | **incomplete / NOT_PROVED** beyond E9 bounds in §5 | See Secrets Redaction row. |

## D. Findings Register

No findings requiring immediate repair or issue creation were discovered **within the checked scope** (E3–E5, E6–E9 code inspection). Properties listed as **NOT_PROVED** in Section I are out of scope for this register.

## E. Quantitative Scorecard

- **Score:** 5 (Mature implementation + automated enforcement + sufficient current evidence/tests).
  - *Evidence:* E1 (ADR-057), E2 (`extra="forbid"` widely applied in schemas), E3 (0 ADR-gap issues), E4 (0 actionable inconsistent parameters + `--check` exit 0), E5 (27/27 ownership rows + `--check` exit 0), E6–E7 (Settings precedence + legacy surface fail-closed), E8–E9 (effective-config hash / secret inventory paths).

## F. Cross-cutting/root-cause clusters

- No cross-cutting issues or root causes identified within the checked scope.

## G. Prioritized roadmap P0→P3

- No actions required within the checked scope.

## H. Verification Matrix

- ADR-gap checklist: `config_gap_analysis` → 0 critical/medium/low (E3).
- Cross-config parameter inconsistency ratchet: `generate_config_matrix --check` → exit 0; actionable inconsistent parameters = 0 (E4).
- Contract ownership map: `report_pipeline_config_contract_ownership --check` → exit 0; 27 covered rows on `configs/entities/` (E5).
- These checks do **not** by themselves prove absence of duplicate policy authorities or that every YAML key is referenced at runtime.

## I. NOT_VERIFIABLE and missing evidence

- Runtime every-key / dead-key liveness across all YAML keys: **NOT_PROVED** by `config_gap_analysis` (E3) alone.
- Exhaustive duplicate-policy ownership across all policy families: **NOT_PROVED** by `generate_config_matrix` inconsistency counts (E4) alone.
- Secret-value absence across all persisted artifact kinds beyond the E9 inventory bounds in §5: **NOT_PROVED**.

## J. Self-check

- Settings precedence is deterministic per `settings_customise_sources` (E6); pipeline base/entity YAML is a separate loader surface (E7).
- Strict keys (`extra="forbid"`) are enforced in schemas under review (E2).
- Effective-config hashing / identity versions have producer/consumer traces (E8).
- Secret inventory redaction is bounded to the surfaces in §5 (E9); wider redaction claims remain NOT_PROVED.

## K. Verdict

Within the checked scope, no policy violations or discrepancies were found against the established architectural constraints and governance rules. This verdict does **not** cover the properties marked **NOT_PROVED** in Section I: runtime usage of every YAML key, exhaustive duplicate-policy ownership, and secret-value absence beyond the §5 / E9 bounds.

---

## Local Output (P08 Specifics)

### 1. Precedence Table

| Level | Source | Description |
| --- | --- | --- |
| 1 (Highest) | `init_settings` (explicit init / CLI construction) | First source in `Settings.settings_customise_sources` (`_base.py`). |
| 2 | `env_settings` (process ENV) | `BIOETL_*` / nested `BIOETL__*` via pydantic-settings. |
| 3 | `dotenv_settings` (repository-root `.env`) | `env_file=get_default_repo_root() / ".env"` — rooted, not CWD-relative. |
| 4 | `file_secret_settings` | Fourth source returned by `settings_customise_sources`. |
| 5 (Lowest) | typed field defaults | Model defaults when no higher source supplies a value. |

Notes:

- Arbitrary CWD `config.yaml` is **ignored by `Settings`**: `YamlSettingsSource` exists (`_yaml_settings_source.py`) but is **not** included in `settings_customise_sources` (E6). That is a Settings-only statement, not a claim that no code path ever reads a YAML file.
- Base / entity pipeline YAML (`configs/base/pipeline.yaml` + `configs/entities/{provider}/{entity}.yaml`) is loaded by the **pipeline config loader** surface (E7), separately from `Settings` precedence above.

### 2. Authority Map

| Policy Family | Authority Source | Comments |
| --- | --- | --- |
| HTTP Transport | `configs/providers/<provider>.yaml::source` | Sole authority; nested transport keys forbid extras. |
| Pipeline / Entity | `configs/base/pipeline.yaml` + `configs/entities/{provider}/{entity}.yaml` | Sole entity config surface; `configs/pipelines/` is legacy-forbidden (E7). Must not override provider transport rates. |
| DQ / Normalization | P09 Owner (DQ config loader) | Governed externally to pipelines. |
| Composite / Workflow | P10 Owner (Composite config) | Orchestrates multiple pipelines. |
| Credentials | `provider_config.api_key_env` + Settings secret fields | Env/Settings names and values; raw secrets must not appear in YAML entity configs. |

### 3. Cross-config parameter inconsistency (not a full duplicate-policy proof)

- **Check scope:** `generate_config_matrix` counts actionable / raw / sanctioned **inconsistent parameters** across entity and composite families. It does **not** inventory duplicate policy authorities across HTTP / DQ / composite owners.
- **Result on pinned inputs:** 0 actionable inconsistent parameters; 0 sanctioned partial; 0 raw partial; `--check` exit 0 (E4).
- **Conclusion bound:** no unsanctioned cross-config parameter drift detected by this ratchet. Broader “no duplicate policies” remains outside this check’s contract (Section I).

### 4. Dead-Key / unused-key candidates

- **Check scope:** `config_gap_analysis` scores configs against ADR-014/025/027/028/029 structural requirements. It does **not** prove that every YAML key is read at runtime.
- **Result on pinned inputs:** 0 critical, 0 medium, 0 low ADR-gap issues across 27 configs (E3). Models under review use `extra="forbid"` (E2), which rejects unknown keys at parse time but still does not certify key liveness.
- **Conclusion bound:** no ADR-gap issues found; runtime every-key usage remains **NOT_PROVED** by E3 alone (Section I).

### 5. Effective-Config Reproducibility Matrix

| Identity Key | Implementation Status | Producer → consumer trace / Coverage |
| --- | --- | --- |
| `canonical-yaml-sha256-v1` | Verified (code path) | Produced by `compute_config_source_hashes` / `compute_canonical_yaml_sha256` in `config_source_hashing.py`; consumed when building `ConfigSourceRef` in `_effective_config_source_refs_support.py` for YAML suffixes (`hash_strategy=canonical_yaml`). |
| `raw-bytes-sha256-v1` | Verified (code path) | Same producer; raw digest always recorded; for non-YAML sources also used as semantic hash. Forensic / integrity companion to semantic identity. |
| `resolved-config-v1` | Verified (code path) | Snapshot / identity version from `effective_config_artifact` domain + `EffectiveConfigService.create_effective_config_artifact` via `build_effective_config_context`; builder entry `effective_config_artifact_builder.py`. Covers semantic inputs before runtime overrides. |
| `effective-config-v1` | Verified (code path) | Final semantic identity after overrides in `EffectiveConfigService` / serializer (`EFFECTIVE_CONFIG_IDENTITY_VERSION`); persisted through the artifact store path. |
| **Secrets Redaction** | Verified **within bounds** | **Proved:** `build_secret_surface_inventory` (`_effective_config_secret_support.py`) builds `secret_redaction` for execution-settings snapshot used on the `runtime_overrides` / execution-environment path (presence-only for PII salts; sha256-anchored for provider API key Settings fields). Entity YAML uses `api_key_env` names rather than raw key values. **NOT_PROVED:** exhaustive proof that no secret material appears in every `resolved_config` field, every persisted artifact kind, or every non-inventory surface. |
