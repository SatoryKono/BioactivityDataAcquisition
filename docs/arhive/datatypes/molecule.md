# Molecule (`molecule`)

| Поле | Тип данных | Допустимые значения | Описание |
|------|------------|----------------------|----------|
| molecule_chembl_id | строка | — | ChEMBL ID молекулы. |
| pref_name | строка | — | Курируемое имя соединения. |
| molecule_type | строка | — | Тип (Small molecule, Protein, Antibody и т.п.). |
| structure_type | строка | — | Тип структурного представления (MOL, SEQUENCE и др.). |
| max_phase | целое (int) | 0–4 | Максимальная клиническая фаза. |
| first_approval | целое (int) | — | Год первого одобрения (если есть). |
| first_in_class | целое (int) | — | Флаг «первый в классе» (код-число). |
| availability_type | целое (int) | 0, 1, 2 | 0 — снят с рынка, 1 — Rx only, 2 — OTC. |
| black_box_warning | целое (int) | 0, 1 | 1 — есть black box warning. |
| dosed_ingredient | логическое | true/false | Используется как дозируемый ингредиент. |
| therapeutic_flag | логическое | true/false | Является терапевтическим агентом. |
| polymer_flag | целое (int) | — | Флаг полимерной природы. |
| natural_product | целое (int) | — | Флаг природного происхождения. |
| prodrug | целое (int) | — | Флаг «пролекарство». |
| chemical_probe | целое (int) | — | Флаг chemical probe. |
| orphan | целое (int) | — | Orphan‑drug статус (код). |
| veterinary | целое (int) | — | Флаг ветеринарного применения. |
| chirality | целое (int) | — | Код хиральности. |
| inorganic_flag | целое (int) | — | Флаг неорганического соединения. |
| oral | логическое | true/false | Оральное применение. |
| parenteral | логическое | true/false | Парентеральное применение. |
| topical | логическое | true/false | Наружное применение. |
| withdrawn_flag | логическое | true/false | Снят ли с рынка. |
| cross_references | список объектов | — | Внешние ID (DrugBank, PubChem и др.). |
| atc_classifications | список объектов | — | ATC‑коды и описания. |
| molecule_properties | объект | — | Набор свойств (MW, ALogP, HBA/HBD, PSA, QED и др.). |
| molecule_structures | объект | — | SMILES, molfile, InChI, InChIKey и др. |
| molecule_hierarchy | объект | — | Связь `molecule_chembl_id` / `parent_chembl_id` / `active_chembl_id`. |
| molecule_synonyms | список объектов | — | Синонимы молекулы. |
| helm_notation | строка | — | HELM‑нотация (для биотерапевтиков). |
| usan_stem | строка | — | USAN stem. |
| usan_stem_definition | строка | — | Определение USAN stem. |
| usan_substem | строка | — | USAN substem. |
| usan_year | целое (int) | — | Год присвоения USAN. |
