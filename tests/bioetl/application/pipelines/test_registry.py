import pytest

from bioetl.application.pipelines.base import PipelineBase
from bioetl.application.pipelines.registry import PIPELINE_REGISTRY, get_pipeline_class


def test_get_pipeline_class_success():
    # Test getting all registered pipelines
    for name, cls in PIPELINE_REGISTRY.items():
        pipeline_cls = get_pipeline_class(name)
        assert pipeline_cls == cls
        assert issubclass(pipeline_cls, PipelineBase)


def test_get_pipeline_class_failure():
    with pytest.raises(ValueError, match="Pipeline 'unknown' not found"):
        get_pipeline_class("unknown")
