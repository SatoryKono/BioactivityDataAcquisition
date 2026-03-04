"""Publication-oriented Silver layer schemas."""

from __future__ import annotations

import pyarrow as pa

PUBMED_PUBLICATION_SCHEMA = pa.schema(
    [
        # === System prefix (MUST be first, per RULES.md §2.4) ===
        pa.field("entity_id", pa.string()),
        pa.field("content_hash", pa.string()),
        pa.field("_run_id", pa.string()),
        pa.field("_run_type", pa.string()),
        pa.field("_source_batch_id", pa.string()),
        pa.field("_source", pa.string()),
        pa.field("_ingestion_ts", pa.string()),
        pa.field("_index", pa.int64()),
        # === Business fields (alphabetical order) ===
        pa.field("_lookup_method", pa.string()),
        pa.field("_original_id", pa.string()),
        pa.field("abstract", pa.string()),
        pa.field(
            "abstract_structured", pa.bool_()
        ),  # Whether abstract has NLM sections
        pa.field("affiliation_list", pa.string()),  # JSON array of unique affiliations
        pa.field("affiliation_structured", pa.string()),  # JSON array with ROR/GRID
        pa.field("author_count", pa.int64()),
        pa.field("author_keys", pa.string()),  # Pipe-delimited Surname_F keys
        pa.field("authors", pa.string()),  # JSON-serialized list
        pa.field("authors_with_affiliations", pa.string()),  # JSON array
        pa.field("chemical_count", pa.int64()),
        pa.field("chemicals", pa.string()),  # Chemical substances (JSON array)
        pa.field("citation_subset", pa.string()),  # Citation subset codes
        pa.field("citations_made", pa.int64()),  # Unified: citations made
        # citations_received: excluded (PubMed doesn't provide citation metrics)
        pa.field("country", pa.string()),
        pa.field("databanks", pa.string()),  # Databank accession numbers (JSON array)
        pa.field("date_completed", pa.string()),  # MEDLINE processing completion date
        pa.field("date_revised", pa.string()),  # Record revision date
        pa.field("doi", pa.string()),
        pa.field("gene_symbols", pa.string()),  # Gene symbols (JSON array)
        pa.field("grant_count", pa.int64()),
        # is_oa: excluded (PubMed doesn't provide OA status directly)
        pa.field("issn", pa.string()),
        pa.field("issue", pa.string()),
        pa.field("journal", pa.string()),
        pa.field("journal_iso_abbrev", pa.string()),  # ISO journal abbreviation
        pa.field("journal_issn_type", pa.string()),  # Print/Electronic/Linking
        pa.field("journal_name_short", pa.string()),  # Journal abbreviation
        pa.field("keyword_count", pa.int64()),
        pa.field("language", pa.string()),
        pa.field("medline_pgn", pa.string()),  # Original PubMed pagination
        pa.field("mesh_heading_count", pa.int64()),
        pa.field("mid", pa.string()),  # Manuscript ID (PMC submission)
        pa.field("nlm_unique_id", pa.string()),  # NLM catalog ID
        pa.field("page_first", pa.string()),
        pa.field("page_last", pa.string()),
        pa.field("page_range", pa.string()),  # Page range string
        pa.field("pii", pa.string()),  # Publisher Item Identifier
        pa.field("pmc_id", pa.string()),
        pa.field("pmid", pa.string(), nullable=False),
        pa.field("pub_date", pa.string()),
        pa.field("pub_day", pa.int64()),  # Publication day (1-31)
        pa.field("pub_month", pa.int64()),  # Publication month (1-12)
        pa.field("publication_class", pa.string()),  # Level 1: "EXP" | "REV" | "PEER"
        pa.field("publication_date", pa.string()),  # Unified: YYYY-MM-DD format
        pa.field("publication_status", pa.string()),  # ppublish/epublish/aheadofprint
        pa.field(
            "publication_subclass", pa.string()
        ),  # Level 2: "Original Experimental Data", etc.
        pa.field("publication_type", pa.string()),  # Unified: publication type
        pa.field("publication_type_list", pa.string()),  # JSON array of pub types
        pa.field(
            "publication_type_unified", pa.string()
        ),  # Level 3: "Journal Article", etc.
        pa.field("publication_types", pa.list_(pa.string())),
        pa.field("publication_year", pa.int64()),
        pa.field("publisher_id", pa.string()),  # Publisher-specific identifier
        pa.field("subject_keywords", pa.list_(pa.string())),  # Author keywords
        pa.field("subject_mesh", pa.list_(pa.string())),  # MeSH terms
        pa.field("title", pa.string()),
        pa.field("volume", pa.string()),
        # === DQ suffix (MUST be last, per RULES.md §2.4) ===
        pa.field("_dq_error", pa.bool_()),
        pa.field("_dq_warn", pa.bool_()),
    ]
)

# Schema for ChEMBL Assay
# See: https://www.ebi.ac.uk/chembl/api/data/assay

SEMANTICSCHOLAR_PUBLICATION_SCHEMA = pa.schema(
    [
        # === System prefix (MUST be first, per RULES.md §2.4) ===
        pa.field("entity_id", pa.string()),
        pa.field("content_hash", pa.string()),
        pa.field("_run_id", pa.string()),
        pa.field("_run_type", pa.string()),
        pa.field("_source_batch_id", pa.string()),
        pa.field("_source", pa.string()),
        pa.field("_ingestion_ts", pa.string()),
        pa.field("_index", pa.int64()),
        # === Business fields (alphabetical order) ===
        # Lookup metadata
        pa.field("_lookup_method", pa.string()),
        pa.field("_original_id", pa.string()),
        pa.field("abstract", pa.string()),
        pa.field("affiliation_list", pa.string()),  # JSON array
        # Author identifiers (for author-level analytics)
        pa.field("author_h_indices", pa.string()),  # JSON array of h-index values
        pa.field("author_keys", pa.string()),  # Pipe-delimited Surname_F keys
        pa.field("author_orcids", pa.string()),
        pa.field("author_s2_ids", pa.string()),  # JSON array of S2 author IDs
        pa.field("authors", pa.string()),  # JSON-serialized list
        pa.field("citation_contexts", pa.string()),  # JSON array of context sentences
        pa.field("citations_made", pa.int64()),  # Unified: from referenceCount
        pa.field("citations_received", pa.int64()),  # Unified: from citationCount
        pa.field("corpus_id", pa.int64()),
        pa.field("dblp_id", pa.string()),  # DBLP publication key
        pa.field("doi", pa.string()),
        pa.field("influential_citation_count", pa.int64()),
        pa.field("is_oa", pa.bool_()),
        pa.field("issue", pa.string()),
        pa.field("journal", pa.string()),
        pa.field("oa_status", pa.string()),
        pa.field("open_access_url", pa.string()),
        pa.field("page_first", pa.string()),
        pa.field("page_last", pa.string()),
        pa.field("page_range", pa.string()),  # Page range: "first-last" format
        pa.field("paper_id", pa.string(), nullable=False),  # Primary key
        pa.field(
            "pmc_id", pa.string()
        ),  # PubMed Central ID (inherited from base schema)
        pa.field("pmid", pa.string()),
        pa.field("publication_class", pa.string()),  # Level 1: "EXP" | "REV" | "PEER"
        pa.field("publication_date", pa.string()),
        pa.field(
            "publication_subclass", pa.string()
        ),  # Level 2: "Original Experimental Data", etc.
        pa.field(
            "publication_type", pa.string()
        ),  # Unified: from publicationTypes (joined)
        pa.field(
            "publication_type_unified", pa.string()
        ),  # Level 3: "Journal Article", etc.
        pa.field("publication_types", pa.string()),  # Raw publicationTypes (JSON array)
        pa.field("publication_year", pa.int64()),
        pa.field("subject_fields", pa.string()),
        pa.field("title", pa.string()),
        pa.field("tldr", pa.string()),
        pa.field("volume", pa.string()),
        # === DQ suffix (MUST be last, if present) ===
        pa.field("_dq_error", pa.bool_()),
        pa.field("_dq_warn", pa.bool_()),
    ]
)

# Schema for CrossRef Publication
# See: https://api.crossref.org/swagger-ui/index.html
CROSSREF_PUBLICATION_SCHEMA = pa.schema(
    [
        # === System prefix (MUST be first, per RULES.md §2.4) ===
        pa.field("entity_id", pa.string()),
        pa.field("content_hash", pa.string()),
        pa.field("_run_id", pa.string()),
        pa.field("_run_type", pa.string()),
        pa.field("_source_batch_id", pa.string()),
        pa.field("_source", pa.string()),
        pa.field("_ingestion_ts", pa.string()),
        pa.field("_index", pa.int64()),
        # _lookup_method: "direct" | "doi" | "pmid" | "title_fallback" | "unknown"
        pa.field("_lookup_method", pa.string()),
        pa.field("_original_id", pa.string()),
        # === Business fields (alphabetical order) ===
        # Note: abstract and affiliation_list not provided by CrossRef but required by PublicationBaseSchema
        pa.field("abstract", pa.string()),  # Not available from CrossRef (None values)
        pa.field(
            "affiliation_list", pa.string()
        ),  # Not available from CrossRef (None values)
        pa.field(
            "alternative_id", pa.string()
        ),  # Publisher-specific IDs (canonical JSON)
        pa.field("author_details", pa.string()),  # JSON array of author objects
        pa.field("author_keys", pa.string()),  # Pipe-delimited Surname_F keys
        pa.field("author_orcids", pa.string()),
        pa.field("authors", pa.string()),  # JSON-serialized list
        pa.field("citations_made", pa.int64()),  # Unified: from references-count
        pa.field(
            "citations_received", pa.int64()
        ),  # Unified: from is-referenced-by-count
        pa.field("content_domain_crossmark_restriction", pa.bool_()),
        pa.field("content_domain_domains", pa.string()),
        # Note: doc_type excluded; CrossRef uses raw 'type' field instead
        # doi: Digital Object Identifier (lowercase, without "https://doi.org/") - Primary key
        pa.field("doi", pa.string(), nullable=False),
        pa.field("issn", pa.string()),
        pa.field("issn_electronic", pa.string()),  # Electronic ISSN
        pa.field("issn_list", pa.string()),  # JSON array of all ISSNs
        pa.field("issn_print", pa.string()),  # Print ISSN
        pa.field("issue", pa.string()),
        pa.field("journal", pa.string()),
        pa.field("journal_name_short", pa.string()),
        pa.field("language", pa.string()),
        pa.field("license_url", pa.string()),
        pa.field("page_first", pa.string()),
        pa.field("page_last", pa.string()),
        # Note: pmid and pmc_id not provided by CrossRef but required by PublicationBaseSchema
        pa.field("pmc_id", pa.string()),  # Not available from CrossRef (None values)
        pa.field("pmid", pa.string()),  # Not available from CrossRef (None values)
        pa.field("publication_class", pa.string()),  # Level 1: "EXP" | "REV" | "PEER"
        pa.field("publication_date", pa.string()),  # Unified: YYYY-MM-DD
        pa.field(
            "publication_subclass", pa.string()
        ),  # Level 2: "Original Experimental Data", etc.
        pa.field(
            "publication_type", pa.string()
        ),  # Raw CrossRef type (journal-article, etc.)
        pa.field(
            "publication_type_unified", pa.string()
        ),  # Level 3: "Journal Article", etc.
        pa.field("publication_year", pa.int64()),
        pa.field("published", pa.string()),  # Canonical publication date
        pa.field("published_online", pa.string()),  # Provider-specific
        pa.field("published_print", pa.string()),  # Provider-specific
        pa.field("publisher", pa.string()),
        pa.field("references", pa.string()),  # JSON array of cited references
        pa.field("subject_keywords", pa.list_(pa.string())),
        pa.field("title", pa.string()),
        pa.field("volume", pa.string()),
        # === DQ suffix (MUST be last, per RULES.md §2.4) ===
        pa.field("_dq_error", pa.bool_()),
        pa.field("_dq_warn", pa.bool_()),
    ]
)

# Schema for OpenAlex Publication
# See: https://docs.openalex.org/api-entities/works
OPENALEX_PUBLICATION_SCHEMA = pa.schema(
    [
        # === System prefix (MUST be first, per RULES.md §2.4) ===
        pa.field("entity_id", pa.string()),
        pa.field("content_hash", pa.string()),
        pa.field("_run_id", pa.string()),
        pa.field("_run_type", pa.string()),
        pa.field("_source_batch_id", pa.string()),
        pa.field("_source", pa.string()),
        pa.field("_ingestion_ts", pa.string()),
        pa.field("_index", pa.int64()),
        # === Business fields (alphabetical order) ===
        # Lookup metadata
        # _lookup_method: "direct" | "doi" | "pmid" | "title_fallback" | "unknown"
        # _original_id: Original identifier used for lookup
        pa.field("_lookup_method", pa.string()),
        pa.field("_original_id", pa.string()),
        pa.field("abstract", pa.string()),
        pa.field("affiliation_list", pa.string()),  # JSON array
        # Author identifiers (JSON arrays preserving author order)
        pa.field("author_keys", pa.string()),  # Pipe-delimited Surname_F keys
        pa.field("author_openalex_ids", pa.string()),  # OpenAlex author IDs
        pa.field("author_orcids", pa.string()),
        pa.field("authors", pa.string()),  # JSON-serialized list
        # Unified: from referenced_works_count
        pa.field("citations_made", pa.int64()),
        # OpenAlex source field: cited_by_count
        # Unified BioETL field: citations_received (standardized across all providers)
        pa.field("citations_received", pa.int64()),
        # NOTE: concepts field removed - OpenAlex deprecated concepts in 2024, use topics instead
        # Note: doc_type excluded; OpenAlex uses raw 'type' field instead
        # Cross-reference IDs for linking publications across providers
        # doi: Digital Object Identifier (lowercase, without "https://doi.org/")
        pa.field("doi", pa.string()),
        # Field-Weighted Citation Impact (must be non-negative)
        pa.field("fwci", pa.float64()),
        # Grants/funding information (JSON array)
        pa.field("grants", pa.string()),
        # Institution identifiers (for cross-referencing and geographic analysis)
        pa.field("institution_country_codes", pa.list_(pa.string())),
        pa.field("institution_ids", pa.list_(pa.string())),
        pa.field("is_oa", pa.bool_()),
        # Quality indicators
        pa.field("is_retracted", pa.bool_()),
        # Journal info
        pa.field("issn", pa.string()),
        # Bibliographic info (from biblio object)
        pa.field("issue", pa.string()),
        pa.field("journal", pa.string()),
        pa.field("language", pa.string()),
        # Microsoft Academic Graph ID (legacy, from ids object)
        pa.field("mag_id", pa.string()),
        pa.field("oa_status", pa.string()),
        # Primary key
        pa.field("openalex_id", pa.string(), nullable=False),
        # Unified page fields (from biblio object)
        pa.field("page_first", pa.string()),
        pa.field("page_last", pa.string()),
        # PubMed Central ID - Not available from OpenAlex API (None values)
        pa.field("pmc_id", pa.string()),
        # pmid: PubMed ID (numeric string: "12345678") - nullable, may not exist for all publications
        pa.field("pmid", pa.string()),
        # Primary topic (single most relevant topic for quick categorization)
        pa.field("primary_topic", pa.string()),  # JSON object
        pa.field("publication_class", pa.string()),  # Level 1: "EXP" | "REV" | "PEER"
        pa.field("publication_date", pa.string()),
        pa.field(
            "publication_subclass", pa.string()
        ),  # Level 2: "Original Experimental Data", etc.
        pa.field(
            "publication_type", pa.string()
        ),  # Raw OpenAlex type (article, book, etc.)
        pa.field(
            "publication_type_unified", pa.string()
        ),  # Level 3: "Journal Article", etc.
        pa.field("publication_year", pa.int64()),
        pa.field("publisher", pa.string()),
        # ROR IDs (may be empty if not returned by Works API)
        pa.field("ror_ids", pa.string()),  # JSON array of ROR URLs
        # Keywords extracted from OpenAlex
        pa.field("subject_keywords", pa.list_(pa.string())),
        # MeSH terms extracted from OpenAlex mesh field
        pa.field("subject_mesh", pa.list_(pa.string())),
        # Topics (hierarchical 4-level classification - replaces deprecated concepts)
        pa.field("subject_topics", pa.string()),  # JSON array
        pa.field("title", pa.string()),
        # Bibliographic info (from biblio object)
        pa.field("volume", pa.string()),
        # === DQ suffix (MUST be last, per RULES.md §2.4) ===
        pa.field("_dq_error", pa.bool_()),
        pa.field("_dq_warn", pa.bool_()),
    ]
)

# Schema for ChEMBL Protein Classification
# See: https://www.ebi.ac.uk/chembl/api/data/protein_class
