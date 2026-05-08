______________________________________________________________________

Version: 0.3.0
Status: draft
Class: repo-only
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last synchronized: '2026-05-08'

______________________________________________________________________

# D-09 Requirements Traceability (Draft Sync Note)

## Назначение

D-09 фиксирует рамку будущего consolidated handbook по трассируемости требований.
Сейчас это non-normative draft и он не заменяет published требования, ADR-реестр и test governance.

## Канонические источники

- `docs/01-requirements/REQUIREMENTS.md`
- `docs/02-architecture/decisions/README.md`
- `docs/02-architecture/decisions/ADR-042-testing-strategy-matrix.md`
- `docs/03-guides/testing.md`
- `docs/00-project/RULES.md`
- `configs/quality/test_matrix.yaml`
- `.github/workflows/tests.yml`
- `.github/workflows/docs.yml`

## Текущий validated контур (summary)

- Нормативный слой требований уже существует в `REQUIREMENTS.md` с REQ-ID и проверочными критериями.
- ADR governance и тестовая стратегия уже опубликованы и используются как основные traceability опоры.
- Для docs-only изменений основной runtime CI (`tests.yml`) intentionally не запускается из-за `paths-ignore` на `docs/**` и `*.md`.
- Контроль документации и link/sync checks уже выполняются отдельным docs-контуром.

## Текущие зоны дрейфа

- Отсутствует единый опубликованный requirements-traceability handbook/registry на уровне `docs/01-requirements/`.
- Черновые аналитические заметки быстро устаревают, если содержат “исполняемые решения” без фактической привязки к текущему governance contour.
- Любые инициативы по `REQ -> ADR -> tests -> CI -> release` должны идти через существующие policy/guides, а не через параллельный контур.

## План синхронизации D-09

1. Использовать D-09 как карту существующих traceability anchors, без дублирования нормативных требований.
1. Если вводится отдельный traceability registry (например, matrix/report), сначала ratify его через governance policy и docs workflow.
1. Любые CI-изменения по traceability согласовывать с действующими workflow boundaries (`tests.yml` vs `docs.yml`) и фиксировать в published guides.
1. После утверждения целевого traceability процесса перенести нормативный текст в `docs/01-requirements/` как published surface, а D-09 оставить кратким pointer-note.

## Критерии промоушена в future published handbook

1. Определён единый published source для requirements traceability (без параллельных реестров).
1. Термины и статусы трассируемости согласованы между `REQUIREMENTS`, ADR и testing governance.
1. Процесс traceability проверяется CI и имеет воспроизводимые команды в published docs.
