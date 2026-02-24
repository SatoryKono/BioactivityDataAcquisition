# План унификации нормализации данных

*Дата: 2026-02-16 | Статус: PROPOSAL*

---

## Контекст

Анализ (`data-normalization-comparison.md`) выявил несогласованности в нормализации одинаковых данных между пайплайнами. В проекте уже есть инфраструктура для унификации:
- `PublicationBaseSchema` — базовая схема для публикаций (5 провайдеров)
- Value Objects: `DOI`, `InChIKey`, `SMILES`, `MolecularWeight`, `PublicationYear`, `PubMedId`
- Composite pipeline configs (`publication.yaml`, `molecule.yaml`) с `field_priorities`
- `ColumnRenamer` / `ColumnOrderer` для qualified column naming
- `FieldSpec` DSL для декларативного маппинга

Но остаются **системные пробелы**, описанные ниже.

---

## Проблема 1: Разные имена для одинаковых полей (Molecule)

ChEMBL и PubChem используют разные имена для идентичных свойств.

| Свойство | ChEMBL | PubChem | Каноническое (предлагаемое) |
|---|---|---|---|
| H-bond acceptors | `hba_count` | `h_bond_acceptor_count` | `hba_count` |
| H-bond donors | `hbd_count` | `h_bond_donor_count` | `hbd_count` |
| Polar surface area | `polar_surface_area` | `tpsa` | `polar_surface_area` |
| LogP | `logp` | `xlogp` | `logp` |
| InChI | `standard_inchi` | `inchi` | `standard_inchi` |

**Текущее состояние:** composite/molecule.yaml использует `field_priorities` с каноническими именами ChEMBL (например, `hba_count`), но PubChem-трансформер выдаёт `h_bond_acceptor_count`. Merger должен знать алиасы.

### Предложение: RF-NORM-01 — Canonical Field Alias Registry

**Что:** Создать реестр алиасов полей в domain-слое.

**Где:** `src/bioetl/domain/registry/field_aliases.py`

```python
@dataclass(frozen=True)
class FieldAlias:
    canonical_name: str          # Каноническое имя (используется в Gold)
    provider_aliases: dict[str, str]  # {provider: provider_field_name}
    description: str

MOLECULE_FIELD_ALIASES: tuple[FieldAlias, ...] = (
    FieldAlias(
        canonical_name="hba_count",
        provider_aliases={"chembl": "hba_count", "pubchem": "h_bond_acceptor_count"},
        description="Hydrogen bond acceptor count",
    ),
    FieldAlias(
        canonical_name="hbd_count",
        provider_aliases={"chembl": "hbd_count", "pubchem": "h_bond_donor_count"},
        description="Hydrogen bond donor count",
    ),
    FieldAlias(
        canonical_name="polar_surface_area",
        provider_aliases={"chembl": "polar_surface_area", "pubchem": "tpsa"},
        description="Topological polar surface area (Å²)",
    ),
    FieldAlias(
        canonical_name="logp",
        provider_aliases={"chembl": "logp", "pubchem": "xlogp"},
        description="Octanol-water partition coefficient",
    ),
    FieldAlias(
        canonical_name="standard_inchi",
        provider_aliases={"chembl": "standard_inchi", "pubchem": "inchi"},
        description="Standard IUPAC InChI identifier",
    ),
)
```

**Интеграция:**
- `ColumnRenamer` использует алиасы при rename в qualified format
- Composite merger использует алиасы для join и conflict resolution
- Gold-схема использует только канонические имена

**Затрагивает:**
- `src/bioetl/domain/registry/field_aliases.py` (новый)
- `src/bioetl/application/composite/column_renamer.py` (расширить)
- `configs/pipelines/composite/molecule.yaml` (добавить секцию `field_aliases`)

---

## Проблема 2: Разные bounds для одинаковых полей

| Поле | ChEMBL | PubChem | Расхождение |
|---|---|---|---|
| `molecular_weight` | без bounds | [0, 100 000] | ChEMBL не ограничивает |
| `hba_count` | ge=0 | [0, 50] | ChEMBL без верхней границы |
| `hbd_count` | ge=0 | [0, 50] | ChEMBL без верхней границы |
| `rotatable_bond_count` | ge=0 | [0, 100] | ChEMBL без верхней границы |
| `heavy_atom_count` | ge=0 | [1, 500] | ChEMBL допускает 0 |
| `logp` | без bounds | [-20, 20] | ChEMBL не ограничивает |
| `canonical_smiles` | без ограничений | max 10 000 chars | ChEMBL без лимита длины |

### Предложение: RF-NORM-02 — Unified Validation Bounds

**Что:** Определить канонические bounds для shared fields в domain-слое. Эти bounds — **объединение** (union) допустимых диапазонов, с учётом химического смысла.

**Где:** `src/bioetl/domain/schemas/constants.py` (расширить)

```python
# === Canonical Validation Bounds (для Gold / composite слоя) ===
# Объединяет bounds ChEMBL и PubChem с учётом химического смысла

CANONICAL_MOLECULAR_WEIGHT_RANGE = (0.0, 100_000.0)    # Da
CANONICAL_HBA_COUNT_RANGE = (0, 200)                     # Relaxed for biologics
CANONICAL_HBD_COUNT_RANGE = (0, 200)                     # Relaxed for biologics
CANONICAL_ROTATABLE_BOND_COUNT_RANGE = (0, 500)          # Large molecules
CANONICAL_HEAVY_ATOM_COUNT_RANGE = (0, 2000)             # Biologics
CANONICAL_LOGP_RANGE = (-30.0, 30.0)                     # Extended for edge cases
CANONICAL_POLAR_SURFACE_AREA_RANGE = (0.0, 5000.0)       # Large molecules
CANONICAL_SMILES_MAX_LENGTH = 20_000                     # Extended for biologics
```

**Действие:**
1. Provider-specific schemes **оставить как есть** (Silver-уровень — валидация по источнику)
2. Canonical bounds применять **только в Gold / composite схемах** — unified validation
3. DQ-правила в `configs/quality/entities/composite/` используют canonical bounds

**Затрагивает:**
- `src/bioetl/domain/schemas/constants.py` (добавить секцию)
- Gold-схемы composite entities (использовать canonical bounds)
- `configs/pipelines/composite/molecule.yaml` → `dq_overrides.field_validations`

---

## Проблема 3: Отсутствует MoleculeBaseSchema

Publications унифицированы через `PublicationBaseSchema`. Для molecules такой базы нет — каждый провайдер определяет свою схему независимо.

### Предложение: RF-NORM-03 — MoleculeBaseSchema

**Что:** Создать `MoleculeBaseSchema` с общими полями для ChEMBL и PubChem.

**Где:** `src/bioetl/domain/schemas/common/molecule_base.py`

```python
class MoleculeBaseSchema(ETLRecordSchema):
    """Base schema with common fields for molecule/compound entities."""

    # === Structural Identifiers ===
    molecule_id: Series[str] = pa.Field(nullable=False)
    canonical_smiles: Series[str] | None = pa.Field(nullable=True)
    inchi_key: Series[str] | None = pa.Field(
        nullable=True, str_matches=INCHI_KEY_REGEX_PATTERN,
    )
    molecular_formula: Series[str] | None = pa.Field(nullable=True)

    # === Physicochemical Properties (canonical names) ===
    molecular_weight: Series[float] | None = pa.Field(nullable=True, ge=0)
    hba_count: Series[int] | None = pa.Field(nullable=True, ge=0)
    hbd_count: Series[int] | None = pa.Field(nullable=True, ge=0)
    rotatable_bond_count: Series[int] | None = pa.Field(nullable=True, ge=0)
    polar_surface_area: Series[float] | None = pa.Field(nullable=True, ge=0)
    heavy_atom_count: Series[int] | None = pa.Field(nullable=True, ge=0)
    logp: Series[float] | None = pa.Field(nullable=True)
```

**Действие:**
1. Оба провайдера наследуют `MoleculeBaseSchema`
2. Каждый **переопределяет** bounds (PubChem — stricter, ChEMBL — laxer)
3. PubChem-трансформер переименовывает поля в канонические (tpsa → polar_surface_area и т.д.)
4. Или оставляет provider-specific имена, а rename делает `ColumnRenamer` через алиасы

**Варианты реализации:**

**Вариант A — Rename в трансформере** (PubChem transformer рenames при выходе из Bronze→Silver):
- Плюс: Silver-данные сразу в каноническом формате
- Минус: теряется информация о source field naming
- Требует: изменить PubChem transformer + schema

**Вариант B — Rename в merger** (через FieldAlias registry из RF-NORM-01):
- Плюс: Silver сохраняет provider-native имена (auditability)
- Минус: сложнее — merger должен знать алиасы
- Текущий подход: composite YAML уже имеет `field_priorities` с unified именами

**Рекомендация: Вариант B** — rename в merger, Silver остаётся provider-native. Это лучше для auditability и lineage tracking.

**Затрагивает:**
- `src/bioetl/domain/schemas/common/molecule_base.py` (новый)
- При варианте A: PubChem schema + transformer (refactor)
- При варианте B: `field_aliases.py` + `column_renamer.py`

---

## Проблема 4: Непоследовательная нормализация контента (Publications)

| Операция | PubMed | CrossRef | OpenAlex | S2 | ChEMBL |
|---|---|---|---|---|---|
| `strip_html_tags()` для title | Да | Нет | Нет | Нет | Нет |
| `strip_html_tags()` для abstract | Да | Нет | Нет | Нет | — |
| `parse_page_range()` | Да | Да | Нет | Нет | Нет |
| End-of-period date normalization | Нет | Да | Нет | Нет | Нет |

### Предложение: RF-NORM-04 — Uniform Content Normalization

**Что:** Поднять общую нормализацию контентных полей в `BasePublicationTransformer`.

**Где:** `src/bioetl/application/core/base_publication_transformer.py` (или расширить существующий)

```python
class BasePublicationTransformer(BaseTransformer):
    """Common normalization for all publication transformers."""

    def _normalize_content_fields(self, record: dict) -> dict:
        """Apply uniform normalization to content fields."""
        # 1. Title: strip HTML tags if present
        if "title" in record and record["title"]:
            record["title"] = strip_html_tags(record["title"])

        # 2. Abstract: strip HTML tags if present
        if "abstract" in record and record["abstract"]:
            record["abstract"] = strip_html_tags(record["abstract"])

        # 3. Page range: parse and expand abbreviations
        if "page_range" in record or "pages" in record:
            raw = record.get("page_range") or record.get("pages")
            first, last = parse_page_range(raw)
            record["page_first"] = first
            record["page_last"] = last

        return record
```

**Принцип:** `strip_html_tags()` — идемпотентная операция. На чистом тексте (без тегов) она ничего не меняет. Безопасно применять ко всем провайдерам.

**Затрагивает:**
- Base publication transformer (расширить или создать)
- CrossRef, OpenAlex, S2 transformers — вызвать `_normalize_content_fields()`
- Тесты: проверить идемпотентность на чистом тексте

---

## Проблема 5: Отсутствуют Value Objects для shared molecular fields

Есть Value Objects для `DOI`, `InChIKey`, `SMILES`, `MolecularWeight`, `PublicationYear`, `PubMedId`. Нет для count-полей, которые часто встречаются в обоих пайплайнах.

### Предложение: RF-NORM-05 — Value Objects для molecular counts

**Что:** Создать Value Objects для shared molecular descriptor fields.

**Где:** `src/bioetl/domain/value_objects/molecular_descriptors.py`

```python
class HydrogenBondCount(ValueObject[int]):
    """H-bond donor or acceptor count. Range: [0, 200]."""

class RotatableBondCount(ValueObject[int]):
    """Rotatable bond count. Range: [0, 500]."""

class HeavyAtomCount(ValueObject[int]):
    """Non-hydrogen atom count. Range: [0, 2000]."""

class PolarSurfaceArea(ValueObject[float]):
    """Topological polar surface area (Å²). Range: [0, 5000]."""

class LogP(ValueObject[float]):
    """Octanol-water partition coefficient. Range: [-30, 30]."""
```

**Применение:**
- Трансформеры: `self.validate_value_object(HeavyAtomCount, value)`
- Единая точка валидации для обоих провайдеров
- Canonical bounds из RF-NORM-02

**Приоритет:** MEDIUM. Текущие `safe_int()` + Pandera bounds работают. Value Objects добавят семантику и единую точку изменения bounds.

**Затрагивает:**
- `src/bioetl/domain/value_objects/molecular_descriptors.py` (новый)
- ChEMBL molecule transformer (опционально — использовать VO)
- PubChem transformer (опционально)

---

## Проблема 6: Несогласованность nullable int стратегий

PubChem использует `pd.Int64Dtype` (nullable integer), ChEMBL — `Series[int] | None` (coerced). Оба рабочие, но создают разные pandas dtypes в Silver.

### Предложение: RF-NORM-06 — Unified Nullable Int Strategy

**Что:** Стандартизировать на `pd.Int64Dtype` для всех nullable integer полей.

**Обоснование:**
- `pd.Int64Dtype` — modern pandas nullable integer (рекомендация pandas 2.x)
- Предотвращает int→float coercion (классическая pandas проблема: `[1, None]` → `[1.0, NaN]`)
- Уже используется в `PublicationBaseSchema` (publication_year, citations_received и т.д.)
- PubChem уже на `Int64Dtype`

**Затрагивает:**
- `src/bioetl/domain/schemas/chembl/molecule.py` (заменить `Series[int] | None` → `Series[pd.Int64Dtype] | None`)
- `src/bioetl/domain/schemas/chembl/activity.py` (аналогично)
- Другие ChEMBL schemas с nullable int полями
- Pandera coerce=True уже обеспечивает обратную совместимость

**Приоритет:** LOW. Pandera coerce=True маскирует различия. Но для consistency и правильных dtypes в Delta Lake стоит привести в порядок.

---

## Проблема 7: InChI prefix валидация только в PubChem

PubChem валидирует `inchi.startswith("InChI=")`, ChEMBL — нет.

### Предложение: RF-NORM-07 — InChI Value Object

**Что:** Создать `InChI` Value Object (аналогично `InChIKey`).

**Где:** `src/bioetl/domain/value_objects/chemical.py`

```python
class InChI(ValueObject[str]):
    """IUPAC InChI identifier.

    Invariants:
        - Must start with "InChI="
        - Normalized by stripping whitespace
    """
    def _validate(self, value: str) -> str:
        normalized = value.strip()
        if not normalized.startswith("InChI="):
            raise ValueError(f"InChI must start with 'InChI=': {value!r}")
        return normalized
```

**Затрагивает:**
- `src/bioetl/domain/value_objects/chemical.py` (добавить класс)
- ChEMBL molecule transformer (использовать `validate_value_object(InChI, ...)`)
- ChEMBL molecule schema (добавить `str_startswith="InChI="`)

---

## Сводка: порядок реализации

| # | Задача | Приоритет | Effort | Зависит от |
|---|---|---|---|---|
| **RF-NORM-01** | Canonical Field Alias Registry | HIGH | M | — |
| **RF-NORM-02** | Unified Validation Bounds | HIGH | S | — |
| **RF-NORM-03** | MoleculeBaseSchema (вариант B — rename в merger) | HIGH | L | RF-NORM-01 |
| **RF-NORM-04** | Uniform Content Normalization (publications) | MEDIUM | M | — |
| **RF-NORM-05** | Value Objects для molecular descriptors | MEDIUM | M | RF-NORM-02 |
| **RF-NORM-06** | Unified Nullable Int Strategy | LOW | M | — |
| **RF-NORM-07** | InChI Value Object | LOW | S | — |

**Effort:** S = 1-2 файла, M = 3-5 файлов, L = 6+ файлов

### Рекомендуемая последовательность

```
Phase 1 (Foundation):
  RF-NORM-02 → RF-NORM-01 → RF-NORM-07

Phase 2 (Molecule Unification):
  RF-NORM-03 → RF-NORM-05

Phase 3 (Publication Cleanup):
  RF-NORM-04

Phase 4 (Polish):
  RF-NORM-06
```

---

## Архитектурные принципы

1. **Silver = provider-native** — Silver-схемы сохраняют оригинальные имена и bounds провайдера (auditability, lineage)
2. **Gold = canonical** — Gold/composite-схемы используют канонические имена и unified bounds
3. **Rename в merger, не в transformer** — трансформеры остаются provider-specific, унификация — в composite слое
4. **Value Objects — single source of truth** — валидация bounds через VO, не дублировать в schemas
5. **Идемпотентная нормализация** — `strip_html_tags()`, `normalize_doi()` безопасны для повторного применения
6. **Обратная совместимость** — все изменения через расширение, не ломать существующие Silver-таблицы
