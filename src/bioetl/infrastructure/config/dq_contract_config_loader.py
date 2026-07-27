"""Contract-based DQ configuration loader."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal, TypeGuard

from bioetl.domain.config import DQConfig
from bioetl.domain.types import JsonDict
from bioetl.domain.types.dq_contracts import DQDisposition
from bioetl.infrastructure.config.base_config_loader import _load_yaml_file
from bioetl.infrastructure.config.contract_registry_loader import (
    load_contract_registry_entries,
    load_contract_registry_entry,
    resolve_contract_registry_path,
)


def _resolve_identity_data(
    registry_entry: JsonDict,
    *,
    contract_ref: str,
) -> JsonDict:
    """Extract normalized identity payload from registry entry."""
    identity_data = registry_entry.get("identity", {})
    if isinstance(identity_data, dict):
        return identity_data
    raise ValueError(
        "Malformed DQ contract registry entry for "
        f"{contract_ref}: identity must be a mapping"
    )


def _require_registry_identity_value(
    *,
    contract_ref: str,
    field_name: str,
    identity_data: JsonDict,
    registry_entry: JsonDict,
) -> object:
    """Resolve a required identity value from identity or legacy entry fields."""
    value = identity_data.get(field_name) or registry_entry.get(field_name)
    if value:
        return value
    raise ValueError(
        f"Malformed DQ contract registry entry for {contract_ref}: missing {field_name}"
    )


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


def _resolve_contract_strict_dq_validation(contract_config: JsonDict) -> bool:
    """Resolve DQ-only strict-validation flag from canonical or legacy key."""
    if "strict_dq_validation" in contract_config:
        return bool(contract_config["strict_dq_validation"])
    return bool(contract_config.get("strict_validation", False))


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


def _is_dq_strictness_mode(
    value: object,
) -> TypeGuard[Literal["lenient", "moderate", "strict"]]:
    return value in {"lenient", "moderate", "strict"}


def _parse_strictness_mode(
    value: object,
) -> Literal["lenient", "moderate", "strict"]:
    if _is_dq_strictness_mode(value):
        return value
    raise ValueError(f"Invalid DQ strictness mode: {value!r}")


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
        self._registry_path = resolve_contract_registry_path(
            configs_root=configs_root,
        )

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
            strictness_mode=_parse_strictness_mode(
                contract_config.get("strictness_mode", "moderate")
            ),
            soft_fail_threshold=_resolve_threshold(contract_config, "soft_fail", 0.05),
            hard_fail_threshold=_resolve_threshold(contract_config, "hard_fail", 0.20),
            strict_validation=_resolve_contract_strict_dq_validation(contract_config),
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

        identity_data = _resolve_identity_data(
            registry_entry,
            contract_ref=contract_ref,
        )
        expected_contract_version = _require_registry_identity_value(
            contract_ref=contract_ref,
            field_name="contract_version",
            identity_data=identity_data,
            registry_entry=registry_entry,
        )
        expected_rule_bundle = _require_registry_identity_value(
            contract_ref=contract_ref,
            field_name="rule_bundle_version",
            identity_data=identity_data,
            registry_entry=registry_entry,
        )
        expected_dq_policy = _require_registry_identity_value(
            contract_ref=contract_ref,
            field_name="dq_policy_ref",
            identity_data=identity_data,
            registry_entry=registry_entry,
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

    def _lookup_registry_entry(self, contract_ref: str) -> JsonDict:
        """Resolve registry entry for contract_ref."""
        try:
            load_contract_registry_entries(self._registry_path)
        except FileNotFoundError as exc:
            raise FileNotFoundError(
                f"DQ contract registry not found: {self._registry_path}"
            ) from exc
        except ValueError as exc:
            message = str(exc)
            if "entries must be a mapping" in message:
                raise ValueError(
                    "Malformed DQ contract registry: entries must be a mapping"
                ) from exc
            raise

        try:
            entry = load_contract_registry_entry(
                contract_ref,
                registry_path=self._registry_path,
            )
        except KeyError as exc:
            raise KeyError(
                f"DQ contract registry entry not found for contract_ref: {contract_ref}"
            ) from exc

        identity_data = entry.get("identity", {})
        if not isinstance(identity_data, dict):
            raise ValueError(
                "Malformed DQ contract registry entry for "
                f"{contract_ref}: identity must be a mapping"
            )
        return entry

    def _load_contract_config(
        self,
        provider: str,
        entity: str,
        pipeline_name: str,
    ) -> JsonDict:
        """Load contract configuration from contract files only."""
        patterns = _build_contract_patterns(
            contracts_dir=self._contracts_dir,
            provider=provider,
            entity=entity,
            pipeline_name=pipeline_name,
        )
        for pattern in patterns:
            if pattern.exists():
                return _load_contract_payload(pattern)

        raise FileNotFoundError(
            f"DQ contract config not found for {pipeline_name}. "
            f"Searched patterns: {[str(path) for path in patterns]}"
        )


def load_dq_config_for_pipeline(
    pipeline_name: str,
    *,
    configs_root: Path,
) -> DQConfig:
    """Convenience function to load DQ config for a pipeline."""
    loader = DQContractConfigLoader(configs_root)
    return loader.load_dq_config_for_pipeline(pipeline_name)


__all__ = [
    "DQContractConfigLoader",
    "load_dq_config_for_pipeline",
]
