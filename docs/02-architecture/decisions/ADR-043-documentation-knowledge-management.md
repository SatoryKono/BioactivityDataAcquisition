______________________________________________________________________

Version: 1.0.0
Status: Accepted
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-30'

______________________________________________________________________

# ADR-043: Documentation and Knowledge Management Strategy

**Status:** Accepted

## **Date:** 2026-03-09 **Status:** Accepted **Decision makers:** @BioETL-Team **Related:** ADR-040 (diagram governance), ADR-041 (naming), ADR-042 (testing)

## Context

BioETL has 100+ documentation files across `docs/`, 43 ADRs, and extensive
inline documentation. However, several knowledge management gaps exist:

1. **ADR Coverage Gap**: No systematic way to identify undocumented architectural decisions
1. **Cross-reference Integrity**: Links between docs break as files move
1. **Provider Docs vs Runbooks Drift**: Provider reference docs and operational playbooks are separate concerns, but the docs policy does not state that clearly
1. **Glossary Synchronization**: Domain terms defined in multiple places without single source
1. **Documentation Drift**: Code changes without corresponding doc updates

### Conflict: Documentation Freshness vs Maintenance Burden

Comprehensive docs require ongoing maintenance. Over-documentation creates
stale content that misleads. The strategy must balance coverage with freshness.

______________________________________________________________________

## Decision

### 1. ADR Gap Detection

Architecture tests MUST verify that key components have corresponding ADRs:

```
Component Category → Required ADR Coverage:
- Each data provider      → Integration ADR
- Each domain port family → Design rationale ADR
- Each infrastructure pattern (circuit breaker, retry, etc.) → Pattern ADR
- Each DQ/governance rule → Policy ADR or RULES.md reference
```

### 2. Cross-Reference Validation

CI MUST validate internal documentation links:

- Markdown link targets must resolve to valid files or explicit published URLs
- ADR references in code comments point to existing ADRs
- RULES.md section references are valid

### 3. Provider Reference Docs and Operational Runbooks

Documentation MUST be split by concern:

- Provider reference docs MUST live under `docs/04-reference/providers/`
- Operational playbooks MUST live under `docs/05-operations/runbooks/`
- `docs/05-operations/runbooks/index.md` MUST index the active operational runbooks

For new providers:

- Provider reference documentation SHOULD be added under `docs/04-reference/providers/{provider}/`
- Provider-specific operational runbooks MAY be added when a provider has unique incident or recovery procedures
- A dedicated `docs/05-operations/runbooks/{provider}.md` file is NOT required by default

### 4. Glossary as Single Source of Truth

`docs/00-project/glossary.md` MUST be the canonical source for domain terms.
All other docs SHOULD link to glossary definitions rather than redefining.

### 5. AI Agent Profile Source of Truth

Runtime agent profiles under `.codex/agents/*.md` MUST be treated as the
canonical operational source for Codex workflows.

Published documentation mirrors under `docs/00-project/ai/agents/agents/*.md`
SHOULD mirror the runtime profiles and MUST NOT intentionally diverge on:

- provider inventory
- ADR inventory
- documentation topology and canonical paths

### 6. Doc Freshness Tracking

Each doc file SHOULD include a `Last verified:` date in frontmatter or header.
CI weekly job flags docs not verified in 90+ days.

______________________________________________________________________

## Consequences

### Positive

- Systematic ADR coverage prevents undocumented decisions
- Cross-reference validation catches broken links before merge
- Provider docs and operational runbooks have explicit boundaries
- Glossary unification reduces term ambiguity
- Runtime AI profiles and published mirrors use one shared fact model

### Negative

- ADR gap detection may initially flag many missing ADRs
- Provider reference docs still add maintenance work for new providers
- Freshness tracking needs human verification dates

### Risks

- **Doc overhead**: Mitigated by templates and automation
- **False positive broken links**: Mitigated by excluding external URLs

______________________________________________________________________

## Compliance

- RULES.md §5: Documentation standards
- ADR-040: Diagram governance (complements this ADR)
- ADR-041: Naming policy (skill/agent docs covered there)

## Rollout

- Rollout steps MUST be sequenced before broad adoption.
- Documentation, configuration, and test surfaces SHOULD be updated in the same change set when the decision is implemented.
- Breaking or migration-sensitive adoption SHOULD include an explicit transition window.

## Rollback

- Rollback MUST identify the last known-good behavior or artifact set.
- If the decision changes contracts, configuration, or storage semantics, rollback SHOULD include data and compatibility checks.
- Rollback triggers SHOULD be observable through tests, runtime signals, or regression symptoms.

## Verification

- Verify architecture, configuration, and documentation changes against the current codebase.
- Run the relevant tests, validators, or parity checks before considering the ADR fully adopted.
- Confirm downstream docs and contracts reflect the same decision boundaries.

## Acceptance Criteria

- [ ] The decision is documented with current status, date, and owner metadata.
- [ ] The implementation path or adoption boundary is testable and linked from the ADR.
- [ ] Supersession or migration impact is documented when the decision changes an earlier posture.
- [ ] Related docs, contracts, and operational guidance are aligned with this ADR.

## References

- [Documentation rules](../../00-project/RULES.md)
- [Documentation link checker](../../../scripts/docs/checks/check_links.py)
- [AI runtime mirror ownership policy](../../00-project/ai/agents/policy/AI_RUNTIME_MIRROR_OWNERSHIP.md)
