# Phase: synthesis

> Router: `research-workflow --phase synthesis --pillar <pillar>`. This file
> holds the phase body for the single `research-workflow` router skill
> (`../SKILL.md`). Do not promote it to a standalone skill.

## When to Use
- Evidence collection is complete for a pillar
- Need to extract actionable insights from raw evidence
- Transforming evidence into structured synthesis

## Prerequisites
- Evidence gate passed (≥5 evidence objects for this pillar)
- Evidence objects in `02-evidence/<pillar>/`

## Workflow Steps

<required>
1. Load all evidence objects for the pillar
2. Identify patterns and themes
3. Resolve or document contradictions
4. Extract key insights
5. Generate synthesis document
6. Link insights to evidence IDs
</required>

## Pattern Identification

Group evidence by theme:
- What claims cluster together?
- What topics have multiple evidence points?
- What themes emerge across sources?

## Insight Structure

```yaml
insight: "SMB segment has price sensitivity ceiling at $30/mo"
observation: "Multiple sources confirm $29-30 WTP peak"
implication: "Pricing above $30 requires enterprise features"
confidence: 0.75
evidence:
  - EV-market-pricing-smb-wtp
  - EV-competitors-pricing-benchmark
```

## Contradiction Handling

For contradictory evidence:
1. Note the contradiction explicitly
2. Assess confidence delta - Higher confidence wins if large gap
3. Check recency - More recent may supersede older
4. Check authority - More authoritative source wins
5. If unresolved - Document both, flag for decision-making

## Output

```markdown
## Synthesis Complete: [pillar]

**Evidence Analyzed:** [N] objects
**Key Insights:** [M]
**Contradictions:** [X] ([Y] resolved, [Z] pending)

### Top Insights
1. [Insight with evidence citation]
2. [Insight with evidence citation]
3. [Insight with evidence citation]

### Decisions Needed
- [Topic requiring DEC-*]
```

See also: [../synthesis-template.md](../synthesis-template.md),
[../evidence-decision-contract.md](../evidence-decision-contract.md).
