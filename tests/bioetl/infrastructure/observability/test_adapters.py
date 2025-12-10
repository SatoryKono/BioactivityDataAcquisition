from bioetl.infrastructure.observability.adapters import (
    PrometheusMetricsPortImpl,
    StructuredLoggerImpl,
    TracingAdapterImpl,
)
from bioetl.infrastructure.settings.metrics import MetricName


def test_structured_logger_bind_and_log():
    logger = StructuredLoggerImpl()
    bound = logger.apply_bind(run_id="t1", stage="extract")
    bound.info("evt", entity="activity")
    bound.error("err", code="E1")


def test_tracing_adapter_noop():
    tracer = TracingAdapterImpl()
    span = tracer.start_span("s1")
    assert span["span"] == "s1"
    headers = {}
    tracer.inject_context(headers)
    assert headers.get("trace") == "noop"


def test_prometheus_metrics_port_updates():
    port = PrometheusMetricsPortImpl()
    port.inc_counter(
        MetricName.CLIENT_REQUEST_TOTAL,
        {"provider": "chembl", "endpoint": "/e", "status": "200"},
    )
    port.observe_histogram(
        MetricName.CLIENT_REQUEST_DURATION_SECONDS,
        0.1,
        {"provider": "chembl", "endpoint": "/e", "status": "200"},
    )
    port.update_stage_total(
        pipeline="p1",
        provider="chembl",
        entity="activity",
        stage="extract",
        outcome="ok",
    )
    port.update_stage_duration(
        pipeline="p1",
        provider="chembl",
        entity="activity",
        stage="extract",
        outcome="ok",
        duration_sec=0.05,
    )
