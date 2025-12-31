# План Рефакторинга Пайплайнов: Удаление Дублирования

*Версия: 1.0 | Дата: 2025-12-29*
*Соответствует: CLAUDE.md §0 "Протокол Двойной Верификации"*

---

## Обзор

Этот план описывает оптимизацию пайплайнов в `src/bioetl/application/pipelines/`, устраняя дублирование между модулями и упрощая оркестрацию через параметризацию.

### Верификация Проведена

| Проверка | Результат | Ссылка |
|----------|-----------|--------|
| refactoring-plan.md "ЛОЖНЫЕ УТВЕРЖДЕНИЯ" | Проверено | `docs/refactoring-plan.md:48-98` |
| BaseChemblTransformer Template Method | ✅ Уже реализован | `base_chembl_transformer.py:29-157` |
| Core orchestration | ✅ Хорошо отфакторено | `application/core/` (executor, runner, base_transformer) |

---

## Верифицированное Дублирование

### 1. YAML Конфигурации — 61% Boilerplate (~600 LOC)

**Файлы:** 11 конфигов в `configs/pipelines/`

| Секция | Дублирование | Файлы:строки |
|--------|--------------|--------------|
| `transform:` | Идентична во всех | `activity.yaml:34-39`, `molecule.yaml:25-30`, и др. |
| `dq_rules:` | Идентична: `soft=0.05`, `hard=0.20` | `activity.yaml:80-82`, `molecule.yaml:71-73` |
| `circuit_breaker:` | Идентична: `failure=5`, `recovery=300` | `activity.yaml:84-86`, `molecule.yaml:75-77` |
| `sink.bronze/silver/gold` | 80% идентична | Все конфиги |
| `csv_export:` | Полностью идентична | Все конфиги с `csv_export` |

**Доказательство дублирования:**

```yaml
# Идентично во ВСЕХ 11 конфигах:
transform:
    version: "1.0.0"
    steps:
        - normalize_values
        - add_metadata
        - calculate_content_hash

dq_rules:
    soft_fail_threshold: 0.05
    hard_fail_threshold: 0.20

circuit_breaker:
    failure_threshold: 5
    recovery_timeout: 300
```

### 2. ChEMBL Трансформеры — Повторяющиеся `_map_*` Паттерны (~400 LOC)

**Файлы:** 8 трансформеров в `pipelines/chembl/*_transformer.py`

| Трансформер | LOC | `_map_*` методов | Паттерн |
|-------------|-----|------------------|---------|
| `activity_transformer.py` | 171 | 5 | `record.get()` + `safe_int/safe_float` |
| `molecule_transformer.py` | 168 | 5 | `record.get()` + `safe_int/safe_float` |
| `assay_transformer.py` | ~143 | 4 | `record.get()` + `safe_int/safe_float` |
| `target_transformer.py` | ~160 | 4 | `record.get()` + aggregation |
| `document_transformer.py` | ~63 | 2 | Direct extraction |
| `cell_line_transformer.py` | ~98 | 2 | Validation helpers |

**Повторяющийся паттерн (75+ occurrences):**

```python
# activity_transformer.py:73-85
def _map_core_identifiers(self, record, activity_id, molecule_id):
    return {
        "activity_id": str(activity_id),
        "molecule_chembl_id": str(molecule_id),
        "target_chembl_id": record.get("target_chembl_id"),
        "record_id": safe_int(record.get("record_id")),
        "src_id": safe_int(record.get("src_id")),
    }

# molecule_transformer.py:80-88 (аналогичный паттерн)
def _map_core_metadata(self, record):
    return {
        "pref_name": record.get("pref_name"),
        "molecule_type": record.get("molecule_type"),
        "max_phase": safe_int(record.get("max_phase")),
        ...
    }
```

### 3. JSON Сериализация — Повторяющиеся Вызовы (~20 occurrences)

```python
# molecule_transformer.py:122-135 (6 вызовов)
"molecule_hierarchy": self.serialize_json(record.get("molecule_hierarchy")),
"molecule_properties": self.serialize_json(record.get("molecule_properties")),
"molecule_structures": self.serialize_json(record.get("molecule_structures")),
"molecule_synonyms": self.serialize_json(record.get("molecule_synonyms")),
"cross_references": self.serialize_json(record.get("cross_references")),
"atc_classifications": self.serialize_json(record.get("atc_classifications")),
```

---

## ✅ Что НЕ Требует Рефакторинга

> **ВАЖНО**: Эти компоненты уже хорошо отфакторены. См. `refactoring-plan.md:48-98`.

| Компонент | Почему НЕ дублирование |
|-----------|------------------------|
| `BaseChemblTransformer` | Template Method уже реализован (`base_chembl_transformer.py:76-128`) |
| `BaseTransformer` | Общая логика трансформации (`base_transformer.py:530 LOC`) |
| Core orchestration | `runner.py`, `executor.py`, `batch_transformer.py` — делегирование работает |
| `transform_utils.py` | Утилиты уже выделены (`flatten_nested_dict` используется) |

---

## План Рефакторинга (Ранжировано по Impact/Complexity)

### Фаза 1: Configuration Templates (HIGH Impact, LOW Complexity)

**Цель:** Сократить 600 LOC boilerplate в YAML конфигах до ~100 LOC.

#### 1.1 Создание базового шаблона конфигурации

**Новый файл:** `configs/pipelines/_defaults.yaml`

```yaml
# configs/pipelines/_defaults.yaml
# Базовые настройки для всех пайплайнов (YAML anchors)

defaults:
  transform: &default_transform
    version: "1.0.0"
    steps:
      - normalize_values
      - add_metadata
      - calculate_content_hash

  dq_rules: &default_dq_rules
    soft_fail_threshold: 0.05
    hard_fail_threshold: 0.20

  circuit_breaker: &default_circuit_breaker
    failure_threshold: 5
    recovery_timeout: 300

  sink:
    bronze: &default_bronze
      path: "data/output/bronze"
      format: jsonl
      save_json: true
      deterministic: true

    silver: &default_silver
      path: "data/output/silver"
      format: delta
      on_schema_mismatch: evolve
      classification: public
      forensic_retention: true
      deterministic: true
      csv_export: &default_csv_export
        enabled: true
        delimiter: ","
        header: true
        encoding: "utf-8"

    gold: &default_gold
      enabled: true
      validation:
        strict: true
      path: "data/output/gold"
      format: delta
      mode: overwrite
      deterministic: true
      csv_export:
        <<: *default_csv_export
        path: "data/output/csv/gold"
```

#### 1.2 Упрощение entity-specific конфигов

**Было (activity.yaml — 96 строк):**
```yaml
# 96 строк с повторяющимися секциями
```

**Станет (activity.yaml — ~40 строк):**
```yaml
# configs/pipelines/chembl/activity.yaml
# Использует defaults через YAML anchors

_include: ../_defaults.yaml  # Loader подхватит anchors

pipeline_name: chembl_activity
provider: chembl
entity_type: activity
version: "1.0.0"
description: "Extract biological activity records from ChEMBL API"

primary_keys: ["activity_id"]
silver_table: "chembl_activity"
source_file: ../../sources/chembl.yaml

# Entity-specific settings ONLY:
gold_filters:
  columns:
    standard_type: [IC50, Ki]
    standard_units: [nM]
    standard_relation: ["="]
    assay_type: [B, F]
    potential_duplicate: ["0"]
  ranges:
    standard_value: { min: 0, include_min: false }
  required_fields:
    - standard_type
    - standard_value
    - standard_units
    - target_chembl_id

# Наследование defaults (anchors):
transform: *default_transform
dq_rules: *default_dq_rules
circuit_breaker: *default_circuit_breaker

sink:
  bronze: *default_bronze
  silver:
    <<: *default_silver
    mode: merge
    primary_key: ["activity_id"]
    csv_export:
      <<: *default_csv_export
      path: "data/output/csv/silver"
  gold:
    <<: *default_gold

input_filter:
  enabled: true
  source_path: "data/input/activity.csv"
  column_name: "activity_id"
  filter_field: "activity_id"
  batch_size: 20
```

#### 1.3 Обновление ConfigLoader

**Файл:** `src/bioetl/infrastructure/config/yaml_loader.py`

```python
# Добавить поддержку _include директивы
def load_config_with_defaults(config_path: Path) -> dict:
    """Load config with defaults from _defaults.yaml."""
    defaults_path = config_path.parent.parent / "_defaults.yaml"

    if defaults_path.exists():
        with open(defaults_path) as f:
            defaults = yaml.safe_load(f)
    else:
        defaults = {}

    with open(config_path) as f:
        config = yaml.safe_load(f)

    # Merge defaults with config (config wins)
    return deep_merge(defaults.get("defaults", {}), config)
```

**Результат Фазы 1:**
- Сокращение: ~600 LOC → ~150 LOC (75% reduction)
- Единый источник правды для defaults
- Entity-specific конфиги содержат только уникальные поля

---

### Фаза 2: Field Mapping Declarative Specs (MEDIUM Impact, MEDIUM Complexity)

**Цель:** Заменить повторяющиеся `_map_*` методы декларативными спецификациями.

#### 2.1 Создание FieldSpec DSL

**Новый файл:** `src/bioetl/application/core/field_specs.py`

```python
"""Declarative field mapping specifications.

Replaces repetitive _map_* methods with config-driven approach.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from bioetl.domain.transformations import safe_float, safe_int


@dataclass(frozen=True, slots=True)
class FieldSpec:
    """Specification for a single field mapping."""
    source: str  # Source field name in record
    target: str | None = None  # Target field name (defaults to source)
    converter: Callable[[Any], Any] | None = None  # Optional type converter
    required: bool = False  # Raise if missing


@dataclass(frozen=True, slots=True)
class FieldGroup:
    """Group of related field specifications."""
    name: str
    fields: tuple[FieldSpec, ...]
    prefix: str = ""  # Optional prefix for target field names


# Type aliases for common converters
INT = safe_int
FLOAT = safe_float
STR = str
NONE = None  # No conversion


def map_fields(record: dict[str, Any], specs: tuple[FieldSpec, ...]) -> dict[str, Any]:
    """Map fields from record according to specifications.

    Args:
        record: Source record dictionary.
        specs: Tuple of field specifications.

    Returns:
        Dictionary with mapped fields.

    Example:
        >>> specs = (
        ...     FieldSpec("activity_id", converter=STR),
        ...     FieldSpec("value", converter=FLOAT),
        ...     FieldSpec("type"),  # No conversion
        ... )
        >>> map_fields({"activity_id": 123, "value": "5.5", "type": "IC50"}, specs)
        {'activity_id': '123', 'value': 5.5, 'type': 'IC50'}
    """
    result = {}
    for spec in specs:
        value = record.get(spec.source)
        target = spec.target or spec.source

        if spec.required and value is None:
            raise ValueError(f"Required field '{spec.source}' is missing")

        if value is not None and spec.converter is not None:
            value = spec.converter(value)

        result[target] = value

    return result


def map_field_group(
    record: dict[str, Any],
    group: FieldGroup
) -> dict[str, Any]:
    """Map a group of fields with optional prefix."""
    mapped = map_fields(record, group.fields)

    if group.prefix:
        return {f"{group.prefix}{k}": v for k, v in mapped.items()}
    return mapped
```

#### 2.2 Рефакторинг ActivityTransformer с использованием FieldSpec

**Было (activity_transformer.py:73-145 — 73 строки 5 методов):**
```python
def _map_core_identifiers(self, record, activity_id, molecule_id):
    return {
        "activity_id": str(activity_id),
        "molecule_chembl_id": str(molecule_id),
        "target_chembl_id": record.get("target_chembl_id"),
        ...
    }

def _map_molecule_target_assay(self, record):
    return {
        "canonical_smiles": record.get("canonical_smiles"),
        ...
    }
# ... 3 more _map_* methods
```

**Станет (activity_transformer.py — ~50 строк):**
```python
from bioetl.application.core.field_specs import (
    FieldSpec, FieldGroup, map_field_group, INT, FLOAT, STR, NONE
)

# Declarative field specifications
CORE_IDENTIFIERS = FieldGroup(
    name="core_identifiers",
    fields=(
        FieldSpec("target_chembl_id"),
        FieldSpec("assay_chembl_id"),
        FieldSpec("document_chembl_id"),
        FieldSpec("record_id", converter=INT),
        FieldSpec("src_id", converter=INT),
    ),
)

ACTIVITY_VALUES = FieldGroup(
    name="activity_values",
    fields=(
        FieldSpec("type"),
        FieldSpec("value", converter=FLOAT),
        FieldSpec("units"),
        FieldSpec("relation"),
        FieldSpec("upper_value", converter=FLOAT),
        FieldSpec("text_value"),
        FieldSpec("standard_type"),
        FieldSpec("standard_value", converter=FLOAT),
        FieldSpec("standard_units"),
        FieldSpec("standard_relation"),
        FieldSpec("standard_upper_value", converter=FLOAT),
        FieldSpec("standard_text_value"),
        FieldSpec("standard_flag", converter=INT),
        FieldSpec("pchembl_value", converter=FLOAT),
        FieldSpec("qudt_units"),
        FieldSpec("uo_units"),
    ),
)

# ... other field groups

class ActivityTransformer(BaseChemblTransformer):
    entity_class = Activity
    primary_id_field = "activity_id"

    # Field groups for this entity
    FIELD_GROUPS = (CORE_IDENTIFIERS, ACTIVITY_VALUES, QUALITY_ANNOTATIONS, MOLECULE_TARGET_ASSAY)

    def _extract_business_data(self, record: BronzeRecord, primary_id: Any) -> dict[str, Any]:
        molecule_id = self._get_required_field(record, "molecule_chembl_id")

        # Core identifiers (primary + secondary)
        result = {
            "activity_id": str(primary_id),
            "molecule_chembl_id": str(molecule_id),
        }

        # Apply all field groups
        for group in self.FIELD_GROUPS:
            result.update(map_field_group(record, group))

        # Handle nested structures (ligand_efficiency, action_type)
        result.update(self._extract_ligand_efficiency(record.get("ligand_efficiency")))
        result.update(self._extract_action_type(record.get("action_type")))

        return result
```

**Результат Фазы 2:**
- Сокращение: ~400 LOC → ~150 LOC (62% reduction)
- Декларативное описание полей
- Легче добавлять новые entity

---

### Фаза 3: JSON Serialization Helper (LOW Impact, LOW Complexity)

**Цель:** Упростить множественную JSON сериализацию.

#### 3.1 Добавление batch-метода в BaseTransformer

**Файл:** `src/bioetl/application/core/base_transformer.py`

```python
def serialize_json_fields(
    self,
    record: dict[str, Any],
    field_names: Sequence[str]
) -> dict[str, str | None]:
    """Serialize multiple JSON fields at once.

    Args:
        record: Source record.
        field_names: Names of fields to serialize.

    Returns:
        Dictionary with serialized JSON strings.

    Example:
        >>> self.serialize_json_fields(record, [
        ...     "molecule_hierarchy",
        ...     "molecule_properties",
        ...     "cross_references",
        ... ])
    """
    return {
        name: self.serialize_json(record.get(name))
        for name in field_names
    }
```

#### 3.2 Рефакторинг MoleculeTransformer

**Было (molecule_transformer.py:120-135):**
```python
def _map_complex_fields(self, record):
    return {
        "molecule_hierarchy": self.serialize_json(record.get("molecule_hierarchy")),
        "molecule_properties": self.serialize_json(record.get("molecule_properties")),
        "molecule_structures": self.serialize_json(record.get("molecule_structures")),
        "molecule_synonyms": self.serialize_json(record.get("molecule_synonyms")),
        "cross_references": self.serialize_json(record.get("cross_references")),
        "atc_classifications": self.serialize_json(record.get("atc_classifications")),
    }
```

**Станет:**
```python
JSON_FIELDS = (
    "molecule_hierarchy",
    "molecule_properties",
    "molecule_structures",
    "molecule_synonyms",
    "cross_references",
    "atc_classifications",
)

def _map_complex_fields(self, record):
    return self.serialize_json_fields(record, JSON_FIELDS)
```

**Результат Фазы 3:**
- Сокращение: ~20 LOC repetition
- Консистентный API для JSON полей

---

## Матрица Воздействия

| Фаза | LOC Сокращение | Файлы | Риск | Приоритет |
|------|----------------|-------|------|-----------|
| **1. Config Templates** | ~450 LOC (75%) | 11 YAML + 1 loader | Низкий | 🔴 HIGH |
| **2. Field Specs** | ~250 LOC (62%) | 8 transformers + 1 new | Средний | 🟠 MEDIUM |
| **3. JSON Helper** | ~15 LOC | 3 transformers + 1 base | Низкий | 🟢 LOW |

**Суммарно:** ~715 LOC сокращение (65% от дублирования)

---

## Критерии Приёмки

### Фаза 1
- [ ] `_defaults.yaml` содержит все общие настройки
- [ ] Все 11 конфигов используют anchors/aliases
- [ ] `ConfigLoader` поддерживает `_include`
- [ ] `make test` проходит
- [ ] Ни один существующий конфиг не ломается

### Фаза 2
- [ ] `field_specs.py` создан с полным API
- [ ] Минимум 3 трансформера рефакторены
- [ ] Unit тесты для `map_fields()`, `map_field_group()`
- [ ] Backward compatibility сохранена

### Фаза 3
- [ ] `serialize_json_fields()` добавлен в `BaseTransformer`
- [ ] Трансформеры с JSON полями обновлены
- [ ] Документация обновлена

---

## Риски и Митигация

| Риск | Вероятность | Митигация |
|------|-------------|-----------|
| YAML anchors не работают cross-file | Средняя | Fallback на inline defaults или OmegaConf |
| Breaking change в конфигах | Низкая | Feature flag + migration script |
| FieldSpec слишком сложен | Низкая | Начать с 1 трансформера, итерировать |

---

## Порядок Выполнения

```
┌─────────────────────────────────────────────────────────────────┐
│              Фаза 1: Config Templates (2-3 часа)                │
├─────────────────────────────────────────────────────────────────┤
│  1.1 Создать _defaults.yaml                                     │
│  1.2 Обновить ConfigLoader                                      │
│  1.3 Мигрировать 1 конфиг (activity.yaml) как proof-of-concept  │
│  1.4 Мигрировать остальные конфиги                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              Фаза 2: Field Specs (3-4 часа)                     │
├─────────────────────────────────────────────────────────────────┤
│  2.1 Создать field_specs.py                                     │
│  2.2 Добавить тесты                                             │
│  2.3 Рефакторить ActivityTransformer                            │
│  2.4 Рефакторить MoleculeTransformer                            │
│  2.5 Рефакторить AssayTransformer                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              Фаза 3: JSON Helper (1 час)                        │
├─────────────────────────────────────────────────────────────────┤
│  3.1 Добавить serialize_json_fields()                           │
│  3.2 Обновить трансформеры                                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Связанные Документы

- `docs/refactoring-plan.md` — Основной план рефакторинга
- `CLAUDE.md` §2.3 — Архитектурные пояснения
- `docs/RULES.md` §7 — Протокол архитектурных обзоров

---

*Строй надёжно. Верифицируй перед рефакторингом.*
