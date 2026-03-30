---
Version: 1.0.0
Status: Accepted
Class: published
Owner: BioETL Team
Reviewers:
- BioETL Team
Last verified: '2026-03-29'
---

# ADR-037: Canonical Schema Source and Generated Artifacts

**Date:** 2026-02-18

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

## Related

- ADR-002 (Medallion Architecture)
- ADR-018 (Gold strict validation)
- ADR-034 (Schema↔Domain config pairs)
