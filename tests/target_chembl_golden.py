# ruff: noqa: E501
"""Golden records snapshot for target_chembl."""

import json

expected_target_records = json.loads(
    """
[
    {
        "target_chembl_id": "CHEMBL1075045",
        "pref_name": "dihydropteroate synthase",
        "score": null,
        "organism": "bacillus anthracis",
        "target_type": "single protein",
        "tax_id": 1392.0,
        "species_group_flag": false,
        "target_components": null,
        "cross_references": null,
        "uniprot_id": null,
        "hash_row": "07266ce497c7f99cfdcfc37141c53077c900f3554228231ab80b381f83139bbe",
        "hash_business_key": "0b478e3bc04dda11b851e91732ca647fedf0377e95965ca4d78f16a2bc131d45",
        "index": 957,
        "database_version": "ChEMBL_36",
        "extracted_at": "2025-12-06T13:39:15.649381+00:00"
    },
    {
        "target_chembl_id": "CHEMBL1075051",
        "pref_name": "dihydrofolate reductase",
        "score": null,
        "organism": "bos taurus",
        "target_type": "single protein",
        "tax_id": 9913.0,
        "species_group_flag": false,
        "target_components": null,
        "cross_references": null,
        "uniprot_id": null,
        "hash_row": "c37417be4aab6b54b249a0f1629f8dab01a217cafdc08e850dce07ea054df106",
        "hash_business_key": "0a6aec52211ab5876cdad2f73cf7daebe1217ec7087d1335ddcad75a3e7c6019",
        "index": 958,
        "database_version": "ChEMBL_36",
        "extracted_at": "2025-12-06T13:39:15.649381+00:00"
    },
    {
        "target_chembl_id": "CHEMBL1075097",
        "pref_name": "arginase-1",
        "score": null,
        "organism": "homo sapiens",
        "target_type": "single protein",
        "tax_id": 9606.0,
        "species_group_flag": false,
        "target_components": null,
        "cross_references": null,
        "uniprot_id": null,
        "hash_row": "fb2c338505b8ba411e8fea6b8206ec6513cc7e893711725e912dcc7a23131297",
        "hash_business_key": "9ee0491a4eb43696bae4aa0fa44527dd965652ab2186347403bc237331971f7b",
        "index": 138,
        "database_version": "ChEMBL_36",
        "extracted_at": "2025-12-06T13:39:15.649381+00:00"
    },
    {
        "target_chembl_id": "CHEMBL1075102",
        "pref_name": "phosphatidylinositol 4-phosphate 3-kinase c2 domain-containing subunit alpha",
        "score": null,
        "organism": "homo sapiens",
        "target_type": "single protein",
        "tax_id": 9606.0,
        "species_group_flag": false,
        "target_components": null,
        "cross_references": null,
        "uniprot_id": null,
        "hash_row": "619f31c7bc9723eea25edd466e46aa5d4fee7eef8fc08999a3eb27c59d7e19ea",
        "hash_business_key": "b518263c2761d867a30b8a1fa17eae9045e768df329195a09e0c0216441ae867",
        "index": 16,
        "database_version": "ChEMBL_36",
        "extracted_at": "2025-12-06T13:39:15.649381+00:00"
    },
    {
        "target_chembl_id": "CHEMBL1075105",
        "pref_name": "protein tyrosine phosphatase type iva 2",
        "score": null,
        "organism": "homo sapiens",
        "target_type": "single protein",
        "tax_id": 9606.0,
        "species_group_flag": false,
        "target_components": null,
        "cross_references": null,
        "uniprot_id": null,
        "hash_row": "f2104bc17fb5ad6d80cda54c4472a3a5e0571242c4e883903767ad8f2a7c01d5",
        "hash_business_key": "eb423a704efa58945d8cecafce9397a682dba0dcbc317cc1528d38406f5e2bf7",
        "index": 598,
        "database_version": "ChEMBL_36",
        "extracted_at": "2025-12-06T13:39:15.649381+00:00"
    },
    {
        "target_chembl_id": "CHEMBL1075108",
        "pref_name": "solute carrier family 12 member 5",
        "score": null,
        "organism": "rattus norvegicus",
        "target_type": "single protein",
        "tax_id": 10116.0,
        "species_group_flag": false,
        "target_components": null,
        "cross_references": null,
        "uniprot_id": null,
        "hash_row": "baf82748619cefb1f93e840b0efb077ba5a20f38c2f4b32c9bb1586ba834e5cc",
        "hash_business_key": "2c016e38ff5d3d8f568c1a13d35106f2ef1d42db3d586b0320553bd61cf936dd",
        "index": 669,
        "database_version": "ChEMBL_36",
        "extracted_at": "2025-12-06T13:39:15.649381+00:00"
    }
]
"""
)
