# CodeRabbit full scope matrix — 20260813

- **BASE_SHA:** `91b02403dfd077ca374a7bdb7cd0b7082e557e39`
- **CodeRabbit:** `0.7.2`
- **Cap:** ≤300 files per leaf
- **Leaves:** 87
- **Tracked / assigned:** 10888 / 10888
- **Duplicate assignments:** 0
- **Coverage exact:** `True`

| leaf_id | wave | files | under_cap | selection |
|---|---:|---:|---|---|
| `S01-domain-aggregates` | A | 19 | `true` | src/bioetl/domain/aggregates |
| `S01-domain-behavior` | A | 53 | `true` | src/bioetl/domain/behavior |
| `S01-domain-composite` | A | 30 | `true` | src/bioetl/domain/composite |
| `S01-domain-config` | A | 12 | `true` | src/bioetl/domain/config |
| `S01-domain-contracts` | A | 23 | `true` | src/bioetl/domain/contracts |
| `S01-domain-control_plane` | A | 32 | `true` | src/bioetl/domain/control_plane |
| `S01-domain-entities` | A | 28 | `true` | src/bioetl/domain/entities |
| `S01-domain-exceptions` | A | 24 | `true` | src/bioetl/domain/exceptions |
| `S01-domain-filtering` | A | 13 | `true` | src/bioetl/domain/filtering |
| `S01-domain-lineage` | A | 6 | `true` | src/bioetl/domain/lineage |
| `S01-domain-mapping` | A | 15 | `true` | src/bioetl/domain/mapping |
| `S01-domain-models` | A | 7 | `true` | src/bioetl/domain/models |
| `S01-domain-normalization` | A | 88 | `true` | src/bioetl/domain/normalization |
| `S01-domain-ports` | A | 77 | `true` | src/bioetl/domain/ports |
| `S01-domain-registry` | A | 6 | `true` | src/bioetl/domain/registry |
| `S01-domain-residual-root` | A | 31 | `true` | src/bioetl/domain |
| `S01-domain-run_reports` | A | 10 | `true` | src/bioetl/domain/run_reports |
| `S01-domain-schemas` | A | 49 | `true` | src/bioetl/domain/schemas |
| `S01-domain-transformations` | A | 5 | `true` | src/bioetl/domain/transformations |
| `S01-domain-types` | A | 24 | `true` | src/bioetl/domain/types |
| `S01-domain-validation` | A | 4 | `true` | src/bioetl/domain/validation |
| `S01-domain-value_objects` | A | 43 | `true` | src/bioetl/domain/value_objects |
| `S01-domain-workflow` | A | 6 | `true` | src/bioetl/domain/workflow |
| `S02-app-core` | A | 198 | `true` | src/bioetl/application/core |
| `S03-app-control-plane` | A | 139 | `true` | src/bioetl/application/services/control_plane |
| `S04-app-services-other` | A | 151 | `true` | src/bioetl/application/services |
| `S04b-app-residual` | A | 171 | `true` | src/bioetl/application |
| `S09-composition` | A | 283 | `true` | src/bioetl/composition |
| `S10-interfaces-cli` | A | 106 | `true` | src/bioetl/interfaces/cli |
| `S11-interfaces-http` | A | 50 | `true` | src/bioetl/interfaces/http |
| `S11b-interfaces-residual` | A | 2 | `true` | src/bioetl/interfaces |
| `S05-app-pipelines` | B | 99 | `true` | src/bioetl/application/pipelines |
| `S07-infra-storage` | B | 146 | `true` | src/bioetl/infrastructure/storage |
| `S16-configs-quality` | B | 100 | `true` | configs/quality |
| `S16b-configs-other` | B | 156 | `true` | configs |
| `S06-infra-adapters` | C | 218 | `true` | src/bioetl/infrastructure/adapters |
| `S08-infra-observability` | C | 57 | `true` | src/bioetl/infrastructure/observability |
| `S08b-infra-residual` | C | 206 | `true` | src/bioetl/infrastructure |
| `S-D-security-residual` | D | 20 | `true` | security-relevant interfaces/composition/infra/scripts plus tests/security |
| `S17-docs-00-project-01` | E | 300 | `true` | docs/00-project |
| `S17-docs-00-project-02` | E | 75 | `true` | docs/00-project |
| `S17-docs-decisions` | E | 60 | `true` | docs/02-architecture/decisions |
| `S18-dashboard-docs` | E | 84 | `true` | dashboard/grafana documentation |
| `S18-grafana` | E | 104 | `true` | grafana |
| `S19-github-workflows` | E | 41 | `true` | .github/workflows |
| `S19b-github-actions` | E | 5 | `true` | .github/actions |
| `S12-tests-architecture-01` | F | 300 | `true` | tests/architecture |
| `S12-tests-architecture-02` | F | 199 | `true` | tests/architecture |
| `S13-tests-unit-domain-01` | F | 300 | `true` | tests/unit/domain |
| `S13-tests-unit-domain-02` | F | 42 | `true` | tests/unit/domain |
| `S14-tests-unit-application-01` | F | 300 | `true` | tests/unit/application |
| `S14-tests-unit-application-02` | F | 95 | `true` | tests/unit/application |
| `S14b-tests-unit-infrastructure-01` | F | 300 | `true` | tests/unit/infrastructure |
| `S14b-tests-unit-infrastructure-02` | F | 81 | `true` | tests/unit/infrastructure |
| `S15-tests-integration` | F | 223 | `true` | tests/integration |
| `S15b-tests-unit-scripts` | F | 132 | `true` | tests/unit/scripts |
| `S15c-tests-residual-01` | F | 300 | `true` | tests |
| `S15c-tests-residual-02` | F | 300 | `true` | tests |
| `S15c-tests-residual-03` | F | 300 | `true` | tests |
| `S15c-tests-residual-04` | F | 173 | `true` | tests |
| `S-R-.github-ISSUES-01` | R | 300 | `true` | residual catch-all: .github/ISSUES |
| `S-R-.github-ISSUES-02` | R | 33 | `true` | residual catch-all: .github/ISSUES |
| `S-R-catchall-01` | R | 137 | `true` | residual catch-all: .claude/agents, .codex/agents, .codex/config.toml, .codex/skills, .devin/QUICK_REFERENCE.md, .devin/TUTORIAL.md, .devin/agent-metrics.json, .devin/agents, .devin/config.json, .devin/mcp_config.json, .devin/prompts, .devin/scripts, .devin/skills, .devin/troubleshooting.md, .devin/wiki-architecture.json, .devin/wiki-core.json, .devin/wiki-index.json, .devin/wiki-observability.json, .devin/wiki-pipelines.json, .devin/wiki-providers.json, .devin/wiki-reference.json, .devin/wiki-schemas.json, .devin/wiki.json, .devin/workflows, .github/CODEOWNERS, .github/CODE_OF_CONDUCT.md, .github/CONTRIBUTING.md |
| `S-R-catchall-02` | R | 94 | `true` | residual catch-all: .github/ISSUE_TEMPLATE, .github/PULL_REQUEST_HYGIENE.md, .github/SECURITY.md, .github/copilot-instructions.md, .github/dependabot.yml, .github/instructions, .github/labeler.yml, .github/pull_request_template.md, .github/root-allowlist.txt, .github/vcr-noext-allowlist.txt, .junie/agents, .junie/guidelines.md, .junie/plans, .junie/skills, .zed/README.md, .zed/USER_SETTINGS_NO_AGENT_MCP.overlay.json, .zed/keymap.json, .zed/mcp.json, .zed/settings.json, .zed/snippets, .zed/tasks.json, data/README.md, data/input, docs/01-requirements |
| `S-R-catchall-03` | R | 60 | `true` | residual catch-all: docs/03-data-model, docs/03-guides |
| `S-R-catchall-04` | R | 298 | `true` | residual catch-all: docs/05-engineering, docs/05-operations, docs/99-archive, docs/DOCKER_QUICKSTART.md, docs/DOCKER_SETUP.md, docs/INDEX.md, docs/devin-optimization-analysis.md, docs/doc.json, docs/docs-folder-analysis.md, docs/filters, docs/plans, docs/reports, docs/reports-migration-analysis.md, docs/security, reports/.bioetl-report-root, reports/README.md, reports/ai, reports/architecture, reports/coverage, reports/docs-evidence |
| `S-R-catchall-05` | R | 57 | `true` | residual catch-all: reports/grafana, reports/logs, reports/observability, reports/plans |
| `S-R-catchall-06` | R | 63 | `true` | residual catch-all: reports/review, reports/root-hygiene, reports/semantic_pipeline_audit, reports/test-swarm, reports/test-telemetry, root-files, src/bioetl |
| `S-R-docs-02-architecture-01` | R | 300 | `true` | residual catch-all: docs/02-architecture |
| `S-R-docs-02-architecture-02` | R | 300 | `true` | residual catch-all: docs/02-architecture |
| `S-R-docs-02-architecture-03` | R | 300 | `true` | residual catch-all: docs/02-architecture |
| `S-R-docs-02-architecture-04` | R | 300 | `true` | residual catch-all: docs/02-architecture |
| `S-R-docs-02-architecture-05` | R | 131 | `true` | residual catch-all: docs/02-architecture |
| `S-R-docs-04-reference-01` | R | 300 | `true` | residual catch-all: docs/04-reference |
| `S-R-docs-04-reference-02` | R | 42 | `true` | residual catch-all: docs/04-reference |
| `S-R-reports-quality-01` | R | 300 | `true` | residual catch-all: reports/quality |
| `S-R-reports-quality-02` | R | 235 | `true` | residual catch-all: reports/quality |
| `S-R-scripts-ai` | R | 178 | `true` | scripts/ai |
| `S-R-scripts-diagrams` | R | 49 | `true` | scripts/diagrams |
| `S-R-scripts-docs` | R | 50 | `true` | scripts/docs |
| `S-R-scripts-engineering` | R | 231 | `true` | scripts/engineering |
| `S-R-scripts-memory` | R | 6 | `true` | scripts/memory |
| `S-R-scripts-ops` | R | 141 | `true` | scripts/ops |
| `S-R-scripts-residual` | R | 23 | `true` | scripts |
| `S-R-scripts-schema` | R | 25 | `true` | scripts/schema |
| `S-R-src-memory-01` | R | 300 | `true` | residual catch-all: src/memory |
| `S-R-src-memory-02` | R | 214 | `true` | residual catch-all: src/memory |
