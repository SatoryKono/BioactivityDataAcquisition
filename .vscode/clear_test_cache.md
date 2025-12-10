# Очистка кэша тестов VS Code

Если VS Code показывает ошибку о несуществующем тесте `test_unified_logger.py::test_logger_initialization_default`, выполните:

1. **Command Palette** (Ctrl+Shift+P):
   - `Python: Clear Cache and Reload Window`
   - или `Python: Refresh Tests`

2. **Если не помогло:**
   - Закройте VS Code
   - Удалите папки кэша (если есть):
     - `.vscode/.python`
     - `.pytest_cache`
   - Откройте VS Code заново
   - Выполните `Python: Discover Tests`

3. **Альтернатива:**
   - Перезагрузите окно: `Developer: Reload Window`

Файл `test_unified_logger.py` не существует в проекте. В папке `tests/bioetl/infrastructure/logging/` есть только `test_logging.py` с 4 тестами.

