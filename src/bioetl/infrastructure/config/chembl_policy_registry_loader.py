"""Loader for ChEMBL semantic-policy registries."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from bioetl.domain.normalization.profiles.chembl_policy_registry_data import (
    ChemblControlledVocabularyFamily,
    ChemblOntologyPolicyFamily,
    ChemblPolicyRegistryData,
    ChemblStrictScalarFamily,
)


class ChemblPolicyRegistryLoader:
    """Load immutable ChEMBL semantic-policy payloads from published configs."""

    def __init__(self, configs_root: Path) -> None:
        self._controlled_vocab_path = configs_root / "vocab" / "chembl_controlled.yaml"
        self._ontology_path = configs_root / "vocab" / "chembl_ontology.yaml"

    def load(self) -> ChemblPolicyRegistryData:
        """Parse config-backed policy registries into immutable domain data."""
        controlled = self._load_yaml(self._controlled_vocab_path)
        ontology = self._load_yaml(self._ontology_path)

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
            ontology_families=tuple(
                ChemblOntologyPolicyFamily(
                    family_name=str(family_name),
                    fields=tuple(str(field_ref) for field_ref in payload["fields"]),
                    code_label_fields=tuple(
                        str(field_ref)
                        for field_ref in payload.get("code_label_fields", ())
                    ),
                    iri_fields=tuple(
                        str(field_ref)
                        for field_ref in payload.get("companion_fields", {}).get(
                            "iri", ()
                        )
                    ),
                    mapping_status_fields=tuple(
                        str(field_ref)
                        for field_ref in payload.get("companion_fields", {}).get(
                            "mapping_status", ()
                        )
                    ),
                    version_fields=tuple(
                        str(field_ref)
                        for field_ref in payload.get("companion_fields", {}).get(
                            "version", ()
                        )
                    ),
                )
                for family_name, payload in ontology["families"].items()
            ),
            publication_classification_fields=(
                "publication_type_unified",
                "publication_subclass",
                "publication_class",
            ),
        )

    @staticmethod
    def _load_strict_scalar_families(
        payload: dict[str, Any],
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
    ) -> dict[str, Any]:  # Any: YAML scalar/sequence leaf types remain heterogeneous
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise TypeError(f"{path} must decode to a mapping; got {type(payload)!r}")
        return payload
