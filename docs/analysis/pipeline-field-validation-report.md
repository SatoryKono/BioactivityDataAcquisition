# Pipeline Field Validation Report

**Дата анализа:** 2026-01-26
**Аналитик:** Claude Code
**Версия кодовой базы:** a1973db

---

## Резюме

Проведён полный аудит соответствия полей между Pandera-схемами и трансформерами для всех 8 провайдеров (21 пайплайн). Выявлено:

| Категория | Количество |
|-----------|------------|
| 🔴 Критические ошибки | 2 |
| ⚠️ Предупреждения | 3 |
| ✅ Корректные пайплайны | 5 |

---

## 1. ChEMBL Activity Pipeline

### Схема: `ActivitySchema`
**Файл:** `src/bioetl/domain/schemas/chembl/activity.py`

### Извлекаемые поля (48):

| Категория | Поля |
|-----------|------|
| Идентификаторы | `activity_id`, `assay_chembl_id`, `molecule_chembl_id`, `target_chembl_id`, `document_chembl_id`, `record_id`, `src_id` |
| Стандартизованные значения | `standard_relation`, `standard_value`, `standard_units`, `standard_type`, `standard_flag`, `standard_text_value`, `standard_upper_value` |
| Исходные значения | `type`, `relation`, `value`, `units`, `text_value`, `upper_value` |
| Метрики | `pchembl_value` |
| Качество | `data_validity_comment`, `activity_comment`, `potential_duplicate`, `toid` |
| Онтологии | `bao_endpoint`, `uo_units`, `qudt_units`, `bao_format`, `bao_label` |
| Ligand Efficiency | `ligand_efficiency_bei`, `ligand_efficiency_le`, `ligand_efficiency_lle`, `ligand_efficiency_sei` |
| Action Type | `action_type_action_type`, `action_type_description`, `action_type_parent_type` |
| Молекула/Таргет | `canonical_smiles`, `molecule_pref_name`, `parent_molecule_chembl_id`, `target_pref_name`, `target_organism`, `target_taxonomy_id` |
| Ассей | `assay_type`, `assay_description`, `assay_variant_accession`, `assay_variant_mutation` |
| Документ | `document_journal`, `document_year` |
| JSON | `activity_properties` |

**Статус:** ✅ Корректно

---

## 2. ChEMBL Molecule Pipeline

### Схема: `MoleculeSchema`
**Файл:** `src/bioetl/domain/schemas/chembl/molecule.py`

### Извлекаемые поля (52):

| Категория | Поля |
|-----------|------|
| Идентификаторы | `molecule_chembl_id` |
| Свойства | `pref_name`, `molecule_type`, `structure_type`, `max_phase`, `first_approval` |
| Флаги | `oral`, `parenteral`, `topical`, `therapeutic_flag`, `withdrawn_flag`, `black_box_warning`, `natural_product`, `first_in_class`, `prodrug`, `inorganic_flag`, `polymer_flag`, `chirality`, `dosed_ingredient`, `availability_type` |
| USAN | `usan_stem`, `usan_stem_definition`, `usan_substem`, `usan_year` |
| Биополимеры | `helm_notation`, `molecule_species` |
| Иерархия | `hierarchy_parent_chembl_id`, `hierarchy_active_chembl_id`, `hierarchy_child_chembl_id` |
| Физ-хим | `property_alogp`, `property_mw_freebase`, `property_full_mwt`, `property_hba`, `property_hbd`, `property_psa`, `property_rtb`, `property_ro5_violations`, `property_heavy_atoms`, `property_aromatic_rings`, `property_qed_weighted`, `property_full_molformula`, `property_ro3_pass` |
| Структура | `canonical_smiles`, `standard_inchi`, `inchikey` |
| JSON | `molecule_hierarchy`, `molecule_properties`, `molecule_structures`, `molecule_synonyms`, `cross_references`, `atc_classifications` |

### ⚠️ Предупреждение

| Поле | Проблема | Рекомендация |
|------|----------|--------------|
| `structure_standard_inchi_key` | Определено в схеме (строка 30), но не заполняется | Удалить из схемы или синхронизировать с `inchikey` |

---

## 3. PubChem Compound Pipeline

### Схема: `PubchemMoleculeSchema`
**Файл:** `src/bioetl/domain/schemas/pubchem/compound.py`

### Извлекаемые поля (40):

| Категория | Поля |
|-----------|------|
| Идентификаторы | `cid` |
| Структура | `canonical_smiles`, `isomeric_smiles`, `inchi`, `inchi_key`, `molecular_formula`, `iupac_name` |
| Физ-хим | `molecular_weight`, `exact_mass`, `monoisotopic_mass`, `xlogp`, `tpsa`, `complexity`, `charge` |
| Атомы/Связи | `heavy_atom_count`, `h_bond_donor_count`, `h_bond_acceptor_count`, `rotatable_bond_count` |
| Стереохимия | `atom_stereo_count`, `defined_atom_stereo_count`, `undefined_atom_stereo_count`, `bond_stereo_count`, `defined_bond_stereo_count`, `undefined_bond_stereo_count`, `isotope_atom_count`, `covalent_unit_count` |
| 3D | `volume_3d`, `conformer_count_3d`, `feature_acceptor_count_3d`, `feature_donor_count_3d`, `feature_anion_count_3d`, `feature_cation_count_3d`, `feature_ring_count_3d`, `feature_hydrophobe_count_3d`, `effective_rotor_count_3d`, `conformer_rmsd_3d`, `x_steric_quadrupole_3d`, `y_steric_quadrupole_3d`, `z_steric_quadrupole_3d`, `feature_count_3d` |

### ⚠️ Предупреждение

| Поле | Проблема | Рекомендация |
|------|----------|--------------|
| `inchi_key` vs `inchikey` | Схема: `inchi_key`, трансформер: `inchikey` | Унифицировать именование |

---

## 4. UniProt Protein Pipeline

### Схема: `UniprotTargetSchema`
**Файл:** `src/bioetl/domain/schemas/uniprot/protein.py`

### Извлекаемые поля (45):

| Категория | Поля |
|-----------|------|
| Идентификаторы | `accession`, `entry_name`, `entry_type`, `secondary_accessions` |
| Белковые имена | `protein_name`, `protein_short_names`, `protein_alternative_names`, `protein_ec_numbers`, `flag` |
| Гены | `gene_primary`, `gene_synonyms`, `gene_orf_names` |
| Организм | `organism_scientific`, `organism_common`, `taxonomy_id`, `lineage` |
| Доказательства | `protein_existence`, `annotation_score`, `reviewed` |
| Последовательность | `sequence`, `sequence_length`, `sequence_mass`, `sequence_checksum`, `sequence_modified` |
| Аудит | `entry_version`, `entry_created`, `entry_modified` |
| Функциональные | `function_comment`, `catalytic_activity`, `activity_regulation`, `subunit`, `pathway`, `subcellular_location`, `tissue_specificity`, `alternative_products`, `disease_involvement`, `similarity_comment`, `caution` |
| Cross-refs | `go_terms`, `drugbank_ids`, `chembl_ids`, `guidetopharmacology_ids` |
| Features | `features`, `keywords` |
| Счётчики | `cross_reference_count`, `feature_count`, `keyword_count`, `isoform_count` |

### 🔴 Критические ошибки

| Поле | Проблема | Локация |
|------|----------|---------|
| `pharmaceutical_use` | Определено в схеме (строка 249), НЕ извлекается в трансформере | `transformer.py:271-302` |
| `publication_count` | Определено в схеме (строка 309), НЕ вычисляется в трансформере | `transformer.py:321-328` |

---

## 5. PubMed Publication Pipeline

### Схема: `PubMedPublicationSchema`
**Файл:** `src/bioetl/domain/schemas/pubmed/publication.py`

### Извлекаемые поля (52):

| Категория | Поля |
|-----------|------|
| Идентификаторы | `pmid`, `doi`, `pii`, `mid`, `publisher_id`, `pmc_id` |
| Контент | `title`, `vernacular_title`, `abstract`, `abstract_structured` |
| Авторы | `authors`, `affiliations`, `structured_affiliations`, `author_count` |
| Журнал | `journal`, `journal_title`, `journal_iso_abbrev`, `journal_issn_type`, `issn`, `nlm_unique_id`, `country` |
| Pagination | `volume`, `issue`, `pages`, `medline_pgn`, `first_page`, `last_page` |
| Даты | `year`, `publication_date`, `pub_month`, `pub_day`, `accepted_date`, `received_date`, `revised_date`, `epub_date`, `date_completed`, `date_revised` |
| Статус | `publication_status`, `publication_type_list`, `publication_types` |
| Классификация | `mesh_terms`, `mesh_heading_count`, `chemicals`, `chemical_count`, `keywords`, `keyword_count`, `databanks`, `gene_symbols` |
| Счётчики | `grant_count`, `reference_count` |

### ⚠️ Предупреждение

| Поле | Проблема | Рекомендация |
|------|----------|--------------|
| `date_completed` | Всегда None (строка 507) | Извлечь из XML или удалить из схемы |
| `date_revised` | Всегда None (строка 508) | Извлечь из XML или удалить из схемы |

---

## 6. CrossRef Publication Pipeline

### Схема: `PublicationEnrichedSchema`
**Файл:** `src/bioetl/domain/schemas/crossref/publication.py`

### Извлекаемые поля (32):
`doi`, `title`, `abstract`, `authors`, `affiliations`, `journal`, `publisher`, `issn`, `issn_print`, `issn_electronic`, `year`, `publication_date`, `published_print`, `published_online`, `published`, `doc_type`, `citation_count`, `reference_count`, `language`, `license_url`, `subjects`, `content_domain_domains`, `content_domain_crossmark_restriction`, `alternative_id`, `short_container_title`, `author_orcids`, `author_details`, `references`, `pmid`, `pmc_id`, `is_oa`, `_source`, `_lookup_method`, `_original_id`

**Статус:** ✅ Корректно

---

## 7. OpenAlex Publication Pipeline

### Схема: `OpenAlexPublicationSchema`
**Файл:** `src/bioetl/domain/schemas/openalex/publication.py`

### Извлекаемые поля (35):
`openalex_id`, `doi`, `pmid`, `pmc_id`, `mag_id`, `title`, `abstract`, `authors`, `affiliations`, `journal`, `issn`, `publisher`, `year`, `publication_date`, `doc_type`, `is_oa`, `oa_status`, `citation_count`, `topics`, `primary_topic`, `grants`, `concepts`, `mesh`, `keywords`, `language`, `volume`, `issue`, `first_page`, `last_page`, `fwci`, `referenced_works_count`, `is_retracted`, `_lookup_method`, `_original_id`, `_source`

**Статус:** ✅ Корректно

---

## 8. SemanticScholar Publication Pipeline

### Схема: `SemanticScholarPublicationSchema`
**Файл:** `src/bioetl/domain/schemas/semanticscholar/publication.py`

### Извлекаемые поля (34):
`paper_id`, `doi`, `pmid`, `pmc_id`, `arxiv_id`, `dblp_id`, `corpus_id`, `title`, `abstract`, `tldr`, `authors`, `affiliations`, `author_s2_ids`, `author_orcids`, `author_h_indices`, `journal`, `volume`, `pages`, `first_page`, `last_page`, `venue`, `year`, `publication_date`, `citation_count`, `reference_count`, `influential_citation_count`, `is_oa`, `open_access_url`, `oa_status`, `fields_of_study`, `publication_types`, `citation_contexts`, `_source`, `_lookup_method`, `_original_id`

**Статус:** ✅ Корректно

---

## План исправлений

### Критические (P0) — Немедленно

| № | Проблема | Файл | Действие |
|---|----------|------|----------|
| 1 | UniProt: pharmaceutical_use | `transformer.py:271` | Добавить `CommentExtractor.extract_by_type(comments, "BIOTECHNOLOGY")` |
| 2 | UniProt: publication_count | `transformer.py:321` | Добавить подсчёт публикаций из references или PubMed cross-refs |

### Предупреждения (P1) — При следующем релизе

| № | Проблема | Файл | Действие |
|---|----------|------|----------|
| 3 | PubChem: inchi_key naming | `compound.py`, `transformer.py` | Унифицировать к `inchi_key` |
| 4 | ChEMBL: structure_standard_inchi_key | `molecule.py` | Удалить избыточное поле |
| 5 | PubMed: date_completed/revised | `transformer.py` | Извлечь из XML или удалить |

---

## Рекомендации по CI

1. Добавить архитектурный тест для проверки соответствия полей схем и трансформеров
2. Создать автоматический скрипт аудита `scripts/audit_field_mapping.py`
3. Интегрировать проверку в `make arch-test`
