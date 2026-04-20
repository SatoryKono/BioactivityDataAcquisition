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

## RAG manifest MVP

The initial RAG MVP builds deterministic markdown manifests for:

- `docs/00-project/`
- `docs/02-architecture/decisions/`
- `docs/05-operations/runbooks/`

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

## Notes workflow

Create a note from a built-in template:

```bash
python -m memory.tooling.create_note --kind episodic-session --title "Current task" --task-id task-123
python -m memory.tooling.create_note --kind curated-lesson --title "Durable lesson"
```

Promote an episodic note into curated memory:

```bash
python -m memory.tooling.promote_note --source src/memory/episodic/summaries/example.md --target-kind lesson
python -m memory.tooling.promote_note --source src/memory/episodic/summaries/example.md --target-kind lesson --move
```
