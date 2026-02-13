"""BioETL: Bioactivity data acquisition and processing pipeline."""

from __future__ import annotations

__version__ = "5.14.0"

# Project-wide monkeypatch for Pandera compatibility with Pandas 3.0.0 on Python 3.14
# Registers pd.Series in Pandera's function dispatch registry to avoid KeyError.
try:
    import pandas as pd
    import pandera as pa
    from typing import Any
    
    # Force registration of pandas backend
    import pandera.backends.pandas
    
    # Create a dummy check to access the dispatch registry
    _check = pa.Check(lambda s: True)
    from pandera.backends.pandas.checks import PandasCheckBackend
    _backend = PandasCheckBackend(_check)
    
    _func = _backend.check_fn.func if hasattr(_backend.check_fn, "func") else _backend.check_fn
    if hasattr(_func, "_function_registry"):
        _registry = _func._function_registry
        if pd.Series not in _registry and Any in _registry:
            _registry[pd.Series] = _registry[Any]
except Exception:
    # Fail silently to avoid breaking the entire project if Pandera/Pandas are not present
    pass
