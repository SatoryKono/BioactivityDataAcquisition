# Assay fields

| field_name          | data_type | is_nullable | is_filterable | description                                                          | example_value              | notes |
|---------------------|----------|------------|--------------|----------------------------------------------------------------------|----------------------------|-------|
| assay_chembl_id     | string   | no         | yes          | ChEMBL ID ассая                                                      | CHEMBL615117              | Основной внешний ID. |
| assay_category      | string   | yes        | yes?         | Категория ассая (primary, confirmatory, screening и т.п.)            | null                       | Требует проверки на реальных данных. |
| assay_cell_type     | string   | yes        | yes          | Тип клетки, если ассай клеточный                                    | null                       | |
| assay_test_type     | string   | yes        | yes          | Тип теста (in vitro / in vivo / ex vivo и т.п.)                      | null                       | |
| assay_tissue        | string   | yes        | yes          | Описание ткани                                                       | null                       | |
| assay_type          | string   | no         | yes          | Тип ассая (`B` – binding, `F` – functional и т.д.)                   | B                          | Часто используется в фильтрах. |
| assay_type_description | string| yes        | ?            | Текстовое описание `assay_type`                                      | Binding                    | |
| cell_chembl_id      | string   | yes        | yes          | Ссылка на клеточную линию                                           | null                       | Связь на `/cell_line`. |
| confidence_score    | integer  | yes        | yes          | Уверенность маппинга ассая к таргету (0–9)                           | 8                          | Рекомендуется фильтр ≥7/8. |
| description         | string   | yes        | yes          | Описание теста                                                       | The compound was tested for the in ... | Можно использовать `__icontains`. |
| document_chembl_id  | string   | yes        | yes          | Документ, описывающий ассай                                         | CHEMBL1125582              | Связь с `/document`. |
| target_chembl_id    | string   | yes        | yes          | ChEMBL ID таргета                                                   | CHEMBL2741                 | Связь с `/target`. |
| tissue_chembl_id    | string   | yes        | yes          | ChEMBL ID ткани                                                     | null                       | Связь с `/tissue`. |
| variant_sequence    | string   | yes        | ?            | Последовательность варианта белка                                   | null                       | Для мутантных таргетов. |
