# Паспорт закрытия: P17-003-external-callers

- **Владелец работы:** Jules
- **Срок:** 2026-10-26
- **Точная ревизия (SHA):** aff36be4c4c080f4ca92a189189d7c5dab208618
- **Область:** External callers of reusable workflows
- **Версии инструментов и backend:** curl, GitHub API
- **Команды и exit codes:**
  - curl (HTTP 200, 0 results but incomplete visibility)
- **Ожидаемый результат:** Find external callers to plan migration.
- **Допустимые пропуски:** N/A
- **Ссылка на доказательства:** This file.
- **Независимый проверяющий:** N/A

## Результаты проверки

1. **Внешние callers:**
   - Статус: UNKNOWN.
   - **BLOCKER:** Global code search is restricted. Both GITHUB_TOKEN_02 and SARIF_GITHUB_TOKEN returned 0 results for `uses:SatoryKono/BioactivityDataAcquisition/.github/workflows/reusable-setup.yml` and `reusable-mermaid-setup.yml`, but these are personal access tokens limited to the user's visibility scope (User: SatoryKono, 0 orgs). Without global or organizational access, external visibility is strictly incomplete. I cannot confirm zero callers.

## Вывод
Статус - BLOCKED. Issue #12482 remains open, workflows are not deleted.
