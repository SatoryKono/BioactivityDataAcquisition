# feat(domain): классификация организмов на доклеточные, одноклеточные и многоклеточные

**Метки**: `enhancement`, `layer:domain`, `layer:application`

______________________________________________________________________

## Резюме

Реализовать доменную функцию классификации организмов на три категории клеточности
по входным данным ChEMBL: `assay_organism` (str) и `assay_taxonomy_id` (int).

| Категория         | Значение enum   | Примеры из данных                                                                                  |
| ----------------- | --------------- | -------------------------------------------------------------------------------------------------- |
| **ACELLULAR**     | `acellular`     | HIV (11676), Influenza A (211044), SARS-CoV (694009), phage lambda (10710)                         |
| **UNICELLULAR**   | `unicellular`   | E. coli (562), S. aureus (1280), Plasmodium (5833), Candida albicans (5476), Methanosarcina (2210) |
| **MULTICELLULAR** | `multicellular` | Homo sapiens (9606), Rattus norvegicus (10116), Aspergillus niger (5061), Glycine max (3847)       |

______________________________________________________________________

## Мотивация

1. **Аналитическая ценность**: интерпретация данных биоактивности зависит от биологического контекста организма-мишени. Лекарственные мишени в многоклеточных организмах имеют иное фармакологическое значение, чем бактериальные мишени.
1. **Обогащение данных**: система уже хранит `taxonomy_id` и `organism`, но не имеет производной классификации по клеточности.
1. **Фильтрация и агрегация**: позволяет агрегировать данные на Gold-уровне по типу клеточности (например, «вся биоактивность против одноклеточных организмов»).

______________________________________________________________________

## Входные данные

Данные приходят из **ChEMBL Assay API** как пара полей:

```
assay_organism: str | None    — название организма (может быть грязным)
assay_taxonomy_id: int | None — NCBI Taxonomy ID
```

### Особенности входных данных

1. **Грязные имена организмов** — нестандартные варианты написания:

   - Нижний регистр: `hiv`, `eel`, `rice`, `monkey`, `b.catarr`
   - Штаммы в имени: `Streptococcus pneumoniae TIGR4`, `Enterococcus faecalis V583`
   - Описательные: `human immuno deficiency virus protease`, `mesocricetus auratus (golden hamster)`
   - Опечатки: `Methanobacteriumthermoautotrophicum` (без пробела)

1. **taxonomy_id — основной ключ классификации** (более надёжен чем organism name)

1. **Один и тот же taxonomy_id для разных написаний**:

   - `11676` → `hiv`, `Human immunodeficiency virus 1`, `human immunodeficiency virus`, `human immuno deficiency virus protease`
   - `8005` → `eel`, `Electrophorus electricus`
   - `39947` → `rice`, `Oryza sativa Japonica Group`

1. **ChEMBL НЕ предоставляет lineage** (в отличие от UniProt API). Нет данных о superkingdom/phylum/genus — только organism name + taxonomy_id.

______________________________________________________________________

## Полная матрица классификации из предоставленных данных

### ACELLULAR (Вирусы, фаги — ~25 записей, ~20 уникальных taxonomy_id)

| taxonomy_id | assay_organism                                                                | Примечание         |
| ----------- | ----------------------------------------------------------------------------- | ------------------ |
| 11676       | Human immunodeficiency virus 1 / hiv / human immuno deficiency virus protease | Retrovirus         |
| 11709       | Human immunodeficiency virus 2                                                | Retrovirus         |
| 11679       | Human immunodeficiency virus type 1 (CLONE 12)                                | HIV-1 clone        |
| 11866       | Avian myeloblastosis virus                                                    | Retrovirus         |
| 11926       | human T-cell leukemia virus type 1                                            | Retrovirus         |
| 11970       | Woolly monkey sarcoma virus                                                   | Retrovirus         |
| 211044      | Influenza A virus (A/Puerto Rico/8/1934(H1N1))                                | Orthomyxovirus     |
| 132504      | Influenza A virus (A/X-31(H3N2))                                              | Orthomyxovirus     |
| 169066      | Human rhinovirus sp. / human rhinovirus type 14                               | Picornavirus       |
| 3052230     | Hepacivirus hominis                                                           | Flavivirus (Hep C) |
| 694009      | Severe acute respiratory syndrome-related coronavirus                         | Coronavirus        |
| 10298       | Human alphaherpesvirus 1                                                      | Herpesvirus        |
| 10299       | Herpes simplex virus (type 1 / strain 17)                                     | HSV-1              |
| 10309       | Herpes simplex virus (type 1 / strain SC16) / herpes simplex virus type 1     | HSV-1 strain       |
| 10310       | Human alphaherpesvirus 2                                                      | HSV-2              |
| 10335       | Human alphaherpesvirus 3                                                      | VZV                |
| 10360       | Human herpesvirus 5 strain AD169                                              | CMV                |
| 10580       | human papillomavirus 11                                                       | HPV                |
| 10665       | Tequatrovirus T4                                                              | Бактериофаг        |
| 10710       | Enterobacteria phage lambda                                                   | Бактериофаг        |

### UNICELLULAR — Бактерии (~42 записи, ~40 уникальных taxonomy_id)

| taxonomy_id | assay_organism                       |
| ----------- | ------------------------------------ |
| 232         | Alteromonas sp.                      |
| 271         | Thermus aquaticus                    |
| 274         | Thermus thermophilus                 |
| 287         | Pseudomonas aeruginosa               |
| 294         | Pseudomonas fluorescens              |
| 303         | Pseudomonas putida                   |
| 480         | b.catarr (Moraxella catarrhalis)     |
| 485         | Neisseria gonorrhoeae                |
| 546         | Citrobacter freundii                 |
| 548         | Klebsiella aerogenes                 |
| 550         | Enterobacter cloacae (+ GC1 variant) |
| 562         | Escherichia coli                     |
| 571         | Klebsiella oxytoca                   |
| 573         | Klebsiella pneumoniae                |
| 582         | Morganella morganii                  |
| 584         | Proteus mirabilis                    |
| 585         | Proteus vulgaris                     |
| 615         | Serratia marcescens                  |
| 632         | Yersinia pestis                      |
| 671         | Vibrio proteolyticus                 |
| 817         | Bacteroides fragilis                 |
| 1280        | Staphylococcus aureus                |
| 158878      | Staphylococcus aureus (штамм)        |
| 1313        | Streptococcus pneumoniae             |
| 170187      | Streptococcus pneumoniae TIGR4       |
| 1393        | Brevibacillus brevis                 |
| 1396        | Bacillus cereus                      |
| 1402        | Bacillus licheniformis               |
| 1422        | Geobacillus stearothermophilus       |
| 1423        | Bacillus subtilis                    |
| 1427        | Bacillus thermoproteolyticus         |
| 1467        | Lederbergia lenta                    |
| 1582        | Lacticaseibacillus casei             |
| 1613        | Limosilactobacillus fermentum        |
| 1764        | Mycobacterium avium                  |
| 1773        | Mycobacterium tuberculosis           |
| 13689       | Sphingomonas paucimobilis            |
| 31952       | Streptomyces spp.                    |
| 40324       | Stenotrophomonas maltophilia         |
| 44001       | Caldicellulosiruptor saccharolyticus |
| 226185      | Enterococcus faecalis V583           |

### UNICELLULAR — Археи (~2 уникальных taxonomy_id)

| taxonomy_id | assay_organism                                                               |
| ----------- | ---------------------------------------------------------------------------- |
| 2210        | Methanosarcina thermophila                                                   |
| 187420      | Methanothermobacter thermautotrophicus / Methanobacteriumthermoautotrophicum |

### UNICELLULAR — Одноклеточные эукариоты (протисты + дрожжи, ~15 уникальных taxonomy_id)

| taxonomy_id | assay_organism                 | Группа               |
| ----------- | ------------------------------ | -------------------- |
| 5476        | Candida albicans               | Дрожжи               |
| 870730      | Ogataea angusta                | Дрожжи               |
| 4754        | Pneumocystis carinii           | Гриб (одноклеточный) |
| 5807        | Cryptosporidium parvum         | Apicomplexa          |
| 5811        | Toxoplasma gondii              | Apicomplexa          |
| 5833        | Plasmodium falciparum          | Apicomplexa          |
| 5839        | Plasmodium falciparum K1       | Apicomplexa          |
| 36329       | Plasmodium falciparum 3D7      | Apicomplexa          |
| 5656        | Crithidia fasciculata          | Kinetoplastida       |
| 5664        | Leishmania major               | Kinetoplastida       |
| 5665        | Leishmania mexicana            | Kinetoplastida       |
| 5691        | Trypanosoma brucei             | Kinetoplastida       |
| 31286       | Trypanosoma brucei rhodesiense | Kinetoplastida       |
| 5693        | Trypanosoma cruzi              | Kinetoplastida       |
| 5888        | Paramecium tetraurelia         | Инфузория            |

### MULTICELLULAR — Животные (Metazoa, ~31 уникальный taxonomy_id)

| taxonomy_id | assay_organism                        |
| ----------- | ------------------------------------- |
| 9606        | Homo sapiens                          |
| 10090       | Mus musculus                          |
| 10116       | Rattus norvegicus                     |
| 9913        | Bos taurus                            |
| 9823        | Sus scrofa                            |
| 10141       | Cavia porcellus                       |
| 9593        | Gorilla gorilla                       |
| 9986        | Oryctolagus cuniculus                 |
| 7787        | Torpedo californica                   |
| 8005        | Electrophorus electricus / eel        |
| 9031        | Gallus gallus                         |
| 7957        | Carassius auratus                     |
| 10036       | mesocricetus auratus (golden hamster) |
| 9796        | Equus caballus                        |
| 9615        | Canis lupus familiaris                |
| 10029       | Cricetulus griseus                    |
| 9940        | Ovis aries                            |
| 9534        | Chlorocebus aethiops / monkey         |
| 9541        | Macaca fascicularis                   |
| 9544        | Macaca mulatta                        |
| 7159        | Aedes aegypti                         |
| 7091        | Bombyx mori                           |
| 7141        | Choristoneura fumiferana              |
| 8355        | Xenopus laevis                        |
| 7227        | Drosophila melanogaster               |
| 9103        | Meleagris gallopavo                   |
| 7460        | Apis mellifera                        |
| 7052        | Luciola lateralis                     |
| 8644        | Naja mocambique                       |
| 8643        | Naja melanoleuca                      |
| 40353       | Echis carinatus                       |

### MULTICELLULAR — Растения (Viridiplantae, ~6 уникальных taxonomy_id)

| taxonomy_id | assay_organism                     |
| ----------- | ---------------------------------- |
| 3847        | Glycine max                        |
| 39947       | Oryza sativa Japonica Group / rice |
| 4577        | Zea mays                           |
| 3988        | Ricinus communis                   |
| 3649        | Carica papaya                      |
| 3888        | Pisum sativum                      |

### MULTICELLULAR — Нитчатые грибы (~5 уникальных taxonomy_id)

| taxonomy_id | assay_organism                      |
| ----------- | ----------------------------------- |
| 5061        | Aspergillus niger                   |
| 64495       | Rhizopus arrhizus                   |
| 4843        | Rhizopus microsporus var. chinensis |
| 64493       | Mucor hiemalis                      |
| 5503        | Curvularia lunata                   |

______________________________________________________________________

## Ключевые отличия от первоначального описания

| Аспект                   | Было (первоначальное описание)          | Стало (скорректированное)                                        |
| ------------------------ | --------------------------------------- | ---------------------------------------------------------------- |
| **Входные данные**       | `lineage: list[str]` (UniProt)          | `taxonomy_id: int` + `organism_name: str` (ChEMBL)               |
| **Источник данных**      | UniProt API (предоставляет lineage)     | ChEMBL API (НЕ предоставляет lineage)                            |
| **Место классификатора** | `TaxonomyExtractor` (UniProt-specific)  | Новый `domain/classification/cellularity.py`                     |
| **Подход**               | Парсинг lineage → superkingdom → phylum | Статический маппинг taxonomy_id + fallback по имени              |
| **Scope**                | Только enum + функция                   | Enum + функция + обогащение AssayTransformer                     |
| **Грибы**                | Общее правило по phylum                 | Дифференцировано: дрожжи → UNICELLULAR, нитчатые → MULTICELLULAR |

______________________________________________________________________

## Проектные решения

### 1. `CellularityType` StrEnum в `src/bioetl/domain/types.py`

```python
class CellularityType(StrEnum):
    """Organism cellularity classification."""

    ACELLULAR = "acellular"
    UNICELLULAR = "unicellular"
    MULTICELLULAR = "multicellular"
```

По аналогии с существующими `RunType`, `HealthStatus`, `PublicationType`.

### 2. Подход: статический маппинг taxonomy_id (НЕ lineage)

**Почему НЕ TaxonomyExtractor**: `TaxonomyExtractor` работает с `organism.lineage` из UniProt API.
ChEMBL не предоставляет lineage — только `assay_organism` (str) + `assay_taxonomy_id` (int).
Поэтому нужен отдельный классификатор.

**Двухуровневая классификация:**

- **Tier 1 (primary)**: Статическое отображение `taxonomy_id → CellularityType` для всех ~100 известных taxonomy_id из датасета. Хранится как `frozenset` по категориям.
- **Tier 2 (fallback)**: Ключевые слова в `organism_name` для неизвестных taxonomy_id (e.g. "virus", "phage", "bacterium").
- **Default**: `None` для неклассифицируемых (AP-004: без sentinel values).

```python
# domain/classification/cellularity.py

_ACELLULAR_TAX_IDS: frozenset[int] = frozenset({11676, 11709, 10665, 10710, ...})
_UNICELLULAR_TAX_IDS: frozenset[int] = frozenset({562, 1280, 5833, 2210, ...})
_MULTICELLULAR_TAX_IDS: frozenset[int] = frozenset({9606, 10090, 5061, 3847, ...})

_ACELLULAR_KEYWORDS = ("virus", "phage", "viroid", "prion")
_UNICELLULAR_KEYWORDS = ("bacillus", "coccus", "monas", "bacterium", "mycobacterium")


def classify_cellularity(
    taxonomy_id: int | None,
    organism_name: str | None = None,
) -> CellularityType | None:
    """Classify organism by cellularity.

    Tier 1: taxonomy_id lookup (primary)
    Tier 2: organism_name keywords (fallback)
    Returns None for unclassifiable organisms.
    """
```

### 3. Размещение в архитектуре

| Компонент                | Файл                                              | Слой                            |
| ------------------------ | ------------------------------------------------- | ------------------------------- |
| `CellularityType` enum   | `src/bioetl/domain/types.py`                      | domain                          |
| `classify_cellularity()` | `src/bioetl/domain/classification/cellularity.py` | domain (чистая логика, без I/O) |
| Маппинг taxonomy_id      | В том же модуле, как `frozenset` константы        | domain                          |

> Domain layer допустим, т.к. классификатор — чистая функция без I/O (ARCH-002).

### 4. Обогащение в AssayTransformer

```python
# В AssayTransformer._extract_business_data():
from bioetl.domain.classification.cellularity import classify_cellularity

business_data["assay_cellularity"] = classify_cellularity(
    taxonomy_id=business_data.get("assay_taxonomy_id"),
    organism_name=business_data.get("assay_organism"),
)
```

______________________________________________________________________

## Пограничные случаи (Edge Cases)

| Случай                                         | taxonomy_id           | Решение                  | Обоснование                                      |
| ---------------------------------------------- | --------------------- | ------------------------ | ------------------------------------------------ |
| Дрожжи (Candida, Ogataea)                      | 5476, 870730          | UNICELLULAR              | Одноклеточные грибы                              |
| Нитчатые грибы (Aspergillus, Rhizopus, Mucor)  | 5061, 64495, 64493    | MULTICELLULAR            | Многоклеточные мицелиальные организмы            |
| Бактериофаги (T4, lambda)                      | 10665, 10710          | ACELLULAR                | Вирусы бактерий — не имеют клеточной организации |
| Археи (Methanosarcina)                         | 2210, 187420          | UNICELLULAR              | Одноклеточные прокариоты                         |
| Протисты (Plasmodium, Trypanosoma, Leishmania) | 5833, 5693, 5664      | UNICELLULAR              | Одноклеточные эукариоты                          |
| Инфузории (Paramecium)                         | 5888                  | UNICELLULAR              | Одноклеточные эукариоты                          |
| Грязные имена (`b.catarr`, `hiv`)              | 480, 11676            | Корректно по taxonomy_id | taxonomy_id — primary key                        |
| Один taxonomy_id — разные имена                | 11676 → hiv/HIV-1/... | Одинаковый результат     | taxonomy_id-based                                |
| `taxonomy_id=None`, `organism_name=None`       | —                     | `None`                   | Нет данных для классификации                     |
| Неизвестный taxonomy_id + имя с "virus"        | ???                   | ACELLULAR                | Fallback по Tier 2                               |
| `Pneumocystis carinii` (4754)                  | 4754                  | UNICELLULAR              | Атипичный гриб, одноклеточная форма              |

______________________________________________________________________

## Scope первой итерации

| Что делаем                                        | Что НЕ делаем                                               |
| ------------------------------------------------- | ----------------------------------------------------------- |
| `CellularityType` enum в domain/types.py          | Не трогаем TaxonomyExtractor (UniProt-specific)             |
| `classify_cellularity()` в domain/classification/ | Не добавляем внешние API (NCBI Taxonomy)                    |
| Маппинг для ~100 taxonomy_id из данных            | Не расширяем маппинг за пределы датасета                    |
| Обогащение `assay_cellularity` в AssayTransformer | Не обогащаем target/cell_line/activity (следующая итерация) |
| Silver schema: `assay_cellularity` поле           | Не меняем Gold schema (следующая итерация)                  |
| Unit тесты для classify_cellularity               | Не делаем integration тесты                                 |

______________________________________________________________________

## Затрагиваемые файлы

| Файл                                                           | Действие | Описание                                             |
| -------------------------------------------------------------- | -------- | ---------------------------------------------------- |
| `src/bioetl/domain/types.py`                                   | EDIT     | Добавить `CellularityType` StrEnum                   |
| `src/bioetl/domain/classification/__init__.py`                 | CREATE   | Новый пакет                                          |
| `src/bioetl/domain/classification/cellularity.py`              | CREATE   | `classify_cellularity()` + маппинг ~100 taxonomy_id  |
| `src/bioetl/application/pipelines/chembl/assay_transformer.py` | EDIT     | Вызов classify_cellularity в \_extract_business_data |
| `src/bioetl/domain/schemas/chembl/assay.py`                    | EDIT     | Поле \`assay_cellularity: Series[str]                |
| `src/bioetl/infrastructure/schemas/silver.py`                  | EDIT     | Поле `assay_cellularity` в Silver Arrow schema       |
| `tests/unit/domain/classification/test_cellularity.py`         | CREATE   | Unit тесты                                           |

______________________________________________________________________

## Связанный существующий код

| Компонент                 | Файл                                                   | Релевантность                                    |
| ------------------------- | ------------------------------------------------------ | ------------------------------------------------ |
| `TaxonomyId` value object | `domain/value_objects/taxonomy_id.py`                  | Валидация taxonomy_id (переиспользуем)           |
| `TaxonomyExtractor`       | `application/pipelines/uniprot/extractors/taxonomy.py` | Только для UniProt lineage, НЕ трогаем           |
| `AssayTransformer`        | `application/pipelines/chembl/assay_transformer.py`    | Точка интеграции classifiy_cellularity           |
| `validate_taxonomy_id()`  | `domain/value_objects/taxonomy_id.py`                  | Используется в AssayTransformer для assay_tax_id |
| Assay entity (Pydantic)   | `domain/entities/chembl.py:197-287`                    | Поля `assay_organism`, `assay_tax_id`            |
| Assay entity (dataclass)  | `domain/entities/chembl_activity.py:29-100`            | Поля `assay_organism`, `assay_taxonomy_id`       |
| Gold Assay schema         | `domain/contracts/gold/chembl.py:147-204`              | Следующая итерация                               |

______________________________________________________________________

## Критерии приёмки (Acceptance Criteria)

- [ ] `CellularityType` enum в `domain/types.py` с 3 значениями
- [ ] `classify_cellularity(taxonomy_id, organism_name)` корректно классифицирует все ~100 taxonomy_id из предоставленных данных
- [ ] Дрожжи (Candida 5476, Ogataea 870730) → UNICELLULAR
- [ ] Нитчатые грибы (Aspergillus 5061, Rhizopus 64495) → MULTICELLULAR
- [ ] Вирусы (HIV 11676, phage lambda 10710) → ACELLULAR
- [ ] Бактерии (E. coli 562) и археи (Methanosarcina 2210) → UNICELLULAR
- [ ] `None` при `taxonomy_id=None` и `organism_name=None`
- [ ] Fallback по organism_name работает для имён с "virus", "phage"
- [ ] `AssayTransformer` обогащает Silver record полем `assay_cellularity`
- [ ] Silver schema содержит `assay_cellularity` поле
- [ ] Архитектурные тесты проходят (ARCH-001 матрица импортов)
- [ ] Unit тесты покрывают все категории + edge cases
- [ ] mypy --strict проходит

### Матрица тест-кейсов

| Input taxonomy_id | Input organism_name              | Expected      | Комментарий                 |
| ----------------- | -------------------------------- | ------------- | --------------------------- |
| 9606              | `Homo sapiens`                   | MULTICELLULAR | Человек                     |
| 562               | `Escherichia coli`               | UNICELLULAR   | Бактерия                    |
| 11676             | `hiv`                            | ACELLULAR     | Вирус, грязное имя          |
| 11676             | `Human immunodeficiency virus 1` | ACELLULAR     | Вирус, полное имя           |
| 5476              | `Candida albicans`               | UNICELLULAR   | Дрожжи (одноклеточный гриб) |
| 5061              | `Aspergillus niger`              | MULTICELLULAR | Нитчатый гриб               |
| 2210              | `Methanosarcina thermophila`     | UNICELLULAR   | Архея                       |
| 5833              | `Plasmodium falciparum`          | UNICELLULAR   | Протист (Apicomplexa)       |
| 10665             | `Tequatrovirus T4`               | ACELLULAR     | Бактериофаг                 |
| 5888              | `Paramecium tetraurelia`         | UNICELLULAR   | Инфузория                   |
| 3847              | `Glycine max`                    | MULTICELLULAR | Растение                    |
| None              | None                             | None          | Нет данных                  |
| None              | `some unknown virus strain`      | ACELLULAR     | Fallback Tier 2             |
| None              | `unknown organism`               | None          | Неклассифицируемый          |
| 999999            | None                             | None          | Неизвестный taxonomy_id     |

______________________________________________________________________

## Архитектурные ограничения

- **Domain purity**: Классификатор НЕ ДОЛЖЕН выполнять I/O (ARCH-002)
- **Import boundaries**: Следовать ARCH-001 матрице; domain не импортирует из infrastructure
- **Naming**: Enum values MUST быть UPPER_SNAKE_CASE (NAME-006); функция SHOULD использовать `classify_*` prefix (NAME-002)
- **DI**: Нет hardcoded dependencies (DI-001); lookup tables — чистые данные, не зависимости
- **Ports facade**: Если нужны новые порты, импорт из `bioetl.domain.ports` (ARCH-008)

______________________________________________________________________

## Вне scope

- Интеграция NCBI Taxonomy API (получение lineage в runtime) — отдельная задача
- Обновление Gold schemas для включения cellularity — следующая итерация
- Обогащение target/cell_line/activity трансформеров — следующая итерация
- Расширение маппинга за пределы предоставленного датасета — по мере необходимости

______________________________________________________________________

## Ссылки

- [NCBI Taxonomy Browser](https://www.ncbi.nlm.nih.gov/taxonomy)
- Domain types: `src/bioetl/domain/types.py`
- TaxonomyId VO: `src/bioetl/domain/value_objects/taxonomy_id.py`
- AssayTransformer: `src/bioetl/application/pipelines/chembl/assay_transformer.py`
- Assay Silver schema: `src/bioetl/domain/schemas/chembl/assay.py`
