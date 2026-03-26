"""Contract-based DQ configuration loader."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from bioetl.domain.config import DQConfig
from bioetl.domain.types import JsonDict
from bioetl.domain.types.dq_contracts import DQDisposition
from bioetl.infrastructure.config.base_config_loader import _load_yaml_file

_CONTRACT_FIELDS = (
    "contract_ref",
    "contract_version",
    "rule_bundle_version",
    "default_disposition_policy",
    "disposition_overrides",
    "strictness_mode",
)


def _resolve_identity_data(registry_entry: JsonDict) -> JsonDict:
    """Extract normalized identity payload from registry entry."""
    identity_data = registry_entry.get("identity", {})
    if isinstance(identity_data, dict):
        return identity_data
    return {}


def _validate_identity_field(
    *, merged: JsonDict, field_name: str, expected: object
) -> None:
    """Ensure identity field is consistent when expected value is defined."""
    actual = merged.get(field_name)
    if expected and actual and actual != expected:
        raise ValueError(
            f"DQ contract config {field_name} mismatch: expected {expected}, got {actual}"
        )


def _resolve_threshold(
    contract_config: JsonDict,
    threshold_name: str,
    default: float,
) -> float:
    """Resolve threshold from explicit field or nested legacy section."""
    direct_key = f"{threshold_name}_threshold"
    if direct_key in contract_config:
        return float(contract_config[direct_key])

    nested = contract_config.get("thresholds")
    if isinstance(nested, dict) and threshold_name in nested:
        return float(nested[threshold_name])
    return default


def _build_legacy_contract_fields(raw_config: JsonDict) -> JsonDict:
    """Extract contract-aware fields from legacy DQ config payload."""
    contract_fields = {
        field: raw_config[field] for field in _CONTRACT_FIELDS if field in raw_config
    }
    if not contract_fields:
        return {}

    thresholds = raw_config.get("thresholds", {})
    threshold_map = thresholds if isinstance(thresholds, dict) else {}
    contract_fields.update(
        {
            "soft_fail_threshold": threshold_map.get("soft_fail", 0.05),
            "hard_fail_threshold": threshold_map.get("hard_fail", 0.20),
            "strict_validation": raw_config.get("strict_validation", False),
            "invalid_record_policy": raw_config.get(
                "invalid_record_policy", "quarantine"
            ),
        }
    )
    return contract_fields


def _try_load_legacy_dq_config_with_contracts(
    *,
    configs_root: Path,
    provider: str,
    entity: str,
) -> JsonDict | None:
    """Try to load contract fields from legacy entity/provider DQ config files."""
    entity_dq_path = configs_root / "entities" / provider / f"{entity}_dq.yaml"
    if entity_dq_path.exists():
        entity_dq_config = _load_yaml_file(entity_dq_path)
        contract_fields = _build_legacy_contract_fields(entity_dq_config)
        if contract_fields:
            return contract_fields

    provider_dq_path = configs_root / "providers" / f"{provider}_dq.yaml"
    if provider_dq_path.exists():
        provider_dq_config = _load_yaml_file(provider_dq_path)
        contract_fields = _build_legacy_contract_fields(provider_dq_config)
        if contract_fields:
            return contract_fields

    return None


def _parse_disposition_overrides(
    overrides: dict[str, str] | None,
) -> dict[str, DQDisposition]:
    """Parse disposition overrides from config."""
    if not overrides:
        return {}
    return {key: DQDisposition(value) for key, value in overrides.items()}


def _create_report_config(
    report_config: JsonDict,
) -> Any:  # Any: Dynamic DQReportConfig creation from heterogeneous JSON
    """Create DQReportConfig from config."""
    from bioetl.domain.config.dq import DQReportConfig

    return DQReportConfig(
        enabled=report_config.get("enabled", True),
        format=report_config.get("format", "json"),
        include_sample_failures=report_config.get("include_sample_failures", True),
        sample_size=report_config.get("sample_size", 10),
        output_path=report_config.get("output_path"),
    )


def _build_contract_patterns(
    *,
    contracts_dir: Path,
    provider: str,
    entity: str,
    pipeline_name: str,
) -> list[Path]:
    """Build contract config lookup patterns."""
    return [
        contracts_dir / provider / f"{entity}.yaml",
        contracts_dir / provider / f"{entity}.json",
        contracts_dir / f"{provider}_{entity}.yaml",
        contracts_dir / f"{provider}_{entity}.json",
        contracts_dir / f"{pipeline_name}.yaml",
        contracts_dir / f"{pipeline_name}.json",
    ]


def _load_contract_payload(path: Path) -> JsonDict:
    """Load single contract payload from YAML/JSON."""
    if path.suffix == ".json":
        with open(path, encoding="utf-8") as file:
            data = json.load(file)
        return data if isinstance(data, dict) else {}
    return _load_yaml_file(path)


class DQContractConfigLoader:
    """Loader for contract-based DQ configuration."""

    def __init__(self, configs_root: Path) -> None:
        self._configs_root = configs_root
        self._contracts_dir = configs_root / "contracts"
        self._registry_path = configs_root / "base" / "contract_registry.yaml"

    def load_dq_config_for_pipeline(self, pipeline_name: str) -> DQConfig:
        """Load DQ configuration for a pipeline from contract files."""
        parts = pipeline_name.split("_")
        if len(parts) < 2:
            raise ValueError(f"Invalid pipeline name: {pipeline_name}")

        provider = parts[0]
        entity = "_".join(parts[1:])
        contract_ref = f"{provider}.{entity}"
        contract_config = self._load_contract_config(provider, entity, pipeline_name)
        contract_config = self._align_with_registry(
            contract_ref=contract_ref,
            contract_config=contract_config,
        )

        return DQConfig(
            contract_ref=contract_config.get("contract_ref"),
            contract_version=contract_config.get("contract_version"),
            rule_bundle_version=contract_config.get("rule_bundle_version"),
            default_disposition_policy=DQDisposition(
                contract_config.get("default_disposition_policy", "warn")
            ),
            disposition_overrides=_parse_disposition_overrides(
                contract_config.get("disposition_overrides", {})
            ),
            strictness_mode=contract_config.get("strictness_mode", "moderate"),
            soft_fail_threshold=_resolve_threshold(contract_config, "soft_fail", 0.05),
            hard_fail_threshold=_resolve_threshold(contract_config, "hard_fail", 0.20),
            strict_validation=contract_config.get("strict_validation", False),
            field_validations=(),
            cross_field_validations=(),
            conditional_validations=(),
            invalid_record_policy=contract_config.get(
                "invalid_record_policy", "quarantine"
            ),
            report=_create_report_config(contract_config.get("report", {})),
            key_nullability_rules=(),
        )

    def _align_with_registry(
        self,
        *,
        contract_ref: str,
        contract_config: JsonDict,
    ) -> JsonDict:
        """Align contract config identity fields with contract registry entry."""
        registry_entry = self._lookup_registry_entry(contract_ref)
        if registry_entry is None:
            return contract_config

        identity_data = _resolve_identity_data(registry_entry)
        expected_contract_version = identity_data.get("contract_version")
        expected_rule_bundle = identity_data.get(
            "rule_bundle_version"
        ) or registry_entry.get("rule_bundle_version")
        expected_dq_policy = identity_data.get("dq_policy_ref") or registry_entry.get(
            "dq_policy_ref"
        )

        merged = dict(contract_config)
        merged.setdefault("contract_ref", contract_ref)
        merged.setdefault("contract_version", expected_contract_version)
        merged.setdefault("rule_bundle_version", expected_rule_bundle)
        merged.setdefault("dq_policy_ref", expected_dq_policy)

        if merged.get("contract_ref") != contract_ref:
            raise ValueError(
                "DQ contract config contract_ref mismatch: "
                f"expected {contract_ref}, got {merged.get('contract_ref')}"
            )

        _validate_identity_field(
            merged=merged,
            field_name="contract_version",
            expected=expected_contract_version,
        )
        _validate_identity_field(
            merged=merged,
            field_name="rule_bundle_version",
            expected=expected_rule_bundle,
        )
        _validate_identity_field(
            merged=merged,
            field_name="dq_policy_ref",
            expected=expected_dq_policy,
        )
        return merged

    def _lookup_registry_entry(self, contract_ref: str) -> JsonDict | None:
        """Resolve registry entry for contract_ref."""
        if not self._registry_path.exists():
            return None
        registry_data = _load_yaml_file(self._registry_path)
        entries = registry_data.get("entries", {})
        if not isinstance(entries, dict):
            return None
        entry = entries.get(contract_ref)
        if not isinstance(entry, dict):
            return None
        return entry

    def _load_contract_config(
        self,
        provider: str,
        entity: str,
        pipeline_name: str,
    ) -> JsonDict:
        """Load contract configuration from file with legacy fallback."""
        patterns = _build_contract_patterns(
            contracts_dir=self._contracts_dir,
            provider=provider,
            entity=entity,
            pipeline_name=pipeline_name,
        )
        for pattern in patterns:
            if pattern.exists():
                return _load_contract_payload(pattern)

        legacy_config = _try_load_legacy_dq_config_with_contracts(
            configs_root=self._configs_root,
            provider=provider,
            entity=entity,
        )
        if legacy_config:
            return legacy_config

        raise FileNotFoundError(
            f"DQ contract config not found for {pipeline_name}. "
            f"Searched patterns: {[str(path) for path in patterns]}"
        )


def load_dq_config_for_pipeline(pipeline_name: str) -> DQConfig:
    """Convenience function to load DQ config for a pipeline."""
    loader = DQContractConfigLoader(Path("configs"))
    return loader.load_dq_config_for_pipeline(pipeline_name)


__all__ = [
    "DQContractConfigLoader",
    "load_dq_config_for_pipeline",
]
