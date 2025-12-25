# План Рефакторинга BioETL

*Версия: 5.4 | Дата: Февраль 2026*

---

## Обзор

Этот документ описывает план рефакторинга с фокусом на **детерминизм**, **Medallion-инварианты** и **чистоту архитектуры**. План актуализирован на основе аудита архитектуры (Feb 2026).

### Приоритеты

| Уровень | Фаза | Цель | Статус |
|---------|------|------|--------|
| 🔴 **Критично** | Фаза 1 | Детерминизм ретраев и Single Source of Time | 🟡 In Progress |
| 🟠 **Высокий** | Фаза 2 | Укрепление Medallion-инвариантов | 🟡 In Progress |
| 🟡 **Средний** | Фаза 3 | Чистота Архитектуры (RecordProcessor, HTTP) | ⚪ Planned |
| 🟢 **Желательно** | Фаза 4 | Документация и Автоматизация | ⚪ Planned |

---

## Фаза 1: Детерминизм и Single Source of Time 🔴

### Цель
Обеспечить полную воспроизводимость пайплайнов за счет устранения `random` и `datetime.now()` из инфраструктурного слоя.

| Задача | Статус | Описание |
|--------|--------|----------|
| **D1: HTTP jitter** | 🟡 Partial | Добавить `deterministic=True` в `RetryConfig` (client.py). Текущая реализация использует `random.uniform` по умолчанию. |
| **D2: Gold writer random** | 🔴 TODO | Заменить `random.uniform` на фиксированный backoff или детерминированный jitter в `GoldWriter`. |
| **T1: PipelineContext** | ✅ DONE | `started_at` добавлен в `PipelineContext`. |
| **T2: RecordProcessor** | 🔴 TODO | Настроить передачу `started_at` из `RecordProcessor` в writer'ы (сейчас используется `datetime.now` внутри writers). |
| **T3: BronzeWriter** | ✅ DONE | `BronzeWriter` принимает `ingestion_ts` (но требует проверки использования). |
| **T4: Infrastructure Cleanup** | 🔴 TODO | Устранить `datetime.now()` в `UnifiedQuarantine`, `LineageService`, `AnomalyDetector`. |
| **T5: Arch Test** | 🔴 TODO | Создать тест `test_determinism.py` для контроля использования `datetime.now()` в infra. |

### D1: Детерминистичный джиттер в HTTP-клиенте (Детали)
**Файл:** `src/bioetl/infrastructure/adapters/http/client.py`
- [ ] Добавить поле `deterministic: bool` в `RetryConfig`.
- [ ] Реализовать Hash-based jitter: `hash(f"{attempt}:{url}:{seed}")`.

### T4: Устранение datetime.now() в Infra (Детали)
**Файлы:**
- `src/bioetl/infrastructure/quarantine/unified.py`
- `src/bioetl/infrastructure/observability/lineage.py`
- `src/bioetl/infrastructure/observability/anomaly/*.py`
- `src/bioetl/infrastructure/adapters/chembl/client.py`
- `src/bioetl/infrastructure/storage/gold_writer.py`

**Действие:**
- Изменить сигнатуры методов, чтобы принимать `timestamp: datetime`.
- Передавать `context.started_at` сверху вниз.

---

## Фаза 2: Укрепление Medallion-Инвариантов 🟠

### Цель
Строгое соблюдение правил записи и эволюции схем в Silver/Gold слоях.

| Задача | Статус | Описание |
|--------|--------|----------|
| **M1: Silver Write Mode** | ✅ DONE | `SilverWriteMode` Enum внедрен и валидируется. |
| **M2: Gold Write Mode** | ✅ DONE | `GoldWriteMode` Enum внедрен и валидируется. |
| **M4: Schema Drift** | 🔴 TODO | Реализовать параметр `on_schema_mismatch` ("error" | "evolve" | "ignore") в `DeltaWriter`. Сейчас drift не обрабатывается явно. |

### M4: Schema Drift Handling (Детали)
**Файл:** `src/bioetl/infrastructure/storage/delta_writer.py`
- [ ] Добавить аргумент `on_schema_mismatch` в `write_silver`.
- [ ] Реализовать логику сравнения схем (incoming vs existing).
- [ ] Реализовать `evolve` (merge schema) и `error` (raise `SchemaEvolutionError`).

---

## Фаза 3: Чистота Архитектуры 🟡

### Цель
Разгрузить "God Objects" и унифицировать дублирующуюся логику.

| Задача | Статус | Описание |
|--------|--------|----------|
| **R1: RecordProcessor** | 🔴 TODO | Декомпозировать `RecordProcessor`. Вынести логику записи слоев в `BronzeLayerHandler`, `SilverLayerHandler`, `GoldLayerHandler`. |
| **R2: HTTP Clients** | 🔴 TODO | Унифицировать клиенты (ChEMBL, UniProt, etc.) в `UnifiedHTTPClient`, убрав дублирование логики `fetch`. |
| **R3: Config Mappers** | 🔴 TODO | Консолидировать логику маппинга YAML -> Domain Config (сейчас размазана по билдерам и мапперам). |

### R1: Декомпозиция RecordProcessor (Детали)
**Файл:** `src/bioetl/application/core/record_processor.py`
- [ ] Создать `src/bioetl/application/core/handlers/`.
- [ ] Вынести `_write_bronze_batch`, `_write_silver_batch`, `_write_gold_batch` в соответствующие Handler-классы.
- [ ] Внедрить Handler'ы в `RecordProcessor` через конструктор.

---

## Фаза 4: Документация и Автоматизация 🟢

| Задача | Статус | Описание |
|--------|--------|----------|
| **A1: RULES.md** | 🔴 TODO | Обновить раздел "Determinism" (§6.1). |
| **A2: ADR-014** | 🔴 TODO | Добавить ADR "Deterministic Writes & Time Source". |
| **A3: CI Checks** | 🔴 TODO | Включить `make arch-test` в CI пайплайн. |

---

## Критерии Приемки (Definition of Done)

1. **Архитектурные тесты проходят без исключений** (пустой whitelist в `test_determinism.py`).
2. **Все Writer'ы детерминированы** (нет `random`, нет неявного `datetime.now`).
3. **RecordProcessor < 150 строк кода.**
4. **Schema Drift обрабатывается явно.**

---

*План обновлен: Feb 2026. Следующий шаг: Реализация Фазы 1 (D2, T2, T4, T5).*
