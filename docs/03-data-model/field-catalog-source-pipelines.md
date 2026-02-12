# Каталог бизнес-полей source-пайплайнов

Область: только source-пайплайны (ChEMBL, PubChem, UniProt, PubMed, CrossRef, OpenAlex, Semantic Scholar). Служебные поля (`entity_id`, `content_hash`, `_run_id`, `_run_type`, `_source_batch_id`, `_source`, `_ingestion_ts`, `_index`, `_dq_error`, `_dq_warn`) опущены и описаны кратко в конце. Типы взяты из PyArrow-схем `src/bioetl/infrastructure/schemas/silver.py`, семантика — из комментариев схем и профильных docs.

Формат таблиц: `поле | тип | что хранится / правило`.

## ChEMBL

### chembl_publication
| Поле | Тип | Описание |
|---|---|---|
| authors | string | JSON-массив авторов (строки) |
| title | string | Заголовок публикации |
| journal | string | Название журнала |
| publication_year | int64 | Год публикации |
| volume | string | Том издания |
| issue | string | Номер выпуска |
| page_first | string | Первая страница (нормализовано) |
| page_last | string | Последняя страница (нормализовано) |
| document_chembl_id | string | PK документа ChEMBL |
| doi | string | DOI без префикса https://doi.org/ |
| pmc_id | string | PubMed Central ID |
| pmid | string | PubMed ID (строкой) |
| abstract | string | Аннотация |
| affiliation_list | string | JSON-массив аффилиаций (для ChEMBL — пусто) |
| author_orcids | string | JSON-массив ORCID (для ChEMBL — пусто) |
| publication_type | string | Тип из ChEMBL, приведённый к unified |
| publication_type_unified | string | Тип публикации L3 (Journal Article и т.п.) |
| publication_subclass | string | Подкласс L2 |
| publication_class | string | Класс L1 (`EXP`/`REV`/`PEER`) |
| publication_date | string | Дата публикации (YYYY-MM-DD, обычно null для ChEMBL) |
| language | string | Язык (обычно null) |
| is_oa | bool | Флаг open access (обычно null) |
| src_id | int64 | Идентификатор источника записи |
| citations_received | int64 | Кол-во входящих цитат (unified) |
| citations_made | int64 | Кол-во исходящих ссылок (unified) |
| chembl_release | string | Версия ChEMBL (CHEMBL_XX) |
| creation_date | string | Дата создания записи (YYYY-MM-DD) |

### chembl_activity
| Поле | Тип | Описание |
|---|---|---|
| action_type_action_type | string | Тип действия (ChEMBL action_type) |
| action_type_description | string | Описание action_type |
| action_type_parent_type | string | Родительский тип action_type |
| activity_comment | string | Комментарий к измерению |
| activity_id | string | PK активности |
| activity_properties | string | JSON со свойствами активности |
| assay_chembl_id | string | FK на анализ |
| assay_description | string | Описание анализа |
| assay_type | string | Тип анализа |
| assay_variant_accession | string | Accession варианта белка |
| assay_variant_mutation | string | Мутация варианта |
| bao_endpoint | string | BAO endpoint |
| bao_format | string | BAO формат |
| bao_label | string | BAO метка |
| canonical_smiles | string | Канонический SMILES лиганда |
| data_validity_comment | string | Комментарий валидности данных |
| data_validity_description | string | Описание валидности |
| document_chembl_id | string | FK на публикацию |
| document_journal | string | Журнал из документа |
| document_year | int64 | Год публикации документа |
| ligand_efficiency_bei | float64 | Binding Efficiency Index |
| ligand_efficiency_le | float64 | Ligand Efficiency |
| ligand_efficiency_lle | float64 | Lipophilic Ligand Efficiency |
| ligand_efficiency_sei | float64 | Surface Efficiency Index |
| manual_curation_flag | float64 | Флаг ручной проверки (nullable int) |
| molecule_chembl_id | string | FK на молекулу |
| molecule_pref_name | string | Предпочтительное имя молекулы |
| original_activity_id | float64 | Исходный ID активности |
| parent_molecule_chembl_id | string | Родительская молекула |
| pchembl_value | float64 | pChEMBL значение |
| potential_duplicate | int64 | Флаг потенциального дубликата |
| qudt_units | string | QUDT единицы |
| record_id | int64 | ID записи активности |
| relation | string | Отношение (`=`, `>`, `<`) |
| src_id | int64 | Источник данных |
| standard_flag | int64 | Флаг стандартизации |
| standard_relation | string | Стандартизированное отношение |
| standard_text_value | string | Текстовое значение (стандартиз.) |
| standard_type | string | Стандартизированный тип измерения |
| standard_units | string | Стандартизированные единицы |
| standard_upper_value | float64 | Верхняя граница значения |
| standard_value | float64 | Стандартизированное числовое значение |
| target_chembl_id | string | FK на мишень |
| target_organism | string | Организм мишени |
| target_pref_name | string | Предпочтительное имя мишени |
| target_taxonomy_id | string | NCBI Taxonomy ID мишени (унифицированное имя) |
| text_value | string | Исходное текстовое значение |
| toid | float64 | Target Ontology ID (nullable int) |
| type | string | Тип активности |
| units | string | Единицы (сырье) |
| uo_units | string | Единицы из Unit Ontology |
| upper_value | float64 | Верхняя граница (сырье) |
| value | float64 | Значение (сырье) |

### chembl_assay
| Поле | Тип | Описание |
|---|---|---|
| aidx | string | Внутренний ID анализа |
| assay_category | string | Категория анализа |
| assay_cell_type | string | Тип клетки |
| assay_chembl_id | string | PK анализа |
| assay_classifications | string | JSON классификаций |
| assay_group | string | Группа анализа |
| assay_organism | string | Организм |
| assay_parameters | string | JSON параметров |
| assay_pref_name | string | Предпочтительное имя |
| assay_strain | string | Штамм |
| assay_subcellular_fraction | string | Субклеточная фракция |
| assay_taxonomy_id | float64 | Таксономия (nullable int) |
| assay_test_type | string | Тип теста |
| assay_tissue | string | Ткань |
| assay_type | string | Тип (из API) |
| assay_type_description | string | Описание типа |
| bao_format | string | BAO формат |
| bao_label | string | BAO метка |
| cell_chembl_id | string | FK на клеточную линию |
| confidence_description | string | Описание confidence_score |
| confidence_score | int64 | Оценка уверенности |
| description | string | Описание анализа |
| document_chembl_id | string | FK на публикацию |
| relationship_description | string | Описание отношения к мишени |
| relationship_type | string | Тип отношения |
| score | float64 | Счёт анализа |
| src_assay_id | string | Исходный ID анализа |
| src_id | int64 | Источник данных |
| target_chembl_id | string | FK на мишень |
| tissue_chembl_id | string | FK на ткань |
| variant_accession | string | Accession варианта |
| variant_isoform | string | Изоформа |
| variant_mutation | string | Мутация |
| variant_organism | string | Организм варианта |
| variant_sequence | string | Последовательность |
| variant_sequence_json | string | JSON исходной последовательности |
| variant_taxonomy_id | float64 | Таксономия варианта (nullable int) |

### chembl_assay_parameters
| Поле | Тип | Описание |
|---|---|---|
| assay_chembl_id | string | FK на анализ |
| assay_param_id | int64 | PK параметра |
| comments | string | Комментарий |
| relation | string | Исходное отношение |
| standard_relation | string | Стандартизированное отношение |
| standard_text_value | string | Текстовое значение (стандартиз.) |
| standard_type | string | Стандартизированный тип параметра |
| standard_units | string | Стандартизированные единицы |
| standard_value | float64 | Стандартизированное значение |
| text_value | string | Исходное текстовое значение |
| type | string | Тип параметра |
| units | string | Единицы измерения |
| value | float64 | Числовое значение |

### chembl_target
| Поле | Тип | Описание |
|---|---|---|
| component_accessions | list<string> | Accession компонентов |
| component_descriptions | list<string> | Описания компонентов |
| component_id | float64 | ID компонента (nullable) |
| component_ids | list<int64> | Список ID компонентов |
| component_relationships | list<string> | Связи компонентов |
| component_types | list<string> | Типы компонентов |
| cross_references | string | JSON кросс-референсов |
| downgraded | bool | Флаг понижения статуса |
| organism | string | Организм |
| pipeline_stages | string | JSON стадий пайплайна |
| pref_name | string | Предпочтительное имя мишени |
| species_group_flag | bool | Флаг групповой мишени |
| target_chembl_id | string | PK мишени |
| target_component_synonyms | string | Синонимы компонентов (JSON) |
| target_components | string | Компоненты (JSON) |
| target_type | string | Тип мишени |
| taxonomy_id | float64 | NCBI Taxonomy ID (nullable) |

### chembl_target_component
| Поле | Тип | Описание |
|---|---|---|
| accession | string | UniProt accession |
| component_id | int64 | PK компонента |
| component_type | string | Тип компонента |
| description | string | Описание |
| organism | string | Организм |
| protein_classification_id | int64 | Основной класс белка |
| protein_classification_ids | list<int64> | Все классы белка |
| protein_classifications | string | Исходный JSON классификаций |
| target_component_synonyms | string | Синонимы (JSON) |
| target_component_xrefs | string | Кросс-референсы (JSON) |
| taxonomy_id | int64 | NCBI Taxonomy ID |

### chembl_cell_line
| Поле | Тип | Описание |
|---|---|---|
| cell_chembl_id | string | PK клеточной линии |
| cell_description | string | Описание |
| cell_name | string | Имя линии |
| cell_source_organism | string | Организм источника |
| cell_source_taxonomy_id | int64 | Таксономия источника |
| cell_source_tissue | string | Ткань источника |
| cellosaurus_id | string | Cellosaurus ID |
| cl_lincs_id | string | LINCS ID |
| efo_id | string | EFO ID |

### chembl_tissue
| Поле | Тип | Описание |
|---|---|---|
| bto_id | string | BRENDA Tissue Ontology ID |
| caloha_id | string | CALIPHO ID |
| efo_id | string | EFO ID |
| pref_name | string | Предпочтительное имя ткани |
| tissue_chembl_id | string | PK ткани |
| uberon_id | string | Uberon ID |

### chembl_subcellular_fraction
| Поле | Тип | Описание |
|---|---|---|
| assay_count | int64 | Кол-во анализов с этой фракцией |
| example_assay_chembl_id | string | Пример ChEMBL assay |
| subcellular_fraction | string | Название фракции (PK) |

### chembl_document_term
| Поле | Тип | Описание |
|---|---|---|
| document_chembl_id | string | PK публикации |
| mesh_id | string | MeSH ID |
| qualifier | string | Квалификатор MeSH |
| term | string | Терм MeSH |
| term_type | string | Тип терма |

### chembl_molecule
| Поле | Тип | Описание |
|---|---|---|
| atc_classifications | string | ATC классификации (JSON) |
| availability_type | float64 | Тип доступности (nullable int) |
| black_box_warning | int64 | BBW флаг |
| canonical_smiles | string | Канонический SMILES |
| chirality | int64 | Хиральность |
| cross_references | string | JSON кросс-референсов |
| dosed_ingredient | int64 | Флаг дозируемого ингредиента |
| first_approval | float64 | Год первого одобрения (nullable int) |
| first_in_class | int64 | Флаг первого в классе |
| helm_notation | string | HELM нотация |
| hierarchy_active_chembl_id | string | Активный ID в иерархии |
| hierarchy_child_chembl_id | string | Дочерний ID |
| hierarchy_parent_chembl_id | string | Родительский ID |
| inchikey | string | InChIKey |
| inorganic_flag | int64 | Флаг неорганичности |
| max_phase | int64 | Максимальная фаза клинических испытаний |
| molecule_chembl_id | string | PK молекулы |
| molecule_hierarchy | string | JSON иерархии |
| molecule_properties | string | JSON свойств |
| molecule_species | string | Вид |
| molecule_structures | string | JSON структур |
| molecule_synonyms | string | Синонимы (JSON) |
| molecule_type | string | Тип молекулы |
| natural_product | int64 | Флаг натурального происхождения |
| oral | bool | Пероральность |
| parenteral | bool | Парентеральность |
| polymer_flag | int64 | Полимер флаг |
| pref_name | string | Предпочтительное имя |
| prodrug | int64 | Флаг пролекарства |
| property_alogp | float64 | ALogP |
| property_aromatic_rings | int64 | Кол-во ароматических колец |
| property_full_molformula | string | Полная формула |
| property_full_mwt | float64 | Полная мол. масса |
| property_hba | int64 | Кол-во акцепторов H |
| property_hbd | int64 | Кол-во доноров H |
| property_heavy_atoms | int64 | Кол-во тяжёлых атомов |
| property_mw_freebase | float64 | Мол. масса freebase |
| property_psa | float64 | Полярная площадь |
| property_qed_weighted | float64 | QED (взвеш.) |
| property_ro3_pass | string | Соответствие RO3 |
| property_ro5_violations | int64 | Нарушения RO5 |
| property_rtb | int64 | Кол-во вращаемых связей |
| standard_inchi | string | Standard InChI |
| structure_type | string | Тип структуры |
| therapeutic_flag | bool | Флаг лекарственного средства |
| topical | bool | Наружное применение |
| usan_stem | string | USAN стем |
| usan_stem_definition | string | Описание стема |
| usan_substem | string | Substem |
| usan_year | float64 | Год присвоения USAN (nullable int) |
| withdrawn_flag | bool | Флаг отзыва |

### chembl_compound_record
| Поле | Тип | Описание |
|---|---|---|
| compound_key | string | Ключ соединения из документа |
| compound_name | string | Имя соединения из документа |
| document_chembl_id | string | FK на публикацию |
| molecule_chembl_id | string | FK на молекулу |
| record_id | int64 | ID записи |
| src_compound_id | string | ID соединения в источнике |
| src_id | int64 | Источник данных |

### chembl_document_similarity
| Поле | Тип | Описание |
|---|---|---|
| avg_tani | float64 | Средний Tanimoto |
| doc_1 | int64 | Doc ID 1 |
| doc_2 | int64 | Doc ID 2 |
| max_tani | float64 | Максимальный Tanimoto |
| mol_tani | float64 | Tanimoto по молекулам |
| pubmed_id1 | string | PubMed ID 1 |
| pubmed_id2 | string | PubMed ID 2 |
| sim_id | int64 | ID похожести |
| tid_tani | float64 | Tanimoto по target |

## PubChem

### pubchem_compound
| Поле | Тип | Описание |
|---|---|---|
| canonical_smiles | string | Канонический SMILES |
| cid | string | PubChem CID (PK, строкой) |
| complexity | float64 | Сложность |
| conformer_count_3d | float64 | Кол-во конформеров 3D |
| conformer_rmsd_3d | float64 | RMSD конформеров |
| effective_rotor_count_3d | float64 | Эффективные ротаторы |
| exact_mass | float64 | Точная масса |
| feature_acceptor_count_3d | float64 | 3D акцепторы |
| feature_anion_count_3d | float64 | 3D анионы |
| feature_cation_count_3d | float64 | 3D катионы |
| feature_count_3d | float64 | Всего 3D фичей |
| feature_donor_count_3d | float64 | 3D доноры |
| feature_hydrophobe_count_3d | float64 | 3D гидрофобы |
| feature_ring_count_3d | float64 | 3D кольца |
| inchi | string | InChI |
| inchikey | string | InChIKey |
| isomeric_smiles | string | Изомерный SMILES |
| iupac_name | string | IUPAC имя |
| molecular_formula | string | Молекулярная формула |
| molecular_weight | float64 | Молекулярная масса |
| monoisotopic_mass | float64 | Моноизотопная масса |
| tpsa | float64 | Полярная площадь |
| x_steric_quadrupole_3d | float64 | Стерический квадруполь X |
| xlogp | float64 | XlogP |
| y_steric_quadrupole_3d | float64 | Стерический квадруполь Y |
| z_steric_quadrupole_3d | float64 | Стерический квадруполь Z |

## UniProt

### uniprot_protein
| Поле | Тип | Описание |
|---|---|---|
| accession | string | UniProt accession (PK) |
| acetylation | string | Места ацетилирования (PTM) |
| active_sites | string | Активные сайты (JSON) |
| activity_regulation | string | Регуляция активности |
| annotation_score | int64 | Качество аннотации (1–5) |
| binding_sites | string | Узлы связывания (JSON) |
| catalytic_activity | string | Каталитическая активность |
| cellular_component | string | GO: клеточный компонент |
| chembl_ids | string | Кросс-референсы ChEMBL target (JSON) |
| disease_involvement | string | Заболевания |
| disulfide_bond | string | Дисульфидные связи |
| domains | string | Домены (JSON) |
| drugbank_ids | string | DrugBank IDs (JSON) |
| entry_name | string | UniProt entry name |
| features_json | string | Полный JSON фичей |
| function_comment | string | Комментарий функции |
| gene_names | list<string> | Синонимы генов |
| genus | string | Род (таксономия) |
| glycosylation | string | Гликозилирование |
| go_terms | string | GO аннотации (JSON) |
| interpro_xrefs | string | InterPro IDs (JSON) |
| intramembrane | string | Внутримембранные области |
| isoform_ids | string | ID изоформ |
| isoform_names | string | Имена изоформ |
| isoform_synonyms | string | Синонимы изоформ |
| lipidation | string | Липидация |
| modified_residue | string | Модифицированные остатки |
| molecular_function | string | GO: мол. функция |
| organism_id | int64 | NCBI Taxonomy ID |
| pathway | string | Пути (Reactome/KEGG) |
| pdb_xrefs | string | PDB ID (JSON) |
| pfam_xrefs | string | Pfam ID (JSON) |
| phosphorylation | string | Фосфорилирование |
| phylum | string | Тип (таксономия) |
| propeptide | string | Пропептиды |
| protein_existence | string | Уровень доказательств |
| protein_name | string | Реком. имя белка |
| reaction_ec_numbers | string | EC номера реакций |
| reactions | string | Описания реакций |
| reactome_xrefs | string | Reactome IDs (JSON) |
| reviewed | bool | Swiss-Prot (true) / TrEMBL (false) |
| sequence_length | int64 | Длина последовательности |
| signal_peptide | string | Сигнальный пептид |
| similarity_comment | string | Комм. схожести |
| subcellular_location | string | Локализация |
| superkingdom | string | Надцарство |
| tissue_specificity | string | Тканевая специфичность |
| topology | string | Топология |
| transmembrane | string | Трансмембранные области |
| ubiquitination | string | Убиквитинирование |

### uniprot_idmapping
| Поле | Тип | Описание |
|---|---|---|
| all_mappings | string | JSON списка маппингов |
| annotation_score | int64 | Оценка качества (1–5) |
| gene_primary | string | Основное имя гена |
| mapping_status | string | Статус (`found`/`not_found`/`error`/`multiple`) |
| organism_common | string | Обычное название организма |
| organism_scientific | string | Научное название |
| protein_name | string | Имя белка |
| reviewed | bool | Swiss-Prot / TrEMBL |
| sequence_length | int64 | Длина последовательности |
| sequence_mass | int64 | Масса (Да) |
| target_chembl_id | string | Входной ChEMBL target ID |
| taxonomy_id | int64 | NCBI Taxonomy ID |
| uniprot_accession | string | UniProt accession (выход) |
| uniprot_entry_name | string | Entry name |

## PubMed

### pubmed_publication
| Поле | Тип | Описание |
|---|---|---|
| _lookup_method | string | Метод поиска (direct/doi/pmid/title_fallback/unknown) |
| _original_id | string | Идентификатор запроса |
| abstract | string | Аннотация |
| abstract_structured | bool | Есть ли структурированные секции |
| affiliation_list | string | Уникальные аффилиации (JSON) |
| affiliation_structured | string | Структурированные аффилиации (ROR/GRID) |
| author_count | int64 | Кол-во авторов |
| authors | string | Список авторов (JSON) |
| authors_with_affiliations | string | Авторы с аффилиациями (JSON) |
| chemical_count | int64 | Кол-во хим. веществ |
| chemicals | string | Вещества (JSON) |
| citation_subset | string | Citation subset codes |
| citations_made | int64 | Исходящие ссылки |
| country | string | Страна публикации |
| databanks | string | Датабанки (JSON) |
| date_completed | string | Дата завершения MEDLINE обработки |
| date_revised | string | Дата ревизии записи |
| doi | string | DOI |
| gene_symbols | string | Ген-символы (JSON) |
| grant_count | int64 | Кол-во грантов |
| issn | string | ISSN |
| issue | string | Номер выпуска |
| journal | string | Название журнала |
| journal_iso_abbrev | string | ISO аббревиатура журнала |
| journal_issn_type | string | Тип ISSN (Print/Electronic/Linking) |
| journal_name_short | string | Короткое имя журнала |
| keyword_count | int64 | Кол-во ключевых слов |
| language | string | Язык |
| medline_pgn | string | Оригинальная пагинация |
| mesh_heading_count | int64 | Кол-во MeSH терминов |
| nlm_unique_id | string | NLM catalog ID |
| page_first | string | Первая страница |
| page_last | string | Последняя страница |
| page_range | string | Диапазон страниц |
| pmc_id | string | PubMed Central ID |
| pmid | string | PubMed ID |
| pub_date | string | Дата публикации (сырье) |
| pub_day | int64 | День публикации |
| pub_month | int64 | Месяц публикации |
| publication_class | string | Класс L1 |
| publication_date | string | Дата (YYYY-MM-DD) |
| publication_status | string | Статус (`ppublish`/`epublish`/`aheadofprint`) |
| publication_subclass | string | Подкласс L2 |
| publication_type | string | Тип (unified) |
| publication_type_list | string | Список типов (JSON) |
| publication_type_unified | string | Тип L3 |
| publication_types | list<string> | Типы (список) |
| publication_year | int64 | Год |
| subject_keywords | list<string> | Авторские ключевые слова |
| subject_mesh | list<string> | MeSH термины |
| title | string | Заголовок |
| volume | string | Том |

## CrossRef

### crossref_publication
| Поле | Тип | Описание |
|---|---|---|
| _lookup_method | string | direct/doi/pmid/title_fallback/unknown |
| _original_id | string | Исходный идентификатор |
| abstract | string | Аннотация (часто null) |
| affiliation_list | string | Аффилиации (часто null) |
| alternative_id | list<string> | Альтернативные ID издателя |
| author_details | string | JSON авторов |
| author_orcids | string | ORCID (JSON) |
| authors | string | Список авторов (JSON) |
| citations_made | int64 | references-count (исходящие) |
| citations_received | int64 | is-referenced-by-count (входящие) |
| content_domain_crossmark_restriction | bool | Ограничения Crossmark |
| content_domain_domains | list<string> | Домены контента |
| doi | string | DOI (PK) |
| issn | string | ISSN |
| issn_electronic | string | Электронный ISSN |
| issn_list | string | Все ISSN (JSON) |
| issn_print | string | Печатный ISSN |
| issue | string | Выпуск |
| journal | string | Журнал |
| journal_name_short | string | Короткое имя журнала |
| language | string | Язык |
| license_url | string | URL лицензии |
| page_first | string | Первая страница |
| page_last | string | Последняя страница |
| pmc_id | string | PMC ID (обычно null) |
| pmid | string | PMID (обычно null) |
| publication_class | string | Класс L1 |
| publication_date | string | Дата (YYYY-MM-DD) |
| publication_subclass | string | Подкласс L2 |
| publication_type | string | Тип CrossRef (raw type) |
| publication_type_unified | string | Тип L3 |
| publication_year | int64 | Год |
| published | string | Каноническая дата публикации |
| published_online | string | Дата онлайн публикации |
| published_print | string | Дата печати |
| publisher | string | Издатель |
| references | string | JSON массива ссылок |
| subject_keywords | list<string> | Ключевые слова |
| title | string | Заголовок |
| volume | string | Том |

## OpenAlex

### openalex_publication
| Поле | Тип | Описание |
|---|---|---|
| _lookup_method | string | direct/doi/pmid/title_fallback/unknown |
| _original_id | string | Исходный ID |
| abstract | string | Аннотация |
| affiliation_list | string | Аффилиации (JSON) |
| author_openalex_ids | string | OpenAlex IDs авторов (JSON) |
| author_orcids | string | ORCID авторов (JSON) |
| authors | string | Список авторов (JSON) |
| citations_made | int64 | Кол-во ссылок (referenced_works_count) |
| citations_received | int64 | Кол-во цитирований (cited_by_count) |
| doi | string | DOI |
| fwci | float64 | Field-Weighted Citation Impact |
| grants | string | Гранты (JSON) |
| institution_country_codes | list<string> | Коды стран организаций |
| institution_ids | list<string> | ID организаций |
| is_oa | bool | Open access |
| is_retracted | bool | Флаг отзыва |
| issn | string | ISSN |
| issue | string | Выпуск |
| journal | string | Журнал |
| language | string | Язык |
| mag_id | string | Microsoft Academic Graph ID |
| oa_status | string | OA статус |
| openalex_id | string | PK OpenAlex |
| page_first | string | Первая страница |
| page_last | string | Последняя страница |
| pmc_id | string | PMC ID (обычно null) |
| pmid | string | PMID (если есть) |
| primary_topic | string | Основная тема (JSON) |
| publication_class | string | Класс L1 |
| publication_date | string | Дата (YYYY-MM-DD) |
| publication_subclass | string | Подкласс L2 |
| publication_type | string | Тип OpenAlex (article/book/...) |
| publication_type_unified | string | Тип L3 |
| publication_year | int64 | Год |
| publisher | string | Издатель |
| ror_ids | string | ROR ID организаций (JSON) |
| subject_keywords | list<string> | Ключевые слова |
| subject_mesh | list<string> | MeSH (если есть) |
| subject_topics | string | Темы (JSON) |
| title | string | Заголовок |
| volume | string | Том |

## Semantic Scholar

### semanticscholar_publication
| Поле | Тип | Описание |
|---|---|---|
| _lookup_method | string | Метод поиска |
| _original_id | string | Исходный ID |
| abstract | string | Аннотация |
| affiliation_list | string | Аффилиации (JSON) |
| author_h_indices | string | h-index авторов (JSON) |
| author_orcids | string | ORCID (JSON) |
| author_s2_ids | string | S2 IDs авторов (JSON) |
| citation_contexts | string | Контексты цитирования (JSON) |
| citations_made | int64 | Кол-во ссылок (referenceCount) |
| citations_received | int64 | Кол-во цитирований (citationCount) |
| corpus_id | int64 | Corpus ID |
| dblp_id | string | DBLP ID |
| doi | string | DOI |
| influential_citation_count | int64 | Влиятельные цитаты |
| is_oa | bool | Open access |
| issue | string | Выпуск |
| journal | string | Журнал |
| oa_status | string | OA статус |
| open_access_url | string | OA URL |
| page_first | string | Первая страница |
| page_last | string | Последняя страница |
| page_range | string | Диапазон страниц |
| paper_id | string | PK Semantic Scholar |
| pmc_id | string | PMC ID |
| pmid | string | PMID |
| publication_class | string | Класс L1 |
| publication_date | string | Дата |
| publication_subclass | string | Подкласс L2 |
| publication_type | string | Тип (joined publicationTypes) |
| publication_type_unified | string | Тип L3 |
| publication_types | string | Исходный список типов (JSON) |
| publication_year | int64 | Год |
| subject_fields | string | Тематические поля |
| title | string | Заголовок |
| tldr | string | Краткое summary |
| volume | string | Том |

## Системные и DQ поля (общие)
- `entity_id`: бизнес-ключ записи (строка).
- `content_hash`: SHA256 содержимого для дедупликации.
- `_run_id`, `_run_type`: идентификатор и тип запуска пайплайна.
- `_source_batch_id`: ID партии источника.
- `_source`: идентификатор провайдера (есть не во всех схемах).
- `_ingestion_ts`: метка загрузки (UTC, ISO-8601 как строка).
- `_index`: порядковый номер записи в партии.
- `_dq_error`, `_dq_warn`: флаги контроля качества (True/False).

