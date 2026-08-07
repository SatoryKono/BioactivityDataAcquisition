# План обновления документации проекта BioETL

**Дата:** 2026-08-05  
**Версия:** 1.0  
**Статус:** Draft

## Executive Summary

На основе анализа текущей документации проекта BioETL выявлено, что основная документация в репозитории `docs/` является актуальной и отражает последние изменения кода. Однако есть несколько областей, которые требуют обновления для улучшения полноты и доступности документации для разных аудиторий.

## Текущее состояние документации

### ✅ Хорошо организованные разделы
- **Architecture (docs/02-architecture/)**: 55 ADR, включая последние ADR-046–055
- **Monitoring (docs/05-operations/)**: Обновлён после surface reduction 2026-07-23
- **Control Plane (docs/03-guides/workflows.md)**: Включает ADR-047 и новые CLI команды
- **API Reference (docs/04-reference/api/)**: Содержит новые порты (StorageMaintenancePort, CompositeCheckpointPort)
- **Normalization (docs/04-reference/normalization/)**: Обновлена с новыми полями публикаций

### ✅ Генерируемые артефакты
- **Pipeline dataflow documentation**: `docs/02-architecture/generated/pipeline-dataflows/`
- **Pipeline passports**: `docs/04-reference/passports/`
- **Normalization field matrix**: `docs/reports/generated/pipeline_normalization_field_matrix/`

## Выявленные пробелы и приоритеты

### Приоритет 1: Критические обновления для пользователей

#### 1.1 Документация pipeline dataflow для пользователей
**Проблема:** Новая функциональность генерации pipeline dataflow документации упоминается в CHANGELOG, но не имеет пользовательского руководства.

**Текущее состояние:**
- Техническая документация существует: `docs/02-architecture/generated/pipeline-dataflows/chembl_activity/pipeline-passport.md`
- Генератор: `scripts/diagrams/render/generate_pipeline_dataflows.py`
- Ссылки на диаграммы и IR JSON присутствуют

**Требуемые действия:**
- [ ] Создать пользовательский guide: `docs/03-guides/pipeline-dataflow-documentation.md`
- [ ] Объяснить назначение pipeline dataflow documentation
- [ ] Описать как читать и интерпретировать pipeline passports
- [ ] Добавить примеры использования для разных пайплайнов
- [ ] Обновить `docs/00-project/00-map.md` с ссылкой на новый guide

**Затронутые файлы:**
- `docs/03-guides/pipeline-dataflow-documentation.md` (новый)
- `docs/00-project/00-map.md` (обновление)

#### 1.2 Обновление pipeline configuration guide
**Проблема:** Существующий `docs/03-guides/pipeline-configuration.md` может не отражать новые возможности генерации dataflow документации.

**Требуемые действия:**
- [ ] Добавить секцию о pipeline dataflow generation
- [ ] Описать интеграцию с CI (drift detection)
- [ ] Объяснить связь между config changes и documentation updates

**Затронутые файлы:**
- `docs/03-guides/pipeline-configuration.md` (обновление)

### Приоритет 2: Архитектурные обновления

#### 2.1 Документация архитектурных рефакторингов
**Проблема:** Последние архитектурные рефакторинги (RF-002, RF-007.3, RF-008.2) отражены в CHANGELOG и технической документации, но могут потребоваться обновления в architecture guides.

**Текущее состояние:**
- CHANGELOG описывает: PostrunMetadataVersionResolver, CompositeCheckpointService, narrow ports migration
- Технические детали в API reference и diagrams
- ADR-054 (Passport Documentation Projections) принят

**Требуемые действия:**
- [ ] Обновить `docs/02-architecture/02-application-layer.md` с новыми паттернами
- [ ] Добавить секцию о port migration strategy
- [ ] Обновить `docs/02-architecture/03-infrastructure-layer.md` с новыми адаптерами
- [ ] Рассмотреть создание отдельного guide: `docs/02-architecture/port-evolution.md`

**Затронутые файлы:**
- `docs/02-architecture/02-application-layer.md` (обновление)
- `docs/02-architecture/03-infrastructure-layer.md` (обновление)
- `docs/02-architecture/port-evolution.md` (новый, опционально)

#### 2.2 Fail-fast semantics documentation
**Проблема:** Изменения в EnrichmentCoordinatorService (fail-fast semantics) описаны в CHANGELOG, но не имеют пользовательской документации.

**Требуемые действия:**
- [ ] Обновить `docs/02-architecture/domain-composite.md` с fail-fast паттернами
- [ ] Добавить описание поведения при ошибках enrichers
- [ ] Обновить composite pipeline documentation

**Затронутые файлы:**
- `docs/02-architecture/domain-composite.md` (обновление)
- `docs/04-reference/pipelines/composite/` (обновление спецификаций)

### Приоритет 3: Operational и runbook обновления

#### 3.1 Runtime locking terminology
**Проблема:** Locking terminology уже обновлена в коде и некоторых документах, но может потребоваться полная синхронизация.

**Текущее состояние:**
- CHANGELOG описывает locking terminology aligned with Local-Only runtime semantics
- Некоторые docs обновлены, но возможны остаточные упоминания старой терминологии

**Требуемые действия:**
- [ ] Проверить все docs на предмет старой терминологии locking
- [ ] Обновить `docs/05-operations/runbooks/scaling.md` (уже обновлено по CHANGELOG)
- [ ] Проверить `docs/03-guides/running-pipelines.md` на предмет locking terminology

**Затронутые файлы:**
- `docs/03-guides/running-pipelines.md` (проверка/обновление)
- Другие operational docs (проверка)

#### 3.2 CLI observability backend defaults
**Проблема:** Изменения в CLI observability backend defaults (--ensure-observability-backend) описаны в CHANGELOG, но могут потребоваться обновления в user guides.

**Требуемые действия:**
- [ ] Обновить `docs/03-guides/metrics-monitoring.md` с новыми defaults
- [ ] Обновить `docs/04-reference/cli.md` с описанием новых опций
- [ ] Проверить `docs/05-operations/01-monitoring-guide.md` на соответствие

**Затронутые файлы:**
- `docs/03-guides/metrics-monitoring.md` (обновление)
- `docs/04-reference/cli.md` (обновление)

### Приоритет 4: Reference documentation улучшения

#### 4.1 Passport documentation guide
**Проблема:** Существует `docs/04-reference/passports/pipeline-passport-guide.md`, но может потребоваться обновление с учётом ADR-054.

**Требуемые действия:**
- [ ] Обновить guide с учётом ADR-054 (Passport Documentation Projections)
- [ ] Добавить примеры использования pipeline passports
- [ ] Описать связь между pipeline dataflow и passports

**Затронутые файлы:**
- `docs/04-reference/passports/pipeline-passport-guide.md` (обновление)

#### 4.2 Normalization documentation completeness
**Проблема:** Normalization governance closure для ChEMBL и publication types отражена в CHANGELOG, но может потребоваться обновление user guides.

**Требуемые действия:**
- [ ] Обновить `docs/03-guides/cheatsheets/pipeline-config.md` с новыми полями
- [ ] Проверить completeness всех normalization guides
- [ ] Добавить примеры использования новых canonical fields

**Затронутые файлы:**
- `docs/03-guides/cheatsheets/pipeline-config.md` (обновление)
- `docs/04-reference/normalization/` (проверка)

## Рекомендации по процессу документирования

### 1. Интеграция с процессом разработки

**Текущая практика:**
- Документация обновляется вместе с кодом (хорошо)
- CHANGELOG ведётся систематически
- ADR процесс формализован

**Рекомендации:**
- [ ] Добавить documentation check в PR template
- [ ] Создать checklist для documentation updates в RULES.md
- [ ] Интегрировать documentation review в code review process

### 2. Автоматизация генерации документации

**Текущее состояние:**
- Pipeline dataflow documentation генерируется автоматически
- ADR registry генерируется автоматически
- Normalization field matrix генерируется автоматически

**Рекомендации:**
- [ ] Добавить CI check для сгенерированной документации
- [ ] Создать script для проверки актуальности user guides
- [ ] Рассмотреть автоматическую генерацию API reference из docstrings

### 3. Структура и навигация

**Текущее состояние:**
- Хорошая структура: 00-project, 01-requirements, 02-architecture, 03-guides, 04-reference, 05-operations
- Project Navigator (00-map.md) хорошо организован

**Рекомендации:**
- [ ] Добавить "What's New" section в 00-map.md для последних изменений
- [ ] Создать changelog для документации (отдельный от CHANGELOG.md)
- [ ] Улучшить cross-references между разделами

### 4. Метрики качества документации

**Рекомендации:**
- [ ] Определить KPI для документации (полнота, актуальность, доступность)
- [ ] Создать script для проверки dead links
- [ ] Внедрить periodic documentation audit (ежеквартально)

## План выполнения

### Фаза 1: Критические обновления (1-2 недели)
1. Создать pipeline dataflow documentation guide
2. Обновить pipeline configuration guide
3. Обновить CLI reference с новыми опциями

### Фаза 2: Архитектурные обновления (2-3 недели)
1. Обновить architecture layer docs с новыми паттернами
2. Документировать fail-fast semantics
3. Обновить composite pipeline documentation

### Фаза 3: Operational обновления (1-2 недели)
1. Проверить и обновить locking terminology
2. Обновить metrics monitoring guide
3. Проверить все operational docs на актуальность

### Фаза 4: Reference улучшения (1-2 недели)
1. Обновить passport documentation guide
2. Проверить normalization documentation completeness
3. Улучшить cross-references

### Фаза 5: Процесс улучшения (1 неделя)
1. Внедрить documentation check в PR template
2. Создать documentation audit process
3. Настроить автоматические проверки для документации

## Критерии успеха

- [ ] Все критические (Priority 1) обновления завершены
- [ ] User guides отражают последние изменения кода
- [ ] Architecture docs синхронизированы с рефакторингами
- [ ] Operational docs актуальны
- [ ] Documentation process интегрирован в разработку
- [ ] Автоматические проверки для документации настроены

## Риски и митигация

| Риск | Вероятность | Влияние | Митигация |
|------|-------------|---------|------------|
| Недостаток времени для всех обновлений | Средняя | Средняя | Приоритизация по критичности, фазовый подход |
| Устаревание документации во время выполнения | Средняя | Низкая | Регулярная синхронизация с CHANGELOG |
| Сложность в создании user guides для технических изменений | Низкая | Средняя | Использование существующих паттернов, консультации с разработчиками |
| Отсутствие автоматических проверок | Средняя | Низкая | Постепенное внедрение, начиная с manual checks |

## Следующие шаги

1. **Утверждение плана** - Получить feedback от команды по приоритетам и объёму
2. **Начало с Priority 1** - Создать pipeline dataflow documentation guide
3. **Регулярный прогресс** - Еженедельные обновления статуса
4. **Интеграция с процессом** - Начать внедрение documentation checks

---

**Создано:** 2026-08-05  
**Автор:** Devin AI Assistant  
**Связанные артефакты:**
- GitHub Issue #8035 (DeepWiki regeneration request)
- CHANGELOG.md (последние изменения кода)
- docs/00-project/00-map.md (текущая структура документации)