# Target Component (`target_component`)

| Поле | Тип данных | Допустимые значения | Описание |
|------|------------|----------------------|----------|
| component_id | целое (int) | — | Внутренний ID компоненты (PK). |
| accession | строка | — | Accession последовательности (UniProt и др.). |
| component_type | строка | — | Тип компоненты (PROTEIN, DNA, RNA и т.п.). |
| description | строка | — | Описание/имя компоненты. |
| organism | строка | — | Организм, откуда взята последовательность. |
| tax_id | целое (int) | — | NCBI Taxonomy ID. |
| sequence | строка | — | Представительная последовательность. |
| go_slims | список объектов | — | Связанные GO Slim термины. |
| protein_classifications | список объектов | — | Идентификаторы protein_classification. |
| target_component_synonyms | список объектов | — | Синонимы компоненты. |
| target_component_xrefs | список объектов | — | Внешние ссылки (xref_id, xref_name, xref_src_db). |
| targets | список объектов | — | Таргеты, содержащие эту компоненту. |
