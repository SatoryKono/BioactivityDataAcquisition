# Паспорт закрытия: P17-002

- **Владелец работы:** Jules
- **Срок:** 2026-10-25
- **Точная ревизия (SHA):** c08883508249e87d297f3b306e7a4d032e36de02
- **Область:** `.github/workflows/reusable-setup.yml`, `.github/workflows/reusable-mermaid-setup.yml`
- **Версии инструментов и backend:** `curl`, GitHub API (поиск кода)
- **Команды и exit codes:**
  - `grep -rn "reusable-setup.yml" .github/workflows/` (exit 1)
  - `grep -rn "reusable-mermaid-setup.yml" .github/workflows/` (exit 1)
  - `curl -s -I "https://api.github.com/search/code?q=SatoryKono/BioactivityDataAcquisition/.github/workflows/reusable-setup.yml"` (HTTP 401 Unauthorized)
- **Тестовые данные:** N/A
- **Ожидаемый результат:** Найти внешних потребителей (callers) для deprecated reusable workflows, чтобы спланировать их миграцию.
- **Допустимые пропуски:** N/A
- **Ссылка на доказательства:** Отсутствует
- **Независимый проверяющий:** N/A

## Результаты проверки

1. **Локальные callers:**
   - `reusable-setup.yml`: 0 использований локально (MEASURED)
   - `reusable-mermaid-setup.yml`: 0 использований локально (MEASURED)

2. **Внешние callers:**
   - Статус: UNKNOWN.
   - **BLOCKER:** Поиск внешних callers через GitHub API заблокирован ошибкой 401 Unauthorized. Отсутствует `GH_TOKEN` или аутентификация в `gh cli`. Невозможно подтвердить отсутствие внешних потребителей.

## Вывод
Статус - BLOCKED. Issue #12482 остается открытой, файлы не удаляются.
