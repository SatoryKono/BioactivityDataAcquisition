
from bioetl.infrastructure.observability.noop_tracing import NoOpTracing, NoOpTracer
from bioetl.domain.ports.noop import NoOpTracing as DomainNoOpTracing

print("Infrastructure NoOpTracer start_as_current_span args:")
import inspect
print(inspect.signature(NoOpTracer.start_as_current_span))

tracer = NoOpTracing().get_tracer("test")
print(f"Tracer type: {type(tracer)}")
try:
    tracer.start_as_current_span("test", attributes={"foo": "bar"})
    print("Success with attributes")
except TypeError as e:
    print(f"Failed with attributes: {e}")

print("-" * 20)
print("Domain NoOpTracing tracer type:")
domain_tracer = DomainNoOpTracing().get_tracer("test")
print(f"Domain Tracer type: {type(domain_tracer)}")
print(inspect.signature(domain_tracer.start_as_current_span))

try:
    domain_tracer.start_as_current_span("test", attributes={"foo": "bar"})
    print("Domain Success with attributes")
except TypeError as e:
    print(f"Domain Failed with attributes: {e}")
