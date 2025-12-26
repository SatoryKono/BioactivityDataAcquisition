
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from bioetl.infrastructure.observability.noop_tracing import NoOpTracer

t = NoOpTracer()
try:
    t.start_as_current_span("test", attributes={"a": 1})
    print("Success")
except TypeError as e:
    print(f"Error: {e}")
