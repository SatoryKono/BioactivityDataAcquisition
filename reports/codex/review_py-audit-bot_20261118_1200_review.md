# Static script lifecycle review — 2026-11-18

Review base: `ca9d5f411405f9bfe58e9db69e83efa0bbefb591`. Scope: 56 overdue supporting/registered scripts, independently reviewed before renewal to 2026-12-18. Existing owners, decisions and historical rationale are retained.

This is a monthly static necessity/current-consumer and I/O/dispatch-boundary review. All 56 source blobs were matched to the base and parsed (27,207 source lines); module APIs, selected I/O/dispatch functions and the current tracked caller/command anchors were inspected. This is not exhaustive functional or security qualification of every source line. No live provider, Docker/monitoring stack, user workbook transformation, destructive cleanup or runtime acceptance was exercised.

The previous IUPHAR branch recorded the same source identities at e44ca5d22ecc76befca3389e8c27abf4d0de18e0. Renewal metadata preserves that valid source anchor; this separate review adds independently observed findings and fixes on main. No IUPHAR acceptance, PASS, issue-closing directive, coverage metric, or quality ceiling is changed.

## Findings and remediation

- AUD-001: parity JSON output created the parent before resolving a relative destination. A rejected `../escape/report.json` could create the rejected directory; valid relative output from another working directory also failed. Resolve first, then create the resolved parent. Explicit absolute external destinations remain supported.
- AUD-002: architecture-suite, VCR-corpus and weak-assert reporters created only the JSON parent. A separate new Markdown directory caused FileNotFoundError. Create both independently resolved output parents.
- GitHub SonarCloud measured 3.3% new-code duplication after adding the missing parent creation to the three existing duplicate publication blocks (maximum 3%). The common publisher now lives in `scripts/engineering/common/report_outputs.py`, resolving both destinations and reusing the existing confined atomic text writer. Its three current callers and supporting lifecycle entry are explicit; no duplication threshold or exclusion was changed.

## Validation and limits

- Before fixes: the new six regression cases produced 5 failures and 1 pass, reproducing both defects and confirming explicit external parity output already worked.
- After fixes: `python -B -m pytest tests/unit/scripts/qa/test_lifecycle_review_output_destinations.py tests/unit/scripts/test_cli_dispatch.py tests/integration/ci/test_silver_gold_filter_parity.py tests/unit/scripts/repo/test_check_scripts_inventory_lifecycle.py -q --no-cov -o addopts=""` — 39 passed, no skips (prepared tree). Exact committed-head checks and GitHub CI are recorded separately in the PR.
- Adding the lifecycle registry/fast guards and debt scorecard tests: 75 passed, one existing Windows-only skip. The skipped fast guard was separately executed under WSL using the installed dev interpreter: one passed with its actual assertions. Full docs link checking and runtime-mirror/freshness drift checking also passed. Runtime source/mirrors were not modified.
- Read-only pre-task retrieval: DEGRADED (missing RAG/timeline artifacts); no refresh or persistent session note. Findings were verified against actual source.
- The expired-review count is reduced by 56 actual reviews, from 228 to 172 as of 2026-11-18. Both existing maximums of 172 remain unchanged. Review renewal does not increase a debt ceiling or waive an executable check.
- No product `src/bioetl` changes, data-contract change, provider request, coverage acceptance, telemetry measurement or historical measurement rebaseline.

## Per-file evidence

Each source hash below is SHA-256 of the reviewed base blob. The four repaired script blobs differ after remediation; their original source identities remain explicit.

### `scripts/ai/sync/governance.py`

Reviewed source SHA-256: `ad4f1eeeeec4639ae2a5216b5871ea5255bacd86a591c5579e80c74a0aa5ffd5`. Current tracked consumer/command: `scripts/ai/codex/doctor.py:41`. Owner: `@bioetl-platform`. Decision: `shared_helper_module`.

Retain the doctor/mirror helper: canonical-source injection and governed Codex/Devin/docs parity are still used. Inspected atomic writes, temporary mirror materialization and the explicit check-only/update boundary; no mirror update was executed.

### `scripts/data_quality/export_chembl_observed_vocab.py`

Reviewed source SHA-256: `8a89304034861a9a8a1bc4586d2932df9ce5caf7e05ee8a12e892d7d98c03927`. Current tracked consumer/command: `scripts/data_quality/__init__.py:5`. Owner: `@bioetl-platform`. Decision: `shared_helper_module`.

Retain deterministic tracked-Bronze vocabulary/profile export through the data-quality package. Its output helper resolves the operator destination before creating the parent, preserving explicit external destinations.

### `scripts/data_quality/run_silver_gold_filter_parity.py`

Reviewed source SHA-256: `43370fa8a445811f2133e5110bff8ee61ee3e27007b112fa599d5d380b392fcc`. Current tracked consumer/command: `scripts/data_quality/__init__.py:7`. Owner: `@bioetl-platform`. Decision: `shared_helper_module`.

Retain the ADR-050 deterministic parity harness and generated-artifact workflow consumer. AUD-001: the output helper creates a relative parent before resolving/rejecting traversal; renewal requires the bounded fix and regression evidence.

### `scripts/diagrams/core/diagram_paths.py`

Reviewed source SHA-256: `0cb6615e6472b638dd1c4f06f59a7fdb0823583077410fe82fad9ca0ebcc8b7d`. Current tracked consumer/command: `scripts/diagrams/check/check_class_method_render_integrity.py:27`. Owner: `@bioetl-platform`. Decision: `shared_helper_module`.

Retain the shared diagram-root/layout resolver used by the method-render integrity checker. The helper supports documented staged layouts and performs path selection without filesystem mutation.

### `scripts/diagrams/render/pipeline_dataflow_ir.py`

Reviewed source SHA-256: `3f7d62e8d15096b7e2a90d19275e2832f163b9a2eec56593344f63cb3af0074b`. Current tracked consumer/command: `scripts/diagrams/render/generate_pipeline_dataflows.py:13`. Owner: `@bioetl-platform`. Decision: `shared_helper_module`.

Retain typed deterministic pipeline IR for the canonical diagram producer. Inspected read-only Git source-date resolution, including non-merge HEAD fallback, and the live configuration/schema fact-loading interfaces.

### `scripts/diagrams/render/pipeline_dataflow_render.py`

Reviewed source SHA-256: `05ab0457f52ca5d2bc17896f1aab447723994ee9d79e964651ea4b9a2c19fbed`. Current tracked consumer/command: `scripts/diagrams/render/generate_pipeline_dataflows.py:14`. Owner: `@bioetl-platform`. Decision: `shared_helper_module`.

Retain the producer's pure Mermaid/passport/CSV/description projection layer. Rendering returns destination-keyed text; it does not itself write files or establish live diagram acceptance.

### `scripts/docs/common/markdown.py`

Reviewed source SHA-256: `060dcf9919f2c571a28007df65046ceb222b63ede1f9141c13239617bb210b8e`. Current tracked consumer/command: `scripts/docs/checks/check_links.py:84`. Owner: `@bioetl-docs`. Decision: `shared_helper_module`.

Retain shared heading/navigation parsing consumed by the link checker. Its small read/parser API avoids a second command surface.

### `scripts/docs/common/paths.py`

Reviewed source SHA-256: `bab926b902f8f644acfbd30cb41d4d39a324253b312f4f748b858d1aff333bcb`. Current tracked consumer/command: `scripts/docs/checks/check_links.py:92`. Owner: `@bioetl-docs`. Decision: `shared_helper_module`.

Retain shared repository/docs roots and generated-artifact classification used by docs checks. The module supplies path facts rather than an executable migration.

### `scripts/docs/common/xlsx.py`

Reviewed source SHA-256: `0480098d6dfbc030302fa7cd3ea4102a673334e682317a02b915e00592a7ea56`. Current tracked consumer/command: `scripts/docs/matrix/build_matrix_dicts.py:25`. Owner: `@bioetl-docs`. Decision: `shared_helper_module`.

Retain the low-level XLSX ZIP/XML cell, shared-string, sheet-target and dimension helpers imported by matrix tooling. Reviewed the source API; no user workbook was modified or functionally qualified.

### `scripts/docs/fixers/fix_links_explicit.py`

Reviewed source SHA-256: `41ea7cfd2d8ac8cb7a69147a868397975302d30f5e8f596bf3daf84b870062b8`. Current tracked consumer/command: `scripts/docs/__main__.py:60`. Owner: `@bioetl-platform`. Decision: `shared_helper_module`.

Retain the registered explicit-link maintenance command. Its rewrite scope is the fixed DOCS_DIR/FIX_MAP contract, and writes occur only for changed Markdown; the fixer was not applied to repository documents during review.

### `scripts/docs/fixers/link_warnings.py`

Reviewed source SHA-256: `9365c1e7f553a14d3031ca4958880ae8687480bd310906c7c726d6ba1f550bcf`. Current tracked consumer/command: `scripts/docs/__main__.py:61`. Owner: `@bioetl-platform`. Decision: `shared_helper_module`.

Retain the registered Mermaid warning fixer. Inspected repository confinement and rebuilding of the safe file path before a changed-content/LF-normalized write.

### `scripts/docs/fixers/sentence_audit.py`

Reviewed source SHA-256: `05cc3de17643c337e11e22de5be9fa36f6258b26825edcbc56a06f694e42ebfa`. Current tracked consumer/command: `scripts/docs/__main__.py:62`. Owner: `@bioetl-platform`. Decision: `shared_helper_module`.

Retain the docs router's source-evidence sentence audit/report generator. Reviewed separate extraction/risk/evidence/report interfaces and SOURCE_DATE_EPOCH timestamp handling; its matches are audit candidates, not runtime qualification.

### `scripts/docs/matrix/build_matrix_dicts.py`

Reviewed source SHA-256: `b22c4943358d623656cc8cb42b227db3aeea3cfbb19e024e8bddfdd4dc6cba86`. Current tracked consumer/command: `scripts/docs/__main__.py:54`. Owner: `@bioetl-platform`. Decision: `shared_helper_module`.

Retain the registered workbook dictionary/value-inventory producer. Inspected XLSX helper consumption, conflicting detail identity checks and temporary-YAML/os.replace publication.

### `scripts/docs/matrix/normalize_values.py`

Reviewed source SHA-256: `93977f6d3791288679e65884b8eff0ee4d250bdfb77eafbf6e46a5b832b6ba60`. Current tracked consumer/command: `scripts/docs/__main__.py:57`. Owner: `@bioetl-platform`. Decision: `shared_helper_module`.

Retain the registered controlled-vocabulary workbook normalizer. Reviewed canonicalization and explicit input/output/mapping publication boundaries, including the temporary-workbook replacement path; no workbook transformation was run.

### `scripts/docs/matrix/structural_contract.py`

Reviewed source SHA-256: `722d4dcbc76d18e1c6afbbd8f32a538432cc097ac6aebbe6ff055de60ea32c20`. Current tracked consumer/command: `scripts/docs/matrix/export_structural_contract.py:19`. Owner: `@bioetl-docs`. Decision: `shared_helper_module`.

Retain the structural export consumer's runtime-to-workbook semantic mapping and stable JSON row contract. The inspected persistence function is an explicit export, not an automatic runtime or evidence refresh.

### `scripts/docs/passports/rename_underscore_to_hyphen.py`

Reviewed source SHA-256: `4e9c31d509902fa47bc331ab68883b0687d06adaf2c8aeef92bc4e67cd397041`. Current tracked consumer/command: `scripts/docs/__main__.py:66`. Owner: `@bioetl-platform`. Decision: `shared_helper_module`.

Retain the router-exposed passport-path migration/check tool. Inspected dry-run/apply separation, constant reference traversal and confined reference rewriting; no passport rename was performed.

### `scripts/docs/passports/source_facts.py`

Reviewed source SHA-256: `93d5897ed483293e7d4957cd5d5475cb5ab1dea55f2e682eb4b86bf56084b5a2`. Current tracked consumer/command: `scripts/diagrams/render/pipeline_dataflow_ir.py:21`. Owner: `@bioetl-platform`. Decision: `shared_helper_module`.

Retain the canonical effective-configuration fact loader imported by the pipeline IR producer, avoiding a second configuration-merge implementation.

### `scripts/engineering/ci/_compatibility_registry.py`

Reviewed source SHA-256: `c9b76e4cc07617166be02ebb16043011ae1be0bd691b8fb9e559d34f9c9f1dbc`. Current tracked consumer/command: `scripts/engineering/ci/_compatibility_telemetry.py:25`. Owner: `@bioetl-platform`. Decision: `shared_helper_module`.

Retain the telemetry-imported compatibility registry loader. Reviewed strict measured-module name validation, argv-list ripgrep dispatch and Python fallback; no registry budget was changed.

### `scripts/engineering/ci/_compatibility_telemetry.py`

Reviewed source SHA-256: `a4b38f785910ab54bf4fad88524ba4f32a7a89cc9d282da19152e72bacac3916`. Current tracked consumer/command: `scripts/engineering/ci/quality_integral_gate.py:30`. Owner: `@bioetl-platform`. Decision: `shared_helper_module`.

Retain compatibility and debt snapshots consumed by quality_integral_gate. Committed-artifact collection is distinct from live scanning and required JSON integer fields fail closed.

### `scripts/engineering/common/cli_dispatch.py`

Reviewed source SHA-256: `ba6497eb3082cede709411e0a13c8fd13fc4b7f715a0d36f0f39b5a613af3f75`. Current tracked consumer/command: `scripts/ai/mcp/__main__.py:20`. Owner: `@bioetl-platform`. Decision: `shared_helper_module`.

Retain the shared routers dispatch module. Reviewed explicit runner selection, required base_dir for script runners, argv-list subprocess invocation and in-process module dispatch boundary.

### `scripts/engineering/qa/check_duplication_complexity_exemptions.py`

Reviewed source SHA-256: `fc8946124812d913362b5ccad55faf6515c9c414894663d1c12645c5c73181e4`. Current tracked consumer/command: `scripts/engineering/qa/__main__.py:109`. Owner: `@bioetl-platform`. Decision: `shared_helper_module`.

Retain the registered duplication/complexity exemption validator. Metadata and synchronized-expiry-cliff validation remain enforced; no exemptions were added.

### `scripts/engineering/qa/config_surface_governance.py`

Reviewed source SHA-256: `78cf3f48d606fb05a8822a1635e29d444485d23e24a95926403981c602b98661`. Current tracked consumer/command: `scripts/engineering/qa/report_config_surface_backlog.py:20`. Owner: `@bioetl-platform`. Decision: `shared_helper_module`.

Retain the shared sanctioned-partial-key policy imported by config-matrix governance. This is a small predicate helper, not another artifact producer.

### `scripts/engineering/qa/docker_stability_campaign/runner.py`

Reviewed source SHA-256: `20afb811ab51de051fa0dbe39245e573397e767588044dbb7a3f1eb14d90feda`. Current tracked consumer/command: `scripts/engineering/qa/run_docker_stability_campaign.py:15`. Owner: `@bioetl-platform`. Decision: `shared_helper_module`.

Retain the resumable campaign implementation imported by its CLI. Reviewed immutable campaign identity, signing-key fingerprint, empty destination and evidence-index checks; no Docker campaign was executed.

### `scripts/engineering/qa/extract_uniprot_semantic_payload_vocab.py`

Reviewed source SHA-256: `c8aee384323ad2777ace1095d0ec5a6d0fd10c44177fcd0b612f082239143107`. Current tracked consumer/command: `scripts/engineering/qa/report_non_chembl_observed_value_inventory.py:25`. Owner: `@bioetl-platform`. Decision: `shared_helper_module`.

Retain the semantic payload vocabulary extractor used by semantic QA. Reviewed JSONL field collection and explicit optional JSON destination; no live provider request occurs in this module.

### `scripts/engineering/qa/file_discovery.py`

Reviewed source SHA-256: `53e126b6902e61f7aed680151f6618b7e7e6a822e2f91f186bf9cbdc154d0693`. Current tracked consumer/command: `scripts/engineering/qa/import_graph_inventory.py:24`. Owner: `@bioetl-platform`. Decision: `shared_helper_module`.

Retain stable rooted file discovery imported by QA inventories. Reviewed directory pruning and absent-root empty result; traversal does not mutate files.

### `scripts/engineering/qa/hotspot_family_metrics.py`

Reviewed source SHA-256: `8e8f92363781a13b03655ba72e33703a3aaed07e98a42c93a1eb77503ef87752`. Current tracked consumer/command: `scripts/engineering/qa/report_hotspot_family_baseline.py:14`. Owner: `@bioetl-platform`. Decision: `shared_helper_module`.

Retain RF-06 hotspot metrics imported by the family reporter. Reviewed tracked-file Git enumeration/fallback and static AST facade, fan-in and LOC classification; ceilings remain unchanged.

### `scripts/engineering/qa/import_graph_inventory.py`

Reviewed source SHA-256: `7c4fc380915799ab3348ce6599f95f09d8a4837b8880371dfb15c139eba939a1`. Current tracked consumer/command: `scripts/engineering/qa/report_compatibility_importer_census.py:1145`. Owner: `@bioetl-platform`. Decision: `shared_helper_module`.

Retain shared import graph analysis used by dead-code/architecture inventory. Reviewed explicit static/dynamic/type-only projections and surfaced parse/read failures; cache publication is best-effort and does not establish runtime import acceptance.

### `scripts/engineering/qa/private_import_exception_metadata.py`

Reviewed source SHA-256: `b0da27a9c404bddb3bdb354f41e19b558d41a183048fe23c8f86ee3c6628665c`. Current tracked consumer/command: `scripts/engineering/qa/report_private_import_inventory.py:23`. Owner: `@bioetl-architecture`. Decision: `shared_helper_module`.

Retain private-import exception metadata enforcement. Scope, unique ids/pairs, owner, rationale, executable enforcement and dated exit conditions are checked; source comments do not grant waivers.

### `scripts/engineering/qa/report_adr_enforcement_matrix.py`

Reviewed source SHA-256: `a696a2fefec686d03a1af903cd040486203c56f3c80d787573d56e5b75a8d0bb`. Current tracked consumer/command: `scripts/engineering/quality/architecture_quality_scorecard.py:14`. Owner: `@bioetl-platform`. Decision: `legacy_manual_utility`.

Retain accepted-ADR matrix production consumed by architecture evidence. Reviewed tracked-only reference scans, argv-safe fallback discovery and resolve-before-write JSON/Markdown destinations.

### `scripts/engineering/qa/report_architecture_debt_remote_main_baseline.py`

Reviewed source SHA-256: `38cc90588124a210e0e87b7c81a672ccbc8b738446d7ed797ce06823a3932e55`. Current tracked consumer/command: `scripts/engineering/qa/__main__.py:173`. Owner: `@bioetl-platform`. Decision: `legacy_manual_utility`.

Retain the registered remote-main baseline owner. Reviewed immutable commit resolution, exact Git blob lookup, conflict-marker rejection and semantic comparison that excludes volatile commit metadata.

### `scripts/engineering/qa/report_architecture_quality_scorecard.py`

Reviewed source SHA-256: `44aa5bd67bda2f7928335fcf4fb98f4d5ca0262fb55cea2cff494cb32b4ac8ce`. Current tracked consumer/command: `scripts/engineering/qa/refresh_governance_artifacts.py:357`. Owner: `@bioetl-platform`. Decision: `legacy_manual_utility`.

Retain canonical architecture scorecard regeneration. Reviewed unique existing test-symbol binding for aggregate invariants before scorecard publication; this command mutates governed artifacts and was not invoked as a read-only audit.

### `scripts/engineering/qa/report_architecture_suite_burndown.py`

Reviewed source SHA-256: `5b2f33586e663432d6264369871506dbc8ebe20765cbb92e832e36b2c903068e`. Current tracked consumer/command: `scripts/engineering/qa/__main__.py:153`. Owner: `@bioetl-platform`. Decision: `shared_helper_module`.

Retain registered architecture-suite census. AUD-002: JSON and Markdown destinations resolve independently but only the JSON parent is created; repair separate Markdown-directory output with a CLI regression.

### `scripts/engineering/qa/report_artifact_duplication_audit.py`

Reviewed source SHA-256: `cef4f3c9c1b0c66997b4c812557ef9e77b340d213f477398c41ec1f45fa7e4ba`. Current tracked consumer/command: `scripts/engineering/qa/__main__.py:161`. Owner: `@bioetl-platform`. Decision: `legacy_manual_utility`.

Retain registered non-JSCPD exact-byte artifact duplication audit. Reviewed explicit scoped tracked discovery and check-versus-write behavior; optional max-duplicate-group ceiling remains enforced.

### `scripts/engineering/qa/report_cast_any_typing_census.py`

Reviewed source SHA-256: `eac62a506ec9d324473cc87c887d8ed9b4a875ea6773109f07bfdff9b93dc80f`. Current tracked consumer/command: `scripts/engineering/qa/__main__.py:180`. Owner: `@bioetl-architecture`. Decision: `shared_helper_module`.

Retain registered cast(Any) census. Reviewed bounded statement-window justification categories and atomic temp/os.replace output; free-form reason tags remain visible instead of granting justification.

### `scripts/engineering/qa/report_chembl_observed_value_inventory.py`

Reviewed source SHA-256: `22586af79f4fc1591c629e796c0f88519a86bb357ee75b1fc3786804840c4e54`. Current tracked consumer/command: `scripts/engineering/qa/__main__.py:166`. Owner: `@bioetl-platform`. Decision: `shared_helper_module`.

Retain tracked ChEMBL observed-value inventory. Reviewed fixture-entry/source-summary interfaces and separate JSON/CSV/text outputs; observed fixture values are not claims about all provider data.

### `scripts/engineering/qa/report_config_surface_backlog.py`

Reviewed source SHA-256: `f285b47e128183e1fac66986617b3c7f42cdcaad94c81a994b676a4af57fb24d`. Current tracked consumer/command: `scripts/engineering/qa/report_live_residual_snapshot.py:76`. Owner: `@bioetl-platform`. Decision: `legacy_manual_utility`.

Retain config-surface backlog owner used by family metrics. Reviewed nested/shadow duplicate-cluster collapse rules and atomic-write/fallback boundary; no duplication ceiling is increased.

### `scripts/engineering/qa/report_domain_io_taint_inventory.py`

Reviewed source SHA-256: `02327160fab438bda845b5b1969b4267da409ad8822774dc9d0895a92c8a60e3`. Current tracked consumer/command: `scripts/engineering/qa/__main__.py:137`. Owner: `@bioetl-architecture`. Decision: `shared_helper_module`.

Retain registered domain I/O static enforcement reporter. Reviewed documented non-interprocedural limits and resolve-before-parent/write JSON publication; pure path/URL value operations are distinct from I/O.

### `scripts/engineering/qa/report_domain_ports_inventory.py`

Reviewed source SHA-256: `78f7a2291690e6840207cd7cccf1b91da36198fe518daa0557d1dbc336876bba`. Current tracked consumer/command: `scripts/engineering/qa/__main__.py:140`. Owner: `@bioetl-architecture`. Decision: `shared_helper_module`.

Retain registered domain-port inventory. Reviewed explicit Protocol/decorator/module denominators and destination resolution before publication; counts are static inventory, not adapter behavior qualification.

### `scripts/engineering/qa/report_flaky_test_burndown_review.py`

Reviewed source SHA-256: `92ee6530240505176b54c349eb476639819a51bde123f664e1612d435950012e`. Current tracked consumer/command: `scripts/engineering/qa/__main__.py:143`. Owner: `@bioetl-platform`. Decision: `shared_helper_module`.

Retain registered flaky-test review producer. Reviewed required empirical JUnit fields/identical node coverage separately from static evidence and confined atomic output; no empirical stability was invented.

### `scripts/engineering/qa/report_port_adapter_factory_coverage.py`

Reviewed source SHA-256: `d896d9acf734a447d409d8022046992cb0339e24f4f6eeae9f2af2338f660a20`. Current tracked consumer/command: `scripts/engineering/qa/__main__.py:146`. Owner: `@bioetl-architecture`. Decision: `shared_helper_module`.

Retain registered port-adapter-factory coverage matrix. Reviewed existence/symbol/test evidence checks and row construction; static linkage does not substitute for exercised adapter acceptance.

### `scripts/engineering/qa/report_test_governance_audit.py`

Reviewed source SHA-256: `3a948e97549cc1268b21c7c9f532a215b8be9c889746b7fa1c3a379291ea6f38`. Current tracked consumer/command: `.github/workflows/tests.yml:439`. Owner: `@bioetl-platform`. Decision: `legacy_manual_utility`.

Retain canonical test-governance scanner used by the evidence workflow. Reviewed source fingerprint, assert reachability and bounded hashing interfaces; its UTF-16 recovery can rewrite inputs, so the scanner is not represented as unconditionally read-only.

### `scripts/engineering/qa/report_vcr_corpus_budget.py`

Reviewed source SHA-256: `50045247607ad07f37abfdbb3a1658ce7e2930ce3aaf7ec81299a00b455a5bed`. Current tracked consumer/command: `scripts/engineering/qa/__main__.py:152`. Owner: `@bioetl-platform`. Decision: `shared_helper_module`.

Retain registered VCR corpus census. AUD-002 also affects its separate Markdown directory; repair publication without changing any corpus-size budget.

### `scripts/engineering/qa/report_weak_assert_inventory.py`

Reviewed source SHA-256: `4fef43ceaad7bf3e914622dae2ca7e3250414af806b1ce0372c4fe2229d30d37`. Current tracked consumer/command: `scripts/engineering/qa/__main__.py:151`. Owner: `@bioetl-platform`. Decision: `shared_helper_module`.

Retain advisory weak-assert census. AUD-002 also affects its separate Markdown directory; retain advisory/static semantics and repair publication only.

### `scripts/engineering/qa/run_architecture_audit_read_only.py`

Reviewed source SHA-256: `afc9307f511ec08e7e9133c0ff710f7f834341a7c91587e4dc0ad9b8c23f65d3`. Current tracked consumer/command: `scripts/engineering/qa/__main__.py:204`. Owner: `@bioetl-architecture`. Decision: `shared_helper_module`.

Retain explicit read-only architecture runner. Reviewed tracked-status mutation guard, timeout/failure diagnostics and child environment construction; no full architecture acceptance is claimed from this static lifecycle review.

### `scripts/engineering/qa/technical_debt_audit_registry.py`

Reviewed source SHA-256: `c64fc136e65853274436ffb84e54ab853227579d9d1fb961ae89489f59e2cb6f`. Current tracked consumer/command: `scripts/engineering/qa/__main__.py:201`. Owner: `@bioetl-architecture`. Decision: `shared_helper_module`.

Retain SHA-pinned technical-debt audit registry enforcement. Reviewed safe relative paths, commit existence, ordered content hashes and semantic report checks; current audit identity is not reset.

### `scripts/engineering/repo/_branch_cleanup_policy.py`

Reviewed source SHA-256: `d6766c934334c8c18bc323aa7903616e5f3bad41ab4309680ee1aaa072770f7a`. Current tracked consumer/command: `scripts/engineering/repo/branch_cleanup.py:47`. Owner: `@bioetl-platform`. Decision: `shared_helper_module`.

Retain shared branch cleanup policy. Reviewed dry-run owner/worktree classifications and explicit prohibition on automatically applying delete proposals; no branches or worktrees were removed.

### `scripts/engineering/repo/_root_governance.py`

Reviewed source SHA-256: `bb77f623d90875962f974668e2dc9ce8c98e92b7093d83b28611dc027ee3af66`. Current tracked consumer/command: `scripts/engineering/diagnostics/audit_structure.py:32`. Owner: `@bioetl-platform`. Decision: `shared_helper_module`.

Retain shared root-governance policy loading. Reviewed canonical catalog/allowlist inputs and blocked cleanup-zone predicate; this helper does not perform cleanup itself.

### `scripts/ops/observability/check_prometheus_rules_health.py`

Reviewed source SHA-256: `06fb89ccc635ed28fab36a743f8dcd946f8c4d6e677d88cb31013114b42d9ff6`. Current tracked consumer/command: `scripts/engineering/qa/check_prometheus_rules.py:717`. Owner: `@bioetl-observability`. Decision: `shared_helper_module`.

Retain live Prometheus rule-health checker used by runtime monitoring diagnostics. Reviewed rule/evaluation and lexical expression parity interfaces; no network request or monitoring stack was started.

### `scripts/ops/observability/grafana/_evidence_readability.py`

Reviewed source SHA-256: `a5be2ee91aa8620a05fc72ba650f9286be39ca8061f6d9b2510e69e0119baee3`. Current tracked consumer/command: `scripts/ops/observability/grafana/render_nav_bus.py:2627`. Owner: `@bioetl-platform`. Decision: `shared_helper_module`.

Retain provisioned-dashboard readability projection consumed by generation. Reviewed selected-run envelope/layout and verdict-preservation interfaces; static model edits do not establish browser readability acceptance.

### `scripts/ops/observability/grafana/capture_acceptance.py`

Reviewed source SHA-256: `8a249ff215992e9cd0d95cf3b783d884da7789075fda6643bf5729af819377a0`. Current tracked consumer/command: `scripts/ops/observability/grafana/check_grafana_dashboard_audit_preflight.py:1947`. Owner: `@bioetl-platform`. Decision: `shared_helper_module`.

Retain immutable capture assessment used by capture verification. Reviewed confined output, shipped-dashboard overwrite refusal, source-bound review and separate layout/accessibility provenance conditions; absent evidence remains NOT_PROVEN.

### `scripts/ops/observability/grafana/capture_provenance.py`

Reviewed source SHA-256: `77a9e3ab25b1d2a8fa5a1959b2a3ac39e894568427c02ca4eea90f343e614b2f`. Current tracked consumer/command: `scripts/ops/observability/grafana/capture_acceptance.py:655`. Owner: `@bioetl-platform`. Decision: `shared_helper_module`.

Retain capture provenance verification imported by assessment. Reviewed exact committed JSON/model identity, capture attachment confinement, PNG/browser context and expanded-row evidence; no capture acceptance was asserted.

### `scripts/ops/observability/grafana/dashboard_state_fixture_v2.py`

Reviewed source SHA-256: `fe8d4408c4e9b6d954320005c26820eac1f9f2dd9aa47161c8fba5673264e6ef`. Current tracked consumer/command: `scripts/ops/observability/grafana/rerender_grafana_screenshots.py:709`. Owner: `@bioetl-platform`. Decision: `shared_helper_module`.

Retain optional renderer fixture loader. Reviewed case loading/digest and fail-closed expected-versus-actual classification; fixture stub operation is separate from the default live render path.

### `scripts/ops/observability/grafana/recover_renderer.py`

Reviewed source SHA-256: `55f33544a6d0ed7a791ebd6b818ca35ff8db060328dd451f4c31f1fd179a67da`. Current tracked consumer/command: `scripts/ops/runtime/docker/runtime_manager.py:2804`. Owner: `@bioetl-observability`. Decision: `shared_helper_module`.

Retain explicit renderer-only recovery command used by runtime manager. Reviewed argv-list timeouts, no-deps renderer recreation, check-only health and UI probing; no recovery or Docker command was executed.

### `scripts/ops/observability/trust_validation_fixture_materialization.py`

Reviewed source SHA-256: `04d67bbb1adae80290a8e0e6d1d8a1c0a1aa5e0710f1f28e83e86c0dbb2e214b`. Current tracked consumer/command: `scripts/ops/observability/grafana/generate_trust_validation_fixtures.py:33`. Owner: `@bioetl-observability`. Decision: `shared_helper_module`.

Retain bounded Trust fixture matrix materializer imported by validation. Reviewed supplied matrix/panel map, output files and index/status derivation; fixture output is not live control-plane acceptance.

### `scripts/ops/runtime/docker/runtime_manager.py`

Reviewed source SHA-256: `ace344c282fef36d986f284cd0483c2403ae61e8a4a9404d9daa4ae5c166126b`. Current tracked consumer/command: `scripts/ops/runtime/docker/docker_runtime_probe.py:41`. Owner: `@bioetl-platform`. Decision: `shared_helper_module`.

Retain optional runtime lifecycle manager imported by readiness tooling. Reviewed scoped environment restoration, bounded recovery and redacted diagnostics plus separate main/monitoring readiness paths; no service lifecycle action was executed.

### `scripts/schema/generation/generate_protein_class_l1_target_type_artifacts.py`

Reviewed source SHA-256: `440ae35e3add9da92c7ac9fe941212f1376dbf8b69a7a52f236ab3117c01973b`. Current tracked consumer/command: `scripts/schema/__main__.py:43`. Owner: `@bioetl-platform`. Decision: `shared_helper_module`.

Retain registered protein-class target-type artifact generator. Reviewed CSV row loading, source/artifact hashes, manifest counts and check-versus-write boundary; no classification acceptance or source-data change is implied.
