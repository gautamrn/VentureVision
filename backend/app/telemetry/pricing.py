import re
from pathlib import Path

from pydantic import BaseModel

PRICING_PATH = Path(__file__).resolve().parents[1] / "config" / "pricing.json"


class ModelPrice(BaseModel):
    input_per_million_tokens: float
    output_per_million_tokens: float


class SearchPrice(BaseModel):
    provider: str
    usd_per_credit: float
    credits_per_basic_search: int


class PricingTable(BaseModel):
    as_of: str
    sources: dict[str, str]
    models: dict[str, ModelPrice]
    search: SearchPrice


class UnpricedModelError(KeyError):
    pass


PRICING = PricingTable.model_validate_json(PRICING_PATH.read_text(encoding="utf-8"))


_DATED_SNAPSHOT = re.compile(r"^(?P<family>.+)-\d{4}-\d{2}-\d{2}$")


def modelPrice(modelName: str) -> ModelPrice:
    # OpenAI reports dated snapshots ("gpt-4o-mini-2024-07-18"); price them by their family key.
    snapshot = _DATED_SNAPSHOT.match(modelName)
    key = snapshot.group("family") if snapshot and modelName not in PRICING.models else modelName
    if key not in PRICING.models:
        raise UnpricedModelError(f"{modelName!r} has no entry in {PRICING_PATH.name}")
    return PRICING.models[key]


def llmCostUsd(modelName: str, promptTokens: int, completionTokens: int) -> float:
    price = modelPrice(modelName)
    return (
        promptTokens * price.input_per_million_tokens + completionTokens * price.output_per_million_tokens
    ) / 1_000_000


def searchCredits(searches: int = 1) -> int:
    return searches * PRICING.search.credits_per_basic_search


def searchCostUsd(searches: int = 1) -> float:
    return searchCredits(searches) * PRICING.search.usd_per_credit
