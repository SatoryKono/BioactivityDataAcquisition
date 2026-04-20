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
```

The validator checks:

- required scaffold files exist
- YAML and JSON resources parse successfully
- schema files expose basic JSON Schema contracts
- source priority references valid source-registry entries
- storage policy covers every retained artifact class and keeps memory paths under
  `src/memory/`

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
- accepted ADRs
- runtime code under `src/bioetl/`
- test evidence under `tests/`
- project configs under `configs/`

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

Dry-run prune for episodic memory:

```bash
python -m memory.tooling.prune
```

Apply pruning:

```bash
python -m memory.tooling.prune --apply
```

Run a curated review loop report:

```bash
python -m memory.tooling.review_curated
python -m memory.tooling.review_curated --json
```

Run the canonical daily agent/engineering workflow:

```bash
python -m memory.tooling.workflow pre-task --task-id task-123 --title "Investigate chembl memory"
python -m memory.tooling.workflow post-task --task-id task-123 --title "Investigate chembl memory" --summary "Validated and refreshed memory surfaces."
```

Detailed daily playbook:

- [DAILY_WORKFLOW.md](DAILY_WORKFLOW.md)

## Unified query facade

Local memory retrieval can be routed through one entry point:

```bash
python -m memory.query catalog sources
python -m memory.query rag --query chembl_activity --source-type code --profile implementation
python -m memory.query timeline --event-family run --query manifest --profile operations
python -m memory.query all chembl_activity --profile architecture
python -m memory.query graph owner-pipeline chembl_activity

Task-aware retrieval profiles:
- `general`: balanced default retrieval across memory surfaces.
- `architecture`: prefer ADR, architecture docs, and structural evidence.
- `implementation`: prefer runtime code, configs, and test-adjacent implementation surfaces.
- `operations`: prefer runbooks, incident context, and run/CI operational evidence.
- `audit`: prefer tests, ADRs, configs, and broad review evidence.
```

## Storage policy

Artifact storage policy is declared in `policy/storage.yaml`.

Current default stance:

- `policy/`, `catalog/`, `schemas/`, and `curated/` are versioned
- `episodic/` is ephemeral and prunable
- `rag/manifests/`, `graph/exports/`, and `timeline/events/` are rebuild-only

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
2. inspect `catalog -> graph -> rag -> source`
3. update canonical source files
4. run `python -m memory.tooling.workflow post-task ...`
5. promote only durable lessons, incidents, decisions, or domain knowledge
6. run `python -m memory.tooling.review_curated` on a regular cadence to review due/stale curated notes

`pre-task` auto-refreshes rebuild-only RAG and timeline artifacts if manifests
are missing, so the workflow remains usable even when `src/memory/` does not
store generated manifests in git.
