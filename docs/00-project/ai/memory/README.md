# AI Memory Surface

*Статус: internal (repo-only entrypoint; excluded from MkDocs)*

Этот каталог хранит memory-артефакты для AI-рантаймов и role-specific agent
profiles в BioETL.

## Surface Model

- **Project memory entry point**:
  [agent-memory.md](agent-memory.md)
  — общий быстрый контекст по проекту, canonical docs anchors и operational
  shortcuts для новой AI-сессии.
- **Role-specific memory snapshots**:
  `memory-py-*.md`
  — focused memory sheets для отдельных агентных ролей; они наследуют
  project-level context из `agent-memory.md`, а не заменяют его.
- **Memory usage policy**:
  [`../agents/guides/MEMORY_USAGE.md`](../agents/guides/MEMORY_USAGE.md)
  — обязательный порядок чтения memory surfaces, conflict priority и
  stale-memory protocol.
- **Post-change validation policy**:
  [`../agents/policy/POST_CHANGE_VALIDATION.md`](../agents/policy/POST_CHANGE_VALIDATION.md)
  — validation protocol после write-capable AI work.

## Role Memory Coverage Matrix

| Role profile | Role memory sheet | Coverage status |
| --- | --- | --- |
| `py-audit-bot` | `memory-py-audit-bot.md` | dedicated |
| `py-plan-bot` | `memory-py-plan-bot.md` | dedicated |
| `py-test-bot` | `memory-py-test-bot.md` | dedicated |
| `py-config-bot` | `memory-py-config-bot.md` | dedicated |
| `py-debug-bot` | `memory-py-debug-bot.md` | dedicated |
| `py-doc-bot` | `memory-py-doc-bot.md` | dedicated |
| `py-architecture-debt-bot` | `memory-py-architecture-debt-bot.md` | dedicated |
| `py-review-orchestrator` | `memory-py-review-orchestrator.md` | dedicated |
| `py-test-swarm` | `memory-py-test-swarm.md` | dedicated |

If a runtime profile is renamed or added, update this matrix and the matching
role profile anchors in `.codex/agents/*.md` and `.gemini/agents/*.md` in the
same change set.
- **Machine-readable memory artifact**:
  `mcp-memory.json`
  — служебный memory snapshot для tooling/integration сценариев, не human
  source of truth.
- **Neo4j project-memory seed pack**:
  `neo4j-project-memory-seed.md` и `neo4j-project-memory-seed.json`
  — phase-by-phase prompts и structured seed facts для заполнения
  `@neo4j-memory` устойчивыми знаниями о проекте.
- **Deterministic Neo4j sync tooling**:
  `python -m scripts.memory sync`
  — строит repo-derived graph snapshot из docs/configs/src/tests/scripts,
  curated policy surfaces, а также semantic impact-analysis layer для
  `port_surface`, `adapter_surface`, `adapter_impl_surface`,
  `pipeline_surface`, `contract_surface` и `alert_surface`.
  Дополнительно memory хранит code-duplication layer для high-signal families:
  `class_surface`, `function_surface`, `method_surface` и
  `duplication_cluster`, чтобы искать повторяющуюся логику и кандидатов на
  вынос в base/shared parent surfaces.
  Текущий ontology layer уже включает:
  `Protocol/class`-level `port_surface`,
  fine-grained `adapter_impl_surface` для concrete adapter modules,
  richer `contract_surface` links к registry/config/schema modules и
  published artifacts, control-plane и lineage/runtime anchors к run-manifest /
  effective-config docs и services, direct
  `pipeline_surface -> RUNS_VIA/VALIDATED_BY/OBSERVED_BY/TESTED_BY`
  edges и config-driven selective
  `alert_surface -> DEPENDS_ON -> pipeline/provider/contract_surface`
  плюс `alert_surface -> OBSERVED_BY -> dashboard_surface` mapping по
  PromQL/dashboard metric overlap и fallback tables.
  Rule tables для pipeline/alert/contract mapping живут в
  `configs/quality/neo4j_memory_mapping.yaml`, а pipeline-to-test ownership
  опирается на `configs/quality/test_matrix.yaml`, включая shared provider
  regression suites.
  Поверх этого deterministic graph теперь включает ещё четыре coverage-блока:
  `storage_surface` для Bronze/Silver/Gold/composite/control-plane artifact refs,
  `runtime_evidence_surface` для `run_manifest` / `run_ledger` /
  `effective_config_artifact` / `lineage`,
  `control_plane_artifact_surface` для artifact-level templates вокруг manifest /
  ledger / effective-config / lineage persistence paths,
  `workflow_surface` / `workflow_job_surface` для `.github/workflows/*.yml`,
  `workflow_call_surface` / `workflow_matrix_variant_surface` /
  `workflow_output_surface` для reusable workflows, matrix-variant execution и
  produced outputs,
  `cli_command_surface` / `cli_option_surface` для command/option graph и
  side-effect semantics,
  `doc_claim_surface` для claim-level documentation traceability,
  и `DESCRIBES` / `ASSERTS_ABOUT` drift edges из published docs/policies к
  code/config/workflow targets.
  Tooling
  может синхронизировать его в локальный Neo4j backend без ручных prompt waves.
  Для cleanup-режима используй `python -m scripts.memory sync --apply --prune-stale`:
  он пересобирает managed relations и удаляет только stale repo-derived nodes
  текущей ingest wave, а не весь graph.
  Для shard-level selective rebuild используй:
  `python -m scripts.memory sync --export /tmp/storage-memory.json --only-storage-layer`,
  `python -m scripts.memory sync --export /tmp/runtime-memory.json --only-runtime-evidence-layer`,
  `python -m scripts.memory sync --export /tmp/workflow-memory.json --only-workflow-graph`,
  `python -m scripts.memory sync --export /tmp/docs-drift-memory.json --only-docs-drift`.
  Для audit/report режима используй `python -m scripts.memory sync --report /tmp/neo4j-memory-audit.json`:
  он пишет JSON-отчет с snapshot stats, live managed/unmanaged summary,
  orphan summary и diff между snapshot и текущим managed graph.
  Для быстрого operator health-check используй
  `python -m scripts.memory sync --report-fast --report /tmp/neo4j-memory-audit.json`:
  этот режим проверяет только critical analysis labels/relations и устойчивее
  для Windows-host HTTP sync.
  Для полного пересоздания текущей managed wave используй
  `python -m scripts.memory sync --apply --full-reset-managed-wave`:
  этот режим сначала удаляет весь repo-managed subgraph текущей волны, а потом
  пересобирает его из текущего состояния репозитория.
  Current-cycle semantics больше не хранятся отдельным legacy label
  `development_cycle_surface`: теперь они проецируются как properties на
  `module_surface` / `class_surface` / `function_surface` / `method_surface`
  и на candidate nodes, чтобы deterministic live sync не зависел от отдельного
  проблемного analysis label.
  Если нужно довести repo-derived labels до полностью deterministic managed-only
  состояния, используй
  `python -m scripts.memory sync --apply --full-reset-managed-wave --prune-legacy-unmanaged`:
  этот режим после rebuild удаляет legacy unmanaged nodes для label-семейств,
  которые теперь полностью принадлежат deterministic sync.
  Для CI/snapshot gate используй
  `python -m scripts.engineering.ci neo4j-memory`:
  он проверяет ontology invariants без живого Neo4j и падает при drift по
  required labels/relations, protocol-level ports, rich contract metadata,
  runtime links, storage/runtime/workflow coverage, docs-to-code `DESCRIBES`
  edges или orphan nodes в snapshot.
  Для live gate с применением sync в реальный локальный Neo4j используй
  `python -m scripts.engineering.ci neo4j-memory-live`.
  Для operator-facing ownership shortcuts используй
  `python -m scripts.memory query <profile> <name>`, например:
  `python -m scripts.memory query owner-contract chembl.activity`,
  `python -m scripts.memory query owner-pipeline chembl_activity`,
  `python -m scripts.memory query owner-alert BioETLPipelineRunFailed`,
  `python -m scripts.memory query owner-doc "architecture diagrams hub"`,
  `python -m scripts.memory query owner-storage silver/chembl/activity`,
  `python -m scripts.memory query owner-runtime-evidence run_manifest`,
  `python -m scripts.memory query owner-workflow tests`,
  `python -m scripts.memory query owner-workflow-job tests::governance-preflight`,
  `python -m scripts.memory query owner-cli-command "scripts.memory sync"`.
  Для ближайших semantic edges используй `neighbors-*` профили, например:
  `python -m scripts.memory query neighbors-pipeline chembl_activity`,
  `python -m scripts.memory query neighbors-alert BioETLPipelineRunFailed`,
  `python -m scripts.memory query neighbors-contract chembl.activity`,
  `python -m scripts.memory query neighbors-storage silver/chembl/activity`,
  `python -m scripts.memory query neighbors-runtime-evidence run_manifest`,
  `python -m scripts.memory query neighbors-run-instance manifest-chain-smoke`,
  `python -m scripts.memory query neighbors-workflow tests`,
  `python -m scripts.memory query neighbors-workflow-job tests::governance-preflight`,
  `python -m scripts.memory query neighbors-cli-command "bioetl run"`.
  Для новых surface-specific shortcuts используй:
  `python -m scripts.memory query docs-drift all`,
  `python -m scripts.memory query workflow-gates tests`,
  `python -m scripts.memory query workflow-artifacts tests`,
  `python -m scripts.memory query storage-lineage silver/chembl/activity`,
  `python -m scripts.memory query field-lineage silver/chembl/activity`,
  `python -m scripts.memory query schema-drift silver/chembl/assay`,
  `python -m scripts.memory query run-artifacts manifest-chain-smoke`,
  `python -m scripts.memory query runtime-state all`,
  `python -m scripts.memory query runtime-locks all`,
  `python -m scripts.memory query workflow-execution all`,
  `python -m scripts.memory query claim-trace all`,
  `python -m scripts.memory query cli-semantics "bioetl run"`.
  Для поиска повторяющейся логики и кандидатов на вынос используй:
  `python -m scripts.memory query duplication-cluster adapter_layer:method_surface:de487f71c608`,
  `python -m scripts.memory query promotion-candidates adapter_layer`,
  `python -m scripts.memory query promotion-candidates composite_layer`,
  `python -m scripts.memory query promotion-candidates all`.
  Для поиска dead/stale code и отделения его от текущего цикла разработки используй:
  `python -m scripts.memory query dead-code-candidates adapter_layer`,
  `python -m scripts.memory query dead-code-candidates all`,
  `python -m scripts.memory query current-cycle-code adapter_layer`,
  `python -m scripts.memory query current-cycle-code all`.
  Для поиска переусложненной логики и removable complexity используй:
  `python -m scripts.memory query overengineered-candidates composite_layer`,
  `python -m scripts.memory query removable-complexity composite_layer`,
  `python -m scripts.memory query simplification-blockers adapter_layer`,
  `python -m scripts.memory query overengineered-candidates all`.

## Additional Coverage Blocks

- **Storage/data surfaces**:
  `storage_surface`
  — deterministic Bronze/Silver/Gold/composite/control-plane artifact refs,
  включая `pipeline_surface -> WRITES_TO`, composite
  `pipeline_surface -> DEPENDS_ON -> storage_surface`, и
  `storage_surface -> PROMOTES_TO`.
- **Control-plane runtime evidence**:
  `runtime_evidence_surface`
  — anchors для `run_manifest`, `run_ledger`, `effective_config_artifact`,
  `lineage` с `BACKED_BY` links к modules, `DESCRIBED_IN` links к docs и
  `WRITES_TO` links к control-plane storage artifacts.
- **Artifact-level control-plane surfaces**:
  `control_plane_artifact_surface`
  — template-level nodes для persisted manifest / ledger / effective-config /
  lineage artifacts и sidecar indexes, связанные через
  `runtime_evidence_surface -> EMITS_ARTIFACT -> control_plane_artifact_surface -> MATERIALIZED_AS -> storage_surface`.
- **CI / workflow graph**:
  `workflow_surface`, `workflow_job_surface`, `workflow_call_surface`,
  `workflow_matrix_variant_surface`, `workflow_output_surface`
  — GitHub Actions workflows/jobs из `.github/workflows/*.yml`, включая
  `DEPENDS_ON` job ordering, `RUNS_VIA` links к repo scripts/files,
  `EXECUTES_GATE` edges к quality gates, reusable workflow calls, matrix
  variants и emitted outputs.
- **CLI semantics graph**:
  `cli_command_surface`, `cli_option_surface`
  — deterministic command/option graph для `bioetl` и project entrypoints,
  включая accepted options и heuristic `SIDE_EFFECTS_ON` links к pipelines /
  quality gates.
- **Docs-to-code drift edges**:
  `doc_source_surface` / `doc_artifact` / `policy_surface -> DESCRIBES -> targets`
  — repo-path citations внутри docs теперь проецируются в graph, чтобы можно
  было навигировать published guidance против current code/config/workflow surface.
  Для high-signal assertions memory теперь также строит `doc_claim_surface`
  и `ASSERTS_ABOUT` links к concrete repo targets.

## Relationship To Other AI Surfaces

- Runtime orchestration и live agent registries остаются в
  `.codex/agents/` и other runtime agent registries.
- Published mirror и assistant-facing guides живут в
  `docs/00-project/ai/agents/`.
- Prompts живут в `docs/00-project/ai/prompts/`.
- Skills и reference mirrors живут в `docs/00-project/ai/skills/`.

## Operating Reminder

- Use `MEMORY_USAGE.md` for runtime-source-first conflict handling and stale
  memory protocol.
- Use `POST_CHANGE_VALIDATION.md` for write-capable validation and final-report
  expectations.
- Treat this directory as a navigation/evidence layer, not as the runtime
  source of truth for agent behavior.

## Implementation Rollout Note

The memory **implementation subsystem** is being formalized under
`src/memory/`.

- `docs/00-project/ai/memory/` remains a repo-facing AI entrypoint and
  reference surface.
- `src/memory/` is the canonical home for memory policy, catalog data,
  schemas, and future retrieval/graph/timeline implementation.
- transitional graph facades now exist under `memory.graph`, while
  `scripts.memory.*` remains a compatibility surface during migration.
- Canonical project truth remains outside both surfaces in runtime code,
  configs, accepted ADRs, and active docs.
- Canonical daily workflow for agents and engineers now lives in
  `src/memory/DAILY_WORKFLOW.md` and is executed through
  `python -m memory.tooling.workflow pre-task ...` and
  `python -m memory.tooling.workflow post-task ...`.

## Daily Workflow Entry Point

For daily AI-assisted engineering and audit work, use the canonical workflow in
`src/memory/` instead of inventing task-local memory conventions:

```bash
python -m memory.tooling.workflow pre-task \
  --task-id task-123 \
  --title "Investigate chembl memory"

python -m memory.tooling.workflow post-task \
  --task-id task-123 \
  --title "Investigate chembl memory" \
  --summary "Verified the relevant source surfaces and refreshed memory."
```

This workflow standardizes:

- pre-task retrieval
- session-note creation
- post-task summary creation
- rebuild-only artifact refresh
- optional promotion into curated memory

Если возникает конфликт между memory notes и runtime source, приоритет у
runtime source и canonical governance docs:

- `docs/00-project/RULES.md`
- `docs/01-requirements/REQUIREMENTS.md`
- accepted ADRs in `docs/02-architecture/decisions/`
- runtime registries in `.codex/agents/` and other runtime agent registries

## Practical Reading Order

1. [agent-memory.md](agent-memory.md)
1. relevant `memory-py-*.md` file for the current role
1. `docs/00-project/ai/agents/` for guides and runtime-facing mirrors

### Dashboard work

Если задача связана с `grafana/dashboards/*.json`, links, Grafana Explore,
Loki/Tempo drilldown или operator navigation между shipped dashboards, используй:

- [../../../03-guides/dashboards/dashboard-extension-llm.md](../../../03-guides/dashboards/dashboard-extension-llm.md)

## Notes

- This overview page is **repo-only** and excluded from MkDocs.
- `agent-memory.md` may still be published as a shared entrypoint under
  `Internal / Extended`, but role-specific memory sheets remain repo-only by
  default.
- Role-specific memory docs are retained for onboarding speed and task focus.
- When a memory note becomes stale, fix the note instead of silently treating it
  as normative truth.
