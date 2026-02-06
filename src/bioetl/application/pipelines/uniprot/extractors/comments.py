"""
Comment extractor for UniProt XML data.
"""

from typing import Any

from bioetl.application.pipelines.uniprot.extractors.abstract import AbstractExtractor
from bioetl.application.pipelines.uniprot.extractors.extractor_utils import (
    ExtractorUtils,
)
from bioetl.domain.types import IsoformNote


class CommentExtractor(AbstractExtractor):
    """
    Extracts comment information from UniProt XML data.

    Comments include function, subunit, subcellular location, etc.
    Complex logic is needed to parse structured comments like subcellular location
    and isoform-specific notes.
    """

    def extract(self, entry: dict[str, Any]) -> dict[str, Any]:
        """
        Extract comments from a UniProt entry.

        Args:
            entry: The UniProt entry dictionary

        Returns:
            Dictionary containing extracted comments and notes
        """
        result: dict[str, Any] = {
            "function": [],
            "subunit": [],
            "subcellular_location": [],
            "tissue_specificity": [],
            "domain": [],
            "ptm": [],
            "similarity": [],
            "mass_spectrometry": [],
            "polymorphism": [],
            "pharmaceutical": [],
            "biotechnology": [],
            "disruption_phenotype": [],
            "disease": [],
            "interaction": [],
            "isoform_notes": [],
        }

        if not (comments := entry.get("comment")):
            return result

        # Ensure list
        if isinstance(comments, dict):
            comments = [comments]

        # Temporary storage for isoform notes
        isoform_notes: list[IsoformNote] = []

        for comment in comments:
            if not isinstance(comment, dict):
                continue

            comment_type = comment.get("@type")
            if not comment_type:
                continue

            # Route to specific handlers
            if comment_type == "function":
                if text := self._get_comment_text(comment):
                    result["function"].append(text)
            elif comment_type == "subunit":
                if text := self._get_comment_text(comment):
                    result["subunit"].append(text)
            elif comment_type == "subcellular location":
                self._process_subcellular_location(
                    comment, result["subcellular_location"]
                )
            elif comment_type == "tissue specificity":
                if text := self._get_comment_text(comment):
                    result["tissue_specificity"].append(text)
            elif comment_type == "domain":
                if text := self._get_comment_text(comment):
                    result["domain"].append(text)
            elif comment_type == "ptm":
                if text := self._get_comment_text(comment):
                    result["ptm"].append(text)
            elif comment_type == "similarity":
                if text := self._get_comment_text(comment):
                    result["similarity"].append(text)
            elif comment_type == "mass spectrometry":
                if text := self._get_comment_text(comment):
                    result["mass_spectrometry"].append(text)
            elif comment_type == "polymorphism":
                if text := self._get_comment_text(comment):
                    result["polymorphism"].append(text)
            elif comment_type == "pharmaceutical":
                if text := self._get_comment_text(comment):
                    result["pharmaceutical"].append(text)
            elif comment_type == "biotechnology":
                if text := self._get_comment_text(comment):
                    result["biotechnology"].append(text)
            elif comment_type == "disruption phenotype":
                if text := self._get_comment_text(comment):
                    result["disruption_phenotype"].append(text)
            elif comment_type == "disease":
                self._process_disease(comment, result["disease"])
            elif comment_type == "interaction":
                self._process_interaction(comment, result["interaction"])
            elif comment_type == "alternative products":
                self._process_isoforms(comment, isoform_notes)

        # Convert isoform notes to dicts
        result["isoform_notes"] = [
            {"isoform_id": note.isoform_id, "note": note.note} for note in isoform_notes
        ]

        return result

    def _get_comment_text(self, comment: dict[str, Any]) -> str | None:
        """Extract text from a comment."""
        return self._clean_text(comment.get("text"))

    def _process_subcellular_location(
        self, comment: dict[str, Any], locations: list[dict[str, Any]]
    ) -> None:
        """Process subcellular location comments."""
        if not (subcell := comment.get("subcellularLocation")):
            return

        # Handle list
        if isinstance(subcell, dict):
            subcell = [subcell]

        for loc_entry in subcell:
            if not isinstance(loc_entry, dict):
                continue

            # Extract distinct parts
            locs = []
            topology = []
            orientation = []

            if l := loc_entry.get("location"):
                if isinstance(l, list):
                    locs.extend([self._clean_text(x) for x in l if isinstance(x, str)])
                    # If dict with #text
                    locs.extend(
                        [
                            self._clean_text(x.get("#text"))
                            for x in l
                            if isinstance(x, dict)
                        ]
                    )
                elif isinstance(l, str):
                    if cleaned := self._clean_text(l):
                        locs.append(cleaned)
                elif isinstance(l, dict):
                    if cleaned := self._clean_text(l.get("#text")):
                        locs.append(cleaned)

            if t := loc_entry.get("topology"):
                if isinstance(t, str):
                    if cleaned := self._clean_text(t):
                        topology.append(cleaned)
                elif isinstance(t, dict):
                    if cleaned := self._clean_text(t.get("#text")):
                        topology.append(cleaned)

            if o := loc_entry.get("orientation"):
                if isinstance(o, str):
                    if cleaned := self._clean_text(o):
                        orientation.append(cleaned)
                elif isinstance(o, dict):
                    if cleaned := self._clean_text(o.get("#text")):
                        orientation.append(cleaned)

            locations.append(
                {
                    "location": locs,
                    "topology": topology,
                    "orientation": orientation,
                    "note": self._clean_text(comment.get("text")),
                }
            )

    def _process_disease(
        self, comment: dict[str, Any], diseases: list[dict[str, Any]]
    ) -> None:
        """Process disease comments."""
        disease_id = comment.get("@id")
        acronym = comment.get("acronym")
        description = comment.get("text")

        # Sometimes disease info is in a 'disease' sub-element
        if dis_tag := comment.get("disease"):
            if isinstance(dis_tag, dict):
                disease_id = disease_id or dis_tag.get("@id")
                acronym = acronym or dis_tag.get("acronym")
                if not description:
                    description = dis_tag.get("description")
                if not description and dis_tag.get("name"):
                    description = dis_tag.get("name")

        if description or disease_id:
            diseases.append(
                {
                    "id": disease_id,
                    "acronym": acronym,
                    "description": self._clean_text(description),
                    "evidence": ExtractorUtils.extract_evidence(comment),
                }
            )

    def _process_interaction(
        self, comment: dict[str, Any], interactions: list[dict[str, Any]]
    ) -> None:
        """Process interaction comments."""
        if interactant := comment.get("interactant"):
            # This is complex in XML, often multiple interactants
            # Simplifying for this implementation
            if isinstance(interactant, list):
                for i in interactant:
                    if label := i.get("label"):
                        interactions.append({"interactant": label, "id": i.get("id")})
            elif isinstance(interactant, dict):
                if label := interactant.get("label"):
                    interactions.append(
                        {"interactant": label, "id": interactant.get("id")}
                    )

    def _process_isoforms(
        self, comment: dict[str, Any], isoform_notes: list[IsoformNote]
    ) -> None:
        """Process isoform-specific notes."""
        if not (molecule := comment.get("molecule")):
            return

        # Handle both single molecule (dict) and list of molecules
        molecules = molecule if isinstance(molecule, list) else [molecule]
        note = comment.get("text", "")

        if not note:
            return

        # Process each molecule entry
        for mol in molecules:
            self._process_single_molecule(mol, note, isoform_notes)

    def _process_single_molecule(
        self, mol: dict[str, Any], note: str, isoform_notes: list[IsoformNote]
    ) -> None:
        """Process a single molecule entry for isoform notes."""
        iso_ids = self._extract_isoform_ids(mol)

        # If we found isoform IDs, associate the note with each one
        for iso_id in iso_ids:
            # Use the helper to process the note
            # This handles cleaning and duplicate checking
            ExtractorUtils.process_single_isoform_note(iso_id, note, isoform_notes)

    def _extract_isoform_ids(self, mol: dict[str, Any]) -> list[str]:
        """Extract isoform IDs from a molecule entry."""
        iso_ids = []
        if identifiers := mol.get("identifier"):
            # Handle single identifier vs list
            if isinstance(identifiers, list):
                for ident in identifiers:
                    if isinstance(ident, dict):
                        if id_val := ident.get("#text"):
                            iso_ids.append(id_val)
                    elif isinstance(ident, str):
                        iso_ids.append(ident)
            elif isinstance(identifiers, dict):
                if id_val := identifiers.get("#text"):
                    iso_ids.append(id_val)
            elif isinstance(identifiers, str):
                iso_ids.append(identifiers)
        return iso_ids

    def _clean_text(self, text: str | None) -> str | None:
        """Clean text by stripping whitespace and removing trailing periods."""
        return ExtractorUtils.clean_text(text)
