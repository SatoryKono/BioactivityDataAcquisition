# Document Term fields

| field_name          | data_type | is_nullable | is_filterable | description                                                                 | example_value                  | notes |
|---------------------|----------|------------|--------------|-----------------------------------------------------------------------------|--------------------------------|-------|
| document_chembl_id  | string   | no         | yes          | ChEMBL ID документа, к которому относится термин                           | CHEMBL1124199                  | Подтверждено в примерах API. |
| term_text           | string   | no         | yes          | Нормализованный текст термина (ключевое слово, фраза)                      | inverse agonist activity       | |
| score               | number   | no         | yes          | Числовая значимость термина для документа                                  | 590                            | Используется для сортировки `order_by=-score`. |
