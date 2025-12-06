from prometheus_client import Histogram

from bioetl.application.pipelines.hooks_impl import MetricsPipelineHookImpl
from bioetl.domain.models import StageResult
from bioetl.infrastructure.observability import metrics


def _histogram_stats(child: Histogram) -> tuple[float, float]:
    samples = {
        sample.name: sample.value
        for sample in child._samples()
        if sample.name in {"_sum", "_count"}
    }
    return samples["_sum"], samples["_count"]


def _reset_metrics() -> None:
    metrics.STAGE_DURATION_SECONDS._metrics.clear()
    metrics.STAGE_TOTAL._metrics.clear()


def test_metrics_hook_records_successful_stage() -> None:
    _reset_metrics()
    hook = MetricsPipelineHookImpl(
        pipeline_id="pipeline-x",
        provider="chembl",
        entity_name="activity",
    )
    result = StageResult(
        stage_name="extract",
        success=True,
        records_processed=5,
        chunks_processed=1,
        duration_sec=1.5,
        errors=[],
    )

    hook.on_stage_end("extract", result)

    histogram_child = metrics.STAGE_DURATION_SECONDS.labels(
        pipeline="pipeline-x",
        provider="chembl",
        entity="activity",
        stage="extract",
        outcome="success",
    )
    counter_child = metrics.STAGE_TOTAL.labels(
        pipeline="pipeline-x",
        provider="chembl",
        entity="activity",
        stage="extract",
        outcome="success",
    )

    duration_sum, duration_count = _histogram_stats(histogram_child)

    assert duration_sum == 1.5
    assert duration_count == 1.0
    assert counter_child._value.get() == 1.0


def test_metrics_hook_records_failed_stage() -> None:
    _reset_metrics()
    hook = MetricsPipelineHookImpl(
        pipeline_id="pipeline-x",
        provider="chembl",
        entity_name="activity",
    )
    result = StageResult(
        stage_name="validate",
        success=False,
        records_processed=0,
        chunks_processed=0,
        duration_sec=0.2,
        errors=["boom"],
    )

    hook.on_stage_end("validate", result)

    histogram_child = metrics.STAGE_DURATION_SECONDS.labels(
        pipeline="pipeline-x",
        provider="chembl",
        entity="activity",
        stage="validate",
        outcome="error",
    )
    counter_child = metrics.STAGE_TOTAL.labels(
        pipeline="pipeline-x",
        provider="chembl",
        entity="activity",
        stage="validate",
        outcome="error",
    )

    duration_sum, duration_count = _histogram_stats(histogram_child)

    assert duration_sum == 0.2
    assert duration_count == 1.0
    assert counter_child._value.get() == 1.0
