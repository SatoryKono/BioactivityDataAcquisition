"""Domain serialization package.

JSON codec stays in ``domain/serialization.py``. This package adds snapshot
helpers without dropping the codec API (#11241).
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

from bioetl.domain.serialization.snapshot_serialization import (
    normalize_snapshot,
    to_serializable_mapping,
)

_CODEC_PATH = Path(__file__).resolve().parents[1] / "serialization.py"
_spec = importlib.util.spec_from_file_location(
    "bioetl.domain._serialization_codec",
    _CODEC_PATH,
)
if _spec is None or _spec.loader is None:
    raise ImportError(f"Cannot load serialization codec from {_CODEC_PATH}")
_codec = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_codec)


class _CodecDelegatingModule(types.ModuleType):
    """Forward private codec attributes so monkeypatching keeps working.

    The codec lives in the sibling ``serialization.py`` module, not in this
    package namespace, so toggling flags such as ``_orjson_available`` must be
    written through to the codec module to affect serialization behavior.
    """

    def __setattr__(self, name: str, value: object) -> None:
        codec = self.__dict__.get("_codec")
        if codec is not None and hasattr(codec, name):
            setattr(codec, name, value)
        super().__setattr__(name, value)


def __getattr__(name: str) -> object:
    try:
        return getattr(_codec, name)
    except AttributeError:
        raise AttributeError(
            f"module {__name__!r} has no attribute {name!r}"
        ) from None


sys.modules[__name__].__class__ = _CodecDelegatingModule

_escape_non_ascii = _codec._escape_non_ascii
_has_non_ascii = _codec._has_non_ascii
canonicalize_json_string = _codec.canonicalize_json_string
deserialize_from_json = _codec.deserialize_from_json
flatten_arrow_table_for_export = _codec.flatten_arrow_table_for_export
is_orjson_available = _codec.is_orjson_available
serialize_to_canonical_json = _codec.serialize_to_canonical_json
serialize_to_json = _codec.serialize_to_json
serialize_to_json_canonical = _codec.serialize_to_json_canonical

__all__ = [
    "_escape_non_ascii",
    "_has_non_ascii",
    "canonicalize_json_string",
    "deserialize_from_json",
    "flatten_arrow_table_for_export",
    "is_orjson_available",
    "normalize_snapshot",
    "serialize_to_canonical_json",
    "serialize_to_json",
    "serialize_to_json_canonical",
    "to_serializable_mapping",
]
