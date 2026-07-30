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
1. inspect retrieved context
1. confirm against canonical source files
1. perform the engineering change or audit
1. `post-task` workflow
1. promote only durable lessons or incidents
1. on a regular cadence run `review-curated` and archive superseded curated notes

The intended retrieval order is:

```text
catalog -> graph -> rag -> source
```

Select `BIOETL_AI_MEMORY_MODE=off|read-only|read-write` before work. Use
`read-only` for retrieval without writes and `read-write` only when persistent
updates are authorized. In `off` mode, pre-task returns a bounded disabled
result before persistent surface resolution, retrieval, refresh, or note
creation. Vendor-hosted conversation and IDE state are **NOT_PROVEN** and are
not controlled merely by setting this variable.

When `read-only` retrieval needs missing rebuild-only RAG or timeline
projections, `pre-task` may build them under an isolated temporary directory.
It ignores a caller-provided refresh output root in this mode, creates no
session note, and does not mutate repository-owned memory surfaces.

## Pre-Task

Run the standard pre-task workflow:

```bash
python -m memory.tooling.workflow pre-task \
  --task-id chembl-memory-audit \
  --title "Audit chembl activity ownership" \
  --query chembl_activity \
  --profile audit \
  --source-ref docs/plans/project-memory-layer-implementation-plan-2026-04-20.md \
  --json
```

What it does:

- runs local retrieval through `memory.query all`
- auto-refreshes only the missing rebuild-only surfaces; timeline recovery no
  longer waits on a full RAG rebuild
- uses a bounded workflow-time RAG rebuild when temporary chunk manifests are
  needed, instead of rebuilding the full deterministic corpus during every
  pre-task call
- validates the catalog/chunk pair before retrieval; a stale, incomplete, or
  source-mismatched pair is treated as unavailable and refreshed or reported as
  degraded
- creates an episodic session note in `src/memory/episodic/sessions/`

If refresh is skipped with `--skip-refresh-if-missing`, the workflow still
returns catalog context and creates the session note, but marks the payload as
degraded when RAG or timeline artifacts are absent.

Use `--profile` to align ranking with the task type: `general`,
`architecture`, `implementation`, `operations`, or `audit`.

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
- capture durable observations as evidence before drawing a decision
- provide subagents only bounded files, symbols, commands, findings,
  constraints, and evidence digests

Evidence and conclusions are separate. A changed conclusion creates a
superseding decision; it does not mutate cited evidence.

Typical follow-up commands:

```bash
python -m memory.query graph owner-pipeline chembl_activity
python -m memory.query rag --query chembl_activity --source-type code --profile implementation
python -m memory.query rag --query runner --file-context src/bioetl/application/core/runner.py --auto-refresh --expanded-graph-path src/memory/graph/projections/bioetl_knowledge_graph_expanded.json
python -m memory.query timeline --event-family run --query chembl_activity --profile operations
python -m memory.query refs src/bioetl/application/core/runner.py --auto-refresh --expanded-graph-path src/memory/graph/projections/bioetl_knowledge_graph_expanded.json
python -m memory.query impact src/bioetl/application/core/runner.py --auto-refresh --expanded-graph-path src/memory/graph/projections/bioetl_knowledge_graph_expanded.json
python -m memory.query module-impact bioetl.application.core.runner --auto-refresh --expanded-graph-path src/memory/graph/projections/bioetl_knowledge_graph_expanded.json
python -m memory.query all chembl_activity --profile architecture --auto-refresh
```

Use `--auto-refresh` when rebuild-only RAG, timeline, or file-relation artifacts
are absent and you want a temporary query-local refresh instead of writing
generated manifests under `src/memory/`. Timeline directories that contain only
placeholder files are treated as not ready and will refresh when
`--auto-refresh` is enabled.

Use `module-impact` or `module-neighborhood` when the useful boundary is a
Python module import relationship; use `impact` or `neighborhood` when the
question starts from a concrete file path.

## Post-Task

Run the standard post-task workflow after the source change or audit is done:

```bash
python -m memory.tooling.workflow post-task \
  --task-id chembl-memory-audit \
  --title "Audit chembl activity ownership" \
  --summary "Confirmed ownership path and updated memory workflow docs." \
  --source-ref src/memory/README.md \
  --validation-timeout-seconds 15 \
  --prune \
  --json
```

What it does:

- creates an episodic summary note in `src/memory/episodic/summaries/`
- validates the memory subsystem
- runs validation with a bounded timeout during the workflow path and returns a
  degraded payload instead of hanging indefinitely when validation exhausts the
  time budget
- refreshes rebuild-only RAG and timeline artifacts into a temporary output root
  with the same bounded workflow-time RAG scope used by `pre-task`
- treats partial refresh failures as degraded follow-up signals instead of
  blocking summary-note creation
- optionally runs episodic prune in dry-run mode, using the policy-backed
  density threshold from `src/memory/policy/retention.yaml`
- bounds both validation and the default post-task refresh when run through the
  CLI, returning an explicit degraded JSON payload instead of hanging on slow
  validation or timeline/RAG refresh work.

Do not use the write-capable post-task path in `off` or `read-only` mode.
Retention apply remains explicit; archive and deletion are distinct.
Migration, general backup/restore, and external-service deletion are not
automated by this workflow.

Use `python -m memory.tooling.prune --json` for the policy-default density
report or `python -m memory.tooling.prune --max-active <N> --json` for an
explicit override. The default cadence is a dry-run review every 7 days with a
target ceiling of 1000 active episodic notes. Use
`python -m memory.tooling.validate --include-working-tree-junk` when local
Python cache files under `src/memory/` should fail validation. Memory tooling
processes disable Python bytecode writes by default, and dev wrappers should
preserve `PYTHONDONTWRITEBYTECODE=1`.

Set `--validation-timeout-seconds 0` only when you intentionally want the
workflow to wait for a full in-process validation scan regardless of duration.
Set `--refresh-timeout-seconds 0` only when you intentionally want post-task
refresh to run in-process without the CLI subprocess timeout. The CLI default
post-task refresh timeout is `120` seconds so cold mounted or cloud-synced
checkouts can finish bounded workflow-scope RAG and timeline refresh before the
workflow returns a degraded payload.

For a lightweight health check that exercises pre-task and post-task without
committing rebuild-only artifacts:

```bash
python -m memory.tooling.workflow smoke --json
```

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
  (default minimum: 2 source refs)
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
- Generated RAG and timeline artifacts are rebuild-only. Canonical full RAG
  output lives in `derived/rag/manifests/`; `rag/manifests/` is a read-only
  migration fallback, and neither lane tracks generated JSON/JSONL files.
- Workflow-scope RAG output is ephemeral and must stay outside both canonical
  in-repo manifest lanes. Readers require the catalog/chunk pair, source
  content, eligible source set, and source identity to validate together.
- `graph/exports/` is rebuild-only.
- If memory and runtime source disagree, runtime source wins.
