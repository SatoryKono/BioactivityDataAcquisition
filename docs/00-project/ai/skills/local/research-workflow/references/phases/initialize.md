# Phase: initialize

> Router: `research-workflow --phase initialize`. This file holds the phase
> body for the single `research-workflow` router skill
> (`../SKILL.md`). Do not promote it to a standalone skill.

## When to Use
- Starting a new product development project
- Beginning a research initiative that needs traceable evidence
- Creating a workspace for explicit decision-making

## Prerequisites
- User must provide a project brief (text description of what they're building)
- Optionally: custom path for ledger workspace (default: `./ledger/`)

## Workflow Steps

<required>
1. Parse the brief into structured components
2. Validate brief completeness (goals, constraints identifiable)
3. Create directory structure
4. Generate BRIEF.md
5. Generate PILLARS.md with default configuration
6. Confirm initialization complete
</required>

## Brief Validation

Extract from the user's input:

| Component        | Description                         | Required    |
| ---------------- | ----------------------------------- | ----------- |
| **Core idea**    | What is being built (1-2 sentences) | Yes         |
| **Target users** | Who will use this                   | Yes         |
| **Key goals**    | What success looks like             | Required    |
| **Constraints**  | What's explicitly out of scope      | Recommended |
| **Context**      | Any domain-specific information     | Optional    |

## Directory Structure

```bash
mkdir -p ledger/{00-brief,01-pillars}
mkdir -p ledger/02-evidence/{market,users,tech,competitors,design,legal,ops,economics}
mkdir -p ledger/{03-synthesis,04-decisions,05-risks,06-prd,07-architecture,08-plan,09-brand,10-gtm-ops}
```

## Output

```markdown
## Ledger Initialized

**Path:** ./ledger/
**Brief:** [2-3 sentence summary]

**Pillar Priorities:**
1. [High priority pillars]
2. [Medium priority pillars]
3. [Lower priority pillars]

**Next step:** Run research workflow with --phase evidence
```

See also: [../brief-template.md](../brief-template.md),
[../pillar-definitions.md](../pillar-definitions.md).
