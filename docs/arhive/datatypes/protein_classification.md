# Protein Classification fields

| field_name               | data_type | is_nullable | is_filterable | description                                                       | example_value                   | notes |
|--------------------------|----------|------------|--------------|-------------------------------------------------------------------|---------------------------------|-------|
| protein_classification_id| integer  | no         | yes          | Внутренний ID класса                                             | 2673                            | |
| pref_name                | string   | no         | yes          | Название белкового класса                                       | Receptor tyrosine kinases       | |
| parent_id                | integer  | yes        | yes          | ID родительского класса                                         | 123                             | |
| class_level              | integer  | yes        | yes          | Уровень в иерархии (1–4)                                        | 3                               | |
| l1                       | string   | yes        | yes          | Название класса верхнего уровня                                 | Enzymes                         | |
| l2                       | string   | yes        | yes          | Второй уровень классификации                                    | Kinases                         | |
| l3                       | string   | yes        | yes          | Третий уровень                                                   | Tyrosine kinases                | |
| l4                       | string   | yes        | yes          | Четвертый уровень                                                | EGFR family                     | |
| replaced_by              | integer  | yes        | ?            | Если класс устарел, ID класса, который его заменил              | 2810                            | |
