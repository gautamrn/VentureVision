from collections.abc import Iterable

MIN_QUOTE_WORDS = 3
_EDGE_PUNCTUATION = " .,;:!?\"'()[]…-"
_TYPOGRAPHIC = str.maketrans({"\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"', "\u2013": "-", "\u2014": "-"})


def normalizeText(text: str) -> str:
    return " ".join(text.lower().translate(_TYPOGRAPHIC).split())


def quoteAppearsIn(quote: str, texts: Iterable[str]) -> bool:
    """True if the quote (3+ words, case/whitespace/typography-insensitive) occurs verbatim in one of the texts."""
    normalized = normalizeText(quote).strip(_EDGE_PUNCTUATION)
    if len(normalized.split()) < MIN_QUOTE_WORDS:
        return False
    return any(normalized in normalizeText(text) for text in texts)
