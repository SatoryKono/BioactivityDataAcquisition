"""Retain normalized DQ inputs across Gold field renames without persisted keys."""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from bioetl.domain.types import JsonDict


class _GoldRuleInputRecord(dict[str, object]):
    """Gold mapping with an immutable, transient snapshot of its Silver inputs."""

    __slots__ = ("_rule_inputs",)

    def __init__(self, record: JsonDict, rule_inputs: Mapping[str, object]) -> None:
        super().__init__(record)
        self._rule_inputs = rule_inputs


def bind_gold_rule_inputs(
    record: JsonDict | None, rule_inputs: JsonDict
) -> JsonDict | None:
    """Bind the exact pre-transform record while retaining ordinary Gold keys."""
    if record is None:
        return None
    source_id, target_id = rule_inputs.get("entity_id"), record.get("entity_id")
    if source_id is not None and target_id is not None and source_id != target_id:
        raise ValueError("Gold transform changed record identity")
    return _GoldRuleInputRecord(record, MappingProxyType(dict(rule_inputs)))


def resolve_gold_rule_inputs(records: list[JsonDict]) -> list[JsonDict]:
    """Read bound Silver inputs, preserving direct Gold callers' input contract."""
    return [
        dict(record._rule_inputs)
        if isinstance(record, _GoldRuleInputRecord)
        else record
        for record in records
    ]
