# Memory: py-doc-bot

*Статус: internal-only (agent memory)*

*Version: 1.0.1 | Date: 2026-04-06 | Parent: agent-memory.md*

> **Focus**: Documentation, ADR management, CHANGELOG, docstrings, glossary sync, doc-code consistency.

______________________________________________________________________

## 1. Identity & Scope

- **Role**: Documentation owner — post-refactor docs, ADR, CHANGELOG
- **Write zone**: `docs/`, docstrings in source files
- **Output artifacts**: `06-doc-update-log.md`
- **ID system**: `DOC-001`, `DOC-002`, ...
- **Model**: sonnet

## Evidence Anchors

When updating architecture, governance, or agent docs, sync against:

- `docs/reports/evidence/project-file-structure/SUMMARY.md`
- `docs/reports/evidence/project-file-structure/04-decisions/SUMMARY.md`
- `docs/reports/evidence/project-package-topology/SUMMARY.md`
- `docs/reports/evidence/project-package-topology/04-decisions/SUMMARY.md`
- `docs/reports/evidence/governance-signals/SUMMARY.md`
- `docs/reports/evidence/governance-signals/04-decisions/SUMMARY.md`

Prefer evidence-backed wording:

- package count is descriptive, not a standalone defect signal;
- family-level topology is the preferred hotspot narrative;
- governance signals should be cited when docs imply prioritization.

## Debt Tracking During Doc Updates

If documentation is updated because files changed, make sure the narrative
tracks technical debt correctly:

- do not present `hotspot inventory` as if it were enforceable `exemption debt`;
- if docs mention debt budgets or exemptions, sync wording with
  `configs/quality/debt_scorecard.yaml` and
  `configs/quality/architecture_metric_exemptions.yaml`;
- preserve the hard rule `ЗАПРЕЩЕНО УВЕЛИЧИВАТЬ ЛИМИТЫ ТЕХ. ДОЛГА.`;
- when a task closes, preserve the debt outcome wording:
  `improved`, `unchanged`, or `worsened`.

______________________________________________________________________

## 2. Documentation Structure

```
docs/
├── 00-project/
│   ├── 00-map.md                   # Navigation hub
│   ├── RULES.md                    # Constitution (единственный источник истины)
│   ├── glossary.md                 # Glossary (canonical terminology)
│   ├── ai/                         # Agent docs, memory, prompts
│   └── governance/                 # Governance policies
├── 01-requirements/
│   └── REQUIREMENTS.md             # Testable requirements
├── 02-architecture/
│   ├── decisions/                  # ADRs (verify live set before citing ranges)
│   ├── diagrams/                   # Canonical diagram source/render/docs tree
│   └── policies/                   # Architecture and review policies
├── 03-guides/                      # Guides & manuals
│   └── development/                # Developer-focused guides
├── 04-reference/                   # API documentation
│   ├── providers/                  # Provider reference docs
│   ├── pipelines/                  # Pipeline specs and xwalks
│   ├── contracts/                  # Contract artifacts
│   ├── schemas/                    # Auxiliary schemas
│   └── templates/                  # Templates and checklists
├── 05-operations/
│   ├── deployment/                 # Deployment and runtime ops
│   ├── runbooks/                   # Operational playbooks
│   └── verification/               # Verification reports
└── 99-archive/                     # Historical docs
```

### Root-level Docs

| File           | Purpose          |
| -------------- | ---------------- |
| `CHANGELOG.md` | Version history  |
| `README.md`    | Project overview |

______________________________________________________________________

## 3. ADR Management

### Current State

- ADR set: verify live from `docs/02-architecture/decisions/` before citing counts or ranges
- Status pattern: generally Accepted; ADR-008 is historically Superseded
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

| ADR     | Topic                                           |
| ------- | ----------------------------------------------- |
| ADR-007 | Circuit Breaker Implementation                  |
| ADR-010 | Local-Only Deployment                           |
| ADR-014 | Deterministic Writes                            |
| ADR-025 | Pipeline Config Unification                     |
| ADR-026 | Composite Pipeline Pattern                      |
| ADR-027 | DQ Rules Externalization                        |
| ADR-028 | Filter Rules Externalization                    |
| ADR-029 | Convention-based Config                         |
| ADR-033 | Publication Validation Strategy                 |
| ADR-037 | Canonical Schema Source and Generated Artifacts |
| ADR-038 | Enum Externalization to YAML                    |
| ADR-039 | Unified Entity Config Format                    |
| ADR-040 | Diagram Governance                              |

______________________________________________________________________

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

______________________________________________________________________

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

______________________________________________________________________

## 6. Glossary Sync

**Glossary file**: `docs/00-project/glossary.md`

Key terms to keep synchronized:

- Medallion layers (Bronze, Silver, Gold)
- Architecture patterns (Hexagonal, DDD, Ports & Adapters)
- Provider names and entity types
- ADR concepts (Content Hash, DQ Thresholds, etc.)

______________________________________________________________________

## 7. Doc-Code Sync Checks

### Statistics to Validate in RULES.md

| Statistic                    | How to Check                                                         |
| ---------------------------- | -------------------------------------------------------------------- |
| Number of ADRs               | `ls docs/02-architecture/decisions/ADR-*.md \| wc -l`                |
| Number of providers          | Check `src/bioetl/infrastructure/adapters/`                          |
| Number of architecture tests | `pytest tests/architecture/ --collect-only \| grep "test_" \| wc -l` |
| Coverage threshold           | Check `pyproject.toml` pytest config                                 |

### Cross-reference Validation

```bash
# Check for broken internal links (canonical checker — unified)
python -m scripts.docs check-links --links

# Check ADR references in code
grep -rn "ADR-[0-9]" src/bioetl/ --include="*.py" | head -20
```

### Unified Script Commands (docs & diagrams)

```bash
# Documentation checks
python -m scripts.docs check-links --links --specs --configs
python -m scripts.docs check-drift --ports --classes --json
python -m scripts.docs check-docstrings --summary --json --fail-under 90
python -m scripts.docs check-kpi --json-out reports/docs-kpi.json

# Documentation fixes
python -m scripts.docs fix-links-auto
python -m scripts.docs fix-links-explicit
python -m scripts.docs fix-link-warnings [paths...]
python -m scripts.docs audit-sentence

# Diagram management
python -m scripts.diagrams lint [paths...]
python -m scripts.diagrams lint-summarize <report>
python -m scripts.diagrams check quality-gates
python -m scripts.diagrams check svg-text
python -m scripts.diagrams fix operators [paths...]
python -m scripts.diagrams fix svg-text-fallback
python -m scripts.diagrams fix svg-styles
python -m scripts.diagrams render-pdf
python -m scripts.diagrams render-docx
python -m scripts.diagrams suite nightly
```

CI gates: `check-links` (`docs.yml`), `check-drift` (`architecture.yml`), `check-docstrings` (`architecture.yml`).
Pre-commit: `lint` (diagrams), `fix-orphans`.
Scheduled: `check-kpi` (Monday 4:00 UTC), `suite nightly` (2:20 UTC).

______________________________________________________________________

## 8. Modes of Operation

| Mode       | Purpose                                       |
| ---------- | --------------------------------------------- |
| `DOC`      | Update docs, docstrings, CHANGELOG            |
| `ADR`      | Create, validate, update ADRs                 |
| `ANALYSIS` | Sync statistics, cross-references, validation |
| `REFUSE`   | Insufficient data                             |

Always declare mode at the start of response.

______________________________________________________________________

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

______________________________________________________________________

## 10. Integration with Other Agents

| Event                            | Action                             |
| -------------------------------- | ---------------------------------- |
| py-test-bot (final pass)         | -> doc-bot updates docs/docstrings |
| py-audit-bot (doc drift finding) | -> doc-bot corrects drift          |
| orchestrator (new entity)        | -> doc-bot adds provider docs      |
| New ADR needed                   | -> doc-bot creates ADR             |
| Refactoring complete             | -> doc-bot updates CHANGELOG       |

______________________________________________________________________

## 11. Key Files for Documentation

| What                    | Path                                         |
| ----------------------- | -------------------------------------------- |
| RULES.md (Constitution) | `docs/00-project/RULES.md`                   |
| Glossary                | `docs/00-project/glossary.md`                |
| Navigation map          | `docs/00-project/00-map.md`                  |
| CHANGELOG               | `CHANGELOG.md`                               |
| ADR directory           | `docs/02-architecture/decisions/`            |
| Agent instructions      | `docs/00-project/ai/agents/guides/CLAUDE.md` |
| Agent persona           | `docs/00-project/ai/agents/guides/AGENT.md`  |

______________________________________________________________________

## 12. Provider Documentation

Locations:

- Provider reference docs: `docs/04-reference/providers/{provider}/`
- Pipeline specs and xwalks: `docs/04-reference/pipelines/{provider}/`
- Operational playbooks: `docs/05-operations/runbooks/` (not 1:1 with providers)

Each provider doc should cover:

- API overview and base URL
- Authentication requirements
- Rate limiting
- Available entity types
- Known limitations
- VCR cassette locations

______________________________________________________________________

*This memory file is specific to py-doc-bot. For general project context see `agent-memory.md`.*
