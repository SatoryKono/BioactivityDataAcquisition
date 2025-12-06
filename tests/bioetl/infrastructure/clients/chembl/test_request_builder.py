from bioetl.infrastructure.clients.chembl.request_builder import (
    ChemblRequestBuilderImpl,
)


def test_build_url():
    builder = ChemblRequestBuilderImpl("http://api")
    url = builder.for_endpoint("test").build({"a": 1, "b": None})
    assert url == "http://api/test.json?a=1"

def test_pagination():
    builder = ChemblRequestBuilderImpl("http://api")
    builder.with_pagination(0, 10)
    assert builder._params["offset"] == 0
    assert builder._params["limit"] == 10

def test_base_url_trim():
    builder = ChemblRequestBuilderImpl("http://api/")
    assert builder.base_url == "http://api"

def test_endpoint_trim():
    builder = ChemblRequestBuilderImpl("http://api")
    builder.for_endpoint("/test/")
    assert builder._endpoint == "test"
