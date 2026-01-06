import pandas as pd
import pandera as pa
from pandera.typing import Series

class SimpleSchemaDecorated(pa.DataFrameModel):
    col1: Series[int] = pa.Field()

    @pa.check("col1")
    @classmethod
    def check_ge_zero(cls, col: Series[int]) -> Series[bool]:
        return col >= 0

df = pd.DataFrame({"col1": [1, 2, 3]})
try:
    SimpleSchemaDecorated.validate(df)
    print("Validation successful")
except Exception as e:
    print(f"Validation failed: {e}")
    # import traceback
    # traceback.print_exc()
