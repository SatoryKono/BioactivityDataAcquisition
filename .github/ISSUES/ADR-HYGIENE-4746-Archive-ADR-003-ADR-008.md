# ADR hygiene: archive historical ADR-003 and ADR-008

**Status**: active
**Priority**: P1 (High)
**Labels**: `documentation`, `governance`
**GitHub Issue**: [#4746](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/4746)
**Issue State**: open
**Last synced**: 2026-05-29

## Problem

`ADR-003` и `ADR-008` должны оставаться историческими/superseded.
Оставление их в live-сетах как активных рекомендаций нарушает ADR governance boundaries.

## Execution Plan

1. Проверить и синхронизировать статус в:
   - `docs/02-architecture/decisions/README.md`
   - `docs/02-architecture/adr-registry.md`
   - `docs/02-architecture/adr-registry/registry.json`
2. Убрать/перенаправить активные ссылки, которые трактуют ADR-003/008 как действующие.
3. Уточнить исторический статус и место хранения для архивных материалов при необходимости:
   - `docs/99-archive/`

## Suggested File Targets

- `docs/02-architecture/decisions/README.md`
- `docs/02-architecture/adr-registry.md`
- `docs/02-architecture/adr-registry/index.md`
- `docs/00-project/RULES.md`

## Acceptance

- Нет active-doc links с ADR-003/008 как live guidance.
- ADR-003/008 корректно отмечены как historical/superseded во всех ADR реестрах.
