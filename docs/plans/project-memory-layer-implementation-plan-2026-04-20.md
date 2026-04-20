# Project Memory Layer Implementation Plan

*Status: Working planning artifact (non-normative)*
*Created: 2026-04-20*
*Scope: staged rollout of a hybrid project-memory subsystem rooted in `src/memory/`*

## Freshness note

This document is a bounded implementation plan. It does not replace canonical
project guidance. If this plan conflicts with active repository sources, the
active sources win:

- `docs/00-project/RULES.md`
- `docs/01-requirements/REQUIREMENTS.md`
- accepted ADRs in `docs/02-architecture/decisions/`
- runtime source in `src/bioetl/`
- active operator guidance in `docs/05-operations/`

This plan governs rollout sequencing only. It must not be treated as a second
knowledge-management policy surface once the implementation stabilizes.

## Executive summary

BioETL already has several memory-adjacent surfaces:

- curated AI memory under `docs/00-project/ai/memory/`
- deterministic graph tooling under `scripts/memory/`
- control-plane evidence via run manifest and run ledger contracts
- operational Neo4j setup and verification docs

What is missing is a single implementation home, a clear lifecycle policy, and
a disciplined split between canonical truth, derived retrieval context, and
temporary working memory.

This plan proposes a `source-first hybrid memory layer` with the following
rules:

1. `src/memory/` becomes the canonical home of the **memory subsystem**.
1. Canonical project truth remains outside `src/memory/`.
1. The subsystem combines RAG, graph memory, structured catalog memory,
   timeline memory, curated long-term memory, and short-lived episodic memory.
1. Every derived artifact must carry provenance, freshness metadata, and a
   clear invalidation path.
1. Memory must be sparse, governed, and prunable. It must not become a second
   repository of stale summaries.

## Why this plan exists

The repository is large enough that both engineers and AI agents repeatedly
need the same contextual answers:

- where a concept is implemented and documented;
- which ADR constrains a module or configuration;
- which tests validate a contract or pipeline;
- which runbooks, alerts, metrics, and dashboards relate to an incident;
- which domain owns a subsystem;
- which lessons are durable enough to keep beyond one task.

Those facts currently exist, but they are fragmented across:

- code,
- docs,
- configs,
- tests,
- scripts,
- CI outputs,
- control-plane artifacts,
- observability assets,
- AI-support notes.

The project needs a memory layer that is useful in daily work without
competing with source-of-truth.

## Target outcome

By the end of this rollout, the repository should have:

- a single memory subsystem root at `src/memory/`;
- an explicit source registry and source-priority model;
- deterministic RAG manifests for indexable repository knowledge;
- deterministic graph export and query surfaces for topology and impact
  analysis;
- timeline/event memory for runs, CI, and incidents;
- curated long-term memory for durable decisions and lessons;
- TTL-governed episodic/session memory;
- validation, refresh, and pruning tooling;
- documented agent workflow rules for memory use.

## Non-goals

- Do not move business logic from `src/bioetl/` into `src/memory/`.
- Do not move accepted ADRs, active runbooks, or active guides into
  `src/memory/`.
- Do not store raw chat transcripts as project memory.
- Do not model every code symbol or every line in the graph.
- Do not allow memory summaries to outrank code, config, or accepted ADRs.

## Current state summary

### Existing memory-adjacent surfaces

- `docs/00-project/ai/memory/README.md`
- `docs/00-project/ai/memory/agent-memory.md`
- `docs/00-project/ai/memory/memory-py-*.md`
- `scripts/memory/sync.py`
- `configs/quality/neo4j_memory_mapping.yaml`
- `docs/05-operations/deployment/neo4j-memory-setup.md`
- `docs/05-operations/verification/neo4j-memory-*.md`
- `docs/02-architecture/decisions/ADR-043-documentation-knowledge-management.md`
- `docs/02-architecture/decisions/ADR-044-run-manifest-ledger-control-plane.md`

### Observed gaps

1. There is no single canonical implementation root for the memory subsystem.
1. Current memory artifacts mix runtime-facing notes, graph tooling guidance,
   and operational setup concerns.
1. There is no unified source registry distinguishing canonical, indexable,
   derived, and ephemeral memory.
1. Freshness, confidence, retention, and invalidation rules are not yet
   standardized across all memory surfaces.
1. There is no explicit promote-or-drop workflow for episodic/session memory.
1. The current Neo4j-derived graph is useful, but it is documented as a tooling
   surface rather than as one part of a broader memory architecture.

### Immediate constraint

`src/memory/` does not exist yet. This rollout starts from a repository state
where the implementation root has to be created.

## Architectural principles

### 1. Source-first

Memory can index, summarize, or relate repository knowledge, but never replace
the primary source.

### 2. One home for the subsystem

All implementation, policy, schemas, and derived memory artifacts belong under
`src/memory/`.

### 3. Deterministic where possible

Graph exports, manifests, policies, and event projections should be generated
deterministically from repository state.

### 4. Curated where necessary

Long-term memory should be sparse and intentionally promoted, not passively
accumulated.

### 5. Prunable by design

Every temporary artifact must have a TTL, invalidation rule, or rebuild path.

### 6. Explainable provenance

Every non-trivial derived artifact must record:

- `source_refs`
- `commit_sha`
- `content_hash`
- `generated_at`
- `freshness_class`
- `confidence`

## Proposed target structure

```text
src/memory/
  README.md
  policy/
    source_priority.yaml
    retention.yaml
    confidence.yaml
    freshness.yaml
    invalidation.yaml
    exclusions.yaml
  catalog/
    source_registry.yaml
    owner_map.yaml
    domain_map.yaml
    repo_zones.yaml
    placement_rules.yaml
  schemas/
    memory_record.schema.json
    rag_chunk.schema.json
    graph_node.schema.json
    graph_edge.schema.json
    timeline_event.schema.json
    curated_note.schema.json
    episodic_note.schema.json
  rag/
    chunking.py
    indexing.py
    retrieval.py
    filters.py
    manifests/
      corpus_catalog.json
      chunks.jsonl
  graph/
    sync.py
    query.py
    ontology.yaml
    mappings.yaml
    exports/
      repo_snapshot.json
  timeline/
    ingest_runs.py
    ingest_ci.py
    ingest_incidents.py
    events/
      runs.jsonl
      ci.jsonl
      incidents.jsonl
  curated/
    decisions/
    incidents/
    lessons/
    domain_knowledge/
  episodic/
    sessions/
    summaries/
  tooling/
    refresh_all.py
    prune.py
    validate.py
```

## Memory type model

### Canonical source layer

Lives outside `src/memory/`. Includes:

- `src/bioetl/`
- `docs/`
- `configs/`
- `tests/`
- `.github/`
- `grafana/`
- accepted ADRs
- active runbooks
- active workflows
- dashboards and alert rules

### RAG memory

Use for precise retrieval over:

- active docs,
- accepted ADRs,
- runbooks,
- code surfaces,
- tests,
- configs,
- workflows,
- dashboards,
- selected operational reports.

### Graph memory

Use for repository topology and impact analysis.

High-signal entity families only:

- modules/packages,
- pipelines/providers/entities,
- configs/contracts,
- docs/ADRs/runbooks,
- tests/test surfaces,
- workflows/jobs,
- dashboards/alerts/metrics,
- run manifests / run ledger artifacts,
- owner/domain boundaries.

### Structured memory

Use for deterministic lookup:

- source priority,
- domain boundaries,
- owner maps,
- placement rules,
- repo zones,
- exclusion lists,
- freshness and retention rules.

### Timeline memory

Use for append-only chronology:

- runs,
- CI,
- incidents,
- selected operational events.

### Curated long-term memory

Use only for promoted, durable knowledge:

- decisions,
- recurring lessons,
- architecture agreements,
- domain knowledge worth keeping.

### Episodic memory

Use for task-local summaries and working context with TTL.

## Data-source classification

The subsystem must classify repository data into four buckets.

### 1. Canonical

Primary truth surfaces.

### 2. Indexable

Surfaces suitable for search, retrieval, or relationship mapping.

### 3. Derived

Generated manifests, graph exports, summaries, and event projections.

### 4. Ephemeral

Short-lived session notes and other expiring artifacts.

## Repository relationships to model

The graph layer should focus on relations that materially improve engineering
work:

- `module -> DESCRIBED_BY -> doc`
- `ADR -> CONSTRAINS -> module/config/test`
- `issue -> RESOLVED_BY -> PR -> TOUCHES -> file`
- `incident -> MITIGATED_BY -> runbook`
- `incident -> OBSERVED_BY -> metric/alert/dashboard`
- `pipeline -> DEFINED_BY -> config`
- `pipeline -> TESTED_BY -> test_surface`
- `pipeline -> OBSERVED_BY -> dashboard/alert`
- `domain_entity -> PROCESSED_BY -> pipeline`
- `runtime_evidence -> EMITS_ARTIFACT -> control_plane_artifact`

The graph should not attempt line-level modeling or full semantic storage of
every implementation detail.

## RAG strategy

### Chunking policy

- Docs / ADRs / runbooks: section-based chunks, target roughly 400-900 tokens.
- Code: symbol-based chunks around public or high-signal modules/classes/functions.
- Tests: test-class or test-file chunks depending on density.
- Configs: top-level object/section chunks.
- Workflow and dashboard JSON: logical-section chunks, not full-file blobs.

### Chunk metadata

Each chunk should include:

- `source_path`
- `source_type`
- `symbol`
- `owner`
- `domain`
- `commit_sha`
- `content_hash`
- `last_verified`
- `freshness_class`
- `graph_node_refs`

### Filter model

Support filtering by:

- source type,
- domain,
- owner,
- repo zone,
- freshness,
- canonical priority,
- archive/generated exclusion.

### Refresh model

- incremental reindex on changed sources;
- periodic full refresh;
- invalidation on delete/move/hash mismatch;
- optional rebuild on policy version change.

## Anti-hallucination policy

The memory subsystem must reduce, not amplify, memory hallucinations.

### Mandatory controls

- source-of-truth priority,
- provenance on every derived artifact,
- freshness metadata,
- confidence scoring,
- deduplication,
- conflict handling,
- explicit invalidation,
- TTL for temporary memory,
- no silent overwrite of conflicting facts.

### Priority order

1. code / config / accepted ADR
1. published active docs / runbooks
1. generated reports
1. curated summaries
1. episodic notes

### Conflict handling rule

If a derived fact conflicts with a higher-priority source:

- the higher-priority source wins;
- the lower-priority artifact is marked stale or conflicting;
- the system should not silently merge the two.

## Delivery streams

The rollout is best handled as seven parallel-but-sequenced streams.

### Stream A. Governance and policy

Deliver:

- `src/memory/README.md`
- source-priority policy
- retention policy
- freshness policy
- confidence policy
- invalidation policy
- exclusion policy

Depends on:

- agreement on subsystem boundaries
- confirmation that `src/memory/` is the canonical implementation root

Definition of done:

- every artifact class has lifecycle rules;
- source-of-truth precedence is explicit;
- anti-hallucination policy is documented in one place.

### Stream B. Structured catalog

Deliver:

- source registry
- owner map
- domain map
- repo zones
- placement rules

Depends on:

- policy decisions from Stream A

Definition of done:

- deterministic lookup exists for owners, domains, and source classes;
- new memory artifacts can declare their source class against the registry.

### Stream C. Graph migration

Deliver:

- `src/memory/graph/sync.py`
- `src/memory/graph/query.py`
- graph ontology and mapping files
- graph export format under `src/memory/graph/exports/`

Migration requirement:

- current `scripts/memory/*` functionality should be rehomed or wrapped from
  `src/memory/graph/` without breaking operator workflows.

Definition of done:

- deterministic graph export exists under `src/memory/graph/`;
- existing high-signal graph use cases remain supported.

### Stream D. RAG manifests and retrieval

Deliver:

- chunking and indexing modules
- corpus manifest
- chunk manifest
- retrieval filters

Definition of done:

- repository knowledge can be indexed deterministically;
- search surfaces carry source metadata and graph references when available.

### Stream E. Timeline memory

Deliver:

- ingestion for runs
- ingestion for CI
- ingestion for incidents
- event schemas and JSONL storage conventions

Definition of done:

- the project can answer “what happened and when” without relying on ad hoc
  summaries.

### Stream F. Curated and episodic memory

Deliver:

- curated note templates
- incident/lesson promotion format
- session note format
- TTL rules
- pruning path

Definition of done:

- durable knowledge is sparse and attributable;
- transient notes have an automatic cleanup path.

### Stream G. Tooling and CI

Deliver:

- `refresh_all.py`
- `validate.py`
- `prune.py`
- optional CI gates for schema validity, freshness drift, and orphan detection

Definition of done:

- memory artifacts can be refreshed, validated, and cleaned predictably.

## Implementation phases

### Phase 0. Baseline framing

Goal:

- create the planning and policy baseline before writing subsystem code.

Tasks:

- create `src/memory/` root;
- add subsystem README;
- define policy and source-class model;
- define artifact schemas.

Validation:

- policy review
- schema lint/validation
- docs link validation

### Phase 1. Minimal skeletal rollout

Goal:

- create the skeleton without changing daily operator workflows.

Tasks:

- add `policy/`, `catalog/`, `schemas/`, `graph/`, `rag/`, `timeline/`,
  `curated/`, `episodic/`, `tooling/`;
- add placeholder validators and refresh entrypoints;
- add migration notes from current surfaces.

Validation:

- repo docs checks
- path/link verification

### Phase 2. Graph migration

Goal:

- make `src/memory/graph/` the new implementation home for the existing
  deterministic memory graph.

Tasks:

- move or wrap `scripts/memory sync` implementation;
- move graph ontology/mapping ownership under `src/memory/graph/`;
- preserve CLI/operator compatibility during transition.

Validation:

- snapshot export parity
- existing memory sync tests
- current Neo4j verification examples

### Phase 3. RAG MVP

Goal:

- establish a deterministic indexable corpus without introducing a heavyweight
  external dependency requirement into the repo itself.

Tasks:

- generate chunk manifests;
- define exclusions and freshness classes;
- support source metadata and graph cross-references.

Validation:

- schema validation of chunk manifests
- sample retrieval smoke tests
- duplicate-source detection

### Phase 4. Timeline MVP

Goal:

- store runs, CI, and incidents as event memory rather than free-form notes.

Tasks:

- define timeline event schema;
- ingest run evidence from existing control-plane surfaces;
- project selected CI and incident events.

Validation:

- sample event projections
- append-only behavior checks

### Phase 5. Curated / episodic workflows

Goal:

- formalize long-term promotion and short-term expiration.

Tasks:

- define curated note templates;
- define promotion criteria;
- define TTL for episodic notes;
- implement pruning.

Validation:

- stale-note pruning tests
- curated-note schema checks

### Phase 6. Tooling and adoption

Goal:

- make the subsystem usable in daily work.

Tasks:

- document the standard agent workflow;
- add validation and refresh commands;
- add repo guidance for how memory is refreshed after changes.

Validation:

- docs checks
- CLI smoke tests
- targeted developer workflow verification

## Detailed work packages

### WP-01. Create subsystem root

Artifacts:

- `src/memory/__init__.py`
- `src/memory/README.md`
- directory scaffold

### WP-02. Define policy package

Artifacts:

- `src/memory/policy/source_priority.yaml`
- `src/memory/policy/retention.yaml`
- `src/memory/policy/confidence.yaml`
- `src/memory/policy/freshness.yaml`
- `src/memory/policy/invalidation.yaml`
- `src/memory/policy/exclusions.yaml`

### WP-03. Define structured catalog

Artifacts:

- `src/memory/catalog/source_registry.yaml`
- `src/memory/catalog/owner_map.yaml`
- `src/memory/catalog/domain_map.yaml`
- `src/memory/catalog/repo_zones.yaml`
- `src/memory/catalog/placement_rules.yaml`

### WP-04. Define schemas

Artifacts:

- `memory_record.schema.json`
- `rag_chunk.schema.json`
- `graph_node.schema.json`
- `graph_edge.schema.json`
- `timeline_event.schema.json`
- `curated_note.schema.json`
- `episodic_note.schema.json`

### WP-05. Rehome graph sync

Artifacts:

- `src/memory/graph/sync.py`
- `src/memory/graph/query.py`
- `src/memory/graph/ontology.yaml`
- `src/memory/graph/mappings.yaml`

Migration notes:

- preserve current `python -m scripts.memory` operator entrypoint until the new
  subsystem path is stable;
- prefer thin compatibility wrappers instead of two diverging
  implementations.

### WP-06. Build RAG manifests

Artifacts:

- `src/memory/rag/chunking.py`
- `src/memory/rag/indexing.py`
- `src/memory/rag/retrieval.py`
- `src/memory/rag/filters.py`
- `src/memory/rag/manifests/corpus_catalog.json`
- `src/memory/rag/manifests/chunks.jsonl`

### WP-07. Build timeline event ingestion

Artifacts:

- `src/memory/timeline/ingest_runs.py`
- `src/memory/timeline/ingest_ci.py`
- `src/memory/timeline/ingest_incidents.py`
- `src/memory/timeline/events/*.jsonl`

### WP-08. Define curated and episodic formats

Artifacts:

- `src/memory/curated/decisions/`
- `src/memory/curated/incidents/`
- `src/memory/curated/lessons/`
- `src/memory/curated/domain_knowledge/`
- `src/memory/episodic/sessions/`
- `src/memory/episodic/summaries/`

### WP-09. Build tooling

Artifacts:

- `src/memory/tooling/refresh_all.py`
- `src/memory/tooling/validate.py`
- `src/memory/tooling/prune.py`

## Migration strategy

### Current surfaces to preserve during transition

- `docs/00-project/ai/memory/`
- `scripts/memory/`
- Neo4j deployment/verification docs

### Migration rule

During the rollout:

- keep operator-facing commands working;
- prefer compatibility wrappers;
- move ownership, implementation, and generated artifacts to `src/memory/`;
- keep docs in `docs/` as published or repo-facing entrypoints, not as the
  implementation store.

### Post-rollout target

- `src/memory/` owns the subsystem;
- `docs/00-project/ai/memory/` becomes entrypoint/reference guidance only;
- legacy direct implementation in `scripts/memory/` is reduced to wrappers or
  removed after the cutover is verified.

## Validation plan

At minimum, each rollout phase should validate:

- docs links and doc freshness surfaces;
- schema validity for new memory artifacts;
- deterministic graph export behavior;
- compatibility with current memory sync workflows;
- pruning behavior for episodic memory;
- no duplicate or conflicting canonical source registration.

Likely verification commands to add or extend:

- `python -m src.memory.tooling.validate`
- `python -m src.memory.tooling.refresh_all`
- `python -m src.memory.tooling.prune`
- current graph/Neo4j snapshot checks
- docs verification checks

The exact command surface can be finalized during Phase 0-1, but the rollout
must include one refresh path, one validation path, and one prune path.

## Risks and trade-offs

### Risk: memory becomes a second source of truth

Mitigation:

- explicit source priority;
- provenance requirements;
- conflict invalidation.

### Risk: `src/memory/` turns into an unbounded dump

Mitigation:

- retention policy;
- TTL for episodic memory;
- prune tooling;
- strict curated promotion rules.

### Risk: graph scope becomes too broad

Mitigation:

- model only high-signal entities and relations;
- keep line-level and low-value symbol noise out of scope.

### Risk: docs and runtime diverge during migration

Mitigation:

- keep docs as entrypoints;
- move implementation, not canonical project truth;
- use wrappers for transition.

### Risk: expensive rollout with unclear value

Mitigation:

- stage delivery;
- start with policy, graph migration, and deterministic manifests;
- avoid expensive infra commitments before the MVP proves useful.

## Acceptance criteria

- `src/memory/` exists as the canonical implementation root of the memory
  subsystem.
- Policy files exist for source priority, retention, freshness, invalidation,
  confidence, and exclusions.
- Structured catalog exists for source registry, owner map, domain map, repo
  zones, and placement rules.
- Graph implementation ownership is moved under `src/memory/graph/`.
- Deterministic RAG manifests exist under `src/memory/rag/manifests/`.
- Timeline event storage exists under `src/memory/timeline/events/`.
- Curated and episodic note formats exist and are governed.
- Validation, refresh, and prune tooling exist.
- The rollout preserves the rule that canonical repository truth remains
  outside `src/memory/`.

## Recommended initial issue breakdown

1. Create subsystem root and policies
1. Define schemas and structured catalog
1. Rehome graph sync and query implementation
1. Build deterministic RAG manifest generation
1. Build timeline event projection
1. Add curated and episodic memory formats
1. Add validation, refresh, and prune tooling
1. Update docs and operator workflow guidance

## Exit criteria for this plan

This plan should be considered complete when:

- the initial memory subsystem MVP is implemented;
- the migration path away from implementation-in-`scripts/memory` is executed;
- active docs reference the new subsystem correctly;
- the project no longer depends on scattered ad hoc memory storage conventions.

At that point, this plan should remain as historical rollout context and any
ongoing rules should live in the actual subsystem docs and accepted ADRs.
