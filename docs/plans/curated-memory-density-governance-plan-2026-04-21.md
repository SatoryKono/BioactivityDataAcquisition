# Curated Memory Density Governance Plan

*Status: Working implementation plan*
*Date: 2026-04-21*
*Owner: BioETL Team*
*Scope: `src/memory/curated/` governance, review quality, and long-term density*

## Executive Summary

This plan defines the next governance wave for the BioETL curated memory layer.
The goal is to move `src/memory/curated/` beyond structurally valid notes into a
small, reviewable, high-signal knowledge layer that grows slowly and remains
useful across future engineering and AI-assisted tasks.

The memory subsystem already has:

- strict note schemas and validation;
- promotion policy;
- duplicate detection;
- archive tooling;
- curated review reporting;
- regular workflow integration through `python -m memory.tooling.workflow review-curated`.

The remaining challenge is not syntax or storage. The remaining challenge is
managed usefulness: deciding which curated notes should remain active, which
should merge, which should move into canonical docs, and which should be
archived.

## Goals

- Keep active curated memory small and dense.
- Promote only repeatable, source-backed knowledge with future reuse value.
- Prevent curated memory from becoming a second changelog, debugging diary, or
  duplicate documentation surface.
- Make review outcomes explicit and auditable.
- Add operational signals for low-value, duplicate, stale, or mislocated
  curated notes.
- Preserve source-first behavior: canonical code, configs, accepted ADRs,
  runbooks, and active docs still outrank memory.

## Non-Goals

- Do not replace ADRs, runbooks, or canonical documentation with curated memory.
- Do not require heavyweight semantic review infrastructure.
- Do not automatically rewrite docs or ADRs from curated notes.
- Do not block every PR on a full curated memory review.
- Do not promote branch-specific or one-off observations into durable memory.

## Current Baseline

The current curated memory layer already supports:

- `src/memory/policy/promotion.yaml` for promotion rules;
- `src/memory/tooling/promote_note.py` for promotion;
- `src/memory/tooling/archive_note.py` for archiving superseded notes;
- `src/memory/tooling/review_curated.py` for freshness and quality drift review;
- `src/memory/tooling/workflow.py review-curated` as the canonical ritual command;
- `src/memory/curated/REVIEW_LOOP.md` as the human review playbook.

This baseline is sufficient for safe operation. The next wave should improve
quality density rather than add broad new memory surfaces.

## Quality Model

Every active curated note should be evaluated against six usefulness dimensions.
These dimensions should begin as review criteria and only later become hard
validation requirements if the team sees consistent value.

### Reuse Value

The note should be useful outside the original task that created it. A note that
only explains what happened in one debugging session belongs in episodic memory,
an incident report, or the task history, not active curated memory.

High reuse examples:

- recurring operational failure patterns;
- repeatable architecture constraints;
- agent workflow rules that prevent future mistakes;
- domain knowledge that accelerates future implementation or review.

Low reuse examples:

- one-off command output;
- temporary branch state;
- “we fixed X” without a general lesson;
- observations that only make sense with private task context.

### Decision Value

The note should help future engineers or agents make decisions. If a note is
only descriptive and has no implication for future action, it is a weak curated
candidate.

Examples of decision value:

- explains when to use a memory layer versus canonical docs;
- clarifies promotion thresholds;
- records why a recurring workaround is acceptable or unacceptable;
- captures a trade-off that is likely to recur.

### Source Overlap

The note should not duplicate canonical docs, ADRs, runbooks, or source comments.
If canonical documentation already fully covers the knowledge, the curated note
should either link to it as supporting memory or be archived.

Outcomes:

- keep when the note adds durable interpretation not present elsewhere;
- merge when two curated notes express the same reusable lesson;
- promote to canonical docs when the knowledge should be part of official
  operational or architecture guidance;
- archive when the note only restates active canonical docs.

### Specificity

The note should be concrete enough to guide action. Generic advice such as
“keep memory clean” is not dense enough unless it names the exact repository
surface, workflow command, policy file, and failure mode.

Good specificity:

- names the affected subsystem;
- points to canonical source refs;
- explains the trigger condition;
- states the expected future behavior.

### Durability

The note should remain useful across several tasks or releases. Curated memory
should not be used for short-lived branch facts unless those facts are explicitly
part of a release or audit snapshot.

Durability should be downgraded when:

- the note depends on unmerged branch state;
- the note describes a temporary workaround;
- the note is tied to a tool behavior expected to change soon;
- the note lacks a stable source ref.

### Actionability

The note should tell a future reader what to do differently. A good curated note
does not merely summarize history; it changes future behavior.

Actionable notes usually contain:

- a rule;
- a warning;
- a decision threshold;
- a follow-up command;
- a clear “do not do this again” lesson.

## Review Outcomes

The curated review loop should classify non-keep notes into explicit outcomes.
These outcomes should appear in review reports and eventually in note metadata.

### `keep`

The note is current, source-backed, non-duplicative, and useful for future work.
No action is required beyond normal future review.

### `refresh`

The note remains useful, but one or more fields need updating:

- `last_verified`;
- source refs;
- summary wording;
- related links;
- review notes.

### `merge`

The note overlaps another curated note enough that the active layer would be
cleaner with one consolidated note. The merged note should retain the strongest
source refs and archive the superseded source notes with a clear reason.

### `archive`

The note is no longer useful as active curated memory. Reasons may include:

- superseded by canonical docs;
- superseded by another curated note;
- stale and no longer source-backed;
- too task-specific;
- low reuse value.

### `promote_to_canonical_docs`

The note is useful enough that memory-only storage is too weak. The right target
may be an ADR, runbook, project guide, glossary, or architecture document.
Tooling should recommend this outcome but should not automatically rewrite
canonical docs.

### `rewrite`

The underlying knowledge is useful, but the note is poorly expressed. Typical
signals include brief summary, weak actionability, missing section detail, or
thin source refs.

## Metadata Evolution

The following metadata should be introduced gradually. It should start as
optional, then become recommended, and only become required after real review
usage proves the fields are valuable.

```yaml
review_status: active
review_outcome: keep
last_reviewed: "2026-04-21T00:00:00Z"
review_notes:
  - "Still useful for promotion governance."
utility_tags:
  - repeatable
  - agent-workflow
  - governance
```

Recommended staged rollout:

1. Allow the fields in note parsing and validation.
1. Show the fields in `review_curated` output when present.
1. Add `mark_reviewed` tooling to update review metadata consistently.
1. Require `last_reviewed` only for notes that have passed a formal review.
1. Consider requiring `utility_tags` for new curated notes after adoption.

## Tooling Plan

### Extend `review_curated`

Add density-oriented review signals:

- `low_reuse_value`;
- `source_overlap:adr`;
- `source_overlap:runbook`;
- `source_overlap:docs`;
- `merge_candidate`;
- `archive_candidate`;
- `promote_to_docs_candidate`;
- `needs_stronger_evidence`;
- `low_actionability`;
- `low_specificity`.

The report should continue to be deterministic and conservative. It should
recommend review actions, not pretend to make all content decisions
automatically.

### Add `mark_reviewed`

Introduce a command such as:

```bash
python -m memory.tooling.mark_reviewed \
  --source src/memory/curated/lessons/example.md \
  --outcome keep \
  --note "Still source-backed and reusable."
```

Expected behavior:

- update `last_reviewed`;
- optionally update `last_verified`;
- set `review_outcome`;
- append review notes;
- preserve existing source refs.

### Add Merge Support

Introduce a command such as:

```bash
python -m memory.tooling.merge_notes \
  --primary src/memory/curated/lessons/a.md \
  --secondary src/memory/curated/lessons/b.md \
  --reason "Duplicate promotion guidance."
```

Expected behavior:

- create or update a consolidated active note;
- archive superseded notes with clear reasons;
- preserve source refs from both notes;
- record merge provenance.

### Promote-To-Docs Recommendation

Do not automatically write canonical docs. Instead, review tooling should emit a
recommendation such as:

```json
{
  "recommendation": "promote_to_canonical_docs",
  "target_surface": "runbook",
  "reason": "Operational guidance is durable and should be visible outside memory."
}
```

## Policy Updates

Update `src/memory/policy/promotion.yaml` with explicit rejection rules.

Do not promote:

- one-off debugging observations;
- raw command output;
- branch-specific facts without explicit release or audit scope;
- summaries without future action;
- knowledge fully covered by canonical docs;
- claims without canonical source refs;
- notes that require private task context.

Do promote:

- repeatable operational lessons;
- architecture constraints;
- recurring incident patterns;
- agent workflow rules;
- durable domain knowledge;
- working decisions not yet worth an ADR but useful across future tasks.

## Health Metrics

The curated review report should expose health metrics:

- total active notes;
- active notes by kind;
- due ratio;
- stale ratio;
- duplicate title count;
- duplicate id count;
- thin provenance count;
- merge candidate count;
- archive candidate count;
- promote-to-docs candidate count;
- notes with low utility signals;
- notes reviewed in the current cycle.

Suggested initial thresholds:

- `stale_ratio <= 10%`;
- `duplicate_theme_count == 0`;
- `thin_provenance_count == 0` for active curated notes;
- all `review_or_archive` notes handled before release checkpoints;
- curated layer growth stays low per review cycle unless explicitly justified.

## Engineering Ritual Integration

The regular ritual should be:

```bash
python -m memory.tooling.workflow review-curated --json
```

Run it:

- before release readiness checks;
- before governance review checkpoints;
- after large architecture or documentation waves;
- after incident/postmortem cleanup;
- on a recurring monthly or quarterly cadence.

Expected human actions:

- refresh notes that remain useful;
- merge duplicate lessons;
- archive superseded notes;
- promote durable canonical knowledge into docs or ADRs;
- avoid promoting task-local observations.

## Acceptance Criteria

This wave is complete when:

- `review_curated` reports freshness and density signals;
- review outcomes are documented and visible in output;
- `mark_reviewed` can update review metadata consistently;
- archive and merge candidates are surfaced by tooling;
- promotion policy explicitly rejects low-density curated notes;
- human-facing memory docs describe the density review ritual;
- tests cover due, stale, duplicate, merge-candidate, archive-candidate, and
  low-density examples.

## Recommended MVP

1. Extend `promotion.yaml` with utility and rejection rules.
1. Extend `review_curated` with density signals and health metrics.
1. Add `mark_reviewed` tooling.
1. Update `REVIEW_LOOP.md` with outcomes and thresholds.
1. Add tests for low-density, archive-candidate, and merge-candidate notes.

This MVP improves useful governance without adding expensive infrastructure or
pretending that content judgment can be fully automated.
