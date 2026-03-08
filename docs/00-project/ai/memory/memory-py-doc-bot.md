# Memory: py-doc-bot

*Version: 1.0.0 | Date: 2026-02-23 | Parent: agent-memory.md*

> **Focus**: Documentation, ADR management, CHANGELOG, docstrings, glossary sync, doc-code consistency.

---

## 1. Identity & Scope

- **Role**: Documentation owner — post-refactor docs, ADR, CHANGELOG
- **Write zone**: `docs/`, docstrings in source files
- **Output artifacts**: `06-doc-update-log.md`
- **ID system**: `DOC-001`, `DOC-002`, ...
- **Model**: sonnet

---

## 2. Documentation Structure

```
docs/
├── 00-project/
│   ├── RULES.md                    # Constitution (единственный источник истины)
│   ├── glossary.md                 # Glossary (canonical terminology)
│   └── agents/
│       ├── CLAUDE.md               # Agent instructions
│       └── AGENT.md                # Agent persona
├── 00-map.md                       # Navigation hub
├── 01-getting-started/             # Onboarding guides
├── 02-architecture/
│   ├── decisions/                  # ADRs (ADR-001 through ADR-040)
│   └── diagrams/                   # Mermaid diagrams
├── 03-guides/                      # Development guides
├── 04-reference/                   # API documentation
├── 05-operations/
│   └── runbooks/                   # Operational runbooks
└── 04-reference/pipelines/          # Provider-specific pipeline docs
```

### Root-level Docs

| File | Purpose |
|------|---------|
| `CHANGELOG.md` | Version history |
| `README.md` | Project overview |

---

## 3. ADR Management

### Current State
- 40 ADRs: ADR-001 through ADR-040 (all present, verified 2026-02-27)
- All in status: Accepted (except ADR-008: Superseded)
- Location: `docs/02-architecture/decisions/`

### ADR Template

```markdown
# ADR-0XX: <Title>

## Status
Accepted | Proposed | Deprecated | Superseded by ADR-0YY

## Context
<Why this decision is needed>

## Decision
<What was decided>

## Consequences
### Positive
- <benefit>

### Negative
- <tradeoff>

### Neutral
- <observation>
```

### Key ADR Reference

| ADR | Topic |
|-----|-------|
| ADR-007 | Circuit Breaker Implementation |
| ADR-010 | Local-Only Deployment |
| ADR-014 | Deterministic Writes |
| ADR-025 | Pipeline Config Unification |
| ADR-026 | Composite Pipeline Pattern |
| ADR-027 | DQ Rules Externalization |
| ADR-028 | Filter Rules Externalization |
| ADR-029 | Convention-based Config |
| ADR-033 | Publication Validation Strategy |
| ADR-037 | Canonical Schema Source and Generated Artifacts |
| ADR-038 | Enum Externalization to YAML |
| ADR-039 | Unified Entity Config Format |
| ADR-040 | Diagram Governance |

---

## 4. CHANGELOG Conventions

```markdown
# Changelog

## [Unreleased]

### Added
- New feature description

### Changed
- Modified behavior description

### Fixed
- Bug fix description

### Removed
- Removed feature description
```

---

## 5. Docstring Conventions

### Module-level

```python
"""Module description.

Provides <functionality> for the <layer> layer.
Part of the <subsystem> subsystem.
"""
```

### Class-level

```python
class MyService:
    """Brief one-line description.

    Detailed description if needed.
    Implements <Port/Protocol> for <purpose>.

    Args:
        client: HTTP client for API communication.
        logger: Structured logger instance.
    """
```

### Method-level

```python
def transform(self, records: list[dict[str, Any]]) -> list[Entity]:
    """Transform raw API records into domain entities.

    Args:
        records: Raw records from API response.

    Returns:
        List of validated domain entities.

    Raises:
        ValidationError: If record fails schema validation.
    """
```

---

## 6. Glossary Sync

**Glossary file**: `docs/00-project/glossary.md`

Key terms to keep synchronized:
- Medallion layers (Bronze, Silver, Gold)
- Architecture patterns (Hexagonal, DDD, Ports & Adapters)
- Provider names and entity types
- ADR concepts (Content Hash, DQ Thresholds, etc.)

---

## 7. Doc-Code Sync Checks

### Statistics to Validate in RULES.md

| Statistic | How to Check |
|-----------|-------------|
| Number of ADRs | `ls docs/02-architecture/decisions/ADR-*.md \| wc -l` |
| Number of providers | Check `src/bioetl/infrastructure/adapters/` |
| Number of architecture tests | `pytest tests/architecture/ --collect-only \| grep "test_" \| wc -l` |
| Coverage threshold | Check `pyproject.toml` pytest config |

### Cross-reference Validation

```bash
# Check for broken internal links (canonical checker)
python scripts/check_doc_links.py --links

# Check ADR references in code
grep -rn "ADR-[0-9]" src/bioetl/ --include="*.py" | head -20
```

---

## 8. Modes of Operation

| Mode | Purpose |
|------|---------|
| `DOC` | Update docs, docstrings, CHANGELOG |
| `ADR` | Create, validate, update ADRs |
| `ANALYSIS` | Sync statistics, cross-references, validation |
| `REFUSE` | Insufficient data |

Always declare mode at the start of response.

---

## 9. DOC Update Log Template

```markdown
### DOC-001: <title>

**Date**: YYYY-MM-DD HH:MM
**RF**: RF-001 (or standalone)
**Mode**: DOC | ADR | ANALYSIS

#### Changes
| File | Action | Description |
|------|--------|-------------|
| `docs/02-architecture/decisions/ADR-034.md` | created | New ADR for ... |
| `src/bioetl/application/pipelines/...` | modified | Updated docstrings |

#### Verification
- [ ] All internal links valid
- [ ] Glossary terms consistent
- [ ] RULES.md statistics accurate
- [ ] CHANGELOG updated
```

---

## 10. Integration with Other Agents

| Event | Action |
|-------|--------|
| py-test-bot (final pass) | -> doc-bot updates docs/docstrings |
| py-audit-bot (doc drift finding) | -> doc-bot corrects drift |
| orchestrator (new entity) | -> doc-bot adds provider docs |
| New ADR needed | -> doc-bot creates ADR |
| Refactoring complete | -> doc-bot updates CHANGELOG |

---

## 11. Key Files for Documentation

| What | Path |
|------|------|
| RULES.md (Constitution) | `docs/00-project/RULES.md` |
| Glossary | `docs/00-project/glossary.md` |
| Navigation map | `docs/00-map.md` |
| CHANGELOG | `CHANGELOG.md` |
| ADR directory | `docs/02-architecture/decisions/` |
| Agent instructions | `docs/00-project/ai/agents/guides/CLAUDE.md` |
| Agent persona | `docs/00-project/ai/agents/guides/AGENT.md` |

---

## 12. Provider Documentation

Location: `docs/04-reference/pipelines/{provider}/`

Each provider doc should cover:
- API overview and base URL
- Authentication requirements
- Rate limiting
- Available entity types
- Known limitations
- VCR cassette locations

---

*This memory file is specific to py-doc-bot. For general project context see `agent-memory.md`.*
