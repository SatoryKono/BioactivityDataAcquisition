# Molecule Form fields

| field_name           | data_type | is_nullable | is_filterable | description                                                  | example_value        | notes |
|----------------------|----------|------------|--------------|--------------------------------------------------------------|----------------------|-------|
| molecule_chembl_id   | string   | no         | yes          | ChEMBL ID конкретной формы (соль, сольват, изомер и т.п.)   | CHEMBL278020         | Используется в URL `molecule_form/{id}`. |
| parent_chembl_id     | string   | no         | yes          | ChEMBL ID родительской молекулы                             | CHEMBL660            | Фильтр `parent_chembl_id=...`. |
| relationship_type    | string   | yes        | yes?         | Тип отношения (SALT_OF, PARENT, HYDRATE_OF и т.п.)           | SALT_OF              | Имя и набор значений нужно подтвердить в `/schema`. |
