"""Immutable boundary records for optional target-class enrichment."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType


def _freeze(value: object) -> object:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    return value


@dataclass(frozen=True, slots=True)
class TargetClassificationInput:
    """One normalized business row with a stable source-row identity."""

    input_row_id: str
    business_data: Mapping[str, object]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "business_data",
            MappingProxyType(
                {key: _freeze(value) for key, value in self.business_data.items()}
            ),
        )


@dataclass(frozen=True, slots=True)
class TargetClassificationArtifact:
    """Canonical artifact bytes; persistence is an application responsibility."""

    name: str
    payload: bytes


@dataclass(frozen=True, slots=True)
class TargetClassificationArtifactReference:
    """Content-addressed reference to a persisted result manifest."""

    uri: str
    sha256: str


@dataclass(frozen=True, slots=True)
class TargetClassificationResult:
    """Projection and separate evidence for exactly one source row."""

    input_row_id: str
    projection: Mapping[str, str | None]
    artifacts: tuple[TargetClassificationArtifact, ...] = ()
    diagnostic_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "projection", MappingProxyType(dict(self.projection)))
        object.__setattr__(self, "artifacts", tuple(self.artifacts))
        object.__setattr__(self, "diagnostic_codes", tuple(self.diagnostic_codes))


@dataclass(frozen=True, slots=True)
class TargetClassificationBatch:
    """Keyed row results and bounded aggregate counters for one call."""

    results: tuple[TargetClassificationResult, ...]
    metrics: Mapping[str, int] = field(default_factory=dict)
    profile_sha256: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "results", tuple(self.results))
        object.__setattr__(self, "metrics", MappingProxyType(dict(self.metrics)))


__all__ = [
    "TargetClassificationArtifact",
    "TargetClassificationArtifactReference",
    "TargetClassificationBatch",
    "TargetClassificationInput",
    "TargetClassificationResult",
]
