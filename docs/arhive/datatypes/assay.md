# Assay (`assay`)

| Поле | Тип данных | Допустимые значения | Описание |
|------|------------|----------------------|----------|
| assay_chembl_id | строка | — | ChEMBL ID ассая. |
| aidx | строка | — | Внутренний индекс ассая/ID депозитора. |
| assay_category | строка | — | Категория теста (screening, confirmatory и т.д.). |
| assay_group | строка | — | Группа/серия, к которой относится тест. |
| assay_organism | строка | — | Организм системы тестирования. |
| assay_tax_id | целое (int) | — | NCBI Taxonomy ID организма. |
| assay_type | строка | — | Код типа (B, F, A, T, P и т.п.). |
| assay_type_description | строка | — | Текстовое описание типа (Binding, Functional и др.). |
| assay_cell_type | строка | — | Тип клетки (cell line/primary и т.п.). |
| assay_tissue | строка | — | Ткань/орган, использованные в тесте. |
| assay_test_type | строка | — | in vitro / in vivo и т.п. |
| assay_strain | строка | — | Штамм организма. |
| assay_subcellular_fraction | строка | — | Субклеточная фракция (microsomes, mitochondria и др.). |
| assay_classifications | список объектов | — | Классификации ассая (BAO и др.). |
| assay_parameters | список объектов | — | Параметры теста (type, value, units, standard_* и пр.). |
| bao_format | строка | — | BAO формат ассая. |
| bao_label | строка | — | Читабельная метка BAO‑формата. |
| cell_chembl_id | строка | — | ID клеточной линии (если тест на клетках). |
| tissue_chembl_id | строка | — | ID ткани (если тест на тканях). |
| variant_sequence | объект | — | Данные о варианте последовательности (accession, mutation и т.д.). |
| confidence_score | целое (int) | — | Скоринговая оценка уверенности в таргете (0–9). |
| confidence_description | строка | — | Текстовое описание уровня уверенности. |
| description | строка | — | Описание того, что измеряет ассай. |
| relationship_type | строка | — | Тип связи ассая с таргетом (direct, homologous и др.). |
| relationship_description | строка | — | Расшифровка `relationship_type`. |
| document_chembl_id | строка | — | Документ с описанием теста. |
| src_assay_id | строка | — | Идентификатор ассая в исходной БД (например, AID). |
| src_id | целое (int) | — | ID источника данных. |
| score | число (float) | — | Score для ранжирования ассая при поиске. |
| target_chembl_id | строка | — | ID таргета, на который ориентирован ассай. |
