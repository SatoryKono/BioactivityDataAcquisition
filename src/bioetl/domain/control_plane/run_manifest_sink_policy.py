"""Sink idempotency policy checks for run manifest construction."""

from __future__ import annotations


def _collect_append_layers(sink: dict[object, object]) -> list[str]:
    """Collect Silver/Gold layers configured with append-mode sinks."""
    return [
        layer_name
        for layer_name in ("silver", "gold")
        if (layer_config := sink.get(layer_name)) is not None
        and _sink_layer_enabled(layer_config)
        and _sink_layer_mode(layer_config) == "append"
    ]


def _validate_append_layer_contract(
    *,
    yaml_config: object,
    layer_name: str,
    layer_config: object | None,
) -> str:
    """Validate one append-mode layer contract and its evidence."""
    contract = _sink_layer_idempotency_contract(layer_config)
    if contract is None:
        raise RuntimeError(
            f"sink.{layer_name}.mode=append requires explicit "
            f"sink.{layer_name}.idempotency_contract"
        )
    if contract == "disallowed":
        raise RuntimeError(
            f"sink.{layer_name}.mode=append is disallowed by "
            f"sink.{layer_name}.idempotency_contract=disallowed"
        )
    if contract not in {
        "append_log",
        "partition_append_with_stable_partition_key",
        "occurrence_only",
    }:
        raise RuntimeError(
            f"sink.{layer_name}.mode=append is incompatible with "
            f"sink.{layer_name}.idempotency_contract={contract}"
        )
    _validate_append_idempotency_evidence(
        yaml_config=yaml_config,
        layer_name=layer_name,
        layer_config=layer_config,
        contract=contract,
    )
    return contract


def _append_replay_guidance(*, append_layers: list[str]) -> str:
    """Build the remediation guidance for append-mode replay rejection."""
    details = ", ".join(
        f"sink.{layer_name}.mode=append" for layer_name in append_layers
    )
    return (
        f"semantic outputs ({details}); use merge/upsert, overwrite, or SCD2 "
        "semantics with stable keys instead"
    )


def _reject_append_for_replay(
    *,
    strict_replay_requested: bool,
    replay_capable_family: bool,
    append_layers: list[str],
) -> None:
    """Reject append-mode semantic outputs in replay-capable contexts."""
    if not append_layers:
        return
    if not (strict_replay_requested or replay_capable_family):
        return
    guidance = _append_replay_guidance(append_layers=append_layers)
    if strict_replay_requested:
        raise RuntimeError(
            "Strict reproducibility contexts cannot use append-mode "
            "Silver/Gold "
            f"{guidance}. Replay-capable pipeline families cannot use "
            "append-mode Silver/Gold semantic outputs either"
        )
    raise RuntimeError(
        "Replay-capable pipeline families cannot use append-mode Silver/Gold "
        f"{guidance}"
    )


def validate_reproducible_sink_modes(
    *,
    yaml_config: object,
    strict_replay_requested: bool,
    replay_capable_family: bool = False,
) -> None:
    """Validate append-mode semantic outputs against explicit idempotency policy."""
    sink = getattr(yaml_config, "sink", None)
    if not isinstance(sink, dict):
        return
    append_layers = _collect_append_layers(sink)
    for layer_name in append_layers:
        layer_config = sink.get(layer_name)
        _validate_append_layer_contract(
            yaml_config=yaml_config,
            layer_name=layer_name,
            layer_config=layer_config,
        )
    _reject_append_for_replay(
        strict_replay_requested=strict_replay_requested,
        replay_capable_family=replay_capable_family,
        append_layers=append_layers,
    )


def _sink_layer_enabled(layer_config: object) -> bool:
    if isinstance(layer_config, dict):
        return bool(layer_config.get("enabled", True))
    return bool(getattr(layer_config, "enabled", True))


def _sink_layer_mode(layer_config: object) -> str:
    raw_mode = (
        layer_config.get("mode", "")
        if isinstance(layer_config, dict)
        else getattr(layer_config, "mode", "")
    )
    return str(raw_mode or "").strip().lower()


def _sink_layer_idempotency_contract(layer_config: object | None) -> str | None:
    raw_contract = (
        layer_config.get("idempotency_contract", None)
        if isinstance(layer_config, dict)
        else getattr(layer_config, "idempotency_contract", None)
    )
    contract = str(raw_contract or "").strip().lower()
    return contract or None


def _validate_append_idempotency_evidence(
    *,
    yaml_config: object,
    layer_name: str,
    layer_config: object | None,
    contract: str,
) -> None:
    """Require machine-readable append idempotency evidence outside strict replay."""
    if contract == "occurrence_only":
        return
    if _append_idempotency_evidence_present(
        yaml_config=yaml_config,
        layer_config=layer_config,
        contract=contract,
    ):
        return
    raise RuntimeError(
        f"sink.{layer_name}.mode=append with "
        f"sink.{layer_name}.idempotency_contract={contract} requires "
        "machine-readable idempotency evidence; add "
        f"sink.{layer_name}.idempotency_evidence or classify the output as "
        "occurrence_only"
    )


def _partition_key_evidence_present(
    *,
    layer_config: object | None,
    evidence: dict[str, object],
) -> bool:
    """Check stable partition key evidence for partition-append contracts."""
    return bool(
        _text_items(evidence.get("stable_partition_keys"))
        or _text_items(evidence.get("partition_keys"))
        or _text_items(_sink_layer_field(layer_config, "partition_keys"))
    )


def _append_log_evidence_present(
    *,
    yaml_config: object,
    evidence: dict[str, object],
) -> bool:
    """Check occurrence identity evidence for append-log contracts."""
    return bool(
        _text_items(evidence.get("occurrence_identity_fields"))
        or _text_items(evidence.get("append_log_identity_fields"))
        or _text_items(getattr(yaml_config, "business_primary_keys", None))
    )


def _append_idempotency_evidence_present(
    *,
    yaml_config: object,
    layer_config: object | None,
    contract: str,
) -> bool:
    evidence = _sink_layer_idempotency_evidence(layer_config)
    if contract == "partition_append_with_stable_partition_key":
        return _partition_key_evidence_present(
            layer_config=layer_config, evidence=evidence
        )
    if contract == "append_log":
        return _append_log_evidence_present(
            yaml_config=yaml_config, evidence=evidence
        )
    return False


def _sink_layer_idempotency_evidence(
    layer_config: object | None,
) -> dict[str, object]:
    evidence = _sink_layer_field(layer_config, "idempotency_evidence")
    if isinstance(evidence, dict):
        return dict(evidence)
    proof = _sink_layer_field(layer_config, "idempotency_proof")
    if isinstance(proof, dict):
        return dict(proof)
    return {}


def _sink_layer_field(layer_config: object | None, field_name: str) -> object | None:
    if isinstance(layer_config, dict):
        return layer_config.get(field_name)
    return getattr(layer_config, field_name, None)


def _scalar_text_items(value: object) -> tuple[str, ...]:
    """Normalize a scalar value to a zero-or-one text tuple."""
    text = str(value or "").strip()
    if not text:
        return ()
    return (text,)


def _sequence_text_items(
    value: list[object] | tuple[object, ...] | set[object] | frozenset[object],
) -> tuple[str, ...]:
    """Normalize sequence items to stripped non-empty texts."""
    return tuple(str(item).strip() for item in value if str(item).strip())


def _text_items(value: object) -> tuple[str, ...]:
    if value is None or isinstance(value, str | bytes):
        return _scalar_text_items(value)
    if not isinstance(value, (list, tuple, set, frozenset)):
        return ()
    return _sequence_text_items(value)
