"""Resolve channel conflicts and infer effective classes from EC categories."""

from __future__ import annotations

import re
from dataclasses import replace
from typing import cast

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
_TRANSCRIPTION_FACTOR = re.compile(r"\btranscription[\s-]+factors?\b", re.IGNORECASE)
_TRANSCRIPTION_FACTOR_RELATED = re.compile(
    r"\b(?:binding|interacting|associated|inhibitors?|activators?|regulators?|"
    r"substrates?|proteases?|peptidases?|subunits?|polypeptides?|cofactors?|coactivators?|corepressors?)\b",
    re.IGNORECASE,
)
_FUNCTIONAL_PARTNER_PREFIX = re.compile(
    r"\b(?:(?:inhibitor|blocker|activator|agonist|antagonist|ligand|regulator|substrate|"
    r"partner|subunit|protease|peptidase|cofactor|coactivator|corepressor)s?"
    r"\s+(?:of|for)|(?:binding|bound)\s+to|(?:interacting|associated)\s+with)"
    r"\s+(?:[\w-]+\s+)*$",
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
    if (
        ION_CHANNEL not in confirmed
        or not any(
            label == "Enzyme" or (label or "").startswith("Enzyme.")
            for label in confirmed
        )
        or outcome.effective_class == ION_CHANNEL
    ):
        return outcome
    return cast(
        Resolution,
        replace(
            outcome,
            effective_class=ION_CHANNEL,
            effective_source="channel_priority",
            effective_subclasses=(),
            rule_id=CHANNEL_PRIORITY_RULE,
        ),
    )


def _assigned_name_term(name: str, expression: re.Pattern[str]) -> str | None:
    """Ignore terms that name a functional partner rather than the target."""
    for hit in expression.finditer(name):
        if not _FUNCTIONAL_PARTNER_PREFIX.search(name[: hit.start()]):
            return hit.group().lower()
    return None


def name_keyword_class(
    name: str | None, *, allow_transcription_factor: bool = False
) -> tuple[str, str] | None:
    """Use standalone functional terms in the target name as local evidence."""
    matches = {
        label: term
        for label, expression in _ASSIGNED_NAME_WORDS.items()
        if (term := _assigned_name_term(name or "", expression)) is not None
    }
    if ION_CHANNEL in matches and all(
        label == ION_CHANNEL or label.startswith("Enzyme.") for label in matches
    ):
        return ION_CHANNEL, matches[ION_CHANNEL]
    if not matches and allow_transcription_factor and name:
        hit = _TRANSCRIPTION_FACTOR.search(name)
        if (
            hit
            and not _FUNCTIONAL_PARTNER_PREFIX.search(name[: hit.start()])
            and not _TRANSCRIPTION_FACTOR_RELATED.search(name[hit.end() :])
        ):
            return TRANSCRIPTION_FACTOR_CLASS, hit.group().lower()
    return next(iter(matches.items())) if len(matches) == 1 else None


def select_ec_class(outcome: Resolution, categories: frozenset[int]) -> Resolution:
    label = "Multitarget" if len(categories) > 1 else _EC_LABELS[next(iter(categories))]
    return _select_local_class(outcome, f"Enzyme.{label}", "ec_rule", EC_CLASS_RULE)


def select_keyword_class(outcome: Resolution, label: str) -> Resolution:
    return _select_local_class(outcome, label, "keyword_rule", KEYWORD_CLASS_RULE)


def _select_local_class(
    outcome: Resolution, label: str, source: str, rule: str
) -> Resolution:
    return cast(
        Resolution,
        replace(
            outcome,
            effective_class=label,
            effective_source=source,
            effective_subclasses=(),
            decision_status=(
                "resolved"
                if outcome.decision_status == "unresolved"
                else outcome.decision_status
            ),
            rule_id=rule,
        ),
    )
