import pytest

from bioetl.application.contracts import PipelineFactoryABC
from bioetl.application.pipelines.base import PipelineBase
from bioetl.application.pipelines.registry import (
    get_pipeline_class,
    get_pipeline_factory,
    list_pipelines,
)


def test_get_pipeline_class_success():
    # Test getting all registered pipelines
    for name in list_pipelines():
        pipeline_cls = get_pipeline_class(name)
        assert issubclass(pipeline_cls, PipelineBase)


def test_get_pipeline_class_failure():
    with pytest.raises(ValueError, match="Pipeline factory 'unknown' not found"):
        get_pipeline_class("unknown")


def test_get_pipeline_factory_success():
    for name in list_pipelines():
        factory = get_pipeline_factory(name)
        assert isinstance(factory, PipelineFactoryABC)
