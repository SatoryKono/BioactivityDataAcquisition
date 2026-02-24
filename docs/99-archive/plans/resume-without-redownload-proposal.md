# Proposal: Возобновление загрузки без повторной подгрузки уже загруженных данных

Date: 2026-02-24
Status: Proposed
Scope: `application/core`, `domain/medallion`, `domain/ports`, `infrastructure/checkpoint`, `interfaces/cli`

## 1) Наблюдения по текущей реализации

1. Сейчас offset для resume берётся из checkpoint metadata (`records_processed`) и передаётся в extraction loop как стартовый offset. Это подходит только для источников со стабильной offset-пагинацией.
1. В `LoadingStrategy` есть только `FULL_SCAN_ONLY`; при нём resume жёстко блокируется и рассчитывает на дедуп в Silver по `content_hash`.
1. В checkpoint не хранится курсор источника и high-water mark, только агрегированный прогресс (`records_processed`).

Следствие: для источников с нестабильной pagination/ordering (например, публикации) «resume без повторной подгрузки» работает неоптимально — приходится делать full scan + dedup.

## 2) Цель модификации

Реализовать режим **stateful resume**:

- продолжать загрузку строго с последней подтверждённой позиции источника;
- не перечитывать уже успешно выгруженные страницы/записи;
- объединять результаты двух (и более) запусков через Silver merge/upsert на `entity_id` + `content_hash`.

## 3) Предлагаемые изменения (архитектурно)

### 3.1 Domain: расширить стратегию загрузки

Добавить вторую стратегию:

- `CHECKPOINT_RESUME` — разрешает возобновление по checkpoint state.

Семантика:

- `FULL_SCAN_ONLY`: как сейчас (resume blocked, dedup only).
- `CHECKPOINT_RESUME`: resume через курсор/offset/high-water-mark.

### 3.2 Domain Port: типизированное состояние checkpoint

Вместо «свободного metadata dict» добавить модель состояния:

```python
@dataclass(frozen=True, slots=True)
class CheckpointState:
    source_cursor: str | None
    source_offset: int | None
    high_watermark: str | None
    records_processed: int
    last_entity_id: str | None
```

Порт:

- `save(..., state: CheckpointState, metadata: dict[str, Any])`
- `load(...) -> tuple[RunID, CheckpointState, dict[str, Any]] | None`

Это убирает неоднозначность `records_processed` как «псевдо-offset».

### 3.3 Application: безопасная фиксация прогресса

В extraction loop фиксировать checkpoint только **после** успешной записи batch в Bronze+Silver+Gold.

Минимальные поля фиксации:

- текущий offset/cursor из data source;
- high-water mark (например, `updated_at <= watermark` для текущего запуска);
- `records_processed`.

На resume:

- если `source_cursor` доступен — продолжать по нему;
- иначе fallback на `source_offset`;
- если стратегия `FULL_SCAN_ONLY` — текущее поведение без resume.

### 3.4 DataSourcePort: поддержка курсора

Расширить контракт чтения:

- вход: `offset`, `cursor`, `high_watermark`;
- выход: записи + `next_cursor` (или через callback/side channel).

Для провайдеров:

- offset-only API: использовать `source_offset`;
- cursor API: использовать `source_cursor`;
- mixed API: приоритет cursor.

### 3.5 Silver merge: объединение результатов двух загрузок

Оставить текущую политику merge/upsert, но формализовать ключи:

- business key: `entity_id`
- version key: `content_hash`
- технические: `_run_id`, `_ingestion_ts` не входят в hash.

Результат:

- данные из run#1 и run#2 консолидируются без дублей;
- новые версии сущности пишутся как новые версии (SCD2/merge-политика слоя).

### 3.6 CLI/Runtime

Расширить `--resume`:

- `--resume` (как флаг);
- `--resume-mode=offset|cursor|auto` (default: `auto`).

`auto`:

- берёт cursor, если поддерживается провайдером;
- иначе offset.

## 4) Совместимость и миграция

1. Поддержать checkpoint schema `v2` (legacy) и `v3` (stateful).
1. Миграция при чтении:
   - если найден `v2`, маппить `records_processed -> source_offset` только для offset-friendly pipeline;
   - для `FULL_SCAN_ONLY` игнорировать resume-state.
1. После первого успешного сохранения писать только `v3`.

## 5) План внедрения (итеративно)

1. **RF-001**: добавить `LoadingStrategy.CHECKPOINT_RESUME` + unit tests.
1. **RF-002**: ввести `CheckpointState` и обновить `CheckpointPort`/`LocalCheckpoint`.
1. **RF-003**: адаптировать `CheckpointManager` и `Runner` под новый state.
1. **RF-004**: расширить `DataSourcePort` и адаптеры (по приоритету: ChEMBL/PubMed/OpenAlex).
1. **RF-005**: e2e тест «прерванный запуск + resume» без повторного чтения страниц.
1. **RF-006**: обновить runbook по checkpoint debugging.

## 6) Критерии приёмки

- Resume продолжает с последней подтверждённой страницы/курсора.
- Повторный запуск не делает re-fetch уже обработанных страниц.
- Silver после двух запусков не содержит дубликатов по `entity_id + content_hash`.
- Архитектурные тесты слоёв и `mypy --strict` проходят.

## 7) Риски

- Провайдеры с нестабильным ordering даже при offset могут пропускать/дублировать записи. Для них обязателен cursor+watermark или `FULL_SCAN_ONLY`.
- Ошибка времени фиксации checkpoint может привести к «at-least-once» чтению. Поэтому checkpoint должен сохраняться только после успешного commit batch.

## 8) Минимальный тестовый набор

- Unit:
  - migration v2->v3 checkpoint;
  - CheckpointManager resume selection (`cursor/offset/none`).
- Integration:
  - interrupted run на mock source с 3 страницами;
  - resume стартует со страницы 2, не читая страницу 1.
- E2E:
  - два последовательных запуска одного pipeline → корректный merge в Silver без дублей.
