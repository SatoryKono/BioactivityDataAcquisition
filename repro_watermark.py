from bioetl.domain.types import Watermark
from datetime import datetime

try:
    print("Attempting Watermark(datetime)...")
    w = Watermark(datetime.now())
    print("Success")
except Exception as e:
    print(f"Failed: {type(e).__name__}: {e}")

try:
    print("Attempting Watermark(int)...")
    w = Watermark(123)
    print("Success")
except Exception as e:
    print(f"Failed: {type(e).__name__}: {e}")

try:
    print("Attempting Watermark(str)...")
    w = Watermark("abc")
    print("Success")
except Exception as e:
    print(f"Failed: {type(e).__name__}: {e}")
