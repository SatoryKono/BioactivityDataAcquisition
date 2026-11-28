"""Strict YAML boundary for the offline target-classification profile."""

from __future__ import annotations

from typing import Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SerializerFunctionWrapHandler,
    model_serializer,
    model_validator,
)

from bioetl.domain.config.target_classification import (
    TargetClassificationConfig,
    TargetClassificationMode,
    TargetTableContract,
)


class TargetClassificationYamlConfig(BaseModel):
    """Keep unknown keys and unpinned enabled profiles out of runtime wiring."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        json_schema_extra={
            "dependentRequired": {
                "snapshot_manifest": ["snapshot_manifest_sha256"],
                "snapshot_manifest_sha256": ["snapshot_manifest"],
            },
            "allOf": [
                {
                    "if": {
                        "properties": {"mode": {"enum": ["shadow", "enrich"]}},
                        "required": ["mode"],
                    },
                    "then": {
                        "required": ["snapshot_manifest", "snapshot_manifest_sha256"],
                        "properties": {
                            "snapshot_manifest": {
                                "type": "string",
                                "minLength": 1,
                                "pattern": r"\S",
                            },
                            "snapshot_manifest_sha256": {
                                "type": "string",
                                "pattern": r"^[0-9a-f]{64}$",
                            },
                        },
                    },
                },
                {
                    # An omitted mode resolves to the legacy schema default, off.
                    "if": {"properties": {"mode": {"enum": ["off", "shadow"]}}},
                    "then": {
                        "properties": {"table_contract": {"enum": ["3.0.0", None]}}
                    },
                },
                {
                    "if": {
                        "properties": {
                            "mode": {"const": "enrich"},
                            "table_contract": {"const": "3.0.0"},
                        },
                        "required": ["mode", "table_contract"],
                    },
                    "then": {"not": {}},
                },
            ],
        },
    )

    mode: TargetClassificationMode = "off"
    snapshot_manifest: str | None = Field(default=None, min_length=1, pattern=r"\S")
    snapshot_manifest_sha256: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )
    table_contract: TargetTableContract | None = None

    @model_serializer(mode="wrap")
    def _omit_absent_table_contract(
        self, handler: SerializerFunctionWrapHandler
    ) -> object:
        """Omit a null selector so manifests written before the field still match."""
        payload = handler(self)
        if (
            isinstance(payload, dict)
            and "table_contract" in payload
            and payload["table_contract"] is None
        ):
            payload.pop("table_contract")
        return payload

    @model_validator(mode="after")
    def validate_profile(self) -> Self:
        self.to_domain()
        return self

    def to_domain(self) -> TargetClassificationConfig:
        return TargetClassificationConfig(
            mode=self.mode,
            snapshot_manifest=self.snapshot_manifest,
            snapshot_manifest_sha256=self.snapshot_manifest_sha256,
            table_contract=self.table_contract,
        )


__all__ = ["TargetClassificationYamlConfig"]
