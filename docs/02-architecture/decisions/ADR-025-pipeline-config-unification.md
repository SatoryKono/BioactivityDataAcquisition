# ADR-025: Pipeline Configuration Unification

| Аспект | Значение |
|--------|----------|
| **Статус** | Accepted |
| **Дата** | 2026-01-13 |
| **Авторы** | BioETL Team |
| **Связанные ADR** | ADR-002 (Medallion Architecture), ADR-024 (Entity Naming) |

## Контекст

Проект BioETL использует YAML-конфигурации для пайплайнов, расположенные в `configs/pipelines/<provider>/<entity>.yaml`. После аудита 19 конфигураций выявлена необходимость документирования существующей трёхуровневой архитектуры конфигурации и создания референсных файлов для провайдеров.

### Текущее состояние

- 19 pipeline configs across 7 providers
- 1 defaults file (`_defaults.yaml`)
- 7 source configs (`configs/sources/*.yaml`)
- No critical MUST violations
- 100% compliance with Delta Lake requirement for Silver layer

### Анализируемая схема

Референсная схема из RULES.md v5.0 Appendix D предлагает плоскую структуру:

```yaml
pipeline:
  name: <entity>_<provider>
  provider: <provider>
transform:
  version: "1.0.0"
  steps: [...]
rate_limit:
  requests_per_second: 5
```

## Решение

**Сохранить существующую трёхуровневую архитектуру конфигурации** с добавлением:
1. Расширенной документации в `_defaults.yaml`
2. Референсных файлов провайдеров в `_providers/`
3. Матрицы соответствия и отчёта о состоянии

### Трёхуровневая иерархия

```
_defaults.yaml          → Global defaults (dq_rules, sink, maintenance)
       │
configs/sources/*.yaml  → Provider settings (rate_limit, client, circuit_breaker)
       │
<provider>/<entity>.yaml → Entity settings (gold_filters, primary_keys)
```

### Обоснование

1. **DRY Principle**: Общие настройки определены один раз в `_defaults.yaml`
2. **Provider Isolation**: Rate limits и client config сгруппированы по провайдеру
3. **Entity Focus**: Pipeline configs содержат только entity-specific логику
4. **Backward Compatibility**: Существующие configs не требуют изменений

## Альтернативы

### Альтернатива 1: Плоская схема (отклонена)

Перейти на схему из референса с rate_limit в каждом pipeline config.

**Причина отклонения:**
- Дублирование rate_limit для каждой entity одного провайдера
- Нарушение DRY principle
- Увеличение риска рассинхронизации настроек

### Альтернатива 2: Вложенный `pipeline:` блок (отклонена)

Добавить `pipeline:` wrapper вокруг `pipeline_name`, `provider`, `entity_type`.

**Причина отклонения:**
- Требует миграции всех 19 configs
- Усложняет парсинг без функциональной выгоды
- Текущая плоская структура поддерживается Pydantic schema

### Альтернатива 3: `transform:` блок (отклонена)

Переместить `version` в `transform.version` и добавить `transform.steps`.

**Причина отклонения:**
- Transform steps определены в коде (BaseTransformer subclasses)
- Steps не конфигурируемы at runtime
- `version` на root level служит той же цели

## Последствия

### Позитивные

1. **Документация**: Чёткое описание схемы в `_defaults.yaml`
2. **Референсы**: Provider-specific настройки документированы в `_providers/`
3. **Отчётность**: Матрица соответствия и issues report для аудита
4. **Стабильность**: Нет breaking changes в существующих configs

### Негативные

1. **Schema drift**: Референсная схема в RULES.md отличается от реализации
   - **Митигация**: Обновить RULES.md Appendix D

2. **Path inconsistency**: Смешанные паттерны путей в configs
   - **Митигация**: P2 задача на стандартизацию

## Артефакты

| Артефакт | Путь | Описание |
|----------|------|----------|
| Compliance Matrix | `reports/pipeline-config-matrix.csv` | Матрица параметров всех configs |
| Issues Report | `reports/pipeline-config-issues.md` | Отчёт о расхождениях |
| Defaults Schema | `configs/pipelines/_defaults.yaml` | Расширенная документация |
| Provider Reference | `configs/pipelines/_providers/*.yaml` | Референсы провайдеров |

## Метрики

| Метрика | До | После |
|---------|----|----|
| MUST violations | 0 | 0 |
| SHOULD compliance | 95% | 95% |
| Documentation coverage | Partial | Complete |
| Provider reference files | 0 | 7 |

## План реализации

### Phase 1: Documentation (Done)

- [x] Расширить документацию `_defaults.yaml`
- [x] Создать `_providers/` с референсными файлами
- [x] Сгенерировать compliance matrix и issues report

### Phase 2: RULES.md Update (P1)

- [ ] Обновить Appendix D с реальной трёхуровневой схемой
- [ ] Добавить примеры provider и entity configs

### Phase 3: Path Standardization (P2)

- [ ] Стандартизировать пути к `data/{layer}/{provider}/{entity}`
- [ ] Обновить 15 configs с `data/output/` паттерном

## Ссылки

- RULES.md §2.1: Medallion Architecture
- `src/bioetl/infrastructure/schemas/pipeline_config.py`: Pydantic schema
- `src/bioetl/domain/config_types.py`: TypedDict definitions
