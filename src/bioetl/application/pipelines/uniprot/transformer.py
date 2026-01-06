"""UniProt Protein Transformer.

Transforms raw UniProt protein records into Silver-layer format using
the Protein domain entity for validation and invariant checking.

Extended to extract:
- Core identifiers and metadata (entry_type, secondary_accessions)
- Protein names (alternative names, EC numbers, flag)
- Organism and taxonomy information
- Functional annotations (function, catalytic_activity, subunit, etc.)
- Cross-references (GO, DrugBank, ChEMBL, GtoPdb)
- Sequence features and keywords
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, cast

from bioetl.application.core.base_transformer import (
    BaseTransformer,
    TransformationError,
)
from bioetl.domain.entities import Protein
from bioetl.domain.services import IdentityService

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.filtering import GoldFilterConfig
    from bioetl.domain.ports import MetricsPort, PiiHasherPort, TracingPort
    from bioetl.domain.types import BronzeRecord, SilverRecord


class UniProtProteinTransformer(BaseTransformer):
    """Transformer for UniProt protein records.

    Uses Protein domain entity for validation and lineage tracking.
    Records without required fields (accession, entry_name) are skipped.
    protein_name is optional and may be None.
    """

    def __init__(
        self,
        provider: str = "uniprot",
        entity_type: str = "protein",
        tracer: TracingPort | None = None,
        metrics: MetricsPort | None = None,
        gold_filters: GoldFilterConfig | None = None,
        identity_service: IdentityService | None = None,
        pii_hasher: PiiHasherPort | None = None,
    ):
        """Initialize UniProt protein transformer.

        Args:
            provider: Data provider identifier.
            entity_type: Entity type for metrics labels. Defaults to 'protein'.
            tracer: Optional tracing port for distributed tracing (O1 observability).
            metrics: Optional metrics port for duration/error tracking (O1 observability).
            gold_filters: Optional filter configuration for Gold layer.
            identity_service: Service for computing entity IDs and content hashes.
            pii_hasher: Optional PII hasher for hashing author names and other PII.

        """
        super().__init__(
            provider,
            entity_type=entity_type,
            tracer=tracer,
            metrics=metrics,
            gold_filters=gold_filters,
            identity_service=identity_service,
            pii_hasher=pii_hasher,
        )

    async def _transform_impl(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> SilverRecord | None:
        """Transform raw UniProt record to Silver format.

        Args:
            context: Pipeline context with run_id, run_type, logger.
            record: Raw Bronze record from UniProt.
            index: Sequential index of the record in the pipeline run.

        Returns:
            SilverRecord if transformation successful, None if skipped.

        Raises:
            TransformationError: If required fields are missing.
            ValueError: If Protein entity validation fails.

        """
        # Step 1: Validate required fields
        accession = self._get_required_field(record, "primaryAccession")
        entry_name = self._get_entry_name(record)

        # Step 2: Build business data dictionary with all fields
        business_data: dict[str, Any] = {
            # Core identifiers
            "accession": accession,
            "entry_name": entry_name,
            "entry_type": record.get("entryType"),
            "secondary_accessions": self._serialize_list(
                record.get("secondaryAccessions")
            ),
            # Protein names
            "protein_name": self._extract_protein_name(record),
            "protein_short_names": self._extract_short_names(record),
            "protein_alternative_names": self._extract_alternative_names(record),
            "protein_ec_numbers": self._extract_ec_numbers(record),
            "flag": self._extract_nested(record, "proteinDescription.flag"),
            # Gene names
            "gene_names": self._extract_gene_names(record),
            "gene_primary": self._extract_primary_gene(record),
            "gene_synonyms": self._extract_gene_synonyms(record),
            "gene_orf_names": self._extract_gene_orf_names(record),
            # Organism
            "organism_scientific": self._extract_nested(
                record, "organism.scientificName"
            ),
            "organism_common": self._extract_nested(record, "organism.commonName"),
            "taxonomy_id": self._extract_nested(record, "organism.taxonId"),
            "lineage": self._serialize_list(
                self._extract_nested(record, "organism.lineage")
            ),
            # Evidence & Quality
            "protein_existence": self._extract_protein_existence(record),
            "annotation_score": record.get("annotationScore"),
            "reviewed": self._is_reviewed(record),
            # Sequence
            "sequence": self._extract_nested(record, "sequence.value"),
            "sequence_length": self._extract_nested(record, "sequence.length"),
            "sequence_mass": self._extract_nested(record, "sequence.molWeight"),
            "sequence_checksum": self._extract_nested(record, "sequence.crc64"),
            # Functional annotations
            "function_comment": self._extract_comments_by_type(record, "FUNCTION"),
            "catalytic_activity": self._extract_catalytic_activity(record),
            "activity_regulation": self._extract_comments_by_type(
                record, "ACTIVITY REGULATION"
            ),
            "subunit": self._extract_comments_by_type(record, "SUBUNIT"),
            "pathway": self._extract_comments_by_type(record, "PATHWAY"),
            "subcellular_location": self._extract_subcellular_locations(record),
            "tissue_specificity": self._extract_comments_by_type(
                record, "TISSUE SPECIFICITY"
            ),
            "alternative_products": self._extract_alternative_products(record),
            "disease_involvement": self._extract_comments_by_type(
                record, "DISEASE"
            ),
            "similarity_comment": self._extract_comments_by_type(record, "SIMILARITY"),
            "caution": self._extract_comments_by_type(record, "CAUTION"),
            # Cross-references
            "go_terms": self._extract_go_terms(record),
            "drugbank_ids": self._extract_xref_ids(record, "DrugBank"),
            "chembl_ids": self._extract_xref_ids(record, "ChEMBL"),
            "guidetopharmacology_ids": self._extract_xref_ids(
                record, "GuidetoPHARMACOLOGY"
            ),
            # Features & Keywords
            "features": self._extract_features(record),
            "keywords": self._extract_keywords(record),
            # Counts
            "cross_reference_count": self._count_list(
                record.get("uniProtKBCrossReferences")
            ),
            "feature_count": self._count_list(record.get("features")),
            "keyword_count": self._count_list(record.get("keywords")),
            "isoform_count": self._count_isoforms(record),
        }

        # Legacy compatibility - keep organism_id for backward compat
        business_data["organism_id"] = business_data.get("taxonomy_id")

        # Step 3: Generate entity_id using IdentityService (RULES.md §2.8)
        entity_id = self.compute_entity_id(
            source_id=accession,
            record={"accession": accession},
        )

        # Step 4: Compute content_hash (RULES.md §2.8.1)
        content_hash = self.compute_content_hash(business_data, exclude_none=True)

        # Step 5: Create domain entity with lineage metadata
        entity = self._create_entity(
            Protein,
            context,
            entity_id=entity_id,
            content_hash=content_hash,
            index=index,
            **business_data,
        )

        # Step 6: Convert to SilverRecord with lineage field renaming
        return cast("SilverRecord", self.entity_to_silver_record(entity))

    def _get_entry_name(self, record: BronzeRecord) -> str:
        """Extract entry name (uniProtkbId) as required field.

        Args:
            record: Bronze record dictionary.

        Returns:
            Entry name string.

        Raises:
            TransformationError: If entry_name is missing.

        """
        entry_name = record.get("uniProtkbId")
        if not entry_name:
            raise TransformationError(
                "Missing required field: uniProtkbId", field="uniProtkbId"
            )
        return str(entry_name)

    def _extract_protein_name(self, record: BronzeRecord) -> str | None:
        """Extract protein name (optional field).

        Args:
            record: Bronze record dictionary.

        Returns:
            Protein name string or None if not found.

        """
        protein_name = self._extract_nested(
            record,
            "proteinDescription.recommendedName.fullName.value",
        )
        return str(protein_name) if protein_name else None

    def _extract_gene_names(self, record: BronzeRecord) -> list[str]:
        """Extract gene names from genes list.

        Args:
            record: Bronze record dictionary.

        Returns:
            List of gene name strings.

        """
        names: list[str] = []
        genes = record.get("genes")
        if not genes or not isinstance(genes, list):
            return names

        for gene in genes:
            if not isinstance(gene, dict):
                continue
            gene_name = gene.get("geneName", {})
            if isinstance(gene_name, dict):
                name = gene_name.get("value")
                if name:
                    names.append(str(name))
        return names

    # ========================================================================
    # Utility Methods
    # ========================================================================

    def _serialize_list(self, value: Any) -> str | None:
        """Serialize a list to JSON string.

        Args:
            value: List to serialize, or None/non-list.

        Returns:
            JSON string or None if empty/None/not a list.
        """
        if not value or not isinstance(value, list):
            return None
        return json.dumps(value, ensure_ascii=False)

    def _count_list(self, value: Any) -> int | None:
        """Count items in a list.

        Args:
            value: List to count, or None/non-list.

        Returns:
            Count or None if not a list.
        """
        if value is None:
            return None
        if isinstance(value, list):
            return len(value)
        return None

    def _is_reviewed(self, record: BronzeRecord) -> bool:
        """Check if entry is Swiss-Prot (reviewed).

        Args:
            record: Bronze record dictionary.

        Returns:
            True if reviewed (Swiss-Prot), False otherwise.
        """
        entry_type = record.get("entryType", "")
        return "Swiss-Prot" in str(entry_type)

    # ========================================================================
    # Protein Name Extraction
    # ========================================================================

    def _extract_short_names(self, record: BronzeRecord) -> str | None:
        """Extract short names from recommended name.

        Args:
            record: Bronze record dictionary.

        Returns:
            JSON array of short names or None.
        """
        short_names = self._extract_nested(
            record, "proteinDescription.recommendedName.shortNames"
        )
        if not short_names or not isinstance(short_names, list):
            return None
        values = [sn.get("value") for sn in short_names if isinstance(sn, dict)]
        values = [v for v in values if v]
        return json.dumps(values, ensure_ascii=False) if values else None

    def _extract_alternative_names(self, record: BronzeRecord) -> str | None:
        """Extract alternative protein names.

        Args:
            record: Bronze record dictionary.

        Returns:
            JSON array of alternative names or None.
        """
        alt_names = self._extract_nested(
            record, "proteinDescription.alternativeNames"
        )
        if not alt_names or not isinstance(alt_names, list):
            return None

        values = []
        for alt in alt_names:
            if isinstance(alt, dict):
                full_name = alt.get("fullName", {})
                if isinstance(full_name, dict):
                    name = full_name.get("value")
                    if name:
                        values.append(name)
        return json.dumps(values, ensure_ascii=False) if values else None

    def _extract_ec_numbers(self, record: BronzeRecord) -> str | None:
        """Extract EC numbers from recommended name.

        Args:
            record: Bronze record dictionary.

        Returns:
            JSON array of EC numbers or None.
        """
        ec_numbers = self._extract_nested(
            record, "proteinDescription.recommendedName.ecNumbers"
        )
        if not ec_numbers or not isinstance(ec_numbers, list):
            return None
        values = [ec.get("value") for ec in ec_numbers if isinstance(ec, dict)]
        values = [v for v in values if v]
        return json.dumps(values, ensure_ascii=False) if values else None

    # ========================================================================
    # Gene Extraction (Extended)
    # ========================================================================

    def _extract_primary_gene(self, record: BronzeRecord) -> str | None:
        """Extract primary gene name.

        Args:
            record: Bronze record dictionary.

        Returns:
            Primary gene name or None.
        """
        genes = record.get("genes")
        if not genes or not isinstance(genes, list):
            return None

        for gene in genes:
            if isinstance(gene, dict):
                gene_name = gene.get("geneName", {})
                if isinstance(gene_name, dict):
                    value = gene_name.get("value")
                    if value:
                        return str(value)
        return None

    def _extract_gene_synonyms(self, record: BronzeRecord) -> str | None:
        """Extract gene synonyms.

        Args:
            record: Bronze record dictionary.

        Returns:
            JSON array of gene synonyms or None.
        """
        genes = record.get("genes")
        if not genes or not isinstance(genes, list):
            return None

        all_synonyms: list[str] = []
        for gene in genes:
            if not isinstance(gene, dict):
                continue
            synonyms = gene.get("synonyms", [])
            if isinstance(synonyms, list):
                for syn in synonyms:
                    if isinstance(syn, dict):
                        value = syn.get("value")
                        if value:
                            all_synonyms.append(str(value))
        return json.dumps(all_synonyms, ensure_ascii=False) if all_synonyms else None

    def _extract_gene_orf_names(self, record: BronzeRecord) -> str | None:
        """Extract ORF names from genes.

        Args:
            record: Bronze record dictionary.

        Returns:
            JSON array of ORF names or None.
        """
        genes = record.get("genes")
        if not genes or not isinstance(genes, list):
            return None

        all_orf: list[str] = []
        for gene in genes:
            if not isinstance(gene, dict):
                continue
            orf_names = gene.get("orfNames", [])
            if isinstance(orf_names, list):
                for orf in orf_names:
                    if isinstance(orf, dict):
                        value = orf.get("value")
                        if value:
                            all_orf.append(str(value))
        return json.dumps(all_orf, ensure_ascii=False) if all_orf else None

    # ========================================================================
    # Evidence & Quality Extraction
    # ========================================================================

    def _extract_protein_existence(self, record: BronzeRecord) -> str | None:
        """Extract protein existence level.

        Normalizes the API value to match schema constants.

        Args:
            record: Bronze record dictionary.

        Returns:
            Protein existence level or None.
        """
        existence = record.get("proteinExistence")
        if not existence:
            return None

        # API may return "1: Evidence at protein level" - extract just the text
        existence_str = str(existence)
        # Map common formats to schema values
        existence_map = {
            "1: Evidence at protein level": "Evidence at protein level",
            "2: Evidence at transcript level": "Evidence at transcript level",
            "3: Inferred from homology": "Inferred from homology",
            "4: Predicted": "Predicted",
            "5: Uncertain": "Uncertain",
        }
        return existence_map.get(existence_str, existence_str)

    # ========================================================================
    # Comment Extraction
    # ========================================================================

    def _extract_comments_by_type(
        self, record: BronzeRecord, comment_type: str
    ) -> str | None:
        """Extract comments of specific type as JSON string.

        Args:
            record: Bronze record.
            comment_type: Comment type (FUNCTION, SUBUNIT, etc.)

        Returns:
            JSON string of comment values or None.
        """
        comments = record.get("comments", [])
        if not comments or not isinstance(comments, list):
            return None

        extracted: list[str] = []
        for comment in comments:
            if not isinstance(comment, dict):
                continue
            if comment.get("commentType") != comment_type:
                continue

            # Extract text values
            texts = comment.get("texts", [])
            if isinstance(texts, list):
                for text in texts:
                    if isinstance(text, dict):
                        value = text.get("value")
                        if value:
                            extracted.append(str(value))

        return json.dumps(extracted, ensure_ascii=False) if extracted else None

    def _extract_catalytic_activity(self, record: BronzeRecord) -> str | None:
        """Extract catalytic activity information.

        Args:
            record: Bronze record.

        Returns:
            JSON array of catalytic activities or None.
        """
        comments = record.get("comments", [])
        if not comments or not isinstance(comments, list):
            return None

        extracted: list[dict[str, Any]] = []
        for comment in comments:
            if not isinstance(comment, dict):
                continue
            if comment.get("commentType") != "CATALYTIC ACTIVITY":
                continue

            reaction = comment.get("reaction", {})
            if isinstance(reaction, dict):
                activity: dict[str, Any] = {}
                if reaction.get("name"):
                    activity["reaction"] = reaction.get("name")
                if reaction.get("ecNumber"):
                    activity["ec_number"] = reaction.get("ecNumber")
                if activity:
                    extracted.append(activity)

        return json.dumps(extracted, ensure_ascii=False) if extracted else None

    def _extract_subcellular_locations(self, record: BronzeRecord) -> str | None:
        """Extract subcellular location information.

        Args:
            record: Bronze record.

        Returns:
            JSON array of subcellular locations or None.
        """
        comments = record.get("comments", [])
        if not comments or not isinstance(comments, list):
            return None

        extracted: list[str] = []
        for comment in comments:
            if not isinstance(comment, dict):
                continue
            if comment.get("commentType") != "SUBCELLULAR LOCATION":
                continue

            locations = comment.get("subcellularLocations", [])
            if isinstance(locations, list):
                for loc in locations:
                    if isinstance(loc, dict):
                        location = loc.get("location", {})
                        if isinstance(location, dict):
                            value = location.get("value")
                            if value:
                                extracted.append(str(value))

        return json.dumps(extracted, ensure_ascii=False) if extracted else None

    def _extract_alternative_products(self, record: BronzeRecord) -> str | None:
        """Extract alternative products (isoforms) information.

        Args:
            record: Bronze record.

        Returns:
            JSON array of isoform information or None.
        """
        comments = record.get("comments", [])
        if not comments or not isinstance(comments, list):
            return None

        extracted: list[dict[str, Any]] = []
        for comment in comments:
            if not isinstance(comment, dict):
                continue
            if comment.get("commentType") != "ALTERNATIVE PRODUCTS":
                continue

            isoforms = comment.get("isoforms", [])
            if isinstance(isoforms, list):
                for iso in isoforms:
                    if isinstance(iso, dict):
                        isoform_data: dict[str, Any] = {}
                        isoform_ids = iso.get("isoformIds", [])
                        if isoform_ids:
                            isoform_data["ids"] = isoform_ids
                        name = iso.get("name", {})
                        if isinstance(name, dict) and name.get("value"):
                            isoform_data["name"] = name.get("value")
                        if isoform_data:
                            extracted.append(isoform_data)

        return json.dumps(extracted, ensure_ascii=False) if extracted else None

    def _count_isoforms(self, record: BronzeRecord) -> int | None:
        """Count the number of isoforms.

        Args:
            record: Bronze record.

        Returns:
            Number of isoforms or None.
        """
        comments = record.get("comments", [])
        if not comments or not isinstance(comments, list):
            return None

        count = 0
        for comment in comments:
            if not isinstance(comment, dict):
                continue
            if comment.get("commentType") != "ALTERNATIVE PRODUCTS":
                continue

            isoforms = comment.get("isoforms", [])
            if isinstance(isoforms, list):
                count += len(isoforms)

        return count if count > 0 else None

    # ========================================================================
    # Cross-Reference Extraction
    # ========================================================================

    def _extract_go_terms(self, record: BronzeRecord) -> str | None:
        """Extract GO terms with structured data.

        Args:
            record: Bronze record.

        Returns:
            JSON array of GO terms: [{"id": "GO:0005524", "term": "ATP binding",
                                      "aspect": "F", "evidence": "IEA"}, ...]
        """
        xrefs = record.get("uniProtKBCrossReferences", [])
        if not xrefs or not isinstance(xrefs, list):
            return None

        go_terms: list[dict[str, Any]] = []
        for xref in xrefs:
            if not isinstance(xref, dict):
                continue
            if xref.get("database") != "GO":
                continue

            go_id = xref.get("id")
            if not go_id:
                continue

            # Parse properties
            props: dict[str, str] = {}
            properties = xref.get("properties", [])
            if isinstance(properties, list):
                for prop in properties:
                    if isinstance(prop, dict):
                        key = prop.get("key")
                        value = prop.get("value")
                        if key and value:
                            props[key] = value

            # Parse "F:ATP binding" → aspect="F", term="ATP binding"
            go_term_value = props.get("GoTerm", "")
            aspect = None
            term = None
            if go_term_value and ":" in go_term_value:
                parts = go_term_value.split(":", 1)
                if len(parts) == 2:
                    aspect = parts[0].strip() if parts[0].strip() in ("F", "P", "C") else None
                    term = parts[1].strip() if parts[1].strip() else None

            go_terms.append({
                "id": go_id,
                "term": term,
                "aspect": aspect,
                "evidence": props.get("GoEvidenceType"),
            })

        return json.dumps(go_terms, ensure_ascii=False) if go_terms else None

    def _extract_xref_ids(self, record: BronzeRecord, database: str) -> str | None:
        """Extract cross-reference IDs for specific database.

        Args:
            record: Bronze record.
            database: Database name (DrugBank, ChEMBL, GuidetoPHARMACOLOGY).

        Returns:
            JSON array of IDs or None.
        """
        xrefs = record.get("uniProtKBCrossReferences", [])
        if not xrefs or not isinstance(xrefs, list):
            return None

        ids: list[str] = []
        for xref in xrefs:
            if not isinstance(xref, dict):
                continue
            if xref.get("database") != database:
                continue

            xref_id = xref.get("id")
            if xref_id:
                ids.append(str(xref_id))

        return json.dumps(ids, ensure_ascii=False) if ids else None

    # ========================================================================
    # Features & Keywords Extraction
    # ========================================================================

    def _extract_features(self, record: BronzeRecord) -> str | None:
        """Extract sequence features.

        Args:
            record: Bronze record.

        Returns:
            JSON array of features or None.
        """
        features = record.get("features", [])
        if not features or not isinstance(features, list):
            return None

        extracted: list[dict[str, Any]] = []
        for feature in features:
            if not isinstance(feature, dict):
                continue

            feature_data: dict[str, Any] = {}
            if feature.get("type"):
                feature_data["type"] = feature.get("type")
            if feature.get("description"):
                feature_data["description"] = feature.get("description")
            if feature.get("featureId"):
                feature_data["feature_id"] = feature.get("featureId")

            # Extract location
            location = feature.get("location", {})
            if isinstance(location, dict):
                start = location.get("start", {})
                end = location.get("end", {})
                if isinstance(start, dict) and start.get("value"):
                    feature_data["start"] = start.get("value")
                if isinstance(end, dict) and end.get("value"):
                    feature_data["end"] = end.get("value")

            if feature_data:
                extracted.append(feature_data)

        return json.dumps(extracted, ensure_ascii=False) if extracted else None

    def _extract_keywords(self, record: BronzeRecord) -> str | None:
        """Extract UniProt keywords.

        Args:
            record: Bronze record.

        Returns:
            JSON array of keywords: [{"id": "KW-0067", "name": "ATP-binding",
                                      "category": "Molecular function"}, ...]
        """
        keywords = record.get("keywords", [])
        if not keywords or not isinstance(keywords, list):
            return None

        extracted: list[dict[str, Any]] = []
        for kw in keywords:
            if not isinstance(kw, dict):
                continue

            kw_data: dict[str, Any] = {}
            if kw.get("id"):
                kw_data["id"] = kw.get("id")
            if kw.get("name"):
                kw_data["name"] = kw.get("name")
            if kw.get("category"):
                kw_data["category"] = kw.get("category")

            if kw_data:
                extracted.append(kw_data)

        return json.dumps(extracted, ensure_ascii=False) if extracted else None
