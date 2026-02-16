# Plan: Перенос ChEMBL enum-констант в YAML (ADR-035)

## Проблема

Значения из ChEMBL Database (EBI) определены в трёх местах:

1. **Python frozensets** в `domain/schemas/constants.py` — используются в Pandera-схемах (`isin=list(...)`)
2. **YAML filter configs** в `configs/filters/entities/chembl/*.yaml` — хардкод подмножеств тех же значений
3. **YAML DQ configs** в `configs/quality/entities/chembl/*.yaml` — хардкод `allowed:` списков

Нет единого источника правды (SSOT). Обновление ChEMBL DB (новая версия) требует правок в 3+ местах.

## Scope: что переносим

Только **ChEMBL-специфичные** frozensets/tuples из `constants.py`:

| Константа | Текущий тип | Потребители |
|-----------|-------------|-------------|
| `STANDARD_RELATIONS` | frozenset[str] | activity.py, assay_parameters.py |
| `ACTIVITY_STANDARD_TYPES` | frozenset[str] | activity.py |
| `ASSAY_PARAMETER_STANDARD_TYPES` | frozenset[str] | assay_parameters.py |
| `DATA_VALIDITY_COMMENTS` | frozenset[str] | activity.py |
| `ASSAY_TYPES` | frozenset[str] | assay.py |
| `ASSAY_TEST_TYPES` | frozenset[str] | assay.py |
| `ASSAY_CATEGORIES` | frozenset[str] | assay.py |
| `RELATIONSHIP_TYPES` | frozenset[str] | assay.py |
| `MOLECULE_TYPES` | frozenset[str] | molecule.py |
| `STRUCTURE_TYPES` | frozenset[str] | molecule.py |
| `MAX_PHASE_VALUES` | tuple[float] | molecule.py |
| `TARGET_TYPES` | frozenset[str] | target.py |
| `TARGET_COMPONENT_RELATIONSHIPS` | frozenset[str] | (unused in schemas) |
| `PUBLICATION_TYPES` | frozenset[str] | publication.py |

**НЕ переносим:** regex-паттерны (`CHEMBL_ID_PATTERN`, `BAO_ID_PATTERN`, etc.) — они привязаны к формату, а не к ChEMBL DB версии.

## Ключевое ограничение

Pandera `pa.Field(isin=...)` исполняется **на уровне определения класса** (module load time). Это значит:

```python
class ActivitySchema(ETLRecordSchema):
    standard_type = pa.Field(isin=list(ACTIVITY_STANDARD_TYPES))  # ← вызывается при import
```

Любое решение должно **предоставить значения до момента импорта модуля схемы** — либо:
- (A) Загрузить YAML синхронно при первом импорте (eager)
- (B) Отказаться от class-level isin и перейти на runtime-валидацию (lazy)
- (C) Генерировать Python из YAML (build-time codegen)

## Предлагаемый подход: Вариант A — YAML как SSOT + eager load

Следуем паттерну ADR-027/ADR-028 (hierarchical config), но с одним отличием: значения загружаются **при первом импорте** constants-модуля, а не через DI.

### Обоснование выбора варианта A

| Критерий | A (eager load) | B (lazy/runtime) | C (codegen) |
|----------|----------------|-------------------|-------------|
| Совместимость с Pandera class-level isin | Нативная | Требует переписать все схемы | Нативная |
| Единый SSOT | YAML файл | YAML файл | YAML файл → Python |
| Complexity | Низкая | Высокая | Средняя (нужен build step) |
| Domain purity | Допустимо (файл-read в constants init) | Чистый domain | Чистый domain |
| IDE support | Полный (значения доступны после import) | Ограничен | Полный |
| Нарушает ли ARCH-002 | Нет — schemas не в domain/types, а в domain/schemas (отдельный модуль utility) | — | — |

**Компромисс:** Один `yaml.safe_load()` при import — это не I/O в бизнес-логике, а инициализация справочника. Аналог: Django settings загружаются при старте. Модуль `domain/schemas/` уже зависит от Pandera (внешняя библиотека).

---

## Пошаговый план

### Phase 1: Создать YAML enum-файлы

**Шаг 1.1:** Создать структуру

```
configs/enums/
├── _schema.yaml              # JSON Schema / описание формата
└── chembl.yaml               # Все ChEMBL DB enum-значения
```

**Шаг 1.2:** `configs/enums/chembl.yaml`

```yaml
# ChEMBL Database Enum Values
# Source: ChEMBL 35 (EBI)
# Last synced: 2026-02-16
#
# Canonical source of truth for all allowed values from ChEMBL DB.
# Used by: Pandera schemas, filter configs, DQ configs.

version: "chembl_35"

activity:
  standard_relations: ["=", "<", "<=", ">", ">="]
  standard_types:
    - IC50
    - EC50
    - Ki
    - Kd
    - AC50
    - GI50
    - Potency
    - Inhibition
    - "% Inhibition"
    - Activity
    - Ratio
    - ED50
    - ID50
  data_validity_comments:
    - "Potential missing data"
    - "Potential author error"
    - "Manually validated"
    - "Potential transcription error"
    - "Outside typical range"
    - "Non standard unit for type"
    - "Author confirmed error"

assay:
  types: ["B", "F", "A", "T", "P", "U"]
  test_types: ["In vivo", "In vitro", "Ex vivo"]
  categories: ["screening", "confirmatory", "panel", "summary", "other"]
  relationship_types: ["D", "H", "M", "N", "S", "U"]
  parameter_standard_types:
    # Inherits from activity.standard_types + parameter-specific
    - CONC
    - PH
    - TEMP
    - TIME
    - DOSE
    - VOLUME
    - WAVELENGTH
    - PERCENT
    - PRESSURE
    - HUMIDITY
    - CELL_COUNT
    - CELL_DENSITY
    - SERUM

molecule:
  types:
    - "Small molecule"
    - "Inorganic small molecule"
    - "Polymeric small molecule"
    - "Antibody"
    - "Antibody drug conjugate"
    - "Protein"
    - "Oligonucleotide"
    - "Oligosaccharide"
    - "Cell"
    - "Enzyme"
    - "Unknown"
    - "Unclassified"
  structure_types: ["MOL", "SEQ", "BOTH", "NONE"]
  max_phase_values: [-1, 0, 0.5, 1, 2, 3, 4]

target:
  types:
    - "SINGLE PROTEIN"
    - "PROTEIN FAMILY"
    - "PROTEIN COMPLEX"
    - "PROTEIN COMPLEX GROUP"
    - "SELECTIVITY GROUP"
    - "CHIMERIC PROTEIN"
    - "CELL-LINE"
    - "TISSUE"
    - "ORGANISM"
    - "MACROMOLECULE"
    - "SMALL MOLECULE"
    - "LIPID"
    - "METAL"
    - "UNKNOWN"
  component_relationships:
    - "SINGLE PROTEIN"
    - "PROTEIN SUBUNIT"
    - "RNA"
    - "INTERACTING PROTEIN"

publication:
  types: ["PUBLICATION", "PATENT", "DATASET", "BOOK"]
```

### Phase 2: Loader в constants.py

**Шаг 2.1:** Добавить в `domain/schemas/constants.py` загрузчик YAML:

```python
"""Centralized constants for schema validation.

Values loaded from configs/enums/chembl.yaml (SSOT).
Regex patterns remain hardcoded (format-dependent, not DB-version-dependent).
"""
from __future__ import annotations

import functools
from pathlib import Path
from typing import Any

import yaml

# ... regex patterns remain as-is ...

# ====================================================================
# ENUM VALUES (loaded from YAML — single source of truth)
# ====================================================================

@functools.cache
def _load_chembl_enums() -> dict[str, Any]:
    """Load ChEMBL enum values from YAML config.

    Cached: loaded once per process, reused on subsequent imports.
    """
    yaml_path = Path(__file__).resolve().parents[4] / "configs" / "enums" / "chembl.yaml"
    with yaml_path.open() as f:
        return yaml.safe_load(f)

def _fs(key1: str, key2: str) -> frozenset[str]:
    """Helper: load a frozenset[str] from nested YAML key."""
    return frozenset(_load_chembl_enums()[key1][key2])

def _tup(key1: str, key2: str) -> tuple[float, ...]:
    """Helper: load a tuple[float] from nested YAML key."""
    return tuple(_load_chembl_enums()[key1][key2])

# Activity
STANDARD_RELATIONS: frozenset[str] = _fs("activity", "standard_relations")
ACTIVITY_STANDARD_TYPES: frozenset[str] = _fs("activity", "standard_types")
DATA_VALIDITY_COMMENTS: frozenset[str] = _fs("activity", "data_validity_comments")

# Assay
ASSAY_TYPES: frozenset[str] = _fs("assay", "types")
ASSAY_TEST_TYPES: frozenset[str] = _fs("assay", "test_types")
ASSAY_CATEGORIES: frozenset[str] = _fs("assay", "categories")
RELATIONSHIP_TYPES: frozenset[str] = _fs("assay", "relationship_types")
ASSAY_PARAMETER_STANDARD_TYPES: frozenset[str] = (
    ACTIVITY_STANDARD_TYPES | _fs("assay", "parameter_standard_types")
)

# Molecule
MOLECULE_TYPES: frozenset[str] = _fs("molecule", "types")
STRUCTURE_TYPES: frozenset[str] = _fs("molecule", "structure_types")
MAX_PHASE_VALUES: tuple[float, ...] = _tup("molecule", "max_phase_values")

# Target
TARGET_TYPES: frozenset[str] = _fs("target", "types")
TARGET_COMPONENT_RELATIONSHIPS: frozenset[str] = _fs("target", "component_relationships")

# Publication
PUBLICATION_TYPES: frozenset[str] = _fs("publication", "types")
```

**Ключевые свойства:**
- Публичный API (`STANDARD_RELATIONS`, etc.) **не меняется** — все потребители работают как раньше
- `@functools.cache` гарантирует одно чтение файла за процесс
- Типы сохраняются: `frozenset[str]`, `tuple[float, ...]`
- `__all__` остаётся без изменений

### Phase 3: Тесты

**Шаг 3.1:** Unit-тест загрузки YAML

```python
# tests/unit/domain/schemas/test_constants_yaml.py

def test_chembl_enums_loaded_from_yaml():
    """Verify constants match YAML file."""
    from bioetl.domain.schemas.constants import (
        ACTIVITY_STANDARD_TYPES,
        ASSAY_TYPES,
        MOLECULE_TYPES,
        STANDARD_RELATIONS,
        TARGET_TYPES,
    )
    assert "IC50" in ACTIVITY_STANDARD_TYPES
    assert "B" in ASSAY_TYPES
    assert "Small molecule" in MOLECULE_TYPES
    assert "=" in STANDARD_RELATIONS
    assert "SINGLE PROTEIN" in TARGET_TYPES

def test_assay_parameter_types_superset():
    """ASSAY_PARAMETER_STANDARD_TYPES is superset of ACTIVITY_STANDARD_TYPES."""
    from bioetl.domain.schemas.constants import (
        ACTIVITY_STANDARD_TYPES,
        ASSAY_PARAMETER_STANDARD_TYPES,
    )
    assert ACTIVITY_STANDARD_TYPES <= ASSAY_PARAMETER_STANDARD_TYPES

def test_yaml_file_exists():
    """Config file must exist at expected path."""
    from pathlib import Path
    yaml_path = Path("configs/enums/chembl.yaml")
    assert yaml_path.exists()
```

**Шаг 3.2:** Consistency-тест: YAML ↔ filter/DQ configs

```python
def test_filter_enum_values_subset_of_yaml():
    """Filter config values must be subsets of YAML enum values."""
    # Загрузить configs/filters/entities/chembl/activity.yaml
    # Проверить что columns.standard_type ⊆ ACTIVITY_STANDARD_TYPES
    # Проверить что columns.assay_type ⊆ ASSAY_TYPES
```

**Шаг 3.3:** Architecture-тест: no hardcoded enums in filter/DQ YAML

Опциональный lint: проверить что filter/DQ YAML не содержат значений вне YAML-enum файла.

### Phase 4: Документация

**Шаг 4.1:** Создать ADR-035

```
docs/02-architecture/decisions/ADR-035-enum-externalization.md
```

Содержание:
- Context: дупликация ChEMBL enum значений в 3 местах
- Decision: YAML как SSOT, eager load в constants.py
- Alternatives: lazy/runtime (B), codegen (C)
- Consequences: +SSOT, +простое обновление ChEMBL версии, -одно file read при import

**Шаг 4.2:** Обновить README/RULES если нужно

### Phase 5: (Опциональная) Cross-reference валидация

Добавить в preflight/DQ check верификацию: значения из filter configs ⊆ значения из `configs/enums/chembl.yaml`. Это поймает опечатки в filter YAML.

---

## Что НЕ входит в план

1. **CrossRef PUBLICATION_TYPES** в `crossref/work.py` — это не ChEMBL, отдельный источник. Можно вынести позже в `configs/enums/crossref.yaml`.
2. **OA_STATUS_VALUES / LOOKUP_METHODS** в `publication_base.py` — это BioETL-internal, не привязаны к ChEMBL DB версии.
3. **Доменные StrEnum** (RunType, HealthStatus, etc.) — это бизнес-логика, не данные из внешней DB.
4. **Regex patterns** — формат-зависимые, не DB-version-зависимые.

## Риски и митигация

| Риск | Вероятность | Митигация |
|------|-------------|-----------|
| YAML-файл не найден при import | Низкая (CI/CD поймает) | Тест `test_yaml_file_exists` + понятный `FileNotFoundError` |
| Рассинхрон YAML ↔ filter/DQ configs | Средняя | Phase 5: consistency test |
| Замедление import | Минимальная (~1ms для YAML parse) | `@functools.cache` + маленький файл (~2KB) |
| Нарушение ARCH-002 (domain purity) | Спорно | `domain/schemas/` — это utility-подмодуль, уже зависит от Pandera. Не бизнес-логика |
| PyPI package без configs/ | Средняя | Добавить `configs/enums/` в `package_data` / `MANIFEST.in` |

## Оценка объёма

| Артефакт | Действие |
|----------|----------|
| `configs/enums/chembl.yaml` | Создать (~80 строк) |
| `domain/schemas/constants.py` | Переписать тело (~60 строк), API без изменений |
| `tests/unit/.../test_constants_yaml.py` | Создать (~40 строк) |
| `ADR-035-enum-externalization.md` | Создать (~80 строк) |
| Pandera-схемы (`activity.py`, `assay.py`, etc.) | **Без изменений** |
| Filter/DQ YAML | **Без изменений** (Phase 5 — опционально) |
