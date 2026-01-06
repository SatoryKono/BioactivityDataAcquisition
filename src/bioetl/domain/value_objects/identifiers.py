"""Identifier Value Objects for BioETL domain.

Contains Value Objects for various scientific identifiers:
- ChemblId: ChEMBL database identifiers (CHEMBL123)
- UniProtId: UniProt accession numbers (P12345)
- DOI: Digital Object Identifiers (10.1234/abc)
- PubMedId: PubMed article identifiers (PMID)
- PubChemCid: PubChem Compound IDs
- InChIKey: InChI Key identifiers (BSYNRYMUTXBXSQ-UHFFFAOYSA-N)
- SMILES: SMILES notation strings
- PublicationYear: Publication year with validation

These Value Objects encapsulate validation and normalization rules.
"""

from __future__ import annotations

import re

from bioetl.domain.value_objects.base import ValueObject


class ChemblId(ValueObject[str]):
    """ChEMBL identifier for molecules, targets, assays, documents, etc.

    Format: CHEMBL followed by a positive integer.
    Examples: CHEMBL25, CHEMBL1234567, CHEMBL941

    Invariants:
        - Starts with "CHEMBL" (case-insensitive, normalized to uppercase)
        - Followed by a positive integer
        - No leading zeros in the numeric part
    """

    __slots__ = ()
    _value: str
    _PATTERN = re.compile(r"^CHEMBL(\d+)$", re.IGNORECASE)

    def _validate(self, value: str) -> str:
        """Validate and normalize ChEMBL ID.

        Args:
            value: Raw ChEMBL ID string.

        Returns:
            Normalized uppercase ChEMBL ID.

        Raises:
            ValueError: If format is invalid.
        """
        if not isinstance(value, str):
            raise ValueError(f"ChemblId must be str, got {type(value).__name__}")

        normalized = value.strip().upper()

        if not normalized:
            raise ValueError("ChemblId cannot be empty")

        match = self._PATTERN.match(normalized)
        if not match:
            raise ValueError(
                f"Invalid ChEMBL ID format: {value!r}. Expected: CHEMBL<number>"
            )

        numeric_part = int(match.group(1))
        if numeric_part <= 0:
            raise ValueError(f"ChEMBL ID number must be positive: {value!r}")

        # Normalize to remove leading zeros
        return f"CHEMBL{numeric_part}"

    @property
    def numeric_id(self) -> int:
        """Get the numeric part of the ChEMBL ID.

        Returns:
            Integer portion of the identifier (e.g., 25 for CHEMBL25).
        """
        return int(self._value[6:])

    @classmethod
    def from_raw(cls, raw: str | None) -> ChemblId | None:
        """Create ChemblId from raw string with normalization.

        Args:
            raw: Raw ChEMBL ID string or None.

        Returns:
            ChemblId if valid, None if input is None, empty, or invalid.
        """
        if not raw or not raw.strip():
            return None
        try:
            return cls(raw)
        except ValueError:
            return None


class UniProtId(ValueObject[str]):
    """UniProt accession number.

    UniProt accession numbers follow specific patterns:
    - Primary format: [OPQ][0-9][A-Z0-9]{3}[0-9] (e.g., P12345, Q9Y6K9)
    - Extended format: [A-NR-Z][0-9]([A-Z][A-Z0-9]{2}[0-9]){1,2} (e.g., A0A1B2C3D4)

    See: https://www.uniprot.org/help/accession_numbers

    Invariants:
        - Matches UniProt accession pattern
        - Normalized to uppercase
    """

    __slots__ = ()
    _value: str

    # Primary accession pattern (6 characters)
    _PRIMARY_PATTERN = re.compile(r"^[OPQ][0-9][A-Z0-9]{3}[0-9]$")

    # Secondary accession pattern for other letters (6 or 10 characters)
    _SECONDARY_PATTERN = re.compile(r"^[A-NR-Z][0-9]([A-Z][A-Z0-9]{2}[0-9]){1,2}$")

    def _validate_format(self, normalized: str) -> bool:
        """Check if normalized string matches UniProt format."""
        return bool(
            self._PRIMARY_PATTERN.match(normalized)
            or self._SECONDARY_PATTERN.match(normalized)
        )

    def _validate(self, value: str) -> str:
        """Validate and normalize UniProt accession.

        Args:
            value: Raw UniProt accession string.

        Returns:
            Normalized uppercase UniProt accession.

        Raises:
            ValueError: If format is invalid.
        """
        if not isinstance(value, str):
            raise ValueError(f"UniProtId must be str, got {type(value).__name__}")

        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("UniProtId cannot be empty")

        if len(normalized) not in (6, 10):
            raise ValueError(
                f"Invalid UniProt accession length: {value!r}. "
                f"Expected 6 or 10 characters."
            )

        if not self._validate_format(normalized):
            raise ValueError(f"Invalid UniProt accession format: {value!r}")
        return normalized

    @property
    def is_primary_format(self) -> bool:
        """Check if this is a primary (6-character) accession.

        Primary format accessions (e.g., P12345) are 6 characters.
        Extended format accessions (e.g., A0A1B2C3D4) are 10 characters.

        Returns:
            True if primary format (6 chars), False if extended (10 chars).
        """
        return len(self._value) == 6

    @classmethod
    def from_raw(cls, raw: str | None) -> UniProtId | None:
        """Create UniProtId from raw string with normalization.

        Args:
            raw: Raw UniProt accession string or None.

        Returns:
            UniProtId if valid, None if input is None, empty, or invalid.
        """
        if not raw or not raw.strip():
            return None
        try:
            return cls(raw)
        except ValueError:
            return None


class DOI(ValueObject[str]):
    """Digital Object Identifier.

    Format: 10.XXXX/suffix where XXXX is a registrant code (4+ digits).
    Examples: 10.1000/xyz123, 10.12345/abc.def

    Invariants:
        - Starts with "10."
        - Has a registrant code of at least 4 digits
        - Has a non-empty suffix after "/"
        - Normalized to lowercase
        - URL prefixes (https://doi.org/, http://doi.org/, doi:) are stripped
    """

    __slots__ = ()
    _value: str

    _PATTERN = re.compile(r"^10\.\d{4,}/\S+$")
    _URL_PREFIXES = (
        "https://doi.org/",
        "http://doi.org/",
        "doi:",
        "DOI:",
    )

    def _strip_url_prefix(self, value: str) -> str:
        """Strip URL prefix from DOI if present."""
        for prefix in self._URL_PREFIXES:
            if value.lower().startswith(prefix.lower()):
                return value[len(prefix) :]
        return value

    def _validate(self, value: str) -> str:
        """Validate and normalize DOI.

        Args:
            value: Raw DOI string, optionally with URL prefix.

        Returns:
            Normalized lowercase DOI (without URL prefix).

        Raises:
            ValueError: If format is invalid.
        """
        if not isinstance(value, str):
            raise ValueError(f"DOI must be str, got {type(value).__name__}")

        normalized = value.strip()
        if not normalized:
            raise ValueError("DOI cannot be empty")

        # Strip URL prefixes and normalize to lowercase
        normalized = self._strip_url_prefix(normalized).lower()

        if not self._PATTERN.match(normalized):
            raise ValueError(f"Invalid DOI format: {value!r}. Expected: 10.XXXX/suffix")

        return normalized

    @property
    def url(self) -> str:
        """Get the full DOI URL for web access.

        Returns:
            Complete HTTPS URL (e.g., 'https://doi.org/10.1038/nature12373').
        """
        return f"https://doi.org/{self._value}"

    @property
    def registrant_code(self) -> str:
        """Get the registrant code (organization identifier).

        The registrant code identifies the organization that registered
        the DOI. It appears after '10.' and before the '/'.

        Returns:
            Registrant code string (e.g., '1038' for Nature Publishing).
        """
        # Format: 10.XXXX/suffix
        return self._value.split("/")[0][3:]  # Skip "10."

    @classmethod
    def from_raw(cls, raw: str | None) -> DOI | None:
        """Create DOI from raw string with normalization.

        Handles common DOI formats including:
        - Plain DOI: 10.1038/nature12373
        - URL format: https://doi.org/10.1038/nature12373
        - Prefix format: doi:10.1038/nature12373

        Args:
            raw: Raw DOI string or None.

        Returns:
            DOI if valid, None if input is None, empty, or invalid.
        """
        if not raw or not raw.strip():
            return None
        try:
            return cls(raw)
        except ValueError:
            return None


class PubMedId(ValueObject[str]):
    """PubMed identifier (PMID).

    A numeric string uniquely identifying an article in PubMed.
    Stored as string to match PubMed API behavior and enable consistent
    cross-provider JOIN operations.

    Examples: "12345", "28891234"

    Invariants:
        - Must be a string containing only digits
        - Must represent a positive integer (no leading zeros except for "0")
        - Cannot exceed reasonable bounds (< 10^10)
    """

    __slots__ = ()
    _value: str
    _PATTERN = re.compile(r"^\d+$")
    _MAX_PMID = 10_000_000_000  # Reasonable upper bound

    def _coerce_to_str(self, value: str | int) -> str:
        """Coerce value to string, raising ValueError on failure."""
        if isinstance(value, bool):
            raise ValueError(f"PubMedId must be str or int, got {type(value).__name__}")
        if isinstance(value, int):
            return str(value)
        if isinstance(value, str):
            return value.strip()
        raise ValueError(f"PubMedId must be str or int, got {type(value).__name__}")

    def _validate(self, value: str | int) -> str:
        """Validate and normalize PubMed ID to string."""
        str_value = self._coerce_to_str(value)

        if not str_value:
            raise ValueError("PubMed ID cannot be empty")
        if not self._PATTERN.match(str_value):
            raise ValueError(
                f"Invalid PubMed ID format: {value!r}. Must contain only digits."
            )

        int_value = int(str_value)
        if int_value <= 0:
            raise ValueError(f"PubMed ID must be positive: {str_value}")
        if int_value >= self._MAX_PMID:
            raise ValueError(f"PubMed ID too large: {str_value}")

        return str(int_value)

    @property
    def as_int(self) -> int:
        """Get the PMID as integer for numeric operations."""
        return int(self._value)

    @classmethod
    def from_raw(cls, raw: str | int | None) -> PubMedId | None:
        """Create PubMedId from raw value with normalization.

        Args:
            raw: Raw PMID string, integer, or None.

        Returns:
            PubMedId if valid, None if input is None, empty, or invalid.
        """
        if raw is None:
            return None
        if isinstance(raw, str) and not raw.strip():
            return None
        try:
            # Convert to string for type safety (coercion handled in _validate)
            str_value = str(raw) if isinstance(raw, int) else raw
            return cls(str_value)
        except ValueError:
            return None


class PubChemCid(ValueObject[int]):
    """PubChem Compound Identifier (CID).

    A positive integer uniquely identifying a compound in PubChem.
    Examples: 2244 (aspirin), 5988 (caffeine)

    Invariants:
        - Must be a positive integer
        - Cannot exceed reasonable bounds (< 10^11)
    """

    __slots__ = ()
    _value: int

    _MAX_CID = 100_000_000_000  # Reasonable upper bound

    def _coerce_to_int(self, value: int | str) -> int:
        """Coerce value to int, raising ValueError on failure."""
        if isinstance(value, bool):
            raise ValueError(f"PubChemCid must be int, got {type(value).__name__}")
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            try:
                return int(value.strip())
            except ValueError:
                raise ValueError(f"Invalid PubChem CID: {value!r}") from None
        raise ValueError(f"PubChemCid must be int, got {type(value).__name__}")

    def _validate(self, value: int) -> int:
        """Validate PubChem CID.

        Args:
            value: Raw CID value.

        Returns:
            Validated CID.

        Raises:
            ValueError: If CID is invalid.
        """
        int_value = self._coerce_to_int(value)
        if int_value <= 0:
            raise ValueError(f"PubChem CID must be positive: {int_value}")
        if int_value >= self._MAX_CID:
            raise ValueError(f"PubChem CID too large: {int_value}")
        return int_value

    @classmethod
    def from_raw(cls, raw: int | str | None) -> PubChemCid | None:
        """Create PubChemCid from raw value with normalization.

        Args:
            raw: Raw CID integer, string, or None.

        Returns:
            PubChemCid if valid, None if input is None, empty, or invalid.
        """
        if raw is None:
            return None
        if isinstance(raw, str) and not raw.strip():
            return None
        try:
            # Convert to int for type safety (coercion handled in _validate)
            int_value = int(raw) if isinstance(raw, str) else raw
            return cls(int_value)
        except ValueError:
            return None


class InChIKey(ValueObject[str]):
    """InChI Key value object.

    InChI Keys are 27-character strings in the format:
    XXXXXXXXXXXXXX-YYYYYYYYYY-Z

    Where:
    - First 14 characters: connectivity layer (molecular skeleton)
    - Middle 10 characters: stereochemistry and isotopes layer
    - Last character: protonation state (usually N for neutral)

    Examples: BSYNRYMUTXBXSQ-UHFFFAOYSA-N (aspirin)

    Invariants:
        - Must be exactly 27 characters
        - Format: 14 uppercase letters, hyphen, 10 uppercase letters, hyphen, 1 uppercase letter
        - Normalized to uppercase
    """

    __slots__ = ()
    _value: str

    _PATTERN = re.compile(r"^[A-Z]{14}-[A-Z]{10}-[A-Z]$")

    def _validate(self, value: str) -> str:
        """Validate and normalize InChI Key.

        Args:
            value: Raw InChI Key string.

        Returns:
            Normalized uppercase InChI Key.

        Raises:
            ValueError: If format is invalid.
        """
        if not isinstance(value, str):
            raise ValueError(f"InChIKey must be str, got {type(value).__name__}")

        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("InChIKey cannot be empty")

        if not self._PATTERN.match(normalized):
            raise ValueError(
                f"Invalid InChI Key format: {value!r}. "
                "Expected: XXXXXXXXXXXXXX-YYYYYYYYYY-Z (27 chars)"
            )

        return normalized

    @property
    def connectivity_layer(self) -> str:
        """Get the connectivity layer (first 14 characters).

        The connectivity layer encodes the molecular skeleton,
        describing atom connections without stereochemistry.

        Returns:
            First 14 characters of the InChI Key.
        """
        return self._value[:14]

    @property
    def stereochemistry_layer(self) -> str:
        """Get the stereochemistry and isotopes layer (middle 10 characters).

        This layer encodes stereochemistry information and isotope labels.
        'UHFFFAOYSA' indicates no stereochemistry or isotopes.

        Returns:
            Middle 10 characters (positions 15-24) of the InChI Key.
        """
        return self._value[15:25]

    @property
    def protonation_layer(self) -> str:
        """Get the protonation layer (last character).

        Indicates the protonation state:
        - N: neutral
        - Other letters indicate charged states

        Returns:
            Last character of the InChI Key.
        """
        return self._value[-1]

    @classmethod
    def from_raw(cls, raw: str | None) -> InChIKey | None:
        """Create InChIKey from raw string with normalization.

        Args:
            raw: Raw InChI Key string or None.

        Returns:
            InChIKey if valid, None if input is None, empty, or invalid.
        """
        if not raw or not raw.strip():
            return None
        try:
            return cls(raw)
        except ValueError:
            return None


class SMILES(ValueObject[str]):
    """SMILES notation value object.

    Simplified Molecular-Input Line-Entry System (SMILES) is a string
    notation for describing molecular structure.

    Examples:
    - CC(=O)OC1=CC=CC=C1C(=O)O (aspirin)
    - CN1C=NC2=C1C(=O)N(C(=O)N2C)C (caffeine)

    Invariants:
        - Must be a non-empty string
        - Normalized by stripping whitespace
        - Optionally can be marked as canonical
    """

    __slots__ = ("_is_canonical",)
    _value: str
    _is_canonical: bool

    def __init__(self, value: str, *, is_canonical: bool = False) -> None:
        """Create SMILES with validated value.

        Args:
            value: Raw SMILES string.
            is_canonical: Whether this is a canonical SMILES.

        Raises:
            ValueError: If validation fails.
        """
        validated = self._validate(value)
        object.__setattr__(self, "_value", validated)
        object.__setattr__(self, "_is_canonical", is_canonical)

    def _validate(self, value: str) -> str:
        """Validate and normalize SMILES.

        Args:
            value: Raw SMILES string.

        Returns:
            Normalized SMILES string.

        Raises:
            ValueError: If SMILES is empty.
        """
        if not isinstance(value, str):
            raise ValueError(f"SMILES must be str, got {type(value).__name__}")

        normalized = value.strip()
        if not normalized:
            raise ValueError("SMILES cannot be empty")

        return normalized

    @property
    def is_canonical(self) -> bool:
        """Check if this is a canonical SMILES representation.

        Canonical SMILES are unique representations where the same
        molecule always produces the same SMILES string.

        Returns:
            True if this is marked as canonical SMILES.
        """
        return self._is_canonical

    @classmethod
    def canonical(cls, smiles: str) -> SMILES:
        """Create a canonical SMILES.

        Args:
            smiles: Canonical SMILES string.

        Returns:
            SMILES marked as canonical.
        """
        return cls(smiles, is_canonical=True)

    @classmethod
    def from_raw(cls, raw: str | None, *, is_canonical: bool = False) -> SMILES | None:
        """Create SMILES from raw string with normalization.

        Args:
            raw: Raw SMILES string or None.
            is_canonical: Whether this is a canonical SMILES.

        Returns:
            SMILES if valid, None if input is None, empty, or invalid.
        """
        if not raw or not raw.strip():
            return None
        try:
            return cls(raw, is_canonical=is_canonical)
        except ValueError:
            return None

    def __eq__(self, other: object) -> bool:
        """Compare by value and canonical flag."""
        if not isinstance(other, SMILES):
            return NotImplemented
        return self._value == other._value and self._is_canonical == other._is_canonical

    def __hash__(self) -> int:
        """Hash based on class, value, and canonical flag."""
        return hash((self.__class__.__name__, self._value, self._is_canonical))

    def __repr__(self) -> str:
        """String representation showing class and value."""
        if self._is_canonical:
            return f"SMILES({self._value!r}, is_canonical=True)"
        return f"SMILES({self._value!r})"


class PublicationYear(ValueObject[int]):
    """Publication year value object with validation.

    Validates that the year falls within a reasonable range for
    scientific publications.

    Examples: 1953 (Watson & Crick), 2020 (COVID papers)

    Invariants:
        - Must be between MIN_YEAR (1800) and MAX_YEAR (2100)
        - Must be a positive integer
    """

    __slots__ = ()
    _value: int

    _MIN_YEAR = 1800  # Reasonable minimum for scientific publications
    _MAX_YEAR = 2100  # Reasonable maximum allowing for future publications

    def _coerce_to_int(self, value: int | str) -> int:
        """Coerce value to int, raising ValueError on failure."""
        if isinstance(value, bool):
            raise ValueError(
                f"PublicationYear must be int, got {type(value).__name__}"
            )
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            try:
                return int(value.strip())
            except ValueError:
                raise ValueError(f"Invalid publication year: {value!r}") from None
        raise ValueError(
            f"PublicationYear must be int, got {type(value).__name__}"
        )

    def _validate(self, value: int) -> int:
        """Validate publication year.

        Args:
            value: Raw year value.

        Returns:
            Validated year.

        Raises:
            ValueError: If year is outside valid range.
        """
        int_value = self._coerce_to_int(value)
        if not self._MIN_YEAR <= int_value <= self._MAX_YEAR:
            raise ValueError(
                f"Year {int_value} outside valid range "
                f"[{self._MIN_YEAR}, {self._MAX_YEAR}]"
            )
        return int_value

    @property
    def decade(self) -> int:
        """Get the decade of the publication year.

        Returns:
            Decade as integer (e.g., 1950 for year 1953).
        """
        return (self._value // 10) * 10

    @property
    def century(self) -> int:
        """Get the century of the publication year.

        Returns:
            Century as integer (e.g., 20 for year 1953).
        """
        return (self._value // 100) + 1

    @classmethod
    def from_raw(cls, raw: int | str | None) -> PublicationYear | None:
        """Create PublicationYear from raw value with normalization.

        Args:
            raw: Raw year integer, string, or None.

        Returns:
            PublicationYear if valid, None if input is None, empty, or invalid.
        """
        if raw is None:
            return None
        if isinstance(raw, str) and not raw.strip():
            return None
        try:
            # Convert to int for type safety (coercion handled in _validate)
            int_value = int(raw) if isinstance(raw, str) else raw
            return cls(int_value)
        except ValueError:
            return None
