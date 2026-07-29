# composite_molecule passport

> Generated documentation projection. Do not edit manually.

- Kind: `pipeline`
- Typed identity: `composite:composite_molecule`
- Schema: `1.0.0`
- Source revision: `41a1d6eab5a5c32c6b7754f6c3156ff87394912f`

## Evidence

- `composite_config`: `configs/composites/molecule.yaml`
- `gold_contract`: `configs/contracts/composite/molecule.yaml`

## Generated facts

```json
{
  "composite": {
    "cross_validation": {
      "enabled": false,
      "enricher_pairings": [],
      "error_threshold": 2,
      "fuzzy_threshold": 0.8,
      "numeric_tolerance": 0.1,
      "quarantine_threshold": 2,
      "warning_threshold": 1
    },
    "dependencies": [],
    "enrichers": [
      {
        "filter_condition": "inchi_key IS NOT NULL",
        "join_keys": [
          "inchi_key",
          "canonical_smiles"
        ],
        "pipeline": "pubchem_compound",
        "required": false,
        "silver_table": "silver/pubchem/compound",
        "timeout_seconds": 3600
      }
    ],
    "execution": {
      "checkpoint_enabled": true,
      "max_concurrency": 1,
      "retry": {
        "backoff_multiplier": 2.0,
        "max_attempts": 3
      }
    },
    "merge": {
      "column_groups": [
        {
          "fields": [
            "entity_id",
            "content_hash",
            "_source",
            "_index"
          ],
          "name": "system",
          "pattern": "^_composite_|^_source_providers|^_enrichment_|^_lineage_",
          "provider_order": [
            "chembl",
            "pubchem"
          ]
        },
        {
          "fields": [
            "molecule_id",
            "inchi_key",
            "standardized_inchi_key",
            "structure_parent_key",
            "inchi",
            "standard_inchi"
          ],
          "name": "identifiers",
          "provider_order": [
            "chembl",
            "pubchem"
          ]
        },
        {
          "fields": [
            "canonical_smiles",
            "isomeric_smiles",
            "helm_notation",
            "structure_type"
          ],
          "name": "structure",
          "provider_order": [
            "chembl",
            "pubchem"
          ]
        },
        {
          "fields": [
            "molecular_weight",
            "molecular_formula",
            "logp",
            "logp_method",
            "polar_surface_area",
            "hba_count",
            "hbd_count",
            "rotatable_bond_count",
            "heavy_atom_count",
            "aromatic_ring_count",
            "qed_weighted",
            "property_ro5_violations",
            "property_ro3_pass"
          ],
          "name": "properties",
          "provider_order": [
            "chembl",
            "pubchem"
          ]
        },
        {
          "fields": [
            "pref_name",
            "iupac_name",
            "molecule_synonyms"
          ],
          "name": "names",
          "provider_order": [
            "chembl",
            "pubchem"
          ]
        },
        {
          "fields": [
            "max_phase",
            "first_approval",
            "therapeutic_flag",
            "black_box_warning",
            "withdrawn_flag",
            "oral",
            "parenteral",
            "topical",
            "first_in_class",
            "prodrug",
            "natural_product",
            "availability_type"
          ],
          "name": "clinical",
          "provider_order": [
            "chembl"
          ]
        },
        {
          "fields": [
            "hierarchy_parent_chembl_id",
            "hierarchy_active_chembl_id",
            "hierarchy_child_chembl_id",
            "molecule_hierarchy"
          ],
          "name": "hierarchy",
          "provider_order": [
            "chembl"
          ]
        },
        {
          "fields": [
            "molecule_type",
            "atc_classifications",
            "chirality",
            "inorganic_flag",
            "polymer_flag",
            "dosed_ingredient"
          ],
          "name": "classification",
          "provider_order": [
            "chembl"
          ]
        },
        {
          "fields": [
            "cross_references"
          ],
          "name": "xrefs",
          "provider_order": [
            "chembl",
            "pubchem"
          ]
        },
        {
          "fields": [
            "usan_year",
            "usan_stem",
            "usan_substem",
            "usan_stem_definition"
          ],
          "name": "usan",
          "provider_order": [
            "chembl"
          ]
        }
      ],
      "conflict_resolution": "seed_priority",
      "exclude_fields": [],
      "output": {
        "gold": "data/output/gold/composite/molecule",
        "silver": "data/output/silver/composite/molecule"
      },
      "preserve_all_sources": true,
      "sort_by": {
        "gold": [
          "entity_id",
          "molecule_id"
        ],
        "pii": [
          "pubmed"
        ],
        "primary_component_id": [
          "chembl"
        ],
        "primary_topic": [
          "openalex"
        ],
        "publication_class": [
          "chembl",
          "pubmed",
          "openalex",
          "crossref",
          "semanticscholar"
        ],
        "publication_id": [
          "chembl.activity"
        ],
        "publication_subclass": [
          "chembl",
          "pubmed",
          "openalex",
          "crossref",
          "semanticscholar"
        ],
        "publication_type_unified": [
          "chembl",
          "pubmed",
          "openalex",
          "crossref",
          "semanticscholar"
        ],
        "publisher_id": [
          "pubmed"
        ],
        "references": [
          "crossref"
        ],
        "silver": [
          "entity_id",
          "molecule_id"
        ],
        "subject_fields": [
          "semanticscholar"
        ],
        "subject_keywords": [
          "crossref",
          "openalex",
          "pubmed",
          "semanticscholar"
        ],
        "subject_mesh": [
          "pubmed",
          "openalex"
        ],
        "subject_topics": [
          "openalex"
        ],
        "target_id": [
          "chembl"
        ],
        "taxonomy_id": [
          "chembl"
        ],
        "tissue_id": [
          "chembl.assay"
        ],
        "title": [
          "chembl",
          "crossref",
          "openalex"
        ]
      },
      "strategy": "left_outer"
    },
    "seed": {
      "output_keys": [
        "molecule_id",
        "inchi_key",
        "canonical_smiles",
        "pref_name"
      ],
      "pipeline": "chembl_molecule",
      "silver_table": "silver/chembl/molecule"
    },
    "version": "1.0.0"
  },
  "diagnostics": [],
  "execution": {
    "control_plane": {
      "checkpoints": true,
      "run_manifest": true
    }
  },
  "identity": {
    "aliases": [],
    "entity": "molecule",
    "pipeline_id": "composite_molecule",
    "pipeline_type": "composite",
    "provider": "composite",
    "status": "active",
    "typed_id": "composite:composite_molecule"
  },
  "kind": "pipeline",
  "observability": {
    "correlation_fields": [
      "run_id",
      "manifest_id"
    ],
    "metric_labels": [
      "pipeline",
      "run_type",
      "status"
    ]
  },
  "passport_schema_version": "1.0.0",
  "provenance": {
    "projector_version": "1.0.0",
    "semantic_content_hash": "sha256:dfecae3285dd9ef27db73d6b02144f048ba387b3fc51d9591db3a079490216a8",
    "source_revision": "41a1d6eab5a5c32c6b7754f6c3156ff87394912f"
  },
  "source_references": [
    {
      "path": "configs/composites/molecule.yaml",
      "role": "composite_config"
    },
    {
      "path": "configs/contracts/composite/molecule.yaml",
      "role": "gold_contract"
    }
  ]
}
```

## Diagnostics

- No blocking diagnostics.
