# Daily Workflow

This document defines the canonical daily memory workflow for AI agents and
engineers working in the BioETL repository.

Memory remains **source-first**:

- runtime truth stays in `src/bioetl/`, `docs/`, `configs/`, `tests/`,
  `.github/`, and `grafana/`
- `src/memory/` stores retrieval policy, graph/timeline/RAG surfaces, and
  durable or short-lived memory artifacts
- memory notes never outrank runtime code, configs, accepted ADRs, or active
  runbooks

## Standard Loop

Use this sequence for normal task work:

1. `pre-task` workflow
2. inspect retrieved context
3. confirm against canonical source files
4. perform the engineering change or audit
5. `post-task` workflow
6. promote only durable lessons or incidents
7. on a regular cadence run `review-curated` and archive superseded curated notes

The intended retrieval order is:

```text
catalog -> graph -> rag -> source
```

## Pre-Task

Run the standard pre-task workflow:

```bash
python -m memory.tooling.workflow pre-task \
  --task-id chembl-memory-audit \
  --title "Audit chembl activity ownership" \
  --query chembl_activity \
  --source-ref docs/plans/project-memory-layer-implementation-plan-2026-04-20.md \
  --json
```

What it does:

- runs local retrieval through `memory.query all`
- auto-refreshes rebuild-only RAG and timeline artifacts if manifests are
  missing
- creates an episodic session note in `src/memory/episodic/sessions/`

Use `--skip-session-note` if the task should not create a working note.

Use explicit retrieval inputs when you already have a temporary refresh root:

```bash
python -m memory.tooling.workflow pre-task \
  --task-id ops-smoke \
  --title "Check workflow gates" \
  --chunks-path /tmp/memory-refresh/rag/manifests/chunks.jsonl \
  --events-dir /tmp/memory-refresh/timeline/events
```

## During The Task

After pre-task retrieval:

- inspect `memory.query graph ...` if ownership or impact analysis is needed
- inspect retrieved RAG chunks and timeline events
- read the canonical source files directly before making a conclusion
- keep task-local findings in the session note instead of inventing hidden state

Typical follow-up commands:

```bash
python -m memory.query graph owner-pipeline chembl_activity
python -m memory.query rag --query chembl_activity --source-type code --profile implementation
python -m memory.query timeline --event-family run --query chembl_activity --profile operations
python -m memory.query all chembl_activity --profile architecture
```

## Post-Task

Run the standard post-task workflow after the source change or audit is done:

```bash
python -m memory.tooling.workflow post-task \
  --task-id chembl-memory-audit \
  --title "Audit chembl activity ownership" \
  --summary "Confirmed ownership path and updated memory workflow docs." \
  --source-ref src/memory/README.md \
  --prune \
  --json
```

What it does:

- creates an episodic summary note in `src/memory/episodic/summaries/`
- validates the memory subsystem
- refreshes rebuild-only RAG and timeline artifacts into a temporary output root
- optionally runs episodic prune in dry-run mode

If the outcome is durable, promote the summary:

```bash
python -m memory.tooling.workflow post-task \
  --task-id memory-hardening \
  --title "Memory hardening" \
  --summary "Documented a reusable lesson about source-first retrieval." \
  --source-ref src/memory/DAILY_WORKFLOW.md \
  --promote-to lesson \
  --move-on-promote
```

Supported promotion targets:

- `decision`
- `incident`
- `lesson`
- `domain_knowledge`

## Curated Review Ritual

Curated memory review is part of the regular engineering ritual, not an optional
cleanup command. Run it on a recurring cadence and before release, governance,
or architecture-review checkpoints:

```bash
python -m memory.tooling.workflow review-curated --json
```

What it does:

- reviews active curated notes
- classifies them as `current`, `due`, or `stale`
- highlights review candidates such as duplicate themes or thin provenance
- points you toward `keep`, `review`, or `review_or_archive`

Use it to keep curated memory small and durable:

- refresh `last_verified` when the note still matches source reality
- improve or merge notes when the knowledge is still useful but underspecified
- archive superseded notes with `python -m memory.tooling.archive_note ...`

## Engineering Scenarios

### Code change

- Use `pre-task` with a domain or symbol-oriented query.
- Read code and tests directly after retrieval.
- Use `post-task` to summarize the change and promote only if the lesson will
  matter again.

### Architecture review

- Use `pre-task` with ADR, ownership, or pipeline terms.
- Follow with `memory.query graph ...` to inspect structural neighbors.
- Promote only stable architectural guidance, not transient review commentary.

### Incident or run failure

- Use `pre-task` with pipeline name, alert name, workflow job, or manifest id.
- Follow with `memory.query timeline ...` and runbook sources.
- Promote incident summaries that encode durable operational lessons or new
  runbook knowledge.

### Documentation or governance audit

- Use `pre-task` with docs, policy, or placement keywords.
- Compare memory notes against canonical docs and config.
- Promote only durable guidance that reduces future drift.

## Promotion Rules

Promote a note only when it is:

- durable across more than one task
- supported by canonical source references
- useful to another engineer or agent without private context

Do not promote:

- raw debugging scratch notes
- one-off command outputs
- temporary branch-specific observations
- conclusions that were not verified against source

## Operational Notes

- `src/memory/episodic/` is short-lived and subject to pruning.
- `src/memory/curated/` is durable and versioned.
- `rag/manifests/`, `timeline/events/`, and `graph/exports/` are rebuild-only.
- If memory and runtime source disagree, runtime source wins.
