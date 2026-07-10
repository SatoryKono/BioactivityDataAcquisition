---
name: "nci-analysis"
description: "Use when asked to analyze content for manipulation, propaganda, disinformation patterns, or when user provides a URL or text asking \"is this manipulative?\", \"analyze this for bias\", \"check for propaganda\", or similar requests. Detects emotional manipulation, suspicious timing, uniform messaging, tribal division, and missing information across 20 categories."
context: "fork"
agent: "general-purpose"
---

# NCI Manipulation Analysis

## Source Of Truth

- Root runtime contract: `../../../AGENTS.md`
- Project rules: `../../../docs/00-project/RULES.md`
- Requirements: `../../../docs/01-requirements/REQUIREMENTS.md`
- Accepted ADRs: `../../../docs/02-architecture/decisions`
- Normative index: `../../../docs/00-project/NORMATIVE_SOURCES.md`
- Deep research method: [../deep-research/SKILL.md](../deep-research/SKILL.md)

## Core Principle

Score influence patterns in the content, not the author's intent or whether the
content is politically agreeable. Accuracy checks are separate and use
`deep-research` when NCI triggers require claim verification.

## Workflow

1. Process input as text or fetch the URL content.
1. Score all 20 categories using
   [references/categories.md](references/categories.md).
1. Calculate composite factors and overall score using
   [references/scoring.md](references/scoring.md).
1. Check deep-research triggers:
   - overall score > 40
   - suspicious timing > 3
   - authority issues > 3
   - cherry-picking > 3
   - historical parallels > 2
1. If triggered, verify 3-5 key factual claims with `deep-research` and source
   scoring from [../deep-research/references/source-evaluation.md](../deep-research/references/source-evaluation.md).
1. Generate both manipulative and legitimate interpretations.
1. Produce the report with category evidence, confidence, limitations, and any
   verification adjustments.

## Output Requirements

- Content summary.
- Overall NCI score on 0-100 scale.
- Five composite factors.
- Top manipulation indicators with evidence snippets.
- Claim verification table when triggered.
- Manipulative interpretation and legitimate interpretation.
- Limitations and confidence.

## References

- [references/categories.md](references/categories.md) - 20 category definitions.
- [references/scoring.md](references/scoring.md) - weights and formulas.
- [references/examples.md](references/examples.md) - calibration examples.
- [references/vocabulary.md](references/vocabulary.md) - detection vocabulary.
- [references/guidance.md](references/guidance.md) - practical factor guidance.

## User Interaction

Ask only when content type is ambiguous, verification depth requires user
trade-off, or output format materially changes the work.

