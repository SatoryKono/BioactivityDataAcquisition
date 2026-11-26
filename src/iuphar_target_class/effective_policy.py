"""Resolve channel conflicts and infer effective classes from EC categories."""

from __future__ import annotations

import re

from .models import EcNumber
from .policy import EC_SINGULAR
from .resolution import Resolution

ION_CHANNEL = "Ion Channel"
TRANSCRIPTION_FACTOR_CLASS = "Receptor.Nuclear receptor"
CHANNEL_PRIORITY_RULE = "ion_channel_over_enzyme"
EC_CLASS_RULE = "ec_effective_class"
KEYWORD_CLASS_RULE = "name_keyword_effective_class"

_NAME_KEYWORDS = {
    ION_CHANNEL: r"channels?|chanels?",
    "Receptor": r"receptors?",
    "Transporter": r"transporters?",
    "Enzyme.Transferase": r"kinases?|elongases?|transferases?",
    "Enzyme.Oxidoreductase": r"oxidases?|dehydrogenases?|reductases?|oxidoreductases?",
    "Enzyme.Hydrolase": r"hydrolases?|phosphatases?|proteases?|peptidases?|esterases?|nucleases?",
    "Enzyme.Lyase": r"lyases?",
    "Enzyme.Isomerase": r"isomerases?|racemases?|epimerases?",
    "Enzyme.Ligase": r"ligases?",
    "Enzyme.Translocase": r"translocases?",
}
_ASSIGNED_NAME_WORDS = {
    label: re.compile(
        rf"\b(?:{pattern})\b(?![\s-]+(?:inhibitors?|blockers?|activators?|agonists?|"
        r"antagonists?|ligands?|binding|associated|interacting|regulators?|substrates?)\b)",
        re.IGNORECASE,
    )
    for label, pattern in _NAME_KEYWORDS.items()
}
_EC_LABELS = dict(EC_SINGULAR)
_FUNCTIONAL_RELATION = re.compile(
    r"\b(?:inhibitors?|blockers?|activators?|agonists?|antagonists?|ligands?|"
    r"binding|associated|interacting|regulators?|substrates?)\b",
    re.IGNORECASE,
)
_FUNCTIONAL_RELATION_PREFIX = re.compile(
    r"\b(?:(?:inhibitor|blocker|activator|agonist|antagonist|ligand|regulator|substrate|"
    r"partner|subunit|protease|peptidase|cofactor|coactivator|corepressor)s?"
    r"[\s-]+(?:of|for)|(?:binding|bound)[\s-]+to|"
    r"(?:interacting|associated)[\s-]+with)\b[^,;()]*$",
    re.IGNORECASE,
)
_TRANSCRIPTION_FACTOR = re.compile(r"\btranscription[\s-]+factors?\b", re.IGNORECASE)
_TRANSCRIPTION_FACTOR_RELATED = re.compile(
    r"\b(?:binding|interacting|associated|inhibitors?|activators?|regulators?|"
    r"substrates?|proteases?|peptidases?|subunits?|polypeptides?|cofactors?|coactivators?|corepressors?)\b",
    re.IGNORECASE,
)


def ec_categories(numbers: tuple[EcNumber, ...]) -> frozenset[int]:
    """Use the confirmed top level, including for partial EC codes."""
    return frozenset(int(item.confirmed_levels[0]) for item in numbers if item.valid)


def select_channel_priority(outcome: Resolution) -> Resolution:
    confirmed = {
        outcome.iuphar_class,
        outcome.local_class,
        *outcome.iuphar_class_candidates,
    }
    enzyme_classes = {
        label
        for label in confirmed
        if label == "Enzyme" or (label or "").startswith("Enzyme.")
    }
    if (
        ION_CHANNEL not in confirmed
        or not enzyme_classes
        or not confirmed.issubset({ION_CHANNEL, None, *enzyme_classes})
        or outcome.effective_class == ION_CHANNEL
    ):
        return outcome
    return _with_effective_class(
        outcome,
        ION_CHANNEL,
        "channel_priority",
        CHANNEL_PRIORITY_RULE,
        decision_status=outcome.decision_status,
    )


def name_keyword_class(
    name: str | None, *, allow_transcription_factor: bool = False
) -> tuple[str, str] | None:
    """Use standalone functional terms in the target name as local evidence."""
    matches = {
        label: hit.group().lower()
        for label, expression in _ASSIGNED_NAME_WORDS.items()
        if (hit := _functional_name_hit(name or "", expression)) is not None
    }
    if ION_CHANNEL in matches and all(
        label == ION_CHANNEL or label.startswith("Enzyme.") for label in matches
    ):
        return ION_CHANNEL, matches[ION_CHANNEL]
    if not matches and allow_transcription_factor and name:
        hit = _TRANSCRIPTION_FACTOR.search(name)
        if (
            hit
            and not _FUNCTIONAL_RELATION_PREFIX.search(name[: hit.start()])
            and not _TRANSCRIPTION_FACTOR_RELATED.search(name[hit.end() :])
        ):
            return TRANSCRIPTION_FACTOR_CLASS, hit.group().lower()
    return next(iter(matches.items())) if len(matches) == 1 else None


def _functional_name_hit(
    name: str, expression: re.Pattern[str]
) -> re.Match[str] | None:
    """Keep binding qualifiers before a term, but reject relations to that term."""
    return next(
        (
            hit
            for hit in expression.finditer(name)
            if not _FUNCTIONAL_RELATION_PREFIX.search(name[: hit.start()])
            and not _FUNCTIONAL_RELATION.search(name[hit.end() :])
        ),
        None,
    )


def select_ec_class(outcome: Resolution, categories: frozenset[int]) -> Resolution:
    label = "Multitarget" if len(categories) > 1 else _EC_LABELS[next(iter(categories))]
    return _select_local_class(outcome, f"Enzyme.{label}", "ec_rule", EC_CLASS_RULE)


def select_keyword_class(outcome: Resolution, label: str) -> Resolution:
    return _select_local_class(outcome, label, "keyword_rule", KEYWORD_CLASS_RULE)


def _select_local_class(
    outcome: Resolution, label: str, source: str, rule: str
) -> Resolution:
    return _with_effective_class(
        outcome,
        label,
        source,
        rule,
        decision_status=(
            "resolved"
            if outcome.decision_status == "unresolved"
            else outcome.decision_status
        ),
    )


def _with_effective_class(
    outcome: Resolution, label: str, source: str, rule: str, *, decision_status: str
) -> Resolution:
    """Retain provider evidence and conflicts when selecting a local class."""
    return Resolution(
        effective_class=label,
        effective_source=source,
        effective_subclasses=(),
        decision_status=decision_status,
        rule_id=rule,
        conflict_codes=outcome.conflict_codes,
        run_incomplete=outcome.run_incomplete,
        iuphar_class=outcome.iuphar_class,
        iuphar_subclass=outcome.iuphar_subclass,
        local_class=outcome.local_class,
        local_subclasses=outcome.local_subclasses,
        iuphar_class_candidates=outcome.iuphar_class_candidates,
        local_candidates=outcome.local_candidates,
        evidence_ids=outcome.evidence_ids,
        raw_type=outcome.raw_type,
        matched_target_id=outcome.matched_target_id,
        candidate_target_ids=outcome.candidate_target_ids,
        component_results=outcome.component_results,
        partial_basis=outcome.partial_basis,
    )
