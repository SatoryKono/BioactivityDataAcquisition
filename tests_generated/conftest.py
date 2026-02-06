"""Shared fixtures for publication validation tests."""

import pytest
import pandas as pd
from datetime import datetime


@pytest.fixture
def minimal_chembl_publication_df() -> pd.DataFrame:
    """Minimal valid ChEMBL publication record."""
    return pd.DataFrame([{
        "document_chembl_id": "CHEMBL1234567",
        "pmid": "12345678",
        "doi": "10.1234/test.2024.001",
        "title": "Test Publication Title",
        "abstract": "Test abstract text for validation.",
        "authors": '["Author A", "Author B"]',
        "journal": "Test Journal",
        "publication_year": 2024,
        "publication_type": "PUBLICATION",
        "volume": "10",
        "issue": "5",
        "page_first": "100",
        "page_last": "110",
        "content_hash": "a" * 64,
        "_source": "chembl",
        "_lookup_method": "direct",
        "_original_id": "CHEMBL1234567",
        "affiliation_list": '["Institution A"]',
        "pmc_id": "PMC1234567",
        "citations_received": 10,
        "citations_made": 5,
        "is_oa": True,
        "language": "eng",
        "publication_date": "2024-01-15",
        "src_id": 123,
        "chembl_release": "CHEMBL_34",
        "creation_date": "2024-01-01",
        "_dq_warn": False,
        "_dq_error": False,
    }])


@pytest.fixture
def minimal_pubmed_publication_df() -> pd.DataFrame:
    """Minimal valid PubMed publication record."""
    return pd.DataFrame([{
        "pmid": "12345678",
        "doi": "10.1234/test.2024.001",
        "pmc_id": "PMC1234567",
        "title": "Test PubMed Publication",
        "abstract": "Test abstract for PubMed validation.",
        "authors": '["Author A", "Author B"]',
        "journal": "Test Journal",
        "publication_year": 2024,
        "publication_date": "2024-01-15",
        "publication_type": "PUBLICATION",
        "language": "eng",
        "page_first": "100",
        "page_last": "110",
        "citations_received": 10,
        "citations_made": 5,
        "is_oa": True,
        "content_hash": "b" * 64,
        "_source": "pubmed",
        "_lookup_method": "direct",
        "_original_id": "12345678",
        "affiliation_list": '["Institution A"]',
        "journal_name_short": "Test J",
        "issn": "1234-5678",
        "country": "USA",
        "author_count": 2,
        "_dq_warn": False,
        "_dq_error": False,
    }])


@pytest.fixture
def minimal_crossref_publication_df() -> pd.DataFrame:
    """Minimal valid CrossRef publication record."""
    return pd.DataFrame([{
        "doi": "10.1234/test.2024.001",
        "pmid": "12345678",
        "title": "Test CrossRef Publication",
        "abstract": "Test abstract for CrossRef validation.",
        "authors": '["Author A", "Author B"]',
        "journal": "Test Journal",
        "publication_year": 2024,
        "publication_date": "2024-01-15",
        "publication_type": "journal-article",
        "language": "en",
        "page_first": "100",
        "page_last": "110",
        "citations_received": 10,
        "citations_made": 5,
        "is_oa": True,
        "content_hash": "c" * 64,
        "_source": "crossref",
        "_lookup_method": "doi",
        "_original_id": "10.1234/test.2024.001",
        "affiliation_list": '["Institution A"]',
        "issn": "1234-5678",
        "publisher": "Test Publisher",
        "_dq_warn": False,
        "_dq_error": False,
    }])


@pytest.fixture
def minimal_openalex_publication_df() -> pd.DataFrame:
    """Minimal valid OpenAlex publication record."""
    return pd.DataFrame([{
        "openalex_id": "W2148763428",
        "doi": "10.1234/test.2024.001",
        "pmid": "12345678",
        "pmc_id": "PMC1234567",
        "title": "Test OpenAlex Publication",
        "abstract": "Test abstract for OpenAlex validation.",
        "authors": '["Author A", "Author B"]',
        "journal": "Test Journal",
        "publication_year": 2024,
        "publication_date": "2024-01-15",
        "publication_type": "article",
        "language": "en",
        "page_first": "100",
        "page_last": "110",
        "citations_received": 10,
        "citations_made": 5,
        "is_oa": True,
        "oa_status": "gold",
        "content_hash": "d" * 64,
        "_source": "openalex",
        "_lookup_method": "doi",
        "_original_id": "10.1234/test.2024.001",
        "affiliation_list": '["Institution A"]',
        "fwci": 1.5,
        "is_retracted": False,
        "_dq_warn": False,
        "_dq_error": False,
    }])


@pytest.fixture
def minimal_semanticscholar_publication_df() -> pd.DataFrame:
    """Minimal valid SemanticScholar publication record."""
    return pd.DataFrame([{
        "paper_id": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0",
        "doi": "10.1234/test.2024.001",
        "pmid": "12345678",
        "title": "Test S2 Publication",
        "abstract": "Test abstract for SemanticScholar validation.",
        "authors": '["Author A", "Author B"]',
        "journal": "Test Journal",
        "publication_year": 2024,
        "publication_date": "2024-01-15",
        "publication_type": "JournalArticle",
        "page_first": "100",
        "page_last": "110",
        "citations_received": 10,
        "citations_made": 5,
        "is_oa": True,
        "oa_status": "gold",
        "content_hash": "e" * 64,
        "_source": "semanticscholar",
        "_lookup_method": "doi",
        "_original_id": "10.1234/test.2024.001",
        "affiliation_list": '["Institution A"]',
        "corpus_id": 12345,
        "influential_citation_count": 5,
        "_dq_warn": False,
        "_dq_error": False,
    }])