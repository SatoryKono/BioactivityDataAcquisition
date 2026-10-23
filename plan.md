1. **Обновление документации (docs/04-reference/environment-variables.md)**
   - Добавить отсутствующие переменные в таблицу `Core Configuration`: `BIOETL_DEBUG`, `BIOETL_TEST_MODE`, `BIOETL_STRICT_ERROR_HANDLING`, `BIOETL_ARCHIVE_ROOT`.
   - Добавить новую таблицу `Pipeline Configuration` со свойствами из класса `PipelineSettings`, такими как `BIOETL_PIPELINE__BATCH_SIZE`, `BIOETL_PIPELINE__CHECKPOINT_INTERVAL`, флаги `ControlPlaneSettings` и т.д.
   - Добавить секцию `Silver Resilience & Retry Policies` с политиками повторных попыток (`BIOETL_PIPELINE__SILVER_METADATA_ATOMIC_RETRY__*`, `BIOETL_PIPELINE__SILVER_MERGE_RETRY__*`, `BIOETL_PIPELINE__SILVER_MERGE_TIMEOUT__*`).
   - Добавить `BIOETL_DEFAULT_EMAIL` в секцию `PubMed`.
   - Добавить `BIOETL_METRICS_ENABLED` и `BIOETL_OBSERVABILITY__METRICS_ENABLED` в секцию `Observability`.
   - Эти изменения уже частично подготовлены и будут применены, чтобы документация точно соответствовала текущему коду (структуре `PydanticBaseSettings`).

2. **Запуск тестов и pre-commit**
   - Выполнить проверку `pytest` (при необходимости для тестов документации) и все pre-commit проверки, требуемые по инструкции `pre_commit_instructions`, чтобы обеспечить правильное тестирование, верификацию, обзор и рефлексию.

3. **Отправка изменений (submit)**
   - Открыть pull request с изменениями в документации на ветке `docs/update-env-vars-reference`.
