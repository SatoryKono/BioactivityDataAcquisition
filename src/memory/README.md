# Memory Subsystem

This package is the canonical implementation home for the BioETL project memory
subsystem.

The subsystem is intentionally **source-first**:

- canonical project truth stays in `src/bioetl/`, `docs/`, `configs/`,
  `tests/`, `.github/`, and `grafana/`;
- `src/memory/` stores memory-specific policy, catalog data, schemas,
  retrieval/layout logic, and future derived memory artifacts;
- memory artifacts must never outrank code, configs, accepted ADRs, or active
  operational documentation.

## Initial scope

This baseline rollout provides:

- policy files under `policy/`
- structured catalogs under `catalog/`
- artifact schemas under `schemas/`
- a validation entrypoint under `memory.tooling.validate`

Future rollout waves will add:

- deterministic graph ownership under `graph/`
- deterministic RAG manifests under `rag/`
- timeline/event memory under `timeline/`
- curated long-term memory under `curated/`
- episodic/session memory under `episodic/`
- operational refresh/prune tooling under `tooling/`

## Validation

Run:

```bash
python -m memory.tooling.validate
python -m memory.tooling.validate --include-working-tree-junk
```

The validator checks:

- required scaffold files exist
- YAML and JSON resources parse successfully
- schema files expose basic JSON Schema contracts
- source priority references valid source-registry entries
- storage policy covers every retained artifact class and keeps memory paths under
  `src/memory/`
- optional working-tree hygiene mode flags Python cache files under `src/memory/`

## Graph entrypoints

The canonical deterministic Neo4j graph implementation now lives under
`src/memory/graph/`.

New canonical entrypoints:

```bash
python -m memory.graph sync --help
python -m memory.graph query --help
python -m memory.graph.sync --help
python -m memory.graph.query --help
```

Legacy compatibility entrypoints remain available while downstream scripts and
tests migrate:

```bash
python -m scripts.memory sync --help
python -m scripts.memory query --help
```

These legacy `scripts.memory.*` modules now resolve to the canonical
`memory.graph.*` implementations.

## RAG manifest MVP

The current RAG MVP builds deterministic manifests for:

- active project and operations docs
- requirements and working rollout plans
- accepted ADRs
- runtime code under `src/bioetl/`
- memory subsystem implementation, policies, schemas, and playbooks under
  `src/memory/`
- test evidence under `tests/`
- project configs under `configs/`
- operational engineering assets under `.github/workflows/`, `grafana/`, and
  `scripts/engineering/`

Generate manifests with:

```bash
python -m memory.rag.indexing --print-summary
```

## Timeline MVP

The initial timeline MVP projects deterministic event memory from canonical
repository sources:

```bash
python -m memory.timeline.ingest_runs
python -m memory.timeline.ingest_ci
python -m memory.timeline.ingest_incidents
```

This yields JSONL events for:

- control-plane run manifests and ledgers
- GitHub workflow definitions
- active incident/failure runbooks

## Tooling

Refresh deterministic artifacts:

```bash
python -m memory.tooling.refresh_all
```

Optional graph export during refresh:

```bash
python -m memory.tooling.refresh_all --include-graph-export
```

Optional file-, module-, and entity-level relation projection import from an
expanded graph snapshot:

```bash
python -m memory.tooling.refresh_all \
  --skip-rag \
  --skip-timeline \
  --include-graph-relations \
  --expanded-graph-path src/memory/graph/projections/bioetl_knowledge_graph_expanded.json
```

This generates rebuild-only artifacts under `graph/projections/` and
`graph/indexes/`, including `file_references.jsonl`, `file_relations.json`,
`module_references.jsonl`, `module_relations.json`, `entity_relations.jsonl`,
and `entity_relations.json`. The entity relation index captures semantic links
such as pipeline definitions, pipeline docs/tests, and ADR constraints. The raw
expanded graph snapshot is treated as derived input; it does not replace source
code, docs, configs, ADRs, or tests.

Dry-run prune for episodic memory:

```bash
python -m memory.tooling.prune
python -m memory.tooling.prune --max-active 100 --json
```

Apply pruning:

```bash
python -m memory.tooling.prune --apply
```

Run a curated review loop report:

```bash
python -m memory.tooling.review_curated
python -m memory.tooling.review_curated --json
python -m memory.tooling.workflow review-curated
python -m memory.tooling.workflow review-curated --json
```

Run the canonical daily agent/engineering workflow:

```bash
python -m memory.tooling.workflow pre-task --task-id task-123 --title "Investigate chembl memory" --profile audit
python -m memory.tooling.workflow post-task --task-id task-123 --title "Investigate chembl memory" --summary "Validated and refreshed memory surfaces."
```

Detailed daily playbook:

- [DAILY_WORKFLOW.md](DAILY_WORKFLOW.md)

## Unified query facade

Local memory retrieval can be routed through one entry point:

```bash
python -m memory.query catalog sources
python -m memory.query rag --query chembl_activity --source-type code --profile implementation
python -m memory.query rag --query runner --file-context src/bioetl/application/core/runner.py --file-relation-index /tmp/memory/graph/indexes/file_relations.json
python -m memory.query timeline --event-family run --query manifest --profile operations
python -m memory.query all chembl_activity --profile architecture
python -m memory.query all runner --file-context src/bioetl/application/core/runner.py --auto-refresh --expanded-graph-path src/memory/graph/projections/bioetl_knowledge_graph_expanded.json
python -m memory.query refs src/bioetl/application/core/runner.py --auto-refresh --expanded-graph-path src/memory/graph/projections/bioetl_knowledge_graph_expanded.json
python -m memory.query impact src/bioetl/application/core/runner.py --auto-refresh --expanded-graph-path src/memory/graph/projections/bioetl_knowledge_graph_expanded.json
python -m memory.query neighborhood src/bioetl/application/core/runner.py --depth 2 --auto-refresh --expanded-graph-path src/memory/graph/projections/bioetl_knowledge_graph_expanded.json
python -m memory.query module-refs bioetl.application.core.runner --auto-refresh --expanded-graph-path src/memory/graph/projections/bioetl_knowledge_graph_expanded.json
python -m memory.query module-impact bioetl.application.core.runner --auto-refresh --expanded-graph-path src/memory/graph/projections/bioetl_knowledge_graph_expanded.json
python -m memory.query module-neighborhood bioetl.application.core.runner --depth 2 --auto-refresh --expanded-graph-path src/memory/graph/projections/bioetl_knowledge_graph_expanded.json
python -m memory.query entity-refs chembl_activity --relation defined_by --auto-refresh --expanded-graph-path src/memory/graph/projections/bioetl_knowledge_graph_expanded.json
python -m memory.query entity-impact configs/entities/chembl/activity.yaml --auto-refresh --expanded-graph-path src/memory/graph/projections/bioetl_knowledge_graph_expanded.json
python -m memory.query entity-neighborhood chembl_activity --depth 2 --auto-refresh --expanded-graph-path src/memory/graph/projections/bioetl_knowledge_graph_expanded.json
python -m memory.query graph owner-pipeline chembl_activity
```

Use `--file-context` when the task starts from a specific file. RAG ranking then
boosts chunks from that file and from files connected through the generated
`references_file` relation index.

Use `module-refs`, `module-impact`, and `module-neighborhood` when the task
starts from a Python import/module boundary rather than a concrete file path.

Use `entity-refs`, `entity-impact`, and `entity-neighborhood` when the task
starts from a semantic graph entity such as a pipeline, config, ADR, doc, or
test target.

Generated RAG and timeline artifacts are rebuild-only. If they are absent,
or if the timeline directory has no generated `*.jsonl` projections, either
refresh them explicitly or use the query facade's temporary refresh mode:

```bash
python -m memory.tooling.refresh_all
python -m memory.query all chembl_activity --profile architecture --auto-refresh
```

Task-aware retrieval profiles:

- `general`: balanced default retrieval across memory surfaces.
- `architecture`: prefer ADR, architecture docs, and structural evidence.
- `implementation`: prefer runtime code, configs, and test-adjacent implementation surfaces.
- `operations`: prefer runbooks, workflows, dashboards, scripts, incident context, and run/CI operational evidence.
- `audit`: prefer tests, workflows, ADRs, configs, and broad review evidence.

## Storage policy

Artifact storage policy is declared in `policy/storage.yaml`.

Current default stance:

- `policy/`, `catalog/`, `schemas/`, and `curated/` are versioned
- `episodic/` is ephemeral and prunable
- `rag/manifests/`, `graph/exports/`, `graph/projections/`, `graph/indexes/`,
  and `timeline/events/` are rebuild-only

## Notes workflow

Create a note from a built-in template:

```bash
python -m memory.tooling.create_note --kind episodic-session --title "Current task" --task-id task-123
python -m memory.tooling.create_note --kind curated-lesson --title "Durable lesson"
```

Promote an episodic note into curated memory:

```bash
python -m memory.tooling.promote_note --source src/memory/episodic/summaries/example.md --target-kind lesson --summary "Durable lesson worth reusing."
python -m memory.tooling.promote_note --source src/memory/episodic/summaries/example.md --target-kind lesson --summary "Durable lesson worth reusing." --move
python -m memory.tooling.archive_note --source src/memory/curated/lessons/example.md --reason "Superseded by newer guidance."
```

## Daily Agent Workflow

Canonical daily sequence for agents and engineers:

1. run `python -m memory.tooling.workflow pre-task ...`
1. inspect `catalog -> graph -> rag -> source`
1. update canonical source files
1. run `python -m memory.tooling.workflow post-task ...`
1. promote only durable lessons, incidents, decisions, or domain knowledge
1. run `python -m memory.tooling.workflow review-curated` on a regular cadence to review due/stale curated notes

`pre-task` auto-refreshes rebuild-only RAG and timeline artifacts if manifests
are missing, so the workflow remains usable even when `src/memory/` does not
store generated manifests in git.
