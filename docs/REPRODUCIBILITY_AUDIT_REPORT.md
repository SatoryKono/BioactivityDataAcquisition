# Reproducibility Audit Report - BioETL

## Executive Summary

Аудит воспроизводимости пайплайнов в проекте BioETL выявил, что система имеет прочную архитектурную основу для воспроизводимости, но есть критические пробелы в реализации, которые не позволяют гарантировать строгую детерминированность и идемпотентность. Текущая реализация обеспечивает хороший уровень control-plane воспроизводимости через RunManifest и execution_fingerprint, но есть проблемы с runtime-детерминизмом и полнотой lineage metadata.

## Фактическая модель воспроизводимости в текущем main

### Реализованные механизмы:
1. **RunManifest** (`src/bioetl/domain/control_plane/run_manifest.py`)
   - Полноценная реализация с execution_fingerprint
   - Code provenance (git_commit, config_hash, contract_ref/version)
   - Source refs и planned artifacts

2. **Checkpoint система** (`src/bioetl/application/composite/checkpoint/`)
   - Сохранение состояния с manifest_id, effective_config_hash, contract_ref/version
   - Механизм resume с валидацией совместимости
   - Atomic сохранение/удаление чекпоинтов

3. **Content hashing** (`src/bioetl/domain/constants.py`)
   - Исключение META_FIELDS из хэширования
   - Стабильная сериализация перед хэшированием

4. **Lineage система** (`src/bioetl/domain/lineage/`)
   - Полноценная модель графа lineage
   - Поддержка всех типов узлов (SOURCE_SYSTEM, BRONZE_BATCH, etc.)
   - Возможность трассировки между run/manifest/artifact

### Проблемные области:

1. **Нарушения детерминизма**:
   - Использование `datetime.now()` в application слое
   - Нестабильный порядок обработки в некоторых трансформерах
   - Отсутствие фиксации seed для случайных операций

2. **Проблемы идемпотентности**:
   - Неполная реализация merge semantics
   - Отсутствие валидации content_hash при повторных записях
   - Частичная поддержка replay vs rebuild

3. **Проблемы control-plane**:
   - Расхождение между manifest_id и checkpoint identity
   - Неполная валидация при resume (отсутствие проверки git_commit)
   - Нет строгой привязки run_id ↔ manifest_id ↔ artifacts

4. **Проблемы lineage**:
   - Не все metadata пишутся в sidecar файлы
   - Отсутствие некоторых полей в реальных артефактах
   - Неполная трассировка для composite pipelines

## Что уже реализовано хорошо

1. **Control-plane архитектура**:
   - Четкое разделение RunManifest и runtime context
   - Полноценная модель execution_fingerprint
   - Хорошая поддержка code provenance

2. **Checkpoint механизм**:
   - Atomic операции сохранения
   - Валидация совместимости при resume
   - Поддержка composite_run_identity

3. **Content integrity**:
   - Корректное исключение meta-полей из хэширования
   - Стабильная сериализация для хэшей
   - Поддержка content_hash в основных сущностях

## Основные проблемы

### Критические (P0)
1. **Нарушение детерминизма в application слое**
   - `src/bioetl/application/composite/runner_pkg/runner_observability_mixin.py:65` - использование `datetime.now()`
   - `src/bioetl/application/core/batch_executor.py` - нестабильная сортировка

2. **Неполная валидация при checkpoint resume**
   - Отсутствует проверка git_commit совместимости
   - Нет валидации полного execution_fingerprint
   - Файл: `src/bioetl/application/services/checkpoint_compatibility_service.py`

3. **Расхождение идентичностей**
   - manifest_id не всегда совпадает с checkpoint identity
   - Нет строгой привязки между сущностями

### Системные (P1)
1. **Неполная идемпотентность merge операций**
   - Отсутствует валидация content_hash при merge
   - Частичная реализация upsert semantics
   - Файл: `src/bioetl/application/composite/conflict_resolver.py`

2. **Неполная lineage metadata**
   - Не все поля пишутся в sidecar файлы
   - Отсутствие трассировки для некоторых операций
   - Файлы: `src/bioetl/application/core/batch_writer_io_mixin.py`

3. **Недостаточная изоляция runtime state**
   - Не все runtime параметры фиксируются в manifest
   - Отсутствует валидация окружения при replay

### Улучшения (P2)
1. **Расширенная валидация replay**
   - Добавить проверку полного execution context
   - Улучшить детектирование drift между runs

2. **Полная трассировка composite pipelines**
   - Добавить missing lineage edges
   - Улучшить sidecar metadata

## Матрица рисков

| Риск                          | Вероятность | Влияние | Приоритет |
|-------------------------------|-------------|---------|-----------|
| Нарушение детерминизма        | Высокая     | Критическое | P0        |
| Неполная идемпотентность      | Средняя     | Высокое    | P1        |
| Расхождение идентичностей     | Высокая     | Высокое    | P0        |
| Неполная lineage              | Средняя     | Среднее    | P1        |
| Недостаточная replay валидация| Низкая      | Среднее    | P2        |

## Количественная оценка

| Категория               | Оценка (0-10) | Обоснование |
|-------------------------|---------------|-------------|
| Determinism             | 6             | Есть нарушения в application слое |
| Idempotency             | 7             | Хорошая основа, но неполная реализация |
| Run Identity            | 8             | Полноценная модель, но есть расхождения |
| Checkpoint Safety       | 9             | Хорошая реализация с валидацией |
| Lineage Completeness    | 6             | Не все metadata пишутся |
| Replay Readiness        | 7             | Возможность есть, но неполная валидация |
| Layer Consistency       | 8             | Хорошее разделение ответственности |

**Интегральная оценка воспроизводимости: 7/10**

## План исправлений

### P0 (Блокеры)
1. **Исправить нарушения детерминизма**
   - Проблема: Использование `datetime.now()` в application слое нарушает детерминизм
   - Влияние: Одинаковый вход может дать разный выход
   - Файлы: `src/bioetl/application/composite/runner_pkg/runner_observability_mixin.py`
   - Фикс: Заменить на инжектируемый timestamp из context
   - DoD: Все timestamp зависят только от run context

2. **Добавить полную валидацию checkpoint compatibility**
   - Проблема: Отсутствует проверка git_commit и полного execution_fingerprint
   - Влияние: Возможен resume с несовместимой версией кода
   - Файлы: `src/bioetl/application/services/checkpoint_compatibility_service.py`
   - Фикс: Добавить валидацию всех runtime anchors
   - DoD: Checkpoint resume валидирует полный execution context

### P1 (Системные улучшения)
1. **Улучшить идемпотентность merge операций**
   - Проблема: Отсутствует валидация content_hash при merge
   - Влияние: Возможны дубликаты при повторном запуске
   - Файлы: `src/bioetl/application/composite/conflict_resolver.py`
   - Фикс: Добавить проверку content_hash перед merge
   - DoD: Повторный запуск не создает дубликаты

2. **Добиться полной lineage metadata**
   - Проблема: Не все поля пишутся в sidecar файлы
   - Влияние: Неполная трассировка для forensic analysis
   - Файлы: `src/bioetl/application/core/batch_writer_io_mixin.py`
   - Фикс: Добавить missing metadata в sidecar
   - DoD: Все lineage поля доступны для реконструкции

3. **Улучшить валидацию replay**
   - Проблема: Недостаточная валидация execution context
   - Влияние: Возможен drift между оригинальным и replay запуском
   - Файлы: `src/bioetl/application/services/run_manifest_service.py`
   - Фикс: Добавить полную валидацию execution_fingerprint
   - DoD: Replay детектирует любые изменения контекста

### P2 (Улучшения)
1. **Расширить трассировку composite pipelines**
   - Проблема: Отсутствуют некоторые lineage edges
   - Влияние: Неполная картина зависимостей
   - Файлы: `src/bioetl/application/composite/merger_post_join.py`
   - Фикс: Добавить missing lineage edges
   - DoD: Полная трассировка всех зависимостей

2. **Улучшить UX для forensic analysis**
   - Проблема: Сложно отличать exact replay от нового запуска
   - Влияние: Сложный forensic analysis
   - Файлы: `src/bioetl/interfaces/cli/commands/debug.py`
   - Фикс: Добавить команды для сравнения runs
   - DoD: Легко детектировать различия между запусками

## Ответ на ключевой вопрос

**Можно ли по текущему состоянию проекта воспроизвести любой pipeline run как строго определённый вычислительный акт?**

**Частично.** Текущая реализация обеспечивает хороший уровень control-plane воспроизводимости через RunManifest и execution_fingerprint, но есть критические пробелы:

1. **Нарушения детерминизма** в application слое (использование `datetime.now()`) не позволяют гарантировать одинаковый результат при одинаковом входе.

2. **Неполная идемпотентность** merge операций означает, что повторный запуск может создать дубликаты.

3. **Расхождение идентичностей** между manifest_id и checkpoint identity осложняет точную реконструкцию.

Для достижения строгой воспроизводимости необходимо:
- Исправить нарушения детерминизма (P0)
- Добиться полной идемпотентности (P1)
- Устранить расхождения идентичностей (P0)
- Добиться полной lineage metadata (P1)

После исправления этих проблем проект сможет гарантировать exact reproducibility.