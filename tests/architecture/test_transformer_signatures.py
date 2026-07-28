"""Architecture tests for transformer interface alignment.

Ensures all transformers follow the standard signature contract
defined in BaseTransformer.

These tests verify:
1. All transformers inherit from BaseTransformer
2. All transformers have provider parameter with default
3. All transformers have observability parameters (tracer, metrics)
4. All concrete transformers implement _transform_impl
5. Transformers don't override the transform() template method
6. All transformers can be instantiated via the explicit DI seam
7. All transformers have entity_type set after initialization

See RULES.md §2 for architecture requirements.
"""

from __future__ import annotations

from functools import cache
import inspect

import pytest

from bioetl.application.core.base_transformer import BaseTransformer
from tests.helpers.transformer_dependencies import (
    build_test_transformer_dependencies,
)


@cache
def get_all_transformers() -> list[type[BaseTransformer]]:
    """Dynamically discover all transformer classes.

    Returns:
        List of all concrete transformer classes in the codebase.

    """
    # ChEMBL transformers
    from bioetl.application.pipelines.chembl import (
        ActivityTransformer,
        AssayParametersTransformer,
        AssayTransformer,
        CellLineTransformer,
        CompoundRecordTransformer,
        MoleculeTransformer,
        ProteinClassTransformer,
        PublicationSimilarityTransformer,
        PublicationTermTransformer,
        PublicationTransformer,
        TargetComponentTransformer,
        TargetTransformer,
    )

    # Other provider transformers
    from bioetl.application.pipelines.crossref.transformer import (
        CrossRefPublicationTransformer,
    )
    from bioetl.application.pipelines.openalex.transformer import (
        OpenAlexPublicationTransformer,
    )
    from bioetl.application.pipelines.pubchem.transformer import (
        PubChemCompoundTransformer,
    )
    from bioetl.application.pipelines.pubmed.transformer import (
        PubMedPublicationTransformer,
    )
    from bioetl.application.pipelines.semanticscholar.transformer import (
        SemanticScholarPublicationTransformer,
    )
    from bioetl.application.pipelines.uniprot.transformer import (
        UniProtProteinTransformer,
    )

    return [
        # ChEMBL transformers
        ActivityTransformer,
        AssayParametersTransformer,
        AssayTransformer,
        CellLineTransformer,
        CompoundRecordTransformer,
        MoleculeTransformer,
        ProteinClassTransformer,
        PublicationSimilarityTransformer,
        PublicationTermTransformer,
        PublicationTransformer,
        TargetComponentTransformer,
        TargetTransformer,
        # Other providers
        CrossRefPublicationTransformer,
        OpenAlexPublicationTransformer,
        PubChemCompoundTransformer,
        PubMedPublicationTransformer,
        SemanticScholarPublicationTransformer,
        UniProtProteinTransformer,
    ]


def _build_dependencies():
    """Create explicit default collaborators for architecture checks."""
    return build_test_transformer_dependencies()


# Standard parameters that all transformers SHOULD have
STANDARD_OPTIONAL_PARAMS = {
    "tracer",
    "metrics",
    "gold_filters",
    "identity_service",
    "pii_hasher",
}

# Collaborators that may be packed into **legacy_collaborators (S107 / RF-017
# constructor budget) instead of remaining as named parameters.
LEGACY_PACKED_OPTIONAL_PARAMS = frozenset(
    {
        "tracer",
        "metrics",
        "identity_service",
        "pii_hasher",
    }
)


def _init_param_names(transformer_class: type[BaseTransformer]) -> set[str]:
    """Return __init__ parameter names without self."""
    sig = inspect.signature(transformer_class.__init__)
    return set(sig.parameters.keys()) - {"self"}


def _accepts_optional_collaborator(
    transformer_class: type[BaseTransformer],
    name: str,
) -> bool:
    """True when the collaborator is a named param or accepted via **legacy packing."""
    params = inspect.signature(transformer_class.__init__).parameters
    if name in params:
        return True
    if name not in LEGACY_PACKED_OPTIONAL_PARAMS:
        return False
    return any(
        parameter.kind is inspect.Parameter.VAR_KEYWORD for parameter in params.values()
    )


class TestTransformerInheritance:
    """Test that all transformers properly inherit from BaseTransformer."""

    @pytest.mark.parametrize("transformer_class", get_all_transformers())
    def test_inherits_from_base_transformer(
        self, transformer_class: type[BaseTransformer]
    ) -> None:
        """All transformers MUST inherit from BaseTransformer.

        This ensures consistent behavior across all transformers including:
        - Template Method pattern for error handling
        - Content hash computation
        - Tracing and metrics observability
        """
        assert issubclass(transformer_class, BaseTransformer), (
            f"{transformer_class.__name__} must inherit from BaseTransformer"
        )


class TestTransformerSignatures:
    """Test transformer constructor signatures follow the contract."""

    @pytest.mark.parametrize("transformer_class", get_all_transformers())
    def test_has_provider_parameter(
        self, transformer_class: type[BaseTransformer]
    ) -> None:
        """All transformers MUST accept provider parameter.

        Provider identifies the data source (chembl, pubchem, etc.)
        and is used for metrics labeling and entity ID generation.
        """
        sig = inspect.signature(transformer_class.__init__)
        params = set(sig.parameters.keys()) - {"self"}
        assert "provider" in params, (
            f"{transformer_class.__name__} must have 'provider' parameter"
        )

    @pytest.mark.parametrize("transformer_class", get_all_transformers())
    def test_provider_has_default(
        self, transformer_class: type[BaseTransformer]
    ) -> None:
        """Provider parameter MUST have a provider-specific default value.

        This allows transformers to be instantiated without explicit provider,
        using sensible defaults (e.g., 'chembl' for ChEMBL transformers).
        """
        sig = inspect.signature(transformer_class.__init__)
        provider_param = sig.parameters.get("provider")
        assert provider_param is not None
        assert provider_param.default != inspect.Parameter.empty, (
            f"{transformer_class.__name__}.provider must have a default value"
        )

    @pytest.mark.parametrize("transformer_class", get_all_transformers())
    def test_has_tracer_parameter(
        self, transformer_class: type[BaseTransformer]
    ) -> None:
        """All transformers SHOULD accept tracer parameter for observability.

        Tracer enables distributed tracing via OpenTelemetry.
        Default should be None (uses NoOpTracing internally).
        May be named or accepted via ``**legacy_collaborators`` (S107 budget).
        """
        assert _accepts_optional_collaborator(transformer_class, "tracer"), (
            f"{transformer_class.__name__} should accept 'tracer' "
            "(named or **legacy_collaborators) for O1 observability"
        )

    @pytest.mark.parametrize("transformer_class", get_all_transformers())
    def test_has_metrics_parameter(
        self, transformer_class: type[BaseTransformer]
    ) -> None:
        """All transformers SHOULD accept metrics parameter for observability.

        Metrics enables duration/error tracking via Prometheus.
        Default should be None (uses NoOpMetrics internally).
        May be named or accepted via ``**legacy_collaborators`` (S107 budget).
        """
        assert _accepts_optional_collaborator(transformer_class, "metrics"), (
            f"{transformer_class.__name__} should accept 'metrics' "
            "(named or **legacy_collaborators) for O1 observability"
        )

    @pytest.mark.parametrize("transformer_class", get_all_transformers())
    def test_has_gold_filters_parameter(
        self, transformer_class: type[BaseTransformer]
    ) -> None:
        """All transformers SHOULD accept gold_filters parameter.

        Gold filters enable configurable filtering of Silver → Gold records.
        """
        params = _init_param_names(transformer_class)
        assert "gold_filters" in params, (
            f"{transformer_class.__name__} should have 'gold_filters' parameter"
        )

    @pytest.mark.parametrize("transformer_class", get_all_transformers())
    def test_has_identity_service_parameter(
        self, transformer_class: type[BaseTransformer]
    ) -> None:
        """All transformers SHOULD accept identity_service parameter.

        EntityIdentityGenerator provides entity ID and content hash computation.
        May be named or accepted via ``**legacy_collaborators`` (S107 budget).
        """
        assert _accepts_optional_collaborator(transformer_class, "identity_service"), (
            f"{transformer_class.__name__} should accept 'identity_service' "
            "(named or **legacy_collaborators)"
        )

    @pytest.mark.parametrize("transformer_class", get_all_transformers())
    def test_has_pii_hasher_parameter(
        self, transformer_class: type[BaseTransformer]
    ) -> None:
        """All transformers SHOULD accept pii_hasher parameter.

        PiiHasher enables optional hashing of PII fields (e.g., author names).
        Default should be None (uses NoOpPiiHasher internally).
        See RULES.md §5.4 for PII hashing requirements.
        May be named or accepted via ``**legacy_collaborators`` (S107 budget).
        """
        assert _accepts_optional_collaborator(transformer_class, "pii_hasher"), (
            f"{transformer_class.__name__} should accept 'pii_hasher' "
            "(named or **legacy_collaborators; RULES.md §5.4)"
        )


class TestTransformerImplementation:
    """Test transformer implementation requirements."""

    @pytest.mark.parametrize("transformer_class", get_all_transformers())
    def test_implements_transform_impl(
        self, transformer_class: type[BaseTransformer]
    ) -> None:
        """All concrete transformers MUST implement _transform_impl.

        The _transform_impl method contains entity-specific transformation logic.
        It's called by the template method transform() which handles error handling.
        """
        # Skip if abstract (BaseTransformer, BaseChemblTransformer)
        if inspect.isabstract(transformer_class):
            pytest.skip(f"{transformer_class.__name__} is abstract")

        # Check method exists and is not abstract
        method = getattr(transformer_class, "_transform_impl", None)
        assert method is not None, (
            f"{transformer_class.__name__} must implement _transform_impl"
        )

        # Verify it's not the abstract method from BaseTransformer
        assert not getattr(method, "__isabstractmethod__", False), (
            f"{transformer_class.__name__}._transform_impl must not be abstract"
        )

    @pytest.mark.parametrize("transformer_class", get_all_transformers())
    def test_does_not_override_transform(
        self, transformer_class: type[BaseTransformer]
    ) -> None:
        """Transformers SHOULD NOT override transform() template method.

        The transform() method in BaseTransformer implements the Template Method
        pattern with unified error handling, tracing, and metrics. Overriding it
        would bypass these standard behaviors.

        If custom behavior is needed, implement it in _transform_impl() instead.
        """
        # Get the method from the class (not inherited)
        own_methods = transformer_class.__dict__
        assert "transform" not in own_methods, (
            f"{transformer_class.__name__} should not override transform() "
            "template method - implement _transform_impl() instead"
        )


class TestTransformerInstantiation:
    """Test transformer instantiation with explicit dependencies."""

    @pytest.mark.parametrize("transformer_class", get_all_transformers())
    def test_instantiation_with_explicit_dependencies(
        self, transformer_class: type[BaseTransformer]
    ) -> None:
        """All transformers MUST be instantiable via explicit DI."""
        try:
            instance = transformer_class(dependencies=_build_dependencies())
            assert instance is not None
        except TypeError as e:
            pytest.fail(
                f"{transformer_class.__name__} cannot be instantiated "
                f"with explicit dependencies: {e}"
            )

    @pytest.mark.parametrize("transformer_class", get_all_transformers())
    def test_entity_type_is_set(self, transformer_class: type[BaseTransformer]) -> None:
        """All transformers MUST have entity_type set after initialization.

        Entity type is used for metrics labeling and tracing attributes.
        It should be a meaningful value, not "unknown".
        """
        instance = transformer_class(dependencies=_build_dependencies())
        assert hasattr(instance, "entity_type"), (
            f"{transformer_class.__name__} must have entity_type attribute"
        )
        assert instance.entity_type is not None, (
            f"{transformer_class.__name__}.entity_type must not be None"
        )
        assert instance.entity_type != "unknown", (
            f"{transformer_class.__name__}.entity_type should not be 'unknown' - "
            "provide explicit entity_type in __init__ or derive from entity_class"
        )

    @pytest.mark.parametrize("transformer_class", get_all_transformers())
    def test_provider_is_set(self, transformer_class: type[BaseTransformer]) -> None:
        """All transformers MUST have provider set after initialization.

        Provider identifies the data source and is used for entity IDs.
        """
        instance = transformer_class(dependencies=_build_dependencies())
        assert hasattr(instance, "provider"), (
            f"{transformer_class.__name__} must have provider attribute"
        )
        assert instance.provider is not None, (
            f"{transformer_class.__name__}.provider must not be None"
        )
        assert instance.provider != "", (
            f"{transformer_class.__name__}.provider must not be empty string"
        )


class TestTransformerObservability:
    """Test transformer observability integration."""

    @pytest.mark.parametrize("transformer_class", get_all_transformers())
    def test_tracer_has_none_default(
        self, transformer_class: type[BaseTransformer]
    ) -> None:
        """Tracer parameter SHOULD default to None.

        None marks the collaborator as composition-owned; the explicit
        runtime default is assembled outside BaseTransformer.
        """
        sig = inspect.signature(transformer_class.__init__)
        tracer_param = sig.parameters.get("tracer")
        if tracer_param is not None:
            assert tracer_param.default is None, (
                f"{transformer_class.__name__}.tracer should default to None"
            )

    @pytest.mark.parametrize("transformer_class", get_all_transformers())
    def test_metrics_has_none_default(
        self, transformer_class: type[BaseTransformer]
    ) -> None:
        """Metrics parameter SHOULD default to None.

        None marks the collaborator as composition-owned; the explicit
        runtime default is assembled outside BaseTransformer.
        """
        sig = inspect.signature(transformer_class.__init__)
        metrics_param = sig.parameters.get("metrics")
        if metrics_param is not None:
            assert metrics_param.default is None, (
                f"{transformer_class.__name__}.metrics should default to None"
            )

    @pytest.mark.parametrize("transformer_class", get_all_transformers())
    def test_has_internal_tracer_attribute(
        self, transformer_class: type[BaseTransformer]
    ) -> None:
        """All transformers MUST have _tracer attribute after init.

        This is set by BaseTransformer and used for distributed tracing.
        """
        instance = transformer_class(dependencies=_build_dependencies())
        assert hasattr(instance, "_tracer"), (
            f"{transformer_class.__name__} must have _tracer attribute"
        )

    @pytest.mark.parametrize("transformer_class", get_all_transformers())
    def test_has_internal_metrics_attribute(
        self, transformer_class: type[BaseTransformer]
    ) -> None:
        """All transformers MUST have _metrics attribute after init.

        This is set by BaseTransformer and used for duration/error tracking.
        """
        instance = transformer_class(dependencies=_build_dependencies())
        assert hasattr(instance, "_metrics"), (
            f"{transformer_class.__name__} must have _metrics attribute"
        )


class TestTransformerGoldFiltering:
    """Test transformer Gold layer filtering capabilities."""

    @pytest.mark.parametrize("transformer_class", get_all_transformers())
    def test_has_should_write_gold_method(
        self, transformer_class: type[BaseTransformer]
    ) -> None:
        """All transformers MUST have should_write_gold method.

        This method determines if a Silver record should be written to Gold.
        Inherited from BaseTransformer.
        """
        instance = transformer_class(dependencies=_build_dependencies())
        assert hasattr(instance, "should_write_gold"), (
            f"{transformer_class.__name__} must have should_write_gold method"
        )
        assert callable(instance.should_write_gold), (
            f"{transformer_class.__name__}.should_write_gold must be callable"
        )

    @pytest.mark.parametrize("transformer_class", get_all_transformers())
    def test_has_transform_for_gold_method(
        self, transformer_class: type[BaseTransformer]
    ) -> None:
        """All transformers MUST have transform_for_gold method.

        This method transforms Silver records for Gold layer.
        Inherited from BaseTransformer.
        """
        instance = transformer_class(dependencies=_build_dependencies())
        assert hasattr(instance, "transform_for_gold"), (
            f"{transformer_class.__name__} must have transform_for_gold method"
        )
        assert callable(instance.transform_for_gold), (
            f"{transformer_class.__name__}.transform_for_gold must be callable"
        )


class TestTransformerIdentity:
    """Test transformer identity computation capabilities."""

    @pytest.mark.parametrize("transformer_class", get_all_transformers())
    def test_has_compute_content_hash_method(
        self, transformer_class: type[BaseTransformer]
    ) -> None:
        """All transformers MUST have compute_content_hash method.

        Content hash is used for record versioning and deduplication.
        Inherited from BaseTransformer.
        """
        instance = transformer_class(dependencies=_build_dependencies())
        assert hasattr(instance, "compute_content_hash"), (
            f"{transformer_class.__name__} must have compute_content_hash method"
        )
        assert callable(instance.compute_content_hash), (
            f"{transformer_class.__name__}.compute_content_hash must be callable"
        )

    @pytest.mark.parametrize("transformer_class", get_all_transformers())
    def test_has_compute_entity_id_method(
        self, transformer_class: type[BaseTransformer]
    ) -> None:
        """All transformers MUST have compute_entity_id method.

        Entity ID provides stable identification across runs.
        Inherited from BaseTransformer.
        """
        instance = transformer_class(dependencies=_build_dependencies())
        assert hasattr(instance, "compute_entity_id"), (
            f"{transformer_class.__name__} must have compute_entity_id method"
        )
        assert callable(instance.compute_entity_id), (
            f"{transformer_class.__name__}.compute_entity_id must be callable"
        )


class TestTransformerPiiHashing:
    """Test transformer PII hashing capabilities."""

    @pytest.mark.parametrize("transformer_class", get_all_transformers())
    def test_has_hash_pii_value_method(
        self, transformer_class: type[BaseTransformer]
    ) -> None:
        """All transformers MUST have hash_pii_value method.

        PII hashing enables privacy-preserving author data handling.
        Inherited from BaseTransformer.
        """
        instance = transformer_class(dependencies=_build_dependencies())
        assert hasattr(instance, "hash_pii_value"), (
            f"{transformer_class.__name__} must have hash_pii_value method"
        )
        assert callable(instance.hash_pii_value), (
            f"{transformer_class.__name__}.hash_pii_value must be callable"
        )

    @pytest.mark.parametrize("transformer_class", get_all_transformers())
    def test_has_hash_pii_list_method(
        self, transformer_class: type[BaseTransformer]
    ) -> None:
        """All transformers MUST have hash_pii_list method.

        PII list hashing is used for author lists.
        Inherited from BaseTransformer.
        """
        instance = transformer_class(dependencies=_build_dependencies())
        assert hasattr(instance, "hash_pii_list"), (
            f"{transformer_class.__name__} must have hash_pii_list method"
        )
        assert callable(instance.hash_pii_list), (
            f"{transformer_class.__name__}.hash_pii_list must be callable"
        )

    @pytest.mark.parametrize("transformer_class", get_all_transformers())
    def test_pii_hasher_has_none_default(
        self, transformer_class: type[BaseTransformer]
    ) -> None:
        """pii_hasher parameter SHOULD default to None.

        None marks the collaborator as composition-owned; the explicit
        runtime default is assembled outside BaseTransformer.
        """
        sig = inspect.signature(transformer_class.__init__)
        pii_hasher_param = sig.parameters.get("pii_hasher")
        if pii_hasher_param is not None:
            assert pii_hasher_param.default is None, (
                f"{transformer_class.__name__}.pii_hasher should default to None"
            )


class TestTransformerHelperMethods:
    """Test transformer helper methods from BaseTransformer."""

    @pytest.mark.parametrize("transformer_class", get_all_transformers())
    def test_has_serialize_json_method(
        self, transformer_class: type[BaseTransformer]
    ) -> None:
        """All transformers MUST have serialize_json static method.

        Used for serializing complex fields (dict/list) to JSON strings.
        """
        assert hasattr(transformer_class, "serialize_json"), (
            f"{transformer_class.__name__} must have serialize_json method"
        )
        assert callable(transformer_class.serialize_json), (
            f"{transformer_class.__name__}.serialize_json must be callable"
        )

    @pytest.mark.parametrize("transformer_class", get_all_transformers())
    def test_has_entity_to_silver_record_method(
        self, transformer_class: type[BaseTransformer]
    ) -> None:
        """All transformers MUST have entity_to_silver_record static method.

        Converts Domain Entity to SilverRecord format with lineage fields.
        """
        assert hasattr(transformer_class, "entity_to_silver_record"), (
            f"{transformer_class.__name__} must have entity_to_silver_record method"
        )
        assert callable(transformer_class.entity_to_silver_record), (
            f"{transformer_class.__name__}.entity_to_silver_record must be callable"
        )
