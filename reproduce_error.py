import pandas as pd
import pandera.pandas as pa
from pandera.api.checks import Check
import sys

print(f"pd.Series: {pd.Series}")

# Try to find where the dispatch happens
# It seems it's in Check implementation
check = pa.Check.str_matches("^[a-z]+$")
# The error happens during __call__ of the backend
from pandera.backends.pandas.checks import PandasCheckBackend

# Let's look at the registry if we can find it
# In pandera 0.26.1, it seems to be in pandera.api.function_dispatch
# But it's used inside the check backend

try:
    backend = PandasCheckBackend(check)
    # The error was: File "C:\Users\HP3168\AppData\Roaming\Python\Python314\site-packages\pandera\api\function_dispatch.py", line 24, in __call__
    # fn = self._function_registry[input_data_type]
    
    # Let's try to simulate what happens in apply_field
    print(f"Check fn: {backend.check_fn}")
    if hasattr(backend.check_fn, "_function_registry"):
        print("Registry keys:", backend.check_fn._function_registry.keys())
        print(f"Is pd.Series in registry? {pd.Series in backend.check_fn._function_registry}")
except Exception as e:
    print(f"Inspection failed: {e}")

df = pd.DataFrame({"col1": ["abc"]})
try:
    pa.SeriesSchema(str, checks=check).validate(df["col1"])
    print("Direct series validation successful")
except Exception as e:
    print(f"Direct series validation failed: {type(e).__name__}: {e}")
