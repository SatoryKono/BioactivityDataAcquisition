# Возобновляемая загрузка без повторной подгрузки и последующим объединением результатов

## Цель

Реализовать режим, в котором при повторном запуске pipeline:

1. система **не подгружает уже обработанные записи** из источника;
1. результат нового запуска **объединяется** с уже загруженными данными без потери истории и без дублей;
1. поведение соответствует Hexagonal Architecture и правилам Medallion (Silver = Delta merge/upsert).

## Кратко о проблеме текущей реализации

Сейчас `CheckpointManager` хранит только `records_processed` (offset-подобный подход). Это работает для источников со стабильной пагинацией, но не покрывает кейс, когда:

- порядок страниц меняется между запросами,
- нужен безопасный resume на уровне бизнес-ключей/курсора,
- требуется объединить частичный run + догрузку без дублирования.

## Предлагаемые модификации

## 1) Добавить стратегию загрузки `cursor_resume`

### Что изменить

- `src/bioetl/domain/medallion.py`

  - расширить `LoadingStrategy`:
    - `FULL_SCAN_ONLY = "full_scan_only"`
    - `CURSOR_RESUME = "cursor_resume"`
  - скорректировать `allows_checkpoint_resume`:
    - `full_scan_only` → `False`
    - `cursor_resume` → `True`

- `src/bioetl/infrastructure/schemas/pipeline_config.py`

  - расширить `Literal` для `loading_strategy` значением `"cursor_resume"`.

### Зачем

`cursor_resume` — явный контракт, что источник должен поддерживать детерминированное продолжение через checkpoint-token, а не только через offset.

## 2) Ввести курсорный checkpoint-контракт в порт данных

### Что изменить

- `src/bioetl/domain/ports/data_source.py`

  - добавить опциональный аргумент `checkpoint_token: str | None = None` в `fetch(...)`.
  - сохранить `offset` для backward compatibility.

- `src/bioetl/application/core/checkpoint_manager.py`

  - сохранять/загружать расширенный metadata:
    - `records_processed` (legacy)
    - `checkpoint_token` (новый режим)
    - `resume_mode` (`offset` / `cursor`)

- `src/bioetl/application/core/batch_executor.py`

  - во время extraction-loop обновлять checkpoint не только по счетчику,
    но и по последнему подтвержденному `checkpoint_token`.

### Зачем

Для resume без повторной подгрузки нужно состояние «где остановились» именно в терминах источника (cursor/next token), а не количества записей.

## 3) Протокол объединения двух запусков

### Что изменить

- `src/bioetl/application/core/runner.py`

  - при `resume=True` и наличии checkpoint:
    - запускать fetch c `checkpoint_token` (при `cursor_resume`);
    - fallback на `offset` для старых pipeline.

- Silver слой (существующий `merge` режим) использовать как конечный этап объединения:

  - ключ: `technical_primary_key` (`entity_id`)
  - защита от дублей: `content_hash`
  - обновление/история по действующей политике SCD/merge.

### Зачем

Это дает «два запуска = один консистентный результат»:

- run-1 загрузил часть;
- run-2 продолжил с курсора;
- Silver merge объединяет данные без дублирования.

## 4) Совместимость и миграция

- Для pipeline без `loading_strategy` поведение не меняется.
- Для `full_scan_only` resume по-прежнему заблокирован.
- `cursor_resume` включать только для адаптеров, где API поддерживает токены продолжения.

## 5) План внедрения по шагам

1. **Domain/API контракты**: enum + schema + DataSourcePort.
1. **Application**: checkpoint metadata v2 (`checkpoint_token`, `resume_mode`).
1. **Infrastructure adapters**: реализация token-based fetch для конкретных провайдеров.
1. **Tests**:
   - unit: `LoadingStrategy`, `CheckpointManager`, `BatchExecutor`;
   - integration: сценарий «run-1 прерван → run-2 resume → merge без дублей».

## 6) Минимальные acceptance-критерии

- При resume с `cursor_resume` первый запрос второго запуска начинается с checkpoint token, а не с начала данных.
- Количество записей в Bronze после двух запусков растет только за счет действительно новых записей.
- В Silver отсутствуют дубли по `(entity_id, content_hash)`.
- Архитектурные тесты по границам слоев остаются зелеными.

## 7) Риски

- Не все провайдеры отдают стабильный cursor/token.
- Для отдельных API может потребоваться гибрид: cursor + защитный dedup по content_hash.
- Нужна явная маркировка в конфиге pipeline, какие источники действительно поддерживают `cursor_resume`.
