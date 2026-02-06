"""Comment data extraction for UniProt records."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

from bioetl.application.pipelines.uniprot.extractors.utils import (
    IsoformNote,
    clean_text,
    process_single_isoform_note,
)


class CommentExtractor:
    """Extracts comment-related data from UniProt XML records."""

    def _clean_text(self, text: str) -> str:
        """Removes trailing periods and excessive whitespace from text."""
        return clean_text(text)

    def extract_comments(self, entry: ET.Element, ns: dict[str, str]) -> dict[str, Any]:
        """
        Extracts various comment types from the UniProt entry.

        Args:
            entry: XML element for the entry
            ns: Namespace dictionary

        Returns:
            Dictionary of extracted comments
        """
        comments = entry.findall("u:comment", ns)

        functions = []
        subunits = []
        domains = []
        inductions = []
        tissues = []
        disruptions = []
        regulations = []
        pathways = []
        misc = []
        polymorphisms = []
        similarities = []
        cautions = []
        pharmaceuticals = []
        biotech = []
        mass_spec = []
        seq_cautions = []
        interactions = []
        diseases = []
        subcellular = []
        catalytic_activities = []
        ec_numbers = set()
        isoform_notes: dict[str, list[IsoformNote]] = {}

        simple_fields = {
            "function", "subunit", "domain", "induction", "tissue specificity",
            "disruption phenotype", "activity regulation", "pathway",
            "miscellaneous", "polymorphism", "similarity", "caution",
            "pharmaceutical", "biotechnology"
        }

        for comment in comments:
            c_type = comment.get("type")

            if c_type == "catalytic activity":
                # Handle structured catalytic activity (reaction)
                reaction = comment.find("u:reaction", ns)
                if reaction is not None:
                    # Extract EC number
                    db_refs = reaction.findall("u:dbReference", ns)
                    for db_ref in db_refs:
                        if db_ref.get("type") == "EC":
                            ec_num = db_ref.get("id")
                            if ec_num:
                                ec_numbers.add(ec_num)

                    # Extract reaction text
                    text = reaction.find("u:text", ns)
                    if text is not None and text.text:
                        cleaned = self._clean_text(text.text)
                        if cleaned:
                            catalytic_activities.append(cleaned)

            elif c_type in simple_fields:
                # Handle simple text fields
                text_elem = comment.find("u:text", ns)
                if text_elem is not None and text_elem.text:
                    cleaned = self._clean_text(text_elem.text)
                    if cleaned:
                        if c_type == "function":
                            functions.append(cleaned)
                        elif c_type == "subunit":
                            subunits.append(cleaned)
                        elif c_type == "domain":
                            domains.append(cleaned)
                        elif c_type == "induction":
                            inductions.append(cleaned)
                        elif c_type == "tissue specificity":
                            tissues.append(cleaned)
                        elif c_type == "disruption phenotype":
                            disruptions.append(cleaned)
                        elif c_type == "activity regulation":
                            regulations.append(cleaned)
                        elif c_type == "pathway":
                            pathways.append(cleaned)
                        elif c_type == "miscellaneous":
                            misc.append(cleaned)
                        elif c_type == "polymorphism":
                            polymorphisms.append(cleaned)
                        elif c_type == "similarity":
                            similarities.append(cleaned)
                        elif c_type == "caution":
                            cautions.append(cleaned)
                        elif c_type == "pharmaceutical":
                            pharmaceuticals.append(cleaned)
                        elif c_type == "biotechnology":
                            biotech.append(cleaned)

            elif c_type == "disease":
                # Handle disease comments
                disease = comment.find("u:disease", ns)
                text_elem = comment.find("u:text", ns)

                # Try to get disease ID if available
                disease_id = None
                if disease is not None:
                    disease_id = disease.get("id")

                # Get text from disease element or fallback to text element
                d_text = None
                if disease is not None:
                    name_elem = disease.find("u:name", ns)
                    if name_elem is not None:
                        d_text = name_elem.text

                    # Also look for description in disease element
                    desc_elem = disease.find("u:description", ns)
                    if desc_elem is not None and desc_elem.text:
                        if d_text:
                            d_text = f"{d_text}: {desc_elem.text}"
                        else:
                            d_text = desc_elem.text

                if not d_text and text_elem is not None:
                    d_text = text_elem.text

                if d_text:
                    cleaned = self._clean_text(d_text)
                    if cleaned:
                        if disease_id:
                            diseases.append(f"{cleaned} (ID: {disease_id})")
                        else:
                            diseases.append(cleaned)

            elif c_type == "subcellular location":
                # Handle subcellular location
                locs = comment.findall("u:subcellularLocation", ns)
                for loc_group in locs:
                    location_parts = []
                    for loc in loc_group:
                        if loc.text:
                            cleaned = self._clean_text(loc.text)
                            if cleaned:
                                location_parts.append(cleaned)

                    if location_parts:
                        subcellular.append("; ".join(location_parts))

            elif c_type == "alternative products":
                # Extract isoform notes
                isoform_notes.update(self._process_isoforms(comment, ns))

            elif c_type == "mass spectrometry":
                # Handle mass spec comments
                text_elem = comment.find("u:text", ns)
                if text_elem is not None and text_elem.text:
                    cleaned = self._clean_text(text_elem.text)
                    if cleaned:
                        mass_spec.append(cleaned)

            elif c_type == "sequence caution":
                # Handle sequence caution
                text_elem = comment.find("u:text", ns)
                conflict_type = comment.get("type")

                caution_parts = []
                if conflict_type:
                    caution_parts.append(f"Type: {conflict_type}")

                if text_elem is not None and text_elem.text:
                    cleaned = self._clean_text(text_elem.text)
                    if cleaned:
                        caution_parts.append(cleaned)

                if caution_parts:
                    seq_cautions.append("; ".join(caution_parts))

            elif c_type == "interaction":
                # Handle interaction
                interactant = comment.find("u:interactant", ns)
                if interactant is not None:
                    # Try to get intact ID or label
                    intact_id = interactant.get("intactId")
                    label = interactant.find("u:label", ns)

                    interact_text = []
                    if label is not None and label.text:
                        interact_text.append(label.text)
                    if intact_id:
                        interact_text.append(f"(IntAct: {intact_id})")

                    if interact_text:
                        interactions.append(" ".join(interact_text))

        return {
            "function": functions,
            "subunit": subunits,
            "domain": domains,
            "induction": inductions,
            "tissue_specificity": tissues,
            "disruption_phenotype": disruptions,
            "activity_regulation": regulations,
            "pathway": pathways,
            "miscellaneous": misc,
            "polymorphism": polymorphisms,
            "similarity": similarities,
            "caution": cautions,
            "pharmaceutical": pharmaceuticals,
            "biotechnology": biotech,
            "mass_spectrometry": mass_spec,
            "sequence_caution": seq_cautions,
            "interaction": interactions,
            "disease": diseases,
            "subcellular_location": subcellular,
            "catalytic_activity": catalytic_activities,
            "ec_numbers": list(ec_numbers),
            "isoform_notes": isoform_notes,
        }

    def _process_isoforms(
        self, comment_element: ET.Element, ns: dict[str, str]
    ) -> dict[str, list[IsoformNote]]:
        """
        Extracts isoform notes from 'alternative products' comments.

        Args:
            comment_element: XML element for the comment
            ns: Namespace dictionary

        Returns:
            Dictionary mapping isoform IDs to lists of IsoformNote objects
        """
        result: dict[str, list[IsoformNote]] = {}

        # Look for isoform elements
        isoforms = comment_element.findall("u:isoform", ns)
        if not isoforms:
            return result

        for isoform in isoforms:
            # Get isoform IDs
            ids = [
                id_elem.text
                for id_elem in isoform.findall("u:id", ns)
                if id_elem.text
            ]
            if not ids:
                continue

            # Check for note text
            note_elem = isoform.find("u:note", ns)
            if note_elem is None or not note_elem.text:
                continue

            note_text = clean_text(note_elem.text)
            if not note_text:
                continue

            process_single_isoform_note(note_text, ids, result)

        return result
