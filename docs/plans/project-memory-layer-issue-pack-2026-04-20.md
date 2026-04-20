# Project Memory Layer Issue Pack

*Status: Working planning artifact (non-normative)*
*Created: 2026-04-20*
*Scope: proposed GitHub issue breakdown for the `src/memory/` rollout*

## Purpose

This file decomposes the umbrella memory-layer rollout into bounded GitHub
issues. It is a staging artifact for issue creation and sequencing, not a
normative project policy.

Primary rollout plan:

- [project-memory-layer-implementation-plan-2026-04-20.md](./project-memory-layer-implementation-plan-2026-04-20.md)

## Suggested dependency order

1. Memory subsystem scaffold, policy, catalog, and schemas
2. Graph subsystem migration into `src/memory/graph`
3. Deterministic RAG manifests and retrieval metadata
4. Timeline/event memory for runs, CI, and incidents
5. Curated and episodic memory with retention and pruning
6. Tooling, validation, refresh, and CI integration
7. Documentation and agent workflow integration

## Issue 1

### Title

`Create src/memory subsystem scaffold, policy package, catalog, and schemas`

### Summary

Create the initial `src/memory/` subsystem root and define the baseline
contracts for policy, structured catalog data, and artifact schemas.

### Scope

- create `src/memory/` root and package scaffold
- add subsystem README
- add `policy/`, `catalog/`, `schemas/` directories
- define source-priority, retention, freshness, invalidation, confidence, and
  exclusions policy files
- define source registry, owner map, domain map, repo zones, and placement
  rules
- define base schemas for memory record, RAG chunk, graph node/edge, timeline
  event, curated note, and episodic note

### Non-goals

- do not implement graph sync migration yet
- do not implement chunk generation yet
- do not move canonical project docs or code into `src/memory/`

### Acceptance criteria

- `src/memory/` exists and is documented as the canonical home of the memory
  subsystem
- policy files exist and encode source-of-truth priority
- structured catalog files exist
- schema files exist for all major artifact classes
- all new files validate and are link-discoverable

## Issue 2

### Title

`Rehome deterministic graph memory sync and query implementation into src/memory/graph`

### Summary

Move graph-memory ownership into `src/memory/graph/` while preserving current
operator-facing workflows and deterministic export behavior.

### Scope

- create `src/memory/graph/`
- rehome or wrap current `scripts/memory` graph sync/query logic
- move graph ontology and mapping ownership under `src/memory/graph/`
- preserve compatibility entrypoints during transition
- define graph export location under `src/memory/graph/exports/`

### Non-goals

- do not redesign the ontology from scratch
- do not break current operator commands during migration

### Acceptance criteria

- deterministic graph export exists under `src/memory/graph/`
- compatibility wrappers remain available where needed
- existing graph use cases remain supported
- snapshot parity or equivalent regression confidence exists

## Issue 3

### Title

`Implement deterministic RAG manifests and repository chunking under src/memory/rag`

### Summary

Create the first RAG-ready repository memory surface under `src/memory/rag/`
using deterministic chunk manifests and metadata-rich corpus catalogs.

### Scope

- create `src/memory/rag/`
- define chunking policy for docs, ADRs, runbooks, code, tests, configs, and
  workflows
- implement corpus catalog generation
- implement chunk manifest generation
- attach metadata such as source path, source type, domain, owner, content
  hash, commit reference, freshness class, and graph node refs
- define exclusion behavior for archive/generated mirrors

### Non-goals

- do not require a production vector store as part of this issue
- do not introduce a heavyweight retrieval backend dependency into the repo

### Acceptance criteria

- deterministic chunk manifests exist under `src/memory/rag/manifests/`
- chunking strategy is documented and implemented
- chunk metadata supports filtering and provenance
- archive/generated duplication is excluded by policy

## Issue 4

### Title

`Implement timeline memory for run, CI, and incident events under src/memory/timeline`

### Summary

Create append-only timeline memory so the project can answer “what happened and
when” using structured event projections rather than ad hoc notes.

### Scope

- create `src/memory/timeline/`
- define timeline event schema
- implement ingestion/projection for run events
- implement ingestion/projection for CI events
- implement ingestion/projection for incident events
- define JSONL storage conventions under `src/memory/timeline/events/`

### Non-goals

- do not replace canonical operational artifacts
- do not use timeline memory as a substitute for curated incident docs

### Acceptance criteria

- event schema exists and validates
- runs, CI, and incidents have defined projection paths
- append-only semantics are documented
- event artifacts remain attributable to canonical sources

## Issue 5

### Title

`Implement curated and episodic memory with retention, promotion, and pruning rules`

### Summary

Create long-term curated memory and short-lived episodic memory surfaces under
`src/memory/curated/` and `src/memory/episodic/` with explicit lifecycle
management.

### Scope

- create curated directories for decisions, incidents, lessons, and domain
  knowledge
- create episodic directories for session notes and summaries
- define curated-note and episodic-note formats
- define promotion criteria for durable knowledge
- define TTL and prune rules for episodic memory

### Non-goals

- do not auto-promote arbitrary task notes into long-term memory
- do not store raw chat transcripts as project memory

### Acceptance criteria

- curated and episodic formats exist
- promotion rules are explicit
- episodic retention and pruning rules are explicit
- long-term memory remains sparse and attributable

## Issue 6

### Title

`Add memory tooling for refresh, validation, pruning, and CI safety checks`

### Summary

Provide the operational tooling required to keep the memory subsystem current,
safe, and prunable.

### Scope

- create `src/memory/tooling/refresh_all.py`
- create `src/memory/tooling/validate.py`
- create `src/memory/tooling/prune.py`
- add schema validation paths
- add freshness/orphan/dedup checks where practical
- define CI-friendly validation scope

### Non-goals

- do not build a heavyweight external control plane for memory operations
- do not require live Neo4j for every validation path

### Acceptance criteria

- one refresh path exists
- one validation path exists
- one prune path exists
- tooling behavior is documented and testable

## Issue 7

### Title

`Document memory subsystem adoption and integrate memory workflow into daily AI-assisted engineering`

### Summary

Update project docs so engineers and AI agents know how to use the memory
subsystem correctly, without treating it as source-of-truth.

### Scope

- document the role of `src/memory/`
- document source-of-truth priority and anti-hallucination policy
- update AI memory entrypoints in `docs/00-project/ai/memory/` so they point to
  the new subsystem correctly
- document migration from current `scripts/memory` ownership
- document standard agent workflow:
  - search context before task
  - update source first
  - refresh memory after task
  - promote or drop session memory

### Non-goals

- do not duplicate policy in multiple conflicting docs
- do not keep docs and implementation ownership split ambiguously

### Acceptance criteria

- active docs explain where memory implementation lives
- docs do not present `src/memory/` as canonical business truth
- AI/runtime-facing entrypoints are updated to the new architecture
- the migration path is understandable to engineers and operators
