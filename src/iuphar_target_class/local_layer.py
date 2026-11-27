"""Local layer. It does not write IUPHAR fields and does not call the network."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass

from .models import Diagnostic, EcNumber, LocalInference
from .normalization import normalize_missing
from .policy import (
    CLASS_PRIORITY,
    EXCLUDED_NHR_KEYWORDS,
    WORKING_CLASSES,
    RuleRecord,
    validate_rules,
)

_FORBIDDEN_TEXT = ("kinase", "channel", "zinc finger", "transcription factor")
_EXCLUDED_NHR_TEXT = ("zinc finger", "transcription factor", "nuclear hormone receptor")
_INDEPENDENT_RULE = "predicted-l1-l2-independent"
_DERIVED_RULE = "predicted-l1-l2-iuphar-derived"
_UNKNOWN_RULE = "predicted-l1-l2-unknown"
_L1_L2_FAMILY = "l1_l2"
_INDEPENDENT_OUTPUT = "predicted working class"
_DERIVED_OUTPUT = "dependent_not_confirmation"
_UNKNOWN_OUTPUT = "candidate_only"
_PROVENANCE_TOKEN = re.compile(r"[A-Za-z0-9_.:-]{1,128}\Z")


@dataclass(frozen=True, slots=True)
class Prediction:
    """One predicted label. Unknown provenance cannot support a class."""

    layer: str
    predicted_class: str | None
    provenance_known: bool
    derived_from_iuphar: bool
    evidence_id: str


@dataclass(frozen=True, slots=True)
class _Support:
    class_name: str
    rule_id: str
    evidence_id: str
    priority: int


@dataclass(frozen=True, slots=True)
class EcInference:
    """EC categories. Names are IUBMB categories, not IUPHAR classes."""

    numbers: tuple[EcNumber, ...]
    ec_categories: tuple[str, ...]
    confirmed_levels: tuple[str, ...]
    multiple_ec_categories: bool
    diagnostics: tuple[Diagnostic, ...]
    support: tuple[_Support, ...]
    observations: tuple[tuple[str, str], ...] = ()


def validate_local_config(rules: tuple[RuleRecord, ...]) -> None:
    """Reject a broken rule before any row is processed."""
    validate_rules(rules)
    for rule in rules:
        if (
            rule.family in {"ec_class", "annotation"}
            and rule.output not in WORKING_CLASSES
        ):
            message = f"rule {rule.rule_id} output is outside the class dictionary"
            raise ValueError(message)


def infer_from_ec(
    numbers: tuple[EcNumber, ...],
    rules: tuple[RuleRecord, ...],
    *,
    organism: str | None = None,
) -> EcInference:
    """Keep every confirmed EC level. Category 7 stays Translocases."""
    validate_local_config(rules)
    diagnostics: list[Diagnostic] = []
    if organism is not None:
        diagnostics.append(
            Diagnostic(
                "organism_not_a_class_filter",
                "info",
                "organism does not add or remove an EC category",
            )
        )
    names: dict[int, str] = {}
    levels: set[str] = set()
    support: list[_Support] = []
    observations: list[tuple[str, str]] = []
    for number in numbers:
        if normalize_missing(number.raw) is None:
            continue
        if not number.valid or number.depth is None or not number.confirmed_levels:
            diagnostics.append(
                Diagnostic(
                    "invalid_ec",
                    "warning",
                    number.diagnostic or "EC is invalid",
                    evidence_id=f"ec:{number.raw}",
                )
            )
            continue
        top = int(number.confirmed_levels[0])
        if number.category_name:
            names[top] = number.category_name
        levels.update(number.confirmed_levels)
        support.extend(_ec_class_support(top, rules, number.raw))
        observations.extend(_ec_observations(top, rules, number.raw))
    categories = tuple(names[key] for key in sorted(names))
    return EcInference(
        numbers=numbers,
        ec_categories=categories,
        confirmed_levels=tuple(sorted(levels, key=_level_key)),
        multiple_ec_categories=len(names) > 1,
        diagnostics=tuple(diagnostics),
        support=tuple(support),
        observations=tuple(observations),
    )


def infer_from_annotations(
    keyword_ids: tuple[str, ...],
    free_text: str | None,
    rules: tuple[RuleRecord, ...],
) -> tuple[tuple[_Support, ...], tuple[str, ...], tuple[Diagnostic, ...]]:
    """Exact keyword ids can support a class. Free text never does."""
    validate_local_config(rules)
    present_ids = tuple(
        keyword_id
        for keyword_id in keyword_ids
        if normalize_missing(keyword_id) is not None
    )
    support = [
        _Support(rule.output, rule.rule_id, f"keyword:{keyword_id}", rule.priority)
        for keyword_id in present_ids
        for rule in rules
        if rule.family == "annotation"
        and rule.input_conditions == f"keyword_id={keyword_id}"
    ]
    candidates: list[str] = []
    diagnostics: list[Diagnostic] = []
    if any(keyword_id in EXCLUDED_NHR_KEYWORDS for keyword_id in present_ids):
        diagnostics.append(
            Diagnostic(
                "broad_nhr_rule_excluded",
                "info",
                "transcription factor and zinc finger keywords do not assign "
                "nuclear hormone receptor",
            )
        )
    if free_text:
        candidates.append("free_text")
        diagnostics.append(
            Diagnostic(
                "free_text_manual_review",
                "info",
                "free text is a manual-review candidate",
            )
        )
        folded = free_text.casefold()
        if any(token in folded for token in _FORBIDDEN_TEXT):
            diagnostics.append(
                Diagnostic(
                    "free_text_substring_ignored",
                    "info",
                    "kinase, channel, zinc finger, and transcription factor "
                    "do not assign a class",
                )
            )
        if any(token in folded for token in _EXCLUDED_NHR_TEXT):
            diagnostics.append(
                Diagnostic(
                    "broad_nhr_rule_excluded",
                    "info",
                    "free text does not assign nuclear hormone receptor",
                )
            )
    return tuple(support), tuple(candidates), tuple(diagnostics)


def collect_prediction_candidates(
    predictions: tuple[Prediction, ...],
    rules: tuple[RuleRecord, ...] = (),
) -> tuple[
    tuple[_Support, ...],
    tuple[str, ...],
    tuple[Diagnostic, ...],
    tuple[tuple[str, str], ...],
]:
    """Predictions cannot supply the explicit rule for Other Protein Target."""
    support: list[_Support] = []
    candidates: list[str] = []
    diagnostics: list[Diagnostic] = []
    observations: list[tuple[str, str]] = []
    for prediction in predictions:
        if prediction.derived_from_iuphar:
            diagnostics.append(
                Diagnostic(
                    "dependent_prediction",
                    "warning",
                    f"{prediction.layer} is derived from the IUPHAR result",
                    evidence_id=prediction.evidence_id,
                )
            )
            observations.extend(
                _named_observations(
                    rules,
                    _DERIVED_RULE,
                    prediction.evidence_id,
                    family=_L1_L2_FAMILY,
                    output=_DERIVED_OUTPUT,
                )
            )
            continue
        if not prediction.provenance_known:
            candidates.append("candidate_only")
            diagnostics.append(
                Diagnostic(
                    "candidate_only",
                    "warning",
                    f"{prediction.layer} provenance is unknown",
                    evidence_id=prediction.evidence_id,
                )
            )
            observations.extend(
                _named_observations(
                    rules,
                    _UNKNOWN_RULE,
                    prediction.evidence_id,
                    family=_L1_L2_FAMILY,
                    output=_UNKNOWN_OUTPUT,
                )
            )
            continue
        if prediction.predicted_class == "Other Protein Target":
            candidates.append("candidate_only")
            diagnostics.append(
                Diagnostic(
                    "prediction_requires_explicit_rule",
                    "info",
                    "Other Protein Target prediction stays candidate-only; "
                    "a matching explicit local rule must supply support",
                    evidence_id=prediction.evidence_id,
                )
            )
            continue
        if prediction.predicted_class in WORKING_CLASSES:
            matched = _matching_rule(
                rules,
                _INDEPENDENT_RULE,
                family=_L1_L2_FAMILY,
                output=_INDEPENDENT_OUTPUT,
            )
            priority = matched.priority if matched is not None else CLASS_PRIORITY
            support.append(
                _Support(
                    str(prediction.predicted_class),
                    f"prediction:{prediction.layer}",
                    prediction.evidence_id,
                    priority,
                )
            )
            if matched is not None:
                support.append(
                    _Support(
                        str(prediction.predicted_class),
                        matched.rule_id,
                        prediction.evidence_id,
                        matched.priority,
                    )
                )
    return tuple(support), tuple(candidates), tuple(diagnostics), tuple(observations)


def apply_local(
    numbers: tuple[EcNumber, ...],
    *,
    rules: tuple[RuleRecord, ...],
    keyword_ids: tuple[str, ...] = (),
    free_text: str | None = None,
    organism: str | None = None,
    predictions: tuple[Prediction, ...] = (),
    subclass_of: Mapping[str, str] | None = None,
) -> LocalInference:
    """Combine local evidence. Conflicting supported classes stay unresolved.

    This returns the classification summary, not the complete EC projection.
    ``infer_from_ec`` retains the original numbers and confirmed levels for
    callers that need that projection; pipeline persistence is a separate step.
    """
    _reject_unknown_subclass_parents(subclass_of or {})
    validate_local_config(rules)
    ec = infer_from_ec(numbers, rules, organism=organism)
    keywords, text_candidates, text_diagnostics = infer_from_annotations(
        keyword_ids,
        free_text,
        rules,
    )
    predicted, prediction_candidates, prediction_diagnostics, prediction_notes = (
        collect_prediction_candidates(predictions, rules)
    )
    support = ec.support + keywords + predicted
    return _assemble(
        ec,
        support,
        text_candidates + prediction_candidates,
        ec.diagnostics + text_diagnostics + prediction_diagnostics,
        subclass_of or {},
        ec.observations + prediction_notes,
    )


def _ec_class_support(
    category: int, rules: tuple[RuleRecord, ...], raw: str
) -> tuple[_Support, ...]:
    wanted = f"ec_category={category}"
    return tuple(
        _Support(rule.output, rule.rule_id, f"ec:{raw}", rule.priority)
        for rule in rules
        if rule.family == "ec_class" and rule.input_conditions == wanted
    )


def _ec_observations(
    category: int, rules: tuple[RuleRecord, ...], raw: str
) -> tuple[tuple[str, str], ...]:
    wanted = f"ec_category={category}"
    return tuple(
        (rule.rule_id, f"ec:{raw}")
        for rule in rules
        if rule.family == "ec" and rule.input_conditions == wanted
    )


def _assemble(
    ec: EcInference,
    support: tuple[_Support, ...],
    candidates: tuple[str, ...],
    diagnostics: tuple[Diagnostic, ...],
    subclass_of: Mapping[str, str],
    observations: tuple[tuple[str, str], ...] = (),
) -> LocalInference:
    resolved, competing = _resolved_class(support, subclass_of)
    noted = list(diagnostics)
    status = "not_supported"
    local_class: str | None = None
    extra: tuple[str, ...] = ()
    if resolved is not None:
        status = "supported"
        local_class = resolved
        extra = competing
        if competing:
            noted.append(
                Diagnostic(
                    "priority_selected",
                    "info",
                    f"{resolved} is the only top-priority class",
                )
            )
    elif competing:
        status = "conflicting"
        extra = competing
    rule_ids = {item.rule_id for item in support} | {
        rule_id for rule_id, _evidence_id in observations
    }
    evidence_ids = {item.evidence_id for item in support} | {
        evidence_id for _rule_id, evidence_id in observations
    }
    return LocalInference(
        local_status=status,
        local_class=local_class,
        local_subclasses=(),
        local_rule_ids=tuple(sorted(rule_ids)),
        local_evidence_ids=tuple(sorted(evidence_ids)),
        ec_categories=ec.ec_categories,
        multiple_ec_categories=ec.multiple_ec_categories,
        local_candidates=tuple(sorted(set(candidates) | set(extra))),
        diagnostics=tuple(
            sorted(
                noted,
                key=lambda item: (
                    item.code,
                    item.level,
                    item.message,
                    item.evidence_id or "",
                ),
            )
        ),
        local_rules_by_evidence=_rules_by_evidence(support, observations),
        supported_evidence_ids=tuple(sorted({item.evidence_id for item in support})),
    )


def _rules_by_evidence(
    support: tuple[_Support, ...],
    observations: tuple[tuple[str, str], ...],
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Keep each witness bound to the rules that actually fired for it."""
    grouped: dict[str, set[str]] = {}
    for item in support:
        grouped.setdefault(item.evidence_id, set()).add(item.rule_id)
    for rule_id, evidence_id in observations:
        grouped.setdefault(evidence_id, set()).add(rule_id)
    return tuple(
        (evidence_id, tuple(sorted(grouped[evidence_id])))
        for evidence_id in sorted(grouped)
    )


def _reject_unknown_subclass_parents(subclass_of: Mapping[str, str]) -> None:
    """A hierarchy parent must be a working class. Evidence is not consulted."""
    for name, parent in subclass_of.items():
        if parent not in WORKING_CLASSES:
            message = f"subclass parent {parent} is outside the class dictionary"
            raise ValueError(message)
        if name in WORKING_CLASSES and name != parent:
            message = f"working class {name} cannot be reparented to {parent}"
            raise ValueError(message)


def _resolved_class(
    support: tuple[_Support, ...], subclass_of: Mapping[str, str]
) -> tuple[str | None, tuple[str, ...]]:
    """Pick a class only when one parent has the strictly highest priority.

    Equal top priorities stay unresolved. Input order is not a tie-break.
    """
    scores: dict[str, int] = {}
    for item in support:
        parent = subclass_of.get(item.class_name, item.class_name)
        previous = scores.get(parent)
        scores[parent] = (
            item.priority if previous is None else max(previous, item.priority)
        )
    if not scores:
        return None, ()
    top = max(scores.values())
    winners = tuple(sorted(name for name, score in scores.items() if score == top))
    if len(winners) == 1:
        superseded = tuple(sorted(name for name in scores if name != winners[0]))
        return winners[0], superseded
    return None, winners


def _level_key(level: str) -> tuple[int, ...]:
    return tuple(int(part) for part in level.split("."))


def _named_observations(
    rules: tuple[RuleRecord, ...],
    rule_id: str,
    evidence_id: str,
    *,
    family: str,
    output: str,
) -> tuple[tuple[str, str], ...]:
    matched = _matching_rule(rules, rule_id, family=family, output=output)
    if matched is None:
        return ()
    return ((matched.rule_id, evidence_id),)


def _matching_rule(
    rules: tuple[RuleRecord, ...],
    rule_id: str,
    *,
    family: str,
    output: str,
) -> RuleRecord | None:
    """Bind a catalog id only when family and outcome also match."""
    for rule in rules:
        if rule.rule_id == rule_id and rule.family == family and rule.output == output:
            return rule
    return None


def predictions_from_row(
    *,
    predicted_l1: str | None,
    predicted_l2: str | None,
    raw_fields: Mapping[str, str | None],
) -> tuple[Prediction, ...]:
    """Read L1/L2 provenance from evidence fields. Missing evidence is not True."""
    predictions: list[Prediction] = []
    for layer, value in (("L1", predicted_l1), ("L2", predicted_l2)):
        if value is None:
            continue
        predictions.append(_prediction_from_evidence(layer, value, raw_fields))
    return tuple(predictions)


def _prediction_from_evidence(
    layer: str, value: str, raw_fields: Mapping[str, str | None]
) -> Prediction:
    prefix = "predicted_" + layer.casefold()
    provenance = _provenance_token(raw_fields.get(prefix + "_provenance"))
    relation = normalize_missing(raw_fields.get(prefix + "_relation"))
    evidence_id = f"{layer}:{provenance}" if provenance else layer
    if relation == "iuphar":
        return Prediction(layer, value, provenance is not None, True, evidence_id)
    if provenance and relation == "independent":
        return Prediction(layer, value, True, False, evidence_id)
    return Prediction(layer, value, False, False, evidence_id)


def _provenance_token(value: str | None) -> str | None:
    text = normalize_missing(value)
    if text is None or _PROVENANCE_TOKEN.fullmatch(text) is None:
        return None
    return text
