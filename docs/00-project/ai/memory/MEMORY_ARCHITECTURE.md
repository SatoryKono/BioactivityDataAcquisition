# BioETL AI Memory Architecture

This document describes repository-owned, vendor-neutral agent memory. It does
not redefine BioETL behavior or governance. `AGENTS.md` owns precedence.

## Taxonomy and ownership

| Layer | Source of truth | Owner | Lifecycle |
| --- | --- | --- | --- |
| Normative | RULES, REQUIREMENTS, accepted ADRs | architecture governance | Git and supersession |
| Procedural | active `.codex/**` runtime | AI runtime governance | reviewed and mirrored |
| Project knowledge | canonical sources; reviewed curated notes | domain/memory owner | review and archive |
| Task working | repository/task/worktree namespace | task owner | short-lived and prunable |
| Evidence | immutable events and digests | evidence producer | append-only |
| Decisions | records citing evidence digests | decision owner | append-only supersession |
| Derived retrieval | RAG, graph, timeline | memory tooling | delete and rebuild |
| Cache | IDE, interpreter, and tool state | producing tool | disposable |
| User memory | explicit repository-owned consent scope | user | controlled lifecycle |

Memory implementation stays outside `src/bioetl`. It MUST NOT introduce agent
I/O or hidden BioETL business rules into product layers.

## Source of truth and precedence

`src/memory/precedence.py` implements separate orders for runtime behavior and
implementation facts. Machine memory, session state, MCP content, IDE state,
and derived indexes never override canonical repository sources. Equal-rank
conflicts fail unresolved.

Vendor-managed conversation storage, compaction, retention, deletion, and
global preferences are **NOT_PROVEN** by repository evidence. Cursor, Gemini,
Junie, Copilot, Devin, and hosted model state remain external until verified.

## Registry, identity, and lifecycle

`src/memory/catalog/memory_registry.yaml` inventories known surfaces, owners,
readers, writers, canonicality, lifecycle, evidence, and runtime-usage status.
Its schema and validator are
`src/memory/schemas/memory_registry.schema.json` and
`src/memory/registry.py`. Unknown vendor use is recorded as `NOT_PROVEN`.

`src/memory/records.py` defines the common repository, commit, branch,
worktree, task, actor, source, trust, classification, status, and supersession
envelope. `src/memory/scope.py` discovers repository scope and task namespace.
Persistent readers MUST reject mismatched scope.

Evidence is immutable. Decisions and durable guidance change through
supersession or archive, not silent historical rewrite. Episodic notes follow
the TTL and density ceiling in `src/memory/policy/retention.yaml`; templates
are not pruned.

## Persistence modes

`BIOETL_AI_MEMORY_MODE` is resolved by `src/memory/persistence.py`.

| Mode | Reads | Writes |
| --- | --- | --- |
| `off` | denied | denied |
| `read-only` | allowed | denied |
| `read-write` | allowed | allowed |

Unknown values fail closed. The compatibility default is `read-write`;
security-sensitive and audit work SHOULD select an explicit restrictive mode.
A repository tool is compliant only when it propagates the mode to every note,
refresh, promotion, cache, evidence, user-memory, and MCP write. The variable
does not prove that an external vendor service obeys it.

The workflow propagates write capability and exposes the selected mode.
Pre-task in `off` mode returns a bounded disabled result before persistent
surface resolution, retrieval, refresh, or note creation.

## Evidence, decisions, and bounded handoff

`src/memory/evidence.py` hashes each evidence envelope and observation.
`EvidenceStore` appends atomically, rejects duplicate identity, and detects
digest mismatch. `DecisionRecord` cites resolvable evidence digests and uses
known `supersedes` links.

`src/memory/handoff.py` permits only bounded `files`, `symbols`, `commands`,
and `findings` context plus constraints and evidence digests. Full
conversations, unrelated user context, secrets, and hidden scratchpads are not
handoff fields.

## Security and user memory

Persistent records carry trust and security classification.
`src/memory/security.py` rejects untrusted direct persistence and detects
bounded prompt-injection, secret, and PII patterns without exposing matched
values. Scanning supplements, but does not replace, canonical verification and
reviewed trust transitions.

Repository-owned promotion, evidence, decision, user-memory, and workflow
write paths scan durable content before persistence. Shared file MCP
persistence is disabled unless explicitly enabled. Enforcement inside external
vendor and hosted backends remains **NOT_PROVEN**.

`src/memory/access.py` fails closed. `src/memory/user_memory.py` requires
active repository-scoped consent and explicit operation grants for enumerate,
export, correct, tombstone, delete, and consent revocation.

Transient repository-owned session/task state is stored only under
`src/memory/episodic/**`, where TTL and density policy apply.
`docs/00-project/ai/**` is a guidance mirror and must not contain generated
session records or raw conversation state.

This controls only repository-owned files. Vendor, IDE, MCP-provider, backup,
and hosted user-memory lifecycle remains **NOT_PROVEN**.

## Reliability, migration, and recovery

`src/memory/storage.py` supplies sidecar locking, optimistic digests,
temporary files, `fsync`, atomic replacement, and locked JSONL append. RAG
publication has transactional rollback.

A general schema-migration registry, full backup/restore workflow, backup
retention policy, and Neo4j recovery contract are not implemented. Until then:

- preserve original records and digests during manual migration;
- back up only classified stores without silently extending retention;
- local plaintext backup supports only `public` and `internal` records;
  `confidential` and `secret` backup fails closed until an approved at-rest
  protector adapter is supplied;
- verify restored digests;
- quarantine corrupt records instead of loading them.

## Verification

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m memory.tooling.validate --json
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest tests/unit/memory -q
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest tests/integration/memory -q
bash scripts/ops/support/skills/check_skills_mirror.sh --check
```

Never raise retention or technical-debt limits to make a gate pass.
