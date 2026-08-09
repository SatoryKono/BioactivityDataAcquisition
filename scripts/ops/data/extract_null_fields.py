#!/usr/bin/env python3
"""Null Field Extraction Tool.

Extracts specified null/empty fields from publication CSV files for analysis.
This tool helps identify consistently empty fields across different data sources.

Usage:
    python scripts/ops/data/extract_null_fields.py <base_path> <output_path>

Arguments:
    base_path: Base path to silver data directory (default: hardcoded path)
    output_path: Output directory for extracted null fields (default: hardcoded path)

Examples:
    # Extract null fields with default paths
    python scripts/ops/data/extract_null_fields.py

    # Extract to custom locations
    python scripts/ops/data/extract_null_fields.py /path/to/data /path/to/output

Returns:
    int: Exit code (0 for success, non-zero for errors)

Raises:
    ValueError: When input paths are invalid
    RuntimeError: When CSV files cannot be processed

Note:
    This script currently uses hardcoded paths and should be updated
    to accept command-line arguments for production use.
"""

from pathlib import Path

import pandas as pd

# Поля для извлечения (всегда пустые/null)
NULL_FIELDS = {
    "crossref": [
        "pmid",
        "abstract",
        "author_orcids",
        "affiliation_list",
        "oa_status",
        "pmc_id",
        "is_oa",
        "publication_pmc_id",
        "publication_pmid",
        "author_ormolecule_ids",
        "publication_doi",
    ],
    "semanticscholar": [
        "citation_contexts",
        "influential_citation_count",
        "author_orcids",
        "author_ormolecule_ids",
        "language",
        "affiliation_list",
        "authors",
        "pmc_id",
        "publication_pmc_id",
        "publisher",
        "issn",
        "publication_pmid",
        "dblp_id",
        "publication_doi",
    ],
    "chembl": [
        "author_orcids",
        "language",
        "affiliation_list",
        "publication_date",
        "citations_received",
        "publication_subclass",
        "publication_class",
        "pmc_id",
        "is_oa",
        "publication_type_unified",
        "publication_pmc_id",
        "citations_made",
    ],
    "pubmed": [
        "author_orcids",
        "publisher_id",
        "oa_status",
        "is_oa",
        "publication_pmc_id",
        "publisher",
        "publication_pmid",
        "publication_doi",
    ],
    "openalex": [
        "pmc_id",
        "publication_pmc_id",
        "grants",
        "publication_pmid",
        "author_ormolecule_ids",
        "publication_doi",
    ],
}


def extract_null_fields(csv_path, fields_to_extract, output_path):
    """Извлечь указанные поля из CSV и сохранить в новый файл"""
    print("Processing", csv_path, "...")

    # Читаем только нужные колонки
    try:
        df = pd.read_csv(csv_path, usecols=lambda col: col in fields_to_extract)

        if df.empty or len(df.columns) == 0:
            print("  ⚠ No matching columns found")
            return

        # Сохраняем
        df.to_csv(output_path, index=False)
        print(
            "  ✓ Saved", len(df), "rows ×", len(df.columns), "columns to", output_path
        )
        print("    Columns:", ", ".join(df.columns.tolist()))

    except Exception as e:
        print(f"  ✗ Error: {e}")


def main():
    base_path = Path(
        r"E:\g-drive\05_AI\github\BioactivityDataAcquisition2\data\output\silver"
    )
    output_dir = Path(
        r"E:\g-drive\05_AI\github\BioactivityDataAcquisition2\data\output\silver\null_fields_extracted"
    )
    output_dir.mkdir(exist_ok=True, parents=True)

    # Обрабатываем каждый источник
    for source, fields in NULL_FIELDS.items():
        csv_path = base_path / source / "publication" / f"{source}_publication.csv"

        if not csv_path.exists():
            print(f"⚠ File not found: {csv_path}")
            continue

        output_path = output_dir / f"{source}_publication_null_fields.csv"
        extract_null_fields(csv_path, fields, output_path)

    print(f"\n✓ All files processed. Output directory: {output_dir}")


if __name__ == "__main__":
    main()
