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
- **Machine-readable memory artifact**:
  `mcp-memory.json`
  — служебный memory snapshot для tooling/integration сценариев, не human
  source of truth.
- **Neo4j project-memory seed pack**:
  `neo4j-project-memory-seed.md` и `neo4j-project-memory-seed.json`
  — phase-by-phase prompts и structured seed facts для заполнения
  `@neo4j-memory` устойчивыми знаниями о проекте.
- **Deterministic Neo4j sync tooling**:
  `python -m scripts.ops sync-neo4j-memory`
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
  Tooling
  может синхронизировать его в локальный Neo4j backend без ручных prompt waves.
  Для cleanup-режима используй `python -m scripts.ops sync-neo4j-memory --apply --prune-stale`:
  он пересобирает managed relations и удаляет только stale repo-derived nodes
  текущей ingest wave, а не весь graph.
  Для audit/report режима используй `python -m scripts.ops sync-neo4j-memory --report /tmp/neo4j-memory-audit.json`:
  он пишет JSON-отчет с snapshot stats, live managed/unmanaged summary,
  orphan summary и diff между snapshot и текущим managed graph.
  Для быстрого operator health-check используй
  `python -m scripts.ops sync-neo4j-memory --report-fast --report /tmp/neo4j-memory-audit.json`:
  этот режим проверяет только critical analysis labels/relations и устойчивее
  для Windows-host HTTP sync.
  Для полного пересоздания текущей managed wave используй
  `python -m scripts.ops sync-neo4j-memory --apply --full-reset-managed-wave`:
  этот режим сначала удаляет весь repo-managed subgraph текущей волны, а потом
  пересобирает его из текущего состояния репозитория.
  Current-cycle semantics больше не хранятся отдельным legacy label
  `development_cycle_surface`: теперь они проецируются как properties на
  `module_surface` / `class_surface` / `function_surface` / `method_surface`
  и на candidate nodes, чтобы deterministic live sync не зависел от отдельного
  проблемного analysis label.
  Если нужно довести repo-derived labels до полностью deterministic managed-only
  состояния, используй
  `python -m scripts.ops sync-neo4j-memory --apply --full-reset-managed-wave --prune-legacy-unmanaged`:
  этот режим после rebuild удаляет legacy unmanaged nodes для label-семейств,
  которые теперь полностью принадлежат deterministic sync.
  Для CI/snapshot gate используй
  `python -m scripts.ci neo4j-memory`:
  он проверяет ontology invariants без живого Neo4j и падает при drift по
  required labels/relations, protocol-level ports, rich contract metadata,
  runtime links или orphan nodes в snapshot.
  Для live gate с применением sync в реальный локальный Neo4j используй
  `python -m scripts.ci neo4j-memory-live`.
  Для operator-facing ownership shortcuts используй
  `python -m scripts.ops query-neo4j-memory <profile> <name>`, например:
  `python -m scripts.ops query-neo4j-memory owner-contract chembl.activity`,
  `python -m scripts.ops query-neo4j-memory owner-pipeline chembl_activity`,
  `python -m scripts.ops query-neo4j-memory owner-alert BioETLPipelineRunFailed`,
  `python -m scripts.ops query-neo4j-memory owner-doc "architecture diagrams hub"`.
  Для ближайших semantic edges используй `neighbors-*` профили, например:
  `python -m scripts.ops query-neo4j-memory neighbors-pipeline chembl_activity`,
  `python -m scripts.ops query-neo4j-memory neighbors-alert BioETLPipelineRunFailed`,
  `python -m scripts.ops query-neo4j-memory neighbors-contract chembl.activity`.
  Для поиска повторяющейся логики и кандидатов на вынос используй:
  `python -m scripts.ops query-neo4j-memory duplication-cluster adapter_layer:method_surface:de487f71c608`,
  `python -m scripts.ops query-neo4j-memory promotion-candidates adapter_layer`,
  `python -m scripts.ops query-neo4j-memory promotion-candidates composite_layer`,
  `python -m scripts.ops query-neo4j-memory promotion-candidates all`.
  Для поиска dead/stale code и отделения его от текущего цикла разработки используй:
  `python -m scripts.ops query-neo4j-memory dead-code-candidates adapter_layer`,
  `python -m scripts.ops query-neo4j-memory dead-code-candidates all`,
  `python -m scripts.ops query-neo4j-memory current-cycle-code adapter_layer`,
  `python -m scripts.ops query-neo4j-memory current-cycle-code all`.
  Для поиска переусложненной логики и removable complexity используй:
  `python -m scripts.ops query-neo4j-memory overengineered-candidates composite_layer`,
  `python -m scripts.ops query-neo4j-memory removable-complexity composite_layer`,
  `python -m scripts.ops query-neo4j-memory simplification-blockers adapter_layer`,
  `python -m scripts.ops query-neo4j-memory overengineered-candidates all`.

## Relationship To Other AI Surfaces

- Runtime orchestration и live agent registries остаются в
  `.codex/agents/` и other runtime agent registries.
- Published mirror и assistant-facing guides живут в
  `docs/00-project/ai/agents/`.
- Prompts живут в `docs/00-project/ai/prompts/`.
- Skills и reference mirrors живут в `docs/00-project/ai/skills/`.

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
