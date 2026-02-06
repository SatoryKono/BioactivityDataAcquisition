"""Shared fixtures for publication validation tests."""

import pytest
import pandas as pd
from datetime import datetime
from uuid import uuid4


@pytest.fixture
def minimal_chembl_publication_df() -> pd.DataFrame:
    """Minimal valid ChEMBL publication record."""
    return pd.DataFrame([{
        # Primary identifier
        "document_chembl_id": "CHEMBL1234567",
        # ETL metadata (required by ETLRecordSchema)
        "entity_id": "CHEMBL1234567",
        "_run_id": str(uuid4()),
        "_run_type": "incremental",
        "_ingestion_ts": datetime.now().isoformat(),
        "_source_batch_id": None,
        "_index": 0,
        # Cross-reference identifiers
        "pmid": "12345678",
        "doi": "10.1234/test.2024.001",
        "pmc_id": "PMC1234567",
        # Core content
        "title": "Test Publication Title",
        "abstract": "Test abstract text for validation.",
        "authors": '["Author A", "Author B"]',
        "affiliation_list": '["Institution A"]',
        # Journal information
        "journal": "Test Journal",
        "volume": "10",
        "issue": "5",
        "page_first": "100",
        "page_last": "110",
        # Publication metadata
        "publication_year": 2024,
        "publication_date": "2024-01-15",
        "publication_type": "PUBLICATION",
        "language": "eng",
        # Metrics
        "citations_received": 10,
        "citations_made": 5,
        "is_oa": True,
        # Provider-specific
        "src_id": 123,
        "chembl_release": "CHEMBL_34",
        "creation_date": "2024-01-01",
        # System fields
        "content_hash": "a" * 64,
        "_source": "chembl",
        "_lookup_method": "direct",
        "_original_id": "CHEMBL1234567",
        "_dq_warn": False,
        "_dq_error": False,
    }])


@pytest.fixture
def minimal_pubmed_publication_df() -> pd.DataFrame:
    """Minimal valid PubMed publication record."""
    return pd.DataFrame([{
        # Primary identifier
        "pmid": "12345678",
        # ETL metadata (required by ETLRecordSchema)
        "entity_id": "12345678",
        "_run_id": str(uuid4()),
        "_run_type": "incremental",
        "_ingestion_ts": datetime.now().isoformat(),
        "_source_batch_id": None,
        "_index": 0,
        # Cross-reference identifiers
        "doi": "10.1234/test.2024.001",
        "pmc_id": "PMC1234567",
        # Core content
        "title": "Test PubMed Publication",
        "abstract": "Test abstract for PubMed validation.",
        "authors": '["Author A", "Author B"]',
        "affiliation_list": '["Institution A"]',
        "author_count": 2,
        # Journal information
        "journal": "Test Journal",
        "journal_name_short": "Test J",
        "issn": "1234-5678",
        "country": "USA",
        "page_first": "100",
        "page_last": "110",
        # Publication metadata
        "publication_year": 2024,
        "publication_date": "2024-01-15",
        "publication_type": "PUBLICATION",
        "language": "eng",
        # Metrics
        "citations_received": 10,
        "citations_made": 5,
        "is_oa": True,
        # PubMed-specific fields (all nullable)
        "pii": None,
        "mid": None,
        "publisher_id": None,
        "abstract_structured": None,
        "journal_iso_abbrev": None,
        "journal_issn_type": None,
        "nlm_unique_id": None,
        "medline_pgn": None,
        "page_range": None,
        "pub_month": None,
        "pub_day": None,
        "publication_status": None,
        "publication_type_list": None,
        "date_completed": None,
        "date_revised": None,
        "citation_subset": None,
        "affiliation_structured": None,
        "mesh_heading_count": None,
        "keyword_count": None,
        "grant_count": None,
        "chemical_count": None,
        "subject_mesh": None,
        "chemicals": None,
        "subject_keywords": None,
        "databanks": None,
        "gene_symbols": None,
        "publication_types": None,
        "authors_with_affiliations": None,
        # System fields
        "content_hash": "b" * 64,
        "_source": "pubmed",
        "_lookup_method": "direct",
        "_original_id": "12345678",
        "_dq_warn": False,
        "_dq_error": False,
    }])


@pytest.fixture
def minimal_crossref_publication_df() -> pd.DataFrame:
    """Minimal valid CrossRef publication record."""
    return pd.DataFrame([{
        # Primary identifier
        "doi": "10.1234/test.2024.001",
        # ETL metadata (required by ETLRecordSchema)
        "entity_id": "10.1234/test.2024.001",
        "_run_id": str(uuid4()),
        "_run_type": "incremental",
        "_ingestion_ts": datetime.now().isoformat(),
        "_source_batch_id": None,
        "_index": 0,
        # Cross-reference identifiers
        "pmid": "12345678",
        # Core content
        "title": "Test CrossRef Publication",
        "abstract": "Test abstract for CrossRef validation.",
        "authors": '["Author A", "Author B"]',
        "affiliation_list": '["Institution A"]',
        # Journal information
        "journal": "Test Journal",
        "issn": "1234-5678",
        "publisher": "Test Publisher",
        "page_first": "100",
        "page_last": "110",
        # Publication metadata
        "publication_year": 2024,
        "publication_date": "2024-01-15",
        "publication_type": "journal-article",
        "language": "en",
        # Metrics
        "citations_received": 10,
        "citations_made": 5,
        "is_oa": True,
        # CrossRef-specific fields (all nullable)
        "issn_list": None,
        "published_print": None,
        "published_online": None,
        "license_url": None,
        "subject_keywords": None,
        "content_domain_domains": None,
        "content_domain_crossmark_restriction": None,
        "alternative_id": None,
        "published": None,
        "journal_name_short": None,
        "issn_print": None,
        "issn_electronic": None,
        "author_orcid_list": None,
        "author_details": None,
        "references": None,
        # System fields
        "content_hash": "c" * 64,
        "_source": "crossref",
        "_lookup_method": "doi",
        "_original_id": "10.1234/test.2024.001",
        "_dq_warn": False,
        "_dq_error": False,
    }])


@pytest.fixture
def minimal_openalex_publication_df() -> pd.DataFrame:
    """Minimal valid OpenAlex publication record."""
    return pd.DataFrame([{
        # Primary identifier
        "openalex_id": "W2148763428",
        # ETL metadata (required by ETLRecordSchema)
        "entity_id": "W2148763428",
        "_run_id": str(uuid4()),
        "_run_type": "incremental",
        "_ingestion_ts": datetime.now().isoformat(),
        "_source_batch_id": None,
        "_index": 0,
        # Cross-reference identifiers
        "doi": "10.1234/test.2024.001",
        "pmid": "12345678",
        "pmc_id": "PMC1234567",
        # Core content
        "title": "Test OpenAlex Publication",
        "abstract": "Test abstract for OpenAlex validation.",
        "authors": '["Author A", "Author B"]',
        "affiliation_list": '["Institution A"]',
        # Journal information
        "journal": "Test Journal",
        "page_first": "100",
        "page_last": "110",
        # Publication metadata
        "publication_year": 2024,
        "publication_date": "2024-01-15",
        "publication_type": "article",
        "language": "en",
        # Metrics
        "citations_received": 10,
        "citations_made": 5,
        "is_oa": True,
        "oa_status": "gold",
        "fwci": 1.5,
        "is_retracted": False,
        # OpenAlex-specific fields (all nullable)
        "issn": None,
        "publisher": None,
        "volume": None,
        "issue": None,
        "subject_topics": None,
        "primary_topic": None,
        "grants": None,
        "subject_mesh": None,
        "subject_keywords": None,
        "mag_id": None,
        "author_orcids": None,
        "author_openalex_ids": None,
        "institution_ids": None,
        "institution_country_codes": None,
        "ror_ids": None,
        # System fields
        "content_hash": "d" * 64,
        "_source": "openalex",
        "_lookup_method": "doi",
        "_original_id": "10.1234/test.2024.001",
        "_dq_warn": False,
        "_dq_error": False,
    }])


@pytest.fixture
def minimal_semanticscholar_publication_df() -> pd.DataFrame:
    """Minimal valid SemanticScholar publication record."""
    return pd.DataFrame([{
        # Primary identifier (40-char hex)
        "paper_id": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0",
        # ETL metadata (required by ETLRecordSchema)
        "entity_id": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0",
        "_run_id": str(uuid4()),
        "_run_type": "incremental",
        "_ingestion_ts": datetime.now().isoformat(),
        "_source_batch_id": None,
        "_index": 0,
        # Cross-reference identifiers
        "doi": "10.1234/test.2024.001",
        "pmid": "12345678",
        "pmc_id": None,  # Inherited from PublicationBaseSchema (nullable)
        "corpus_id": 12345,
        # Core content
        "title": "Test S2 Publication",
        "abstract": "Test abstract for SemanticScholar validation.",
        "authors": '["Author A", "Author B"]',
        "affiliation_list": '["Institution A"]',
        # Journal information
        "journal": "Test Journal",
        "page_first": "100",
        "page_last": "110",
        # Publication metadata
        "publication_year": 2024,
        "publication_date": "2024-01-15",
        "publication_type": "JournalArticle",
        "language": None,  # Inherited from PublicationBaseSchema (nullable)
        # Metrics
        "citations_received": 10,
        "citations_made": 5,
        "influential_citation_count": 5,
        "is_oa": True,
        "oa_status": "gold",
        # SemanticScholar-specific fields (all nullable)
        "dblp_id": None,
        "tldr": None,
        "volume": None,
        "page_range": None,
        "open_access_url": None,
        "subject_fields": None,
        "publication_types": None,
        "author_s2_ids": None,
        "author_orcids": None,
        "author_h_indices": None,
        "citation_contexts": None,
        # System fields
        "content_hash": "e" * 64,
        "_source": "semanticscholar",
        "_lookup_method": "doi",
        "_original_id": "10.1234/test.2024.001",
        "_dq_warn": False,
        "_dq_error": False,
    }])