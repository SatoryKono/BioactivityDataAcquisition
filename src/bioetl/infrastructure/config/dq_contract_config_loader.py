"""Contract-based DQ configuration loader.

Loads DQ configuration from contract files for the new contract-based DQ system.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from bioetl.domain.config import DQConfig
from bioetl.domain.types import JsonDict
from bioetl.domain.types.dq_contracts import DQDisposition
from bioetl.infrastructure.config.base_config_loader import _load_yaml_file


class DQContractConfigLoader:
    """Loader for contract-based DQ configuration."""

    def __init__(self, configs_root: Path) -> None:
        """Initialize DQ contract config loader.

        Args:
            configs_root: Root directory containing contract configs.
        """
        self._configs_root = configs_root
        self._contracts_dir = configs_root / "contracts"

    def load_dq_config_for_pipeline(self, pipeline_name: str) -> DQConfig:
        """Load DQ configuration for a pipeline from contract files.

        Args:
            pipeline_name: Name of the pipeline (e.g., 'chembl_activity').

        Returns:
            DQConfig object with contract-based configuration.

        Raises:
            FileNotFoundError: If contract config file is not found.
            ValueError: If contract config is invalid.
        """
        # Parse pipeline name to get provider and entity
        parts = pipeline_name.split("_")
        if len(parts) < 2:
            raise ValueError(f"Invalid pipeline name: {pipeline_name}")

        provider = parts[0]
        entity = "_".join(parts[1:])

        # Try to load contract config
        contract_config = self._load_contract_config(provider, entity, pipeline_name)

        # Create DQConfig from contract data
        dq_config = DQConfig(
            contract_ref=contract_config.get("contract_ref"),
            contract_version=contract_config.get("contract_version"),
            rule_bundle_version=contract_config.get("rule_bundle_version"),
            default_disposition_policy=DQDisposition(
                contract_config.get("default_disposition_policy", "warn")
            ),
            disposition_overrides=(
                self._parse_disposition_overrides(
                    contract_config.get("disposition_overrides", {})
                )
                if contract_config.get("disposition_overrides")
                else {}
            ),
            strictness_mode=contract_config.get("strictness_mode", "moderate"),
            # Legacy fields (set defaults for backward compatibility)
            soft_fail_threshold=contract_config.get("soft_fail_threshold", 0.05),
            hard_fail_threshold=contract_config.get("hard_fail_threshold", 0.20),
            strict_validation=contract_config.get("strict_validation", False),
            field_validations=(),
            cross_field_validations=(),
            conditional_validations=(),
            invalid_record_policy=contract_config.get(
                "invalid_record_policy", "quarantine"
            ),
            report=self._create_report_config(contract_config.get("report", {})),
            key_nullability_rules=(),
        )

        return dq_config

    def _load_contract_config(
        self, provider: str, entity: str, pipeline_name: str
    ) -> JsonDict:
        """Load contract configuration from file.

        Args:
            provider: Provider name.
            entity: Entity name.
            pipeline_name: Full pipeline name for fallback patterns.

        Returns:
            Dictionary with contract configuration.

        Raises:
            FileNotFoundError: If contract config file is not found.
        """
        # Try different contract file patterns
        patterns = [
            self._contracts_dir / f"{provider}" / f"{entity}.yaml",
            self._contracts_dir / f"{provider}" / f"{entity}.json",
            self._contracts_dir / f"{provider}_{entity}.yaml",
            self._contracts_dir / f"{provider}_{entity}.json",
            self._contracts_dir / f"{pipeline_name}.yaml",
            self._contracts_dir / f"{pipeline_name}.json",
        ]

        for pattern in patterns:
            if pattern.exists():
                if pattern.suffix == ".json":
                    with open(pattern) as f:
                        return json.load(f)
                else:  # YAML
                    return _load_yaml_file(pattern)

        # If no contract file found, try to load from legacy DQ config
        # with contract fields
        legacy_config = self._try_load_legacy_dq_config_with_contracts(provider, entity)
        if legacy_config:
            return legacy_config

        # If still not found, raise error
        raise FileNotFoundError(
            f"DQ contract config not found for {pipeline_name}. "
            f"Searched patterns: {[str(p) for p in patterns]}"
        )

    def _try_load_legacy_dq_config_with_contracts(
        self, provider: str, entity: str
    ) -> JsonDict | None:
        """Try to load contract fields from legacy DQ config files.

        Args:
            provider: Provider name.
            entity: Entity name.

        Returns:
            Dictionary with contract configuration if found, None otherwise.
        """
        # Try to load from entity DQ config
        entity_dq_path = (
            self._configs_root / "entities" / provider / f"{entity}_dq.yaml"
        )
        if entity_dq_path.exists():
            entity_dq_config = _load_yaml_file(entity_dq_path)
            # Extract contract fields if present
            contract_fields = {}
            for field in [
                "contract_ref",
                "contract_version",
                "rule_bundle_version",
                "default_disposition_policy",
                "disposition_overrides",
                "strictness_mode",
            ]:
                if field in entity_dq_config:
                    contract_fields[field] = entity_dq_config[field]

            if contract_fields:
                # Add legacy fields for backward compatibility
                contract_fields.update(
                    {
                        "soft_fail_threshold": entity_dq_config.get(
                            "thresholds", {}
                        ).get("soft_fail", 0.05),
                        "hard_fail_threshold": entity_dq_config.get(
                            "thresholds", {}
                        ).get("hard_fail", 0.20),
                        "strict_validation": entity_dq_config.get(
                            "strict_validation", False
                        ),
                        "invalid_record_policy": entity_dq_config.get(
                            "invalid_record_policy", "quarantine"
                        ),
                    }
                )
                return contract_fields

        # Try to load from provider DQ config
        provider_dq_path = self._configs_root / "providers" / f"{provider}_dq.yaml"
        if provider_dq_path.exists():
            provider_dq_config = _load_yaml_file(provider_dq_path)
            # Extract contract fields if present
            contract_fields = {}
            for field in [
                "contract_ref",
                "contract_version",
                "rule_bundle_version",
                "default_disposition_policy",
                "disposition_overrides",
                "strictness_mode",
            ]:
                if field in provider_dq_config:
                    contract_fields[field] = provider_dq_config[field]

            if contract_fields:
                # Add legacy fields for backward compatibility
                contract_fields.update(
                    {
                        "soft_fail_threshold": provider_dq_config.get(
                            "thresholds", {}
                        ).get("soft_fail", 0.05),
                        "hard_fail_threshold": provider_dq_config.get(
                            "thresholds", {}
                        ).get("hard_fail", 0.20),
                        "strict_validation": provider_dq_config.get(
                            "strict_validation", False
                        ),
                        "invalid_record_policy": provider_dq_config.get(
                            "invalid_record_policy", "quarantine"
                        ),
                    }
                )
                return contract_fields

        return None

    def _parse_disposition_overrides(
        self, overrides: dict[str, str] | None
    ) -> dict[str, DQDisposition]:
        """Parse disposition overrides from config.

        Args:
            overrides: Dictionary of disposition overrides.

        Returns:
            Dictionary with DQDisposition values.
        """
        if not overrides:
            return {}

        return {k: DQDisposition(v) for k, v in overrides.items()}

    def _create_report_config(
        self, report_config: JsonDict
    ) -> Any:  # Any: Dynamic DQReportConfig creation from heterogeneous JSON
        """Create DQReportConfig from config.

        Args:
            report_config: Report configuration dictionary.

        Returns:
            DQReportConfig object.
        """
        from bioetl.domain.config.dq import DQReportConfig

        return DQReportConfig(
            enabled=report_config.get("enabled", True),
            format=report_config.get("format", "json"),
            include_sample_failures=report_config.get("include_sample_failures", True),
            sample_size=report_config.get("sample_size", 10),
            output_path=report_config.get("output_path"),
        )


def load_dq_config_for_pipeline(pipeline_name: str) -> DQConfig:
    """Convenience function to load DQ config for a pipeline.

    Args:
        pipeline_name: Name of the pipeline.

    Returns:
        DQConfig object.
    """
    from pathlib import Path

    # Use default configs directory
    configs_root = Path("configs")
    loader = DQContractConfigLoader(configs_root)
    return loader.load_dq_config_for_pipeline(pipeline_name)


__all__ = [
    "DQContractConfigLoader",
    "load_dq_config_for_pipeline",
]
