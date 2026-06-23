______________________________________________________________________

Version: 1.0.0
Status: Accepted
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-30'

______________________________________________________________________

# ADR-037: Canonical Schema Source and Generated Artifacts

**Date:** 2026-02-18
**Status:** Accepted
**Decision makers:** @BioETL-Team

## Context

В проекте одновременно поддерживаются три типа schema-артефактов:

1. Pandera Silver schemas (`src/bioetl/domain/schemas/...`)
1. PyArrow Silver schemas (`src/bioetl/infrastructure/schemas/silver.py`)
1. Gold contracts (`src/bioetl/domain/contracts/gold/...` + `docs/04-reference/contracts/gold/*.json`)

До этого изменения обновление выполнялось частично вручную. Это приводило к
рискy drift между конфигурациями и runtime-артефактами.

## Decision

Каноническим источником schema-структуры для provider/entity pair объявляются:

- `configs/entities/{provider}/{entity}.yaml` — структура column groups и
  композиция полей,
- typed annotations в Silver Pandera schema classes — типовая семантика полей.

На этой основе вводится единый генератор `scripts/schema/generate_schema_artifacts.py`,
который:

1. генерирует Pandera-canonical registry
   (`src/bioetl/domain/schemas/generated/registry.py`),
1. генерирует Gold JSON contracts через существующий exporter
   (`src/tools/scripts/schema/generate_contracts.py`),
1. поддерживает режим `--check` для CI gate по stale generated artifacts.

## Consequences

### Positive

- Единая точка входа для schema generation.
- CI гарантирует отсутствие незакоммиченных изменений в generated artifacts.
- Улучшается трассируемость schema provenance (registry → YAML paths).

### Trade-offs

- Требуется запуск генератора при изменениях schema-конфигураций.
- CI добавляет отдельный blocking job на проверку generated artifacts.

## References

- ADR-002 (Medallion Architecture)
- ADR-018 (Gold strict validation)
- ADR-034 (Schema↔Domain config pairs)

## Compliance

| Control      | Requirement                                                                | Status | Evidence                                 |
| ------------ | -------------------------------------------------------------------------- | ------ | ---------------------------------------- |
| Format       | ADR MUST use standard metadata and normalized section headings             | `pass` | `ADR-037-canonical-schema-generation.md` |
| Status       | ADR status MUST be explicit and consistent                                 | `pass` | `Accepted`                               |
| Supersession | Superseded or superseding ADRs SHOULD be linked explicitly when applicable | `n/a`  | `metadata block`                         |
| Verification | Implementation and validation expectations MUST be documented              | `pass` | `Verification / Acceptance Criteria`     |
| References   | Related ADRs, docs, or artifacts SHOULD be linked                          | `pass` | `References`                             |

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
