# Предложение: возобновление загрузки без повторной подгрузки уже обработанных данных

## Цель

Реализовать `resume` так, чтобы при перезапуске пайплайна:

1. **не запрашивать повторно** уже обработанные страницы/батчи из источника;
1. **не дублировать** данные в Silver;
1. **объединять** результаты нескольких запусков в одну консистентную выборку.

## Проблема текущей реализации

Сейчас `resume` в `PipelineRunner` использует только `records_processed` как `offset`. Это недостаточно надёжно:

- источники с нестабильной пагинацией могут отдавать сдвинутые окна;
- повторный запуск может повторно получить часть ранее обработанных записей;
- checkpoint не хранит информацию о фактически подтверждённых батчах.

## Архитектурно корректный подход (Hexagonal + Medallion)

Нужно разделить задачу на два независимых механизма:

1. **Source resume token** (уровень извлечения):

   - хранить в checkpoint не только `records_processed`, но и `cursor/page_token/last_entity_id`;
   - при `resume` начинать чтение с подтверждённого токена.

1. **Idempotent merge** (уровень Silver):

   - продолжать merge/upsert по `entity_id + content_hash`;
   - при повторном поступлении того же контента запись не должна дублироваться.

Такой split соответствует Medallion: Bronze отвечает за факт получения, Silver — за консолидацию/дедупликацию.

## Предлагаемые изменения по коду

### 1) Расширить checkpoint metadata

**Файл:** `src/bioetl/application/core/checkpoint_manager.py`

Добавить в checkpoint структуру (пример):

```python
metadata = {
    "records_processed": records_processed,
    "source_resume_token": source_resume_token,
    "last_successful_batch": last_successful_batch,
    "watermark": watermark,
}
```

Где:

- `source_resume_token`: курсор API (или `None`);
- `last_successful_batch`: монотонный номер подтверждённого батча;
- `watermark`: provider-специфичный маркер (дата/ID).

### 2) Ввести типизированное состояние resume

**Новые доменные типы (предложение):**

- `src/bioetl/domain/dto/resume_state.py`

```python
@dataclass(frozen=True)
class ResumeState:
    records_processed: int
    source_resume_token: str | None
    last_successful_batch: int
    watermark: str | None
```

Checkpoint manager должен читать/писать `ResumeState`, а не «сырой dict».

### 3) Передавать resume token в extract слой

**Файлы:**

- `src/bioetl/application/core/runner.py`
- `src/bioetl/application/core/batch_executor.py` (или соответствующий executor)
- provider extractors в `src/bioetl/application/pipelines/*`

Изменение контракта выполнения:

- вместо одного `offset` передавать `resume_state`;
- extractors должны уметь стартовать с `source_resume_token`.

Для провайдеров без курсора сохранять fallback на offset/watermark.

### 4) Checkpoint только после подтверждённой записи в Silver

Семантика save checkpoint:

1. batch fetched;
1. batch transformed;
1. batch merged into Silver;
1. **только после (3)** сохранить новый `ResumeState`.

Это исключает «ложный прогресс», когда checkpoint ушёл вперёд фактической фиксации данных.

### 5) Явный режим merge результатов запусков

**Runtime/CLI (предложение):**

- добавить флаг `--merge-runs` (по умолчанию `true` для incremental);
- при `merge-runs=true` запрещать destructive очистки Silver в pre-run фазе.

Поведение:

- Run A записал N батчей и остановился;
- Run B с `--resume` дочитывает оставшееся;
- Silver содержит объединённый результат A+B без дублей.

### 6) Защита от дублей в рамках одного recovery-окна

Добавить в executor краткоживущий in-memory фильтр на `content_hash` внутри run (не в domain):

- снижает нагрузку на Silver merge при повторной доставке одного и того же окна;
- не заменяет Delta merge, а дополняет его.

## Изменения тестов

### Unit

1. `tests/unit/application/core/test_checkpoint_manager.py`

   - чтение/запись расширенного `ResumeState`;
   - backward compatibility для старых checkpoint (только `records_processed`).

1. `tests/unit/application/core/test_runner_resume.py`

   - проверка передачи `resume_state` в executor;
   - проверка, что checkpoint сохраняется после успешного merge.

### Integration

1. `tests/integration/.../test_resume_no_refetch.py`

   - симулировать аварийное завершение после части батчей;
   - второй запуск должен стартовать с `source_resume_token`, а не с нуля.

1. `tests/integration/infrastructure/storage/test_silver_writer.py`

   - merge A+B: итог без дублей по `content_hash`.

## Совместимость и миграция

1. Старые checkpoint (без новых полей) читать как:
   - `source_resume_token=None`
   - `last_successful_batch=0`
   - `watermark=None`
1. Новый формат сохранять сразу после следующего успешного батча.
1. Для `full_scan_only` оставить текущий запрет resume (как и сейчас).

## Наблюдаемость

Добавить поля в structured logs:

- `resume_mode`
- `source_resume_token`
- `last_successful_batch`
- `merge_runs`

Минимальные метрики:

- `resume_refetched_records_total`
- `resume_skipped_records_total`
- `resume_merged_records_total`

## Критерии готовности

1. Перезапуск после падения не инициирует повторную загрузку уже подтверждённых батчей.
1. Итог Silver после двух запусков эквивалентен одному успешному запуску.
1. Архитектурные тесты слоёв проходят без нарушений.
1. `mypy --strict` и целевые unit/integration тесты проходят.
