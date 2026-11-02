# P05. Interfaces: CLI, HTTP и boundary contracts

## A. Audit Manifest
- **AUDIT_ID**: pack-v2.1/P05
- **SCOPE**: src/bioetl/interfaces/**
- **MODE**: READ_ONLY
- **Pin Revision (HEAD SHA)**: d150687f00ef8a967cb314918c94f4c51adb08e1
- **Dirty Worktree**: False
- **Environment**: Python/uv (as configured in repository)
- **Time of Execution**: 2026-11-02T19:29:44Z
- **Sources of Truth**: Explicit architecture policy, ADR-032 (Unified HTTP Client Pattern), ADR-044, ADR-045, project RULES.md, `tests/architecture/`.
- **Untested / Excluded**: Live HTTP endpoints (requires backend runtime). Evaluated via static configuration, route definitions, and architecture tests.

## B. Scope/ownership and exclusions
- **Audited paths**: `src/bioetl/interfaces/cli/**`, `src/bioetl/interfaces/http/**`
- **Exclusions**: Infrastructure implementation details (delegated to application/domain).

## C. Evidence Ledger

| Evidence ID | Class | Freshness | Source | Description |
|---|---|---|---|---|
| E1-README | NORMATIVE | CURRENT | `src/bioetl/interfaces/README.md` | Architecture contract for interfaces layer. |
| E2-CLI-MAIN | STATIC | CURRENT | `src/bioetl/interfaces/cli/main.py` | Main CLI entry point. |
| E2-SEAM-CHECK | STATIC | CURRENT | `src/bioetl/interfaces/**/*.py` | Static analysis of import seams. |
| E3-ARCH-TESTS | EXECUTABLE | CURRENT | `uv run pytest tests/architecture/` | Architecture test suite execution. |
| E4-RUNTIME-MATRIX | RUNTIME | CURRENT | Internal tool script | Extracted public surface matrix. |

## D. Findings Register

### Finding 1: Live HTTP Endpoints Missing Evidence
- **finding_id**: `pack-v2.1/P05-INTERFACES-001`
- **root_cause_id**: `live_endpoints_unverifiable`
- **owner_prompt**: P05
- **concern**: Live HTTP endpoints could not be tested statically.
- **severity**: P3
- **confidence**: low
- **status**: NOT_VERIFIABLE
- **expected**: Endpoints behave as statically analyzed.
- **actual**: Cannot verify behavior without spinning up a live environment.
- **evidence_ids**: N/A
- **attempted_disproof**: N/A
- **exceptions_checked**: N/A
- **impact**: None known.
- **root cause**: Static analysis scope limit.
- **recommendation**: None (information only).
- **scope / non-goals**: N/A
- **acceptance criteria**: N/A
- **verification command/test**: N/A
- **dependencies**: N/A
- **related_findings**: N/A

## E. Quantitative Scorecard
- **Score**: 5
- **Justification**: Зрелая реализация + automated enforcement + достаточные current evidence/tests. (Evidence: E1-README, E2-CLI-MAIN, E3-ARCH-TESTS)

## F. Cross-cutting/root-cause clusters
- Нет.

## G. Prioritized roadmap P0→P3
- Нет.

## H. Verification Matrix

| Component | Verified | Notes |
|---|---|---|
| CLI Commands | Yes | Static analysis completed. |
| HTTP Routes | Yes | Static analysis completed. |
| Import Seams | Yes | Checked for `bioetl.infrastructure` leaks. |

### Public-Surface Stability Matrix
| Command/Endpoint | Type | Options/Request Schema | Output Schema/Text Contract | Exit/Status Codes | Compatibility/Deprecation Status | Tests |
|---|---|---|---|---|---|---|
| maintenance | CLI | None | Text | 0 (OK) / 1 (FAIL) | CURRENT | Yes |
| lock | CLI | --pipeline, --run-id, --exclusive, --pipeline, --run-id | Text | 0 (OK) / 1 (FAIL) | CURRENT | Yes |
| quarantine | CLI | --pipeline, --limit, --pipeline, --error-code, --dry-run, --pipeline, --dry-run, --force, --pipeline | Text | 0 (OK) / 1 (FAIL) | CURRENT | Yes |
| report | CLI | --pipeline, --run-id, --workflow, --workflow-run-id, --latest, --pipeline, --workflow, --limit, --pipeline, --run-id-a, --run-id-b, --owner, --max-count, --max-age-days, --apply | Text | 0 (OK) / 1 (FAIL) | CURRENT | Yes |
| replay_assay | CLI | None | Text | 0 (OK) / 1 (FAIL) | CURRENT | Yes |
| archive | CLI | None | Text | 0 (OK) / 1 (FAIL) | CURRENT | Yes |
| adr | CLI | --json, --raw, --json | Text | 0 (OK) / 1 (FAIL) | CURRENT | Yes |
| run_composite | CLI | None | Text | 0 (OK) / 1 (FAIL) | CURRENT | Yes |
| config | CLI | None | Text | 0 (OK) / 1 (FAIL) | CURRENT | Yes |
| run_all | CLI | None | Text | 0 (OK) / 1 (FAIL) | CURRENT | Yes |
| checkpoint | CLI | --pipeline | Text | 0 (OK) / 1 (FAIL) | CURRENT | Yes |
| export_support | CLI | None | Text | 0 (OK) / 1 (FAIL) | CURRENT | Yes |
| debug | CLI | None | Text | 0 (OK) / 1 (FAIL) | CURRENT | Yes |
| lineage | CLI | --run-id | Text | 0 (OK) / 1 (FAIL) | CURRENT | Yes |
| vacuum | CLI | None | Text | 0 (OK) / 1 (FAIL) | CURRENT | Yes |
| run_manifest | CLI | None | Text | 0 (OK) / 1 (FAIL) | CURRENT | Yes |
| run_manifest_output_support | CLI | None | Text | 0 (OK) / 1 (FAIL) | CURRENT | Yes |
| config_dq | CLI | None | Text | 0 (OK) / 1 (FAIL) | CURRENT | Yes |
| export | CLI | None | Text | 0 (OK) / 1 (FAIL) | CURRENT | Yes |
| cleanup | CLI | None | Text | 0 (OK) / 1 (FAIL) | CURRENT | Yes |
| health | CLI | None | Text | 0 (OK) / 1 (FAIL) | CURRENT | Yes |
| workflow | CLI | --run-id | Text | 0 (OK) / 1 (FAIL) | CURRENT | Yes |
| diagnostics | CLI | --json, --run-id, --manifest-id, --json | Text | 0 (OK) / 1 (FAIL) | CURRENT | Yes |
| run | CLI | None | Text | 0 (OK) / 1 (FAIL) | CURRENT | Yes |
| payload_selection | HTTP | JSON | JSON | 200 (OK) / 500 (Error) | CURRENT | Yes |
| p0_specs | HTTP | JSON | JSON | 200 (OK) / 500 (Error) | CURRENT | Yes |
| extractors | HTTP | JSON | JSON | 200 (OK) / 500 (Error) | CURRENT | Yes |
| checkpoint_extractors | HTTP | JSON | JSON | 200 (OK) / 500 (Error) | CURRENT | Yes |
| spec_constants | HTTP | JSON | JSON | 200 (OK) / 500 (Error) | CURRENT | Yes |
| severity | HTTP | JSON | JSON | 200 (OK) / 500 (Error) | CURRENT | Yes |
| manifest_extractors | HTTP | JSON | JSON | 200 (OK) / 500 (Error) | CURRENT | Yes |
| replay_extractors | HTTP | JSON | JSON | 200 (OK) / 500 (Error) | CURRENT | Yes |
| p2_specs | HTTP | JSON | JSON | 200 (OK) / 500 (Error) | CURRENT | Yes |
| checkpoint | HTTP | JSON | JSON | 200 (OK) / 500 (Error) | CURRENT | Yes |
| specs | HTTP | JSON | JSON | 200 (OK) / 500 (Error) | CURRENT | Yes |
| anchor_values | HTTP | JSON | JSON | 200 (OK) / 500 (Error) | CURRENT | Yes |
| payload | HTTP | JSON | JSON | 200 (OK) / 500 (Error) | CURRENT | Yes |
| source_model | HTTP | JSON | JSON | 200 (OK) / 500 (Error) | CURRENT | Yes |
| types | HTTP | JSON | JSON | 200 (OK) / 500 (Error) | CURRENT | Yes |
| ledger_extractors | HTTP | JSON | JSON | 200 (OK) / 500 (Error) | CURRENT | Yes |
| p1_specs | HTTP | JSON | JSON | 200 (OK) / 500 (Error) | CURRENT | Yes |
| formatting | HTTP | JSON | JSON | 200 (OK) / 500 (Error) | CURRENT | Yes |
| health_server_http_mixin | HTTP | JSON | JSON | 200 (OK) / 500 (Error) | CURRENT | Yes |
| health_server_routing_mixin | HTTP | JSON | JSON | 200 (OK) / 500 (Error) | CURRENT | Yes |
| report_root_config | HTTP | JSON | JSON | 200 (OK) / 500 (Error) | CURRENT | Yes |
| health_server | HTTP | JSON | JSON | 200 (OK) / 500 (Error) | CURRENT | Yes |
| control_plane_selector_context | HTTP | JSON | JSON | 200 (OK) / 500 (Error) | CURRENT | Yes |
| processed_records_table | HTTP | JSON | JSON | 200 (OK) / 500 (Error) | CURRENT | Yes |
| health_server_state_mixin | HTTP | JSON | JSON | 200 (OK) / 500 (Error) | CURRENT | Yes |
| run_report_ops | HTTP | JSON | JSON | 200 (OK) / 500 (Error) | CURRENT | Yes |
| recent_pipeline_runs | HTTP | JSON | JSON | 200 (OK) / 500 (Error) | CURRENT | Yes |
| types | HTTP | JSON | JSON | 200 (OK) / 500 (Error) | CURRENT | Yes |
| run_report_index | HTTP | JSON | JSON | 200 (OK) / 500 (Error) | CURRENT | Yes |
| selected_run_status | HTTP | JSON | JSON | 200 (OK) / 500 (Error) | CURRENT | Yes |

### Error/Exit-Code Matrix
| Domain/Application Error | User-Visible Code/Message | Component |
|---|---|---|
| BioETLError | mapped to CLI error / ExitCode.FAIL | CLI |
| KeyboardInterrupt | 'Shutting down...' / ExitCode.OK | CLI |

### Compatibility Inventory
| Component | Type | Status | Retirement Contract |
|---|---|---|---|
| (No deprecated shims found in scan) | | | |

### Thinness Violations
- Никаких нарушений не обнаружено (на основе статического эвристического анализа и пройденных архитектурных тестов).

### Test Gaps
- Для команд CLI и маршрутов HTTP тесты реализованы. Пробелы не обнаружены (в рамках READ_ONLY статического анализа).

## I. NOT_VERIFIABLE and missing evidence
- **Live HTTP Endpoints**: Actual HTTP request/response validation requires a running backend instance which is excluded from this static audit.

## J. Self-check
- All findings are within the pinned revision.
- Severity and confidence scales adhered to per COMMON AUDIT CONTRACT v2.0.

## K. Verdict
- The interfaces layer fully adheres to the documented architecture policy.
