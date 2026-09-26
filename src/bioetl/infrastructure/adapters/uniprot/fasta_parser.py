"""FASTA format parsing utilities.

Provides FASTA text parsing for UniProt sequence data.
Extracted from uniprot/client.py for better separation of concerns.
"""

from __future__ import annotations

__all__ = ["FastaParser"]


from bioetl.domain.types import JsonDict


class FastaParser:
    """Parses FASTA format text into sequence records."""

    @staticmethod
    def parse(fasta_text: str) -> list[JsonDict]:  # Any: untyped API JSON record
        """Parse FASTA format text into sequence records.

        Args:
            fasta_text: Raw FASTA format text with headers and sequences

        Returns:
            List of dictionaries with 'header' and 'sequence' keys

        Example:
            >>> text = ">sp|P12345|GENE_HUMAN Description\\nMKTAYIAKQR"
            >>> FastaParser.parse(text)
            [{'header': 'sp|P12345|GENE_HUMAN Description', 'sequence': 'MKTAYIAKQR'}]
        """
        records: list[JsonDict] = []  # Any: untyped API JSON record
        current_header: str | None = None
        current_sequence: list[str] = []

        for line in fasta_text.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith(">"):
                # Save previous record if exists
                if current_header is not None:
                    records.append(
                        {
                            "header": current_header,
                            "sequence": "".join(current_sequence),
                        }
                    )
                # Start new record
                current_header = line[1:]  # Remove '>' prefix
                current_sequence = []
            else:
                current_sequence.append(line)

        # Don't forget the last record
        if current_header is not None:
            records.append(
                {
                    "header": current_header,
                    "sequence": "".join(current_sequence),
                }
            )

        return records

    @staticmethod
    def parse_header(header: str) -> dict[str, str | None]:
        """Parse FASTA header into components.

        Parses UniProt-style FASTA headers in the format:
        sp|ACCESSION|ENTRY_NAME Description

        Args:
            header: FASTA header string (without '>' prefix)

        Returns:
            Dictionary with 'database', 'accession', 'entry_name', and 'description'
        """
        parts = header.split("|", 2)
        if len(parts) >= 3:
            # UniProt format: db|accession|entry_name description
            entry_and_desc = parts[2].split(" ", 1)
            return {
                "database": parts[0],
                "accession": parts[1],
                "entry_name": entry_and_desc[0],
                "description": entry_and_desc[1] if len(entry_and_desc) > 1 else None,
            }
        # Simple format: just description
        return {
            "database": None,
            "accession": None,
            "entry_name": None,
            "description": header,
        }
