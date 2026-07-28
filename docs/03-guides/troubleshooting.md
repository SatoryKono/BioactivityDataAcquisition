______________________________________________________________________

Version: 1.1.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-07-28'

______________________________________________________________________

# Руководство по устранению неполадок

В этом руководстве описаны решения частых проблем при разработке и запуске пайплайнов.

> **Расширенный каталог паттернов:** [Common Error Patterns](../05-operations/troubleshooting/common-errors.md) (#6547) — import/type/DQ/HTTP/pipeline/performance templates.

## Локальный режим и файловое хранилище

### Напоминание: Redis/MinIO не используются в текущем режиме

- **Контекст**: Проект работает в локальном режиме (local-only) по дизайну и не использует Redis или MinIO.
- **Ссылка**: См. [ADR-010: Local-Only Deployment](../02-architecture/decisions/ADR-010-local-only-deployment.md).

### Ошибка: `FileNotFoundError` или отсутствуют локальные пути данных

- **Симптом**: Пайплайн падает при чтении или записи локальных файлов.
- **Причина**: Ожидаемая структура директорий в `data/` отсутствует или настроена неверно.
- **Решение**:
  1. Сверьте локальную структуру хранения в [Local Storage Layout](local-storage-layout.md).
  1. Убедитесь, что базовая директория `data/` и подкаталоги `data/output/` существуют и доступны для записи.
  1. Перезапустите пайплайн, чтобы он создал отсутствующие папки, если это требуется.

## Запуск пайплайнов

### Ошибка: `PipelineNotFoundError: No pipeline named '...'`

- **Симптом**: CLI сообщает об отсутствии пайплайна.
- **Причина**: Имя, переданное в `--pipeline`, не совпадает ни с одним файлом в `configs/entities/`.
- **Решение**:
  1. Выведите список доступных пайплайнов: `bioetl config list-pipelines` или `bioetl run-all --list-only`.
  1. Проверьте корректность имени пайплайна.
  1. Убедитесь, что соответствующий YAML-файл существует в `configs/entities/`.

### Ошибка: `LockNotAcquiredError`

- **Симптом**: Пайплайн не стартует из-за невозможности захватить блокировку.
- **Причина**: Уже запущен другой экземпляр того же пайплайна или предыдущий запуск завершился аварийно.
- **Решение**:
  1. Проверьте наличие других процессов того же пайплайна.
  1. Если процесс завис, завершите именно его на уровне ОС и затем перезапустите пайплайн.
  1. При необходимости используйте `bioetl lock check --pipeline ... --run-id ...` только как локальную диагностику текущего процесса.
  1. В Local-Only режиме блокировки находятся в `MemoryLock`, поэтому `bioetl lock release` не является cross-process механизмом снятия чужого lock.

### Ошибка: `pydantic.ValidationError`

- **Симптом**: Пайплайн падает на стадии `transform` или `load` с ошибкой валидации Pydantic.
- **Причина**: Данные из источника изменились и больше не соответствуют модели в `src/bioetl/domain/`.
- **Решение**:
  1. Изучите сообщение об ошибке и определите проблемное поле.
  1. Проверьте сырые данные в локальном Bronze-слое по пути `data/output/bronze/{provider}/{entity}/{date}/` (см. `data/` и [Local Storage Layout](local-storage-layout.md)).
  1. Обновите Pydantic-модель в `src/bioetl/domain/` (например, сделайте поле опциональным или добавьте новое). Это событие **schema drift** и его нужно задокументировать.

## Качество данных

### Высокая доля записей в карантине

- **Симптом**: В сводке запуска отображается большой процент записей, отправленных в карантин.
- **Причина**: Массово срабатывает некритичное правило качества данных.
- **Решение**:
  1. Просмотрите карантинные записи:
     ```bash
     bioetl quarantine inspect --pipeline your-pipeline-name --limit 20
     ```
  1. Проанализируйте `error-code` и `payload`, чтобы определить первопричину (например, неожиданные `null` или неверные SMILES).
  1. Скорректируйте правила качества данных или логику трансформации в соответствующем адаптере.

### Высокая доля `Silver filter rejects`

- **Симптом**: В сводке запуска или Grafana растёт `Silver filter rejects` / `filtered_out`.
- **Причина**: Silver filters массово исключают записи по одному или нескольким правилам.
- **Решение**:
  1. Проверьте summary в Grafana:
     - `bioetl-overview-v2`
     - `bioetl-runtime`
     - `bioetl-dq-v2`
  1. Получите агрегаты по причинам:
     ```bash
     bioetl quarantine stats --pipeline your-pipeline-name --error-code FILTERED_OUT_SILVER
     bioetl quarantine stats --pipeline your-pipeline-name --error-code FILTERED_OUT_SILVER --group-by reason-code-field
     ```
  1. Посмотрите конкретные записи и точную причину исключения:
     ```bash
     bioetl quarantine inspect --pipeline your-pipeline-name --error-code FILTERED_OUT_SILVER --limit 20
     ```
  1. Ориентируйтесь прежде всего на structured поля `reason_code`, `field`,
     `rule_type`, `operator`, `expected`, `actual`, а не только на текст `Reason`.

## См. также

- [Running Pipelines](running-pipelines.md) — CLI команды и опции
- [Run Lifecycle](run-lifecycle.md) — актуальная последовательность runtime,
  manifest, ledger, storage и quarantine closeout
- [Replay Guide](replay-guide.md) — fail-closed exact replay boundaries и
  required evidence
- [Dashboard Guide](dashboard-guide.md) — shipped Grafana dashboard inventory и
  validation commands
- [DQ Framework](dq-framework.md) — DQ analyzers, checks, contracts и
  quarantine boundaries
- [Getting Started](getting-started.md) — первичная настройка
- [ADR-010: Local-Only Deployment](../02-architecture/decisions/ADR-010-local-only-deployment.md) — режим локального запуска
- [Local Storage Layout](local-storage-layout.md) — структура `data/` и слоёв хранения
- [Project Rules](../00-project/RULES.md) — пороги качества данных и обработка ошибок
