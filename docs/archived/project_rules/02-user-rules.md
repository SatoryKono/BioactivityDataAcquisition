# User Rules

*Синхронизировано с RULES.md v5.10 (2026-01-06)*

Репозиторий: SatoryKono/BioactivityDataAcquisition

## 0. Глобальные инварианты BioETL (обязательно)

Следующие инварианты применяются во всех задачах и правках, без исключений (выдержка из Core Prompt/Core Principles):

- Делайте «готовые действия»: минимальные патчи/команды/чек-листы, пригодные к CI сразу.
- Время — только ISO‑UTC. Публичные контракты не менять молча: оформляйте миграции и фиксируйте в `DEPRECATIONS.md`.
- Детерминизм I/O: стабильный порядок строк/колонок, каноническая сериализация JSON, атомарные записи.
- Validate‑before‑write: любые таблицы валидируются Pandera со строгим порядком колонок; при провале записи нет.
- Структурное логирование через UnifiedLogger; `print()` не использовать.
- Секреты — только из переменных окружения/секрет‑менеджера; никаких хардкодов.
- CLI и конфиги — однозначные контракты; единые флаги.

## Уровни Требований (RFC 2119)

- **MUST**: Абсолютное требование. Нарушение = дефект.
- **SHOULD**: Сильная рекомендация. Отклонение требует обоснования в PR.
- **MAY**: На усмотрение разработчика.

## Назначение

Эти правила описывают, как работать в Cursor с кодом и документацией проекта, сохраняя детерминизм, трассируемость и
соответствие контрактам данных.

## 1. Роль пользователя в Cursor

1.1. Вносить минимальные, атомарные правки. Категории:

- Багфикс без изменения контрактов данных.
- Рефакторинг без изменения публичного API и схем.
- Расширение функциональности с явным изменением версий схем/контрактов.
- Правки документации, синхронизированные с кодом.

1.2. Не «чинить» чужие подсистемы в том же PR. Отдельный PR для каждой подсистемы.

## 2. Общие требования при редактировании

### 2.1. Детерминизм (MUST)

| Требование        | Спецификация                                                   |
|-------------------|----------------------------------------------------------------|
| Время             | Только UTC; только ISO-8601; naive datetime **MUST NOT**       |
| Файловые операции | Атомарные (tmp + rename)                                       |
| Сортировка        | Фиксированная; «естественная»/недетерминированная **MUST NOT** |
| Сериализация      | Каноническая (stable key order, fixed types)                   |

### 2.2. Идентификаторы (MUST)

- Использовать канонические ID: ChEMBL IDs, UniProt accessions, PubChem CIDs, DOI.
- Surrogate ID без явного бизнес-ключа и хэша **MUST NOT**.

### 2.3. Схемы и валидация (MUST)

- Любые изменения столбцов/типов/допустимых значений **MUST** проходить через Pandera-схемы.
- Порядок колонок и допустимые NULL фиксированы. Смена = мажорная версия схемы и миграция.
- Sentinel values (-1, "N/A", 9999) **MUST NOT**.

### 2.4. Логирование и метаданные (MUST)

Структурные JSON-логи с полями:

- `pipeline_version`
- `git_commit`
- `config_hash`
- `run_id`
- `started_at_utc`

Для каждого артефакта — sidecar `meta.yaml` с lineage и QC.

**Log Schema**:
| Поле | Обязательность |
|------|----------------|
| `ts` | MUST |
| `level` | MUST |
| `run_id` | MUST |
| `pipeline` | MUST |
| `stage` | MUST |
| `dataset` | SHOULD |
| `record_count` | SHOULD |

Дополнительно: запрещено использовать `print()` для логирования; только структурные логи через UnifiedLogger.

### 2.5. HTTP/внешние источники (MUST)

- Только через `UnifiedAPIClient` или специализированные клиенты.
- Таймауты, ретраи с backoff, TTL-кэш, circuit breaker.
- Политика 429/5xx: exponential backoff, бюджет попыток, троттлинг.

**Circuit Breaker параметры**:
| Параметр | Значение |
|----------|----------|
| Trigger | 5 consecutive errors |
| Open Duration | 5 минут |
| Recovery | Half-Open → 1 пробный запрос |

### 2.6. Ввод/вывод данных (MUST)

- CSV/Parquet с фиксированным порядком столбцов.
- Нормализованные NA/NULL.
- Финальные файлы неизменяемы.
- Контрольные суммы (BLAKE2), размер, строки, хэш бизнес-ключа — в `meta.yaml` и QC-отчёте.

### 2.7. Medallion Architecture (MUST)

| Уровень | Формат        | Действие                                                                |
|---------|---------------|-------------------------------------------------------------------------|
| Bronze  | JSONL + zstd  | Append-only, path `bronze/{format_version}/{provider}/{entity}/{date}/` |
| Silver  | Delta Lake    | Merge/Upsert. Raw Parquet **MUST NOT**.                                 |
| Gold    | Delta/Parquet | Strict validation. SCD Type 2 или партиции.                             |

### 2.8. Quarantine (MUST)

Битые данные → `common.quarantine`:

- Retention: 30 дней.
- `dq_status`: `NEW` → `IGNORED` / `REPROCESSED`.
- Операции: `make quarantine-inspect/replay/purge`.

### 2.9. Backfill/Replay (MUST)

- Обязательные поля: `_run_id` (UUID), `_run_type` (`incremental` | `backfill` | `rebuild`).
- Merge Priority: `rebuild` > `backfill` > `incremental`.
- Lock для exclusive backfill: `lock:{provider}_{entity}:exclusive`.

### 2.10. Документация (MUST)

- Любое изменение контрактов данных **MUST** сопровождаться синхронной правкой в `docs/` и примеров CLI.
- Breaking changes: лейбл в PR, 14-дневный deprecation period.

#### 2.10.1. Именование файлов документации (MUST)

- Имена — только в нижнем регистре, слова через дефис (kebab‑case), без подчёркиваний.
- Секвенции — двузначный префикс `NN-` (например, `01-overview.md`).
- Для пайплайнов: `NN-<entity>-<provider>-<topic>.md` (напр., `09-activity-chembl-extraction.md`).
- Заголовок H1 должен дублировать имя файла в Title Case.
- Внутренние якоря из `##` — в kebab‑case.

### 2.11. Диаграммы (SHOULD)

Соблюдать `docs/architecture/diagrams/00-diagramming-policy.md`:

- Хранить первичный текстовый формат (Mermaid/PlantUML).
- Один файл — одна диаграмма.
- Обновлять при архитектурных или pipeline-изменениях.

### 2.12. Код-стиль (MUST)

- Форматирование: ruff format (или black с идентичными настройками), длина строки 100, Python 3.10+.
- Импорты: isort (stdlib → third‑party → first‑party), wildcard imports запрещены.
- Типы: публичные API полностью аннотированы; `mypy --strict` без `Any` и `type: ignore`, кроме явно обоснованных
  случаев.
- Пре-коммиты: ruff, black/ruff-format, isort, mypy, pytest, coverage.
- Минимальный порог `pytest --cov=src/bioetl` — 80%.
- Запрещены «магические числа» и глобальное мутабельное состояние; предпочтение композиции над наследованием.

### 2.13. Конкурентность и блокировки (MUST)

> **Note**: Local-Only Deployment (ADR-010). Redis отложен для будущего распределённого развёртывания.

| Параметр      | Значение (Local-Only)    |
|---------------|--------------------------|
| Механизм      | `MemoryLock` (in-process)|
| Max Duration  | 4 часа                   |

**Invariant**: Потеря блокировки = потеря права на запись. Safety Guard **MUST** валидировать lock ownership перед записью.

### 2.14. Рефакторинг модулей (MUST)

Перед рефакторингом модуля X:

```bash
# Импорты
grep -r "from bioetl.domain.X import" src/
grep -r "import bioetl.domain.X" src/

# Использования
grep -r "X\." src/ --include="*.py"

# Тесты
grep -r "X" tests/ --include="*.py"

# Re-exports
grep -r "X" src/bioetl/domain/__init__.py
```

**Требования**:

- Карта зависимостей **MUST** быть составлена до начала.
- Coverage >80% перед рефакторингом.
- Тесты обновляются до изменения реализации.

**Валидация**:

- [ ] `pytest tests/ -v --tb=short`
- [ ] `mypy src/bioetl/ --strict`
- [ ] `python -c "from bioetl.domain import *"`
- [ ] Документация обновлена
- [ ] `__init__.py` exports актуальны
- [ ] Deprecation warnings добавлены
- [ ] `CHANGELOG.md` обновлён
- [ ] PR description содержит breaking changes

## 3. Чего делать нельзя (MUST NOT)

| Запрет                                     | Обоснование                         |
|--------------------------------------------|-------------------------------------|
| Менять порядок столбцов «по красоте»       | Нарушает детерминизм                |
| Подменять идентификаторы эвристиками       | Без явного правила нормализации     |
| Ad-hoc HTTP-вызовы, обходя клиенты         | Нет retry, circuit breaker          |
| Локальная таймзона/нестабильные timestamp  | Нарушает детерминизм                |
| Загрузка без контрольных сумм и sidecar    | Нет lineage                         |
| Коммитить секреты/ключи, выводить в логах  | Security violation                  |
| Рефакторить без карты зависимостей         | Высокий риск регрессии              |
| Sentinel values (-1, "N/A")                | Используйте NULL                    |
| Raw Parquet в Silver                       | Используйте Delta Lake              |
| Использовать `print()` для логирования     | Нарушает политику структурных логов |

## 4. Disaster Recovery (SHOULD)

| Параметр | Значение |
|----------|----------|
| RPO      | 24 часа  |
| RTO      | 4 часа   |

**DR Scenarios**:
| Сценарий | Действие |
|----------|----------|
| Повреждение Bronze/Silver | Stop → S3 Point-in-Time Restore → `--full-rebuild` |
| Потеря чекпоинта | `--ignore-checkpoint` |
| Отказ региона | DNS Failover → Terraform в резервном регионе |

## 5. Шаблон PR-чеклиста

- [ ] Изменены только необходимые файлы; атомарность соблюдена.
- [ ] Схемы Pandera обновлены; версия/column-order/nullable отражены.
- [ ] Обновлены `docs/` и примеры CLI.
- [ ] Пройдены: ruff, black, isort, mypy-strict, pytest (+golden-files), pandera-validation.
- [ ] Добавлены/обновлены QC-отчёты и `meta.yaml` с lineage.
- [ ] Все внешние вызовы через унифицированные клиенты; retry/circuit breaker настроены.
- [ ] Breaking changes: лейбл `breaking-change`, 14-дневный deprecation period.
- [ ] Log Schema соблюдена (run_id, pipeline, stage).
- [ ] Sentinel values не используются.
- [ ] Документация следует правилам именования (kebab‑case, `NN-` префикс, H1=имя файла).
- [ ] Отсутствуют вызовы `print()`; используется UnifiedLogger для структурных логов.
