# Именованный блокер: Требуется уточнение scope для регрессии покрытия

## Детали блокера
Пользователь запретил продолжать предложенное расширение тестов для регрессии покрытия без уточнения scope. Я предоставляю существующие результаты по запросу и завершаю сессию как именованный блокер для ожидания определения scope и назначения ответственного.

## Существующие результаты

*   **Main SHA:** `a02ef44c00e6c39496fdc1d5ec72b050cd24d4f5`
*   **Упавшая Job:** `tests / coverage-verify`
*   **URL упавшей Job:** `https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/40442852679/job/121989342330`
*   **Отчёты покрытия модулей:**
    *   `src/bioetl/domain/normalization/rules.py`: coverage regressed 100.00% -> 94.96%
    *   `src/bioetl/infrastructure/observability/observability_backend_probes.py`: coverage regressed 100.00% -> 95.83%
*   **Связанные коммиты / PR:**
    *   `e3bfc2eac26b88382aad5029fa0a34a4bf2763ea` (PR #12435): Встраивание очистки строк в правила нормализации (`src/bioetl/domain/normalization/rules.py`).
    *   `f5c3b438160ff79af9e16be7333c84f8e6a61805` (PR #12540): Ограничение URL-схем в HTTP-зондах (`src/bioetl/infrastructure/observability/observability_backend_probes.py`).
*   **Текущая рабочая ветка:** `main` (выполнен fetch/merge с `origin/main` во время анализа)
*   **Сохраненные измерения:**
    *   В локальном анализе при запуске pytest с `--cov-report=term-missing`, `rules.py` показал падение покрытия до 51% - 39% из-за пропущенных импортов, что является известным артефактом структуры набора тестов и изоляции.
    *   `metrics_publisher_adapter.py` также показал 0% покрытия во время локального исследования.

**Необходимое действие:**
Ожидание назначения владельца проблемы и определения полного scope для проблемы покрытия. Не приступайте к добавлению новых тестов до разрешения этого вопроса.
