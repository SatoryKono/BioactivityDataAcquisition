# scripts/qa — Quality & Architecture Checks

Architecture and quality-gate checks, debt telemetry, and code hygiene audits.

## Unified Entry Point

```bash
python -m scripts.engineering.qa --help
python -m scripts.engineering.qa <command> [args...]
```

## Commands

| Command                          | Script                                                | Description                                                                                       |
| -------------------------------- | ----------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| `check-naming`                   | `naming_audit.py`                                     | Naming convention audit (RULES.md §2) with `configs/naming_exceptions.yaml` as exception registry |
| `check-architecture`             | `check_architecture.py`                               | Canonical compatibility wrapper for the legacy infrastructure architecture check                  |
| `check-app-deps`                 | `check_application_deps.py`                           | Canonical compatibility wrapper for the legacy application dependency check                       |
| `check-constructor-args`         | `check_constructor_args.py`                           | Canonical compatibility wrapper for the legacy constructor argument audit                         |
| `check-duplication-complexity-exemptions` | `check_duplication_complexity_exemptions.py` | Validate that workflow complexity exemptions stay owner-scoped, expiring, and registry-backed    |
| `check-c901`                     | `check_c901_baseline.py`                              | C901 complexity baseline enforcement                                                              |
| `check-naming-pkg`               | `check_naming_package_consistency.py`                 | Package naming consistency check                                                                  |
| `check-exemptions`               | `check_quality_exemptions.py`                         | Quality exemptions audit                                                                          |
| `check-xwalk-missing-backlog`    | `check_xwalk_missing_backlog.py`                      | Validate that xwalk `MISSING_*` markers are tracked in the backlog                                |
| `generate-debt-tasks`            | `generate_architecture_debt_tasks.py`                 | Generate `tasks_architecture_metric_exemptions_*.json` from the registry                          |
| `reduce-architecture-debt`       | `reduce_architecture_debt.py`                         | Build `architecture_debt_execution_plan_*.json` from the latest tasks file                        |
| `check-terminology`              | `lint_terminology.py`                                 | Terminology linting against glossary                                                              |
| `proof-or-stop`                  | `src/memory/proof_cli.py`                             | Plan, capture, assemble, verify, pilot, and explicitly ingest source-bound closeout evidence       |
| `report-dep-map`                 | `generate_architecture_dependency_map.py`             | Generate/check architecture dependency map                                                        |
| `report-vcr-metadata`            | `report_vcr_metadata_catalog.py`                      | Generate/check canonical VCR metadata catalog                                                     |
| `check-vcr-replay-preflight`     | `vcr/check_replay_preflight.py`                       | Fail fast on unresolved replay VCR pointers and cheap catalog drift                                |
| `report-provider-contract-drift` | `report_provider_contract_drift.py`                   | Generate provider contract drift diagnostics from replay cassettes                                |
| `report-domain-io-taint-inventory` | `report_domain_io_taint_inventory.py`               | Generate/check semantic Domain I/O taint evidence                                                  |
| `report-domain-ports-inventory`  | `report_domain_ports_inventory.py`                    | Generate/check domain `*Port` Protocol inventory and `@runtime_checkable` coverage                 |
| `check-prometheus-rules`         | `check_prometheus_rules.py`                           | Run deterministic promtool syntax and rule-vector validation                                      |
| `report-dashboard-inventory`     | `report_dashboard_inventory.py`                       | Generate/check dashboard inventory parity, provisioning drift, deployed drift, and local health   |
| `report-dashboard-panel-audit-matrix` | `report_dashboard_panel_audit_matrix.py`         | Generate/check the dashboard panel audit matrix mirror                                            |
| `report-dashboard-scalar-density` | `report_dashboard_scalar_density.py`             | Survey/check scalar information density by dashboard row                                           |
| `report-panel-title-inventory`   | `report_panel_title_inventory.py`                     | Generate/check the dashboard panel-title inventory mirror from shipped JSON                       |
| `report-dashboard-promql-scope`  | `report_dashboard_promql_scope.py`                    | Generate/check dashboard PromQL scope, forbidden `run_id` selectors, and deprecated metric tokens |
| `assemble-observability-closure-evidence` | `assemble_observability_closure_evidence.py` | Validate, hash, and occurrence-bind one typed closure-campaign evidence envelope                    |
| `report-family-baseline`         | `report_hotspot_family_baseline.py`                   | Generate/check RF-06 hotspot-family baseline artifacts                                            |
| `report-flaky-test-burndown-review` | `report_flaky_test_burndown_review.py`             | Generate/check curated flaky-test review evidence bound to current test governance                 |
| `report-adr-enforcement-matrix`  | `report_adr_enforcement_matrix.py`                    | Generate/check accepted ADR enforcement coverage matrix                                           |
| `report-module-coverage`         | `report_module_coverage_inventory.py`                 | Generate/check module-level coverage inventory                                                  |
| `check-branch-coverage`          | `check_branch_coverage.py`                            | Enforce branch coverage from reports/coverage/coverage.xml                                    |
| `report-contract-coverage-matrix` | `report_contract_coverage_matrix.py`                 | Generate/check contract coverage matrix for active entity configs                             |
| `report-port-adapter-factory-coverage` | `report_port_adapter_factory_coverage.py`        | Generate/check core port-adapter-factory coverage matrix                                      |
| `report-compatibility-importer-census` | `report_compatibility_importer_census.py`        | Generate deterministic importer census for sanctioned seams and twin modules                  |
| `report-dead-code-inventory`     | `report_dead_code_inventory.py`                       | Generate repo-local static dead-code review inventory                                         |
| `check-docs-drift`               | `check_docs_drift.py`                                 | Documentation forbidden-pattern drift check                                                   |
| `report-observability-metric-inventory` | `report_observability_metric_inventory.py`      | Generate registry/runtime/docs observability metric inventory                                 |
| `validate-dq-consistency`        | `validate_dq_consistency.py`                          | Validate DQ policy/config consistency                                                         |
| `report-lazy-import-inventory`   | `report_lazy_import_inventory.py`                     | Generate/check lazy import inventory                                                          |
| `report-source-tree-manifest`    | `report_source_tree_manifest.py`                      | Generate/check source tree manifest                                                           |
| `check-dashboard-performance-budgets` | `check_dashboard_performance_budgets.py`          | Validate dashboard performance budgets                                                        |
| `report-architecture-quality-scorecard` | `report_architecture_quality_scorecard.py`       | Generate architecture quality scorecard (owner: python scripts/engineering/qa/report_architecture_quality_scorecard.py) |
| `report-invariant-audit-rebaseline` | `report_invariant_audit_rebaseline.py`              | Generate/check stale invariant-audit evidence matrix and duplicate-issue gates                    |
| `report-architecture-debt-remote-main-baseline` | `report_architecture_debt_remote_main_baseline.py` | Generate/check clean remote-main architecture debt baseline artifacts                             |
| `report-debt-governance-gates`   | `report_debt_governance_gates.py`                     | Generate/check normalized debt-reduction fail-fast gate rollup                                    |
| `validate-technical-debt-audit`  | `technical_debt_audit_registry.py`                    | Validate exact-SHA lifecycle, evidence hash, and report headline semantics                          |
| `run-architecture-audit-read-only` | `run_architecture_audit_read_only.py`                | Run check-only architecture evidence diagnostics without pretest sync or artifact writes          |
| `report-hotspots`                | `generate_hotspot_degradation_report.py`              | Generate performance hotspot degradation report                                                   |
| `report-duplication-baseline`    | `report_duplication_baseline.py`                      | Generate report-only duplication baseline for `composition`/`application`                         |
| `report-artifact-duplication-audit` | `report_artifact_duplication_audit.py`              | Generate/check exact-byte duplication audit for JSCPD-excluded config, contract, and registry artifacts |
| `analyze-duplicate-functions`    | `analyze_duplicate_functions.py`                      | Compatibility wrapper for the legacy AST duplicate-function analyzer                              |
| `calibrate-hotspots`             | `scripts/engineering/qa/calibrate_hotspot_budgets.py` | Calibrate hotspot budgets                                                                         |
| `run-tests`                      | `test_health.py`                                      | Run a named test-health lane and emit JUnit XML plus JSON summary                                 |
| `summarize-junit`                | `test_health.py`                                      | Aggregate existing JUnit XML into test-health JSON summary                                        |
| `test-health`                    | `test_health.py`                                      | Summarize historical lane history from recent `reports/quality/test-runs/*.json` evidence         |
| `_gen_cyclic_workflows`          | `_gen_cyclic_workflows.py`                            | Bounded generator of zero-arg Grok workflow cards; supporting catalog utility                     |
| `snapshot-sonarcloud-open`       | `snapshot_sonarcloud_open.py`                         | Bounded live SonarCloud OPEN-issue snapshot exporter; supporting catalog utility                  |

## When to Use

| Command                          | When                                                                                                                                             | Trigger                                    |
| -------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------ |
| `check-naming`                   | After adding/renaming classes, functions, or modules; enforces NAME-001..009 rules                                                               | CI gate (`architecture.yml`, every PR)     |
| `check-architecture`             | When reproducing or migrating the legacy infrastructure architecture check through the canonical QA entrypoint                                   | Manual, Makefile migration path            |
| `check-app-deps`                 | When reproducing or migrating the legacy application dependency check through the canonical QA entrypoint                                        | Manual, Makefile migration path            |
| `check-constructor-args`         | When reproducing or migrating the legacy constructor-args audit through the canonical QA entrypoint                                              | CI migration path, manual use              |
| `check-duplication-complexity-exemptions` | After editing `.github/workflows/duplication-complexity.yml` or the exemption registry; keeps owner/expiry metadata in sync                 | CI gate (`duplication-complexity.yml`)     |
| `check-c901`                     | After modifying complex functions; prevents new C901 violations above baseline                                                                   | CI gate (`import-linter.yml`, every PR)    |
| `check-naming-pkg`               | After restructuring packages or adding new modules; enforces factory isolation                                                                   | CI gate (`architecture.yml`)               |
| `check-exemptions`               | After modifying quality exemption registry                                                                                                       | CI gate (`architecture.yml`)               |
| `check-xwalk-missing-backlog`    | After changing provider xwalk CSV files; prevents new `MISSING_*` schema gaps without explicit classification and owner issue                    | Data-contract governance gate              |
| `generate-debt-tasks`            | Before a debt-reduction campaign; creates the canonical refactoring task backlog from the registry                                               | Manual, on-demand                          |
| `reduce-architecture-debt`       | Before running the debt-reduction agent; classifies latest tasks into an execution order                                                         | Manual, on-demand                          |
| `check-terminology`              | After adding domain terms; validates code uses canonical terminology per `glossary.md`                                                           | CI gate (`architecture.yml`)               |
| `report-dep-map`                 | After changing imports in `src/bioetl/`; use `--check` for drift detection, `--update` to regenerate                                             | Pre-commit hook + CI gate                  |
| `report-vcr-metadata`            | When updating VCR fixture governance rollout or sidecar inventory; use `--check` for drift detection, `--update` to regenerate                   | Architecture / test-governance maintenance |
| `report-provider-contract-drift` | When reviewing provider-facing API drift in PR/CI; writes a machine-readable replay report and can fail on warnings/breaking drift               | Provider contract replay CI gate           |
| `report-domain-io-taint-inventory` | After changing Domain imports or I/O-adjacent calls; use `--check` to detect stale or unreviewed taint evidence                               | Architecture governance / CI drift check   |
| `check-prometheus-rules`         | After changing repo-backed Prometheus rule files or promtool vector tests; default covers observability and control-plane rule files; use `--runner docker` in CI | Observability rule validation gate         |
| `report-dashboard-inventory`     | When validating shipped Grafana dashboards against docs, provisioning, or exported/deployed snapshots; use `--health-summary` for a local rollup | Dashboard governance / drift check         |
| `report-dashboard-panel-audit-matrix` | When shipped dashboard panel audit metadata must match the generated docs mirror                                                        | Docs CI dashboard governance gate          |
| `report-dashboard-scalar-density` | After changing scalar panel geometry or density policy; use `--check` to fail on non-allowlisted sparse groups                         | Dashboard density governance gate          |
| `report-panel-title-inventory`   | After changing shipped Grafana dashboard panel titles or layout rows; use `--check` to catch generated mirror drift                              | Docs CI dashboard governance gate          |
| `report-dashboard-promql-scope`  | After changing dashboard PromQL, selectors, or deprecated observability metrics; use `--check` to catch forbidden `run_id` selectors and stale metric tokens | Dashboard PromQL governance gate           |
| `report-family-baseline`         | When reviewing RF-06 hotspot-family budgets or checking that the committed family baseline artifacts still match the code                        | Manual, preflight / CI drift check         |
| `report-flaky-test-burndown-review` | After changing the curated flaky inventory or test-governance snapshot; use `--check` to fail on missing or stale review evidence              | Test governance / CI drift check           |
| `report-dashboard-scenes-parity` | After changing shipped dashboard panels or ADR-053 route mappings; use `--check` to fail closed on parity drift | Optional Scenes shadow parity |
| `report-adr-enforcement-matrix`  | When accepted ADR coverage must be mapped to implementation owners and enforcement owners                                                        | Architecture governance / CI drift check   |
| `report-module-coverage`         | After changing `src/bioetl/` imports or adding modules; use `--check --allow-missing-coverage-xml` for hash-only refresh, `--check` for full drift | Module coverage / CI drift check            |
| `check-branch-coverage`          | After changing branch coverage gates; enforces `reports/coverage/coverage.xml` thresholds                                                      | CI coverage gate                           |
| `report-contract-coverage-matrix` | After changing entity configs or contracts; validates cross-entity coverage                                                                  | Contract governance / CI drift check       |
| `report-port-adapter-factory-coverage` | After changing port-adapter factories; validates core coverage matrix                                                                  | Architecture governance / CI drift check   |
| `report-compatibility-importer-census` | After changing sanctioned seams or twin modules; generates deterministic census                                                        | Architecture / importer governance         |
| `report-dead-code-inventory`     | After removing code; use `--check` to detect stale dead-code inventory                                                                        | Code hygiene / CI drift check              |
| `check-docs-drift`               | After changing docs; validates forbidden-pattern drift                                                                                       | Docs governance / CI drift check           |
| `report-observability-metric-inventory` | After changing observability metrics; use `--check` for drift                                                                         | Observability / CI drift check             |
| `validate-dq-consistency`        | After changing DQ configs; validates policy/config consistency                                                                               | DQ governance / CI drift check             |
| `report-lazy-import-inventory`   | After changing lazy imports; use `--check` for drift                                                                                       | Architecture / lazy import governance      |
| `report-source-tree-manifest`    | After changing source tree; generates manifest for hash tracking                                                                           | Governance / manifest drift check          |
| `check-dashboard-performance-budgets` | After changing dashboard performance budgets; validates budgets                                                                        | Dashboard governance / CI drift check      |
| `report-invariant-audit-rebaseline` | When converting architecture/invariant audits into GitHub issues; validates stale paths, current anchors, and duplicate issue evidence        | Audit governance / issue triage gate       |
| `report-architecture-debt-remote-main-baseline` | Before debt closeout; records clean `origin/main` architecture debt evidence from Git tree blobs                                      | Architecture debt closeout / CI drift check |
| `report-debt-governance-gates`   | Before debt-reduction closeout; aggregates quality artifacts into normalized pass/fail/warn fail-fast gates                                      | Architecture debt closeout / CI gate       |
| `validate-technical-debt-audit`  | When consuming or refreshing a technical-debt audit; rejects ambiguous reports, stale evidence hashes, and semantic headline drift                | Audit lifecycle / semantic drift gate      |
| `run-architecture-audit-read-only` | When collecting architecture audit evidence without allowing dev-wrapper pretest sync or generated-artifact writes                         | Manual, read-only audit                    |
| `report-hotspots`                | After performance benchmark runs; generates degradation report from JSONL observations                                                           | Manual, on-demand                          |
| `report-duplication-baseline`    | When reviewing duplication pressure in `composition` or `application`; generates report-only baseline artifacts without creating a blocking gate | Manual, on-demand                          |
| `analyze-duplicate-functions`    | When you need the older duplicate-function AST report through the canonical QA entrypoint                                                        | Manual, audit/reporting                    |
| `calibrate-hotspots`             | After collecting new performance observations; recalculates budget thresholds                                                                    | Manual, on-demand                          |
| `run-tests`                      | When a local or CI run should be recorded under a canonical `test_lanes` suite name                                                              | Local / CI test-health telemetry           |
| `summarize-junit`                | When an existing CI pytest job already wrote JUnit XML and should be folded into the test-health format                                          | CI test-health telemetry migration         |
| `test-health`                    | When reviewing recent lane history, failing nodeids, and skip/failure counts; historical evidence only, not the current coverage baseline        | Local / CI test-health reporting           |

Important distinction:

- `report-hotspots` is for benchmark-backed performance hotspots.
- `report-duplication-baseline` is for structural duplication visibility in `src/bioetl/composition` and `src/bioetl/application`.
- `report-artifact-duplication-audit` is for exact-byte duplication visibility
  in non-Python governance artifacts excluded by JSCPD, especially `configs/**`,
  contract snapshots/docs, and registry-backed quality artifacts.
- `reports/quality/hotspot-duplication-baseline.{json,md}` is the canonical
  multi-target duplication evidence surface. Specialized single-target artifacts
  such as `control-plane-duplication.*` and `runtime-builders-duplication.*`
  must be regenerated from the same command/ruleset and stay byte-for-byte
  aligned with the matching hotspot-baseline target rows.
- Source-tree size hotspots such as `>10 KB` files or `>350 LOC` files are a separate structural inventory and should be discussed as hotspot inventory, not as scorecard exemption debt.
- `check-c901` remains the clean blocking baseline for complexity debt; file-size scorecard numbers refer to exemption registry state unless a policy explicitly says otherwise.

Direct script path:

- `scripts/engineering/qa/report_duplication_baseline.py` (`python -m scripts.engineering.qa report-duplication-baseline`) generates report-only duplication baseline artifacts for governance review.
- `scripts/engineering/qa/run_architecture_audit_read_only.py` (`python -m scripts.engineering.qa run-architecture-audit-read-only`) runs check-only architecture diagnostics and fails if tracked governance surfaces mutate.
- `scripts/engineering/qa/generate_architecture_debt_tasks.py` (`python -m scripts.engineering.qa generate-debt-tasks`) generates the canonical architecture debt task backlog.
- `scripts/engineering/qa/reduce_architecture_debt.py` (`python -m scripts.engineering.qa reduce-architecture-debt`) builds the orchestration plan consumed by the architecture-debt agent.

## Canonical Commands

```bash
python scripts/engineering/qa/generate_architecture_dependency_map.py --check
python scripts/engineering/qa/generate_architecture_dependency_map.py --update
python scripts/engineering/qa/report_vcr_metadata_catalog.py --check
python scripts/engineering/qa/report_vcr_metadata_catalog.py --update
python -m scripts.engineering.qa check-vcr-replay-preflight --strict
python scripts/engineering/qa/report_provider_contract_drift.py --output reports/quality/provider-contract-drift-report.json --fail-on breaking
python -m scripts.engineering.qa report-domain-io-taint-inventory
python -m scripts.engineering.qa report-domain-io-taint-inventory --check
python -m scripts.engineering.qa report-family-baseline --check
python -m scripts.engineering.qa report-family-baseline --update
python -m scripts.engineering.qa report-flaky-test-burndown-review
python -m scripts.engineering.qa report-flaky-test-burndown-review --check
python -m scripts.engineering.qa report-adr-enforcement-matrix --check
python -m scripts.engineering.qa report-adr-enforcement-matrix --update
python -m scripts.engineering.qa report-invariant-audit-rebaseline --check
python -m scripts.engineering.qa report-invariant-audit-rebaseline --update
python -m scripts.engineering.qa report-architecture-debt-remote-main-baseline --check
python -m scripts.engineering.qa report-architecture-debt-remote-main-baseline --update
python -m scripts.engineering.qa report-debt-governance-gates --check
python -m scripts.engineering.qa report-debt-governance-gates --update
python -m scripts.engineering.qa validate-technical-debt-audit --json
python -m scripts.engineering.qa validate-technical-debt-audit --print-semantic-summary
python -m scripts.engineering.qa run-architecture-audit-read-only
python -m scripts.engineering.qa run-tests --suite unit-fast --skip-preflight -- --no-cov
python -m scripts.engineering.qa run-tests --suite unit-parallel-safe --skip-preflight -- --no-cov
python -m scripts.engineering.qa summarize-junit --suite unit-fast --junit-glob 'reports/test-telemetry/*.xml'
python -m scripts.engineering.qa test-health --last 30 --markdown-out reports/quality/test-runs/rollup.md
python -m scripts.engineering.qa test-health --suite coverage-verify --run-id coverage-verify-local --junit-glob 'reports/quality/test-runs/junit/*.xml' --last 30 --markdown-out reports/quality/test-runs/rollup.md
python -m scripts.engineering.qa report-dashboard-inventory --health-summary --json
python -m scripts.engineering.qa report-dashboard-inventory --deployed-dir /path/to/grafana-exports --check --json
python -m scripts.engineering.qa check-prometheus-rules
python -m scripts.engineering.qa check-prometheus-rules --rules-file grafana/prometheus-rules/bioetl_control_plane_current_status.yml
python -m scripts.engineering.qa report-dashboard-panel-audit-matrix --check
python -m scripts.engineering.qa report-dashboard-scalar-density --check
python -m scripts.engineering.qa report-module-coverage --check --allow-missing-coverage-xml
python -m scripts.engineering.qa check-branch-coverage
python -m scripts.engineering.qa report-contract-coverage-matrix --check
python -m scripts.engineering.qa report-port-adapter-factory-coverage --check
python -m scripts.engineering.qa report-compatibility-importer-census --check
python -m scripts.engineering.qa report-dead-code-inventory --check
python -m scripts.engineering.qa check-docs-drift
python -m scripts.engineering.qa report-observability-metric-inventory --check
python -m scripts.engineering.qa validate-dq-consistency
python -m scripts.engineering.qa report-lazy-import-inventory --check
python -m scripts.engineering.qa report-source-tree-manifest --check
python -m scripts.engineering.qa check-dashboard-performance-budgets
python scripts/engineering/qa/report_architecture_quality_scorecard.py
python -m scripts.engineering.qa report-panel-title-inventory --check
python -m scripts.engineering.qa report-dashboard-promql-scope --check
python scripts/engineering/qa/report_duplication_baseline.py
python -m scripts.engineering.qa report-artifact-duplication-audit --check
python -m scripts.engineering.qa check-architecture
python -m scripts.engineering.qa check-app-deps
python -m scripts.engineering.qa check-constructor-args
python -m scripts.engineering.qa check-duplication-complexity-exemptions
python -m scripts.engineering.qa check-xwalk-missing-backlog
python -m scripts.engineering.qa analyze-duplicate-functions
```

`run-tests` and `summarize-junit` classify failures with
`configs/quality/test_health_classifiers.yaml`. Those classes are
informational; pytest exit codes and quality gates remain the blocking source of
truth. `test-health` rollups and `reports/quality/test-runs/rollup.md` are
historical lane history only. The authoritative committed telemetry baseline
lives in `configs/quality/test_telemetry_baseline.yaml`, and current
merge-blocking coverage status remains owned by the live `coverage-verify` lane.

The legacy direct paths for the historical architecture, application-deps, and
constructor-args checks remain supported during the migration window, but new
integrations should use the grouped QA commands above. The grouped QA commands
now own the implementation, and the older direct paths have been removed in
favor of the unified entry point.
