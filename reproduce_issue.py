from bioetl.infrastructure.observability.noop_tracing import NoOpTracer

tracer = NoOpTracer()
try:
    tracer.start_as_current_span("test", attributes={"foo": "bar"})
    print("Success")
except TypeError as e:
    print(f"Failed: {e}")
