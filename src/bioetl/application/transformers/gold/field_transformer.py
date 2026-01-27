"""Unified Silver to Gold field transformer.

Implements unified transformation rules for publication entities as defined
in the Publication Schema Unification Strategy.
"""

from __future__ import annotations

from typing import Any

import orjson
import pandas as pd


class GoldFieldTransformer:
    """Unified transformation logic for Silver -> Gold."""

    TRANSFORM_RULES = {
        # Int->Float for nullable integers (Pandas nullable int -> float for compatibility)
        "int_to_float": [
            "year",
            "citation_count",
            "reference_count",
            "author_count",
            "mesh_heading_count",
            "keyword_count",
            "grant_count",
            "chemical_count",
            "corpus_id",
            "pub_month",
            "pub_day",
            "fwci",  # Added unified metric
        ],
        # JSON string -> Python list (object)
        "json_to_list": [
            "keywords",
            "mesh_terms",
            "chemicals",
            "concepts",
            "fields_of_study",
            "publication_types",
            "subjects",
            "databanks",
            "gene_symbols",
            "affiliations",
            "topics",
            "primary_topic",
            "grants",
            "author_orcids",
            "author_details",
            "references",
            "citation_contexts",
            "authors",  # Added authors
            "alternative_id",
            # issn excluded (can be str or list depending on provider)
            "short_container_title",
            "content_domain_domains",
            "mesh", # OpenAlex
        ],
        # Rename with alias
        "alias_mapping": {
            "_source": "source",
            "_lookup_method": "lookup_method",
            "_original_id": "original_id",
            "_dq_warn": "dq_warn",
            "_dq_error": "dq_error",
        },
    }

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply unified transformations.

        1. Renames columns based on alias_mapping.
        2. Coerces specific integer columns to float.
        3. Deserializes JSON string columns to Python objects (lists/dicts).
        """
        # Apply aliases
        df = df.rename(columns=self.TRANSFORM_RULES["alias_mapping"])

        # Apply int -> float
        for col in self.TRANSFORM_RULES["int_to_float"]:
            if col in df.columns:
                # Convert to numeric, coercing errors to NaN
                df[col] = pd.to_numeric(df[col], errors="coerce").astype(float)

        # Apply json -> list
        for col in self.TRANSFORM_RULES["json_to_list"]:
            if col in df.columns:
                df[col] = df[col].apply(self._safe_json_loads)

        return df

    def _safe_json_loads(self, val: Any) -> Any:
        """Safely load JSON string, returning None on failure or if empty."""
        if pd.isna(val) or val is None or val == "":
            return None
        if not isinstance(val, str):
            # If it's already a list/dict, return as is
            return val
        try:
            return orjson.loads(val)
        except orjson.JSONDecodeError:
            return None
