import inspect

import pytest

from bioetl.domain.ports.noop import NoOpTracing as DomainNoOpTracing
from bioetl.infrastructure.observability.noop_tracing import NoOpTracer, NoOpTracing


def test_reproduce_noop_tracer_issue():
    print("\nInfrastructure NoOpTracer start_as_current_span args:")
    sig = inspect.signature(NoOpTracer.start_as_current_span)
    print(sig)

    tracer = NoOpTracing().get_tracer("test")
    print(f"Tracer type: {type(tracer)}")

    # This should not fail
    try:
        tracer.start_as_current_span("test", attributes={"foo": "bar"})
        print("Success with attributes")
    except TypeError as e:
        pytest.fail(f"Failed with attributes: {e}")


def test_reproduce_domain_noop_tracer_issue():
    print("\nDomain NoOpTracing tracer type:")
    domain_tracer = DomainNoOpTracing().get_tracer("test")
    print(f"Domain Tracer type: {type(domain_tracer)}")
    sig = inspect.signature(domain_tracer.start_as_current_span)
    print(sig)

    # This should not fail
    try:
        domain_tracer.start_as_current_span("test", attributes={"foo": "bar"})
        print("Domain Success with attributes")
    except TypeError as e:
        pytest.fail(f"Domain Failed with attributes: {e}")
