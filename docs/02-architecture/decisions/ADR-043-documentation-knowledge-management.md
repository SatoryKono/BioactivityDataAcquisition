# ADR-043: Documentation and Knowledge Management Strategy

**Status:** Accepted
**Date:** 2026-03-09
**Authors:** Claude (architecture review)
**Supersedes:** —
**Related:** ADR-040 (diagram governance), ADR-041 (naming), ADR-042 (testing)

---

## Context

BioETL has 100+ documentation files across `docs/`, 41 ADRs, and extensive
inline documentation. However, several knowledge management gaps exist:

1. **ADR Coverage Gap**: No systematic way to identify undocumented architectural decisions
2. **Cross-reference Integrity**: Links between docs break as files move
3. **Provider Runbook Template**: New providers lack standardized onboarding docs
4. **Glossary Synchronization**: Domain terms defined in multiple places without single source
5. **Documentation Drift**: Code changes without corresponding doc updates

### Conflict: Documentation Freshness vs Maintenance Burden

Comprehensive docs require ongoing maintenance. Over-documentation creates
stale content that misleads. The strategy must balance coverage with freshness.

---

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
- Markdown link targets exist (`[text](path)` → path is valid file)
- ADR references in code comments point to existing ADRs
- RULES.md section references are valid

### 3. Provider Runbook Template

Each provider MUST have a runbook in `docs/05-operations/runbooks/{provider}.md`:

```yaml
# Template sections:
- Overview: Provider purpose, data types, API version
- Authentication: How to obtain and configure credentials
- Rate Limits: Provider-specific limits and BioETL configuration
- VCR Recording: Steps to record/update cassettes
- Troubleshooting: Common errors and resolutions
- Data Quality: Provider-specific DQ considerations
- Contacts: API support, documentation links
```

### 4. Glossary as Single Source of Truth

`docs/04-reference/glossary.md` MUST be the canonical source for domain terms.
All other docs SHOULD link to glossary definitions rather than redefining.

### 5. Doc Freshness Tracking

Each doc file SHOULD include a `Last verified:` date in frontmatter or header.
CI weekly job flags docs not verified in 90+ days.

---

## Consequences

### Positive
- Systematic ADR coverage prevents undocumented decisions
- Cross-reference validation catches broken links before merge
- Provider runbooks standardize onboarding experience
- Glossary unification reduces term ambiguity

### Negative
- ADR gap detection may initially flag many missing ADRs
- Provider runbook requirement adds docs work for new providers
- Freshness tracking needs human verification dates

### Risks
- **Doc overhead**: Mitigated by templates and automation
- **False positive broken links**: Mitigated by excluding external URLs

---

## Compliance

- RULES.md §5: Documentation standards
- ADR-040: Diagram governance (complements this ADR)
- ADR-041: Naming policy (skill/agent docs covered there)
