from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl

AnnotationType = Literal[
    "strong",
    "contradicted",
    "needs_research",
    "weak_claim",
    "vague",
    "unsubstantiated",
]


class EvidenceItem(BaseModel):
    query: str
    title: str
    snippet: str
    source_url: HttpUrl
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Citation(BaseModel):
    quote: str
    source_url: HttpUrl
    retrieved_at: datetime


class MarketCompetitor(BaseModel):
    competitor: str
    pricing: str
    funding: str
    citation: Citation | None = None


class Subscores(BaseModel):
    market_size: int
    competition: int
    revenue_model: int
    uniqueness: int


class InvestorQuestion(BaseModel):
    question: str
    why_it_matters: str


class PitchAnnotation(BaseModel):
    excerpt: str
    annotation_type: AnnotationType
    note: str
    citation: Citation | None = None
    downgraded_from: AnnotationType | None = None


class Groundedness(BaseModel):
    cited_claims: int
    total_claims: int
    downgraded_claims: int


class DealContext(BaseModel):
    typical_stage: str
    typical_raise_range: str
    typical_dilution: str
    red_flags: list[str]


class MemoOutput(BaseModel):
    pitch_score: int
    subscores: Subscores
    strengthen_suggestions: list[str]
    executive_summary: str
    market_matrix: list[MarketCompetitor]
    risk_vectors: list[str]
    confidence_score: float
    citation_links: list[HttpUrl]
    investor_questions: list[InvestorQuestion]
    pitch_annotations: list[PitchAnnotation]
    deal_context: DealContext
    feature_suggestions: list[str]
    groundedness: Groundedness | None = None


class PitchRequest(BaseModel):
    pitch: str = Field(..., min_length=40, max_length=5000)
    mode: Literal["market_scan", "pitch_lab"] = "market_scan"


class RunResponse(BaseModel):
    status: str
    iterations: int
    memo: MemoOutput | None
