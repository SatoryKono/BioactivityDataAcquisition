# Расширение BioETL: Добавление новых Pipeline

*Синхронизировано с RULES.md v5.19 | Последнее обновление: 2026-01-14*

---

## Обзор

Данный документ описывает процесс добавления новых pipeline в BioETL,
включая создание конфигураций, трансформеров и тестов.

---

## 1. Чек-лист создания нового Pipeline

- [ ] Создать entity config в `configs/pipelines/<provider>/<entity>.yaml`
- [ ] Валидировать через `_schema.json`
- [ ] Выбрать каноническое имя согласно [02-naming-policy.md](02-naming-policy.md)
- [ ] Создать трансформер в `src/bioetl/application/pipelines/`
- [ ] Зарегистрировать в `PipelineRegistry`
- [ ] Добавить фабрику (при необходимости)
- [ ] Написать unit и integration тесты
- [ ] Обновить документацию провайдера

---

## 2. Шаблон Entity Config

### 2.1. Минимальный шаблон

```yaml
# configs/pipelines/<provider>/<entity>.yaml
# Pipeline configuration for <Provider> <Entity>.
#
# Inherits defaults from ../_defaults.yaml:
# - dq_overrides, circuit_breaker, sink structure, maintenance, input_filter
#
# IMPORTANT: Use Canonical Terms from 02-naming-policy.md
```

### 2.2. Обязательные поля

| Поле | Тип | Описание | Требование |
|------|-----|----------|------------|
| `pipeline_name` | string | Формат `{provider}_{entity}` | MUST |
| `provider` | enum | Один из: chembl, pubchem, uniprot, pubmed, crossref, openalex, semanticscholar | MUST |
| `entity_type` | string | Тип сущности | MUST |
| `version` | string | Семантическая версия `X.Y.Z` | MUST |
| `primary_keys` | array | Первичный ключ | MUST |
| `silver_table` | string | Имя Silver таблицы | MUST |
| `gold_table` | string | Имя Gold таблицы | MUST |
| `sink` | object | Конфигурация слоёв | MUST |
| `sink.*.sort_by` | object | Сортировка для детерминизма | MUST |

### 2.3. sort_by — Обязательное требование (ADR-014)

**MUST**: Каждый entity config должен содержать `sort_by` для Silver и Gold слоёв.

```yaml
sink:
  silver:
    sort_by:
      columns: ["primary_key_column"]  # Список колонок для сортировки
      ascending: true                   # true = ASC, false = DESC
  gold:
    sort_by:
      columns: ["primary_key_column"]
      ascending: true
```

**Почему это важно:**
- Гарантирует детерминизм выходных файлов
- Обеспечивает воспроизводимость результатов
- Стабилизирует diff-сравнения между запусками

---

## 3. Валидация через JSON Schema

### 3.1. Автоматическая валидация

Все entity configs валидируются через `configs/pipelines/_schema.json`.

**Pre-commit hook:**
```yaml
# .pre-commit-config.yaml
- repo: local
  hooks:
    - id: validate-pipeline-configs
      name: Validate pipeline configs
      entry: python scripts/validate_pipeline_configs.py
      language: python
      files: ^configs/pipelines/.+\.yaml$
      exclude: ^configs/pipelines/_
```

### 3.2. Ручная валидация

```bash
# Валидация одного файла
python scripts/validate_pipeline_configs.py configs/pipelines/chembl/activity.yaml

# Валидация всех конфигов
python scripts/validate_pipeline_configs.py

# Или через make
make validate-configs
```

### 3.3. Структура JSON Schema

Схема `_schema.json` проверяет:

| Проверка | Описание |
|----------|----------|
| `required` | Наличие обязательных полей |
| `pattern` | Формат `pipeline_name` (`^[a-z]+_[a-z_]+$`) |
| `enum` | Допустимые значения `provider` |
| `type` | Типы данных полей |
| `minimum/maximum` | Ограничения числовых значений |

---

## 4. Создание трансформера

### 4.1. Шаблон трансформера

```python
# src/bioetl/application/pipelines/<provider>_<entity>.py
"""Трансформер для <Provider> <Entity>."""

from dataclasses import dataclass
from typing import Any

from bioetl.application.core.base_transformer import BaseTransformer


@dataclass
class <Provider><Entity>Transformer(BaseTransformer):
    """Трансформер для обработки <entity> записей из <Provider>."""

    def transform_record(self, record: dict[str, Any]) -> dict[str, Any]:
        """Трансформация одной записи.

        Args:
            record: Сырая запись из Bronze.

        Returns:
            Трансформированная запись для Silver.
        """
        return {
            "<entity>_id": record.get("<entity>_id"),
            # ... другие поля
        }

    def validate_record(self, record: dict[str, Any]) -> bool:
        """Валидация записи перед трансформацией.

        Args:
            record: Запись для валидации.

        Returns:
            True если запись валидна.
        """
        return "<entity>_id" in record
```

### 4.2. Регистрация в Registry

```python
# src/bioetl/composition/registry.py
from bioetl.application.pipelines.<provider>_<entity> import <Provider><Entity>Transformer

@register("<provider>_<entity>")
class <Provider><Entity>Pipeline:
    transformer_class = <Provider><Entity>Transformer
```

---

## 5. Тестирование

### 5.1. Unit тесты трансформера

```python
# tests/unit/application/pipelines/test_<provider>_<entity>.py
import pytest
from bioetl.application.pipelines.<provider>_<entity> import <Provider><Entity>Transformer


class Test<Provider><Entity>Transformer:
    def test_transform_record_valid(self):
        transformer = <Provider><Entity>Transformer()
        record = {"<entity>_id": "123", ...}
        result = transformer.transform_record(record)
        assert result["<entity>_id"] == "123"

    def test_validate_record_missing_id(self):
        transformer = <Provider><Entity>Transformer()
        record = {}
        assert not transformer.validate_record(record)
```

### 5.2. Integration тесты с VCR

```python
# tests/integration/adapters/test_<provider>_<entity>.py
import pytest

@pytest.mark.vcr()
async def test_fetch_<entity>_from_<provider>():
    # VCR-кассета автоматически записывает HTTP-ответы
    ...
```

### 5.3. Валидация конфига

```python
# tests/unit/configs/test_<provider>_<entity>_config.py
import json
import yaml
import jsonschema


def test_<provider>_<entity>_config_valid():
    with open("configs/pipelines/_schema.json") as f:
        schema = json.load(f)
    with open("configs/pipelines/<provider>/<entity>.yaml") as f:
        config = yaml.safe_load(f)

    # Должен пройти без исключений
    jsonschema.validate(config, schema)


def test_<provider>_<entity>_has_sort_by():
    with open("configs/pipelines/<provider>/<entity>.yaml") as f:
        config = yaml.safe_load(f)

    assert "sort_by" in config["sink"]["silver"]
    assert "sort_by" in config["sink"]["gold"]
```

---

## 6. Документация провайдера

После создания pipeline обновите документацию:

1. **`docs/providers/<provider>/README.md`** — добавить entity в список
2. **`docs/00-map.md`** — обновить счётчик pipelines
3. **`CLAUDE.md`** — обновить метрики (если существенные изменения)

---

## 7. Пример: Добавление chembl_target_component

### 7.1. Config

```yaml
# configs/pipelines/chembl/target_component.yaml
pipeline_name: chembl_target_component
provider: chembl
entity_type: target_component
version: "1.0.0"
description: "Extract target component records from ChEMBL API"

primary_keys: ["component_id"]
silver_table: "chembl_target_component"
gold_table: "chembl_target_component"

source_file: ../../sources/chembl.yaml

gold_filters:
  required_fields:
    - component_id
    - component_type

sink:
  bronze:
    path: "data/output/bronze/chembl/target_component"
  silver:
    path: "data/output/silver/chembl/target_component"
    primary_key: ["component_id"]
    partition_by: []
    sort_by:
      columns: ["component_id"]
      ascending: true
    csv_export:
      path: "data/output/csv/silver/chembl/target_component"
  gold:
    path: "data/output/gold/chembl/target_component"
    sort_by:
      columns: ["component_id"]
      ascending: true
    csv_export:
      path: "data/output/csv/gold/chembl/target_component"

input_filter:
  enabled: false
```

### 7.2. Валидация

```bash
# Проверить соответствие схеме
python scripts/validate_pipeline_configs.py configs/pipelines/chembl/target_component.yaml
```

---

## Связанные документы

- [03-file-policy.md](03-file-policy.md) — Политика файлов
- [ADR-014: Deterministic Writes](../02-architecture/decisions/ADR-014-deterministic-writes.md)
- [ADR-025: Pipeline Config Unification](../02-architecture/decisions/ADR-025-pipeline-config-unification.md)
- [03-guides/add-new-source.md](../03-guides/add-new-source.md) — Добавление нового провайдера

---

*Последнее обновление: 2026-01-14*
