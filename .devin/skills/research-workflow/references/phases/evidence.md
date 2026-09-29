# Phase: evidence

> Router: `research-workflow --phase evidence --pillar <pillar>`. This file
> holds the phase body for the single `research-workflow` router skill
> (`../SKILL.md`). Do not promote it to a standalone skill.

## When to Use
- Researching a specific pillar and need to create traceable evidence objects
- Building evidence base for decision-making
- Conducting structured research with confidence scoring

## Prerequisites
- Ledger workspace initialized (Phase 1 complete)
- Pillar assignment (which pillar to research)
- Research scope from `01-pillars/PILLARS.md`

## Workflow Steps

<required>
1. Load pillar scope and research questions
2. Identify evidence sources
3. Collect raw evidence
4. Create Evidence Objects with semantic IDs
5. Validate evidence quality
6. Check evidence gate (minimum 5 per pillar)
</required>

## Evidence Sources

| Source Type    | Examples                        | Typical Confidence |
| -------------- | ------------------------------- | ------------------ |
| `url`          | Research reports, documentation | 60-90              |
| `pdf`          | Academic papers, whitepapers    | 70-95              |
| `interview`    | User interviews, expert calls   | 50-80              |
| `internal-doc` | Company data, prior research    | 60-85              |
| `experiment`   | A/B tests, prototypes           | 70-95              |
| `dataset`      | Analytics, survey results       | 65-90              |

## Evidence Object Schema

```yaml
id: EV-market-pricing-smb-wtp
pillar: market
source:
  type: url
  ref: "https://example.com/pricing-research"
  retrieved_at: 2026-01-21
claim: "SMB segment willingness-to-pay peaks at $29/mo for productivity tools."
quote: "Our survey of 500 SMBs found median WTP of $29/month..."
confidence: 0.75
assumptions:
  - "Survey sample representative of target market"
  - "WTP for 'productivity tools' applies to our specific category"
notes: "Sample skewed toward US companies. May need regional validation."
tags:
  - pricing
  - smb
  - wtp
```

## Quality Gates

Each Evidence Object must pass:

| Check               | Requirement               |
| ------------------- | ------------------------- |
| Falsifiable claim   | Claim can be proven wrong |
| Confidence assigned | 0.0-1.0 value present     |
| Assumptions listed  | At least 1 assumption     |
| Source traceable    | Can revisit the source    |
| ID is semantic      | Follows ID scheme         |

**Evidence Gate:** Minimum 5 Evidence Objects per pillar before proceeding to synthesis.

## Output

```markdown
## Evidence Collection Complete: [pillar]

**Evidence Objects Created:** [N]
**Gate Status:** [PASSED/FAILED]

### Evidence Summary
| ID | Claim Summary | Confidence |
|----|---------------|------------|
| EV-market-tam-b2b-saas | TAM is $X billion | 0.80 |
| EV-market-pricing-smb-wtp | SMB WTP peaks at $29/mo | 0.75 |
```

See also: [../evidence-object-schema.md](../evidence-object-schema.md),
[../id-generation-rules.md](../id-generation-rules.md),
[../research-protocols.md](../research-protocols.md).
