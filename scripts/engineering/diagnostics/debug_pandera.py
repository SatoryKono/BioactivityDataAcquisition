import pandas as pd
import pandera as pa
import pandera.pandas as panpa

# Monkeypatch FunctionDispatch
try:
    import pandera.api.function_dispatch as fd

    original_call = fd.FunctionDispatch.__call__

    def patched_call(self, *args, **kwargs):
        try:
            return original_call(self, *args, **kwargs)
        except KeyError as e:
            if "pandas.Series" in str(e) or (
                len(args) > 0 and isinstance(args[0], pd.Series)
            ):
                from typing import Any

                if Any in self._function_registry:
                    # Fallback to Any handler if Series handler is missing
                    # Note: this might raise NotImplementedError for built-ins,
                    # but it's better than KeyError
                    return self._function_registry[Any](*args, **kwargs)
            raise

    fd.FunctionDispatch.__call__ = patched_call
    print("FunctionDispatch monkeypatched")
except Exception as e:
    print(f"Failed to patch FunctionDispatch: {e}")

df = pd.DataFrame({"a": [1, 2, 3]})


class TestModel(pa.DataFrameModel):
    a: int = pa.Field(ge=0)


try:
    TestModel.validate(df)
    print("DataFrameModel validation PASSED after FunctionDispatch patch!")
except Exception as e:
    print(f"DataFrameModel validation FAILED: {type(e).__name__}: {e}")
