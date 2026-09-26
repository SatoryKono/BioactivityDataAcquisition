"""Settings / config doubles for unit tests (PD5-1 / #6996).

``types.SimpleNamespace`` is not assignable to concrete Settings/config
Protocols under basedpyright. Prefer these typed stand-ins.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

__all__ = ["SimpleSettings", "as_settings"]


@dataclass
class SimpleSettings:
    """Loose settings bag with attribute access used by many unit tests."""

    values: dict[str, Any] = field(default_factory=dict)

    def __getattr__(self, name: str) -> Any:
        try:
            return self.values[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def get(self, name: str, default: Any = None) -> Any:
        return self.values.get(name, default)

    def __getitem__(self, name: str) -> Any:
        return self.values[name]

    def __contains__(self, name: object) -> bool:
        return name in self.values


def as_settings(**kwargs: Any) -> SimpleSettings:
    """Build a SimpleSettings instance from keyword fields."""
    return SimpleSettings(values=dict(kwargs))
