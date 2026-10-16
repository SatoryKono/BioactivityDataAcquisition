Реализация независимого event-journal для collection/outcome receipts в `run_pytest_resilient.py` и небольшого pytest плагина.

**Отличие подхода:**
Вместо изменения штатных механизмов сбора диагностик/retry semantics, этот подход внедряет независимый легковесный pytest-плагин (`pytest_event_journal.py`). Плагин напрямую перехватывает хуки (collection, deselected, runtest_logreport, sessionfinish) и пишет события в атомарные JSONL-файлы (`receipt_<run_id>_<attempt>_<worker_id>_<unique_id>.jsonl`). Это гарантирует детерминированное сохранение истории collection и execution без двойного счёта, не конфликтует с retry.
Для проверки actual checkout SHA используется git (с mismatch fail).
Environment variables очищаются: используется строгий безопасный allowlist.

**Ограничения и integration risks:**
1. Если GITHUB_RUN_ID или GITHUB_RUN_ATTEMPT не установлены (например, при локальном запуске), используются значения "local" и "1".
2. Event-journal пишется на диск в реальном времени. При сбоях диска запись может прерваться (но не приведет к падению тестов, хотя receipt будет неполным).
3. Проверка SHA работает только при наличии `git`.

**Negative / Race cases доказательства:**
Тесты в `tests/architecture/ci/test_event_journal.py`:
- `test_event_journal_negative_secret_leak`: секреты в `os.environ` (например, `SUPER_SECRET_TOKEN`) гарантированно удаляются из receipt'ов.
- `test_event_journal_sha_mismatch`: если передать неверный SHA в `EXPECTED_CHECKOUT_SHA`, выполнение падает (mismatch).
- `test_event_journal_race_conditions`: запуск тестов в xdist (параллельно) создает атомарные независимые receipt-файлы от разных worker'ов без конфликтов записи.

Base SHA: 40fa210b9279c5a10568783815230a8955cc1d02
Head SHA: 4a872733e08137cd88edddbb0f3319be7f677b1e
