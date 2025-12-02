import sys
import types

import pytest


if "structlog" not in sys.modules:
    structlog_module = types.ModuleType("structlog")

    class _BoundLogger:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def bind(self, **ctx):
            return self

        def info(self, *args, **kwargs):
            return None

        def error(self, *args, **kwargs):
            return None

        def debug(self, *args, **kwargs):
            return None

        def warning(self, *args, **kwargs):
            return None

    structlog_module.stdlib = types.SimpleNamespace(BoundLogger=_BoundLogger)
    structlog_module.get_logger = lambda *args, **kwargs: _BoundLogger()
    structlog_module.is_configured = lambda: True
    structlog_module.configure = lambda **kwargs: None
    structlog_module.processors = types.SimpleNamespace(
        TimeStamper=lambda fmt=None: None, JSONRenderer=lambda: None
    )
    structlog_module.PrintLoggerFactory = lambda: None

    sys.modules["structlog"] = structlog_module
    sys.modules["structlog.stdlib"] = structlog_module.stdlib

if "tqdm" not in sys.modules:
    tqdm_module = types.ModuleType("tqdm")

    def _noop_tqdm(*args, **kwargs):
        return None

    tqdm_module.tqdm = _noop_tqdm
    sys.modules["tqdm"] = tqdm_module

from bioetl.core.custom_types import (
    CUSTOM_FIELD_NORMALIZERS,
    normalize_array,
    normalize_chembl_id,
    normalize_doi,
    normalize_pcid,
    normalize_pmid,
    normalize_record,
    normalize_uniprot,
)


class TestIdentifierNormalizers:
    def test_normalize_doi(self):
        assert normalize_doi("https://doi.org/10.1000/ABC") == "10.1000/abc"
        with pytest.raises(ValueError):
            normalize_doi("not-a-doi")

    def test_normalize_chembl(self):
        assert normalize_chembl_id("chembl12") == "CHEMBL12"
        assert normalize_chembl_id("12") == "CHEMBL12"
        with pytest.raises(ValueError):
            normalize_chembl_id("CHEMBL12X")

    def test_normalize_pmid(self):
        assert normalize_pmid("12345") == "12345"
        with pytest.raises(ValueError):
            normalize_pmid("pmid123")

    def test_normalize_pcid(self):
        assert normalize_pcid("CID987") == "987"
        with pytest.raises(ValueError):
            normalize_pcid("CID98X")

    def test_normalize_uniprot(self):
        assert normalize_uniprot("p12345") == "P12345"
        with pytest.raises(ValueError):
            normalize_uniprot("invalid")


class TestCollectionNormalizers:
    def test_normalize_array_with_scalar(self):
        result = normalize_array([" 10.1234/XYZ "], item_normalizer=normalize_doi)
        assert result == ["10.1234/xyz"]

    def test_normalize_array_error(self):
        with pytest.raises(ValueError):
            normalize_array("not-a-list", item_normalizer=str)

    def test_normalize_record(self):
        result = normalize_record({"pmid": "123"}, value_normalizer=normalize_pmid)
        assert result == {"pmid": "123"}

    def test_normalize_record_error(self):
        with pytest.raises(ValueError):
            normalize_record([1, 2])


def test_custom_field_normalizers_contains_expected_keys():
    for key in [
        "doi",
        "doi_chembl",
        "document_chembl_id",
        "pubmed_id",
        "pcid",
        "uniprot_accession",
    ]:
        assert key in CUSTOM_FIELD_NORMALIZERS
