# Target Component fields

| field_name               | data_type | is_nullable | is_filterable | description                                                       | example_value       | notes |
|--------------------------|----------|------------|--------------|-------------------------------------------------------------------|---------------------|-------|
| component_id             | integer  | no         | yes          | Внутренний ID белкового компонента                               | 4879                | Используется в `target_component/{id}`. |
| accession                | string   | no         | yes          | UniProt accession                                                 | Q13936              | |
| component_type           | string   | yes        | yes?         | Тип компонента (PROTEIN, NUCLEIC_ACID и т.п.)                     | PROTEIN             | |
| organism                 | string   | yes        | yes          | Организм, которому принадлежит последовательность                | Homo sapiens        | |
| sequence                 | string   | yes        | no           | Аминокислотная последовательность                                | MENSDS...           | Большое текстовое поле. |
| protein_classification_id| integer  | yes        | yes          | FK на protein_classification                                     | 1173                | |
| go_slims                 | array    | yes        | ?            | Связанные GO slim термины                                        | [GO:0005886, ...]   | Список идентификаторов. |
| target_component_synonyms| array    | yes        | ?            | Синонимы компонента (генные символы и т.п.)                      | [{"component_synonym": "CYP3A4"}] | Структура элементов нужно проверить по `/schema`. |
