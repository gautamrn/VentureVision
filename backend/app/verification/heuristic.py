"""Model-free claim verifier: the eval baseline that every LLM verdict has to beat.

Word overlap decides whether the evidence is about the claim at all; numbers of the same
kind (percent, money, plain count) and direction words decide support versus contradiction.
"""

import re
from dataclasses import dataclass
from typing import Literal

from app.schemas.evals import EvidenceSnippet, Prediction
from app.verification.grounding import normalizeText

MIN_TOPIC_OVERLAP = 0.34
MIN_SUPPORT_OVERLAP = 0.5
NUMBER_TOLERANCE = 0.15

STOPWORDS = frozenset(
    """a an and are as at be been by for from has have in is it its of on or our that the their
    this to was were will with we you your per about around roughly approximately over under more
    than less fewer at least most only up into while which who what when where how all any each
    already today they them those these there here it's than then so such also very""".split()
)
NEGATIONS = frozenset({"no", "not", "never", "none", "nobody", "neither", "without"})
OPPOSITE_DIRECTIONS = (
    (
        frozenset({"shrink", "decline", "decrease", "fall", "contract", "drop"}),
        frozenset({"grow", "growth", "increase", "rise", "reach", "expand", "cagr"}),
    ),
    (frozenset({"smallest", "lowest", "least"}), frozenset({"largest", "highest", "biggest"})),
    (frozenset({"cheaper", "lower"}), frozenset({"pricier", "costlier", "higher"})),
)

NumberKind = Literal["percent", "money", "count"]
Comparator = Literal["approx", "atLeast", "atMost"]

_SCALE = {"billion": 1e9, "bn": 1e9, "b": 1e9, "million": 1e6, "mn": 1e6, "m": 1e6, "thousand": 1e3, "k": 1e3}
_NUMBER = re.compile(
    r"(?P<currency>\$|usd\s?)?(?P<value>\d+(?:,\d{3})*(?:\.\d+)?)\s?"
    r"(?P<unit>%|percent\b|billion\b|bn\b|b\b|million\b|mn\b|m\b|thousand\b|k\b)?",
    re.IGNORECASE,
)
_AT_LEAST = re.compile(r"(over|more than|at least|above|exceeds?|upwards of)\s*$")
_AT_MOST = re.compile(r"(under|less than|below|at most|fewer than|only|up to)\s*$")
_WORD = re.compile(r"[a-z][a-z'-]*")


@dataclass(frozen=True)
class Quantity:
    value: float
    kind: NumberKind
    comparator: Comparator


def stem(word: str) -> str:
    word = word.strip("'-").removesuffix("'s")
    for suffix, replacement in (("ies", "y"), ("ing", ""), ("ed", ""), ("es", ""), ("s", "")):
        if len(word) > len(suffix) + 3 and word.endswith(suffix) and not word.endswith("ss"):
            return word[: -len(suffix)] + replacement
    return word


def contentWords(text: str) -> set[str]:
    return {stem(w) for w in _WORD.findall(normalizeText(text)) if w not in STOPWORDS and len(w) > 1}


def quantities(text: str) -> list[Quantity]:
    normalized = normalizeText(text)
    found: list[Quantity] = []
    for match in _NUMBER.finditer(normalized):
        raw = match.group("value").replace(",", "")
        value = float(raw)
        unit = (match.group("unit") or "").lower()
        currency = match.group("currency") is not None
        if not currency and not unit and "." not in raw and 1900 <= value <= 2100:
            continue  # a year, not a quantity
        if unit in ("%", "percent"):
            kind: NumberKind = "percent"
        else:
            value *= _SCALE.get(unit, 1)
            kind = "money" if currency else "count"
        before = normalized[max(0, match.start() - 14) : match.start()]
        comparator: Comparator = "atLeast" if _AT_LEAST.search(before) else "atMost" if _AT_MOST.search(before) else "approx"
        found.append(Quantity(value=value, kind=kind, comparator=comparator))
    return found


def _matches(claimed: Quantity, observed: float) -> bool:
    if claimed.comparator == "atLeast":
        return observed >= claimed.value * (1 - NUMBER_TOLERANCE / 5)
    if claimed.comparator == "atMost":
        return observed <= claimed.value * (1 + NUMBER_TOLERANCE / 5)
    return abs(observed - claimed.value) <= NUMBER_TOLERANCE * max(abs(observed), abs(claimed.value))


def numericAgreement(claim: str, evidence: str) -> Literal["consistent", "conflict", "none"]:
    observed = quantities(evidence)
    compared = [q for q in quantities(claim) if any(o.kind == q.kind for o in observed)]
    if not compared:
        return "none"
    for claimed in compared:
        if not any(o.kind == claimed.kind and _matches(claimed, o.value) for o in observed):
            return "conflict"
    return "consistent"


def directionConflict(claim: str, evidence: str) -> str | None:
    claimWords = {stem(w) for w in _WORD.findall(normalizeText(claim))}
    evidenceWords = {stem(w) for w in _WORD.findall(normalizeText(evidence))}
    negated = (claimWords & NEGATIONS) - evidenceWords
    if negated:
        return f"claim negates ('{sorted(negated)[0]}') what the evidence asserts"
    for left, right in OPPOSITE_DIRECTIONS:
        for mine, theirs in ((left, right), (right, left)):
            stemmedMine = {stem(w) for w in mine}
            stemmedTheirs = {stem(w) for w in theirs}
            if claimWords & stemmedMine and evidenceWords & stemmedTheirs and not evidenceWords & stemmedMine:
                return f"claim says '{sorted(claimWords & stemmedMine)[0]}', evidence says '{sorted(evidenceWords & stemmedTheirs)[0]}'"
    return None


def classifyClaim(claim: str, evidence: list[EvidenceSnippet]) -> Prediction:
    if not evidence:
        return Prediction(label="unsupported", detail="no evidence")

    claimWords = contentWords(claim)
    if not claimWords:
        return Prediction(label="unsupported", detail="claim has no content words")

    def overlapWith(item: EvidenceSnippet) -> float:
        return len(claimWords & contentWords(f"{item.title} {item.text}")) / len(claimWords)

    best = max(evidence, key=overlapWith)
    overlap = overlapWith(best)
    if overlap < MIN_TOPIC_OVERLAP:
        return Prediction(label="unsupported", detail=f"evidence is off-topic (word overlap {overlap:.2f})")

    numbers = numericAgreement(claim, best.text)
    if numbers == "conflict":
        return Prediction(label="contradicted", detail=f"numbers disagree (word overlap {overlap:.2f})")
    direction = directionConflict(claim, best.text)
    if direction:
        return Prediction(label="contradicted", detail=f"{direction} (word overlap {overlap:.2f})")
    if numbers == "consistent" or overlap >= MIN_SUPPORT_OVERLAP:
        reason = "numbers agree" if numbers == "consistent" else "high word overlap"
        return Prediction(label="supported", detail=f"{reason} (word overlap {overlap:.2f})")
    return Prediction(label="unsupported", detail=f"related but not confirming (word overlap {overlap:.2f})")
