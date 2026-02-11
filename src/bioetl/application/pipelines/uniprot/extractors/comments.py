"""
Comment extractor for UniProt JSON data.
"""

from __future__ import annotations

from typing import Any

from bioetl.application.pipelines.uniprot.extractors.abstract import AbstractExtractor
from bioetl.application.pipelines.uniprot.extractors.extractor_utils import (
    ExtractorUtils,
)
from bioetl.domain.serialization import serialize_to_json


class CommentExtractor(AbstractExtractor):
    """
    Extracts comment information from UniProt JSON data.

    Comments include function, subunit, subcellular location, etc.
    """

    def extract(self, entry: dict[str, Any]) -> dict[str, Any]:
        """
        Extract comments from a UniProt entry.

        Note: This method is kept for compatibility but the Transformer
        primarily uses the static methods below.

        Args:
            entry: The UniProt entry dictionary

        Returns:
            Dictionary containing extracted comments and notes
        """
        # This implementation mimics the legacy behavior but uses the new static methods
        # to process the 'comments' field from the entry.
        result: dict[str, Any] = {}
        comments = entry.get("comments", [])

        result["function"] = CommentExtractor.extract_by_type(comments, "FUNCTION")
        result["subunit"] = CommentExtractor.extract_by_type(comments, "SUBUNIT")
        result["subcellular_location"] = CommentExtractor.extract_subcellular_locations(comments)
        # ... map other fields as needed if this method is actually used.
        return result

    @staticmethod
    def extract_by_type(comments: Any, comment_type: str) -> str | None:
        """Extract comment text by type."""
        if not comments or not isinstance(comments, list):
            return None

        target_type = comment_type.upper()

        results = []
        for comment in comments:
            if not isinstance(comment, dict):
                continue
            if comment.get("commentType", "").upper() == target_type:
                # Text is usually in 'texts' list of objects with 'value'
                texts = comment.get("texts", [])
                for t in texts:
                    if isinstance(t, dict) and (val := t.get("value")):
                        results.append(val)
                    elif isinstance(t, str):
                        results.append(t)

        return serialize_to_json(results, ensure_ascii=False) if results else None

    @staticmethod
    def extract_catalytic_activity(comments: Any) -> str | None:
        """Extract catalytic activity."""
        if not comments or not isinstance(comments, list):
            return None

        activities = []
        for comment in comments:
            if not isinstance(comment, dict):
                continue
            if comment.get("commentType") == "CATALYTIC ACTIVITY":
                reaction = comment.get("reaction", {})

                # We construct a dict or string representation?
                # Transformer expects a list of reactions (strings) or structured?
                # The schema says JSON array of catalytic reactions.
                # The test expects a list of dicts with 'reaction' and 'ec_number'.
                # But the test calls json.loads(result) and asserts parsed[0]["reaction"] == ...

                activity = {}
                if name := reaction.get("name"):
                    activity["reaction"] = name
                if ec := reaction.get("ecNumber"):
                    activity["ec_number"] = ec
                if source := reaction.get("evidence"): # or source
                     activity["evidence"] = source

                if activity:
                    activities.append(activity)

        return serialize_to_json(activities, ensure_ascii=False) if activities else None

    @staticmethod
    def extract_subcellular_locations(comments: Any) -> str | None:
        """Extract subcellular locations."""
        if not comments or not isinstance(comments, list):
            return None

        locations = []
        for comment in comments:
            if not isinstance(comment, dict):
                continue
            if comment.get("commentType") == "SUBCELLULAR LOCATION":
                subcells = comment.get("subcellularLocations", [])
                for sc in subcells:
                    location_entry = sc.get("location", {})
                    loc_val = location_entry.get("value")
                    if loc_val:
                        locations.append(loc_val)

                    topology_entry = sc.get("topology", {})
                    if top_val := topology_entry.get("value"):
                         # Optionally add topology to the list or return structured
                         # The schema expects JSON array of strings (locations).
                         # But wait, test says: "Cytoplasm" in parsed.
                         # So simpler list of strings is expected.
                         pass

        return serialize_to_json(list(set(locations)), ensure_ascii=False) if locations else None

    @staticmethod
    def extract_alternative_products(comments: Any) -> str | None:
        """Extract alternative products (isoforms)."""
        if not comments or not isinstance(comments, list):
            return None

        products = []
        for comment in comments:
            if comment.get("commentType") == "ALTERNATIVE PRODUCTS":
                isoforms = comment.get("isoforms", [])
                for iso in isoforms:
                    item = {}
                    if name := iso.get("name", {}).get("value"):
                         item["name"] = name
                    if ids := iso.get("isoformIds"):
                         item["ids"] = ids
                    if syns := iso.get("synonyms"):
                         item["synonyms"] = [s.get("value") for s in syns if s.get("value")]
                    if note := iso.get("note", {}).get("value"):
                         item["note"] = note
                    products.append(item)

        return serialize_to_json(products, ensure_ascii=False) if products else None

    @staticmethod
    def extract_cofactors(comments: Any) -> str | None:
        """Extract cofactors."""
        if not comments or not isinstance(comments, list):
            return None

        cofactors = []
        for comment in comments:
            if comment.get("commentType") == "COFACTOR":
                 cofs = comment.get("cofactors", [])
                 for cof in cofs:
                     item = {}
                     if name := cof.get("name"):
                         item["name"] = name
                     if ref := cof.get("cofactorCrossReference", {}).get("id"):
                         item["chebi_id"] = ref
                     if note_texts := cof.get("note", {}).get("texts"):
                         if note_texts and isinstance(note_texts, list):
                             item["note"] = note_texts[0].get("value")
                     cofactors.append(item)

        return serialize_to_json(cofactors, ensure_ascii=False) if cofactors else None

    @staticmethod
    def extract_biophysicochemical_properties(comments: Any) -> str | None:
        """Extract biophysicochemical properties."""
        if not comments or not isinstance(comments, list):
            return None

        props = {}
        for comment in comments:
            if comment.get("commentType") == "BIOPHYSICOCHEMICAL PROPERTIES":
                # pH Dependence
                if ph := comment.get("phDependence"):
                     texts = ph.get("texts", [])
                     props["ph_dependence"] = [t.get("value") for t in texts if t.get("value")]

                # Temperature Dependence
                if temp := comment.get("temperatureDependence"):
                     texts = temp.get("texts", [])
                     props["temperature_dependence"] = [t.get("value") for t in texts if t.get("value")]

                # Kinetics
                if kinetics := comment.get("kineticParameters"):
                    kp = {}
                    if kms := kinetics.get("michaelisConstants"):
                        kp["km"] = kms
                    if vmax := kinetics.get("maximumVelocities"):
                        kp["vmax"] = vmax
                    if kp:
                        props["kinetic_parameters"] = kp

                # Redox
                if redox := comment.get("redoxPotential"):
                     texts = redox.get("texts", [])
                     props["redox_potential"] = [t.get("value") for t in texts if t.get("value")]

        return serialize_to_json(props, ensure_ascii=False) if props else None

    @staticmethod
    def extract_induction(comments: Any) -> str | None:
        """Extract induction information."""
        return CommentExtractor.extract_by_type(comments, "INDUCTION")

    @staticmethod
    def count_isoforms(comments: Any) -> int:
        """Count isoforms."""
        if not comments or not isinstance(comments, list):
            return 0

        count = 0
        for comment in comments:
             if comment.get("commentType") == "ALTERNATIVE PRODUCTS":
                 iso_list = comment.get("isoforms", [])
                 if isinstance(iso_list, list):
                     count += len(iso_list)
        return count

    @staticmethod
    def extract_isoform_details(comments: Any) -> dict[str, str | None]:
        """Extract detailed isoform info."""
        names = []
        ids = []
        synonyms = []

        if comments and isinstance(comments, list):
            for comment in comments:
                if comment.get("commentType") == "ALTERNATIVE PRODUCTS":
                    isoforms = comment.get("isoforms", [])
                    for iso in isoforms:
                        # Names
                        if name := iso.get("name", {}).get("value"):
                            names.append(name)

                        # IDs
                        if iso_ids := iso.get("isoformIds"):
                            ids.extend(iso_ids)

                        # Synonyms
                        if syns := iso.get("synonyms"):
                            for s in syns:
                                if val := s.get("value"):
                                    synonyms.append(val)

        return {
            "isoform_names": serialize_to_json(names, ensure_ascii=False) if names else None,
            "isoform_ids": serialize_to_json(ids, ensure_ascii=False) if ids else None,
            "isoform_synonyms": serialize_to_json(synonyms, ensure_ascii=False) if synonyms else None,
        }

    @staticmethod
    def extract_reactions(comments: Any) -> str | None:
        """Extract reactions."""
        if not comments or not isinstance(comments, list):
             return None

        reactions = []
        for comment in comments:
            if comment.get("commentType") == "CATALYTIC ACTIVITY":
                if name := comment.get("reaction", {}).get("name"):
                    reactions.append(name)

        return serialize_to_json(reactions, ensure_ascii=False) if reactions else None

    @staticmethod
    def extract_reaction_ec_numbers(comments: Any) -> str | None:
        """Extract EC numbers from reactions."""
        if not comments or not isinstance(comments, list):
             return None

        ecs = []
        for comment in comments:
            if comment.get("commentType") == "CATALYTIC ACTIVITY":
                if ec := comment.get("reaction", {}).get("ecNumber"):
                    ecs.append(ec)

        return serialize_to_json(ecs, ensure_ascii=False) if ecs else None
