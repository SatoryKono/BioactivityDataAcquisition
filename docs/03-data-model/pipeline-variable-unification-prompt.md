# Промт для унификации наименований переменных и валидации данных

## Область: пайплайны Activity, Assay, Target, Molecule (ChEMBL)

**Версия**: 1.0.0
**Дата**: 2026-02-13
**Задача**: Стандартизировать наименования полей (переменных) и правила валидации
данных для 4-х основных ChEMBL source-пайплайнов.

---

## Содержание

1. [Обзор слоёв данных](#1-обзор-слоёв-данных)
2. [Поля по пайплайнам](#2-поля-по-пайплайнам)
   - [Activity](#21-activity)
   - [Assay](#22-assay)
   - [Target](#23-target)
   - [Molecule](#24-molecule)
3. [Кросс-таблица унификации](#3-кросс-таблица-унификации)
4. [Выявленные расхождения](#4-выявленные-расхождения)
5. [Рекомендации по унификации](#5-рекомендации-по-унификации)

---

## 1. Обзор слоёв данных

Каждое поле проходит через 4 уровня:

| Слой | Источник | Представление |
|------|----------|---------------|
| **API (Bronze)** | Сырые данные ChEMBL REST API | `dict[str, Any]` — JSON ответ |
| **DTO** | Pydantic-модель для валидации на границе | `chembl.py` (`ActivityRecord`, etc.) |
| **Entity (Silver)** | Domain entity — dataclass | `bioactivity.py`, `chembl_activity.py`, `chembl_structures.py` |
| **Gold Schema** | Pandera DataFrameModel | `chembl.py` (Gold contracts) |

Переименования (renaming) происходят в **Transformer** (`*_transformer.py`).

---

## 2. Поля по пайплайнам

### 2.1 Activity

| # | API (Bronze) | DTO (ActivityRecord) | Transformer → Silver | Entity (Bioactivity) | Gold Schema | Описание |
|---|---|---|---|---|---|---|
| 1 | `activity_id` | `activity_id` | `activity_id` | `activity_id` | `activity_id` | PK измерения биоактивности |
| 2 | `molecule_chembl_id` | `molecule_id` | → `molecule_id` | `molecule_id` | `molecule_id` | FK на молекулу |
| 3 | `target_chembl_id` | `target_id` | → `target_id` | `target_id` | `target_id` | FK на мишень |
| 4 | `assay_chembl_id` | `assay_id` | → `assay_id` | `assay_id` | `assay_id` | FK на анализ |
| 5 | `document_chembl_id` | `publication_id` | → `publication_id` | `publication_id` | `publication_id` | FK на публикацию |
| 6 | `record_id` | `record_id` | `record_id` | `record_id` | `record_id` | FK на compound_record |
| 7 | `src_id` | `src_id` | `src_id` | `src_id` | `src_id` | ID источника данных |
| 8 | `canonical_smiles` | `canonical_smiles` | `canonical_smiles` | `canonical_smiles` | `canonical_smiles` | SMILES молекулы (денорм.) |
| 9 | `molecule_pref_name` | `molecule_pref_name` | `molecule_pref_name` | `molecule_pref_name` | `molecule_pref_name` | Имя молекулы (денорм.) |
| 10 | `parent_molecule_chembl_id` | `parent_molecule_id` | → `parent_molecule_id` | `parent_molecule_id` | `parent_molecule_id` | Родит. молекула (денорм.) |
| 11 | `target_pref_name` | `target_pref_name` | `target_pref_name` | `target_pref_name` | `target_pref_name` | Имя мишени (денорм.) |
| 12 | `target_organism` | `target_organism` | `target_organism` | `target_organism` | `target_organism` | Организм мишени (денорм.) |
| 13 | `target_tax_id` | `target_tax_id` | → `taxonomy_id` | `taxonomy_id` | `taxonomy_id` | NCBI Taxonomy ID мишени |
| 14 | `assay_type` | `assay_type` | `assay_type` | `assay_type` | `assay_type` | Тип анализа (B/F/A) |
| 15 | `assay_description` | `assay_description` | `assay_description` | `assay_description` | `assay_description` | Описание анализа (денорм.) |
| 16 | `assay_variant_accession` | `assay_variant_accession` | `assay_variant_accession` | `assay_variant_accession` | `assay_variant_accession` | UniProt accession варианта |
| 17 | `assay_variant_mutation` | `assay_variant_mutation` | `assay_variant_mutation` | `assay_variant_mutation` | `assay_variant_mutation` | Мутация варианта |
| 18 | `bao_endpoint` | `bao_endpoint` | `bao_endpoint` | `bao_endpoint` | `bao_endpoint` | BAO endpoint |
| 19 | `bao_format` | `bao_format` | `bao_format` | `bao_format` | `bao_format` | BAO формат |
| 20 | `bao_label` | `bao_label` | `bao_label` | `bao_label` | `bao_label` | BAO метка |
| 21 | `type` | `type` | `type` | `type` | `type` | Исходный тип измерения |
| 22 | `value` | `value` | `value` | `value` | `value` | Исходное значение |
| 23 | `units` | `units` | `units` | `units` | `units` | Исходные единицы |
| 24 | `relation` | `relation` | `relation` | `relation` | `relation` | Исходное отношение (=, >, <) |
| 25 | `upper_value` | `upper_value` | `upper_value` | `upper_value` | `upper_value` | Верхняя граница (исходн.) |
| 26 | `text_value` | `text_value` | `text_value` | `text_value` | `text_value` | Текстовое значение (исходн.) |
| 27 | `standard_type` | `standard_type` | `standard_type` | `standard_type` | `standard_type` | Стандартиз. тип (IC50, Ki) |
| 28 | `standard_value` | `standard_value` | `standard_value` | `standard_value` | `standard_value` | Стандартиз. значение |
| 29 | `standard_units` | `standard_units` | `standard_units` | `standard_units` | `standard_units` | Стандартиз. единицы (nM) |
| 30 | `standard_relation` | `standard_relation` | `standard_relation` | `standard_relation` | `standard_relation` | Стандартиз. отношение |
| 31 | `standard_upper_value` | `standard_upper_value` | `standard_upper_value` | `standard_upper_value` | `standard_upper_value` | Стандартиз. верхняя граница |
| 32 | `standard_text_value` | `standard_text_value` | `standard_text_value` | `standard_text_value` | `standard_text_value` | Стандартиз. текстовое знач. |
| 33 | `standard_flag` | `standard_flag` | `standard_flag` | `standard_flag` | `standard_flag` | Флаг стандартизации (0/1) |
| 34 | `pchembl_value` | `pchembl_value` | `pchembl_value` | `pchembl_value` | `pchembl_value` | -log10(M) значение |
| 35 | `ligand_efficiency.bei` | `ligand_efficiency_bei` | → `ligand_efficiency_bei` | `ligand_efficiency_bei` | `ligand_efficiency_bei` | Binding Efficiency Index |
| 36 | `ligand_efficiency.le` | `ligand_efficiency_le` | → `ligand_efficiency_le` | `ligand_efficiency_le` | `ligand_efficiency_le` | Ligand Efficiency |
| 37 | `ligand_efficiency.lle` | `ligand_efficiency_lle` | → `ligand_efficiency_lle` | `ligand_efficiency_lle` | `ligand_efficiency_lle` | Lipophilic Ligand Efficiency |
| 38 | `ligand_efficiency.sei` | `ligand_efficiency_sei` | → `ligand_efficiency_sei` | `ligand_efficiency_sei` | `ligand_efficiency_sei` | Surface Efficiency Index |
| 39 | `qudt_units` | `qudt_units` | `qudt_units` | `qudt_units` | `qudt_units` | QUDT единицы |
| 40 | `uo_units` | `uo_units` | `uo_units` | `uo_units` | `uo_units` | Units Ontology ID |
| 41 | `document_journal` | `journal` | → `journal` | `journal` | `journal` | Журнал (денорм.) |
| 42 | `document_year` | `publication_year` | → `publication_year` | `publication_year` | `publication_year` | Год публикации (денорм.) |
| 43 | — | — | — | `publication_doi` | `publication_doi` | DOI публикации |
| 44 | — | — | — | `publication_pmid` | `publication_pmid` | PubMed ID |
| 45 | — | — | — | `publication_pmc_id` | `publication_pmc_id` | PMC ID |
| 46 | `activity_comment` | `activity_comment` | `activity_comment` | `activity_comment` | `activity_comment` | Комментарий к измерению |
| 47 | `data_validity_comment` | `data_validity_comment` | `data_validity_comment` | `data_validity_comment` | `data_validity_comment` | Комментарий валидности |
| 48 | `data_validity_description` | `data_validity_description` | `data_validity_description` | `data_validity_description` | `data_validity_description` | Описание валидности |
| 49 | `potential_duplicate` | `potential_duplicate` | `potential_duplicate` | `potential_duplicate` | `potential_duplicate` | Флаг дубликата |
| 50 | `manual_curation_flag` | — | `manual_curation_flag` | `manual_curation_flag` | — | Ручная проверка |
| 51 | `original_activity_id` | — | `original_activity_id` | `original_activity_id` | — | FK трассировки |
| 52 | `toid` | `toid` | `toid` | `toid` | `toid` | Test Occasion ID |
| 53 | `action_type.*` | `action_type` | → `action_type` | `action_type` | `action_type` | Тип действия |
| 54 | `action_type.description` | `action_type_description` | → `action_type_description` | `action_type_description` | `action_type_description` | Описание типа действия |
| 55 | `action_type.parent_type` | **`action_type_parent`** | → `action_type_parent_type` | `action_type_parent_type` | `action_type_parent_type` | Родит. тип действия |
| 56 | `activity_properties` | **`activity_properties_json`** | → `activity_properties` | `activity_properties` | `activity_properties` | Свойства (JSON) |

**Расхождения Activity:**
- DTO `action_type_parent` ≠ Entity/Gold `action_type_parent_type`
- DTO `activity_properties_json` ≠ Entity/Gold `activity_properties`
- DTO `target_tax_id` — остаётся API-имя; Entity/Gold: `taxonomy_id`

---

### 2.2 Assay

| # | API (Bronze) | DTO (AssayRecord) | Transformer → Silver | Entity (Assay) | Gold Schema | Описание |
|---|---|---|---|---|---|---|
| 1 | `assay_chembl_id` | `assay_id` | → `assay_id` | `assay_id` | `assay_id` | PK анализа |
| 2 | `target_chembl_id` | `target_id` | → `target_id` | `target_id` | `target_id` | FK на мишень |
| 3 | `document_chembl_id` | `publication_id` | → `publication_id` | `publication_id` | `publication_id` | FK на публикацию |
| 4 | `cell_chembl_id` | `cell_id` | → `cell_id` | `cell_id` | `cell_id` | FK на клеточную линию |
| 5 | `tissue_chembl_id` | `tissue_id` | → `tissue_id` | `tissue_id` | `tissue_id` | FK на ткань |
| 6 | `src_id` | `src_id` | `src_id` | `src_id` | `src_id` | ID источника |
| 7 | `src_assay_id` | `src_assay_id` | `src_assay_id` | `src_assay_id` | `src_assay_id` | Исходный ID анализа |
| 8 | `aidx` | `aidx` | `aidx` | `aidx` | `aidx` | Индекс анализа |
| 9 | `assay_type` | `assay_type` | `assay_type` | `assay_type` | `assay_type` | Тип (B/F/A/T/P/U) |
| 10 | `assay_type_description` | `assay_type_description` | `assay_type_description` | `assay_type_description` | `assay_type_description` | Описание типа |
| 11 | `assay_category` | `assay_category` | `assay_category` | `assay_category` | `assay_category` | Категория |
| 12 | `assay_test_type` | `assay_test_type` | `assay_test_type` | `assay_test_type` | `assay_test_type` | Тип теста |
| 13 | `assay_group` | `assay_group` | `assay_group` | `assay_group` | `assay_group` | Группа |
| 14 | `assay_organism` | `assay_organism` | `assay_organism` | `assay_organism` | `assay_organism` | Организм анализа |
| 15 | `assay_tax_id` | **`assay_tax_id`** | → `taxonomy_id` | `taxonomy_id` | `taxonomy_id` | NCBI Taxonomy ID анализа |
| 16 | `assay_cell_type` | `assay_cell_type` | `assay_cell_type` | `assay_cell_type` | `assay_cell_type` | Тип клетки |
| 17 | `assay_tissue` | `assay_tissue` | `assay_tissue` | `assay_tissue` | `assay_tissue` | Ткань |
| 18 | `assay_strain` | `assay_strain` | `assay_strain` | `assay_strain` | `assay_strain` | Штамм |
| 19 | `assay_subcellular_fraction` | `assay_subcellular_fraction` | `assay_subcellular_fraction` | `assay_subcellular_fraction` | `assay_subcellular_fraction` | Субклеточная фракция |
| 20 | `bao_format` | `bao_format` | `bao_format` | `bao_format` | `bao_format` | BAO формат |
| 21 | `bao_label` | `bao_label` | `bao_label` | `bao_label` | `bao_label` | BAO метка |
| 22 | `description` | `description` | `description` | `description` | `description` | Полное описание |
| 23 | `confidence_score` | `confidence_score` | `confidence_score` | `confidence_score` | `confidence_score` | Оценка уверенности (0-9) |
| 24 | `confidence_description` | `confidence_description` | `confidence_description` | `confidence_description` | `confidence_description` | Описание уверенности |
| 25 | `relationship_type` | `relationship_type` | `relationship_type` | `relationship_type` | `relationship_type` | Тип связи с мишенью |
| 26 | `relationship_description` | `relationship_description` | `relationship_description` | `relationship_description` | `relationship_description` | Описание связи |
| 27 | `assay_pref_name` | `assay_pref_name` | `assay_pref_name` | `assay_pref_name` | `assay_pref_name` | Предпочтительное имя |
| 28 | `score` | `score` | `score` | `score` | `score` | Счёт (отд. от confidence) |
| 29 | `variant_sequence.accession` | `variant_accession` | → `variant_accession` | `variant_accession` | `variant_accession` | UniProt accession варианта |
| 30 | `variant_sequence.isoform` | `variant_isoform` | → `variant_isoform` | `variant_isoform` | `variant_isoform` | Изоформа |
| 31 | `variant_sequence.mutation` | `variant_mutation` | → `variant_mutation` | `variant_mutation` | `variant_mutation` | Мутация |
| 32 | `variant_sequence.organism` | `variant_organism` | → `variant_organism` | `variant_organism` | `variant_organism` | Организм варианта |
| 33 | `variant_sequence.sequence` | `variant_sequence` | → `variant_sequence` | `variant_sequence` | `variant_sequence` | Аминокислотн. последоват. |
| 34 | `variant_sequence.tax_id` | **`variant_tax_id`** | → `variant_taxonomy_id` | `variant_taxonomy_id` | `variant_taxonomy_id` | Taxonomy ID варианта |
| 35 | `variant_sequence` (JSON) | `variant_sequence_json` | `variant_sequence_json` | `variant_sequence_json` | `variant_sequence_json` | Исходный JSON варианта |
| 36 | `assay_classifications` | **`assay_classifications_json`** | → `assay_classifications` | `assay_classifications` | `assay_classifications` | Классификации (JSON) |
| 37 | `assay_parameters` | **`assay_parameters_json`** | → `assay_parameters` | `assay_parameters` | `assay_parameters` | Параметры (JSON) |

**Расхождения Assay:**
- DTO `assay_tax_id` (int) — API-имя; Entity/Gold: `taxonomy_id`
- DTO `variant_tax_id` (int) — API-имя; Entity/Gold: `variant_taxonomy_id`
- DTO `assay_classifications_json` ≠ Entity/Gold `assay_classifications`
- DTO `assay_parameters_json` ≠ Entity/Gold `assay_parameters`

---

### 2.3 Target

| # | API (Bronze) | DTO (TargetRecord) | Transformer → Silver | Entity (Target) | Gold Schema | Описание |
|---|---|---|---|---|---|---|
| 1 | `target_chembl_id` | `target_id` | → `target_id` | `target_id` | `target_id` | PK мишени |
| 2 | `pref_name` | `pref_name` | `pref_name` | `pref_name` | `pref_name` | Предпочтительное имя |
| 3 | `target_type` | `target_type` | `target_type` | `target_type` | `target_type` | Тип (SINGLE PROTEIN, ...) |
| 4 | `organism` | `organism` | `organism` | `organism` | `organism` | Организм |
| 5 | `tax_id` | **`tax_id`** | → `taxonomy_id` | `taxonomy_id` | `taxonomy_id` | NCBI Taxonomy ID |
| 6 | `species_group_flag` | `species_group_flag` | `species_group_flag` | `species_group_flag` | `species_group_flag` | Флаг группы видов |
| 7 | `downgraded` | `downgraded` | `downgraded` (→ bool) | `downgraded` | `downgraded` | Deprecated флаг |
| 8 | `pipeline_stages` | `pipeline_stages` | `pipeline_stages` (JSON) | `pipeline_stages` | `pipeline_stages` | Стадии пайплайна (JSON) |
| 9 | `target_components` | **`target_components_json`** | → `target_components` | `target_components` | `target_components` | Компоненты (JSON) |
| 10 | — | — | `target_component_synonyms` | `target_component_synonyms` | `target_component_synonyms` | Синонимы компон. (JSON) |
| 11 | `cross_references` (вложен.) | **`cross_references_json`** | → `cross_references` | `cross_references` | `cross_references` | Кросс-ссылки (JSON) |
| 12 | (из target_components) | `component_accessions` | `component_accessions` | `component_accessions` | `component_accessions` | UniProt accession(s) |
| 13 | (из target_components) | — | `primary_component_id` | `primary_component_id` | `primary_component_id` | Первый component_id |
| 14 | (из target_components) | `component_ids` | `component_ids` | `component_ids` | `component_ids` | Список ID компонентов |
| 15 | (из target_components) | `component_types` | `component_types` | `component_types` | `component_types` | Типы компонентов |
| 16 | (из target_components) | `component_relationships` | `component_relationships` | `component_relationships` | `component_relationships` | Связи компонентов |
| 17 | (из target_components) | `component_descriptions` | `component_descriptions` | `component_descriptions` | `component_descriptions` | Описания компонентов |
| 18 | — | **`component_tax_ids`** | — | — | — | Tax IDs компон. (DTO only) |
| 19 | — | `description` | — | — | — | Описание (DTO only) |
| 20 | — | `dap_id` | — | — | — | Drug-Affinity Panel ID (DTO) |
| 21 | — | `target_constraints` | — | — | — | Constraints (DTO only) |

**Расхождения Target:**
- DTO `tax_id` (int) — API-имя; Entity/Gold: `taxonomy_id`
- DTO `target_components_json` ≠ Entity/Gold `target_components`
- DTO `cross_references_json` ≠ Entity/Gold `cross_references`
- DTO `component_tax_ids` — есть только в DTO, нет в Entity/Gold
- DTO `description`, `dap_id`, `target_constraints` — есть в DTO, нет в Entity/Gold
- `primary_component_id` — нет в DTO, есть в Entity/Gold (computed в трансформере)

---

### 2.4 Molecule

| # | API (Bronze) | DTO (MoleculeRecord) | Transformer → Silver | Entity (Molecule) | Gold Schema | Описание |
|---|---|---|---|---|---|---|
| 1 | `molecule_chembl_id` | `molecule_id` | → `molecule_id` | `molecule_id` | `molecule_id` | PK молекулы |
| 2 | `pref_name` | `pref_name` | `pref_name` | `pref_name` | `pref_name` | Предпочтительное имя |
| 3 | `molecule_type` | `molecule_type` | `molecule_type` | `molecule_type` | `molecule_type` | Тип (Small molecule, ...) |
| 4 | `structure_type` | `structure_type` | `structure_type` | `structure_type` | `structure_type` | Тип структуры (MOL/NONE) |
| 5 | `max_phase` | `max_phase` | `max_phase` | `max_phase` | `max_phase` | Клинич. фаза (0-4) |
| 6 | `first_approval` | `first_approval` | `first_approval` | `first_approval` | `first_approval` | Год первого одобрения |
| 7 | `oral` | `oral` | `oral` | `oral` | `oral` | Пероральность |
| 8 | `parenteral` | `parenteral` | `parenteral` | `parenteral` | `parenteral` | Парентеральность |
| 9 | `topical` | `topical` | `topical` | `topical` | `topical` | Наружное применение |
| 10 | `therapeutic_flag` | `therapeutic_flag` | `therapeutic_flag` | `therapeutic_flag` | `therapeutic_flag` | Лекарственное средство |
| 11 | `withdrawn_flag` | `withdrawn_flag` | `withdrawn_flag` | `withdrawn_flag` | `withdrawn_flag` | Отозван |
| 12 | `black_box_warning` | `black_box_warning` | `black_box_warning` | `black_box_warning` | `black_box_warning` | BBW флаг |
| 13 | `natural_product` | `natural_product` | `natural_product` | `natural_product` | `natural_product` | Натур. происхождение |
| 14 | `first_in_class` | `first_in_class` | `first_in_class` | `first_in_class` | `first_in_class` | Первый в классе |
| 15 | `prodrug` | `prodrug` | `prodrug` | `prodrug` | `prodrug` | Пролекарство |
| 16 | `inorganic_flag` | `inorganic_flag` | `inorganic_flag` | `inorganic_flag` | `inorganic_flag` | Неорганическое |
| 17 | `polymer_flag` | `polymer_flag` | `polymer_flag` | `polymer_flag` | `polymer_flag` | Полимер |
| 18 | `chirality` | `chirality` | `chirality` | `chirality` | `chirality` | Хиральность |
| 19 | `dosed_ingredient` | `dosed_ingredient` | `dosed_ingredient` | `dosed_ingredient` | `dosed_ingredient` | Дозируемый ингредиент |
| 20 | `availability_type` | `availability_type` | `availability_type` | `availability_type` | `availability_type` | Тип доступности |
| 21 | `usan_stem` | `usan_stem` | `usan_stem` | `usan_stem` | `usan_stem` | USAN стем |
| 22 | `usan_stem_definition` | `usan_stem_definition` | `usan_stem_definition` | `usan_stem_definition` | `usan_stem_definition` | Описание стема |
| 23 | `usan_substem` | `usan_substem` | `usan_substem` | `usan_substem` | `usan_substem` | USAN сабстем |
| 24 | `usan_year` | `usan_year` | `usan_year` | `usan_year` | `usan_year` | Год USAN |
| 25 | `helm_notation` | `helm_notation` | `helm_notation` | `helm_notation` | `helm_notation` | HELM нотация |
| 26 | `molecule_species` | `molecule_species` | `molecule_species` | `molecule_species` | `molecule_species` | Вид (ACID/BASE/...) |
| 27 | `molecule_hierarchy.*` | — | → JSON `molecule_hierarchy` | `molecule_hierarchy` | `molecule_hierarchy` | Иерархия (JSON) |
| 28 | `molecule_hierarchy.parent_chembl_id` | `hierarchy_parent_chembl_id` | → `hierarchy_parent_chembl_id` | `hierarchy_parent_chembl_id` | `hierarchy_parent_chembl_id` | Родитель |
| 29 | `molecule_hierarchy.active_chembl_id` | `hierarchy_active_chembl_id` | → `hierarchy_active_chembl_id` | `hierarchy_active_chembl_id` | `hierarchy_active_chembl_id` | Активная форма |
| 30 | `molecule_hierarchy.molecule_chembl_id` | `hierarchy_child_chembl_id` | → `hierarchy_child_chembl_id` | `hierarchy_child_chembl_id` | `hierarchy_child_chembl_id` | Дочерний (renamed) |
| 31 | `molecule_properties.alogp` | `property_alogp` | → `property_alogp` | `property_alogp` | — | ALogP |
| 32 | `molecule_properties.mw_freebase` | `property_mw_freebase` | → `property_mw_freebase` | `property_mw_freebase` | `property_mw_freebase` | Мол. масса (freebase) |
| 33 | `molecule_properties.full_mwt` | `property_full_mwt` | → `property_full_mwt` | `property_full_mwt` | — | Полная мол. масса |
| 34 | `molecule_properties.hba` | `property_hba` | → `property_hba` | `property_hba` | — | Акцепторы H |
| 35 | `molecule_properties.hbd` | `property_hbd` | → `property_hbd` | `property_hbd` | — | Доноры H |
| 36 | `molecule_properties.psa` | `property_psa` | → `property_psa` | `property_psa` | — | Полярная площадь |
| 37 | `molecule_properties.rtb` | `property_rtb` | → `property_rtb` | `property_rtb` | — | Вращаемые связи |
| 38 | `molecule_properties.num_ro5_violations` | `property_ro5_violations` | → `property_ro5_violations` | `property_ro5_violations` | `property_ro5_violations` | Нарушения RO5 |
| 39 | `molecule_properties.heavy_atoms` | `property_heavy_atoms` | → `property_heavy_atoms` | `property_heavy_atoms` | — | Тяжёлые атомы |
| 40 | `molecule_properties.aromatic_rings` | `property_aromatic_rings` | → `property_aromatic_rings` | `property_aromatic_rings` | — | Ароматические кольца |
| 41 | `molecule_properties.qed_weighted` | `property_qed_weighted` | → `property_qed_weighted` | `property_qed_weighted` | `property_qed_weighted` | QED взвешенный |
| 42 | `molecule_properties.full_molformula` | `property_full_molformula` | → `property_full_molformula` | `property_full_molformula` | `property_full_molformula` | Мол. формула |
| 43 | `molecule_properties.ro3_pass` | `property_ro3_pass` | → `property_ro3_pass` | `property_ro3_pass` | `property_ro3_pass` | RO3 (Y/N) |
| 44 | — | — | alias `logp` = `property_alogp` | `logp` | `logp` | LogP (каноническое) |
| 45 | — | — | alias `logp_method` = "alogp" | `logp_method` | `logp_method` | Метод расчёта LogP |
| 46 | — | — | alias `molecular_weight` = `property_full_mwt` | `molecular_weight` | `molecular_weight` | Мол. масса (каноническое) |
| 47 | — | — | alias `polar_surface_area` = `property_psa` | `polar_surface_area` | `polar_surface_area` | PSA (каноническое) |
| 48 | — | — | alias `rotatable_bond_count` = `property_rtb` | `rotatable_bond_count` | `rotatable_bond_count` | Вращ. связи (каноническое) |
| 49 | — | — | alias `heavy_atom_count` = `property_heavy_atoms` | `heavy_atom_count` | `heavy_atom_count` | Тяж. атомы (каноническое) |
| 50 | — | — | alias `aromatic_ring_count` = `property_aromatic_rings` | `aromatic_ring_count` | `aromatic_ring_count` | Аром. кольца (каноническое) |
| 51 | — | — | alias `hba_count` = `property_hba` | `hba_count` | `hba_count` | HBA (каноническое) |
| 52 | — | — | alias `hbd_count` = `property_hbd` | `hbd_count` | `hbd_count` | HBD (каноническое) |
| 53 | `molecule_structures.canonical_smiles` | `canonical_smiles` | → `canonical_smiles` | `canonical_smiles` | `canonical_smiles` | SMILES |
| 54 | `molecule_structures.standard_inchi` | `standard_inchi` | → `standard_inchi` | `standard_inchi` | `standard_inchi` | InChI |
| 55 | `molecule_structures.standard_inchi_key` | `inchi_key` | → `inchi_key` | `inchi_key` | `inchi_key` | InChI Key (renamed) |
| 56 | `molecule_properties` (JSON) | **`molecule_properties_json`** | → `molecule_properties` | `molecule_properties` | `molecule_properties` | Свойства (JSON) |
| 57 | `molecule_structures` (JSON) | **`molecule_structures_json`** | → `molecule_structures` | `molecule_structures` | `molecule_structures` | Структуры (JSON) |
| 58 | `molecule_synonyms` (JSON) | **`molecule_synonyms_json`** | → `molecule_synonyms` | `molecule_synonyms` | `molecule_synonyms` | Синонимы (JSON) |
| 59 | `cross_references` (JSON) | **`cross_references_json`** | → `cross_references` | `cross_references` | `cross_references` | Кросс-ссылки (JSON) |
| 60 | `atc_classifications` (JSON) | **`atc_classifications_json`** | → `atc_classifications` | `atc_classifications` | `atc_classifications` | ATC (JSON) |
| 61 | — | **`molecule_hierarchy_json`** | → `molecule_hierarchy` | `molecule_hierarchy` | `molecule_hierarchy` | Иерархия (JSON) |

**Расхождения Molecule:**
- DTO использует `*_json` суффикс для JSON-полей; Entity/Gold — без суффикса
- Gold содержит и `property_*` поля и alias-поля (дублирование)
- `property_alogp`, `property_psa`, `property_full_mwt`, `property_hba`, `property_hbd`, `property_rtb`, `property_heavy_atoms`, `property_aromatic_rings` отсутствуют в Gold — только alias-версии (кроме `property_mw_freebase`, `property_ro5_violations`, `property_qed_weighted`, `property_full_molformula`, `property_ro3_pass`)

---

## 3. Кросс-таблица унификации

### 3.1 Идентификаторы (общие между пайплайнами)

| Унифицированное поле | Activity | Assay | Target | Molecule | Описание |
|---|---|---|---|---|---|
| `activity_id` | `activity_id` | — | — | — | PK активности |
| `assay_id` | `assay_chembl_id` → `assay_id` | `assay_chembl_id` → `assay_id` | — | — | PK/FK анализа |
| `target_id` | `target_chembl_id` → `target_id` | `target_chembl_id` → `target_id` | `target_chembl_id` → `target_id` | — | PK/FK мишени |
| `molecule_id` | `molecule_chembl_id` → `molecule_id` | — | — | `molecule_chembl_id` → `molecule_id` | PK/FK молекулы |
| `publication_id` | `document_chembl_id` → `publication_id` | `document_chembl_id` → `publication_id` | — | — | FK на публикацию |
| `cell_id` | — | `cell_chembl_id` → `cell_id` | — | — | FK на клеточную линию |
| `tissue_id` | — | `tissue_chembl_id` → `tissue_id` | — | — | FK на ткань |
| `src_id` | `src_id` | `src_id` | — | — | ID источника данных |
| `record_id` | `record_id` | — | — | — | FK на compound_record |

### 3.2 Таксономия и организм

| Унифицированное поле | Activity | Assay | Target | Molecule | Описание |
|---|---|---|---|---|---|
| `taxonomy_id` | `target_tax_id` → **taxonomy_id** | `assay_tax_id` → **taxonomy_id** | `tax_id` → **taxonomy_id** | — | NCBI Taxonomy ID |
| `organism` | — | — | `organism` | — | Основной организм (контекст — target) |
| `target_organism` | `target_organism` (денорм.) | — | — | — | Организм мишени (в activity) |
| `assay_organism` | — | `assay_organism` | — | — | Организм анализа |
| `variant_taxonomy_id` | — | `variant.tax_id` → **variant_taxonomy_id** | — | — | Taxonomy ID варианта |

**Проблема**: одно поле `taxonomy_id` обозначает разные сущности в разных пайплайнах:
- В Activity: taxonomy_id мишени (target)
- В Assay: taxonomy_id анализа (assay organism)
- В Target: taxonomy_id мишени

### 3.3 Имена и описания

| Унифицированное поле | Activity | Assay | Target | Molecule | Описание |
|---|---|---|---|---|---|
| `pref_name` | — | `assay_pref_name` | `pref_name` | `pref_name` | Предпочтительное имя |
| `molecule_pref_name` | `molecule_pref_name` (денорм.) | — | — | — | Имя молекулы (в activity) |
| `target_pref_name` | `target_pref_name` (денорм.) | — | — | — | Имя мишени (в activity) |
| `description` | — | `description` | — | — | Описание |
| `assay_description` | `assay_description` (денорм.) | — | — | — | Описание анализа (в activity) |

### 3.4 BAO (BioAssay Ontology)

| Унифицированное поле | Activity | Assay | Target | Molecule | Описание |
|---|---|---|---|---|---|
| `bao_format` | `bao_format` | `bao_format` | — | — | BAO формат |
| `bao_label` | `bao_label` | `bao_label` | — | — | BAO метка |
| `bao_endpoint` | `bao_endpoint` | — | — | — | BAO endpoint |

### 3.5 Тип анализа и классификация

| Унифицированное поле | Activity | Assay | Target | Molecule | Описание |
|---|---|---|---|---|---|
| `assay_type` | `assay_type` (денорм.) | `assay_type` | — | — | Тип анализа |
| `assay_type_description` | — | `assay_type_description` | — | — | Описание типа |
| `assay_category` | — | `assay_category` | — | — | Категория |
| `assay_test_type` | — | `assay_test_type` | — | — | Тип теста |
| `assay_group` | — | `assay_group` | — | — | Группа |
| `target_type` | — | — | `target_type` | — | Тип мишени |
| `molecule_type` | — | — | — | `molecule_type` | Тип молекулы |
| `structure_type` | — | — | — | `structure_type` | Тип структуры |

### 3.6 Измерения и стандартизация (Activity only)

| Унифицированное поле | Activity | Assay | Target | Molecule | Описание |
|---|---|---|---|---|---|
| `type` | `type` | — | — | — | Исходный тип |
| `value` | `value` | — | — | — | Исходное значение |
| `units` | `units` | — | — | — | Исходные единицы |
| `relation` | `relation` | — | — | — | Исходное отношение |
| `upper_value` | `upper_value` | — | — | — | Верхняя граница |
| `text_value` | `text_value` | — | — | — | Текстовое значение |
| `standard_type` | `standard_type` | — | — | — | Стандартиз. тип |
| `standard_value` | `standard_value` | — | — | — | Стандартиз. значение |
| `standard_units` | `standard_units` | — | — | — | Стандартиз. единицы |
| `standard_relation` | `standard_relation` | — | — | — | Стандартиз. отношение |
| `standard_upper_value` | `standard_upper_value` | — | — | — | Стандартиз. верхн. граница |
| `standard_text_value` | `standard_text_value` | — | — | — | Стандартиз. текст |
| `standard_flag` | `standard_flag` | — | — | — | Флаг стандартизации |
| `pchembl_value` | `pchembl_value` | — | — | — | pChEMBL (-log10 M) |

### 3.7 Ligand Efficiency (Activity only)

| Унифицированное поле | Activity | Assay | Target | Molecule | Описание |
|---|---|---|---|---|---|
| `ligand_efficiency_bei` | `ligand_efficiency_bei` | — | — | — | BEI |
| `ligand_efficiency_le` | `ligand_efficiency_le` | — | — | — | LE |
| `ligand_efficiency_lle` | `ligand_efficiency_lle` | — | — | — | LLE |
| `ligand_efficiency_sei` | `ligand_efficiency_sei` | — | — | — | SEI |

### 3.8 Молекулярные свойства (Molecule only, с дублированием)

| Унифицированное (канонич.) | property_* (Silver) | alias (Gold) | Описание |
|---|---|---|---|
| `logp` | `property_alogp` | `logp` | Липофильность |
| `molecular_weight` | `property_full_mwt` | `molecular_weight` | Молекулярная масса |
| `polar_surface_area` | `property_psa` | `polar_surface_area` | PSA |
| `rotatable_bond_count` | `property_rtb` | `rotatable_bond_count` | Вращаемые связи |
| `heavy_atom_count` | `property_heavy_atoms` | `heavy_atom_count` | Тяжёлые атомы |
| `aromatic_ring_count` | `property_aromatic_rings` | `aromatic_ring_count` | Ароматич. кольца |
| `hba_count` | `property_hba` | `hba_count` | Акцепторы H |
| `hbd_count` | `property_hbd` | `hbd_count` | Доноры H |
| `property_mw_freebase` | `property_mw_freebase` | `property_mw_freebase` | MW freebase (нет alias) |
| `property_ro5_violations` | `property_ro5_violations` | `property_ro5_violations` | RO5 нарушения |
| `property_qed_weighted` | `property_qed_weighted` | `property_qed_weighted` | QED score |
| `property_full_molformula` | `property_full_molformula` | `property_full_molformula` | Мол. формула |
| `property_ro3_pass` | `property_ro3_pass` | `property_ro3_pass` | RO3 pass (Y/N) |

### 3.9 Структурные идентификаторы

| Унифицированное поле | Activity | Assay | Target | Molecule | Описание |
|---|---|---|---|---|---|
| `canonical_smiles` | `canonical_smiles` (денорм.) | — | — | `canonical_smiles` | SMILES |
| `standard_inchi` | — | — | — | `standard_inchi` | InChI |
| `inchi_key` | — | — | — | `standard_inchi_key` → `inchi_key` | InChI Key |

### 3.10 Компоненты мишени (Target only)

| Унифицированное поле | Activity | Assay | Target | Molecule | Описание |
|---|---|---|---|---|---|
| `component_accessions` | — | — | `component_accessions` | — | UniProt accession(s) |
| `component_ids` | — | — | `component_ids` | — | Component ID(s) |
| `component_types` | — | — | `component_types` | — | Типы компонентов |
| `component_relationships` | — | — | `component_relationships` | — | Связи компонентов |
| `component_descriptions` | — | — | `component_descriptions` | — | Описания компонентов |
| `primary_component_id` | — | — | `primary_component_id` | — | Первый component_id |
| `target_components` | — | — | `target_components` (JSON) | — | Полный JSON |
| `target_component_synonyms` | — | — | `target_component_synonyms` (JSON) | — | Синонимы |
| `cross_references` | — | — | `cross_references` (JSON) | `cross_references` (JSON) | Кросс-ссылки |

### 3.11 Варианты (Assay only)

| Унифицированное поле | Activity | Assay | Target | Molecule | Описание |
|---|---|---|---|---|---|
| `variant_accession` | — | `variant_accession` | — | — | UniProt accession |
| `variant_isoform` | — | `variant_isoform` | — | — | Изоформа |
| `variant_mutation` | — | `variant_mutation` | — | — | Мутация |
| `variant_organism` | — | `variant_organism` | — | — | Организм |
| `variant_sequence` | — | `variant_sequence` | — | — | Последовательность |
| `variant_taxonomy_id` | — | `variant_taxonomy_id` | — | — | Taxonomy ID |
| `variant_sequence_json` | — | `variant_sequence_json` | — | — | Исходный JSON |
| `assay_variant_accession` | `assay_variant_accession` (денорм.) | — | — | — | Вариант (в activity) |
| `assay_variant_mutation` | `assay_variant_mutation` (денорм.) | — | — | — | Мутация (в activity) |

### 3.12 Публикации (денорм. в Activity)

| Унифицированное поле | Activity | Assay | Target | Molecule | Описание |
|---|---|---|---|---|---|
| `journal` | `document_journal` → `journal` | — | — | — | Журнал |
| `publication_year` | `document_year` → `publication_year` | — | — | — | Год |
| `publication_doi` | `publication_doi` | — | — | — | DOI |
| `publication_pmid` | `publication_pmid` | — | — | — | PubMed ID |
| `publication_pmc_id` | `publication_pmc_id` | — | — | — | PMC ID |

### 3.13 Quality / Meta (Activity only)

| Унифицированное поле | Activity | Assay | Target | Molecule | Описание |
|---|---|---|---|---|---|
| `activity_comment` | `activity_comment` | — | — | — | Комментарий |
| `data_validity_comment` | `data_validity_comment` | — | — | — | Качество данных |
| `data_validity_description` | `data_validity_description` | — | — | — | Описание качества |
| `potential_duplicate` | `potential_duplicate` | — | — | — | Дубликат |
| `action_type` | `action_type` | — | — | — | Тип действия |
| `action_type_description` | `action_type_description` | — | — | — | Описание |
| `action_type_parent_type` | `action_type_parent_type` | — | — | — | Родит. тип |
| `activity_properties` | `activity_properties` (JSON) | — | — | — | Свойства (JSON) |
| `toid` | `toid` | — | — | — | Test Occasion ID |

### 3.14 Assay Confidence / Relationship

| Унифицированное поле | Activity | Assay | Target | Molecule | Описание |
|---|---|---|---|---|---|
| `confidence_score` | — | `confidence_score` | — | — | Уверенность (0-9) |
| `confidence_description` | — | `confidence_description` | — | — | Описание |
| `relationship_type` | — | `relationship_type` | — | — | Тип связи |
| `relationship_description` | — | `relationship_description` | — | — | Описание связи |
| `score` | — | `score` | — | — | Счёт анализа |

### 3.15 Flags (Target + Molecule)

| Унифицированное поле | Activity | Assay | Target | Molecule | Описание |
|---|---|---|---|---|---|
| `downgraded` | — | — | `downgraded` (bool) | — | Deprecated |
| `species_group_flag` | — | — | `species_group_flag` | — | Группа видов |
| `inorganic_flag` | — | — | — | `inorganic_flag` | Неорганическое |
| `polymer_flag` | — | — | — | `polymer_flag` | Полимер |
| `withdrawn_flag` | — | — | — | `withdrawn_flag` | Отозван |
| `therapeutic_flag` | — | — | — | `therapeutic_flag` | Терапевтическое |

### 3.16 Системные поля (общие для всех)

| Поле | Activity | Assay | Target | Molecule | Описание |
|---|---|---|---|---|---|
| `entity_id` | ✅ | ✅ | ✅ | ✅ | Бизнес-ключ |
| `content_hash` | ✅ | ✅ | ✅ | ✅ | SHA256 дедупликация |
| `_run_id` | ✅ | ✅ | ✅ | ✅ | ID запуска |
| `_run_type` | ✅ | ✅ | ✅ | ✅ | Тип (INCR/BACK/REBUILD) |
| `_source_batch_id` | ✅ | ✅ | ✅ | ✅ | ID батча |
| `_ingestion_ts` | ✅ | ✅ | ✅ | ✅ | Метка загрузки |
| `_index` | ✅ | ✅ | ✅ | ✅ | Порядковый номер |

---

## 4. Выявленные расхождения

### 4.1 DTO ↔ Entity/Gold: суффикс `_json`

| Слой | DTO (Pydantic) | Entity/Gold | Затронуто |
|---|---|---|---|
| Activity | `activity_properties_json` | `activity_properties` | 1 поле |
| Assay | `assay_classifications_json`, `assay_parameters_json` | `assay_classifications`, `assay_parameters` | 2 поля |
| Target | `target_components_json`, `target_component_synonyms_json`, `cross_references_json` | `target_components`, `target_component_synonyms`, `cross_references` | 3 поля |
| Molecule | `molecule_hierarchy_json`, `molecule_properties_json`, `molecule_structures_json`, `molecule_synonyms_json`, `cross_references_json`, `atc_classifications_json` | без `_json` суффикса | 6 полей |

**Вывод**: DTO добавляет `_json` суффикс; Entity/Gold — без суффикса.
Нужно выбрать единый стиль.

### 4.2 DTO ↔ Entity/Gold: taxonomy naming

| Пайплайн | DTO | API (Bronze) | Entity/Gold |
|---|---|---|---|
| Activity | `target_tax_id` | `target_tax_id` | `taxonomy_id` |
| Assay | `assay_tax_id` | `assay_tax_id` | `taxonomy_id` |
| Assay (variant) | `variant_tax_id` | `variant_sequence.tax_id` | `variant_taxonomy_id` |
| Target | `tax_id` | `tax_id` | `taxonomy_id` |

**Вывод**: DTO сохраняет API-имена; Entity/Gold унифицировано. Нужно ли унифицировать DTO?

### 4.3 Семантическое перекрытие `taxonomy_id`

Поле `taxonomy_id` имеет разную семантику в зависимости от пайплайна:
- **Activity**: taxonomy_id target (мишени)
- **Assay**: taxonomy_id assay organism (анализа)
- **Target**: taxonomy_id target (мишени)

Это может приводить к ошибкам при join/merge. Рассмотреть:
- `target_taxonomy_id` (Activity, Target)
- `assay_taxonomy_id` (Assay)
- `variant_taxonomy_id` (Assay) — уже унифицировано.

### 4.4 Дублирование property_* и alias-полей (Molecule)

В Molecule есть двойная система наименования:
- `property_alogp` (Silver/Entity) → `logp` (alias, Gold)
- `property_full_mwt` (Silver/Entity) → `molecular_weight` (alias, Gold)
- `property_psa` → `polar_surface_area`
- `property_rtb` → `rotatable_bond_count`
- И т.д.

Некоторые `property_*` остаются в Gold без alias (`property_mw_freebase`, `property_ro5_violations`).
Это создаёт:
1. Дублирование данных (оба поля в DataFrame)
2. Непоследовательность (часть с alias, часть — нет)

### 4.5 DTO fields, отсутствующие в Entity/Gold

| Pipeline | DTO Field | Статус |
|---|---|---|
| Activity | `manual_curation_flag` | В Entity есть, в Gold — нет |
| Activity | `original_activity_id` | В Entity есть, в Gold — нет |
| Target | `description` | Только в DTO |
| Target | `dap_id` | Только в DTO |
| Target | `target_constraints` | Только в DTO |
| Target | `component_tax_ids` | Только в DTO |

### 4.6 Naming style: `action_type_parent` vs `action_type_parent_type`

| Слой | Имя |
|---|---|
| DTO (ActivityRecord) | `action_type_parent` |
| Entity (Bioactivity) | `action_type_parent_type` |
| Gold Schema | `action_type_parent_type` |

---

## 5. Рекомендации по унификации

### 5.1 Taxonomy ID — добавить контекстный префикс

```
activity.taxonomy_id    → activity.target_taxonomy_id
assay.taxonomy_id       → assay.assay_taxonomy_id
target.taxonomy_id      → target.taxonomy_id (OK, контекст однозначен)
assay.variant_taxonomy_id → OK (уже с префиксом)
```

### 5.2 DTO — убрать суффикс `_json` или добавить его везде

**Вариант A (убрать)**: DTO поля = Entity/Gold поля. Меньше маппингов.
**Вариант B (оставить)**: `_json` суффикс помогает при debugging. Маппинг в трансформере.

### 5.3 Molecule properties — выбрать один стиль

**Вариант A: Оставить только alias-имена в Gold**
Удалить дублирование `property_*`. Gold содержит только `logp`, `molecular_weight`, `polar_surface_area`, etc. + остаточные `property_ro5_violations`, `property_qed_weighted`, `property_full_molformula`, `property_ro3_pass`, `property_mw_freebase`.

**Вариант B: Унифицировать все property_* через alias**
Добавить alias для оставшихся:
- `property_ro5_violations` → `ro5_violations`
- `property_qed_weighted` → `qed_weighted`
- `property_full_molformula` → `molecular_formula`
- `property_ro3_pass` → `ro3_pass`
- `property_mw_freebase` → `mw_freebase`

### 5.4 DTO — синхронизировать с Entity

- `action_type_parent` → `action_type_parent_type` (как в Entity/Gold)
- DTO taxonomy поля: решить — сохранить API-имена или унифицировать

### 5.5 Input Filter — унифицировать column_name

| Pipeline | input_filter.column_name | input_filter.filter_field | Расхождение? |
|---|---|---|---|
| Activity | `activity_id` | `activity_id` | ✅ OK |
| Assay | `assay_chembl_id` | `assay_id` | ⚠️ column_name ≠ filter_field |
| Target | `target_id` | `target_id` | ✅ OK |
| Molecule | `molecule_id` | `molecule_id` | ✅ OK |

Assay input_filter.column_name использует `assay_chembl_id` (API-имя), в то время как
остальные используют unified имя. Рекомендация: `column_name: assay_id`.

---

## Файлы для изменений

| Категория | Файл | Что менять |
|---|---|---|
| DTO | `src/bioetl/domain/entities/chembl.py` | taxonomy naming, `_json` суффиксы, `action_type_parent` |
| Entity Activity | `src/bioetl/domain/entities/bioactivity.py` | taxonomy_id → target_taxonomy_id (если принят §5.1) |
| Entity Assay | `src/bioetl/domain/entities/chembl_activity.py` | taxonomy_id → assay_taxonomy_id (если принят §5.1) |
| Transformer Activity | `src/bioetl/application/pipelines/chembl/activity_transformer.py` | Маппинг taxonomy |
| Transformer Assay | `src/bioetl/application/pipelines/chembl/assay_transformer.py` | Маппинг taxonomy |
| Gold Schema | `src/bioetl/domain/contracts/gold/chembl.py` | taxonomy naming, property alias |
| Filter Config | `configs/filter/entities/chembl/assay.yaml` | column_name |
| DQ Config | `configs/dq/entities/chembl/*.yaml` | Поля для валидации |
| Silver Schema | `src/bioetl/infrastructure/schemas/silver.py` | Имена колонок |
| Тесты | `tests/unit/application/pipelines/chembl/` | Обновить маппинги |
| Тесты архитектуры | `tests/architecture/` | Проверить границы |
