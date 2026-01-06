"""Architecture tests for PII hashing compliance.

Tests RULES.md §5.4: Silver layer MUST hash PII fields using
sha256(lowercase(value) + SALT).

These tests verify:
1. PiiHasherPort is properly defined in domain/ports
2. Transformers with PII fields accept PiiHasherPort
3. BaseTransformer provides hash_pii_* methods
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from bioetl.domain import ports


class TestPiiHasherPortContract:
    """Tests for PiiHasherPort contract compliance."""

    def test_pii_hasher_port_exists(self) -> None:
        """PiiHasherPort MUST be defined in domain/ports."""
        assert hasattr(ports, "PiiHasherPort"), (
            "PiiHasherPort MUST be defined in domain/ports "
            "per RULES.md §5.4 Sensitive Data Policy"
        )

    def test_pii_hasher_port_is_runtime_checkable(self) -> None:
        """PiiHasherPort MUST be @runtime_checkable for isinstance checks."""
        port = ports.PiiHasherPort
        # Check if it has the runtime_checkable marker
        assert getattr(port, "__protocol_attrs__", None) is not None or hasattr(
            port, "_is_runtime_protocol"
        ), "PiiHasherPort MUST be @runtime_checkable"

    def test_pii_hasher_port_has_required_methods(self) -> None:
        """PiiHasherPort MUST define hash_value, hash_list, get_salt_id."""
        port = ports.PiiHasherPort
        required_methods = ["hash_value", "hash_list", "get_salt_id"]

        for method in required_methods:
            assert hasattr(
                port, method
            ), f"PiiHasherPort MUST define {method}() method per RULES.md §5.4"

    def test_pii_hasher_port_exported_in_all(self) -> None:
        """PiiHasherPort MUST be in domain.ports.__all__."""
        assert (
            "PiiHasherPort" in ports.__all__
        ), "PiiHasherPort MUST be exported in domain.ports.__all__"

    def test_noop_pii_hasher_exists(self) -> None:
        """NoOpPiiHasher MUST exist for testing and backward compatibility."""
        assert hasattr(
            ports, "NoOpPiiHasher"
        ), "NoOpPiiHasher MUST be defined for testing and backward compatibility"

    def test_noop_pii_hasher_implements_port(self) -> None:
        """NoOpPiiHasher MUST implement PiiHasherPort."""
        hasher = ports.NoOpPiiHasher()
        assert isinstance(
            hasher, ports.PiiHasherPort
        ), "NoOpPiiHasher MUST implement PiiHasherPort"


class TestBaseTransformerPiiSupport:
    """Tests for PII support in BaseTransformer."""

    def test_base_transformer_accepts_pii_hasher(self) -> None:
        """BaseTransformer.__init__ MUST accept pii_hasher parameter."""
        from bioetl.application.core.base_transformer import BaseTransformer

        sig = inspect.signature(BaseTransformer.__init__)
        param_names = list(sig.parameters.keys())

        assert "pii_hasher" in param_names, (
            "BaseTransformer.__init__ MUST accept pii_hasher parameter "
            "for RULES.md §5.4 compliance"
        )

    def test_base_transformer_has_hash_methods(self) -> None:
        """BaseTransformer MUST provide hash_pii_value and hash_pii_list methods."""
        from bioetl.application.core.base_transformer import BaseTransformer

        assert hasattr(
            BaseTransformer, "hash_pii_value"
        ), "BaseTransformer MUST provide hash_pii_value() method"
        assert hasattr(
            BaseTransformer, "hash_pii_list"
        ), "BaseTransformer MUST provide hash_pii_list() method"


class TestTransformersWithPii:
    """Tests that transformers with PII fields use PiiHasherPort."""

    # Transformers known to handle PII (author names)
    PII_TRANSFORMERS = [
        "bioetl.application.pipelines.crossref.transformer.CrossRefTransformer",
        "bioetl.application.pipelines.pubmed.transformer.PubMedPublicationTransformer",
        "bioetl.application.pipelines.chembl.base_chembl_transformer.BaseChemblTransformer",
    ]

    @pytest.mark.parametrize("transformer_path", PII_TRANSFORMERS)
    def test_pii_transformers_accept_pii_hasher(self, transformer_path: str) -> None:
        """Transformers with PII fields MUST accept pii_hasher parameter."""
        module_path, class_name = transformer_path.rsplit(".", 1)

        # Import the module and class
        import importlib

        module = importlib.import_module(module_path)
        transformer_class = getattr(module, class_name)

        sig = inspect.signature(transformer_class.__init__)
        param_names = list(sig.parameters.keys())

        assert "pii_hasher" in param_names, (
            f"{class_name}.__init__ MUST accept pii_hasher parameter "
            f"for RULES.md §5.4 compliance. "
            f"Authors and other PII fields MUST be hashed in Silver layer."
        )


class TestPiiHasherImplementation:
    """Tests for Sha256PiiHasher implementation."""

    def test_sha256_hasher_exists_in_infrastructure(self) -> None:
        """Sha256PiiHasher MUST exist in infrastructure/security."""
        from bioetl.infrastructure.security import Sha256PiiHasher

        assert Sha256PiiHasher is not None

    def test_sha256_hasher_implements_port(self) -> None:
        """Sha256PiiHasher MUST implement PiiHasherPort."""
        from bioetl.infrastructure.security import Sha256PiiHasher
        from bioetl.infrastructure.security.pii_hasher import SaltConfig

        config = SaltConfig(current_salt="x" * 64)
        hasher = Sha256PiiHasher(salt_config=config)

        assert isinstance(
            hasher, ports.PiiHasherPort
        ), "Sha256PiiHasher MUST implement PiiHasherPort"


class TestPiiFieldsInTransformers:
    """Tests that PII fields are actually hashed in transformer code."""

    def test_crossref_transformer_hashes_authors(self) -> None:
        """CrossRefTransformer MUST hash authors field."""
        transformer_path = Path(
            "src/bioetl/application/pipelines/crossref/transformer.py"
        )
        content = transformer_path.read_text()

        # Check that hash_pii_list is called for authors
        assert (
            "hash_pii_list" in content
        ), "CrossRefTransformer MUST use hash_pii_list() for authors field"

    def test_pubmed_transformer_hashes_authors(self) -> None:
        """PubMedPublicationTransformer MUST hash authors field."""
        transformer_path = Path(
            "src/bioetl/application/pipelines/pubmed/transformer.py"
        )
        content = transformer_path.read_text()

        assert (
            "hash_pii_list" in content
        ), "PubMedPublicationTransformer MUST use hash_pii_list() for authors field"

    def test_chembl_document_transformer_hashes_authors(self) -> None:
        """DocumentTransformer MUST hash authors field."""
        transformer_path = Path(
            "src/bioetl/application/pipelines/chembl/document_transformer.py"
        )
        content = transformer_path.read_text()

        # ChEMBL uses single string authors, so hash_pii_value
        assert (
            "hash_pii_value" in content
        ), "ChEMBL DocumentTransformer MUST use hash_pii_value() for authors field"
