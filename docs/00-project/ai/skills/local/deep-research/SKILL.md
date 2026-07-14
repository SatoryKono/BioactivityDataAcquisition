> Mirror status: This file is a published/internal mirror under `docs/00-project/ai/**`. It is not a canonical runtime surface.
> Canonical runtime source: `.codex/skills/deep-research/SKILL.md`
> Governance: AI_RUNTIME_MIRROR_OWNERSHIP.md
> Edit the runtime source first, then refresh this mirror.
______________________________________________________________________

---
name: "deep-research"
description: "Use when asked for \"deep research\", \"thorough analysis\", \"comprehensive report\", \"investigate\", \"due diligence\", or when multiple sources are needed to answer complex questions. Produces well-sourced research reports through iterative refinement."
context: "fork"
agent: "general-purpose"
---

# Conducting Deep Research

## Source Of Truth

- Normative index: `../../../../NORMATIVE_SOURCES.md`
- Root runtime contract: `../../../../../../AGENTS.md`
- Project rules: `../../../../RULES.md`
- Requirements: `../../../../../01-requirements/REQUIREMENTS.md`
- Accepted ADRs in `../../../../../02-architecture/decisions/`
- Memory policy: `../../../agents/guides/MEMORY_USAGE.md`
- Post-change validation: `../../../agents/policy/POST_CHANGE_VALIDATION.md`

## Workflow

Use this skill for complex research, comparisons, due diligence, state-of-art
surveys, or questions requiring multiple sources. Do not use it for simple
lookups.

1. Clarify scope only when the topic, timeframe, geography, or success criteria
   are ambiguous.
1. Write a research brief with topic, scope, key questions, constraints, and
   response language.
1. Draft from existing knowledge and mark uncertainty.
1. Red-team the draft using [references/critique-framework.md](references/critique-framework.md).
1. Run targeted research with reflection after each search; use
   [references/search-patterns.md](references/search-patterns.md) for query
   selection.
1. Score sources, track contradictions, and cite claims using
   [references/source-evaluation.md](references/source-evaluation.md).
1. Refine the draft until claims are sourced, unsupported claims are removed,
   and contradictions are explicit.
1. Evaluate quality; repeat critique/research/refinement up to three cycles
   when the answer is still below decision quality.
1. Finalize using [references/report-templates.md](references/report-templates.md).

## Output Requirements

- Executive summary.
- Findings organized by research question.
- Methodology and source confidence.
- Limitations, gaps, and unresolved contradictions.
- Source list with confidence indicators.

## User Interaction

Ask for user input only when the scope is genuinely ambiguous, sources conflict
in a way that requires user judgment, or the user must choose between additional
research and finalizing with known limitations.
