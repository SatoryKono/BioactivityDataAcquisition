"""Loader for ChEMBL semantic-policy registries."""

from __future__ import annotations

from pathlib import Path

import yaml

from bioetl.domain.normalization.profiles.chembl_policy_registry_data import (
    ChemblControlledVocabularyFamily,
    ChemblOntologyPolicyFamily,
    ChemblPolicyRegistryData,
    ChemblReferenceIdentifierFamily,
    ChemblStrictScalarFamily,
)


class ChemblPolicyRegistryLoader:
    """Load immutable ChEMBL semantic-policy payloads from published configs."""

    def __init__(self, configs_root: Path) -> None:
        self._controlled_vocab_path = configs_root / "vocab" / "chembl_controlled.yaml"
        self._ontology_path = configs_root / "vocab" / "chembl_ontology.yaml"
        self._reference_identifier_path = (
            configs_root / "vocab" / "chembl_reference_identifiers.yaml"
        )

    def load(self) -> ChemblPolicyRegistryData:
        """Parse config-backed policy registries into immutable domain data."""
        controlled = self._load_yaml(self._controlled_vocab_path)
        ontology = self._load_yaml(self._ontology_path)
        reference_identifiers = self._load_yaml(self._reference_identifier_path)

        return ChemblPolicyRegistryData(
            strict_boolean_families=self._load_strict_scalar_families(
                controlled,
                registry_key="strict_boolean_families",
            ),
            strict_flag_families=self._load_strict_scalar_families(
                controlled,
                registry_key="strict_flag_families",
            ),
            controlled_vocabularies=tuple(
                ChemblControlledVocabularyFamily(
                    family_name=str(family_name),
                    invalid_value_mode=str(payload["invalid_value_mode"]),
                    fields=tuple(str(field_ref) for field_ref in payload["fields"]),
                )
                for family_name, payload in controlled[
                    "controlled_vocabularies"
                ].items()
            ),
            ontology_families=self._load_ontology_families(ontology),
            publication_classification_fields=(
                "publication_type_unified",
                "publication_subclass",
                "publication_class",
            ),
            reference_identifier_families=tuple(
                ChemblReferenceIdentifierFamily(
                    family_name=str(family_name),
                    reference_family=str(payload["reference_family"]),
                    invalid_value_mode=str(payload["invalid_value_mode"]),
                    fields=tuple(str(field_ref) for field_ref in payload["fields"]),
                )
                for family_name, payload in reference_identifiers[
                    "reference_identifier_families"
                ].items()
            ),
        )

    @staticmethod
    def _load_ontology_families(
        payload: dict[str, object],  # Any: YAML scalar/sequence leaf types remain heterogeneous
    ) -> tuple[ChemblOntologyPolicyFamily, ...]:
        families = payload.get("families", {})
        if not isinstance(families, dict):
            raise TypeError(
                f"families must decode to a mapping; got {type(families)!r}"
            )

        augmented_families = {
            str(family_name): dict(family_payload)
            for family_name, family_payload in families.items()
            if isinstance(family_payload, dict)
        }
        ChemblPolicyRegistryLoader._merge_unit_companion_policies(
            augmented_families,
            payload.get("unit_companion_policies", {}),
        )

        return tuple(
            ChemblOntologyPolicyFamily(
                family_name=family_name,
                fields=tuple(str(field_ref) for field_ref in family_payload["fields"]),
                companion_governance=str(
                    family_payload.get("companion_governance", "full_companion_bundle")
                ),
                code_label_fields=tuple(
                    str(field_ref)
                    for field_ref in family_payload.get("code_label_fields", ())
                ),
                iri_fields=tuple(
                    str(field_ref)
                    for field_ref in family_payload.get("companion_fields", {}).get(
                        "iri", ()
                    )
                ),
                mapping_status_fields=tuple(
                    str(field_ref)
                    for field_ref in family_payload.get("companion_fields", {}).get(
                        "mapping_status", ()
                    )
                ),
                version_fields=tuple(
                    str(field_ref)
                    for field_ref in family_payload.get("companion_fields", {}).get(
                        "version", ()
                    )
                ),
            )
            for family_name, family_payload in augmented_families.items()
        )

    @staticmethod
    def _merge_unit_companion_policies(
        families: dict[str, dict[str, object]],  # Any: YAML scalar/sequence leaf types remain heterogeneous
        unit_companion_policies: object,
    ) -> None:
        if not isinstance(unit_companion_policies, dict):
            return

        for policy_payload in unit_companion_policies.values():
            if not isinstance(policy_payload, dict):
                continue
            field_refs = tuple(
                str(field_ref)
                for field_ref in policy_payload.get("fields", ())
                if isinstance(field_ref, str)
            )
            ontology_families = policy_payload.get("ontology_families", ())
            if not isinstance(ontology_families, (list, tuple)):
                continue
            for family_name in ontology_families:
                if not isinstance(family_name, str):
                    continue
                family_payload = families.get(family_name)
                if family_payload is None:
                    continue
                ChemblPolicyRegistryLoader._merge_unit_companion_family(
                    family_payload=family_payload,
                    family_name=family_name,
                    policy_fields=field_refs,
                )

    @staticmethod
    def _merge_unit_companion_family(
        *,
        family_payload: dict[str, object],  # Any: YAML scalar/sequence leaf types remain heterogeneous
        family_name: str,
        policy_fields: tuple[str, ...],
    ) -> None:
        base_suffix = f".{family_name}_units"
        family_fields = [
            str(field_ref) for field_ref in family_payload.get("fields", ())
        ]
        companion_fields = family_payload.setdefault("companion_fields", {})
        if not isinstance(companion_fields, dict):
            companion_fields = {}
            family_payload["companion_fields"] = companion_fields

        iri_fields = [str(field_ref) for field_ref in companion_fields.get("iri", ())]
        mapping_status_fields = [
            str(field_ref) for field_ref in companion_fields.get("mapping_status", ())
        ]
        version_fields = [
            str(field_ref) for field_ref in companion_fields.get("version", ())
        ]

        for field_ref in policy_fields:
            if not field_ref.endswith(base_suffix):
                continue
            pipeline_name, _field_name = field_ref.split(".", maxsplit=1)
            ChemblPolicyRegistryLoader._append_unique(family_fields, field_ref)
            ChemblPolicyRegistryLoader._append_unique(
                iri_fields, f"{pipeline_name}.{family_name}_unit_iri"
            )
            ChemblPolicyRegistryLoader._append_unique(
                mapping_status_fields,
                f"{pipeline_name}.{family_name}_unit_mapping_status",
            )
            ChemblPolicyRegistryLoader._append_unique(
                version_fields, f"{pipeline_name}.{family_name}_ontology_version"
            )

        family_payload["fields"] = tuple(family_fields)
        companion_fields["iri"] = tuple(iri_fields)
        companion_fields["mapping_status"] = tuple(mapping_status_fields)
        companion_fields["version"] = tuple(version_fields)

    @staticmethod
    def _append_unique(values: list[str], candidate: str) -> None:
        if candidate not in values:
            values.append(candidate)

    @staticmethod
    def _load_strict_scalar_families(
        payload: dict[str, object],
        *,
        registry_key: str,
    ) -> tuple[ChemblStrictScalarFamily, ...]:
        families = payload.get(registry_key, {})
        if not isinstance(families, dict):
            raise TypeError(
                f"{registry_key} must decode to a mapping; got {type(families)!r}"
            )

        return tuple(
            ChemblStrictScalarFamily(
                family_name=str(family_name),
                invalid_value_mode=str(family_payload["invalid_value_mode"]),
                fields=tuple(str(field_ref) for field_ref in family_payload["fields"]),
            )
            for family_name, family_payload in families.items()
        )

    @staticmethod
    def _load_yaml(
        path: Path,
    ) -> dict[str, object]:
        if not path.exists():
            if path.name == "chembl_reference_identifiers.yaml":
                return {"reference_identifier_families": {}}
            raise FileNotFoundError(path)
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise TypeError(f"{path} must decode to a mapping; got {type(payload)!r}")
        return payload
